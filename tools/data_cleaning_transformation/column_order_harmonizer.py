"""
🌊 Column Order Harmonizer
Reorder CSV columns to match curated presets (with duplicate stripping).
"""

from __future__ import annotations

import csv
import os
import re
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PySide6.QtCore import Qt, QObject, QThread, Signal, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QProgressBar,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
import pandas as pd

from tools.templates import BaseToolDialog, PathConfigMixin
from styles import get_path_manager


def _normalize_header_name(value: str) -> str:
    """Normalize a header name for canonical comparison."""
    lower = value.strip().lower()
    replaced = lower.replace("_", " ").replace("-", " ")
    return " ".join(replaced.split())


_DEFAULT_SEQUENCE = [
    "Website Name",
    "Event name",
    "Date",
    "FullURL",
    "Country",
    "Device category",
    "Session default channel grouping",
    "Session medium",
    "Session source",
    "Session campaign",
    "Sessions",
    "Event count",
    "Engaged sessions",
    "Engagement rate",
    "Views",
    "Active users",
    "New users",
    "Total users",
    "Total revenue",
]

_PRESET_DEFINITIONS: Dict[str, List[str]] = {
    "Default (Website Metrics)": _DEFAULT_SEQUENCE,
}

_COLUMN_SYNONYMS_RAW: Dict[str, str] = {
    "website_name": "Website Name",
    "event_name": "Event name",
    "full_url": "FullURL",
    "full url": "FullURL",
    "fullurl": "FullURL",
    "session_default_channel_grouping": "Session default channel grouping",
    "session_default_channel_group": "Session default channel grouping",
    "session_medium": "Session medium",
    "session_source": "Session source",
    "session_campaign": "Session campaign",
    "sessions": "Sessions",
    "event_count": "Event count",
    "engaged_sessions": "Engaged sessions",
    "engagement_rate": "Engagement rate",
    "views": "Views",
    "active_users": "Active users",
    "new_users": "New users",
    "total_users": "Total users",
    "total_revenue": "Total revenue",
}

_CANONICAL_COLUMNS = OrderedDict(
    (_normalize_header_name(name), name) for name in _DEFAULT_SEQUENCE
)
_CANONICAL_LOOKUP: Dict[str, str] = dict(_CANONICAL_COLUMNS)
_DISPLAY_TO_NORMALIZED: Dict[str, str] = {
    display: normalized for normalized, display in _CANONICAL_COLUMNS.items()
}
for variant, display in _COLUMN_SYNONYMS_RAW.items():
    canonical_display = display
    if canonical_display not in _DISPLAY_TO_NORMALIZED:
        continue
    variant_normalized = _normalize_header_name(variant)
    _CANONICAL_LOOKUP[variant_normalized] = canonical_display

_TIMESTAMP_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}_\d{4}(?:_\d{2})?")
_SANITIZED_TOOL_NAME = re.sub(r"[^A-Za-z0-9]+", "_", "Column Order Harmonizer").strip("_")
_SANITIZED_SCRIPT_NAME = re.sub(
    r"[^A-Za-z0-9]+", "_", Path(__file__).name
).strip("_") or "Script"


@dataclass
class HarmonizerResult:
    success: int = 0
    failed: int = 0
    duplicates_removed: int = 0
    extras_removed: int = 0


@dataclass
class ColumnCandidateInfo:
    df_col: str
    raw_name: str
    original_index: int
    canonical_name: Optional[str] = None


@dataclass
class OutputColumnTracker:
    non_empty_count: int = 0
    total_rows: int = 0
    rows_per_chunk: List[int] = field(default_factory=list)


