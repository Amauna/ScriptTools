"""
🌊 BigQuery CSV Cleaner Tool
Clean CSV files for BigQuery compatibility with preview, options, and zero-input-modification.
Specifically handles null values in float/integer columns.
"""

import sys
import csv
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Dict, Optional, Any
from collections import defaultdict

from PySide6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QFileDialog, QTextEdit, QCheckBox,
    QScrollArea, QWidget, QFrame, QMessageBox, QProgressBar, QComboBox,
    QTableWidget, QTableWidgetItem, QGroupBox, QSplitter, QHeaderView
)
from PySide6.QtCore import Qt, Signal, QObject, QThread
from PySide6.QtGui import QFont, QColor

# Import theme system if available
try:
    from styles import get_theme_manager
    THEME_AVAILABLE = True
except Exception:
    THEME_AVAILABLE = False


class CSVAnalysisResult:
    """Result of CSV file analysis"""
    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.headers: List[str] = []
        self.total_rows = 0
        self.column_types: Dict[int, str] = {}  # col_index -> type (float, int, string)
        self.null_positions: Dict[int, List[int]] = {}  # col_index -> list of row indices with nulls
        self.empty_positions: Dict[int, List[int]] = {}  # col_index -> list of row indices with empty strings
        self.error_message: Optional[str] = None

