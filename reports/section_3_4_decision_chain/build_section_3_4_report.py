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
REPORT_DIR = ROOT / 'reports' / 'section_3_4_decision_chain'
FIGURES_DIR = REPORT_DIR / 'figures'
REPORT_PATH = REPORT_DIR / 'section_3_4_report.txt'

EXECUTABLE_ACTIONS = {'OPEN_LONG', 'OPEN_SHORT'}
THESIS_BLUE = '#3E6EA8'
THESIS_TEAL = '#3EA8A1'
THESIS_GOLD = '#C9992E'
THESIS_RED = '#B85450'
THESIS_GREY = '#7F8790'


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


def load_frame(history_file: HistoryFile) -> pd.DataFrame | None:
    if history_file.path is None or not history_file.path.exists():
        return None
    return pd.read_parquet(history_file.path)


def to_ts(value: Any) -> pd.Timestamp | None:
    parsed = pd.to_datetime(value, utc=True, errors='coerce')
    if pd.isna(parsed):
        return None
    return pd.Timestamp(parsed)


def ts_series(frame: pd.DataFrame | None, column: str) -> pd.Series:
    if frame is None or column not in frame.columns:
        return pd.Series(dtype='datetime64[ns, UTC]')
    series = pd.to_datetime(frame[column], utc=True, errors='coerce')
    return series.dropna()


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
        return '0.00%'
    return f'{(float(part) / float(total)) * 100:.{digits}f}%'


def markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    header_line = '| ' + ' | '.join(headers) + ' |'
    separator = '| ' + ' | '.join(['---'] * len(headers)) + ' |'
    body_lines = ['| ' + ' | '.join(str(cell) for cell in row) + ' |' for row in rows]
    return '\n'.join([header_line, separator, *body_lines])


def prob_summary(series: pd.Series) -> dict[str, str]:
    numeric = pd.to_numeric(series, errors='coerce').dropna()
    if numeric.empty:
        return {'min': 'nerasta', 'mean': 'nerasta', 'median': 'nerasta', 'max': 'nerasta'}
    return {
        'min': fmt_number(numeric.min(), 6),
        'mean': fmt_number(numeric.mean(), 6),
        'median': fmt_number(numeric.median(), 6),
        'max': fmt_number(numeric.max(), 6),
    }


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
                    return [str(item).strip() for item in parsed if str(item).strip() and str(item).strip() != '[]']
            except Exception:
                continue
        return [text]
    return [str(value).strip()]


def top_counts(series: pd.Series, limit: int = 10, drop_empty: bool = True) -> pd.Series:
    normalized = series.astype('string')
    if drop_empty:
        normalized = normalized.loc[normalized.notna() & (normalized.str.strip() != '')]
    if normalized.empty:
        return pd.Series(dtype='int64')
    return normalized.value_counts().head(limit)


def flatten_reason_counts(values: pd.Series, limit: int = 10, exclude: set[str] | None = None) -> pd.Series:
    exclude = exclude or set()
    counter: dict[str, int] = {}
    for value in values.tolist():
        for item in parse_reason_list(value):
            if item in exclude:
                continue
            counter[item] = counter.get(item, 0) + 1
    if not counter:
        return pd.Series(dtype='int64')
    return pd.Series(counter).sort_values(ascending=False).head(limit)


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
    max_value = values.max() if len(values) else 0
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


def draw_horizontal_bar_chart(
    series: pd.Series,
    output_path: Path,
    *,
    title: str,
    xlabel: str,
    color: str,
) -> None:
    ordered = series.sort_values(ascending=True)
    plt.figure(figsize=(10, 6))
    ax = plt.gca()
    bars = ax.barh(ordered.index.astype(str), ordered.astype(float), color=color, edgecolor='black', linewidth=0.6)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.grid(axis='x', linestyle='--', alpha=0.35)
    ax.set_axisbelow(True)
    max_value = ordered.max() if len(ordered) else 0
    for bar, value in zip(bars, ordered.astype(float), strict=False):
        ax.text(
            bar.get_width() + max(max_value * 0.015, 0.5),
            bar.get_y() + bar.get_height() / 2,
            f'{int(value)}',
            va='center',
            fontsize=10,
        )
    plt.tight_layout()
    plt.savefig(output_path, dpi=200)
    plt.close()


def dedupe_latest(frame: pd.DataFrame, key_columns: list[str], sort_column: str) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    deduped = frame.copy()
    deduped[sort_column] = pd.to_datetime(deduped[sort_column], utc=True, errors='coerce')
    deduped = deduped.sort_values(sort_column, ascending=True)
    return deduped.drop_duplicates(subset=key_columns, keep='last').reset_index(drop=True)


def status_counts_automation(frame: pd.DataFrame) -> dict[str, int]:
    if frame.empty or 'status' not in frame.columns:
        return {'success': 0, 'skipped': 0, 'failed': 0}
    normalized = frame['status'].astype('string').fillna('')
    return {
        'success': int((normalized == 'success').sum()),
        'skipped': int((normalized == 'skipped').sum()),
        'failed': int((normalized == 'failed').sum()),
    }


