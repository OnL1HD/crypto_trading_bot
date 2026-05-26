from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import yaml


DEFAULT_FEATURE_NAMES = [
    "log_return_1",
    "log_return_4",
    "close_to_open_return",
    "high_low_range_pct",
    "body_pct",
    "upper_wick_pct",
    "lower_wick_pct",
    "body_to_range_ratio",
    "ema_20_dist",
    "ema_50_dist",
    "ema_20_50_spread",
    "rsi_14",
    "macd_hist",
    "atr_14_pct",
    "rolling_vol_12",
    "rolling_vol_48",
    "volume_change_1",
    "volume_ma_ratio_20",
    "turnover_ma_ratio_20",
]

LABEL_NAME_MAP = {
    -1: "NEUTRAL",
    0: "DOWN",
    1: "UP",
}

plt = None


def import_pyplot():
    try:
        import matplotlib.pyplot as pyplot
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "matplotlib is required for visualization. Install it with: "
            "python -m pip install matplotlib"
        ) from exc
    return pyplot


def load_settings(config_path: Path) -> dict:
    with config_path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Unified visualization tool for processed/features/labeled/splits/windows/normalized "
            "pipeline datasets."
        )
    )

    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument(
        "--processed",
        action="store_true",
        help="Use data/processed/<symbol>_<timeframe>_clean.parquet",
    )
    source_group.add_argument(
        "--features",
        action="store_true",
        help="Use data/features/<symbol>_<timeframe>_features_v1.parquet",
    )
    source_group.add_argument(
        "--labeled",
        action="store_true",
        help="Use data/labeled/<symbol>_<timeframe>_labeled_v1.parquet",
    )
    source_group.add_argument(
        "--splits",
        action="store_true",
        help="Use train/val/test parquet splits from data/splits",
    )
    source_group.add_argument(
        "--windows",
        action="store_true",
        help="Use train/val/test window NPZ datasets from data/windows",
    )
    source_group.add_argument(
        "--normalized",
        action="store_true",
        help="Use train/val/test normalized window NPZ datasets from data/normalized",
    )

    parser.add_argument(
        "--overview",
        action="store_true",
        help="General overview visualization for the selected dataset source",
    )
    parser.add_argument(
        "--feature",
        type=str,
        default=None,
        help="Plot a single feature over time (also used by --feature-dist and --sample-window)",
    )
    parser.add_argument(
        "--feature-corr",
        action="store_true",
        help="Plot numeric feature correlation heatmap",
    )
    parser.add_argument(
        "--feature-dist",
        action="store_true",
        help="Plot histogram distribution for a selected feature",
    )
    parser.add_argument(
        "--class-balance",
        action="store_true",
        help="Plot class-balance charts",
    )
    parser.add_argument(
        "--future-return-dist",
        action="store_true",
        help="Plot future_return histogram(s)",
    )
    parser.add_argument(
        "--labels-over-time",
        action="store_true",
        help="Plot monthly label counts over time (labeled dataset)",
    )
    parser.add_argument(
        "--sample-window",
        action="store_true",
        help="Inspect one sample window from train/val/test split",
    )
    parser.add_argument(
        "--gaps",
        action="store_true",
        help="Report and visualize open_time gaps larger than expected timeframe",
    )

    parser.add_argument(
        "--split",
        choices=["train", "val", "test"],
        default="train",
        help="Split for split-dependent modes (default: train)",
    )
    parser.add_argument(
        "--sample-index",
        type=int,
        default=0,
        help="Sample index for --sample-window (default: 0)",
    )
    parser.add_argument(
        "--start-date",
        type=str,
        default=None,
        help="Optional start date filter for parquet datasets (YYYY-MM-DD, UTC)",
    )
    parser.add_argument(
        "--end-date",
        type=str,
        default=None,
        help="Optional end date filter for parquet datasets (YYYY-MM-DD, UTC, inclusive)",
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="Save plot(s) as PNG into --output-dir instead of showing interactively",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/visualizations",
        help="Output directory for saved figures (default: data/visualizations)",
    )

    return parser.parse_args()


def resolve_source(args: argparse.Namespace) -> str:
    if args.processed:
        return "processed"
    if args.features:
        return "features"
    if args.labeled:
        return "labeled"
    if args.splits:
        return "splits"
    if args.windows:
        return "windows"
    return "normalized"


def is_feature_over_time_mode(args: argparse.Namespace) -> bool:
    return args.feature is not None and not args.feature_dist and not args.sample_window


