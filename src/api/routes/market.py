from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from src.schemas.market import MarketCandlesResponse, MarketLatestResponse
from src.services.market_service import get_latest_market_candle, get_market_candles


router = APIRouter(tags=["market"])


@router.get("/market/latest", response_model=MarketLatestResponse)
def market_latest() -> MarketLatestResponse:
    try:
        return get_latest_market_candle()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load latest market candle: {exc}",
        ) from exc


@router.get("/market/candles", response_model=MarketCandlesResponse)
def market_candles(
    limit: int = Query(default=300, ge=1),
    start: str | None = None,
    end: str | None = None,
) -> MarketCandlesResponse:
    try:
        return get_market_candles(limit=limit, start=start, end=end)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load market candles: {exc}",
        ) from exc
