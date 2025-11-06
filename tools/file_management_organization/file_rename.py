"""
🌊 File Renamer Tool
Add prefix/suffix to file names while preserving original names
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

from PySide6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QFileDialog, QTextEdit, QCheckBox,
    QScrollArea, QWidget, QFrame, QMessageBox, QProgressBar
)
from PySide6.QtCore import Qt, Signal, QObject, QThread
from PySide6.QtGui import QFont

# Import NEW theme system ✨
try:
    from styles import ThemeLoader, get_theme_manager
    from styles.components import ExecutionLogFooter, create_execution_log_footer
    THEME_AVAILABLE = True
except ImportError:
    # Add parent directory to path for standalone execution
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    try:
        from styles import ThemeLoader, get_theme_manager
        from styles.components import ExecutionLogFooter, create_execution_log_footer
        THEME_AVAILABLE = True
    except ImportError:
        # Ultimate fallback
        THEME_AVAILABLE = False
        print("⚠️  Theme not available, using default styling")
        ExecutionLogFooter = None
        create_execution_log_footer = None


class FileRenameWorker(QObject):
    """Worker for file renaming operations"""
    log_signal = Signal(str)
    progress_signal = Signal(int, int)  # current, total
    finished_signal = Signal(int, int)  # success_count, fail_count
    
    def __init__(self, files_to_rename: List[Dict], prefix: str, suffix: str, output_dir: Path):
        super().__init__()
        self.files_to_rename = files_to_rename
        self.prefix = prefix
        self.suffix = suffix
        self.output_dir = output_dir
        self.should_stop = False
        
        # Store all log messages for file export (like Looker Studio)
        self.execution_log = []
    
    def log(self, message: str):
        """Log message (emits signal and stores for file export)"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        self.execution_log.append(formatted_message)
        self.log_signal.emit(message)
    
    def run(self):
        """Rename files"""
        success_count = 0
        fail_count = 0
        total = len(self.files_to_rename)
        start_time = datetime.now()
        
        self.log("=" * 60)
        self.log("🔄 STARTING FILE RENAME OPERATION...")
        self.log("=" * 60)
        self.log(f"Total files to rename: {total}")
        self.log(f"Prefix: '{self.prefix}'")
        self.log(f"Suffix: '{self.suffix}'")
        self.log(f"Output directory: {self.output_dir}")
        self.log("")
        
        for idx, file_info in enumerate(self.files_to_rename, 1):
            if self.should_stop:
                self.log("⚠️  Operation cancelled by user")
                break
            
            try:
                original_path = Path(file_info['path'])
                original_name = original_path.stem
                extension = original_path.suffix
                
                # Build new name with prefix/suffix
                new_name = f"{self.prefix}{original_name}{self.suffix}{extension}"
                new_path = self.output_dir / new_name
                
                self.log(f"[{idx}/{total}] Processing: {original_path.name}")
                self.log(f"   └─ New name: {new_name}")
                
                # Copy file with new name
                import shutil
                shutil.copy2(original_path, new_path)
                
                self.log(f"   └─ ✅ Success!")
                success_count += 1
                
            except Exception as e:
                self.log(f"   └─ ❌ Error: {str(e)}")
                fail_count += 1
            
            self.progress_signal.emit(idx, total)
            self.log("")
        
        self.log("=" * 60)
        self.log("🎉 RENAME OPERATION COMPLETE!")
        self.log("=" * 60)
        self.log(f"✅ Success: {success_count} file(s)")
        self.log(f"❌ Failed: {fail_count} file(s)")
        self.log("")
        
        # Save execution logs (like Looker Studio)
        duration = (datetime.now() - start_time).total_seconds()
        self._save_execution_log(success_count, fail_count, duration)
        
        self.finished_signal.emit(success_count, fail_count)
    
    def stop(self):
        """Stop the operation"""
        self.should_stop = True
    
    def _save_execution_log(self, success_count: int, fail_count: int, duration: float):
        """Save execution log and session summary (matching Looker Studio pattern)"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # 1. Save detailed execution log to OUTPUT directory
            log_file = self.output_dir / "execution_log.txt"
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write("🌊 FILE RENAMER TOOL - EXECUTION LOG\n")
                f.write("=" * 80 + "\n\n")
                
                # Write all log messages
                for log_entry in self.execution_log:
                    f.write(f"{log_entry}\n")
            
            self.log(f"📝 Execution log saved: execution_log.txt")
            
            # 2. Save summary report to OUTPUT directory
            summary_file = self.output_dir / "rename_summary.txt"
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write("🌊 FILE RENAMER TOOL - SUMMARY REPORT\n")
                f.write("=" * 80 + "\n\n")
                
                f.write(f"Timestamp: {timestamp}\n")
                f.write(f"Status: {'✅ SUCCESS' if fail_count == 0 else '⚠️ PARTIAL SUCCESS' if success_count > 0 else '❌ FAILED'}\n")
                f.write(f"Duration: {duration:.2f} seconds\n\n")
                
                f.write(f"Renamed: {success_count} file(s)\n")
                f.write(f"Failed: {fail_count} file(s)\n")
                f.write(f"Total: {success_count + fail_count} file(s)\n\n")
                
                f.write(f"Prefix: '{self.prefix}'\n")
                f.write(f"Suffix: '{self.suffix}'\n")
                f.write(f"Output: {self.output_dir}\n\n")
                
                f.write(f"Full logs available in: execution_log.txt\n")
            
            self.log(f"📊 Summary report saved: rename_summary.txt")
            
            # 3. Save session summary to GUI_LOGS folder (lightweight, just summary)
            try:
                gui_logs_dir = Path(self.output_dir).parent.parent / "gui_logs"
                gui_logs_dir.mkdir(parents=True, exist_ok=True)
                
                session_log = gui_logs_dir / f"file_renamer_session_{timestamp}.txt"
                with open(session_log, 'w', encoding='utf-8') as f:
                    f.write("=" * 80 + "\n")
                    f.write(f"🌊 FILE RENAMER SESSION - {timestamp}\n")
                    f.write("=" * 80 + "\n\n")
                    
                    f.write(f"Status: {'✅ SUCCESS' if fail_count == 0 else '⚠️ PARTIAL SUCCESS' if success_count > 0 else '❌ FAILED'}\n")
                    f.write(f"Renamed: {success_count} file(s)\n")
                    f.write(f"Failed: {fail_count} file(s)\n")
                    f.write(f"Duration: {duration:.2f} seconds\n")
                    f.write(f"Prefix: '{self.prefix}'\n")
                    f.write(f"Suffix: '{self.suffix}'\n")
                    f.write(f"Output: {self.output_dir}\n")
                    f.write(f"\nFull logs saved in output directory.\n")
                
                self.log(f"📁 Session log saved to gui_logs/")
            except Exception as e:
                self.log(f"⚠️ Could not save to gui_logs: {str(e)}")
            
        except Exception as e:
            self.log(f"⚠️ Warning: Could not save execution log - {str(e)}")


class FileCheckbox(QWidget):
    """Custom checkbox widget for file selection"""
    def __init__(self, file_path: Path, parent=None, on_state_changed=None):
        super().__init__(parent)
        self.file_path = file_path
        self.on_state_changed = on_state_changed
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)
        
        self.checkbox = QCheckBox()
        self.checkbox.setChecked(True)  # Default: selected
        self.checkbox.stateChanged.connect(self._on_checkbox_changed)
        
        self.label = QLabel(file_path.name)
        self.label.setWordWrap(True)
        
        layout.addWidget(self.checkbox)
        layout.addWidget(self.label, 1)
    
    def _on_checkbox_changed(self):
        """Called when checkbox state changes"""
        if self.on_state_changed:
            self.on_state_changed()
    
    def is_checked(self) -> bool:
        return self.checkbox.isChecked()
    
    def set_checked(self, checked: bool):
        self.checkbox.setChecked(checked)


class FileRenamerTool(QDialog):
    """File Renamer Tool"""
    
    def __init__(self, parent=None, input_path: str = None, output_path: str = None):
        super().__init__(parent)
        
        # Initialize comprehensive logging
        self.setup_logging()
        
        # State - use provided paths or smart defaults
        self.input_path = Path(input_path) if input_path else Path.cwd()
        
        # Smart default output path - create a timestamped folder
        if output_path:
            self.output_path = Path(output_path)
        else:
            # Create default output folder with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_output = Path.cwd() / "execution test" / "Output" / f"file_rename_{timestamp}"
            default_output.mkdir(parents=True, exist_ok=True)
            self.output_path = default_output
        self.scanned_files: List[Path] = []
        self.file_checkboxes: List[FileCheckbox] = []
        self.worker = None
        self.worker_thread = None
        self.is_renaming = False
        
        # Get theme - Inherit from parent (main GUI) using NEW system! ✨
        self.current_theme = None
        if THEME_AVAILABLE:
            # Try to inherit theme from parent (main GUI)
            if hasattr(parent, 'current_theme') and parent.current_theme:
                self.current_theme = parent.current_theme
                safe_theme_name = self.current_theme.theme_name.encode('ascii', 'ignore').decode('ascii')
                print(f"✅ [THEME] Inherited from parent: {safe_theme_name}")
            else:
                # Fallback: load default theme
                theme_manager = get_theme_manager()
                themes = theme_manager.get_available_themes()
                if themes:
                    self.current_theme = theme_manager.load_theme(themes[0])
                    print(f"✅ [THEME] Loaded default: {themes[0]}")
        
        # Setup
        self.setup_window()
        self.setup_ui()
        self.apply_theme()
        
        self.log("📁 File Renamer Tool initialized! 🌊")
        self.log("📌 WORKFLOW:")
        self.log("  1. Select Input folder → Scan for files")
        self.log("  2. Select files to rename (use checkboxes)")
        self.log("  3. Enter prefix and/or suffix")
        self.log("  4. Select Output folder → Rename files")
        self.log("")
    
    def setup_logging(self):
        """Setup logging - matches Looker Studio pattern"""
        # No debug logger needed - we'll save session summary to gui_logs after each operation
        pass
    
    def setup_window(self):
        """Setup window"""
        self.setWindowTitle("📁 File Renamer Tool")
        self.setGeometry(100, 100, 1000, 800)
        
        # Set window flags to show all controls
        self.setWindowFlags(Qt.Window | Qt.WindowMinMaxButtonsHint | Qt.WindowCloseButtonHint)
        
        # Center on screen
        screen_geometry = self.screen().geometry()
        x = (screen_geometry.width() - 1000) // 2
        y = (screen_geometry.height() - 800) // 2
        self.move(x, y)
    
    def setup_ui(self):
        """Setup UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # Title
        title = QLabel("📁 File Renamer Tool")
        title.setFont(QFont("Arial", 24, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)
        
        # Subtitle
        subtitle = QLabel("Add prefix/suffix to file names")
        subtitle.setFont(QFont("Arial", 12))
        subtitle.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(subtitle)
        
        # Input folder
        input_layout = QHBoxLayout()
        input_label = QLabel("Input Folder:")
        input_label.setFont(QFont("Arial", 10, QFont.Bold))
        input_label.setFixedWidth(100)
        self.input_entry = QLineEdit()
        self.input_entry.setPlaceholderText("Select input folder...")
        self.input_entry.setText(str(self.input_path))
        input_btn = QPushButton("📂 Browse")
        input_btn.clicked.connect(self.browse_input)
        input_btn.setFixedWidth(100)
        input_layout.addWidget(input_label)
        input_layout.addWidget(self.input_entry)
        input_layout.addWidget(input_btn)
        main_layout.addLayout(input_layout)
        
        # Scan button
        scan_layout = QHBoxLayout()
        self.scan_btn = QPushButton("🔍 Scan Folder")
        self.scan_btn.clicked.connect(self.scan_folder)
        self.scan_btn.setFixedHeight(40)
        scan_layout.addWidget(self.scan_btn)
        main_layout.addLayout(scan_layout)
        
        # ===== TWO COLUMN LAYOUT =====
        columns_layout = QHBoxLayout()
        columns_layout.setSpacing(20)
        
        # ===== LEFT COLUMN: FILE LIST =====
        left_column = QVBoxLayout()
        left_column.setSpacing(10)
        
        # File list header with counts and selection buttons
        file_list_header = QHBoxLayout()
        self.file_count_label = QLabel("Files: 0")
        self.file_count_label.setFont(QFont("Arial", 10, QFont.Bold))
        
        self.select_all_btn = QPushButton("✅ Select All")
        self.select_all_btn.clicked.connect(self.select_all_files)
        self.select_all_btn.setFixedWidth(120)
        self.select_all_btn.setEnabled(False)
        
        self.select_none_btn = QPushButton("⬜ Select None")
        self.select_none_btn.clicked.connect(self.select_no_files)
        self.select_none_btn.setFixedWidth(120)
        self.select_none_btn.setEnabled(False)
        
        file_list_header.addWidget(self.file_count_label)
        file_list_header.addStretch()
        file_list_header.addWidget(self.select_all_btn)
        file_list_header.addWidget(self.select_none_btn)
        left_column.addLayout(file_list_header)
        
        # File list (scrollable)
        self.file_list_scroll = QScrollArea()
        self.file_list_scroll.setWidgetResizable(True)
        self.file_list_scroll.setMinimumHeight(300)
        self.file_list_scroll.setMaximumHeight(400)
        
        self.file_list_widget = QWidget()
        self.file_list_layout = QVBoxLayout(self.file_list_widget)
        self.file_list_layout.setContentsMargins(10, 10, 10, 10)
        self.file_list_layout.setSpacing(5)
        self.file_list_layout.addStretch()
        
        self.file_list_scroll.setWidget(self.file_list_widget)
        left_column.addWidget(self.file_list_scroll)
        
        # ===== RIGHT COLUMN: RENAME OPTIONS =====
        right_column = QVBoxLayout()
        right_column.setSpacing(15)
        
        # Rename options header
        rename_label = QLabel("Rename Options:")
        rename_label.setFont(QFont("Arial", 12, QFont.Bold))
        right_column.addWidget(rename_label)
        
        # Prefix
        prefix_layout = QHBoxLayout()
        prefix_label = QLabel("Prefix:")
        prefix_label.setFont(QFont("Arial", 10, QFont.Bold))
        prefix_label.setFixedWidth(80)
        self.prefix_entry = QLineEdit()
        self.prefix_entry.setPlaceholderText("Text to add before filename...")
        self.prefix_entry.textChanged.connect(self.update_preview)
        prefix_layout.addWidget(prefix_label)
        prefix_layout.addWidget(self.prefix_entry)
        right_column.addLayout(prefix_layout)
        
        # Suffix
        suffix_layout = QHBoxLayout()
        suffix_label = QLabel("Suffix:")
        suffix_label.setFont(QFont("Arial", 10, QFont.Bold))
        suffix_label.setFixedWidth(80)
        self.suffix_entry = QLineEdit()
        self.suffix_entry.setPlaceholderText("Text to add after filename...")
        self.suffix_entry.textChanged.connect(self.update_preview)
        suffix_layout.addWidget(suffix_label)
        suffix_layout.addWidget(self.suffix_entry)
        right_column.addLayout(suffix_layout)
        
        # Preview
        preview_layout = QVBoxLayout()
        preview_label = QLabel("Preview:")
        preview_label.setFont(QFont("Arial", 10, QFont.Bold))
        self.preview_label = QLabel("example.txt → example.txt")
        self.preview_label.setWordWrap(True)
        self.preview_label.setFont(QFont("Arial", 9))
        self.preview_label.setObjectName("previewLabel")  # Use theme-based styling
        preview_layout.addWidget(preview_label)
        preview_layout.addWidget(self.preview_label)
        right_column.addLayout(preview_layout)
        
        # Output folder
        output_layout = QVBoxLayout()
        output_label = QLabel("Output Folder:")
        output_label.setFont(QFont("Arial", 10, QFont.Bold))
        output_layout.addWidget(output_label)
        
        output_folder_layout = QHBoxLayout()
        self.output_entry = QLineEdit()
        self.output_entry.setPlaceholderText("Select output folder...")
        self.output_entry.setText(str(self.output_path))
        output_btn = QPushButton("📂 Browse")
        output_btn.clicked.connect(self.browse_output)
        output_btn.setFixedWidth(100)
        output_folder_layout.addWidget(self.output_entry)
        output_folder_layout.addWidget(output_btn)
        output_layout.addLayout(output_folder_layout)
        right_column.addLayout(output_layout)
        
        # Rename button
        self.rename_btn = QPushButton("🚀 Rename Files")
        self.rename_btn.clicked.connect(self.rename_files)
        self.rename_btn.setFixedHeight(50)
        self.rename_btn.setEnabled(False)
        right_column.addWidget(self.rename_btn)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        right_column.addWidget(self.progress_bar)
        
        # Add columns to main layout
        columns_layout.addLayout(left_column, 2)  # Left column gets 2/3 of space
        columns_layout.addLayout(right_column, 1)  # Right column gets 1/3 of space
        main_layout.addLayout(columns_layout)
        
        # Log area with buttons
        log_header_layout = QHBoxLayout()
        log_label = QLabel("📋 Log:")
        log_label.setFont(QFont("Arial", 10, QFont.Bold))
        log_header_layout.addWidget(log_label)
        log_header_layout.addStretch()
        
        # Log management buttons
        self.copy_log_btn = QPushButton("📋 Copy Log")
        self.copy_log_btn.clicked.connect(self.copy_log)
        self.copy_log_btn.setFixedWidth(100)
        
        self.reset_log_btn = QPushButton("🗑️ Reset Log")
        self.reset_log_btn.clicked.connect(self.reset_log)
        self.reset_log_btn.setFixedWidth(100)
        
        self.save_log_btn = QPushButton("💾 Save Log")
        self.save_log_btn.clicked.connect(self.save_log)
        self.save_log_btn.setFixedWidth(100)
        
        log_header_layout.addWidget(self.copy_log_btn)
        log_header_layout.addWidget(self.reset_log_btn)
        log_header_layout.addWidget(self.save_log_btn)
        main_layout.addLayout(log_header_layout)
        
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setMaximumHeight(150)
        main_layout.addWidget(self.log_area)
    
    def apply_theme(self):
        """Apply theme using NEW system! ✨"""
        if not THEME_AVAILABLE or not self.current_theme:
            return
        
        try:
            # Apply theme to this dialog window
            self.current_theme.apply_to_window(self)
            
            # Safe logging
            safe_theme_name = self.current_theme.theme_name.encode('ascii', 'ignore').decode('ascii')
            print(f"✅ [THEME] Applied to File Renamer tool: {safe_theme_name}")
            
        except Exception as e:
            print(f"⚠️ [THEME] Error applying theme: {e}")
    
    def refresh_theme(self):
        """Refresh theme when user switches - Inherit from parent! ✨"""
        print(f"🔄 [THEME] refresh_theme() called on File Renamer tool!")
        
        if not THEME_AVAILABLE:
            return
        
        try:
            # Get theme from parent (main GUI)
            parent = self.parent()
            if hasattr(parent, 'current_theme') and parent.current_theme:
                self.current_theme = parent.current_theme
                safe_theme_name = self.current_theme.theme_name.encode('ascii', 'ignore').decode('ascii')
                print(f"✅ [THEME] Inherited from parent: {safe_theme_name}")
            else:
                print(f"⚠️ [THEME] Parent has no theme, keeping current")
            
            # Reapply theme
            self.apply_theme()
            
        except Exception as e:
            print(f"⚠️ [THEME] Error refreshing theme: {e}")
    
    def log(self, message: str):
        """Add message to log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_area.append(f"[{timestamp}] {message}")
    
    def browse_input(self):
        """Browse for input folder"""
        folder = QFileDialog.getExistingDirectory(self, "Select Input Folder", str(self.input_path))
        if folder:
            self.input_path = Path(folder)
            self.input_entry.setText(str(self.input_path))
            self.log(f"📂 Input folder selected: {self.input_path}")
    
    def browse_output(self):
        """Browse for output folder"""
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder", str(self.output_path))
        if folder:
            self.output_path = Path(folder)
            self.output_entry.setText(str(self.output_path))
            self.log(f"📂 Output folder selected: {self.output_path}")
    
    def scan_folder(self):
        """Scan input folder for files"""
        input_path = Path(self.input_entry.text())
        
        if not input_path.exists():
            self.show_message("Invalid Path", "Input folder does not exist!", "warning")
            return
        
        if not input_path.is_dir():
            self.show_message("Invalid Path", "Input path is not a folder!", "warning")
            return
        
        self.log(f"🔍 Scanning folder: {input_path}")
        
        # Clear previous scan
        self.scanned_files.clear()
        self.file_checkboxes.clear()
        
        # Clear file list layout
        while self.file_list_layout.count() > 1:  # Keep stretch at the end
            item = self.file_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Scan for files (not subdirectories)
        try:
            files = [f for f in input_path.iterdir() if f.is_file()]
            files.sort(key=lambda x: x.name.lower())
            
            self.scanned_files = files
            
            self.log(f"✅ Found {len(files)} file(s)")
            self.file_count_label.setText(f"Files: {len(files)}")
            
            # Create checkboxes for each file
            for file_path in files:
                file_checkbox = FileCheckbox(file_path, on_state_changed=self.update_rename_button_state)
                self.file_checkboxes.append(file_checkbox)
                self.file_list_layout.insertWidget(self.file_list_layout.count() - 1, file_checkbox)
            
            # Enable selection buttons
            self.select_all_btn.setEnabled(len(files) > 0)
            self.select_none_btn.setEnabled(len(files) > 0)
            
            # Enable rename button if we have files
            self.update_rename_button_state()
            
            # Update preview
            self.update_preview()
            
        except Exception as e:
            self.log(f"❌ Error scanning folder: {str(e)}")
            self.show_message("Scan Error", f"Error scanning folder:\n{str(e)}", "error")
    
    def select_all_files(self):
        """Select all files"""
        for checkbox in self.file_checkboxes:
            checkbox.set_checked(True)
        self.log("✅ Selected all files")
        self.update_rename_button_state()
    
    def select_no_files(self):
        """Deselect all files"""
        for checkbox in self.file_checkboxes:
            checkbox.set_checked(False)
        self.log("⬜ Deselected all files")
        self.update_rename_button_state()
    
    def update_preview(self):
        """Update preview of renamed file"""
        prefix = self.prefix_entry.text()
        suffix = self.suffix_entry.text()
        
        if self.scanned_files:
            example_file = self.scanned_files[0]
            original_name = example_file.stem
            extension = example_file.suffix
            new_name = f"{prefix}{original_name}{suffix}{extension}"
            self.preview_label.setText(f"{example_file.name} → {new_name}")
        else:
            self.preview_label.setText(f"example.txt → {prefix}example{suffix}.txt")
    
    def update_rename_button_state(self):
        """Update rename button enabled state"""
        selected_count = sum(1 for cb in self.file_checkboxes if cb.is_checked())
        self.rename_btn.setEnabled(selected_count > 0 and not self.is_renaming)
    
    def rename_files(self):
        """Start file renaming operation"""
        
        if self.is_renaming:
            self.log("⚠️  Rename operation already in progress, ignoring request")
            return
        
        # Double-check that we're not in a bad state
        if self.worker_thread and self.worker_thread.isRunning():
            self.log("⚠️  Worker thread still running, forcing cleanup...")
            try:
                self.worker_thread.quit()
                self.worker_thread.wait(1000)
                if self.worker_thread.isRunning():
                    self.worker_thread.terminate()
                    self.worker_thread.wait(500)
            except Exception as e:
                pass
        
        # Get selected files
        selected_files = [
            {'path': cb.file_path, 'name': cb.file_path.name}
            for cb in self.file_checkboxes if cb.is_checked()
        ]
        
        if not selected_files:
            self.show_message("No Files Selected", "Please select at least one file to rename!", "warning")
            return
        
        prefix = self.prefix_entry.text()
        suffix = self.suffix_entry.text()
        
        if not prefix and not suffix:
            self.show_message("No Changes", "Please enter a prefix and/or suffix!", "warning")
            return
        
        # Output path will be handled below with smart defaults
        
        self.log(f"🚀 Starting rename operation for {len(selected_files)} file(s)...")
        
        # Create new timestamped output folder for this operation (if using default path)
        current_output = Path(self.output_entry.text())
        default_base = Path.cwd() / "execution test" / "Output"
        
        # If current output is in the default base directory, create a new timestamped folder
        if str(current_output).startswith(str(default_base)):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            new_output = default_base / f"file_rename_{timestamp}"
            new_output.mkdir(parents=True, exist_ok=True)
            self.output_path = new_output
            self.output_entry.setText(str(self.output_path))
            self.log(f"📁 Created new output folder: {self.output_path}")
        else:
            # Use the manually selected output path
            self.output_path = current_output
            if not self.output_path.exists():
                self.output_path.mkdir(parents=True, exist_ok=True)
                self.log(f"📁 Created output folder: {self.output_path}")
        
        # Clean up any existing worker/thread first
        try:
            if self.worker_thread and self.worker_thread.isRunning():
                self.log("⚠️  Stopping previous worker thread...")
                self.worker_thread.quit()
                if not self.worker_thread.wait(3000):  # Wait up to 3 seconds
                    self.log("⚠️  Force terminating worker thread...")
                    self.worker_thread.terminate()
                    self.worker_thread.wait(1000)
            
            # Disconnect all signals first
            if self.worker_thread:
                try:
                    self.worker_thread.started.disconnect()
                except:
                    pass
                try:
                    self.worker_thread.finished.disconnect()
                except:
                    pass
            
            if self.worker:
                try:
                    self.worker.log_signal.disconnect()
                except:
                    pass
                try:
                    self.worker.progress_signal.disconnect()
                except:
                    pass
                try:
                    self.worker.finished_signal.disconnect()
                except:
                    pass
            
            # Clean up old worker and thread
            if self.worker:
                self.worker.deleteLater()
            if self.worker_thread:
                self.worker_thread.deleteLater()
                
            self.log("✅ Previous worker cleaned up successfully")
            
        except Exception as e:
            self.log(f"⚠️  Error during cleanup: {str(e)}")
            # Continue anyway
        
        # Disable UI
        self.is_renaming = True
        self.rename_btn.setEnabled(False)
        self.rename_btn.setText("⏳ Renaming...")
        self.scan_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(selected_files))
        self.progress_bar.setValue(0)
        
        # Create fresh worker thread
        try:
            self.worker = FileRenameWorker(selected_files, prefix, suffix, self.output_path)
            self.worker_thread = QThread()
            self.worker.moveToThread(self.worker_thread)
            
            # Connect signals with error handling
            self.worker_thread.started.connect(self.worker.run)
            
            self.worker.log_signal.connect(self.log)
            
            self.worker.progress_signal.connect(self.on_progress)
            
            self.worker.finished_signal.connect(self.on_rename_complete)
            
            self.worker_thread.finished.connect(self.on_worker_thread_finished)
            
            self.log("✅ Worker thread created and signals connected")
            
            # Start
            self.worker_thread.start()
            self.log("✅ Worker thread started")
            
        except Exception as e:
            self.log(f"❌ Error creating worker thread: {str(e)}")
            import traceback
            
            self.show_message("Error", f"Failed to create worker thread:\n{str(e)}", "error")
            
            # Reset UI state
            self.is_renaming = False
            self.rename_btn.setEnabled(True)
            self.rename_btn.setText("🚀 Rename Files")
            self.scan_btn.setEnabled(True)
            self.progress_bar.setVisible(False)
            return
    
    def on_progress(self, current: int, total: int):
        """Update progress bar"""
        self.progress_bar.setValue(current)
    
    def on_rename_complete(self, success_count: int, fail_count: int):
        """Called when rename operation completes"""
        
        # Get the sender to identify which worker completed
        sender = self.sender()
        
        # CRITICAL FIX: Only process if this is from the CURRENT worker
        # This prevents old workers from interfering with new ones
        if sender != self.worker:
            self.log("⚠️  Ignoring signal from old worker")
            return
        
        # Reset button state immediately
        self.is_renaming = False
        self.rename_btn.setEnabled(True)
        self.rename_btn.setText("🚀 Rename Files")
        self.scan_btn.setEnabled(True)
        
        # Show simple completion message - no reset needed!
        self.show_message(
            "Rename Complete! 🎉",
            f"Successfully renamed {success_count} file(s)!\n"
            f"Failed: {fail_count} file(s)\n\n"
            f"Output folder:\n{self.output_path}\n\n"
            f"💡 Tip: Change prefix/suffix and click 'Rename Files' again!",
            "success" if fail_count == 0 else "warning"
        )
    
    def on_rename_failed(self, error_msg: str):
        """Called when rename operation fails"""
        # Reset button state immediately
        self.is_renaming = False
        self.rename_btn.setEnabled(True)
        self.rename_btn.setText("🚀 Rename Files")
        self.scan_btn.setEnabled(True)
        
        self.show_message("Rename Failed", f"Error: {error_msg}", "error")
    
    def copy_log(self):
        """Copy log content to clipboard"""
        try:
            from PySide6.QtWidgets import QApplication
            clipboard = QApplication.clipboard()
            clipboard.setText(self.log_area.toPlainText())
            self.log("📋 Log copied to clipboard!")
        except Exception as e:
            self.log(f"❌ Failed to copy log: {str(e)}")
    
    def reset_log(self):
        """Clear the log area"""
        self.log_area.clear()
        self.log("🗑️ Log cleared!")
    
    def save_log(self):
        """Save log to file"""
        try:
            from PySide6.QtWidgets import QFileDialog
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_filename = f"file_renamer_log_{timestamp}.txt"
            
            filename, _ = QFileDialog.getSaveFileName(
                self, "Save Log File", default_filename, "Text Files (*.txt);;All Files (*)"
            )
            
            if filename:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(self.log_area.toPlainText())
                self.log(f"💾 Log saved to: {filename}")
        except Exception as e:
            self.log(f"❌ Failed to save log: {str(e)}")
    
    def reset_tool_for_reuse(self):
        """Reset tool for multiple use operations"""
        # Clear file list
        self.scanned_files.clear()
        self.file_checkboxes.clear()
        
        # Clear file list layout
        while self.file_list_layout.count() > 1:  # Keep stretch at the end
            item = self.file_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Reset file count
        self.file_count_label.setText("Files: 0")
        
        # Disable selection buttons
        self.select_all_btn.setEnabled(False)
        self.select_none_btn.setEnabled(False)
        
        # Clear prefix/suffix
        self.prefix_entry.clear()
        self.suffix_entry.clear()
        
        # Reset preview
        self.preview_label.setText("example.txt → example.txt")
        
        # Create new default output folder for next operation
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_output = Path.cwd() / "execution test" / "Output" / f"file_rename_{timestamp}"
        default_output.mkdir(parents=True, exist_ok=True)
        self.output_path = default_output
        self.output_entry.setText(str(self.output_path))
        
        # Disable rename button
        self.rename_btn.setEnabled(False)
        
        # Hide progress bar
        self.progress_bar.setVisible(False)
        
        self.log("🔄 Tool reset for new operation!")
        self.log(f"📁 New output folder: {self.output_path}")
    
    def on_worker_thread_finished(self):
        """Called when worker thread finishes"""
        try:
            # Get the sender to identify which thread finished
            sender = self.sender()
            
            # CRITICAL FIX: Only process if this is from the CURRENT worker thread
            # This prevents old threads from interfering with new ones
            if sender != self.worker_thread:
                self.log("⚠️  Ignoring signal from old worker thread")
                return
            
            self.log("🌊 Worker thread finished")
            
            # Only clean up worker - button states already reset by on_rename_complete
            # Reset UI only if not already reset
            if self.is_renaming:
                self.is_renaming = False
                self.rename_btn.setEnabled(True)
                self.rename_btn.setText("🚀 Rename Files")
                self.scan_btn.setEnabled(True)
            
            self.progress_bar.setVisible(False)
            
            # Clean up worker and thread references
            self.worker = None
            self.worker_thread = None
            
            self.update_rename_button_state()
            self.log("✅ Worker thread cleanup completed")
            
        except Exception as e:
            self.log(f"❌ Error in on_worker_thread_finished: {str(e)}")
            import traceback
            # Try to reset UI anyway
            try:
                self.is_renaming = False
                self.rename_btn.setEnabled(True)
                self.rename_btn.setText("🚀 Rename Files")
                self.scan_btn.setEnabled(True)
                self.progress_bar.setVisible(False)
            except Exception as e2:
                pass
    
    def show_message(self, title: str, message: str, msg_type: str = "info"):
        """Show message box"""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        
        if msg_type == "success":
            msg_box.setIcon(QMessageBox.Information)
        elif msg_type == "warning":
            msg_box.setIcon(QMessageBox.Warning)
        elif msg_type == "error":
            msg_box.setIcon(QMessageBox.Critical)
        else:
            msg_box.setIcon(QMessageBox.Information)
        
        msg_box.exec()
    
    def closeEvent(self, event):
        """Handle window close"""
        if self.is_renaming:
            reply = QMessageBox.question(
                self, "Confirm Close",
                "Rename operation is in progress. Are you sure you want to close?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                event.ignore()
                return
            
            # Stop worker and cleanup
            if self.worker:
                self.worker.stop()
            
            # Wait for thread to finish
            if self.worker_thread and self.worker_thread.isRunning():
                self.worker_thread.quit()
                self.worker_thread.wait(3000)
        
        # Clean up resources
        if self.worker_thread and self.worker_thread.isRunning():
            self.worker_thread.quit()
            self.worker_thread.wait(1000)
        
        event.accept()


def main():
    """Main entry point"""
    app = QApplication(sys.argv)
    tool = FileRenamerTool()
    tool.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

