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
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import re

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
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QScrollArea,
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
FORMAT_SAMPLE_LIMIT = 3

FORMAT_SPEC_MAP: Dict[str, str] = {
    "%Y": "YYYY",
    "%y": "YY",
    "%m": "MM",
    "%-m": "M",
    "%d": "DD",
    "%-d": "D",
    "%H": "HH",
    "%I": "hh",
    "%M": "mm",
    "%S": "ss",
    "%b": "MMM",
    "%B": "MMMM",
    "%a": "ddd",
    "%A": "dddd",
}

FORMAT_REGEX_PATTERNS: List[Tuple[re.Pattern[str], str]] = [
    (re.compile(r"^\d{4}-\d{2}-\d{2}$"), "YYYY-MM-DD"),
    (re.compile(r"^\d{4}/\d{2}/\d{2}$"), "YYYY/MM/DD"),
    (re.compile(r"^\d{1,2}/\d{1,2}/\d{4}$"), "M/D/YYYY"),
    (re.compile(r"^\d{2}/\d{2}/\d{4}$"), "MM/DD/YYYY"),
    (re.compile(r"^\d{2}/\d{2}/\d{2}$"), "MM/DD/YY"),
    (re.compile(r"^\d{1,2}-[A-Za-z]{3}-\d{2}$"), "D-MMM-YY"),
    (re.compile(r"^\d{2}-[A-Za-z]{3}-\d{2}$"), "DD-MMM-YY"),
    (re.compile(r"^[A-Za-z]{3} \d{1,2}, \d{4}$"), "MMM DD, YYYY"),
    (re.compile(r"^[A-Za-z]{3} \d{1,2} \d{4}$"), "MMM DD YYYY"),
    (re.compile(r"^\d{1,2} [A-Za-z]{3} \d{4}$"), "D MMM YYYY"),
]

FORMAT_PRESETS_INPUT: Tuple[Tuple[str, str], ...] = (
    ("ISO 8601 (YYYY-MM-DD)", "%Y-%m-%d"),
    ("US Slash (MM/DD/YYYY)", "%m/%d/%Y"),
    ("US Slash Short (MM/DD/YY)", "%m/%d/%y"),
    ("Compact (YYYYMMDD)", "%Y%m%d"),
    ("Month Name (MMM DD, YYYY)", "%b %d, %Y"),
    ("Day-Month-Year (DD-MMM-YY)", "%d-%b-%y"),
)

