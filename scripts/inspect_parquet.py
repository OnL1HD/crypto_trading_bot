import argparse
from pathlib import Path

import pandas as pd
import yaml


def load_settings(settings_path: Path) -> dict:
    with settings_path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inspect raw, processed, features, or labeled BTCUSDT parquet dataset."
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--raw", action="store_true", help="Inspect the raw dataset.")
    group.add_argument("--processed", action="store_true", help="Inspect the processed dataset.")
    group.add_argument("--features", action="store_true", help="Inspect the features dataset.")
    group.add_argument("--labeled", action="store_true", help="Inspect the labeled dataset.")
    return parser.parse_args()


def resolve_dataset_path(project_root: Path, settings: dict, dataset_type: str) -> Path:
    symbol = settings["symbol"]
    timeframe = settings["timeframe"]
    exchange = settings.get("exchange", "bybit")

    if dataset_type == "labeled":
        labeled_dir = settings["data"].get("labeled_dir", "data/labeled")
        return project_root / labeled_dir / f"{symbol}_{timeframe}_labeled_v1.parquet"

    if dataset_type == "features":
        features_dir = settings["data"]["features_dir"]
        return project_root / features_dir / f"{symbol}_{timeframe}_features_v1.parquet"

    if dataset_type == "processed":
        processed_dir = settings["data"]["processed_dir"]
        return project_root / processed_dir / f"{symbol}_{timeframe}_clean.parquet"

    raw_dir = settings["data"]["raw_dir"]
    return project_root / raw_dir / exchange / symbol / f"{timeframe}.parquet"


def main() -> None:
    args = parse_args()
    if args.labeled:
        dataset_type = "labeled"
    elif args.features:
        dataset_type = "features"
    elif args.processed:
        dataset_type = "processed"
    else:
        dataset_type = "raw"

    project_root = Path(__file__).resolve().parents[1]
    settings_path = project_root / "config" / "settings.yaml"
    settings = load_settings(settings_path)
    dataset_path = resolve_dataset_path(project_root, settings, dataset_type)

    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset not found: {dataset_path}")

    df = pd.read_parquet(dataset_path)

    print("=" * 72)
    print("PARQUET INSPECTION")
    print("=" * 72)
    print(f"Dataset type: {dataset_type}")
    print(f"Dataset path: {dataset_path}")
    print(f"Total rows:   {len(df)}")
    print(f"Columns:      {list(df.columns)}")

    preview_rows = 5 if dataset_type == "features" else 10

    print(f"\nFIRST {preview_rows} ROWS")
    print("-" * 72)
    if dataset_type == "features":
        with pd.option_context("display.max_columns", None, "display.width", 200):
            print(df.head(preview_rows).to_string(index=False))
    else:
        print(df.head(preview_rows))

    print(f"\nLAST {preview_rows} ROWS")
    print("-" * 72)
    if dataset_type == "features":
        with pd.option_context("display.max_columns", None, "display.width", 200):
            print(df.tail(preview_rows).to_string(index=False))
    else:
        print(df.tail(preview_rows))

    if "open_time" in df.columns and not df.empty:
        earliest = df["open_time"].min()
        latest = df["open_time"].max()
    else:
        earliest = "N/A"
        latest = "N/A"

    print("\nTIMESTAMP RANGE")
    print("-" * 72)
    print(f"Earliest open_time: {earliest}")
    print(f"Latest open_time:   {latest}")
    print("=" * 72)


if __name__ == "__main__":
    main()
