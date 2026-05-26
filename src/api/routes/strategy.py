from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from src.schemas.strategy import StrategyHistoryResponse, StrategyLatestResponse
from src.services.strategy_service import get_latest_strategy, get_strategy_history_response


router = APIRouter(tags=['strategy'])


@router.get('/strategy/latest', response_model=StrategyLatestResponse)
def strategy_latest() -> StrategyLatestResponse:
    try:
        return get_latest_strategy()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f'Failed to load latest strategy decision: {exc}') from exc


@router.get('/strategy/history', response_model=StrategyHistoryResponse)
def strategy_history(
    limit: int = Query(default=200, ge=1, le=2000),
    start: str | None = None,
    end: str | None = None,
) -> StrategyHistoryResponse:
    try:
        return get_strategy_history_response(limit=limit, start=start, end=end)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f'Failed to load strategy history: {exc}') from exc
