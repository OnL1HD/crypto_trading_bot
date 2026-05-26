from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src.core.settings import AppSettings, load_settings, to_repo_relative
from src.schemas.risk import RiskDecisionRecord, RiskHistoryResponse


RISK_LOG_COLUMNS = [
    'decided_at',
    'source_timestamp',
    'predicted_for_timestamp',
    'requested_action',
    'approved_action',
    'allowed',
    'order_notional_usdt',
    'approved_leverage',
    'conviction_score',
    'risk_budget_usdt',
    'stop_distance_pct',
    'volatility_penalty_multiplier',
    'stop_loss',
    'take_profit',
    'reason_codes',
    'size_reason',
    'leverage_reason',
    'signal_type',
    'probability_up',
    'strategy_version',
    'risk_version',
]


def _risk_log_path(settings: AppSettings) -> Path:
    return settings.risk_dir / f'{settings.symbol}_{settings.timeframe}_risk_history.parquet'


def _empty_risk_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=RISK_LOG_COLUMNS)


def _coerce_risk_frame(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.copy()
    for column in RISK_LOG_COLUMNS:
        if column not in normalized.columns:
            normalized[column] = None

    normalized = normalized[RISK_LOG_COLUMNS]
    for column in ('decided_at', 'source_timestamp', 'predicted_for_timestamp'):
        normalized[column] = pd.to_datetime(normalized[column], utc=True, errors='coerce')

    for column in (
        'order_notional_usdt',
        'conviction_score',
        'risk_budget_usdt',
        'stop_distance_pct',
        'volatility_penalty_multiplier',
        'stop_loss',
        'take_profit',
        'probability_up',
    ):
        normalized[column] = pd.to_numeric(normalized[column], errors='coerce')
    normalized['approved_leverage'] = pd.to_numeric(
        normalized['approved_leverage'],
        errors='coerce',
    ).fillna(0).astype('int64')
    normalized['allowed'] = normalized['allowed'].fillna(False).astype(bool)
    return normalized


def _load_risk_frame(settings: AppSettings | None = None) -> tuple[Path, pd.DataFrame]:
    resolved_settings = settings or load_settings()
    path = _risk_log_path(resolved_settings)
    if not path.exists():
        return path, _empty_risk_frame()
    return path, _coerce_risk_frame(pd.read_parquet(path))


def _record_to_row(record: RiskDecisionRecord) -> dict[str, object]:
    row = record.model_dump()
    row['reason_codes'] = json.dumps(record.reason_codes)
    return row


def append_risk_record(
    record: RiskDecisionRecord,
    settings: AppSettings | None = None,
) -> RiskDecisionRecord:
    resolved_settings = settings or load_settings()
    path, frame = _load_risk_frame(resolved_settings)
    new_frame = _coerce_risk_frame(pd.DataFrame([_record_to_row(record)]))

    updated = pd.concat([frame, new_frame], ignore_index=True)
    updated = updated.sort_values('decided_at', ascending=True).reset_index(drop=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    updated.to_parquet(path, index=False)
    return record


def _parse_reason_codes(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if value is None or pd.isna(value):
        return []
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return [value]
        if isinstance(parsed, list):
            return [str(item) for item in parsed]
    return [str(value)]


def _row_to_risk_record(row: pd.Series) -> RiskDecisionRecord | None:
    decided_at = row.get('decided_at')
    source_timestamp = row.get('source_timestamp')
    predicted_for_timestamp = row.get('predicted_for_timestamp')
    order_notional_usdt = pd.to_numeric(row.get('order_notional_usdt'), errors='coerce')
    approved_leverage = pd.to_numeric(row.get('approved_leverage'), errors='coerce')
    conviction_score = pd.to_numeric(row.get('conviction_score'), errors='coerce')
    risk_budget_usdt = pd.to_numeric(row.get('risk_budget_usdt'), errors='coerce')
    stop_distance_pct = pd.to_numeric(row.get('stop_distance_pct'), errors='coerce')
    volatility_penalty_multiplier = pd.to_numeric(
        row.get('volatility_penalty_multiplier'),
        errors='coerce',
    )
    probability_up = pd.to_numeric(row.get('probability_up'), errors='coerce')
    stop_loss = pd.to_numeric(row.get('stop_loss'), errors='coerce')
    take_profit = pd.to_numeric(row.get('take_profit'), errors='coerce')

    if pd.isna(decided_at) or pd.isna(source_timestamp) or pd.isna(predicted_for_timestamp):
        return None
    if (
        pd.isna(order_notional_usdt)
        or pd.isna(approved_leverage)
        or pd.isna(conviction_score)
        or pd.isna(risk_budget_usdt)
        or pd.isna(probability_up)
    ):
        return None

    return RiskDecisionRecord.model_validate(
        {
            'decided_at': pd.Timestamp(decided_at).isoformat(),
            'source_timestamp': pd.Timestamp(source_timestamp).isoformat(),
            'predicted_for_timestamp': pd.Timestamp(predicted_for_timestamp).isoformat(),
            'requested_action': str(row.get('requested_action') or 'SKIP'),
            'approved_action': str(row.get('approved_action') or 'SKIP'),
            'allowed': bool(row.get('allowed')),
            'order_notional_usdt': float(order_notional_usdt),
            'approved_leverage': int(approved_leverage),
            'conviction_score': float(conviction_score),
            'risk_budget_usdt': float(risk_budget_usdt),
            'stop_distance_pct': None if pd.isna(stop_distance_pct) else float(stop_distance_pct),
            'volatility_penalty_multiplier': (
                None
                if pd.isna(volatility_penalty_multiplier)
                else float(volatility_penalty_multiplier)
            ),
            'stop_loss': None if pd.isna(stop_loss) else float(stop_loss),
            'take_profit': None if pd.isna(take_profit) else float(take_profit),
            'reason_codes': _parse_reason_codes(row.get('reason_codes')),
            'size_reason': str(row.get('size_reason') or 'static_notional_fallback'),
            'leverage_reason': str(row.get('leverage_reason') or 'static_leverage_fallback'),
            'signal_type': str(row.get('signal_type') or 'HOLD'),
            'probability_up': float(probability_up),
            'strategy_version': str(row.get('strategy_version') or 'v1'),
            'risk_version': str(row.get('risk_version') or 'v1'),
        }
    )


def get_latest_risk_record(settings: AppSettings | None = None) -> RiskDecisionRecord | None:
    _, frame = _load_risk_frame(settings)
    if frame.empty:
        return None
    return _row_to_risk_record(frame.iloc[-1])


def get_risk_history(
    limit: int = 200,
    start: str | None = None,
    end: str | None = None,
    settings: AppSettings | None = None,
) -> RiskHistoryResponse:
    resolved_settings = settings or load_settings()
    path, frame = _load_risk_frame(resolved_settings)
    frame = frame.sort_values('decided_at', ascending=True)

    if start is not None:
        start_ts = pd.to_datetime(start, utc=True, errors='coerce')
        if pd.isna(start_ts):
            raise ValueError(f"Invalid 'start' timestamp: {start}")
        frame = frame.loc[frame['predicted_for_timestamp'] >= start_ts]

    if end is not None:
        end_ts = pd.to_datetime(end, utc=True, errors='coerce')
        if pd.isna(end_ts):
            raise ValueError(f"Invalid 'end' timestamp: {end}")
        frame = frame.loc[frame['predicted_for_timestamp'] <= end_ts]

    if limit > 0 and not frame.empty:
        frame = frame.tail(limit)

    decisions: list[RiskDecisionRecord] = []
    for row in frame.to_dict(orient='records'):
        record = _row_to_risk_record(pd.Series(row))
        if record is not None:
            decisions.append(record)

    return RiskHistoryResponse(
        symbol=resolved_settings.symbol,
        timeframe=resolved_settings.timeframe,
        source_path=to_repo_relative(path),
        count=len(decisions),
        decisions=decisions,
    )
