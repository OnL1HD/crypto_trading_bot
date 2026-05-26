from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


AutomationCycleStatus = Literal['success', 'failed', 'skipped', 'running']
StageStatus = Literal['ok', 'failed', 'skipped', 'not_run']


class AutomationCycleRecord(BaseModel):
    cycle_id: str
    started_at: str
    finished_at: str | None = None
    bar_timestamp: str
    status: AutomationCycleStatus
    data_refresh_status: StageStatus
    inference_status: StageStatus
    signal_status: StageStatus
    strategy_status: StageStatus
    risk_status: StageStatus
    execution_status: StageStatus
    position_management_status: StageStatus
    reconciliation_status: StageStatus
    dry_run: bool
    execution_attempted: bool
    execution_allowed: bool
    execution_skipped_reason: str | None = None
    position_management_exit_reason: str | None = None
    position_management_close_requested: bool = False
    position_management_close_executed: bool = False
    reconciliation_blocked: bool = False
    reconciliation_reason_codes: list[str] = []
    signal_type: str | None = None
    strategy_action: str | None = None
    risk_allowed: bool | None = None
    probability_up: float | None = None
    source_timestamp: str | None = None
    predicted_for_timestamp: str | None = None
    error_message: str | None = None


class AutomationStatusResponse(BaseModel):
    enabled: bool
    dry_run: bool
    run_execution_step: bool
    auto_execute_demo_orders: bool
    last_processed_bar: str | None = None
    active_cycle: bool
    latest_cycle: AutomationCycleRecord | None = None
    message: str


class AutomationLatestCycleResponse(BaseModel):
    symbol: str
    timeframe: str
    available: bool
    message: str
    cycle: AutomationCycleRecord | None = None


class AutomationHistoryResponse(BaseModel):
    symbol: str
    timeframe: str
    source_path: str
    count: int
    cycles: list[AutomationCycleRecord]
