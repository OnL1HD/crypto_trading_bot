from __future__ import annotations

from src.core.settings import load_settings
from src.integrations.bybit_private_client import BybitPrivateClient
from src.schemas.exchange import AccountCheckStatus, ExchangeStatusResponse


def _missing_private_env_names(api_key: str | None, api_secret: str | None) -> list[str]:
    missing: list[str] = []
    if api_key is None:
        missing.append("BYBIT_API_KEY")
    if api_secret is None:
        missing.append("BYBIT_API_SECRET")
    return missing


def get_exchange_status() -> ExchangeStatusResponse:
    settings = load_settings()

    missing_env_names = _missing_private_env_names(settings.bybit_api_key, settings.bybit_api_secret)
    private_api_present = len(missing_env_names) == 0
    private_api_ready_flag = settings.bybit_private_api_ready
    private_api_configured = private_api_present
    testnet_enabled = settings.bybit_use_testnet
    execution_enabled = False
    account_check_supported = private_api_present

    account_check_status: AccountCheckStatus = "not_run"
    account_check_message = "Account check not run"

    if not private_api_present:
        account_check_message = "Missing env values: " + ", ".join(missing_env_names)
    elif not private_api_ready_flag:
        account_check_message = "Private API ready flag is false (BYBIT_PRIVATE_API_READY)"
    else:
        client = BybitPrivateClient(
            api_key=settings.bybit_api_key or "",
            api_secret=settings.bybit_api_secret or "",
            use_testnet=testnet_enabled,
        )
        account_ok, account_message = client.check_account_access()
        account_check_status = "ok" if account_ok else "failed"
        account_check_message = account_message

    paper_trading_ready = (
        private_api_configured
        and private_api_ready_flag
        and not execution_enabled
        and account_check_status != "failed"
    )

    if not private_api_configured:
        message = "Bybit private API not configured: missing key/secret"
    elif not private_api_ready_flag:
        message = "Bybit private API configured but ready flag is false"
    elif account_check_status == "failed":
        message = "Bybit private API configured, but account readiness check failed"
    elif paper_trading_ready:
        message = "Bybit private API is ready for future paper trading (execution disabled)"
    else:
        message = "Bybit private API status available"

    return ExchangeStatusResponse(
        exchange=settings.exchange,
        private_api_present=private_api_present,
        private_api_ready_flag=private_api_ready_flag,
        private_api_configured=private_api_configured,
        testnet_enabled=testnet_enabled,
        execution_enabled=execution_enabled,
        paper_trading_ready=paper_trading_ready,
        account_check_supported=account_check_supported,
        account_check_status=account_check_status,
        account_check_message=account_check_message,
        message=message,
    )
