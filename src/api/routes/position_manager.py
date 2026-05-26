from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from src.schemas.position_manager import (
    PositionManagementHistoryResponse,
    PositionManagementLatestResponse,
)
from src.services.position_manager_service import (
    get_latest_position_management,
    get_position_management_history_response,
)


router = APIRouter(tags=['position-management'])


@router.get('/position-management/latest', response_model=PositionManagementLatestResponse)
def position_management_latest() -> PositionManagementLatestResponse:
    try:
        return get_latest_position_management()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f'Failed to load latest position management decision: {exc}') from exc


@router.get('/position-management/history', response_model=PositionManagementHistoryResponse)
def position_management_history(limit: int = Query(default=200, ge=1, le=2000)) -> PositionManagementHistoryResponse:
    try:
        return get_position_management_history_response(limit=limit)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f'Failed to load position management history: {exc}') from exc
