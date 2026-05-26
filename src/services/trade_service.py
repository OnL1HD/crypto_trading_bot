from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.core.serialization import to_iso_timestamp
from src.core.settings import AppSettings, load_settings, to_repo_relative
from src.schemas.execution import OpenPositionsResponse, TradeHistoryResponse, TradeRecord


TRADE_COLUMNS = [
    'trade_id',
    'symbol',
    'direction',
    'entry_time',
    'entry_price',
    'stop_loss',
    'take_profit',
    'entry_order_id',
    'exit_time',
    'exit_price',
    'exit_order_id',
    'leverage',
    'quantity',
    'status',
    'source_entry_signal',
    'source_exit_signal',
    'realized_pnl',
    'execution_mode',
]


def _trades_path(settings: AppSettings) -> Path:
    return settings.execution_dir / f'{settings.execution.symbol}_{settings.execution.market_type}_trades.parquet'


def _empty_trade_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=TRADE_COLUMNS)


def _coerce_trade_frame(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.copy()
    for column in TRADE_COLUMNS:
        if column not in normalized.columns:
            normalized[column] = None

    normalized = normalized[TRADE_COLUMNS]
    for column in ('entry_time', 'exit_time'):
        normalized[column] = pd.to_datetime(normalized[column], utc=True, errors='coerce')

    for column in ('entry_price', 'stop_loss', 'take_profit', 'exit_price', 'quantity', 'realized_pnl'):
        normalized[column] = pd.to_numeric(normalized[column], errors='coerce')

    normalized['leverage'] = pd.to_numeric(normalized['leverage'], errors='coerce').fillna(0).astype('int64')
    return normalized


def _load_trade_frame(settings: AppSettings | None = None) -> tuple[Path, pd.DataFrame]:
    resolved_settings = settings or load_settings()
    path = _trades_path(resolved_settings)
    if not path.exists():
        return path, _empty_trade_frame()
    return path, _coerce_trade_frame(pd.read_parquet(path))


def append_trade(record: TradeRecord, settings: AppSettings | None = None) -> TradeRecord:
    resolved_settings = settings or load_settings()
    path, frame = _load_trade_frame(resolved_settings)
    new_frame = _coerce_trade_frame(pd.DataFrame([record.model_dump()]))
    updated = pd.concat([frame, new_frame], ignore_index=True)
    updated = updated.sort_values('entry_time', ascending=True).reset_index(drop=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    updated.to_parquet(path, index=False)
    return record


def close_trade(
    trade_id: str,
    *,
    exit_time: str,
    exit_price: float | None,
    exit_order_id: str | None,
    source_exit_signal: str,
    settings: AppSettings | None = None,
) -> TradeRecord:
    resolved_settings = settings or load_settings()
    path, frame = _load_trade_frame(resolved_settings)
    if frame.empty:
        raise ValueError(f'Trade not found: {trade_id}')

    matches = frame.index[frame['trade_id'] == trade_id].tolist()
    if not matches:
        raise ValueError(f'Trade not found: {trade_id}')

    row_index = matches[-1]
    current = frame.iloc[row_index]
    if str(current.get('status')) != 'OPEN':
        raise ValueError(f'Trade is not open: {trade_id}')

    entry_price = pd.to_numeric(current.get('entry_price'), errors='coerce')
    quantity = pd.to_numeric(current.get('quantity'), errors='coerce')
    direction = str(current.get('direction') or '')

    realized_pnl: float | None = None
    if not pd.isna(entry_price) and not pd.isna(quantity) and exit_price is not None:
        quantity_float = float(quantity)
        entry_price_float = float(entry_price)
        if direction == 'LONG':
            realized_pnl = (exit_price - entry_price_float) * quantity_float
        elif direction == 'SHORT':
            realized_pnl = (entry_price_float - exit_price) * quantity_float

    exit_timestamp = pd.to_datetime(exit_time, utc=True, errors='coerce')
    if pd.isna(exit_timestamp):
        raise ValueError(f'Invalid exit_time for trade close: {exit_time}')
    exit_timestamp = pd.Timestamp(exit_timestamp).floor('ms')

    frame.loc[row_index, 'exit_time'] = exit_timestamp
    frame.loc[row_index, 'exit_price'] = exit_price
    frame.loc[row_index, 'exit_order_id'] = exit_order_id
    frame.loc[row_index, 'source_exit_signal'] = source_exit_signal
    frame.loc[row_index, 'realized_pnl'] = realized_pnl
    frame.loc[row_index, 'status'] = 'CLOSED'

    frame = frame.sort_values('entry_time', ascending=True).reset_index(drop=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path, index=False)

    updated_record = _row_to_trade_record(frame.loc[frame['trade_id'] == trade_id].iloc[-1])
    if updated_record is None:
        raise ValueError(f'Failed to serialize closed trade: {trade_id}')
    return updated_record


def _row_to_trade_record(row: pd.Series) -> TradeRecord | None:
    entry_time = to_iso_timestamp(row.get('entry_time'))
    if entry_time is None:
        return None

    leverage = pd.to_numeric(row.get('leverage'), errors='coerce')
    quantity = pd.to_numeric(row.get('quantity'), errors='coerce')
    if pd.isna(leverage) or pd.isna(quantity):
        return None

    entry_price = pd.to_numeric(row.get('entry_price'), errors='coerce')
    stop_loss = pd.to_numeric(row.get('stop_loss'), errors='coerce')
    take_profit = pd.to_numeric(row.get('take_profit'), errors='coerce')
    exit_price = pd.to_numeric(row.get('exit_price'), errors='coerce')
    realized_pnl = pd.to_numeric(row.get('realized_pnl'), errors='coerce')

    return TradeRecord(
        trade_id=str(row.get('trade_id') or ''),
        symbol=str(row.get('symbol') or ''),
        direction=str(row.get('direction') or 'LONG'),
        entry_time=entry_time,
        entry_price=None if pd.isna(entry_price) else float(entry_price),
        stop_loss=None if pd.isna(stop_loss) else float(stop_loss),
        take_profit=None if pd.isna(take_profit) else float(take_profit),
        entry_order_id=None if pd.isna(row.get('entry_order_id')) else str(row.get('entry_order_id')),
        exit_time=to_iso_timestamp(row.get('exit_time')),
        exit_price=None if pd.isna(exit_price) else float(exit_price),
        exit_order_id=None if pd.isna(row.get('exit_order_id')) else str(row.get('exit_order_id')),
        leverage=int(leverage),
        quantity=float(quantity),
        status=str(row.get('status') or 'OPEN'),
        source_entry_signal=str(row.get('source_entry_signal') or ''),
        source_exit_signal=None if pd.isna(row.get('source_exit_signal')) else str(row.get('source_exit_signal')),
        realized_pnl=None if pd.isna(realized_pnl) else float(realized_pnl),
        execution_mode=str(row.get('execution_mode') or 'demo'),
    )


def get_open_trade_records(settings: AppSettings | None = None) -> list[TradeRecord]:
    _, frame = _load_trade_frame(settings)
    open_frame = frame.loc[frame['status'] == 'OPEN'].sort_values('entry_time', ascending=True)
    records: list[TradeRecord] = []
    for row in open_frame.to_dict(orient='records'):
        record = _row_to_trade_record(pd.Series(row))
        if record is not None:
            records.append(record)
    return records


def get_open_positions_response(settings: AppSettings | None = None) -> OpenPositionsResponse:
    resolved_settings = settings or load_settings()
    path, _ = _load_trade_frame(resolved_settings)
    positions = get_open_trade_records(resolved_settings)
    return OpenPositionsResponse(
        symbol=resolved_settings.execution.symbol,
        source_path=to_repo_relative(path),
        count=len(positions),
        positions=positions,
    )


def get_trade_history(limit: int = 200, settings: AppSettings | None = None) -> TradeHistoryResponse:
    resolved_settings = settings or load_settings()
    path, frame = _load_trade_frame(resolved_settings)
    frame = frame.sort_values('entry_time', ascending=True)
    if limit > 0 and not frame.empty:
        frame = frame.tail(limit)

    trades: list[TradeRecord] = []
    for row in frame.to_dict(orient='records'):
        record = _row_to_trade_record(pd.Series(row))
        if record is not None:
            trades.append(record)

    return TradeHistoryResponse(
        symbol=resolved_settings.execution.symbol,
        source_path=to_repo_relative(path),
        count=len(trades),
        trades=trades,
    )
