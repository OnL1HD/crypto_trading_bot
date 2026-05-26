from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from src.schemas.signals import SignalType


RiskAction = Literal[
    'OPEN_LONG',
    'OPEN_SHORT',
    'HOLD',
    'SKIP',
    'CLOSE_LONG',
    'CLOSE_SHORT',
    'FLIP_TO_LONG',
    'FLIP_TO_SHORT',
]


class RiskDecisionRecord(BaseModel):
    decided_at: str
    source_timestamp: str
    predicted_for_timestamp: str
    requested_action: RiskAction
    approved_action: RiskAction
    allowed: bool
    order_notional_usdt: float
    approved_leverage: int
    conviction_score: float
    risk_budget_usdt: float
    stop_distance_pct: float | None = None
    volatility_penalty_multiplier: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    reason_codes: list[str]
    size_reason: str
    leverage_reason: str
    signal_type: SignalType
    probability_up: float
    strategy_version: str
    risk_version: str


class RiskLatestResponse(BaseModel):
    symbol: str
    timeframe: str
    available: bool
    message: str
    decision: RiskDecisionRecord | None = None


class RiskHistoryResponse(BaseModel):
    symbol: str
    timeframe: str
    source_path: str
    count: int
    decisions: list[RiskDecisionRecord]
