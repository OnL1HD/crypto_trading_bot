from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def to_iso_timestamp(value: object) -> str | None:
    if value is None:
        return None

    if isinstance(value, pd.Timestamp):
        if pd.isna(value):
            return None
        if value.tzinfo is None:
            return value.tz_localize("UTC").isoformat()
        return value.tz_convert("UTC").isoformat()

    if isinstance(value, np.datetime64):
        if np.isnat(value):
            return None
        return pd.Timestamp(value, tz="UTC").isoformat()

    parsed = pd.to_datetime(value, utc=True, errors="coerce")
    if pd.isna(parsed):
        return None
    return pd.Timestamp(parsed).isoformat()


def to_json_compatible(value: Any) -> Any:
    if value is None:
        return None

    if isinstance(value, (str, int, bool)):
        return value

    if isinstance(value, np.generic):
        value = value.item()

    if isinstance(value, (pd.Timestamp, np.datetime64)):
        return to_iso_timestamp(value)

    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return value

    if isinstance(value, (list, dict, tuple, set)):
        return value

    if pd.isna(value):
        return None

    return value


def row_to_json_dict(row: pd.Series) -> dict[str, Any]:
    return {str(key): to_json_compatible(value) for key, value in row.items()}
