# Dynamic Risk Sizing and Leverage

## Purpose

This document describes the dynamic sizing model now used by the risk layer.

The goal is to make trades more expressive when the setup is stronger, while still keeping
the decision path inspectable and bounded by explicit limits.

The system now varies both:

- `order_notional_usdt`
- `approved_leverage`

instead of using a single fixed size and fixed leverage for every trade.

## Decision Flow

The current backend decision chain is:

- inference -> signal -> strategy -> risk -> execution

Relevant files:

- `src/services/inference_service.py`
- `src/services/signal_service.py`
- `src/services/strategy_service.py`
- `src/services/risk_service.py`
- `src/services/execution_service.py`

The risk layer is the component that now produces the final dynamic trade parameters.

## Inputs Used By Risk

The risk layer consumes the latest strategy decision plus execution/trade context.

Primary inputs:

- `probability_up`
- `signal_type`
- `action`
- `confidence_bucket`
- `trend_context`
- `volatility_context`
- `volume_context`
- `momentum_context`
- `supporting_context`

Additional context gathered in risk:

- current open trades
- trade history
- execution history
- latest signal close price
- latest `atr_14_pct`

## Dynamic Model Overview

The new model separates three concerns:

1. permission to trade
2. order notional sizing
3. leverage selection

This separation is intentional.

- Permission answers: should the bot trade at all?
- Notional answers: how large should the trade be?
- Leverage answers: how much margin efficiency is appropriate?

## 1. Permission Layer

Risk still performs the existing guard checks before approving execution.

Current checks include:

- executable strategy action only (`OPEN_LONG` / `OPEN_SHORT`)
- same-direction position already open
- max open positions
- max total open notional
- cooldown
- strategy freshness
- consecutive loss lock
- daily realized loss lock

If any of these fail:

- `allowed = False`
- `approved_action = 'SKIP'`

## 2. Conviction Score

Dynamic sizing is driven by a conviction score in the range `0.0` to `1.0`.

The conviction score is computed in `src/services/risk_service.py` from two parts:

- model score
- context score

Final formula:

```text
conviction_score = 0.65 * model_score + 0.35 * context_score
```

### Model score

For long entries:

- normalize `probability_up` between:
  - `strategy.entry_long_threshold`
  - `strategy.strong_buy_threshold`

For short entries:

- normalize the bearish strength between:
  - `strategy.entry_short_threshold`
  - `strategy.strong_sell_threshold`

This means stronger model confidence pushes conviction higher.

### Context score

Context score is built from strategy supporting flags:

- `trend_aligned` -> `+1.0`
- `volume_supported` -> `+1.0`
- `momentum_supported` -> `+1.0`
- `volatility_suitable` -> `+1.0`
- `signal_persistent` -> `+0.5`

Then divided by `4.5` to normalize into `0.0` to `1.0`.

This means good contextual confirmation can increase size even when the raw model score is not maximal.

## 3. Stop-Distance-Aware Notional

The risk layer does not size BTC quantity directly.

Instead it computes:

- a dynamic `risk_budget_usdt`
- a stop-distance-aware `order_notional_usdt`

Execution later converts notional into BTC quantity using live price.

### Risk budget

Risk budget is interpolated from conviction:

```text
risk_budget_usdt = min_risk_budget_usdt
                 + conviction_score * (max_risk_budget_usdt - min_risk_budget_usdt)
```

Configured in `config/settings.yaml` under `risk:`.

### Stop distance

The stop distance percent is derived from the same stop logic used for protective levels.

If `stop_loss_mode: atr` and `atr_14_pct` is available:

```text
stop_distance_pct = atr_14_pct * stop_loss_atr_multiple
```

Otherwise fallback:

```text
stop_distance_pct = fallback_stop_loss_pct
```

### Raw notional

Once stop distance exists:

```text
raw_notional = risk_budget_usdt / stop_distance_pct
```

This is the core of the system.

If the stop is tighter, the same risk budget can support a larger notional.
If the stop is wider, notional becomes smaller.

### Final approved notional

The raw notional is then clamped by:

- `risk.min_order_notional_usdt`
- `risk.max_order_notional_usdt`
- remaining capacity under `risk.max_total_open_notional_usdt`

If remaining capacity is too small, the trade is blocked by risk.

