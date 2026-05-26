from __future__ import annotations

from src.core.settings import AppSettings
from src.schemas.execution import OpenPositionsResponse
from src.services.trade_service import get_open_positions_response, get_open_trade_records


def get_open_positions(settings: AppSettings | None = None) -> OpenPositionsResponse:
    return get_open_positions_response(settings)


def get_open_position_records(settings: AppSettings | None = None):
    return get_open_trade_records(settings)