class ColumnOrderWorker(QObject):
    progress_signal = Signal(int, int)
    status_signal = Signal(str)
    log_signal = Signal(str)
    finished_signal = Signal(int, int)

    def __init__(
        self,
        files: List[Path],
        column_sequence: List[str],
        remove_extra_columns: bool,
        input_path: Path,
        output_path: Path,
        output_success_path: Path,
        output_failed_path: Path,
        report_root_path: Path,
        chunksize: int = 100_000,
        max_workers: int = 8,
    ) -> None:
        super().__init__()
        self.files = files
        self.column_sequence = column_sequence
        self.remove_extra_columns = remove_extra_columns
        self.input_path = input_path
        self.output_path = output_path
        self.output_success_path = output_success_path
        self.output_failed_path = output_failed_path
        self.report_root_path = report_root_path
        self.chunksize = chunksize
        self.max_workers = max_workers
        self._stop = False
        self.results: List[Dict[str, str]] = []

    def run(self) -> None:
        result_success = 0
        result_failed = 0
        total = len(self.files)

        self.log_signal.emit(
            f"🚀 Starting harmonization of {total} file(s) (chunksize={self.chunksize})"
        )

        workers = min(self.max_workers, max(1, total))
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futures = {
                ex.submit(self._process_file, file_path): file_path for file_path in self.files
            }
            completed = 0
            for fut in as_completed(futures):
                if self._stop:
                    break
                file_path = futures[fut]
                completed += 1
                try:
                    success, reason = fut.result()
                    if success:
                        result_success += 1
                        self.log_signal.emit(f"✅ Column order updated for {file_path.name}")
                        self.results.append({"file": file_path.name, "status": "success", "reason": ""})
                    else:
                        result_failed += 1
                        self.results.append({"file": file_path.name, "status": "failed", "reason": reason or "Unknown failure"})
                except Exception as exc:
                    result_failed += 1
                    message = f"❌ Failed to process {file_path.name}: {exc}"
                    self.log_signal.emit(message)
                    self.results.append({"file": file_path.name, "status": "failed", "reason": str(exc)})

                self.progress_signal.emit(completed, total)
                self.status_signal.emit(f"Processed {completed}/{total}: {file_path.name}")

        self._write_report()
        self.finished_signal.emit(result_success, result_failed)

    def stop(self) -> None:
        self._stop = True

    def _copy_to_failed(self, file_path: Path) -> None:
        if self.output_failed_path is None:
            return
        try:
            self.output_failed_path.mkdir(parents=True, exist_ok=True)
            target = self.output_failed_path / file_path.name
            shutil.copy2(file_path, target)
        except Exception as exc:  # pragma: no cover - defensive
            self.log_signal.emit(f"⚠️ Unable to copy {file_path.name} to failed folder: {exc}")

    def _normalize_cols(self, cols: List[str]) -> List[str]:
        return [c.strip() for c in cols]

    def _detect_csv_dialect(self, file_path: Path) -> Tuple[csv.Dialect, str]:
        """
        Sniff the CSV dialect for delimiter/quoting preservation. Falls back to csv.excel.
        Returns the dialect alongside a non-empty line terminator.
        """
        default_dialect = csv.excel
        fallback_lineterminator = "\n"
        try:
            with file_path.open("r", encoding="utf-8-sig", newline="") as handle:
                sample = handle.read(2048)
                handle.seek(0)
                if sample.strip():
                    detected = csv.Sniffer().sniff(sample)
                else:
                    detected = default_dialect
        except Exception as exc:  # pragma: no cover - defensive
            self.log_signal.emit(
                f"⚠️ Unable to sniff CSV dialect for {file_path.name}. Using defaults. ({exc})"
            )
            detected = default_dialect

        line_terminator = getattr(detected, "lineterminator", None) or fallback_lineterminator
        return detected, line_terminator

    def _process_file(self, file_path: Path) -> Tuple[bool, Optional[str]]:
        try:
            dialect, line_terminator = self._detect_csv_dialect(file_path)

            with file_path.open("r", encoding="utf-8-sig", newline="") as fh:
                reader = csv.reader(fh, dialect=dialect)
                raw_header = next(reader, [])
                if not raw_header:
                    reason = "Empty file"
                    self.log_signal.emit(f"❌ {reason}: {file_path.name}")
                    self._copy_to_failed(file_path)
                    return False, reason

            trimmed_header = [name.strip() for name in raw_header]
            candidate_map: Dict[str, List[ColumnCandidateInfo]] = {}
            direct_candidates: Dict[str, List[ColumnCandidateInfo]] = {}
            extras_by_normalized: Dict[str, List[ColumnCandidateInfo]] = {}

            for idx, raw_name in enumerate(trimmed_header):
                normalized = _normalize_header_name(raw_name)
                canonical_display = _CANONICAL_LOOKUP.get(normalized)
                candidate = ColumnCandidateInfo(
                    df_col=raw_name,
                    raw_name=raw_name,
                    original_index=idx,
                    canonical_name=canonical_display,
                )
                if canonical_display:
                    candidate_map.setdefault(canonical_display, []).append(candidate)
                else:
                    extras_by_normalized.setdefault(normalized, []).append(candidate)
                direct_candidates.setdefault(raw_name, []).append(candidate)

            missing_columns: List[str] = []
            ambiguous_columns: List[str] = []
            selected_ga4: "OrderedDict[str, ColumnCandidateInfo]" = OrderedDict()

            for display_name in self.column_sequence:
                normalized_expected = _normalize_header_name(display_name)
                canonical_display = _CANONICAL_LOOKUP.get(normalized_expected)

                if canonical_display:
                    candidates = candidate_map.get(canonical_display, [])
                    error_label = canonical_display
                    target_name = canonical_display
                else:
                    candidates = direct_candidates.get(display_name, [])
                    error_label = display_name
                    target_name = display_name
                if not candidates:
                    missing_columns.append(error_label)
                    continue
                if len(candidates) > 1:
                    ambiguous_columns.append(error_label)
                    continue
                selected_candidate = candidates[0]
                selected_ga4[target_name] = selected_candidate
                if selected_candidate.canonical_name is None:
                    normalized_selected = _normalize_header_name(selected_candidate.raw_name)
                    existing = extras_by_normalized.get(normalized_selected, [])
                    filtered = [
                        extra for extra in existing if extra.original_index != selected_candidate.original_index
                    ]
                    if filtered:
                        extras_by_normalized[normalized_selected] = filtered
                    elif normalized_selected in extras_by_normalized:
                        extras_by_normalized.pop(normalized_selected)

            if ambiguous_columns:
                reason = f"Ambiguous columns detected: {', '.join(ambiguous_columns)}"
                self.log_signal.emit(f"❌ {reason} in {file_path.name}")
                self._copy_to_failed(file_path)
                return False, reason

            if missing_columns:
                reason = f"Missing required columns: {', '.join(missing_columns)}"
                self.log_signal.emit(f"❌ {reason} in {file_path.name}")
                self._copy_to_failed(file_path)
                return False, reason

            extras_preserved: List[ColumnCandidateInfo] = []
            for norm, candidates in extras_by_normalized.items():
                if len(candidates) > 1:
                    names = ", ".join(candidate.raw_name for candidate in candidates)
                    self.log_signal.emit(
                        f"⚠️ Duplicate non-contract columns detected ({names}) in {file_path.name}; using first occurrence."
                    )
                best_candidate = min(candidates, key=lambda candidate: candidate.original_index)
                extras_preserved.append(best_candidate)

            extras_preserved.sort(key=lambda candidate: candidate.original_index)

            if self.remove_extra_columns:
                extras_preserved = []

            ordered_header = list(selected_ga4.keys())
            extras_map: Dict[str, ColumnCandidateInfo] = {}
            if extras_preserved:
                for candidate in extras_preserved:
                    ordered_header.append(candidate.raw_name)
                    extras_map[candidate.raw_name] = candidate

            renamed_columns = {
                display_name: candidate
                for display_name, candidate in selected_ga4.items()
                if candidate.df_col != display_name
            }

            fresh_reader = pd.read_csv(
                file_path,
                dtype=str,
                encoding="utf-8-sig",
                low_memory=False,
                sep=dialect.delimiter,
                quotechar=dialect.quotechar,
                doublequote=dialect.doublequote,
                escapechar=dialect.escapechar,
                quoting=dialect.quoting,
                chunksize=self.chunksize,
                keep_default_na=False,
            )

            self.output_success_path.mkdir(parents=True, exist_ok=True)
            output_file = self.output_success_path / file_path.name
            if output_file.exists():
                output_file.unlink()

            header_written = False
            wrote_any = False
            output_trackers: Dict[str, OutputColumnTracker] = {
                column_name: OutputColumnTracker() for column_name in ordered_header
            }
            total_rows_processed = 0
            chunk_index = 0

            self.log_signal.emit(f"📄 File: {file_path.name}")
            if renamed_columns:
                for display_name, candidate in renamed_columns.items():
                    self.log_signal.emit(
                        f"   └─ Renamed column '{candidate.df_col}' → '{display_name}'"
                    )

            for chunk in fresh_reader:
                chunk.columns = self._normalize_cols(list(chunk.columns))
                row_count = len(chunk.index)
                if row_count == 0:
                    continue

                output_columns: Dict[str, pd.Series] = {}
                for display_name, candidate in selected_ga4.items():
                    column_key = candidate.df_col
                    if column_key in chunk.columns:
                        series = chunk[column_key].astype(str)
                    else:
                        series = pd.Series([""] * row_count, dtype=str)
                    tracker = output_trackers[display_name]
                    tracker.total_rows += row_count
                    tracker.non_empty_count += int(series.str.strip().ne("").sum())
                    tracker.rows_per_chunk.append(row_count)
                    output_columns[display_name] = series

                for extra_name, candidate in extras_map.items():
                    if candidate.df_col in chunk.columns:
                        series = chunk[candidate.df_col].astype(str)
                    else:
                        series = pd.Series([""] * row_count, dtype=str)
                    tracker = output_trackers[extra_name]
                    tracker.total_rows += row_count
                    tracker.non_empty_count += int(series.str.strip().ne("").sum())
                    tracker.rows_per_chunk.append(row_count)
                    output_columns[extra_name] = series

                out_chunk = pd.DataFrame(output_columns, columns=ordered_header)
                mode = "a" if header_written else "w"
                to_csv_kwargs = {
                    "index": False,
                    "mode": mode,
                    "header": not header_written,
                    "encoding": "utf-8-sig",
                    "sep": dialect.delimiter,
                    "quotechar": dialect.quotechar,
                    "doublequote": dialect.doublequote,
                    "escapechar": dialect.escapechar,
                    "quoting": dialect.quoting,
                }
                if line_terminator:
                    to_csv_kwargs["lineterminator"] = line_terminator
                out_chunk.to_csv(output_file, **to_csv_kwargs)
                header_written = True
                wrote_any = True
                chunk_index += 1
                total_rows_processed += row_count
                approx = f"~{self.chunksize:,}" if row_count >= self.chunksize else f"{row_count:,}"
                self.log_signal.emit(
                    f"   └─ Chunk {chunk_index}: processed {approx} rows (cumulative {total_rows_processed:,})"
                )

            if not wrote_any:
                with output_file.open("w", encoding="utf-8-sig", newline="") as fh:
                    writer_kwargs = {
                        "delimiter": dialect.delimiter,
                        "quotechar": dialect.quotechar,
                        "doublequote": dialect.doublequote,
                        "escapechar": dialect.escapechar,
                        "quoting": dialect.quoting,
                    }
                    if line_terminator:
                        writer_kwargs["lineterminator"] = line_terminator
                    writer = csv.writer(fh, **writer_kwargs)
                    writer.writerow(ordered_header)
                self.log_signal.emit("   └─ No data rows detected; header written only.")
            else:
                self.log_signal.emit(
                    f"   └─ Total rows processed: {total_rows_processed:,} across {chunk_index} chunk(s)"
                )
                self.log_signal.emit("   └─ Done update.")

            validation_success = self._validate_output_file(
                output_file=output_file,
                ordered_header=ordered_header,
                output_trackers=output_trackers,
                total_rows_processed=total_rows_processed,
            )
            if not validation_success:
                self.log_signal.emit(
                    f"❌ Validation failed for {file_path.name}. Removing output file."
                )
                if output_file.exists():
                    try:
                        output_file.unlink()
                    except Exception:
                        pass
                self._copy_to_failed(file_path)
                return False, "Validation failed"

            if extras_preserved and not self.remove_extra_columns:
                extras_names = ", ".join(candidate.raw_name for candidate in extras_preserved)
                self.log_signal.emit(
                    f"➕ Preserved additional column(s) appended in {file_path.name}: {extras_names}"
                )

            return True, None
        except Exception as exc:
            self.log_signal.emit(f"❌ Failed to process {file_path.name}: {exc}")
            self._copy_to_failed(file_path)
            return False, str(exc)

    def _compute_candidate_metrics(
        self, file_path: Path, candidates: List[ColumnCandidateInfo]
    ) -> None:
        raise RuntimeError("_compute_candidate_metrics is obsolete and should not be called.")

    def _select_best_candidate(
        self, candidates: List[ColumnCandidateInfo]
    ) -> Tuple[ColumnCandidateInfo, int, int]:
        raise RuntimeError("_select_best_candidate is obsolete and should not be called.")

    def _validate_output_file(
        self,
        output_file: Path,
        ordered_header: List[str],
        output_trackers: Dict[str, OutputColumnTracker],
        total_rows_processed: int,
    ) -> bool:
        try:
            with output_file.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.reader(handle)
                header = next(reader, [])
                row_count_out = sum(1 for _ in reader)
            if header != ordered_header:
                self.log_signal.emit(
                    f"❌ Header validation failed for {output_file.name}: expected {ordered_header}, found {header}"
                )
                return False
            if row_count_out != total_rows_processed:
                self.log_signal.emit(
                    f"❌ Row count mismatch for {output_file.name}: expected {total_rows_processed}, found {row_count_out}"
                )
                return False

            for column_name, tracker in output_trackers.items():
                if tracker.total_rows != total_rows_processed:
                    self.log_signal.emit(
                        f"❌ Row alignment mismatch in column '{column_name}' for {output_file.name}."
                    )
                    return False

            return True
        except Exception as exc:
            self.log_signal.emit(f"❌ Validation error for {output_file.name}: {exc}")
            return False

    def _write_report(self) -> None:
        if not self.results:
            return
        if self.report_root_path is None:
            return
        try:
            self.report_root_path.mkdir(parents=True, exist_ok=True)
            report_path = self.report_root_path / "_harmonization_report.txt"
            success_count = sum(1 for entry in self.results if entry["status"] == "success")
            failed_entries = [entry for entry in self.results if entry["status"] == "failed"]
            total = len(self.results)
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            lines: List[str] = [
                "Column Order Harmonizer — Run Summary",
                f"Timestamp         : {timestamp}",
                f"Files Processed   : {total}",
                f"Successes         : {success_count}",
                f"Failures          : {len(failed_entries)}",
                "",
            ]
            if failed_entries:
                lines.append("Failures:")
                for entry in failed_entries:
                    reason = entry["reason"] or "Unknown failure"
                    lines.append(f"  - {entry['file']}: {reason}")
                lines.append("")
            else:
                lines.append("No failures recorded. All files harmonized successfully.")
                lines.append("")
            lines.append("End of report.")
            with report_path.open("w", encoding="utf-8") as handle:
                handle.write("\n".join(lines))
            self.log_signal.emit(f"📝 Harmonization summary saved to {report_path}")
        except Exception as exc:
            self.log_signal.emit(f"⚠️ Unable to write harmonization report: {exc}")


