from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import yaml


FEATURE_NAMES = [
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
    "rsi_14_change_1",
    "macd_hist",
    "macd_hist_change_1",
    "atr_14_pct",
    "rolling_vol_12",
    "rolling_vol_48",
    "volume_change_1",
    "volume_ma_ratio_20",
    "turnover_ma_ratio_20",
    "hour_sin",
    "hour_cos",
    "dow_sin",
    "dow_cos",
    "close_to_rolling_high_96",
    "close_to_rolling_low_96",
    "range_position_96",
]

EXPECTED_KEYS = {"X", "y", "end_time"}
DATASET_VERSION = "v4"


def load_settings(config_path: Path) -> dict:
    with config_path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def load_window_npz(file_path: Path, split_name: str) -> dict[str, np.ndarray]:
    if not file_path.exists():
        raise FileNotFoundError(f"{split_name} window dataset not found: {file_path}")

    payload = np.load(file_path)
    keys = set(payload.files)
    missing_keys = sorted(EXPECTED_KEYS - keys)
    if missing_keys:
        raise ValueError(f"{split_name} dataset missing keys: {missing_keys}")

    X = payload["X"]
    y = payload["y"]
    end_time = payload["end_time"]

    validate_split_arrays(X, y, end_time, split_name)

    return {"X": X, "y": y, "end_time": end_time}


def validate_split_arrays(
    X: np.ndarray,
    y: np.ndarray,
    end_time: np.ndarray,
    split_name: str,
) -> None:
    if X.ndim != 3:
        raise ValueError(f"{split_name} X must be 3D, got shape={X.shape}")
    if y.ndim != 1:
        raise ValueError(f"{split_name} y must be 1D, got shape={y.shape}")
    if end_time.ndim != 1:
        raise ValueError(f"{split_name} end_time must be 1D, got shape={end_time.shape}")

    sample_count = X.shape[0]
    if y.shape[0] != sample_count or end_time.shape[0] != sample_count:
        raise ValueError(
            f"{split_name} array length mismatch: X={sample_count}, y={y.shape[0]}, "
            f"end_time={end_time.shape[0]}"
        )

    if X.shape[2] != len(FEATURE_NAMES):
        raise ValueError(
            f"{split_name} feature dimension mismatch: expected={len(FEATURE_NAMES)}, "
            f"got={X.shape[2]}"
        )