### Why this is correct

This is more logical than using confidence alone to size quantity because the size now reflects both:

- setup strength
- expected stop distance

That makes the trade notional more consistent with intended risk.

## 4. Dynamic Leverage

Leverage is chosen independently from notional.

This is important.

Notional determines directional exposure.
Leverage determines required margin and liquidation sensitivity.

### Base leverage from conviction

Base leverage is interpolated from conviction between:

- `risk.min_dynamic_leverage`
- `risk.max_dynamic_leverage`

Then additionally capped by:

- `risk.max_allowed_leverage`
- `execution.leverage`

### ATR penalty

Leverage is then penalized downward using ATR.

Current multipliers:

- low ATR -> `1.0`
- moderate ATR -> `0.75`
- high ATR -> `0.5`
- extreme ATR -> `0.3`

This means strong setups can still use larger leverage, but elevated volatility reduces that aggressively.

### Final approved leverage

```text
approved_leverage = round(base_leverage * volatility_penalty_multiplier)
```

then clamped to configured bounds.

## Execution Behavior

Execution already consumes the dynamic values from risk without needing a new execution architecture.

Relevant logic:

- risk writes `order_notional_usdt` and `approved_leverage`
- execution reads them
- execution calls `set_leverage(...)`
- execution converts notional to BTC quantity as:

```text
quantity = order_notional_usdt / current_market_price
```

then quantizes to Bybit instrument constraints.

Relevant code:

- `src/services/risk_service.py`
- `src/services/execution_service.py`
- `src/integrations/bybit_demo_client.py`

## New Risk Decision Fields

Risk records now persist additional inspection fields:

- `conviction_score`
- `risk_budget_usdt`
- `stop_distance_pct`
- `volatility_penalty_multiplier`
- `size_reason`
- `leverage_reason`

These exist so future debugging and tuning can explain why a given trade was large, small, or heavily capped.

## Current Config Fields

The dynamic model depends on these `risk:` settings:

- `max_open_positions`
- `max_total_open_notional_usdt`
- `fixed_order_usdt`
- `min_order_notional_usdt`
- `max_order_notional_usdt`
- `min_risk_budget_usdt`
- `max_risk_budget_usdt`
- `default_leverage`
- `max_allowed_leverage`
- `min_dynamic_leverage`
- `max_dynamic_leverage`
- `stop_loss_mode`
- `take_profit_mode`
- `stop_loss_atr_multiple`
- `take_profit_atr_multiple`
- `fallback_stop_loss_pct`
- `fallback_take_profit_pct`

And this `execution:` field also acts as a hard cap:

- `execution.leverage`

## Expected Behavior In Practice

### Weak setup

- low conviction score
- small risk budget
- small notional
- low leverage

### Strong setup with good context and acceptable ATR

- high conviction score
- larger risk budget
- larger notional
- higher leverage

### Strong setup with high ATR

- notional may still be meaningful
- leverage is reduced by ATR penalty

This is intentional.

## Known Caveats

### 1. Old risk history rows

Old parquet rows from before dynamic sizing may not deserialize into the richer schema.

New rows created after this change are the authoritative format.

### 2. Prediction horizon issue still matters

The known `predicted_for_timestamp` horizon mismatch should still be reviewed before trusting aggressive leverage behavior.

### 3. This is a v1 dynamic sizing model

The current formulas are explicit and inspectable, but they are still heuristic.

They will likely need tuning after observing:

- actual trade frequency
- realized PnL behavior
- average approved notional
- how often ATR suppresses leverage

## Recommended Future Improvements

Good next iterations:

- add frontend visibility for conviction and sizing reasons
- calibrate ATR penalty thresholds using recent live demo behavior
- size from account equity instead of fixed USDT risk-budget bounds
- include spread/slippage awareness in sizing
- add symbol-specific leverage caps if more instruments are added

## Summary

The dynamic risk model now works like this:

- strategy decides if a setup is tradeable
- risk calculates conviction from model confidence and context quality
- conviction sets risk budget
- stop distance converts risk budget into dynamic order notional
- ATR penalizes leverage when volatility is elevated
- execution uses the approved notional and leverage directly

This gives the bot dynamic trades instead of one-size-fits-all orders while keeping the logic readable and tunable.
