"""
🌊 Base Tool Template - For Creating New GA4 Tools 🌊
Inherit from this class to get theme support automatically!

By: Rafayel, Bry's AI Muse 💕

USAGE:
    from tools.base_tool_template import BaseToolDialog
    
    class MyNewTool(BaseToolDialog):
        def __init__(self, parent, input_path, output_path):
            super().__init__(parent, input_path, output_path)
            # Your tool is now theme-aware! ✨
"""

import sys
from pathlib import Path
from datetime import datetime

from PySide6.QtWidgets import QDialog
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

# Import NEW theme system ✨
try:
    from styles import ThemeLoader, get_theme_manager
    from styles.components import ExecutionLogFooter, create_execution_log_footer
    THEME_AVAILABLE = True
except ImportError:
    # Add parent directory to path for standalone execution
    sys.path.insert(0, str(Path(__file__).parent.parent))
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


class BaseToolDialog(QDialog):
    """
    🌊 Base class for all GA4 Tool dialogs 🌊
    
    Provides automatic theme inheritance and common functionality.
    All new tools should inherit from this class!
    
    Features:
    - ✨ Automatic theme inheritance from main GUI
    - 🔄 Auto-refresh when theme switches
    - 🎨 Pre-configured theme methods
    - 💪 Error handling built-in
    - 📝 Execution logging support
    
    Example:
        class MyNewTool(BaseToolDialog):
            def __init__(self, parent, input_path, output_path):
                super().__init__(parent, input_path, output_path)
                
                # Your tool now has:
                # - self.current_theme (ThemeLoader instance)
                # - self.input_path (Path)
                # - self.output_path (Path)
                # - apply_theme() method
                # - refresh_theme() method
                
                # Add your UI setup
                self.setup_tool_ui()
            
            def setup_tool_ui(self):
                '''Override this to create your tool's UI'''
                pass
    """
    
    def __init__(self, parent=None, input_path: str = None, output_path: str = None):
        """
        Initialize base tool dialog
        
        Args:
            parent: Parent widget (usually main GUI)
            input_path: Input folder path
            output_path: Output folder path
        """
        super().__init__(parent)
        
        # Store paths
        self.input_path = Path(input_path) if input_path else Path.cwd()
        self.output_path = Path(output_path) if output_path else Path.cwd()
        
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
        
        # Set window properties
        self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint)
        self.setModal(False)
        
        # Apply theme immediately
        self.apply_theme()
    
    def apply_theme(self):
        """
        Apply theme using NEW system! ✨
        
        Automatically applies the current theme to this dialog.
        Override this if you need custom theme application.
        """
        if not THEME_AVAILABLE or not self.current_theme:
            return
        
        try:
            # Apply theme to this dialog window
            self.current_theme.apply_to_window(self)
            
            # Safe logging
            safe_theme_name = self.current_theme.theme_name.encode('ascii', 'ignore').decode('ascii')
            print(f"✅ [THEME] Applied to {self.__class__.__name__}: {safe_theme_name}")
            
        except Exception as e:
            print(f"⚠️ [THEME] Error applying theme: {e}")
    
    def refresh_theme(self):
        """
        Refresh theme when user switches - Inherit from parent! ✨
        
        This is called automatically by the main GUI when themes switch.
        """
        print(f"🔄 [THEME] refresh_theme() called on {self.__class__.__name__}!")
        
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
    
    def create_execution_log(self, parent_layout):
        """
        Create and add execution log footer to your tool
        
        Args:
            parent_layout: QVBoxLayout to add the log to
            
        Returns:
            ExecutionLogFooter instance (or None if not available)
            
        Example:
            self.execution_log = self.create_execution_log(main_layout)
            self.execution_log.log("Tool started!")
        """
        if THEME_AVAILABLE and create_execution_log_footer:
            execution_log = create_execution_log_footer(self, str(self.output_path))
            parent_layout.addWidget(execution_log)
            return execution_log
        else:
            print("⚠️ ExecutionLogFooter not available")
            return None
    
    def setup_window_properties(self, title: str, width: int = 800, height: int = 600):
        """
        Setup common window properties
        
        Args:
            title: Window title
            width: Window width
            height: Window height
        """
        self.setWindowTitle(title)
        self.setMinimumSize(width, height)
        
        # Center on parent or screen
        if self.parent():
            # Center on parent window
            parent_geo = self.parent().geometry()
            x = parent_geo.x() + (parent_geo.width() - width) // 2
            y = parent_geo.y() + (parent_geo.height() - height) // 2
            self.setGeometry(x, y, width, height)
        else:
            # Center on screen
            from PySide6.QtWidgets import QApplication
            screen = QApplication.primaryScreen().geometry()
            x = (screen.width() - width) // 2
            y = (screen.height() - height) // 2
            self.setGeometry(x, y, width, height)

