from __future__ import annotations

from fastapi import APIRouter

from src.schemas.health import HealthResponse
from src.services.health_service import get_health_status


router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return get_health_status()
