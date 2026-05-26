# BTCUSDT 15m Window Dataset Specification v1

## Purpose
This step converts chronological labeled split datasets into sequence windows that are directly usable by a TCN model.

## Why sliding windows
Sequence models learn temporal structure from fixed-length histories. Sliding windows provide consistent `(time_steps, features)` inputs for supervised learning.

## Window definition
- Window size: `256`
- Input alignment: `X_t` uses feature rows `[t-255 ... t]`
- Target alignment: `y_t` uses `label` at row `t`
- Neutral rows (`label=-1`) are allowed inside `X`; only windows with neutral target row are excluded from supervised targets.

## Split isolation
Train, validation, and test are windowed separately. Windows never cross split boundaries, which preserves proper chronological evaluation.

## Gap filtering
Windows are dropped if any internal consecutive `open_time` gap is greater than `2 hours`. This avoids feeding sequences with unrealistic large time jumps.

## Output files
- `data/windows/BTCUSDT_15m_train_windows_v1.npz`
- `data/windows/BTCUSDT_15m_val_windows_v1.npz`
- `data/windows/BTCUSDT_15m_test_windows_v1.npz`

Each file contains:
- `X`: shape `(samples, 256, features)`
- `y`: shape `(samples,)`
- `end_time`: `open_time` at the window endpoint row `t`

## Notes
- No scaling or normalization is applied in this step.
- This is the final sequence construction step before normalization and model training.
