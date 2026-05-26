from __future__ import annotations

from dataclasses import dataclass
from typing import cast

import pandas as pd

from src.core.serialization import utc_now_iso
from src.core.settings import AppSettings, StrategySettings, load_settings
from src.schemas.strategy import (
    ConfidenceBucket,
    ContextLabel,
    StrategyAction,
    StrategyDecisionRecord,
    StrategyHistoryResponse,
    StrategyLatestResponse,
    StrategySupportingContext,
)
from src.services.features_service import get_latest_feature_snapshot
from src.services.inference_history_service import get_inference_history
from src.services.signal_service import get_latest_signal, get_signal_history
from src.services.strategy_log_service import (
    append_strategy_record,
    get_latest_strategy_record,
    get_strategy_history,
)
from src.services.trade_service import get_open_trade_records


FEATURE_KEYS = {
    'ema_20_dist',
    'ema_50_dist',
    'ema_20_50_spread',
    'atr_14_pct',
    'rolling_vol_12',
    'rolling_vol_48',
    'rsi_14',
    'macd_hist',
    'log_return_1',
    'log_return_4',
    'volume_change_1',
    'volume_ma_ratio_20',
    'turnover_ma_ratio_20',
}


@dataclass(frozen=True)
class PositionSummary:
    has_open_long: bool
    has_open_short: bool


@dataclass(frozen=True)
class StrategyInputs:
    signal_probability_up: float
    prediction_class: int
    signal_type: str
    source_timestamp: str
    predicted_for_timestamp: str
    model_version: str | None
    feature_values: dict[str, float | None]
    position_summary: PositionSummary
    consecutive_same_signal_count: int
    previous_non_hold_signal: str | None


def _coerce_feature_value(snapshot: object) -> float | None:
    if snapshot is None:
        return None
    try:
        parsed = float(cast(float | int | str, snapshot))
    except (TypeError, ValueError):
        return None
    if pd.isna(parsed):
        return None
    return parsed


def _confidence_bucket(probability_up: float, strategy: StrategySettings) -> ConfidenceBucket:
    if probability_up >= strategy.strong_buy_threshold:
        return 'STRONG_BULLISH'
    if probability_up >= strategy.entry_long_threshold:
        return 'MEDIUM_BULLISH'
    if probability_up >= strategy.buy_signal_threshold:
        return 'WEAK_BULLISH'
    if probability_up <= strategy.strong_sell_threshold:
        return 'STRONG_BEARISH'
    if probability_up <= strategy.entry_short_threshold:
        return 'MEDIUM_BEARISH'
    if probability_up <= strategy.sell_signal_threshold:
        return 'WEAK_BEARISH'
    return 'NEUTRAL'


def _build_feature_values(settings: AppSettings) -> tuple[dict[str, float | None], bool]:
    response = get_latest_feature_snapshot()
    snapshot = response.snapshot or {}
    feature_values = {key: _coerce_feature_value(snapshot.get(key)) for key in FEATURE_KEYS}
    feature_snapshot_available = any(value is not None for value in feature_values.values())
    return feature_values, feature_snapshot_available


def _build_position_summary(settings: AppSettings) -> PositionSummary:
    open_trades = get_open_trade_records(settings)
    return PositionSummary(
        has_open_long=any(trade.direction == 'LONG' for trade in open_trades),
        has_open_short=any(trade.direction == 'SHORT' for trade in open_trades),
    )


def _consecutive_same_signal_count(settings: AppSettings, signal_type: str) -> tuple[int, str | None]:
    history = get_signal_history(limit=max(8, settings.strategy.min_signal_persistence_bars + 4), settings=settings)
    signals = history.signals
    if not signals:
        return 0, None

    consecutive = 0
    previous_non_hold_signal: str | None = None
    for signal in reversed(signals):
        if signal.signal_type == signal_type:
            consecutive += 1
            continue
        if signal.signal_type != 'HOLD':
            previous_non_hold_signal = signal.signal_type
        break

    if previous_non_hold_signal is None:
        for signal in reversed(signals[:-consecutive or None]):
            if signal.signal_type != 'HOLD':
                previous_non_hold_signal = signal.signal_type
                break

    return consecutive, previous_non_hold_signal


