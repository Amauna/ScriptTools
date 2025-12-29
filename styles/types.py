"""
🌊 Theme Type Definitions
TypedDict definitions for theme structure and type safety
"""

from typing import TypedDict, Optional


class ThemeColors(TypedDict, total=False):
    """Theme color palette definitions"""
    # Core colors
    background: str
    surface: str
    surface_variant: str
    
    # Primary colors
    primary: str
    primary_hover: str
    primary_variant: str
    
    # Secondary colors
    secondary: str
    secondary_hover: str
    
    # Text colors
    text_primary: str
    text_secondary: str
    text_on_primary: str
    text_on_secondary: str
    
    # Border colors
    border: str
    border_focus: str
    
    # Accent colors
    accent: str
    
    # Semantic colors
    success: str
    warning: str
    error: str
    info: str


class ThemeMetadata(TypedDict, total=False):
    """Theme metadata information"""
    author: str
    description: str
    version: str
    tags: list[str]


class ThemeData(TypedDict):
    """Complete theme structure"""
    name: str
    appearance_mode: str  # "light" or "dark"
    colors: ThemeColors
    metadata: Optional[ThemeMetadata]

