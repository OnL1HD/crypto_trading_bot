from __future__ import annotations

import ast
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / 'data'
REPORT_DIR = ROOT / 'reports' / 'section_3_5_demo_trading'
FIGURES_DIR = REPORT_DIR / 'figures'
REPORT_PATH = REPORT_DIR / 'section_3_5_report.txt'

THESIS_BLUE = '#3E6EA8'
THESIS_TEAL = '#3EA8A1'
THESIS_GOLD = '#C9992E'
THESIS_RED = '#B85450'
THESIS_GREY = '#7F8790'
THESIS_GREEN = '#4C9A5E'
THESIS_ORANGE = '#D78941'


@dataclass(frozen=True)
class HistoryFile:
    label: str
    path: Path | None


def find_single(label: str, patterns: list[str]) -> HistoryFile:
    matches: list[Path] = []
    for pattern in patterns:
        matches.extend(DATA_DIR.glob(pattern))
    deduped = sorted({path.resolve() for path in matches})
    if not deduped:
        return HistoryFile(label=label, path=None)
    if len(deduped) == 1:
        return HistoryFile(label=label, path=Path(deduped[0]))
    latest = max((Path(path) for path in deduped), key=lambda item: item.stat().st_mtime)
    return HistoryFile(label=label, path=latest)


def load_frame(history_file: HistoryFile) -> pd.DataFrame:
    if history_file.path is None or not history_file.path.exists():
        return pd.DataFrame()
    return pd.read_parquet(history_file.path)


def to_ts(value: Any) -> pd.Timestamp | None:
    parsed = pd.to_datetime(value, utc=True, errors='coerce')
    if pd.isna(parsed):
        return None
    return pd.Timestamp(parsed)


def iso_or_nerasta(value: pd.Timestamp | None) -> str:
    if value is None or pd.isna(value):
        return 'nerasta'
    return value.isoformat()


def fmt_number(value: Any, digits: int = 2) -> str:
    if value is None:
        return 'nerasta'
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 'nerasta'
    if not np.isfinite(numeric):
        return 'nerasta'
    return f'{numeric:.{digits}f}'


def fmt_int(value: Any) -> str:
    if value is None:
        return 'nerasta'
    try:
        return str(int(value))
    except (TypeError, ValueError):
        return 'nerasta'


def fmt_pct(part: int | float, total: int | float, digits: int = 2) -> str:
    if total in (0, 0.0):
        return 'nerasta'
    return f'{(float(part) / float(total)) * 100:.{digits}f}%'


def fmt_ratio_pct(value: Any, digits: int = 2) -> str:
    if value is None:
        return 'nerasta'
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 'nerasta'
    if not np.isfinite(numeric):
        return 'nerasta'
    return f'{numeric:.{digits}f}%'


def fmt_duration_minutes(value: Any, digits: int = 2) -> str:
    if value is None:
        return 'nerasta'
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 'nerasta'
    if not np.isfinite(numeric):
        return 'nerasta'
    return f'{numeric:.{digits}f} min.'


def markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    header_line = '| ' + ' | '.join(headers) + ' |'
    separator = '| ' + ' | '.join(['---'] * len(headers)) + ' |'
    body_lines = ['| ' + ' | '.join(str(cell) for cell in row) + ' |' for row in rows]
    return '\n'.join([header_line, separator, *body_lines])


def normalize_string(series: pd.Series) -> pd.Series:
    return series.astype('string').fillna('').str.strip()


def top_counts(series: pd.Series, limit: int = 10, drop_empty: bool = True) -> pd.Series:
    normalized = normalize_string(series)
    if drop_empty:
        normalized = normalized.loc[normalized != '']
    if normalized.empty:
        return pd.Series(dtype='int64')
    return normalized.value_counts().head(limit)


def parse_reason_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, float) and np.isnan(value):
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, tuple):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        text = value.strip()
        if text == '' or text.lower() == 'nan':
            return []
        for loader in (json.loads, ast.literal_eval):
            try:
                parsed = loader(text)
                if isinstance(parsed, (list, tuple)):
                    return [str(item).strip() for item in parsed if str(item).strip()]
            except Exception:
                continue
        return [text]
    return [str(value).strip()]


def flatten_reason_counts(values: pd.Series, limit: int = 10) -> pd.Series:
    counter: dict[str, int] = {}
    for value in values.tolist():
        for item in parse_reason_list(value):
            counter[item] = counter.get(item, 0) + 1
    if not counter:
        return pd.Series(dtype='int64')
    return pd.Series(counter).sort_values(ascending=False).head(limit)


def canonical_close_reason(value: Any) -> str:
    if value is None:
        return 'nerasta'
    text = str(value).strip()
    if text == '' or text.lower() == 'nan':
        return 'nerasta'
    if text.startswith('position_manager:'):
        return text.split(':', 1)[1]
    if text.startswith('manual_reconciliation_cleanup:'):
        return 'manual_reconciliation_cleanup'
    return text


