from __future__ import annotations

from src.core.settings import load_settings, to_repo_relative
from src.schemas.features import FeaturesLatestResponse
from src.services.data_snapshot_service import latest_row_as_json


def get_latest_feature_snapshot() -> FeaturesLatestResponse:
    settings = load_settings()
    source_path = settings.features_dir / f"{settings.symbol}_{settings.timeframe}_features_v1.parquet"
    snapshot, latest_timestamp = latest_row_as_json(source_path)

    return FeaturesLatestResponse(
        symbol=settings.symbol,
        timeframe=settings.timeframe,
        source_path=to_repo_relative(source_path),
        latest_timestamp=latest_timestamp,
        snapshot=snapshot,
    )
