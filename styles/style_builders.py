"""
🌊 Style Builders
Reusable style generation functions for common widget patterns
"""

from typing import Dict, Tuple


def build_button_style(
    colors: Dict[str, str],
    variant: str = "primary",
    radius: int = 8,
    padding: Tuple[int, int] = (10, 20),
    border_width: int = 2
) -> str:
    """
    Build button style stylesheet
    
    Args:
        colors: Theme colors dictionary
        variant: Button variant ("primary", "secondary", "ghost")
        radius: Border radius in pixels
        padding: Tuple of (vertical, horizontal) padding
        border_width: Border width in pixels
    
    Returns:
        QSS stylesheet string
    """
    padding_v, padding_h = padding
    
    if variant == "primary":
        bg_color = colors.get("primary", "#000000")
        hover_color = colors.get("primary_hover", bg_color)
        text_color = colors.get("text_on_primary", "#FFFFFF")
        border_color = bg_color
    elif variant == "secondary":
        bg_color = colors.get("secondary", "#808080")
        hover_color = colors.get("secondary_hover", bg_color)
        text_color = colors.get("text_on_secondary", "#FFFFFF")
        border_color = bg_color
    elif variant == "ghost":
        bg_color = "transparent"
        hover_color = colors.get("primary", "#000000")
        text_color = colors.get("primary", "#000000")
        border_color = colors.get("primary", "#000000")
    else:
        bg_color = colors.get("surface", "#FFFFFF")
        hover_color = colors.get("surface_variant", bg_color)
        text_color = colors.get("text_primary", "#000000")
        border_color = colors.get("border", "#CCCCCC")
    
    disabled_bg = colors.get("surface_variant", "#E0E0E0")
    disabled_text = colors.get("text_secondary", "#808080")
    disabled_border = colors.get("border", "#CCCCCC")
    
    if variant == "ghost":
        return f"""
            QPushButton {{
                background-color: {bg_color};
                color: {text_color};
                border: {border_width}px solid {border_color};
                border-radius: {radius}px;
                padding: {padding_v}px {padding_h}px;
                font-size: 14px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
                color: {colors.get('text_on_primary', '#FFFFFF')};
            }}
        """
    else:
        return f"""
            QPushButton {{
                background-color: {bg_color};
                color: {text_color};
                border: {border_width}px solid {border_color};
                border-radius: {radius}px;
                padding: {padding_v}px {padding_h}px;
                font-size: 14px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
                border-color: {hover_color};
            }}
            QPushButton:pressed {{
                background-color: {bg_color};
            }}
            QPushButton:disabled {{
                background-color: {disabled_bg};
                color: {disabled_text};
                border-color: {disabled_border};
            }}
        """


def build_frame_style(
    colors: Dict[str, str],
    radius: int = 12,
    padding: int = 15,
    border_width: int = 1
) -> str:
    """
    Build frame/panel style stylesheet
    
    Args:
        colors: Theme colors dictionary
        radius: Border radius in pixels
        padding: Padding in pixels
        border_width: Border width in pixels
    
    Returns:
        QSS stylesheet string
    """
    bg_color = colors.get("surface", "#FFFFFF")
    border_color = colors.get("border", "#CCCCCC")
    
    return f"""
        QFrame {{
            background-color: {bg_color};
            border: {border_width}px solid {border_color};
            border-radius: {radius}px;
            padding: {padding}px;
        }}
    """


def build_input_style(
    colors: Dict[str, str],
    radius: int = 8,
    padding: Tuple[int, int] = (8, 12),
    border_width: int = 2
) -> str:
    """
    Build input field style stylesheet
    
    Args:
        colors: Theme colors dictionary
        radius: Border radius in pixels
        padding: Tuple of (vertical, horizontal) padding
        border_width: Border width in pixels
    
    Returns:
        QSS stylesheet string
    """
    padding_v, padding_h = padding
    bg_color = colors.get("surface", "#FFFFFF")
    text_color = colors.get("text_primary", "#000000")
    border_color = colors.get("border", "#CCCCCC")
    focus_color = colors.get("border_focus", colors.get("primary", "#0000FF"))
    disabled_bg = colors.get("surface_variant", "#F0F0F0")
    disabled_text = colors.get("text_secondary", "#808080")
    
    return f"""
        QLineEdit {{
            background-color: {bg_color};
            color: {text_color};
            border: {border_width}px solid {border_color};
            border-radius: {radius}px;
            padding: {padding_v}px {padding_h}px;
            font-size: 14px;
        }}
        QLineEdit:focus {{
            border-color: {focus_color};
        }}
        QLineEdit:disabled {{
            background-color: {disabled_bg};
            color: {disabled_text};
        }}
    """


def build_label_style(
    colors: Dict[str, str],
    font_size: int = 14
) -> str:
    """
    Build label style stylesheet
    
    Args:
        colors: Theme colors dictionary
        font_size: Font size in pixels
    
    Returns:
        QSS stylesheet string
    """
    text_color = colors.get("text_primary", "#000000")
    
    return f"""
        QLabel {{
            color: {text_color};
            font-size: {font_size}px;
        }}
    """

