from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src.core.settings import AppSettings, load_settings, to_repo_relative
from src.schemas.reconciliation import ReconciliationHistoryResponse, ReconciliationResultRecord


RECONCILIATION_COLUMNS = [
    'checked_at',
    'status',
    'local_open_count',
    'exchange_open_count',
    'matched',
    'mismatch_count',
    'reason_codes',
    'details',
    'block_new_execution',
    'source',
]


def _history_path(settings: AppSettings) -> Path:
    return settings.reconciliation_dir / f'{settings.symbol}_{settings.timeframe}_reconciliation_history.parquet'


def _empty_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=RECONCILIATION_COLUMNS)


def _coerce_frame(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.copy()
    for column in RECONCILIATION_COLUMNS:
        if column not in normalized.columns:
            normalized[column] = None
    normalized = normalized[RECONCILIATION_COLUMNS]
    normalized['checked_at'] = pd.to_datetime(normalized['checked_at'], utc=True, errors='coerce')
    for column in ('local_open_count', 'exchange_open_count', 'mismatch_count'):
        normalized[column] = pd.to_numeric(normalized[column], errors='coerce').fillna(0).astype('int64')
    for column in ('matched', 'block_new_execution'):
        normalized[column] = normalized[column].fillna(False).astype(bool)
    return normalized


def _load_frame(settings: AppSettings | None = None) -> tuple[Path, pd.DataFrame]:
    resolved_settings = settings or load_settings()
    path = _history_path(resolved_settings)
    if not path.exists():
        return path, _empty_frame()
    return path, _coerce_frame(pd.read_parquet(path))


def append_reconciliation_result(
    record: ReconciliationResultRecord,
    settings: AppSettings | None = None,
) -> ReconciliationResultRecord:
    resolved_settings = settings or load_settings()
    path, frame = _load_frame(resolved_settings)
    row = record.model_dump()
    row['reason_codes'] = json.dumps(record.reason_codes)
    row['details'] = json.dumps(record.details)
    new_frame = _coerce_frame(pd.DataFrame([row]))
    updated = pd.concat([frame, new_frame], ignore_index=True)
    updated = updated.sort_values('checked_at', ascending=True).reset_index(drop=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    updated.to_parquet(path, index=False)
    return record


def _decode_list(value: object) -> list[str]:
    if value is None or pd.isna(value):
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            return [value]
        if isinstance(decoded, list):
            return [str(item) for item in decoded]
    return [str(value)]


def _row_to_record(row: pd.Series) -> ReconciliationResultRecord | None:
    checked_at = row.get('checked_at')
    if pd.isna(checked_at):
        return None
    return ReconciliationResultRecord.model_validate(
        {
            'checked_at': pd.Timestamp(checked_at).isoformat(),
            'status': str(row.get('status') or 'warning'),
            'local_open_count': int(pd.to_numeric(row.get('local_open_count'), errors='coerce') or 0),
            'exchange_open_count': int(pd.to_numeric(row.get('exchange_open_count'), errors='coerce') or 0),
            'matched': bool(row.get('matched')),
            'mismatch_count': int(pd.to_numeric(row.get('mismatch_count'), errors='coerce') or 0),
            'reason_codes': _decode_list(row.get('reason_codes')),
            'details': _decode_list(row.get('details')),
            'block_new_execution': bool(row.get('block_new_execution')),
            'source': str(row.get('source') or 'manual'),
        }
    )


def get_latest_reconciliation_record(settings: AppSettings | None = None) -> ReconciliationResultRecord | None:
    _, frame = _load_frame(settings)
    if frame.empty:
        return None
    return _row_to_record(frame.iloc[-1])


def get_reconciliation_history(
    limit: int = 200,
    settings: AppSettings | None = None,
) -> ReconciliationHistoryResponse:
    resolved_settings = settings or load_settings()
    path, frame = _load_frame(resolved_settings)
    frame = frame.sort_values('checked_at', ascending=True)
    if limit > 0 and not frame.empty:
        frame = frame.tail(limit)

    results: list[ReconciliationResultRecord] = []
    for row in frame.to_dict(orient='records'):
        record = _row_to_record(pd.Series(row))
        if record is not None:
            results.append(record)

    return ReconciliationHistoryResponse(
        symbol=resolved_settings.symbol,
        timeframe=resolved_settings.timeframe,
        source_path=to_repo_relative(path),
        count=len(results),
        results=results,
    )
