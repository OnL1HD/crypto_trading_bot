# BTCUSDT 15m Feature Specification v1

## Purpose
This document defines the first feature set used in the TCN-based BTCUSDT 15m forecasting pipeline. The goal is to provide a compact, causal, and reproducible feature baseline for experimentation.

## Input dataset
Features are generated from:

- `data/processed/BTCUSDT_15m_clean.parquet`

## Output dataset
Features are saved to:

- `data/features/BTCUSDT_15m_features_v1.parquet`

## Feature groups

### A. Price / return features
- `log_return_1`
  - Explanation: one-candle log return of closing price.
  - Formula: `log(close_t / close_{t-1})`.
  - Why included: captures immediate price movement with scale-friendly return math.
- `log_return_4`
  - Explanation: four-candle log return of closing price.
  - Formula: `log(close_t / close_{t-4})`.
  - Why included: captures short multi-candle momentum on 15m data.
- `close_to_open_return`
  - Explanation: intrabar return from open to close.
  - Formula: `(close_t / open_t) - 1`.
  - Why included: summarizes directional move inside each candle.
- `high_low_range_pct`
  - Explanation: intrabar high-low range as percentage.
  - Formula: `(high_t / low_t) - 1`.
  - Why included: captures candle amplitude and local volatility.

### B. Candle structure features
- `body_pct`
  - Explanation: candle body size relative to open.
  - Formula: `(close_t - open_t) / open_t`.
  - Why included: captures directional pressure of the candle body.
- `upper_wick_pct`
  - Explanation: upper wick size relative to open.
  - Formula: `(high_t - max(open_t, close_t)) / open_t`.
  - Why included: captures rejection from higher prices.
- `lower_wick_pct`
  - Explanation: lower wick size relative to open.
  - Formula: `(min(open_t, close_t) - low_t) / open_t`.
  - Why included: captures rejection from lower prices.
- `body_to_range_ratio`
  - Explanation: body size as a share of full candle range.
  - Formula: `abs(close_t - open_t) / (high_t - low_t)`.
  - Why included: separates decisive directional candles from noisy wide-range candles.

### C. Trend features
- `ema_20_dist`
  - Explanation: distance between close and 20-period EMA.
  - Formula: `(close_t / ema20_t) - 1`.
  - Why included: shows short-horizon trend extension or mean-reversion pressure.
- `ema_50_dist`
  - Explanation: distance between close and 50-period EMA.
  - Formula: `(close_t / ema50_t) - 1`.
  - Why included: adds medium-horizon trend context.
- `ema_20_50_spread`
  - Explanation: spread between short and medium EMAs.
  - Formula: `(ema20_t / ema50_t) - 1`.
  - Why included: captures trend alignment and slope regime.

### D. Momentum features
- `rsi_14`
  - Explanation: 14-period Relative Strength Index.
  - Formula: standard RSI(14) on close.
  - Why included: captures momentum state and potential overbought/oversold conditions.
- `macd_hist`
  - Explanation: MACD histogram (MACD line minus signal line).
  - Formula: `macd_t - signal_t` with standard MACD settings.
  - Why included: measures momentum acceleration and turning behavior.

### E. Volatility features
- `atr_14_pct`
  - Explanation: 14-period ATR scaled by close price.
  - Formula: `atr14_t / close_t`.
  - Why included: normalized true-range volatility signal.
- `rolling_vol_12`
  - Explanation: short rolling volatility of one-candle log returns.
  - Formula: `std(log_return_1, window=12)`.
  - Why included: captures recent local turbulence.
- `rolling_vol_48`
  - Explanation: longer rolling volatility of one-candle log returns.
  - Formula: `std(log_return_1, window=48)`.
  - Why included: captures broader short-term volatility regime.

### F. Volume / participation features
- `volume_change_1`
  - Explanation: one-candle percentage change in volume.
  - Formula: `(volume_t / volume_{t-1}) - 1`.
  - Why included: captures participation surges and fades.
- `volume_ma_ratio_20`
  - Explanation: volume relative to its 20-period mean.
  - Formula: `volume_t / mean(volume, 20)_t`.
  - Why included: identifies unusual activity versus recent baseline.
- `turnover_ma_ratio_20`
  - Explanation: turnover relative to its 20-period mean.
  - Formula: `turnover_t / mean(turnover, 20)_t`.
  - Why included: adds notional-flow context complementary to raw volume.

## Design principles
- All features are causal and use only current and past candles.
- No future information is used at any step.
- The feature set is intentionally compact but expressive.
- Coverage spans trend, momentum, volatility, candle structure, and participation.
- The same feature definitions are suitable for offline training and later real-time inference.

## Notes
- Rows at the start of the series are dropped due to rolling-window and indicator warmup periods.
- This warmup-related row drop is expected and normal.
- This is feature set version 1 and can be extended later through controlled experiments.