@dataclass
class ScanResult:
    file_path: Path
    columns: int
    rows: int


class FileScanWorker(QObject):
    progress_signal = Signal(int, int)
    file_scanned = Signal(int, Path, int, int)
    log_signal = Signal(str)
    finished_signal = Signal(list, dict)

    def __init__(self, files: List[Path], cache_snapshot: Dict[str, Tuple[float, int, int]]):
        super().__init__()
        self.files = files
        self.cache_snapshot = cache_snapshot or {}
        self.updated_cache: Dict[str, Tuple[float, int, int]] = {}
        self._stop = False

    def stop(self) -> None:
        self._stop = True

    def run(self) -> None:
        total = len(self.files)
        results: List[ScanResult] = []

        for index, file_path in enumerate(self.files, start=1):
            if self._stop:
                break
            columns, rows = self._inspect_file(file_path)
            results.append(ScanResult(file_path=file_path, columns=columns, rows=rows))
            self.file_scanned.emit(index, file_path, columns, rows)
            self.progress_signal.emit(index, total)

        self.finished_signal.emit(results, self.updated_cache)

    def _inspect_file(self, csv_file: Path) -> Tuple[int, int]:
        cache_key = str(csv_file.resolve())
        try:
            stat_info = csv_file.stat()
            cached = self.cache_snapshot.get(cache_key)
            if cached and cached[0] == stat_info.st_mtime_ns:
                self.updated_cache[cache_key] = cached
                return cached[1], cached[2]

            columns = 0
            rows = 0
            with csv_file.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.reader(handle)
                header = next(reader, [])
                columns = len(header)
                for _ in reader:
                    rows += 1

            self.updated_cache[cache_key] = (stat_info.st_mtime_ns, columns, rows)
            return columns, rows
        except Exception as exc:
            self.log_signal.emit(f"⚠️ Failed to inspect {csv_file.name}: {exc}")
            self.updated_cache[cache_key] = (0.0, 0, 0)
            return 0, 0


