from __future__ import annotations

from pathlib import Path
import json

import matplotlib
matplotlib.use('Agg')
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml


LABEL_NAME_MAP = {
    -1: 'NEUTRAL',
    0: 'DOWN',
    1: 'UP',
}


def load_settings(path: Path) -> dict:
    with path.open('r', encoding='utf-8') as handle:
        return yaml.safe_load(handle)


def load_npz(path: Path) -> dict[str, np.ndarray]:
    payload = np.load(path, allow_pickle=True)
    return {key: payload[key] for key in payload.files}


def to_utc_series(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, utc=True, errors='coerce')


def frame_meta(df: pd.DataFrame, timestamp_column: str = 'open_time') -> dict[str, object]:
    meta: dict[str, object] = {'rows': int(len(df))}
    if timestamp_column in df.columns and not df.empty:
        ts = to_utc_series(df[timestamp_column])
        meta['start'] = ts.min()
        meta['end'] = ts.max()
    else:
        meta['start'] = None
        meta['end'] = None
    return meta


def class_counts(series: pd.Series) -> dict[str, int]:
    counts = series.value_counts(dropna=False).to_dict()
    return {
        'UP': int(counts.get(1, 0)),
        'DOWN': int(counts.get(0, 0)),
        'NEUTRAL': int(counts.get(-1, 0)),
    }


def binary_counts(array: np.ndarray) -> dict[str, int]:
    values, counts = np.unique(array.astype(int), return_counts=True)
    mapping = {int(value): int(count) for value, count in zip(values.tolist(), counts.tolist())}
    return {
        'DOWN': mapping.get(0, 0),
        'UP': mapping.get(1, 0),
    }


def format_ts(value: object) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return 'nerasta'
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    return str(value)


def add_hist(ax: plt.Axes, series: pd.Series, title: str) -> None:
    clean = pd.to_numeric(series, errors='coerce').dropna()
    ax.hist(clean.to_numpy(), bins=40, color='#2b6cb0', alpha=0.85, edgecolor='white', linewidth=0.3)
    ax.set_title(title, fontsize=9)
    ax.grid(alpha=0.2)


