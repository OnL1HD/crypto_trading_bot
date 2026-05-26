from __future__ import annotations

from fastapi import APIRouter, HTTPException

from src.schemas.pipeline import PipelineStatusResponse
from src.services.pipeline_status_service import get_pipeline_status


router = APIRouter(prefix="/status", tags=["status"])


@router.get("/pipeline", response_model=PipelineStatusResponse)
def pipeline_status() -> PipelineStatusResponse:
    try:
        return get_pipeline_status()
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to inspect pipeline status: {exc}",
        ) from exc
