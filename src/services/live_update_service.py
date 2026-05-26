from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from src.core.settings import AppSettings
from src.services.automation_service import get_automation_service
from src.services.reconciliation_service import run_reconciliation_check


logger = logging.getLogger(__name__)


def _timeframe_to_timedelta(timeframe: str) -> timedelta:
    text = timeframe.strip().lower()
    if len(text) < 2:
        raise ValueError(f"Unsupported timeframe format: {timeframe}")

    suffix = text[-1]
    value_part = text[:-1]

    try:
        value = int(value_part)
    except ValueError as exc:
        raise ValueError(f"Unsupported timeframe format: {timeframe}") from exc

    if value <= 0:
        raise ValueError(f"Timeframe value must be positive: {timeframe}")

    if suffix == "m":
        return timedelta(minutes=value)
    if suffix == "h":
        return timedelta(hours=value)
    if suffix == "d":
        return timedelta(days=value)

    raise ValueError(f"Unsupported timeframe suffix in: {timeframe}")
class LiveUpdateService:
    def __init__(self, settings: AppSettings) -> None:
        self._settings = settings
        self._timeframe_step = _timeframe_to_timedelta(settings.timeframe)
        self._automation_service = get_automation_service(settings)
        self._task: asyncio.Task[None] | None = None
        self._stopping = asyncio.Event()
        self._lock = asyncio.Lock()
        self._last_completed_slot: datetime | None = None

    async def start(self) -> None:
        if not self._settings.live_updates_enabled:
            logger.info("Live updates are disabled")
            return

        if self._settings.reconciliation.enabled and self._settings.reconciliation.run_on_startup:
            try:
                await asyncio.to_thread(run_reconciliation_check, source='startup', settings=self._settings)
            except Exception as exc:
                logger.warning('Startup reconciliation failed: %s', exc)

        startup_slot = self._resolve_startup_slot(datetime.now(timezone.utc))
        if startup_slot is not None:
            try:
                logger.info('Running startup catch-up cycle for slot %s', startup_slot.isoformat())
                if self._settings.automation.enabled:
                    await self._automation_service.run_cycle_for_bar(startup_slot, triggered_by='startup')
                else:
                    await self._automation_service.run_refresh_scripts()
                self._last_completed_slot = startup_slot
            except Exception as exc:
                logger.warning('Startup catch-up cycle failed: %s', exc)

        if self._task is not None and not self._task.done():
            return

        self._stopping.clear()
        self._task = asyncio.create_task(self._run_loop())
        logger.info(
            "Live update loop started (poll=%ss, lag=%ss)",
            self._settings.live_update_poll_seconds,
            self._settings.live_update_lag_seconds,
        )

    async def stop(self) -> None:
        self._stopping.set()
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None

    async def _run_loop(self) -> None:
        while not self._stopping.is_set():
            try:
                await self._maybe_run_cycle()
            except Exception as exc:
                logger.exception("Live update cycle failed: %r", exc)

            try:
                await asyncio.wait_for(
                    self._stopping.wait(),
                    timeout=self._settings.live_update_poll_seconds,
                )
            except asyncio.TimeoutError:
                continue

    def _resolve_target_slot(self, now_utc: datetime) -> datetime | None:
        slot_seconds = int(self._timeframe_step.total_seconds())
        if slot_seconds <= 0:
            return None

        epoch_seconds = int(now_utc.timestamp())
        slot_start_seconds = epoch_seconds - (epoch_seconds % slot_seconds)
        slot_start = datetime.fromtimestamp(slot_start_seconds, tz=timezone.utc)

        age_seconds = int((now_utc - slot_start).total_seconds())
        if age_seconds < self._settings.live_update_lag_seconds:
            return None

        if self._settings.automation.require_completed_bar:
            completed_slot = slot_start - self._timeframe_step
            return completed_slot

        return slot_start

    def _resolve_startup_slot(self, now_utc: datetime) -> datetime | None:
        target_slot = self._resolve_target_slot(now_utc)
        if target_slot is not None:
            return target_slot

        slot_seconds = int(self._timeframe_step.total_seconds())
        if slot_seconds <= 0:
            return None

        epoch_seconds = int(now_utc.timestamp())
        slot_start_seconds = epoch_seconds - (epoch_seconds % slot_seconds)
        slot_start = datetime.fromtimestamp(slot_start_seconds, tz=timezone.utc)
        return slot_start - self._timeframe_step

    async def _maybe_run_cycle(self) -> None:
        now_utc = datetime.now(timezone.utc)
        target_slot = self._resolve_target_slot(now_utc)
        if target_slot is None:
            return

        if self._last_completed_slot is not None and target_slot <= self._last_completed_slot:
            return

        async with self._lock:
            if self._last_completed_slot is not None and target_slot <= self._last_completed_slot:
                return

            logger.info("Live update cycle started for slot %s", target_slot.isoformat())
            if self._settings.automation.enabled:
                await self._automation_service.run_cycle_for_bar(target_slot)
            else:
                await self._automation_service.run_refresh_scripts()
            self._last_completed_slot = target_slot
            logger.info("Live update cycle finished for slot %s", target_slot.isoformat())