def plot_close(processed_df: pd.DataFrame, out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(14, 5))
    ax.plot(processed_df['open_time'], processed_df['close'], color='#1f4e79', linewidth=0.8)
    ax.set_title('BTCUSDT close kaina per visa laikotarpi')
    ax.set_xlabel('Data')
    ax.set_ylabel('Close')
    ax.grid(alpha=0.25)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def plot_volume(processed_df: pd.DataFrame, out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(14, 5))
    ax.plot(processed_df['open_time'], processed_df['volume'], color='#2f855a', linewidth=0.6)
    ax.set_title('BTCUSDT prekybos apimtis per visa laikotarpi')
    ax.set_xlabel('Data')
    ax.set_ylabel('Volume')
    ax.grid(alpha=0.25)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def plot_split_timeline(split_meta: dict[str, dict[str, object]], out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(14, 3.8))
    order = ['TRAIN', 'VALIDATION', 'TEST']
    colors = {'TRAIN': '#2b6cb0', 'VALIDATION': '#d69e2e', 'TEST': '#c53030'}
    y_positions = [2, 1, 0]
    for name, y in zip(order, y_positions):
        start = pd.Timestamp(split_meta[name]['start'])
        end = pd.Timestamp(split_meta[name]['end'])
        width = end - start
        ax.barh(y, width=width, left=start, height=0.45, color=colors[name], alpha=0.9)
        ax.text(start + width / 2, y, name, ha='center', va='center', color='white', fontsize=10, fontweight='bold')
    ax.set_yticks(y_positions)
    ax.set_yticklabels(order)
    ax.set_title('Mokymo, validavimo ir testavimo laikotarpiu laiko juosta')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax.grid(axis='x', alpha=0.25)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def plot_class_distribution(
    labeled_counts: dict[str, int],
    split_binary_counts: dict[str, dict[str, int]],
    out_path: Path,
) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.8))

    labels = ['DOWN', 'NEUTRAL', 'UP']
    counts = [labeled_counts['DOWN'], labeled_counts['NEUTRAL'], labeled_counts['UP']]
    colors = ['#c53030', '#718096', '#2f855a']
    axes[0].bar(labels, counts, color=colors)
    axes[0].set_title('Pazymeetu klasiu pasiskirstymas (labeled v3)')
    axes[0].set_ylabel('Eiluciu skaicius')
    axes[0].grid(axis='y', alpha=0.25)

    split_names = ['TRAIN', 'VALIDATION', 'TEST']
    down = [split_binary_counts[name]['DOWN'] for name in split_names]
    up = [split_binary_counts[name]['UP'] for name in split_names]
    axes[1].bar(split_names, down, color='#c53030', label='DOWN')
    axes[1].bar(split_names, up, bottom=down, color='#2f855a', label='UP')
    axes[1].set_title('Galutiniu binariniu klasiu pasiskirstymas (normalized v7)')
    axes[1].set_ylabel('Langeliu skaicius')
    axes[1].legend()
    axes[1].grid(axis='y', alpha=0.25)

    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def plot_feature_distributions(feature_df: pd.DataFrame, selected: list[str], out_path: Path) -> None:
    fig, axes = plt.subplots(4, 4, figsize=(16, 14))
    flat_axes = axes.flatten()
    for ax, feature in zip(flat_axes, selected):
        add_hist(ax, feature_df[feature], feature)
    for ax in flat_axes[len(selected):]:
        ax.axis('off')
    fig.suptitle('Atrinktu pozymiu skirstiniai', fontsize=14)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def plot_correlation(feature_df: pd.DataFrame, selected: list[str], out_path: Path) -> None:
    corr = feature_df[selected].corr(numeric_only=True)
    fig, ax = plt.subplots(figsize=(12, 10))
    im = ax.imshow(corr.to_numpy(), cmap='coolwarm', vmin=-1, vmax=1)
    ax.set_xticks(range(len(selected)))
    ax.set_xticklabels(selected, rotation=90, fontsize=8)
    ax.set_yticks(range(len(selected)))
    ax.set_yticklabels(selected, fontsize=8)
    ax.set_title('Atrinktu pozymiu koreliaciju silumos zemelapis')
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def plot_normalized_window(train_payload: dict[str, np.ndarray], feature_names: list[str], out_path: Path) -> None:
    X = train_payload['X']
    sample = X[0]
    fig, ax = plt.subplots(figsize=(14, 8))
    im = ax.imshow(sample.T, aspect='auto', cmap='viridis', interpolation='nearest')
    ax.set_title('Pirmojo train lango normalizuotu pozymiu matrica (v7)')
    ax.set_xlabel('Laiko zingsnis lange')
    ax.set_ylabel('Pozymis')
    ax.set_yticks(range(len(feature_names)))
    ax.set_yticklabels(feature_names, fontsize=7)
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def build_feature_groups() -> dict[str, list[str]]:
    return {
        'Kainos ir grazos pozymiai': [
            'log_return_1',
            'log_return_4',
            'close_to_open_return',
            'high_low_range_pct',
        ],
        'Zvakes strukturos pozymiai': [
            'body_pct',
            'upper_wick_pct',
            'lower_wick_pct',
            'body_to_range_ratio',
        ],
        'Trendo pozymiai': [
            'ema_20_dist',
            'ema_50_dist',
            'ema_20_50_spread',
        ],
        'Momento pozymiai': [
            'rsi_14',
            'macd_hist',
        ],
        'Volatilumo pozymiai': [
            'atr_14_pct',
            'rolling_vol_12',
            'rolling_vol_48',
        ],
        'Apimties pozymiai': [
            'volume_change_1',
            'volume_ma_ratio_20',
            'turnover_ma_ratio_20',
        ],
        'Laiko cikliniai pozymiai': [
            'hour_sin',
            'hour_cos',
            'dow_sin',
            'dow_cos',
        ],
        'Konteksto ir reiksmiu intervalo pozymiai': [
            'close_to_rolling_high_96',
            'close_to_rolling_low_96',
            'range_position_96',
        ],
    }


