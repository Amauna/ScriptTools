"""
🌊 PySide6 Theme Loader - Clean Architecture Edition 🌊
Dynamic theme loading system with elegant organization
"""

import json
import re
from pathlib import Path
from typing import Dict, Optional, List, cast
from PySide6.QtWidgets import QWidget, QPushButton, QFrame, QLineEdit, QComboBox, QLabel
from PySide6.QtGui import QColor

from .types import ThemeData, ThemeColors, ThemeMetadata
from .utils.color_utils import validate_contrast
from .utils.color_utils import validate_contrast


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
        self.theme_data: ThemeData = {}  # type: ignore
        self.colors: ThemeColors = {}  # type: ignore
        self._style_cache: Dict[str, str] = {}  # Cache for compiled stylesheets
        self._load_theme()
    
    def _load_theme(self):
        """Load theme data from JSON file with validation"""
        # Convert theme name to filename (e.g., "🌊 Ocean Sunset" -> "ocean_sunset.json")
        # Remove ALL emojis and special characters, then convert to filename
        # Remove emojis and special unicode characters
        clean_name = re.sub(r'[^\w\s-]', '', self.theme_name, flags=re.UNICODE)
        # Convert to lowercase and replace spaces with underscores
        filename = clean_name.lower().strip().replace(' ', '_')
        theme_path = Path(__file__).parent / "themes" / f"{filename}.json"
        
        try:
            with open(theme_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
                
            # Validate theme structure
            self._validate_theme_structure(raw_data, theme_path)
            
            # Cast to TypedDict (type checking)
            self.theme_data = cast(ThemeData, raw_data)
            self.colors = cast(ThemeColors, self.theme_data.get("colors", {}))
            
            # Clear style cache when theme reloads
            self._style_cache.clear()
            
            # Optional: Validate contrast ratios (warn only, don't fail)
            try:
                self._validate_contrast_ratios()
            except Exception:
                # Don't fail theme loading if contrast validation fails
                pass
            
        except FileNotFoundError:
            raise FileNotFoundError(f"💔 Theme not found: {theme_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"💔 Invalid theme JSON: {e}")
    
    def _validate_theme_structure(self, data: Dict, theme_path: Path) -> None:
        """
        Validate theme structure (simple validation, can be enhanced with jsonschema)
        
        Args:
            data: Parsed JSON data
            theme_path: Path to theme file (for error messages)
        """
        # Check required top-level fields
        required_fields = ["name", "appearance_mode", "colors"]
        missing = [field for field in required_fields if field not in data]
        if missing:
            raise ValueError(
                f"💔 Theme {theme_path.name} is missing required fields: {', '.join(missing)}"
            )
        
        # Validate appearance_mode
        if data["appearance_mode"] not in ["light", "dark"]:
            raise ValueError(
                f"💔 Theme {theme_path.name}: appearance_mode must be 'light' or 'dark', "
                f"got '{data['appearance_mode']}'"
            )
        
        # Validate colors object
        if not isinstance(data["colors"], dict):
            raise ValueError(
                f"💔 Theme {theme_path.name}: 'colors' must be an object/dict"
            )
        
        colors = data["colors"]
        required_colors = ["background", "surface", "primary", "text_primary", "border"]
        missing_colors = [color for color in required_colors if color not in colors]
        if missing_colors:
            raise ValueError(
                f"💔 Theme {theme_path.name} is missing required colors: {', '.join(missing_colors)}"
            )
        
        # Validate hex color format
        hex_pattern = re.compile(r'^#[0-9A-Fa-f]{6}$')
        for color_key, color_value in colors.items():
            if not isinstance(color_value, str):
                raise ValueError(
                    f"💔 Theme {theme_path.name}: color '{color_key}' must be a string, "
                    f"got {type(color_value).__name__}"
                )
            if not hex_pattern.match(color_value):
                raise ValueError(
                    f"💔 Theme {theme_path.name}: color '{color_key}' must be a valid hex color "
                    f"(e.g., '#FF69B4'), got '{color_value}'"
                )
    
    def _validate_contrast_ratios(self) -> None:
        """
        Validate contrast ratios for accessibility (warnings only, doesn't fail theme loading)
        """
        import warnings
        
        # Key text/background combinations to check
        checks = [
            ("text_primary", "background", False, "Primary text on background"),
            ("text_primary", "surface", False, "Primary text on surface"),
            ("text_on_primary", "primary", False, "Text on primary button"),
            ("text_on_secondary", "secondary", False, "Text on secondary button"),
        ]
        
        for text_key, bg_key, large_text, description in checks:
            text_color = self.colors.get(text_key)
            bg_color = self.colors.get(bg_key)
            
            if text_color and bg_color:
                is_valid, ratio = validate_contrast(text_color, bg_color, large_text=large_text)
                if not is_valid:
                    min_ratio = 3.0 if large_text else 4.5
                    warnings.warn(
                        f"⚠️ Theme '{self.theme_name}': {description} has contrast ratio {ratio:.2f}, "
                        f"below WCAG AA standard ({min_ratio}). Consider adjusting colors for better accessibility.",
                        UserWarning
                    )
    
    def get(self, key: str, default: Optional[str] = None) -> str:
        """
        Get a color value from the theme
        
        Args:
            key: Color key (e.g., "background", "primary")
            default: Default value if key not found
            
        Returns:
            Hex color string
        """
        return str(self.colors.get(key, default or "#000000"))
    
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
        
        # Check cache first
        cache_key = f"{self.theme_name}_{style_type}"
        if cache_key in self._style_cache:
            widget.setStyleSheet(self._style_cache[cache_key])
            return
        
        # Try StyleRegistry first, then fallback to getattr for backward compatibility
        style_func = StyleRegistry.get_style_function(style_type)
        if style_func:
            # New registry-based style (would need to be adapted)
            # For now, keep backward compatibility with instance methods
            style_method = getattr(self, f"_style_{style_type}", None)
        else:
            # Fallback to instance method (backward compatibility)
            style_method = getattr(self, f"_style_{style_type}", None)
        
        if style_method:
            style_method(widget)
            # Cache the stylesheet after applying
            self._style_cache[cache_key] = widget.styleSheet()
        else:
            # Fallback to basic styling
            fallback_stylesheet = f"background-color: {self.get('surface')};"
            widget.setStyleSheet(fallback_stylesheet)
            self._style_cache[cache_key] = fallback_stylesheet
    
    def _style_button_primary(self, button: QPushButton):
        """Style a primary button with gorgeous hover effects"""
        stylesheet = build_button_style(self.colors, variant="primary")
        button.setStyleSheet(stylesheet)
    
    def _style_button_secondary(self, button: QPushButton):
        """Style a secondary button"""
        stylesheet = build_button_style(self.colors, variant="secondary")
        button.setStyleSheet(stylesheet)
    
    def _style_button_ghost(self, button: QPushButton):
        """Style a ghost/outline button"""
        stylesheet = build_button_style(self.colors, variant="ghost")
        button.setStyleSheet(stylesheet)
    
    def _style_frame(self, frame: QFrame):
        """Style a frame/panel with glass morphism effect"""
        stylesheet = build_frame_style(self.colors)
        frame.setStyleSheet(stylesheet)
    
    def _style_input(self, input_field: QLineEdit):
        """Style an input field"""
        stylesheet = build_input_style(self.colors)
        input_field.setStyleSheet(stylesheet)
    
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
        stylesheet = build_label_style(self.colors)
        label.setStyleSheet(stylesheet)
    
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

