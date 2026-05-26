from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.core.serialization import to_iso_timestamp
from src.core.settings import AppSettings, load_settings


FEATURES_DATASET_SUFFIX = "features_v1.parquet"
MODEL_EXTENSIONS = (".pt", ".pth", ".ckpt")


class InferenceNotReadyError(RuntimeError):
    pass


@dataclass(frozen=True)
class ScalerStats:
    feature_names: list[str]
    mean: np.ndarray
    std: np.ndarray
    source_path: Path


@dataclass(frozen=True)
class PreparedInferenceInput:
    model_input: np.ndarray
    source_timestamp: str | None
    window_size: int
    feature_count: int


@dataclass(frozen=True)
class LoadedModel:
    model: Any
    source_path: Path
    model_version: str
    runtime: str
    model_type: str


def _build_tcn_binary_classifier(checkpoint_config: dict[str, Any]) -> Any:
    try:
        import torch
        from torch import nn
        from torch.nn.utils import weight_norm
    except ModuleNotFoundError as exc:
        raise InferenceNotReadyError("PyTorch runtime is unavailable in this environment") from exc

    class Chomp1d(nn.Module):
        def __init__(self, chomp_size: int) -> None:
            super().__init__()
            self.chomp_size = chomp_size

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            if self.chomp_size == 0:
                return x
            return x[:, :, : -self.chomp_size].contiguous()

    class TemporalBlock(nn.Module):
        def __init__(
            self,
            in_channels: int,
            out_channels: int,
            kernel_size: int,
            dilation: int,
            dropout: float,
        ) -> None:
            super().__init__()
            padding = (kernel_size - 1) * dilation

            self.conv1 = weight_norm(
                nn.Conv1d(
                    in_channels,
                    out_channels,
                    kernel_size,
                    stride=1,
                    padding=padding,
                    dilation=dilation,
                )
            )
            self.chomp1 = Chomp1d(padding)
            self.relu1 = nn.ReLU()
            self.dropout1 = nn.Dropout(dropout)

            self.conv2 = weight_norm(
                nn.Conv1d(
                    out_channels,
                    out_channels,
                    kernel_size,
                    stride=1,
                    padding=padding,
                    dilation=dilation,
                )
            )
            self.chomp2 = Chomp1d(padding)
            self.relu2 = nn.ReLU()
            self.dropout2 = nn.Dropout(dropout)

            self.net = nn.Sequential(
                self.conv1,
                self.chomp1,
                self.relu1,
                self.dropout1,
                self.conv2,
                self.chomp2,
                self.relu2,
                self.dropout2,
            )

            self.downsample: nn.Conv1d | None = None
            if in_channels != out_channels:
                self.downsample = nn.Conv1d(in_channels, out_channels, kernel_size=1)
            self.relu = nn.ReLU()

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            out = self.net(x)
            residual = x if self.downsample is None else self.downsample(x)
            return self.relu(out + residual)

    class TCNBinaryClassifier(nn.Module):
        def __init__(
            self,
            input_channels: int,
            channels: list[int],
            kernel_size: int,
            dropout: float,
        ) -> None:
            super().__init__()
            layers: list[nn.Module] = []

            for layer_index, out_channels in enumerate(channels):
                in_channels = input_channels if layer_index == 0 else channels[layer_index - 1]
                dilation = 2 ** layer_index
                layers.append(
                    TemporalBlock(
                        in_channels=in_channels,
                        out_channels=out_channels,
                        kernel_size=kernel_size,
                        dilation=dilation,
                        dropout=dropout,
                    )
                )

            self.tcn = nn.Sequential(*layers)
            self.classifier = nn.Linear(channels[-1], 1)

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            features = self.tcn(x)
            last_step = features[:, :, -1]
            logits = self.classifier(last_step)
            return logits.squeeze(-1)

    input_channels = int(checkpoint_config.get("input_channels", 19))
    channels_raw = checkpoint_config.get("channels", [32, 64, 64, 64, 64, 64])
    if not isinstance(channels_raw, list) or len(channels_raw) == 0:
        raise InferenceNotReadyError("Checkpoint config 'channels' must be a non-empty list")

    channels = [int(value) for value in channels_raw]
    kernel_size = int(checkpoint_config.get("kernel_size", 3))
    dropout = float(checkpoint_config.get("dropout", 0.3))

    return TCNBinaryClassifier(
        input_channels=input_channels,
        channels=channels,
        kernel_size=kernel_size,
        dropout=dropout,
    )


