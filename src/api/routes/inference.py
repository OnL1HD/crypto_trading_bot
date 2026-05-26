from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from src.schemas.inference import InferenceHistoryResponse, InferenceLatestResponse
from src.services.inference_history_service import get_inference_history
from src.services.inference_service import get_latest_inference


router = APIRouter(tags=["inference"])


@router.get("/inference/latest", response_model=InferenceLatestResponse)
def inference_latest() -> InferenceLatestResponse:
    try:
        return get_latest_inference()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to run latest inference: {exc}",
        ) from exc


@router.get("/inference/history", response_model=InferenceHistoryResponse)
def inference_history(limit: int = Query(default=300, ge=1, le=2000)) -> InferenceHistoryResponse:
    try:
        return get_inference_history(limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load inference history: {exc}",
        ) from exc
