from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from src.schemas.reconciliation import ReconciliationHistoryResponse, ReconciliationLatestResponse, ReconciliationResultRecord
from src.services.reconciliation_service import (
    get_latest_reconciliation,
    get_reconciliation_history_response,
    run_reconciliation_check,
)


router = APIRouter(tags=['reconciliation'])


@router.get('/reconciliation/latest', response_model=ReconciliationLatestResponse)
def reconciliation_latest() -> ReconciliationLatestResponse:
    try:
        return get_latest_reconciliation()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f'Failed to load latest reconciliation result: {exc}') from exc


@router.get('/reconciliation/history', response_model=ReconciliationHistoryResponse)
def reconciliation_history(limit: int = Query(default=200, ge=1, le=2000)) -> ReconciliationHistoryResponse:
    try:
        return get_reconciliation_history_response(limit=limit)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f'Failed to load reconciliation history: {exc}') from exc


@router.post('/reconciliation/run-now', response_model=ReconciliationResultRecord)
def reconciliation_run_now() -> ReconciliationResultRecord:
    try:
        return run_reconciliation_check(source='manual')
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f'Failed to run reconciliation check: {exc}') from exc
