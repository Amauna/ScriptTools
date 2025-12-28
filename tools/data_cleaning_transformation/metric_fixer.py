"""
🌊 Metric Field Fixer Tool
Fix blank/empty/null values in numeric/metric columns by replacing them with 0
Clean your CSV files with beautiful preview and safe application
"""

import sys
import os
import csv
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Set
import json
import hashlib

from PySide6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QCheckBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QScrollArea, QWidget, QFrame,
    QMessageBox, QProgressBar, QGroupBox, QSplitter, QTreeWidget, QTreeWidgetItem
)
from PySide6.QtCore import Qt, Signal, QObject, QThread
from PySide6.QtGui import QFont, QColor

# Import base template for automatic theme support
from tools.templates import BaseToolDialog, PathConfigMixin
from styles import get_path_manager


@dataclass
class ColumnIssueSummary:
    column_name: str
    total_values: int = 0
    numeric_values: int = 0
    blank_count: int = 0
    invalid_numeric_count: int = 0
    low_range_numeric_count: int = 0
    revenue_format_count: int = 0
    percentage_format_count: int = 0


@dataclass
class FileScanSummary:
    """Lightweight summary persisted for each scanned CSV file."""
    file_path: Path
    total_rows: int
    issue_count: int
    cache_path: Path
    error_message: Optional[str] = None


