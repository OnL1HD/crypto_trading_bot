from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class MarketLatestResponse(BaseModel):
    symbol: str
    timeframe: str
    source_path: str
    latest_timestamp: str | None
    candle: dict[str, Any]


class MarketCandle(BaseModel):
    open_time: str
    open: float | None
    high: float | None
    low: float | None
    close: float | None
    volume: float | None


class MarketCandlesResponse(BaseModel):
    symbol: str
    timeframe: str
    source_path: str
    count: int
    candles: list[MarketCandle]
