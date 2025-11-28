"""
🌊 Shared Path Configuration Mixin
Reusable editable input/output path controls with browse + open helpers.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Dict, Any

from PySide6.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QFileDialog,
    QMessageBox,
)
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt


class PathConfigMixin:
    """Mixin providing fully-editable input/output path controls with presets."""

    PATH_CONFIG_DEFAULT: Dict[str, Any] = {
        "show_input": True,
        "show_output": True,
        "include_open_buttons": True,
        "input_label": "📥 Input Folder:",
        "output_label": "📤 Output Folder:",
    }
    PATH_CONFIG: Dict[str, Any] = {}

    _path_input_edit: Optional[QLineEdit] = None
    _path_output_edit: Optional[QLineEdit] = None

    def get_path_config(self) -> Dict[str, Any]:
        config = self.PATH_CONFIG_DEFAULT.copy()
        config.update(getattr(self, "PATH_CONFIG", {}) or {})
        return config

    def build_path_controls(self, parent_layout, **overrides) -> QFrame:
        config = self.get_path_config()
        config.update(overrides)

        frame = QFrame()
        frame.setObjectName("pathFrame")
        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(10, 10, 10, 10)
        frame_layout.setSpacing(8)

        self._path_input_edit = None
        self._path_output_edit = None

        if config.get("show_input", True):
            row, edit = self._create_path_row(
                label_text=config.get("input_label", "📥 Input Folder:"),
                initial_path=self.input_path,
                browse_handler=self.browse_input_folder,
                open_handler=self.open_input_folder if config.get("include_open_buttons", True) else None,
            )
            self._path_input_edit = edit
            frame_layout.addLayout(row)

        if config.get("show_output", True):
            row, edit = self._create_path_row(
                label_text=config.get("output_label", "📤 Output Folder:"),
                initial_path=self.output_path,
                browse_handler=self.browse_output_folder,
                open_handler=self.open_output_folder if config.get("include_open_buttons", True) else None,
            )
            self._path_output_edit = edit
            frame_layout.addLayout(row)

        parent_layout.addWidget(frame)
        self._sync_path_edits(self.input_path, self.output_path)
        return frame

    def _create_path_row(self, *, label_text: str, initial_path: Path, browse_handler, open_handler):
        row = QHBoxLayout()
        row.setSpacing(10)

        label = QLabel(label_text)
        label.setFont(QFont("Arial", 11, QFont.Bold))
        row.addWidget(label)

        edit = QLineEdit(str(initial_path))
        edit.editingFinished.connect(self._on_path_edit_finished)
        row.addWidget(edit, 1)

        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(browse_handler)
        row.addWidget(browse_btn)

        if open_handler is not None:
            open_btn = QPushButton("Open")
            open_btn.clicked.connect(open_handler)
            row.addWidget(open_btn)

        return row, edit

    def browse_input_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Input Folder",
            str(self.input_path),
        )
        if not folder:
            return
        candidate = Path(folder)
        if getattr(self, "path_manager", None):
            self.path_manager.set_input_path(candidate)
        else:
            self.input_path = candidate
            self._sync_path_edits(candidate, self.output_path)
        self._log_path_event(f"📥 Input folder set: {candidate}")

    def browse_output_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Output Folder",
            str(self.output_path),
        )
        if not folder:
            return
        candidate = Path(folder)
        if getattr(self, "path_manager", None):
            self.path_manager.set_output_path(candidate)
        else:
            self.output_path = candidate
            self._sync_path_edits(self.input_path, candidate)
        self._log_path_event(f"📤 Output folder set: {candidate}")

    def open_input_folder(self):
        try:
            import os

            os.startfile(str(self.input_path))
        except Exception as exc:  # pragma: no cover - OS specific
            QMessageBox.warning(
                self,
                "Unable to Open",
                f"Could not open input folder:\n{exc}",
            )

    def open_output_folder(self):
        try:
            import os

            os.startfile(str(self.output_path))
        except Exception as exc:  # pragma: no cover - OS specific
            QMessageBox.warning(
                self,
                "Unable to Open",
                f"Could not open output folder:\n{exc}",
            )

    def _on_path_edit_finished(self):
        sender = self.sender()
        if sender is None:
            return
        text = sender.text().strip()
        if sender is self._path_input_edit:
            self._handle_input_text(text)
        elif sender is self._path_output_edit:
            self._handle_output_text(text)

    def _handle_input_text(self, text: str) -> None:
        if not text:
            self._sync_path_edits(self.input_path, self.output_path)
            return
        candidate = Path(text)
        if not candidate.exists():
            QMessageBox.warning(
                self,
                "Invalid Path",
                f"Input path does not exist:\n{text}",
            )
            self._sync_path_edits(self.input_path, self.output_path)
            return
        if getattr(self, "path_manager", None):
            self.path_manager.set_input_path(candidate)
        else:
            self.input_path = candidate
            self._sync_path_edits(candidate, self.output_path)
        self._log_path_event(f"📥 Input folder set: {candidate}")

    def _handle_output_text(self, text: str) -> None:
        if not text:
            self._sync_path_edits(self.input_path, self.output_path)
            return
        candidate = Path(text)
        if not candidate.exists():
            reply = QMessageBox.question(
                self,
                "Create Folder?",
                f"Output path does not exist. Create it?\n{text}",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply == QMessageBox.Yes:
                try:
                    candidate.mkdir(parents=True, exist_ok=True)
                except Exception as exc:
                    QMessageBox.warning(
                        self,
                        "Unable to Create Folder",
                        f"Could not create folder:\n{exc}",
                    )
                    self._sync_path_edits(self.input_path, self.output_path)
                    return
            else:
                self._sync_path_edits(self.input_path, self.output_path)
                return
        if getattr(self, "path_manager", None):
            self.path_manager.set_output_path(candidate)
        else:
            self.output_path = candidate
            self._sync_path_edits(self.input_path, candidate)
        self._log_path_event(f"📤 Output folder set: {candidate}")

    def _sync_path_edits(self, input_path: Path, output_path: Path) -> None:
        super_sync = getattr(super(), "_sync_path_edits", None)
        if callable(super_sync):
            super_sync(input_path, output_path)
        if self._path_input_edit is not None:
            self._path_input_edit.blockSignals(True)
            self._path_input_edit.setText(str(input_path))
            self._path_input_edit.blockSignals(False)
        if self._path_output_edit is not None:
            self._path_output_edit.blockSignals(True)
            self._path_output_edit.setText(str(output_path))
            self._path_output_edit.blockSignals(False)

    def _log_path_event(self, message: str) -> None:
        logger = getattr(self, "log", None)
        if callable(logger):
            try:
                logger(message)
                return
            except TypeError:
                pass
        execution_log = getattr(self, "execution_log", None)
        if execution_log is not None and hasattr(execution_log, "log"):
            execution_log.log(message)