def _resolve_existing_path(primary_path: Path, fallback_glob: str | None = None) -> Path:
    if primary_path.exists() or fallback_glob is None:
        return primary_path

    matches = sorted(
        primary_path.parent.glob(fallback_glob),
        key=lambda file_path: file_path.stat().st_mtime,
        reverse=True,
    )
    if matches:
        return matches[0]
    return primary_path


def _resolve_model_path(settings: AppSettings) -> Path:
    if settings.inference_model_path is not None:
        configured_path = settings.inference_model_path
        if configured_path.exists():
            return configured_path

        if configured_path.parent.exists():
            extension = configured_path.suffix if configured_path.suffix else "*"
            if extension == "*":
                pattern = f"{settings.symbol}_{settings.timeframe}_*"
            else:
                pattern = f"{settings.symbol}_{settings.timeframe}_*{extension}"
            matches = sorted(
                configured_path.parent.glob(pattern),
                key=lambda path: path.stat().st_mtime,
                reverse=True,
            )
            if matches:
                return matches[0]

    candidate_dirs = [
        settings.project_root / "models",
        settings.project_root / "artifacts" / "models",
        settings.project_root / "data" / "models",
    ]

    symbol_prefix = f"{settings.symbol}_{settings.timeframe}_"
    matches: list[Path] = []
    for candidate_dir in candidate_dirs:
        if not candidate_dir.exists():
            continue

        for extension in MODEL_EXTENSIONS:
            matches.extend(candidate_dir.glob(f"{symbol_prefix}*{extension}"))

    if matches:
        return sorted(matches, key=lambda path: path.stat().st_mtime, reverse=True)[0]

    return settings.project_root / "models" / f"{settings.symbol}_{settings.timeframe}_model.pt"


def resolve_model_path(settings: AppSettings | None = None) -> Path:
    resolved_settings = settings or load_settings()
    return _resolve_model_path(resolved_settings)


def _resolve_scaler_stats_path(settings: AppSettings) -> Path:
    if settings.inference_scaler_stats_path is not None:
        configured_path = settings.inference_scaler_stats_path
        if configured_path.exists():
            return configured_path

        if configured_path.parent.exists():
            matches = sorted(
                configured_path.parent.glob(f"{settings.symbol}_{settings.timeframe}_scaler_stats_*.npz"),
                key=lambda path: path.stat().st_mtime,
                reverse=True,
            )
            if matches:
                return matches[0]

        return configured_path

    return _resolve_existing_path(
        settings.normalized_dir / f"{settings.symbol}_{settings.timeframe}_scaler_stats_v1.npz",
        f"{settings.symbol}_{settings.timeframe}_scaler_stats_*.npz",
    )


def resolve_scaler_stats_path(settings: AppSettings | None = None) -> Path:
    resolved_settings = settings or load_settings()
    return _resolve_scaler_stats_path(resolved_settings)


def _resolve_features_path(settings: AppSettings) -> Path:
    return _resolve_existing_path(
        settings.features_dir / f"{settings.symbol}_{settings.timeframe}_{FEATURES_DATASET_SUFFIX}",
        f"{settings.symbol}_{settings.timeframe}_features_*.parquet",
    )


