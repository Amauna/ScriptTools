"""
🌊 YouTube Channel Folder Renamer
-----------------------------------
PySide6 GUI that reuses the existing folder-scanning + CSV renaming logic,
bringing the tool into the Script Tools suite with consistent path controls,
selection summaries, and threaded processing.
"""

from __future__ import annotations

import os
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import Qt, QObject, QThread, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QLabel,
    QComboBox,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QProgressBar,
    QMessageBox,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QFrame,
    QAbstractItemView,
    QHeaderView,
    QSizePolicy,
)

from tools.templates import BaseToolDialog, PathConfigMixin


def _sanitize_channel_name(name: str) -> str:
    cleaned = re.sub(r'[\\/:*?"<>|]', "_", name).strip()
    return cleaned or "channel"


@dataclass
class FolderInfo:
    original_name: str
    channel_name: str
    original_path: Path
    target_file: Optional[str] = None
    target_file_path: Optional[Path] = None
    status_message: str = "Waiting for file"
    tree_item: Optional[QTreeWidgetItem] = field(default=None, compare=False)


class YouTubeRenamerWorker(QObject):
    progress_signal = Signal(int, int)
    status_signal = Signal(object, str, bool)
    finished_signal = Signal(int, int)

    def __init__(self, targets: List[FolderInfo], output_dir: Path) -> None:
        super().__init__()
        self.targets = targets
        self.output_dir = output_dir

    def run(self) -> None:
        total = len(self.targets)
        success_count = 0
        fail_count = 0

        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            for folder in self.targets:
                self.status_signal.emit(folder, f"Error creating output dir: {exc}", False)
            self.finished_signal.emit(success_count, total)
            return

        for index, folder in enumerate(self.targets, start=1):
            target_name = folder.target_file
            target_path = folder.target_file_path
            if not target_name or not target_path or not target_path.exists():
                self.status_signal.emit(folder, "File missing before copy", False)
                fail_count += 1
                self.progress_signal.emit(index, total)
                continue

            sanitized = _sanitize_channel_name(folder.channel_name or folder.original_name)
            destination = self.output_dir / f"{sanitized}.csv"

            try:
                shutil.copy2(target_path, destination)
                self.status_signal.emit(folder, "Completed", True)
                success_count += 1
            except Exception as exc:
                self.status_signal.emit(folder, f"Error: {exc}", False)
                fail_count += 1

            self.progress_signal.emit(index, total)

        self.finished_signal.emit(success_count, fail_count)


