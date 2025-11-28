"""
Date format converter engine.

Provides shared batch logic for both the CLI and GUI wrappers.
Normalises a single date column to a canonical output format while emitting
manifest records for auditability and resume support.
"""

from __future__ import annotations

import json
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Tuple

import pandas as pd

# Tokens considered empty/invalid for date parsing.
INVALID_TOKENS = {"", " ", "na", "n/a", "none", "null", "nan", "-", "—"}
DEFAULT_CHUNK_SIZE = 50_000


@dataclass(slots=True)
class DateConversionConfig:
    column_name: str
    input_formats: Tuple[str, ...]
    output_format: str
    fallback_mode: str = "blank"  # blank | original | constant
    fallback_value: str = ""
    keep_original: bool = False
    infer_missing_formats: bool = True


@dataclass(slots=True)
class BatchConfig:
    output_root: Path
    workers: int = 1
    dry_run: bool = False
    write_parquet: bool = False
    resume: bool = False
    manifest_path: Optional[Path] = None
    chunk_size: int = DEFAULT_CHUNK_SIZE


def default_manifest_name(root: Path) -> Path:
    return root / "manifest.jsonl"


def discover_files(root: Path) -> List[Path]:
    if not root.exists():
        return []
    return sorted([path for path in root.glob("*.csv") if path.is_file()])


def load_completed_from_manifest(path: Optional[Path]) -> Dict[str, Dict]:
    if path is None or not path.exists():
        return {}

    cache: Dict[str, Dict] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            input_path = record.get("input_path")
            if input_path:
                cache[input_path] = record
    return cache


def append_manifest_record(path: Path, record: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False))
        handle.write("\n")


def _sanitize_value(value: object) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    if isinstance(value, str):
        text = value.strip()
    else:
        text = str(value).strip()
    if not text:
        return None
    lowered = text.lower()
    if lowered in INVALID_TOKENS:
        return None
    return text


def _parse_with_formats(value: str, formats: Iterable[str]) -> Optional[datetime]:
    for fmt in formats:
        try:
            return datetime.strptime(value, fmt)
        except (ValueError, TypeError):
            continue
    return None


def _infer_datetime(value: str) -> Optional[datetime]:
    try:
        parsed = pd.to_datetime(value, errors="coerce")
    except Exception:
        return None
    if pd.isna(parsed):
        return None
    if isinstance(parsed, pd.Timestamp):
        return parsed.to_pydatetime()
    if isinstance(parsed, datetime):
        return parsed
    return None


def _fallback_value(raw_value: object, config: DateConversionConfig) -> str:
    if config.fallback_mode == "original":
        return "" if raw_value is None else str(raw_value)
    if config.fallback_mode == "constant":
        return config.fallback_value
    return ""


def convert_value(
    raw_value: object,
    config: DateConversionConfig,
    counters: Dict[str, int],
) -> str:
    cleaned = _sanitize_value(raw_value)
    if cleaned is None:
        counters["fallback"] += 1
        return _fallback_value(raw_value, config)

    parsed = _parse_with_formats(cleaned, config.input_formats)
    if parsed is not None:
        counters["parsed"] += 1
        return parsed.strftime(config.output_format)

    if config.infer_missing_formats:
        inferred = _infer_datetime(cleaned)
        if inferred is not None:
            counters["parsed_inferred"] += 1
            return inferred.strftime(config.output_format)

    counters["fallback"] += 1
    return _fallback_value(raw_value, config)


def _prepare_directories(batch_cfg: BatchConfig) -> Dict[str, Path]:
    output_root = batch_cfg.output_root
    output_root.mkdir(parents=True, exist_ok=True)
    csv_dir = output_root / "Converted"
    parquet_dir = output_root / "ConvertedParquet"
    if not batch_cfg.dry_run:
        csv_dir.mkdir(parents=True, exist_ok=True)
        if batch_cfg.write_parquet:
            parquet_dir.mkdir(parents=True, exist_ok=True)
    return {"csv": csv_dir, "parquet": parquet_dir}


