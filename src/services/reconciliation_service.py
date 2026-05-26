from __future__ import annotations

from dataclasses import dataclass

from src.core.serialization import utc_now_iso
from src.core.settings import AppSettings, load_settings
from src.integrations.bybit_demo_client import BybitDemoClient, BybitDemoClientError
from src.schemas.reconciliation import (
    ReconciliationHistoryResponse,
    ReconciliationLatestResponse,
    ReconciliationResultRecord,
    ReconciliationSource,
)
from src.services.reconciliation_log_service import (
    append_reconciliation_result,
    get_latest_reconciliation_record,
    get_reconciliation_history,
)
from src.services.trade_service import get_open_trade_records


@dataclass(frozen=True)
class ExchangePositionSnapshot:
    symbol: str
    side: str
    size: float


def _create_demo_client(settings: AppSettings) -> BybitDemoClient:
    return BybitDemoClient(
        api_key=settings.bybit_demo_api_key or '',
        api_secret=settings.bybit_demo_api_secret or '',
        base_url=settings.bybit_demo_base_url,
    )


def _fetch_exchange_positions(settings: AppSettings) -> list[ExchangePositionSnapshot]:
    client = _create_demo_client(settings)
    raw_positions = client.get_positions(
        category=settings.execution.market_type,
        settle_coin='USDT',
    )
    positions: list[ExchangePositionSnapshot] = []
    for item in raw_positions:
        symbol = str(item.get('symbol') or '')
        side = str(item.get('side') or '')
        size_raw = item.get('size')
        try:
            size = float(size_raw)
        except (TypeError, ValueError):
            size = 0.0
        if symbol == '' or side == '' or size <= 0:
            continue
        positions.append(ExchangePositionSnapshot(symbol=symbol, side=side, size=size))
    return positions


def _side_matches(local_direction: str, exchange_side: str) -> bool:
    return (local_direction == 'LONG' and exchange_side.lower() == 'buy') or (
        local_direction == 'SHORT' and exchange_side.lower() == 'sell'
    )


def _size_mismatch(local_qty: float, exchange_qty: float, tolerance_ratio: float, tolerance_min_qty: float) -> bool:
    diff = abs(local_qty - exchange_qty)
    tolerance = max(abs(local_qty) * tolerance_ratio, tolerance_min_qty)
    return diff > tolerance


def run_reconciliation_check(
    *,
    source: ReconciliationSource = 'manual',
    settings: AppSettings | None = None,
) -> ReconciliationResultRecord:
    resolved_settings = settings or load_settings()
    local_open_trades = get_open_trade_records(resolved_settings)
    local_trades_for_symbol = [trade for trade in local_open_trades if trade.symbol == resolved_settings.execution.symbol]

    reason_codes: list[str] = []
    details: list[str] = []
    block_new_execution = False

    try:
        exchange_positions = _fetch_exchange_positions(resolved_settings)
    except (BybitDemoClientError, RuntimeError) as exc:
        reason_codes.append('EXCHANGE_STATE_UNAVAILABLE')
        details.append(str(exc))
        record = ReconciliationResultRecord(
            checked_at=utc_now_iso(),
            status='blocked',
            local_open_count=len(local_trades_for_symbol),
            exchange_open_count=0,
            matched=False,
            mismatch_count=1,
            reason_codes=reason_codes,
            details=details,
            block_new_execution=True,
            source=source,
        )
        return append_reconciliation_result(record, resolved_settings)

    exchange_for_symbol = [position for position in exchange_positions if position.symbol == resolved_settings.execution.symbol]
    exchange_out_of_scope = [position for position in exchange_positions if position.symbol != resolved_settings.execution.symbol]

    if local_trades_for_symbol and not exchange_for_symbol:
        reason_codes.append('LOCAL_OPEN_EXCHANGE_FLAT')
        details.append('Local state has open trades but exchange is flat for the managed symbol.')

    if not local_trades_for_symbol and exchange_for_symbol:
        reason_codes.append('LOCAL_FLAT_EXCHANGE_OPEN')
        details.append('Exchange has an open managed-symbol position but local state is flat.')

    if exchange_out_of_scope:
        reason_codes.append('SYMBOL_SCOPE_MISMATCH')
        details.append('Exchange has open positions outside the managed symbol scope.')

    if len(local_trades_for_symbol) == 1 and len(exchange_for_symbol) == 1:
        local_trade = local_trades_for_symbol[0]
        exchange_position = exchange_for_symbol[0]
        if not _side_matches(local_trade.direction, exchange_position.side):
            reason_codes.append('DIRECTION_MISMATCH')
            details.append('Local/open direction does not match exchange position side.')
        if _size_mismatch(
            local_trade.quantity,
            exchange_position.size,
            resolved_settings.reconciliation.size_tolerance_ratio,
            resolved_settings.reconciliation.size_tolerance_min_qty,
        ):
            reason_codes.append('SIZE_MISMATCH')
            details.append('Local/open quantity differs materially from exchange position size.')
    elif len(local_trades_for_symbol) != len(exchange_for_symbol):
        if len(local_trades_for_symbol) > 1 or len(exchange_for_symbol) > 1:
            reason_codes.append('POSITION_COUNT_MISMATCH')
            details.append('Local and exchange open position counts differ for the managed symbol.')

    mismatch_count = len(reason_codes)
    matched = mismatch_count == 0
    if matched:
        status = 'ok'
    else:
        status = 'blocked' if resolved_settings.reconciliation.block_on_mismatch else 'mismatch'
    if not matched and resolved_settings.reconciliation.block_on_mismatch:
        block_new_execution = True

    record = ReconciliationResultRecord(
        checked_at=utc_now_iso(),
        status=status,
        local_open_count=len(local_trades_for_symbol),
        exchange_open_count=len(exchange_for_symbol),
        matched=matched,
        mismatch_count=mismatch_count,
        reason_codes=reason_codes,
        details=details,
        block_new_execution=block_new_execution,
        source=source,
    )
    return append_reconciliation_result(record, resolved_settings)


def get_latest_reconciliation(settings: AppSettings | None = None) -> ReconciliationLatestResponse:
    resolved_settings = settings or load_settings()
    latest = get_latest_reconciliation_record(resolved_settings)
    if latest is None:
        return ReconciliationLatestResponse(
            symbol=resolved_settings.symbol,
            timeframe=resolved_settings.timeframe,
            available=False,
            message='No reconciliation result has been recorded yet',
            result=None,
        )
    return ReconciliationLatestResponse(
        symbol=resolved_settings.symbol,
        timeframe=resolved_settings.timeframe,
        available=True,
        message='Latest reconciliation result loaded',
        result=latest,
    )


def get_reconciliation_history_response(
    limit: int = 200,
    settings: AppSettings | None = None,
) -> ReconciliationHistoryResponse:
    return get_reconciliation_history(limit=limit, settings=settings)
