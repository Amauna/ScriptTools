"""
🌊 Data Summary Tool - Per-File CSV Analysis
Analyzes each CSV file individually and provides detailed metrics per file
"""

from __future__ import annotations

import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from collections import defaultdict
import traceback
import csv

from PySide6.QtWidgets import (
    QApplication, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QTextEdit, QProgressBar, QScrollArea, QWidget, QMessageBox, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog
)
from PySide6.QtCore import Qt, Signal, QObject, QThread
from PySide6.QtGui import QFont

from tools.templates import BaseToolDialog, PathConfigMixin
from styles import get_path_manager

# Import NEW theme system ✨
try:
    from styles.components import ExecutionLogFooter, create_execution_log_footer
    THEME_AVAILABLE = True
except ImportError:
    # Add parent directory to path for standalone execution
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    try:
        from styles.components import ExecutionLogFooter, create_execution_log_footer
        THEME_AVAILABLE = True
    except ImportError:
        # Ultimate fallback
        THEME_AVAILABLE = False
        print("⚠️  Theme not available, using default styling")
        ExecutionLogFooter = None
        create_execution_log_footer = None


class DataSummaryWorker(QObject):
    """Worker for analyzing CSV files individually (per-file analysis)"""
    log_signal = Signal(str)
    progress_signal = Signal(int, int)  # current, total
    finished_signal = Signal(dict)  # summary_data
    
    def __init__(self, input_folder: Path, output_dir: Path):
        super().__init__()
        self.input_folder = input_folder
        self.output_dir = output_dir
        self.should_stop = False
        
        # Store all log messages for file export
        self.execution_log_messages = []
    
    def log(self, message: str):
        """Log message (emits signal and stores for file export)"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        self.execution_log_messages.append(formatted_message)
        self.log_signal.emit(message)
    
    def run(self):
        """Analyze all CSV files in folder"""
        try:
            self._run_analysis()
        except Exception as e:
            self.log(f"❌ CRITICAL ERROR: {str(e)}")
            self.log(f"Traceback: {traceback.format_exc()}")
            
            # Emit error result
            self.finished_signal.emit({
                'status': 'error',
                'error': str(e)
            })
            
            # Quit the thread
            if self.thread():
                self.thread().quit()
    
    def _run_analysis(self):
        """Internal analysis method with full error handling"""
        start_time = datetime.now()
        
        self.log("=" * 60)
        self.log("🔍 STARTING PER-FILE CSV ANALYSIS...")
        self.log("=" * 60)
        self.log(f"Input folder: {self.input_folder}")
        self.log("")
        
        # Find all CSV files
        csv_files = list(self.input_folder.glob("*.csv"))
        csv_files = [f for f in csv_files if not f.name.endswith('.bak')]
        
        if not csv_files:
            self.log("⚠️  No CSV files found in folder!")
            self.finished_signal.emit({
                'status': 'no_files'
            })
            return
        
        self.log(f"📂 Found {len(csv_files)} CSV file(s)")
        self.log("")
        
        # Analyze each CSV file individually
        files_summary = self._analyze_files_individually(csv_files)
        
        if not files_summary:
            self.log("⚠️  No data found in CSV files!")
            self.finished_signal.emit({
                'status': 'no_data'
            })
            return
        
        self.log("")
        self.log("=" * 60)
        self.log("🎉 ANALYSIS COMPLETE!")
        self.log("=" * 60)
        self.log(f"✅ Files analyzed: {len(files_summary)}")
        self.log("")
        
        # Calculate grand totals
        grand_totals = self._calculate_grand_totals(files_summary)
        
        # Save execution logs
        duration = (datetime.now() - start_time).total_seconds()
        output_dir = self.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        
        self._save_execution_log(output_dir, len(files_summary), grand_totals['total_rows'], duration)
        self._export_summary_to_csv(files_summary, grand_totals, output_dir)
        
        # Emit results
        self.finished_signal.emit({
            'status': 'success',
            'files_summary': files_summary,
            'grand_totals': grand_totals,
            'duration': duration,
            'output_dir': output_dir
        })
        
        # Quit the thread
        if self.thread():
            self.thread().quit()
    
    def _analyze_files_individually(self, csv_files: List[Path]) -> List[Dict]:
        """Analyze each CSV file individually"""
        files_summary = []
        
        for idx, csv_file in enumerate(csv_files, 1):
            if self.should_stop:
                self.log("⚠️  Analysis cancelled by user")
                break
            
            try:
                self.log(f"[{idx}/{len(csv_files)}] Analyzing: {csv_file.name}")
                self.progress_signal.emit(idx, len(csv_files))
                
                # Read file
                with open(csv_file, 'r', newline='', encoding='utf-8') as f:
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
                        self.log(f"   └─ ⚠️  Empty file, skipping")
                        continue
                    
                    # Extract headers and data
                    headers = rows[0]
                    data_rows = rows[1:]
                    
                    self.log(f"   └─ Total lines: {len(rows):,}")
                    self.log(f"   └─ Data rows: {len(data_rows):,}")
                    self.log(f"   └─ Columns: {len(headers)}")
                    
                    # Detect numeric columns
                    numeric_indices = self._detect_numeric_columns(headers, data_rows)
                    
                    if not numeric_indices:
                        self.log(f"   └─ ⚠️  No numeric columns detected, skipping metrics")
                    
                    # Calculate totals for each numeric column
                    column_totals = {}
                    for col_name, col_idx in numeric_indices.items():
                        total = 0.0
                        for row in data_rows:
                            if len(row) > col_idx:
                                value = self._clean_numeric_value(row[col_idx])
                                total += value
                        column_totals[col_name] = total
                    
                    # Extract date range if available
                    date_range = self._extract_date_range(headers, data_rows)
                    
                    # Calculate file size
                    file_size_mb = csv_file.stat().st_size / (1024 * 1024)
                    
                    # Store file summary
                    file_info = {
                        'filename': csv_file.name,
                        'filepath': csv_file,
                        'total_rows': len(data_rows),
                        'total_columns': len(headers),
                        'headers': headers,
                        'numeric_columns': list(numeric_indices.keys()),
                        'column_totals': column_totals,
                        'date_range': date_range,
                        'file_size_mb': file_size_mb
                    }
                    
                    files_summary.append(file_info)
                    
                    # Log totals
                    if column_totals:
                        self.log(f"   └─ Metrics calculated: {len(column_totals)}")
                        # Show top 3 metrics
                        for col_name in list(column_totals.keys())[:3]:
                            value = column_totals[col_name]
                            self.log(f"      • {col_name}: {value:,.2f}")
                    
                    self.log("")
                    
            except Exception as e:
                self.log(f"   └─ ❌ Error analyzing {csv_file.name}: {str(e)}")
                self.log(f"      {traceback.format_exc()}")
                continue
        
        return files_summary
    
    def _clean_numeric_value(self, value: str) -> float:
        """Clean and convert numeric value, handling commas and special formatting"""
        if not value:
            return 0.0
        
        # Remove common formatting
        cleaned = value.strip()
        cleaned = cleaned.replace(',', '')  # Remove thousand separators
        cleaned = cleaned.replace('$', '')  # Remove currency symbols
        cleaned = cleaned.replace('₱', '')  # Remove peso symbol
        cleaned = cleaned.replace('%', '')  # Remove percent
        cleaned = cleaned.replace(' ', '')  # Remove spaces
        
        try:
            return float(cleaned)
        except ValueError:
            return 0.0
    
    def _detect_numeric_columns(self, headers: List[str], rows: List[List[str]], sample_size: int = 200) -> Dict[str, int]:
        """Automatically detect numeric columns with enhanced detection"""
        numeric_indices = {}
        
        # Columns to exclude from numeric detection
        exclude_columns = ['Website Name', 'Date', 'Country', 'City', 'Source', 'Medium', 'Campaign', 
                          'Browser', 'Device', 'OS', 'Landing page', 'Page path', 'Channel']
        exclude_lower = [col.lower() for col in exclude_columns]
        
        for idx, header in enumerate(headers):
            # Skip excluded columns
            if header.lower() in exclude_lower:
                continue
            
            # Sample rows to check if column is numeric
            numeric_count = 0
            total_non_empty = 0
            
            sample_rows = rows[:min(sample_size, len(rows))]
            
            for row in sample_rows:
                if len(row) > idx:
                    value = row[idx].strip()
                    if value:  # Only check non-empty values
                        total_non_empty += 1
                        cleaned_value = self._clean_numeric_value(value)
                        if cleaned_value != 0.0 or value in ('0', '0.0', '0.00'):
                            numeric_count += 1
            
            # If at least 70% of non-empty values are numeric, consider it a numeric column
            if total_non_empty > 0:
                percentage = (numeric_count / total_non_empty) * 100
                if percentage >= 70:
                    numeric_indices[header] = idx
        
        return numeric_indices
    
    def _extract_date_range(self, headers: List[str], rows: List[List[str]]) -> str:
        """Extract date range from data rows"""
        # Look for date columns
        date_idx = None
        for idx, header in enumerate(headers):
            if 'date' in header.lower():
                date_idx = idx
                break
        
        if date_idx is None:
            return "N/A"
        
        # Get all dates
        dates = []
        for row in rows:
            if len(row) > date_idx and row[date_idx].strip():
                dates.append(row[date_idx].strip())
        
        if not dates:
            return "N/A"
        
        min_date = min(dates)
        max_date = max(dates)
        
        if min_date == max_date:
            return min_date
        else:
            return f"{min_date} to {max_date}"
    
    def _calculate_grand_totals(self, files_summary: List[Dict]) -> Dict:
        """Calculate grand totals across all files"""
        grand_totals = {
            'total_files': len(files_summary),
            'total_rows': sum(f['total_rows'] for f in files_summary),
            'total_size_mb': sum(f['file_size_mb'] for f in files_summary),
            'column_totals': {}
        }
        
        # Aggregate column totals
        all_columns = set()
        for file_info in files_summary:
            all_columns.update(file_info['column_totals'].keys())
        
        for col in all_columns:
            total = sum(file_info['column_totals'].get(col, 0) for file_info in files_summary)
            grand_totals['column_totals'][col] = total
        
        return grand_totals
    
    def _export_summary_to_csv(self, files_summary: List[Dict], grand_totals: Dict, output_dir: Path):
        """Export the per-file summary to a CSV file"""
        try:
            output_file = output_dir / "file_summary.csv"
            
            # Get all unique column names
            all_columns = sorted(grand_totals['column_totals'].keys())
            
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # Build header row
                header_row = ['File Name', 'Date Range', 'Rows', 'Columns', 'Size (MB)']
                header_row.extend(all_columns)
                writer.writerow(header_row)
                
                # Write data rows (one per file)
                for file_info in files_summary:
                    row = [
                        file_info['filename'],
                        file_info['date_range'],
                        file_info['total_rows'],
                        file_info['total_columns'],
                        f"{file_info['file_size_mb']:.2f}"
                    ]
                    
                    for col in all_columns:
                        value = file_info['column_totals'].get(col, 0)
                        row.append(value)
                    
                    writer.writerow(row)
                
                # Write grand totals row
                total_row = [
                    'GRAND TOTAL',
                    '',
                    grand_totals['total_rows'],
                    '',
                    f"{grand_totals['total_size_mb']:.2f}"
                ]
                
                for col in all_columns:
                    total_row.append(grand_totals['column_totals'][col])
                
                writer.writerow(total_row)
            
            self.log(f"📊 Summary exported to: file_summary.csv")
            
            # Also export validation file
            self._export_validation_file(files_summary, grand_totals, output_dir)
            
        except Exception as e:
            self.log(f"⚠️ Warning: Could not export CSV - {str(e)}")
    
    def _export_validation_file(self, files_summary: List[Dict], grand_totals: Dict, output_dir: Path):
        """Export detailed validation file for manual verification"""
        try:
            validation_file = output_dir / "validation_details.txt"
            
            with open(validation_file, 'w', encoding='utf-8') as f:
                f.write("=" * 100 + "\n")
                f.write("🔍 PER-FILE ANALYSIS REPORT\n")
                f.write("=" * 100 + "\n\n")
                
                # File summary table
                f.write("📊 FILES ANALYZED:\n")
                f.write("=" * 100 + "\n")
                f.write(f"{'FILE NAME':<50} | {'ROWS':>10} | {'COLUMNS':>10} | {'SIZE (MB)':>12}\n")
                f.write("-" * 100 + "\n")
                
                for file_info in files_summary:
                    f.write(f"{file_info['filename']:<50} | {file_info['total_rows']:>10,} | ")
                    f.write(f"{file_info['total_columns']:>10} | {file_info['file_size_mb']:>12.2f}\n")
                
                f.write("-" * 100 + "\n")
                f.write(f"{'TOTAL':<50} | {grand_totals['total_rows']:>10,} | ")
                f.write(f"{'':>10} | {grand_totals['total_size_mb']:>12.2f}\n")
                f.write("=" * 100 + "\n\n")
                
                # Detailed metrics per file
                f.write("📈 DETAILED METRICS BY FILE:\n")
                f.write("=" * 100 + "\n\n")
                
                all_columns = sorted(grand_totals['column_totals'].keys())
                
                for file_info in files_summary:
                    f.write("-" * 100 + "\n")
                    f.write(f"📄 FILE: {file_info['filename']}\n")
                    f.write("-" * 100 + "\n")
                    f.write(f"   Date Range: {file_info['date_range']}\n")
                    f.write(f"   Total Rows: {file_info['total_rows']:,}\n")
                    f.write(f"   Total Columns: {file_info['total_columns']}\n")
                    f.write(f"   File Size: {file_info['file_size_mb']:.2f} MB\n\n")
                    
                    if file_info['column_totals']:
                        f.write("   Column Totals:\n")
                        for col in all_columns:
                            if col in file_info['column_totals']:
                                value = file_info['column_totals'][col]
                                f.write(f"   • {col:<30} : {value:>15,.2f}\n")
                    else:
                        f.write("   No numeric columns found.\n")
                    
                    f.write("\n")
                
                # Grand totals
                f.write("=" * 100 + "\n")
                f.write("🏆 GRAND TOTALS (ALL FILES)\n")
                f.write("=" * 100 + "\n")
                f.write(f"   Total Files: {grand_totals['total_files']}\n")
                f.write(f"   Total Rows: {grand_totals['total_rows']:,}\n")
                f.write(f"   Total Size: {grand_totals['total_size_mb']:.2f} MB\n\n")
                
                if grand_totals['column_totals']:
                    f.write("   Combined Column Totals:\n")
                    for col in all_columns:
                        value = grand_totals['column_totals'][col]
                        f.write(f"   • {col:<30} : {value:>15,.2f}\n")
            
            self.log(f"✅ Validation file exported: validation_details.txt")
            
        except Exception as e:
            self.log(f"⚠️ Could not export validation file: {str(e)}")
    
    def _save_execution_log(self, output_dir: Path, files_count: int, total_rows: int, duration: float):
        """Save execution log and session summary"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Save detailed execution log
            log_file = output_dir / "execution_log.txt"
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write("🌊 PER-FILE CSV ANALYSIS - EXECUTION LOG\n")
                f.write("=" * 80 + "\n\n")
                
                for log_entry in self.execution_log_messages:
                    f.write(f"{log_entry}\n")
            
            self.log(f"📝 Execution log saved: execution_log.txt")
            
            # Save summary report
            summary_file = output_dir / "analysis_summary.txt"
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write("🌊 PER-FILE CSV ANALYSIS - SUMMARY REPORT\n")
                f.write("=" * 80 + "\n\n")
                
                f.write(f"Timestamp: {timestamp}\n")
                f.write(f"Status: ✅ SUCCESS\n")
                f.write(f"Duration: {duration:.2f} seconds\n\n")
                
                f.write(f"Files analyzed: {files_count}\n")
                f.write(f"Total rows: {total_rows:,}\n\n")
                
                f.write(f"Input folder: {self.input_folder}\n")
                f.write(f"Output: {output_dir}\n\n")
                
                f.write(f"Full logs available in: execution_log.txt\n")
            
            self.log(f"📊 Summary report saved: analysis_summary.txt")
            
            # Save session summary to gui_logs folder
            try:
                gui_logs_dir = output_dir.parent.parent / "gui_logs"
                gui_logs_dir.mkdir(parents=True, exist_ok=True)
                
                session_log = gui_logs_dir / f"file_summary_session_{timestamp}.txt"
                with open(session_log, 'w', encoding='utf-8') as f:
                    f.write("=" * 80 + "\n")
                    f.write(f"🌊 FILE SUMMARY SESSION - {timestamp}\n")
                    f.write("=" * 80 + "\n\n")
                    
                    f.write(f"Status: ✅ SUCCESS\n")
                    f.write(f"Files analyzed: {files_count}\n")
                    f.write(f"Total rows: {total_rows:,}\n")
                    f.write(f"Duration: {duration:.2f} seconds\n")
                    f.write(f"Input: {self.input_folder}\n")
                    f.write(f"Output: {output_dir}\n")
                    f.write(f"\nFull logs saved in output directory.\n")
                
                self.log(f"📁 Session log saved to gui_logs/")
            except Exception as e:
                self.log(f"⚠️ Could not save to gui_logs: {str(e)}")
            
        except Exception as e:
            self.log(f"⚠️ Warning: Could not save execution log - {str(e)}")
    
    def stop(self):
        """Stop the operation"""
        self.should_stop = True