def validate_requested_modes(args: argparse.Namespace) -> None:
    feature_over_time_mode = is_feature_over_time_mode(args)

    has_mode = any(
        [
            args.overview,
            feature_over_time_mode,
            args.feature_corr,
            args.feature_dist,
            args.class_balance,
            args.future_return_dist,
            args.labels_over_time,
            args.sample_window,
            args.gaps,
        ]
    )
    if not has_mode:
        raise ValueError("At least one plot mode is required. Use --overview, --feature, etc.")

    if args.sample_index < 0:
        raise ValueError("--sample-index must be >= 0")


def resolve_paths(project_root: Path, settings: dict) -> dict:
    symbol = settings.get("symbol")
    timeframe = settings.get("timeframe")
    if not symbol or not timeframe:
        raise ValueError("Missing required config values: symbol, timeframe")

    data_cfg = settings.get("data", {})
    processed_dir = data_cfg.get("processed_dir", "data/processed")
    features_dir = data_cfg.get("features_dir", "data/features")
    labeled_dir = data_cfg.get("labeled_dir", "data/labeled")
    splits_dir = data_cfg.get("splits_dir", "data/splits")
    windows_dir = data_cfg.get("windows_dir", "data/windows")
    normalized_dir = data_cfg.get("normalized_dir", "data/normalized")

    return {
        "processed": project_root / processed_dir / f"{symbol}_{timeframe}_clean.parquet",
        "features": project_root / features_dir / f"{symbol}_{timeframe}_features_v1.parquet",
        "labeled": project_root / labeled_dir / f"{symbol}_{timeframe}_labeled_v1.parquet",
        "splits": {
            "train": project_root / splits_dir / f"{symbol}_{timeframe}_train_v1.parquet",
            "val": project_root / splits_dir / f"{symbol}_{timeframe}_val_v1.parquet",
            "test": project_root / splits_dir / f"{symbol}_{timeframe}_test_v1.parquet",
        },
        "windows": {
            "train": project_root / windows_dir / f"{symbol}_{timeframe}_train_windows_v1.npz",
            "val": project_root / windows_dir / f"{symbol}_{timeframe}_val_windows_v1.npz",
            "test": project_root / windows_dir / f"{symbol}_{timeframe}_test_windows_v1.npz",
        },
        "normalized": {
            "train": project_root / normalized_dir / f"{symbol}_{timeframe}_train_windows_norm_v1.npz",
            "val": project_root / normalized_dir / f"{symbol}_{timeframe}_val_windows_norm_v1.npz",
            "test": project_root / normalized_dir / f"{symbol}_{timeframe}_test_windows_norm_v1.npz",
        },
        "scaler_stats": project_root / normalized_dir / f"{symbol}_{timeframe}_scaler_stats_v1.npz",
    }


def parse_utc_date(value: str, arg_name: str) -> pd.Timestamp:
    timestamp = pd.to_datetime(value, utc=True, errors="coerce")
    if pd.isna(timestamp):
        raise ValueError(f"Invalid {arg_name}: {value}. Expected YYYY-MM-DD.")
    return pd.Timestamp(timestamp)


def parse_time_bounds(args: argparse.Namespace) -> tuple[pd.Timestamp | None, pd.Timestamp | None]:
    start = None
    end_exclusive = None

    if args.start_date is not None:
        start = parse_utc_date(args.start_date, "--start-date")
    if args.end_date is not None:
        end_exclusive = parse_utc_date(args.end_date, "--end-date") + pd.Timedelta(days=1)

    if start is not None and end_exclusive is not None and end_exclusive <= start:
        raise ValueError("--end-date must be on or after --start-date")

    return start, end_exclusive


def timeframe_to_timedelta(timeframe: str) -> pd.Timedelta:
    mapping = {
        "1m": pd.Timedelta(minutes=1),
        "3m": pd.Timedelta(minutes=3),
        "5m": pd.Timedelta(minutes=5),
        "15m": pd.Timedelta(minutes=15),
        "30m": pd.Timedelta(minutes=30),
        "1h": pd.Timedelta(hours=1),
        "2h": pd.Timedelta(hours=2),
        "4h": pd.Timedelta(hours=4),
        "6h": pd.Timedelta(hours=6),
        "12h": pd.Timedelta(hours=12),
        "1d": pd.Timedelta(days=1),
        "1w": pd.Timedelta(weeks=1),
    }
    if timeframe not in mapping:
        raise ValueError(f"Unsupported timeframe: {timeframe}")
    return mapping[timeframe]


def load_parquet_dataset(path: Path, dataset_name: str) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"{dataset_name} dataset not found: {path}")

    df = pd.read_parquet(path)
    if "open_time" in df.columns:
        df["open_time"] = pd.to_datetime(df["open_time"], utc=True, errors="coerce")
        if bool(df["open_time"].isna().any()):
            invalid_count = int(df["open_time"].isna().sum())
            raise ValueError(f"{dataset_name} has invalid open_time values: {invalid_count}")
        df = df.sort_values("open_time", ascending=True).reset_index(drop=True)
    return df


