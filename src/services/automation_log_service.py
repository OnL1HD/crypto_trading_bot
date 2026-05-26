from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src.core.settings import AppSettings, load_settings, to_repo_relative
from src.schemas.automation import AutomationCycleRecord, AutomationHistoryResponse


AUTOMATION_LOG_COLUMNS = [
    'cycle_id',
    'started_at',
    'finished_at',
    'bar_timestamp',
    'status',
    'data_refresh_status',
    'inference_status',
    'signal_status',
    'strategy_status',
    'risk_status',
    'execution_status',
    'position_management_status',
    'reconciliation_status',
    'dry_run',
    'execution_attempted',
    'execution_allowed',
    'execution_skipped_reason',
    'position_management_exit_reason',
    'position_management_close_requested',
    'position_management_close_executed',
    'reconciliation_blocked',
    'reconciliation_reason_codes',
    'signal_type',
    'strategy_action',
    'risk_allowed',
    'probability_up',
    'source_timestamp',
    'predicted_for_timestamp',
    'error_message',
]


def _automation_log_path(settings: AppSettings) -> Path:
    return settings.automation_dir / f'{settings.symbol}_{settings.timeframe}_automation_cycles.parquet'


def _empty_automation_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=AUTOMATION_LOG_COLUMNS)


def _decode_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, tuple):
        return [str(item) for item in value]
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            return [value]
        if isinstance(decoded, list):
            return [str(item) for item in decoded]
    try:
        if pd.isna(value):
            return []
    except (TypeError, ValueError):
        pass
    return [str(value)]


def _encode_list(value: object) -> str:
    return json.dumps(_decode_list(value))


