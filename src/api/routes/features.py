from __future__ import annotations

from fastapi import APIRouter, HTTPException

from src.schemas.features import FeaturesLatestResponse
from src.services.features_service import get_latest_feature_snapshot


router = APIRouter(tags=["features"])


@router.get("/features/latest", response_model=FeaturesLatestResponse)
def features_latest() -> FeaturesLatestResponse:
    try:
        return get_latest_feature_snapshot()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load latest feature snapshot: {exc}",
        ) from exc