def main() -> None:
    report_root = Path(__file__).resolve().parent
    project_root = report_root.parents[1]
    figure_dir = report_root / 'figures'
    figure_dir.mkdir(parents=True, exist_ok=True)

    settings = load_settings(project_root / 'config' / 'settings.yaml')
    symbol = settings['symbol']
    timeframe = settings['timeframe']
    exchange = settings.get('exchange', 'bybit')

    data_cfg = settings['data']
    paths = {
        'raw': project_root / data_cfg['raw_dir'] / exchange / symbol / f'{timeframe}.parquet',
        'processed': project_root / data_cfg['processed_dir'] / f'{symbol}_{timeframe}_clean.parquet',
        'features_v3': project_root / data_cfg['features_dir'] / f'{symbol}_{timeframe}_features_v3.parquet',
        'labeled_v3': project_root / data_cfg['labeled_dir'] / f'{symbol}_{timeframe}_labeled_v3.parquet',
        'split_train_v3': project_root / data_cfg['splits_dir'] / f'{symbol}_{timeframe}_train_v3.parquet',
        'split_val_v3': project_root / data_cfg['splits_dir'] / f'{symbol}_{timeframe}_val_v3.parquet',
        'split_test_v3': project_root / data_cfg['splits_dir'] / f'{symbol}_{timeframe}_test_v3.parquet',
        'window_train_v3': project_root / data_cfg['windows_dir'] / f'{symbol}_{timeframe}_train_windows_v3.npz',
        'window_val_v3': project_root / data_cfg['windows_dir'] / f'{symbol}_{timeframe}_val_windows_v3.npz',
        'window_test_v3': project_root / data_cfg['windows_dir'] / f'{symbol}_{timeframe}_test_windows_v3.npz',
        'norm_train_v7': project_root / data_cfg['normalized_dir'] / f'{symbol}_{timeframe}_train_windows_norm_v7.npz',
        'norm_val_v7': project_root / data_cfg['normalized_dir'] / f'{symbol}_{timeframe}_val_windows_norm_v7.npz',
        'norm_test_v7': project_root / data_cfg['normalized_dir'] / f'{symbol}_{timeframe}_test_windows_norm_v7.npz',
        'scaler_v7': project_root / data_cfg['normalized_dir'] / f'{symbol}_{timeframe}_scaler_stats_v7.npz',
    }

    raw_df = pd.read_parquet(paths['raw'])
    processed_df = pd.read_parquet(paths['processed'])
    features_df = pd.read_parquet(paths['features_v3'])
    labeled_df = pd.read_parquet(paths['labeled_v3'])
    split_train_df = pd.read_parquet(paths['split_train_v3'])
    split_val_df = pd.read_parquet(paths['split_val_v3'])
    split_test_df = pd.read_parquet(paths['split_test_v3'])

    for frame in [raw_df, processed_df, features_df, labeled_df, split_train_df, split_val_df, split_test_df]:
        if 'open_time' in frame.columns:
            frame['open_time'] = to_utc_series(frame['open_time'])

    window_train = load_npz(paths['window_train_v3'])
    window_val = load_npz(paths['window_val_v3'])
    window_test = load_npz(paths['window_test_v3'])
    norm_train = load_npz(paths['norm_train_v7'])
    norm_val = load_npz(paths['norm_val_v7'])
    norm_test = load_npz(paths['norm_test_v7'])
    scaler = load_npz(paths['scaler_v7'])

    feature_names = scaler['feature_names'].astype(str).tolist()
    feature_groups = build_feature_groups()
    selected_features = [
        'log_return_1',
        'log_return_4',
        'rsi_14',
        'macd_hist',
        'atr_14_pct',
        'rolling_vol_12',
        'rolling_vol_48',
        'volume_ma_ratio_20',
        'close_to_rolling_high_96',
        'close_to_rolling_low_96',
        'range_position_96',
        'hour_sin',
        'hour_cos',
        'dow_sin',
        'dow_cos',
    ]

    raw_meta = frame_meta(raw_df)
    processed_meta = frame_meta(processed_df)
    features_meta = frame_meta(features_df)
    labeled_meta = frame_meta(labeled_df)
    split_meta = {
        'TRAIN': frame_meta(split_train_df),
        'VALIDATION': frame_meta(split_val_df),
        'TEST': frame_meta(split_test_df),
    }

    window_meta = {
        'TRAIN': {'samples': int(window_train['X'].shape[0]), 'sequence_length': int(window_train['X'].shape[1])},
        'VALIDATION': {'samples': int(window_val['X'].shape[0]), 'sequence_length': int(window_val['X'].shape[1])},
        'TEST': {'samples': int(window_test['X'].shape[0]), 'sequence_length': int(window_test['X'].shape[1])},
    }
    norm_meta = {
        'TRAIN': {'samples': int(norm_train['X'].shape[0]), 'sequence_length': int(norm_train['X'].shape[1])},
        'VALIDATION': {'samples': int(norm_val['X'].shape[0]), 'sequence_length': int(norm_val['X'].shape[1])},
        'TEST': {'samples': int(norm_test['X'].shape[0]), 'sequence_length': int(norm_test['X'].shape[1])},
    }

    labeled_counts_total = class_counts(labeled_df['label'])
    labeled_counts_split = {
        'TRAIN': class_counts(split_train_df['label']),
        'VALIDATION': class_counts(split_val_df['label']),
        'TEST': class_counts(split_test_df['label']),
    }
    binary_counts_split = {
        'TRAIN': binary_counts(norm_train['y']),
        'VALIDATION': binary_counts(norm_val['y']),
        'TEST': binary_counts(norm_test['y']),
    }
    binary_counts_total = {
        'DOWN': sum(item['DOWN'] for item in binary_counts_split.values()),
        'UP': sum(item['UP'] for item in binary_counts_split.values()),
    }

    descriptive_stats = features_df[selected_features].describe(percentiles=[0.25, 0.5, 0.75]).T
    descriptive_stats = descriptive_stats[['count', 'mean', 'std', 'min', '25%', '50%', '75%', 'max']]

    plot_close(processed_df, figure_dir / 'v7_close_price_full_period.png')
    plot_volume(processed_df, figure_dir / 'v7_volume_full_period.png')
    plot_split_timeline(split_meta, figure_dir / 'v7_split_timeline.png')
    plot_class_distribution(labeled_counts_total, binary_counts_split, figure_dir / 'v7_target_class_distribution.png')
    plot_feature_distributions(features_df, selected_features, figure_dir / 'v7_selected_feature_distributions.png')
    plot_correlation(features_df, selected_features, figure_dir / 'v7_selected_feature_correlation_heatmap.png')
    plot_normalized_window(norm_train, feature_names, figure_dir / 'v7_example_normalized_train_window.png')

    figures = [
        {
            'filename': 'v7_close_price_full_period.png',
            'shows': 'BTCUSDT uzdarymo kainos dinamika per visa analizuojama laikotarpi.',
            'caption': 'BTCUSDT 15 min. uzdarymo kainos dinamika visame analizuotame laikotarpyje.',
        },
        {
            'filename': 'v7_volume_full_period.png',
            'shows': 'BTCUSDT prekybos apimties dinamika per visa analizuojama laikotarpi.',
            'caption': 'BTCUSDT 15 min. prekybos apimties dinamika visame analizuotame laikotarpyje.',
        },
        {
            'filename': 'v7_split_timeline.png',
            'shows': 'Train, validation ir test skaidymo laiko atkarpos.',
            'caption': 'Duomenu rinkinio skaidymas i mokymo, validavimo ir testavimo laikotarpius.',
        },
        {
            'filename': 'v7_target_class_distribution.png',
            'shows': 'Labeled klasiu pasiskirstymas ir galutiniu binariniu mokymo klasiu pasiskirstymas pagal skiltis.',
            'caption': 'Tiksliniu klasiu pasiskirstymas pries ir po galutinio binarinio filtravimo.',
        },
        {
            'filename': 'v7_selected_feature_distributions.png',
            'shows': 'Atrinktu pagrindiniu pozymiu empiriniu skirstiniu histogramos.',
            'caption': 'Svarbiausiu modelio pozymiu skirstiniai parengtame duomenu rinkinyje.',
        },
        {
            'filename': 'v7_selected_feature_correlation_heatmap.png',
            'shows': 'Atrinktu pozymiu tarpusavio koreliaciju matrica.',
            'caption': 'Atrinktu pozymiu tarpusavio koreliaciju silumos zemelapis.',
        },
        {
            'filename': 'v7_example_normalized_train_window.png',
            'shows': 'Vieno normalizuoto mokymo lango pozymiu matrica.',
            'caption': 'Normalizuoto 256 zingsniu mokymo lango pavyzdys, naudotas TCN modeliui.',
        },
    ]

    summary = {
        'symbol': symbol,
        'timeframe': timeframe,
        'renamed_mapping': 'normalized v7 corresponds to old v3 feature/labeled/split/window artifacts',
        'date_range': {'start': format_ts(raw_meta['start']), 'end': format_ts(raw_meta['end'])},
        'feature_count': len(feature_names),
        'sequence_length': int(norm_train['X'].shape[1]),
        'split_sizes': {
            'train_rows': int(split_meta['TRAIN']['rows']),
            'validation_rows': int(split_meta['VALIDATION']['rows']),
            'test_rows': int(split_meta['TEST']['rows']),
        },
        'window_counts': {
            'train': int(norm_meta['TRAIN']['samples']),
            'validation': int(norm_meta['VALIDATION']['samples']),
            'test': int(norm_meta['TEST']['samples']),
            'total': int(sum(item['samples'] for item in norm_meta.values())),
        },
        'label_horizon': 12,
        'return_threshold': 0.003,
        'selected_feature_count': len(selected_features),
    }

    (report_root / 'dataset_v7_summary.json').write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding='utf-8',
    )

    lines: list[str] = []
    lines.append('Paruošto duomenų rinkinio analizė: v7')
    lines.append('')
    lines.append('Duomenų rinkinio tapatybė')
    lines.append('- Symbolis: ' + symbol)
    lines.append('- Laikotarpis: ' + timeframe)
    lines.append('- Normalizuotas galutinis variantas: v7')
    lines.append('- Atitinkantis ankstesnis artifactų rinkinys: features/labeled/splits/windows v3')
    lines.append('- Pažymių skaičius: ' + str(len(feature_names)))
    lines.append('- Sekos ilgis: ' + str(norm_train['X'].shape[1]))
    lines.append('- Etikečių horizontas: 12 (nustatyta pagal v3 eksperimentų dokumentaciją, nes artifactuose ši reikšmė nesaugoma)')
    lines.append('- Gražos slenkstis: 0.003 (nustatyta pagal v3 eksperimentų dokumentaciją, nes artifactuose ši reikšmė nesaugoma)')
    lines.append('')

    lines.append('Duomenų rinkinio apimtis')
    lines.append('Tipas | Failas | Eilučių / pavyzdžių skaičius | Pradžia | Pabaiga')
    lines.append(f"Raw | {paths['raw'].name} | {raw_meta['rows']} | {format_ts(raw_meta['start'])} | {format_ts(raw_meta['end'])}")
    lines.append(f"Processed | {paths['processed'].name} | {processed_meta['rows']} | {format_ts(processed_meta['start'])} | {format_ts(processed_meta['end'])}")
    lines.append(f"Features v3 | {paths['features_v3'].name} | {features_meta['rows']} | {format_ts(features_meta['start'])} | {format_ts(features_meta['end'])}")
    lines.append(f"Labeled v3 | {paths['labeled_v3'].name} | {labeled_meta['rows']} | {format_ts(labeled_meta['start'])} | {format_ts(labeled_meta['end'])}")
    lines.append(f"Split TRAIN v3 | {paths['split_train_v3'].name} | {split_meta['TRAIN']['rows']} | {format_ts(split_meta['TRAIN']['start'])} | {format_ts(split_meta['TRAIN']['end'])}")
    lines.append(f"Split VALIDATION v3 | {paths['split_val_v3'].name} | {split_meta['VALIDATION']['rows']} | {format_ts(split_meta['VALIDATION']['start'])} | {format_ts(split_meta['VALIDATION']['end'])}")
    lines.append(f"Split TEST v3 | {paths['split_test_v3'].name} | {split_meta['TEST']['rows']} | {format_ts(split_meta['TEST']['start'])} | {format_ts(split_meta['TEST']['end'])}")
    lines.append(f"Windows TRAIN v3 | {paths['window_train_v3'].name} | {window_meta['TRAIN']['samples']} | {format_ts(split_meta['TRAIN']['start'])} | {format_ts(split_meta['TRAIN']['end'])}")
    lines.append(f"Windows VALIDATION v3 | {paths['window_val_v3'].name} | {window_meta['VALIDATION']['samples']} | {format_ts(split_meta['VALIDATION']['start'])} | {format_ts(split_meta['VALIDATION']['end'])}")
    lines.append(f"Windows TEST v3 | {paths['window_test_v3'].name} | {window_meta['TEST']['samples']} | {format_ts(split_meta['TEST']['start'])} | {format_ts(split_meta['TEST']['end'])}")
    lines.append(f"Normalized TRAIN v7 | {paths['norm_train_v7'].name} | {norm_meta['TRAIN']['samples']} | {format_ts(split_meta['TRAIN']['start'])} | {format_ts(split_meta['TRAIN']['end'])}")
    lines.append(f"Normalized VALIDATION v7 | {paths['norm_val_v7'].name} | {norm_meta['VALIDATION']['samples']} | {format_ts(split_meta['VALIDATION']['start'])} | {format_ts(split_meta['VALIDATION']['end'])}")
    lines.append(f"Normalized TEST v7 | {paths['norm_test_v7'].name} | {norm_meta['TEST']['samples']} | {format_ts(split_meta['TEST']['start'])} | {format_ts(split_meta['TEST']['end'])}")
    lines.append('')

    lines.append('Duomenų skaidymas')
    lines.append('Skiltis | Eilučių skaičius labeled v3 | Langų skaičius normalized v7 | Pradžia | Pabaiga')
    for name in ['TRAIN', 'VALIDATION', 'TEST']:
        lines.append(
            f"{name} | {split_meta[name]['rows']} | {norm_meta[name]['samples']} | {format_ts(split_meta[name]['start'])} | {format_ts(split_meta[name]['end'])}"
        )
    lines.append('Bendras galutinių langų skaičius: ' + str(sum(item['samples'] for item in norm_meta.values())))
    lines.append('')

    lines.append('Tikslinių klasių pasiskirstymas')
    lines.append('Labeled v3 bendras pasiskirstymas:')
    lines.append(f"- UP: {labeled_counts_total['UP']}")
    lines.append(f"- DOWN: {labeled_counts_total['DOWN']}")
    lines.append(f"- NEUTRAL: {labeled_counts_total['NEUTRAL']}")
    lines.append('')
    lines.append('Labeled v3 pasiskirstymas pagal skiltis:')
    for name in ['TRAIN', 'VALIDATION', 'TEST']:
        counts = labeled_counts_split[name]
        lines.append(f"- {name}: UP={counts['UP']}, DOWN={counts['DOWN']}, NEUTRAL={counts['NEUTRAL']}")
    lines.append('')
    lines.append('Galutinis binarinis pasiskirstymas normalized v7 (po neutralių target pašalinimo):')
    for name in ['TRAIN', 'VALIDATION', 'TEST']:
        counts = binary_counts_split[name]
        lines.append(f"- {name}: UP={counts['UP']}, DOWN={counts['DOWN']}")
    lines.append(f"- Iš viso: UP={binary_counts_total['UP']}, DOWN={binary_counts_total['DOWN']}")
    lines.append('')

    lines.append('Požymių rinkinio struktūra')
    lines.append('Bendras požymių skaičius: ' + str(len(feature_names)))
    for group_name, names in feature_groups.items():
        existing = [name for name in names if name in feature_names]
        lines.append(f"- {group_name} ({len(existing)}): {', '.join(existing)}")
    lines.append('')

    lines.append('Atrinktų požymių aprašomoji statistika')
    lines.append('Požymis | count | mean | std | min | 25% | 50% | 75% | max')
    for feature_name, row in descriptive_stats.iterrows():
        lines.append(
            f"{feature_name} | {int(row['count'])} | {row['mean']:.6f} | {row['std']:.6f} | {row['min']:.6f} | {row['25%']:.6f} | {row['50%']:.6f} | {row['75%']:.6f} | {row['max']:.6f}"
        )
    lines.append('')

    lines.append('Sugeneruotos vizualizacijos')
    for figure in figures:
        lines.append(f"- Failas: figures/{figure['filename']}")
        lines.append(f"  Ką rodo: {figure['shows']}")
        lines.append(f"  Siūlomas paveikslo pavadinimas: {figure['caption']}")
    lines.append('')

    lines.append('Svarbiausios išvados 3.1 skyriui')
    lines.append(f"- Galutinis analizuotas modelio duomenų rinkinys yra normalized v7, kuris atitinka ankstesnį v3 požymių rinkinį su {len(feature_names)} požymiais.")
    lines.append(f"- Duomenys apima laikotarpį nuo {format_ts(raw_meta['start'])} iki {format_ts(raw_meta['end'])}, o po apdorojimo ir pažymių konstravimo galutinis features v3 rinkinys turi {features_meta['rows']} eilučių.")
    lines.append(f"- Labeled v3 rinkinyje prieš galutinį binarinį filtravimą buvo trys klasės: UP={labeled_counts_total['UP']}, DOWN={labeled_counts_total['DOWN']}, NEUTRAL={labeled_counts_total['NEUTRAL']}.")
    lines.append(f"- Galutiniam TCN modelio mokymui naudoti {sum(item['samples'] for item in norm_meta.values())} langai, kurių sekos ilgis yra {norm_train['X'].shape[1]} laiko žingsnių.")
    lines.append('- Mokymo duomenų atvaizdavimo kryptis šiame variante buvo ne požymių mažinimas, o papildomo konteksto įtraukimas: prie bazinių kainos, trendo, momento ir apimties požymių pridėti laiko cikliniai bei rolling range konteksto požymiai.')
    lines.append('- Esamo validavimo skripto ataskaitos rodo, kad raw rinkinyje intervalų tarpų nerasta, o processed rinkinyje liko vienas 45 minučių tarpas po filtravimo; ši informacija papildomai išsaugota raw_validation.txt ir processed_validation.txt failuose.')
    lines.append('- V7 artefaktai patvirtina, kad geriausiam modeliui naudotas 26 požymių, 256 žingsnių įėjimo langų duomenų rinkinys.')

    (report_root / 'dataset_v7_report.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
