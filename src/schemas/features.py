from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class FeaturesLatestResponse(BaseModel):
    symbol: str
    timeframe: str
    source_path: str
    latest_timestamp: str | None
    snapshot: dict[str, Any]