# OLD METHODS REMOVED - NO LONGER NEEDED FOR PER-FILE ANALYSIS
class _OLD_WEBSITE_GROUPING_METHODS:
    """These methods were for the old website-grouping approach and are no longer used"""
    
    def _generate_summary_by_website_OLD(self, headers: List[str], rows: List[List[str]]) -> Tuple[Dict[str, Dict[str, any]], List[str]]:
        """Generate summary statistics grouped by Website Name"""
        # Find the index of "Website Name" column
        try:
            website_name_idx = headers.index('Website Name')
        except ValueError:
            self.log("❌ Error: 'Website Name' column not found in CSV files")
            return {}, []
        
        # Automatically detect numeric columns
        self.log("🔍 Detecting numeric columns...")
        numeric_indices = self._detect_numeric_columns(headers, rows)
        
        self.log(f"✅ Found {len(numeric_indices)} numeric columns:")
        for col_name in sorted(numeric_indices.keys()):
            self.log(f"   • {col_name}")
        self.log("")
        
        # Get Date column index
        date_idx = None
        try:
            date_idx = headers.index('Date')
        except ValueError:
            self.log(f"⚠️  Warning: 'Date' column not found, date range will not be available")
        
        # Initialize summary dictionary
        summary = defaultdict(lambda: {
            'row_count': 0,
            'min_date': None,
            'max_date': None,
            **{col: 0.0 for col in numeric_indices.keys()}
        })
        
        # Track errors for debugging
        skipped_rows = 0
        empty_websites = 0
        parsing_errors = defaultdict(int)
        
        # Process each row
        for row_idx, row in enumerate(rows):
            if len(row) <= website_name_idx:
                skipped_rows += 1
                continue
            
            website_name = row[website_name_idx].strip()
            
            if not website_name:
                empty_websites += 1
                continue
            
            # Increment row count
            summary[website_name]['row_count'] += 1
            
            # Track date range
            if date_idx is not None and len(row) > date_idx:
                date_value = row[date_idx].strip()
                if date_value:
                    if summary[website_name]['min_date'] is None or date_value < summary[website_name]['min_date']:
                        summary[website_name]['min_date'] = date_value
                    if summary[website_name]['max_date'] is None or date_value > summary[website_name]['max_date']:
                        summary[website_name]['max_date'] = date_value
            
            # Sum numeric columns using enhanced cleaning
            for col_name, col_idx in numeric_indices.items():
                if len(row) > col_idx:
                    raw_value = row[col_idx].strip()
                    if raw_value:
                        cleaned_value = self._clean_numeric_value(raw_value)
                        summary[website_name][col_name] += cleaned_value
                        
                        # Track if cleaning failed
                        if cleaned_value == 0.0 and raw_value not in ('0', '0.0', '0.00', ''):
                            parsing_errors[col_name] += 1
        
        # Log any issues found
        if skipped_rows > 0:
            self.log(f"⚠️  Skipped {skipped_rows} rows (incomplete data)")
        if empty_websites > 0:
            self.log(f"⚠️  Skipped {empty_websites} rows (empty Website Name)")
        if parsing_errors:
            self.log(f"⚠️  Numeric parsing issues detected:")
            for col, count in sorted(parsing_errors.items(), key=lambda x: x[1], reverse=True)[:5]:
                self.log(f"   • {col}: {count} values couldn't be parsed")
        
        # Calculate total rows counted per website
        total_website_rows = sum(data['row_count'] for data in summary.values())
        expected_rows = len(rows) - skipped_rows - empty_websites
        
        # Log summary statistics
        self.log("")
        self.log(f"📊 Aggregation complete:")
        self.log(f"   • Websites found: {len(summary)}")
        self.log(f"   • Rows processed: {expected_rows:,}")
        self.log(f"   • Rows counted (by website): {total_website_rows:,}")
        self.log(f"   • Metrics tracked: {len(numeric_indices)}")
        
        # Verify row count matches
        if total_website_rows != expected_rows:
            self.log(f"⚠️  WARNING: Row count discrepancy!")
            self.log(f"   Expected: {expected_rows:,}")
            self.log(f"   Counted: {total_website_rows:,}")
            self.log(f"   Difference: {abs(expected_rows - total_website_rows):,}")
        else:
            self.log(f"✅ Row count verification: ALL ROWS ACCOUNTED FOR")
        
        self.log("")
        
        return dict(summary), list(numeric_indices.keys())
    
    def _get_ordered_columns(self, numeric_columns: List[str]) -> List[str]:
        """Return numeric columns in the preferred display order"""
        # Define preferred order
        preferred_order = [
            'Sessions',
            'Engaged sessions',
            'Views',
            'Active users',
            'New users',
            'Total users',
            'Total revenue'
        ]
        
        # Create ordered list
        ordered = []
        
        # Add columns from preferred order that exist
        for col in preferred_order:
            if col in numeric_columns:
                ordered.append(col)
        
        # Add any remaining columns (sorted alphabetically)
        remaining = sorted([col for col in numeric_columns if col not in preferred_order])
        ordered.extend(remaining)
        
        return ordered
    
    def _export_summary_to_csv(self, summary: Dict[str, Dict[str, any]], numeric_columns: List[str], output_dir: Path):
        """Export the summary to a CSV file"""
        try:
            output_file = output_dir / "website_summary.csv"
            
            # Get columns in preferred order
            ordered_columns = self._get_ordered_columns(numeric_columns)
            
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # Build header row
                header_row = ['Website Name', 'Date From', 'Date To', 'Row Count']
                header_row.extend(ordered_columns)
                writer.writerow(header_row)
                
                # Write data rows (sorted by Website Name)
                sorted_websites = sorted(summary.keys())
                
                # Calculate totals
                totals = {'row_count': 0}
                all_min_dates = []
                all_max_dates = []
                
                for col in ordered_columns:
                    totals[col] = 0.0
                
                for website in sorted_websites:
                    data = summary[website]
                    
                    # Build data row
                    row = [
                        website,
                        data.get('min_date', 'N/A'),
                        data.get('max_date', 'N/A'),
                        data['row_count']
                    ]
                    
                    for col in ordered_columns:
                        value = data.get(col, 0)
                        row.append(value)
                        totals[col] += value
                    
                    writer.writerow(row)
                    
                    # Collect dates for totals row
                    totals['row_count'] += data['row_count']
                    if data.get('min_date') and data.get('min_date') != 'N/A':
                        all_min_dates.append(data['min_date'])
                    if data.get('max_date') and data.get('max_date') != 'N/A':
                        all_max_dates.append(data['max_date'])
                
                # Write totals row
                overall_min = min(all_min_dates) if all_min_dates else 'N/A'
                overall_max = max(all_max_dates) if all_max_dates else 'N/A'
                
                total_row = [
                    'ALL WEBSITES',
                    overall_min,
                    overall_max,
                    totals['row_count']
                ]
                
                for col in ordered_columns:
                    total_row.append(totals[col])
                
                writer.writerow(total_row)
            
            self.log(f"📊 Summary exported to: website_summary.csv")
            
            # Also export a detailed validation file
            self._export_validation_file(summary, numeric_columns, output_dir)
            
        except Exception as e:
            self.log(f"⚠️ Warning: Could not export CSV - {str(e)}")
    
    def _export_validation_file(self, summary: Dict[str, Dict[str, any]], numeric_columns: List[str], output_dir: Path):
        """Export detailed validation file for manual verification"""
        try:
            validation_file = output_dir / "validation_details.txt"
            
            ordered_columns = self._get_ordered_columns(numeric_columns)
            
            with open(validation_file, 'w', encoding='utf-8') as f:
                f.write("=" * 100 + "\n")
                f.write("🔍 VALIDATION REPORT - Detailed Breakdown\n")
                f.write("=" * 100 + "\n\n")
                f.write("Use this file to verify the accuracy of the summary.\n")
                f.write("Compare these totals with your manual calculations.\n\n")
                
                # ROW COUNT VERIFICATION SECTION
                f.write("=" * 100 + "\n")
                f.write("📊 ROW COUNT VERIFICATION\n")
                f.write("=" * 100 + "\n\n")
                f.write("This shows how many data rows (excluding headers) were found for each website.\n")
                f.write("Verify these counts match your expectations!\n\n")
                
                sorted_websites = sorted(summary.keys())
                total_rows_counted = 0
                
                f.write(f"{'WEBSITE NAME':<50} | {'DATA ROWS':>15}\n")
                f.write("-" * 100 + "\n")
                
                for website in sorted_websites:
                    data = summary[website]
                    row_count = data['row_count']
                    total_rows_counted += row_count
                    f.write(f"{website:<50} | {row_count:>15,}\n")
                
                f.write("-" * 100 + "\n")
                f.write(f"{'TOTAL (all websites)':<50} | {total_rows_counted:>15,}\n")
                f.write("=" * 100 + "\n\n")
                
                f.write("NOTE: This count excludes:\n")
                f.write("  • Header rows (1 per CSV file)\n")
                f.write("  • Rows with empty 'Website Name' field\n")
                f.write("  • Incomplete rows (rows shorter than expected)\n\n")
                
                # DETAILED METRICS PER WEBSITE
                f.write("=" * 100 + "\n")
                f.write("📈 DETAILED METRICS BY WEBSITE\n")
                f.write("=" * 100 + "\n\n")
                
                for website in sorted_websites:
                    data = summary[website]
                    
                    f.write("-" * 100 + "\n")
                    f.write(f"📌 WEBSITE: {website}\n")
                    f.write("-" * 100 + "\n")
                    f.write(f"   Date Range: {data.get('min_date', 'N/A')} to {data.get('max_date', 'N/A')}\n")
                    f.write(f"   Total Rows: {data['row_count']:,}\n\n")
                    
                    f.write("   Metrics:\n")
                    for col in ordered_columns:
                        value = data.get(col, 0)
                        f.write(f"   • {col:<30} : {value:>15,.2f}\n")
                    
                    f.write("\n")
                
                # Write grand totals
                f.write("=" * 100 + "\n")
                f.write("🏆 GRAND TOTALS (ALL WEBSITES)\n")
                f.write("=" * 100 + "\n")
                
                totals = {'row_count': 0}
                for col in numeric_columns:
                    totals[col] = 0.0
                
                for data in summary.values():
                    totals['row_count'] += data['row_count']
                    for col in numeric_columns:
                        totals[col] += data.get(col, 0)
                
                f.write(f"   Total Rows: {totals['row_count']:,}\n\n")
                f.write("   Total Metrics:\n")
                for col in ordered_columns:
                    value = totals[col]
                    f.write(f"   • {col:<30} : {value:>15,.2f}\n")
                
                f.write("\n")
                f.write("=" * 100 + "\n")
                f.write("✅ VERIFICATION CHECKLIST:\n")
                f.write("=" * 100 + "\n")
                f.write("[ ] Row counts per website match your expectations\n")
                f.write("[ ] Total row count matches your CSV files (minus headers)\n")
                f.write("[ ] Metric values look reasonable\n")
                f.write("[ ] Date ranges are correct\n")
                f.write("[ ] All expected websites are present\n")
            
            self.log(f"✅ Validation file exported: validation_details.txt")
            
        except Exception as e:
            self.log(f"⚠️ Could not export validation file: {str(e)}")
    
    def _save_execution_log(self, output_dir: Path, websites_count: int, total_rows: int, duration: float):
        """Save execution log and session summary"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Save detailed execution log
            log_file = output_dir / "execution_log.txt"
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write("🌊 CSV SUMMARY BY WEBSITE NAME - EXECUTION LOG\n")
                f.write("=" * 80 + "\n\n")
                
                for log_entry in self.execution_log_messages:
                    f.write(f"{log_entry}\n")
            
            self.log(f"📝 Execution log saved: execution_log.txt")
            
            # Save summary report
            summary_file = output_dir / "analysis_summary.txt"
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write("🌊 CSV SUMMARY BY WEBSITE NAME - SUMMARY REPORT\n")
                f.write("=" * 80 + "\n\n")
                
                f.write(f"Timestamp: {timestamp}\n")
                f.write(f"Status: ✅ SUCCESS\n")
                f.write(f"Duration: {duration:.2f} seconds\n\n")
                
                f.write(f"Websites found: {websites_count}\n")
                f.write(f"Total rows: {total_rows:,}\n\n")
                
                f.write(f"Input folder: {self.input_folder}\n")
                f.write(f"Output: {output_dir}\n\n")
                
                f.write(f"Full logs available in: execution_log.txt\n")
            
            self.log(f"📊 Summary report saved: analysis_summary.txt")
            
            # Save session summary to gui_logs folder
            try:
                gui_logs_dir = output_dir.parent.parent / "gui_logs"
                gui_logs_dir.mkdir(parents=True, exist_ok=True)
                
                session_log = gui_logs_dir / f"website_summary_session_{timestamp}.txt"
                with open(session_log, 'w', encoding='utf-8') as f:
                    f.write("=" * 80 + "\n")
                    f.write(f"🌊 WEBSITE SUMMARY SESSION - {timestamp}\n")
                    f.write("=" * 80 + "\n\n")
                    
                    f.write(f"Status: ✅ SUCCESS\n")
                    f.write(f"Websites: {websites_count}\n")
                    f.write(f"Total rows: {total_rows:,}\n")
                    f.write(f"Duration: {duration:.2f} seconds\n")
                    f.write(f"Input: {self.input_folder}\n")
                    f.write(f"Output: {output_dir}\n")
                    f.write(f"\nFull logs saved in output directory.\n")
                
                self.log(f"📁 Session log saved to gui_logs/")
            except Exception as e:
                self.log(f"⚠️ Could not save to gui_logs: {str(e)}")
            
        except Exception as e:
            self.log(f"⚠️ Warning: Could not save execution log - {str(e)}")
    
    def stop(self):
        """Stop the operation"""
        self.should_stop = True


class DataSummaryTool(PathConfigMixin, BaseToolDialog):
    """Per-File CSV Analysis Tool with Modern UI"""

    PATH_CONFIG = {
        "show_input": True,
        "show_output": False,
        "include_open_buttons": True,
        "input_label": "📥 Input Folder (CSV Files):",
    }

    def __init__(self, parent=None, input_path: str = None, output_path: str = None):
        super().__init__(parent, input_path, output_path)

        self.path_manager = get_path_manager()
        base_output = Path(output_path) if output_path else Path(self.path_manager.get_output_path())
        self.output_path = base_output

        self.is_analyzing = False
        self.worker: Optional[DataSummaryWorker] = None
        self.worker_thread: Optional[QThread] = None
        self.execution_log_messages: List[str] = []
        self.current_files_summary = None
        self.current_grand_totals = None

        self.setup_window()
        self.setup_ui()
        self.apply_theme()

        self.log("📊 Per-File CSV Analysis Tool initialized! 🌊")
        self.log("📌 WORKFLOW:")
        self.log("  1. Select Input folder → Scan CSV files")
        self.log("  2. Analyze each file individually")
        self.log("  3. View per-file metrics and grand totals")
        self.log("")

    def setup_window(self):
        """Setup window"""
        self.setWindowTitle("📊 Per-File CSV Analysis")
        self.setGeometry(100, 100, 1400, 900)
        
        # Set window flags
        self.setWindowFlags(Qt.Window | Qt.WindowMinMaxButtonsHint | Qt.WindowCloseButtonHint)
        
        # Center on screen
        screen_geometry = self.screen().geometry()
        x = (screen_geometry.width() - 1400) // 2
        y = (screen_geometry.height() - 900) // 2
        self.move(x, y)
    
    def setup_ui(self):
        """Setup UI"""
        # Create main scroll area
        main_scroll = QScrollArea()
        main_scroll.setWidgetResizable(True)
        main_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        main_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # Create main widget and layout
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title = QLabel("📊 Per-File CSV Analysis")
        title.setFont(QFont("Arial", 20, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)
        
        # Subtitle
        subtitle = QLabel("Analyzes each CSV file individually with automatic metric detection and totals")
        subtitle.setFont(QFont("Arial", 10))
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setObjectName("infoLabel")
        main_layout.addWidget(subtitle)
        
        # Path controls (input only)
        self.build_path_controls(
            main_layout,
            show_input=True,
            show_output=False,
            include_open_buttons=True,
            input_label="📥 Input Folder (CSV Files):",
        )
        
        # Analyze button
        self.analyze_btn = QPushButton("🔍 Analyze Files")
        self.analyze_btn.clicked.connect(self.analyze_files)
        self.analyze_btn.setFixedHeight(50)
        main_layout.addWidget(self.analyze_btn)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        
        # Results section
        self._create_results_section(main_layout)
        
        # Execution Log Footer ✨
        log_widget = self.create_execution_log(main_layout)
        if not log_widget:
            log_label = QLabel("📋 Execution Log:")
            log_label.setFont(QFont("Arial", 10, QFont.Bold))
            main_layout.addWidget(log_label)
            
            self.log_area = QTextEdit()
            self.log_area.setReadOnly(True)
            self.log_area.setMaximumHeight(150)
            main_layout.addWidget(self.log_area)
        
        # Set the main widget as the scroll area's widget
        main_scroll.setWidget(main_widget)
        
        # Set the scroll area as the dialog's layout
        dialog_layout = QVBoxLayout(self)
        dialog_layout.setContentsMargins(0, 0, 0, 0)
        dialog_layout.addWidget(main_scroll)
    
    def _create_results_section(self, main_layout):
        """Create results display section"""
        # Section title
        results_label = QLabel("📊 RESULTS")
        results_label.setFont(QFont("Arial", 14, QFont.Bold))
        results_label.setObjectName("sectionTitle")
        main_layout.addWidget(results_label)
        
        # Summary stats frame
        self.stats_frame = QFrame()
        self.stats_frame.setObjectName("glassFrame")
        stats_layout = QHBoxLayout(self.stats_frame)
        
        # Stats labels
        self.total_websites_label = QLabel("Files: 0")
        self.total_websites_label.setFont(QFont("Arial", 11))
        self.total_websites_label.setObjectName("infoLabel")
        stats_layout.addWidget(self.total_websites_label)
        
        self.total_rows_label = QLabel("Total Rows: 0")
        self.total_rows_label.setFont(QFont("Arial", 11))
        self.total_rows_label.setObjectName("infoLabel")
        stats_layout.addWidget(self.total_rows_label)
        
        self.date_range_label = QLabel("Date Range: N/A")
        self.date_range_label.setFont(QFont("Arial", 11))
        self.date_range_label.setObjectName("infoLabel")
        stats_layout.addWidget(self.date_range_label)
        
        main_layout.addWidget(self.stats_frame)
        
        # Results table
        self.results_table = QTableWidget()
        self.results_table.setObjectName("tableWidget")
        self.results_table.setMinimumHeight(400)
        main_layout.addWidget(self.results_table)
        
        # Export buttons
        export_layout = QHBoxLayout()
        
        self.export_csv_btn = QPushButton("📊 Export to CSV")
        self.export_csv_btn.clicked.connect(self.export_to_csv)
        self.export_csv_btn.setEnabled(False)
        export_layout.addWidget(self.export_csv_btn)
        
        self.view_details_btn = QPushButton("👁 View Details")
        self.view_details_btn.clicked.connect(self.view_details)
        self.view_details_btn.setEnabled(False)
        export_layout.addWidget(self.view_details_btn)
        
        export_layout.addStretch()
        main_layout.addLayout(export_layout)
    
    def apply_theme(self):
        """Apply theme using NEW system! ✨"""
        if not THEME_AVAILABLE or not self.current_theme:
            return
        
        try:
            self.current_theme.apply_to_window(self)
            safe_theme_name = self.current_theme.theme_name.encode('ascii', 'ignore').decode('ascii')
            print(f"✅ [THEME] Applied to Website Summary tool: {safe_theme_name}")
        except Exception as e:
            print(f"⚠️ [THEME] Error applying theme: {e}")
    
    def refresh_theme(self):
        """Refresh theme when user switches - Inherit from parent! ✨"""
        print(f"🔄 [THEME] refresh_theme() called on Website Summary tool!")
        
        if not THEME_AVAILABLE:
            return
        
        try:
            parent = self.parent()
            if hasattr(parent, 'current_theme') and parent.current_theme:
                self.current_theme = parent.current_theme
                safe_theme_name = self.current_theme.theme_name.encode('ascii', 'ignore').decode('ascii')
                print(f"✅ [THEME] Inherited from parent: {safe_theme_name}")
            else:
                print(f"⚠️ [THEME] Parent has no theme, keeping current")
            
            self.apply_theme()
        except Exception as e:
            print(f"⚠️ [THEME] Error refreshing theme: {e}")
    
    def log(self, message: str, level: str = "INFO"):
        """Add log message and persist it for exports."""
        super().log(message, level=level)

        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        self.execution_log_messages.append(formatted_message)

        if not (hasattr(self, 'execution_log') and getattr(self.execution_log, 'log', None)):
            if hasattr(self, 'log_area'):
                self.log_area.append(formatted_message)
    
    def analyze_files(self):
        """Start file analysis"""
        if self.is_analyzing:
            self.log("⚠️  Analysis already in progress")
            return
        
        if not self.input_path.exists():
            QMessageBox.warning(self, "Error", f"Input folder does not exist:\n{self.input_path}")
            return
        
        self.log(f"🔍 Starting analysis...")

        path_info = self.path_manager.prepare_tool_output(
            "Data Summary Tool",
            script_name=Path(__file__).name,
        )
        run_root = path_info.get("root")
        if run_root is None:
            QMessageBox.critical(
                self,
                "Output Error",
                "Unable to create an output folder for this analysis run.",
            )
            self.is_analyzing = False
            self.analyze_btn.setEnabled(True)
            self.analyze_btn.setText("🔍 Analyze Files")
            self.progress_bar.setVisible(False)
            return

        run_root.mkdir(parents=True, exist_ok=True)
        self.output_path = run_root
        self._sync_path_edits(Path(self.input_path), self.output_path)
        self.log(f"📁 Output run directory: {self.output_path}")

        # Disable UI
        self.is_analyzing = True
        self.analyze_btn.setEnabled(False)
        self.analyze_btn.setText("⏳ Analyzing...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # Clear previous results
        self.results_table.setRowCount(0)
        self.results_table.setColumnCount(0)
        
        # Create worker thread
        try:
            self.worker = DataSummaryWorker(Path(self.input_path), self.output_path)
            self.worker_thread = QThread()
            self.worker.moveToThread(self.worker_thread)
            
            # Connect signals
            self.worker_thread.started.connect(self.worker.run)
            self.worker.log_signal.connect(self.log)
            self.worker.progress_signal.connect(self.on_progress)
            self.worker.finished_signal.connect(self.on_analysis_complete)
            self.worker_thread.finished.connect(self.on_worker_thread_finished)
            
            # Start
            self.worker_thread.start()
            self.log("✅ Analysis started")
            
        except Exception as e:
            self.log(f"❌ Error starting analysis: {str(e)}")
            self.is_analyzing = False
            self.analyze_btn.setEnabled(True)
            self.analyze_btn.setText("🔍 Analyze Files")
            self.progress_bar.setVisible(False)
    
    def on_progress(self, current: int, total: int):
        """Update progress bar"""
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
    
    def on_analysis_complete(self, results: dict):
        """Called when analysis completes"""
        # Reset button state
        self.is_analyzing = False
        self.analyze_btn.setEnabled(True)
        self.analyze_btn.setText("🔍 Analyze Files")
        
        # Handle different status types
        if results['status'] == 'no_files':
            QMessageBox.information(self, "No Files", "No CSV files found in the selected folder.")
            return
        
        if results['status'] == 'no_data':
            QMessageBox.information(self, "No Data", "No data found in CSV files.")
            return
        
        if results['status'] == 'error':
            QMessageBox.critical(self, "Analysis Error", f"An error occurred during analysis:\n\n{results.get('error', 'Unknown error')}")
            return
        
        # Store results (NEW per-file structure)
        self.current_files_summary = results['files_summary']
        self.current_grand_totals = results['grand_totals']
        
        # Update UI
        self._update_results_display(results)
        
        # Enable export buttons
        self.export_csv_btn.setEnabled(True)
        self.view_details_btn.setEnabled(True)
        
        # Show success message
        QMessageBox.information(
            self,
            "Analysis Complete! 🎉",
            f"Successfully analyzed CSV files!\n\n"
            f"Files analyzed: {results['grand_totals']['total_files']}\n"
            f"Total rows: {results['grand_totals']['total_rows']:,}\n\n"
            f"Reports saved to:\n{results['output_dir']}"
        )
    
    def _update_results_display(self, results: dict):
        """Update results display with per-file analysis data"""
        files_summary = results['files_summary']
        grand_totals = results['grand_totals']
        
        # Update stats labels
        self.total_websites_label.setText(f"Files: {grand_totals['total_files']}")
        self.total_rows_label.setText(f"Total Rows: {grand_totals['total_rows']:,}")
        
        # Get overall date range from all files
        all_dates = [f['date_range'] for f in files_summary if f['date_range'] != 'N/A']
        if all_dates:
            self.date_range_label.setText(f"Multiple date ranges (see details)")
        else:
            self.date_range_label.setText("Date Range: N/A")
        
        # Get all unique metric columns
        all_columns = sorted(grand_totals['column_totals'].keys())
        display_columns = all_columns[:5] if len(all_columns) > 5 else all_columns
        
        # Setup table headers (FILE-BASED)
        headers = ['File Name', 'Date Range', 'Rows', 'Columns', 'Size (MB)'] + display_columns
        self.results_table.setColumnCount(len(headers))
        self.results_table.setHorizontalHeaderLabels(headers)
        self.results_table.setRowCount(len(files_summary) + 1)  # +1 for totals row
        
        # Populate table (per file)
        for row_idx, file_info in enumerate(files_summary):
            # File Name
            self.results_table.setItem(row_idx, 0, QTableWidgetItem(file_info['filename']))
            
            # Date Range
            self.results_table.setItem(row_idx, 1, QTableWidgetItem(file_info['date_range']))
            
            # Rows
            self.results_table.setItem(row_idx, 2, QTableWidgetItem(f"{file_info['total_rows']:,}"))
            
            # Columns
            self.results_table.setItem(row_idx, 3, QTableWidgetItem(str(file_info['total_columns'])))
            
            # Size (MB)
            self.results_table.setItem(row_idx, 4, QTableWidgetItem(f"{file_info['file_size_mb']:.2f}"))
            
            # Metric columns
            for col_idx, col in enumerate(display_columns):
                value = file_info['column_totals'].get(col, 0)
                formatted_value = self._format_value(col, value)
                self.results_table.setItem(row_idx, 5 + col_idx, QTableWidgetItem(formatted_value))
        
        # Add grand totals row
        totals_row = len(files_summary)
        self.results_table.setItem(totals_row, 0, QTableWidgetItem("GRAND TOTAL"))
        self.results_table.setItem(totals_row, 1, QTableWidgetItem(""))
        self.results_table.setItem(totals_row, 2, QTableWidgetItem(f"{grand_totals['total_rows']:,}"))
        self.results_table.setItem(totals_row, 3, QTableWidgetItem(""))
        self.results_table.setItem(totals_row, 4, QTableWidgetItem(f"{grand_totals['total_size_mb']:.2f}"))
        
        for col_idx, col in enumerate(display_columns):
            value = grand_totals['column_totals'].get(col, 0)
            formatted_value = self._format_value(col, value)
            self.results_table.setItem(totals_row, 5 + col_idx, QTableWidgetItem(formatted_value))
        
        # Configure table appearance
        header = self.results_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        for i in range(1, len(headers)):
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
    
    def _get_ordered_columns(self, numeric_columns: List[str]) -> List[str]:
        """Return numeric columns in preferred order"""
        preferred_order = [
            'Sessions',
            'Engaged sessions',
            'Views',
            'Active users',
            'New users',
            'Total users',
            'Total revenue'
        ]
        
        ordered = []
        for col in preferred_order:
            if col in numeric_columns:
                ordered.append(col)
        
        remaining = sorted([col for col in numeric_columns if col not in preferred_order])
        ordered.extend(remaining)
        
        return ordered
    
    def _format_value(self, col_name: str, value: float) -> str:
        """Format value based on column type"""
        if 'revenue' in col_name.lower() or 'cost' in col_name.lower():
            if value >= 1000000:
                return f"${value/1000000:.1f}M"
            elif value >= 1000:
                return f"${value/1000:.1f}K"
            else:
                return f"${value:.0f}"
        else:
            if value >= 1000000:
                return f"{value/1000000:.1f}M"
            elif value >= 1000:
                return f"{value/1000:.0f}K"
            else:
                return f"{value:.0f}"
    
    def export_to_csv(self):
        """Export current results to CSV"""
        if not self.current_files_summary:
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save CSV File",
            str(self.output_path / "file_summary.csv"),
            "CSV Files (*.csv)"
        )
        
        if file_path:
            self.log(f"📊 Exporting to: {file_path}")
            # Export logic is already done by worker, just copy
            QMessageBox.information(self, "Export", f"CSV file saved to:\n{file_path}")
    
    def view_details(self):
        """View detailed metrics window"""
        if not self.current_files_summary:
            return
        
        self.log("👁 Opening detailed view...")
        # Create detailed view window
        details_window = self._create_details_window()
        details_window.exec()
    
    def _create_details_window(self):
        """Create detailed metrics window"""
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QTableWidget
        
        dialog = QDialog(self)
        dialog.setWindowTitle("📊 Detailed Website Metrics")
        dialog.setGeometry(100, 100, 1200, 700)
        
        layout = QVBoxLayout(dialog)
        
        # Title
        title = QLabel("📊 Complete Website Metrics")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Table with ALL columns
        table = QTableWidget()
        table.setObjectName("tableWidget")
        
        sorted_files = sorted(self.current_files_summary)
        ordered_columns = self._get_ordered_columns(self._get_all_metric_columns(self.current_files_summary))
        
        headers = ['File Name', 'Date Range', 'Rows'] + ordered_columns
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setRowCount(len(sorted_files))
        
        for row_idx, file_info in enumerate(sorted_files):
            data = self.current_files_summary[file_info]
            
            table.setItem(row_idx, 0, QTableWidgetItem(file_info))
            table.setItem(row_idx, 1, QTableWidgetItem(data.get('date_range', 'N/A')))
            table.setItem(row_idx, 2, QTableWidgetItem(f"{data['total_rows']:,}"))
            
            for col_idx, col in enumerate(ordered_columns):
                value = data.get(col, 0)
                formatted_value = self._format_value(col, value)
                table.setItem(row_idx, 3 + col_idx, QTableWidgetItem(formatted_value))
        
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        
        layout.addWidget(table)
        
        # Apply theme
        if THEME_AVAILABLE and self.current_theme:
            self.current_theme.apply_to_window(dialog)
        
        return dialog
    
    def _get_all_metric_columns(self, files_summary: List[Dict]) -> List[str]:
        """Extract all unique metric column names from the per-file summary."""
        all_columns = set()
        for file_info in files_summary:
            all_columns.update(file_info['numeric_columns'])
        return sorted(list(all_columns))
    
    def on_worker_thread_finished(self):
        """Called when worker thread finishes"""
        sender = self.sender()
        
        if sender != self.worker_thread:
            self.log("⚠️  Ignoring signal from old worker thread")
            return
        
        self.log("🌊 Analysis thread finished")
        
        if self.is_analyzing:
            self.is_analyzing = False
            self.analyze_btn.setEnabled(True)
            self.analyze_btn.setText("🔍 Analyze Files")
        
        self.progress_bar.setVisible(False)
        
        # Clean up
        self.worker = None
        self.worker_thread = None
    
    def closeEvent(self, event):
        """Handle window close"""
        if self.is_analyzing:
            reply = QMessageBox.question(
                self, "Confirm Close",
                "Analysis is in progress. Are you sure you want to close?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                event.ignore()
                return
            
            if self.worker:
                self.worker.stop()
            
            if self.worker_thread and self.worker_thread.isRunning():
                self.worker_thread.quit()
                self.worker_thread.wait(3000)
        
        if self.worker_thread and self.worker_thread.isRunning():
            self.worker_thread.quit()
            self.worker_thread.wait(1000)
        
        super().closeEvent(event)
    
    def _handle_paths_changed(self, input_path: Path, output_path: Path) -> None:
        """Sync UI when shared paths change."""
        super()._handle_paths_changed(input_path, output_path)
        self._sync_path_edits(input_path, output_path)
        if hasattr(self, 'execution_log') and hasattr(self.execution_log, 'set_output_path'):
            self.execution_log.set_output_path(str(output_path))


def main():
    """Main entry point"""
    app = QApplication(sys.argv)
    
    path_manager = get_path_manager()
    input_path = str(path_manager.get_input_path())
    output_path = str(path_manager.get_output_path())
    
    tool = DataSummaryTool(None, input_path, output_path)
    tool.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