def _trend_context(feature_values: dict[str, float | None]) -> ContextLabel:
    ema_20_dist = feature_values['ema_20_dist']
    ema_50_dist = feature_values['ema_50_dist']
    spread = feature_values['ema_20_50_spread']
    if ema_20_dist is None or ema_50_dist is None or spread is None:
        return 'missing'
    if ema_20_dist > 0 and ema_50_dist > 0 and spread > 0:
        return 'supportive'
    if ema_20_dist < 0 and ema_50_dist < 0 and spread < 0:
        return 'adverse'
    return 'neutral'


def _trend_alignment(signal_type: str, trend_context: ContextLabel) -> tuple[bool, bool]:
    if signal_type == 'BUY':
        return trend_context == 'supportive', trend_context == 'adverse'
    if signal_type == 'SELL':
        return trend_context == 'adverse', trend_context == 'supportive'
    return False, False


def _volatility_context(feature_values: dict[str, float | None], strategy: StrategySettings) -> ContextLabel:
    atr_14_pct = feature_values['atr_14_pct']
    rolling_vol_12 = feature_values['rolling_vol_12']
    rolling_vol_48 = feature_values['rolling_vol_48']
    if atr_14_pct is None and rolling_vol_12 is None and rolling_vol_48 is None:
        return 'missing'
    if atr_14_pct is not None and atr_14_pct < strategy.min_atr_14_pct:
        return 'adverse'
    if rolling_vol_12 is not None and rolling_vol_48 is not None and rolling_vol_48 > 0:
        if rolling_vol_12 < rolling_vol_48 * 0.55:
            return 'adverse'
    return 'supportive'


def _volume_context(feature_values: dict[str, float | None], strategy: StrategySettings) -> ContextLabel:
    volume_ratio = feature_values['volume_ma_ratio_20']
    turnover_ratio = feature_values['turnover_ma_ratio_20']
    if volume_ratio is None and turnover_ratio is None:
        return 'missing'
    if volume_ratio is None or turnover_ratio is None:
        return 'neutral'
    if volume_ratio >= strategy.min_volume_ma_ratio_20 and turnover_ratio >= strategy.min_turnover_ma_ratio_20:
        return 'supportive'
    return 'adverse'


def _momentum_context(signal_type: str, feature_values: dict[str, float | None]) -> ContextLabel:
    rsi_14 = feature_values['rsi_14']
    macd_hist = feature_values['macd_hist']
    log_return_1 = feature_values['log_return_1']
    log_return_4 = feature_values['log_return_4']
    if rsi_14 is None and macd_hist is None and log_return_1 is None and log_return_4 is None:
        return 'missing'
    if None in {rsi_14, macd_hist, log_return_1, log_return_4}:
        return 'neutral'

    if signal_type == 'BUY':
        bullish = cast(float, macd_hist) > 0 and cast(float, rsi_14) >= 52 and cast(float, log_return_4) >= -0.004
        bearish = cast(float, macd_hist) < 0 and cast(float, rsi_14) < 48 and cast(float, log_return_4) < 0
        if bullish:
            return 'supportive'
        if bearish:
            return 'adverse'
        return 'neutral'

    if signal_type == 'SELL':
        bearish = cast(float, macd_hist) < 0 and cast(float, rsi_14) <= 48 and cast(float, log_return_4) <= 0.004
        bullish = cast(float, macd_hist) > 0 and cast(float, rsi_14) > 52 and cast(float, log_return_4) > 0
        if bearish:
            return 'supportive'
        if bullish:
            return 'adverse'
        return 'neutral'

    return 'neutral'


