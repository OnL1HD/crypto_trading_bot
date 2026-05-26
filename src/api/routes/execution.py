from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from src.schemas.execution import (
    ExecutionHistoryResponse,
    ExecutionRunResponse,
    ExecutionStatusResponse,
    OpenPositionsResponse,
    TradeHistoryResponse,
)
from src.services.execution_log_service import get_execution_history
from src.services.execution_service import get_execution_status, run_latest_signal_execution
from src.services.position_service import get_open_positions
from src.services.trade_service import get_trade_history


router = APIRouter(tags=['execution'])


@router.get('/execution/status', response_model=ExecutionStatusResponse)
def execution_status() -> ExecutionStatusResponse:
    try:
        return get_execution_status()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f'Failed to load execution status: {exc}') from exc


@router.get('/execution/history', response_model=ExecutionHistoryResponse)
def execution_history(limit: int = Query(default=200, ge=1, le=2000)) -> ExecutionHistoryResponse:
    try:
        return get_execution_history(limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f'Failed to load execution history: {exc}') from exc


@router.get('/positions/open', response_model=OpenPositionsResponse)
def positions_open() -> OpenPositionsResponse:
    try:
        return get_open_positions()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f'Failed to load open positions: {exc}') from exc


@router.get('/trades/history', response_model=TradeHistoryResponse)
def trades_history(limit: int = Query(default=200, ge=1, le=2000)) -> TradeHistoryResponse:
    try:
        return get_trade_history(limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f'Failed to load trade history: {exc}') from exc


@router.post('/execution/run-latest-signal', response_model=ExecutionRunResponse)
def run_latest_signal() -> ExecutionRunResponse:
    try:
        return run_latest_signal_execution()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f'Failed to run latest signal execution: {exc}') from exc
