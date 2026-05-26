from __future__ import annotations

from pydantic import BaseModel


class InferenceLatestResponse(BaseModel):
    configured: bool
    status: str
    message: str
    model_type: str | None = None
    runtime: str | None = None
    model_version: str | None = None
    model_path: str | None = None
    scaler_stats_path: str | None = None
    input_layout: str | None = None
    decision_threshold: float | None = None
    prediction_class: int | None = None
    probability_up: float | None = None
    source_timestamp: str | None = None
    predicted_for_timestamp: str | None = None
    window_size: int | None = None
    feature_count: int | None = None
    timestamp_utc: str


class InferenceHistoryPoint(BaseModel):
    predicted_for_timestamp: str
    source_timestamp: str
    prediction_class: int
    probability_up: float
    decision_threshold: float
    model_version: str | None = None
    inferred_at: str


class InferenceHistoryResponse(BaseModel):
    symbol: str
    timeframe: str
    source_path: str
    count: int
    predictions: list[InferenceHistoryPoint]
