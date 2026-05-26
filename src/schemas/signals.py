from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


SignalType = Literal["BUY", "SELL", "HOLD"]


class SignalRecord(BaseModel):
    generated_at: str
    source_timestamp: str
    predicted_for_timestamp: str
    close_price: float | None = None
    prediction_class: int
    probability_up: float
    signal_type: SignalType
    signal_reason: str
    model_version: str | None = None
    model_path: str | None = None


class SignalLatestResponse(BaseModel):
    symbol: str
    timeframe: str
    available: bool
    message: str
    signal: SignalRecord | None = None


class SignalHistoryResponse(BaseModel):
    symbol: str
    timeframe: str
    source_path: str
    count: int
    signals: list[SignalRecord]