def fit_train_scaler(X_train: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    mean = X_train.mean(axis=(0, 1), dtype=np.float64)
    std = X_train.std(axis=(0, 1), dtype=np.float64)

    zero_std_mask = std == 0.0
    std_safe = std.copy()
    std_safe[zero_std_mask] = 1.0

    return mean, std_safe, zero_std_mask


def transform_split(X: np.ndarray, mean: np.ndarray, std: np.ndarray) -> np.ndarray:
    normalized = (X.astype(np.float64, copy=False) - mean) / std
    return normalized.astype(np.float32, copy=False)


def save_normalized_dataset(file_path: Path, X: np.ndarray, y: np.ndarray, end_time: np.ndarray) -> None:
    np.savez_compressed(file_path, X=X, y=y, end_time=end_time)


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    settings = load_settings(project_root / "config" / "settings.yaml")

    symbol = settings.get("symbol")
    timeframe = settings.get("timeframe")
    windows_dir = settings.get("data", {}).get("windows_dir", "data/windows")
    normalized_dir = settings.get("data", {}).get("normalized_dir", "data/normalized")

    if not symbol or not timeframe:
        raise ValueError("Missing required config values: symbol, timeframe")

    input_paths = {
        "TRAIN": project_root / windows_dir / f"{symbol}_{timeframe}_train_windows_{DATASET_VERSION}.npz",
        "VALIDATION": project_root / windows_dir / f"{symbol}_{timeframe}_val_windows_{DATASET_VERSION}.npz",
        "TEST": project_root / windows_dir / f"{symbol}_{timeframe}_test_windows_{DATASET_VERSION}.npz",
    }

    output_paths = {
        "TRAIN": project_root / normalized_dir / f"{symbol}_{timeframe}_train_windows_norm_{DATASET_VERSION}.npz",
        "VALIDATION": project_root / normalized_dir / f"{symbol}_{timeframe}_val_windows_norm_{DATASET_VERSION}.npz",
        "TEST": project_root / normalized_dir / f"{symbol}_{timeframe}_test_windows_norm_{DATASET_VERSION}.npz",
    }
    scaler_stats_path = project_root / normalized_dir / f"{symbol}_{timeframe}_scaler_stats_{DATASET_VERSION}.npz"

    datasets = {
        split_name: load_window_npz(path, split_name)
        for split_name, path in input_paths.items()
    }

    X_train = datasets["TRAIN"]["X"]
    mean, std, zero_std_mask = fit_train_scaler(X_train)

    normalized = {}
    for split_name, payload in datasets.items():
        normalized[split_name] = {
            "X": transform_split(payload["X"], mean, std),
            "y": payload["y"],
            "end_time": payload["end_time"],
        }

    output_paths["TRAIN"].parent.mkdir(parents=True, exist_ok=True)
    for split_name, payload in normalized.items():
        save_normalized_dataset(
            output_paths[split_name],
            payload["X"],
            payload["y"],
            payload["end_time"],
        )

    np.savez_compressed(
        scaler_stats_path,
        feature_names=np.array(FEATURE_NAMES, dtype="U"),
        mean=mean,
        std=std,
    )

    print("Input shapes")
    print("-" * 72)
    print(f"TRAIN X/y/end_time: {datasets['TRAIN']['X'].shape}, {datasets['TRAIN']['y'].shape}, {datasets['TRAIN']['end_time'].shape}")
    print(f"VALIDATION X/y/end_time: {datasets['VALIDATION']['X'].shape}, {datasets['VALIDATION']['y'].shape}, {datasets['VALIDATION']['end_time'].shape}")
    print(f"TEST X/y/end_time: {datasets['TEST']['X'].shape}, {datasets['TEST']['y'].shape}, {datasets['TEST']['end_time'].shape}")
    print("")

    print("Output shapes")
    print("-" * 72)
    print(f"TRAIN X/y/end_time: {normalized['TRAIN']['X'].shape}, {normalized['TRAIN']['y'].shape}, {normalized['TRAIN']['end_time'].shape}")
    print(f"VALIDATION X/y/end_time: {normalized['VALIDATION']['X'].shape}, {normalized['VALIDATION']['y'].shape}, {normalized['VALIDATION']['end_time'].shape}")
    print(f"TEST X/y/end_time: {normalized['TEST']['X'].shape}, {normalized['TEST']['y'].shape}, {normalized['TEST']['end_time'].shape}")
    print("")

    zero_std_indices = np.flatnonzero(zero_std_mask)
    print(f"Scaler mean shape: {mean.shape}")
    print(f"Scaler std shape: {std.shape}")
    print(f"Zero-std features found: {'YES' if len(zero_std_indices) > 0 else 'NO'}")
    if len(zero_std_indices) > 0:
        zero_std_features = [FEATURE_NAMES[idx] for idx in zero_std_indices.tolist()]
        print(f"Zero-std feature names: {zero_std_features}")
    print("")

    print(f"Saved TRAIN normalized dataset: {output_paths['TRAIN']}")
    print(f"Saved VALIDATION normalized dataset: {output_paths['VALIDATION']}")
    print(f"Saved TEST normalized dataset: {output_paths['TEST']}")
    print(f"Saved scaler stats: {scaler_stats_path}")
    print("")

    first_window_df = pd.DataFrame(normalized["TRAIN"]["X"][0], columns=pd.Index(FEATURE_NAMES))
    print("FIRST TRAIN WINDOW (first 5 rows)")
    print("-" * 72)
    with pd.option_context("display.max_columns", None, "display.width", 220):
        print(first_window_df.head(5).to_string(index=False))
    print("")
    print(f"First training label: {int(normalized['TRAIN']['y'][0])}")
    print(f"First training end_time: {normalized['TRAIN']['end_time'][0]}")
    print("")

    train_mean_check = normalized["TRAIN"]["X"].mean(axis=(0, 1), dtype=np.float64)
    train_std_check = normalized["TRAIN"]["X"].std(axis=(0, 1), dtype=np.float64)
    sanity_df = pd.DataFrame(
        {
            "feature": FEATURE_NAMES,
            "mean_approx": np.round(train_mean_check, 6),
            "std_approx": np.round(train_std_check, 6),
        }
    )

    print("Normalization sanity check (TRAIN)")
    print("-" * 72)
    print(sanity_df.to_string(index=False))


if __name__ == "__main__":
    main()
