from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from typing import cast
from uuid import uuid4

import pandas as pd

from src.core.serialization import utc_now_iso
from src.core.settings import AppSettings, ExecutionSettings, load_settings
from src.integrations.bybit_demo_client import BybitDemoClient, BybitDemoClientError
from src.schemas.execution import (
    ExecutionAttemptRecord,
    ExecutionRunResponse,
    ExecutionStatusResponse,
    TradeRecord,
)
from src.schemas.signals import SignalRecord
from src.services.execution_log_service import (
    append_execution_record,
    get_latest_execution_record,
    has_successful_execution_for_key,
    latest_successful_execution_at,
)
from src.services.risk_service import evaluate_and_save_latest_risk
from src.services.signal_service import get_latest_signal
from src.services.strategy_service import get_latest_strategy
from src.services.trade_service import append_trade, close_trade, get_open_trade_records


class ExecutionServiceError(RuntimeError):
    pass


@dataclass(frozen=True)
class PendingExecution:
    signal: SignalRecord
    execution_key: str
    direction: str
    side: str


def build_execution_key(signal: SignalRecord) -> str:
    version = signal.model_version or 'unknown_model'
    return f'{signal.predicted_for_timestamp}|{version}|{signal.signal_type}'


def _build_attempt_record(
    *,
    settings: AppSettings,
    execution_key: str,
    signal: SignalRecord,
    status: str,
    success: bool,
    side: str | None,
    position_direction: str | None,
    exchange_order_id: str | None = None,
    exchange_response_code: str | None = None,
    exchange_response_message: str | None = None,
    error_message: str | None = None,
    order_notional_usdt: float | None = None,
    leverage: int | None = None,
) -> ExecutionAttemptRecord:
    return ExecutionAttemptRecord(
        attempted_at=utc_now_iso(),
        execution_key=execution_key,
        signal_type=signal.signal_type,
        source_timestamp=signal.source_timestamp,
        predicted_for_timestamp=signal.predicted_for_timestamp,
        symbol=settings.execution.symbol,
        side=side,
        position_direction=position_direction,
        order_type=settings.execution.order_type,
        order_notional_usdt=float(order_notional_usdt or settings.execution.fixed_order_usdt),
        leverage=leverage or settings.execution.leverage,
        execution_mode='demo',
        success=success,
        status=status,
        exchange_order_id=exchange_order_id,
        exchange_response_code=exchange_response_code,
        exchange_response_message=exchange_response_message,
        error_message=error_message,
    )


def _persist_attempt(record: ExecutionAttemptRecord, settings: AppSettings) -> ExecutionAttemptRecord:
    return append_execution_record(record, settings)


def _signal_reference_time(signal: SignalRecord) -> pd.Timestamp | None:
    for candidate in (signal.generated_at, signal.predicted_for_timestamp, signal.source_timestamp):
        parsed = pd.to_datetime(candidate, utc=True, errors='coerce')
        if pd.isna(parsed):
            continue
        timestamp = cast(pd.Timestamp, pd.Timestamp(parsed))
        if pd.isna(timestamp):
            continue
        return timestamp
    return None


def _utc_now_timestamp() -> pd.Timestamp:
    return pd.Timestamp.now(tz='UTC')


def _validate_execution_settings(settings: AppSettings) -> None:
    execution = settings.execution
    if execution.mode != 'demo':
        raise ExecutionServiceError(f"Unsupported execution mode '{execution.mode}'. Demo mode only.")
    if execution.market_type != 'linear':
        raise ExecutionServiceError(
            f"Unsupported market_type '{execution.market_type}'. Only linear is supported in v1."
        )
    if execution.order_type != 'market':
        raise ExecutionServiceError(
            f"Unsupported order_type '{execution.order_type}'. Only market orders are supported in v1."
        )
    if not settings.bybit_use_demo_trading:
        raise ExecutionServiceError('BYBIT_USE_DEMO_TRADING must be true for demo execution.')
    if not settings.bybit_demo_api_key or not settings.bybit_demo_api_secret:
        raise ExecutionServiceError('Demo trading credentials are not configured in backend env.')


def _resolve_pending_execution_for_action(
    signal: SignalRecord,
    action: str,
    execution: ExecutionSettings,
) -> PendingExecution | None:
    if action == 'OPEN_LONG':
        if not execution.allow_long:
            return None
        return PendingExecution(signal=signal, execution_key=build_execution_key(signal), direction='LONG', side='Buy')
    if action == 'OPEN_SHORT':
        if not execution.allow_short:
            return None
        return PendingExecution(signal=signal, execution_key=build_execution_key(signal), direction='SHORT', side='Sell')
    return None


