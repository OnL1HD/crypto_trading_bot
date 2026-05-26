from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


ReconciliationStatus = Literal['ok', 'warning', 'mismatch', 'blocked']
ReconciliationSource = Literal['startup', 'post_cycle', 'manual', 'pre_execution', 'post_execution']


class ReconciliationResultRecord(BaseModel):
    checked_at: str
    status: ReconciliationStatus
    local_open_count: int
    exchange_open_count: int
    matched: bool
    mismatch_count: int
    reason_codes: list[str]
    details: list[str]
    block_new_execution: bool
    source: ReconciliationSource


class ReconciliationLatestResponse(BaseModel):
    symbol: str
    timeframe: str
    available: bool
    message: str
    result: ReconciliationResultRecord | None = None


class ReconciliationHistoryResponse(BaseModel):
    symbol: str
    timeframe: str
    source_path: str
    count: int
    results: list[ReconciliationResultRecord]