def _coerce_automation_frame(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.copy()
    for column in AUTOMATION_LOG_COLUMNS:
        if column not in normalized.columns:
            normalized[column] = None

    normalized = normalized[AUTOMATION_LOG_COLUMNS]
    for column in ('started_at', 'finished_at', 'bar_timestamp', 'source_timestamp', 'predicted_for_timestamp'):
        normalized[column] = pd.to_datetime(normalized[column], utc=True, errors='coerce')

    for column in (
        'dry_run',
        'execution_attempted',
        'execution_allowed',
        'risk_allowed',
        'position_management_close_requested',
        'position_management_close_executed',
        'reconciliation_blocked',
    ):
        normalized[column] = normalized[column].fillna(False).astype(bool)
    normalized['probability_up'] = pd.to_numeric(normalized['probability_up'], errors='coerce')
    return normalized


def _load_automation_frame(settings: AppSettings | None = None) -> tuple[Path, pd.DataFrame]:
    resolved_settings = settings or load_settings()
    path = _automation_log_path(resolved_settings)
    if not path.exists():
        return path, _empty_automation_frame()
    return path, _coerce_automation_frame(pd.read_parquet(path))


def append_automation_cycle(
    record: AutomationCycleRecord,
    settings: AppSettings | None = None,
) -> AutomationCycleRecord:
    resolved_settings = settings or load_settings()
    path, frame = _load_automation_frame(resolved_settings)
    row = record.model_dump()
    row['reconciliation_reason_codes'] = json.dumps(record.reconciliation_reason_codes)
    new_frame = _coerce_automation_frame(pd.DataFrame([row]))
    updated = pd.concat([frame, new_frame], ignore_index=True)
    updated = updated.sort_values('started_at', ascending=True).reset_index(drop=True)
    updated['reconciliation_reason_codes'] = updated['reconciliation_reason_codes'].apply(_encode_list)
    path.parent.mkdir(parents=True, exist_ok=True)
    updated.to_parquet(path, index=False)
    return record


def _row_to_cycle_record(row: pd.Series) -> AutomationCycleRecord | None:
    started_at = row.get('started_at')
    bar_timestamp = row.get('bar_timestamp')
    if pd.isna(started_at) or pd.isna(bar_timestamp):
        return None

    probability_up = pd.to_numeric(row.get('probability_up'), errors='coerce')
    return AutomationCycleRecord.model_validate(
        {
            'cycle_id': str(row.get('cycle_id') or ''),
            'started_at': pd.Timestamp(started_at).isoformat(),
            'finished_at': None if pd.isna(row.get('finished_at')) else pd.Timestamp(row.get('finished_at')).isoformat(),
            'bar_timestamp': pd.Timestamp(bar_timestamp).isoformat(),
            'status': str(row.get('status') or 'failed'),
            'data_refresh_status': str(row.get('data_refresh_status') or 'not_run'),
            'inference_status': str(row.get('inference_status') or 'not_run'),
            'signal_status': str(row.get('signal_status') or 'not_run'),
            'strategy_status': str(row.get('strategy_status') or 'not_run'),
            'risk_status': str(row.get('risk_status') or 'not_run'),
            'execution_status': str(row.get('execution_status') or 'not_run'),
            'position_management_status': str(row.get('position_management_status') or 'not_run'),
            'reconciliation_status': str(row.get('reconciliation_status') or 'not_run'),
            'dry_run': bool(row.get('dry_run')),
            'execution_attempted': bool(row.get('execution_attempted')),
            'execution_allowed': bool(row.get('execution_allowed')),
            'execution_skipped_reason': None
            if pd.isna(row.get('execution_skipped_reason'))
            else str(row.get('execution_skipped_reason')),
            'position_management_exit_reason': None
            if pd.isna(row.get('position_management_exit_reason'))
            else str(row.get('position_management_exit_reason')),
            'position_management_close_requested': bool(row.get('position_management_close_requested')),
            'position_management_close_executed': bool(row.get('position_management_close_executed')),
            'reconciliation_blocked': bool(row.get('reconciliation_blocked')),
            'reconciliation_reason_codes': _decode_list(row.get('reconciliation_reason_codes')),
            'signal_type': None if pd.isna(row.get('signal_type')) else str(row.get('signal_type')),
            'strategy_action': None if pd.isna(row.get('strategy_action')) else str(row.get('strategy_action')),
            'risk_allowed': None if pd.isna(row.get('risk_allowed')) else bool(row.get('risk_allowed')),
            'probability_up': None if pd.isna(probability_up) else float(probability_up),
            'source_timestamp': None
            if pd.isna(row.get('source_timestamp'))
            else pd.Timestamp(row.get('source_timestamp')).isoformat(),
            'predicted_for_timestamp': None
            if pd.isna(row.get('predicted_for_timestamp'))
            else pd.Timestamp(row.get('predicted_for_timestamp')).isoformat(),
            'error_message': None if pd.isna(row.get('error_message')) else str(row.get('error_message')),
        }
    )


def get_latest_automation_cycle(settings: AppSettings | None = None) -> AutomationCycleRecord | None:
    _, frame = _load_automation_frame(settings)
    if frame.empty:
        return None
    return _row_to_cycle_record(frame.iloc[-1])


def has_cycle_for_bar(
    bar_timestamp: str,
    settings: AppSettings | None = None,
    *,
    include_skipped: bool = False,
) -> bool:
    _, frame = _load_automation_frame(settings)
    if frame.empty:
        return False
    bar_ts = pd.to_datetime(bar_timestamp, utc=True, errors='coerce')
    if pd.isna(bar_ts):
        return False
    matching = frame.loc[frame['bar_timestamp'] == bar_ts]
    if not include_skipped:
        matching = matching.loc[matching['status'] != 'skipped']
    return not matching.empty


def get_automation_history(
    limit: int = 200,
    settings: AppSettings | None = None,
) -> AutomationHistoryResponse:
    resolved_settings = settings or load_settings()
    path, frame = _load_automation_frame(resolved_settings)
    frame = frame.sort_values('started_at', ascending=True)
    if limit > 0 and not frame.empty:
        frame = frame.tail(limit)

    cycles: list[AutomationCycleRecord] = []
    for row in frame.to_dict(orient='records'):
        record = _row_to_cycle_record(pd.Series(row))
        if record is not None:
            cycles.append(record)

    return AutomationHistoryResponse(
        symbol=resolved_settings.symbol,
        timeframe=resolved_settings.timeframe,
        source_path=to_repo_relative(path),
        count=len(cycles),
        cycles=cycles,
    )