def classify_risk_state(frame: pd.DataFrame) -> pd.Series:
    if frame.empty:
        return pd.Series(dtype='string')
    requested = frame.get('requested_action', pd.Series(index=frame.index, dtype='string')).astype('string')
    allowed = frame.get('allowed', pd.Series(index=frame.index, dtype='boolean')).astype('boolean')
    state = pd.Series(index=frame.index, dtype='string')
    state.loc[allowed.fillna(False)] = 'allowed'
    state.loc[~allowed.fillna(False) & requested.isin(list(EXECUTABLE_ACTIONS))] = 'blocked'
    state.loc[state.isna()] = 'skipped'
    return state


def unique_execution_success(frame: pd.DataFrame) -> tuple[int, int]:
    if frame.empty:
        return 0, 0
    entry_frame = frame.copy()
    if 'signal_type' in entry_frame.columns:
        signal_type = entry_frame['signal_type'].astype('string').fillna('')
        entry_frame = entry_frame.loc[~signal_type.str.startswith('CLOSE_')]
    if entry_frame.empty:
        return 0, 0
    keyed = dedupe_latest(entry_frame, ['execution_key'], 'attempted_at')
    attempts = len(keyed)
    status = keyed.get('status', pd.Series(index=keyed.index, dtype='string')).astype('string')
    success = keyed.get('success', pd.Series(index=keyed.index, dtype='boolean')).astype('boolean').fillna(False)
    order_id_present = keyed.get('exchange_order_id', pd.Series(index=keyed.index, dtype='string')).astype('string').notna()
    successful = int((((status == 'placed') & success) | ((status == 'placed') & order_id_present)).sum())
    return attempts, successful


def execution_actual_demo_count(frame: pd.DataFrame) -> tuple[int, int]:
    if frame.empty:
        return 0, 0
    all_actual = int(frame['exchange_order_id'].notna().sum()) if 'exchange_order_id' in frame.columns else 0
    entry_frame = frame.copy()
    if 'signal_type' in entry_frame.columns:
        signal_type = entry_frame['signal_type'].astype('string').fillna('')
        entry_frame = entry_frame.loc[~signal_type.str.startswith('CLOSE_')]
    entry_actual = int(entry_frame['exchange_order_id'].notna().sum()) if 'exchange_order_id' in entry_frame.columns else 0
    return all_actual, entry_actual