class ColumnOrderHarmonizer(PathConfigMixin, BaseToolDialog):
    """Dialog for harmonizing column order based on presets."""

    PATH_CONFIG = {
        "show_input": True,
        "show_output": True,
        "include_open_buttons": True,
        "input_label": "📥 Input Folder:",
        "output_label": "📤 Output Folder:",
    }

    def __init__(self, parent, input_path: str, output_path: str):
        super().__init__(parent, input_path, output_path)

        self.setup_window_properties(
            title="🌊 Column Order Harmonizer",
            width=1200,
            height=820,
        )

        self.csv_files: List[Path] = []
        self.worker_thread: Optional[QThread] = None
        self.worker: Optional[ColumnOrderWorker] = None
        self.scan_worker_thread: Optional[QThread] = None
        self.scan_worker: Optional[FileScanWorker] = None

        self._custom_presets: Dict[str, List[str]] = {}
        self.remove_extra_columns = False
        self.batch_size_limit: int = 0  # 0 = process all files; override in code if needed.
        self._scan_cache: Dict[str, Tuple[float, int, int]] = {}
        self.test_mode = False
        self._user_input_path: Optional[Path] = None
        self._user_output_path: Optional[Path] = None
        self.output_run_root: Optional[Path] = None
        self.output_run_success: Optional[Path] = None
        self.output_run_failed: Optional[Path] = None

        self._initializing_ui = True
        self.setup_ui()
        self._sync_path_edits(self.input_path, self.output_path)
        self.scan_files()
        self._initializing_ui = False

    def setup_ui(self) -> None:
        self._initializing_ui = True

        self.setMinimumSize(960, 720)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(14)

        header_label = QLabel("🌊 Column Order Harmonizer")
        header_label.setFont(QFont("Arial", 22, QFont.Bold))
        header_label.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(header_label)

        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName("contentScroll")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.content_widget = QWidget()
        content_layout = QVBoxLayout(self.content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(15)

        self.path_section = self.build_path_section()
        content_layout.addWidget(self.path_section)

        self.files_section = self.build_files_panel()
        content_layout.addWidget(self.files_section)

        self.workspace_section = self.build_workspace_panel()
        content_layout.addWidget(self.workspace_section)

        self.action_section = self.build_action_panel()
        content_layout.addWidget(self.action_section)

        content_layout.addStretch(1)

        self.scroll_area.setWidget(self.content_widget)
        self.main_layout.addWidget(self.scroll_area, 1)

        self.log_section = self.build_log_panel()
        if self.log_section is not None:
            self.main_layout.addWidget(self.log_section)

        self._apply_theme_styles()
        self._initializing_ui = False
        self._toggle_files_empty_state(False, "No CSV files detected. Click \"Scan Files\" to refresh.")
        self._update_action_state()
        QTimer.singleShot(0, self._update_action_state)
        self._set_status("Ready.")

    def build_path_section(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("pathFrame")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        self.build_path_controls(layout)

        self.test_mode_checkbox = QCheckBox("Test Mode (use golden dataset)")
        self.test_mode_checkbox.setObjectName("modernCheckbox")
        self.test_mode_checkbox.stateChanged.connect(self._toggle_test_mode)
        layout.addWidget(self.test_mode_checkbox)

        button_row = QHBoxLayout()
        button_row.addStretch()
        self.scan_btn = QPushButton("🔄 Scan Files")
        self.scan_btn.clicked.connect(self.scan_files)
        self.scan_btn.setObjectName("glassButton")
        self.scan_btn.setMinimumHeight(36)
        button_row.addWidget(self.scan_btn)
        layout.addLayout(button_row)

        return frame

    def build_files_panel(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("glassFrame")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        title = QLabel("📁 Scanned Files")
        title.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(title)

        self.files_table = QTableWidget()
        self.files_table.setObjectName("tableWidget")
        self.files_table.setColumnCount(3)
        self.files_table.setHorizontalHeaderLabels(["Filename", "Columns (unique)", "Rows"])
        header_view = self.files_table.horizontalHeader()
        header_view.setSectionResizeMode(0, QHeaderView.Stretch)
        header_view.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header_view.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.files_table.setAlternatingRowColors(True)
        self.files_table.setMinimumHeight(220)
        self.files_table.hide()
        layout.addWidget(self.files_table, 1)

        self.files_empty_label = QLabel("No CSV files detected. Click \"Scan Files\" to refresh.")
        self.files_empty_label.setAlignment(Qt.AlignCenter)
        self.files_empty_label.setObjectName("infoLabel")
        self.files_empty_label.setWordWrap(True)
        layout.addWidget(self.files_empty_label)

        return frame

    def build_workspace_panel(self) -> QWidget:
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)

        preset_frame = self.build_preset_panel()
        sequence_frame = self.build_sequence_panel()

        layout.addWidget(preset_frame, 1)
        layout.addWidget(sequence_frame, 1)

        return container

    def build_preset_panel(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("glassFrame")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        row = QHBoxLayout()
        row.setSpacing(10)

        preset_label = QLabel("🎯 Column Preset:")
        preset_label.setFont(QFont("Arial", 11, QFont.Bold))
        row.addWidget(preset_label)

        self.preset_combo = QComboBox()
        self.preset_combo.setObjectName("modernDropdown")
        for name in _PRESET_DEFINITIONS.keys():
            self.preset_combo.addItem(name)
        self.preset_combo.addItem("Custom (edit below)")
        self.preset_combo.currentTextChanged.connect(self.on_preset_changed)
        row.addWidget(self.preset_combo, 1)

        save_btn = QPushButton("💾 Save Custom Preset")
        save_btn.clicked.connect(self.save_custom_preset)
        save_btn.setObjectName("presetButton")
        row.addWidget(save_btn)

        reset_btn = QPushButton("↺ Reset to Preset")
        reset_btn.clicked.connect(self.reset_sequence_text)
        reset_btn.setObjectName("presetButton")
        row.addWidget(reset_btn)

        layout.addLayout(row)

        instructions = QLabel(
            "Enter one column per line. Order is respected; duplicates are removed automatically."
        )
        instructions.setObjectName("infoLabel")
        layout.addWidget(instructions)

        self.preset_status_label = QLabel("Active preset: Default (Website Metrics)")
        self.preset_status_label.setObjectName("infoLabel")
        layout.addWidget(self.preset_status_label)
        self._update_preset_status(self.preset_combo.currentText())

        layout.addStretch(1)

        remove_checkbox = QCheckBox("Remove columns that are not listed in the preset")
        remove_checkbox.setObjectName("modernCheckbox")
        remove_checkbox.stateChanged.connect(self._handle_remove_extras_toggle)
        layout.addWidget(remove_checkbox)
        self.remove_extras_checkbox = remove_checkbox

        return frame

    def build_sequence_panel(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("glassFrame")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        label = QLabel("✍️ Column Sequence")
        label.setFont(QFont("Arial", 11, QFont.Bold))
        layout.addWidget(label)

        hint = QLabel("One column per line. Extra columns remain appended after presets run.")
        hint.setObjectName("infoLabel")
        layout.addWidget(hint)

        self.sequence_editor = QPlainTextEdit()
        self.sequence_editor.setObjectName("logText")
        self.sequence_editor.setPlaceholderText("Website Name\nEvent name\nDate\n...")
        self.sequence_editor.setMinimumHeight(200)
        layout.addWidget(self.sequence_editor)

        self.reset_sequence_text()

        layout.addStretch(1)

        return frame

    def build_action_panel(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("actionFrame")
        outer_layout = QVBoxLayout(frame)
        outer_layout.setContentsMargins(15, 15, 15, 15)
        outer_layout.setSpacing(10)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        outer_layout.addWidget(self.progress_bar)

        button_row = QHBoxLayout()
        button_row.setSpacing(10)

        self.reorder_btn = QPushButton("✨ Harmonize Columns")
        self.reorder_btn.setMinimumHeight(40)
        self.reorder_btn.clicked.connect(self.start_reorder)
        self.reorder_btn.setEnabled(False)
        self.reorder_btn.setObjectName("actionButton")
        button_row.addWidget(self.reorder_btn)

        self.open_output_btn = QPushButton("📁 Open Output")
        self.open_output_btn.clicked.connect(self.open_output_folder)
        self.open_output_btn.setObjectName("actionButton")
        button_row.addWidget(self.open_output_btn)

        self.reset_btn = QPushButton("↺ Reset")
        self.reset_btn.clicked.connect(self.reset_tool_state)
        self.reset_btn.setObjectName("actionButton")
        button_row.addWidget(self.reset_btn)

        button_row.addStretch()

        self.status_label = QLabel("Ready.")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        button_row.addWidget(self.status_label)

        outer_layout.addLayout(button_row)

        return frame

    def build_log_panel(self) -> Optional[QFrame]:
        container = QFrame()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 10, 0, 0)
        container_layout.setSpacing(6)

        title = QLabel("📓 Execution Log")
        title.setFont(QFont("Arial", 11, QFont.Bold))
        container_layout.addWidget(title)

        self.execution_log = self.create_execution_log(container_layout)
        if self.execution_log:
            self.log("Tool initialized! Ready to reorder columns.")
        else:
            container = None

        return container

    def _toggle_files_empty_state(self, has_files: bool, message: Optional[str] = None) -> None:
        if not hasattr(self, "files_table") or not hasattr(self, "files_empty_label"):
            return
        if has_files:
            self.files_empty_label.hide()
            self.files_table.show()
        else:
            if message:
                self.files_empty_label.setText(message)
            self.files_table.hide()
            self.files_empty_label.show()

    def _set_status(self, message: str) -> None:
        if hasattr(self, "status_label"):
            self.status_label.setText(message)

    def _is_worker_active(self) -> bool:
        return bool(self.worker_thread and self.worker_thread.isRunning())

    def _is_scan_active(self) -> bool:
        return bool(self.scan_worker_thread and self.scan_worker_thread.isRunning())

    def _update_action_state(self) -> None:
        has_files = bool(getattr(self, "csv_files", []))
        worker_active = self._is_worker_active()
        scan_active = self._is_scan_active()

        if hasattr(self, "reorder_btn"):
            self.reorder_btn.setEnabled(has_files and not worker_active and not scan_active)
        if hasattr(self, "scan_btn"):
            self.scan_btn.setEnabled(not worker_active and not scan_active)
        if hasattr(self, "reset_btn"):
            self.reset_btn.setEnabled(not worker_active and not scan_active)

    def reset_tool_state(self) -> None:
        if self._is_scan_active():
            QMessageBox.information(
                self,
                "Scan In Progress",
                "Please wait for the file scan to finish before resetting.",
            )
            return
        if self._is_worker_active():
            QMessageBox.information(
                self,
                "Operation In Progress",
                "Please stop the harmonization before resetting the tool.",
            )
            return
        self.csv_files.clear()
        if hasattr(self, "files_table"):
            self.files_table.setRowCount(0)
        self._toggle_files_empty_state(False, "No CSV files detected. Click \"Scan Files\" to refresh.")
        self.reset_sequence_text()
        if hasattr(self, "progress_bar"):
            self.progress_bar.setVisible(False)
            self.progress_bar.setValue(0)
        self._set_status("Ready.")
        self._update_action_state()
        if self.execution_log:
            self.log("🔄 Tool state reset to defaults.")

    def _apply_theme_styles(self) -> None:
        if not getattr(self, "current_theme", None):
            return

        if hasattr(self, "preset_combo"):
            self.current_theme.apply_to_widget(self.preset_combo, "combo")

        if hasattr(self, "sequence_editor"):
            self.current_theme.apply_to_widget(self.sequence_editor, "input")

        if hasattr(self, "scan_btn"):
            self.current_theme.apply_to_widget(self.scan_btn, "button_secondary")

        if hasattr(self, "reorder_btn"):
            self.current_theme.apply_to_widget(self.reorder_btn, "button_primary")

        if hasattr(self, "test_mode_checkbox"):
            self.current_theme.apply_to_widget(self.test_mode_checkbox, "checkbox")

        if hasattr(self, "open_output_btn"):
            self.current_theme.apply_to_widget(self.open_output_btn, "button_secondary")

        if hasattr(self, "reset_btn"):
            self.current_theme.apply_to_widget(self.reset_btn, "button_ghost")

        if hasattr(self, "status_label"):
            self.current_theme.apply_to_widget(self.status_label, "label")

        section_frames = [
            getattr(self, "path_section", None),
            getattr(self, "files_section", None),
            getattr(self, "workspace_section", None),
            getattr(self, "action_section", None),
        ]
        for frame in section_frames:
            if isinstance(frame, QFrame):
                self.current_theme.apply_to_widget(frame, "frame")


    def refresh_theme(self):
        super().refresh_theme()
        self._apply_theme_styles()

    def scan_files(self) -> None:
        if self.scan_worker_thread and self.scan_worker_thread.isRunning():
            QMessageBox.information(
                self,
                "Scan In Progress",
                "File scanning is already running.",
            )
            return

        self.csv_files.clear()
        self.files_table.setRowCount(0)
        if hasattr(self, "progress_bar"):
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)

        input_path = Path(self.input_path)
        if not input_path.exists():
            self._toggle_files_empty_state(False, "Input folder not found. Update the path and try again.")
            self._set_status("Input folder not found.")
            QMessageBox.warning(
                self,
                "Input Folder Missing",
                f"Input path does not exist:\n{input_path}",
            )
            self._update_action_state()
            if hasattr(self, "progress_bar"):
                self.progress_bar.setVisible(False)
            return

        files = sorted(input_path.glob("*.csv"))
        if not files:
            self._toggle_files_empty_state(False, "No CSV files found in the selected folder.")
            self._set_status("No CSV files found.")
            if self.execution_log:
                self.log("⚠️ No CSV files detected in the input folder.")
            self._update_action_state()
            if hasattr(self, "progress_bar"):
                self.progress_bar.setVisible(False)
            return

        self._toggle_files_empty_state(True)
        self._set_status(f"Scanning {len(files)} file(s)…")
        self._update_action_state()

        cache_snapshot = dict(self._scan_cache)
        self.scan_worker_thread = QThread()
        self.scan_worker = FileScanWorker(files=files, cache_snapshot=cache_snapshot)
        self.scan_worker.moveToThread(self.scan_worker_thread)

        self.scan_worker_thread.started.connect(self.scan_worker.run)
        self.scan_worker.progress_signal.connect(self._handle_scan_progress)
        self.scan_worker.file_scanned.connect(self._handle_scan_result)
        self.scan_worker.log_signal.connect(self.log_message)
        self.scan_worker.finished_signal.connect(self._handle_scan_finished)
        self.scan_worker.finished_signal.connect(self.scan_worker_thread.quit)
        self.scan_worker.finished_signal.connect(self.scan_worker.deleteLater)
        self.scan_worker_thread.finished.connect(self._cleanup_scan_worker)

        self.scan_worker_thread.start()
        if self.execution_log:
            self.log(f"🔍 Scanning {len(files)} CSV file(s)…")

    def on_preset_changed(self, preset_name: str) -> None:
        if preset_name == "Custom (edit below)":
            self._update_preset_status(preset_name)
            self._log_preset_change(preset_name)
            return
        sequence = self._get_columns_for_preset(preset_name)
        self._load_sequence(sequence)
        self._update_preset_status(preset_name)
        self._log_preset_change(preset_name)

    def reset_sequence_text(self) -> None:
        preset_name = self.preset_combo.currentText()
        sequence = self._get_columns_for_preset(preset_name)
        self._load_sequence(sequence)
        self._update_preset_status(preset_name)
        self._log_preset_change(preset_name)

    def _get_columns_for_preset(self, preset_name: str) -> List[str]:
        if preset_name in self._custom_presets:
            return self._custom_presets[preset_name]
        return _PRESET_DEFINITIONS.get(preset_name, _DEFAULT_SEQUENCE)

    def _load_sequence(self, sequence: List[str]) -> None:
        text = "\n".join(sequence)
        self.sequence_editor.blockSignals(True)
        self.sequence_editor.setPlainText(text)
        self.sequence_editor.blockSignals(False)
        if not getattr(self, "_initializing_ui", False) and self.execution_log:
            self.log(f"📝 Updated active column sequence ({len(sequence)} columns).")

    def _update_preset_status(self, preset_name: str) -> None:
        if not hasattr(self, "preset_status_label"):
            return
        if preset_name == "Custom (edit below)":
            status = "Active preset: Custom (manual order)"
        else:
            status = f"Active preset: {preset_name}"
        self.preset_status_label.setText(status)

    def _log_preset_change(self, preset_name: str) -> None:
        if getattr(self, "_initializing_ui", False):
            return
        if self.execution_log:
            self.log(f"🎯 Preset applied: {preset_name}")

    def save_custom_preset(self) -> None:
        lines = self._collect_sequence_from_editor()
        if not lines:
            QMessageBox.warning(
                self,
                "Invalid Sequence",
                "Please enter at least one column name before saving a preset.",
            )
            return

        name, ok = QInputDialog.getText(
            self,
            "Save Custom Preset",
            "Preset name:",
        )
        if not ok or not name.strip():
            return

        preset_name = name.strip()
        if preset_name in _PRESET_DEFINITIONS:
            QMessageBox.warning(
                self,
                "Preset Exists",
                "A built-in preset already uses that name. Choose another.",
            )
            return

        self._custom_presets[preset_name] = lines
        self.preset_combo.insertItem(self.preset_combo.count() - 1, preset_name)
        self.preset_combo.setCurrentText(preset_name)
        if self.execution_log:
            self.log(f"💾 Saved custom preset: {preset_name}")
        self._update_preset_status(preset_name)

    def _collect_sequence_from_editor(self) -> List[str]:
        lines = [line.strip() for line in self.sequence_editor.toPlainText().splitlines()]
        return [line for line in lines if line]

    def start_reorder(self) -> None:
        if not self.csv_files:
            QMessageBox.information(
                self,
                "No CSV Files",
                "Scan the input folder first—no CSV files found.",
            )
            return

        sequence = self._collect_sequence_from_editor()
        if not sequence:
            QMessageBox.warning(
                self,
                "Invalid Sequence",
                "Please define at least one column in the sequence editor.",
            )
            if self.execution_log:
                self.log("⚠️ Harmonization cancelled: no column sequence defined.")
            return

        if self.worker_thread and self.worker_thread.isRunning():
            QMessageBox.information(
                self,
                "In Progress",
                "Column harmonization is already running.",
            )
            return

        base_output = self._compute_base_output_path(self.output_path)
        if base_output != Path(self.output_path):
            self.path_manager.set_output_path(base_output)
            self.output_path = base_output
            self._sync_path_edits(self.input_path, base_output)
        else:
            self.path_manager.set_output_path(base_output)

        path_info = self.allocate_run_directory(
            "Column Order Harmonizer",
            script_name=Path(__file__).name,
            sync_paths=False,
            announce=False,
        )
        self.output_run_root = path_info.get("root")
        self.output_run_success = path_info.get("success")
        self.output_run_failed = path_info.get("failed")
        if self.execution_log and self.output_run_root:
            self.log(f"📁 Output run directory: {self.output_run_root}")
            if self.output_run_success:
                self.log(f"   ├─ Success: {self.output_run_success}")
            if self.output_run_failed:
                self.log(f"   └─ Failed: {self.output_run_failed}")

        files_to_process = self._select_files_for_batch()
        if not files_to_process:
            QMessageBox.information(
                self,
                "No Files Selected",
                "No files are selected for harmonization.",
            )
            return

        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximum(len(files_to_process))
        self._set_status("Starting column harmonization…")
        self._update_action_state()

        self.worker_thread = QThread()
        self.worker = ColumnOrderWorker(
            files=files_to_process,
            column_sequence=sequence,
            remove_extra_columns=self.remove_extra_columns,
            input_path=Path(self.input_path),
            output_path=Path(self.output_run_root or self.output_path),
            output_success_path=self.output_run_success,
            output_failed_path=self.output_run_failed,
            report_root_path=self.output_run_root,
        )
        self.worker.moveToThread(self.worker_thread)

        self.worker_thread.started.connect(self.worker.run)
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.status_signal.connect(self.update_status)
        self.worker.log_signal.connect(self.log_message)
        self.worker.finished_signal.connect(self.on_worker_finished)
        self.worker.finished_signal.connect(self.worker_thread.quit)
        self.worker.finished_signal.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)

        self.worker_thread.start()

        if self.execution_log:
            self.log("🚀 Harmonization started.")

    def update_progress(self, current: int, total: int) -> None:
        if total <= 0:
            return
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self._set_status(f"Harmonizing ({current}/{total})…")

    def update_status(self, message: str) -> None:
        self._set_status(message)

    def log_message(self, message: str) -> None:
        if self.execution_log:
            self.log(message)

    def on_worker_finished(self, success: int, failed: int) -> None:
        self.progress_bar.setVisible(False)
        summary = f"Completed: {success} success, {failed} failed."
        self._set_status(summary)
        if self.execution_log:
            self.log(f"🏁 {summary}")
            if success:
                self.log("Review log for duplicate or extra column removals per file.")
            if getattr(self, "output_run_root", None):
                self.log(f"🗂 Output root: {self.output_run_root}")
                if getattr(self, "output_run_success", None):
                    self.log(f"   ├─ Success: {self.output_run_success}")
                if getattr(self, "output_run_failed", None):
                    self.log(f"   └─ Failed: {self.output_run_failed}")

        self.worker = None
        self.worker_thread = None
        self.show()
        self.raise_()
        self.activateWindow()
        self._update_action_state()

    def _handle_scan_progress(self, current: int, total: int) -> None:
        if hasattr(self, "progress_bar"):
            self.progress_bar.setMaximum(total)
            self.progress_bar.setValue(current)
        self._set_status(f"Scanning files ({current}/{total})…")

    def _handle_scan_result(self, index: int, file_path: Path, columns: int, rows: int) -> None:
        row_position = self.files_table.rowCount()
        self.files_table.insertRow(row_position)
        self.files_table.setItem(row_position, 0, QTableWidgetItem(file_path.name))
        self.files_table.setItem(row_position, 1, QTableWidgetItem(str(columns)))
        self.files_table.setItem(row_position, 2, QTableWidgetItem(str(rows)))

    def _handle_scan_finished(self, results: List[ScanResult], updated_cache: Dict[str, Tuple[float, int, int]]) -> None:
        self.csv_files = [result.file_path for result in results]
        self._scan_cache.update(updated_cache)
        total_files = len(results)
        self._set_status(f"Found {total_files} CSV file(s).")
        if self.execution_log:
            self.log(f"📂 Scan complete: {total_files} CSV file(s) ready.")
        if hasattr(self, "progress_bar"):
            self.progress_bar.setVisible(False)
            self.progress_bar.setValue(0)
        self._update_action_state()

    def _cleanup_scan_worker(self) -> None:
        if self.scan_worker_thread:
            self.scan_worker_thread.deleteLater()
        self.scan_worker_thread = None
        self.scan_worker = None
        self._update_action_state()

    def _select_files_for_batch(self) -> List[Path]:
        if self.batch_size_limit and self.batch_size_limit > 0:
            selected = list(self.csv_files[: self.batch_size_limit])
            if self.execution_log:
                self.log(
                    f"📦 Processing first {len(selected)} file(s) out of {len(self.csv_files)} "
                    f"(batch size limit: {self.batch_size_limit})."
                )
            return selected
        return list(self.csv_files)

    def open_input_folder(self) -> None:
        try:
            os.startfile(self.input_path)
        except Exception as exc:  # pragma: no cover - OS-specific
            QMessageBox.warning(
                self,
                "Unable to Open",
                f"Could not open input folder:\n{exc}",
            )

    def open_output_folder(self) -> None:
        target = self.output_run_root or self.output_path
        try:
            os.startfile(target)
        except Exception as exc:  # pragma: no cover - OS-specific
            QMessageBox.warning(
                self,
                "Unable to Open",
                f"Could not open output folder:\n{exc}",
            )

    def _handle_paths_changed(self, input_path: Path, output_path: Path) -> None:
        super()._handle_paths_changed(input_path, output_path)
        self._sync_path_edits(input_path, output_path)
        if self.execution_log and hasattr(self.execution_log, "set_output_path"):
            self.execution_log.set_output_path(str(output_path))

    def _handle_remove_extras_toggle(self, state: int) -> None:
        self.remove_extra_columns = state == Qt.Checked
        if self.execution_log:
            if self.remove_extra_columns:
                self.log("✂️ Columns not present in the preset will be removed from output files.")
            else:
                self.log("🔄 Columns not present in the preset will be appended after ordered columns.")

    def _toggle_test_mode(self, state: int) -> None:
        self.test_mode = state == Qt.Checked
        if self.test_mode:
            self._user_input_path = Path(self.input_path)
            self._user_output_path = Path(self.output_path)
            test_input = self._get_test_data_path()
            test_output = self._get_test_output_path()
            test_output.mkdir(parents=True, exist_ok=True)
            self._sync_path_edits(test_input, test_output)
            if self.execution_log:
                self.log("🧪 Test Mode enabled: using golden dataset.")
        else:
            restored_input = self._user_input_path or Path(self.input_path)
            restored_output = self._user_output_path or Path(self.output_path)
            self._sync_path_edits(restored_input, restored_output)
            if self.execution_log:
                self.log("🧪 Test Mode disabled: using configured paths.")
        self.scan_files()

    def _get_test_data_path(self) -> Path:
        return Path(__file__).resolve().parent.parent.parent / "test_data"

    def _get_test_output_path(self) -> Path:
        return Path(__file__).resolve().parent.parent.parent / "test_output"

    def _compute_base_output_path(self, path: Path) -> Path:
        """
        Derive the user-selected base output directory by stripping tool/script/timestamp folders.
        """
        try:
            parts = list(Path(path).resolve().parts)
        except FileNotFoundError:
            parts = list(Path(path).absolute().parts)

        lowered = [part.lower() for part in parts]
        strip_index = None
        for idx, part in enumerate(parts):
            part_lower = lowered[idx]
            if part_lower == _SANITIZED_TOOL_NAME.lower():
                strip_index = idx
                break
            if part_lower == _SANITIZED_SCRIPT_NAME.lower():
                strip_index = idx
                break
            if _TIMESTAMP_PATTERN.fullmatch(part):
                strip_index = idx
                break
            if part_lower in {"success", "failed"}:
                strip_index = idx
                break

        if strip_index is not None and strip_index > 0:
            base = Path(parts[0])
            for segment in parts[1:strip_index]:
                base /= segment
            return base

        return Path(path)

    def closeEvent(self, event):  # noqa: N802
        if self.worker_thread and self.worker_thread.isRunning():
            reply = QMessageBox.question(
                self,
                "Harmonization Running",
                "Column harmonization is in progress. Stop it and close?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply == QMessageBox.No:
                event.ignore()
                return
            if self.worker_thread.isRunning():
                self.worker_thread.quit()
                self.worker_thread.wait(2000)
        super().closeEvent(event)


def main():
    from PySide6.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)

    class DummyParent:
        def __init__(self):
            try:
                from styles import get_theme_manager

                theme_manager = get_theme_manager()
                themes = theme_manager.get_available_themes()
                self.current_theme = (
                    theme_manager.load_theme(themes[0]) if themes else None
                )
            except Exception:
                self.current_theme = None

    from styles import get_path_manager

    parent = DummyParent()
    path_manager = get_path_manager()
    tool = ColumnOrderHarmonizer(
        parent,
        str(path_manager.get_input_path()),
        str(path_manager.get_output_path()),
    )
    tool.show()
    tool.raise_()
    tool.activateWindow()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
