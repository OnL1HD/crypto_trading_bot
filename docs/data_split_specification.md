# BTCUSDT 15m Data Split Specification v1

## Purpose
This step splits the labeled BTCUSDT 15m dataset into train, validation, and test subsets for downstream time-series modeling.

## Why chronological splitting
The dataset is time-series data, so splits must follow time order. Chronological splitting preserves causality and avoids training on future information.

## Split boundaries
Boundaries are loaded from `config/settings.yaml`:

- Train: `train_start` to `train_end` (inclusive)
- Validation: `val_start` to `val_end` (inclusive)
- Test: `open_time >= test_start`

Configured values:

- `train_start`: `2020-01-01`
- `train_end`: `2023-12-31`
- `val_start`: `2024-01-01`
- `val_end`: `2024-12-31`
- `test_start`: `2025-01-01`

## Output files
The split script writes:

- `data/splits/BTCUSDT_15m_train_v1.parquet`
- `data/splits/BTCUSDT_15m_val_v1.parquet`
- `data/splits/BTCUSDT_15m_test_v1.parquet`

## Notes
- Splitting happens before window creation.
- All label classes are preserved in splits (`UP=1`, `DOWN=0`, `NEUTRAL=-1`).
- No shuffling is used.
- This step is required to avoid future leakage between train/validation/test periods.