class MetricFixerWorker(QObject):
    """Worker that scans and fixes CSV files in a background thread"""
    log_signal = Signal(str)
    progress_signal = Signal(int, int)  # current, total
    scan_complete_signal = Signal(list)  # List[FileScanSummary]
    fix_complete_signal = Signal(int, int)  # success, failed

    CONTRACT_NUMERIC_COLUMNS = {
        "sessions",
        "event count",
        "engaged sessions",
        "views",
        "active users",
        "new users",
        "total users",
        "total revenue",
        "total users",
        "total_users",
    }
    REVENUE_COLUMNS = {"total revenue"}
    
    def __init__(
        self,
        files: List[Path],
        output_dir: Path,
        selected_columns: Dict[Path, Set[int]],
        *,
        scan_cache_dir: Optional[Path] = None,
        max_workers: int = 4,
        column_metadata: Optional[Dict[Path, Dict[str, Set[int]]]] = None,
        fast_mode: bool = False,
    ):
        super().__init__()
        self.files = files
        self.output_dir = output_dir
        self.selected_columns = selected_columns  # file -> set of column indices to fix
        self.should_stop = False
        self.execution_log: List[str] = []
        self.max_workers = max(1, max_workers)
        self.scan_cache_dir = scan_cache_dir
        self.cached_column_metadata: Dict[Path, Dict[str, Set[int]]] = column_metadata or {}
        self.fast_mode = fast_mode
    
    def _log(self, message: str):
        """Log message with timestamp"""
        ts = datetime.now().strftime("%H:%M:%S")
        formatted = f"[{ts}] {message}"
        self.execution_log.append(formatted)
        self.log_signal.emit(message)

    def _ensure_cache_dir(self) -> Path:
        """Ensure a dedicated cache directory exists for the current scan run."""
        if self.scan_cache_dir is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_root = self.output_dir if self.output_dir else Path.cwd()
            cache_root = base_root / "_metric_scan_cache"
            self.scan_cache_dir = cache_root / timestamp
        self.scan_cache_dir.mkdir(parents=True, exist_ok=True)
        return self.scan_cache_dir
    
    def _is_numeric_value(self, value: str) -> bool:
        """Check if value is numeric (int or float)"""
        if not value or not value.strip():
            return False
        value = value.strip()
        try:
            float(value)
            return True
        except ValueError:
            return False
    
    INVALID_VALUE_TOKENS = {"", "null", "none", "n/a", "na", "nil", "-", "—", "nan"}

    @classmethod
    def _is_invalid_value(cls, value: str) -> bool:
        """Check if value is invalid (blank, empty, null, etc.)"""
        if value is None:
            return True
        value_lower = value.strip().lower()
        return value_lower in cls.INVALID_VALUE_TOKENS
    
    def _detect_numeric_column(self, column_values: List[str]) -> bool:
        """Detect if column is numeric (at least 70% numeric values)"""
        if not column_values:
            return False
        
        total = len(column_values)
        numeric_count = 0
        
        for val in column_values:
            if self._is_numeric_value(val):
                numeric_count += 1
        
        # Column is numeric if at least 70% of values are numeric
        return (numeric_count / total) >= 0.7 if total > 0 else False
    
    def _looks_like_percentage_name(self, column_name: str) -> bool:
        column_lower = column_name.strip().lower()
        indicators = ["rate", "percentage", "percent", "engagement", "%", "ratio", "pct"]
        return any(indicator in column_lower for indicator in indicators)
    
    def _detect_percentage_column(self, column_name: str, column_values: List[str]) -> bool:
        """Detect if column is a percentage column (0-1 range or name suggests percentage)"""
        if not column_values:
            return False
        
        # Check column name for percentage indicators
        if self._looks_like_percentage_name(column_name):
            return True
        
        # Check value range: if most values are between 0-1 (inclusive), it's likely a percentage
        numeric_values = []
        for val in column_values:
            if self._is_numeric_value(val):
                try:
                    num_val = float(val.strip())
                    numeric_values.append(num_val)
                except (ValueError, AttributeError):
                    continue
        
        if not numeric_values:
            return False
        
        # Check if most values are in 0-1 range (with some tolerance for values slightly above 1 like 1.00)
        in_range_count = 0
        for num_val in numeric_values:
            # Allow 0-1.1 range to account for 1.00, 1.0, etc.
            if 0 <= num_val <= 1.1:
                in_range_count += 1
        
        # If at least 80% of numeric values are in 0-1.1 range, it's likely a percentage
        return (in_range_count / len(numeric_values)) >= 0.8 if numeric_values else False
    
    def scan_files(self):
        """Scan CSV files for metric field issues in parallel and persist summaries to cache."""
        self._log("DEBUG: MetricFixerWorker.scan_files method entered on worker thread.") # Confirm worker method entry
        import time

        start = time.time()
        total = len(self.files)

        self._log("=" * 60)
        self._log("🔍 SCANNING CSV FILES FOR METRIC FIELD ISSUES...")
        self._log("=" * 60)
        self._log(f"Files to scan: {total}")
        self._log("")

        if total == 0:
            self.scan_complete_signal.emit([])
            return

        cache_dir = self._ensure_cache_dir()
        summaries: List[Optional[FileScanSummary]] = [None] * total

        with ThreadPoolExecutor(max_workers=min(self.max_workers, total)) as executor:
            target_func = self._analyze_csv_fast if self.fast_mode else self._analyze_csv
            futures = {
                executor.submit(target_func, file_path, cache_dir): (index, file_path)
                for index, file_path in enumerate(self.files)
            }

            completed = 0
            for future in as_completed(futures):
                index, file_path = futures[future]

                if self.should_stop:
                    break

                try:
                    summary = future.result()
                except Exception as exc:  # pragma: no cover - defensive
                    summary = FileScanSummary(
                        file_path=file_path,
                        total_rows=0,
                        issue_count=0,
                        cache_path=cache_dir / f"error_{index}.json",
                        error_message=str(exc),
                    )

                summaries[index] = summary

                if summary.error_message:
                    self._log(
                        f"   ❌ Error scanning {file_path.name}: {summary.error_message}"
                    )
                else:
                    self._log(
                        f"   ✅ {file_path.name} — rows: {summary.total_rows}, issues: {summary.issue_count}"
                    )

                completed += 1
                self.progress_signal.emit(completed, total)

        if self.should_stop:
            self._log("⚠️ Scan cancelled by user.")
            self.scan_complete_signal.emit([])
            return

        duration = time.time() - start
        total_issues = sum(
            summary.issue_count
            for summary in summaries
            if summary and not summary.error_message
        )

        self._log("")
        self._log(f"✅ Scan complete! ({duration:.2f}s)")
        self._log(
            f"📊 Files scanned: {len([s for s in summaries if s])} | Total issues: {total_issues}"
        )
        self._log(f"📁 Scan cache directory: {cache_dir}")

        self.scan_complete_signal.emit([s for s in summaries if s is not None])
    
    def _analyze_csv(self, file_path: Path, cache_dir: Path) -> FileScanSummary:
        """Analyze a CSV file for metric field issues and persist a cached summary."""

        try:
            with file_path.open("r", newline="", encoding="utf-8") as handle:
                sample = handle.read(2048)
                handle.seek(0)

                try:
                    sniffer = csv.Sniffer()
                    dialect = sniffer.sniff(sample)
                except csv.Error:
                    dialect = csv.excel

                reader = csv.reader(handle, dialect)
                header = next(reader, None)

                if not header:
                    return FileScanSummary(
                        file_path=file_path,
                        total_rows=0,
                        issue_count=0,
                        cache_path=cache_dir / f"{file_path.stem}_empty.json",
                        error_message="Empty file",
                    )

                num_cols = len(header)
                column_stats: List[ColumnIssueSummary] = [
                    ColumnIssueSummary(column_name=name) for name in header
                ]

                total_rows = 0
                for row in reader:
                    total_rows += 1

                    if len(row) < num_cols:
                        row = list(row) + [""] * (num_cols - len(row))
                    elif len(row) > num_cols:
                        row = row[:num_cols]

                    for col_idx, raw_value in enumerate(row):
                        summary = column_stats[col_idx]
                        summary.total_values += 1

                        value = raw_value.strip() if raw_value is not None else ""

                        if self._is_invalid_value(value):
                            summary.blank_count += 1
                            continue

                        normalized = value.replace(",", "")
                        if not self._is_numeric_value(normalized):
                            summary.invalid_numeric_count += 1
                            continue

                        summary.numeric_values += 1

                        try:
                            num_value = float(normalized)
                        except ValueError:
                            summary.invalid_numeric_count += 1
                            continue

                        if 0 <= num_value <= 1.1:
                            summary.low_range_numeric_count += 1

                        decimals = 0
                        if "." in normalized:
                            decimals = len(normalized.split(".")[-1])
                        if decimals != 2:
                            if header[col_idx].strip().lower() in self.REVENUE_COLUMNS:
                                summary.revenue_format_count += 1
                            summary.percentage_format_count += 1

                numeric_columns: Set[int] = set()
                percentage_columns: Set[int] = set()
                revenue_columns: Set[int] = set()
                column_issue_details: List[Dict[str, int]] = []
                total_issue_count = 0

                for idx, summary in enumerate(column_stats):
                    column_name = header[idx]
                    total = summary.total_values

                    if total == 0:
                        continue

                    forced_numeric = column_name.strip().lower() in self.CONTRACT_NUMERIC_COLUMNS
                    numeric_ratio = summary.numeric_values / total if total else 0
                    is_numeric = numeric_ratio >= 0.7 or forced_numeric
                    if is_numeric:
                        numeric_columns.add(idx)

                    is_percentage = False
                    if self._looks_like_percentage_name(column_name):
                        is_percentage = True
                    elif summary.numeric_values > 0:
                        in_range_ratio = summary.low_range_numeric_count / summary.numeric_values
                        if in_range_ratio >= 0.8:
                            is_percentage = True
                    if is_percentage:
                        percentage_columns.add(idx)

                    is_revenue = column_name.strip().lower() in self.REVENUE_COLUMNS
                    if is_revenue:
                        revenue_columns.add(idx)

                    percentage_format_count = summary.percentage_format_count if is_percentage else 0
                    revenue_format_count = summary.revenue_format_count if is_revenue else 0

                    total_issues = (
                        summary.blank_count
                        + summary.invalid_numeric_count
                        + (summary.low_range_numeric_count if is_percentage else 0)
                        + percentage_format_count
                        + revenue_format_count
                    )

                    if total_issues > 0:
                        column_issue_details.append(
                            {
                                "index": idx,
                                "name": column_name,
                                "blank_count": summary.blank_count,
                                "invalid_numeric_count": summary.invalid_numeric_count,
                                "low_range_numeric_count": summary.low_range_numeric_count,
                                "percentage_format_count": percentage_format_count,
                                "revenue_format_count": revenue_format_count,
                            }
                        )
                        total_issue_count += total_issues

                cache_filename = hashlib.sha1(str(file_path).encode("utf-8")).hexdigest() + ".json"
                cache_path = cache_dir / cache_filename
                cache_payload = {
                    "file_path": str(file_path),
                    "headers": header,
                    "total_rows": total_rows,
                    "issue_count": total_issue_count,
                    "numeric_columns": sorted(numeric_columns),
                    "percentage_columns": sorted(percentage_columns),
                    "revenue_columns": sorted(revenue_columns),
                    "columns": column_issue_details,
                }

                with cache_path.open("w", encoding="utf-8") as cache_handle:
                    json.dump(cache_payload, cache_handle, ensure_ascii=False, indent=2)

                return FileScanSummary(
                    file_path=file_path,
                    total_rows=total_rows,
                    issue_count=total_issue_count,
                    cache_path=cache_path,
                )

        except Exception as exc:  # pragma: no cover - defensive
            error_filename = hashlib.sha1(f"error-{file_path}".encode("utf-8")).hexdigest() + ".json"
            error_path = cache_dir / error_filename
            with error_path.open("w", encoding="utf-8") as handle:
                json.dump({"file_path": str(file_path), "error": str(exc)}, handle)

            return FileScanSummary(
                file_path=file_path,
                total_rows=0,
                issue_count=0,
                cache_path=error_path,
                error_message=str(exc),
            )
    
    def _analyze_csv_fast(self, file_path: Path, cache_dir: Path) -> FileScanSummary:
        """
        Quickly analyze a CSV by only reading its header to find target metric columns.
        This is a lightweight alternative to the full _analyze_csv scan.
        """
        try:
            with file_path.open("r", newline="", encoding="utf-8") as handle:
                # Sniff dialect from a sample
                sample = handle.read(2048)
                handle.seek(0)
                try:
                    dialect = csv.Sniffer().sniff(sample)
                except csv.Error:
                    dialect = csv.excel

                reader = csv.reader(handle, dialect)
                header = next(reader, None)

                if not header:
                    return FileScanSummary(
                        file_path=file_path, total_rows=0, issue_count=0,
                        cache_path=cache_dir / f"{file_path.stem}_empty.json",
                        error_message="Empty file",
                    )

                # Identify target columns from header
                numeric_columns: Set[int] = set()
                percentage_columns: Set[int] = set()
                revenue_columns: Set[int] = set()
                column_issue_details: List[Dict[str, int]] = []

                # Combine all known metric/revenue/percentage column names for checking
                all_target_cols = self.CONTRACT_NUMERIC_COLUMNS | self.REVENUE_COLUMNS
                
                for idx, col_name in enumerate(header):
                    col_lower = col_name.strip().lower()
                    
                    is_revenue = col_lower in self.REVENUE_COLUMNS
                    is_percentage = self._looks_like_percentage_name(col_name)
                    # A column is numeric if it's explicitly in our contract or if it looks like revenue/percentage
                    is_numeric = col_lower in all_target_cols or is_revenue or is_percentage

                    if is_numeric:
                        numeric_columns.add(idx)
                        if is_revenue:
                            revenue_columns.add(idx)
                        if is_percentage:
                            percentage_columns.add(idx)

                        # We don't have real counts, so we just add the column to the list
                        # The UI will show it as having "issues" to allow selection
                        column_issue_details.append({
                            "index": idx,
                            "name": col_name,
                            "blank_count": 1, # Dummy value to indicate it's a target
                            "invalid_numeric_count": 0,
                            "low_range_numeric_count": 0,
                            "percentage_format_count": 0,
                            "revenue_format_count": 0,
                        })

                total_issue_count = len(column_issue_details)

                # Persist lightweight cache summary
                cache_filename = hashlib.sha1(f"{file_path}-fast".encode("utf-8")).hexdigest() + ".json"
                cache_path = cache_dir / cache_filename
                cache_payload = {
                    "file_path": str(file_path),
                    "headers": header,
                    "total_rows": -1,  # Indicate that rows were not counted
                    "issue_count": total_issue_count,
                    "numeric_columns": sorted(numeric_columns),
                    "percentage_columns": sorted(percentage_columns),
                    "revenue_columns": sorted(revenue_columns),
                    "columns": column_issue_details,
                }

                with cache_path.open("w", encoding="utf-8") as cache_handle:
                    json.dump(cache_payload, cache_handle, ensure_ascii=False, indent=2)

                return FileScanSummary(
                    file_path=file_path, total_rows=-1,
                    issue_count=total_issue_count, cache_path=cache_path,
                )

        except Exception as exc: # pragma: no cover
            error_filename = hashlib.sha1(f"error-fast-{file_path}".encode("utf-8")).hexdigest() + ".json"
            error_path = cache_dir / error_filename
            with error_path.open("w", encoding="utf-8") as handle:
                json.dump({"file_path": str(file_path), "error": str(exc)}, handle)
            return FileScanSummary(
                file_path=file_path, total_rows=0, issue_count=0,
                cache_path=error_path, error_message=str(exc),
            )

    def _fix_single_file(self, file_path: Path) -> (bool, int, Optional[str]):
        """
        Fixes a single CSV file.

        Returns:
            Tuple[bool, int, Optional[str]]: (success, changes_made, error_message)
        """
        selected_cols = self.selected_columns.get(file_path, set())
        if not selected_cols:
            return True, 0, "No columns selected for fixing."

        metadata = self.cached_column_metadata.get(file_path)
        if metadata is None:
            metadata = {
                "numeric_columns": set(),
                "percentage_columns": set(),
                "revenue_columns": set(),
            }

        output_file = self.output_dir / file_path.name
        tmp_file = output_file.with_suffix(output_file.suffix + ".tmp")

        try:
            with file_path.open("r", newline="", encoding="utf-8") as read_handle:
                sample = read_handle.read(2048)
                read_handle.seek(0)

                try:
                    sniffer = csv.Sniffer()
                    dialect = sniffer.sniff(sample)
                except csv.Error:
                    dialect = csv.excel

                reader = csv.reader(read_handle, dialect)
                header = next(reader, None)

                if header is None:
                    with tmp_file.open("w", newline="", encoding="utf-8") as write_handle:
                        csv.writer(write_handle, dialect=dialect).writerow([])
                    tmp_file.replace(output_file)
                    return True, 0, None

                with tmp_file.open("w", newline="", encoding="utf-8") as write_handle:
                    writer = csv.writer(write_handle, dialect=dialect)
                    writer.writerow(header)

                    changes_made = 0

                    for row in reader:
                        if len(row) < len(header):
                            row = list(row) + [""] * (len(header) - len(row))
                        elif len(row) > len(header):
                            row = row[: len(header)]

                        for col_idx in selected_cols:
                            current_value = row[col_idx] if col_idx < len(row) else ""
                            new_value = self._apply_fixes_to_value(
                                current_value,
                                metadata,
                                col_idx,
                            )
                            if new_value != current_value:
                                changes_made += 1
                                row[col_idx] = new_value

                        writer.writerow(row)

            tmp_file.replace(output_file)
            return True, changes_made, None

        except Exception as e:
            try:
                if tmp_file.exists():
                    tmp_file.unlink()
            except Exception:
                pass
            return False, 0, str(e)

    def fix_files(self):
        """Fix selected metric fields in CSV files in parallel."""
        import time
        start = time.time()

        self._log("=" * 60)
        self._log("🔧 FIXING METRIC FIELDS (PARALLEL)...")
        self._log("=" * 60)

        success = 0
        failed = 0

        self.output_dir.mkdir(parents=True, exist_ok=True)

        files_to_fix = [
            file_path
            for file_path, columns in self.selected_columns.items()
            if columns
        ]

        total_files = len(files_to_fix)
        if total_files == 0:
            self._log("No files require fixing.")
            self.fix_complete_signal.emit(0, 0)
            return

        with ThreadPoolExecutor(max_workers=min(self.max_workers, total_files)) as executor:
            futures = {
                executor.submit(self._fix_single_file, file_path): file_path
                for file_path in files_to_fix
            }

            completed = 0
            for future in as_completed(futures):
                file_path = futures[future]

                if self.should_stop:
                    break

                try:
                    is_success, changes_made, error_message = future.result()
                    if is_success:
                        if changes_made > 0:
                            self._log(f"   ✅ Applied {changes_made} change(s) in {file_path.name}")
                        else:
                            self._log(f"   ✅ No changes required for {file_path.name}")
                        success += 1
                    else:
                        self._log(f"   ❌ Error fixing {file_path.name}: {error_message}")
                        failed += 1

                except Exception as e:
                    self._log(f"   ❌ Critical error fixing {file_path.name}: {e}")
                    failed += 1

                completed += 1
                self.progress_signal.emit(completed, total_files)

        if self.should_stop:
            self._log("⚠️ Fix process cancelled by user.")

        duration = time.time() - start
        self._log("")
        self._log(f"✅ Fix complete! ({duration:.2f}s)")
        self._log(f"📊 Success: {success}, Failed: {failed}")

        self.fix_complete_signal.emit(success, failed)
    
    def _apply_fixes_to_value(
        self,
        raw_value: str,
        metadata: Dict[str, Set[int]],
        col_idx: int,
    ) -> str:
        value = raw_value.strip() if raw_value is not None else ""
        percentage_columns = metadata.get("percentage_columns", set())
        revenue_columns = metadata.get("revenue_columns", set())
        numeric_columns = metadata.get("numeric_columns", set())

        is_percentage = col_idx in percentage_columns
        is_revenue = col_idx in revenue_columns
        is_numeric = col_idx in numeric_columns

        if is_percentage:
            return self._format_percentage_value(value)

        if is_revenue:
            return self._format_revenue_value(value)

        if is_numeric:
            return self._format_numeric_value(value)

        return value

    def _format_percentage_value(self, value: str) -> str:
        if self._is_invalid_value(value):
            return "0.00"
        try:
            num_value = float(value.replace(",", ""))
        except ValueError:
            return "0.00"

        if 0 <= num_value <= 1.1:
            num_value *= 100

        return f"{num_value:.2f}"

    def _format_revenue_value(self, value: str) -> str:
        if self._is_invalid_value(value):
            return "0.00"
        try:
            num_value = float(value.replace(",", ""))
        except ValueError:
            return "0.00"

        return f"{num_value:.2f}"

    def _format_numeric_value(self, value: str) -> str:
        if self._is_invalid_value(value):
            return "0"
        try:
            num_value = float(value.replace(",", ""))
        except ValueError:
            return "0"

        if num_value.is_integer():
            return str(int(num_value))
        return str(num_value)


