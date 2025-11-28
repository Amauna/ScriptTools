"""
🌊 BigQuery Transfer Diagnostics Tool
Scan CSV batches for BigQuery compatibility issues and produce concise reports.
"""

from __future__ import annotations

import csv
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

from PySide6.QtCore import QObject, QThread, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from tools.templates import BaseToolDialog, PathConfigMixin
from styles import get_path_manager


SCHEMA_DEFINITION = [
    ("Website Name", "STRING"),
    ("Event name", "STRING"),
    ("Date", "DATE"),
    ("FullURL", "STRING"),
    ("Country", "STRING"),
    ("Device category", "STRING"),
    ("Session default channel grouping", "STRING"),
    ("Session medium", "STRING"),
    ("Session source", "STRING"),
    ("Session campaign", "STRING"),
    ("Sessions", "INTEGER"),
    ("Event count", "INTEGER"),
    ("Engaged sessions", "INTEGER"),
    ("Engagement rate", "FLOAT"),
    ("Views", "INTEGER"),
    ("Active users", "INTEGER"),
    ("New users", "INTEGER"),
    ("Total users", "INTEGER"),
    ("Total revenue", "INTEGER"),
]

INTEGER_COLUMN_INDICES = [
    idx for idx, (_, column_type) in enumerate(SCHEMA_DEFINITION) if column_type == "INTEGER"
]
FLOAT_COLUMN_INDICES = [
    idx for idx, (_, column_type) in enumerate(SCHEMA_DEFINITION) if column_type == "FLOAT"
]


def _normalize_header(name: str) -> str:
    return name.strip()


# ---------------------------------------------------------------------------
# Diagnostics result models
# ---------------------------------------------------------------------------

@dataclass
class IssueDetail:
    severity: str  # "FATAL" | "WARNING"
    code: str
    message: str
    location: str = "n/a"

    def render(self) -> str:
        return f"[{self.severity}/{self.code}] {self.message} (Location: {self.location})"


@dataclass
class FileDiagnostics:
    file_path: Path
    status: str  # "PASS" | "WARN" | "FAIL"
    issues: List[IssueDetail] = field(default_factory=list)
    encoding_used: Optional[str] = None
    row_count: int = 0
    column_count: int = 0
    elapsed_ms: int = 0

    def key_summary(self) -> str:
        if not self.issues:
            return "No issues detected."
        highlights = []
        for issue in self.issues[:2]:
            highlights.append(f"{issue.severity}: {issue.code}")
        if len(self.issues) > 2:
            highlights.append(f"+{len(self.issues) - 2} more")
        return " | ".join(highlights)


# ---------------------------------------------------------------------------
# Worker thread
# ---------------------------------------------------------------------------