def load_scaler_stats(settings: AppSettings | None = None) -> ScalerStats:
    resolved_settings = settings or load_settings()
    scaler_stats_path = _resolve_scaler_stats_path(resolved_settings)
    if not scaler_stats_path.exists():
        raise InferenceNotReadyError(f"Scaler stats artifact not found: {scaler_stats_path}")

    try:
        with np.load(scaler_stats_path) as payload:
            for required_key in ("feature_names", "mean", "std"):
                if required_key not in payload.files:
                    raise InferenceNotReadyError(
                        f"Scaler stats artifact is missing '{required_key}': {scaler_stats_path}"
                    )

            raw_feature_names = payload["feature_names"].tolist()
            feature_names = [str(name) for name in raw_feature_names]
            mean = np.asarray(payload["mean"], dtype=np.float64)
            std = np.asarray(payload["std"], dtype=np.float64)
    except InferenceNotReadyError:
        raise
    except Exception as exc:
        raise InferenceNotReadyError(
            f"Failed to load scaler stats from {scaler_stats_path}: {exc}"
        ) from exc

    if len(feature_names) == 0:
        raise InferenceNotReadyError(f"Scaler stats feature_names is empty: {scaler_stats_path}")
    if mean.ndim != 1 or std.ndim != 1:
        raise InferenceNotReadyError(
            f"Scaler stats mean/std must be 1D arrays: mean={mean.shape}, std={std.shape}"
        )
    if len(feature_names) != mean.shape[0] or len(feature_names) != std.shape[0]:
        raise InferenceNotReadyError(
            "Scaler stats feature dimension mismatch: "
            f"feature_names={len(feature_names)}, mean={mean.shape[0]}, std={std.shape[0]}"
        )

    std_safe = std.copy()
    std_safe[std_safe == 0.0] = 1.0

    return ScalerStats(
        feature_names=feature_names,
        mean=mean,
        std=std_safe,
        source_path=scaler_stats_path,
    )


def _validate_latest_window(df: pd.DataFrame, window_size: int, max_gap_minutes: int) -> pd.DataFrame:
    if len(df) < window_size:
        raise InferenceNotReadyError(
            f"Insufficient feature rows for inference window: have {len(df)}, need {window_size}"
        )

    latest_window = df.tail(window_size).reset_index(drop=True)
    window_diffs = latest_window["open_time"].diff().dropna()
    max_allowed_gap = pd.Timedelta(minutes=max_gap_minutes)
    if bool((window_diffs > max_allowed_gap).any()):
        raise InferenceNotReadyError(
            "Latest feature window contains a gap larger than "
            f"{max_gap_minutes} minutes"
        )

    return latest_window


def prepare_latest_input(
    scaler_stats: ScalerStats,
    settings: AppSettings | None = None,
) -> PreparedInferenceInput:
    resolved_settings = settings or load_settings()
    features_path = _resolve_features_path(resolved_settings)
    if not features_path.exists():
        raise InferenceNotReadyError(f"Features dataset not found: {features_path}")

    try:
        features_df = pd.read_parquet(features_path)
    except Exception as exc:
        raise InferenceNotReadyError(f"Failed to read features dataset: {features_path}: {exc}") from exc

    if features_df.empty:
        raise InferenceNotReadyError(f"Features dataset is empty: {features_path}")
    if "open_time" not in features_df.columns:
        raise InferenceNotReadyError(f"Features dataset missing open_time column: {features_path}")

    missing_features = [
        feature_name for feature_name in scaler_stats.feature_names if feature_name not in features_df.columns
    ]
    if missing_features:
        raise InferenceNotReadyError(
            "Features dataset missing required scaler features: " + ", ".join(missing_features)
        )

    prepared_df = features_df[["open_time", *scaler_stats.feature_names]].copy()
    prepared_df["open_time"] = pd.to_datetime(prepared_df["open_time"], utc=True, errors="coerce")
    prepared_df = prepared_df.loc[pd.notna(prepared_df["open_time"])]
    prepared_df = prepared_df.sort_values("open_time", ascending=True).reset_index(drop=True)

    duplicate_count = int(prepared_df["open_time"].duplicated().sum())
    if duplicate_count > 0:
        raise InferenceNotReadyError(f"Features dataset has duplicate open_time rows: {duplicate_count}")

    for feature_name in scaler_stats.feature_names:
        prepared_df[feature_name] = pd.to_numeric(prepared_df[feature_name], errors="coerce")

    latest_window = _validate_latest_window(
        prepared_df,
        window_size=resolved_settings.inference_window_size,
        max_gap_minutes=resolved_settings.inference_max_gap_minutes,
    )

    feature_window = latest_window[scaler_stats.feature_names].to_numpy(dtype=np.float64, copy=False)
    if feature_window.shape != (resolved_settings.inference_window_size, len(scaler_stats.feature_names)):
        raise InferenceNotReadyError(
            "Unexpected feature window shape: "
            f"{feature_window.shape}, expected "
            f"({resolved_settings.inference_window_size}, {len(scaler_stats.feature_names)})"
        )

    finite_mask = np.isfinite(feature_window)
    if not bool(finite_mask.all()):
        invalid_count = int((~finite_mask).sum())
        raise InferenceNotReadyError(
            f"Latest feature window contains non-finite values: {invalid_count}"
        )

    normalized_window = ((feature_window - scaler_stats.mean) / scaler_stats.std).astype(np.float32, copy=False)
    if resolved_settings.inference_input_layout == "batch_feature_window":
        model_input = np.transpose(normalized_window, (1, 0))[np.newaxis, :, :]
    else:
        model_input = normalized_window[np.newaxis, :, :]

    source_timestamp = to_iso_timestamp(latest_window["open_time"].iloc[-1])
    return PreparedInferenceInput(
        model_input=model_input,
        source_timestamp=source_timestamp,
        window_size=resolved_settings.inference_window_size,
        feature_count=len(scaler_stats.feature_names),
    )


