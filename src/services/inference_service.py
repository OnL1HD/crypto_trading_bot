from __future__ import annotations

from pathlib import Path
import logging

from src.core.serialization import utc_now_iso
from src.core.settings import load_settings, to_repo_relative
from src.schemas.inference import InferenceLatestResponse
from src.services.inference_history_service import build_predicted_for_timestamp, save_latest_inference_snapshot
from src.services.model_runtime_service import (
    InferenceNotReadyError,
    load_model,
    load_scaler_stats,
    prepare_latest_input,
    resolve_model_path,
    resolve_scaler_stats_path,
    run_inference,
)
from src.services.risk_service import evaluate_and_save_latest_risk
from src.services.signal_service import save_signal_from_inference
from src.services.strategy_service import evaluate_and_save_latest_strategy


logger = logging.getLogger(__name__)


def _to_relative_or_absolute(path: Path | None) -> str | None:
    if path is None:
        return None
    return to_repo_relative(path)


def _not_ready_response(
    *,
    status: str,
    message: str,
    model_type: str | None = None,
    runtime: str | None = None,
    model_version: str | None = None,
    model_path: Path | None = None,
    scaler_stats_path: Path | None = None,
    input_layout: str | None = None,
    decision_threshold: float | None = None,
    source_timestamp: str | None = None,
    predicted_for_timestamp: str | None = None,
    window_size: int | None = None,
    feature_count: int | None = None,
) -> InferenceLatestResponse:
    return InferenceLatestResponse(
        configured=False,
        status=status,
        message=message,
        model_type=model_type,
        runtime=runtime,
        model_version=model_version,
        model_path=_to_relative_or_absolute(model_path),
        scaler_stats_path=_to_relative_or_absolute(scaler_stats_path),
        input_layout=input_layout,
        decision_threshold=decision_threshold,
        prediction_class=None,
        probability_up=None,
        source_timestamp=source_timestamp,
        predicted_for_timestamp=predicted_for_timestamp,
        window_size=window_size,
        feature_count=feature_count,
        timestamp_utc=utc_now_iso(),
    )


def get_latest_inference() -> InferenceLatestResponse:
    settings = load_settings()
    model_path = resolve_model_path(settings)
    scaler_stats_path = resolve_scaler_stats_path(settings)

    try:
        scaler_stats = load_scaler_stats(settings)
    except InferenceNotReadyError as exc:
        return _not_ready_response(
            status="scaler_not_ready",
            message=str(exc),
            model_type=settings.inference_model_type,
            model_path=model_path,
            scaler_stats_path=scaler_stats_path,
            input_layout=settings.inference_input_layout,
            decision_threshold=settings.inference_probability_threshold,
            window_size=settings.inference_window_size,
        )

    try:
        prepared_input = prepare_latest_input(scaler_stats, settings)
    except InferenceNotReadyError as exc:
        return _not_ready_response(
            status="input_not_ready",
            message=str(exc),
            model_type=settings.inference_model_type,
            model_path=model_path,
            scaler_stats_path=scaler_stats_path,
            input_layout=settings.inference_input_layout,
            decision_threshold=settings.inference_probability_threshold,
            window_size=settings.inference_window_size,
            feature_count=len(scaler_stats.feature_names),
        )

    try:
        loaded_model = load_model(settings)
    except InferenceNotReadyError as exc:
        return _not_ready_response(
            status="model_not_ready",
            message=str(exc),
            model_type=settings.inference_model_type,
            model_path=model_path,
            scaler_stats_path=scaler_stats.source_path,
            input_layout=settings.inference_input_layout,
            decision_threshold=settings.inference_probability_threshold,
            source_timestamp=prepared_input.source_timestamp,
            predicted_for_timestamp=(
                build_predicted_for_timestamp(prepared_input.source_timestamp, settings.timeframe)
                if prepared_input.source_timestamp is not None
                else None
            ),
            window_size=prepared_input.window_size,
            feature_count=prepared_input.feature_count,
        )

    try:
        prediction_class, probability_up = run_inference(loaded_model, prepared_input, settings)
    except InferenceNotReadyError as exc:
        return _not_ready_response(
            status="inference_failed",
            message=str(exc),
            model_type=loaded_model.model_type,
            runtime=loaded_model.runtime,
            model_version=loaded_model.model_version,
            model_path=loaded_model.source_path,
            scaler_stats_path=scaler_stats.source_path,
            input_layout=settings.inference_input_layout,
            decision_threshold=settings.inference_probability_threshold,
            source_timestamp=prepared_input.source_timestamp,
            predicted_for_timestamp=(
                build_predicted_for_timestamp(prepared_input.source_timestamp, settings.timeframe)
                if prepared_input.source_timestamp is not None
                else None
            ),
            window_size=prepared_input.window_size,
            feature_count=prepared_input.feature_count,
        )

    predicted_for_timestamp: str | None = None
    if prepared_input.source_timestamp is not None:
        try:
            predicted_for_timestamp = build_predicted_for_timestamp(
                prepared_input.source_timestamp,
                settings.timeframe,
            )
        except Exception as exc:
            logger.warning("Failed to compute predicted_for_timestamp: %s", exc)

    response = InferenceLatestResponse(
        configured=True,
        status="ok",
        message="Live inference completed successfully",
        model_type=loaded_model.model_type,
        runtime=loaded_model.runtime,
        model_version=loaded_model.model_version,
        model_path=_to_relative_or_absolute(loaded_model.source_path),
        scaler_stats_path=_to_relative_or_absolute(scaler_stats.source_path),
        input_layout=settings.inference_input_layout,
        decision_threshold=settings.inference_probability_threshold,
        prediction_class=prediction_class,
        probability_up=probability_up,
        source_timestamp=prepared_input.source_timestamp,
        predicted_for_timestamp=predicted_for_timestamp,
        window_size=prepared_input.window_size,
        feature_count=prepared_input.feature_count,
        timestamp_utc=utc_now_iso(),
    )

    try:
        save_latest_inference_snapshot(response, settings)
    except Exception as exc:
        logger.warning("Failed to persist inference snapshot: %s", exc)

    try:
        save_signal_from_inference(response, settings)
    except Exception as exc:
        logger.warning("Failed to persist signal snapshot: %s", exc)

    try:
        evaluate_and_save_latest_strategy(settings)
    except Exception as exc:
        logger.warning("Failed to persist strategy decision: %s", exc)

    try:
        evaluate_and_save_latest_risk(settings)
    except Exception as exc:
        logger.warning("Failed to persist risk decision: %s", exc)

    return response