class YouTubeChannelFolderRenamerTool(PathConfigMixin, BaseToolDialog):
    """PySide6 replacement for the old Tkinter YouTube folder renamer."""

    PATH_CONFIG = {
        "show_input": True,
        "show_output": True,
        "include_open_buttons": True,
        "input_label": "📥 Source Folder:",
        "output_label": "📤 Output Folder:",
    }

    def __init__(self, parent=None, input_path: str = None, output_path: str = None):
        super().__init__(parent, input_path, output_path)

        self.folders_to_process: List[FolderInfo] = []
        self.active_file_name: Optional[str] = None
        self.worker: Optional[YouTubeRenamerWorker] = None
        self.worker_thread: Optional[QThread] = None

        self.setWindowTitle("📺 YouTube Channel Folder Renamer")
        self.setMinimumSize(1100, 720)

        self.setup_ui()
        self.apply_theme()
        self.log("🧭 YouTube Channel Folder Renamer ready.")

    def setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(14)
        main_layout.setContentsMargins(14, 14, 14, 14)

        title = QLabel("YouTube Channel Folder Renamer")
        title.setFont(QFont("Arial", 20, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)

        self.build_path_controls(
            main_layout,
            show_input=True,
            show_output=True,
            include_open_buttons=True,
            input_label="📥 Source Folder:",
            output_label="📤 Output Folder:",
        )

        control_row = QHBoxLayout()
        control_row.setSpacing(12)

        self.scan_btn = QPushButton("🔍 Scan Folders")
        self.scan_btn.clicked.connect(self.scan_folders)
        self.scan_btn.setFixedHeight(38)
        control_row.addWidget(self.scan_btn)

        file_type_label = QLabel("File to Rename:")
        file_type_label.setFont(QFont("Arial", 10, QFont.Bold))
        control_row.addWidget(file_type_label)

        self.file_type_combo = QComboBox()
        self.file_type_combo.setEnabled(False)
        self.file_type_combo.currentIndexChanged.connect(self.on_file_type_selected)
        control_row.addWidget(self.file_type_combo, 1)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        control_row.addWidget(spacer)

        main_layout.addLayout(control_row)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(
            ["Original Folder", "Channel Name", "File to Rename", "Status"]
        )
        self.tree.setRootIsDecorated(False)
        self.tree.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.tree.setAlternatingRowColors(True)
        header = self.tree.header()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        main_layout.addWidget(self.tree, stretch=1)

        selection_row = QHBoxLayout()
        self.select_all_btn = QPushButton("Select All")
        self.select_all_btn.setEnabled(False)
        self.select_all_btn.clicked.connect(lambda: self.tree.selectAll())
        selection_row.addWidget(self.select_all_btn)

        self.select_none_btn = QPushButton("Select None")
        self.select_none_btn.setEnabled(False)
        self.select_none_btn.clicked.connect(lambda: self.tree.clearSelection())
        selection_row.addWidget(self.select_none_btn)

        selection_row.addStretch()

        self.process_btn = QPushButton("➡️ Process Selected Folders")
        self.process_btn.setEnabled(False)
        self.process_btn.clicked.connect(self.process_folders)
        self.process_btn.setFixedHeight(40)
        selection_row.addWidget(self.process_btn)

        main_layout.addLayout(selection_row)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)

        self.status_label = QLabel("Ready.")
        main_layout.addWidget(self.status_label)

        self.execution_log = self.create_execution_log(main_layout)

    # ------------------------------------------------------------------
    # Scanning helpers
    # ------------------------------------------------------------------

    def scan_folders(self) -> None:
        source = Path(self.input_path)
        if not source.exists():
            QMessageBox.warning(self, "Source Missing", "Please select a valid source folder.")
            return

        self.tree.clear()
        self.folders_to_process.clear()
        self.file_type_combo.clear()
        self.file_type_combo.setEnabled(False)
        self.active_file_name = None
        self.select_all_btn.setEnabled(False)
        self.select_none_btn.setEnabled(False)
        self.process_btn.setEnabled(False)

        for entry in sorted(source.iterdir()):
            if not entry.is_dir():
                continue
            folder_name = entry.name
            channel_name = self._extract_channel_name(folder_name)
            folder_info = FolderInfo(
                original_name=folder_name,
                channel_name=channel_name,
                original_path=entry,
            )

            item = QTreeWidgetItem(
                [folder_name, channel_name, "Select a file to rename...", folder_info.status_message]
            )
            item.setData(0, Qt.UserRole, folder_info)
            folder_info.tree_item = item
            self.tree.addTopLevelItem(item)
            self.folders_to_process.append(folder_info)

        if not self.folders_to_process:
            self.status_label.setText("No folders found in the source directory.")
            QMessageBox.information(self, "Scan Result", "No folders were found in the selected source.")
            return

        self.status_label.setText(f"Scanned {len(self.folders_to_process)} folders.")
        self.select_all_btn.setEnabled(True)
        self.select_none_btn.setEnabled(True)
        self.populate_file_types()
        self.process_btn.setEnabled(False)
        self.log(f"Scanned {len(self.folders_to_process)} folders from {source}")

    def _extract_channel_name(self, folder_name: str) -> str:
        pattern = r"Content \d{4}-\d{2}-\d{2}_\d{4}-\d{2}-\d{2} (.+)"
        match = re.match(pattern, folder_name)
        if match:
            return match.group(1).strip()
        return folder_name

    def populate_file_types(self) -> None:
        csv_files = set()
        for folder in self.folders_to_process:
            try:
                for entry in folder.original_path.iterdir():
                    if entry.is_file() and entry.suffix.lower() == ".csv":
                        csv_files.add(entry.name)
            except PermissionError:
                continue

        if not csv_files:
            self.file_type_combo.clear()
            self.file_type_combo.setEnabled(False)
            self.status_label.setText("No CSV files found inside scanned folders.")
            QMessageBox.warning(self, "No CSV Files", "Could not locate any CSV files inside the scanned folders.")
            return

        sorted_files = sorted(csv_files)
        self.file_type_combo.clear()
        self.file_type_combo.addItem("Select a file to rename...", "")
        for name in sorted_files:
            self.file_type_combo.addItem(name, name)
        self.file_type_combo.setCurrentIndex(0)
        self.file_type_combo.setEnabled(True)
        self.status_label.setText("Select a file type to refresh folder state.")
        self.log(f"Discovered {len(sorted_files)} unique CSV file types.")

    def on_file_type_selected(self, index: int) -> None:
        file_name = self.file_type_combo.currentData()
        self.active_file_name = file_name if file_name else None
        if not file_name:
            self._update_file_columns(None)
            self.process_btn.setEnabled(False)
            return

        self._update_file_columns(file_name)
        matches = sum(1 for f in self.folders_to_process if f.target_file_path)
        self.status_label.setText(f"File '{file_name}' found in {matches}/{len(self.folders_to_process)} folders.")
        self.process_btn.setEnabled(bool(matches))

    def _update_file_columns(self, file_name: Optional[str]) -> None:
        for folder in self.folders_to_process:
            item = folder.tree_item
            if file_name:
                candidate = folder.original_path / file_name
                if candidate.exists():
                    folder.target_file = file_name
                    folder.target_file_path = candidate
                    folder.status_message = "File ready"
                    item.setText(2, f"✓ {file_name}")
                    item.setText(3, folder.status_message)
                else:
                    folder.target_file = None
                    folder.target_file_path = None
                    folder.status_message = "File missing"
                    item.setText(2, f"✗ {file_name} (not found)")
                    item.setText(3, folder.status_message)
            else:
                folder.target_file = None
                folder.target_file_path = None
                folder.status_message = "Awaiting selection"
                item.setText(2, "Select a file to rename...")
                item.setText(3, folder.status_message)
        self.tree.repaint()

    # ------------------------------------------------------------------
    # Processing
    # ------------------------------------------------------------------

    def process_folders(self) -> None:
        if not self.active_file_name:
            QMessageBox.warning(self, "No file selected", "Please select a file to rename first.")
            return

        output_path = Path(self.output_path)
        if not output_path.exists():
            try:
                output_path.mkdir(parents=True, exist_ok=True)
            except Exception as exc:
                QMessageBox.warning(self, "Output Error", f"Unable to create output folder: {exc}")
                return

        selected_items = self.tree.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No folders selected", "Select folders to process first.")
            return

        targets: List[FolderInfo] = []
        for item in selected_items:
            folder: FolderInfo = item.data(0, Qt.UserRole)
            if folder and folder.target_file_path:
                targets.append(folder)
            else:
                QMessageBox.warning(
                    self,
                    "Missing File",
                    f"Folder '{folder.original_name}' does not contain '{self.active_file_name}'.",
                )

        if not targets:
            return

        if not QMessageBox.question(
            self,
            "Confirm",
            f"Process {len(targets)} folder(s) and copy '{self.active_file_name}' to the output?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        ) == QMessageBox.Yes:
            return

        self._start_worker(targets, output_path)

    def _start_worker(self, targets: List[FolderInfo], output_path: Path) -> None:
        self.process_btn.setEnabled(False)
        self.scan_btn.setEnabled(False)
        self.select_all_btn.setEnabled(False)
        self.select_none_btn.setEnabled(False)
        self.file_type_combo.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(targets))
        self.progress_bar.setValue(0)
        self.status_label.setText("Processing folders...")

        self.worker_thread = QThread()
        self.worker = YouTubeRenamerWorker(targets, output_path)
        self.worker.moveToThread(self.worker_thread)

        self.worker_thread.started.connect(self.worker.run)
        self.worker.progress_signal.connect(self._on_worker_progress)
        self.worker.status_signal.connect(self._on_worker_status)
        self.worker.finished_signal.connect(self._on_worker_finished)
        self.worker.finished_signal.connect(self.worker_thread.quit)
        self.worker_thread.finished.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)

        self.worker_thread.start()
        self.log(f"Started processing {len(targets)} folders into {output_path}")

    def _on_worker_progress(self, current: int, total: int) -> None:
        self.progress_bar.setMaximum(max(total, 1))
        self.progress_bar.setValue(current)

    def _on_worker_status(self, folder: FolderInfo, message: str, success: bool) -> None:
        folder.status_message = message
        if folder.tree_item:
            folder.tree_item.setText(3, message)
        self.log(f"{folder.original_name}: {message}")

    def _on_worker_finished(self, success: int, failure: int) -> None:
        self.progress_bar.setVisible(False)
        self.scan_btn.setEnabled(True)
        self.file_type_combo.setEnabled(True)
        self.select_all_btn.setEnabled(True)
        self.select_none_btn.setEnabled(True)
        self.process_btn.setEnabled(True)
        summary = f"Completed: {success}, Failed: {failure}"
        self.status_label.setText(summary)
        QMessageBox.information(self, "Processing Complete", summary)
        self.log(f"Processing complete — {summary}")

        self.worker = None
        self.worker_thread = None


YouTubeChannelFolderRenamer = YouTubeChannelFolderRenamerTool

