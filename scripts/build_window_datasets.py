from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import yaml


WINDOW_SIZE = 256
MAX_ALLOWED_GAP = pd.Timedelta(hours=2)
MAX_ALLOWED_GAP_NP = np.timedelta64(2, "h")
EXCLUDED_COLUMNS = {"open_time", "future_return", "label"}
REQUIRED_COLUMNS = {"open_time", "label"}
DATASET_VERSION = "v4"


def load_settings(config_path: Path) -> dict:
    with config_path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build TCN-ready sliding-window datasets from chronological labeled splits."
    )
    parser.add_argument(
        "--inspect",
        action="store_true",
        help="Print basic preview information for each split's built windows.",
    )
    return parser.parse_args()


def validate_required_columns(df: pd.DataFrame, split_name: str) -> None:
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing_columns:
        raise ValueError(
            f"{split_name} split is missing required columns: " + ", ".join(missing_columns)
        )


def standardize_and_validate_order(df: pd.DataFrame, split_name: str) -> pd.DataFrame:
    prepared = df.copy()
    prepared["open_time"] = pd.to_datetime(prepared["open_time"], utc=True, errors="coerce")

    invalid_time_count = int(prepared["open_time"].isna().sum())
    if invalid_time_count > 0:
        raise ValueError(f"{split_name} split has invalid open_time values: {invalid_time_count}")

    prepared = prepared.sort_values("open_time", ascending=True).reset_index(drop=True)

    duplicate_count = int(prepared["open_time"].duplicated().sum())
    if duplicate_count > 0:
        raise ValueError(f"{split_name} split has duplicate open_time rows: {duplicate_count}")

    ordering_violations = int((prepared["open_time"].diff().dropna() <= pd.Timedelta(0)).sum())
    if ordering_violations > 0:
        raise ValueError(
            f"{split_name} split has non-increasing open_time steps: {ordering_violations}"
        )

    if not bool(prepared["label"].isin([0, 1, -1]).all()):
        raise ValueError(f"{split_name} split contains label values outside {{0, 1, -1}}")

    return prepared


def resolve_feature_columns(df: pd.DataFrame) -> list[str]:
    feature_columns = [column for column in df.columns if column not in EXCLUDED_COLUMNS]
    if not feature_columns:
        raise ValueError("No feature columns found after excluding open_time/future_return/label.")
    return feature_columns


def validate_feature_columns(df: pd.DataFrame, split_name: str, expected_features: list[str]) -> None:
    missing_columns = [column for column in expected_features if column not in df.columns]
    if missing_columns:
        raise ValueError(
            f"{split_name} split is missing expected feature columns: "
            + ", ".join(missing_columns)
        )


def build_windows_for_split(
    df: pd.DataFrame,
    feature_columns: list[str],
) -> dict:
    row_count = len(df)
    feature_count = len(feature_columns)
    dropped_insufficient_history = min(WINDOW_SIZE - 1, row_count)
    candidate_count = max(row_count - WINDOW_SIZE + 1, 0)

    feature_matrix = df[feature_columns].to_numpy(dtype=np.float32, copy=False)
    labels = df["label"].to_numpy(dtype=np.int8, copy=False)
    end_times_all = (
        df["open_time"].dt.tz_convert("UTC").dt.tz_localize(None).to_numpy(dtype="datetime64[ns]")
    )

    if candidate_count == 0:
        return {
            "X": np.empty((0, WINDOW_SIZE, feature_count), dtype=np.float32),
            "y": np.empty((0,), dtype=np.int8),
            "end_time": np.empty((0,), dtype="datetime64[ns]"),
            "input_rows": row_count,
            "candidate_count": candidate_count,
            "dropped_insufficient_history": dropped_insufficient_history,
            "dropped_neutral_target": 0,
            "dropped_gap": 0,
            "final_count": 0,
        }

    diffs = np.diff(end_times_all)
    large_gap_flags = diffs > MAX_ALLOWED_GAP_NP
    gap_window_mask = np.lib.stride_tricks.sliding_window_view(
        large_gap_flags,
        WINDOW_SIZE - 1,
    ).any(axis=1)
    non_gap_window_mask = ~gap_window_mask

    feature_windows_view = np.lib.stride_tricks.sliding_window_view(
        feature_matrix,
        WINDOW_SIZE,
        axis=0,
    )
    feature_windows_view = np.swapaxes(feature_windows_view, 1, 2)

    candidate_labels = labels[WINDOW_SIZE - 1 :]
    candidate_end_times = end_times_all[WINDOW_SIZE - 1 :]

    neutral_target_mask = candidate_labels == -1
    windows_dropped_neutral_target = int(neutral_target_mask.sum())

    valid_after_label_mask = ~neutral_target_mask
    windows_dropped_gap = int((gap_window_mask & valid_after_label_mask).sum())
    valid_window_mask = valid_after_label_mask & non_gap_window_mask

    X = feature_windows_view[valid_window_mask].astype(np.float32, copy=False)
    y = candidate_labels[valid_window_mask].astype(np.int8, copy=False)
    end_time = candidate_end_times[valid_window_mask]

    if not np.isin(y, [0, 1]).all():
        raise ValueError("Final target array y contains values outside {0, 1}")

    return {
        "X": X,
        "y": y,
        "end_time": end_time,
        "input_rows": row_count,
        "candidate_count": candidate_count,
        "dropped_insufficient_history": dropped_insufficient_history,
        "dropped_neutral_target": windows_dropped_neutral_target,
        "dropped_gap": windows_dropped_gap,
        "final_count": len(X),
    }


