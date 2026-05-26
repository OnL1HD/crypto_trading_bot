# BTCUSDT 15m Window Normalization Specification v1

## Purpose
This step standardizes TCN-ready window datasets so features have a consistent scale before model training.

## Why train-only statistics
Normalization parameters must be fitted only on training data to avoid leaking information from validation or test periods.

## Shared scaler across splits
Validation and test windows are transformed with the same scaler fitted on train windows to keep evaluation realistic and comparable.

## Formula
For each feature:

- `x_norm = (x - mean_train) / std_train`

`mean_train` and `std_train` are computed feature-wise over all train samples and all timesteps.

## Output files
- `data/normalized/BTCUSDT_15m_train_windows_norm_v1.npz`
- `data/normalized/BTCUSDT_15m_val_windows_norm_v1.npz`
- `data/normalized/BTCUSDT_15m_test_windows_norm_v1.npz`
- `data/normalized/BTCUSDT_15m_scaler_stats_v1.npz`

## Notes
- `y` is not normalized.
- `end_time` is preserved unchanged.
- This is the final preprocessing step before model training.
