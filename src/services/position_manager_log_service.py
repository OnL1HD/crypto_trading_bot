from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.core.settings import AppSettings, load_settings, to_repo_relative
from src.schemas.position_manager import (
    PositionManagementDecisionRecord,
    PositionManagementHistoryResponse,
)


POSITION_MANAGEMENT_LOG_COLUMNS = [
    'decision_id',
    'decided_at',
    'trade_id',
    'symbol',
    'direction',
    'position_status',
    'current_price',
    'entry_price',
    'stop_loss',
    'take_profit',
    'holding_minutes',
    'exit_action',
    'exit_reason',
    'should_execute_close',
    'executed_close',
    'execution_skipped_reason',
    'strategy_context_summary',
    'source_timestamp',
    'strategy_version',
    'position_management_version',
]


def _log_path(settings: AppSettings) -> Path:
    return settings.position_management_dir / f'{settings.symbol}_{settings.timeframe}_position_management_history.parquet'


def _empty_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=POSITION_MANAGEMENT_LOG_COLUMNS)


def _coerce_frame(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.copy()
    for column in POSITION_MANAGEMENT_LOG_COLUMNS:
        if column not in normalized.columns:
            normalized[column] = None

    normalized = normalized[POSITION_MANAGEMENT_LOG_COLUMNS]
    for column in ('decided_at', 'source_timestamp'):
        normalized[column] = pd.to_datetime(normalized[column], utc=True, errors='coerce')
    for column in ('current_price', 'entry_price', 'stop_loss', 'take_profit', 'holding_minutes'):
        normalized[column] = pd.to_numeric(normalized[column], errors='coerce')
    for column in ('should_execute_close', 'executed_close'):
        normalized[column] = normalized[column].fillna(False).astype(bool)
    return normalized


def _load_frame(settings: AppSettings | None = None) -> tuple[Path, pd.DataFrame]:
    resolved_settings = settings or load_settings()
    path = _log_path(resolved_settings)
    if not path.exists():
        return path, _empty_frame()
    return path, _coerce_frame(pd.read_parquet(path))


def append_position_management_record(
    record: PositionManagementDecisionRecord,
    settings: AppSettings | None = None,
) -> PositionManagementDecisionRecord:
    resolved_settings = settings or load_settings()
    path, frame = _load_frame(resolved_settings)
    new_frame = _coerce_frame(pd.DataFrame([record.model_dump()]))
    updated = pd.concat([frame, new_frame], ignore_index=True)
    updated = updated.sort_values('decided_at', ascending=True).reset_index(drop=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    updated.to_parquet(path, index=False)
    return record


def _row_to_record(row: pd.Series) -> PositionManagementDecisionRecord | None:
    decided_at = row.get('decided_at')
    if pd.isna(decided_at):
        return None
    holding_minutes = pd.to_numeric(row.get('holding_minutes'), errors='coerce')
    if pd.isna(holding_minutes):
        return None

    return PositionManagementDecisionRecord.model_validate(
        {
            'decision_id': str(row.get('decision_id') or ''),
            'decided_at': pd.Timestamp(decided_at).isoformat(),
            'trade_id': str(row.get('trade_id') or ''),
            'symbol': str(row.get('symbol') or ''),
            'direction': str(row.get('direction') or 'LONG'),
            'position_status': str(row.get('position_status') or 'OPEN'),
            'current_price': None if pd.isna(row.get('current_price')) else float(row.get('current_price')),
            'entry_price': None if pd.isna(row.get('entry_price')) else float(row.get('entry_price')),
            'stop_loss': None if pd.isna(row.get('stop_loss')) else float(row.get('stop_loss')),
            'take_profit': None if pd.isna(row.get('take_profit')) else float(row.get('take_profit')),
            'holding_minutes': float(holding_minutes),
            'exit_action': str(row.get('exit_action') or 'HOLD_POSITION'),
            'exit_reason': str(row.get('exit_reason') or 'position_hold'),
            'should_execute_close': bool(row.get('should_execute_close')),
            'executed_close': bool(row.get('executed_close')),
            'execution_skipped_reason': None
            if pd.isna(row.get('execution_skipped_reason'))
            else str(row.get('execution_skipped_reason')),
            'strategy_context_summary': None
            if pd.isna(row.get('strategy_context_summary'))
            else str(row.get('strategy_context_summary')),
            'source_timestamp': None
            if pd.isna(row.get('source_timestamp'))
            else pd.Timestamp(row.get('source_timestamp')).isoformat(),
            'strategy_version': None if pd.isna(row.get('strategy_version')) else str(row.get('strategy_version')),
            'position_management_version': str(row.get('position_management_version') or 'v1'),
        }
    )


def get_latest_position_management_record(settings: AppSettings | None = None) -> PositionManagementDecisionRecord | None:
    _, frame = _load_frame(settings)
    if frame.empty:
        return None
    return _row_to_record(frame.iloc[-1])


def get_position_management_history(
    limit: int = 200,
    settings: AppSettings | None = None,
) -> PositionManagementHistoryResponse:
    resolved_settings = settings or load_settings()
    path, frame = _load_frame(resolved_settings)
    frame = frame.sort_values('decided_at', ascending=True)
    if limit > 0 and not frame.empty:
        frame = frame.tail(limit)

    decisions: list[PositionManagementDecisionRecord] = []
    for row in frame.to_dict(orient='records'):
        record = _row_to_record(pd.Series(row))
        if record is not None:
            decisions.append(record)

    return PositionManagementHistoryResponse(
        symbol=resolved_settings.symbol,
        timeframe=resolved_settings.timeframe,
        source_path=to_repo_relative(path),
        count=len(decisions),
        decisions=decisions,
    )
