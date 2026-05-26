from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


ExecutionMode = Literal['demo']
ExecutionStatus = Literal[
    'disabled',
    'skipped',
    'rejected',
    'placed',
    'closed',
    'failed',
]
PositionDirection = Literal['LONG', 'SHORT']
TradeStatus = Literal['OPEN', 'CLOSED']


class ExecutionAttemptRecord(BaseModel):
    attempted_at: str
    execution_key: str
    signal_type: str
    source_timestamp: str | None = None
    predicted_for_timestamp: str | None = None
    symbol: str
    side: str | None = None
    position_direction: PositionDirection | None = None
    order_type: str
    order_notional_usdt: float
    leverage: int
    execution_mode: ExecutionMode
    success: bool
    status: ExecutionStatus
    exchange_order_id: str | None = None
    exchange_response_code: str | None = None
    exchange_response_message: str | None = None
    error_message: str | None = None


class ExecutionHistoryResponse(BaseModel):
    symbol: str
    source_path: str
    count: int
    executions: list[ExecutionAttemptRecord]


class TradeRecord(BaseModel):
    trade_id: str
    symbol: str
    direction: PositionDirection
    entry_time: str
    entry_price: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    entry_order_id: str | None = None
    exit_time: str | None = None
    exit_price: float | None = None
    exit_order_id: str | None = None
    leverage: int
    quantity: float
    status: TradeStatus
    source_entry_signal: str
    source_exit_signal: str | None = None
    realized_pnl: float | None = None
    execution_mode: ExecutionMode


class OpenPositionsResponse(BaseModel):
    symbol: str
    source_path: str
    count: int
    positions: list[TradeRecord]


class TradeHistoryResponse(BaseModel):
    symbol: str
    source_path: str
    count: int
    trades: list[TradeRecord]


class ExecutionStatusResponse(BaseModel):
    enabled: bool
    mode: ExecutionMode
    symbol: str
    market_type: str
    order_type: str
    leverage: int
    max_open_positions: int
    open_positions_count: int
    demo_api_configured: bool
    demo_trading_enabled: bool
    dry_run_logging: bool
    latest_execution: ExecutionAttemptRecord | None = None
    message: str


class ExecutionRunResponse(BaseModel):
    triggered_at: str
    signal_type: str | None = None
    execution_key: str | None = None
    message: str
    actions: list[ExecutionAttemptRecord]
