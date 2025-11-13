"""
🌊 Date Format Converter Tool
-----------------------------

PySide GUI for normalising the `Date` column across CSV files.
Optimised for large batches with streaming conversion, column detection,
and manifest-aware resume support.
"""

from __future__ import annotations

import csv
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PySide6.QtCore import QObject, QThread, Qt, Signal, QSignalBlocker
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from tools.date_time_utilities.date_format_converter_engine import (
    BatchConfig,
    DateConversionConfig,
    DEFAULT_CHUNK_SIZE,
    default_manifest_name,
    discover_files,
    load_completed_from_manifest,
    run_batch,
)
from tools.templates import BaseToolDialog, PathConfigMixin


PREVIEW_ROW_LIMIT = 50
SIZE_WARNING_THRESHOLD = 1_500_000_000  # ~1.5 GB
COLUMN_ALIAS_PRIORITY: Tuple[str, ...] = (
    "date",
    "eventdate",
    "sessiondate",
    "ga4date",
    "fulldate",
    "day",
)
DEFAULT_INPUT_FORMATS = ["%Y-%m-%d", "%m/%d/%Y", "%Y%m%d"]
DEFAULT_OUTPUT_FORMAT = "%Y-%m-%d"


def _normalise_column_name(name: str) -> str:
    return "".join(ch for ch in name.lower() if ch.isalnum())


def _format_bytes(num_bytes: int) -> str:
    if num_bytes <= 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(num_bytes)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} TB"


@dataclass
class ConverterOptions:
    target_column: str
    input_formats: List[str]
    output_format: str
    fallback_mode: str
    fallback_value: str
    keep_original: bool
    infer: bool
    workers: int
    dry_run: bool
    write_parquet: bool
    resume: bool
    chunk_size: int


class DateConverterWorker(QObject):
    log_signal = Signal(str)
    progress_signal = Signal(int, int, dict)
    finished_signal = Signal(dict)

    def __init__(
        self,
        files: List[Path],
        options: ConverterOptions,
        output_root: Path,
        manifest_path: Path,
    ):
        super().__init__()
        self.files = files
        self.options = options
        self.output_root = output_root
        self.manifest_path = manifest_path

    def run(self) -> None:
        try:
            config = DateConversionConfig(
                column_name=self.options.target_column,
                input_formats=tuple(self.options.input_formats),
                output_format=self.options.output_format,
                fallback_mode=self.options.fallback_mode,
                fallback_value=self.options.fallback_value,
                keep_original=self.options.keep_original,
                infer_missing_formats=self.options.infer,
            )

            batch_cfg = BatchConfig(
                output_root=self.output_root,
                workers=max(1, self.options.workers),
                dry_run=self.options.dry_run,
                write_parquet=self.options.write_parquet,
                resume=self.options.resume,
                manifest_path=self.manifest_path,
                chunk_size=max(1_000, self.options.chunk_size),
            )

            resume_cache = (
                load_completed_from_manifest(self.manifest_path)
                if self.options.resume
                else {}
            )

            if self.options.dry_run:
                self.log_signal.emit("🧪 Dry run enabled — no files will be written.")

            summary = run_batch(
                self.files,
                config,
                batch_cfg,
                resume_cache=resume_cache,
                progress_callback=self.progress_signal.emit,
            )
            self.finished_signal.emit(summary)
        except Exception as exc:  # pragma: no cover - defensive
            self.log_signal.emit(f"❌ Worker crashed: {exc}")
            self.finished_signal.emit(
                {
                    "total": len(self.files),
                    "success": 0,
                    "failed": len(self.files),
                    "skipped": 0,
                    "parsed": 0,
                    "parsed_inferred": 0,
                    "fallback": 0,
                    "bytes_total": 0,
                    "dry_run": self.options.dry_run,
                    "results": [],
                    "manifest": str(self.manifest_path),
                }
            )


