from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from src.schemas.signals import SignalHistoryResponse, SignalLatestResponse
from src.services.signal_service import get_latest_signal, get_signal_history


router = APIRouter(tags=["signals"])


@router.get("/signals/latest", response_model=SignalLatestResponse)
def signals_latest() -> SignalLatestResponse:
    try:
        return get_latest_signal()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load latest signal: {exc}",
        ) from exc


@router.get("/signals/history", response_model=SignalHistoryResponse)
def signals_history(
    limit: int = Query(default=200, ge=1, le=2000),
    start: str | None = None,
    end: str | None = None,
) -> SignalHistoryResponse:
    try:
        return get_signal_history(limit=limit, start=start, end=end)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load signal history: {exc}",
        ) from exc