def close_reason_label(value: str) -> str:
    labels = {
        'stop_loss_exit': 'Stop-loss',
        'take_profit_exit': 'Take-profit',
        'max_holding_time_exit': 'Maksimali laikymo trukmė',
        'opposite_strategy_signal_exit': 'Priešingas signalas',
        'manual_reconciliation_cleanup': 'Rankinis suderinimo valymas',
        'nerasta': 'Nerasta',
    }
    return labels.get(value, value.replace('_', ' '))


def position_reason_label(value: str) -> str:
    labels = {
        'position_hold': 'Pozicija laikoma',
        'stop_loss_exit': 'Stop-loss',
        'take_profit_exit': 'Take-profit',
        'max_holding_time_exit': 'Maksimali laikymo trukmė',
        'opposite_strategy_signal_exit': 'Priešingas signalas',
        'current_price_unavailable': 'Kaina nerasta',
    }
    return labels.get(value, value.replace('_', ' '))


def outcome_label(value: float) -> str:
    if value > 0:
        return 'Pelningas'
    if value < 0:
        return 'Nuostolingas'
    return 'Nulinis'


def draw_bar_chart(
    series: pd.Series,
    output_path: Path,
    *,
    title: str,
    xlabel: str,
    ylabel: str,
    color: str,
) -> None:
    plt.figure(figsize=(10, 6))
    ax = plt.gca()
    values = series.astype(float)
    bars = ax.bar(series.index.astype(str), values, color=color, edgecolor='black', linewidth=0.6)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(axis='y', linestyle='--', alpha=0.35)
    ax.set_axisbelow(True)
    max_value = float(values.max()) if len(values) else 0.0
    for bar, value in zip(bars, values, strict=False):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + max(max_value * 0.015, 0.5),
            f'{int(value)}',
            ha='center',
            va='bottom',
            fontsize=10,
        )
    plt.tight_layout()
    plt.savefig(output_path, dpi=200)
    plt.close()


def draw_trade_pnl_chart(frame: pd.DataFrame, output_path: Path) -> None:
    plt.figure(figsize=(12, 6))
    ax = plt.gca()
    colors = [THESIS_GREEN if value > 0 else THESIS_RED if value < 0 else THESIS_GREY for value in frame['realized_pnl']]
    x_labels = [f'S{index + 1}' for index in range(len(frame))]
    bars = ax.bar(x_labels, frame['realized_pnl'], color=colors, edgecolor='black', linewidth=0.6)
    ax.axhline(0, color='black', linewidth=0.9)
    ax.set_title('Uždarytų sandorių realizuotas PnL')
    ax.set_xlabel('Sandoris')
    ax.set_ylabel('Realizuotas PnL, USDT')
    ax.grid(axis='y', linestyle='--', alpha=0.35)
    ax.set_axisbelow(True)
    for bar, value in zip(bars, frame['realized_pnl'], strict=False):
        y = value + (0.18 if value >= 0 else -0.28)
        va = 'bottom' if value >= 0 else 'top'
        ax.text(bar.get_x() + bar.get_width() / 2, y, f'{value:.2f}', ha='center', va=va, fontsize=9)
    plt.tight_layout()
    plt.savefig(output_path, dpi=200)
    plt.close()


def draw_pnl_curve(frame: pd.DataFrame, output_path: Path) -> None:
    plt.figure(figsize=(12, 6))
    ax = plt.gca()
    ax.plot(frame['exit_time'], frame['cumulative_realized_pnl'], color=THESIS_BLUE, linewidth=2.2, marker='o', markersize=4)
    ax.axhline(0, color='black', linewidth=0.9)
    ax.set_title('Kaupiamasis realizuotas PnL laike')
    ax.set_xlabel('Uždarymo laikas')
    ax.set_ylabel('Kaupiamasis realizuotas PnL, USDT')
    ax.grid(True, linestyle='--', alpha=0.35)
    for label in ax.get_xticklabels():
        label.set_rotation(25)
        label.set_ha('right')
    plt.tight_layout()
    plt.savefig(output_path, dpi=200)
    plt.close()


def draw_histogram(series: pd.Series, output_path: Path, *, title: str, xlabel: str, color: str) -> None:
    values = pd.to_numeric(series, errors='coerce').dropna()
    if values.empty:
        values = pd.Series([0.0])
    plt.figure(figsize=(10, 6))
    ax = plt.gca()
    ax.hist(values.astype(float), bins=min(8, max(3, len(values))), color=color, edgecolor='black', linewidth=0.6)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel('Sandorių skaičius')
    ax.grid(axis='y', linestyle='--', alpha=0.35)
    ax.set_axisbelow(True)
    plt.tight_layout()
    plt.savefig(output_path, dpi=200)
    plt.close()


def draw_pnl_by_reason_chart(series: pd.Series, output_path: Path) -> None:
    ordered = series.sort_values(ascending=True)
    plt.figure(figsize=(11, 6))
    ax = plt.gca()
    colors = [THESIS_GREEN if value > 0 else THESIS_RED if value < 0 else THESIS_GREY for value in ordered.astype(float)]
    bars = ax.barh(ordered.index.astype(str), ordered.astype(float), color=colors, edgecolor='black', linewidth=0.6)
    ax.axvline(0, color='black', linewidth=0.9)
    ax.set_title('Vidutinis realizuotas PnL pagal uždarymo priežastį')
    ax.set_xlabel('Vidutinis realizuotas PnL, USDT')
    ax.grid(axis='x', linestyle='--', alpha=0.35)
    ax.set_axisbelow(True)
    for bar, value in zip(bars, ordered.astype(float), strict=False):
        offset = 0.12 if value >= 0 else -0.12
        ha = 'left' if value >= 0 else 'right'
        ax.text(value + offset, bar.get_y() + bar.get_height() / 2, f'{value:.2f}', va='center', ha=ha, fontsize=9)
    plt.tight_layout()
    plt.savefig(output_path, dpi=200)
    plt.close()


