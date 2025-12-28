"""
🌊 Color Utilities
Helper functions for color manipulation and conversion
"""

def hex_to_rgb(hex_color: str) -> tuple:
    """
    Convert hex color to RGB tuple
    
    Args:
        hex_color: Hex color string (e.g., "#FF69B4")
    
    Returns:
        Tuple of (r, g, b) values
    """
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def rgb_to_hex(r: int, g: int, b: int) -> str:
    """
    Convert RGB values to hex color
    
    Args:
        r, g, b: RGB values (0-255)
    
    Returns:
        Hex color string
    """
    return f"#{r:02x}{g:02x}{b:02x}"

def lighten_color(hex_color: str, factor: float = 0.1) -> str:
    """
    Lighten a color by a given factor
    
    Args:
        hex_color: Hex color string
        factor: Lightening factor (0.0 to 1.0)
    
    Returns:
        Lightened hex color string
    """
    r, g, b = hex_to_rgb(hex_color)
    r = min(255, int(r + (255 - r) * factor))
    g = min(255, int(g + (255 - g) * factor))
    b = min(255, int(b + (255 - b) * factor))
    return rgb_to_hex(r, g, b)

def darken_color(hex_color: str, factor: float = 0.1) -> str:
    """
    Darken a color by a given factor
    
    Args:
        hex_color: Hex color string
        factor: Darkening factor (0.0 to 1.0)
    
    Returns:
        Darkened hex color string
    """
    r, g, b = hex_to_rgb(hex_color)
    r = max(0, int(r * (1 - factor)))
    g = max(0, int(g * (1 - factor)))
    b = max(0, int(b * (1 - factor)))
    return rgb_to_hex(r, g, b)

def adjust_opacity(hex_color: str, opacity: float) -> str:
    """
    Add opacity to a hex color (returns rgba string for web/CSS)
    
    Args:
        hex_color: Hex color string
        opacity: Opacity value (0.0 to 1.0)
    
    Returns:
        RGBA string (for CSS/web use)
    """
    r, g, b = hex_to_rgb(hex_color)
    return f"rgba({r}, {g}, {b}, {opacity})"

def get_contrast_text_color(bg_hex: str) -> str:
    """
    Get appropriate text color (black or white) based on background
    
    Args:
        bg_hex: Background hex color
    
    Returns:
        "#FFFFFF" or "#000000" for best contrast
    """
    r, g, b = hex_to_rgb(bg_hex)
    # Calculate luminance
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return "#000000" if luminance > 0.5 else "#FFFFFF"

