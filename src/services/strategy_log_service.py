from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.core.settings import AppSettings, load_settings, to_repo_relative
from src.schemas.strategy import StrategyDecisionRecord, StrategyHistoryResponse


STRATEGY_LOG_COLUMNS = [
    'decided_at',
    'source_timestamp',
    'predicted_for_timestamp',
    'probability_up',
    'prediction_class',
    'signal_type',
    'confidence_bucket',
    'trend_context',
    'volatility_context',
    'volume_context',
    'momentum_context',
    'action',
    'action_reason',
    'strategy_version',
    'model_version',
    'feature_snapshot_available',
    'trend_aligned',
    'volatility_suitable',
    'volume_supported',
    'momentum_supported',
    'signal_persistent',
    'flip_noise_blocked',
    'has_open_long',
    'has_open_short',
    'counter_trend_signal',
]


def _strategy_log_path(settings: AppSettings) -> Path:
    return settings.strategy_dir / f'{settings.symbol}_{settings.timeframe}_strategy_history.parquet'


def _empty_strategy_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=STRATEGY_LOG_COLUMNS)


def _coerce_strategy_frame(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.copy()
    for column in STRATEGY_LOG_COLUMNS:
        if column not in normalized.columns:
            normalized[column] = None

    normalized = normalized[STRATEGY_LOG_COLUMNS]
    for column in ('decided_at', 'source_timestamp', 'predicted_for_timestamp'):
        normalized[column] = pd.to_datetime(normalized[column], utc=True, errors='coerce')

    normalized['probability_up'] = pd.to_numeric(normalized['probability_up'], errors='coerce')
    normalized['prediction_class'] = pd.to_numeric(normalized['prediction_class'], errors='coerce').fillna(0).astype('int64')

    for column in (
        'feature_snapshot_available',
        'trend_aligned',
        'volatility_suitable',
        'volume_supported',
        'momentum_supported',
        'signal_persistent',
        'flip_noise_blocked',
        'has_open_long',
        'has_open_short',
        'counter_trend_signal',
    ):
        normalized[column] = normalized[column].fillna(False).astype(bool)

    return normalized


def _load_strategy_frame(settings: AppSettings | None = None) -> tuple[Path, pd.DataFrame]:
    resolved_settings = settings or load_settings()
    path = _strategy_log_path(resolved_settings)
    if not path.exists():
        return path, _empty_strategy_frame()
    return path, _coerce_strategy_frame(pd.read_parquet(path))


def _record_to_row(record: StrategyDecisionRecord) -> dict[str, object]:
    row = record.model_dump(exclude={'supporting_context'})
    row.update(record.supporting_context.model_dump())
    return row


def append_strategy_record(
    record: StrategyDecisionRecord,
    settings: AppSettings | None = None,
) -> StrategyDecisionRecord:
    resolved_settings = settings or load_settings()
    path, frame = _load_strategy_frame(resolved_settings)
    new_frame = _coerce_strategy_frame(pd.DataFrame([_record_to_row(record)]))

    if not frame.empty:
        same_prediction = frame['predicted_for_timestamp'] == pd.to_datetime(record.predicted_for_timestamp, utc=True)
        same_version = frame['strategy_version'] == record.strategy_version
        frame = frame.loc[~(same_prediction & same_version)]

    updated = pd.concat([frame, new_frame], ignore_index=True)
    updated = updated.sort_values('predicted_for_timestamp', ascending=True).reset_index(drop=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    updated.to_parquet(path, index=False)
    return record


def _row_to_strategy_record(row: pd.Series) -> StrategyDecisionRecord | None:
    decided_at = row.get('decided_at')
    source_timestamp = row.get('source_timestamp')
    predicted_for_timestamp = row.get('predicted_for_timestamp')
    probability_up = pd.to_numeric(row.get('probability_up'), errors='coerce')
    prediction_class = pd.to_numeric(row.get('prediction_class'), errors='coerce')

    if pd.isna(decided_at) or pd.isna(source_timestamp) or pd.isna(predicted_for_timestamp):
        return None
    if pd.isna(probability_up) or pd.isna(prediction_class):
        return None

    return StrategyDecisionRecord.model_validate(
        {
            'decided_at': pd.Timestamp(decided_at).isoformat(),
            'source_timestamp': pd.Timestamp(source_timestamp).isoformat(),
            'predicted_for_timestamp': pd.Timestamp(predicted_for_timestamp).isoformat(),
            'probability_up': float(probability_up),
            'prediction_class': int(prediction_class),
            'signal_type': str(row.get('signal_type') or 'HOLD'),
            'confidence_bucket': str(row.get('confidence_bucket') or 'NEUTRAL'),
            'trend_context': str(row.get('trend_context') or 'missing'),
            'volatility_context': str(row.get('volatility_context') or 'missing'),
            'volume_context': str(row.get('volume_context') or 'missing'),
            'momentum_context': str(row.get('momentum_context') or 'missing'),
            'action': str(row.get('action') or 'HOLD'),
            'action_reason': str(row.get('action_reason') or 'unknown'),
            'strategy_version': str(row.get('strategy_version') or 'v1'),
            'model_version': None if pd.isna(row.get('model_version')) else str(row.get('model_version')),
            'supporting_context': {
                'feature_snapshot_available': bool(row.get('feature_snapshot_available')),
                'trend_aligned': bool(row.get('trend_aligned')),
                'volatility_suitable': bool(row.get('volatility_suitable')),
                'volume_supported': bool(row.get('volume_supported')),
                'momentum_supported': bool(row.get('momentum_supported')),
                'signal_persistent': bool(row.get('signal_persistent')),
                'flip_noise_blocked': bool(row.get('flip_noise_blocked')),
                'has_open_long': bool(row.get('has_open_long')),
                'has_open_short': bool(row.get('has_open_short')),
                'counter_trend_signal': bool(row.get('counter_trend_signal')),
            },
        }
    )


def get_latest_strategy_record(settings: AppSettings | None = None) -> StrategyDecisionRecord | None:
    _, frame = _load_strategy_frame(settings)
    if frame.empty:
        return None
    return _row_to_strategy_record(frame.iloc[-1])


def get_strategy_history(
    limit: int = 200,
    start: str | None = None,
    end: str | None = None,
    settings: AppSettings | None = None,
) -> StrategyHistoryResponse:
    resolved_settings = settings or load_settings()
    path, frame = _load_strategy_frame(resolved_settings)
    frame = frame.sort_values('predicted_for_timestamp', ascending=True)

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

    decisions: list[StrategyDecisionRecord] = []
    for row in frame.to_dict(orient='records'):
        record = _row_to_strategy_record(pd.Series(row))
        if record is not None:
            decisions.append(record)

    return StrategyHistoryResponse(
        symbol=resolved_settings.symbol,
        timeframe=resolved_settings.timeframe,
        source_path=to_repo_relative(path),
        count=len(decisions),
        decisions=decisions,
    )
