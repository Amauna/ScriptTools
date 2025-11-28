"""
🌊 Column Order Harmonizer
Reorder CSV columns to match curated presets (with duplicate stripping).
"""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from PySide6.QtCore import Qt, QObject, QThread, Signal
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

from tools.templates import BaseToolDialog, PathConfigMixin


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


@dataclass
class HarmonizerResult:
    success: int = 0
    failed: int = 0
    duplicates_removed: int = 0
    extras_removed: int = 0


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
    ) -> None:
        super().__init__()
        self.files = files
        self.column_sequence = column_sequence
        self.remove_extra_columns = remove_extra_columns
        self.input_path = input_path
        self.output_path = output_path

    def run(self) -> None:
        result = HarmonizerResult()
        total = len(self.files)

        for index, file_path in enumerate(self.files, start=1):
            self.progress_signal.emit(index - 1, total)
            relative_name = file_path.name
            self.status_signal.emit(f"Processing {relative_name}")
            self.log_signal.emit(f"🔄 Reordering columns for {relative_name}")

            try:
                duplicates_removed, extras_removed = self._process_file(file_path)
            except Exception as exc:  # pragma: no cover - runtime safety
                result.failed += 1
                self.log_signal.emit(
                    f"❌ Failed to process {relative_name}: {exc}"
                )
            else:
                result.success += 1
                if duplicates_removed:
                    self.log_signal.emit(
                        f"🧹 Removed {duplicates_removed} duplicate column(s) from {relative_name}"
                    )
                if extras_removed:
                    self.log_signal.emit(
                        f"✂️ Removed {extras_removed} column(s) not listed in preset from {relative_name}"
                    )
                self.log_signal.emit(
                    f"✅ Column order updated for {relative_name}"
                )
                result.duplicates_removed += duplicates_removed
                result.extras_removed += extras_removed

            self.progress_signal.emit(index, total)

        self.finished_signal.emit(result.success, result.failed)

    def _process_file(self, file_path: Path) -> tuple[int, int]:
        with file_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.reader(handle)
            try:
                header = next(reader)
            except StopIteration:
                raise ValueError("Empty file")

            all_rows = [row for row in reader]

        cleaned_header, index_map, duplicates_removed = self._deduplicate_columns(
            header, all_rows
        )
        ordered_header = self._build_header(cleaned_header)

        if not ordered_header:
            raise ValueError(f"No valid columns detected in {file_path.name}")

        rows: List[List[str]] = []
        for row in all_rows:
            row_dict = self._row_to_dict(row, index_map, cleaned_header)
            rows.append([row_dict.get(column, "") for column in ordered_header])

        self.output_path.mkdir(parents=True, exist_ok=True)
        output_file = self.output_path / file_path.name
        with output_file.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(ordered_header)
            writer.writerows(rows)
        extras_removed = len(cleaned_header) - len(ordered_header)
        return duplicates_removed, extras_removed

    @staticmethod
    def _deduplicate_columns(
        header: List[str], rows: List[List[str]]
    ) -> tuple[List[str], List[int], int]:
        cleaned_header: List[str] = []
        index_map: List[int] = []
        seen: Dict[tuple[str, tuple[str, ...]], int] = {}
        duplicates_removed = 0

        for idx, column in enumerate(header):
            normalized = column.strip()
            if not normalized:
                duplicates_removed += 1
                continue

            column_values = tuple(
                row[idx] if idx < len(row) else "" for row in rows
            )
            key = (normalized, column_values)
            if key in seen:
                duplicates_removed += 1
                continue

            seen[key] = idx
            cleaned_header.append(normalized)
            index_map.append(idx)

        return cleaned_header, index_map, duplicates_removed

    def _build_header(self, cleaned_header: List[str]) -> List[str]:
        desired: List[str] = []
        remaining: List[str] = []

        desired_set = set()
        for column in self.column_sequence:
            normalized = column.strip()
            if not normalized:
                continue
            if normalized in cleaned_header and normalized not in desired_set:
                desired.append(normalized)
                desired_set.add(normalized)

        if self.remove_extra_columns:
            return desired

        for column in cleaned_header:
            if column not in desired_set:
                remaining.append(column)
        return desired + remaining

    @staticmethod
    def _row_to_dict(
        row: List[str], index_map: List[int], header: List[str]
    ) -> Dict[str, str]:
        mapping: Dict[str, str] = {}
        for column, source_index in zip(header, index_map):
            value = row[source_index] if source_index < len(row) else ""
            mapping[column] = value
        return mapping


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

        self._custom_presets: Dict[str, List[str]] = {}
        self.remove_extra_columns = False

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
        self._set_status("Ready.")

    def build_path_section(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("pathFrame")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        self.build_path_controls(layout)

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
        self.files_table.setColumnCount(2)
        self.files_table.setHorizontalHeaderLabels(["Filename", "Columns (unique)"])
        header_view = self.files_table.horizontalHeader()
        header_view.setSectionResizeMode(0, QHeaderView.Stretch)
        header_view.setSectionResizeMode(1, QHeaderView.ResizeToContents)
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

    def _update_action_state(self) -> None:
        has_files = bool(getattr(self, "csv_files", []))
        worker_active = self._is_worker_active()

        if hasattr(self, "reorder_btn"):
            self.reorder_btn.setEnabled(has_files and not worker_active)
        if hasattr(self, "scan_btn"):
            self.scan_btn.setEnabled(not worker_active)
        if hasattr(self, "reset_btn"):
            self.reset_btn.setEnabled(not worker_active)

    def reset_tool_state(self) -> None:
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
        self.csv_files.clear()
        self.files_table.setRowCount(0)
        if hasattr(self, "progress_bar"):
            self.progress_bar.setVisible(False)
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
            return

        files = sorted(input_path.glob("*.csv"))
        self.csv_files = files

        if not files:
            self._toggle_files_empty_state(False, "No CSV files found in the selected folder.")
            self._set_status("No CSV files found.")
            if self.execution_log:
                self.log("⚠️ No CSV files detected in the input folder.")
            self._update_action_state()
            return

        self._toggle_files_empty_state(True)

        self.execution_log_messages = []
        for row_index, csv_file in enumerate(files):
            columns = self._peek_columns(csv_file)
            self.files_table.insertRow(row_index)
            self.files_table.setItem(
                row_index,
                0,
                QTableWidgetItem(csv_file.name),
            )
            self.files_table.setItem(
                row_index,
                1,
                QTableWidgetItem(str(columns)),
            )

        self._set_status(f"Found {len(files)} CSV file(s).")
        if self.execution_log:
            self.log(f"📂 Found {len(files)} CSV file(s) in input folder.")
        self._update_action_state()

    @staticmethod
    def _peek_columns(csv_file: Path) -> int:
        try:
            with csv_file.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.reader(handle)
                header = next(reader, [])
                unique = set()
                for column in header:
                    normalized = column.strip()
                    if normalized:
                        unique.add(normalized)
                return len(unique)
        except Exception:
            return 0

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

        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximum(len(self.csv_files))
        self._set_status("Starting column harmonization...")
        self._update_action_state()

        self.worker_thread = QThread()
        self.worker = ColumnOrderWorker(
            files=self.csv_files,
            column_sequence=sequence,
            remove_extra_columns=self.remove_extra_columns,
            input_path=Path(self.input_path),
            output_path=Path(self.output_path),
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
        self.worker = None
        self.worker_thread = None
        self._update_action_state()

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
        try:
            os.startfile(self.output_path)
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