def _build_strategy_inputs(settings: AppSettings) -> StrategyInputs | None:
    latest_signal_response = get_latest_signal(settings=settings)
    if not latest_signal_response.available or latest_signal_response.signal is None:
        return None

    latest_signal = latest_signal_response.signal
    inference_history = get_inference_history(limit=1, settings=settings)
    prediction_class = latest_signal.prediction_class
    if inference_history.predictions:
        latest_prediction = inference_history.predictions[-1]
        if latest_prediction.predicted_for_timestamp == latest_signal.predicted_for_timestamp:
            prediction_class = latest_prediction.prediction_class

    feature_values, _ = _build_feature_values(settings)
    consecutive_same_signal_count, previous_non_hold_signal = _consecutive_same_signal_count(
        settings,
        latest_signal.signal_type,
    )

    return StrategyInputs(
        signal_probability_up=latest_signal.probability_up,
        prediction_class=prediction_class,
        signal_type=latest_signal.signal_type,
        source_timestamp=latest_signal.source_timestamp,
        predicted_for_timestamp=latest_signal.predicted_for_timestamp,
        model_version=latest_signal.model_version,
        feature_values=feature_values,
        position_summary=_build_position_summary(settings),
        consecutive_same_signal_count=consecutive_same_signal_count,
        previous_non_hold_signal=previous_non_hold_signal,
    )


def _decision_from_inputs(inputs: StrategyInputs, settings: AppSettings) -> StrategyDecisionRecord:
    strategy = settings.strategy
    trend_context = _trend_context(inputs.feature_values)
    trend_aligned, counter_trend_signal = _trend_alignment(inputs.signal_type, trend_context)
    volatility_context = _volatility_context(inputs.feature_values, strategy)
    volume_context = _volume_context(inputs.feature_values, strategy)
    momentum_context = _momentum_context(inputs.signal_type, inputs.feature_values)
    confidence_bucket = _confidence_bucket(inputs.signal_probability_up, strategy)
    feature_snapshot_available = any(value is not None for value in inputs.feature_values.values())
    volatility_suitable = volatility_context != 'adverse'
    volume_supported = volume_context == 'supportive'
    momentum_supported = momentum_context != 'adverse'
    is_strong_signal = confidence_bucket in {'STRONG_BULLISH', 'STRONG_BEARISH'}
    is_medium_signal = confidence_bucket in {'MEDIUM_BULLISH', 'MEDIUM_BEARISH'}
    signal_persistent = inputs.consecutive_same_signal_count >= strategy.min_signal_persistence_bars
    flip_noise_blocked = False

    action: StrategyAction = 'HOLD'
    action_reason = 'strategy_hold_no_tradeable_signal'

    if inputs.signal_type == 'HOLD' or confidence_bucket == 'NEUTRAL':
        action = 'HOLD'
        action_reason = 'base_signal_hold'
    elif inputs.signal_type == 'BUY' and inputs.position_summary.has_open_long:
        action = 'HOLD'
        action_reason = 'long_position_already_open'
    elif inputs.signal_type == 'SELL' and inputs.position_summary.has_open_short:
        action = 'HOLD'
        action_reason = 'short_position_already_open'
    elif inputs.signal_type == 'BUY' and inputs.position_summary.has_open_short:
        action = 'SKIP'
        action_reason = 'opposite_short_position_open'
    elif inputs.signal_type == 'SELL' and inputs.position_summary.has_open_long:
        action = 'SKIP'
        action_reason = 'opposite_long_position_open'
    else:
        if inputs.signal_type == 'BUY' and inputs.signal_probability_up < strategy.entry_long_threshold:
            action = 'SKIP'
            action_reason = 'buy_signal_below_entry_threshold'
        elif inputs.signal_type == 'SELL' and inputs.signal_probability_up > strategy.entry_short_threshold:
            action = 'SKIP'
            action_reason = 'sell_signal_below_entry_threshold'
        elif strategy.flip_noise_guard_enabled and inputs.previous_non_hold_signal is not None:
            if (
                inputs.previous_non_hold_signal != inputs.signal_type
                and not is_strong_signal
                and inputs.consecutive_same_signal_count <= strategy.min_signal_persistence_bars
            ):
                action = 'SKIP'
                action_reason = 'flip_noise_guard_blocked'
                flip_noise_blocked = True
        elif not signal_persistent:
            action = 'SKIP'
            action_reason = 'signal_not_persistent'
        elif strategy.use_trend_filter and counter_trend_signal:
            if is_strong_signal and strategy.allow_counter_trend_on_strong_signal:
                action_reason = 'strong_counter_trend_signal_allowed'
            else:
                action = 'SKIP'
                action_reason = 'counter_trend_signal_blocked'
        elif (
            strategy.use_trend_filter
            and strategy.require_trend_alignment_for_weak_signals
            and not trend_aligned
            and not is_strong_signal
        ):
            action = 'SKIP'
            action_reason = 'trend_alignment_required'
        elif strategy.use_volatility_filter and not volatility_suitable and not is_strong_signal:
            action = 'SKIP'
            action_reason = 'volatility_filter_blocked'
        elif strategy.use_volume_filter and not volume_supported and not is_strong_signal:
            action = 'SKIP'
            action_reason = 'volume_filter_blocked'
        elif strategy.use_momentum_filter and momentum_context == 'adverse' and not is_strong_signal:
            action = 'SKIP'
            action_reason = 'momentum_filter_blocked'
        else:
            if inputs.signal_type == 'BUY':
                action = 'OPEN_LONG'
                action_reason = 'long_entry_approved'
            elif inputs.signal_type == 'SELL':
                action = 'OPEN_SHORT'
                action_reason = 'short_entry_approved'

            if action in {'OPEN_LONG', 'OPEN_SHORT'} and is_strong_signal:
                action_reason = f'{action_reason}_strong_confidence'
            elif action in {'OPEN_LONG', 'OPEN_SHORT'} and is_medium_signal:
                action_reason = f'{action_reason}_context_confirmed'

    return StrategyDecisionRecord(
        decided_at=utc_now_iso(),
        source_timestamp=inputs.source_timestamp,
        predicted_for_timestamp=inputs.predicted_for_timestamp,
        probability_up=inputs.signal_probability_up,
        prediction_class=inputs.prediction_class,
        signal_type=cast(object, inputs.signal_type),
        confidence_bucket=confidence_bucket,
        trend_context=trend_context,
        volatility_context=volatility_context,
        volume_context=volume_context,
        momentum_context=momentum_context,
        action=action,
        action_reason=action_reason,
        supporting_context=StrategySupportingContext(
            feature_snapshot_available=feature_snapshot_available,
            trend_aligned=trend_aligned,
            volatility_suitable=volatility_suitable,
            volume_supported=volume_supported,
            momentum_supported=momentum_supported,
            signal_persistent=signal_persistent,
            flip_noise_blocked=flip_noise_blocked,
            has_open_long=inputs.position_summary.has_open_long,
            has_open_short=inputs.position_summary.has_open_short,
            counter_trend_signal=counter_trend_signal,
        ),
        strategy_version=strategy.version,
        model_version=inputs.model_version,
    )