def _process_chunk(
    chunk: pd.DataFrame,
    config: DateConversionConfig,
    counters: Dict[str, int],
    backup_name: Optional[str],
) -> pd.DataFrame:
    if backup_name is not None:
        chunk[backup_name] = chunk[config.column_name]
    chunk[config.column_name] = chunk[config.column_name].map(
        lambda value: convert_value(value, config, counters)
    )
    return chunk


def process_file(
    file_path: Path,
    config: DateConversionConfig,
    batch_cfg: BatchConfig,
) -> Dict[str, object]:
    record: Dict[str, object] = {
        "input_path": str(file_path),
        "status": "failed",
        "parsed": 0,
        "parsed_inferred": 0,
        "fallback": 0,
        "output_csv": "",
        "output_parquet": "",
        "message": "",
        "bytes": file_path.stat().st_size if file_path.exists() else 0,
    }

    if not file_path.exists():
        record["message"] = "file missing"
        return record

    column_name = config.column_name
    counters = {"parsed": 0, "parsed_inferred": 0, "fallback": 0}

    backup_name: Optional[str] = f"{column_name}_raw" if config.keep_original else None

    try:
        chunk_iter = pd.read_csv(
            file_path,
            dtype=str,
            keep_default_na=False,
            encoding="utf-8-sig",
            chunksize=batch_cfg.chunk_size,
        )
    except Exception as exc:
        record["message"] = f"unable to read file: {exc}"
        return record

    written_chunks = 0
    if batch_cfg.write_parquet:
        parquet_chunks: List[pd.DataFrame] = []
    else:
        parquet_chunks = []

    directories = _prepare_directories(batch_cfg)
    csv_output = directories["csv"] / file_path.name

    try:
        for chunk in chunk_iter:
            if column_name not in chunk.columns:
                record["message"] = f"column '{column_name}' not found"
                return record

            processed_chunk = _process_chunk(chunk, config, counters, backup_name)

            if not batch_cfg.dry_run:
                processed_chunk.to_csv(
                    csv_output,
                    mode="w" if written_chunks == 0 else "a",
                    header=written_chunks == 0,
                    index=False,
                    encoding="utf-8-sig",
                )
            if batch_cfg.write_parquet:
                parquet_chunks.append(processed_chunk.copy(deep=True))

            written_chunks += 1
    except Exception as exc:
        record["message"] = f"conversion failed: {exc}"
        return record

    if written_chunks == 0:
        record["message"] = "empty file"
        return record

    record["parsed"] = counters["parsed"]
    record["parsed_inferred"] = counters["parsed_inferred"]
    record["fallback"] = counters["fallback"]

    if batch_cfg.dry_run:
        record["status"] = "success"
        record["message"] = "dry_run"
        return record

    record["output_csv"] = str(csv_output)

    if batch_cfg.write_parquet:
        parquet_output = directories["parquet"] / file_path.with_suffix(".parquet").name
        try:
            combined = pd.concat(parquet_chunks, ignore_index=True)
            combined.to_parquet(parquet_output, index=False)
            record["output_parquet"] = str(parquet_output)
        except Exception as exc:
            record["message"] = f"csv written but parquet failed: {exc}"
            record["status"] = "partial"
            return record

    record["status"] = "success"
    return record


def _progress_callback_factory(callback: Optional[Callable[[int, int, Dict[str, object]], None]]):
    if callback is None:
        return lambda *_: None
    return callback


