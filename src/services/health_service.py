from __future__ import annotations

from src.core.serialization import utc_now_iso
from src.schemas.health import HealthResponse


def get_health_status() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service="crypto-trading-bot-api",
        version="0.1.0",
        timestamp_utc=utc_now_iso(),
    )