class DateFormatConverterTool(PathConfigMixin, BaseToolDialog):
    PATH_CONFIG = {
        "show_input": True,
        "show_output": True,
        "include_open_buttons": True,
        "input_label": "📥 Input Folder:",
        "output_label": "📤 Output Folder:",
    }

    def __init__(self, parent, input_path: str, output_path: str) -> None:
        super().__init__(parent, input_path, output_path)

        self.csv_files: List[Path] = []
        self.file_stats: Dict[str, Dict[str, int]] = {}
        self.preview_cache: Dict[str, Tuple[List[str], List[List[str]]]] = {}
        self.column_frequencies: Counter[str] = Counter()
        self.column_candidates: List[str] = []
        self.detected_column: Optional[str] = None
        self.total_scan_bytes: int = 0

        self.worker_thread: Optional[QThread] = None
        self.worker: Optional[DateConverterWorker] = None

        self.is_scanning = False
        self.is_converting = False
        self.size_warning_threshold = SIZE_WARNING_THRESHOLD

        self.status_label: Optional[QLabel] = None
        self.column_status_label: Optional[QLabel] = None
        self.scan_stats_label: Optional[QLabel] = None

        self.setup_window_properties(
            title="🗓️ Date Format Converter",
            width=1120,
            height=760,
        )

        self._build_ui()
        self.apply_theme()

        if self.execution_log:
            self.log("🗓️ Date Format Converter ready. Scan the folder, verify detection, then press Convert.")

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(12)

        header = QLabel("🗓️ Date Format Converter")
        header.setFont(QFont("Arial", 20, QFont.Bold))
        header.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(header)

        self.build_path_controls(
            main_layout,
            show_input=True,
            show_output=True,
            include_open_buttons=True,
        )

        control_frame = QFrame()
        control_layout = QHBoxLayout(control_frame)
        control_layout.setContentsMargins(8, 8, 8, 8)
        control_layout.setSpacing(10)

        self.scan_button = QPushButton("🔍 Scan CSV Files")
        self.scan_button.setMinimumHeight(36)
        self.scan_button.clicked.connect(self.scan_files)
        control_layout.addWidget(self.scan_button)

        self.convert_button = QPushButton("✅ Convert Dates")
        self.convert_button.setMinimumHeight(36)
        self.convert_button.setEnabled(False)
        self.convert_button.clicked.connect(self.start_conversion)
        control_layout.addWidget(self.convert_button)

        control_layout.addStretch()

        self.status_label = QLabel("Ready.")
        control_layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%v / %m files")
        control_layout.addWidget(self.progress_bar)

        main_layout.addWidget(control_frame)

        splitter = QSplitter(Qt.Horizontal)

        # Left panel: file table + preview
        left_panel = QFrame()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(10, 10, 10, 10)
        left_layout.setSpacing(8)

        files_label = QLabel("📁 Discovered Files")
        files_label.setFont(QFont("Arial", 12, QFont.Bold))
        left_layout.addWidget(files_label)

        self.files_table = QTableWidget()
        self.files_table.setColumnCount(4)
        self.files_table.setHorizontalHeaderLabels(["Filename", "Columns", "Rows", "Size"])
        header_view = self.files_table.horizontalHeader()
        header_view.setSectionResizeMode(0, QHeaderView.Stretch)
        header_view.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header_view.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header_view.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.files_table.verticalHeader().setVisible(False)
        self.files_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.files_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.files_table.setAlternatingRowColors(True)
        self.files_table.itemSelectionChanged.connect(self._on_file_selected)
        left_layout.addWidget(self.files_table)

        preview_label = QLabel(f"👁️ Preview (first {PREVIEW_ROW_LIMIT} rows)")
        preview_label.setFont(QFont("Arial", 12, QFont.Bold))
        left_layout.addWidget(preview_label)

        self.preview_table = QTableWidget()
        self.preview_table.horizontalHeader().setStretchLastSection(True)
        left_layout.addWidget(self.preview_table)

        splitter.addWidget(left_panel)

        # Right panel: column detection + settings
        right_panel = QFrame()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(10, 10, 10, 10)
        right_layout.setSpacing(10)

        self.column_group = self._build_column_group()
        right_layout.addWidget(self.column_group)

        settings_group = self._build_settings_group()
        right_layout.addWidget(settings_group)

        workers_row = QHBoxLayout()
        workers_row.setSpacing(12)

        workers_row.addWidget(QLabel("Parallel workers:"))
        self.workers_input = QLineEdit("2")
        workers_row.addWidget(self.workers_input)

        workers_row.addWidget(QLabel("Chunk size:"))
        self.chunk_size_input = QLineEdit(str(DEFAULT_CHUNK_SIZE))
        self.chunk_size_input.setToolTip("Rows per batch when streaming large files. Larger chunks use more memory but run faster.")
        workers_row.addWidget(self.chunk_size_input)

        workers_row.addStretch()
        right_layout.addLayout(workers_row)

        summary_group = QGroupBox("📊 Last Run Summary")
        summary_layout = QVBoxLayout(summary_group)
        summary_layout.setSpacing(4)
        self.summary_label = QLabel("No runs yet.")
        self.summary_label.setWordWrap(True)
        summary_layout.addWidget(self.summary_label)
        right_layout.addWidget(summary_group)

        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        main_layout.addWidget(splitter, stretch=1)

        self.execution_log = self.create_execution_log(main_layout)

    def _build_column_group(self) -> QGroupBox:
        group = QGroupBox("🎯 Target Column")
        layout = QVBoxLayout(group)
        layout.setSpacing(6)

        self.column_status_label = QLabel("Scan a folder to detect date-like columns.")
        self.column_status_label.setWordWrap(True)
        layout.addWidget(self.column_status_label)

        self.scan_stats_label = QLabel("No files scanned yet.")
        self.scan_stats_label.setWordWrap(True)
        layout.addWidget(self.scan_stats_label)

        override_row = QHBoxLayout()
        override_row.setSpacing(8)
        self.override_checkbox = QCheckBox("Manual override")
        self.override_checkbox.setEnabled(False)
        self.override_checkbox.stateChanged.connect(self._on_override_toggled)
        override_row.addWidget(self.override_checkbox)
        override_row.addStretch()
        layout.addLayout(override_row)

        self.column_override_combo = QComboBox()
        self.column_override_combo.setEnabled(False)
        self.column_override_combo.currentTextChanged.connect(self._on_override_selection_changed)
        layout.addWidget(self.column_override_combo)

        return group

    def _build_settings_group(self) -> QGroupBox:
        group = QGroupBox("⚙️ Conversion Settings")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        layout.addWidget(QLabel("Input formats (one per line):"))
        self.input_formats_edit = QTextEdit()
        self.input_formats_edit.setPlaceholderText("%Y-%m-%d\n%m/%d/%Y\n%Y%m%d")
        self.input_formats_edit.setPlainText("\n".join(DEFAULT_INPUT_FORMATS))
        layout.addWidget(self.input_formats_edit)

        layout.addWidget(QLabel("Output format:"))
        self.output_format_edit = QLineEdit(DEFAULT_OUTPUT_FORMAT)
        layout.addWidget(self.output_format_edit)

        fallback_row = QHBoxLayout()
        fallback_row.setSpacing(8)
        fallback_row.addWidget(QLabel("Fallback behaviour:"))

        self.fallback_combo = QComboBox()
        self.fallback_combo.addItems(["blank", "original", "constant"])
        fallback_row.addWidget(self.fallback_combo)

        self.fallback_value_edit = QLineEdit()
        self.fallback_value_edit.setPlaceholderText("Value when fallback = constant")
        fallback_row.addWidget(self.fallback_value_edit)
        layout.addLayout(fallback_row)

        self.keep_original_checkbox = QCheckBox("Preserve original column (create Date_raw)")
        layout.addWidget(self.keep_original_checkbox)

        self.infer_checkbox = QCheckBox("Attempt automatic inference for other formats")
        self.infer_checkbox.setChecked(True)
        layout.addWidget(self.infer_checkbox)

        self.dry_run_checkbox = QCheckBox("Dry run (no files written)")
        layout.addWidget(self.dry_run_checkbox)

        self.no_parquet_checkbox = QCheckBox("Skip Parquet output")
        self.no_parquet_checkbox.setChecked(True)
        layout.addWidget(self.no_parquet_checkbox)

        self.resume_checkbox = QCheckBox("Resume (skip successful files)")
        layout.addWidget(self.resume_checkbox)

        return group

    # ------------------------------------------------------------------
    # Scanning & Preview
    # ------------------------------------------------------------------

    def _reset_scan_state(self) -> None:
        self.preview_cache.clear()
        self.column_frequencies.clear()
        self.column_candidates.clear()
        self.detected_column = None
        self.total_scan_bytes = 0

    def _scan_single_file(self, file_path: Path) -> Tuple[List[str], List[List[str]], int]:
        header: List[str] = []
        preview_rows: List[List[str]] = []
        row_count = 0

        with file_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.reader(handle)
            header = [column.strip() for column in next(reader, [])]
            for row in reader:
                row_count += 1
                if len(preview_rows) < PREVIEW_ROW_LIMIT:
                    preview_rows.append([str(value) for value in row])

        return header, preview_rows, row_count

    def scan_files(self) -> None:
        if self.is_scanning or self.is_converting:
            return

        input_path = self.input_path
        if not input_path or not input_path.exists():
            QMessageBox.warning(self, "Input Folder Missing", "Please select a valid input folder.")
            return

        csv_files = discover_files(input_path)
        if not csv_files:
            QMessageBox.information(self, "No CSV Files", "No CSV files found in the selected folder.")
            self._set_status("No CSV files detected.")
            return

        self.is_scanning = True
        self.scan_button.setEnabled(False)
        self.convert_button.setEnabled(False)
        self.progress_bar.setVisible(False)
        self._set_status(f"Scanning {len(csv_files)} file(s)…")

        self.csv_files = csv_files
        self.file_stats.clear()
        self._reset_scan_state()

        for index, file_path in enumerate(csv_files, start=1):
            header: List[str] = []
            preview_rows: List[List[str]] = []
            row_count = 0
            size_bytes = 0

            try:
                header, preview_rows, row_count = self._scan_single_file(file_path)
                size_bytes = file_path.stat().st_size
                self.total_scan_bytes += size_bytes

                for column in header:
                    if column:
                        self.column_frequencies[column] += 1

                self.preview_cache[str(file_path)] = (header, preview_rows)
            except Exception as exc:
                self.preview_cache[str(file_path)] = ([], [])
                if self.execution_log:
                    self.log(f"⚠️ Unable to read {file_path.name}: {exc}")

            self.file_stats[str(file_path)] = {
                "columns": len(header),
                "rows": row_count,
                "size": size_bytes,
            }

            if self.execution_log and index % 25 == 0:
                self.log(f"…scanned {index}/{len(csv_files)} files")

        self.column_candidates = sorted(
            self.column_frequencies.keys(),
            key=lambda name: (-self.column_frequencies[name], name.lower()),
        )
        self.detected_column = self._resolve_target_column()

        self._update_file_table()
        if self.csv_files:
            self.files_table.selectRow(0)
            self.refresh_preview(self.csv_files[0])

        self.is_scanning = False
        self.scan_button.setEnabled(True)
        self._update_column_detection_ui()
        self._update_scan_stats()
        self._update_convert_button_state()
        self._set_status(f"Scan complete — {len(self.csv_files)} file(s)")

        if self.execution_log:
            self.log(
                f"✅ Scan complete. Files: {len(self.csv_files)}, Columns discovered: {len(self.column_frequencies)}, Total size: {_format_bytes(self.total_scan_bytes)}"
            )

    def _update_file_table(self) -> None:
        self.files_table.setRowCount(0)
        for file_path in self.csv_files:
            stats = self.file_stats.get(str(file_path), {})
            row_index = self.files_table.rowCount()
            self.files_table.insertRow(row_index)

            self.files_table.setItem(row_index, 0, QTableWidgetItem(file_path.name))
            self.files_table.setItem(row_index, 1, QTableWidgetItem(str(stats.get("columns", 0))))
            self.files_table.setItem(row_index, 2, QTableWidgetItem(str(stats.get("rows", 0))))
            self.files_table.setItem(row_index, 3, QTableWidgetItem(_format_bytes(stats.get("size", 0))))

    def _on_file_selected(self) -> None:
        selected_items = self.files_table.selectedItems()
        if not selected_items:
            return
        row = selected_items[0].row()
        if 0 <= row < len(self.csv_files):
            self.refresh_preview(self.csv_files[row])

    def refresh_preview(self, file_path: Optional[Path] = None) -> None:
        self.preview_table.clear()
        if not file_path:
            self.preview_table.setRowCount(0)
            self.preview_table.setColumnCount(0)
            return

        header, rows = self.preview_cache.get(str(file_path), ([], []))
        self.preview_table.setColumnCount(len(header))
        self.preview_table.setHorizontalHeaderLabels(header)
        self.preview_table.setRowCount(len(rows))

        for row_index, row in enumerate(rows):
            padded = row + [""] * (len(header) - len(row))
            for column_index, value in enumerate(padded[: len(header)]):
                item = QTableWidgetItem(value)
                item.setFlags(Qt.ItemIsEnabled)
                self.preview_table.setItem(row_index, column_index, item)

    def _update_scan_stats(self) -> None:
        if not self.csv_files:
            self.scan_stats_label.setText("No files scanned.")
            return
        self.scan_stats_label.setText(
            f"Files: {len(self.csv_files)}, Total size: {_format_bytes(self.total_scan_bytes)}, Columns discovered: {len(self.column_frequencies)}"
        )

    # ------------------------------------------------------------------
    # Column detection + overrides
    # ------------------------------------------------------------------

    def _resolve_target_column(self) -> Optional[str]:
        if not self.column_frequencies:
            return None

        normalised_map: Dict[str, List[str]] = {}
        for column in self.column_frequencies:
            key = _normalise_column_name(column)
            normalised_map.setdefault(key, []).append(column)

        for alias in COLUMN_ALIAS_PRIORITY:
            if alias in normalised_map:
                candidates = sorted(
                    normalised_map[alias],
                    key=lambda name: (-self.column_frequencies[name], name.lower()),
                )
                if candidates:
                    return candidates[0]

        fallback_candidates = [
            column
            for column in self.column_frequencies
            if "date" in _normalise_column_name(column)
        ]
        if fallback_candidates:
            return max(
                fallback_candidates,
                key=lambda name: (self.column_frequencies[name], name.lower()),
            )

        return max(
            self.column_frequencies,
            key=lambda name: (self.column_frequencies[name], -len(name)),
            default=None,
        )

    def _get_active_column(self) -> Optional[str]:
        if self.override_checkbox.isChecked():
            value = self.column_override_combo.currentText().strip()
            return value or None
        return self.detected_column

    def _refresh_column_status_text(self) -> None:
        if not self.column_status_label:
            return
        if self.override_checkbox.isChecked():
            selected = self.column_override_combo.currentText().strip()
            if selected:
                self.column_status_label.setText(
                    f"Manual override active → using <b>{selected}</b>."
                )
            else:
                self.column_status_label.setText("Manual override active — select a column.")
            return

        if self.detected_column:
            freq = self.column_frequencies.get(self.detected_column, 0)
            self.column_status_label.setText(
                f"Auto-detected column: <b>{self.detected_column}</b> (present in {freq} file(s))."
            )
        else:
            self.column_status_label.setText(
                "No date-like column detected. Enable manual override to choose one."
            )

    def _update_column_detection_ui(self) -> None:
        with QSignalBlocker(self.override_checkbox):
            self.override_checkbox.setEnabled(bool(self.csv_files))
            if not self.csv_files:
                self.override_checkbox.setChecked(False)

        with QSignalBlocker(self.column_override_combo):
            self.column_override_combo.clear()
            for column in self.column_candidates:
                self.column_override_combo.addItem(column)
            if self.detected_column:
                index = self.column_override_combo.findText(self.detected_column)
                if index >= 0:
                    self.column_override_combo.setCurrentIndex(index)

        self.column_override_combo.setEnabled(self.override_checkbox.isChecked())
        self._refresh_column_status_text()

    def _on_override_toggled(self, state: int) -> None:
        enabled = state == Qt.Checked
        self.column_override_combo.setEnabled(enabled)
        self._refresh_column_status_text()
        self._update_convert_button_state()

    def _on_override_selection_changed(self) -> None:
        self._refresh_column_status_text()
        self._update_convert_button_state()

    # ------------------------------------------------------------------
    # Conversion
    # ------------------------------------------------------------------

    def _collect_options(self) -> Optional[ConverterOptions]:
        if not self.csv_files:
            QMessageBox.warning(self, "No Files", "Scan CSV files before converting.")
            return None

        target_column = self._get_active_column()
        if not target_column:
            QMessageBox.warning(
                self,
                "No Column Detected",
                "No date-like column detected. Enable manual override to pick one.",
            )
            return None

        input_formats = [
            line.strip()
            for line in self.input_formats_edit.toPlainText().splitlines()
            if line.strip()
        ]
        if not input_formats:
            QMessageBox.warning(
                self,
                "No Input Formats",
                "Provide at least one input date format.",
            )
            return None

        output_format = self.output_format_edit.text().strip() or DEFAULT_OUTPUT_FORMAT
        fallback_mode = self.fallback_combo.currentText()
        fallback_value = self.fallback_value_edit.text().strip()
        if fallback_mode == "constant" and not fallback_value:
            fallback_value = "1970-01-01"

        try:
            workers = max(1, int(self.workers_input.text().strip() or "2"))
        except ValueError:
            QMessageBox.warning(self, "Invalid Workers", "Workers must be a positive integer.")
            return None

        try:
            chunk_size = max(1_000, int(self.chunk_size_input.text().strip() or str(DEFAULT_CHUNK_SIZE)))
        except ValueError:
            QMessageBox.warning(self, "Invalid Chunk Size", "Chunk size must be a positive integer.")
            return None

        return ConverterOptions(
            target_column=target_column,
            input_formats=input_formats,
            output_format=output_format,
            fallback_mode=fallback_mode,
            fallback_value=fallback_value,
            keep_original=self.keep_original_checkbox.isChecked(),
            infer=self.infer_checkbox.isChecked(),
            workers=workers,
            dry_run=self.dry_run_checkbox.isChecked(),
            write_parquet=not self.no_parquet_checkbox.isChecked(),
            resume=self.resume_checkbox.isChecked(),
            chunk_size=chunk_size,
        )

    def _estimate_total_bytes(self) -> int:
        total = 0
        for path in self.csv_files:
            if path.exists():
                total += path.stat().st_size
        return total

    def start_conversion(self) -> None:
        if self.is_converting or self.is_scanning:
            return

        options = self._collect_options()
        if options is None:
            return

        total_bytes = self._estimate_total_bytes()
        if total_bytes > self.size_warning_threshold:
            decision = QMessageBox.question(
                self,
                "Large Batch Warning",
                (
                    f"This batch is large ({_format_bytes(total_bytes)}). "
                    "Ensure you have enough disk space and memory.\n\nProceed?"
                ),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if decision != QMessageBox.Yes:
                self._set_status("Conversion aborted by user.")
                return

        run_info = self.allocate_run_directory(
            "Date Format Converter",
            script_name=Path(__file__).name,
        )
        run_root = Path(run_info["root"])
        manifest_path = default_manifest_name(run_root)

        self.is_converting = True
        self.scan_button.setEnabled(False)
        self.convert_button.setEnabled(False)

        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(self.csv_files))
        self.progress_bar.setValue(0)
        self._set_status(f"Converting {len(self.csv_files)} file(s)…")

        self.worker_thread = QThread()
        self.worker = DateConverterWorker(
            files=self.csv_files,
            options=options,
            output_root=run_root,
            manifest_path=manifest_path,
        )
        self.worker.moveToThread(self.worker_thread)

        self.worker_thread.started.connect(self.worker.run)
        self.worker.log_signal.connect(self.log)
        self.worker.progress_signal.connect(self._on_progress_update)
        self.worker.finished_signal.connect(self._on_conversion_finished)
        self.worker.finished_signal.connect(self.worker_thread.quit)
        self.worker_thread.finished.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)

        self.worker_thread.start()
        if self.execution_log:
            self.log(
                f"🚀 Starting date conversion — workers={options.workers}, chunk_size={options.chunk_size}, dry_run={options.dry_run}"
            )

    def _on_progress_update(self, current: int, total: int, record: Dict) -> None:
        self.progress_bar.setMaximum(max(total, 1))
        self.progress_bar.setValue(min(current, total))

        file_name = Path(record.get("input_path", "")).name or "(unknown file)"
        status = record.get("status", "unknown")
        message = record.get("message", "")
        is_skipped = bool(record.get("skipped"))

        if is_skipped:
            status_text = f"{current}/{total} · {file_name} → skipped (resume)"
        else:
            status_text = f"{current}/{total} · {file_name} → {status}"
            if message and status not in {"success", "partial"}:
                status_text += f" ({message})"

        self._set_status(status_text)

        if self.execution_log:
            prefix = "⏭️" if is_skipped else "📦"
            log_message = f"{prefix} [{current}/{total}] {file_name}: {status}"
            if message:
                log_message += f" — {message}"
            self.log(log_message)

    def _on_conversion_finished(self, summary: Dict) -> None:
        self.is_converting = False
        self.progress_bar.setVisible(False)
        self.scan_button.setEnabled(True)
        self._update_convert_button_state()

        success = summary.get("success", 0)
        failed = summary.get("failed", 0)
        skipped = summary.get("skipped", 0)
        parsed = summary.get("parsed", 0)
        inferred = summary.get("parsed_inferred", 0)
        fallback = summary.get("fallback", 0)
        total = summary.get("total", len(self.csv_files))
        total_bytes = summary.get("bytes_total", 0)
        manifest = summary.get("manifest", "")
        results: List[Dict] = summary.get("results", [])

        message_lines = [
            f"Total files: {total}",
            f"Success: {success}",
            f"Failed: {failed}",
            f"Skipped: {skipped}",
            f"Parsed: {parsed}",
            f"Parsed (inferred): {inferred}",
            f"Fallback triggered: {fallback}",
            f"Total bytes: {_format_bytes(total_bytes)}",
        ]
        if manifest:
            message_lines.append(f"Manifest: {manifest}")

        QMessageBox.information(
            self,
            "Conversion Complete",
            "\n".join(message_lines),
        )

        failure_rows = [
            record
            for record in results
            if record.get("status") not in {"success", "partial"}
            and not record.get("skipped")
        ]
        if failure_rows:
            failure_lines = "<br>".join(
                f"&nbsp;• {Path(record.get('input_path', '')).name}: {record.get('message', 'unknown error')}"
                for record in failure_rows[:3]
            )
            failure_summary = f"Top failures:<br>{failure_lines}"
        else:
            failure_summary = "Top failures: none 🎉"

        summary_html = (
            f"Total files: {total}<br>"
            f"Success: {success} &nbsp;&nbsp; Failed: {failed} &nbsp;&nbsp; Skipped: {skipped}<br>"
            f"Parsed: {parsed} &nbsp;&nbsp; Parsed (inferred): {inferred} &nbsp;&nbsp; Fallback: {fallback}<br>"
            f"Total bytes processed: {_format_bytes(total_bytes)}<br>"
            f"{failure_summary}"
        )
        if manifest:
            summary_html += f"<br>Manifest: {manifest}"

        self.summary_label.setText(summary_html)
        self._set_status(f"Conversion complete — {success} success, {failed} failed, {skipped} skipped.")

        if self.execution_log:
            self.log("🏁 Conversion complete.")
            if failure_rows:
                for record in failure_rows[:5]:
                    self.log(
                        f"   ❌ {Path(record.get('input_path', '')).name}: {record.get('message', 'unknown error')}"
                    )
            if summary.get("dry_run"):
                self.log("🧪 Dry run summary only — no files were written.")

        self.worker = None
        self.worker_thread = None

    # ------------------------------------------------------------------
    # Theme
    # ------------------------------------------------------------------

    def _update_convert_button_state(self) -> None:
        has_files = bool(self.csv_files)
        has_column = bool(self._get_active_column())
        if has_files and not has_column:
            self.convert_button.setToolTip("No target column detected. Enable manual override to select one.")
        else:
            self.convert_button.setToolTip("")
        self.convert_button.setEnabled(has_files and has_column and not self.is_converting and not self.is_scanning)

    def _set_status(self, message: str) -> None:
        if self.status_label is not None:
            self.status_label.setText(message)

    def _apply_theme_styles(self) -> None:
        if not getattr(self, "current_theme", None):
            return
        theme = self.current_theme
        theme.apply_to_widget(self.scan_button, "button_secondary")
        theme.apply_to_widget(self.convert_button, "button_primary")
        theme.apply_to_widget(self.status_label, "label")
        theme.apply_to_widget(self.summary_label, "label_muted")
        theme.apply_to_widget(self.column_status_label, "label")
        theme.apply_to_widget(self.scan_stats_label, "label_muted")

        frames = [
            getattr(self, "column_group", None),
        ]
        for widget in frames:
            if isinstance(widget, QFrame):
                theme.apply_to_widget(widget, "frame")

    def refresh_theme(self) -> None:
        super().refresh_theme()
        self._apply_theme_styles()

    def closeEvent(self, event) -> None:  # noqa: N802
        if self.worker and self.worker_thread and self.worker_thread.isRunning():
            self.worker_thread.requestInterruption()
            self.worker_thread.quit()
            self.worker_thread.wait(2000)
        super().closeEvent(event)


DateFormatConverter = DateFormatConverterTool


def main() -> None:
    import sys

    app = QApplication(sys.argv)

    class DummyParent:
        def __init__(self):
            from styles import get_theme_manager

            try:
                theme_manager = get_theme_manager()
                themes = theme_manager.get_available_themes()
                self.current_theme = (
                    theme_manager.load_theme(themes[0]) if themes else None
                )
            except Exception:
                self.current_theme = None

    parent = DummyParent()
    tool = DateFormatConverterTool(
        parent,
        input_path=str(Path.cwd()),
        output_path=str(Path.cwd()),
    )
    tool.show()
    tool.raise_()
    tool.activateWindow()
    sys.exit(app.exec())


if __name__ == "__main__":  # pragma: no cover
    main()