class CSVCleanerWorker(QObject):
    """Worker that analyzes and cleans CSV files in a background thread."""
    log_signal = Signal(str)
    progress_signal = Signal(int, int)
    analysis_signal = Signal(list)  # List[CSVAnalysisResult]
    finished_signal = Signal(int, int)

    def __init__(self, files: List[Path], output_dir: Path, cleaning_options: Dict[str, bool]):
        super().__init__()
        self.files = files
        self.output_dir = output_dir
        self.cleaning_options = cleaning_options  # What cleaning to perform
        self.should_stop = False
        self.execution_log: List[str] = []
        self.analysis_results: List[CSVAnalysisResult] = []

    def _log(self, message: str):
        ts = datetime.now().strftime("%H:%M:%S")
        formatted = f"[{ts}] {message}"
        self.execution_log.append(formatted)
        self.log_signal.emit(message)

    def _save_execution_log(self, success: int, failed: int, duration_s: float):
        try:
            log_file = self.output_dir / "execution_log.txt"
            with open(log_file, "w", encoding="utf-8") as f:
                f.write("=" * 80 + "\n")
                f.write("🌊 FIND & REPLACE TOOL - EXECUTION LOG\n")
                f.write("=" * 80 + "\n\n")
                for entry in self.execution_log:
                    f.write(entry + "\n")

            summary_file = self.output_dir / "replace_summary.txt"
            with open(summary_file, "w", encoding="utf-8") as f:
                f.write("=" * 80 + "\n")
                f.write("🌊 FIND & REPLACE TOOL - SUMMARY REPORT\n")
                f.write("=" * 80 + "\n\n")
                f.write(f"Timestamp: {datetime.now().strftime('%Y%m%d_%H%M%S')}\n")
                f.write(f"Status: {'✅ SUCCESS' if failed == 0 else '⚠️ PARTIAL' if success > 0 else '❌ FAILED'}\n")
                f.write(f"Duration: {duration_s:.2f} seconds\n\n")
                f.write(f"Processed: {success + failed} file(s)\n")
                f.write(f"Modified: {success} file(s)\n")
                f.write(f"Errors: {failed} file(s)\n")
                f.write(f"Output: {self.output_dir}\n")
        except Exception:
            pass

    def _detect_column_type(self, values: List[str]) -> str:
        """Detect if column is float, int, or string"""
        if not values:
            return "string"
        
        float_count = 0
        int_count = 0
        
        for val in values:
            val = val.strip()
            if not val or val.lower() in ['null', 'none', 'n/a', 'na', '']:
                continue
            
            # Try float
            try:
                float(val)
                float_count += 1
                # Check if it's also an integer
                if '.' not in val and 'e' not in val.lower():
                    int_count += 1
            except ValueError:
                pass
        
        # Need at least 50% of non-null values to match type
        non_empty = [v for v in values if v.strip() and v.strip().lower() not in ['null', 'none', 'n/a', 'na', '']]
        total = len(non_empty)
        
        if total == 0:
            return "string"
        
        if int_count / total >= 0.5:
            return "int"
        elif float_count / total >= 0.5:
            return "float"
        else:
            return "string"
    
    def _analyze_csv(self, file_path: Path) -> CSVAnalysisResult:
        """Analyze a CSV file and detect issues"""
        result = CSVAnalysisResult(file_path)
        
        try:
            with open(file_path, 'r', newline='', encoding='utf-8') as f:
                # Detect dialect
                sample = f.read(2048)
                f.seek(0)
                
                try:
                    sniffer = csv.Sniffer()
                    dialect = sniffer.sniff(sample)
                except csv.Error:
                    dialect = csv.excel
                
                reader = csv.reader(f, dialect)
                rows = list(reader)
                
                if not rows:
                    result.error_message = "Empty file"
                    return result
                
                # Get headers
                result.headers = rows[0]
                data_rows = rows[1:]
                result.total_rows = len(data_rows)
                
                if not data_rows:
                    result.error_message = "No data rows"
                    return result
                
                # Analyze each column
                num_cols = len(result.headers)
                for col_idx in range(num_cols):
                    column_values = []
                    for row in data_rows:
                        if col_idx < len(row):
                            column_values.append(row[col_idx])
                        else:
                            column_values.append("")
                    
                    # Detect type
                    result.column_types[col_idx] = self._detect_column_type(column_values)
                    
                    # Find null positions (empty strings, null, etc.)
                    result.null_positions[col_idx] = []
                    result.empty_positions[col_idx] = []
                    
                    for row_idx, val in enumerate(column_values):
                        val_lower = val.strip().lower()
                        if val_lower in ['null', 'none', 'n/a', 'na']:
                            result.null_positions[col_idx].append(row_idx)
                        elif not val.strip():
                            result.empty_positions[col_idx].append(row_idx)
        
        except Exception as e:
            result.error_message = str(e)
        
        return result
    
    def run_analysis(self):
        """First phase: Analyze files and report what will be cleaned"""
        import time
        start = time.time()
        total = len(self.files)
        
        self._log("=" * 60)
        self._log("🔍 ANALYZING CSV FILES FOR BIGQUERY COMPATIBILITY...")
        self._log("=" * 60)
        self._log(f"Files: {total}")
        self._log("")
        
        self.analysis_results = []
        
        for idx, file_path in enumerate(self.files, start=1):
            if self.should_stop:
                self._log("⚠️ Operation cancelled by user")
                break
            
            self._log(f"[{idx}/{total}] Analyzing {file_path.name}...")
            result = self._analyze_csv(file_path)
            
            if result.error_message:
                self._log(f"   ⚠️ {result.error_message}")
            else:
                null_count = sum(len(row_indices) for row_indices in result.null_positions.values())
                empty_count = sum(len(row_indices) for row_indices in result.empty_positions.values())
                self._log(f"   ✓ Rows: {result.total_rows:,}, Columns: {len(result.headers)}")
                self._log(f"   ✓ Null values found: {null_count}, Empty strings: {empty_count}")
                
                # Log column types
                type_summary = defaultdict(int)
                for col_idx, col_type in result.column_types.items():
                    type_summary[col_type] += 1
                type_str = ", ".join([f"{k}: {v}" for k, v in type_summary.items()])
                self._log(f"   ✓ Types: {type_str}")
            
            self.analysis_results.append(result)
            self.progress_signal.emit(idx, total)
        
        self._log("")
        self._log("✅ ANALYSIS COMPLETE!")
        self._log("")
        self._log("📋 Review the preview above and configure cleaning options.")
        self._log("Click 'Apply Cleaning' when ready to process files.")
        
        # Emit results for preview
        self.analysis_signal.emit(self.analysis_results)
    
    def run_cleaning(self):
        """Second phase: Actually clean the files based on options"""
        import time
        start = time.time()
        total = len(self.files)
        success_count = 0
        fail_count = 0
        
        self._log("")
        self._log("=" * 60)
        self._log("🧹 STARTING CSV CLEANING...")
        self._log("=" * 60)
        self._log(f"Files: {total}")
        
        # Log active options
        active_options = [opt for opt, enabled in self.cleaning_options.items() if enabled]
        if active_options:
            self._log(f"Active cleaning: {', '.join(active_options)}")
        else:
            self._log("⚠️ No cleaning options enabled!")
        
        self._log("")
        
        for idx, file_path in enumerate(self.files, start=1):
            if self.should_stop:
                self._log("⚠️ Operation cancelled by user")
                break
            
            try:
                # Find corresponding analysis result
                analysis = None
                for a in self.analysis_results:
                    if a.file_path == file_path:
                        analysis = a
                        break
                
                if not analysis or analysis.error_message:
                    self._log(f"[{idx}/{total}] ⚠️ Skipping {file_path.name}: {analysis.error_message if analysis else 'No analysis'}")
                    continue
                
                # Read and clean
                with open(file_path, 'r', newline='', encoding='utf-8') as f:
                    sample = f.read(2048)
                    f.seek(0)
                    
                    try:
                        sniffer = csv.Sniffer()
                        dialect = sniffer.sniff(sample)
                    except csv.Error:
                        dialect = csv.excel
                    
                    reader = csv.reader(f, dialect)
                    rows = list(reader)
                    
                    if not rows:
                        continue
                    
                    headers = rows[0]
                    data_rows = rows[1:]
                    
                    # Apply cleaning to each cell
                    changes_count = 0
                    for row_idx, row in enumerate(data_rows):
                        for col_idx, val in enumerate(row):
                            if col_idx >= len(headers):
                                continue
                            
                            original_val = val
                            new_val = val
                            
                            # Handle null values in numeric columns
                            if self.cleaning_options.get('handle_null_in_numeric', False):
                                val_lower = val.strip().lower()
                                is_null = val_lower in ['null', 'none', 'n/a', 'na'] or not val.strip()
                                col_type = analysis.column_types.get(col_idx, 'string')
                                
                                if is_null and col_type in ['float', 'int']:
                                    new_val = '0'  # Replace null with 0 for numeric columns
                                    if new_val != original_val:
                                        changes_count += 1
                            
                            # Handle empty strings in all columns
                            if self.cleaning_options.get('handle_empty_strings', False):
                                if not val.strip():
                                    col_type = analysis.column_types.get(col_idx, 'string')
                                    if col_type == 'string':
                                        new_val = ''  # Keep empty for strings (or could set to 'NULL')
                                    else:
                                        new_val = '0'  # Set to 0 for numeric types
                                    if new_val != original_val:
                                        changes_count += 1
                            
                            # Update row
                            if new_val != original_val:
                                row[col_idx] = new_val
                    
                    # Write to output
                    target = self.output_dir / file_path.name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    
                    with open(target, 'w', newline='', encoding='utf-8') as out_f:
                        writer = csv.writer(out_f, dialect=dialect)
                        writer.writerow(headers)
                        writer.writerows(data_rows)
                    
                    if changes_count > 0:
                        self._log(f"[{idx}/{total}] ✅ {file_path.name} → {changes_count} value(s) cleaned")
                        success_count += 1
                    else:
                        self._log(f"[{idx}/{total}] {file_path.name} → No changes needed")
                
            except Exception as e:
                self._log(f"[{idx}/{total}] ❌ Error on {file_path.name}: {e}")
                fail_count += 1
            
            self.progress_signal.emit(idx, total)
        
        self._log("")
        self._log("🎉 CSV CLEANING COMPLETE!")
        self._save_execution_log(success_count, fail_count, time.time() - start)
        self.finished_signal.emit(success_count, fail_count)

    def stop(self):
        self.should_stop = True


