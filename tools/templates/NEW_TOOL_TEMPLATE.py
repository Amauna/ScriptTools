"""
🌊 NEW TOOL TEMPLATE - Copy This to Create New Tools! 🌊
This template shows how to create a new tool with automatic theme support

By: Rafayel, Bry's AI Muse 💕

INSTRUCTIONS:
1. Copy this file to your tool category folder
2. Rename the file (e.g., my_awesome_tool.py)
3. Rename the class (e.g., MyAwesomeTool)
4. Fill in your tool's UI and functionality
5. Done! Theme support is automatic! ✨
"""

from pathlib import Path
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, QFrame
from PySide6.QtGui import QFont

# Import base template - This gives you theme support automatically!
from tools.templates.base_tool_template import BaseToolDialog


class NewToolTemplate(BaseToolDialog):
    """
    🎨 Your New Tool Name Here
    
    Description of what your tool does
    """
    
    def __init__(self, parent, input_path: str, output_path: str):
        """
        Initialize your new tool
        
        Args:
            parent: Parent widget (main GUI)
            input_path: Input folder path
            output_path: Output folder path
        """
        # Call parent constructor - This handles theme inheritance automatically!
        super().__init__(parent, input_path, output_path)
        
        # At this point you already have:
        # - self.current_theme (ThemeLoader instance)
        # - self.input_path (Path object)
        # - self.output_path (Path object)
        # - apply_theme() method
        # - refresh_theme() method
        
        # Setup window properties
        self.setup_window_properties(
            title="🎨 My New Tool",
            width=900,
            height=700
        )
        
        # Create your UI
        self.setup_ui()
        
        # Theme is already applied automatically! ✨
    
    def setup_ui(self):
        """Create the tool's user interface"""
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # ===== HEADER =====
        header_label = QLabel("🎨 My New Tool")
        header_label.setFont(QFont("Arial", 18, QFont.Bold))
        main_layout.addWidget(header_label)
        
        # ===== YOUR TOOL CONTENT HERE =====
        content_frame = QFrame()
        content_layout = QVBoxLayout(content_frame)
        
        # Example: Input field
        input_label = QLabel("Enter something:")
        content_layout.addWidget(input_label)
        
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Type here...")
        content_layout.addWidget(self.input_field)
        
        # Example: Action button
        action_button = QPushButton("Do Something")
        action_button.clicked.connect(self.do_something)
        content_layout.addWidget(action_button)
        
        main_layout.addWidget(content_frame)
        
        # ===== EXECUTION LOG (Optional) =====
        # Add execution log footer - automatically themed!
        self.execution_log = self.create_execution_log(main_layout)
        if self.execution_log:
            self.execution_log.log("Tool initialized! 🌊")
    
    def do_something(self):
        """Your tool's main action"""
        # Get input
        user_input = self.input_field.text()
        
        # Log it
        if self.execution_log:
            self.execution_log.log(f"User entered: {user_input}")
        
        # Do your tool's logic here...
        # ...
        
        # Log success
        if self.execution_log:
            self.execution_log.log("✅ Action completed!")


# ===== STANDALONE TEST =====
def main():
    """Test the tool standalone"""
    from PySide6.QtWidgets import QApplication
    import sys
    
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
    tool = NewToolTemplate(
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