class MetricFixerTool(PathConfigMixin, BaseToolDialog):
    """Tool for fixing metric naming inconsistencies."""

    PATH_CONFIG = {
        "show_input": True,
        "show_output": True,
        "include_open_buttons": True,
        "input_label": "📥 Input Folder:",
        "output_label": "📤 Output Folder:",
    }
    
    def __init__(self, parent, input_path: str, output_path: str):
        """Initialize the metric fixer tool"""
        super().__init__(parent, input_path, output_path)
        
        # Setup window
        self.setup_window_properties(
            title="🌊 Metric Field Fixer",
            width=1200,
            height=800
        )
        
        # State
        self.scan_summaries: List[FileScanSummary] = []
        self.summary_cache_paths: Dict[Path, Path] = {}
        self.column_metadata: Dict[Path, Dict[str, Set[int]]] = {}
        self.selected_columns: Dict[Path, Set[int]] = {}  # file -> set of column indices
        self.worker = None
        self.worker_thread = None
        self.is_scanning = False
        self.is_fixing = False
        
        # Setup UI
        self.setup_ui()
        
        # Initial log
        if self.execution_log: # Ensure log is initialized before use
            self.log("🌊 Metric Field Fixer initialized!")
            self.log("Ready to scan and fix metric fields!")
    
    def setup_ui(self):
        """Create the tool's user interface"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # ===== HEADER =====
        header_label = QLabel("🌊 Metric Field Fixer")
        header_label.setFont(QFont("Arial", 20, QFont.Bold))
        header_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(header_label)
        
        self.build_path_controls(
            main_layout,
            show_input=True,
            show_output=True,
            include_open_buttons=True,
        )
        
        # ===== ACTION BUTTONS =====
        action_frame = QFrame()
        action_layout = QHBoxLayout(action_frame)
        action_layout.setContentsMargins(10, 10, 10, 10)
        action_layout.setSpacing(10)
        
        self.scan_btn = QPushButton("🔍 Scan Files")
        self.scan_btn.setFont(QFont("Arial", 12, QFont.Bold))
        self.scan_btn.setMinimumHeight(40)
        self.scan_btn.clicked.connect(self.start_scan)
        action_layout.addWidget(self.scan_btn)
        
        self.apply_btn = QPushButton("✅ Apply Fixes")
        self.apply_btn.setFont(QFont("Arial", 12, QFont.Bold))
        self.apply_btn.setMinimumHeight(40)
        self.apply_btn.setEnabled(False)
        self.apply_btn.clicked.connect(self.start_fix)
        action_layout.addWidget(self.apply_btn)
        
        action_layout.addStretch(1)

        self.fast_mode_checkbox = QCheckBox("⚡️ Fast Mode (Headers Only)")
        self.fast_mode_checkbox.setFont(QFont("Arial", 10))
        self.fast_mode_checkbox.setToolTip(
            "Scans only the header of each file to find target columns.\n"
            "Much faster for large numbers of files, but less detailed."
        )
        self.fast_mode_checkbox.setChecked(True)
        action_layout.addWidget(self.fast_mode_checkbox)
        
        main_layout.addWidget(action_frame)
        
        # ===== PROGRESS BAR =====
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setTextVisible(True)
        main_layout.addWidget(self.progress)
        
        # ===== MAIN CONTENT (Splitter) =====
        splitter = QSplitter(Qt.Horizontal)
        
        # Left: Column Selection
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(10, 10, 10, 10)
        
        left_title = QLabel("📋 Select Columns to Fix")
        left_title.setFont(QFont("Arial", 14, QFont.Bold))
        left_layout.addWidget(left_title)
        
        # Selection buttons
        select_buttons = QHBoxLayout()
        self.select_all_btn = QPushButton("✅ Select All")
        self.select_all_btn.setEnabled(False)
        self.select_all_btn.clicked.connect(self.select_all_columns)
        select_buttons.addWidget(self.select_all_btn)
        
        self.select_none_btn = QPushButton("⬜ Select None")
        self.select_none_btn.setEnabled(False)
        self.select_none_btn.clicked.connect(self.select_none_columns)
        select_buttons.addWidget(self.select_none_btn)
        
        select_buttons.addStretch()
        left_layout.addLayout(select_buttons)
        
        # Scrollable column list
        self.column_tree = QTreeWidget()
        self.column_tree.setHeaderLabels(["File / Column", "Issues"])
        self.column_tree.setColumnCount(2)
        self.column_tree.setSortingEnabled(False)
        self.column_tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.column_tree.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        left_layout.addWidget(self.column_tree)
        
        splitter.addWidget(left_widget)
        
        # Right: Preview Table
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(10, 10, 10, 10)
        
        right_title = QLabel("👁️ Preview (Sample 100 Rows)") # Updated label
        right_title.setFont(QFont("Arial", 14, QFont.Bold))
        right_layout.addWidget(right_title)
        
        self.preview_table = QTableWidget()
        self.preview_table.setAlternatingRowColors(True)
        self.preview_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.preview_table.horizontalHeader().setStretchLastSection(True)
        right_layout.addWidget(self.preview_table)
        
        splitter.addWidget(right_widget)
        
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        
        main_layout.addWidget(splitter, 1)
        
        # ===== EXECUTION LOG =====
        self.execution_log = self.create_execution_log(main_layout)
    
    def start_scan(self):
        """Start scanning CSV files"""
        # Remove the QMessageBox debug. It served its purpose.
        # QMessageBox.information(self, "Debug", "start_scan method invoked!")

        self.log("DEBUG: start_scan method entered.") # Replaced print with log

        if self.is_scanning or self.is_fixing:
            self.log("DEBUG: Scan/Fix already in progress, returning.") # Replaced print with log
            return
        
        self.log(f"🔍 Attempting to scan files from input path: {self.input_path}") # Added explicit log
        
        # Find CSV files
        csv_files = list(self.input_path.glob("*.csv"))
        
        self.log(f"DEBUG: Found {len(csv_files)} CSV file(s) in {self.input_path}.") # Added explicit log

        if not csv_files:
            QMessageBox.warning(
                self,
                "No Files",
                f"No CSV files found in:\n{self.input_path}"
            )
            return

        # Clear previous results
        self.scan_summaries = []
        self.summary_cache_paths.clear()
        self.column_metadata.clear()
        self.selected_columns = {}
        self.column_tree.clear() # Ensure the tree is cleared before a new scan
        self._clear_preview()
        
        # Start worker
        self.is_scanning = True
        self.scan_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setMaximum(len(csv_files))
        self.progress.setValue(0)

        max_workers = min(8, (os.cpu_count() or 4))
        scan_cache_dir = self._prepare_scan_cache_directory()
        fast_mode = self.fast_mode_checkbox.isChecked()
        self.worker = MetricFixerWorker(
            files=csv_files,
            output_dir=self.output_path,
            selected_columns={},
            scan_cache_dir=scan_cache_dir,
            max_workers=max_workers,
            fast_mode=fast_mode,
        )
        
        self.worker_thread = QThread()
        self.worker.moveToThread(self.worker_thread)
        
        self.worker_thread.started.connect(self.worker.scan_files)
        self.worker.log_signal.connect(self._log)
        self.worker.progress_signal.connect(self._on_scan_progress)
        self.worker.scan_complete_signal.connect(self._on_scan_complete)
        
        self.worker_thread.start()
        self.log("DEBUG: Worker thread officially started by GUI.") # Confirm thread start from GUI side

        self.log(f"🔍 Scanning {len(csv_files)} CSV file(s). Please wait...")
    
    def _on_scan_progress(self, current: int, total: int):
        """Update scan progress"""
        self.progress.setValue(current)

    def _prepare_scan_cache_directory(self) -> Path:
        """Allocate a timestamped cache directory for scan summaries."""
        base_output = self.path_manager.get_output_path()
        tool_root = base_output / "Metric_Fixer"
        cache_root = tool_root / "ScanCache"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        cache_dir = cache_root / timestamp
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir

    def _load_summary_payload(self, summary: FileScanSummary) -> Optional[Dict[str, object]]:
        """Load the cached JSON summary for a scanned file."""
        cache_path = summary.cache_path
        try:
            with cache_path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except Exception as exc:
            if self.execution_log:
                self.log(f"⚠️ Unable to read summary for {summary.file_path.name}: {exc}")
            return None

        self.column_metadata[summary.file_path] = {
            "numeric_columns": set(payload.get("numeric_columns", [])),
            "percentage_columns": set(payload.get("percentage_columns", [])),
            "revenue_columns": set(payload.get("revenue_columns", [])),
            "headers": payload.get("headers", []),
        }

        return payload
    
    def _on_scan_complete(self, results: List[FileScanSummary]):
        """Handle scan completion"""
        self.scan_summaries = results
        self.is_scanning = False
        self.scan_btn.setEnabled(True)
        self.progress.setVisible(False)

        for summary in results:
            self.summary_cache_paths[summary.file_path] = summary.cache_path

        # Update UI
        self._update_column_list()
        self._clear_preview()
        self._update_preview()

        if self.execution_log:
            total_issues = sum(s.issue_count for s in results if not s.error_message)
            self.log(f"✅ Scan complete! Found {total_issues} issue(s) to fix")
            QMessageBox.information(
                self,
                "Scan Complete",
                f"Scan finished successfully!\nFound {len(results)} file(s) with {total_issues} issue(s).",
            )
            self.apply_btn.setEnabled(total_issues > 0)
            self.select_all_btn.setEnabled(total_issues > 0)
            self.select_none_btn.setEnabled(total_issues > 0)

            self.log("DEBUG: _on_scan_complete finished. Attempting to update column list.")

    def _update_column_list(self):
        """Update the column selection list based on cached summaries."""
        try: # Start of try block
            self.log(f"DEBUG: _update_column_list entered. Scan summaries count: {len(self.scan_summaries)}")
            self.column_tree.clear()

            if not self.scan_summaries: # Use the passed scan_summaries here
                self.log("DEBUG: No scan summaries found to display.")
                return

            has_any_columns = False
            files_added_count = 0
            columns_added_count = 0

            for summary in self.scan_summaries: # Iterate over the passed scan_summaries
                if summary.error_message:
                    file_item = QTreeWidgetItem([f"❌ {summary.file_path.name}", "Error"])
                    file_item.setForeground(0, QColor("#f87171"))
                    file_item.setFont(0, QFont("Arial", 11, QFont.Bold))
                    self.column_tree.addTopLevelItem(file_item)
                    files_added_count += 1
                    self.log(f"DEBUG: Added error file item: {summary.file_path.name}")
                    continue

                payload = self._load_summary_payload(summary)
                if not payload:
                    self.log(f"DEBUG: No payload for {summary.file_path.name}, skipping.")
                    continue

                columns = payload.get("columns", [])
                if not columns:
                    self.log(f"DEBUG: No columns with issues for {summary.file_path.name}, skipping.")
                    continue

                has_any_columns = True

                file_item = QTreeWidgetItem([f"📄 {summary.file_path.name}", ""])
                file_item.setFont(0, QFont("Arial", 11, QFont.Bold))
                file_item.setFlags(file_item.flags() | Qt.ItemIsUserCheckable)
                file_item.setCheckState(0, Qt.Checked) # Initially check the file itself
                self.column_tree.addTopLevelItem(file_item)
                files_added_count += 1
                self.log(f"DEBUG: Added file item: {summary.file_path.name}")

                selected_set = self.selected_columns.setdefault(summary.file_path, set())
                selected_set.clear() # Clear existing selections for this file

                for column_info in columns:
                    col_idx = column_info.get("index")
                    col_name = column_info.get("name", f"Column {col_idx}")
                    blank_count = column_info.get("blank_count", 0)
                    invalid_count = column_info.get("invalid_numeric_count", 0)
                    low_range_count = column_info.get("low_range_numeric_count", 0)
                    pct_format = column_info.get("percentage_format_count", 0)
                    rev_format = column_info.get("revenue_format_count", 0)
                    total_issues = (
                        blank_count
                        + invalid_count
                        + low_range_count
                        + pct_format
                        + rev_format
                    )

                    column_item = QTreeWidgetItem([f"    {col_name}", str(total_issues)])
                    column_item.setFlags(column_item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsSelectable)
                    column_item.setCheckState(0, Qt.Checked)

                    # Store file_path and col_idx in the item for easy retrieval
                    column_item.setData(0, Qt.UserRole, (str(summary.file_path), col_idx)) # Store as string for data storage

                    tooltip_parts = []
                    if blank_count:
                        tooltip_parts.append(f"Blank/invalid: {blank_count}")
                    if invalid_count:
                        tooltip_parts.append(f"Non-numeric: {invalid_count}")
                    if low_range_count:
                        tooltip_parts.append(f"0-1 range: {low_range_count}")
                    if pct_format:
                        tooltip_parts.append(f"% formatting: {pct_format}")
                    if rev_format:
                        tooltip_parts.append(f"Revenue decimals: {rev_format}")
                    if tooltip_parts:
                        column_item.setToolTip(0, "\n".join(tooltip_parts))
                    
                    file_item.addChild(column_item)
                    selected_set.add(col_idx)
                    columns_added_count += 1
                    self.log(f"DEBUG: Added column item: {col_name} for {summary.file_path.name}")

            if not has_any_columns:

                no_issues_item = QTreeWidgetItem([
                    "✅ No issues found! All metric columns are clean.", ""
                ])
                no_issues_item.setFont(0, QFont("Arial", 12))
                no_issues_item.setForeground(0, QColor("#4CAF50"))
                self.column_tree.addTopLevelItem(no_issues_item)
                self.log("DEBUG: Added 'No issues found' item.")

            # self.apply_btn.setEnabled(has_selection) # This line is moved to _on_scan_complete
            # The connections are already set up in setup_ui, no need to re-connect
            # self.column_tree.itemChanged.connect(self._on_column_item_changed)
            # self.column_tree.itemClicked.connect(self._on_file_selected_in_tree)
            # self.column_tree.expandAll() # Temporarily disabled for debugging
            self.column_tree.resizeColumnToContents(1) # Adjust column width
            # self.column_tree.update() # Temporarily disabled for debugging
            self.log(f"DEBUG: _update_column_list finished. Files added: {files_added_count}, Columns added: {columns_added_count}.")
        except Exception as e:
            self.log(f"CRITICAL ERROR in _update_column_list: {e}")
            QMessageBox.critical(self, "UI Error", f"A critical error occurred while updating the column list: {e}")

    def _on_column_item_changed(self, item: QTreeWidgetItem, column: int):
        """Handle column checkbox toggle in QTreeWidget"""
        if column != 0: # Only care about changes to the checkbox in the first column
            return

        file_path_str, col_idx_val = item.data(0, Qt.UserRole) if item.data(0, Qt.UserRole) else (None, None)
        
        if file_path_str is None and col_idx_val is None: # This is a file item
            file_path = Path(item.text(0).replace("📄 ", ""))
            state = item.checkState(0)
            # Propagate state to children (columns)
            for i in range(item.childCount()):
                child_item = item.child(i)
                child_item.setCheckState(0, state)
        else: # This is a column item
            file_path = Path(file_path_str)
            col_idx = int(col_idx_val)
            state = item.checkState(0)

            if file_path not in self.selected_columns:
                self.selected_columns[file_path] = set()
            
            if state == Qt.Checked:
                self.selected_columns[file_path].add(col_idx)
            else:
                self.selected_columns[file_path].discard(col_idx)

            # Update parent (file) check state if all children are checked/unchecked
            parent_item = item.parent()
            if parent_item:
                all_children_checked = True
                all_children_unchecked = True
                for i in range(parent_item.childCount()):
                    child = parent_item.child(i)
                    if child.checkState(0) == Qt.Unchecked:
                        all_children_checked = False
                    if child.checkState(0) == Qt.Checked:
                        all_children_unchecked = False
                
                if all_children_checked:
                    parent_item.setCheckState(0, Qt.Checked)
                elif all_children_unchecked:
                    parent_item.setCheckState(0, Qt.Unchecked)
                else:
                    parent_item.setCheckState(0, Qt.PartiallyChecked)

        # Update apply button state based on current selections
        self._update_apply_button_state()
        
        # Update preview
        self._update_preview() # This will be updated to show sample rows of selected file
    
    def _update_apply_button_state(self):
        """
        Helper to update the enabled state of the apply button
        based on current column selections.
        """
        has_selections = False
        for path, cols in self.selected_columns.items():
            if cols:
                has_selections = True
                break
        self.apply_btn.setEnabled(has_selections and not self.is_scanning)

    def select_all_columns(self):
        """Select all columns (only those with issues) in the QTreeWidget."""
        for i in range(self.column_tree.topLevelItemCount()):
            file_item = self.column_tree.topLevelItem(i)
            if file_item and file_item.text(0).startswith("📄 "): # Only process actual file nodes
                file_item.setCheckState(0, Qt.Checked)
                file_path = Path(file_item.text(0).replace("📄 ", ""))
                self.selected_columns.setdefault(file_path, set())
                self.selected_columns[file_path].clear()
                for j in range(file_item.childCount()):
                    column_item = file_item.child(j)
                    column_item.setCheckState(0, Qt.Checked)
                    file_path_str, col_idx_val = column_item.data(0, Qt.UserRole)
                    if file_path_str and col_idx_val is not None:
                        self.selected_columns[Path(file_path_str)].add(int(col_idx_val))
        
        self._update_apply_button_state()
        self._update_preview()
    
    def select_none_columns(self):
        """Deselect all columns in the QTreeWidget."""
        for file_path in list(self.selected_columns.keys()):
            self.selected_columns[file_path].clear()

        for i in range(self.column_tree.topLevelItemCount()):
            file_item = self.column_tree.topLevelItem(i)
            file_item.setCheckState(0, Qt.Unchecked)
            for j in range(file_item.childCount()):
                file_item.child(j).setCheckState(0, Qt.Unchecked)
        
        self._update_apply_button_state()
        self._clear_preview()
        self._update_preview()
    
    def _clear_preview(self):
        """Clear preview table"""
        self.preview_table.setRowCount(0)
        self.preview_table.setColumnCount(0)
    
    def _update_preview(self, file_path: Optional[Path] = None):
        """Load and display a sample of the selected CSV file in the preview table."""
        self.preview_table.setRowCount(0)
        self.preview_table.setColumnCount(0)

        if file_path is None or not file_path.exists():
            self.preview_table.setRowCount(1)
            self.preview_table.setColumnCount(1)
            self.preview_table.setHorizontalHeaderLabels(["No File Selected / Preview Disabled"])
            self.preview_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            notice_item = QTableWidgetItem(
                "Select a file from the list to view a sample preview."
            )
            notice_item.setFlags(Qt.ItemIsEnabled)
            self.preview_table.setItem(0, 0, notice_item)
            return

        try:
            with file_path.open("r", newline="", encoding="utf-8") as handle:
                # Sniff dialect
                sample = handle.read(2048)
                handle.seek(0)
                try:
                    dialect = csv.Sniffer().sniff(sample)
                except csv.Error:
                    dialect = csv.excel

                reader = csv.reader(handle, dialect)
                header = next(reader, None)
                if not header:
                    self.preview_table.setRowCount(1)
                    self.preview_table.setColumnCount(1)
                    self.preview_table.setHorizontalHeaderLabels(["Empty File"])
                    empty_item = QTableWidgetItem("File is empty or has no header.")
                    empty_item.setFlags(Qt.ItemIsEnabled)
                    self.preview_table.setItem(0, 0, empty_item)
                    return

                self.preview_table.setColumnCount(len(header))
                self.preview_table.setHorizontalHeaderLabels(header)
                self.preview_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

                rows_to_display = []
                for i, row in enumerate(reader):
                    if i >= 100:  # Limit to 100 rows for performance
                        break
                    # Ensure row length matches header length for display consistency
                    if len(row) < len(header):
                        row = list(row) + [""] * (len(header) - len(row))
                    elif len(row) > len(header):
                        row = row[:len(header)]
                    rows_to_display.append(row)

                self.preview_table.setRowCount(len(rows_to_display))
                for r_idx, row_data in enumerate(rows_to_display):
                    for c_idx, cell_data in enumerate(row_data):
                        item = QTableWidgetItem(cell_data)
                        item.setFlags(Qt.ItemIsEnabled) # Make cells non-editable
                        self.preview_table.setItem(r_idx, c_idx, item)

        except Exception as e:
            self.log(f"⚠️ Error loading preview for {file_path.name}: {e}")
            self.preview_table.setRowCount(1)
            self.preview_table.setColumnCount(1)
            self.preview_table.setHorizontalHeaderLabels(["Preview Error"])
            error_item = QTableWidgetItem(f"Could not load preview: {e}")
            error_item.setFlags(Qt.ItemIsEnabled)
            self.preview_table.setItem(0, 0, error_item)

    def _on_file_selected_in_tree(self, item: QTreeWidgetItem, column: int):
        """
        Handles selection changes in the QTreeWidget to update the preview.
        Only updates preview if a file item (top-level) is clicked.
        """
        # Check if it's a file item (not a column item)
        file_path_str, col_idx_val = item.data(0, Qt.UserRole) if item.data(0, Qt.UserRole) else (None, None)
        
        if file_path_str is None and col_idx_val is None: # This is a file item
            file_name_prefix = "📄 "
            item_text = item.text(0)
            if item_text.startswith(file_name_prefix):
                file_path = Path(item_text.replace(file_name_prefix, ""))
                self._update_preview(file_path)
            else:
                self._clear_preview()
        else:
            self._clear_preview()

    def start_fix(self):
        """Start fixing selected metric fields"""
        if self.is_fixing or self.is_scanning:
            return
        
        # Check if any columns selected
        has_selections = any(cols for cols in self.selected_columns.values())
        if not has_selections:
            QMessageBox.warning(
                self,
                "No Selection",
                "Please select at least one column to fix!"
            )
            return

        files_to_fix = [
            file_path
            for file_path, columns in self.selected_columns.items()
            if columns
        ]

        if not files_to_fix:
            QMessageBox.warning(
                self,
                "No Selection",
                "Please select at least one column to fix!"
            )
            return
 
        # Confirm
        reply = QMessageBox.question(
            self,
            "Confirm Fix",
            "This will create fixed CSV files in the output folder.\n\nContinue?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # Create output folder for this run
        info = self.allocate_run_directory(
            "Metric Fixer",
            script_name=Path(__file__).name,
        )
        self.output_path = Path(info["root"])
         
        # Start worker
        self.is_fixing = True
        self.apply_btn.setEnabled(False)
        self.scan_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setMaximum(len(files_to_fix))
        self.progress.setValue(0)
        
        self.worker = MetricFixerWorker(
            files=files_to_fix,
            output_dir=self.output_path,
            selected_columns={path: set(columns) for path, columns in self.selected_columns.items()},
            column_metadata=self.column_metadata,
        )
        
        self.worker_thread = QThread()
        self.worker.moveToThread(self.worker_thread)
        
        self.worker_thread.started.connect(self.worker.fix_files)
        self.worker.log_signal.connect(self._log)
        self.worker.progress_signal.connect(self._on_fix_progress)
        self.worker.fix_complete_signal.connect(self._on_fix_complete)
        
        self.worker_thread.start()
        
        if self.execution_log:
            self.log("🔧 Starting to fix metric fields...")
    
    def _on_fix_progress(self, current: int, total: int):
        """Update fix progress"""
        self.progress.setValue(current)
    
    def _on_fix_complete(self, success: int, failed: int):
        """Handle fix completion"""
        self.is_fixing = False
        self.apply_btn.setEnabled(True)
        self.scan_btn.setEnabled(True)
        self.progress.setVisible(False)
        
        if self.execution_log:
            self.log(f"✅ Fix complete! Success: {success}, Failed: {failed}")
        
        QMessageBox.information(
            self,
            "Fix Complete",
            f"Fixed {success} file(s) successfully!\n\nOutput: {self.output_path}"
        )
    
    def _log(self, message: str):
        """Log message to execution log"""
        if self.execution_log:
            self.log(message)
    
    def closeEvent(self, event):
        """Handle window close"""
        if self.worker_thread and self.worker_thread.isRunning():
            self.worker.should_stop = True
            self.worker_thread.quit()
            self.worker_thread.wait(3000)
        
        event.accept()

# Alias for main.py compatibility
MetricFixer = MetricFixerTool


def main():
    """Test the tool standalone"""
    from PySide6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # Create dummy parent with theme
    class DummyParent:
        def __init__(self):
            try:
                from styles import get_theme_manager
                theme_manager = get_theme_manager()
                themes = theme_manager.get_available_themes()
                self.current_theme = theme_manager.load_theme(themes[0]) if themes else None
            except:
                self.current_theme = None
    
    parent = DummyParent()
    
    # Create tool
    from styles import get_path_manager
    path_manager = get_path_manager()
    tool = MetricFixerTool(
        parent,
        str(path_manager.get_input_path()),
        str(path_manager.get_output_path())
    )
    
    tool.show()
    tool.raise_()
    tool.activateWindow()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

