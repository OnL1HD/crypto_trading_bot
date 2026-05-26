from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from src.schemas.risk import RiskHistoryResponse, RiskLatestResponse
from src.services.risk_service import get_latest_risk, get_risk_history_response


router = APIRouter(tags=['risk'])


@router.get('/risk/latest', response_model=RiskLatestResponse)
def risk_latest() -> RiskLatestResponse:
    try:
        return get_latest_risk()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f'Failed to load latest risk decision: {exc}') from exc


@router.get('/risk/history', response_model=RiskHistoryResponse)
def risk_history(
    limit: int = Query(default=200, ge=1, le=2000),
    start: str | None = None,
    end: str | None = None,
) -> RiskHistoryResponse:
    try:
        return get_risk_history_response(limit=limit, start=start, end=end)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f'Failed to load risk history: {exc}') from exc
