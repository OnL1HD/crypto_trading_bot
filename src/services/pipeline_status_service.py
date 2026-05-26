from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.core.serialization import to_iso_timestamp, utc_now_iso
from src.core.settings import load_settings, to_repo_relative
from src.schemas.pipeline import ArtifactStatus, PipelineStatusResponse, StageStatus


def _resolve_existing_path(primary_path: Path, fallback_glob: str | None = None) -> Path:
    if primary_path.exists() or fallback_glob is None:
        return primary_path

    matches = sorted(
        primary_path.parent.glob(fallback_glob),
        key=lambda file_path: file_path.stat().st_mtime,
        reverse=True,
    )
    if matches:
        return matches[0]
    return primary_path


def _probe_parquet(name: str, path: Path, timestamp_column: str = "open_time") -> ArtifactStatus:
    status = ArtifactStatus(name=name, path=to_repo_relative(path), exists=path.exists())
    if not path.exists():
        return status

    try:
        df = pd.read_parquet(path)
        status.readable = True
        status.row_count = int(len(df))

        if timestamp_column in df.columns and not df.empty:
            timestamp_series = pd.to_datetime(df[timestamp_column], utc=True, errors="coerce").dropna()
            if not timestamp_series.empty:
                status.latest_timestamp = to_iso_timestamp(timestamp_series.max())
    except Exception as exc:
        status.readable = False
        status.error = f"{type(exc).__name__}: {exc}"

    return status


def _probe_npz(name: str, path: Path) -> ArtifactStatus:
    status = ArtifactStatus(name=name, path=to_repo_relative(path), exists=path.exists())
    if not path.exists():
        return status

    try:
        with np.load(path) as payload:
            status.readable = True

            if "y" in payload.files:
                status.row_count = int(payload["y"].shape[0])
            elif "X" in payload.files:
                status.row_count = int(payload["X"].shape[0])

            if "end_time" in payload.files and payload["end_time"].size > 0:
                status.latest_timestamp = to_iso_timestamp(payload["end_time"][-1])
    except Exception as exc:
        status.readable = False
        status.error = f"{type(exc).__name__}: {exc}"

    return status


def get_pipeline_status() -> PipelineStatusResponse:
    settings = load_settings()

    processed_path = settings.processed_dir / f"{settings.symbol}_{settings.timeframe}_clean.parquet"
    features_path = settings.features_dir / f"{settings.symbol}_{settings.timeframe}_features_v1.parquet"
    labeled_path = settings.labeled_dir / f"{settings.symbol}_{settings.timeframe}_labeled_v1.parquet"

    splits = {
        "train": settings.splits_dir / f"{settings.symbol}_{settings.timeframe}_train_v1.parquet",
        "val": settings.splits_dir / f"{settings.symbol}_{settings.timeframe}_val_v1.parquet",
        "test": settings.splits_dir / f"{settings.symbol}_{settings.timeframe}_test_v1.parquet",
    }

    windows = {
        "train": settings.windows_dir / f"{settings.symbol}_{settings.timeframe}_train_windows_v1.npz",
        "val": settings.windows_dir / f"{settings.symbol}_{settings.timeframe}_val_windows_v1.npz",
        "test": settings.windows_dir / f"{settings.symbol}_{settings.timeframe}_test_windows_v1.npz",
    }

    normalized = {
        "train": _resolve_existing_path(
            settings.normalized_dir / f"{settings.symbol}_{settings.timeframe}_train_windows_norm_v1.npz",
            f"{settings.symbol}_{settings.timeframe}_train_windows_norm_*.npz",
        ),
        "val": _resolve_existing_path(
            settings.normalized_dir / f"{settings.symbol}_{settings.timeframe}_val_windows_norm_v1.npz",
            f"{settings.symbol}_{settings.timeframe}_val_windows_norm_*.npz",
        ),
        "test": _resolve_existing_path(
            settings.normalized_dir / f"{settings.symbol}_{settings.timeframe}_test_windows_norm_v1.npz",
            f"{settings.symbol}_{settings.timeframe}_test_windows_norm_*.npz",
        ),
        "scaler_stats": _resolve_existing_path(
            settings.normalized_dir / f"{settings.symbol}_{settings.timeframe}_scaler_stats_v1.npz",
            f"{settings.symbol}_{settings.timeframe}_scaler_stats_*.npz",
        ),
    }

    stages = [
        StageStatus(stage="processed", artifacts=[_probe_parquet("processed", processed_path)]),
        StageStatus(stage="features", artifacts=[_probe_parquet("features", features_path)]),
        StageStatus(stage="labeled", artifacts=[_probe_parquet("labeled", labeled_path)]),
        StageStatus(
            stage="splits",
            artifacts=[
                _probe_parquet("split_train", splits["train"]),
                _probe_parquet("split_val", splits["val"]),
                _probe_parquet("split_test", splits["test"]),
            ],
        ),
        StageStatus(
            stage="windows",
            artifacts=[
                _probe_npz("windows_train", windows["train"]),
                _probe_npz("windows_val", windows["val"]),
                _probe_npz("windows_test", windows["test"]),
            ],
        ),
        StageStatus(
            stage="normalized",
            artifacts=[
                _probe_npz("normalized_train", normalized["train"]),
                _probe_npz("normalized_val", normalized["val"]),
                _probe_npz("normalized_test", normalized["test"]),
                _probe_npz("scaler_stats", normalized["scaler_stats"]),
            ],
        ),
    ]

    return PipelineStatusResponse(
        symbol=settings.symbol,
        timeframe=settings.timeframe,
        generated_at=utc_now_iso(),
        stages=stages,
    )