def run_batch(
    files: Iterable[Path],
    config: DateConversionConfig,
    batch_cfg: BatchConfig,
    resume_cache: Optional[Dict[str, Dict]] = None,
    progress_callback: Optional[Callable[[int, int, Dict[str, object]], None]] = None,
) -> Dict[str, object]:
    manifest_path = batch_cfg.manifest_path or default_manifest_name(batch_cfg.output_root)
    batch_cfg.manifest_path = manifest_path
    if not batch_cfg.dry_run:
        manifest_path.parent.mkdir(parents=True, exist_ok=True)

    files_list = list(files)
    resume_cache = resume_cache or {}
    totals = {
        "total": len(files_list),
        "success": 0,
        "failed": 0,
        "skipped": 0,
        "parsed": 0,
        "parsed_inferred": 0,
        "fallback": 0,
        "bytes_total": 0,
    }
    results: List[Dict[str, object]] = []
    progress = _progress_callback_factory(progress_callback)

    directories = _prepare_directories(batch_cfg)

    for path in files_list:
        if path.exists():
            totals["bytes_total"] += path.stat().st_size

    progress_count = 0

    pending_files: List[Path] = []
    for file_path in files_list:
        input_key = str(file_path)
        if batch_cfg.resume and input_key in resume_cache:
            totals["skipped"] += 1
            cached_record = dict(resume_cache[input_key])
            cached_record.setdefault("status", "skipped")
            cached_record["skipped"] = True
            results.append(cached_record)
            progress_count += 1
            progress(progress_count, totals["total"], cached_record)
            continue
        pending_files.append(file_path)

    def _handle_record(record: Dict[str, object]) -> None:
        nonlocal progress_count

        record["manifest_path"] = str(manifest_path)
        results.append(record)

        status = record.get("status")
        if status == "success":
            totals["success"] += 1
        elif status == "partial":
            totals["success"] += 1
        else:
            totals["failed"] += 1

        totals["parsed"] += int(record.get("parsed", 0) or 0)
        totals["parsed_inferred"] += int(record.get("parsed_inferred", 0) or 0)
        totals["fallback"] += int(record.get("fallback", 0) or 0)

        if not batch_cfg.dry_run:
            append_manifest_record(manifest_path, record)

        progress_count += 1
        progress(progress_count, totals["total"], record)

    if not pending_files:
        summary = {
            **totals,
            "dry_run": batch_cfg.dry_run,
            "output_root": str(batch_cfg.output_root),
            "manifest": str(manifest_path),
            "write_parquet": batch_cfg.write_parquet,
            "results": results,
            "csv_directory": str(directories["csv"]),
            "parquet_directory": str(directories["parquet"]),
        }
        return summary

    if batch_cfg.workers <= 1:
        for file_path in pending_files:
            record = process_file(file_path, config, batch_cfg)
            _handle_record(record)
    else:
        with ProcessPoolExecutor(max_workers=batch_cfg.workers) as executor:
            future_map = {
                executor.submit(process_file, file_path, config, batch_cfg): file_path
                for file_path in pending_files
            }
            for future in as_completed(future_map):
                file_path = future_map[future]
                try:
                    record = future.result()
                except Exception as exc:  # pragma: no cover - defensive
                    record = {
                        "input_path": str(file_path),
                        "status": "failed",
                        "parsed": 0,
                        "parsed_inferred": 0,
                        "fallback": 0,
                        "output_csv": "",
                        "output_parquet": "",
                        "message": f"worker exception: {exc}",
                        "bytes": file_path.stat().st_size if file_path.exists() else 0,
                    }
                _handle_record(record)

    summary = {
        **totals,
        "dry_run": batch_cfg.dry_run,
        "output_root": str(batch_cfg.output_root),
        "manifest": str(manifest_path),
        "write_parquet": batch_cfg.write_parquet,
        "results": results,
        "csv_directory": str(directories["csv"]),
        "parquet_directory": str(directories["parquet"]),
    }
    return summary


__all__ = [
    "BatchConfig",
    "DateConversionConfig",
    "DEFAULT_CHUNK_SIZE",
    "default_manifest_name",
    "discover_files",
    "load_completed_from_manifest",
    "run_batch",
    "process_file",
    "convert_value",
]

