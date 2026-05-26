from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

import pandas as pd

from src.core.serialization import utc_now_iso
from src.core.settings import AppSettings, PositionManagementSettings, load_settings
from src.schemas.execution import TradeRecord
from src.schemas.position_manager import (
    PositionManagementDecisionRecord,
    PositionManagementHistoryResponse,
    PositionManagementLatestResponse,
)
from src.schemas.strategy import StrategyDecisionRecord
from src.services.execution_service import close_trade_by_id
from src.services.market_service import get_latest_market_candle
from src.services.position_manager_log_service import (
    append_position_management_record,
    get_latest_position_management_record,
    get_position_management_history,
)
from src.services.strategy_service import get_latest_strategy
from src.services.trade_service import get_open_trade_records


def _safe_timestamp(value: str | None) -> pd.Timestamp | None:
    if value is None:
        return None
    parsed = pd.to_datetime(value, utc=True, errors='coerce')
    if pd.isna(parsed):
        return None
    return pd.Timestamp(parsed)


def _current_price(settings: AppSettings) -> float | None:
    candle = get_latest_market_candle().candle
    value = candle.get('close') if candle is not None else None
    numeric = pd.to_numeric(value, errors='coerce')
    if pd.isna(numeric):
        return None
    return float(numeric)


def _holding_minutes(trade: TradeRecord) -> float:
    entry_time = _safe_timestamp(trade.entry_time)
    if entry_time is None:
        return 0.0
    elapsed = pd.Timestamp.now(tz='UTC') - entry_time
    return max(0.0, elapsed.total_seconds() / 60.0)


def _strategy_context_summary(strategy: StrategyDecisionRecord | None) -> str | None:
    if strategy is None:
        return None
    return f'{strategy.signal_type} | {strategy.action} | {strategy.confidence_bucket}'


def _opposite_signal_exit(
    trade: TradeRecord,
    strategy: StrategyDecisionRecord | None,
    settings: PositionManagementSettings,
) -> tuple[bool, str]:
    if not settings.enable_opposite_signal_exit or strategy is None:
        return False, 'position_hold'

    if trade.direction == 'LONG' and strategy.signal_type == 'SELL':
        if settings.require_strong_opposite_signal_for_exit:
            if strategy.probability_up > settings.opposite_signal_confidence_threshold_long_exit:
                return False, 'position_hold'
        return True, 'opposite_strategy_signal_exit'

    if trade.direction == 'SHORT' and strategy.signal_type == 'BUY':
        if settings.require_strong_opposite_signal_for_exit:
            if strategy.probability_up < settings.opposite_signal_confidence_threshold_short_exit:
                return False, 'position_hold'
        return True, 'opposite_strategy_signal_exit'

    return False, 'position_hold'


