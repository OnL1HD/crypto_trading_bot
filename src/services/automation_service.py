from __future__ import annotations

import asyncio
import logging
import subprocess
import sys
from datetime import datetime, timezone
from uuid import uuid4

from src.core.serialization import utc_now_iso
from src.core.settings import AppSettings, load_settings
from src.schemas.automation import (
    AutomationCycleRecord,
    AutomationHistoryResponse,
    AutomationLatestCycleResponse,
    AutomationStatusResponse,
)
from src.services.automation_log_service import (
    append_automation_cycle,
    get_automation_history,
    get_latest_automation_cycle,
    has_cycle_for_bar,
)
from src.services.execution_service import run_latest_signal_execution
from src.services.inference_service import get_latest_inference
from src.services.position_manager_service import evaluate_open_positions
from src.services.reconciliation_service import run_reconciliation_check
from src.services.risk_service import evaluate_and_save_latest_risk
from src.services.signal_service import get_latest_signal
from src.services.strategy_service import evaluate_and_save_latest_strategy, get_latest_strategy


logger = logging.getLogger(__name__)


def _replace_cycle(cycle: AutomationCycleRecord, **updates: object) -> AutomationCycleRecord:
    return cycle.model_copy(update=updates)


def _tail_text(text: str, line_count: int = 12) -> str:
    lines = [line for line in text.splitlines() if line.strip() != '']
    if not lines:
        return ''
    return '\n'.join(lines[-line_count:])


def _timeframe_to_seconds(timeframe: str) -> int:
    text = timeframe.strip().lower()
    if len(text) < 2:
        raise ValueError(f'Unsupported timeframe format: {timeframe}')

    suffix = text[-1]
    value = int(text[:-1])
    if suffix == 'm':
        return value * 60
    if suffix == 'h':
        return value * 3600
    if suffix == 'd':
        return value * 86400
    raise ValueError(f'Unsupported timeframe format: {timeframe}')


def _normalize_bar_timestamp(now_utc: datetime, timeframe: str, require_completed_bar: bool) -> datetime:
    step_seconds = _timeframe_to_seconds(timeframe)
    epoch_seconds = int(now_utc.timestamp())
    slot_start_seconds = epoch_seconds - (epoch_seconds % step_seconds)
    if require_completed_bar:
        slot_start_seconds -= step_seconds
    return datetime.fromtimestamp(slot_start_seconds, tz=timezone.utc)