def print_split_summary(split_name: str, result: dict) -> None:
    X = result["X"]
    y = result["y"]
    end_time = result["end_time"]

    up_count = int((y == 1).sum())
    down_count = int((y == 0).sum())

    print(f"{split_name} input rows: {result['input_rows']}")
    print(f"{split_name} candidate windows before filtering: {result['candidate_count']}")
    print(
        f"{split_name} windows dropped due to insufficient history: "
        f"{result['dropped_insufficient_history']}"
    )
    print(
        f"{split_name} windows dropped due to neutral target label: "
        f"{result['dropped_neutral_target']}"
    )
    print(f"{split_name} windows dropped due to gap filtering: {result['dropped_gap']}")
    print(f"{split_name} final window count: {result['final_count']}")
    print(f"{split_name} X shape: {X.shape}")
    print(f"{split_name} y shape: {y.shape}")
    print(f"{split_name} class distribution -> UP: {up_count}, DOWN: {down_count}")
    if len(end_time) > 0:
        print(f"{split_name} earliest end_time: {end_time[0]}")
        print(f"{split_name} latest end_time: {end_time[-1]}")
    else:
        print(f"{split_name} earliest end_time: N/A")
        print(f"{split_name} latest end_time: N/A")


def print_split_inspect(split_name: str, result: dict) -> None:
    X = result["X"]
    y = result["y"]
    end_time = result["end_time"]

    if len(end_time) == 0:
        print(f"\n{split_name} inspect")
        print("-" * 72)
        print("No windows available to inspect.")
        return

    first_three = end_time[:3].astype("datetime64[ns]").astype(str).tolist()
    last_three = end_time[-3:].astype("datetime64[ns]").astype(str).tolist()

    print(f"\n{split_name} inspect")
    print("-" * 72)
    print(f"First 3 end_time values: {first_three}")
    print(f"Last 3 end_time values: {last_three}")
    print(f"First window shape: {X[0].shape}")
    print(f"First label: {int(y[0])}")
    print(f"Last label: {int(y[-1])}")


def main() -> None:
    args = parse_args()

    project_root = Path(__file__).resolve().parents[1]
    settings = load_settings(project_root / "config" / "settings.yaml")

    symbol = settings.get("symbol")
    timeframe = settings.get("timeframe")
    splits_dir = settings.get("data", {}).get("splits_dir", "data/splits")
    windows_dir = settings.get("data", {}).get("windows_dir", "data/windows")

    if not symbol or not timeframe:
        raise ValueError("Missing required config values: symbol, timeframe")

    split_paths = {
        "TRAIN": project_root / splits_dir / f"{symbol}_{timeframe}_train_{DATASET_VERSION}.parquet",
        "VALIDATION": project_root / splits_dir / f"{symbol}_{timeframe}_val_{DATASET_VERSION}.parquet",
        "TEST": project_root / splits_dir / f"{symbol}_{timeframe}_test_{DATASET_VERSION}.parquet",
    }

    output_paths = {
        "TRAIN": project_root / windows_dir / f"{symbol}_{timeframe}_train_windows_{DATASET_VERSION}.npz",
        "VALIDATION": project_root / windows_dir / f"{symbol}_{timeframe}_val_windows_{DATASET_VERSION}.npz",
        "TEST": project_root / windows_dir / f"{symbol}_{timeframe}_test_windows_{DATASET_VERSION}.npz",
    }

    loaded_splits: dict[str, pd.DataFrame] = {}
    for split_name, split_path in split_paths.items():
        if not split_path.exists():
            raise FileNotFoundError(f"{split_name} split dataset not found: {split_path}")

        split_df = pd.read_parquet(split_path)
        validate_required_columns(split_df, split_name)
        loaded_splits[split_name] = standardize_and_validate_order(split_df, split_name)

    expected_feature_columns = resolve_feature_columns(loaded_splits["TRAIN"])
    for split_name, split_df in loaded_splits.items():
        validate_feature_columns(split_df, split_name, expected_feature_columns)

    built_results: dict[str, dict] = {}
    for split_name in ["TRAIN", "VALIDATION", "TEST"]:
        built_results[split_name] = build_windows_for_split(
            loaded_splits[split_name],
            expected_feature_columns,
        )

    output_paths["TRAIN"].parent.mkdir(parents=True, exist_ok=True)
    for split_name, result in built_results.items():
        np.savez_compressed(
            output_paths[split_name],
            X=result["X"],
            y=result["y"],
            end_time=result["end_time"],
        )

    print(f"Window size: {WINDOW_SIZE}")
    print(f"Max allowed internal gap: {MAX_ALLOWED_GAP}")
    print(f"Feature column count: {len(expected_feature_columns)}")
    print("")

    for split_name in ["TRAIN", "VALIDATION", "TEST"]:
        print_split_summary(split_name, built_results[split_name])
        print("")

    print(f"Saved TRAIN windows: {output_paths['TRAIN']}")
    print(f"Saved VALIDATION windows: {output_paths['VALIDATION']}")
    print(f"Saved TEST windows: {output_paths['TEST']}")

    if args.inspect:
        for split_name in ["TRAIN", "VALIDATION", "TEST"]:
            print_split_inspect(split_name, built_results[split_name])


if __name__ == "__main__":
    main()