def apply_time_filter(
    df: pd.DataFrame,
    start: pd.Timestamp | None,
    end_exclusive: pd.Timestamp | None,
) -> pd.DataFrame:
    if "open_time" not in df.columns:
        return df

    mask = pd.Series(True, index=df.index)
    if start is not None:
        mask &= df["open_time"] >= start
    if end_exclusive is not None:
        mask &= df["open_time"] < end_exclusive

    return df.loc[mask].reset_index(drop=True)


def load_split_parquets(
    split_paths: dict,
    start: pd.Timestamp | None,
    end_exclusive: pd.Timestamp | None,
) -> dict[str, pd.DataFrame]:
    loaded = {}
    for split_name, path in split_paths.items():
        split_df = load_parquet_dataset(path, f"{split_name.upper()} split")
        split_df = apply_time_filter(split_df, start, end_exclusive)
        loaded[split_name] = split_df
    return loaded


def load_split_npz(split_paths: dict, dataset_name: str) -> dict[str, dict[str, np.ndarray]]:
    loaded: dict[str, dict[str, np.ndarray]] = {}
    for split_name, path in split_paths.items():
        if not path.exists():
            raise FileNotFoundError(f"{dataset_name} {split_name} split dataset not found: {path}")

        with np.load(path) as payload:
            keys = set(payload.files)
            missing = sorted({"X", "y", "end_time"} - keys)
            if missing:
                raise ValueError(f"{dataset_name} {split_name} dataset missing keys: {missing}")
            loaded[split_name] = {
                "X": payload["X"],
                "y": payload["y"],
                "end_time": payload["end_time"],
            }
    return loaded


def resolve_output_dir(project_root: Path, output_dir_arg: str) -> Path:
    output_dir_path = Path(output_dir_arg)
    if output_dir_path.is_absolute():
        return output_dir_path
    return project_root / output_dir_path


