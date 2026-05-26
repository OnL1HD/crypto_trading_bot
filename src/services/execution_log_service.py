from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.core.serialization import to_iso_timestamp
from src.core.settings import AppSettings, load_settings, to_repo_relative
from src.schemas.execution import ExecutionAttemptRecord, ExecutionHistoryResponse


EXECUTION_LOG_COLUMNS = [
    'attempted_at',
    'execution_key',
    'signal_type',
    'source_timestamp',
    'predicted_for_timestamp',
    'symbol',
    'side',
    'position_direction',
    'order_type',
    'order_notional_usdt',
    'leverage',
    'execution_mode',
    'success',
    'status',
    'exchange_order_id',
    'exchange_response_code',
    'exchange_response_message',
    'error_message',
]


def _execution_log_path(settings: AppSettings) -> Path:
    return settings.execution_dir / f'{settings.execution.symbol}_{settings.execution.market_type}_execution_log.parquet'


def _empty_log_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=EXECUTION_LOG_COLUMNS)


def _coerce_execution_frame(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.copy()
    for column in EXECUTION_LOG_COLUMNS:
        if column not in normalized.columns:
            normalized[column] = None

    normalized = normalized[EXECUTION_LOG_COLUMNS]
    for column in ('attempted_at', 'source_timestamp', 'predicted_for_timestamp'):
        normalized[column] = pd.to_datetime(normalized[column], utc=True, errors='coerce')

    normalized['order_notional_usdt'] = pd.to_numeric(normalized['order_notional_usdt'], errors='coerce')
    normalized['leverage'] = pd.to_numeric(normalized['leverage'], errors='coerce').fillna(0).astype('int64')
    normalized['success'] = normalized['success'].fillna(False).astype(bool)
    return normalized


def _load_execution_frame(settings: AppSettings | None = None) -> tuple[Path, pd.DataFrame]:
    resolved_settings = settings or load_settings()
    path = _execution_log_path(resolved_settings)
    if not path.exists():
        return path, _empty_log_frame()
    return path, _coerce_execution_frame(pd.read_parquet(path))


def append_execution_record(
    record: ExecutionAttemptRecord,
    settings: AppSettings | None = None,
) -> ExecutionAttemptRecord:
    resolved_settings = settings or load_settings()
    path, frame = _load_execution_frame(resolved_settings)
    new_frame = _coerce_execution_frame(pd.DataFrame([record.model_dump()]))
    updated = pd.concat([frame, new_frame], ignore_index=True)
    updated = updated.sort_values('attempted_at', ascending=True).reset_index(drop=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    updated.to_parquet(path, index=False)
    return record


def _row_to_execution_record(row: pd.Series) -> ExecutionAttemptRecord | None:
    attempted_at = to_iso_timestamp(row.get('attempted_at'))
    if attempted_at is None:
        return None

    order_notional_usdt = pd.to_numeric(row.get('order_notional_usdt'), errors='coerce')
    leverage = pd.to_numeric(row.get('leverage'), errors='coerce')
    success = bool(row.get('success'))

    if pd.isna(order_notional_usdt) or pd.isna(leverage):
        return None

    return ExecutionAttemptRecord(
        attempted_at=attempted_at,
        execution_key=str(row.get('execution_key') or ''),
        signal_type=str(row.get('signal_type') or ''),
        source_timestamp=to_iso_timestamp(row.get('source_timestamp')),
        predicted_for_timestamp=to_iso_timestamp(row.get('predicted_for_timestamp')),
        symbol=str(row.get('symbol') or ''),
        side=None if pd.isna(row.get('side')) else str(row.get('side')),
        position_direction=None if pd.isna(row.get('position_direction')) else str(row.get('position_direction')),
        order_type=str(row.get('order_type') or ''),
        order_notional_usdt=float(order_notional_usdt),
        leverage=int(leverage),
        execution_mode=str(row.get('execution_mode') or 'demo'),
        success=success,
        status=str(row.get('status') or 'failed'),
        exchange_order_id=None if pd.isna(row.get('exchange_order_id')) else str(row.get('exchange_order_id')),
        exchange_response_code=None
        if pd.isna(row.get('exchange_response_code'))
        else str(row.get('exchange_response_code')),
        exchange_response_message=None
        if pd.isna(row.get('exchange_response_message'))
        else str(row.get('exchange_response_message')),
        error_message=None if pd.isna(row.get('error_message')) else str(row.get('error_message')),
    )


def get_latest_execution_record(settings: AppSettings | None = None) -> ExecutionAttemptRecord | None:
    _, frame = _load_execution_frame(settings)
    if frame.empty:
        return None
    return _row_to_execution_record(frame.iloc[-1])


def has_successful_execution_for_key(execution_key: str, settings: AppSettings | None = None) -> bool:
    _, frame = _load_execution_frame(settings)
    if frame.empty:
        return False
    matching = frame.loc[(frame['execution_key'] == execution_key) & (frame['success'])]
    return not matching.empty


def latest_successful_execution_at(settings: AppSettings | None = None) -> pd.Timestamp | None:
    _, frame = _load_execution_frame(settings)
    successful = frame.loc[frame['success']]
    if successful.empty:
        return None
    latest = successful['attempted_at'].dropna()
    if latest.empty:
        return None
    return pd.Timestamp(latest.max())


def get_execution_history(limit: int = 200, settings: AppSettings | None = None) -> ExecutionHistoryResponse:
    resolved_settings = settings or load_settings()
    path, frame = _load_execution_frame(resolved_settings)
    if limit > 0 and not frame.empty:
        frame = frame.tail(limit)

    records: list[ExecutionAttemptRecord] = []
    for row in frame.to_dict(orient='records'):
        record = _row_to_execution_record(pd.Series(row))
        if record is not None:
            records.append(record)

    return ExecutionHistoryResponse(
        symbol=resolved_settings.execution.symbol,
        source_path=to_repo_relative(path),
        count=len(records),
        executions=records,
    )
