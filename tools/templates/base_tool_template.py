"""
🌊 Base Tool Template - For Creating New GA4 Tools 🌊
Inherit from this class to get theme support automatically!

USAGE:
    from tools.base_tool_template import BaseToolDialog
    
    class MyNewTool(BaseToolDialog):
        def __init__(self, parent, input_path, output_path):
            super().__init__(parent, input_path, output_path)
            # Your tool is now theme-aware! ✨
"""

import sys
from pathlib import Path
from typing import Optional, Dict

from PySide6.QtWidgets import QDialog
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

# Import NEW theme system ✨
try:
    from styles import ThemeLoader, get_theme_manager, get_path_manager, get_log_manager
    from styles.components import ExecutionLogFooter, create_execution_log_footer
    THEME_AVAILABLE = True
except ImportError:
    # Add parent directory to path for standalone execution
    sys.path.insert(0, str(Path(__file__).parent.parent))
    try:
        from styles import ThemeLoader, get_theme_manager, get_path_manager, get_log_manager
        from styles.components import ExecutionLogFooter, create_execution_log_footer
        THEME_AVAILABLE = True
    except ImportError:
        # Ultimate fallback
        THEME_AVAILABLE = False
        print("⚠️  Theme not available, using default styling")
        ExecutionLogFooter = None
        get_log_manager = lambda: None
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
                # - allocate_run_directory() helper for PathManager switch-case
                
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

        self.path_manager = get_path_manager()
        self._path_listener_registered = False

        # Unified logging
        self.log_manager = None
        self.log_category = f"TOOL:{self.__class__.__name__}"
        self._tool_logger_id = f"{self.__class__.__name__}_{id(self)}"
        try:
            if callable(get_log_manager):
                self.log_manager = get_log_manager()
        except Exception:
            self.log_manager = None

        self.execution_log = None
        self._suppress_footer_callback = False

        default_input = self.path_manager.get_input_path()
        default_output = self.path_manager.get_output_path()

        resolved_input = Path(input_path).expanduser().resolve() if input_path else default_input
        resolved_output = Path(output_path).expanduser().resolve() if output_path else default_output

        self.input_path = resolved_input
        self.output_path = resolved_output

        # Synchronize with global manager when explicit overrides are provided
        if input_path:
            self.path_manager.set_input_path(resolved_input)
        if output_path:
            self.path_manager.set_output_path(resolved_output)

        self.path_manager.register_listener(self._handle_paths_changed)
        self._path_listener_registered = True

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

    def allocate_run_directory(
        self,
        tool_name: str,
        *,
        script_name: Optional[str] = None,
        sync_paths: bool = True,
        announce: bool = True,
    ) -> Dict[str, Path]:
        """Request a run directory from the PathManager and optionally sync paths/log it."""

        info = self.path_manager.prepare_tool_output(
            tool_name,
            script_name=script_name,
        )
        run_root = info.get("root")
        if run_root is None:
            raise RuntimeError(f"PathManager did not return a run directory for {tool_name}.")

        if sync_paths:
            run_root = Path(run_root)
            self.output_path = run_root
            self._sync_path_edits(Path(self.input_path), run_root)

        if announce and hasattr(self, "log"):
            try:
                self.log(f"📁 Output run directory: {run_root}")
            except Exception:
                pass

        return info

    def _handle_paths_changed(self, input_path: Path, output_path: Path) -> None:
        """Keep local state aligned with the shared path manager."""
        self._sync_path_edits(input_path, output_path)

    def _sync_path_edits(self, input_path: Path, output_path: Path) -> None:
        """Update internal path state (UI mixins extend this)."""
        self.input_path = input_path
        self.output_path = output_path
        if hasattr(self, "execution_log") and self.execution_log:
            try:
                if hasattr(self.execution_log, "set_output_path"):
                    self.execution_log.set_output_path(str(output_path))
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Logging helpers
    # ------------------------------------------------------------------
    def log_event(
        self,
        message: str,
        *,
        level: str = "INFO",
        category: Optional[str] = None,
        mirror_to_footer: bool = True,
    ) -> None:
        """
        Relay a tool event to the unified session log (and optionally the UI).

        Args:
            message: Event description.
            level: Logging severity indicator.
            category: Override for session category (defaults to tool identifier).
            mirror_to_footer: Whether to echo into the execution footer.
        """
        category_name = category or self.log_category

        if self.log_manager:
            try:
                self.log_manager.log_event(category_name, message, level)
            except Exception:
                pass

        if mirror_to_footer and hasattr(self, "execution_log") and self.execution_log:
            try:
                self._suppress_footer_callback = True
                self.execution_log.log(message)
            except Exception:
                pass
            finally:
                self._suppress_footer_callback = False

    # Backwards compatibility for existing tools still calling self.log(...)
    def log(self, message: str, level: str = "INFO") -> None:
        """Compatibility wrapper for legacy tools."""
        self.log_event(message, level=level)

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

    def closeEvent(self, event):
        """Ensure path manager listeners are released on close."""
        if self._path_listener_registered:
            try:
                self.path_manager.unregister_listener(self._handle_paths_changed)
            except Exception:
                pass
            finally:
                self._path_listener_registered = False

        self.log_event("Tool dialog closed.", mirror_to_footer=False)
        super().closeEvent(event)

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
            self.execution_log = execution_log

            # Mirror footer actions into the unified log
            if hasattr(execution_log, "log_cleared"):
                execution_log.log_cleared.connect(self._log_footer_cleared)
            if hasattr(execution_log, "log_saved"):
                execution_log.log_saved.connect(self._log_footer_saved)
            if hasattr(execution_log, "log_appended"):
                execution_log.log_appended.connect(self._log_footer_appended)

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

    # ------------------------------------------------------------------
    # Execution log callbacks
    # ------------------------------------------------------------------
    def _log_footer_cleared(self) -> None:
        """Ensure log clear actions are persisted in the session log."""
        self.log_event("Execution log cleared by user.", mirror_to_footer=False)

    def _log_footer_saved(self, file_path: str) -> None:
        """Record when the execution log is saved to disk."""
        self.log_event(f"Execution log saved to: {file_path}", mirror_to_footer=False)

    def _log_footer_appended(self, message: str) -> None:
        """
        Capture messages injected directly via the footer (e.g., copy confirmation),
        ensuring they reach the unified session log.
        """
        if getattr(self, "_suppress_footer_callback", False):
            return
        self.log_event(message, mirror_to_footer=False)