def finalize_figure(
    fig: plt.Figure,
    args: argparse.Namespace,
    project_root: Path,
    file_name: str,
    saved_paths: list[Path],
) -> int:
    if args.save:
        output_dir = resolve_output_dir(project_root, args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / file_name
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        saved_paths.append(output_path)
    return 1


def require_feature_column(df: pd.DataFrame, feature_name: str) -> None:
    if feature_name not in df.columns:
        available = ", ".join(df.columns.tolist())
        raise ValueError(
            f"Feature '{feature_name}' not found. Available columns: {available}"
        )


def label_counts_to_named(labels: np.ndarray | pd.Series) -> pd.Series:
    raw_counts = pd.Series(labels).value_counts().sort_index()
    named_counts = pd.Series(dtype="int64")
    for label_value, count in raw_counts.items():
        label_int = int(label_value)
        label_name = LABEL_NAME_MAP.get(label_int, str(label_int))
        named_counts.loc[label_name] = int(count)
    return named_counts


def split_class_count_frame_from_dfs(split_dfs: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = {}
    for split_name, split_df in split_dfs.items():
        if "label" not in split_df.columns:
            raise ValueError(f"Split '{split_name}' does not contain label column")
        rows[split_name] = label_counts_to_named(split_df["label"])
    return pd.DataFrame(rows).T.fillna(0).astype(int)


def split_class_count_frame_from_npz(split_npz: dict[str, dict[str, np.ndarray]]) -> pd.DataFrame:
    rows = {}
    for split_name, payload in split_npz.items():
        rows[split_name] = label_counts_to_named(payload["y"])
    return pd.DataFrame(rows).T.fillna(0).astype(int)


def plot_grouped_class_balance(class_frame: pd.DataFrame, title: str) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(10, 5))
    x = np.arange(len(class_frame.index))
    n_cols = len(class_frame.columns)
    width = 0.8 / max(n_cols, 1)

    for idx, col_name in enumerate(class_frame.columns):
        offset = (idx - (n_cols - 1) / 2) * width
        ax.bar(x + offset, class_frame[col_name].to_numpy(), width=width, label=col_name)

    ax.set_xticks(x)
    ax.set_xticklabels([split.upper() for split in class_frame.index])
    ax.set_ylabel("Count")
    ax.set_title(title)
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    return fig


def print_feature_stats(df: pd.DataFrame, feature_name: str) -> None:
    series = pd.to_numeric(df[feature_name], errors="coerce")
    print(f"Feature: {feature_name}")
    print(f"Rows: {len(series)}")
    print(f"Min: {series.min()}")
    print(f"Max: {series.max()}")
    print(f"Mean: {series.mean()}")
    print(f"Std: {series.std()}")
    print(f"Null count: {int(series.isna().sum())}")


def print_split_time_ranges(split_dfs: dict[str, pd.DataFrame]) -> None:
    for split_name in ["train", "val", "test"]:
        split_df = split_dfs.get(split_name)
        if split_df is None or split_df.empty:
            print(f"{split_name.upper()} range: empty")
            continue
        earliest = split_df["open_time"].iloc[0]
        latest = split_df["open_time"].iloc[-1]
        print(f"{split_name.upper()} range: {earliest} -> {latest}")


def plot_processed_overview(df: pd.DataFrame) -> plt.Figure:
    if df.empty:
        raise ValueError("Processed dataset is empty after filtering")

    returns = pd.to_numeric(df["close"], errors="coerce").pct_change().dropna()

    fig, axes = plt.subplots(3, 1, figsize=(12, 10), sharex=True)
    axes[0].plot(df["open_time"], df["close"], linewidth=1.0)
    axes[0].set_title("Processed: Close price over time")
    axes[0].set_ylabel("Close")
    axes[0].grid(alpha=0.3)

    axes[1].plot(df["open_time"], df["volume"], linewidth=0.8, color="tab:orange")
    axes[1].set_title("Processed: Volume over time")
    axes[1].set_ylabel("Volume")
    axes[1].grid(alpha=0.3)

    axes[2].hist(returns, bins=80, color="tab:green", alpha=0.85)
    axes[2].set_title("Processed: Close-to-close return distribution")
    axes[2].set_xlabel("Return")
    axes[2].set_ylabel("Frequency")

    fig.tight_layout()
    return fig


def plot_features_overview(df: pd.DataFrame) -> plt.Figure:
    if df.empty:
        raise ValueError("Features dataset is empty after filtering")

    representative = ["rsi_14", "ema_20_dist", "rolling_vol_48"]
    available = [name for name in representative if name in df.columns]
    if len(available) < 3:
        numeric_cols = [
            col
            for col in df.columns
            if col != "open_time" and pd.api.types.is_numeric_dtype(df[col])
        ]
        available = numeric_cols[:3]

    if not available:
        raise ValueError("No numeric feature columns available for features overview")

    print(f"Features rows: {len(df)}")
    print(f"Features columns: {len(df.columns)}")
    print(f"Features time range: {df['open_time'].iloc[0]} -> {df['open_time'].iloc[-1]}")

    fig, axes = plt.subplots(len(available), 1, figsize=(12, 3.5 * len(available)), sharex=True)
    if len(available) == 1:
        axes = [axes]

    for idx, feature_name in enumerate(available):
        axes[idx].plot(df["open_time"], df[feature_name], linewidth=1.0)
        axes[idx].set_title(f"Features: {feature_name} over time")
        axes[idx].set_ylabel(feature_name)
        axes[idx].grid(alpha=0.3)

    axes[-1].set_xlabel("open_time")
    fig.tight_layout()
    return fig


def plot_labeled_overview(df: pd.DataFrame) -> plt.Figure:
    if df.empty:
        raise ValueError("Labeled dataset is empty after filtering")
    if "label" not in df.columns or "future_return" not in df.columns:
        raise ValueError("Labeled dataset must contain label and future_return columns")

    counts = label_counts_to_named(df["label"])

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    axes[0].bar(counts.index.tolist(), counts.values, color=["tab:green", "tab:red", "tab:blue"][: len(counts)])
    axes[0].set_title("Labeled: class counts")
    axes[0].set_ylabel("Count")
    axes[0].grid(axis="y", alpha=0.3)

    axes[1].hist(pd.to_numeric(df["future_return"], errors="coerce").dropna(), bins=80, color="tab:purple", alpha=0.85)
    axes[1].set_title("Labeled: future_return distribution")
    axes[1].set_xlabel("future_return")
    axes[1].set_ylabel("Frequency")

    fig.tight_layout()
    return fig


def plot_splits_overview(split_dfs: dict[str, pd.DataFrame]) -> plt.Figure:
    row_counts = pd.Series({split_name: len(df) for split_name, df in split_dfs.items()})
    class_frame = split_class_count_frame_from_dfs(split_dfs)
    print_split_time_ranges(split_dfs)

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    axes[0].bar([name.upper() for name in row_counts.index], row_counts.values, color="tab:blue")
    axes[0].set_title("Splits: row counts")
    axes[0].set_ylabel("Rows")
    axes[0].grid(axis="y", alpha=0.3)

    x = np.arange(len(class_frame.index))
    n_cols = len(class_frame.columns)
    width = 0.8 / max(n_cols, 1)
    for idx, col_name in enumerate(class_frame.columns):
        offset = (idx - (n_cols - 1) / 2) * width
        axes[1].bar(x + offset, class_frame[col_name].to_numpy(), width=width, label=col_name)

    axes[1].set_xticks(x)
    axes[1].set_xticklabels([name.upper() for name in class_frame.index])
    axes[1].set_title("Splits: class balance")
    axes[1].set_ylabel("Count")
    axes[1].legend()
    axes[1].grid(axis="y", alpha=0.3)

    fig.tight_layout()
    return fig


def plot_windows_overview(
    split_npz: dict[str, dict[str, np.ndarray]],
    title_prefix: str,
) -> plt.Figure:
    sample_counts = pd.Series(
        {split_name: int(payload["X"].shape[0]) for split_name, payload in split_npz.items()}
    )
    class_frame = split_class_count_frame_from_npz(split_npz)

    for split_name in ["train", "val", "test"]:
        payload = split_npz[split_name]
        print(
            f"{split_name.upper()} shapes: X={payload['X'].shape}, "
            f"y={payload['y'].shape}, end_time={payload['end_time'].shape}"
        )

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    axes[0].bar([name.upper() for name in sample_counts.index], sample_counts.values, color="tab:blue")
    axes[0].set_title(f"{title_prefix}: sample counts")
    axes[0].set_ylabel("Samples")
    axes[0].grid(axis="y", alpha=0.3)

    x = np.arange(len(class_frame.index))
    n_cols = len(class_frame.columns)
    width = 0.8 / max(n_cols, 1)
    for idx, col_name in enumerate(class_frame.columns):
        offset = (idx - (n_cols - 1) / 2) * width
        axes[1].bar(x + offset, class_frame[col_name].to_numpy(), width=width, label=col_name)

    axes[1].set_xticks(x)
    axes[1].set_xticklabels([name.upper() for name in class_frame.index])
    axes[1].set_title(f"{title_prefix}: class balance")
    axes[1].set_ylabel("Count")
    axes[1].legend()
    axes[1].grid(axis="y", alpha=0.3)

    fig.tight_layout()
    return fig


def plot_feature_over_time(df: pd.DataFrame, feature_name: str, source_name: str) -> plt.Figure:
    if "open_time" not in df.columns:
        raise ValueError(f"{source_name} dataset has no open_time column for --feature mode")
    require_feature_column(df, feature_name)

    print_feature_stats(df, feature_name)

    fig, ax = plt.subplots(figsize=(12, 4.5))
    ax.plot(df["open_time"], pd.to_numeric(df[feature_name], errors="coerce"), linewidth=1.0)
    ax.set_title(f"{source_name}: {feature_name} over time")
    ax.set_xlabel("open_time")
    ax.set_ylabel(feature_name)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    return fig


def plot_feature_correlation(df: pd.DataFrame, source_name: str) -> plt.Figure:
    numeric_df = df.select_dtypes(include=[np.number]).copy()
    if source_name == "labeled" and "label" in numeric_df.columns:
        numeric_df = numeric_df.drop(columns=["label"])

    if numeric_df.empty:
        raise ValueError("No numeric columns available for correlation heatmap")

    corr = numeric_df.corr()
    fig, ax = plt.subplots(figsize=(11, 9))
    heatmap = ax.imshow(corr.values, cmap="coolwarm", vmin=-1, vmax=1)
    ax.set_title(f"{source_name}: feature correlation")
    ax.set_xticks(np.arange(len(corr.columns)))
    ax.set_yticks(np.arange(len(corr.columns)))
    ax.set_xticklabels(corr.columns, rotation=90, fontsize=8)
    ax.set_yticklabels(corr.columns, fontsize=8)
    fig.colorbar(heatmap, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    return fig


def plot_feature_distribution_from_df(df: pd.DataFrame, feature_name: str, source_name: str) -> plt.Figure:
    require_feature_column(df, feature_name)
    values = pd.to_numeric(df[feature_name], errors="coerce").dropna()

    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.hist(values, bins=80, alpha=0.85, color="tab:blue")
    ax.set_title(f"{source_name}: distribution of {feature_name}")
    ax.set_xlabel(feature_name)
    ax.set_ylabel("Frequency")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    return fig


def plot_labeled_class_balance(df: pd.DataFrame) -> plt.Figure:
    if "label" not in df.columns:
        raise ValueError("Labeled dataset must contain label column for --class-balance")

    counts = label_counts_to_named(df["label"])
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.bar(counts.index.tolist(), counts.values, color=["tab:green", "tab:red", "tab:blue"][: len(counts)])
    ax.set_title("Labeled: class balance")
    ax.set_ylabel("Count")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    return fig


def plot_future_return_distribution_labeled(df: pd.DataFrame) -> plt.Figure:
    if "future_return" not in df.columns:
        raise ValueError("Labeled dataset must contain future_return for --future-return-dist")

    fig, ax = plt.subplots(figsize=(10, 4.5))
    if "label" in df.columns:
        for label_value in sorted(df["label"].dropna().unique().tolist()):
            label_name = LABEL_NAME_MAP.get(int(label_value), str(int(label_value)))
            values = pd.to_numeric(
                df.loc[df["label"] == label_value, "future_return"],
                errors="coerce",
            ).dropna()
            if not values.empty:
                ax.hist(values, bins=70, alpha=0.45, label=label_name)
        ax.legend()
    else:
        values = pd.to_numeric(df["future_return"], errors="coerce").dropna()
        ax.hist(values, bins=80, alpha=0.85, color="tab:blue")

    ax.set_title("Labeled: future_return distribution")
    ax.set_xlabel("future_return")
    ax.set_ylabel("Frequency")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    return fig


def plot_future_return_distribution_splits(split_dfs: dict[str, pd.DataFrame]) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(10, 4.5))
    for split_name in ["train", "val", "test"]:
        split_df = split_dfs[split_name]
        if "future_return" not in split_df.columns:
            raise ValueError(f"Split '{split_name}' does not contain future_return column")
        values = pd.to_numeric(split_df["future_return"], errors="coerce").dropna()
        if not values.empty:
            ax.hist(values, bins=70, alpha=0.35, label=split_name.upper())

    ax.set_title("Splits: future_return distribution")
    ax.set_xlabel("future_return")
    ax.set_ylabel("Frequency")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    return fig


def plot_labels_over_time(df: pd.DataFrame) -> plt.Figure:
    if "label" not in df.columns or "open_time" not in df.columns:
        raise ValueError("Labeled dataset must contain open_time and label for --labels-over-time")

    monthly = (
        df.set_index("open_time")
        .groupby([pd.Grouper(freq="MS"), "label"])
        .size()
        .unstack(fill_value=0)
    )

    fig, ax = plt.subplots(figsize=(12, 5))
    for label_value in sorted(monthly.columns.tolist()):
        label_name = LABEL_NAME_MAP.get(int(label_value), str(int(label_value)))
        ax.plot(monthly.index, monthly[label_value], label=label_name)

    ax.set_title("Labeled: monthly label counts")
    ax.set_xlabel("Month")
    ax.set_ylabel("Count")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    return fig


def resolve_feature_names(paths: dict) -> list[str]:
    scaler_stats_path = paths["scaler_stats"]
    if scaler_stats_path.exists():
        with np.load(scaler_stats_path) as payload:
            if "feature_names" in payload.files:
                feature_names = payload["feature_names"].tolist()
                if feature_names:
                    return [str(name) for name in feature_names]
    return DEFAULT_FEATURE_NAMES.copy()


def resolve_feature_index(feature_name: str, feature_names: list[str]) -> int:
    if feature_name not in feature_names:
        available = ", ".join(feature_names)
        raise ValueError(f"Feature '{feature_name}' not found. Available features: {available}")
    return feature_names.index(feature_name)


def plot_feature_distribution_from_npz(
    split_npz: dict[str, dict[str, np.ndarray]],
    split_name: str,
    feature_name: str,
    feature_names: list[str],
    source_name: str,
) -> plt.Figure:
    feature_idx = resolve_feature_index(feature_name, feature_names)
    split_payload = split_npz[split_name]
    values = split_payload["X"][:, :, feature_idx].reshape(-1)

    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.hist(values, bins=80, alpha=0.85, color="tab:blue")
    ax.set_title(
        f"{source_name}: distribution of {feature_name} ({split_name.upper()} split)"
    )
    ax.set_xlabel(feature_name)
    ax.set_ylabel("Frequency")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    return fig


def plot_sample_window(
    split_npz: dict[str, dict[str, np.ndarray]],
    split_name: str,
    sample_index: int,
    feature_name: str | None,
    feature_names: list[str],
    source_name: str,
) -> plt.Figure:
    payload = split_npz[split_name]
    X = payload["X"]
    y = payload["y"]
    end_time = payload["end_time"]

    sample_count = X.shape[0]
    if sample_count == 0:
        raise ValueError(f"{source_name} {split_name} split has no samples")
    if sample_index >= sample_count:
        raise ValueError(
            f"sample_index out of bounds for {split_name}: {sample_index} >= {sample_count}"
        )

    sample_window = X[sample_index]
    sample_label = int(y[sample_index])
    sample_end_time = end_time[sample_index]

    print(f"Split: {split_name.upper()}")
    print(f"Sample index: {sample_index}")
    print(f"Sample window shape: {sample_window.shape}")
    print(f"Sample label: {sample_label}")
    print(f"Sample end_time: {sample_end_time}")

    if feature_name is not None:
        feature_idx = resolve_feature_index(feature_name, feature_names)
        fig, ax = plt.subplots(figsize=(10, 4.5))
        ax.plot(np.arange(sample_window.shape[0]), sample_window[:, feature_idx], linewidth=1.2)
        ax.set_title(
            f"{source_name}: sample window {split_name.upper()} idx={sample_index} "
            f"feature={feature_name}"
        )
        ax.set_xlabel("Timestep")
        ax.set_ylabel(feature_name)
        ax.grid(alpha=0.3)
        fig.tight_layout()
        return fig

    fig, ax = plt.subplots(figsize=(10, 5))
    image = ax.imshow(sample_window.T, aspect="auto", origin="lower", cmap="viridis")
    ax.set_title(f"{source_name}: sample window heatmap {split_name.upper()} idx={sample_index}")
    ax.set_xlabel("Timestep")
    ax.set_ylabel("Feature index")
    ax.set_yticks(np.arange(len(feature_names)))
    ax.set_yticklabels(feature_names, fontsize=7)
    fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    return fig


def compute_gaps(df: pd.DataFrame, expected_delta: pd.Timedelta) -> pd.DataFrame:
    if "open_time" not in df.columns:
        raise ValueError("Dataset has no open_time column for --gaps")
    if df.empty:
        return pd.DataFrame(columns=["prev_open_time", "open_time", "diff"])

    interval_df = pd.DataFrame(
        {
            "prev_open_time": df["open_time"].shift(1),
            "open_time": df["open_time"],
        }
    ).iloc[1:]
    interval_df["diff"] = interval_df["open_time"] - interval_df["prev_open_time"]
    return interval_df.loc[interval_df["diff"] > expected_delta].reset_index(drop=True)


def plot_gaps(gaps_df: pd.DataFrame, expected_delta: pd.Timedelta, source_name: str) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(10, 4.5))
    if gaps_df.empty:
        ax.text(0.5, 0.5, "No gaps larger than expected timeframe.", ha="center", va="center")
        ax.set_title(f"{source_name}: gaps (> {expected_delta})")
        ax.set_axis_off()
        fig.tight_layout()
        return fig

    gap_minutes = gaps_df["diff"].dt.total_seconds().to_numpy() / 60.0
    ax.bar(np.arange(len(gap_minutes)), gap_minutes, color="tab:red", alpha=0.85)
    ax.set_title(f"{source_name}: gaps (> {expected_delta})")
    ax.set_xlabel("Gap index")
    ax.set_ylabel("Gap length (minutes)")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    return fig