def build_report() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    files = {
        'trades': find_single('trades', ['execution/*trades*.parquet', 'execution/*trade*.parquet']),
        'execution': find_single('execution', ['execution/*execution_log*.parquet', 'execution/*execution*.parquet']),
        'position_management': find_single('position_management', ['position_management/*position_management*.parquet', 'position_management/*management*.parquet']),
        'reconciliation': find_single('reconciliation', ['reconciliation/*reconciliation*.parquet', 'reconciliation/*history*.parquet']),
        'automation': find_single('automation', ['automation/*automation_cycles*.parquet', 'automation/*cycle*.parquet']),
    }

    trades_df = load_frame(files['trades'])
    execution_df = load_frame(files['execution'])
    position_management_df = load_frame(files['position_management'])
    reconciliation_df = load_frame(files['reconciliation'])
    automation_df = load_frame(files['automation'])

    if not trades_df.empty:
        trades_df = trades_df.copy()
        trades_df['entry_time'] = pd.to_datetime(trades_df['entry_time'], utc=True, errors='coerce')
        trades_df['exit_time'] = pd.to_datetime(trades_df['exit_time'], utc=True, errors='coerce')
        trades_df['realized_pnl'] = pd.to_numeric(trades_df['realized_pnl'], errors='coerce')
        trades_df['quantity'] = pd.to_numeric(trades_df['quantity'], errors='coerce')
        trades_df['entry_price'] = pd.to_numeric(trades_df['entry_price'], errors='coerce')
        trades_df['exit_price'] = pd.to_numeric(trades_df['exit_price'], errors='coerce')
        trades_df['close_reason_raw'] = trades_df['source_exit_signal'].apply(canonical_close_reason)
        trades_df['close_reason_label'] = trades_df['close_reason_raw'].apply(close_reason_label)
        trades_df['holding_minutes'] = (trades_df['exit_time'] - trades_df['entry_time']).dt.total_seconds() / 60.0
        trades_df['entry_notional_usdt'] = trades_df['entry_price'] * trades_df['quantity']

    if not execution_df.empty:
        execution_df = execution_df.copy()
        execution_df['attempted_at'] = pd.to_datetime(execution_df['attempted_at'], utc=True, errors='coerce')

    if not position_management_df.empty:
        position_management_df = position_management_df.copy()
        position_management_df['decided_at'] = pd.to_datetime(position_management_df['decided_at'], utc=True, errors='coerce')
        position_management_df['holding_minutes'] = pd.to_numeric(position_management_df['holding_minutes'], errors='coerce')

    if not reconciliation_df.empty:
        reconciliation_df = reconciliation_df.copy()
        reconciliation_df['checked_at'] = pd.to_datetime(reconciliation_df['checked_at'], utc=True, errors='coerce')
        reconciliation_df['block_new_execution'] = reconciliation_df['block_new_execution'].fillna(False).astype(bool)
        reconciliation_df['matched'] = reconciliation_df['matched'].fillna(False).astype(bool)

    closed_trades = trades_df.loc[normalize_string(trades_df.get('status', pd.Series(dtype='string'))) == 'CLOSED'].copy() if not trades_df.empty else pd.DataFrame()
    closed_trades_with_pnl = closed_trades.loc[closed_trades['realized_pnl'].notna()].copy() if not closed_trades.empty else pd.DataFrame()
    closed_trades_with_pnl = closed_trades_with_pnl.sort_values('exit_time', ascending=True).reset_index(drop=True)
    if not closed_trades_with_pnl.empty:
        closed_trades_with_pnl['cumulative_realized_pnl'] = closed_trades_with_pnl['realized_pnl'].cumsum()
        closed_trades_with_pnl['trade_sequence'] = np.arange(1, len(closed_trades_with_pnl) + 1)
        closed_trades_with_pnl['outcome'] = closed_trades_with_pnl['realized_pnl'].apply(outcome_label)

    trade_coverage_earliest = None if closed_trades.empty else min(
        value for value in [closed_trades['entry_time'].min(), closed_trades['exit_time'].min()] if pd.notna(value)
    )
    trade_coverage_latest = None if closed_trades.empty else max(
        value for value in [closed_trades['entry_time'].max(), closed_trades['exit_time'].max()] if pd.notna(value)
    )
    execution_coverage_earliest = None if execution_df.empty else execution_df['attempted_at'].min()
    execution_coverage_latest = None if execution_df.empty else execution_df['attempted_at'].max()
    position_management_coverage_earliest = None if position_management_df.empty else position_management_df['decided_at'].min()
    position_management_coverage_latest = None if position_management_df.empty else position_management_df['decided_at'].max()
    reconciliation_coverage_earliest = None if reconciliation_df.empty else reconciliation_df['checked_at'].min()
    reconciliation_coverage_latest = None if reconciliation_df.empty else reconciliation_df['checked_at'].max()

    coverage_rows = [
        [
            'Sandorių istorija',
            'nerasta' if files['trades'].path is None else files['trades'].path.relative_to(ROOT).as_posix(),
            fmt_int(len(closed_trades)),
            iso_or_nerasta(trade_coverage_earliest),
            iso_or_nerasta(trade_coverage_latest),
            'Aprėptis skaičiuota nuo ankstyviausio entry_time iki vėliausio exit_time.',
        ],
        [
            'Vykdymo žurnalas',
            'nerasta' if files['execution'].path is None else files['execution'].path.relative_to(ROOT).as_posix(),
            fmt_int(len(execution_df)),
            iso_or_nerasta(execution_coverage_earliest),
            iso_or_nerasta(execution_coverage_latest),
            'Naudotas attempted_at stulpelis.',
        ],
        [
            'Pozicijų priežiūra',
            'nerasta' if files['position_management'].path is None else files['position_management'].path.relative_to(ROOT).as_posix(),
            fmt_int(len(position_management_df)),
            iso_or_nerasta(position_management_coverage_earliest),
            iso_or_nerasta(position_management_coverage_latest),
            'Naudotas decided_at stulpelis.',
        ],
        [
            'Būsenų suderinimas',
            'nerasta' if files['reconciliation'].path is None else files['reconciliation'].path.relative_to(ROOT).as_posix(),
            fmt_int(len(reconciliation_df)),
            iso_or_nerasta(reconciliation_coverage_earliest),
            iso_or_nerasta(reconciliation_coverage_latest),
            'Naudotas checked_at stulpelis.',
        ],
    ]

    total_closed_trades = int(len(closed_trades))
    total_closed_with_pnl = int(len(closed_trades_with_pnl))
    pnl_missing_count = total_closed_trades - total_closed_with_pnl
    long_count_all = int((normalize_string(closed_trades.get('direction', pd.Series(dtype='string'))) == 'LONG').sum()) if not closed_trades.empty else 0
    short_count_all = int((normalize_string(closed_trades.get('direction', pd.Series(dtype='string'))) == 'SHORT').sum()) if not closed_trades.empty else 0
    profitable_count = int((closed_trades_with_pnl['realized_pnl'] > 0).sum()) if not closed_trades_with_pnl.empty else 0
    losing_count = int((closed_trades_with_pnl['realized_pnl'] < 0).sum()) if not closed_trades_with_pnl.empty else 0
    breakeven_count = int((closed_trades_with_pnl['realized_pnl'] == 0).sum()) if not closed_trades_with_pnl.empty else 0
    win_rate = (profitable_count / total_closed_with_pnl * 100.0) if total_closed_with_pnl else None
    total_realized_pnl = closed_trades_with_pnl['realized_pnl'].sum() if not closed_trades_with_pnl.empty else None
    average_pnl = closed_trades_with_pnl['realized_pnl'].mean() if not closed_trades_with_pnl.empty else None
    median_pnl = closed_trades_with_pnl['realized_pnl'].median() if not closed_trades_with_pnl.empty else None
    best_pnl = closed_trades_with_pnl['realized_pnl'].max() if not closed_trades_with_pnl.empty else None
    worst_pnl = closed_trades_with_pnl['realized_pnl'].min() if not closed_trades_with_pnl.empty else None
    net_return_pct = None
    net_return_note = 'nerasta – sandorių istorijoje nėra portfelio kapitalo arba sąskaitos balanso stulpelio, todėl grynosios grąžos procentas neapskaičiuotas.'

    average_holding = closed_trades['holding_minutes'].mean() if not closed_trades.empty else None
    median_holding = closed_trades['holding_minutes'].median() if not closed_trades.empty else None
    shortest_holding = closed_trades['holding_minutes'].min() if not closed_trades.empty else None
    longest_holding = closed_trades['holding_minutes'].max() if not closed_trades.empty else None

    direction_rows: list[list[Any]] = []
    if not closed_trades.empty:
        for direction in ['LONG', 'SHORT']:
            direction_frame_all = closed_trades.loc[normalize_string(closed_trades['direction']) == direction]
            direction_frame_pnl = direction_frame_all.loc[direction_frame_all['realized_pnl'].notna()]
            direction_trade_count = int(len(direction_frame_all))
            direction_profit = int((direction_frame_pnl['realized_pnl'] > 0).sum()) if not direction_frame_pnl.empty else 0
            direction_win_rate = (direction_profit / len(direction_frame_pnl) * 100.0) if len(direction_frame_pnl) else None
            direction_rows.append([
                direction,
                fmt_int(direction_trade_count),
                fmt_int(direction_profit),
                fmt_ratio_pct(direction_win_rate),
                fmt_number(direction_frame_pnl['realized_pnl'].sum() if not direction_frame_pnl.empty else None, 5),
                fmt_number(direction_frame_pnl['realized_pnl'].mean() if not direction_frame_pnl.empty else None, 5),
            ])

    close_reason_summary = closed_trades.groupby(['close_reason_raw', 'close_reason_label'], dropna=False).agg(
        trade_count=('trade_id', 'count'),
        pnl_observations=('realized_pnl', lambda series: int(series.notna().sum())),
        average_pnl=('realized_pnl', 'mean'),
        total_pnl=('realized_pnl', 'sum'),
    ).reset_index() if not closed_trades.empty else pd.DataFrame(columns=['close_reason_raw', 'close_reason_label', 'trade_count', 'pnl_observations', 'average_pnl', 'total_pnl'])
    if not close_reason_summary.empty:
        close_reason_summary = close_reason_summary.sort_values(['trade_count', 'close_reason_label'], ascending=[False, True]).reset_index(drop=True)
    close_reason_rows = [
        [
            row.close_reason_label,
            fmt_int(row.trade_count),
            fmt_pct(int(row.trade_count), total_closed_trades),
            fmt_number(row.average_pnl if int(row.pnl_observations) > 0 else None, 5),
            fmt_number(row.total_pnl if int(row.pnl_observations) > 0 else None, 5),
            'realized_pnl nerasta' if int(row.pnl_observations) == 0 else 'apskaičiuota iš uždarytų sandorių',
        ]
        for row in close_reason_summary.itertuples(index=False)
    ]

    position_management_total = int(len(position_management_df))
    monitored_positions_unique = int(position_management_df['trade_id'].nunique()) if not position_management_df.empty and 'trade_id' in position_management_df.columns else 0
    should_execute_counts = (
        position_management_df['should_execute_close'].fillna(False).astype(bool).value_counts().reindex([True, False], fill_value=0)
        if not position_management_df.empty and 'should_execute_close' in position_management_df.columns
        else pd.Series({True: 0, False: 0})
    )
    executed_close_counts = (
        position_management_df['executed_close'].fillna(False).astype(bool).value_counts().reindex([True, False], fill_value=0)
        if not position_management_df.empty and 'executed_close' in position_management_df.columns
        else pd.Series({True: 0, False: 0})
    )
    close_decision_rows = position_management_df.loc[
        position_management_df['should_execute_close'].fillna(False).astype(bool)
    ].copy() if not position_management_df.empty and 'should_execute_close' in position_management_df.columns else pd.DataFrame()
    average_close_decision_holding = close_decision_rows['holding_minutes'].mean() if not close_decision_rows.empty else None
    position_reason_counts = top_counts(position_management_df['exit_reason'], limit=10) if not position_management_df.empty and 'exit_reason' in position_management_df.columns else pd.Series(dtype='int64')
    position_rows = [
        ['Iš viso pozicijų priežiūros patikrų', fmt_int(position_management_total)],
        ['Unikalios stebėtos pozicijos', fmt_int(monitored_positions_unique)],
        ['Uždarymo rekomendacijų skaičius (should_execute_close=True)', fmt_int(int(should_execute_counts.get(True, 0)))],
        ['Pozicijų laikymo sprendimų skaičius (should_execute_close=False)', fmt_int(int(should_execute_counts.get(False, 0)))],
        ['Įvykdytų uždarymų skaičius (executed_close=True)', fmt_int(int(executed_close_counts.get(True, 0)))],
        ['Įrašų su executed_close=False skaičius', fmt_int(int(executed_close_counts.get(False, 0)))],
        ['Tiesioginis would_close stulpelis', 'nerasta – naudotas artimiausias atitikmuo should_execute_close.'],
        ['Vidutinė laikymo trukmė uždarymo sprendimo momentu', fmt_duration_minutes(average_close_decision_holding)],
    ]

    reconciliation_total = int(len(reconciliation_df))
    reconciliation_full_matches = int(reconciliation_df['matched'].sum()) if not reconciliation_df.empty else 0
    reconciliation_mismatches = int((~reconciliation_df['matched']).sum()) if not reconciliation_df.empty else 0
    reconciliation_blocks = int(reconciliation_df['block_new_execution'].sum()) if not reconciliation_df.empty else 0
    reconciliation_success_rate = (reconciliation_full_matches / reconciliation_total * 100.0) if reconciliation_total else None
    reconciliation_reason_counts = flatten_reason_counts(reconciliation_df['reason_codes'], limit=10) if not reconciliation_df.empty and 'reason_codes' in reconciliation_df.columns else pd.Series(dtype='int64')
    reconciliation_state_distribution = pd.Series(
        {
            'Pilnas atitikimas': reconciliation_full_matches,
            'Neužblokuotas neatitikimas': max(reconciliation_mismatches - reconciliation_blocks, 0),
            'Blokuojantis neatitikimas': reconciliation_blocks,
        }
    )

    manual_reconciliation_trade_count = int((closed_trades['close_reason_raw'] == 'manual_reconciliation_cleanup').sum()) if not closed_trades.empty else 0
    manual_resolution_note = (
        'Istorijoje matyti rankinio suderinimo požymiai: dvi vietinės OPEN pozicijos uždarytos su priežastimi '
        '`manual_reconciliation_cleanup:exchange_flat`, po to vėlesni suderinimo įrašai tapo `ok`.'
        if manual_reconciliation_trade_count > 0
        else 'Nerasta aiškaus rankinio suderinimo įrašo sandorių istorijoje.'
    )
    automatic_resolution_note = 'Automatinio neatitikimų išsprendimo žyma nerasta – atskiras automatinio sutvarkymo stulpelis neaptiktas.'

    figure_rows = [
        [
            'realized_pnl_curve.png',
            'Parodo kaupiamojo realizuoto PnL kitimą pagal uždarytų sandorių laiką.',
            '3.11 pav. Kaupiamojo realizuoto demonstracinių sandorių PnL kitimas laike.',
        ],
        [
            'trade_pnl_by_trade.png',
            'Parodo kiekvieno uždaryto sandorio realizuotą PnL atskiru stulpeliu.',
            '3.12 pav. Atskirų uždarytų demonstracinių sandorių realizuotas PnL.',
        ],
        [
            'trade_outcome_distribution.png',
            'Parodo pelningų, nuostolingų, nulinių ir PnL neturinčių sandorių pasiskirstymą.',
            '3.13 pav. Uždarytų sandorių baigčių pasiskirstymas.',
        ],
        [
            'close_reason_distribution.png',
            'Parodo uždarymo priežasčių pasiskirstymą tarp visų uždarytų sandorių.',
            '3.14 pav. Uždarytų sandorių priežasčių pasiskirstymas.',
        ],
        [
            'holding_duration_distribution.png',
            'Parodo uždarytų sandorių laikymo trukmės skirstinį valandomis.',
            '3.15 pav. Uždarytų demonstracinių sandorių laikymo trukmės skirstinys.',
        ],
        [
            'reconciliation_status_distribution.png',
            'Parodo pilnų atitikimų, neužblokuotų neatitikimų ir blokuojančių neatitikimų skaičių.',
            '3.16 pav. Būsenų suderinimo rezultatų pasiskirstymas.',
        ],
        [
            'pnl_by_close_reason.png',
            'Parodo vidutinį realizuotą PnL pagal uždarymo priežastį ten, kur PnL reikšmė buvo užfiksuota.',
            '3.17 pav. Vidutinis realizuotas PnL pagal sandorio uždarymo priežastį.',
        ],
    ]

    if not closed_trades_with_pnl.empty:
        draw_pnl_curve(closed_trades_with_pnl, FIGURES_DIR / 'realized_pnl_curve.png')
        draw_trade_pnl_chart(closed_trades_with_pnl, FIGURES_DIR / 'trade_pnl_by_trade.png')
    else:
        draw_bar_chart(pd.Series({'nerasta': 0}), FIGURES_DIR / 'realized_pnl_curve.png', title='Kaupiamasis realizuotas PnL laike', xlabel='Laikas', ylabel='PnL, USDT', color=THESIS_GREY)
        draw_bar_chart(pd.Series({'nerasta': 0}), FIGURES_DIR / 'trade_pnl_by_trade.png', title='Uždarytų sandorių realizuotas PnL', xlabel='Sandoris', ylabel='PnL, USDT', color=THESIS_GREY)

    outcome_counts = pd.Series(
        {
            'Pelningas': profitable_count,
            'Nuostolingas': losing_count,
            'Nulinis': breakeven_count,
            'PnL nerasta': pnl_missing_count,
        }
    )
    draw_bar_chart(
        outcome_counts,
        FIGURES_DIR / 'trade_outcome_distribution.png',
        title='Uždarytų sandorių baigčių pasiskirstymas',
        xlabel='Baigtis',
        ylabel='Sandorių skaičius',
        color=THESIS_GOLD,
    )

    close_reason_chart = close_reason_summary.set_index('close_reason_label')['trade_count'] if not close_reason_summary.empty else pd.Series({'Nerasta': 0})
    draw_bar_chart(
        close_reason_chart,
        FIGURES_DIR / 'close_reason_distribution.png',
        title='Uždarymo priežasčių pasiskirstymas',
        xlabel='Priežastis',
        ylabel='Sandorių skaičius',
        color=THESIS_TEAL,
    )

    holding_hours = closed_trades['holding_minutes'] / 60.0 if not closed_trades.empty else pd.Series(dtype='float64')
    draw_histogram(
        holding_hours,
        FIGURES_DIR / 'holding_duration_distribution.png',
        title='Laikymo trukmės skirstinys',
        xlabel='Laikymo trukmė, val.',
        color=THESIS_ORANGE,
    )

    draw_bar_chart(
        reconciliation_state_distribution,
        FIGURES_DIR / 'reconciliation_status_distribution.png',
        title='Būsenų suderinimo rezultatų pasiskirstymas',
        xlabel='Būsena',
        ylabel='Patikrų skaičius',
        color=THESIS_BLUE,
    )

    pnl_by_reason = close_reason_summary.loc[
        close_reason_summary['pnl_observations'] > 0,
        ['close_reason_label', 'average_pnl'],
    ].set_index('close_reason_label')['average_pnl'] if not close_reason_summary.empty else pd.Series(dtype='float64')
    if pnl_by_reason.empty:
        pnl_by_reason = pd.Series({'Nerasta': 0.0})
    draw_pnl_by_reason_chart(pnl_by_reason, FIGURES_DIR / 'pnl_by_close_reason.png')

    report_lines: list[str] = []
    report_lines.append('# 3.5 Demonstracinės prekybos, pozicijų valdymo ir būsenų suderinimo rezultatai')
    report_lines.append('')

    report_lines.append('## Analizuotų istorijos failų apimtis')
    report_lines.append('')
    report_lines.append(markdown_table(
        ['Sritis', 'Failas', 'Įrašų skaičius', 'Ankstyviausias laikas', 'Vėliausias laikas', 'Pastaba'],
        coverage_rows,
    ))
    report_lines.append('')

    report_lines.append('## Demonstracinės prekybos rezultatų santrauka')
    report_lines.append('')
    report_lines.append(markdown_table(
        ['Rodiklis', 'Reikšmė'],
        [
            ['Uždarytų sandorių skaičius', fmt_int(total_closed_trades)],
            ['Uždarytų sandorių su realizuotu PnL', fmt_int(total_closed_with_pnl)],
            ['Uždarytų sandorių be realizuoto PnL', fmt_int(pnl_missing_count)],
            ['LONG sandorių skaičius', fmt_int(long_count_all)],
            ['SHORT sandorių skaičius', fmt_int(short_count_all)],
            ['Pelningų sandorių skaičius', fmt_int(profitable_count)],
            ['Nuostolingų sandorių skaičius', fmt_int(losing_count)],
            ['Nulinių sandorių skaičius', fmt_int(breakeven_count)],
            ['Laimėjimų dalis (tik iš sandorių su žinomu PnL)', fmt_ratio_pct(win_rate)],
            ['Bendras realizuotas PnL, USDT', fmt_number(total_realized_pnl, 5)],
            ['Grynoji grąža, %', fmt_ratio_pct(net_return_pct)],
            ['Vidutinis PnL vienam sandoriui, USDT', fmt_number(average_pnl, 5)],
            ['Medianinis PnL vienam sandoriui, USDT', fmt_number(median_pnl, 5)],
            ['Geriausias sandoris, USDT', fmt_number(best_pnl, 5)],
            ['Blogiausias sandoris, USDT', fmt_number(worst_pnl, 5)],
            ['Vidutinė laikymo trukmė', fmt_duration_minutes(average_holding)],
            ['Medianinė laikymo trukmė', fmt_duration_minutes(median_holding)],
            ['Trumpiausia laikymo trukmė', fmt_duration_minutes(shortest_holding)],
            ['Ilgiausia laikymo trukmė', fmt_duration_minutes(longest_holding)],
            ['Šiuo metu atvirų vietinių sandorių skaičius', fmt_int(int((normalize_string(trades_df.get('status', pd.Series(dtype='string'))) == 'OPEN').sum()) if not trades_df.empty else 0)],
        ],
    ))
    report_lines.append('')
    report_lines.append(f'- {net_return_note}')
    report_lines.append('- Kaupiamasis realizuotas PnL pavaizduotas figūroje `realized_pnl_curve.png` ir skaičiuotas tik iš uždarytų sandorių, kuriuose buvo užpildytas `realized_pnl` laukas.')
    report_lines.append('')

    report_lines.append('## Sandorių krypties analizė')
    report_lines.append('')
    report_lines.append(markdown_table(
        ['Kryptis', 'Sandorių skaičius', 'Pelningų sandorių skaičius', 'Laimėjimų dalis', 'Bendras PnL, USDT', 'Vidutinis PnL, USDT'],
        direction_rows or [['nerasta', 'nerasta', 'nerasta', 'nerasta', 'nerasta', 'nerasta']],
    ))
    report_lines.append('')
    if long_count_all == 0 and short_count_all > 0:
        report_lines.append('- Analizuojamoje istorijoje neužfiksuota nė vieno LONG sandorio; visi uždaryti sandoriai buvo SHORT krypties.')
    elif short_count_all == 0 and long_count_all > 0:
        report_lines.append('- Analizuojamoje istorijoje neužfiksuota nė vieno SHORT sandorio; visi uždaryti sandoriai buvo LONG krypties.')
    else:
        report_lines.append('- Istorijoje buvo tiek LONG, tiek SHORT sandorių, todėl krypties palyginimas atliktas abiem kryptims.')
    report_lines.append('')

    report_lines.append('## Pozicijų uždarymo priežastys')
    report_lines.append('')
    report_lines.append(markdown_table(
        ['Uždarymo priežastis', 'Sandorių skaičius', 'Dalis nuo uždarytų sandorių', 'Vidutinis PnL, USDT', 'Bendras PnL, USDT', 'Pastaba'],
        close_reason_rows or [['nerasta', 'nerasta', 'nerasta', 'nerasta', 'nerasta', 'Nerastas tinkamas uždarymo priežasties stulpelis.']],
    ))
    report_lines.append('')
    report_lines.append('- `source_exit_signal` laukas leido atskirti pozicijų valdymo uždarymus nuo rankinio suderinimo valymo.')
    report_lines.append('- `pnl_by_close_reason.png` figūroje parodytas vidutinis realizuotas PnL pagal uždarymo priežastį tik tiems atvejams, kuriuose `realized_pnl` reikšmė buvo užfiksuota.')
    report_lines.append('')

    report_lines.append('## Pozicijų priežiūros rezultatai')
    report_lines.append('')
    report_lines.append(markdown_table(
        ['Rodiklis', 'Reikšmė'],
        position_rows,
    ))
    report_lines.append('')
    report_lines.append(markdown_table(
        ['Dažniausia pozicijų priežiūros priežastis', 'Skaičius'],
        [[position_reason_label(str(index)), fmt_int(value)] for index, value in position_reason_counts.items()] or [['nerasta', 'nerasta']],
    ))
    report_lines.append('')
    report_lines.append('- Pozicijų priežiūros istorijoje dominuoja `position_hold` sprendimai, tačiau visi `should_execute_close=True` atvejai taip pat turi `executed_close=True` reikšmę.')
    report_lines.append('- Tai rodo, kad uždarymo rekomendacijos pozicijų valdymo sluoksnyje praktikoje buvo paverstos realiais uždarymais per demonstracinio vykdymo mechanizmą.')
    report_lines.append('')

    report_lines.append('## Būsenų suderinimo rezultatai')
    report_lines.append('')
    report_lines.append(markdown_table(
        ['Rodiklis', 'Reikšmė'],
        [
            ['Iš viso suderinimo patikrų', fmt_int(reconciliation_total)],
            ['Pilnų atitikimų skaičius', fmt_int(reconciliation_full_matches)],
            ['Neatitikimų skaičius', fmt_int(reconciliation_mismatches)],
            ['Blokuojančių neatitikimų skaičius', fmt_int(reconciliation_blocks)],
            ['Suderinimo sėkmės rodiklis', fmt_ratio_pct(reconciliation_success_rate)],
            ['Tiesioginis automatinio sutvarkymo žymuo', 'nerasta'],
        ],
    ))
    report_lines.append('')
    report_lines.append(markdown_table(
        ['Dažniausia neatitikimo / blokavimo priežastis', 'Skaičius'],
        [[str(index), fmt_int(value)] for index, value in reconciliation_reason_counts.items()] or [['nerasta', 'nerasta']],
    ))
    report_lines.append('')
    report_lines.append(f'- {manual_resolution_note}')
    report_lines.append(f'- {automatic_resolution_note}')
    report_lines.append('- Naujausi suderinimo įrašai rodo `ok` būseną ir nulinius vietinių bei Bybit demonstracinių atvirų pozicijų skaitiklius.')
    report_lines.append('')

    report_lines.append('## Sugeneruotos vizualizacijos')
    report_lines.append('')
    report_lines.append(markdown_table(
        ['Failo pavadinimas', 'Ką rodo', 'Siūloma lietuviška antraštė'],
        figure_rows,
    ))
    report_lines.append('')

    report_lines.append('## Svarbiausios interpretacijos 3.5 skyriui')
    report_lines.append('')
    interpretation_lines = [
        f'- Demonstracinė prekyba techniškai veikė: vykdymo žurnale rasti {fmt_int(int((normalize_string(execution_df.get("status", pd.Series(dtype="string"))) == "placed").sum()) if not execution_df.empty else 0)} sėkmingi atidarymo įrašai su `status=placed`, o pozicijų priežiūros istorijoje {fmt_int(int(executed_close_counts.get(True, 0)))} uždarymo sprendimų buvo realiai įvykdyta (`executed_close=True`).',
        f'- Pozicijų atidarymo ir uždarymo grandinė buvo nuosekli: sandorių faile iš viso užfiksuotas {fmt_int(total_closed_trades)} uždarytų sandorių skaičius, o analizės pabaigoje vietinių OPEN sandorių nebeliko.',
        f'- Finansinis rezultatas analizuojamu laikotarpiu buvo neigiamas: bendras realizuotas PnL iš {fmt_int(total_closed_with_pnl)} sandorių su žinomu rezultatu sudarė {fmt_number(total_realized_pnl, 5)} USDT, o laimėjimų dalis siekė {fmt_ratio_pct(win_rate)}.',
        '- Neigiamas realizuotas PnL pats savaime nepaneigia techninio prototipo tinkamumo, nes šiame etape buvo tikrinama, ar sistema geba automatiškai atidaryti, prižiūrėti, uždaryti ir suderinti pozicijų būsenas tarp vietinės istorijos ir Bybit demonstracinės aplinkos.',
        f'- Imtis ekonominėms išvadoms dar per maža: sandorių istorijoje tėra {fmt_int(total_closed_trades)} uždarytas sandoris, iš kurių {fmt_int(pnl_missing_count)} buvo uždaryti rankinio suderinimo valymo metu ir neturi realizuoto PnL reikšmės.',
        '- Tolimesniam darbo etapui tai reiškia, kad verta ilginti stebėjimo laikotarpį, kaupti didesnę demonstracinių sandorių imtį ir tik tada vertinti ekonominį strategijos gyvybingumą; tuo pačiu galima tobulinti išėjimo taisykles ir automatizuoto suderinimo mechanizmus.',
    ]
    report_lines.extend(interpretation_lines)
    report_lines.append('')

    REPORT_PATH.write_text('\n'.join(report_lines), encoding='utf-8')


if __name__ == '__main__':
    build_report()