@lru_cache(maxsize=4)
def _load_torch_model_cached(
    path_str: str,
    device: str,
    mtime_ns: int,
    model_type: str,
    allow_unsafe_deserialization: bool,
) -> tuple[Any, str]:
    del mtime_ns

    try:
        import torch
    except ModuleNotFoundError as exc:
        raise InferenceNotReadyError("PyTorch runtime is unavailable in this environment") from exc

    model_path = Path(path_str)
    map_location = torch.device(device)

    try:
        model = torch.jit.load(str(model_path), map_location=map_location)
        model.eval()
        return model, "torchscript"
    except Exception:
        pass

    try:
        loaded = torch.load(str(model_path), map_location=map_location)
    except Exception as exc:
        error_text = str(exc)
        if "Weights only load failed" in error_text and allow_unsafe_deserialization:
            try:
                loaded = torch.load(
                    str(model_path),
                    map_location=map_location,
                    weights_only=False,
                )
            except Exception as unsafe_exc:
                raise InferenceNotReadyError(
                    "Checkpoint load failed even with unsafe deserialization enabled: "
                    f"{unsafe_exc}"
                ) from unsafe_exc
        elif "Weights only load failed" in error_text:
            raise InferenceNotReadyError(
                "Checkpoint requires full pickle deserialization but this is disabled. "
                "Set inference.allow_unsafe_deserialization=true (or env "
                "INFERENCE_ALLOW_UNSAFE_DESERIALIZATION=true) only for trusted local artifacts, "
                "or re-export model as TorchScript."
            ) from exc
        else:
            raise

    if isinstance(loaded, torch.nn.Module):
        loaded.eval()
        return loaded, "torch"

    if isinstance(loaded, dict):
        candidate = loaded.get("model")
        if isinstance(candidate, torch.nn.Module):
            candidate.eval()
            return candidate, "torch"

        state_dict = loaded.get("model_state_dict")
        if isinstance(state_dict, dict):
            if model_type != "tcn":
                raise InferenceNotReadyError(
                    "Checkpoint contains only model_state_dict and unsupported model_type. "
                    "Provide a TorchScript/module checkpoint or set inference.model_type=tcn."
                )

            checkpoint_config = loaded.get("config")
            if checkpoint_config is None:
                checkpoint_config = {}
            if not isinstance(checkpoint_config, dict):
                raise InferenceNotReadyError("Checkpoint config must be a dictionary")

            rebuilt_model = _build_tcn_binary_classifier(checkpoint_config)
            try:
                rebuilt_model.load_state_dict(state_dict, strict=True)
            except Exception as exc:
                raise InferenceNotReadyError(
                    "Failed to load TCN state_dict into runtime architecture: "
                    f"{exc}"
                ) from exc

            rebuilt_model.eval()
            return rebuilt_model, "torch_state_dict"

        raise InferenceNotReadyError(
            "Checkpoint dictionary does not include a runnable module. "
            "Provide a TorchScript file or a serialized torch.nn.Module checkpoint."
        )

    raise InferenceNotReadyError(
        "Unsupported model artifact format. "
        "Provide a TorchScript file or a serialized torch.nn.Module checkpoint."
    )


