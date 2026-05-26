from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.core.serialization import to_iso_timestamp
from src.core.settings import AppSettings, load_settings, to_repo_relative
from src.schemas.inference import InferenceLatestResponse
from src.schemas.signals import SignalHistoryResponse, SignalLatestResponse, SignalRecord, SignalType


SIGNAL_REASON_V1 = "probability_threshold_v1"
SIGNAL_COLUMNS = [
    "generated_at",
    "source_timestamp",
    "predicted_for_timestamp",
    "close_price",
    "prediction_class",
    "probability_up",
    "signal_type",
    "signal_reason",
    "model_version",
    "model_path",
]


def _signals_path(settings: AppSettings) -> Path:
    return settings.signals_dir / f"{settings.symbol}_{settings.timeframe}_signal_history.parquet"


def _safe_utc_timestamp(value: str | None) -> pd.Timestamp | None:
    if value is None:
        return None
    parsed = pd.to_datetime(value, utc=True, errors="coerce")
    if pd.isna(parsed):
        return None
    return pd.Timestamp(parsed)


def _resolve_signal_type(probability_up: float, settings: AppSettings) -> SignalType:
    if probability_up >= settings.strategy.buy_signal_threshold:
        return "BUY"
    if probability_up <= settings.strategy.sell_signal_threshold:
        return "SELL"
    return "HOLD"


def _lookup_close_price(source_timestamp: str, settings: AppSettings) -> float | None:
    processed_path = settings.processed_dir / f"{settings.symbol}_{settings.timeframe}_clean.parquet"
    if not processed_path.exists():
        return None

    frame = pd.read_parquet(processed_path)
    if frame.empty or "open_time" not in frame.columns or "close" not in frame.columns:
        return None

    frame = frame[["open_time", "close"]].copy()
    frame["open_time"] = pd.to_datetime(frame["open_time"], utc=True, errors="coerce")
    frame = frame.loc[frame["open_time"].notna()]

    source_ts = _safe_utc_timestamp(source_timestamp)
    if source_ts is None:
        return None

    matched = frame.loc[frame["open_time"] == source_ts]
    if matched.empty:
        return None

    close_value = pd.to_numeric(matched.iloc[-1]["close"], errors="coerce")
    if pd.isna(close_value):
        return None
    return float(close_value)