class AutomationService:
    def __init__(self, settings: AppSettings) -> None:
        self._settings = settings
        self._lock = asyncio.Lock()
        self._active_cycle = False

    async def run_cycle_for_bar(self, bar_timestamp: datetime, *, triggered_by: str = 'scheduler') -> AutomationCycleRecord:
        bar_iso = bar_timestamp.astimezone(timezone.utc).isoformat()
        async with self._lock:
            self._active_cycle = True
            try:
                delayed_cycle_message: str | None = None
                if triggered_by == 'scheduler' and self._settings.automation.max_cycle_delay_seconds > 0:
                    step_seconds = _timeframe_to_seconds(self._settings.timeframe)
                    expected_completion = bar_timestamp.astimezone(timezone.utc).timestamp() + step_seconds
                    cycle_delay = datetime.now(timezone.utc).timestamp() - expected_completion
                    if cycle_delay > self._settings.automation.max_cycle_delay_seconds:
                        delayed_cycle_message = f'Cycle delayed by {int(cycle_delay)}s from {triggered_by}'
                        logger.warning(
                            'Processing delayed automation cycle for %s (%ss late)',
                            bar_iso,
                            int(cycle_delay),
                        )

                if not self._settings.automation.allow_reprocess_latest_bar and has_cycle_for_bar(bar_iso, self._settings):
                    cycle = AutomationCycleRecord(
                        cycle_id=uuid4().hex,
                        started_at=utc_now_iso(),
                        finished_at=utc_now_iso(),
                        bar_timestamp=bar_iso,
                        status='skipped',
                        data_refresh_status='skipped',
                        inference_status='skipped',
                        signal_status='skipped',
                        strategy_status='skipped',
                        risk_status='skipped',
                        execution_status='skipped',
                        position_management_status='skipped',
                        reconciliation_status='skipped',
                        dry_run=self._settings.automation.dry_run,
                        execution_attempted=False,
                        execution_allowed=False,
                        execution_skipped_reason='BAR_ALREADY_PROCESSED',
                        position_management_exit_reason=None,
                        position_management_close_requested=False,
                        position_management_close_executed=False,
                        reconciliation_blocked=False,
                        reconciliation_reason_codes=[],
                        error_message=f'Automation skipped duplicate bar from {triggered_by}',
                    )
                    return append_automation_cycle(cycle, self._settings)

                cycle = AutomationCycleRecord(
                    cycle_id=uuid4().hex,
                    started_at=utc_now_iso(),
                    finished_at=None,
                    bar_timestamp=bar_iso,
                    status='running',
                    data_refresh_status='not_run',
                    inference_status='not_run',
                    signal_status='not_run',
                    strategy_status='not_run',
                    risk_status='not_run',
                    execution_status='not_run',
                    position_management_status='not_run',
                    reconciliation_status='not_run',
                    dry_run=self._settings.automation.dry_run,
                    execution_attempted=False,
                    execution_allowed=False,
                    execution_skipped_reason=None,
                    position_management_exit_reason=None,
                    position_management_close_requested=False,
                    position_management_close_executed=False,
                    reconciliation_blocked=False,
                    reconciliation_reason_codes=[],
                    error_message=delayed_cycle_message,
                )

                try:
                    await self._run_pipeline_scripts()
                    cycle = _replace_cycle(cycle, data_refresh_status='ok')
                except Exception as exc:
                    cycle = _replace_cycle(
                        cycle,
                        status='failed',
                        data_refresh_status='failed',
                        execution_status='skipped',
                        position_management_status='skipped',
                        reconciliation_status='skipped',
                        execution_skipped_reason='DATA_REFRESH_FAILED',
                        error_message=str(exc),
                    )
                    if self._settings.automation.pause_on_stage_failure:
                        return self._finalize_cycle(cycle)

                try:
                    inference = await asyncio.to_thread(get_latest_inference)
                    inference_ok = inference.configured and inference.status == 'ok'
                    cycle = _replace_cycle(
                        cycle,
                        inference_status='ok' if inference_ok else 'failed',
                        probability_up=inference.probability_up,
                        source_timestamp=inference.source_timestamp,
                        predicted_for_timestamp=inference.predicted_for_timestamp,
                    )
                    if not inference_ok and self._settings.automation.pause_on_stage_failure:
                        cycle = _replace_cycle(
                            cycle,
                            status='failed',
                            execution_status='skipped',
                            position_management_status='skipped',
                            reconciliation_status='skipped',
                            execution_skipped_reason='INFERENCE_FAILED',
                            error_message=inference.message,
                        )
                        return self._finalize_cycle(cycle)
                except Exception as exc:
                    cycle = _replace_cycle(
                        cycle,
                        status='failed',
                        inference_status='failed',
                        execution_status='skipped',
                        position_management_status='skipped',
                        reconciliation_status='skipped',
                        execution_skipped_reason='INFERENCE_FAILED',
                        error_message=str(exc),
                    )
                    return self._finalize_cycle(cycle)

                signal = get_latest_signal(settings=self._settings).signal
                cycle = _replace_cycle(
                    cycle,
                    signal_status='ok' if signal is not None else 'failed',
                    signal_type=None if signal is None else signal.signal_type,
                )

                strategy = evaluate_and_save_latest_strategy(settings=self._settings)
                cycle = _replace_cycle(
                    cycle,
                    strategy_status='ok' if strategy is not None else 'failed',
                    strategy_action=None if strategy is None else strategy.action,
                )

                risk = evaluate_and_save_latest_risk(settings=self._settings)
                cycle = _replace_cycle(
                    cycle,
                    risk_status='ok' if risk is not None else 'failed',
                    risk_allowed=None if risk is None else risk.allowed,
                    execution_allowed=False if risk is None else risk.allowed,
                )

                reconciliation_result = None
                if self._settings.reconciliation.enabled and self._settings.reconciliation.run_pre_execution_check:
                    reconciliation_result = run_reconciliation_check(source='pre_execution', settings=self._settings)
                    cycle = _replace_cycle(
                        cycle,
                        reconciliation_status='ok' if reconciliation_result.matched else ('blocked' if reconciliation_result.block_new_execution else 'failed'),
                        reconciliation_blocked=reconciliation_result.block_new_execution,
                        reconciliation_reason_codes=reconciliation_result.reason_codes,
                    )

                if not self._settings.automation.run_execution_step:
                    cycle = _replace_cycle(
                        cycle,
                        execution_status='skipped',
                        execution_skipped_reason='EXECUTION_STEP_DISABLED',
                        status='success',
                    )
                elif risk is None:
                    cycle = _replace_cycle(
                        cycle,
                        status='failed',
                        execution_status='skipped',
                        execution_skipped_reason='RISK_DECISION_UNAVAILABLE',
                    )
                elif not risk.allowed:
                    cycle = _replace_cycle(
                        cycle,
                        status='success',
                        execution_status='skipped',
                        execution_skipped_reason='RISK_BLOCKED',
                    )
                elif reconciliation_result is not None and reconciliation_result.block_new_execution:
                    cycle = _replace_cycle(
                        cycle,
                        status='success',
                        execution_status='skipped',
                        execution_skipped_reason='RECONCILIATION_BLOCKED',
                    )
                elif self._settings.automation.dry_run or not self._settings.automation.auto_execute_demo_orders:
                    cycle = _replace_cycle(
                        cycle,
                        status='success',
                        execution_status='skipped',
                        execution_attempted=False,
                        execution_skipped_reason='AUTOMATION_DRY_RUN' if self._settings.automation.dry_run else 'AUTO_EXECUTION_DISABLED',
                    )
                else:
                    execution_response = await asyncio.to_thread(run_latest_signal_execution, self._settings)
                    execution_attempted = len(execution_response.actions) > 0
                    execution_failed = any(action.status == 'failed' for action in execution_response.actions)
                    cycle = _replace_cycle(
                        cycle,
                        status='failed' if execution_failed else 'success',
                        execution_status='failed' if execution_failed else 'ok',
                        execution_attempted=execution_attempted,
                        execution_skipped_reason=None if execution_attempted else 'NO_EXECUTION_ACTIONS',
                    )

                try:
                    position_close_block_reason = None
                    if self._settings.automation.dry_run:
                        position_close_block_reason = 'POSITION_CLOSE_DRY_RUN'
                    elif not self._settings.position_management.close_positions_via_demo_execution:
                        position_close_block_reason = 'POSITION_CLOSE_AUTO_EXECUTION_DISABLED'

                    position_decisions = evaluate_open_positions(
                        settings=self._settings,
                        allow_close_execution=(
                            not self._settings.automation.dry_run
                            and self._settings.position_management.close_positions_via_demo_execution
                        ),
                        close_execution_block_reason=position_close_block_reason,
                    )
                    if position_decisions:
                        latest_position_decision = position_decisions[-1]
                        cycle = _replace_cycle(
                            cycle,
                            position_management_status='ok',
                            position_management_exit_reason=latest_position_decision.exit_reason,
                            position_management_close_requested=latest_position_decision.exit_action in {'CLOSE_LONG', 'CLOSE_SHORT'},
                            position_management_close_executed=latest_position_decision.executed_close,
                        )
                    else:
                        cycle = _replace_cycle(cycle, position_management_status='skipped')
                except Exception as exc:
                    cycle = _replace_cycle(
                        cycle,
                        status='failed',
                        position_management_status='failed',
                        position_management_exit_reason='POSITION_MANAGEMENT_FAILED',
                        error_message=str(exc),
                    )

                if self._settings.reconciliation.enabled and self._settings.reconciliation.run_post_cycle_check:
                    post_cycle_reconciliation = run_reconciliation_check(source='post_cycle', settings=self._settings)
                    cycle = _replace_cycle(
                        cycle,
                        reconciliation_status='ok' if post_cycle_reconciliation.matched else ('blocked' if post_cycle_reconciliation.block_new_execution else 'failed'),
                        reconciliation_blocked=post_cycle_reconciliation.block_new_execution,
                        reconciliation_reason_codes=post_cycle_reconciliation.reason_codes,
                    )

                return self._finalize_cycle(cycle)
            finally:
                self._active_cycle = False

    async def run_refresh_scripts(self) -> None:
        async with self._lock:
            await self._run_pipeline_scripts()

    def _finalize_cycle(self, cycle: AutomationCycleRecord) -> AutomationCycleRecord:
        finished = _replace_cycle(cycle, finished_at=utc_now_iso())
        return append_automation_cycle(finished, self._settings)

    async def _run_pipeline_scripts(self) -> None:
        for script_name in (
            'fetch_btc_ohlcv.py',
            'process_btc_ohlcv.py',
            'build_features.py',
        ):
            await self._run_script(script_name)

    async def _run_script(self, script_name: str) -> None:
        script_path = self._settings.project_root / 'scripts' / script_name
        if not script_path.exists():
            raise FileNotFoundError(f'Automation script not found: {script_path}')

        completed = await asyncio.to_thread(
            subprocess.run,
            [sys.executable, str(script_path)],
            cwd=str(self._settings.project_root),
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
        )

        if completed.returncode == 0:
            return

        combined_tail = _tail_text(completed.stderr) or _tail_text(completed.stdout)
        raise RuntimeError(
            f'{script_name} failed with exit code {completed.returncode}. '
            f'Output tail: {combined_tail}'
        )

    def get_status(self) -> AutomationStatusResponse:
        latest_cycle = get_latest_automation_cycle(self._settings)
        if not self._settings.automation.enabled:
            message = 'Automation loop is disabled by config.'
        elif self._settings.automation.dry_run:
            message = 'Automation is enabled in dry-run mode.'
        elif not self._settings.automation.auto_execute_demo_orders:
            message = 'Automation runs the cycle but automatic demo execution is disabled.'
        else:
            message = 'Automation is enabled and may place demo orders automatically.'

        return AutomationStatusResponse(
            enabled=self._settings.automation.enabled,
            dry_run=self._settings.automation.dry_run,
            run_execution_step=self._settings.automation.run_execution_step,
            auto_execute_demo_orders=self._settings.automation.auto_execute_demo_orders,
            last_processed_bar=None if latest_cycle is None else latest_cycle.bar_timestamp,
            active_cycle=self._active_cycle,
            latest_cycle=latest_cycle,
            message=message,
        )

    def get_latest_cycle_response(self) -> AutomationLatestCycleResponse:
        latest_cycle = get_latest_automation_cycle(self._settings)
        if latest_cycle is None:
            return AutomationLatestCycleResponse(
                symbol=self._settings.symbol,
                timeframe=self._settings.timeframe,
                available=False,
                message='No automation cycle has been recorded yet',
                cycle=None,
            )
        return AutomationLatestCycleResponse(
            symbol=self._settings.symbol,
            timeframe=self._settings.timeframe,
            available=True,
            message='Latest automation cycle loaded',
            cycle=latest_cycle,
        )

    def get_history_response(self, limit: int = 200) -> AutomationHistoryResponse:
        return get_automation_history(limit=limit, settings=self._settings)


