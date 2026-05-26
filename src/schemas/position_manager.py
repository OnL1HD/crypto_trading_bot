from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from src.schemas.execution import PositionDirection, TradeStatus


PositionExitAction = Literal['CLOSE_LONG', 'CLOSE_SHORT', 'HOLD_POSITION', 'SKIP_POSITION']


class PositionManagementDecisionRecord(BaseModel):
    decision_id: str
    decided_at: str
    trade_id: str
    symbol: str
    direction: PositionDirection
    position_status: TradeStatus
    current_price: float | None = None
    entry_price: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    holding_minutes: float
    exit_action: PositionExitAction
    exit_reason: str
    should_execute_close: bool
    executed_close: bool
    execution_skipped_reason: str | None = None
    strategy_context_summary: str | None = None
    source_timestamp: str | None = None
    strategy_version: str | None = None
    position_management_version: str


class PositionManagementLatestResponse(BaseModel):
    symbol: str
    timeframe: str
    available: bool
    message: str
    decision: PositionManagementDecisionRecord | None = None


class PositionManagementHistoryResponse(BaseModel):
    symbol: str
    timeframe: str
    source_path: str
    count: int
    decisions: list[PositionManagementDecisionRecord]
