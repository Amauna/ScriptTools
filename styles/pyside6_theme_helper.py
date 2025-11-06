"""
🌊 PySide6 Theme Helper
Easy theme application for PySide6 widgets with glass morphism
"""

from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QPalette, QColor
from typing import Dict
from .components.pyside6_styles import (
    get_app_stylesheet,
    get_glass_button_style,
    get_glass_frame_style,
    get_modern_input_style,
    hex_to_rgba
)

def apply_theme_to_app(app: QApplication, theme_colors: Dict):
    """
    Apply theme to entire application with beautiful glass effects
    
    Args:
        app: QApplication instance
        theme_colors: Theme color dictionary from theme manager
    """
    # Get complete stylesheet
    stylesheet = get_app_stylesheet(theme_colors)
    app.setStyleSheet(stylesheet)
    
    # Set application palette for native widgets
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(theme_colors["background"]))
    palette.setColor(QPalette.WindowText, QColor(theme_colors["text_primary"]))
    palette.setColor(QPalette.Base, QColor(theme_colors["surface"]))
    palette.setColor(QPalette.AlternateBase, QColor(theme_colors["surface_variant"]))
    palette.setColor(QPalette.Text, QColor(theme_colors["text_primary"]))
    palette.setColor(QPalette.Button, QColor(theme_colors["primary"]))
    palette.setColor(QPalette.ButtonText, QColor(theme_colors["text_on_primary"]))
    palette.setColor(QPalette.Highlight, QColor(theme_colors["primary"]))
    palette.setColor(QPalette.HighlightedText, QColor(theme_colors["text_on_primary"]))
    
    app.setPalette(palette)

def apply_glass_effect(widget: QWidget, theme_colors: Dict):
    """
    Apply glass morphism effect to a widget
    
    Args:
        widget: QWidget to apply effect to
        theme_colors: Theme color dictionary
    """
    # Enable transparency
    widget.setAttribute(Qt.WA_TranslucentBackground)
    
    # Apply glass stylesheet
    widget.setStyleSheet(get_glass_frame_style(theme_colors, blur=True))

def create_gradient_background(widget: QWidget, theme_colors: Dict, direction: str = "vertical"):
    """
    Apply gradient background to widget
    
    Args:
        widget: QWidget to apply gradient to
        theme_colors: Theme color dictionary
        direction: "vertical", "horizontal", "diagonal"
    """
    from .components.pyside6_styles import create_gradient
    
    gradient = create_gradient(
        theme_colors["background"],
        theme_colors["surface"],
        direction
    )
    
    widget.setStyleSheet(f"""
        QWidget {{
            background: {gradient};
            border: none;
        }}
    """)

def get_modern_card_style(theme_colors: Dict) -> str:
    """
    Get modern card/panel style with shadow effect
    
    Returns:
        QSS stylesheet string
    """
    return f"""
        QFrame {{
            background-color: {hex_to_rgba(theme_colors["surface"], 0.85)};
            border: 1px solid {hex_to_rgba(theme_colors["border"], 0.2)};
            border-radius: 12px;
            padding: 15px;
        }}
    """

def get_dialog_style(theme_colors: Dict) -> str:
    """
    Get beautiful dialog window style
    
    Returns:
        QSS stylesheet string
    """
    return f"""
        QDialog {{
            background: {hex_to_rgba(theme_colors["background"], 0.95)};
            border: 2px solid {theme_colors["border"]};
            border-radius: 15px;
        }}
    """