def _create_demo_client(settings: AppSettings) -> BybitDemoClient:
    return BybitDemoClient(
        api_key=settings.bybit_demo_api_key or '',
        api_secret=settings.bybit_demo_api_secret or '',
        base_url=settings.bybit_demo_base_url,
    )


def _determine_order_quantity(
    client: BybitDemoClient,
    settings: AppSettings,
    *,
    order_notional_usdt: float,
) -> tuple[Decimal, float]:
    ticker = client.get_ticker(category=settings.execution.market_type, symbol=settings.execution.symbol)
    constraints = client.get_instrument_constraints(
        category=settings.execution.market_type,
        symbol=settings.execution.symbol,
    )

    price_text = ticker.get('markPrice') or ticker.get('lastPrice') or ticker.get('indexPrice')
    if price_text is None:
        raise ExecutionServiceError('No usable market price was returned for order sizing.')
    price = float(cast(str, price_text))
    if price <= 0:
        raise ExecutionServiceError(f'Invalid market price returned for sizing: {price}')

    raw_qty = Decimal(str(order_notional_usdt)) / Decimal(str(price))
    quantity = client.quantize_quantity(raw_qty, constraints)
    if quantity <= 0:
        raise ExecutionServiceError(
            'Configured fixed_order_usdt is too small for the instrument minimum quantity constraints.'
        )
    return quantity, price


def _close_trade_position(
    trade: TradeRecord,
    *,
    client: BybitDemoClient,
    settings: AppSettings,
    signal: SignalRecord,
    execution_key: str,
) -> ExecutionAttemptRecord:
    close_side = 'Sell' if trade.direction == 'LONG' else 'Buy'
    ticker = client.get_ticker(category=settings.execution.market_type, symbol=settings.execution.symbol)
    price_text = ticker.get('markPrice') or ticker.get('lastPrice') or ticker.get('indexPrice')
    close_price = float(price_text) if price_text is not None else None

    result = client.create_market_order(
        category=settings.execution.market_type,
        symbol=settings.execution.symbol,
        side=close_side,
        qty=Decimal(str(trade.quantity)),
        reduce_only=True,
    )
    close_trade(
        trade.trade_id,
        exit_time=utc_now_iso(),
        exit_price=close_price,
        exit_order_id=result.order_id,
        source_exit_signal=execution_key,
        settings=settings,
    )
    return _persist_attempt(
        _build_attempt_record(
            settings=settings,
            execution_key=execution_key,
            signal=signal,
            status='closed',
            success=True,
            side=close_side,
            position_direction=trade.direction,
            exchange_order_id=result.order_id,
            exchange_response_code=result.ret_code,
            exchange_response_message=result.ret_msg,
        ),
        settings,
    )


def close_trade_by_id(
    trade_id: str,
    *,
    close_reason: str,
    settings: AppSettings | None = None,
) -> ExecutionAttemptRecord:
    resolved_settings = settings or load_settings()
    _validate_execution_settings(resolved_settings)
    open_trades = get_open_trade_records(resolved_settings)
    matching = [trade for trade in open_trades if trade.trade_id == trade_id]
    if not matching:
        raise ExecutionServiceError(f'Open trade not found for close: {trade_id}')

    trade = matching[-1]
    client = _create_demo_client(resolved_settings)
    close_side = 'Sell' if trade.direction == 'LONG' else 'Buy'
    ticker = client.get_ticker(category=resolved_settings.execution.market_type, symbol=resolved_settings.execution.symbol)
    price_text = ticker.get('markPrice') or ticker.get('lastPrice') or ticker.get('indexPrice')
    close_price = float(price_text) if price_text is not None else None
    result = client.create_market_order(
        category=resolved_settings.execution.market_type,
        symbol=resolved_settings.execution.symbol,
        side=close_side,
        qty=Decimal(str(trade.quantity)),
        reduce_only=True,
    )
    close_trade(
        trade.trade_id,
        exit_time=utc_now_iso(),
        exit_price=close_price,
        exit_order_id=result.order_id,
        source_exit_signal=close_reason,
        settings=resolved_settings,
    )
    return _persist_attempt(
        ExecutionAttemptRecord(
            attempted_at=utc_now_iso(),
            execution_key=f'{trade.trade_id}|{close_reason}',
            signal_type=f'CLOSE_{trade.direction}',
            source_timestamp=None,
            predicted_for_timestamp=None,
            symbol=resolved_settings.execution.symbol,
            side=close_side,
            position_direction=trade.direction,
            order_type=resolved_settings.execution.order_type,
            order_notional_usdt=float((trade.entry_price or 0.0) * trade.quantity),
            leverage=trade.leverage,
            execution_mode='demo',
            success=True,
            status='closed',
            exchange_order_id=result.order_id,
            exchange_response_code=result.ret_code,
            exchange_response_message=result.ret_msg,
            error_message=None,
        ),
        resolved_settings,
    )


