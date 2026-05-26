from __future__ import annotations

from fastapi import APIRouter, HTTPException

from src.schemas.exchange import ExchangeStatusResponse
from src.services.exchange_status_service import get_exchange_status


router = APIRouter(tags=["exchange"])


@router.get("/exchange/status", response_model=ExchangeStatusResponse)
def exchange_status() -> ExchangeStatusResponse:
    try:
        return get_exchange_status()
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to inspect exchange status: {exc}",
        ) from exc
