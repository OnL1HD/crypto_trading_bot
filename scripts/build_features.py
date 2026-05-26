from __future__ import annotations

from pathlib import Path
from typing import cast

import numpy as np
import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator, MACD
from ta.volatility import AverageTrueRange
import yaml


REQUIRED_INPUT_COLUMNS = [
    "open_time",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "turnover",
]

NUMERIC_COLUMNS = ["open", "high", "low", "close", "volume", "turnover"]

FEATURE_COLUMNS = [
    "log_return_1",
    "log_return_4",
    "close_to_open_return",
    "high_low_range_pct",
    "body_pct",
    "upper_wick_pct",
    "lower_wick_pct",
    "body_to_range_ratio",
    "ema_20_dist",
    "ema_50_dist",
    "ema_20_50_spread",
    "rsi_14",
    "rsi_14_change_1",
    "macd_hist",
    "macd_hist_change_1",
    "atr_14_pct",
    "rolling_vol_12",
    "rolling_vol_48",
    "volume_change_1",
    "volume_ma_ratio_20",
    "turnover_ma_ratio_20",
    "hour_sin",
    "hour_cos",
    "dow_sin",
    "dow_cos",
    "close_to_rolling_high_96",
    "close_to_rolling_low_96",
    "range_position_96",
]

FEATURE_VERSION = "v4"


def load_settings(config_path: Path) -> dict:
    with config_path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def validate_required_columns(df: pd.DataFrame) -> None:
    missing_columns = [column for column in REQUIRED_INPUT_COLUMNS if column not in df.columns]
    if missing_columns:
        raise ValueError(
            "Processed dataset is missing required columns: " + ", ".join(missing_columns)
        )


def cast_input_types(df: pd.DataFrame) -> pd.DataFrame:
    typed_df = df.copy()
    typed_df["open_time"] = pd.to_datetime(typed_df["open_time"], utc=True, errors="coerce")
    for column in NUMERIC_COLUMNS:
        typed_df[column] = pd.to_numeric(typed_df[column], errors="coerce")
    return typed_df


def build_feature_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    open_ = df["open"]
    high = df["high"]
    low = df["low"]
    close = df["close"]
    volume = df["volume"]
    turnover = df["turnover"]

    ema_20 = EMAIndicator(close=close, window=20).ema_indicator()
    ema_50 = EMAIndicator(close=close, window=50).ema_indicator()
    rsi_14 = RSIIndicator(close=close, window=14).rsi()
    macd_hist = MACD(close=close).macd_diff()
    atr_14 = AverageTrueRange(high=high, low=low, close=close, window=14).average_true_range()

    candle_top = pd.concat([open_, close], axis=1).max(axis=1)
    candle_bottom = pd.concat([open_, close], axis=1).min(axis=1)
    candle_range = (high - low).replace(0, np.nan)
    rolling_high_96 = high.rolling(window=96).max()
    rolling_low_96 = low.rolling(window=96).min()
    rolling_range_96 = (rolling_high_96 - rolling_low_96).replace(0, np.nan)
    hour = df["open_time"].dt.hour
    day_of_week = df["open_time"].dt.dayofweek

    features = pd.DataFrame(index=df.index)
    features["open_time"] = df["open_time"]
    features["log_return_1"] = np.log(close / close.shift(1))
    features["log_return_4"] = np.log(close / close.shift(4))
    features["close_to_open_return"] = (close / open_) - 1
    features["high_low_range_pct"] = (high / low) - 1
    features["body_pct"] = (close - open_) / open_
    features["upper_wick_pct"] = (high - candle_top) / open_
    features["lower_wick_pct"] = (candle_bottom - low) / open_
    features["body_to_range_ratio"] = (close - open_).abs() / candle_range
    features["ema_20_dist"] = (close / ema_20) - 1
    features["ema_50_dist"] = (close / ema_50) - 1
    features["ema_20_50_spread"] = (ema_20 / ema_50) - 1
    features["rsi_14"] = rsi_14
    features["rsi_14_change_1"] = rsi_14.diff(periods=1)
    features["macd_hist"] = macd_hist
    features["macd_hist_change_1"] = macd_hist.diff(periods=1)
    features["atr_14_pct"] = atr_14 / close
    features["rolling_vol_12"] = features["log_return_1"].rolling(window=12).std()
    features["rolling_vol_48"] = features["log_return_1"].rolling(window=48).std()
    features["volume_change_1"] = volume.pct_change(periods=1)
    features["volume_ma_ratio_20"] = volume / volume.rolling(window=20).mean()
    features["turnover_ma_ratio_20"] = turnover / turnover.rolling(window=20).mean()
    features["hour_sin"] = np.sin(2 * np.pi * hour / 24.0)
    features["hour_cos"] = np.cos(2 * np.pi * hour / 24.0)
    features["dow_sin"] = np.sin(2 * np.pi * day_of_week / 7.0)
    features["dow_cos"] = np.cos(2 * np.pi * day_of_week / 7.0)
    features["close_to_rolling_high_96"] = (close / rolling_high_96) - 1
    features["close_to_rolling_low_96"] = (close / rolling_low_96) - 1
    features["range_position_96"] = (close - rolling_low_96) / rolling_range_96

    features = features[["open_time", *FEATURE_COLUMNS]]
    features = features.replace([np.inf, -np.inf], np.nan)
    return cast(pd.DataFrame, features)


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    settings = load_settings(project_root / "config" / "settings.yaml")

    symbol = settings.get("symbol")
    timeframe = settings.get("timeframe")
    processed_dir = settings.get("data", {}).get("processed_dir")
    features_dir = settings.get("data", {}).get("features_dir")

    if not symbol or not timeframe or not processed_dir or not features_dir:
        raise ValueError(
            "Missing required config values: symbol, timeframe, data.processed_dir, data.features_dir"
        )

    input_path = project_root / processed_dir / f"{symbol}_{timeframe}_clean.parquet"
    output_path = project_root / features_dir / f"{symbol}_{timeframe}_features_{FEATURE_VERSION}.parquet"

    if not input_path.exists():
        raise FileNotFoundError(f"Processed dataset not found: {input_path}")

    input_df = pd.read_parquet(input_path)
    input_row_count = len(input_df)

    validate_required_columns(input_df)
    typed_df = cast_input_types(input_df)
    typed_df = typed_df.sort_values("open_time", ascending=True).reset_index(drop=True)

    feature_df = build_feature_dataframe(typed_df)

    row_count_before_drop = len(feature_df)
    feature_df = feature_df.dropna().reset_index(drop=True)
    dropped_warmup_rows = row_count_before_drop - len(feature_df)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    feature_df.to_parquet(output_path, index=False)

    output_row_count = len(feature_df)
    earliest_open_time = feature_df["open_time"].iloc[0] if not feature_df.empty else "N/A"
    latest_open_time = feature_df["open_time"].iloc[-1] if not feature_df.empty else "N/A"

    print(f"Input file path: {input_path}")
    print(f"Output file path: {output_path}")
    print(f"Input row count: {input_row_count}")
    print(f"Output row count: {output_row_count}")
    print(f"Rows dropped due to NaNs / warmup: {dropped_warmup_rows}")
    print(f"Earliest open_time in output: {earliest_open_time}")
    print(f"Latest open_time in output: {latest_open_time}")
    print(f"Final feature column list: {FEATURE_COLUMNS}")


if __name__ == "__main__":
    main()