class DiagnosticsWorker(QObject):
    log_signal = Signal(str)
    progress_signal = Signal(int, int)
    status_signal = Signal(str)
    file_result_signal = Signal(object)
    finished_signal = Signal(bool, str)

    def __init__(self, files: List[Path], stop_on_first_fatal: bool) -> None:
        super().__init__()
        self.files = files
        self.stop_on_first_fatal = stop_on_first_fatal
        self.should_stop = False

    def run(self) -> None:
        start_time = datetime.now()
        try:
            total = len(self.files)
            for index, file_path in enumerate(self.files, start=1):
                if self.should_stop:
                    self.finished_signal.emit(False, "Run cancelled by user.")
                    return

                self.progress_signal.emit(index - 1, total)
                self.status_signal.emit(f"Scanning {file_path.name}...")
                result = self._diagnose_file(file_path)
                self.file_result_signal.emit(result)

                if result.status == "FAIL" and self.stop_on_first_fatal:
                    msg = f"Stopped after fatal issue in {file_path.name}."
                    self.finished_signal.emit(
                        True,
                        f"{msg} Duration: {self._format_duration(start_time)}",
                    )
                    return

            self.progress_signal.emit(total, total)
            self.finished_signal.emit(True, f"Diagnostics completed in {self._format_duration(start_time)}.")
        except Exception as exc:  # pragma: no cover - defensive
            trace = traceback.format_exc()
            self.log_signal.emit(f"❌ Unexpected error: {exc}\n{trace}")
            self.finished_signal.emit(False, f"Diagnostics failed: {exc}")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _diagnose_file(self, file_path: Path) -> FileDiagnostics:
        issues: List[IssueDetail] = []
        encoding_used, reader_rows = self._read_csv(file_path, issues)

        if reader_rows is None:
            return FileDiagnostics(
                file_path=file_path,
                status="FAIL",
                issues=issues,
                encoding_used=encoding_used,
            )

        headers, data_rows = reader_rows
        headers = [_normalize_header(header) for header in headers]
        result = FileDiagnostics(
            file_path=file_path,
            status="PASS",
            issues=issues,
            encoding_used=encoding_used,
            row_count=len(data_rows),
            column_count=len(headers),
        )

        if not headers:
            issues.append(
                IssueDetail(
                    severity="FATAL",
                    code="MISSING_HEADER",
                    message="Header row missing or empty.",
                    location="Row 1",
                )
            )
            result.status = "FAIL"
            return result

        self._check_headers(headers, issues)
        self._check_schema(headers, issues)
        self._check_rows(headers, data_rows, issues)
        self._check_types(headers, data_rows, issues)
        self._check_null_density(headers, data_rows, issues)

        if any(issue.severity == "FATAL" for issue in issues):
            result.status = "FAIL"
        elif any(issue.severity == "WARNING" for issue in issues):
            result.status = "WARN"

        return result

    def _read_csv(
        self,
        file_path: Path,
        issues: List[IssueDetail],
    ) -> Tuple[Optional[str], Optional[Tuple[List[str], List[List[str]]]]]:
        encodings = ["utf-8-sig", "utf-8", "latin-1"]
        last_exception: Optional[Exception] = None

        for encoding in encodings:
            try:
                with file_path.open("r", encoding=encoding, newline="") as handle:
                    reader = csv.reader(handle)
                    rows = list(reader)
                if not rows:
                    issues.append(
                        IssueDetail(
                            severity="FATAL",
                            code="EMPTY_FILE",
                            message="File has no rows.",
                        )
                    )
                    return encoding, None
                header = rows[0]
                data_rows = rows[1:]
                if encoding != "utf-8-sig":
                    issues.append(
                        IssueDetail(
                            severity="WARNING",
                            code="NON_UTF8_ENCODING",
                            message=f"File decoded using {encoding}. Consider converting to UTF-8.",
                        )
                    )
                return encoding, (header, data_rows)
            except Exception as exc:
                last_exception = exc

        issues.append(
            IssueDetail(
                severity="FATAL",
                code="UNREADABLE_FILE",
                message=f"Could not decode CSV with common encodings. Last error: {last_exception}",
            )
        )
        return None, None

    def _check_headers(self, headers: List[str], issues: List[IssueDetail]) -> None:
        seen = {}
        for idx, header in enumerate(headers):
            location = f"Column {idx + 1}"
            if not header:
                issues.append(
                    IssueDetail(
                        severity="FATAL",
                        code="BLANK_HEADER",
                        message="Blank column header detected.",
                        location=location,
                    )
                )
                continue

            if header in seen:
                issues.append(
                    IssueDetail(
                        severity="FATAL",
                        code="DUPLICATE_HEADER",
                        message=f'Duplicate header "{header}" found (first at column {seen[header] + 1}).',
                        location=location,
                    )
                )
            else:
                seen[header] = idx

    def _check_schema(self, headers: List[str], issues: List[IssueDetail]) -> None:
        if len(headers) != len(SCHEMA_DEFINITION):
            issues.append(
                IssueDetail(
                    severity="FATAL",
                    code="SCHEMA_LENGTH_MISMATCH",
                    message=f"Header count {len(headers)} does not match expected {len(SCHEMA_DEFINITION)}.",
                    location="Header row",
                )
            )

        expected_names = [name for name, _ in SCHEMA_DEFINITION]
        for idx, expected in enumerate(expected_names):
            actual = headers[idx] if idx < len(headers) else ""
            actual_display = actual if actual else "<missing>"
            if actual != expected:
                issues.append(
                    IssueDetail(
                        severity="FATAL",
                        code="SCHEMA_ORDER_MISMATCH",
                        message=f'Expected "{expected}" at position {idx + 1}, found "{actual_display}".',
                        location=f"Column {idx + 1}",
                    )
                )

    def _check_types(
        self,
        headers: List[str],
        data_rows: List[List[str]],
        issues: List[IssueDetail],
    ) -> None:
        if not data_rows:
            return

        for row_index, row in enumerate(data_rows, start=2):
            # Integer columns must be whole numbers
            for col_idx in INTEGER_COLUMN_INDICES:
                if col_idx >= len(row):
                    continue
                value = row[col_idx].strip()
                if not value:
                    continue
                sanitized = value.replace(",", "")
                if sanitized.startswith(("+", "-")):
                    numeric_part = sanitized[1:]
                else:
                    numeric_part = sanitized
                if numeric_part.isdigit():
                    continue
                try:
                    float_val = float(sanitized)
                except ValueError:
                    float_val = None
                if float_val is not None and float_val.is_integer():
                    issues.append(
                        IssueDetail(
                            severity="FATAL",
                            code="NUMERIC_DECIMAL",
                            message=f'Integer column contains decimal value "{value}".',
                            location=f"Row {row_index}, Column {col_idx + 1} ({headers[col_idx]})",
                        )
                    )
                else:
                    issues.append(
                        IssueDetail(
                            severity="FATAL",
                            code="NUMERIC_PARSE",
                            message=f'Integer column contains non-numeric value "{value}".',
                            location=f"Row {row_index}, Column {col_idx + 1} ({headers[col_idx]})",
                        )
                    )

            # Float columns must be parseable
            for col_idx in FLOAT_COLUMN_INDICES:
                if col_idx >= len(row):
                    continue
                value = row[col_idx].strip()
                if not value:
                    continue
                try:
                    float(value.replace(",", ""))
                except ValueError:
                    issues.append(
                        IssueDetail(
                            severity="FATAL",
                            code="FLOAT_PARSE",
                            message=f'Float column contains non-numeric value "{value}".',
                            location=f"Row {row_index}, Column {col_idx + 1} ({headers[col_idx]})",
                        )
                    )

    def _check_rows(
        self,
        headers: List[str],
        data_rows: List[List[str]],
        issues: List[IssueDetail],
    ) -> None:
        expected_columns = len(headers)
        for row_index, row in enumerate(data_rows, start=2):
            length = len(row)
            if length != expected_columns:
                issues.append(
                    IssueDetail(
                        severity="FATAL",
                        code="COLUMN_COUNT_MISMATCH",
                        message=f"Row has {length} columns; expected {expected_columns}.",
                        location=f"Row {row_index}",
                    )
                )
                continue

            if not any(cell.strip() for cell in row):
                issues.append(
                    IssueDetail(
                        severity="WARNING",
                        code="EMPTY_ROW",
                        message="Row is completely empty.",
                        location=f"Row {row_index}",
                    )
                )

    def _check_null_density(
        self,
        headers: List[str],
        data_rows: List[List[str]],
        issues: List[IssueDetail],
    ) -> None:
        if not data_rows:
            return

        column_null_counts = [0] * len(headers)
        total_rows = len(data_rows)

        for row in data_rows:
            for idx, value in enumerate(row):
                if not value or not value.strip():
                    column_null_counts[idx] += 1

        for idx, header in enumerate(headers):
            null_ratio = column_null_counts[idx] / total_rows
            if null_ratio >= 0.4:
                issues.append(
                    IssueDetail(
                        severity="WARNING",
                        code="COLUMN_NULL_DENSITY",
                        message=f'Column "{header.strip() or header}" contains {null_ratio:.0%} blank/null values.',
                        location=f"Column {idx + 1}",
                    )
                )

    @staticmethod
    def _format_duration(start_time: datetime) -> str:
        delta = datetime.now() - start_time
        minutes, seconds = divmod(delta.total_seconds(), 60)
        return f"{int(minutes):02d}:{int(seconds):02d}"