def load_model(settings: AppSettings | None = None) -> LoadedModel:
    resolved_settings = settings or load_settings()
    model_type = resolved_settings.inference_model_type
    model_path = _resolve_model_path(resolved_settings)
    if not model_path.exists():
        raise InferenceNotReadyError(f"Model artifact not found: {model_path}")

    if model_path.suffix.lower() not in MODEL_EXTENSIONS:
        raise InferenceNotReadyError(
            f"Unsupported model file extension '{model_path.suffix}' for {model_path}"
        )

    try:
        model, runtime = _load_torch_model_cached(
            str(model_path),
            resolved_settings.inference_device,
            model_path.stat().st_mtime_ns,
            model_type,
            resolved_settings.inference_allow_unsafe_deserialization,
        )
    except InferenceNotReadyError:
        raise
    except Exception as exc:
        raise InferenceNotReadyError(f"Failed to load model from {model_path}: {exc}") from exc

    return LoadedModel(
        model=model,
        source_path=model_path,
        model_version=model_path.name,
        runtime=runtime,
        model_type=model_type,
    )


def _extract_probability_up(raw_output: Any) -> float:
    try:
        import torch
    except ModuleNotFoundError as exc:
        raise InferenceNotReadyError("PyTorch runtime is unavailable in this environment") from exc

    output = raw_output
    scalar_mode = "logits"
    if isinstance(output, dict):
        for key in ("probability_up", "probabilities", "probs", "logits", "output"):
            if key in output:
                output = output[key]
                if key == "probability_up":
                    scalar_mode = "probability"
                elif key in {"probabilities", "probs"}:
                    scalar_mode = "probabilities"
                break

    if isinstance(output, (list, tuple)) and output:
        output = output[0]

    if isinstance(output, torch.Tensor):
        output_array = output.detach().cpu().numpy()
    else:
        output_array = np.asarray(output)

    output_array = np.asarray(output_array, dtype=np.float64)
    squeezed = np.squeeze(output_array)

    if squeezed.ndim == 0:
        scalar = float(squeezed)
        if scalar_mode == "probability":
            return scalar
        return float(1.0 / (1.0 + np.exp(-scalar)))

    if squeezed.ndim == 1:
        if squeezed.size == 1:
            scalar = float(squeezed[0])
            if scalar_mode == "probability":
                return scalar
            return float(1.0 / (1.0 + np.exp(-scalar)))

        if squeezed.size == 2:
            if (
                scalar_mode == "probabilities"
                and np.all((squeezed >= 0.0) & (squeezed <= 1.0))
                and np.isclose(squeezed.sum(), 1.0, atol=1e-3)
            ):
                return float(squeezed[1])
            logits = squeezed - np.max(squeezed)
            probs = np.exp(logits)
            probs = probs / probs.sum()
            return float(probs[1])

    if squeezed.ndim == 2 and squeezed.shape[0] >= 1:
        return _extract_probability_up(squeezed[0])

    raise InferenceNotReadyError(f"Unsupported model output shape for binary inference: {output_array.shape}")


def run_inference(model: LoadedModel, prepared_input: PreparedInferenceInput, settings: AppSettings | None = None) -> tuple[int, float]:
    resolved_settings = settings or load_settings()

    try:
        import torch
    except ModuleNotFoundError as exc:
        raise InferenceNotReadyError("PyTorch runtime is unavailable in this environment") from exc

    device = torch.device(resolved_settings.inference_device)
    input_tensor = torch.from_numpy(prepared_input.model_input).to(device)

    try:
        with torch.no_grad():
            raw_output = model.model(input_tensor)
    except Exception as exc:
        raise InferenceNotReadyError(f"Model forward pass failed: {exc}") from exc

    probability_up = _extract_probability_up(raw_output)
    probability_up = max(0.0, min(1.0, probability_up))
    prediction_class = 1 if probability_up >= resolved_settings.inference_probability_threshold else 0
    return prediction_class, probability_up
