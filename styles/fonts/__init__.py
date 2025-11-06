"""
🎨 Fonts Package
Font presets for consistent typography
"""

import json
from pathlib import Path

def load_font_preset(preset_name: str = "modern") -> dict:
    """
    Load a font preset from JSON
    
    Args:
        preset_name: Name of the font preset (e.g., "modern", "handwritten")
    
    Returns:
        Dictionary of font configurations
    """
    font_file = Path(__file__).parent / f"{preset_name}.json"
    
    if font_file.exists():
        with open(font_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        # Default fallback
        return {
            "name": "Default",
            "fonts": {
                "heading": {"family": "Arial", "size": 24, "weight": "bold"},
                "body": {"family": "Arial", "size": 11, "weight": "normal"}
            }
        }

def get_font_tuple(font_config: dict) -> tuple:
    """
    Convert font config to tkinter font tuple
    
    Args:
        font_config: Font configuration dict {"family": ..., "size": ..., "weight": ...}
    
    Returns:
        Tuple in format (family, size, weight)
    """
    return (
        font_config.get("family", "Arial"),
        font_config.get("size", 11),
        font_config.get("weight", "normal")
    )

__all__ = ['load_font_preset', 'get_font_tuple']

