"""
🌊 GA4 Tools Suite - Styles Package
Centralized theme and styling system
"""

# PySide6 theme system
from .theme_loader import (
    ThemeLoader,
    ThemeManager,
    get_theme_manager
)

# Theme types and validation
from .types import ThemeData, ThemeColors, ThemeMetadata
from .theme_validator import ThemeValidator, ThemeValidationResult
from .style_registry import StyleRegistry

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
    # Theme types and validation
    'ThemeData',
    'ThemeColors',
    'ThemeMetadata',
    'ThemeValidator',
    'ThemeValidationResult',
    'StyleRegistry',
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
    'calculate_contrast_ratio',
    'validate_contrast',
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