def _coerce_signal_frame(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.copy()
    for column in SIGNAL_COLUMNS:
        if column not in normalized.columns:
            normalized[column] = None

    normalized = normalized[SIGNAL_COLUMNS]
    normalized["generated_at"] = pd.to_datetime(normalized["generated_at"], utc=True, errors="coerce")
    normalized["source_timestamp"] = pd.to_datetime(normalized["source_timestamp"], utc=True, errors="coerce")
    normalized["predicted_for_timestamp"] = pd.to_datetime(
        normalized["predicted_for_timestamp"],
        utc=True,
        errors="coerce",
    )
    normalized = normalized.loc[
        normalized["source_timestamp"].notna() & normalized["predicted_for_timestamp"].notna()
    ]

    normalized["close_price"] = pd.to_numeric(normalized["close_price"], errors="coerce")
    normalized["prediction_class"] = pd.to_numeric(normalized["prediction_class"], errors="coerce")
    normalized["probability_up"] = pd.to_numeric(normalized["probability_up"], errors="coerce")
    normalized["signal_type"] = normalized["signal_type"].astype("string")
    normalized["signal_reason"] = normalized["signal_reason"].astype("string")
    normalized["model_version"] = normalized["model_version"].astype("string")
    normalized["model_path"] = normalized["model_path"].astype("string")
    return normalized


def generate_signal_from_inference(
    inference: InferenceLatestResponse,
    settings: AppSettings | None = None,
) -> SignalRecord | None:
    if not inference.configured or inference.status != "ok":
        return None
    if (
        inference.source_timestamp is None
        or inference.predicted_for_timestamp is None
        or inference.prediction_class is None
        or inference.probability_up is None
    ):
        return None

    resolved_settings = settings or load_settings()
    signal_type = _resolve_signal_type(float(inference.probability_up), resolved_settings)
    close_price = _lookup_close_price(inference.source_timestamp, resolved_settings)

    return SignalRecord(
        generated_at=inference.timestamp_utc,
        source_timestamp=inference.source_timestamp,
        predicted_for_timestamp=inference.predicted_for_timestamp,
        close_price=close_price,
        prediction_class=int(inference.prediction_class),
        probability_up=float(inference.probability_up),
        signal_type=signal_type,
        signal_reason=SIGNAL_REASON_V1,
        model_version=inference.model_version,
        model_path=inference.model_path,
    )


def save_signal_from_inference(
    inference: InferenceLatestResponse,
    settings: AppSettings | None = None,
) -> SignalRecord | None:
    resolved_settings = settings or load_settings()
    signal = generate_signal_from_inference(inference, resolved_settings)
    if signal is None:
        return None

    history_path = _signals_path(resolved_settings)
    if history_path.exists():
        history_df = _coerce_signal_frame(pd.read_parquet(history_path))
    else:
        history_df = pd.DataFrame(columns=SIGNAL_COLUMNS)

    new_row_df = _coerce_signal_frame(pd.DataFrame([signal.model_dump()]))
    if new_row_df.empty:
        return None

    target_predicted_for = new_row_df.iloc[0]["predicted_for_timestamp"]
    target_model_version = new_row_df.iloc[0]["model_version"]

    if not history_df.empty:
        same_predicted_for = history_df["predicted_for_timestamp"] == target_predicted_for
        if pd.isna(target_model_version):
            same_model = history_df["model_version"].isna()
        else:
            same_model = history_df["model_version"] == target_model_version
        history_df = history_df.loc[~(same_predicted_for & same_model)]

    updated_df = pd.concat([history_df, new_row_df], ignore_index=True)
    updated_df = updated_df.sort_values("predicted_for_timestamp", ascending=True).reset_index(drop=True)

    history_path.parent.mkdir(parents=True, exist_ok=True)
    updated_df.to_parquet(history_path, index=False)
    return signal


def _build_signal_record(row: pd.Series) -> SignalRecord | None:
    generated_at = to_iso_timestamp(row.get("generated_at"))
    source_timestamp = to_iso_timestamp(row.get("source_timestamp"))
    predicted_for_timestamp = to_iso_timestamp(row.get("predicted_for_timestamp"))

    prediction_class_value = pd.to_numeric(row.get("prediction_class"), errors="coerce")
    probability_up_value = pd.to_numeric(row.get("probability_up"), errors="coerce")
    close_price_value = pd.to_numeric(row.get("close_price"), errors="coerce")
    signal_type_value = row.get("signal_type")
    signal_reason_value = row.get("signal_reason")

    if (
        generated_at is None
        or source_timestamp is None
        or predicted_for_timestamp is None
        or pd.isna(prediction_class_value)
        or pd.isna(probability_up_value)
        or not isinstance(signal_type_value, str)
        or signal_type_value not in {"BUY", "SELL", "HOLD"}
        or not isinstance(signal_reason_value, str)
    ):
        return None

    model_version_raw = row.get("model_version")
    model_path_raw = row.get("model_path")

    return SignalRecord(
        generated_at=generated_at,
        source_timestamp=source_timestamp,
        predicted_for_timestamp=predicted_for_timestamp,
        close_price=None if pd.isna(close_price_value) else float(close_price_value),
        prediction_class=int(prediction_class_value),
        probability_up=float(probability_up_value),
        signal_type=signal_type_value,
        signal_reason=signal_reason_value,
        model_version=None if pd.isna(model_version_raw) else str(model_version_raw),
        model_path=None if pd.isna(model_path_raw) else str(model_path_raw),
    )


def get_latest_signal(settings: AppSettings | None = None) -> SignalLatestResponse:
    resolved_settings = settings or load_settings()
    history_path = _signals_path(resolved_settings)

    if not history_path.exists():
        return SignalLatestResponse(
            symbol=resolved_settings.symbol,
            timeframe=resolved_settings.timeframe,
            available=False,
            message="No signal history artifact found yet",
            signal=None,
        )

    frame = _coerce_signal_frame(pd.read_parquet(history_path))
    frame = frame.sort_values("predicted_for_timestamp", ascending=True)
    if frame.empty:
        return SignalLatestResponse(
            symbol=resolved_settings.symbol,
            timeframe=resolved_settings.timeframe,
            available=False,
            message="Signal history is empty",
            signal=None,
        )

    latest_signal = _build_signal_record(frame.iloc[-1])
    if latest_signal is None:
        return SignalLatestResponse(
            symbol=resolved_settings.symbol,
            timeframe=resolved_settings.timeframe,
            available=False,
            message="No valid signal row available in history",
            signal=None,
        )

    return SignalLatestResponse(
        symbol=resolved_settings.symbol,
        timeframe=resolved_settings.timeframe,
        available=True,
        message="Latest signal loaded",
        signal=latest_signal,
    )


def get_signal_history(
    limit: int = 200,
    start: str | None = None,
    end: str | None = None,
    settings: AppSettings | None = None,
) -> SignalHistoryResponse:
    resolved_settings = settings or load_settings()
    history_path = _signals_path(resolved_settings)

    if not history_path.exists():
        return SignalHistoryResponse(
            symbol=resolved_settings.symbol,
            timeframe=resolved_settings.timeframe,
            source_path=to_repo_relative(history_path),
            count=0,
            signals=[],
        )

    frame = _coerce_signal_frame(pd.read_parquet(history_path))
    frame = frame.sort_values("predicted_for_timestamp", ascending=True)

    if start is not None:
        start_ts = _safe_utc_timestamp(start)
        if start_ts is None:
            raise ValueError(f"Invalid 'start' timestamp: {start}")
        frame = frame.loc[frame["predicted_for_timestamp"] >= start_ts]

    if end is not None:
        end_ts = _safe_utc_timestamp(end)
        if end_ts is None:
            raise ValueError(f"Invalid 'end' timestamp: {end}")
        frame = frame.loc[frame["predicted_for_timestamp"] <= end_ts]

    if limit > 0:
        frame = frame.tail(limit)

    signals: list[SignalRecord] = []
    for row in frame.to_dict(orient="records"):
        signal = _build_signal_record(pd.Series(row))
        if signal is not None:
            signals.append(signal)

    return SignalHistoryResponse(
        symbol=resolved_settings.symbol,
        timeframe=resolved_settings.timeframe,
        source_path=to_repo_relative(history_path),
        count=len(signals),
        signals=signals,
    )
