from __future__ import annotations

import math

import pandas as pd

from src.core.serialization import to_iso_timestamp
from src.core.settings import load_settings, to_repo_relative
from src.schemas.market import MarketCandle, MarketCandlesResponse, MarketLatestResponse
from src.services.data_snapshot_service import latest_row_as_json


def get_latest_market_candle() -> MarketLatestResponse:
    settings = load_settings()
    source_path = settings.processed_dir / f"{settings.symbol}_{settings.timeframe}_clean.parquet"
    candle, latest_timestamp = latest_row_as_json(source_path)

    return MarketLatestResponse(
        symbol=settings.symbol,
        timeframe=settings.timeframe,
        source_path=to_repo_relative(source_path),
        latest_timestamp=latest_timestamp,
        candle=candle,
    )


def _parse_utc_timestamp(value: str, field_name: str) -> pd.Timestamp:
    parsed = pd.to_datetime(value, utc=True, errors="coerce")
    if pd.isna(parsed):
        raise ValueError(f"Invalid '{field_name}' timestamp: {value}")
    return pd.Timestamp(parsed)


def _safe_float(value: object) -> float | None:
    if value is None:
        return None

    numeric = pd.to_numeric(value, errors="coerce")
    if pd.isna(numeric):
        return None

    number = float(numeric)
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def get_market_candles(
    limit: int = 300,
    start: str | None = None,
    end: str | None = None,
) -> MarketCandlesResponse:
    if limit <= 0:
        raise ValueError("'limit' must be a positive integer")

    settings = load_settings()
    source_path = settings.processed_dir / f"{settings.symbol}_{settings.timeframe}_clean.parquet"
    if not source_path.exists():
        raise FileNotFoundError(f"Dataset not found: {source_path}")

    df = pd.read_parquet(source_path)
    if df.empty:
        return MarketCandlesResponse(
            symbol=settings.symbol,
            timeframe=settings.timeframe,
            source_path=to_repo_relative(source_path),
            count=0,
            candles=[],
        )

    required_columns = ["open_time", "open", "high", "low", "close", "volume"]
    missing_columns = [column for column in required_columns if column not in df.columns]
    if missing_columns:
        raise ValueError(
            "Processed dataset is missing required candle columns: " + ", ".join(missing_columns)
        )

    df = df[required_columns].copy()
    df["open_time"] = pd.to_datetime(df["open_time"], utc=True, errors="coerce")
    df = df.dropna(subset=["open_time"])
    df = df.sort_values("open_time", ascending=True).reset_index(drop=True)

    if start is not None:
        start_ts = _parse_utc_timestamp(start, "start")
        df = df.loc[df["open_time"] >= start_ts]

    if end is not None:
        end_ts = _parse_utc_timestamp(end, "end")
        df = df.loc[df["open_time"] <= end_ts]

    if df.empty:
        return MarketCandlesResponse(
            symbol=settings.symbol,
            timeframe=settings.timeframe,
            source_path=to_repo_relative(source_path),
            count=0,
            candles=[],
        )

    df = df.tail(limit).reset_index(drop=True)

    candles = [
        MarketCandle(
            open_time=to_iso_timestamp(row.open_time) or "",
            open=_safe_float(row.open),
            high=_safe_float(row.high),
            low=_safe_float(row.low),
            close=_safe_float(row.close),
            volume=_safe_float(row.volume),
        )
        for row in df.itertuples(index=False)
    ]

    return MarketCandlesResponse(
        symbol=settings.symbol,
        timeframe=settings.timeframe,
        source_path=to_repo_relative(source_path),
        count=len(candles),
        candles=candles,
    )