def evaluate_latest_strategy(settings: AppSettings | None = None) -> StrategyDecisionRecord | None:
    resolved_settings = settings or load_settings()
    inputs = _build_strategy_inputs(resolved_settings)
    if inputs is None:
        return None
    return _decision_from_inputs(inputs, resolved_settings)


def evaluate_and_save_latest_strategy(settings: AppSettings | None = None) -> StrategyDecisionRecord | None:
    resolved_settings = settings or load_settings()
    decision = evaluate_latest_strategy(resolved_settings)
    if decision is None:
        return None
    return append_strategy_record(decision, resolved_settings)


def get_latest_strategy(settings: AppSettings | None = None) -> StrategyLatestResponse:
    resolved_settings = settings or load_settings()
    latest_record = get_latest_strategy_record(resolved_settings)
    if latest_record is not None:
        return StrategyLatestResponse(
            symbol=resolved_settings.symbol,
            timeframe=resolved_settings.timeframe,
            available=True,
            message='Latest strategy decision loaded',
            decision=latest_record,
        )

    evaluated = evaluate_and_save_latest_strategy(resolved_settings)
    if evaluated is None:
        return StrategyLatestResponse(
            symbol=resolved_settings.symbol,
            timeframe=resolved_settings.timeframe,
            available=False,
            message='No strategy decision is available yet',
            decision=None,
        )

    return StrategyLatestResponse(
        symbol=resolved_settings.symbol,
        timeframe=resolved_settings.timeframe,
        available=True,
        message='Strategy decision evaluated from latest stored signal',
        decision=evaluated,
    )


def get_strategy_history_response(
    limit: int = 200,
    start: str | None = None,
    end: str | None = None,
    settings: AppSettings | None = None,
) -> StrategyHistoryResponse:
    return get_strategy_history(limit=limit, start=start, end=end, settings=settings)
