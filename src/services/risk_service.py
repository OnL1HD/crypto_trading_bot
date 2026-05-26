from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

import pandas as pd

from src.core.serialization import utc_now_iso
from src.core.settings import AppSettings, RiskSettings, load_settings
from src.schemas.execution import ExecutionAttemptRecord, TradeRecord
from src.schemas.risk import RiskDecisionRecord, RiskHistoryResponse, RiskLatestResponse
from src.schemas.strategy import StrategyDecisionRecord
from src.services.execution_log_service import get_execution_history
from src.services.features_service import get_latest_feature_snapshot
from src.services.risk_log_service import append_risk_record, get_latest_risk_record, get_risk_history
from src.services.signal_service import get_latest_signal
from src.services.strategy_service import get_latest_strategy
from src.services.trade_service import get_open_trade_records, get_trade_history


EXECUTABLE_ACTIONS = {'OPEN_LONG', 'OPEN_SHORT'}
APPROVAL_REASON = 'RISK_APPROVED'


@dataclass(frozen=True)
class RiskContext:
    strategy_decision: StrategyDecisionRecord
    open_trades: list[TradeRecord]
    trade_history: list[TradeRecord]
    execution_history: list[ExecutionAttemptRecord]
    reference_price: float | None
    atr_14_pct: float | None


def _safe_timestamp(value: str | None) -> pd.Timestamp | None:
    if value is None:
        return None
    parsed = pd.to_datetime(value, utc=True, errors='coerce')
    if pd.isna(parsed):
        return None
    return pd.Timestamp(parsed)


def _clamp_float(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(value, maximum))


def _clamp_int(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(value, maximum))


def _normalize(value: float, minimum: float, maximum: float) -> float:
    if maximum <= minimum:
        return 1.0 if value >= maximum else 0.0
    return _clamp_float((value - minimum) / (maximum - minimum), 0.0, 1.0)


def _build_context(settings: AppSettings, strategy_decision: StrategyDecisionRecord) -> RiskContext:
    latest_signal = get_latest_signal(settings=settings).signal
    reference_price = None
    if latest_signal is not None and latest_signal.predicted_for_timestamp == strategy_decision.predicted_for_timestamp:
        reference_price = latest_signal.close_price

    feature_snapshot = get_latest_feature_snapshot().snapshot
    atr_14_pct_raw = feature_snapshot.get('atr_14_pct') if feature_snapshot is not None else None
    try:
        atr_14_pct = None if atr_14_pct_raw is None else float(atr_14_pct_raw)
    except (TypeError, ValueError):
        atr_14_pct = None
    if atr_14_pct is not None and pd.isna(atr_14_pct):
        atr_14_pct = None

    return RiskContext(
        strategy_decision=strategy_decision,
        open_trades=get_open_trade_records(settings),
        trade_history=get_trade_history(limit=500, settings=settings).trades,
        execution_history=get_execution_history(limit=500, settings=settings).executions,
        reference_price=reference_price,
        atr_14_pct=atr_14_pct,
    )


def _current_open_notional(open_trades: list[TradeRecord]) -> float:
    total = 0.0
    for trade in open_trades:
        if trade.entry_price is None:
            continue
        total += float(trade.entry_price) * float(trade.quantity)
    return total


def _latest_entry_attempt_at(executions: list[ExecutionAttemptRecord]) -> pd.Timestamp | None:
    timestamps: list[pd.Timestamp] = []
    for record in executions:
        if not record.success or record.status != 'placed':
            continue
        attempted_at = _safe_timestamp(record.attempted_at)
        if attempted_at is not None:
            timestamps.append(attempted_at)
    if not timestamps:
        return None
    return max(timestamps)


def _count_consecutive_losses(trades: list[TradeRecord]) -> int:
    closed_trades = [trade for trade in trades if trade.status == 'CLOSED']
    ordered = sorted(
        closed_trades,
        key=lambda trade: trade.exit_time or trade.entry_time,
    )

    consecutive = 0
    for trade in reversed(ordered):
        pnl = trade.realized_pnl
        if pnl is None:
            break
        if pnl < 0:
            consecutive += 1
            continue
        break
    return consecutive


def _daily_realized_loss(trades: list[TradeRecord]) -> float:
    today = pd.Timestamp.now(tz='UTC').normalize()
    total_loss = 0.0
    for trade in trades:
        if trade.status != 'CLOSED' or trade.realized_pnl is None or trade.realized_pnl >= 0:
            continue
        exit_time = _safe_timestamp(trade.exit_time)
        if exit_time is None or exit_time.normalize() != today:
            continue
        total_loss += abs(float(trade.realized_pnl))
    return total_loss