def _evaluate_trade(
    trade: TradeRecord,
    *,
    current_price: float | None,
    strategy: StrategyDecisionRecord | None,
    settings: AppSettings,
    allow_close_execution: bool,
    close_execution_block_reason: str | None,
) -> PositionManagementDecisionRecord:
    manager = settings.position_management
    holding_minutes = _holding_minutes(trade)
    exit_action = 'HOLD_POSITION'
    exit_reason = 'position_hold'

    if current_price is None:
        exit_action = 'SKIP_POSITION'
        exit_reason = 'current_price_unavailable'
    elif manager.enable_stop_loss_exit and trade.stop_loss is not None:
        if trade.direction == 'LONG' and current_price <= trade.stop_loss:
            exit_action = 'CLOSE_LONG'
            exit_reason = 'stop_loss_exit'
        elif trade.direction == 'SHORT' and current_price >= trade.stop_loss:
            exit_action = 'CLOSE_SHORT'
            exit_reason = 'stop_loss_exit'

    if exit_action == 'HOLD_POSITION' and current_price is not None and manager.enable_take_profit_exit and trade.take_profit is not None:
        if trade.direction == 'LONG' and current_price >= trade.take_profit:
            exit_action = 'CLOSE_LONG'
            exit_reason = 'take_profit_exit'
        elif trade.direction == 'SHORT' and current_price <= trade.take_profit:
            exit_action = 'CLOSE_SHORT'
            exit_reason = 'take_profit_exit'

    if exit_action == 'HOLD_POSITION' and manager.enable_max_holding_exit:
        if holding_minutes >= manager.max_holding_minutes:
            exit_action = 'CLOSE_LONG' if trade.direction == 'LONG' else 'CLOSE_SHORT'
            exit_reason = 'max_holding_time_exit'

    if exit_action == 'HOLD_POSITION':
        opposite_exit, opposite_reason = _opposite_signal_exit(trade, strategy, manager)
        if opposite_exit:
            exit_action = 'CLOSE_LONG' if trade.direction == 'LONG' else 'CLOSE_SHORT'
            exit_reason = opposite_reason

    close_requested = exit_action in {'CLOSE_LONG', 'CLOSE_SHORT'}
    should_execute_close = close_requested
    executed_close = False
    execution_skipped_reason: str | None = None

    if close_requested and not allow_close_execution:
        execution_skipped_reason = close_execution_block_reason or 'POSITION_CLOSE_SKIPPED'

    if close_requested and allow_close_execution:
        close_trade_by_id(
            trade.trade_id,
            close_reason=f'position_manager:{exit_reason}',
            settings=settings,
        )
        executed_close = True

    return PositionManagementDecisionRecord(
        decision_id=uuid4().hex,
        decided_at=utc_now_iso(),
        trade_id=trade.trade_id,
        symbol=trade.symbol,
        direction=trade.direction,
        position_status=trade.status,
        current_price=current_price,
        entry_price=trade.entry_price,
        stop_loss=trade.stop_loss,
        take_profit=trade.take_profit,
        holding_minutes=holding_minutes,
        exit_action=exit_action,
        exit_reason=exit_reason,
        should_execute_close=should_execute_close,
        executed_close=executed_close,
        execution_skipped_reason=execution_skipped_reason,
        strategy_context_summary=_strategy_context_summary(strategy),
        source_timestamp=None if strategy is None else strategy.source_timestamp,
        strategy_version=None if strategy is None else strategy.strategy_version,
        position_management_version=manager.version,
    )


def evaluate_open_positions(
    *,
    settings: AppSettings | None = None,
    allow_close_execution: bool = False,
    close_execution_block_reason: str | None = None,
) -> list[PositionManagementDecisionRecord]:
    resolved_settings = settings or load_settings()
    manager = resolved_settings.position_management
    if not manager.enabled or not manager.evaluate_each_cycle:
        return []

    open_trades = get_open_trade_records(resolved_settings)
    if not open_trades:
        return []

    strategy_response = get_latest_strategy(settings=resolved_settings)
    strategy = strategy_response.decision if strategy_response.available else None
    current_price = _current_price(resolved_settings)
    decisions: list[PositionManagementDecisionRecord] = []
    for trade in open_trades:
        decision = _evaluate_trade(
            trade,
            current_price=current_price,
            strategy=strategy,
            settings=resolved_settings,
            allow_close_execution=allow_close_execution and manager.close_positions_via_demo_execution,
            close_execution_block_reason=close_execution_block_reason,
        )
        decisions.append(append_position_management_record(decision, resolved_settings))
    return decisions


def get_latest_position_management(settings: AppSettings | None = None) -> PositionManagementLatestResponse:
    resolved_settings = settings or load_settings()
    decision = get_latest_position_management_record(resolved_settings)
    if decision is None:
        return PositionManagementLatestResponse(
            symbol=resolved_settings.symbol,
            timeframe=resolved_settings.timeframe,
            available=False,
            message='No position management decision has been recorded yet',
            decision=None,
        )
    return PositionManagementLatestResponse(
        symbol=resolved_settings.symbol,
        timeframe=resolved_settings.timeframe,
        available=True,
        message='Latest position management decision loaded',
        decision=decision,
    )


def get_position_management_history_response(
    limit: int = 200,
    settings: AppSettings | None = None,
) -> PositionManagementHistoryResponse:
    return get_position_management_history(limit=limit, settings=settings)