_AUTOMATION_SERVICE: AutomationService | None = None


def get_automation_service(settings: AppSettings | None = None) -> AutomationService:
    global _AUTOMATION_SERVICE
    resolved_settings = settings or load_settings()
    if _AUTOMATION_SERVICE is None:
        _AUTOMATION_SERVICE = AutomationService(resolved_settings)
    return _AUTOMATION_SERVICE


def get_automation_status(settings: AppSettings | None = None) -> AutomationStatusResponse:
    return get_automation_service(settings).get_status()


def get_latest_automation_cycle_response(settings: AppSettings | None = None) -> AutomationLatestCycleResponse:
    return get_automation_service(settings).get_latest_cycle_response()


def get_automation_history_response(limit: int = 200, settings: AppSettings | None = None) -> AutomationHistoryResponse:
    return get_automation_service(settings).get_history_response(limit=limit)


async def run_automation_cycle_now(settings: AppSettings | None = None) -> AutomationCycleRecord:
    resolved_settings = settings or load_settings()
    service = get_automation_service(resolved_settings)
    bar_timestamp = _normalize_bar_timestamp(
        datetime.now(timezone.utc),
        resolved_settings.timeframe,
        resolved_settings.automation.require_completed_bar,
    )
    return await service.run_cycle_for_bar(bar_timestamp, triggered_by='manual')