def build_report() -> None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    files = {
        'signals': find_single('signals', ['signals/*signal_history*.parquet', 'signals/*signals*.parquet']),
        'strategy': find_single('strategy', ['strategy/*strategy_history*.parquet', 'strategy/*strategy*.parquet']),
        'risk': find_single('risk', ['risk/*risk_history*.parquet', 'risk/*risk*.parquet']),
        'automation': find_single('automation', ['automation/*automation_cycles*.parquet', 'automation/*cycle*.parquet']),
        'execution': find_single('execution', ['execution/*execution_log*.parquet', 'execution/*execution*.parquet']),
    }

    signal_df = load_frame(files['signals'])
    strategy_df = load_frame(files['strategy'])
    risk_df = load_frame(files['risk'])
    automation_df = load_frame(files['automation'])
    execution_df = load_frame(files['execution'])

    if signal_df is None:
        signal_df = pd.DataFrame()
    if strategy_df is None:
        strategy_df = pd.DataFrame()
    if risk_df is None:
        risk_df = pd.DataFrame()
    if automation_df is None:
        automation_df = pd.DataFrame()
    if execution_df is None:
        execution_df = pd.DataFrame()

    signal_time = ts_series(signal_df, 'predicted_for_timestamp')
    strategy_time = ts_series(strategy_df, 'predicted_for_timestamp')
    risk_time = ts_series(risk_df, 'predicted_for_timestamp')
    automation_time = ts_series(automation_df, 'bar_timestamp')
    execution_time = ts_series(execution_df, 'attempted_at')

    coverage_rows = []
    coverage_specs = [
        ('Signalų istorija', files['signals'], signal_df, 'predicted_for_timestamp', signal_time),
        ('Strategijos istorija', files['strategy'], strategy_df, 'predicted_for_timestamp', strategy_time),
        ('Rizikos istorija', files['risk'], risk_df, 'predicted_for_timestamp', risk_time),
        ('Automatiniai ciklai', files['automation'], automation_df, 'bar_timestamp', automation_time),
        ('Vykdymo žurnalas', files['execution'], execution_df, 'attempted_at', execution_time),
    ]
    for label, history_file, frame, time_column, series in coverage_specs:
        coverage_rows.append([
            label,
            'nerasta' if history_file.path is None else history_file.path.relative_to(ROOT).as_posix(),
            fmt_int(len(frame)),
            time_column,
            iso_or_nerasta(series.min() if not series.empty else None),
            iso_or_nerasta(series.max() if not series.empty else None),
        ])

    signal_counts = (
        signal_df['signal_type'].astype('string').value_counts().reindex(['BUY', 'SELL', 'HOLD'], fill_value=0)
        if 'signal_type' in signal_df.columns
        else pd.Series({'BUY': 0, 'SELL': 0, 'HOLD': 0})
    )
    signal_total = int(len(signal_df))
    signal_prob = prob_summary(signal_df['probability_up']) if 'probability_up' in signal_df.columns else prob_summary(pd.Series(dtype='float64'))
    signal_confidence_note = 'nerasta – signalų istorijoje nėra confidence_bucket stulpelio.'
    signal_columns = ', '.join(signal_df.columns.tolist()) if not signal_df.empty else 'nerasta'

    strategy_counts = top_counts(strategy_df['action'], limit=20) if 'action' in strategy_df.columns else pd.Series(dtype='int64')
    strategy_total = int(len(strategy_df))
    strategy_reason_counts = top_counts(strategy_df['action_reason'], limit=10) if 'action_reason' in strategy_df.columns else pd.Series(dtype='int64')
    strategy_confidence_counts = top_counts(strategy_df['confidence_bucket'], limit=20) if 'confidence_bucket' in strategy_df.columns else pd.Series(dtype='int64')

    strategy_signal_window_note = 'nerasta'
    candidate_actions = int(strategy_counts.get('OPEN_LONG', 0) + strategy_counts.get('OPEN_SHORT', 0))
    candidate_conversion_note = 'nerasta'
    if not signal_time.empty and not strategy_time.empty:
        common_start = max(signal_time.min(), strategy_time.min())
        common_end = min(signal_time.max(), strategy_time.max())
        overlap_signals = signal_df.copy()
        overlap_signals['predicted_for_timestamp'] = pd.to_datetime(
            overlap_signals['predicted_for_timestamp'], utc=True, errors='coerce'
        )
        overlap_signals = overlap_signals.loc[
            overlap_signals['predicted_for_timestamp'].between(common_start, common_end, inclusive='both')
        ]
        overlap_non_hold = int(overlap_signals['signal_type'].astype('string').isin(['BUY', 'SELL']).sum())
        strategy_signal_window_note = (
            f'Persidengiančio strategijos ir signalų laikotarpio langas: '
            f'{common_start.isoformat()} – {common_end.isoformat()}.'
        )
        candidate_conversion_note = (
            f'Iš {overlap_non_hold} ne HOLD signalų persidengiančiame lange '
            f'{candidate_actions} virto kandidatiniais veiksmais OPEN_LONG arba OPEN_SHORT '
            f'({fmt_pct(candidate_actions, overlap_non_hold)}).'
        )

    risk_total = int(len(risk_df))
    risk_state = classify_risk_state(risk_df)
    risk_state_counts = risk_state.value_counts().reindex(['allowed', 'blocked', 'skipped'], fill_value=0)
    approved_action_counts = top_counts(risk_df['approved_action'], limit=20) if 'approved_action' in risk_df.columns else pd.Series(dtype='int64')
    blocked_reason_counts = flatten_reason_counts(
        risk_df.loc[risk_state == 'blocked', 'reason_codes'] if 'reason_codes' in risk_df.columns else pd.Series(dtype='object'),
        limit=10,
        exclude={'RISK_APPROVED', 'NON_EXECUTABLE_ACTION'},
    )
    if blocked_reason_counts.empty:
        blocked_reason_counts = pd.Series({'nerasta': 0})
    allowed_numeric = risk_df.loc[risk_df.get('allowed', pd.Series(dtype='boolean')).fillna(False)]
    allowed_notional = prob_summary(allowed_numeric['order_notional_usdt']) if 'order_notional_usdt' in allowed_numeric.columns else prob_summary(pd.Series(dtype='float64'))
    allowed_leverage = prob_summary(allowed_numeric['approved_leverage']) if 'approved_leverage' in allowed_numeric.columns else prob_summary(pd.Series(dtype='float64'))

    automation_total = int(len(automation_df))
    automation_status = status_counts_automation(automation_df)
    automation_no_trade = int((~automation_df.get('execution_attempted', pd.Series(dtype='boolean')).fillna(False)).sum()) if not automation_df.empty else 0
    automation_attempts = int(automation_df.get('execution_attempted', pd.Series(dtype='boolean')).fillna(False).sum()) if not automation_df.empty else 0
    automation_success_exec = int(((automation_df.get('execution_attempted', pd.Series(dtype='boolean')).fillna(False)) & (automation_df.get('execution_status', pd.Series(dtype='string')).astype('string') == 'ok')).sum()) if not automation_df.empty else 0
    automation_reason_values: list[str] = []
    if not automation_df.empty:
        for _, row in automation_df.iterrows():
            skip_reason = row.get('execution_skipped_reason')
            error_message = row.get('error_message')
            if isinstance(skip_reason, str) and skip_reason.strip():
                automation_reason_values.append(skip_reason.strip())
            elif isinstance(error_message, str) and error_message.strip():
                automation_reason_values.append(error_message.strip())
    automation_reason_counts = top_counts(pd.Series(automation_reason_values, dtype='string'), limit=10, drop_empty=True)

    execution_total = int(len(execution_df))
    execution_status_counts = top_counts(execution_df['status'], limit=20) if 'status' in execution_df.columns else pd.Series(dtype='int64')
    execution_reason_values: list[str] = []
    if not execution_df.empty:
        for _, row in execution_df.iterrows():
            error_message = row.get('error_message')
            response_message = row.get('exchange_response_message')
            status_value = str(row.get('status') or '')
            if isinstance(error_message, str) and error_message.strip():
                execution_reason_values.append(f'{status_value}: {error_message.strip()}')
            elif status_value in {'failed', 'rejected'} and isinstance(response_message, str) and response_message.strip():
                execution_reason_values.append(f'{status_value}: {response_message.strip()}')
    execution_reason_counts = top_counts(pd.Series(execution_reason_values, dtype='string'), limit=10, drop_empty=True)
    execution_actual_all, execution_actual_entries = execution_actual_demo_count(execution_df)
    unique_entry_attempts, unique_successful_entries = unique_execution_success(execution_df)

    signal_unique = dedupe_latest(signal_df, ['predicted_for_timestamp', 'model_version'], 'generated_at') if not signal_df.empty else pd.DataFrame()
    strategy_unique = dedupe_latest(strategy_df, ['predicted_for_timestamp', 'strategy_version'], 'decided_at') if not strategy_df.empty else pd.DataFrame()
    risk_unique = dedupe_latest(risk_df, ['predicted_for_timestamp', 'strategy_version'], 'decided_at') if not risk_df.empty else pd.DataFrame()
    execution_entry_unique = pd.DataFrame()
    if not execution_df.empty:
        execution_entry_unique = execution_df.copy()
        if 'signal_type' in execution_entry_unique.columns:
            signal_type = execution_entry_unique['signal_type'].astype('string').fillna('')
            execution_entry_unique = execution_entry_unique.loc[~signal_type.str.startswith('CLOSE_')]
        if not execution_entry_unique.empty:
            execution_entry_unique = dedupe_latest(execution_entry_unique, ['execution_key'], 'attempted_at')

    funnel_note = 'Piltuvėlio skaičiavimai atlikti tik bendrame signalų, strategijos ir rizikos istorijų laikotarpyje, kad sluoksnių skaičiai būtų palyginami.'
    funnel_rows: list[list[str]] = []
    funnel_counts_for_chart: dict[str, int] = {}
    if signal_unique.empty or strategy_unique.empty or risk_unique.empty:
        funnel_rows = [
            ['Modelio signalai iš viso', 'nerasta', 'Trūksta bent vieno iš signalų, strategijos arba rizikos istorijos failų.'],
            ['Ne HOLD signalai', 'nerasta', 'Trūksta bent vieno iš signalų, strategijos arba rizikos istorijos failų.'],
            ['Strategijos OPEN veiksmai', 'nerasta', 'Trūksta bent vieno iš signalų, strategijos arba rizikos istorijos failų.'],
            ['Rizikos leisti veiksmai', 'nerasta', 'Trūksta bent vieno iš signalų, strategijos arba rizikos istorijos failų.'],
            ['Vykdymo bandymai', 'nerasta', 'Trūksta bent vieno iš signalų, strategijos arba rizikos istorijos failų.'],
            ['Sėkmingi vykdymai', 'nerasta', 'Trūksta bent vieno iš signalų, strategijos arba rizikos istorijos failų.'],
        ]
    else:
        common_start = max(
            pd.to_datetime(signal_unique['predicted_for_timestamp'], utc=True, errors='coerce').dropna().min(),
            pd.to_datetime(strategy_unique['predicted_for_timestamp'], utc=True, errors='coerce').dropna().min(),
            pd.to_datetime(risk_unique['predicted_for_timestamp'], utc=True, errors='coerce').dropna().min(),
        )
        common_end = min(
            pd.to_datetime(signal_unique['predicted_for_timestamp'], utc=True, errors='coerce').dropna().max(),
            pd.to_datetime(strategy_unique['predicted_for_timestamp'], utc=True, errors='coerce').dropna().max(),
            pd.to_datetime(risk_unique['predicted_for_timestamp'], utc=True, errors='coerce').dropna().max(),
        )

        signal_unique['_ts'] = pd.to_datetime(signal_unique['predicted_for_timestamp'], utc=True, errors='coerce')
        strategy_unique['_ts'] = pd.to_datetime(strategy_unique['predicted_for_timestamp'], utc=True, errors='coerce')
        risk_unique['_ts'] = pd.to_datetime(risk_unique['predicted_for_timestamp'], utc=True, errors='coerce')
        if not execution_entry_unique.empty and 'predicted_for_timestamp' in execution_entry_unique.columns:
            execution_entry_unique['_ts'] = pd.to_datetime(
                execution_entry_unique['predicted_for_timestamp'], utc=True, errors='coerce'
            )

        signal_window = signal_unique.loc[signal_unique['_ts'].between(common_start, common_end, inclusive='both')]
        strategy_window = strategy_unique.loc[strategy_unique['_ts'].between(common_start, common_end, inclusive='both')]
        risk_window = risk_unique.loc[risk_unique['_ts'].between(common_start, common_end, inclusive='both')]
        risk_allowed_any = risk_df.copy()
        if not risk_allowed_any.empty:
            risk_allowed_any['predicted_for_timestamp'] = pd.to_datetime(
                risk_allowed_any['predicted_for_timestamp'], utc=True, errors='coerce'
            )
            risk_allowed_any = risk_allowed_any.loc[
                risk_allowed_any['predicted_for_timestamp'].between(common_start, common_end, inclusive='both')
                & risk_allowed_any.get('approved_action', pd.Series(index=risk_allowed_any.index, dtype='string')).astype('string').isin(list(EXECUTABLE_ACTIONS))
                & risk_allowed_any.get('allowed', pd.Series(index=risk_allowed_any.index, dtype='boolean')).fillna(False)
            ]
        execution_window = (
            execution_entry_unique.loc[execution_entry_unique['_ts'].between(common_start, common_end, inclusive='both')]
            if not execution_entry_unique.empty and '_ts' in execution_entry_unique.columns
            else pd.DataFrame()
        )

        model_signals_total = int(len(signal_window))
        non_hold_total = int(signal_window['signal_type'].astype('string').isin(['BUY', 'SELL']).sum()) if 'signal_type' in signal_window.columns else 0
        strategy_open_total = int(strategy_window['action'].astype('string').isin(list(EXECUTABLE_ACTIONS)).sum()) if 'action' in strategy_window.columns else 0
        risk_allowed_predictions = set(risk_allowed_any['predicted_for_timestamp'].dropna().tolist()) if not risk_allowed_any.empty else set()
        risk_allowed_total = len(risk_allowed_predictions)
        if not execution_window.empty and risk_allowed_predictions:
            execution_window = execution_window.loc[
                execution_window['predicted_for_timestamp'].isin(risk_allowed_predictions)
            ]
        else:
            execution_window = pd.DataFrame(columns=execution_window.columns)
        execution_attempt_total = int(execution_window['predicted_for_timestamp'].nunique()) if not execution_window.empty else 0
        execution_success_total = int(
            execution_window.loc[
                execution_window.get('status', pd.Series(index=execution_window.index, dtype='string')).astype('string') == 'placed',
                'predicted_for_timestamp',
            ].nunique()
        ) if not execution_window.empty else 0

        funnel_rows = [
            ['Modelio signalai iš viso', fmt_int(model_signals_total), f'Bendras laikotarpis: {common_start.isoformat()} – {common_end.isoformat()}.'],
            ['Ne HOLD signalai', fmt_int(non_hold_total), f'Dalis nuo modelio signalų: {fmt_pct(non_hold_total, model_signals_total)}.'],
            ['Strategijos OPEN veiksmai', fmt_int(strategy_open_total), f'Dalis nuo ne HOLD signalų: {fmt_pct(strategy_open_total, non_hold_total)}.'],
            ['Rizikos leisti veiksmai', fmt_int(risk_allowed_total), f'Dalis nuo strategijos OPEN veiksmų: {fmt_pct(risk_allowed_total, strategy_open_total)}.'],
            ['Vykdymo bandymai', fmt_int(execution_attempt_total), f'Dalis nuo rizikos leistų veiksmų: {fmt_pct(execution_attempt_total, risk_allowed_total)}.'],
            ['Sėkmingi vykdymai', fmt_int(execution_success_total), f'Dalis nuo vykdymo bandymų: {fmt_pct(execution_success_total, execution_attempt_total)}.'],
        ]
        funnel_counts_for_chart = {
            'Modelio signalai': model_signals_total,
            'Ne HOLD signalai': non_hold_total,
            'Strategijos OPEN': strategy_open_total,
            'Rizikos leisti': risk_allowed_total,
            'Vykdymo bandymai': execution_attempt_total,
            'Sėkmingi vykdymai': execution_success_total,
        }
        funnel_note = (
            f'Piltuvėlis apribotas bendru laikotarpiu {common_start.isoformat()} – {common_end.isoformat()}, '
            'nes signalų istorija prasideda anksčiau nei strategijos ir rizikos istorijos. '
            'Rizikos etapas skaičiuotas pagal unikalius predicted_for_timestamp, kuriems bent kartą buvo gautas allowed=True ir OPEN_* approved_action, '
            'nes rizikos istorija yra append-only ir vėlesni pervertinimai gali pakeisti paskutinę būseną.'
        )

    signal_chart = signal_counts.reindex(['BUY', 'SELL', 'HOLD'], fill_value=0)
    draw_bar_chart(
        signal_chart,
        FIGURES_DIR / 'signal_action_distribution.png',
        title='Signalų pasiskirstymas',
        xlabel='Signalo tipas',
        ylabel='Įrašų skaičius',
        color=THESIS_BLUE,
    )

    strategy_chart = strategy_counts.reindex(
        ['OPEN_LONG', 'OPEN_SHORT', 'HOLD', 'SKIP'],
        fill_value=0,
    )
    draw_bar_chart(
        strategy_chart,
        FIGURES_DIR / 'strategy_action_distribution.png',
        title='Strategijos veiksmų pasiskirstymas',
        xlabel='Strategijos veiksmas',
        ylabel='Įrašų skaičius',
        color=THESIS_TEAL,
    )

    draw_bar_chart(
        risk_state_counts.reindex(['allowed', 'blocked', 'skipped'], fill_value=0),
        FIGURES_DIR / 'risk_decision_distribution.png',
        title='Rizikos sprendimų pasiskirstymas',
        xlabel='Rizikos būsena',
        ylabel='Įrašų skaičius',
        color=THESIS_GOLD,
    )

    draw_bar_chart(
        pd.Series(automation_status).reindex(['success', 'skipped', 'failed'], fill_value=0),
        FIGURES_DIR / 'automation_cycle_status_distribution.png',
        title='Automatinio ciklo būsenų pasiskirstymas',
        xlabel='Ciklo būsena',
        ylabel='Ciklų skaičius',
        color=THESIS_RED,
    )

    if funnel_counts_for_chart:
        draw_horizontal_bar_chart(
            pd.Series(funnel_counts_for_chart),
            FIGURES_DIR / 'decision_funnel.png',
            title='Sprendimų grandinės piltuvėlis',
            xlabel='Įrašų skaičius',
            color=THESIS_BLUE,
        )
    else:
        draw_horizontal_bar_chart(
            pd.Series({'nerasta': 0}),
            FIGURES_DIR / 'decision_funnel.png',
            title='Sprendimų grandinės piltuvėlis',
            xlabel='Įrašų skaičius',
            color=THESIS_GREY,
        )

    draw_horizontal_bar_chart(
        strategy_reason_counts if not strategy_reason_counts.empty else pd.Series({'nerasta': 0}),
        FIGURES_DIR / 'top_strategy_reasons.png',
        title='Dažniausios strategijos priežastys',
        xlabel='Įrašų skaičius',
        color=THESIS_TEAL,
    )

    draw_horizontal_bar_chart(
        blocked_reason_counts,
        FIGURES_DIR / 'top_risk_block_reasons.png',
        title='Dažniausios rizikos blokavimo priežastys',
        xlabel='Įrašų skaičius',
        color=THESIS_RED,
    )

    figure_rows = [
        [
            'signal_action_distribution.png',
            'Parodo BUY, SELL ir HOLD signalų skaičių signalų istorijoje.',
            '3.4 pav. Signalų sluoksnio veiksmų pasiskirstymas (BUY, SELL, HOLD).',
        ],
        [
            'strategy_action_distribution.png',
            'Parodo strategijos sluoksnio veiksmų OPEN_LONG, OPEN_SHORT, HOLD ir SKIP pasiskirstymą.',
            '3.5 pav. Strategijos sluoksnio veiksmų pasiskirstymas.',
        ],
        [
            'risk_decision_distribution.png',
            'Parodo, kiek rizikos sprendimų buvo leisti, blokuoti arba priskirti prie skipped.',
            '3.6 pav. Rizikos sluoksnio sprendimų pasiskirstymas.',
        ],
        [
            'automation_cycle_status_distribution.png',
            'Parodo automatinių ciklų būsenų success, skipped ir failed pasiskirstymą.',
            '3.7 pav. Automatinio ciklo būsenų pasiskirstymas.',
        ],
        [
            'decision_funnel.png',
            'Parodo sprendimų grandinės mažėjimą nuo signalų iki sėkmingų vykdymų bendrame laikotarpyje.',
            '3.8 pav. Sprendimų grandinės piltuvėlis nuo signalų iki sėkmingo vykdymo.',
        ],
        [
            'top_strategy_reasons.png',
            'Parodo 10 dažniausių strategijos veiksmų priežasčių.',
            '3.9 pav. Dažniausios strategijos sluoksnio sprendimo priežastys.',
        ],
        [
            'top_risk_block_reasons.png',
            'Parodo 10 dažniausių rizikos sluoksnio blokavimo priežasčių.',
            '3.10 pav. Dažniausios rizikos sluoksnio blokavimo priežastys.',
        ],
    ]

    strategy_rows = []
    for key in ['OPEN_LONG', 'OPEN_SHORT', 'HOLD', 'SKIP']:
        count = int(strategy_counts.get(key, 0))
        strategy_rows.append([key, fmt_int(count), fmt_pct(count, strategy_total)])
    for key, value in strategy_counts.items():
        if key in {'OPEN_LONG', 'OPEN_SHORT', 'HOLD', 'SKIP'}:
            continue
        strategy_rows.append([str(key), fmt_int(value), fmt_pct(int(value), strategy_total)])

    risk_state_rows = [
        ['allowed', fmt_int(int(risk_state_counts.get('allowed', 0))), fmt_pct(int(risk_state_counts.get('allowed', 0)), risk_total)],
        ['blocked', fmt_int(int(risk_state_counts.get('blocked', 0))), fmt_pct(int(risk_state_counts.get('blocked', 0)), risk_total)],
        ['skipped', fmt_int(int(risk_state_counts.get('skipped', 0))), fmt_pct(int(risk_state_counts.get('skipped', 0)), risk_total)],
    ]

    automation_rows = [
        ['Iš viso ciklų', fmt_int(automation_total)],
        ['Sėkmingi ciklai', fmt_int(automation_status['success'])],
        ['Praleisti ciklai', fmt_int(automation_status['skipped'])],
        ['Nesėkmingi ciklai', fmt_int(automation_status['failed'])],
        ['Ciklai be prekybos bandymo', fmt_int(automation_no_trade)],
        ['Ciklai su vykdymo bandymu', fmt_int(automation_attempts)],
        ['Ciklai su identifikuotu sėkmingu vykdymu', fmt_int(automation_success_exec)],
    ]

    execution_rows = []
    for status_name, count in execution_status_counts.items():
        execution_rows.append([str(status_name), fmt_int(count), fmt_pct(int(count), execution_total)])

    report_lines: list[str] = []
    report_lines.append('# 3.4 Sprendimų grandinės ir automatinio ciklo rezultatai')
    report_lines.append('')

    report_lines.append('## Analizuotų istorijos failų apimtis')
    report_lines.append('')
    report_lines.append(markdown_table(
        ['Sluoksnis', 'Failas', 'Įrašų skaičius', 'Laiko stulpelis', 'Ankstyviausias laikas', 'Vėliausias laikas'],
        coverage_rows,
    ))
    report_lines.append('')

    report_lines.append('## Signalų sluoksnio rezultatai')
    report_lines.append('')
    report_lines.append(markdown_table(
        ['Rodiklis', 'Reikšmė'],
        [
            ['Signalų įrašų skaičius', fmt_int(signal_total)],
            ['BUY', f"{fmt_int(int(signal_counts.get('BUY', 0)))} ({fmt_pct(int(signal_counts.get('BUY', 0)), signal_total)})"],
            ['SELL', f"{fmt_int(int(signal_counts.get('SELL', 0)))} ({fmt_pct(int(signal_counts.get('SELL', 0)), signal_total)})"],
            ['HOLD', f"{fmt_int(int(signal_counts.get('HOLD', 0)))} ({fmt_pct(int(signal_counts.get('HOLD', 0)), signal_total)})"],
            ['probability_up min', signal_prob['min']],
            ['probability_up mean', signal_prob['mean']],
            ['probability_up median', signal_prob['median']],
            ['probability_up max', signal_prob['max']],
            ['Confidence bucket skirstinys', signal_confidence_note],
            ['Signalų faile rasti stulpeliai', signal_columns],
        ],
    ))
    report_lines.append('')

    report_lines.append('## Strategijos sluoksnio rezultatai')
    report_lines.append('')
    report_lines.append(markdown_table(
        ['Veiksmas', 'Skaičius', 'Dalis nuo strategijos įrašų'],
        strategy_rows,
    ))
    report_lines.append('')
    report_lines.append(markdown_table(
        ['Dažniausia strategijos priežastis', 'Skaičius'],
        [[str(index), fmt_int(value)] for index, value in strategy_reason_counts.items()] or [['nerasta', 'nerasta']],
    ))
    report_lines.append('')
    report_lines.append(markdown_table(
        ['Confidence bucket', 'Skaičius'],
        [[str(index), fmt_int(value)] for index, value in strategy_confidence_counts.items()] or [['nerasta', 'nerasta']],
    ))
    report_lines.append('')
    report_lines.append(f'- Iš viso strategijos sprendimų: {strategy_total}.')
    report_lines.append(f'- Kandidatiniai prekybiniai veiksmai (OPEN_LONG + OPEN_SHORT): {candidate_actions}.')
    report_lines.append(f'- {strategy_signal_window_note}')
    report_lines.append(f'- {candidate_conversion_note}')
    report_lines.append('')

    report_lines.append('## Rizikos sluoksnio rezultatai')
    report_lines.append('')
    report_lines.append(markdown_table(
        ['Rizikos būsena', 'Skaičius', 'Dalis nuo rizikos įrašų'],
        risk_state_rows,
    ))
    report_lines.append('')
    report_lines.append(markdown_table(
        ['Patvirtintas veiksmas', 'Skaičius'],
        [[str(index), fmt_int(value)] for index, value in approved_action_counts.items()] or [['nerasta', 'nerasta']],
    ))
    report_lines.append('')
    report_lines.append(markdown_table(
        ['Dažniausia rizikos blokavimo priežastis', 'Skaičius'],
        [[str(index), fmt_int(value)] for index, value in blocked_reason_counts.items()] or [['nerasta', 'nerasta']],
    ))
    report_lines.append('')
    report_lines.append(markdown_table(
        ['Rodiklis', 'Reikšmė'],
        [
            ['Rizikos įrašų skaičius', fmt_int(risk_total)],
            ['Leistų sprendimų order_notional_usdt min', allowed_notional['min']],
            ['Leistų sprendimų order_notional_usdt mean', allowed_notional['mean']],
            ['Leistų sprendimų order_notional_usdt median', allowed_notional['median']],
            ['Leistų sprendimų order_notional_usdt max', allowed_notional['max']],
            ['Leistų sprendimų approved_leverage min', allowed_leverage['min']],
            ['Leistų sprendimų approved_leverage mean', allowed_leverage['mean']],
            ['Leistų sprendimų approved_leverage median', allowed_leverage['median']],
            ['Leistų sprendimų approved_leverage max', allowed_leverage['max']],
        ],
    ))
    report_lines.append('')
    report_lines.append('- Pastaba: rizikos istorija yra append-only, todėl tas pats predicted_for_timestamp gali būti įvertintas kelis kartus skirtinguose automatikos cikluose ar rankiniuose kvietimuose.')
    report_lines.append('')

    report_lines.append('## Automatinio ciklo rezultatai')
    report_lines.append('')
    report_lines.append(markdown_table(
        ['Rodiklis', 'Reikšmė'],
        automation_rows,
    ))
    report_lines.append('')
    report_lines.append(markdown_table(
        ['Dažniausia skip/error priežastis', 'Skaičius'],
        [[str(index), fmt_int(value)] for index, value in automation_reason_counts.items()] or [['nerasta', 'nerasta']],
    ))
    report_lines.append('')

    report_lines.append('## Vykdymo bandymų rezultatai')
    report_lines.append('')
    report_lines.append(markdown_table(
        ['Vykdymo būsena', 'Skaičius', 'Dalis nuo vykdymo įrašų'],
        execution_rows or [['nerasta', 'nerasta', 'nerasta']],
    ))
    report_lines.append('')
    report_lines.append(markdown_table(
        ['Dažniausia skip/fail priežastis', 'Skaičius'],
        [[str(index), fmt_int(value)] for index, value in execution_reason_counts.items()] or [['nerasta', 'nerasta']],
    ))
    report_lines.append('')
    report_lines.append(markdown_table(
        ['Rodiklis', 'Reikšmė'],
        [
            ['Vykdymo žurnalo įrašų skaičius', fmt_int(execution_total)],
            ['Įrašai, pasiekę realų demo order_id (visi)', fmt_int(execution_actual_all)],
            ['Įrašai, pasiekę realų demo order_id (tik entry bandymai)', fmt_int(execution_actual_entries)],
            ['Unikalūs entry vykdymo bandymai', fmt_int(unique_entry_attempts)],
            ['Unikalūs sėkmingi entry vykdymai', fmt_int(unique_successful_entries)],
        ],
    ))
    report_lines.append('')

    report_lines.append('## Sprendimų grandinės piltuvėlis')
    report_lines.append('')
    report_lines.append(markdown_table(
        ['Piltuvėlio etapas', 'Skaičius', 'Pastaba'],
        funnel_rows,
    ))
    report_lines.append('')
    report_lines.append(f'- {funnel_note}')
    report_lines.append('')

    report_lines.append('## Sugeneruotos vizualizacijos')
    report_lines.append('')
    report_lines.append(markdown_table(
        ['Failo pavadinimas', 'Ką rodo', 'Siūloma lietuviška antraštė'],
        figure_rows,
    ))
    report_lines.append('')

    report_lines.append('## Svarbiausios interpretacijos 3.4 skyriui')
    report_lines.append('')
    interpretation_lines = [
        f'- Signalų istorijoje užfiksuoti {signal_total} modelio interpretacijos įrašai; tarp jų BUY sudaro {fmt_pct(int(signal_counts.get("BUY", 0)), signal_total)}, SELL – {fmt_pct(int(signal_counts.get("SELL", 0)), signal_total)}, HOLD – {fmt_pct(int(signal_counts.get("HOLD", 0)), signal_total)}.',
        f'- Strategijos sluoksnis sugeneravo {strategy_total} sprendimų, iš kurių {candidate_actions} buvo kandidatiniai atidarymo veiksmai OPEN_LONG arba OPEN_SHORT.',
        f'- Rizikos sluoksnyje sukaupta {risk_total} sprendimų; allowed sudaro {fmt_pct(int(risk_state_counts.get("allowed", 0)), risk_total)}, blocked – {fmt_pct(int(risk_state_counts.get("blocked", 0)), risk_total)}, skipped – {fmt_pct(int(risk_state_counts.get("skipped", 0)), risk_total)}.',
        f'- Automatiniame cikle sukaupti {automation_total} ciklai, iš kurių {automation_status["success"]} baigėsi success, {automation_status["skipped"]} – skipped, o {automation_status["failed"]} – failed.',
        f'- Vykdymo žurnale matyti {execution_total} įrašas(-ai); {unique_successful_entries} unikalūs entry bandymai pasiekė sėkmingą demo vykdymą.',
        '- Piltuvėlis turi būti interpretuojamas tik bendrame sluoksnių persidengimo laikotarpyje, nes signalų istorija prasideda anksčiau nei strategijos ir rizikos istorijos.',
        '- Šiame skyriuje sąmoningai nevertinamas galutinis PnL ar uždarytų sandorių rezultatyvumas; tai palikta 3.5 poskyriui.',
    ]
    report_lines.extend(interpretation_lines)
    report_lines.append('')

    REPORT_PATH.write_text('\n'.join(report_lines), encoding='utf-8')


if __name__ == '__main__':
    build_report()
