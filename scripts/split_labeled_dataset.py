from __future__ import annotations

import argparse
from pathlib import Path
from typing import cast

import pandas as pd
import yaml


REQUIRED_COLUMNS = ["open_time", "future_return", "label"]
DATASET_VERSION = "v4"


def load_settings(config_path: Path) -> dict:
    with config_path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Split labeled BTCUSDT 15m dataset into chronological train/val/test parquet files."
    )
    parser.add_argument(
        "--inspect",
        action="store_true",
        help="Print first 5 and last 5 rows for each split.",
    )
    return parser.parse_args()


def to_utc_timestamp(value: object, key_name: str) -> pd.Timestamp:
    if value is None:
        raise ValueError(f"Missing split boundary in config: {key_name}")

    value_str = str(value)
    if value_str == "":
        raise ValueError(f"Missing split boundary in config: {key_name}")

    timestamp = pd.to_datetime(value_str, utc=True, errors="coerce")
    if pd.isna(timestamp):
        raise ValueError(f"Invalid split boundary in config: {key_name}={value_str}")
    return cast(pd.Timestamp, timestamp)


def to_utc_end_exclusive(value: str, key_name: str) -> pd.Timestamp:
    return cast(pd.Timestamp, to_utc_timestamp(value, key_name) + pd.Timedelta(days=1))


def validate_required_columns(df: pd.DataFrame) -> None:
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing_columns:
        raise ValueError(
            "Labeled dataset is missing required columns: " + ", ".join(missing_columns)
        )


def validate_increasing_timestamps(df: pd.DataFrame, split_name: str) -> None:
    violations = int((df["open_time"].diff().dropna() <= pd.Timedelta(0)).sum())
    if violations > 0:
        raise ValueError(
            f"{split_name} split has non-increasing open_time steps: {violations}"
        )


def print_split_summary(split_name: str, df: pd.DataFrame) -> None:
    earliest = df["open_time"].iloc[0]
    latest = df["open_time"].iloc[-1]
    up_count = int((df["label"] == 1).sum())
    down_count = int((df["label"] == 0).sum())
    neutral_count = int((df["label"] == -1).sum())

    print(f"{split_name} rows: {len(df)}")
    print(f"{split_name} earliest open_time: {earliest}")
    print(f"{split_name} latest open_time: {latest}")
    print(f"{split_name} class distribution -> UP: {up_count}, DOWN: {down_count}, NEUTRAL: {neutral_count}")


def print_split_inspect(split_name: str, df: pd.DataFrame) -> None:
    print(f"\n{split_name} FIRST 5 ROWS")
    print("-" * 72)
    print(df.head(5).to_string(index=False))

    print(f"\n{split_name} LAST 5 ROWS")
    print("-" * 72)
    print(df.tail(5).to_string(index=False))


def main() -> None:
    args = parse_args()

    project_root = Path(__file__).resolve().parents[1]
    settings = load_settings(project_root / "config" / "settings.yaml")

    symbol = settings.get("symbol")
    timeframe = settings.get("timeframe")
    labeled_dir = settings.get("data", {}).get("labeled_dir", "data/labeled")
    splits_dir = settings.get("data", {}).get("splits_dir", "data/splits")
    split_cfg = settings.get("split", {})

    if not symbol or not timeframe:
        raise ValueError("Missing required config values: symbol, timeframe")

    train_start = to_utc_timestamp(split_cfg.get("train_start"), "split.train_start")
    train_end_exclusive = to_utc_end_exclusive(split_cfg.get("train_end"), "split.train_end")
    val_start = to_utc_timestamp(split_cfg.get("val_start"), "split.val_start")
    val_end_exclusive = to_utc_end_exclusive(split_cfg.get("val_end"), "split.val_end")
    test_start = to_utc_timestamp(split_cfg.get("test_start"), "split.test_start")

    if train_end_exclusive <= train_start:
        raise ValueError("Invalid train boundaries: train_end must be on/after train_start")
    if val_end_exclusive <= val_start:
        raise ValueError("Invalid val boundaries: val_end must be on/after val_start")

    input_path = project_root / labeled_dir / f"{symbol}_{timeframe}_labeled_{DATASET_VERSION}.parquet"
    train_output_path = project_root / splits_dir / f"{symbol}_{timeframe}_train_{DATASET_VERSION}.parquet"
    val_output_path = project_root / splits_dir / f"{symbol}_{timeframe}_val_{DATASET_VERSION}.parquet"
    test_output_path = project_root / splits_dir / f"{symbol}_{timeframe}_test_{DATASET_VERSION}.parquet"

    if not input_path.exists():
        raise FileNotFoundError(f"Labeled dataset not found: {input_path}")

    df = pd.read_parquet(input_path)
    validate_required_columns(df)

    df["open_time"] = pd.to_datetime(df["open_time"], utc=True, errors="coerce")
    if bool(df["open_time"].isna().any()):
        invalid_open_time_count = int(df["open_time"].isna().sum())
        raise ValueError(f"open_time contains invalid values: {invalid_open_time_count}")

    if not bool(df["label"].isin([0, 1, -1]).all()):
        raise ValueError("label column contains values outside {0, 1, -1}")

    df = df.sort_values("open_time", ascending=True).reset_index(drop=True)

    duplicate_count = int(df["open_time"].duplicated().sum())
    if duplicate_count > 0:
        raise ValueError(f"Labeled dataset contains duplicate open_time rows: {duplicate_count}")

    validate_increasing_timestamps(df, "Input")

    train_df = df.loc[(df["open_time"] >= train_start) & (df["open_time"] < train_end_exclusive)].copy()
    val_df = df.loc[(df["open_time"] >= val_start) & (df["open_time"] < val_end_exclusive)].copy()
    test_df = df.loc[df["open_time"] >= test_start].copy()

    splits = [("TRAIN", train_df), ("VALIDATION", val_df), ("TEST", test_df)]
    for split_name, split_df in splits:
        if split_df.empty:
            raise ValueError(
                f"{split_name} split is empty. Check split boundaries and input coverage."
            )
        validate_increasing_timestamps(split_df, split_name)

    overlap_count = int(
        pd.concat(
            [
                train_df[["open_time"]],
                val_df[["open_time"]],
                test_df[["open_time"]],
            ],
            ignore_index=True,
        )["open_time"].duplicated().sum()
    )
    if overlap_count > 0:
        raise ValueError(f"Split overlap detected across train/val/test: {overlap_count} rows")

    train_output_path.parent.mkdir(parents=True, exist_ok=True)
    train_df.to_parquet(train_output_path, index=False)
    val_df.to_parquet(val_output_path, index=False)
    test_df.to_parquet(test_output_path, index=False)

    print(f"Input dataset path: {input_path}")
    print(f"Input row count: {len(df)}")
    print("")
    print_split_summary("TRAIN", train_df)
    print("")
    print_split_summary("VALIDATION", val_df)
    print("")
    print_split_summary("TEST", test_df)
    print("")
    print(f"Saved train split: {train_output_path}")
    print(f"Saved val split: {val_output_path}")
    print(f"Saved test split: {test_output_path}")

    if args.inspect:
        with pd.option_context("display.max_columns", None, "display.width", 220):
            print_split_inspect("TRAIN", train_df)
            print_split_inspect("VALIDATION", val_df)
            print_split_inspect("TEST", test_df)


if __name__ == "__main__":
    main()
