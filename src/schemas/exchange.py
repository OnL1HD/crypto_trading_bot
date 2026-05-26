from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


AccountCheckStatus = Literal["not_run", "ok", "failed"]


class ExchangeStatusResponse(BaseModel):
    exchange: str
    private_api_present: bool
    private_api_ready_flag: bool
    private_api_configured: bool
    testnet_enabled: bool
    execution_enabled: bool
    paper_trading_ready: bool
    account_check_supported: bool
    account_check_status: AccountCheckStatus
    account_check_message: str
    message: str
