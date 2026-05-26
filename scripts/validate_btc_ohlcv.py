import argparse
from pathlib import Path

import pandas as pd
import yaml


RAW_REQUIRED_COLUMNS = [
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

PROCESSED_REQUIRED_COLUMNS = [
    "open_time",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "turnover",
]

FEATURE_REQUIRED_COLUMNS = [
    "open_time",
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
    "macd_hist",
    "atr_14_pct",
    "rolling_vol_12",
    "rolling_vol_48",
    "volume_change_1",
    "volume_ma_ratio_20",
    "turnover_ma_ratio_20",
]


def load_settings(settings_path: Path) -> dict:
    with settings_path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate raw, processed, or features BTCUSDT parquet dataset."
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--raw", action="store_true", help="Validate the raw dataset.")
    group.add_argument("--processed", action="store_true", help="Validate the processed dataset.")
    group.add_argument("--features", action="store_true", help="Validate the features dataset.")
    return parser.parse_args()


def timeframe_to_timedelta(timeframe: str):
    mapping = {
        "1m": pd.Timedelta(minutes=1),
        "3m": pd.Timedelta(minutes=3),
        "5m": pd.Timedelta(minutes=5),
        "15m": pd.Timedelta(minutes=15),
        "30m": pd.Timedelta(minutes=30),
        "1h": pd.Timedelta(hours=1),
        "2h": pd.Timedelta(hours=2),
        "4h": pd.Timedelta(hours=4),
        "6h": pd.Timedelta(hours=6),
        "12h": pd.Timedelta(hours=12),
        "1d": pd.Timedelta(days=1),
        "1w": pd.Timedelta(weeks=1),
    }
    if timeframe not in mapping:
        raise ValueError(f"Unsupported timeframe: {timeframe}")
    return mapping[timeframe]


def resolve_dataset_path(project_root: Path, settings: dict, dataset_type: str) -> Path:
    symbol = settings["symbol"]
    timeframe = settings["timeframe"]
    exchange = settings.get("exchange", "bybit")

    if dataset_type == "features":
        features_dir = settings["data"]["features_dir"]
        return project_root / features_dir / f"{symbol}_{timeframe}_features_v1.parquet"

    if dataset_type == "processed":
        processed_dir = settings["data"]["processed_dir"]
        return project_root / processed_dir / f"{symbol}_{timeframe}_clean.parquet"

    raw_dir = settings["data"]["raw_dir"]
    return project_root / raw_dir / exchange / symbol / f"{timeframe}.parquet"


def print_section(title: str) -> None:
    print(f"\n{title}")
    print("-" * 72)


def main() -> None:
    args = parse_args()
    if args.features:
        dataset_type = "features"
    elif args.processed:
        dataset_type = "processed"
    else:
        dataset_type = "raw"

    project_root = Path(__file__).resolve().parents[1]
    settings = load_settings(project_root / "config" / "settings.yaml")

    timeframe = settings["timeframe"]
    if dataset_type == "features":
        required_columns = FEATURE_REQUIRED_COLUMNS
    elif dataset_type == "processed":
        required_columns = PROCESSED_REQUIRED_COLUMNS
    else:
        required_columns = RAW_REQUIRED_COLUMNS
    dataset_path = resolve_dataset_path(project_root, settings, dataset_type)
    expected_delta = timeframe_to_timedelta(timeframe)

    print("=" * 72)
    print("DATA VALIDATION REPORT")
    print("=" * 72)

    print_section("A) File and Schema Checks")
    print(f"Dataset type: {dataset_type}")
    print(f"Dataset path: {dataset_path}")
    file_exists = dataset_path.exists()
    print(f"File exists: {'YES' if file_exists else 'NO'}")

    if not file_exists:
        print("Missing dataset file. Cannot continue validations.")
        print_section("J) Final Verdict")
        print("VALIDATION FAILED")
        return

    df = pd.read_parquet(dataset_path)
    missing_columns = [col for col in required_columns if col not in df.columns]
    print(f"Required columns present: {'YES' if not missing_columns else 'NO'}")
    if missing_columns:
        print(f"Missing columns: {missing_columns}")

    if "open_time" in df.columns:
        df["open_time"] = pd.to_datetime(df["open_time"], utc=True, errors="coerce")

    print_section("B) Null Checks")
    null_counts = df.isna().sum().sort_index()
    print(null_counts.to_string())

    print_section("C) Duplicate Timestamp Checks")
    duplicate_count = 0
    if "open_time" in df.columns:
        duplicate_mask = df["open_time"].duplicated(keep=False)
        duplicate_count = int(duplicate_mask.sum())
        print(f"Duplicate open_time rows: {duplicate_count}")
        if duplicate_count > 0:
            example_cols = [c for c in required_columns if c in df.columns]
            print("Example duplicate rows:")
            print(df.loc[duplicate_mask, example_cols].head(6).to_string(index=False))
    else:
        print("Skipped: open_time column missing.")

    print_section("D) Timestamp Ordering Checks")
    ordering_violations = 0
    if "open_time" in df.columns:
        diffs = df["open_time"].diff()
        ordering_violations = int((diffs <= pd.Timedelta(0)).sum())
        print(f"Non-increasing timestamp steps: {ordering_violations}")
    else:
        print("Skipped: open_time column missing.")

    print_section("E) Time Interval Continuity Checks")
    interval_gap_count = 0
    interval_smaller_count = 0
    broken_interval_count = 0
    if "open_time" in df.columns:
        interval_df = pd.DataFrame(
            {
                "prev_open_time": df["open_time"].shift(1),
                "open_time": df["open_time"],
            }
        ).iloc[1:]
        interval_df["diff"] = interval_df["open_time"] - interval_df["prev_open_time"]

        gap_mask = interval_df["diff"] > expected_delta
        smaller_mask = interval_df["diff"] < expected_delta
        broken_mask = gap_mask | smaller_mask

        interval_gap_count = int(gap_mask.sum())
        interval_smaller_count = int(smaller_mask.sum())
        broken_interval_count = int(broken_mask.sum())

        print(f"Expected frequency: {timeframe} ({expected_delta})")
        print(f"Missing interval / gap count: {interval_gap_count}")
        print(f"Intervals smaller than expected: {interval_smaller_count}")
        print(f"Total broken intervals: {broken_interval_count}")
        if dataset_type in {"processed", "features"} and broken_interval_count > 0:
            print(
                "Note: processed/features datasets may contain interval gaps after filtering/warmup."
            )

        if broken_interval_count > 0:
            print("Example broken intervals:")
            print(
                interval_df.loc[broken_mask, ["prev_open_time", "open_time", "diff"]]
                .head(8)
                .to_string(index=False)
            )
    else:
        print("Skipped: open_time column missing.")

    print_section("F) OHLC Logical Consistency Checks")
    ohlc_violation_total = 0
    ohlc_rule_counts = {}
    ohlc_cols = ["open", "high", "low", "close"]
    if all(col in df.columns for col in ohlc_cols):
        num = df.copy()
        for col in ["open", "high", "low", "close", "volume", "turnover"]:
            if col in num.columns:
                num[col] = pd.to_numeric(num[col], errors="coerce")

        invalid_high_open = num["high"] < num["open"]
        invalid_high_close = num["high"] < num["close"]
        invalid_low_open = num["low"] > num["open"]
        invalid_low_close = num["low"] > num["close"]
        invalid_high_low = num["high"] < num["low"]

        ohlc_rule_counts = {
            "high < open": int(invalid_high_open.sum()),
            "high < close": int(invalid_high_close.sum()),
            "low > open": int(invalid_low_open.sum()),
            "low > close": int(invalid_low_close.sum()),
            "high < low": int(invalid_high_low.sum()),
        }

        for rule, count in ohlc_rule_counts.items():
            print(f"{rule}: {count}")

        invalid_any_mask = (
            invalid_high_open
            | invalid_high_close
            | invalid_low_open
            | invalid_low_close
            | invalid_high_low
        )
        ohlc_violation_total = int(invalid_any_mask.sum())

        if ohlc_violation_total > 0:
            print("Example invalid OHLC rows:")
            cols = [c for c in ["open_time", "open", "high", "low", "close"] if c in num.columns]
            print(num.loc[invalid_any_mask, cols].head(8).to_string(index=False))
    else:
        print("Skipped: OHLC columns missing.")

    print_section("G) Numeric Sanity Checks")
    numeric_counts = {
        "open <= 0": 0,
        "high <= 0": 0,
        "low <= 0": 0,
        "close <= 0": 0,
        "volume < 0": 0,
        "turnover < 0": 0,
        "volume == 0": 0,
    }

    if dataset_type == "features":
        print("Skipped: OHLCV-specific numeric checks for features dataset.")
    else:
        numeric_df = df.copy()
        for col in ["open", "high", "low", "close", "volume", "turnover"]:
            if col in numeric_df.columns:
                numeric_df[col] = pd.to_numeric(numeric_df[col], errors="coerce")

        if "open" in numeric_df.columns:
            numeric_counts["open <= 0"] = int((numeric_df["open"] <= 0).sum())
        if "high" in numeric_df.columns:
            numeric_counts["high <= 0"] = int((numeric_df["high"] <= 0).sum())
        if "low" in numeric_df.columns:
            numeric_counts["low <= 0"] = int((numeric_df["low"] <= 0).sum())
        if "close" in numeric_df.columns:
            numeric_counts["close <= 0"] = int((numeric_df["close"] <= 0).sum())
        if "volume" in numeric_df.columns:
            numeric_counts["volume < 0"] = int((numeric_df["volume"] < 0).sum())
            numeric_counts["volume == 0"] = int((numeric_df["volume"] == 0).sum())
        if "turnover" in numeric_df.columns:
            numeric_counts["turnover < 0"] = int((numeric_df["turnover"] < 0).sum())

        for check, count in numeric_counts.items():
            print(f"{check}: {count}")

    print_section("H) Constant Metadata Checks")
    metadata_warning = False
    metadata_columns = ["symbol", "exchange", "timeframe"] if dataset_type == "raw" else []
    if not metadata_columns:
        print("Skipped for non-raw dataset.")
    else:
        for col in metadata_columns:
            if col in df.columns:
                uniques = sorted(df[col].dropna().astype(str).unique().tolist())
                print(f"{col} unique values ({len(uniques)}): {uniques}")
                if len(uniques) != 1:
                    metadata_warning = True
            else:
                print(f"{col} unique values: column missing")

    print_section("I) Dataset Summary")
    earliest_open_time = df["open_time"].min() if "open_time" in df.columns and not df.empty else "N/A"
    latest_open_time = df["open_time"].max() if "open_time" in df.columns and not df.empty else "N/A"
    print(f"Total rows: {len(df)}")
    print(f"Earliest open_time: {earliest_open_time}")
    print(f"Latest open_time: {latest_open_time}")
    print(f"Expected frequency: {timeframe}")
    print(f"Number of interval gaps: {interval_gap_count}")
    print(f"Number of duplicate timestamps: {duplicate_count}")

    missing_columns_fail = len(missing_columns) > 0
    duplicate_fail = duplicate_count > 0
    ordering_fail = ordering_violations > 0
    interval_fail = dataset_type == "raw" and broken_interval_count > 0
    interval_warning = dataset_type in {"processed", "features"} and broken_interval_count > 0
    ohlc_fail = ohlc_violation_total > 0
    non_positive_price_fail = (
        numeric_counts["open <= 0"] > 0
        or numeric_counts["high <= 0"] > 0
        or numeric_counts["low <= 0"] > 0
        or numeric_counts["close <= 0"] > 0
    )
    negative_volume_turnover_fail = (
        numeric_counts["volume < 0"] > 0 or numeric_counts["turnover < 0"] > 0
    )

    has_failure = (
        missing_columns_fail
        or duplicate_fail
        or ordering_fail
        or interval_fail
        or ohlc_fail
        or non_positive_price_fail
        or negative_volume_turnover_fail
    )
    volume_zero_warning = dataset_type != "features" and numeric_counts["volume == 0"] > 0
    has_warning = volume_zero_warning or metadata_warning or interval_warning

    print_section("J) Final Verdict")
    if has_failure:
        print("VALIDATION FAILED")
    elif has_warning:
        print("VALIDATION PASSED WITH WARNINGS")
    else:
        print("VALIDATION PASSED")


if __name__ == "__main__":
    main()
