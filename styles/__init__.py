"""
🌊 GA4 Tools Suite - Styles Package
Centralized theme and styling system

By: Rafayel, Bry's AI Muse 💕
"""

# PySide6 theme system
from .theme_loader import (
    ThemeLoader,
    ThemeManager,
    get_theme_manager
)

# PySide6 helper functions
from .pyside6_theme_helper import (
    apply_theme_to_app,
    apply_glass_effect,
    create_gradient_background,
    get_modern_card_style,
    get_dialog_style
)

# Components
from .components import (
    get_app_stylesheet,
    get_glass_button_style,
    get_glass_frame_style,
    get_modern_input_style,
    hex_to_rgba,
    create_gradient,
    ExecutionLogFooter,
    create_execution_log_footer
)

# Utils
from .utils import (
    hex_to_rgb,
    rgb_to_hex,
    lighten_color,
    darken_color,
    adjust_opacity,
    get_contrast_text_color,
    get_path_manager,
    PathManager,
    get_log_manager,
    LogManager
)

# Animations
from .animations import (
    FadeAnimation,
    SlideAnimation,
    ScaleAnimation,
    CombinedAnimations,
    animate_show,
    animate_hide
)

__all__ = [
    # Theme system
    'ThemeLoader',
    'ThemeManager',
    'get_theme_manager',
    # PySide6 helpers
    'apply_theme_to_app',
    'apply_glass_effect',
    'create_gradient_background',
    'get_modern_card_style',
    'get_dialog_style',
    # Component styles
    'get_app_stylesheet',
    'get_glass_button_style',
    'get_glass_frame_style',
    'get_modern_input_style',
    'hex_to_rgba',
    'create_gradient',
    # Components
    'ExecutionLogFooter',
    'create_execution_log_footer',
    # Utils
    'hex_to_rgb',
    'rgb_to_hex',
    'lighten_color',
    'darken_color',
    'adjust_opacity',
    'get_contrast_text_color',
    'get_path_manager',
    'PathManager',
    'get_log_manager',
    'LogManager',
    # Animations
    'FadeAnimation',
    'SlideAnimation',
    'ScaleAnimation',
    'CombinedAnimations',
    'animate_show',
    'animate_hide'
]

