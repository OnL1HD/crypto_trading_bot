from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.core.serialization import row_to_json_dict, to_iso_timestamp


def load_latest_row(path: Path, timestamp_column: str = "open_time") -> tuple[pd.Series, str | None]:
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")

    df = pd.read_parquet(path)
    if df.empty:
        raise ValueError(f"Dataset is empty: {path}")

    if timestamp_column in df.columns:
        df[timestamp_column] = pd.to_datetime(df[timestamp_column], utc=True, errors="coerce")
        valid_df = df.dropna(subset=[timestamp_column])
        if not valid_df.empty:
            df = valid_df.sort_values(timestamp_column, ascending=True).reset_index(drop=True)

    latest_row = df.iloc[-1]
    latest_timestamp = to_iso_timestamp(latest_row.get(timestamp_column))
    return latest_row, latest_timestamp


def latest_row_as_json(path: Path, timestamp_column: str = "open_time") -> tuple[dict[str, object], str | None]:
    latest_row, latest_timestamp = load_latest_row(path, timestamp_column=timestamp_column)
    return row_to_json_dict(latest_row), latest_timestamp
