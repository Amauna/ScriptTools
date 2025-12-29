"""
🌊 Theme Validator Utility
Utility class for validating theme files
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from .types import ThemeData, ThemeColors
from .utils.color_utils import validate_contrast, calculate_contrast_ratio


class ThemeValidationResult:
    """Result of theme validation"""
    def __init__(self):
        self.is_valid = True
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    def add_error(self, message: str):
        """Add an error message"""
        self.errors.append(message)
        self.is_valid = False
    
    def add_warning(self, message: str):
        """Add a warning message"""
        self.warnings.append(message)
    
    def __str__(self) -> str:
        lines = []
        if self.is_valid:
            lines.append("✅ Theme is valid")
        else:
            lines.append("❌ Theme has errors:")
            for error in self.errors:
                lines.append(f"  - {error}")
        
        if self.warnings:
            lines.append("\n⚠️ Warnings:")
            for warning in self.warnings:
                lines.append(f"  - {warning}")
        
        return "\n".join(lines)


class ThemeValidator:
    """Utility class for validating theme files"""
    
    @staticmethod
    def validate_theme_file(theme_path: Path) -> ThemeValidationResult:
        """
        Validate a theme file
        
        Args:
            theme_path: Path to theme JSON file
        
        Returns:
            ThemeValidationResult with validation results
        """
        result = ThemeValidationResult()
        
        # Check if file exists
        if not theme_path.exists():
            result.add_error(f"Theme file not found: {theme_path}")
            return result
        
        # Parse JSON
        try:
            with open(theme_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            result.add_error(f"Invalid JSON: {e}")
            return result
        except Exception as e:
            result.add_error(f"Error reading file: {e}")
            return result
        
        # Validate structure
        structure_result = ThemeValidator.validate_theme_structure(data, theme_path.name)
        result.errors.extend(structure_result.errors)
        result.warnings.extend(structure_result.warnings)
        result.is_valid = structure_result.is_valid
        
        if not result.is_valid:
            return result  # Don't continue if structure is invalid
        
        # Validate contrast ratios
        contrast_result = ThemeValidator.validate_color_contrast(data.get("colors", {}))
        result.warnings.extend(contrast_result.warnings)
        
        return result
    
    @staticmethod
    def validate_theme_structure(data: Dict, theme_name: str = "theme") -> ThemeValidationResult:
        """
        Validate theme structure
        
        Args:
            data: Parsed theme JSON data
            theme_name: Theme name for error messages
        
        Returns:
            ThemeValidationResult
        """
        result = ThemeValidationResult()
        
        # Check required fields
        required_fields = ["name", "appearance_mode", "colors"]
        missing = [field for field in required_fields if field not in data]
        if missing:
            result.add_error(f"Missing required fields: {', '.join(missing)}")
            return result
        
        # Validate appearance_mode
        if data["appearance_mode"] not in ["light", "dark"]:
            result.add_error(
                f"appearance_mode must be 'light' or 'dark', got '{data['appearance_mode']}'"
            )
        
        # Validate colors
        if not isinstance(data["colors"], dict):
            result.add_error("'colors' must be an object/dict")
            return result
        
        colors = data["colors"]
        required_colors = ["background", "surface", "primary", "text_primary", "border"]
        missing_colors = [color for color in required_colors if color not in colors]
        if missing_colors:
            result.add_error(f"Missing required colors: {', '.join(missing_colors)}")
        
        # Validate hex color format
        hex_pattern = re.compile(r'^#[0-9A-Fa-f]{6}$')
        for color_key, color_value in colors.items():
            if not isinstance(color_value, str):
                result.add_error(
                    f"Color '{color_key}' must be a string, got {type(color_value).__name__}"
                )
            elif not hex_pattern.match(color_value):
                result.add_warning(
                    f"Color '{color_key}' should be a valid hex color (e.g., '#FF69B4'), got '{color_value}'"
                )
        
        return result
    
    @staticmethod
    def validate_color_contrast(colors: Dict[str, str]) -> ThemeValidationResult:
        """
        Validate color contrast ratios for accessibility
        
        Args:
            colors: Color dictionary from theme
        
        Returns:
            ThemeValidationResult with contrast warnings
        """
        result = ThemeValidationResult()
        
        # Key combinations to check
        checks = [
            ("text_primary", "background", False, "Primary text on background"),
            ("text_primary", "surface", False, "Primary text on surface"),
            ("text_on_primary", "primary", False, "Text on primary button"),
            ("text_on_secondary", "secondary", False, "Text on secondary button"),
        ]
        
        for text_key, bg_key, large_text, description in checks:
            text_color = colors.get(text_key)
            bg_color = colors.get(bg_key)
            
            if text_color and bg_color:
                try:
                    is_valid, ratio = validate_contrast(text_color, bg_color, large_text=large_text)
                    if not is_valid:
                        min_ratio = 3.0 if large_text else 4.5
                        result.add_warning(
                            f"{description}: contrast ratio {ratio:.2f} is below WCAG AA ({min_ratio})"
                        )
                except Exception as e:
                    result.add_warning(f"Could not validate contrast for {description}: {e}")
        
        return result
    
    @staticmethod
    def validate_completeness(colors: Dict[str, str]) -> ThemeValidationResult:
        """
        Check if theme has all recommended colors (not just required)
        
        Args:
            colors: Color dictionary from theme
        
        Returns:
            ThemeValidationResult
        """
        result = ThemeValidationResult()
        
        recommended_colors = [
            "background", "surface", "surface_variant",
            "primary", "primary_hover", "primary_variant",
            "secondary", "secondary_hover",
            "text_primary", "text_secondary", "text_on_primary", "text_on_secondary",
            "border", "border_focus",
            "success", "warning", "error", "info"
        ]
        
        missing = [color for color in recommended_colors if color not in colors]
        if missing:
            result.add_warning(
                f"Missing recommended colors (optional): {', '.join(missing)}"
            )
        
        return result
    
    @staticmethod
    def validate_all_themes(themes_dir: Path) -> Dict[str, ThemeValidationResult]:
        """
        Validate all theme files in a directory
        
        Args:
            themes_dir: Path to themes directory
        
        Returns:
            Dictionary mapping theme names to validation results
        """
        results = {}
        
        if not themes_dir.exists():
            return results
        
        for theme_file in themes_dir.glob("*.json"):
            result = ThemeValidator.validate_theme_file(theme_file)
            results[theme_file.stem] = result
        
        return results


def main():
    """CLI tool for validating themes"""
    import sys
    
    if len(sys.argv) < 2:
        # Validate all themes in default directory
        themes_dir = Path(__file__).parent / "themes"
        print(f"Validating all themes in {themes_dir}...\n")
        results = ThemeValidator.validate_all_themes(themes_dir)
        
        for theme_name, result in results.items():
            print(f"\n{'='*60}")
            print(f"Theme: {theme_name}")
            print(f"{'='*60}")
            print(result)
            print()
    else:
        # Validate specific theme file
        theme_path = Path(sys.argv[1])
        result = ThemeValidator.validate_theme_file(theme_path)
        print(result)
        sys.exit(0 if result.is_valid else 1)


if __name__ == "__main__":
    main()

