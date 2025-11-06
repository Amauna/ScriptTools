"""
🌊 Metric Field Fixer Tool
Fix blank/empty/null values in numeric/metric columns by replacing them with 0
Clean your CSV files with beautiful preview and safe application
"""

import sys
import csv
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple, Optional, Set
from collections import defaultdict

from PySide6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFileDialog, QTextEdit, QCheckBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QScrollArea, QWidget, QFrame,
    QMessageBox, QProgressBar, QGroupBox, QSplitter, QLineEdit
)
from PySide6.QtCore import Qt, Signal, QObject, QThread
from PySide6.QtGui import QFont, QColor

# Import base template for automatic theme support
from tools.templates.base_tool_template import BaseToolDialog


class MetricAnalysisResult:
    """Result of CSV file analysis for metric fields"""
    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.headers: List[str] = []
        self.total_rows = 0
        self.numeric_columns: Dict[int, str] = {}  # col_index -> column_name
        self.percentage_columns: Set[int] = set()  # col_index -> True if percentage column
        self.issues: Dict[int, List[Tuple[int, str]]] = {}  # col_index -> [(row_idx, value), ...]
        self.issue_count = 0
        self.error_message: Optional[str] = None


class MetricFixerWorker(QObject):
    """Worker that scans and fixes CSV files in a background thread"""
    log_signal = Signal(str)
    progress_signal = Signal(int, int)  # current, total
    scan_complete_signal = Signal(list)  # List[MetricAnalysisResult]
    fix_complete_signal = Signal(int, int)  # success, failed
    
    def __init__(self, files: List[Path], output_dir: Path, selected_columns: Dict[Path, Set[int]]):
        super().__init__()
        self.files = files
        self.output_dir = output_dir
        self.selected_columns = selected_columns  # file -> set of column indices to fix
        self.should_stop = False
        self.execution_log: List[str] = []
        self.scan_results: List[MetricAnalysisResult] = []
    
    def _log(self, message: str):
        """Log message with timestamp"""
        ts = datetime.now().strftime("%H:%M:%S")
        formatted = f"[{ts}] {message}"
        self.execution_log.append(formatted)
        self.log_signal.emit(message)
    
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
    
    def _is_invalid_value(self, value: str) -> bool:
        """Check if value is invalid (blank, empty, null, etc.)"""
        if not value:
            return True
        value_lower = value.strip().lower()
        invalid_values = ['', 'null', 'none', 'n/a', 'na', 'nil', '-', '—', 'nan']
        return value_lower in invalid_values
    
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
    
    def _detect_percentage_column(self, column_name: str, column_values: List[str]) -> bool:
        """Detect if column is a percentage column (0-1 range or name suggests percentage)"""
        if not column_values:
            return False
        
        # Check column name for percentage indicators
        column_lower = column_name.lower()
        name_indicators = ['rate', 'percentage', 'percent', 'engagement', '%', 'ratio', 'pct']
        if any(indicator in column_lower for indicator in name_indicators):
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
        """Scan CSV files for metric field issues"""
        import time
        start = time.time()
        total = len(self.files)
        
        self._log("=" * 60)
        self._log("🔍 SCANNING CSV FILES FOR METRIC FIELD ISSUES...")
        self._log("=" * 60)
        self._log(f"Files to scan: {total}")
        self._log("")
        
        self.scan_results = []
        
        for idx, file_path in enumerate(self.files):
            if self.should_stop:
                break
            
            self.progress_signal.emit(idx + 1, total)
            self._log(f"[{idx + 1}/{total}] Scanning: {file_path.name}")
            
            result = self._analyze_csv(file_path)
            if result.error_message:
                self._log(f"   ❌ Error: {result.error_message}")
            else:
                self._log(f"   ✓ Found {len(result.numeric_columns)} numeric column(s)")
                self._log(f"   ✓ Found {result.issue_count} issue(s) to fix")
            self.scan_results.append(result)
        
        duration = time.time() - start
        self._log("")
        self._log(f"✅ Scan complete! ({duration:.2f}s)")
        self._log(f"📊 Total files scanned: {len(self.scan_results)}")
        
        self.scan_complete_signal.emit(self.scan_results)
    
    def _analyze_csv(self, file_path: Path) -> MetricAnalysisResult:
        """Analyze a CSV file for metric field issues"""
        result = MetricAnalysisResult(file_path)
        
        try:
            with open(file_path, 'r', newline='', encoding='utf-8') as f:
                # Detect CSV dialect
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
                    if col_idx >= len(result.headers):
                        continue
                    
                    column_name = result.headers[col_idx]
                    column_values = []
                    
                    # Collect all values for this column
                    for row in data_rows:
                        if col_idx < len(row):
                            column_values.append(row[col_idx])
                        else:
                            column_values.append("")
                    
                    # Check if column is numeric
                    if self._detect_numeric_column(column_values):
                        result.numeric_columns[col_idx] = column_name
                        
                        # Check if it's a percentage column
                        if self._detect_percentage_column(column_name, column_values):
                            result.percentage_columns.add(col_idx)
                        
                        # Find invalid values
                        issues = []
                        for row_idx, val in enumerate(column_values):
                            if self._is_invalid_value(val):
                                issues.append((row_idx, val))
                        
                        if issues:
                            result.issues[col_idx] = issues
                            result.issue_count += len(issues)
        
        except Exception as e:
            result.error_message = str(e)
        
        return result
    
    def fix_files(self):
        """Fix selected metric fields in CSV files"""
        import time
        start = time.time()
        
        self._log("=" * 60)
        self._log("🔧 FIXING METRIC FIELDS...")
        self._log("=" * 60)
        
        success = 0
        failed = 0
        
        for idx, result in enumerate(self.scan_results):
            if self.should_stop:
                break
            
            file_path = result.file_path
            
            # Check if this file has selected columns to fix
            if file_path not in self.selected_columns:
                continue
            
            selected_cols = self.selected_columns[file_path]
            if not selected_cols:
                continue
            
            self.progress_signal.emit(idx + 1, len(self.scan_results))
            self._log(f"[{idx + 1}/{len(self.scan_results)}] Fixing: {file_path.name}")
            
            try:
                # Read CSV
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
                
                # Fix selected columns
                fixed_count = 0
                for col_idx in selected_cols:
                    is_percentage = col_idx in result.percentage_columns
                    
                    if col_idx in result.issues:
                        # Fix blank/null values first
                        # Determine replacement value: "0.00" for percentage columns, "0" for regular numeric
                        replacement_value = "0.00" if is_percentage else "0"
                        
                        for row_idx, _ in result.issues[col_idx]:
                            # row_idx is 0-indexed from data_rows (after header)
                            # So rows[row_idx + 1] is the actual row (rows[0] is header)
                            if row_idx + 1 < len(rows):
                                actual_row = rows[row_idx + 1]
                                if col_idx < len(actual_row):
                                    actual_row[col_idx] = replacement_value
                                    fixed_count += 1
                    
                    # Convert percentage columns from 0-1 range to 0-100 range (multiply by 100)
                    if is_percentage:
                        # Process all rows (skip header)
                        for row_idx in range(1, len(rows)):
                            if row_idx < len(rows) and col_idx < len(rows[row_idx]):
                                current_value = rows[row_idx][col_idx].strip()
                                
                                # Skip if empty or already processed as blank
                                if not current_value or current_value.lower() in ['null', 'none', 'n/a', 'na', 'nil', '-', '—', 'nan']:
                                    continue
                                
                                # Try to convert and multiply by 100
                                try:
                                    num_value = float(current_value)
                                    # Only convert values in 0-1 range (decimal format)
                                    # If value > 1.1, assume it's already in 0-100 format
                                    if 0 <= num_value <= 1.1:
                                        # Convert from 0-1 to 0-100 range and format as float with 2 decimals
                                        converted_value = num_value * 100
                                        rows[row_idx][col_idx] = f"{converted_value:.2f}"
                                        fixed_count += 1
                                    elif num_value > 1.1:
                                        # Already in 0-100 format, just ensure it's formatted as float with 2 decimals
                                        rows[row_idx][col_idx] = f"{num_value:.2f}"
                                        fixed_count += 1
                                except (ValueError, AttributeError):
                                    # If conversion fails, skip this value
                                    continue
                
                # Write fixed CSV
                output_file = self.output_dir / file_path.name
                with open(output_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f, dialect)
                    writer.writerows(rows)
                
                # Log what was done
                percentage_cols = [col_idx for col_idx in selected_cols if col_idx in result.percentage_columns]
                if percentage_cols:
                    self._log(f"   ✅ Fixed {fixed_count} value(s) in {file_path.name}")
                    self._log(f"   📊 Converted percentage columns from 0-1 to 0-100 format (floats with 2 decimals)")
                else:
                    self._log(f"   ✅ Fixed {fixed_count} value(s) in {file_path.name}")
                success += 1
                
            except Exception as e:
                self._log(f"   ❌ Error fixing {file_path.name}: {e}")
                failed += 1
        
        duration = time.time() - start
        self._log("")
        self._log(f"✅ Fix complete! ({duration:.2f}s)")
        self._log(f"📊 Success: {success}, Failed: {failed}")
        
        self.fix_complete_signal.emit(success, failed)


