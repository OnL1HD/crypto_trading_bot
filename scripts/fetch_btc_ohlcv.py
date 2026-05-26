from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import time

import pandas as pd
import requests
import yaml


BYBIT_KLINE_URL = "https://api.bybit.com/v5/market/kline"
BYBIT_CATEGORY = "linear"
BATCH_LIMIT = 1000


def load_settings(config_path: Path) -> dict:
    with config_path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def timeframe_to_bybit_interval(timeframe: str) -> str:
    mapping = {
        "1m": "1",
        "3m": "3",
        "5m": "5",
        "15m": "15",
        "30m": "30",
        "1h": "60",
        "2h": "120",
        "4h": "240",
        "6h": "360",
        "12h": "720",
        "1d": "D",
        "1w": "W",
        "1M": "M",
    }
    if timeframe not in mapping:
        raise ValueError(f"Unsupported timeframe '{timeframe}' for Bybit mapping.")
    return mapping[timeframe]


def timeframe_to_milliseconds(timeframe: str) -> int:
    minute_map = {
        "1m": 1,
        "3m": 3,
        "5m": 5,
        "15m": 15,
        "30m": 30,
        "1h": 60,
        "2h": 120,
        "4h": 240,
        "6h": 360,
        "12h": 720,
        "1d": 1440,
        "1w": 10080,
    }
    if timeframe not in minute_map:
        raise ValueError(f"Unsupported timeframe '{timeframe}' for fixed interval backfill.")
    return minute_map[timeframe] * 60 * 1000


def as_utc_milliseconds(value: str) -> int:
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        timestamp = timestamp.tz_localize("UTC")
    else:
        timestamp = timestamp.tz_convert("UTC")
    return int(timestamp.timestamp() * 1000)


def fetch_bybit_kline_batch(
    session: requests.Session,
    symbol: str,
    interval: str,
    start_ms: int,
    end_ms: int,
    limit: int = BATCH_LIMIT,
    retries: int = 3,
) -> list[list[str]]:
    params = {
        "category": BYBIT_CATEGORY,
        "symbol": symbol,
        "interval": interval,
        "start": start_ms,
        "end": end_ms,
        "limit": limit,
    }

    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            response = session.get(BYBIT_KLINE_URL, params=params, timeout=20)
            response.raise_for_status()
            payload = response.json()

            if payload.get("retCode") != 0:
                raise RuntimeError(
                    f"Bybit API error retCode={payload.get('retCode')}, "
                    f"retMsg={payload.get('retMsg')}"
                )

            return payload.get("result", {}).get("list", [])
        except (requests.RequestException, ValueError, RuntimeError) as exc:
            last_error = exc
            if attempt < retries - 1:
                time.sleep(1.0 * (attempt + 1))
                continue
            break

    raise RuntimeError(f"Failed to fetch Bybit klines after {retries} attempts: {last_error}")


def build_ohlcv_dataframe(records: list[dict]) -> pd.DataFrame:
    columns = [
        "open_time",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "turnover",
        "symbol",
        "exchange",
        "timeframe",
    ]
    df = pd.DataFrame.from_records(records, columns=columns)

    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)

    numeric_columns = ["open", "high", "low", "close", "volume", "turnover"]
    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.sort_values("open_time", ascending=True)
    df = df.drop_duplicates(subset=["open_time"], keep="last")
    df = df.reset_index(drop=True)

    return df[columns]


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    settings_path = project_root / "config" / "settings.yaml"
    settings = load_settings(settings_path)

    exchange = settings.get("exchange")
    symbol = settings.get("symbol")
    timeframe = settings.get("timeframe")
    start_date = settings.get("split", {}).get("train_start")
    raw_dir = settings.get("data", {}).get("raw_dir")

    if exchange != "bybit":
        raise ValueError(f"This script currently supports exchange='bybit' only, got '{exchange}'.")
    if not symbol or not timeframe or not start_date or not raw_dir:
        raise ValueError("Missing required settings in config/settings.yaml.")

    bybit_interval = timeframe_to_bybit_interval(timeframe)
    candle_ms = timeframe_to_milliseconds(timeframe)
    current_start_ms = as_utc_milliseconds(start_date)
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)

    records: list[dict] = []
    session = requests.Session()

    while current_start_ms <= now_ms:
        batch_end_ms = min(current_start_ms + (BATCH_LIMIT * candle_ms) - 1, now_ms)
        batch = fetch_bybit_kline_batch(
            session=session,
            symbol=symbol,
            interval=bybit_interval,
            start_ms=current_start_ms,
            end_ms=batch_end_ms,
            limit=BATCH_LIMIT,
        )

        if not batch:
            current_start_ms = batch_end_ms + candle_ms
            continue

        max_open_time_ms = current_start_ms
        for candle in batch:
            open_time_ms = int(candle[0])
            max_open_time_ms = max(max_open_time_ms, open_time_ms)
            records.append(
                {
                    "open_time": open_time_ms,
                    "open": candle[1],
                    "high": candle[2],
                    "low": candle[3],
                    "close": candle[4],
                    "volume": candle[5],
                    "turnover": candle[6],
                    "symbol": symbol,
                    "exchange": exchange,
                    "timeframe": timeframe,
                }
            )

        next_start_ms = max_open_time_ms + candle_ms
        current_start_ms = next_start_ms if next_start_ms > current_start_ms else batch_end_ms + candle_ms

    if not records:
        raise RuntimeError("No OHLCV rows were fetched from Bybit.")

    df = build_ohlcv_dataframe(records)

    output_path = project_root / raw_dir / exchange / symbol / f"{timeframe}.parquet"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output_path, index=False)

    print(f"Rows: {len(df)}")
    print(f"Earliest: {df['open_time'].iloc[0]}")
    print(f"Latest: {df['open_time'].iloc[-1]}")
    print(f"Saved: {output_path}")


if __name__ == "__main__":
    main()
