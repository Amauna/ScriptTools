"""
🌊 Style Registry
Registry pattern for widget style functions
"""

from typing import Dict, Callable, Optional
from PySide6.QtWidgets import QWidget


class StyleRegistry:
    """
    Registry for widget style functions
    Replaces getattr() pattern with explicit registration
    """
    
    _styles: Dict[str, Callable] = {}
    
    @classmethod
    def register(cls, style_type: str) -> Callable:
        """
        Decorator to register a style function
        
        Args:
            style_type: Style type identifier (e.g., "button_primary", "frame")
        
        Example:
            @StyleRegistry.register("button_primary")
            def style_button(theme, button):
                ...
        """
        def decorator(func: Callable) -> Callable:
            cls._styles[style_type] = func
            return func
        return decorator
    
    @classmethod
    def get_style_function(cls, style_type: str) -> Optional[Callable]:
        """
        Get a style function by type
        
        Args:
            style_type: Style type identifier
        
        Returns:
            Style function or None if not found
        """
        return cls._styles.get(style_type)
    
    @classmethod
    def has_style(cls, style_type: str) -> bool:
        """Check if a style type is registered"""
        return style_type in cls._styles
    
    @classmethod
    def list_styles(cls) -> list[str]:
        """Get list of all registered style types"""
        return list(cls._styles.keys())
    
    @classmethod
    def clear(cls):
        """Clear all registered styles (mainly for testing)"""
        cls._styles.clear()