class BigQueryCSVCleaner(QDialog):
    """Dialog UI for BigQuery CSV Cleaning tool."""

    def __init__(self, parent=None, input_path: str = None, output_path: str = None):
        super().__init__(parent)

        # Paths
        self.input_path = Path(input_path) if input_path else Path.cwd()
        if output_path:
            self.output_path = Path(output_path)
        else:
            # Default output same as input
            self.output_path = self.input_path

        # Theme
        self.current_theme = None
        if THEME_AVAILABLE and hasattr(parent, 'current_theme') and parent.current_theme:
            self.current_theme = parent.current_theme

        # Worker and state
        self.worker = None
        self.worker_thread = None
        self.is_running = False
        self.analysis_complete = False
        self.analysis_results: List[CSVAnalysisResult] = []

        self._setup_window()
        self._setup_ui()
        self._apply_theme()

    def _setup_window(self):
        self.setWindowTitle("🧹 BigQuery CSV Cleaner")
        self.setGeometry(100, 100, 1200, 850)
        self.setWindowFlags(Qt.Window | Qt.WindowMinMaxButtonsHint | Qt.WindowCloseButtonHint)
        screen_geometry = self.screen().geometry()
        x = (screen_geometry.width() - 1200) // 2
        y = (screen_geometry.height() - 850) // 2
        self.move(x, y)

    def _setup_ui(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(20, 20, 20, 20)
        main.setSpacing(15)

        # Title
        title = QLabel("🧹 BigQuery CSV Cleaner")
        title.setFont(QFont("Arial", 20, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        main.addWidget(title)

        # Input
        in_row = QHBoxLayout()
        in_label = QLabel("Input Folder:")
        in_label.setFont(QFont("Arial", 10, QFont.Bold))
        in_label.setFixedWidth(110)
        self.in_edit = QLineEdit(str(self.input_path))
        in_btn = QPushButton("📂 Browse")
        in_btn.clicked.connect(self._browse_input)
        in_btn.setFixedWidth(100)
        in_row.addWidget(in_label)
        in_row.addWidget(self.in_edit)
        in_row.addWidget(in_btn)
        main.addLayout(in_row)

        # Scan
        scan_row = QHBoxLayout()
        self.scan_btn = QPushButton("🔍 Scan Folder")
        self.scan_btn.clicked.connect(self._scan_folder)
        self.scan_btn.setFixedHeight(40)
        scan_row.addWidget(self.scan_btn)
        main.addLayout(scan_row)

        # Two columns
        columns = QHBoxLayout()
        columns.setSpacing(20)

        # Left: files
        left = QVBoxLayout()
        left.setSpacing(10)

        file_header = QHBoxLayout()
        self.file_count = QLabel("Files: 0")
        self.file_count.setFont(QFont("Arial", 10, QFont.Bold))
        self.sel_all = QPushButton("✅ Select All")
        self.sel_all.clicked.connect(self._select_all)
        self.sel_all.setFixedWidth(120)
        self.sel_all.setEnabled(False)
        self.sel_none = QPushButton("⬜ Select None")
        self.sel_none.clicked.connect(self._select_none)
        self.sel_none.setFixedWidth(120)
        self.sel_none.setEnabled(False)
        file_header.addWidget(self.file_count)
        file_header.addStretch()
        file_header.addWidget(self.sel_all)
        file_header.addWidget(self.sel_none)
        left.addLayout(file_header)

        self.file_scroll = QScrollArea()
        self.file_scroll.setWidgetResizable(True)
        self.file_scroll.setMinimumHeight(280)
        self.file_scroll.setMaximumHeight(380)
        self.file_list_widget = QWidget()
        self.file_list_layout = QVBoxLayout(self.file_list_widget)
        self.file_list_layout.setContentsMargins(10, 10, 10, 10)
        self.file_list_layout.setSpacing(5)
        self.file_list_layout.addStretch()
        self.file_scroll.setWidget(self.file_list_widget)
        left.addWidget(self.file_scroll)

        # Right: options
        right = QVBoxLayout()
        right.setSpacing(12)

        opts_title = QLabel("Replace Options:")
        opts_title.setFont(QFont("Arial", 12, QFont.Bold))
        right.addWidget(opts_title)

        find_row = QHBoxLayout()
        find_label = QLabel("Find:")
        find_label.setFont(QFont("Arial", 10, QFont.Bold))
        find_label.setFixedWidth(100)
        self.find_edit = QLineEdit()
        self.find_edit.setPlaceholderText("Text to find...")
        self.find_edit.textChanged.connect(self._update_run_state)
        find_row.addWidget(find_label)
        find_row.addWidget(self.find_edit)
        right.addLayout(find_row)

        repl_row = QHBoxLayout()
        repl_label = QLabel("Replace with:")
        repl_label.setFont(QFont("Arial", 10, QFont.Bold))
        repl_label.setFixedWidth(100)
        self.repl_edit = QLineEdit()
        self.repl_edit.setPlaceholderText("Replacement text...")
        repl_row.addWidget(repl_label)
        repl_row.addWidget(self.repl_edit)
        right.addLayout(repl_row)

        # Options
        self.chk_match_case = QCheckBox("Match case")
        self.chk_whole_word = QCheckBox("Whole word")
        self.chk_backup = QCheckBox("Create .bak when overwriting")
        right.addWidget(self.chk_match_case)
        right.addWidget(self.chk_whole_word)
        right.addWidget(self.chk_backup)

        # Output
        out_label = QLabel("Output Folder:")
        out_label.setFont(QFont("Arial", 10, QFont.Bold))
        right.addWidget(out_label)
        out_row = QHBoxLayout()
        self.out_edit = QLineEdit(str(self.output_path))
        out_btn = QPushButton("📂 Browse")
        out_btn.clicked.connect(self._browse_output)
        out_btn.setFixedWidth(100)
        out_row.addWidget(self.out_edit)
        out_row.addWidget(out_btn)
        right.addLayout(out_row)

        # Action
        self.run_btn = QPushButton("🚀 Run Find & Replace")
        self.run_btn.clicked.connect(self._run)
        self.run_btn.setFixedHeight(48)
        self.run_btn.setEnabled(False)
        right.addWidget(self.run_btn)

        # Progress
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        right.addWidget(self.progress)

        columns.addLayout(left, 2)
        columns.addLayout(right, 1)
        main.addLayout(columns)

        # Log controls
        log_header = QHBoxLayout()
        log_label = QLabel("📋 Log:")
        log_label.setFont(QFont("Arial", 10, QFont.Bold))
        log_header.addWidget(log_label)
        log_header.addStretch()
        self.btn_copy_log = QPushButton("📋 Copy Log")
        self.btn_copy_log.clicked.connect(self._copy_log)
        self.btn_copy_log.setFixedWidth(110)
        self.btn_clear_log = QPushButton("🗑️ Reset Log")
        self.btn_clear_log.clicked.connect(self._clear_log)
        self.btn_clear_log.setFixedWidth(110)
        self.btn_save_log = QPushButton("💾 Save Log")
        self.btn_save_log.clicked.connect(self._save_log)
        self.btn_save_log.setFixedWidth(110)
        log_header.addWidget(self.btn_copy_log)
        log_header.addWidget(self.btn_clear_log)
        log_header.addWidget(self.btn_save_log)
        main.addLayout(log_header)

        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setMaximumHeight(160)
        main.addWidget(self.log_area)

        # State
        self.scanned_files: List[Path] = []
        self.file_rows: List[Tuple[QCheckBox, QLabel]] = []

    def _apply_theme(self):
        if not THEME_AVAILABLE or not self.current_theme:
            return
        try:
            self.current_theme.apply_to_window(self)
        except Exception:
            pass

    def refresh_theme(self):
        parent = self.parent()
        if THEME_AVAILABLE and hasattr(parent, 'current_theme') and parent.current_theme:
            self.current_theme = parent.current_theme
            self._apply_theme()

    def _log(self, message: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_area.append(f"[{ts}] {message}")

    def _browse_input(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Input Folder", str(self.input_path))
        if folder:
            self.input_path = Path(folder)
            self.in_edit.setText(str(self.input_path))
            self._log(f"📂 Input folder selected: {self.input_path}")

    def _browse_output(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder", str(self.output_path))
        if folder:
            self.output_path = Path(folder)
            self.out_edit.setText(str(self.output_path))
            self._log(f"📂 Output folder selected: {self.output_path}")

    def _scan_folder(self):
        p = Path(self.in_edit.text())
        if not p.exists() or not p.is_dir():
            QMessageBox.warning(self, "Invalid Path", "Input folder does not exist or is not a folder!")
            return
        self._log(f"🔍 Scanning: {p}")
        self.scanned_files.clear()
        while self.file_list_layout.count() > 1:
            item = self.file_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        files = [f for f in p.iterdir() if f.is_file()]
        files.sort(key=lambda x: x.name.lower())
        self.scanned_files = files
        self.file_count.setText(f"Files: {len(files)}")
        for f in files:
            row = QHBoxLayout()
            chk = QCheckBox()
            chk.setChecked(True)
            name = QLabel(f.name)
            row_w = QWidget()
            row_w.setLayout(row)
            row.addWidget(chk)
            row.addWidget(name, 1)
            self.file_list_layout.insertWidget(self.file_list_layout.count() - 1, row_w)
        self.sel_all.setEnabled(len(files) > 0)
        self.sel_none.setEnabled(len(files) > 0)
        self._update_run_state()
        self._log(f"✅ Found {len(files)} file(s)")

    def _selected_files(self) -> List[Path]:
        result: List[Path] = []
        # Iterate children widgets except the final stretch
        for i in range(self.file_list_layout.count() - 1):
            w = self.file_list_layout.itemAt(i).widget()
            if not w:
                continue
            chk = w.findChild(QCheckBox)
            if chk and chk.isChecked():
                # Retrieve file name from label text
                lbl = w.findChild(QLabel)
                if lbl:
                    name = lbl.text()
                    for f in self.scanned_files:
                        if f.name == name:
                            result.append(f)
                            break
        return result

    def _select_all(self):
        for i in range(self.file_list_layout.count() - 1):
            w = self.file_list_layout.itemAt(i).widget()
            if not w:
                continue
            chk = w.findChild(QCheckBox)
            if chk:
                chk.setChecked(True)
        self._update_run_state()
        self._log("✅ Selected all files")

    def _select_none(self):
        for i in range(self.file_list_layout.count() - 1):
            w = self.file_list_layout.itemAt(i).widget()
            if not w:
                continue
            chk = w.findChild(QCheckBox)
            if chk:
                chk.setChecked(False)
        self._update_run_state()
        self._log("⬜ Deselected all files")

    def _update_run_state(self):
        self.run_btn.setEnabled(len(self._selected_files()) > 0 and not self.is_running and bool(self.find_edit.text()))

    def _run(self):
        if self.is_running:
            self._log("⚠️ Operation already running")
            return
        selected = self._selected_files()
        if not selected:
            QMessageBox.warning(self, "No Files", "Please select at least one file.")
            return
        find_text = self.find_edit.text()
        if not find_text:
            QMessageBox.warning(self, "Missing Find Text", "Please enter text to find.")
            return
        replace_text = self.repl_edit.text()

        # Output folder rotation
        current_output = Path(self.out_edit.text())
        default_base = Path.cwd() / "execution test" / "Output"
        if str(current_output).startswith(str(default_base)):
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            new_output = default_base / f"find_replace_{ts}"
            new_output.mkdir(parents=True, exist_ok=True)
            self.output_path = new_output
            self.out_edit.setText(str(self.output_path))
            self._log(f"📁 Created new output folder: {self.output_path}")
        else:
            self.output_path = current_output
            if not self.output_path.exists():
                self.output_path.mkdir(parents=True, exist_ok=True)
                self._log(f"📁 Created output folder: {self.output_path}")

        # Prepare worker with cleaning options
        cleaning_options = {
            'handle_null_in_numeric': True,  # Default for BigQuery compatibility
            'handle_empty_strings': True,
        }
        
        try:
            self.worker = CSVCleanerWorker(
                files=selected,
                output_dir=self.output_path,
                cleaning_options=cleaning_options,
            )
            self.worker_thread = QThread()
            self.worker.moveToThread(self.worker_thread)
            self.worker_thread.started.connect(self.worker.run)
            self.worker.log_signal.connect(self._log)
            self.worker.progress_signal.connect(self._on_progress)
            self.worker.finished_signal.connect(self._on_finished)
            self.worker_thread.finished.connect(self._on_thread_finished)

            # UI state
            self.is_running = True
            self.run_btn.setEnabled(False)
            self.scan_btn.setEnabled(False)
            self.progress.setVisible(True)
            self.progress.setMaximum(len(selected))
            self.progress.setValue(0)

            self.worker_thread.start()
            self._log("✅ Worker started")
        except Exception as e:
            self._log(f"❌ Failed to start: {e}")
            self.is_running = False
            self.run_btn.setEnabled(True)
            self.scan_btn.setEnabled(True)
            self.progress.setVisible(False)

    def _on_progress(self, current: int, total: int):
        self.progress.setValue(current)

    def _on_finished(self, success: int, failed: int):
        sender = self.sender()
        if sender != self.worker:
            self._log("⚠️ Ignoring signal from old worker")
            return
        self.is_running = False
        self.run_btn.setEnabled(True)
        self.scan_btn.setEnabled(True)
        QMessageBox.information(
            self,
            "Replace Complete",
            f"Modified: {success} file(s)\nErrors: {failed} file(s)\nOutput: {self.output_path}",
        )

    def _on_thread_finished(self):
        try:
            self.progress.setVisible(False)
            self.worker = None
            self.worker_thread = None
        except Exception:
            pass

    def _copy_log(self):
        try:
            QApplication.clipboard().setText(self.log_area.toPlainText())
            self._log("📋 Log copied to clipboard!")
        except Exception as e:
            self._log(f"❌ Failed to copy log: {e}")

    def _clear_log(self):
        self.log_area.clear()
        self._log("🗑️ Log cleared!")

    def _save_log(self):
        try:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_name = f"find_replace_log_{ts}.txt"
            filename, _ = QFileDialog.getSaveFileName(self, "Save Log File", default_name, "Text Files (*.txt);;All Files (*)")
            if filename:
                Path(filename).write_text(self.log_area.toPlainText(), encoding="utf-8")
                self._log(f"💾 Log saved: {filename}")
        except Exception as e:
            self._log(f"❌ Failed to save log: {e}")

    def closeEvent(self, event):
        if self.is_running and self.worker:
            reply = QMessageBox.question(
                self, "Confirm Close", "Operation in progress. Close anyway?", QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                event.ignore()
                return
            self.worker.stop()
            if self.worker_thread and self.worker_thread.isRunning():
                self.worker_thread.quit()
                self.worker_thread.wait(2000)
        event.accept()


def main():
    app = QApplication(sys.argv)
    tool = BigQueryCSVCleaner()
    tool.show()
    sys.exit(app.exec())


# Alias for main.py compatibility
FindReplaceTool = BigQueryCSVCleaner

if __name__ == "__main__":
    main()
