"""
🌊 Metric Fixer Batch CLI
==========================

Normalize GA4 metric CSV exports in bulk with deterministic schema enforcement.

Usage (examples):
    python tools/data_cleaning_transformation/metric_fixer_batch.py \
        --input "C:/path/to/raw_csv" \
        --output "C:/path/to/clean_csv" \
        --workers 4

    python tools/data_cleaning_transformation/metric_fixer_batch.py \
        --input raw --output clean \
        --schema schemas/metric_schema_v1.yaml \
        --manifest clean/metric_fixer_manifest.jsonl \
        --dry-run --limit 5

The script scans the input directory for CSV files, coerces numeric columns to the
expected types (e.g. integers for counts, decimals with two places for revenue),
logs every coercion, and writes clean CSV (and optional Parquet) copies alongside
an execution manifest for auditing or GUI inspection.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, getcontext
from pathlib import Path
import re
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import pandas as pd

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    yaml = None


getcontext().prec = 28

INVALID_VALUE_TOKENS = {
    "",
    "null",
    "none",
    "nan",
    "n/a",
    "na",
    "nil",
    "-",
    "—",
}


def now_ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def default_manifest_name(output_dir: Path) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return output_dir / f"metric_fixer_manifest_{ts}.jsonl"


def quantizer_for_scale(scale: int) -> Decimal:
    if scale <= 0:
        return Decimal("1")
    return Decimal("1").scaleb(-scale)


def parse_decimal(value: str) -> Decimal:
    return Decimal(value)


def to_decimal(value: Optional[str]) -> Optional[Decimal]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    value_str = str(value).strip()
    if not value_str:
        return None
    try:
        return Decimal(value_str)
    except InvalidOperation:
        return None


@dataclass(frozen=True)
class ColumnConfig:
    name: str
    dtype: str  # "int", "decimal", "string"
    default: str
    scale: int = 0
    percent_mode: bool = False
    clamp: bool = False
    min_value: Optional[Decimal] = None
    max_value: Optional[Decimal] = None
    aliases: Tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, raw: Dict) -> "ColumnConfig":
        return cls(
            name=raw["name"],
            dtype=raw.get("dtype", "string"),
            default=str(raw.get("default", "")),
            scale=int(raw.get("scale", 0) or 0),
            percent_mode=bool(raw.get("percent_mode", False)),
            clamp=bool(raw.get("clamp", False)),
            min_value=to_decimal(raw.get("min")),
            max_value=to_decimal(raw.get("max")),
            aliases=tuple(raw.get("aliases", [])),
        )

    def to_payload(self) -> Dict:
        data = asdict(self)
        if self.min_value is not None:
            data["min_value"] = str(self.min_value)
        if self.max_value is not None:
            data["max_value"] = str(self.max_value)
        return data

    def canonical_keys(self) -> List[str]:
        keys = {canonicalize(self.name)}
        for alias in self.aliases:
            keys.add(canonicalize(alias))
        if "_" in self.name:
            keys.add(canonicalize(self.name.replace("_", " ")))
        return list(keys)


DEFAULT_SCHEMA: Dict[str, ColumnConfig] = {
    cfg.name: cfg
    for cfg in (
        ColumnConfig(name="sessions", dtype="int", default="0"),
        ColumnConfig(name="event_count", dtype="int", default="0"),
        ColumnConfig(name="engaged_sessions", dtype="int", default="0"),
        ColumnConfig(
            name="engagement_rate",
            dtype="decimal",
            default="0.00",
            scale=2,
            percent_mode=True,
            clamp=True,
            min_value=Decimal("0.00"),
            max_value=Decimal("100.00"),
        ),
        ColumnConfig(name="views", dtype="int", default="0"),
        ColumnConfig(name="active_users", dtype="int", default="0"),
        ColumnConfig(name="new_users", dtype="int", default="0"),
        ColumnConfig(name="total_users", dtype="int", default="0"),
        ColumnConfig(
            name="total_revenue",
            dtype="decimal",
            default="0.00",
            scale=2,
            clamp=True,
            min_value=Decimal("0.00"),
        ),
    )
}


def load_schema(schema_path: Optional[Path]) -> Dict[str, ColumnConfig]:
    if schema_path is None:
        return DEFAULT_SCHEMA

    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_path}")

    if yaml is None:
        raise RuntimeError("PyYAML is required to load schema files. Install with `pip install PyYAML`.")

    with schema_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)

    if not isinstance(data, dict) or "columns" not in data:
        raise ValueError("Schema file must be a mapping with a 'columns' key.")

    schema: Dict[str, ColumnConfig] = {}
    for entry in data["columns"]:
        cfg = ColumnConfig.from_dict(entry)
        schema[cfg.name.lower()] = cfg

    return schema


def canonicalize(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", name.lower())


def sanitize_numeric_token(value: str) -> Tuple[str, bool]:
    cleaned = value.strip()
    if not cleaned:
        return "", False

    had_percent = cleaned.endswith("%")
    if had_percent:
        cleaned = cleaned[:-1]

    cleaned = cleaned.replace(",", "")
    if cleaned.startswith("(") and cleaned.endswith(")"):
        cleaned = f"-{cleaned[1:-1]}"

    for symbol in ("$", "€", "£", "₱"):
        cleaned = cleaned.replace(symbol, "")

    cleaned = cleaned.strip()
    return cleaned, had_percent


def normalize_value(
    raw_value: str,
    config: ColumnConfig,
    counters: Counter,
) -> str:
    value = "" if raw_value is None else str(raw_value)
    normalized_token = value.strip()
    if not normalized_token or normalized_token.lower() in INVALID_VALUE_TOKENS:
        counters["blank_to_default"] += 1
        return config.default

    cleaned, had_percent_symbol = sanitize_numeric_token(normalized_token)
    if not cleaned:
        counters["blank_to_default"] += 1
        return config.default

    if config.dtype == "int":
        try:
            decimal_value = Decimal(cleaned)
        except InvalidOperation:
            counters["invalid_to_default"] += 1
            return config.default

        quantized = decimal_value.quantize(Decimal("1"), rounding=ROUND_HALF_UP)

        if quantized != decimal_value:
            counters["int_quantized"] += 1

        if config.clamp:
            if config.min_value is not None and quantized < config.min_value:
                quantized = config.min_value
                counters["clamped"] += 1
            if config.max_value is not None and quantized > config.max_value:
                quantized = config.max_value
                counters["clamped"] += 1

        return str(int(quantized))

    if config.dtype == "decimal":
        try:
            decimal_value = Decimal(cleaned)
        except InvalidOperation:
            counters["invalid_to_default"] += 1
            return config.default

        if config.percent_mode and not had_percent_symbol and Decimal("-0.001") <= decimal_value <= Decimal("1.1"):
            decimal_value *= Decimal("100")
            counters["percent_scaled"] += 1

        if config.percent_mode and had_percent_symbol:
            counters["percent_symbol"] += 1

        if config.clamp:
            if config.min_value is not None and decimal_value < config.min_value:
                decimal_value = config.min_value
                counters["clamped"] += 1
            if config.max_value is not None and decimal_value > config.max_value:
                decimal_value = config.max_value
                counters["clamped"] += 1

        quant = quantizer_for_scale(config.scale)
        quantized = decimal_value.quantize(quant, rounding=ROUND_HALF_UP)

        if quantized != decimal_value:
            counters["decimal_quantized"] += 1

        return format(quantized, f".{config.scale}f")

    # passthrough for strings
    return normalized_token


def normalize_series(series: pd.Series, config: ColumnConfig) -> Tuple[pd.Series, Dict[str, int]]:
    counters: Counter = Counter()

    def _convert(val: str) -> str:
        return normalize_value(val, config, counters)

    result = series.fillna("").astype(str).map(_convert)
    return result, dict(counters)


def process_file(
    file_path: Path,
    output_root: Path,
    schema_payload: Dict[str, Dict],
    write_parquet: bool,
    dry_run: bool,
) -> Dict:
    schema = [ColumnConfig.from_dict(cfg) for cfg in schema_payload.values()]

    df = pd.read_csv(file_path, dtype=str, keep_default_na=False)
    original_columns = list(df.columns)

    column_reports: Dict[str, Dict[str, int]] = {}
    created_columns: List[str] = []
    column_lookup = {canonicalize(col): col for col in df.columns}

    for cfg in schema:
        match_name: Optional[str] = None
        for key in cfg.canonical_keys():
            if key in column_lookup:
                match_name = column_lookup[key]
                break

        if match_name is None:
            df[cfg.name] = cfg.default
            column_reports[cfg.name] = {"created_column": 1}
            created_columns.append(cfg.name)
            continue

        if match_name != cfg.name:
            df.rename(columns={match_name: cfg.name}, inplace=True)
            match_name = cfg.name

        for key in cfg.canonical_keys():
            column_lookup.pop(key, None)

        normalized_series, stats = normalize_series(df[match_name], cfg)
        df[match_name] = normalized_series
        column_reports[match_name] = stats

    rows_processed = len(df.index)

    outputs: Dict[str, Optional[str]] = {"csv": None, "parquet": None}

    if not dry_run:
        csv_dir = output_root / "clean_csv"
        parquet_dir = output_root / "parquet"
        csv_dir.mkdir(parents=True, exist_ok=True)
        if write_parquet:
            parquet_dir.mkdir(parents=True, exist_ok=True)

        csv_path = csv_dir / file_path.name
        df.to_csv(csv_path, index=False, encoding="utf-8")
        outputs["csv"] = str(csv_path)

        if write_parquet:
            parquet_path = parquet_dir / f"{file_path.stem}.parquet"
            try:
                df.to_parquet(parquet_path, index=False)
                outputs["parquet"] = str(parquet_path)
            except Exception as exc:  # pragma: no cover - optional dependency
                outputs["parquet_error"] = str(exc)

    return {
        "file": str(file_path),
        "rows": rows_processed,
        "original_columns": original_columns,
        "coercions": column_reports,
        "created_columns": created_columns,
        "output": outputs,
        "success": True,
    }


def discover_files(input_dir: Path) -> List[Path]:
    return sorted([p for p in input_dir.glob("*.csv") if p.is_file()])


def load_completed_from_manifest(manifest_path: Path) -> Dict[str, Dict]:
    if not manifest_path.exists():
        return {}

    completed: Dict[str, Dict] = {}
    with manifest_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if record.get("success"):
                completed[record["file"]] = record
    return completed


def configure_logger(output_root: Path) -> Path:
    log_dir = output_root / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "metric_fixer_batch.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )

    return log_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Metric Fixer Batch CLI")
    parser.add_argument("--input", required=True, type=Path, help="Directory containing raw CSV files.")
    parser.add_argument("--output", required=True, type=Path, help="Directory for cleaned outputs.")
    parser.add_argument("--schema", type=Path, help="Optional YAML schema definition.")
    parser.add_argument("--manifest", type=Path, help="Path to manifest JSONL. Defaults inside output directory.")
    parser.add_argument("--workers", type=int, default=os.cpu_count() or 2, help="Parallel workers (default: CPU count).")
    parser.add_argument("--only", nargs="*", help="Optional list of CSV filenames to process.")
    parser.add_argument("--resume", action="store_true", help="Skip files already recorded as success in the manifest.")
    parser.add_argument("--dry-run", action="store_true", help="Process without writing output files.")
    parser.add_argument("--no-parquet", action="store_true", help="Skip Parquet output.")
    parser.add_argument("--limit", type=int, help="Limit number of files processed (for smoke tests).")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    input_dir: Path = args.input
    output_root: Path = args.output
    schema_path: Optional[Path] = args.schema
    manifest_path: Optional[Path] = args.manifest
    workers: int = max(1, args.workers)
    only: Optional[Sequence[str]] = args.only
    resume: bool = args.resume
    dry_run: bool = args.dry_run
    write_parquet: bool = not args.no_parquet
    limit: Optional[int] = args.limit

    output_root.mkdir(parents=True, exist_ok=True)
    log_path = configure_logger(output_root)

    logging.info("🌊 Metric Fixer Batch starting")
    logging.info("Input directory: %s", input_dir)
    logging.info("Output directory: %s", output_root)
    logging.info("Log file: %s", log_path)

    schema = load_schema(schema_path)
    schema_payload = {name: cfg.to_payload() for name, cfg in schema.items()}
    logging.info("Loaded schema with %d columns", len(schema_payload))

    if not input_dir.exists():
        logging.error("Input directory does not exist: %s", input_dir)
        raise SystemExit(1)

    all_files = discover_files(input_dir)
    if only:
        only_set = {name.lower() for name in only}
        all_files = [p for p in all_files if p.name.lower() in only_set]

    if limit is not None:
        all_files = all_files[: max(0, limit)]

    if not all_files:
        logging.warning("No CSV files found to process.")
        return

    logging.info("Discovered %d CSV file(s)", len(all_files))

    manifest_path = manifest_path or default_manifest_name(output_root)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    completed_records = load_completed_from_manifest(manifest_path) if resume else {}

    files_to_process: List[Path] = []
    for path in all_files:
        if resume and str(path) in completed_records:
            logging.info("Skipping (resume enabled): %s", path.name)
            continue
        files_to_process.append(path)

    if not files_to_process:
        logging.info("All files were previously processed successfully.")
        return

    logging.info("Processing %d file(s)...", len(files_to_process))

    summary = {
        "total": len(files_to_process),
        "success": 0,
        "failed": 0,
        "rows": 0,
        "coercions": Counter(),
    }

    with manifest_path.open("a", encoding="utf-8") as manifest_handle:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(
                    process_file,
                    file_path,
                    output_root,
                    schema_payload,
                    write_parquet,
                    dry_run,
                ): file_path
                for file_path in files_to_process
            }

            for idx, future in enumerate(as_completed(futures), start=1):
                file_path = futures[future]
                try:
                    result = future.result()
                    summary["success"] += 1
                    summary["rows"] += result.get("rows", 0)

                    for column_stats in result.get("coercions", {}).values():
                        summary["coercions"].update(column_stats)

                    logging.info("[%d/%d] ✅ %s — rows: %s", idx, summary["total"], file_path.name, result.get("rows"))
                except Exception as exc:  # pragma: no cover - defensive
                    summary["failed"] += 1
                    result = {
                        "file": str(file_path),
                        "success": False,
                        "error": str(exc),
                    }
                    logging.exception("[%d/%d] ❌ %s", idx, summary["total"], file_path.name)

                result["timestamp"] = now_ts()
                manifest_handle.write(json.dumps(result, ensure_ascii=False))
                manifest_handle.write("\n")
                manifest_handle.flush()

    logging.info("✅ Processing complete")
    logging.info("Files — success: %d, failed: %d, total rows: %d", summary["success"], summary["failed"], summary["rows"])
    if summary["coercions"]:
        logging.info("Coercion counters: %s", dict(summary["coercions"]))
    logging.info("Manifest saved to: %s", manifest_path)


if __name__ == "__main__":
    main()

