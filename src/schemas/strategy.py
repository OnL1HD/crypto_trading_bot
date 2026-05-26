from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from src.schemas.signals import SignalType


StrategyAction = Literal['OPEN_LONG', 'OPEN_SHORT', 'HOLD', 'SKIP']
ConfidenceBucket = Literal[
    'STRONG_BULLISH',
    'MEDIUM_BULLISH',
    'WEAK_BULLISH',
    'NEUTRAL',
    'WEAK_BEARISH',
    'MEDIUM_BEARISH',
    'STRONG_BEARISH',
]
ContextLabel = Literal['supportive', 'neutral', 'adverse', 'missing']


class StrategySupportingContext(BaseModel):
    feature_snapshot_available: bool
    trend_aligned: bool
    volatility_suitable: bool
    volume_supported: bool
    momentum_supported: bool
    signal_persistent: bool
    flip_noise_blocked: bool
    has_open_long: bool
    has_open_short: bool
    counter_trend_signal: bool


class StrategyDecisionRecord(BaseModel):
    decided_at: str
    source_timestamp: str
    predicted_for_timestamp: str
    probability_up: float
    prediction_class: int
    signal_type: SignalType
    confidence_bucket: ConfidenceBucket
    trend_context: ContextLabel
    volatility_context: ContextLabel
    volume_context: ContextLabel
    momentum_context: ContextLabel
    action: StrategyAction
    action_reason: str
    supporting_context: StrategySupportingContext
    strategy_version: str
    model_version: str | None = None


class StrategyLatestResponse(BaseModel):
    symbol: str
    timeframe: str
    available: bool
    message: str
    decision: StrategyDecisionRecord | None = None


class StrategyHistoryResponse(BaseModel):
    symbol: str
    timeframe: str
    source_path: str
    count: int
    decisions: list[StrategyDecisionRecord]
