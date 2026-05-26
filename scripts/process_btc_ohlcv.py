from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml


REQUIRED_COLUMNS = [
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

NUMERIC_COLUMNS = ["open", "high", "low", "close", "volume", "turnover"]
OUTPUT_COLUMNS = ["open_time", "open", "high", "low", "close", "volume", "turnover"]


def load_settings(config_path: Path) -> dict:
    with config_path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def validate_required_columns(df: pd.DataFrame) -> None:
    missing_columns = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_columns:
        raise ValueError(
            "Raw dataset is missing required columns: "
            + ", ".join(missing_columns)
        )


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    settings = load_settings(project_root / "config" / "settings.yaml")

    symbol = settings.get("symbol")
    timeframe = settings.get("timeframe")
    exchange = settings.get("exchange", "bybit")
    raw_dir = settings.get("data", {}).get("raw_dir")
    processed_dir = settings.get("data", {}).get("processed_dir")

    if not symbol or not timeframe or not raw_dir or not processed_dir:
        raise ValueError(
            "Missing required config values: symbol, timeframe, data.raw_dir, data.processed_dir"
        )

    input_path = project_root / raw_dir / exchange / symbol / f"{timeframe}.parquet"
    output_path = project_root / processed_dir / f"{symbol}_{timeframe}_clean.parquet"

    if not input_path.exists():
        raise FileNotFoundError(f"Raw dataset not found: {input_path}")

    raw_df = pd.read_parquet(input_path)
    input_row_count = len(raw_df)
    validate_required_columns(raw_df)

    df = raw_df.copy()
    df["open_time"] = pd.to_datetime(df["open_time"], utc=True, errors="coerce")
    for column in NUMERIC_COLUMNS:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    df = df.sort_values("open_time", ascending=True)

    before_drop_duplicates = len(df)
    df = df.drop_duplicates(subset=["open_time"], keep="last")
    duplicate_rows_removed = before_drop_duplicates - len(df)

    zero_volume_rows_removed = int((df["volume"] == 0).sum())
    df = df.loc[df["volume"] != 0]

    df = df[OUTPUT_COLUMNS].reset_index(drop=True)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output_path, index=False)

    output_row_count = len(df)
    earliest_open_time = df["open_time"].iloc[0] if not df.empty else "N/A"
    latest_open_time = df["open_time"].iloc[-1] if not df.empty else "N/A"

    print(f"Input file path: {input_path}")
    print(f"Output file path: {output_path}")
    print(f"Input row count: {input_row_count}")
    print(f"Output row count: {output_row_count}")
    print(f"Rows removed due to zero volume: {zero_volume_rows_removed}")
    print(f"Rows removed due to duplicate timestamps: {duplicate_rows_removed}")
    print(f"Earliest open_time after processing: {earliest_open_time}")
    print(f"Latest open_time after processing: {latest_open_time}")
    print(f"Final column list: {list(df.columns)}")


if __name__ == "__main__":
    main()