def _compute_model_score(decision: StrategyDecisionRecord, settings: AppSettings) -> float:
    probability_up = float(decision.probability_up)
    strategy = settings.strategy
    if decision.action == 'OPEN_LONG':
        return _normalize(
            probability_up,
            strategy.entry_long_threshold,
            strategy.strong_buy_threshold,
        )
    if decision.action == 'OPEN_SHORT':
        return _normalize(
            strategy.entry_short_threshold - probability_up,
            0.0,
            strategy.entry_short_threshold - strategy.strong_sell_threshold,
        )
    return 0.0


def _compute_context_score(decision: StrategyDecisionRecord) -> float:
    context = decision.supporting_context
    score = 0.0
    if context.trend_aligned:
        score += 1.0
    if context.volume_supported:
        score += 1.0
    if context.momentum_supported:
        score += 1.0
    if context.volatility_suitable:
        score += 1.0
    if context.signal_persistent:
        score += 0.5
    return score / 4.5


def _compute_conviction_score(decision: StrategyDecisionRecord, settings: AppSettings) -> float:
    model_score = _compute_model_score(decision, settings)
    context_score = _compute_context_score(decision)
    conviction = 0.65 * model_score + 0.35 * context_score
    return _clamp_float(conviction, 0.0, 1.0)


def _resolve_stop_distance_pct(risk: RiskSettings, atr_14_pct: float | None) -> float | None:
    stop_pct = risk.fallback_stop_loss_pct
    if risk.stop_loss_mode == 'atr' and atr_14_pct is not None and atr_14_pct > 0:
        stop_pct = atr_14_pct * risk.stop_loss_atr_multiple
    if stop_pct <= 0:
        return None
    return stop_pct


def _resolve_take_profit_pct(risk: RiskSettings, atr_14_pct: float | None) -> float | None:
    take_pct = risk.fallback_take_profit_pct
    if risk.take_profit_mode == 'atr' and atr_14_pct is not None and atr_14_pct > 0:
        take_pct = atr_14_pct * risk.take_profit_atr_multiple
    if take_pct <= 0:
        return None
    return take_pct


def _compute_dynamic_risk_budget(conviction_score: float, risk: RiskSettings) -> float:
    return risk.min_risk_budget_usdt + conviction_score * (
        risk.max_risk_budget_usdt - risk.min_risk_budget_usdt
    )


def _compute_dynamic_order_notional(
    *,
    action: str,
    conviction_score: float,
    stop_distance_pct: float | None,
    current_open_notional: float,
    risk: RiskSettings,
) -> tuple[float, float, str]:
    risk_budget = _compute_dynamic_risk_budget(conviction_score, risk)
    if action not in EXECUTABLE_ACTIONS:
        return 0.0, risk_budget, 'non_executable_action'

    remaining_capacity = max(0.0, risk.max_total_open_notional_usdt - current_open_notional)
    if remaining_capacity < risk.min_order_notional_usdt:
        return 0.0, risk_budget, 'remaining_capacity_below_min_order_notional'

    if stop_distance_pct is None or stop_distance_pct <= 0:
        fallback_notional = _clamp_float(
            risk.fixed_order_usdt,
            risk.min_order_notional_usdt,
            min(risk.max_order_notional_usdt, remaining_capacity),
        )
        return fallback_notional, risk_budget, 'fallback_static_notional_missing_stop_distance'

    raw_notional = risk_budget / stop_distance_pct
    approved_notional = _clamp_float(
        raw_notional,
        risk.min_order_notional_usdt,
        min(risk.max_order_notional_usdt, remaining_capacity),
    )
    if approved_notional >= raw_notional:
        return approved_notional, risk_budget, 'conviction_and_stop_distance_sized'
    if remaining_capacity <= risk.max_order_notional_usdt:
        return approved_notional, risk_budget, 'capped_by_remaining_notional_capacity'
    return approved_notional, risk_budget, 'capped_by_max_order_notional'


def _compute_volatility_penalty_multiplier(
    atr_14_pct: float | None,
    settings: AppSettings,
) -> tuple[float, str]:
    baseline_atr = settings.strategy.min_atr_14_pct
    if atr_14_pct is None or atr_14_pct <= 0 or baseline_atr <= 0:
        return 0.75, 'atr_missing_conservative_penalty'

    atr_ratio = atr_14_pct / baseline_atr
    if atr_ratio <= 1.25:
        return 1.0, 'low_atr_full_leverage'
    if atr_ratio <= 2.0:
        return 0.75, 'moderate_atr_penalty'
    if atr_ratio <= 3.0:
        return 0.5, 'high_atr_penalty'
    return 0.3, 'extreme_atr_penalty'


