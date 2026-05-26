from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import yaml


HORIZON_CANDLES = 12
RETURN_THRESHOLD = 0.003
DATASET_VERSION = "v4"


def load_settings(config_path: Path) -> dict:
    with config_path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build directional classification labels for BTCUSDT 15m features."
    )
    parser.add_argument(
        "--inspect",
        action="store_true",
        help="Print column list and first/last 10 rows of labeled output.",
    )
    return parser.parse_args()


def validate_timestamp_integrity(df: pd.DataFrame, dataset_name: str) -> None:
    duplicate_count = int(df["open_time"].duplicated().sum())
    if duplicate_count > 0:
        raise ValueError(f"{dataset_name} contains duplicate open_time rows: {duplicate_count}")

    ordering_violations = int((df["open_time"].diff().dropna() <= pd.Timedelta(0)).sum())
    if ordering_violations > 0:
        raise ValueError(
            f"{dataset_name} has non-increasing open_time steps: {ordering_violations}"
        )


def validate_no_feature_nans(df: pd.DataFrame, feature_columns: list[str]) -> None:
    feature_nan_counts = df[feature_columns].isna().sum()
    nan_columns = feature_nan_counts[feature_nan_counts > 0]
    if not nan_columns.empty:
        details = ", ".join(f"{col}={int(count)}" for col, count in nan_columns.items())
        raise ValueError(f"Feature NaNs detected: {details}")


def main() -> None:
    args = parse_args()

    project_root = Path(__file__).resolve().parents[1]
    settings = load_settings(project_root / "config" / "settings.yaml")

    symbol = settings.get("symbol")
    timeframe = settings.get("timeframe")
    processed_dir = settings.get("data", {}).get("processed_dir")
    features_dir = settings.get("data", {}).get("features_dir")
    labeled_dir = settings.get("data", {}).get("labeled_dir", "data/labeled")

    if not symbol or not timeframe or not processed_dir or not features_dir:
        raise ValueError(
            "Missing required config values: symbol, timeframe, data.processed_dir, data.features_dir"
        )

    features_path = project_root / features_dir / f"{symbol}_{timeframe}_features_{DATASET_VERSION}.parquet"
    processed_path = project_root / processed_dir / f"{symbol}_{timeframe}_clean.parquet"
    output_path = project_root / labeled_dir / f"{symbol}_{timeframe}_labeled_{DATASET_VERSION}.parquet"

    if not features_path.exists():
        raise FileNotFoundError(f"Features dataset not found: {features_path}")
    if not processed_path.exists():
        raise FileNotFoundError(f"Processed dataset not found: {processed_path}")

    feature_df = pd.read_parquet(features_path, engine="pyarrow")
    processed_df = pd.read_parquet(processed_path, engine="pyarrow")

    feature_df["open_time"] = pd.to_datetime(feature_df["open_time"], utc=True, errors="coerce")
    processed_df["open_time"] = pd.to_datetime(processed_df["open_time"], utc=True, errors="coerce")
    processed_df["close"] = pd.to_numeric(processed_df["close"], errors="coerce")

    feature_df = feature_df.sort_values("open_time", ascending=True).reset_index(drop=True)
    processed_df = processed_df.sort_values("open_time", ascending=True).reset_index(drop=True)

    validate_timestamp_integrity(feature_df, "Features dataset")
    validate_timestamp_integrity(processed_df, "Processed dataset")

    feature_columns = [column for column in feature_df.columns if column != "open_time"]
    if not feature_columns:
        raise ValueError("Features dataset does not contain feature columns.")

    validate_no_feature_nans(feature_df, feature_columns)

    close_df = processed_df[["open_time", "close"]].copy()
    close_nan_count = int(pd.isna(close_df["close"]).sum())
    if close_nan_count > 0:
        raise ValueError(f"Processed close column contains NaNs: {close_nan_count}")

    merged_df = feature_df.merge(close_df, on="open_time", how="inner", validate="one_to_one")
    merged_df = merged_df.sort_values("open_time", ascending=True).reset_index(drop=True)

    if len(merged_df) != len(feature_df):
        raise ValueError(
            "Feature/processed alignment failed after inner join: "
            f"features_rows={len(feature_df)}, merged_rows={len(merged_df)}"
        )

    merged_df["future_return"] = (merged_df["close"].shift(-HORIZON_CANDLES) / merged_df["close"]) - 1.0

    if len(merged_df) <= HORIZON_CANDLES:
        raise ValueError(
            f"Insufficient rows to build labels with horizon={HORIZON_CANDLES}: {len(merged_df)}"
        )

    rows_before_labeling = len(merged_df)
    rows_dropped_horizon = HORIZON_CANDLES
    label_base_df = merged_df.iloc[:-HORIZON_CANDLES].copy()

    labeled_df = label_base_df.copy()
    up_mask = labeled_df["future_return"] > RETURN_THRESHOLD
    down_mask = labeled_df["future_return"] < -RETURN_THRESHOLD
    labeled_df["label"] = np.select(
        [up_mask, down_mask],
        [1, 0],
        default=-1,
    ).astype("int8")

    if rows_before_labeling - len(label_base_df) != HORIZON_CANDLES:
        raise RuntimeError(
            "Unexpected horizon drop count: "
            f"expected={HORIZON_CANDLES}, actual={rows_before_labeling - len(label_base_df)}"
        )

    validate_no_feature_nans(labeled_df, feature_columns)

    if bool(labeled_df["future_return"].isna().any()):
        future_return_nan_count = int(labeled_df["future_return"].isna().sum())
        raise ValueError(f"future_return contains NaNs after horizon trim: {future_return_nan_count}")

    if not bool(labeled_df["label"].isin([1, 0, -1]).all()):
        raise ValueError("label column contains values outside {1, 0, -1}")

    validate_timestamp_integrity(labeled_df, "Labeled dataset")

    final_columns = ["open_time", *feature_columns, "future_return", "label"]
    labeled_df = labeled_df[final_columns].reset_index(drop=True)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    labeled_df.to_parquet(output_path, index=False, engine="pyarrow")

    up_count = int((labeled_df["label"] == 1).sum())
    down_count = int((labeled_df["label"] == 0).sum())
    neutral_count = int((labeled_df["label"] == -1).sum())

    print(f"Input row count: {rows_before_labeling}")
    print(f"Rows dropped due to horizon: {rows_dropped_horizon}")
    print(f"UP: {up_count}")
    print(f"DOWN: {down_count}")
    print(f"NEUTRAL: {neutral_count}")
    print(f"Final dataset size: {len(labeled_df)}")
    print(f"Saved: {output_path}")

    if args.inspect:
        print("\nCOLUMN LIST")
        print("-" * 72)
        print(list(labeled_df.columns))

        print("\nFIRST 10 ROWS")
        print("-" * 72)
        with pd.option_context("display.max_columns", None, "display.width", 220):
            print(labeled_df.head(10).to_string(index=False))

        print("\nLAST 10 ROWS")
        print("-" * 72)
        with pd.option_context("display.max_columns", None, "display.width", 220):
            print(labeled_df.tail(10).to_string(index=False))


if __name__ == "__main__":
    main()
