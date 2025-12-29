"""
✨ Animations Package - PySide6 Animations
Beautiful Qt native animations for your UI
"""

from .pyside6_animations import (
    FadeAnimation,
    SlideAnimation,
    ScaleAnimation,
    CombinedAnimations,
    animate_show,
    animate_hide
)

__all__ = [
    # Animation classes
    'FadeAnimation',
    'SlideAnimation',
    'ScaleAnimation',
    'CombinedAnimations',
    # Convenience functions
    'animate_show',
    'animate_hide'
]