class MetricFixerTool(BaseToolDialog):
    """
    🌊 Metric Field Fixer Tool
    Fix blank/empty/null values in numeric/metric columns
    """
    
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
        self.scan_results: List[MetricAnalysisResult] = []
        self.selected_columns: Dict[Path, Set[int]] = {}  # file -> set of column indices
        self.worker = None
        self.worker_thread = None
        self.is_scanning = False
        self.is_fixing = False
        
        # Setup UI
        self.setup_ui()
        
        # Initial log
        if self.execution_log:
            self.execution_log.log("🌊 Metric Field Fixer initialized!")
            self.execution_log.log("Ready to scan and fix metric fields!")
    
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
        
        # ===== INPUT SECTION =====
        input_frame = QFrame()
        input_layout = QHBoxLayout(input_frame)
        input_layout.setContentsMargins(10, 10, 10, 10)
        
        input_label = QLabel("📂 Input Folder:")
        input_label.setFont(QFont("Arial", 11, QFont.Bold))
        input_label.setFixedWidth(120)
        
        self.input_edit = QLineEdit(str(self.input_path))
        self.input_edit.setReadOnly(True)
        
        browse_btn = QPushButton("📂 Browse")
        browse_btn.clicked.connect(self.browse_input)
        browse_btn.setFixedWidth(100)
        
        input_layout.addWidget(input_label)
        input_layout.addWidget(self.input_edit)
        input_layout.addWidget(browse_btn)
        
        main_layout.addWidget(input_frame)
        
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
        
        action_layout.addStretch()
        
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
        self.column_scroll = QScrollArea()
        self.column_scroll.setWidgetResizable(True)
        self.column_widget = QWidget()
        self.column_layout = QVBoxLayout(self.column_widget)
        self.column_layout.setContentsMargins(5, 5, 5, 5)
        self.column_scroll.setWidget(self.column_widget)
        left_layout.addWidget(self.column_scroll)
        
        splitter.addWidget(left_widget)
        
        # Right: Preview Table
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(10, 10, 10, 10)
        
        right_title = QLabel("👁️ Preview (First 20 Rows)")
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
    
    def browse_input(self):
        """Browse for input folder"""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Input Folder",
            str(self.input_path)
        )
        
        if folder:
            self.input_path = Path(folder)
            self.input_edit.setText(str(self.input_path))
            if self.execution_log:
                self.execution_log.log(f"📂 Input folder: {self.input_path}")
    
    def start_scan(self):
        """Start scanning CSV files"""
        if self.is_scanning or self.is_fixing:
            return
        
        # Find CSV files
        csv_files = list(self.input_path.glob("*.csv"))
        
        if not csv_files:
            QMessageBox.warning(
                self,
                "No Files",
                f"No CSV files found in:\n{self.input_path}"
            )
            return
        
        # Clear previous results
        self.scan_results = []
        self.selected_columns = {}
        self._clear_column_list()
        self._clear_preview()
        
        # Start worker
        self.is_scanning = True
        self.scan_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setMaximum(len(csv_files))
        self.progress.setValue(0)
        
        self.worker = MetricFixerWorker(
            files=csv_files,
            output_dir=self.output_path,
            selected_columns={}
        )
        
        self.worker_thread = QThread()
        self.worker.moveToThread(self.worker_thread)
        
        self.worker_thread.started.connect(self.worker.scan_files)
        self.worker.log_signal.connect(self._log)
        self.worker.progress_signal.connect(self._on_scan_progress)
        self.worker.scan_complete_signal.connect(self._on_scan_complete)
        
        self.worker_thread.start()
        
        if self.execution_log:
            self.execution_log.log(f"🔍 Scanning {len(csv_files)} CSV file(s)...")
    
    def _on_scan_progress(self, current: int, total: int):
        """Update scan progress"""
        self.progress.setValue(current)
    
    def _on_scan_complete(self, results: List[MetricAnalysisResult]):
        """Handle scan completion"""
        self.scan_results = results
        self.is_scanning = False
        self.scan_btn.setEnabled(True)
        self.progress.setVisible(False)
        
        # Update UI
        self._update_column_list()
        self._update_preview()
        
        if self.execution_log:
            total_issues = sum(r.issue_count for r in results)
            self.execution_log.log(f"✅ Scan complete! Found {total_issues} issue(s) to fix")
        
        # Enable selection if we have results
        if results:
            self.select_all_btn.setEnabled(True)
            self.select_none_btn.setEnabled(True)
            self.apply_btn.setEnabled(True)
    
    def _update_column_list(self):
        """Update the column selection list - ONLY show columns with issues!"""
        self._clear_column_list()
        
        if not self.scan_results:
            return
        
        # Group by file
        has_any_columns = False
        for result in self.scan_results:
            # Only show columns that have ACTUAL issues (not 0 issues)
            columns_with_issues = {
                col_idx: col_name 
                for col_idx, col_name in result.numeric_columns.items()
                if col_idx in result.issues and len(result.issues[col_idx]) > 0
            }
            
            if not columns_with_issues:
                continue  # Skip files with no issues
            
            has_any_columns = True
            
            # File header
            file_label = QLabel(f"📄 {result.file_path.name}")
            file_label.setFont(QFont("Arial", 11, QFont.Bold))
            self.column_layout.addWidget(file_label)
            
            # Initialize selection for this file
            if result.file_path not in self.selected_columns:
                self.selected_columns[result.file_path] = set()
            
            # Column checkboxes - ONLY for columns with issues!
            for col_idx, col_name in columns_with_issues.items():
                issue_count = len(result.issues[col_idx])
                
                # Add "%" indicator for percentage columns
                is_percentage = col_idx in result.percentage_columns
                percentage_indicator = " %" if is_percentage else ""
                
                checkbox = QCheckBox(f"{col_name}{percentage_indicator} ({issue_count} issues)")
                checkbox.setChecked(True)  # Select all by default
                checkbox.stateChanged.connect(
                    lambda state, f=result.file_path, c=col_idx: self._on_column_toggle(f, c, state)
                )
                
                self.column_layout.addWidget(checkbox)
                
                # Add to selected if checked
                if checkbox.isChecked():
                    self.selected_columns[result.file_path].add(col_idx)
            
            # Spacer
            spacer = QWidget()
            spacer.setFixedHeight(10)
            self.column_layout.addWidget(spacer)
        
        # Show message if no issues found
        if not has_any_columns:
            no_issues_label = QLabel("✅ No issues found! All metric columns are clean.")
            no_issues_label.setFont(QFont("Arial", 12))
            no_issues_label.setAlignment(Qt.AlignCenter)
            no_issues_label.setStyleSheet("color: #4CAF50; font-weight: bold; padding: 20px;")
            self.column_layout.addWidget(no_issues_label)
        
        self.column_layout.addStretch()
    
    def _clear_column_list(self):
        """Clear the column selection list"""
        while self.column_layout.count():
            item = self.column_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
    
    def _on_column_toggle(self, file_path: Path, col_idx: int, state: int):
        """Handle column checkbox toggle"""
        if file_path not in self.selected_columns:
            self.selected_columns[file_path] = set()
        
        if state == Qt.Checked:
            self.selected_columns[file_path].add(col_idx)
        else:
            self.selected_columns[file_path].discard(col_idx)
        
        # Update apply button state
        has_selections = any(cols for cols in self.selected_columns.values())
        self.apply_btn.setEnabled(has_selections and not self.is_scanning)
        
        # Update preview
        self._update_preview()
    
    def select_all_columns(self):
        """Select all columns (only those with issues)"""
        for result in self.scan_results:
            if result.file_path not in self.selected_columns:
                self.selected_columns[result.file_path] = set()
            
            # Only select columns that have issues
            for col_idx in result.numeric_columns.keys():
                if col_idx in result.issues and len(result.issues[col_idx]) > 0:
                    self.selected_columns[result.file_path].add(col_idx)
        
        # Update checkboxes
        for i in range(self.column_layout.count()):
            item = self.column_layout.itemAt(i)
            if item and item.widget() and isinstance(item.widget(), QCheckBox):
                item.widget().setChecked(True)
        
        self.apply_btn.setEnabled(True)
        self._update_preview()
    
    def select_none_columns(self):
        """Deselect all columns"""
        for file_path in list(self.selected_columns.keys()):
            self.selected_columns[file_path].clear()
        
        # Update checkboxes
        for i in range(self.column_layout.count()):
            item = self.column_layout.itemAt(i)
            if item and item.widget() and isinstance(item.widget(), QCheckBox):
                item.widget().setChecked(False)
        
        self.apply_btn.setEnabled(False)
        self._clear_preview()
    
    def _clear_preview(self):
        """Clear preview table"""
        self.preview_table.setRowCount(0)
        self.preview_table.setColumnCount(0)
    
    def _update_preview(self):
        """Update preview table with first file's data (limited to 20 rows)"""
        self._clear_preview()
        
        if not self.scan_results:
            return
        
        # Find first file with selected columns
        preview_result = None
        for result in self.scan_results:
            if result.file_path in self.selected_columns:
                selected_cols = self.selected_columns[result.file_path]
                if selected_cols:
                    preview_result = result
                    break
        
        if not preview_result:
            return
        
        try:
            # Read CSV file
            with open(preview_result.file_path, 'r', newline='', encoding='utf-8') as f:
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
                return
            
            headers = rows[0]
            data_rows = rows[1:]
            
            # Limit to 20 rows for preview
            preview_rows = data_rows[:20]
            
            # Setup table
            self.preview_table.setColumnCount(len(headers))
            self.preview_table.setHorizontalHeaderLabels(headers)
            self.preview_table.setRowCount(len(preview_rows))
            
            # Get selected columns for this file
            selected_cols = self.selected_columns[preview_result.file_path]
            
            # Fill table
            for row_idx, row_data in enumerate(preview_rows):
                for col_idx, header in enumerate(headers):
                    value = row_data[col_idx] if col_idx < len(row_data) else ""
                    item = QTableWidgetItem(value)
                    
                    is_percentage = col_idx in preview_result.percentage_columns
                    
                    # Highlight if this column is selected and has issues
                    if col_idx in selected_cols and col_idx in preview_result.issues:
                        # Check if this row has an issue in this column
                        issue_rows = {r for r, _ in preview_result.issues[col_idx]}
                        if row_idx in issue_rows:
                            item.setBackground(QColor(255, 200, 200))  # Light red for issues
                            # Show replacement value: "0.00" for percentage columns, "0" for regular numeric
                            replacement = "0.00" if is_percentage else "0"
                            item.setText(f"{value} → {replacement}")  # Show what will be fixed
                    # Show conversion preview for percentage columns (even if no issues)
                    elif col_idx in selected_cols and is_percentage:
                        # Show what the value will be converted to (0-1 → 0-100)
                        try:
                            num_value = float(value) if value.strip() else 0
                            if 0 <= num_value <= 1.1:
                                converted = num_value * 100
                                item.setBackground(QColor(200, 255, 200))  # Light green for conversion
                                item.setText(f"{value} → {converted:.2f}")
                            elif num_value > 1.1:
                                # Already in 0-100 format, just format it
                                item.setBackground(QColor(200, 255, 200))  # Light green for formatting
                                item.setText(f"{value} → {num_value:.2f}")
                        except (ValueError, AttributeError):
                            pass
                    
                    self.preview_table.setItem(row_idx, col_idx, item)
            
            # Resize columns
            self.preview_table.resizeColumnsToContents()
            
        except Exception as e:
            if self.execution_log:
                self.execution_log.log(f"⚠️ Error updating preview: {e}")
    
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
        
        # Confirm
        reply = QMessageBox.question(
            self,
            "Confirm Fix",
            "This will create fixed CSV files in the output folder.\n\nContinue?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # Create output folder
        self.output_path.mkdir(parents=True, exist_ok=True)
        
        # Start worker
        self.is_fixing = True
        self.apply_btn.setEnabled(False)
        self.scan_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setMaximum(len(self.scan_results))
        self.progress.setValue(0)
        
        self.worker = MetricFixerWorker(
            files=[r.file_path for r in self.scan_results],
            output_dir=self.output_path,
            selected_columns=self.selected_columns
        )
        
        self.worker_thread = QThread()
        self.worker.moveToThread(self.worker_thread)
        
        self.worker_thread.started.connect(self.worker.fix_files)
        self.worker.log_signal.connect(self._log)
        self.worker.progress_signal.connect(self._on_fix_progress)
        self.worker.fix_complete_signal.connect(self._on_fix_complete)
        
        self.worker_thread.start()
        
        if self.execution_log:
            self.execution_log.log("🔧 Starting to fix metric fields...")
    
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
            self.execution_log.log(f"✅ Fix complete! Success: {success}, Failed: {failed}")
        
        QMessageBox.information(
            self,
            "Fix Complete",
            f"Fixed {success} file(s) successfully!\n\nOutput: {self.output_path}"
        )
    
    def _log(self, message: str):
        """Log message to execution log"""
        if self.execution_log:
            self.execution_log.log(message)
    
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
    tool = MetricFixerTool(
        parent,
        str(Path.home() / "Documents"),
        str(Path.cwd() / "Output")
    )
    
    tool.show()
    tool.raise_()
    tool.activateWindow()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