FORMAT_PRESETS_OUTPUT: Tuple[Tuple[str, str], ...] = (
    ("ISO 8601 (YYYY-MM-DD)", "%Y-%m-%d"),
    ("US Slash (MM/DD/YYYY)", "%m/%d/%Y"),
    ("European Dots (DD.MM.YYYY)", "%d.%m.%Y"),
    ("Long Month (MMMM DD, YYYY)", "%B %d, %Y"),
)


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

        self.csv_files_all: List[Path] = []
        self.csv_files_target: List[Path] = []
        self.file_stats: Dict[str, Dict[str, int]] = {}
        self.preview_cache: Dict[str, Tuple[List[str], List[List[str]]]] = {}
        self.file_map: Dict[str, Path] = {}
        self.file_check_state: Dict[str, bool] = {}
        self.column_frequencies: Counter[str] = Counter()
        self.detected_column: Optional[str] = None
        self.total_scan_bytes: int = 0
        self.format_groups: List[Dict[str, Any]] = []
        self.format_default_signature: Optional[str] = None
        self.format_checkbox_map: Dict[str, QCheckBox] = {}
        self.format_lists: Dict[str, QListWidget] = {}
        self.suppress_item_change: bool = False

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

        # Left panel: format tabs
        left_panel = QFrame()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(10, 10, 10, 10)
        left_layout.setSpacing(8)

        formats_label = QLabel("📁 Detected Date Formats")
        formats_label.setFont(QFont("Arial", 12, QFont.Bold))
        left_layout.addWidget(formats_label)

        self.format_tabs = QTabWidget()
        self.format_tabs.setTabBarAutoHide(False)
        self.format_tabs.setUsesScrollButtons(True)
        self.format_tabs.currentChanged.connect(self._on_tab_changed)
        left_layout.addWidget(self.format_tabs)

        splitter.addWidget(left_panel)

        # Right panel: format selection + settings
        right_panel = QFrame()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(10, 10, 10, 10)
        right_layout.setSpacing(10)

        self.format_selection_group = self._build_format_selection_group()
        right_layout.addWidget(self.format_selection_group)
        self._rebuild_format_checkboxes()

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

    def _build_format_selection_group(self) -> QGroupBox:
        group = QGroupBox("🎯 Format Selection")
        layout = QVBoxLayout(group)
        layout.setSpacing(6)

        self.column_status_label = QLabel("Scan a folder to detect date-like columns.")
        self.column_status_label.setWordWrap(True)
        layout.addWidget(self.column_status_label)

        self.scan_stats_label = QLabel("No files scanned yet.")
        self.scan_stats_label.setWordWrap(True)
        layout.addWidget(self.scan_stats_label)

        self.format_summary_label = QLabel("No format groups yet.")
        self.format_summary_label.setWordWrap(True)
        layout.addWidget(self.format_summary_label)

        button_row = QHBoxLayout()
        self.select_all_formats_button = QPushButton("Select All")
        self.select_all_formats_button.setEnabled(False)
        self.select_all_formats_button.clicked.connect(lambda: self._bulk_toggle_formats(True))
        button_row.addWidget(self.select_all_formats_button)

        self.select_none_formats_button = QPushButton("Select None")
        self.select_none_formats_button.setEnabled(False)
        self.select_none_formats_button.clicked.connect(lambda: self._bulk_toggle_formats(False))
        button_row.addStretch()
        button_row.addWidget(self.select_none_formats_button)
        layout.addLayout(button_row)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.format_checkbox_widget = QWidget()
        self.format_checkbox_layout = QVBoxLayout(self.format_checkbox_widget)
        self.format_checkbox_layout.setContentsMargins(0, 0, 0, 0)
        self.format_checkbox_layout.setSpacing(4)
        self.format_checkbox_widget.setMinimumHeight(140)
        scroll_area.setWidget(self.format_checkbox_widget)
        layout.addWidget(scroll_area)

        return group

    def _build_settings_group(self) -> QGroupBox:
        group = QGroupBox("⚙️ Conversion Settings")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        layout.addWidget(QLabel("Input formats (one per line):"))
        self.input_formats_edit = QTextEdit()
        self.input_formats_edit.setPlaceholderText("%Y-%m-%d\n%m/%d/%Y\n%Y%m%d")
        self.input_formats_edit.setPlainText("\n".join(DEFAULT_INPUT_FORMATS))
        self.input_formats_edit.textChanged.connect(self._on_input_formats_changed)
        layout.addWidget(self.input_formats_edit)

        preset_row = QHBoxLayout()
        self.input_format_preset_combo = QComboBox()
        for label, fmt in FORMAT_PRESETS_INPUT:
            self.input_format_preset_combo.addItem(label, fmt)
        preset_row.addWidget(self.input_format_preset_combo)

        insert_button = QPushButton("Insert Preset")
        insert_button.clicked.connect(self._on_add_input_preset)
        preset_row.addWidget(insert_button)
        preset_row.addStretch()
        layout.addLayout(preset_row)

        layout.addWidget(QLabel("Output format:"))
        output_row = QHBoxLayout()
        self.output_format_edit = QLineEdit(DEFAULT_OUTPUT_FORMAT)
        output_row.addWidget(self.output_format_edit)

        self.output_format_combo = QComboBox()
        for label, fmt in FORMAT_PRESETS_OUTPUT:
            self.output_format_combo.addItem(label, fmt)
        self.output_format_combo.currentIndexChanged.connect(self._on_output_preset_changed)
        output_row.addWidget(self.output_format_combo)
        layout.addLayout(output_row)

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
        self.file_map.clear()
        self.column_frequencies.clear()
        self.detected_column = None
        self.total_scan_bytes = 0
        self.format_groups.clear()
        self.format_default_signature = None
        self.format_checkbox_map.clear()
        self.format_lists.clear()
        self.file_check_state.clear()
        self.csv_files_target.clear()

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

        self.csv_files_all = csv_files
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

            self.file_map[str(file_path)] = file_path
            self.file_stats[str(file_path)] = {
                "columns": len(header),
                "rows": row_count,
                "size": size_bytes,
            }

            if self.execution_log and index % 25 == 0:
                self.log(f"…scanned {index}/{len(csv_files)} files")

        self.is_scanning = False
        self.scan_button.setEnabled(True)
        self.detected_column = self._resolve_target_column()
        self._update_column_status_text()
        self._update_format_groups()
        self._update_scan_stats()
        self._update_convert_button_state()
        self._set_status(f"Scan complete — {len(self.csv_files_all)} file(s)")

        if self.execution_log:
            self.log(
                f"✅ Scan complete. Files: {len(self.csv_files_all)}, Columns discovered: {len(self.column_frequencies)}, Total size: {_format_bytes(self.total_scan_bytes)}"
            )

    def _update_scan_stats(self) -> None:
        if not self.csv_files_all:
            self.scan_stats_label.setText("No files scanned.")
            return
        self.scan_stats_label.setText(
            f"Files: {len(self.csv_files_all)}, Total size: {_format_bytes(self.total_scan_bytes)}, Columns discovered: {len(self.column_frequencies)}"
        )

    # ------------------------------------------------------------------
    # Column and format helpers
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
        return self.detected_column

    def _update_column_status_text(self) -> None:
        if not self.column_status_label:
            return

        if not self.csv_files_all:
            self.column_status_label.setText("Scan a folder to detect date-like columns.")
            return

        if self.detected_column:
            freq = self.column_frequencies.get(self.detected_column, 0)
            self.column_status_label.setText(
                f"Auto-detected column: <b>{self.detected_column}</b> (present in {freq} file(s))."
            )
        else:
            self.column_status_label.setText(
                "No date-like column detected. Adjust input formats or rescan."
            )

    # ------------------------------------------------------------------
    # Format grouping
    # ------------------------------------------------------------------

    def _get_input_formats_for_detection(self) -> List[str]:
        text = self.input_formats_edit.toPlainText() if self.input_formats_edit else ""
        formats = [line.strip() for line in text.splitlines() if line.strip()]
        return formats or DEFAULT_INPUT_FORMATS

    def _match_signature(self, value: str, formats: List[str]) -> Optional[str]:
        cleaned = value.strip()
        if not cleaned:
            return None

        for fmt in formats:
            try:
                datetime.strptime(cleaned, fmt)
            except ValueError:
                continue
            return self._strftime_to_signature(fmt)

        for pattern, signature in FORMAT_REGEX_PATTERNS:
            if pattern.match(cleaned):
                return signature

        return None

    def _strftime_to_signature(self, fmt: str) -> str:
        signature_parts: List[str] = []
        i = 0
        length = len(fmt)
        while i < length:
            if fmt[i] == "%":
                token = fmt[i : i + 2]
                replacement = FORMAT_SPEC_MAP.get(token)
                if replacement is None and i + 2 < length and fmt[i + 1] == "-":
                    token = fmt[i : i + 3]
                    replacement = FORMAT_SPEC_MAP.get(token)
                    if replacement is not None:
                        signature_parts.append(replacement)
                        i += 3
                        continue
                if replacement is not None:
                    signature_parts.append(replacement)
                elif i + 1 < length:
                    signature_parts.append(fmt[i + 1])
                i += 2
            else:
                signature_parts.append(fmt[i])
                i += 1
        return "".join(signature_parts).strip()

    def _determine_file_signature(
                self,
        file_path: Path,
        column_name: str,
        formats: List[str],
    ) -> str:
        header, rows = self.preview_cache.get(str(file_path), ([], []))
        if not header or column_name not in header:
            return "Missing Column"

        column_index = header.index(column_name)
        samples: List[str] = []
        for row in rows:
            if column_index >= len(row):
                continue
            value = row[column_index].strip()
            if value:
                samples.append(value)
            if len(samples) >= FORMAT_SAMPLE_LIMIT:
                break

        if not samples:
            return "No Sample"

        signatures = [
            signature
            for signature in (
                self._match_signature(sample, formats) for sample in samples
            )
            if signature
        ]
        if signatures:
            return Counter(signatures).most_common(1)[0][0]
        return "Unknown Format"

    def _update_format_groups(self) -> None:
        if not self.csv_files_all:
            self.format_groups = []
            self.format_default_signature = None
            self.file_check_state.clear()
            self.csv_files_target = []
            self._rebuild_format_checkboxes()
            self._populate_format_tabs()
            self._update_format_summary()
            self._update_convert_button_state()
            return

        column_name = self._get_active_column()
        if not column_name:
            self.format_groups = []
            self.format_default_signature = None
            self.file_check_state.clear()
            self.csv_files_target = []
            self._rebuild_format_checkboxes()
            self._populate_format_tabs()
            self._update_format_summary()
            self._update_convert_button_state()
            return

        formats = self._get_input_formats_for_detection()
        signature_map: Dict[str, List[Path]] = {}
        for file_path in self.csv_files_all:
            signature = self._determine_file_signature(file_path, column_name, formats)
            signature_map.setdefault(signature, []).append(file_path)

        sorted_groups = sorted(
            signature_map.items(),
            key=lambda item: (-len(item[1]), item[0].lower()),
        )
        if not sorted_groups:
            self.format_groups = []
            self.format_default_signature = None
            self.file_check_state.clear()
            self.csv_files_target = []
            self._rebuild_format_checkboxes()
            self._populate_format_tabs()
            self._update_format_summary()
            self._update_convert_button_state()
            return

        default_signature = sorted_groups[0][0]
        self.format_default_signature = default_signature
        self.format_groups = [
            {
                "signature": signature,
                "files": files,
                "is_default": signature == default_signature,
            }
            for signature, files in sorted_groups
        ]

        self.file_check_state = {}
        for group in self.format_groups:
            is_default = group["is_default"]
            default_checked = not is_default or len(self.format_groups) == 1
            for file_path in group["files"]:
                self.file_check_state[str(file_path)] = default_checked

        self._rebuild_format_checkboxes()
        self._populate_format_tabs()
        self._recompute_target_files()
        self._update_format_summary()
        self._update_convert_button_state()

    def _rebuild_format_checkboxes(self) -> None:
        while self.format_checkbox_layout.count():
            item = self.format_checkbox_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self.format_checkbox_map.clear()

        if not self.format_groups:
            placeholder = QLabel("No detected date formats yet. Scan CSV files to populate this list.")
            placeholder.setWordWrap(True)
            placeholder.setAlignment(Qt.AlignTop | Qt.AlignLeft)
            self.format_checkbox_layout.addWidget(placeholder)
        else:
            for group in self.format_groups:
                signature = group["signature"]
                files = group["files"]
                checked_count = sum(
                    1 for path in files if self.file_check_state.get(str(path), False)
                )
                checkbox = QCheckBox(
                    f"{signature} ({len(files)} file{'s' if len(files) != 1 else ''})"
                )
                checkbox.setTristate(True)
                state = Qt.PartiallyChecked
                if checked_count == 0:
                    state = Qt.Unchecked
                elif checked_count == len(files):
                    state = Qt.Checked
                checkbox.setCheckState(state)
                checkbox.stateChanged.connect(
                    lambda state, sig=signature: self._on_format_checkbox_toggled(sig, state)
                )
                self.format_checkbox_layout.addWidget(checkbox)
                self.format_checkbox_map[signature] = checkbox

        self.format_checkbox_layout.addStretch()

        self.select_all_formats_button.setEnabled(True)
        self.select_none_formats_button.setEnabled(True)

    def _on_format_checkbox_toggled(self, signature: str, state: int) -> None:
        if state == Qt.PartiallyChecked:
            return
        include = state == Qt.Checked
        group = next((g for g in self.format_groups if g["signature"] == signature), None)
        if not group:
            return

        self.suppress_item_change = True
        try:
            for file_path in group["files"]:
                key = str(file_path)
                self.file_check_state[key] = include
                list_widget = self.format_lists.get(signature)
                if list_widget is None:
                    continue
                for index in range(list_widget.count()):
                    item = list_widget.item(index)
                    if item.data(Qt.UserRole) == key:
                        item.setCheckState(Qt.Checked if include else Qt.Unchecked)
                        break
        finally:
            self.suppress_item_change = False

        self._recompute_target_files()
        self._update_format_checkbox_state(signature)
        self._update_format_summary()
        self._update_convert_button_state()

    def _bulk_toggle_formats(self, include: bool) -> None:
        if not self.format_groups:
            return

        self.suppress_item_change = True
        try:
            for group in self.format_groups:
                for file_path in group["files"]:
                    key = str(file_path)
                    self.file_check_state[key] = include
                    list_widget = self.format_lists.get(group["signature"])
                    if list_widget is None:
                        continue
                    for index in range(list_widget.count()):
                        item = list_widget.item(index)
                        if item.data(Qt.UserRole) == key:
                            item.setCheckState(Qt.Checked if include else Qt.Unchecked)
            for signature in self.format_lists.keys():
                self._update_format_checkbox_state(signature)
        finally:
            self.suppress_item_change = False

        self._recompute_target_files()
        self._update_format_summary()
        self._update_convert_button_state()

    def _populate_format_tabs(self) -> None:
        self.format_tabs.blockSignals(True)
        self.format_tabs.clear()
        self.format_lists.clear()

        if not self.format_groups:
            self.format_tabs.setTabBarAutoHide(True)
            self.format_tabs.blockSignals(False)
            return

        self.format_tabs.setTabBarAutoHide(len(self.format_groups) <= 1)

        for group in self.format_groups:
            signature = group["signature"]
            files = group["files"]
            list_widget = QListWidget()
            list_widget.setSelectionMode(QListWidget.NoSelection)
            list_widget.itemChanged.connect(self._on_list_item_changed)

            self.suppress_item_change = True
            try:
                for file_path in files:
                    key = str(file_path)
                    item = QListWidgetItem(file_path.name)
                    item.setData(Qt.UserRole, key)
                    item.setData(Qt.UserRole + 1, signature)
                    item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
                    checked = self.file_check_state.get(key, False)
                    item.setCheckState(Qt.Checked if checked else Qt.Unchecked)
                    list_widget.addItem(item)
            finally:
                self.suppress_item_change = False

            tab_label = signature
            if group["is_default"] and len(self.format_groups) > 1:
                tab_label = f"{tab_label} (baseline)"
            self.format_tabs.addTab(list_widget, tab_label)
            self.format_lists[signature] = list_widget

        self.format_tabs.blockSignals(False)

    def _on_tab_changed(self, index: int) -> None:  # noqa: ARG002
        return

    def _on_list_item_changed(self, item: QListWidgetItem) -> None:
        if self.suppress_item_change:
            return
        path_str = item.data(Qt.UserRole)
        signature = item.data(Qt.UserRole + 1)
        if not path_str or not signature:
            return
        self.file_check_state[path_str] = item.checkState() == Qt.Checked
        self._recompute_target_files()
        self._update_format_checkbox_state(signature)
        self._update_format_summary()
        self._update_convert_button_state()

    def _recompute_target_files(self) -> None:
        self.csv_files_target = [
            path for path in self.csv_files_all if self.file_check_state.get(str(path), False)
        ]

    def _update_format_checkbox_state(self, signature: str) -> None:
        checkbox = self.format_checkbox_map.get(signature)
        if checkbox is None:
            return
        group = next((g for g in self.format_groups if g["signature"] == signature), None)
        if not group:
            return

        total = len(group["files"])
        checked = sum(
            1 for path in group["files"] if self.file_check_state.get(str(path), False)
        )
        with QSignalBlocker(checkbox):
            state = Qt.PartiallyChecked
            if checked == 0:
                state = Qt.Unchecked
            elif checked == total:
                state = Qt.Checked
            checkbox.setCheckState(state)

    def _update_format_summary(self) -> None:
        if not self.format_groups:
            self.format_summary_label.setText("No format groups yet.")
            return

        lines: List[str] = []
        for group in self.format_groups:
            total = len(group["files"])
            selected = sum(
                1 for path in group["files"] if self.file_check_state.get(str(path), False)
            )
            prefix = "Baseline" if group["is_default"] else "Variant"
            noun = "file" if total == 1 else "files"
            lines.append(
                f"{prefix}: {group['signature']} ({selected}/{total} {noun} selected)"
            )

        selected_total = len(self.csv_files_target)
        overall_total = len(self.csv_files_all)
        lines.append(f"Selected for conversion: {selected_total}/{overall_total} file(s)")
        self.format_summary_label.setText("<br>".join(lines))

    def _on_input_formats_changed(self) -> None:
        if self.is_scanning or self.is_converting:
            return
        if not self.csv_files_all:
            return
        self._update_format_groups()

    def _on_add_input_preset(self) -> None:
        fmt = self.input_format_preset_combo.currentData()
        if not fmt:
            return
        existing = [line.strip() for line in self.input_formats_edit.toPlainText().splitlines() if line.strip()]
        if fmt not in existing:
            existing.append(fmt)
            self.input_formats_edit.setPlainText("\n".join(existing))

    def _on_output_preset_changed(self, index: int) -> None:  # noqa: ARG002
        fmt = self.output_format_combo.currentData()
        if fmt:
            self.output_format_edit.setText(fmt)

    # ------------------------------------------------------------------
    # Conversion
    # ------------------------------------------------------------------

    def _collect_options(self) -> Optional[ConverterOptions]:
        if not self.csv_files_target:
            QMessageBox.warning(self, "No Files", "Scan CSV files before converting.")
            return None

        target_column = self._get_active_column()
        if not target_column:
            QMessageBox.warning(
                self,
                "No Column Detected",
                "No date-like column detected. Adjust input formats and rescan.",
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
        for path in self.csv_files_target:
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
        self.progress_bar.setMaximum(len(self.csv_files_target))
        self.progress_bar.setValue(0)
        self._set_status(f"Converting {len(self.csv_files_target)} file(s)…")

        self.worker_thread = QThread()
        self.worker = DateConverterWorker(
            files=self.csv_files_target,
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
        total = summary.get("total", len(self.csv_files_target))
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
        has_files = bool(self.csv_files_target)
        has_column = bool(self._get_active_column())
        if has_files and not has_column:
            self.convert_button.setToolTip("No date column detected. Adjust input formats and rescan.")
        elif not has_files:
            self.convert_button.setToolTip("No files selected for conversion. Adjust format filters or rescan.")
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
        theme.apply_to_widget(self.format_summary_label, "label_muted")
        theme.apply_to_widget(self.select_all_formats_button, "button_secondary")
        theme.apply_to_widget(self.select_none_formats_button, "button_secondary")

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

