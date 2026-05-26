from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pandas as pd

from src.core.serialization import to_iso_timestamp
from src.core.settings import AppSettings, load_settings, to_repo_relative
from src.schemas.inference import InferenceHistoryPoint, InferenceHistoryResponse, InferenceLatestResponse


HISTORY_COLUMNS = [
    "predicted_for_timestamp",
    "source_timestamp",
    "prediction_class",
    "probability_up",
    "decision_threshold",
    "model_version",
    "inferred_at",
]


def _history_path(settings: AppSettings) -> Path:
    return settings.inference_dir / f"{settings.symbol}_{settings.timeframe}_inference_history.parquet"


def _timeframe_to_timedelta(timeframe: str) -> timedelta:
    normalized = timeframe.strip().lower()
    if len(normalized) < 2:
        raise ValueError(f"Unsupported timeframe format: {timeframe}")

    unit = normalized[-1]
    value_text = normalized[:-1]
    try:
        value = int(value_text)
    except ValueError as exc:
        raise ValueError(f"Unsupported timeframe format: {timeframe}") from exc

    if value <= 0:
        raise ValueError(f"Timeframe value must be positive: {timeframe}")

    if unit == "m":
        return timedelta(minutes=value)
    if unit == "h":
        return timedelta(hours=value)
    if unit == "d":
        return timedelta(days=value)

    raise ValueError(f"Unsupported timeframe unit: {timeframe}")


def build_predicted_for_timestamp(source_timestamp: str, timeframe: str) -> str:
    source_ts = pd.to_datetime(source_timestamp, utc=True, errors="coerce")
    if pd.isna(source_ts):
        raise ValueError(f"Invalid source timestamp: {source_timestamp}")

    predicted_for = pd.Timestamp(source_ts) + _timeframe_to_timedelta(timeframe)
    predicted_iso = to_iso_timestamp(predicted_for)
    if predicted_iso is None:
        raise ValueError(f"Failed to compute predicted_for_timestamp from {source_timestamp}")
    return predicted_iso


def _coerce_history_frame(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.copy()
    for column in HISTORY_COLUMNS:
        if column not in normalized.columns:
            normalized[column] = None

    normalized = normalized[HISTORY_COLUMNS]
    normalized["predicted_for_timestamp"] = pd.to_datetime(
        normalized["predicted_for_timestamp"],
        utc=True,
        errors="coerce",
    )
    normalized = normalized.loc[normalized["predicted_for_timestamp"].notna()]
    normalized["source_timestamp"] = pd.to_datetime(normalized["source_timestamp"], utc=True, errors="coerce")
    normalized["inferred_at"] = pd.to_datetime(normalized["inferred_at"], utc=True, errors="coerce")
    normalized["prediction_class"] = pd.to_numeric(normalized["prediction_class"], errors="coerce")
    normalized["probability_up"] = pd.to_numeric(normalized["probability_up"], errors="coerce")
    normalized["decision_threshold"] = pd.to_numeric(normalized["decision_threshold"], errors="coerce")
    return normalized


def save_latest_inference_snapshot(
    response: InferenceLatestResponse,
    settings: AppSettings | None = None,
) -> None:
    if not response.configured or response.status != "ok":
        return
    if response.source_timestamp is None:
        return
    if response.prediction_class is None or response.probability_up is None:
        return
    if response.decision_threshold is None:
        return

    resolved_settings = settings or load_settings()
    history_path = _history_path(resolved_settings)
    predicted_for_timestamp = build_predicted_for_timestamp(
        response.source_timestamp,
        resolved_settings.timeframe,
    )

    row = {
        "predicted_for_timestamp": predicted_for_timestamp,
        "source_timestamp": response.source_timestamp,
        "prediction_class": int(response.prediction_class),
        "probability_up": float(response.probability_up),
        "decision_threshold": float(response.decision_threshold),
        "model_version": response.model_version,
        "inferred_at": response.timestamp_utc,
    }

    if history_path.exists():
        existing_df = pd.read_parquet(history_path)
        history_df = _coerce_history_frame(existing_df)
    else:
        history_df = pd.DataFrame(columns=HISTORY_COLUMNS)

    new_row_df = pd.DataFrame([row])
    new_row_df = _coerce_history_frame(new_row_df)

    if not history_df.empty:
        target_predicted_for = new_row_df.iloc[0]["predicted_for_timestamp"]
        history_df = history_df.loc[history_df["predicted_for_timestamp"] != target_predicted_for]

    updated_df = pd.concat([history_df, new_row_df], ignore_index=True)
    updated_df = updated_df.sort_values("predicted_for_timestamp", ascending=True).reset_index(drop=True)

    history_path.parent.mkdir(parents=True, exist_ok=True)
    updated_df.to_parquet(history_path, index=False)


def get_inference_history(limit: int = 300, settings: AppSettings | None = None) -> InferenceHistoryResponse:
    resolved_settings = settings or load_settings()
    history_path = _history_path(resolved_settings)

    if not history_path.exists():
        return InferenceHistoryResponse(
            symbol=resolved_settings.symbol,
            timeframe=resolved_settings.timeframe,
            source_path=to_repo_relative(history_path),
            count=0,
            predictions=[],
        )

    frame = _coerce_history_frame(pd.read_parquet(history_path))
    frame = frame.sort_values("predicted_for_timestamp", ascending=True)
    if limit > 0:
        frame = frame.tail(limit)

    points: list[InferenceHistoryPoint] = []
    for row in frame.itertuples(index=False):
        predicted_for_timestamp = to_iso_timestamp(row.predicted_for_timestamp)
        source_timestamp = to_iso_timestamp(row.source_timestamp)
        inferred_at = to_iso_timestamp(row.inferred_at)

        if (
            predicted_for_timestamp is None
            or source_timestamp is None
            or inferred_at is None
            or pd.isna(row.prediction_class)
            or pd.isna(row.probability_up)
            or pd.isna(row.decision_threshold)
        ):
            continue

        points.append(
            InferenceHistoryPoint(
                predicted_for_timestamp=predicted_for_timestamp,
                source_timestamp=source_timestamp,
                prediction_class=int(row.prediction_class),
                probability_up=float(row.probability_up),
                decision_threshold=float(row.decision_threshold),
                model_version=None if pd.isna(row.model_version) else str(row.model_version),
                inferred_at=inferred_at,
            )
        )

    return InferenceHistoryResponse(
        symbol=resolved_settings.symbol,
        timeframe=resolved_settings.timeframe,
        source_path=to_repo_relative(history_path),
        count=len(points),
        predictions=points,
    )
