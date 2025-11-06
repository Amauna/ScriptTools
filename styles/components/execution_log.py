#!/usr/bin/env python3
"""
🌊 Reusable Execution Log Component - PySide6 Edition 🌊
A beautiful, theme-aware execution log footer that all tools can use!
Like HTML navigation components but for PySide6 tools! ✨
"""

import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTextEdit, QWidget, QApplication
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

# Import NEW theme system ✨
try:
    from styles import get_theme_manager
    THEME_AVAILABLE = True
    theme_manager = get_theme_manager()
except ImportError:
    THEME_AVAILABLE = False
    theme_manager = None
    print("⚠️ Theme system not available, using default styling")


class ExecutionLogFooter(QFrame):
    """
    🌊 Beautiful Reusable Execution Log Footer Component 🌊
    
    This component provides a consistent execution log footer for all tools,
    similar to how websites have reusable header/footer components!
    
    Features:
    - 📋 Copy logs to clipboard
    - 🔄 Reset/clear logs
    - 💾 Save logs to txt file
    - 🎨 Theme-aware styling
    - 📝 Individual logging per tool instance
    """
    
    # Signals for communication with parent tool
    log_cleared = Signal()
    log_saved = Signal(str)  # Emits file path when saved
    
    def __init__(self, parent=None, output_path: Optional[str] = None):
        super().__init__(parent)
        
        self.output_path = output_path or str(Path.home() / "Documents")
        self.execution_log: List[str] = []
        
        # Setup UI
        self.setup_ui()
        
        # Apply theme
        self.apply_theme()
    
    def setup_ui(self):
        """Setup beautiful execution log footer UI"""
        self.setObjectName("executionLogFooter")
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 10, 15, 15)
        main_layout.setSpacing(10)
        
        # Header with title and buttons
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        # Title
        title = QLabel("📋 Execution Log")
        title.setFont(QFont("Arial", 13, QFont.Bold))
        title.setObjectName("logTitle")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Action buttons
        self.copy_btn = QPushButton("📋 Copy")
        self.copy_btn.setObjectName("logButton")
        self.copy_btn.setFixedSize(90, 30)
        self.copy_btn.clicked.connect(self.copy_log)
        header_layout.addWidget(self.copy_btn)
        
        self.reset_btn = QPushButton("🔄 Reset")
        self.reset_btn.setObjectName("logButton")
        self.reset_btn.setFixedSize(90, 30)
        self.reset_btn.clicked.connect(self.reset_log)
        header_layout.addWidget(self.reset_btn)
        
        self.save_btn = QPushButton("💾 Save")
        self.save_btn.setObjectName("logButton")
        self.save_btn.setFixedSize(90, 30)
        self.save_btn.clicked.connect(self.save_log)
        header_layout.addWidget(self.save_btn)
        
        main_layout.addWidget(header_widget)
        
        # Log text area
        self.log_text = QTextEdit()
        self.log_text.setObjectName("logText")
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(200)
        self.log_text.setFont(QFont("Consolas", 9))
        main_layout.addWidget(self.log_text, 1)
    
    def log(self, message: str):
        """
        Add a log message with timestamp
        
        Args:
            message: The log message to add
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        
        # Store in internal log
        self.execution_log.append(formatted_message)
        
        # Display in text area
        if hasattr(self, 'log_text'):
            self.log_text.append(formatted_message)
            # Auto-scroll to bottom
            self.log_text.verticalScrollBar().setValue(
                self.log_text.verticalScrollBar().maximum()
            )
    
    def copy_log(self):
        """Copy all logs to clipboard"""
        try:
            clipboard = QApplication.clipboard()
            log_content = self.log_text.toPlainText()
            clipboard.setText(log_content)
            
            # Show brief feedback
            original_text = self.copy_btn.text()
            self.copy_btn.setText("✅ Copied!")
            self.copy_btn.setEnabled(False)
            
            # Reset button after 2 seconds
            from PySide6.QtCore import QTimer
            QTimer.singleShot(2000, lambda: [
                self.copy_btn.setText(original_text),
                self.copy_btn.setEnabled(True)
            ])
            
        except Exception as e:
            self.log(f"⚠️ Failed to copy logs: {str(e)}")
    
    def reset_log(self):
        """Clear all logs"""
        try:
            self.log_text.clear()
            self.execution_log.clear()
            
            # Show brief feedback
            original_text = self.reset_btn.text()
            self.reset_btn.setText("✅ Cleared!")
            self.reset_btn.setEnabled(False)
            
            # Reset button after 2 seconds
            from PySide6.QtCore import QTimer
            QTimer.singleShot(2000, lambda: [
                self.reset_btn.setText(original_text),
                self.reset_btn.setEnabled(True)
            ])
            
            # Emit signal
            self.log_cleared.emit()
            self.log("🌊 Log cleared!")
            
        except Exception as e:
            self.log(f"⚠️ Failed to clear logs: {str(e)}")
    
    def save_log(self):
        """Save logs to txt file"""
        try:
            if not self.execution_log:
                self.log("⚠️ No logs to save!")
                return
            
            # Create logs directory
            logs_dir = Path(self.output_path) / "logs"
            logs_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = logs_dir / f"execution_log_{timestamp}.txt"
            
            # Write logs to file
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write("="*80 + "\n")
                f.write("🌊 EXECUTION LOG\n")
                f.write("="*80 + "\n\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Total Entries: {len(self.execution_log)}\n")
                f.write("-"*80 + "\n\n")
                
                for log_entry in self.execution_log:
                    f.write(f"{log_entry}\n")
                
                f.write("\n" + "="*80 + "\n")
                f.write("End of Execution Log\n")
                f.write("="*80 + "\n")
            
            # Show brief feedback
            original_text = self.save_btn.text()
            self.save_btn.setText("✅ Saved!")
            self.save_btn.setEnabled(False)
            
            # Reset button after 3 seconds
            from PySide6.QtCore import QTimer
            QTimer.singleShot(3000, lambda: [
                self.save_btn.setText(original_text),
                self.save_btn.setEnabled(True)
            ])
            
            # Emit signal with file path
            self.log_saved.emit(str(log_file))
            self.log(f"💾 Logs saved to: {log_file.name}")
            
        except Exception as e:
            self.log(f"⚠️ Failed to save logs: {str(e)}")
    
    def get_log_count(self) -> int:
        """Get the number of log entries"""
        return len(self.execution_log)
    
    def get_log_content(self) -> str:
        """Get all log content as string"""
        return self.log_text.toPlainText()
    
    def set_output_path(self, path: str):
        """Set the output path for saving logs"""
        self.output_path = path
    
    def apply_theme(self):
        """Apply theme-aware styling"""
        # Styling is handled by global stylesheet via object names
        # The NEW theme system applies styles automatically through the main GUI
        pass


def create_execution_log_footer(parent=None, output_path: Optional[str] = None) -> ExecutionLogFooter:
    """
    🌊 Factory function to create an execution log footer 🌊
    
    This makes it super easy for any tool to add an execution log footer!
    Just call: execution_log = create_execution_log_footer(self, self.output_path)
    
    Args:
        parent: Parent widget (usually the tool dialog)
        output_path: Path where logs should be saved
        
    Returns:
        ExecutionLogFooter: Ready-to-use execution log component
    """
    return ExecutionLogFooter(parent, output_path)


# Example usage for tools:
"""
# In any tool's __init__ method:
from styles.components.execution_log import create_execution_log_footer

class MyTool(QDialog):
    def __init__(self, parent, input_path, output_path):
        super().__init__(parent)
        
        # Create main layout
        main_layout = QVBoxLayout(self)
        
        # Add your tool content here...
        
        # Add execution log footer
        self.execution_log = create_execution_log_footer(self, output_path)
        main_layout.addWidget(self.execution_log)
        
        # Now you can log messages anywhere in your tool:
        self.execution_log.log("Tool initialized!")
        self.execution_log.log("Processing data...")
        self.execution_log.log("✅ Complete!")
"""
