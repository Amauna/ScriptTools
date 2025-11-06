"""
🌊 PySide6 Theme Loader - Clean Architecture Edition 🌊
Dynamic theme loading system with elegant organization

By: Rafayel, Bry's AI Muse 💕
"""

import json
from pathlib import Path
from typing import Dict, Optional, List
from PySide6.QtWidgets import QWidget, QPushButton, QFrame, QLineEdit, QComboBox, QLabel
from PySide6.QtGui import QColor


class ThemeLoader:
    """
    ✨ Elegant theme loader for PySide6
    Loads theme data from JSON and applies styles dynamically
    """
    
    def __init__(self, theme_name: str):
        """
        Initialize theme loader with a specific theme
        
        Args:
            theme_name: Name of the theme (e.g., "Ocean Sunset", "Blush Romance")
        """
        self.theme_name = theme_name
        self.theme_data = {}
        self.colors = {}
        self._load_theme()
    
    def _load_theme(self):
        """Load theme data from JSON file"""
        # Convert theme name to filename (e.g., "🌊 Ocean Sunset" -> "ocean_sunset.json")
        # Remove ALL emojis and special characters, then convert to filename
        import re
        # Remove emojis and special unicode characters
        clean_name = re.sub(r'[^\w\s-]', '', self.theme_name, flags=re.UNICODE)
        # Convert to lowercase and replace spaces with underscores
        filename = clean_name.lower().strip().replace(' ', '_')
        theme_path = Path(__file__).parent / "themes" / f"{filename}.json"
        
        try:
            with open(theme_path, "r", encoding="utf-8") as f:
                self.theme_data = json.load(f)
                self.colors = self.theme_data.get("colors", {})
        except FileNotFoundError:
            raise FileNotFoundError(f"💔 Theme not found: {theme_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"💔 Invalid theme JSON: {e}")
    
    def get(self, key: str, default: Optional[str] = None) -> str:
        """
        Get a color value from the theme
        
        Args:
            key: Color key (e.g., "background", "primary")
            default: Default value if key not found
            
        Returns:
            Hex color string
        """
        return self.colors.get(key, default or "#000000")
    
    def get_nested(self, *keys, default: Optional[str] = None) -> str:
        """
        Get nested values from theme data
        
        Example:
            theme.get_nested("colors", "primary") -> "#FF69B4"
        """
        data = self.theme_data
        for key in keys:
            if isinstance(data, dict):
                data = data.get(key)
            else:
                return default or "#000000"
        return data if data else default or "#000000"
    
    def is_dark_mode(self) -> bool:
        """Check if theme is dark mode"""
        return self.theme_data.get("appearance_mode", "light") == "dark"
    
    # 🎨 Widget Style Application Methods 🎨
    
    def apply_to_widget(self, widget: QWidget, style_type: str = "auto"):
        """
        Apply theme style to a widget automatically
        
        Args:
            widget: QWidget to style
            style_type: Type of style to apply (auto, button, frame, input, etc.)
        """
        if style_type == "auto":
            # Auto-detect widget type
            if isinstance(widget, QPushButton):
                style_type = "button_primary"
            elif isinstance(widget, QFrame):
                style_type = "frame"
            elif isinstance(widget, QLineEdit):
                style_type = "input"
            elif isinstance(widget, QComboBox):
                style_type = "combo"
            elif isinstance(widget, QLabel):
                style_type = "label"
        
        # Apply appropriate style
        style_method = getattr(self, f"_style_{style_type}", None)
        if style_method:
            style_method(widget)
        else:
            # Fallback to basic styling
            widget.setStyleSheet(f"background-color: {self.get('surface')};")
    
    def _style_button_primary(self, button: QPushButton):
        """Style a primary button with gorgeous hover effects"""
        button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.get('primary')};
                color: {self.get('text_on_primary')};
                border: 2px solid {self.get('primary')};
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self.get('primary_hover')};
                border-color: {self.get('primary_hover')};
            }}
            QPushButton:pressed {{
                background-color: {self.get('primary')};
                transform: scale(0.98);
            }}
            QPushButton:disabled {{
                background-color: {self.get('surface_variant')};
                color: {self.get('text_secondary')};
                border-color: {self.get('border')};
            }}
        """)
    
    def _style_button_secondary(self, button: QPushButton):
        """Style a secondary button"""
        button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.get('secondary')};
                color: {self.get('text_on_secondary')};
                border: 2px solid {self.get('secondary')};
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self.get('secondary_hover')};
                border-color: {self.get('secondary_hover')};
            }}
            QPushButton:pressed {{
                background-color: {self.get('secondary')};
            }}
        """)
    
    def _style_button_ghost(self, button: QPushButton):
        """Style a ghost/outline button"""
        button.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {self.get('primary')};
                border: 2px solid {self.get('primary')};
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self.get('primary')};
                color: {self.get('text_on_primary')};
            }}
        """)
    
    def _style_frame(self, frame: QFrame):
        """Style a frame/panel with glass morphism effect"""
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {self.get('surface')};
                border: 1px solid {self.get('border')};
                border-radius: 12px;
                padding: 15px;
            }}
        """)
    
    def _style_input(self, input_field: QLineEdit):
        """Style an input field"""
        input_field.setStyleSheet(f"""
            QLineEdit {{
                background-color: {self.get('surface')};
                color: {self.get('text_primary')};
                border: 2px solid {self.get('border')};
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 14px;
            }}
            QLineEdit:focus {{
                border-color: {self.get('border_focus')};
            }}
            QLineEdit:disabled {{
                background-color: {self.get('surface_variant')};
                color: {self.get('text_secondary')};
            }}
        """)
    
    def _style_combo(self, combo: QComboBox):
        """Style a combobox (dropdown)"""
        combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {self.get('surface')};
                color: {self.get('text_primary')};
                border: 2px solid {self.get('border')};
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 14px;
                min-width: 150px;
            }}
            QComboBox:hover {{
                border-color: {self.get('primary')};
            }}
            QComboBox:focus {{
                border-color: {self.get('border_focus')};
            }}
            QComboBox::drop-down {{
                border: none;
                padding-right: 10px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid {self.get('text_primary')};
                margin-right: 5px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {self.get('surface')};
                color: {self.get('text_primary')};
                border: 2px solid {self.get('border')};
                border-radius: 8px;
                selection-background-color: {self.get('primary')};
                selection-color: {self.get('text_on_primary')};
                padding: 5px;
            }}
            QComboBox QAbstractItemView::item {{
                padding: 8px;
                border-radius: 4px;
            }}
            QComboBox QAbstractItemView::item:hover {{
                background-color: {self.get('surface_variant')};
            }}
        """)
    
    def _style_label(self, label: QLabel):
        """Style a label"""
        label.setStyleSheet(f"""
            QLabel {{
                color: {self.get('text_primary')};
                font-size: 14px;
            }}
        """)
    
    def apply_to_window(self, window: QWidget):
        """
        Apply theme to entire window/application
        
        Args:
            window: Main window widget
        """
        window.setStyleSheet(f"""
            QWidget {{
                background-color: {self.get('background')};
                color: {self.get('text_primary')};
                font-family: 'Segoe UI', Arial, sans-serif;
            }}
        """)
    
    def get_qcolor(self, key: str) -> QColor:
        """
        Get QColor object for a theme color
        
        Args:
            key: Color key
            
        Returns:
            QColor object
        """
        hex_color = self.get(key)
        return QColor(hex_color)


class ThemeManager:
    """
    🎭 Central theme management system
    Handles theme switching and provides theme list
    """
    
    def __init__(self, themes_dir: Optional[Path] = None):
        """
        Initialize theme manager
        
        Args:
            themes_dir: Path to themes directory (defaults to styles/themes)
        """
        if themes_dir is None:
            themes_dir = Path(__file__).parent / "themes"
        
        self.themes_dir = Path(themes_dir)
        self.available_themes = []
        self.current_theme: Optional[ThemeLoader] = None
        self._scan_themes()
    
    def _scan_themes(self):
        """Scan themes directory for available themes"""
        if not self.themes_dir.exists():
            raise FileNotFoundError(f"💔 Themes directory not found: {self.themes_dir}")
        
        for theme_file in self.themes_dir.glob("*.json"):
            try:
                with open(theme_file, "r", encoding="utf-8") as f:
                    theme_data = json.load(f)
                    theme_name = theme_data.get("name", theme_file.stem.replace("_", " ").title())
                    self.available_themes.append(theme_name)
            except Exception as e:
                print(f"⚠️ Failed to load theme {theme_file.name}: {e}")
        
        # Sort themes alphabetically
        self.available_themes.sort()
    
    def get_available_themes(self) -> List[str]:
        """Get list of all available theme names"""
        return self.available_themes.copy()
    
    def load_theme(self, theme_name: str) -> ThemeLoader:
        """
        Load a specific theme
        
        Args:
            theme_name: Name of the theme
            
        Returns:
            ThemeLoader instance
        """
        self.current_theme = ThemeLoader(theme_name)
        return self.current_theme
    
    def get_current_theme(self) -> Optional[ThemeLoader]:
        """Get currently loaded theme"""
        return self.current_theme


# 🌊 Global theme manager instance 🌊
_theme_manager = None

def get_theme_manager() -> ThemeManager:
    """Get global theme manager instance (singleton pattern)"""
    global _theme_manager
    if _theme_manager is None:
        _theme_manager = ThemeManager()
    return _theme_manager