def _open_trade_position(
    pending: PendingExecution,
    *,
    client: BybitDemoClient,
    settings: AppSettings,
    order_notional_usdt: float | None = None,
    leverage: int | None = None,
    stop_loss: float | None = None,
    take_profit: float | None = None,
) -> ExecutionAttemptRecord:
    approved_order_notional = order_notional_usdt or float(settings.execution.fixed_order_usdt)
    approved_leverage = leverage or settings.execution.leverage
    try:
        client.set_leverage(
            category=settings.execution.market_type,
            symbol=settings.execution.symbol,
            leverage=approved_leverage,
        )
    except BybitDemoClientError as exc:
        raise ExecutionServiceError(f'Failed to apply leverage: {exc}') from exc

    quantity, reference_price = _determine_order_quantity(
        client,
        settings,
        order_notional_usdt=approved_order_notional,
    )
    result = client.create_market_order(
        category=settings.execution.market_type,
        symbol=settings.execution.symbol,
        side=pending.side,
        qty=quantity,
        reduce_only=False,
    )
    append_trade(
        TradeRecord(
            trade_id=uuid4().hex,
            symbol=settings.execution.symbol,
            direction=pending.direction,
            entry_time=utc_now_iso(),
            entry_price=reference_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            entry_order_id=result.order_id,
            leverage=approved_leverage,
            quantity=float(quantity),
            status='OPEN',
            source_entry_signal=pending.execution_key,
            execution_mode='demo',
        ),
        settings,
    )
    return _persist_attempt(
        _build_attempt_record(
            settings=settings,
            execution_key=pending.execution_key,
            signal=pending.signal,
            status='placed',
            success=True,
            side=pending.side,
            position_direction=pending.direction,
            exchange_order_id=result.order_id,
            exchange_response_code=result.ret_code,
            exchange_response_message=result.ret_msg,
            order_notional_usdt=approved_order_notional,
            leverage=approved_leverage,
        ),
        settings,
    )


def get_execution_status(settings: AppSettings | None = None) -> ExecutionStatusResponse:
    resolved_settings = settings or load_settings()
    latest_execution = get_latest_execution_record(resolved_settings)
    open_positions_count = len(get_open_trade_records(resolved_settings))
    demo_api_configured = bool(
        resolved_settings.bybit_demo_api_key and resolved_settings.bybit_demo_api_secret
    )

    if not resolved_settings.execution.enabled:
        message = 'Execution is disabled by config.'
    elif not demo_api_configured:
        message = 'Execution is enabled, but demo API credentials are missing.'
    elif not resolved_settings.bybit_use_demo_trading:
        message = 'Execution is enabled, but BYBIT_USE_DEMO_TRADING is false.'
    else:
        message = 'Demo execution is configured for manual triggering.'

    return ExecutionStatusResponse(
        enabled=resolved_settings.execution.enabled,
        mode='demo',
        symbol=resolved_settings.execution.symbol,
        market_type=resolved_settings.execution.market_type,
        order_type=resolved_settings.execution.order_type,
        leverage=resolved_settings.execution.leverage,
        max_open_positions=resolved_settings.execution.max_open_positions,
        open_positions_count=open_positions_count,
        demo_api_configured=demo_api_configured,
        demo_trading_enabled=resolved_settings.bybit_use_demo_trading,
        dry_run_logging=resolved_settings.execution.dry_run_logging,
        latest_execution=latest_execution,
        message=message,
    )


