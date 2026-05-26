from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import os
from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SETTINGS_PATH = PROJECT_ROOT / "config" / "settings.yaml"
DOTENV_PATH = PROJECT_ROOT / ".env"


@dataclass(frozen=True)
class ExecutionSettings:
    enabled: bool
    mode: str
    symbol: str
    market_type: str
    order_type: str
    allow_long: bool
    allow_short: bool
    leverage: int
    max_open_positions: int
    fixed_order_usdt: float
    cooldown_minutes: int
    prevent_duplicate_signal_execution: bool
    close_opposite_before_flip: bool
    require_signal_freshness: bool
    max_signal_age_minutes: int
    dry_run_logging: bool


@dataclass(frozen=True)
class StrategySettings:
    version: str
    buy_signal_threshold: float
    sell_signal_threshold: float
    entry_long_threshold: float
    entry_short_threshold: float
    strong_buy_threshold: float
    strong_sell_threshold: float
    use_trend_filter: bool
    use_volatility_filter: bool
    use_volume_filter: bool
    use_momentum_filter: bool
    require_trend_alignment_for_weak_signals: bool
    allow_counter_trend_on_strong_signal: bool
    min_atr_14_pct: float
    min_volume_ma_ratio_20: float
    min_turnover_ma_ratio_20: float
    min_signal_persistence_bars: int
    flip_noise_guard_enabled: bool


@dataclass(frozen=True)
class RiskSettings:
    version: str
    max_open_positions: int
    max_total_open_notional_usdt: float
    fixed_order_usdt: float
    min_order_notional_usdt: float
    max_order_notional_usdt: float
    min_risk_budget_usdt: float
    max_risk_budget_usdt: float
    default_leverage: int
    max_allowed_leverage: int
    min_dynamic_leverage: int
    max_dynamic_leverage: int
    require_fresh_strategy: bool
    max_strategy_age_minutes: int
    enable_cooldown: bool
    cooldown_minutes: int
    enable_daily_loss_lock: bool
    max_daily_realized_loss_usdt: float
    enable_consecutive_loss_pause: bool
    max_consecutive_losses: int
    stop_loss_mode: str
    take_profit_mode: str
    stop_loss_atr_multiple: float
    take_profit_atr_multiple: float
    fallback_stop_loss_pct: float
    fallback_take_profit_pct: float


@dataclass(frozen=True)
class AutomationSettings:
    version: str
    enabled: bool
    dry_run: bool
    run_execution_step: bool
    auto_execute_demo_orders: bool
    require_completed_bar: bool
    allow_reprocess_latest_bar: bool
    max_cycle_delay_seconds: int
    pause_on_stage_failure: bool


@dataclass(frozen=True)
class PositionManagementSettings:
    version: str
    enabled: bool
    evaluate_each_cycle: bool
    enable_stop_loss_exit: bool
    enable_take_profit_exit: bool
    enable_max_holding_exit: bool
    enable_opposite_signal_exit: bool
    max_holding_minutes: int
    require_strong_opposite_signal_for_exit: bool
    opposite_signal_confidence_threshold_long_exit: float
    opposite_signal_confidence_threshold_short_exit: float
    close_positions_via_demo_execution: bool


@dataclass(frozen=True)
class ReconciliationSettings:
    version: str
    enabled: bool
    run_on_startup: bool
    run_pre_execution_check: bool
    run_post_cycle_check: bool
    block_on_mismatch: bool
    size_tolerance_ratio: float
    size_tolerance_min_qty: float


@dataclass(frozen=True)
class AppSettings:
    project_root: Path
    exchange: str
    symbol: str
    timeframe: str
    raw_dir: Path
    processed_dir: Path
    features_dir: Path
    labeled_dir: Path
    splits_dir: Path
    windows_dir: Path
    normalized_dir: Path
    inference_dir: Path
    signals_dir: Path
    strategy_dir: Path
    risk_dir: Path
    automation_dir: Path
    position_management_dir: Path
    reconciliation_dir: Path
    execution_dir: Path
    bybit_api_key: str | None
    bybit_api_secret: str | None
    bybit_use_testnet: bool
    bybit_private_api_ready: bool
    bybit_demo_api_key: str | None
    bybit_demo_api_secret: str | None
    bybit_use_demo_trading: bool
    bybit_demo_base_url: str
    inference_model_path: Path | None
    inference_scaler_stats_path: Path | None
    inference_window_size: int
    inference_device: str
    inference_model_type: str
    inference_probability_threshold: float
    inference_input_layout: str
    inference_max_gap_minutes: int
    inference_allow_unsafe_deserialization: bool
    live_updates_enabled: bool
    live_update_poll_seconds: int
    live_update_lag_seconds: int
    strategy: StrategySettings
    risk: RiskSettings
    automation: AutomationSettings
    position_management: PositionManagementSettings
    reconciliation: ReconciliationSettings
    execution: ExecutionSettings