def _compute_dynamic_leverage(
    *,
    action: str,
    conviction_score: float,
    atr_14_pct: float | None,
    settings: AppSettings,
) -> tuple[int, float | None, str]:
    risk = settings.risk
    leverage_cap = min(
        risk.max_dynamic_leverage,
        risk.max_allowed_leverage,
        settings.execution.leverage,
    )
    if action not in EXECUTABLE_ACTIONS:
        return risk.min_dynamic_leverage, None, 'non_executable_action'

    base_leverage = risk.min_dynamic_leverage + conviction_score * (
        leverage_cap - risk.min_dynamic_leverage
    )
    penalty_multiplier, penalty_reason = _compute_volatility_penalty_multiplier(atr_14_pct, settings)
    adjusted_leverage = int(round(base_leverage * penalty_multiplier))
    approved_leverage = _clamp_int(
        adjusted_leverage,
        risk.min_dynamic_leverage,
        leverage_cap,
    )
    return approved_leverage, penalty_multiplier, penalty_reason


def _compute_protective_levels(
    *,
    action: str,
    reference_price: float | None,
    atr_14_pct: float | None,
    risk: RiskSettings,
) -> tuple[float | None, float | None]:
    if action not in EXECUTABLE_ACTIONS or reference_price is None or reference_price <= 0:
        return None, None

    stop_pct = _resolve_stop_distance_pct(risk, atr_14_pct)
    take_pct = _resolve_take_profit_pct(risk, atr_14_pct)
    if stop_pct is None or take_pct is None:
        return None, None

    stop_distance = reference_price * stop_pct
    take_distance = reference_price * take_pct
    if action == 'OPEN_LONG':
        return reference_price - stop_distance, reference_price + take_distance
    return reference_price + stop_distance, reference_price - take_distance


def _evaluate_risk_context(context: RiskContext, settings: AppSettings) -> RiskDecisionRecord:
    decision = context.strategy_decision
    risk = settings.risk
    requested_action = decision.action
    approved_action = requested_action if requested_action in EXECUTABLE_ACTIONS else 'SKIP'
    reason_codes: list[str] = []
    conviction_score = _compute_conviction_score(decision, settings)
    current_open_notional = _current_open_notional(context.open_trades)
    stop_distance_pct = _resolve_stop_distance_pct(risk, context.atr_14_pct)
    order_notional_usdt, risk_budget_usdt, size_reason = _compute_dynamic_order_notional(
        action=requested_action,
        conviction_score=conviction_score,
        stop_distance_pct=stop_distance_pct,
        current_open_notional=current_open_notional,
        risk=risk,
    )
    approved_leverage, volatility_penalty_multiplier, leverage_reason = _compute_dynamic_leverage(
        action=requested_action,
        conviction_score=conviction_score,
        atr_14_pct=context.atr_14_pct,
        settings=settings,
    )

    if requested_action not in EXECUTABLE_ACTIONS:
        reason_codes.append('NON_EXECUTABLE_ACTION')

    if requested_action == 'OPEN_LONG' and any(trade.direction == 'LONG' for trade in context.open_trades):
        reason_codes.append('SAME_DIRECTION_POSITION_EXISTS')
    if requested_action == 'OPEN_SHORT' and any(trade.direction == 'SHORT' for trade in context.open_trades):
        reason_codes.append('SAME_DIRECTION_POSITION_EXISTS')

    if requested_action in EXECUTABLE_ACTIONS and len(context.open_trades) >= risk.max_open_positions:
        reason_codes.append('MAX_OPEN_POSITIONS_REACHED')

    if requested_action in EXECUTABLE_ACTIONS:
        if order_notional_usdt <= 0:
            reason_codes.append('INSUFFICIENT_NOTIONAL_CAPACITY')
        elif current_open_notional + order_notional_usdt > risk.max_total_open_notional_usdt:
            reason_codes.append('MAX_TOTAL_OPEN_NOTIONAL_EXCEEDED')

    if risk.enable_cooldown and risk.cooldown_minutes > 0 and requested_action in EXECUTABLE_ACTIONS:
        latest_entry_at = _latest_entry_attempt_at(context.execution_history)
        if latest_entry_at is not None:
            cooldown = timedelta(minutes=risk.cooldown_minutes)
            if pd.Timestamp.now(tz='UTC') - latest_entry_at < cooldown:
                reason_codes.append('COOLDOWN_ACTIVE')

    if risk.require_fresh_strategy:
        decided_at = _safe_timestamp(decision.decided_at)
        if decided_at is None:
            reason_codes.append('STALE_STRATEGY_DECISION')
        else:
            max_age = timedelta(minutes=risk.max_strategy_age_minutes)
            if pd.Timestamp.now(tz='UTC') - decided_at > max_age:
                reason_codes.append('STALE_STRATEGY_DECISION')

    if risk.enable_consecutive_loss_pause:
        consecutive_losses = _count_consecutive_losses(context.trade_history)
        if consecutive_losses >= risk.max_consecutive_losses:
            reason_codes.append('MAX_CONSECUTIVE_LOSSES_REACHED')

    if risk.enable_daily_loss_lock:
        daily_realized_loss = _daily_realized_loss(context.trade_history)
        if daily_realized_loss >= risk.max_daily_realized_loss_usdt:
            reason_codes.append('DAILY_LOSS_LOCK_ACTIVE')

    allowed = len(reason_codes) == 0
    if allowed:
        reason_codes.append(APPROVAL_REASON)
    else:
        approved_action = 'SKIP'

    stop_loss, take_profit = _compute_protective_levels(
        action=requested_action,
        reference_price=context.reference_price,
        atr_14_pct=context.atr_14_pct,
        risk=risk,
    )

    return RiskDecisionRecord(
        decided_at=utc_now_iso(),
        source_timestamp=decision.source_timestamp,
        predicted_for_timestamp=decision.predicted_for_timestamp,
        requested_action=requested_action,
        approved_action=approved_action,
        allowed=allowed,
        order_notional_usdt=order_notional_usdt,
        approved_leverage=approved_leverage,
        conviction_score=conviction_score,
        risk_budget_usdt=risk_budget_usdt,
        stop_distance_pct=stop_distance_pct,
        volatility_penalty_multiplier=volatility_penalty_multiplier,
        stop_loss=stop_loss,
        take_profit=take_profit,
        reason_codes=reason_codes,
        size_reason=size_reason,
        leverage_reason=leverage_reason,
        signal_type=decision.signal_type,
        probability_up=decision.probability_up,
        strategy_version=decision.strategy_version,
        risk_version=risk.version,
    )