def run_latest_signal_execution(settings: AppSettings | None = None) -> ExecutionRunResponse:
    resolved_settings = settings or load_settings()
    latest_signal_response = get_latest_signal(settings=resolved_settings)
    actions: list[ExecutionAttemptRecord] = []

    if not latest_signal_response.available or latest_signal_response.signal is None:
        return ExecutionRunResponse(
            triggered_at=utc_now_iso(),
            message='No latest signal is available for execution.',
            actions=actions,
        )

    signal = latest_signal_response.signal
    execution_key = build_execution_key(signal)

    latest_strategy_response = get_latest_strategy(settings=resolved_settings)
    if not latest_strategy_response.available or latest_strategy_response.decision is None:
        record = _persist_attempt(
            _build_attempt_record(
                settings=resolved_settings,
                execution_key=execution_key,
                signal=signal,
                status='rejected',
                success=False,
                side=None,
                position_direction=None,
                error_message='No latest strategy decision is available for execution.',
            ),
            resolved_settings,
        )
        actions.append(record)
        return ExecutionRunResponse(
            triggered_at=utc_now_iso(),
            signal_type=signal.signal_type,
            execution_key=execution_key,
            message='Execution requires a strategy decision first.',
            actions=actions,
        )

    latest_risk_decision = evaluate_and_save_latest_risk(settings=resolved_settings)
    if latest_risk_decision is None:
        record = _persist_attempt(
            _build_attempt_record(
                settings=resolved_settings,
                execution_key=execution_key,
                signal=signal,
                status='rejected',
                success=False,
                side=None,
                position_direction=None,
                error_message='No latest risk decision is available for execution.',
            ),
            resolved_settings,
        )
        actions.append(record)
        return ExecutionRunResponse(
            triggered_at=utc_now_iso(),
            signal_type=signal.signal_type,
            execution_key=execution_key,
            message='Execution requires a risk decision first.',
            actions=actions,
        )

    risk_decision = latest_risk_decision
    pending = _resolve_pending_execution_for_action(
        signal,
        risk_decision.approved_action,
        resolved_settings.execution,
    )

    if not risk_decision.allowed or pending is None:
        risk_message = ', '.join(risk_decision.reason_codes) if risk_decision.reason_codes else 'RISK_BLOCKED'
        record = _persist_attempt(
            _build_attempt_record(
                settings=resolved_settings,
                execution_key=execution_key,
                signal=signal,
                status='rejected',
                success=False,
                side=None,
                position_direction=None,
                error_message=f'Risk blocked execution: {risk_message}',
                order_notional_usdt=risk_decision.order_notional_usdt,
                leverage=risk_decision.approved_leverage,
            ),
            resolved_settings,
        )
        actions.append(record)
        return ExecutionRunResponse(
            triggered_at=utc_now_iso(),
            signal_type=signal.signal_type,
            execution_key=execution_key,
            message='Risk blocked execution for the latest strategy decision.',
            actions=actions,
        )

    if resolved_settings.execution.require_signal_freshness:
        reference_time = _signal_reference_time(signal)
        if reference_time is None:
            record = _persist_attempt(
                _build_attempt_record(
                    settings=resolved_settings,
                    execution_key=execution_key,
                    signal=signal,
                    status='rejected',
                    success=False,
                    side=pending.side,
                    position_direction=pending.direction,
                    error_message='Signal freshness could not be validated.',
                    order_notional_usdt=risk_decision.order_notional_usdt,
                    leverage=risk_decision.approved_leverage,
                ),
                resolved_settings,
            )
            actions.append(record)
            return ExecutionRunResponse(
                triggered_at=utc_now_iso(),
                signal_type=signal.signal_type,
                execution_key=execution_key,
                message='Signal freshness validation failed.',
                actions=actions,
            )

        max_age = timedelta(minutes=resolved_settings.execution.max_signal_age_minutes)
        if _utc_now_timestamp() - reference_time > max_age:
            record = _persist_attempt(
                _build_attempt_record(
                    settings=resolved_settings,
                    execution_key=execution_key,
                    signal=signal,
                    status='skipped',
                    success=False,
                    side=pending.side,
                    position_direction=pending.direction,
                    error_message='Signal is stale and exceeds max_signal_age_minutes.',
                    order_notional_usdt=risk_decision.order_notional_usdt,
                    leverage=risk_decision.approved_leverage,
                ),
                resolved_settings,
            )
            actions.append(record)
            return ExecutionRunResponse(
                triggered_at=utc_now_iso(),
                signal_type=signal.signal_type,
                execution_key=execution_key,
                message='Latest signal is stale and was not executed.',
                actions=actions,
            )

    if (
        resolved_settings.execution.prevent_duplicate_signal_execution
        and has_successful_execution_for_key(execution_key, resolved_settings)
    ):
        record = _persist_attempt(
            _build_attempt_record(
                settings=resolved_settings,
                execution_key=execution_key,
                signal=signal,
                status='skipped',
                success=False,
                side=pending.side,
                position_direction=pending.direction,
                error_message='Duplicate signal execution prevented by config.',
                order_notional_usdt=risk_decision.order_notional_usdt,
                leverage=risk_decision.approved_leverage,
            ),
            resolved_settings,
        )
        actions.append(record)
        return ExecutionRunResponse(
            triggered_at=utc_now_iso(),
            signal_type=signal.signal_type,
            execution_key=execution_key,
            message='Duplicate signal execution was skipped.',
            actions=actions,
        )

    latest_success = latest_successful_execution_at(resolved_settings)
    if latest_success is not None and resolved_settings.execution.cooldown_minutes > 0:
        cooldown = timedelta(minutes=resolved_settings.execution.cooldown_minutes)
        now_utc = _utc_now_timestamp()
        if now_utc - latest_success < cooldown:
            record = _persist_attempt(
                _build_attempt_record(
                    settings=resolved_settings,
                    execution_key=execution_key,
                    signal=signal,
                    status='skipped',
                    success=False,
                    side=pending.side,
                    position_direction=pending.direction,
                    error_message='Cooldown window is active.',
                    order_notional_usdt=risk_decision.order_notional_usdt,
                    leverage=risk_decision.approved_leverage,
                ),
                resolved_settings,
            )
            actions.append(record)
            return ExecutionRunResponse(
                triggered_at=utc_now_iso(),
                signal_type=signal.signal_type,
                execution_key=execution_key,
                message='Cooldown prevented execution.',
                actions=actions,
            )

    if not resolved_settings.execution.enabled:
        record = _persist_attempt(
            _build_attempt_record(
                settings=resolved_settings,
                execution_key=execution_key,
                signal=signal,
                status='disabled',
                success=False,
                side=pending.side,
                position_direction=pending.direction,
                error_message='Execution is disabled by config.',
                order_notional_usdt=risk_decision.order_notional_usdt,
                leverage=risk_decision.approved_leverage,
            ),
            resolved_settings,
        )
        actions.append(record)
        return ExecutionRunResponse(
            triggered_at=utc_now_iso(),
            signal_type=signal.signal_type,
            execution_key=execution_key,
            message='Execution is disabled. No exchange order was sent.',
            actions=actions,
        )

    try:
        _validate_execution_settings(resolved_settings)
        client = _create_demo_client(resolved_settings)
        open_trades = get_open_trade_records(resolved_settings)

        opposite_direction = 'SHORT' if pending.direction == 'LONG' else 'LONG'
        opposite_trades = [trade for trade in open_trades if trade.direction == opposite_direction]
        if resolved_settings.execution.close_opposite_before_flip and opposite_trades:
            for trade in opposite_trades:
                actions.append(
                    _close_trade_position(
                        trade,
                        client=client,
                        settings=resolved_settings,
                        signal=signal,
                        execution_key=execution_key,
                    )
                )

        open_trades = get_open_trade_records(resolved_settings)
        if len(open_trades) >= resolved_settings.execution.max_open_positions:
            record = _persist_attempt(
                _build_attempt_record(
                    settings=resolved_settings,
                    execution_key=execution_key,
                    signal=signal,
                    status='rejected',
                    success=False,
                    side=pending.side,
                    position_direction=pending.direction,
                    error_message='max_open_positions limit reached.',
                    order_notional_usdt=risk_decision.order_notional_usdt,
                    leverage=risk_decision.approved_leverage,
                ),
                resolved_settings,
            )
            actions.append(record)
            return ExecutionRunResponse(
                triggered_at=utc_now_iso(),
                signal_type=signal.signal_type,
                execution_key=execution_key,
                message='Open-position limit prevented a new order.',
                actions=actions,
            )

        actions.append(
            _open_trade_position(
                pending,
                client=client,
                settings=resolved_settings,
                order_notional_usdt=risk_decision.order_notional_usdt,
                leverage=risk_decision.approved_leverage,
                stop_loss=risk_decision.stop_loss,
                take_profit=risk_decision.take_profit,
            )
        )
        return ExecutionRunResponse(
            triggered_at=utc_now_iso(),
            signal_type=signal.signal_type,
            execution_key=execution_key,
            message='Latest signal execution completed.',
            actions=actions,
        )
    except (ExecutionServiceError, BybitDemoClientError) as exc:
        record = _persist_attempt(
            _build_attempt_record(
                settings=resolved_settings,
                execution_key=execution_key,
                signal=signal,
                status='failed',
                success=False,
                side=pending.side,
                position_direction=pending.direction,
                error_message=str(exc),
                order_notional_usdt=risk_decision.order_notional_usdt,
                leverage=risk_decision.approved_leverage,
            ),
            resolved_settings,
        )
        actions.append(record)
        return ExecutionRunResponse(
            triggered_at=utc_now_iso(),
            signal_type=signal.signal_type,
            execution_key=execution_key,
            message='Execution failed before completing all actions.',
            actions=actions,
        )