def _parse_bool(value: object, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value

    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return default


def _load_dotenv(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}

    values: dict[str, str] = {}
    with path.open("r", encoding="utf-8") as file:
        for raw_line in file:
            line = raw_line.strip()
            if line == "" or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            if key == "":
                continue

            if (value.startswith('"') and value.endswith('"')) or (
                value.startswith("'") and value.endswith("'")
            ):
                value = value[1:-1]

            values[key] = value

    return values


def _env_value(key: str, dotenv_values: dict[str, str]) -> str | None:
    value = os.environ.get(key)
    if value is not None:
        stripped = value.strip()
        return stripped if stripped != "" else None

    dotenv_value = dotenv_values.get(key)
    if dotenv_value is None:
        return None

    stripped_dotenv = dotenv_value.strip()
    return stripped_dotenv if stripped_dotenv != "" else None


def _parse_int(value: object, default: int, *, minimum: int, field_name: str) -> int:
    if value is None:
        return default

    try:
        parsed = int(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid integer value for '{field_name}': {value}") from exc

    if parsed < minimum:
        raise ValueError(f"'{field_name}' must be >= {minimum}, got {parsed}")
    return parsed


def _parse_float(
    value: object,
    default: float,
    *,
    minimum: float,
    maximum: float,
    field_name: str,
) -> float:
    if value is None:
        return default

    try:
        parsed = float(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid float value for '{field_name}': {value}") from exc

    if parsed < minimum or parsed > maximum:
        raise ValueError(f"'{field_name}' must be between {minimum} and {maximum}, got {parsed}")
    return parsed


def _optional_path_from_string(project_root: Path, raw_value: object) -> Path | None:
    if raw_value is None:
        return None
    if not isinstance(raw_value, str):
        raise ValueError(f"Expected path string, got {type(raw_value).__name__}")

    trimmed = raw_value.strip()
    if trimmed == "":
        return None

    path = Path(trimmed)
    if path.is_absolute():
        return path
    return project_root / path


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Settings file not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        content = yaml.safe_load(file)

    if content is None:
        return {}
    if not isinstance(content, dict):
        raise ValueError(f"Settings YAML must be a mapping: {path}")
    return content


def _path_from_data_config(project_root: Path, data_cfg: dict[str, Any], key: str, default: str) -> Path:
    raw_value = data_cfg.get(key, default)
    if not isinstance(raw_value, str) or raw_value.strip() == "":
        raise ValueError(f"Invalid data path setting '{key}': {raw_value}")
    return project_root / Path(raw_value)


@lru_cache(maxsize=1)
def load_settings() -> AppSettings:
    payload = _read_yaml(SETTINGS_PATH)
    dotenv_values = _load_dotenv(DOTENV_PATH)
    data_cfg = payload.get("data", {})
    if not isinstance(data_cfg, dict):
        raise ValueError("'data' section in config/settings.yaml must be a mapping")

    symbol = payload.get("symbol")
    timeframe = payload.get("timeframe")
    if not isinstance(symbol, str) or symbol.strip() == "":
        raise ValueError("Missing or invalid 'symbol' in config/settings.yaml")
    if not isinstance(timeframe, str) or timeframe.strip() == "":
        raise ValueError("Missing or invalid 'timeframe' in config/settings.yaml")

    exchange = payload.get("exchange", "bybit")
    if not isinstance(exchange, str) or exchange.strip() == "":
        raise ValueError("Missing or invalid 'exchange' in config/settings.yaml")

    inference_cfg = payload.get("inference", {})
    if inference_cfg is None:
        inference_cfg = {}
    if not isinstance(inference_cfg, dict):
        raise ValueError("'inference' section in config/settings.yaml must be a mapping")

    live_updates_cfg = payload.get("live_updates", {})
    if live_updates_cfg is None:
        live_updates_cfg = {}
    if not isinstance(live_updates_cfg, dict):
        raise ValueError("'live_updates' section in config/settings.yaml must be a mapping")

    execution_cfg = payload.get("execution", {})
    if execution_cfg is None:
        execution_cfg = {}
    if not isinstance(execution_cfg, dict):
        raise ValueError("'execution' section in config/settings.yaml must be a mapping")

    strategy_cfg = payload.get("strategy", {})
    if strategy_cfg is None:
        strategy_cfg = {}
    if not isinstance(strategy_cfg, dict):
        raise ValueError("'strategy' section in config/settings.yaml must be a mapping")

    risk_cfg = payload.get("risk", {})
    if risk_cfg is None:
        risk_cfg = {}
    if not isinstance(risk_cfg, dict):
        raise ValueError("'risk' section in config/settings.yaml must be a mapping")

    automation_cfg = payload.get("automation", {})
    if automation_cfg is None:
        automation_cfg = {}
    if not isinstance(automation_cfg, dict):
        raise ValueError("'automation' section in config/settings.yaml must be a mapping")

    position_management_cfg = payload.get("position_management", {})
    if position_management_cfg is None:
        position_management_cfg = {}
    if not isinstance(position_management_cfg, dict):
        raise ValueError("'position_management' section in config/settings.yaml must be a mapping")

    reconciliation_cfg = payload.get("reconciliation", {})
    if reconciliation_cfg is None:
        reconciliation_cfg = {}
    if not isinstance(reconciliation_cfg, dict):
        raise ValueError("'reconciliation' section in config/settings.yaml must be a mapping")

    bybit_api_key = _env_value("BYBIT_API_KEY", dotenv_values)
    bybit_api_secret = _env_value("BYBIT_API_SECRET", dotenv_values)
    bybit_use_testnet = _parse_bool(_env_value("BYBIT_USE_TESTNET", dotenv_values), default=False)
    bybit_private_api_ready = _parse_bool(
        _env_value("BYBIT_PRIVATE_API_READY", dotenv_values),
        default=False,
    )
    bybit_demo_api_key = _env_value("BYBIT_DEMO_API_KEY", dotenv_values)
    bybit_demo_api_secret = _env_value("BYBIT_DEMO_API_SECRET", dotenv_values)
    bybit_use_demo_trading = _parse_bool(
        _env_value("BYBIT_USE_DEMO_TRADING", dotenv_values),
        default=True,
    )
    bybit_demo_base_url = (
        _env_value("BYBIT_DEMO_BASE_URL", dotenv_values) or "https://api-demo.bybit.com"
    )

    inference_model_path = _optional_path_from_string(
        PROJECT_ROOT,
        _env_value("INFERENCE_MODEL_PATH", dotenv_values) or inference_cfg.get("model_path"),
    )
    inference_scaler_stats_path = _optional_path_from_string(
        PROJECT_ROOT,
        _env_value("INFERENCE_SCALER_STATS_PATH", dotenv_values)
        or inference_cfg.get("scaler_stats_path"),
    )

    inference_window_size = _parse_int(
        _env_value("INFERENCE_WINDOW_SIZE", dotenv_values) or inference_cfg.get("window_size"),
        default=256,
        minimum=1,
        field_name="INFERENCE_WINDOW_SIZE",
    )
    inference_model_type_value = _env_value("INFERENCE_MODEL_TYPE", dotenv_values)
    if inference_model_type_value is None:
        cfg_model_type = inference_cfg.get("model_type", "tcn")
        inference_model_type_value = "tcn" if cfg_model_type is None else str(cfg_model_type)

    inference_model_type = inference_model_type_value.strip().lower()
    if inference_model_type == "":
        inference_model_type = "tcn"

    inference_probability_threshold = _parse_float(
        _env_value("INFERENCE_PROBABILITY_THRESHOLD", dotenv_values)
        or inference_cfg.get("probability_threshold"),
        default=0.5,
        minimum=0.0,
        maximum=1.0,
        field_name="INFERENCE_PROBABILITY_THRESHOLD",
    )

    inference_max_gap_minutes = _parse_int(
        _env_value("INFERENCE_MAX_GAP_MINUTES", dotenv_values)
        or inference_cfg.get("max_gap_minutes"),
        default=120,
        minimum=1,
        field_name="INFERENCE_MAX_GAP_MINUTES",
    )
    inference_allow_unsafe_deserialization = _parse_bool(
        _env_value("INFERENCE_ALLOW_UNSAFE_DESERIALIZATION", dotenv_values)
        or inference_cfg.get("allow_unsafe_deserialization"),
        default=False,
    )

    live_updates_enabled = _parse_bool(
        _env_value("LIVE_UPDATES_ENABLED", dotenv_values) or live_updates_cfg.get("enabled"),
        default=True,
    )
    live_update_poll_seconds = _parse_int(
        _env_value("LIVE_UPDATE_POLL_SECONDS", dotenv_values) or live_updates_cfg.get("poll_seconds"),
        default=30,
        minimum=5,
        field_name="LIVE_UPDATE_POLL_SECONDS",
    )
    live_update_lag_seconds = _parse_int(
        _env_value("LIVE_UPDATE_LAG_SECONDS", dotenv_values) or live_updates_cfg.get("lag_seconds"),
        default=90,
        minimum=0,
        field_name="LIVE_UPDATE_LAG_SECONDS",
    )

    strategy_buy_signal_threshold = _parse_float(
        strategy_cfg.get("buy_signal_threshold"),
        default=0.55,
        minimum=0.0,
        maximum=1.0,
        field_name="strategy.buy_signal_threshold",
    )
    strategy_sell_signal_threshold = _parse_float(
        strategy_cfg.get("sell_signal_threshold"),
        default=0.45,
        minimum=0.0,
        maximum=1.0,
        field_name="strategy.sell_signal_threshold",
    )
    strategy_entry_long_threshold = _parse_float(
        strategy_cfg.get("entry_long_threshold"),
        default=0.58,
        minimum=0.0,
        maximum=1.0,
        field_name="strategy.entry_long_threshold",
    )
    strategy_entry_short_threshold = _parse_float(
        strategy_cfg.get("entry_short_threshold"),
        default=0.42,
        minimum=0.0,
        maximum=1.0,
        field_name="strategy.entry_short_threshold",
    )
    strategy_strong_buy_threshold = _parse_float(
        strategy_cfg.get("strong_buy_threshold"),
        default=0.70,
        minimum=0.0,
        maximum=1.0,
        field_name="strategy.strong_buy_threshold",
    )
    strategy_strong_sell_threshold = _parse_float(
        strategy_cfg.get("strong_sell_threshold"),
        default=0.30,
        minimum=0.0,
        maximum=1.0,
        field_name="strategy.strong_sell_threshold",
    )
    strategy_min_atr_14_pct = _parse_float(
        strategy_cfg.get("min_atr_14_pct"),
        default=0.001,
        minimum=0.0,
        maximum=1.0,
        field_name="strategy.min_atr_14_pct",
    )
    strategy_min_volume_ma_ratio_20 = _parse_float(
        strategy_cfg.get("min_volume_ma_ratio_20"),
        default=0.8,
        minimum=0.0,
        maximum=1000.0,
        field_name="strategy.min_volume_ma_ratio_20",
    )
    strategy_min_turnover_ma_ratio_20 = _parse_float(
        strategy_cfg.get("min_turnover_ma_ratio_20"),
        default=0.8,
        minimum=0.0,
        maximum=1000.0,
        field_name="strategy.min_turnover_ma_ratio_20",
    )
    strategy_min_signal_persistence_bars = _parse_int(
        strategy_cfg.get("min_signal_persistence_bars"),
        default=1,
        minimum=1,
        field_name="strategy.min_signal_persistence_bars",
    )

    if strategy_sell_signal_threshold >= strategy_buy_signal_threshold:
        raise ValueError("strategy.sell_signal_threshold must be less than strategy.buy_signal_threshold")
    if strategy_entry_short_threshold >= strategy_entry_long_threshold:
        raise ValueError("strategy.entry_short_threshold must be less than strategy.entry_long_threshold")
    if strategy_strong_sell_threshold >= strategy_entry_short_threshold:
        raise ValueError("strategy.strong_sell_threshold must be less than strategy.entry_short_threshold")
    if strategy_strong_buy_threshold <= strategy_entry_long_threshold:
        raise ValueError("strategy.strong_buy_threshold must be greater than strategy.entry_long_threshold")

    strategy_settings = StrategySettings(
        version=str(strategy_cfg.get("version", "v1")).strip() or "v1",
        buy_signal_threshold=strategy_buy_signal_threshold,
        sell_signal_threshold=strategy_sell_signal_threshold,
        entry_long_threshold=strategy_entry_long_threshold,
        entry_short_threshold=strategy_entry_short_threshold,
        strong_buy_threshold=strategy_strong_buy_threshold,
        strong_sell_threshold=strategy_strong_sell_threshold,
        use_trend_filter=_parse_bool(strategy_cfg.get("use_trend_filter"), default=True),
        use_volatility_filter=_parse_bool(strategy_cfg.get("use_volatility_filter"), default=True),
        use_volume_filter=_parse_bool(strategy_cfg.get("use_volume_filter"), default=True),
        use_momentum_filter=_parse_bool(strategy_cfg.get("use_momentum_filter"), default=True),
        require_trend_alignment_for_weak_signals=_parse_bool(
            strategy_cfg.get("require_trend_alignment_for_weak_signals"),
            default=True,
        ),
        allow_counter_trend_on_strong_signal=_parse_bool(
            strategy_cfg.get("allow_counter_trend_on_strong_signal"),
            default=True,
        ),
        min_atr_14_pct=strategy_min_atr_14_pct,
        min_volume_ma_ratio_20=strategy_min_volume_ma_ratio_20,
        min_turnover_ma_ratio_20=strategy_min_turnover_ma_ratio_20,
        min_signal_persistence_bars=strategy_min_signal_persistence_bars,
        flip_noise_guard_enabled=_parse_bool(
            strategy_cfg.get("flip_noise_guard_enabled"),
            default=True,
        ),
    )

    risk_max_open_positions = _parse_int(
        risk_cfg.get("max_open_positions"),
        default=2,
        minimum=1,
        field_name="risk.max_open_positions",
    )
    risk_max_total_open_notional_usdt = _parse_float(
        risk_cfg.get("max_total_open_notional_usdt"),
        default=20.0,
        minimum=0.0001,
        maximum=1_000_000.0,
        field_name="risk.max_total_open_notional_usdt",
    )
    risk_fixed_order_usdt = _parse_float(
        risk_cfg.get("fixed_order_usdt"),
        default=10.0,
        minimum=0.0001,
        maximum=1_000_000.0,
        field_name="risk.fixed_order_usdt",
    )
    risk_min_order_notional_usdt = _parse_float(
        risk_cfg.get("min_order_notional_usdt"),
        default=75.0,
        minimum=0.0001,
        maximum=1_000_000.0,
        field_name="risk.min_order_notional_usdt",
    )
    risk_max_order_notional_usdt = _parse_float(
        risk_cfg.get("max_order_notional_usdt"),
        default=600.0,
        minimum=0.0001,
        maximum=1_000_000.0,
        field_name="risk.max_order_notional_usdt",
    )
    risk_min_risk_budget_usdt = _parse_float(
        risk_cfg.get("min_risk_budget_usdt"),
        default=1.5,
        minimum=0.0001,
        maximum=1_000_000.0,
        field_name="risk.min_risk_budget_usdt",
    )
    risk_max_risk_budget_usdt = _parse_float(
        risk_cfg.get("max_risk_budget_usdt"),
        default=6.0,
        minimum=0.0001,
        maximum=1_000_000.0,
        field_name="risk.max_risk_budget_usdt",
    )
    risk_default_leverage = _parse_int(
        risk_cfg.get("default_leverage"),
        default=2,
        minimum=1,
        field_name="risk.default_leverage",
    )
    risk_max_allowed_leverage = _parse_int(
        risk_cfg.get("max_allowed_leverage"),
        default=3,
        minimum=1,
        field_name="risk.max_allowed_leverage",
    )
    risk_min_dynamic_leverage = _parse_int(
        risk_cfg.get("min_dynamic_leverage"),
        default=2,
        minimum=1,
        field_name="risk.min_dynamic_leverage",
    )
    risk_max_dynamic_leverage = _parse_int(
        risk_cfg.get("max_dynamic_leverage"),
        default=20,
        minimum=1,
        field_name="risk.max_dynamic_leverage",
    )
    risk_max_strategy_age_minutes = _parse_int(
        risk_cfg.get("max_strategy_age_minutes"),
        default=20,
        minimum=1,
        field_name="risk.max_strategy_age_minutes",
    )
    risk_cooldown_minutes = _parse_int(
        risk_cfg.get("cooldown_minutes"),
        default=15,
        minimum=0,
        field_name="risk.cooldown_minutes",
    )
    risk_max_daily_realized_loss_usdt = _parse_float(
        risk_cfg.get("max_daily_realized_loss_usdt"),
        default=20.0,
        minimum=0.0,
        maximum=1_000_000.0,
        field_name="risk.max_daily_realized_loss_usdt",
    )
    risk_max_consecutive_losses = _parse_int(
        risk_cfg.get("max_consecutive_losses"),
        default=3,
        minimum=1,
        field_name="risk.max_consecutive_losses",
    )
    risk_stop_loss_atr_multiple = _parse_float(
        risk_cfg.get("stop_loss_atr_multiple"),
        default=1.0,
        minimum=0.0,
        maximum=100.0,
        field_name="risk.stop_loss_atr_multiple",
    )
    risk_take_profit_atr_multiple = _parse_float(
        risk_cfg.get("take_profit_atr_multiple"),
        default=1.5,
        minimum=0.0,
        maximum=100.0,
        field_name="risk.take_profit_atr_multiple",
    )
    risk_fallback_stop_loss_pct = _parse_float(
        risk_cfg.get("fallback_stop_loss_pct"),
        default=0.01,
        minimum=0.0,
        maximum=1.0,
        field_name="risk.fallback_stop_loss_pct",
    )
    risk_fallback_take_profit_pct = _parse_float(
        risk_cfg.get("fallback_take_profit_pct"),
        default=0.015,
        minimum=0.0,
        maximum=1.0,
        field_name="risk.fallback_take_profit_pct",
    )

    if risk_default_leverage > risk_max_allowed_leverage:
        raise ValueError("risk.default_leverage must be <= risk.max_allowed_leverage")
    if risk_min_order_notional_usdt > risk_max_order_notional_usdt:
        raise ValueError("risk.min_order_notional_usdt must be <= risk.max_order_notional_usdt")
    if risk_max_total_open_notional_usdt < risk_min_order_notional_usdt:
        raise ValueError("risk.max_total_open_notional_usdt must be >= risk.min_order_notional_usdt")
    if risk_min_risk_budget_usdt > risk_max_risk_budget_usdt:
        raise ValueError("risk.min_risk_budget_usdt must be <= risk.max_risk_budget_usdt")
    if risk_min_dynamic_leverage > risk_max_dynamic_leverage:
        raise ValueError("risk.min_dynamic_leverage must be <= risk.max_dynamic_leverage")
    if risk_max_dynamic_leverage > risk_max_allowed_leverage:
        raise ValueError("risk.max_dynamic_leverage must be <= risk.max_allowed_leverage")
    if risk_default_leverage < risk_min_dynamic_leverage:
        raise ValueError("risk.default_leverage must be >= risk.min_dynamic_leverage")

    risk_settings = RiskSettings(
        version=str(risk_cfg.get("version", "v1")).strip() or "v1",
        max_open_positions=risk_max_open_positions,
        max_total_open_notional_usdt=risk_max_total_open_notional_usdt,
        fixed_order_usdt=risk_fixed_order_usdt,
        min_order_notional_usdt=risk_min_order_notional_usdt,
        max_order_notional_usdt=risk_max_order_notional_usdt,
        min_risk_budget_usdt=risk_min_risk_budget_usdt,
        max_risk_budget_usdt=risk_max_risk_budget_usdt,
        default_leverage=risk_default_leverage,
        max_allowed_leverage=risk_max_allowed_leverage,
        min_dynamic_leverage=risk_min_dynamic_leverage,
        max_dynamic_leverage=risk_max_dynamic_leverage,
        require_fresh_strategy=_parse_bool(risk_cfg.get("require_fresh_strategy"), default=True),
        max_strategy_age_minutes=risk_max_strategy_age_minutes,
        enable_cooldown=_parse_bool(risk_cfg.get("enable_cooldown"), default=True),
        cooldown_minutes=risk_cooldown_minutes,
        enable_daily_loss_lock=_parse_bool(risk_cfg.get("enable_daily_loss_lock"), default=True),
        max_daily_realized_loss_usdt=risk_max_daily_realized_loss_usdt,
        enable_consecutive_loss_pause=_parse_bool(
            risk_cfg.get("enable_consecutive_loss_pause"),
            default=True,
        ),
        max_consecutive_losses=risk_max_consecutive_losses,
        stop_loss_mode=str(risk_cfg.get("stop_loss_mode", "atr")).strip().lower() or "atr",
        take_profit_mode=str(risk_cfg.get("take_profit_mode", "atr")).strip().lower() or "atr",
        stop_loss_atr_multiple=risk_stop_loss_atr_multiple,
        take_profit_atr_multiple=risk_take_profit_atr_multiple,
        fallback_stop_loss_pct=risk_fallback_stop_loss_pct,
        fallback_take_profit_pct=risk_fallback_take_profit_pct,
    )

    automation_settings = AutomationSettings(
        version=str(automation_cfg.get("version", "v1")).strip() or "v1",
        enabled=_parse_bool(automation_cfg.get("enabled"), default=True),
        dry_run=_parse_bool(automation_cfg.get("dry_run"), default=True),
        run_execution_step=_parse_bool(automation_cfg.get("run_execution_step"), default=True),
        auto_execute_demo_orders=_parse_bool(
            automation_cfg.get("auto_execute_demo_orders"),
            default=False,
        ),
        require_completed_bar=_parse_bool(automation_cfg.get("require_completed_bar"), default=True),
        allow_reprocess_latest_bar=_parse_bool(
            automation_cfg.get("allow_reprocess_latest_bar"),
            default=False,
        ),
        max_cycle_delay_seconds=_parse_int(
            automation_cfg.get("max_cycle_delay_seconds"),
            default=90,
            minimum=0,
            field_name="automation.max_cycle_delay_seconds",
        ),
        pause_on_stage_failure=_parse_bool(
            automation_cfg.get("pause_on_stage_failure"),
            default=False,
        ),
    )

    position_management_settings = PositionManagementSettings(
        version=str(position_management_cfg.get("version", "v1")).strip() or "v1",
        enabled=_parse_bool(position_management_cfg.get("enabled"), default=True),
        evaluate_each_cycle=_parse_bool(position_management_cfg.get("evaluate_each_cycle"), default=True),
        enable_stop_loss_exit=_parse_bool(
            position_management_cfg.get("enable_stop_loss_exit"),
            default=True,
        ),
        enable_take_profit_exit=_parse_bool(
            position_management_cfg.get("enable_take_profit_exit"),
            default=True,
        ),
        enable_max_holding_exit=_parse_bool(
            position_management_cfg.get("enable_max_holding_exit"),
            default=True,
        ),
        enable_opposite_signal_exit=_parse_bool(
            position_management_cfg.get("enable_opposite_signal_exit"),
            default=True,
        ),
        max_holding_minutes=_parse_int(
            position_management_cfg.get("max_holding_minutes"),
            default=240,
            minimum=1,
            field_name="position_management.max_holding_minutes",
        ),
        require_strong_opposite_signal_for_exit=_parse_bool(
            position_management_cfg.get("require_strong_opposite_signal_for_exit"),
            default=True,
        ),
        opposite_signal_confidence_threshold_long_exit=_parse_float(
            position_management_cfg.get("opposite_signal_confidence_threshold_long_exit"),
            default=0.40,
            minimum=0.0,
            maximum=1.0,
            field_name="position_management.opposite_signal_confidence_threshold_long_exit",
        ),
        opposite_signal_confidence_threshold_short_exit=_parse_float(
            position_management_cfg.get("opposite_signal_confidence_threshold_short_exit"),
            default=0.60,
            minimum=0.0,
            maximum=1.0,
            field_name="position_management.opposite_signal_confidence_threshold_short_exit",
        ),
        close_positions_via_demo_execution=_parse_bool(
            position_management_cfg.get("close_positions_via_demo_execution"),
            default=False,
        ),
    )

    reconciliation_settings = ReconciliationSettings(
        version=str(reconciliation_cfg.get("version", "v1")).strip() or "v1",
        enabled=_parse_bool(reconciliation_cfg.get("enabled"), default=True),
        run_on_startup=_parse_bool(reconciliation_cfg.get("run_on_startup"), default=True),
        run_pre_execution_check=_parse_bool(
            reconciliation_cfg.get("run_pre_execution_check"),
            default=True,
        ),
        run_post_cycle_check=_parse_bool(
            reconciliation_cfg.get("run_post_cycle_check"),
            default=True,
        ),
        block_on_mismatch=_parse_bool(reconciliation_cfg.get("block_on_mismatch"), default=True),
        size_tolerance_ratio=_parse_float(
            reconciliation_cfg.get("size_tolerance_ratio"),
            default=0.05,
            minimum=0.0,
            maximum=1.0,
            field_name="reconciliation.size_tolerance_ratio",
        ),
        size_tolerance_min_qty=_parse_float(
            reconciliation_cfg.get("size_tolerance_min_qty"),
            default=0.00001,
            minimum=0.0,
            maximum=1_000_000.0,
            field_name="reconciliation.size_tolerance_min_qty",
        ),
    )

    execution_leverage = _parse_int(
        execution_cfg.get("leverage"),
        default=2,
        minimum=1,
        field_name="execution.leverage",
    )
    execution_max_open_positions = _parse_int(
        execution_cfg.get("max_open_positions"),
        default=2,
        minimum=1,
        field_name="execution.max_open_positions",
    )
    execution_cooldown_minutes = _parse_int(
        execution_cfg.get("cooldown_minutes"),
        default=0,
        minimum=0,
        field_name="execution.cooldown_minutes",
    )
    execution_max_signal_age_minutes = _parse_int(
        execution_cfg.get("max_signal_age_minutes"),
        default=20,
        minimum=1,
        field_name="execution.max_signal_age_minutes",
    )
    execution_fixed_order_usdt = _parse_float(
        execution_cfg.get("fixed_order_usdt"),
        default=10.0,
        minimum=0.0001,
        maximum=1_000_000.0,
        field_name="execution.fixed_order_usdt",
    )

    execution_mode = str(execution_cfg.get("mode", "demo")).strip().lower() or "demo"
    execution_symbol = str(execution_cfg.get("symbol", symbol)).strip().upper() or symbol
    execution_market_type = str(execution_cfg.get("market_type", "linear")).strip().lower() or "linear"
    execution_order_type = str(execution_cfg.get("order_type", "market")).strip().lower() or "market"

    execution_settings = ExecutionSettings(
        enabled=_parse_bool(execution_cfg.get("enabled"), default=False),
        mode=execution_mode,
        symbol=execution_symbol,
        market_type=execution_market_type,
        order_type=execution_order_type,
        allow_long=_parse_bool(execution_cfg.get("allow_long"), default=True),
        allow_short=_parse_bool(execution_cfg.get("allow_short"), default=True),
        leverage=execution_leverage,
        max_open_positions=execution_max_open_positions,
        fixed_order_usdt=execution_fixed_order_usdt,
        cooldown_minutes=execution_cooldown_minutes,
        prevent_duplicate_signal_execution=_parse_bool(
            execution_cfg.get("prevent_duplicate_signal_execution"),
            default=True,
        ),
        close_opposite_before_flip=_parse_bool(
            execution_cfg.get("close_opposite_before_flip"),
            default=True,
        ),
        require_signal_freshness=_parse_bool(
            execution_cfg.get("require_signal_freshness"),
            default=True,
        ),
        max_signal_age_minutes=execution_max_signal_age_minutes,
        dry_run_logging=_parse_bool(execution_cfg.get("dry_run_logging"), default=True),
    )

    inference_device_value = _env_value("INFERENCE_DEVICE", dotenv_values)
    if inference_device_value is None:
        cfg_device = inference_cfg.get("device", "cpu")
        inference_device_value = "cpu" if cfg_device is None else str(cfg_device)

    inference_device = inference_device_value.strip()
    if inference_device == "":
        inference_device = "cpu"

    inference_input_layout_value = _env_value("INFERENCE_INPUT_LAYOUT", dotenv_values)
    if inference_input_layout_value is None:
        cfg_layout = inference_cfg.get("input_layout")
        if cfg_layout is None:
            inference_input_layout_value = (
                "batch_feature_window" if inference_model_type == "tcn" else "batch_window_feature"
            )
        else:
            inference_input_layout_value = str(cfg_layout)

    inference_input_layout = inference_input_layout_value.strip()
    if inference_input_layout not in {"batch_window_feature", "batch_feature_window"}:
        raise ValueError(
            "INFERENCE_INPUT_LAYOUT must be 'batch_window_feature' or 'batch_feature_window'"
        )

    return AppSettings(
        project_root=PROJECT_ROOT,
        exchange=exchange,
        symbol=symbol,
        timeframe=timeframe,
        raw_dir=_path_from_data_config(PROJECT_ROOT, data_cfg, "raw_dir", "data/raw"),
        processed_dir=_path_from_data_config(PROJECT_ROOT, data_cfg, "processed_dir", "data/processed"),
        features_dir=_path_from_data_config(PROJECT_ROOT, data_cfg, "features_dir", "data/features"),
        labeled_dir=_path_from_data_config(PROJECT_ROOT, data_cfg, "labeled_dir", "data/labeled"),
        splits_dir=_path_from_data_config(PROJECT_ROOT, data_cfg, "splits_dir", "data/splits"),
        windows_dir=_path_from_data_config(PROJECT_ROOT, data_cfg, "windows_dir", "data/windows"),
        normalized_dir=_path_from_data_config(PROJECT_ROOT, data_cfg, "normalized_dir", "data/normalized"),
        inference_dir=_path_from_data_config(PROJECT_ROOT, data_cfg, "inference_dir", "data/inference"),
        signals_dir=_path_from_data_config(PROJECT_ROOT, data_cfg, "signals_dir", "data/signals"),
        strategy_dir=_path_from_data_config(PROJECT_ROOT, data_cfg, "strategy_dir", "data/strategy"),
        risk_dir=_path_from_data_config(PROJECT_ROOT, data_cfg, "risk_dir", "data/risk"),
        automation_dir=_path_from_data_config(PROJECT_ROOT, data_cfg, "automation_dir", "data/automation"),
        position_management_dir=_path_from_data_config(
            PROJECT_ROOT,
            data_cfg,
            "position_management_dir",
            "data/position_management",
        ),
        reconciliation_dir=_path_from_data_config(
            PROJECT_ROOT,
            data_cfg,
            "reconciliation_dir",
            "data/reconciliation",
        ),
        execution_dir=_path_from_data_config(PROJECT_ROOT, data_cfg, "execution_dir", "data/execution"),
        bybit_api_key=bybit_api_key,
        bybit_api_secret=bybit_api_secret,
        bybit_use_testnet=bybit_use_testnet,
        bybit_private_api_ready=bybit_private_api_ready,
        bybit_demo_api_key=bybit_demo_api_key,
        bybit_demo_api_secret=bybit_demo_api_secret,
        bybit_use_demo_trading=bybit_use_demo_trading,
        bybit_demo_base_url=bybit_demo_base_url,
        inference_model_path=inference_model_path,
        inference_scaler_stats_path=inference_scaler_stats_path,
        inference_window_size=inference_window_size,
        inference_device=inference_device,
        inference_model_type=inference_model_type,
        inference_probability_threshold=inference_probability_threshold,
        inference_input_layout=inference_input_layout,
        inference_max_gap_minutes=inference_max_gap_minutes,
        inference_allow_unsafe_deserialization=inference_allow_unsafe_deserialization,
        live_updates_enabled=live_updates_enabled,
        live_update_poll_seconds=live_update_poll_seconds,
        live_update_lag_seconds=live_update_lag_seconds,
        strategy=strategy_settings,
        risk=risk_settings,
        automation=automation_settings,
        position_management=position_management_settings,
        reconciliation=reconciliation_settings,
        execution=execution_settings,
    )


def to_repo_relative(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)
