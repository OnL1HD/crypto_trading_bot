# Data Visualization Usage

## Purpose
`scripts/visualize_data.py` is a single command-line visualization utility for inspecting major pipeline datasets:

- processed parquet
- features parquet
- labeled parquet
- split parquets (train/val/test)
- window NPZ datasets (train/val/test)
- normalized window NPZ datasets (train/val/test)

It is designed for fast visual checks during feature engineering and data-quality validation.

## Run from project root

```bash
python scripts/visualize_data.py ...
```

If matplotlib is not installed in your environment, install it first:

```bash
python -m pip install matplotlib
```

## Dataset source flags (exactly one required)

- `--processed`
- `--features`
- `--labeled`
- `--splits`
- `--windows`
- `--normalized`

## Plot mode flags

- `--overview`
- `--feature FEATURE_NAME`
- `--feature-corr`
- `--feature-dist`
- `--class-balance`
- `--future-return-dist`
- `--labels-over-time`
- `--sample-window`
- `--gaps`

At least one plot mode must be provided.

## Additional arguments

- `--split {train,val,test}` (default: `train`)
- `--sample-index INT` (default: `0`)
- `--start-date YYYY-MM-DD`
- `--end-date YYYY-MM-DD`
- `--save`
- `--output-dir PATH` (default: `data/visualizations`)

Date filtering is applied to parquet datasets with `open_time`.

## Example commands

```bash
python scripts/visualize_data.py --processed --overview
python scripts/visualize_data.py --features --feature-corr --save
python scripts/visualize_data.py --features --feature rsi_14
python scripts/visualize_data.py --labeled --class-balance --future-return-dist
python scripts/visualize_data.py --splits --overview
python scripts/visualize_data.py --normalized --sample-window --split train --sample-index 0 --feature rsi_14
python scripts/visualize_data.py --processed --gaps
```

## Output behavior

- Without `--save`, plots are shown interactively.
- With `--save`, plots are saved as PNG files in `--output-dir`.

Example filenames:

- `processed_overview.png`
- `features_corr.png`
- `labeled_class_balance.png`
- `normalized_sample_window_train_idx0.png`