def main() -> None:
    global plt

    args = parse_args()
    validate_requested_modes(args)
    source = resolve_source(args)

    plt = import_pyplot()

    project_root = Path(__file__).resolve().parents[1]
    settings = load_settings(project_root / "config" / "settings.yaml")
    paths = resolve_paths(project_root, settings)
    start, end_exclusive = parse_time_bounds(args)

    saved_paths: list[Path] = []
    figure_count = 0

    parquet_df: pd.DataFrame | None = None
    split_dfs: dict[str, pd.DataFrame] | None = None
    split_npz: dict[str, dict[str, np.ndarray]] | None = None
    feature_names = DEFAULT_FEATURE_NAMES.copy()

    if source in {"processed", "features", "labeled"}:
        parquet_df = load_parquet_dataset(paths[source], source)
        parquet_df = apply_time_filter(parquet_df, start, end_exclusive)
    elif source == "splits":
        split_dfs = load_split_parquets(paths["splits"], start, end_exclusive)
    elif source == "windows":
        split_npz = load_split_npz(paths["windows"], "windows")
        feature_names = DEFAULT_FEATURE_NAMES.copy()
    elif source == "normalized":
        split_npz = load_split_npz(paths["normalized"], "normalized")
        feature_names = resolve_feature_names(paths)

    if args.overview:
        if source == "processed":
            fig = plot_processed_overview(parquet_df)
            figure_count += finalize_figure(fig, args, project_root, "processed_overview.png", saved_paths)
        elif source == "features":
            fig = plot_features_overview(parquet_df)
            figure_count += finalize_figure(fig, args, project_root, "features_overview.png", saved_paths)
        elif source == "labeled":
            fig = plot_labeled_overview(parquet_df)
            figure_count += finalize_figure(fig, args, project_root, "labeled_overview.png", saved_paths)
        elif source == "splits":
            fig = plot_splits_overview(split_dfs)
            figure_count += finalize_figure(fig, args, project_root, "splits_overview.png", saved_paths)
        elif source == "windows":
            fig = plot_windows_overview(split_npz, "Windows")
            figure_count += finalize_figure(fig, args, project_root, "windows_overview.png", saved_paths)
        else:
            fig = plot_windows_overview(split_npz, "Normalized")
            figure_count += finalize_figure(fig, args, project_root, "normalized_overview.png", saved_paths)

    if is_feature_over_time_mode(args):
        if source not in {"processed", "features", "labeled"}:
            raise ValueError("--feature over-time mode is supported for --processed, --features, or --labeled")
        fig = plot_feature_over_time(parquet_df, args.feature, source)
        figure_count += finalize_figure(
            fig,
            args,
            project_root,
            f"{source}_feature_{args.feature}.png",
            saved_paths,
        )

    if args.feature_corr:
        if source not in {"features", "labeled"}:
            raise ValueError("--feature-corr is supported for --features or --labeled")
        fig = plot_feature_correlation(parquet_df, source)
        figure_count += finalize_figure(fig, args, project_root, f"{source}_corr.png", saved_paths)

    if args.feature_dist:
        if source in {"features", "labeled"}:
            if args.feature is None:
                raise ValueError("--feature-dist requires --feature FEATURE_NAME")
            fig = plot_feature_distribution_from_df(parquet_df, args.feature, source)
            figure_count += finalize_figure(
                fig,
                args,
                project_root,
                f"{source}_feature_dist_{args.feature}.png",
                saved_paths,
            )
        elif source == "normalized":
            if args.feature is None:
                raise ValueError("--feature-dist with --normalized requires --feature FEATURE_NAME")
            fig = plot_feature_distribution_from_npz(
                split_npz,
                args.split,
                args.feature,
                feature_names,
                source,
            )
            figure_count += finalize_figure(
                fig,
                args,
                project_root,
                f"normalized_feature_dist_{args.split}_{args.feature}.png",
                saved_paths,
            )
        else:
            raise ValueError("--feature-dist is supported for --features, --labeled, or --normalized")

    if args.class_balance:
        if source == "labeled":
            fig = plot_labeled_class_balance(parquet_df)
            figure_count += finalize_figure(
                fig,
                args,
                project_root,
                "labeled_class_balance.png",
                saved_paths,
            )
        elif source == "splits":
            class_frame = split_class_count_frame_from_dfs(split_dfs)
            fig = plot_grouped_class_balance(class_frame, "Splits: class balance")
            figure_count += finalize_figure(
                fig,
                args,
                project_root,
                "splits_class_balance.png",
                saved_paths,
            )
        elif source in {"windows", "normalized"}:
            class_frame = split_class_count_frame_from_npz(split_npz)
            fig = plot_grouped_class_balance(class_frame, f"{source.capitalize()}: class balance")
            figure_count += finalize_figure(
                fig,
                args,
                project_root,
                f"{source}_class_balance.png",
                saved_paths,
            )
        else:
            raise ValueError("--class-balance is supported for --labeled, --splits, --windows, or --normalized")

    if args.future_return_dist:
        if source == "labeled":
            fig = plot_future_return_distribution_labeled(parquet_df)
            figure_count += finalize_figure(
                fig,
                args,
                project_root,
                "labeled_future_return_dist.png",
                saved_paths,
            )
        elif source == "splits":
            fig = plot_future_return_distribution_splits(split_dfs)
            figure_count += finalize_figure(
                fig,
                args,
                project_root,
                "splits_future_return_dist.png",
                saved_paths,
            )
        else:
            raise ValueError("--future-return-dist is supported for --labeled or --splits")

    if args.labels_over_time:
        if source != "labeled":
            raise ValueError("--labels-over-time is supported only for --labeled")
        fig = plot_labels_over_time(parquet_df)
        figure_count += finalize_figure(
            fig,
            args,
            project_root,
            "labeled_labels_over_time.png",
            saved_paths,
        )

    if args.sample_window:
        if source not in {"windows", "normalized"}:
            raise ValueError("--sample-window is supported for --windows or --normalized")
        fig = plot_sample_window(
            split_npz,
            args.split,
            args.sample_index,
            args.feature,
            feature_names,
            source,
        )
        figure_count += finalize_figure(
            fig,
            args,
            project_root,
            f"{source}_sample_window_{args.split}_idx{args.sample_index}.png",
            saved_paths,
        )

    if args.gaps:
        if source not in {"processed", "features", "labeled"}:
            raise ValueError("--gaps is supported for --processed, --features, or --labeled")
        expected_delta = timeframe_to_timedelta(settings.get("timeframe", "15m"))
        gaps_df = compute_gaps(parquet_df, expected_delta)
        print(f"Expected interval: {expected_delta}")
        print(f"Gap count (> expected): {len(gaps_df)}")
        if not gaps_df.empty:
            print("First gap examples:")
            print(gaps_df.head(10).to_string(index=False))
        fig = plot_gaps(gaps_df, expected_delta, source)
        figure_count += finalize_figure(fig, args, project_root, f"{source}_gaps.png", saved_paths)

    if args.save and saved_paths:
        print("Saved plots:")
        for path in saved_paths:
            print(path)

    if not args.save and figure_count > 0:
        plt.show()


if __name__ == "__main__":
    main()