def evaluate_latest_risk(settings: AppSettings | None = None) -> RiskDecisionRecord | None:
    resolved_settings = settings or load_settings()
    latest_strategy_response = get_latest_strategy(settings=resolved_settings)
    if not latest_strategy_response.available or latest_strategy_response.decision is None:
        return None

    context = _build_context(resolved_settings, latest_strategy_response.decision)
    return _evaluate_risk_context(context, resolved_settings)


def evaluate_and_save_latest_risk(settings: AppSettings | None = None) -> RiskDecisionRecord | None:
    resolved_settings = settings or load_settings()
    decision = evaluate_latest_risk(resolved_settings)
    if decision is None:
        return None
    return append_risk_record(decision, resolved_settings)


def get_latest_risk(settings: AppSettings | None = None) -> RiskLatestResponse:
    resolved_settings = settings or load_settings()
    latest_strategy_response = get_latest_strategy(settings=resolved_settings)
    if not latest_strategy_response.available or latest_strategy_response.decision is None:
        return RiskLatestResponse(
            symbol=resolved_settings.symbol,
            timeframe=resolved_settings.timeframe,
            available=False,
            message='No strategy decision is available for risk evaluation',
            decision=None,
        )

    latest_record = get_latest_risk_record(resolved_settings)
    strategy_decision = latest_strategy_response.decision
    if latest_record is not None:
        same_prediction = latest_record.predicted_for_timestamp == strategy_decision.predicted_for_timestamp
        same_strategy_version = latest_record.strategy_version == strategy_decision.strategy_version
        if same_prediction and same_strategy_version:
            return RiskLatestResponse(
                symbol=resolved_settings.symbol,
                timeframe=resolved_settings.timeframe,
                available=True,
                message='Latest risk decision loaded',
                decision=latest_record,
            )

    evaluated = evaluate_and_save_latest_risk(resolved_settings)
    if evaluated is None:
        return RiskLatestResponse(
            symbol=resolved_settings.symbol,
            timeframe=resolved_settings.timeframe,
            available=False,
            message='No risk decision is available yet',
            decision=None,
        )

    return RiskLatestResponse(
        symbol=resolved_settings.symbol,
        timeframe=resolved_settings.timeframe,
        available=True,
        message='Risk decision evaluated from latest strategy decision',
        decision=evaluated,
    )


def get_risk_history_response(
    limit: int = 200,
    start: str | None = None,
    end: str | None = None,
    settings: AppSettings | None = None,
) -> RiskHistoryResponse:
    return get_risk_history(limit=limit, start=start, end=end, settings=settings)
