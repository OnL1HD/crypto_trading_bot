from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from src.schemas.automation import (
    AutomationCycleRecord,
    AutomationHistoryResponse,
    AutomationLatestCycleResponse,
    AutomationStatusResponse,
)
from src.services.automation_service import (
    get_automation_history_response,
    get_automation_status,
    get_latest_automation_cycle_response,
    run_automation_cycle_now,
)


router = APIRouter(tags=['automation'])


@router.get('/automation/status', response_model=AutomationStatusResponse)
def automation_status() -> AutomationStatusResponse:
    try:
        return get_automation_status()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f'Failed to load automation status: {exc}') from exc


@router.get('/automation/latest-cycle', response_model=AutomationLatestCycleResponse)
def automation_latest_cycle() -> AutomationLatestCycleResponse:
    try:
        return get_latest_automation_cycle_response()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f'Failed to load latest automation cycle: {exc}') from exc


@router.get('/automation/history', response_model=AutomationHistoryResponse)
def automation_history(limit: int = Query(default=200, ge=1, le=2000)) -> AutomationHistoryResponse:
    try:
        return get_automation_history_response(limit=limit)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f'Failed to load automation history: {exc}') from exc


@router.post('/automation/run-now', response_model=AutomationCycleRecord)
async def automation_run_now() -> AutomationCycleRecord:
    try:
        return await run_automation_cycle_now()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f'Failed to run automation cycle: {exc}') from exc