# ---------------------------------------------------------------------------
# Tool dialog
# ---------------------------------------------------------------------------

class BigQueryTransferDiagnostics(PathConfigMixin, BaseToolDialog):
    """Diagnose CSV batches for BigQuery transfer readiness."""

    PATH_CONFIG = {
        "show_input": True,
        "show_output": True,
        "include_open_buttons": True,
        "input_label": "📥 Input Folder:",
        "output_label": "📤 Output Folder:",
    }

    STATUS_COLORS = {
        "PASS": QBrush(QColor("#2e7d32")),
        "WARN": QBrush(QColor("#f9a825")),
        "FAIL": QBrush(QColor("#c62828")),
    }

    def __init__(self, parent, input_path: str, output_path: str):
        super().__init__(parent, input_path, output_path)

        self.setup_window_properties(
            title="🌊 BigQuery Transfer Diagnostics",
            width=1100,
            height=800,
        )

        self.results: List[FileDiagnostics] = []
        self.worker_thread: Optional[QThread] = None
        self.worker: Optional[DiagnosticsWorker] = None
        self.current_filter: str = "ALL"

        self._setup_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        header = QLabel("🌊 BigQuery Transfer Diagnostics")
        header.setFont(QFont("Arial", 22, QFont.Bold))
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)

        self.build_path_controls(layout)
        layout.addWidget(self._build_controls_section())
        layout.addWidget(self._build_results_table())
        layout.addWidget(self._build_summary_card())

        self.execution_log = self.create_execution_log(layout)
        if self.execution_log:
            self.log("Tool initialized. Ready to analyze CSV batches.")

    def _build_controls_section(self) -> QWidget:
        container = QFrame()
        container.setObjectName("controlFrame")
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(15, 15, 15, 15)
        container_layout.setSpacing(12)

        # Options row
        options_row = QHBoxLayout()
        options_row.setSpacing(12)

        self.stop_on_fatal_checkbox = QCheckBox("Stop after first fatal issue")
        self.stop_on_fatal_checkbox.setChecked(False)
        options_row.addWidget(self.stop_on_fatal_checkbox)
        options_row.addStretch()
        container_layout.addLayout(options_row)

        # Action row
        action_row = QHBoxLayout()
        action_row.setSpacing(12)

        self.run_button = QPushButton("🚀 Run Diagnostics")
        self.run_button.setMinimumHeight(40)
        self.run_button.clicked.connect(self.start_diagnostics)
        action_row.addWidget(self.run_button)

        self.filter_all_btn = QPushButton("All")
        self.filter_all_btn.setCheckable(True)
        self.filter_all_btn.setChecked(True)
        self.filter_all_btn.clicked.connect(lambda: self._apply_filter("ALL"))
        action_row.addWidget(self.filter_all_btn)

        self.filter_warn_btn = QPushButton("Warnings")
        self.filter_warn_btn.setCheckable(True)
        self.filter_warn_btn.clicked.connect(lambda: self._apply_filter("WARN"))
        action_row.addWidget(self.filter_warn_btn)

        self.filter_fail_btn = QPushButton("Failures")
        self.filter_fail_btn.setCheckable(True)
        self.filter_fail_btn.clicked.connect(lambda: self._apply_filter("FAIL"))
        action_row.addWidget(self.filter_fail_btn)

        action_row.addStretch()
        container_layout.addLayout(action_row)

        # Progress row
        progress_row = QVBoxLayout()
        progress_row.setSpacing(6)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        progress_row.addWidget(self.progress_bar)

        self.status_label = QLabel("Ready.")
        self.status_label.setObjectName("statusLabel")
        progress_row.addWidget(self.status_label)

        container_layout.addLayout(progress_row)

        return container

    def _build_results_table(self) -> QWidget:
        frame = QFrame()
        frame.setObjectName("resultsFrame")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        title = QLabel("📄 Diagnostics Results")
        title.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(title)

        self.results_table = QTableWidget(0, 3)
        self.results_table.setHorizontalHeaderLabels(["File", "Status", "Highlights"])
        self.results_table.horizontalHeader().setStretchLastSection(True)
        self.results_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.results_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.results_table.setAlternatingRowColors(True)
        layout.addWidget(self.results_table, 1)

        return frame

    def _build_summary_card(self) -> QWidget:
        frame = QFrame()
        frame.setObjectName("summaryFrame")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(6)

        self.summary_label = QLabel("No diagnostics run yet.")
        self.summary_label.setObjectName("summaryLabel")
        layout.addWidget(self.summary_label)

        return frame

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def start_diagnostics(self) -> None:
        if self.worker_thread and self.worker_thread.isRunning():
            QMessageBox.information(self, "Diagnostics Running", "Please wait for the current run to finish.")
            return

        input_path = Path(self.input_path)
        if not input_path.exists():
            QMessageBox.warning(self, "Input Folder Missing", f"Input path does not exist:\n{input_path}")
            return

        path_info = get_path_manager().prepare_tool_output(
            "BigQuery Transfer Diagnostics",
            script_name=Path(__file__).name,
        )
        run_root = path_info.get("root")
        if run_root is not None:
            self.output_path = run_root
            self._sync_path_edits(Path(self.input_path), run_root)
            if self.execution_log:
                self.log(f"📁 Output run directory: {run_root}")

        files = [
            file_path
            for file_path in sorted(input_path.glob("*.csv"))
            if file_path.is_file()
        ]
        if not files:
            QMessageBox.information(self, "No CSV Files", "No CSV files found in the selected input folder.")
            return

        self.results.clear()
        self._refresh_table()
        self._update_summary()

        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(files))
        self.progress_bar.setValue(0)
        self.status_label.setText("Starting diagnostics...")

        self.run_button.setEnabled(False)
        self.filter_all_btn.setEnabled(False)
        self.filter_warn_btn.setEnabled(False)
        self.filter_fail_btn.setEnabled(False)
        self.stop_on_fatal_checkbox.setEnabled(False)

        self.worker_thread = QThread(self)
        self.worker = DiagnosticsWorker(
            files=files,
            stop_on_first_fatal=self.stop_on_fatal_checkbox.isChecked(),
        )
        self.worker.moveToThread(self.worker_thread)

        self.worker_thread.started.connect(self.worker.run)
        self.worker.log_signal.connect(self.log)
        self.worker.progress_signal.connect(self._update_progress)
        self.worker.status_signal.connect(self._update_status)
        self.worker.file_result_signal.connect(self._handle_file_result)
        self.worker.finished_signal.connect(self._diagnostics_finished)

        self.worker.finished_signal.connect(self.worker_thread.quit)
        self.worker.finished_signal.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)

        if self.execution_log:
            self.log("🚀 Diagnostics started.")

        self.worker_thread.start()

    def _update_progress(self, current: int, total: int) -> None:
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)

    def _update_status(self, message: str) -> None:
        self.status_label.setText(message)
        if self.execution_log:
            self.log(message)

    def _handle_file_result(self, result: FileDiagnostics) -> None:
        self.results.append(result)
        self._refresh_table()
        self._update_summary()

        if self.execution_log:
            prefix = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌"}.get(result.status, "📄")
            self.log(f"{prefix} {result.file_path.name} → {result.status}")
            for issue in result.issues:
                self.log(f"   • {issue.render()}")

    def _diagnostics_finished(self, success: bool, message: str) -> None:
        self.progress_bar.setVisible(False)
        self.status_label.setText(message)
        if self.execution_log:
            self.log(message)

        self._write_report()

        self.run_button.setEnabled(True)
        self.filter_all_btn.setEnabled(True)
        self.filter_warn_btn.setEnabled(True)
        self.filter_fail_btn.setEnabled(True)
        self.stop_on_fatal_checkbox.setEnabled(True)

        self.worker = None
        self.worker_thread = None

    # ------------------------------------------------------------------
    # Table & summaries
    # ------------------------------------------------------------------

    def _refresh_table(self) -> None:
        self.results_table.setRowCount(len(self.results))
        for row, result in enumerate(self.results):
            file_item = QTableWidgetItem(result.file_path.name)
            status_item = QTableWidgetItem(result.status)
            summary_item = QTableWidgetItem(result.key_summary())

            brush = self.STATUS_COLORS.get(result.status)
            if brush:
                status_item.setForeground(brush)

            self.results_table.setItem(row, 0, file_item)
            self.results_table.setItem(row, 1, status_item)
            self.results_table.setItem(row, 2, summary_item)

        self._apply_filter(self.current_filter, update_buttons=False)

    def _apply_filter(self, filter_key: str, update_buttons: bool = True) -> None:
        self.current_filter = filter_key
        for row, result in enumerate(self.results):
            show = (
                filter_key == "ALL"
                or (filter_key == "WARN" and result.status == "WARN")
                or (filter_key == "FAIL" and result.status == "FAIL")
            )
            self.results_table.setRowHidden(row, not show)

        if update_buttons:
            self.filter_all_btn.setChecked(filter_key == "ALL")
            self.filter_warn_btn.setChecked(filter_key == "WARN")
            self.filter_fail_btn.setChecked(filter_key == "FAIL")

    def _update_summary(self) -> None:
        total = len(self.results)
        fail = sum(1 for r in self.results if r.status == "FAIL")
        warn = sum(1 for r in self.results if r.status == "WARN")
        passed = sum(1 for r in self.results if r.status == "PASS")

        self.summary_label.setText(
            f"Files scanned: {total} | Fail: {fail} | Warn: {warn} | Pass: {passed}"
        )

    # ------------------------------------------------------------------
    # Report generation
    # ------------------------------------------------------------------

    def _write_report(self) -> None:
        if not self.results:
            return

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        report_lines = [
            f"# BigQuery Diagnostics — {timestamp}",
            self.summary_label.text(),
            "",
        ]

        for result in self.results:
            report_lines.append(f"{result.status} | {result.file_path.name}")
            if not result.issues:
                report_lines.append("    - No issues detected.")
            else:
                for issue in result.issues:
                    report_lines.append(f"    - {issue.render()}")
            report_lines.append("")

        report_path = Path(self.output_path) / "diagnostic_report.txt"
        try:
            with report_path.open("w", encoding="utf-8") as handle:
                handle.write("\n".join(report_lines))
            if self.execution_log:
                self.log(f"📝 Report saved to {report_path}")
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Unable to Save Report",
                f"Could not write diagnostic report:\n{exc}",
            )
            if self.execution_log:
                self.log(f"❌ Failed to save report: {exc}")


# ---------------------------------------------------------------------------
# Standalone execution
# ---------------------------------------------------------------------------

def main() -> None:  # pragma: no cover - manual testing helper
    import sys
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    class DummyParent:
        def __init__(self):
            try:
                from styles import get_theme_manager

                theme_manager = get_theme_manager()
                themes = theme_manager.get_available_themes()
                self.current_theme = theme_manager.load_theme(themes[0]) if themes else None
            except Exception:
                self.current_theme = None

    from styles import get_path_manager

    parent = DummyParent()
    path_manager = get_path_manager()
    tool = BigQueryTransferDiagnostics(
        parent,
        str(path_manager.get_input_path()),
        str(path_manager.get_output_path()),
    )
    tool.show()
    tool.raise_()
    tool.activateWindow()
    sys.exit(app.exec())


if __name__ == "__main__":  # pragma: no cover - manual execution
    main()

