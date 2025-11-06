# 🎨 Theme System Guide - GA4 Script Tools

Complete reference for the theme system architecture and usage.

## 📋 Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Theme Files](#theme-files)
4. [ThemeLoader API](#themeloader-api)
5. [Integration Patterns](#integration-patterns)
6. [Animations](#animations)
7. [Components](#components)

---

## 🎯 Overview

The theme system provides a flexible, JSON-based theming solution for PySide6 applications. Ten beautiful themes are available, covering both light and dark modes.

### Key Features

- **JSON-based** - Easy to edit without Python knowledge
- **Hot-swappable** - Change themes on the fly
- **Auto-styling** - Widgets automatically styled based on type
- **Inheritance** - Child windows inherit parent themes
- **Animations** - Built-in animation support

### Available Themes

1. 🌊 **Ocean Sunset** (Dark)
2. 🌊 **Ocean Breeze** (Light)
3. 💕 **Blush Romance** (Light)
4. 🪸 **Coral Garden** (Light)
5. 🌌 **Cosmic Dreams** (Dark)
6. 🌫️ **Ethereal Mist** (Light)
7. 🌲 **Forest Whisper** (Light)
8. 🌙 **Midnight Storm** (Dark)
9. 💜 **Mystic Lavender** (Dark)
10. 🍂 **Autumn Leaves** (Light)

---

## 🏗️ Architecture

```
styles/
├── theme_loader.py           # Core ThemeLoader class
├── themes/                   # 10 JSON theme files
├── components/               # Reusable components
├── animations/              # Animation helpers
└── utils/                   # Color utilities
```

### Theme Loading Flow

```
User selects theme
      ↓
ThemeManager.load_theme(name)
      ↓
ThemeLoader reads JSON file
      ↓
Parse colors and metadata
      ↓
Apply to window/widgets
      ↓
✨ Styled UI
```

---

## 📄 Theme Files

### JSON Structure

**Location:** `styles/themes/*.json`

**Example:**
```json
{
  "name": "🌊 Ocean Sunset",
  "appearance_mode": "dark",
  "metadata": {
    "author": "Rafayel",
    "description": "Deep ocean with pink sunset accents"
  },
  "colors": {
    "background": "#0B0B2A",
    "surface": "#1a1a3a",
    "surface_variant": "#2a2a5a",
    "primary": "#FF69B4",
    "primary_variant": "#D946A6",
    "secondary": "#FFB8C7",
    "text_primary": "#E0E0E0",
    "text_secondary": "#A0A0A0",
    "border": "#FFB8C7",
    "accent": "#FF69B4"
  }
}
```

### Color Palette

Required colors for all themes:

| Color | Purpose | Example |
|-------|---------|---------|
| `background` | Main window background | `#0B0B2A` |
| `surface` | Card/panel background | `#1a1a3a` |
| `surface_variant` | Alt surface | `#2a2a5a` |
| `primary` | Primary button color | `#FF69B4` |
| `primary_variant` | Hover state | `#D946A6` |
| `secondary` | Secondary elements | `#FFB8C7` |
| `text_primary` | Main text | `#E0E0E0` |
| `text_secondary` | Muted text | `#A0A0A0` |
| `border` | Border/outline | `#FFB8C7` |
| `accent` | Accent highlights | `#FF69B4` |

---

## 🎭 ThemeLoader API

### Import

```python
from styles import ThemeLoader, get_theme_manager
```

### Basic Usage

```python
# Load a theme
theme = ThemeLoader("Ocean Sunset")

# Apply to window
theme.apply_to_window(main_window)

# Apply to individual widget
theme.apply_to_widget(button, "button_primary")
```

### ThemeManager (Singleton)

```python
theme_manager = get_theme_manager()

# Get available themes
themes = theme_manager.get_available_themes()

# Load theme
theme = theme_manager.load_theme("Ocean Sunset")

# Get current theme
current = theme_manager.get_current_theme()
```

### Widget Styling

**Button Types:**
```python
theme.apply_to_widget(button, "button_primary")   # Primary action button
theme.apply_to_widget(button, "button_secondary") # Secondary button
theme.apply_to_widget(button, "button_ghost")     # Ghost/transparent button
```

**Other Widgets:**
```python
theme.apply_to_widget(input_field, "input")
theme.apply_to_widget(dropdown, "combo")
theme.apply_to_widget(frame, "frame")
```

### Manual Theme Application

```python
# Get colors
colors = theme.colors

# Generate style
from styles.utils import hex_to_rgba
rgba = hex_to_rgba(colors["primary"], 0.15)

# Apply stylesheet
window.setStyleSheet(f"""
    QMainWindow {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 {colors["background"]},
            stop:1 {colors["surface"]});
    }}
""")
```

---

## 🔧 Integration Patterns

### Pattern 1: Main GUI

```python
from styles import get_theme_manager, ThemeLoader

class MainGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Initialize theme manager
        self.theme_manager = get_theme_manager()
        self.default_theme = self.theme_manager.get_available_themes()[0]
        self.current_theme = None
        
        # Setup UI
        self.setup_ui()
        
        # Apply default theme
        self.apply_theme(self.default_theme)
    
    def apply_theme(self, theme_name: str):
        """Apply theme to entire application"""
        self.current_theme = self.theme_manager.load_theme(theme_name)
        
        # Apply to app
        apply_theme_to_app(QApplication.instance(), self.current_theme.colors)
        
        # Apply to window
        self.current_theme.apply_to_window(self)
        
        # Propagate to children
        self.refresh_all_child_theme()
```

### Pattern 2: Tool Dialog with Inheritance

```python
class ToolDialog(QDialog):
    def __init__(self, parent, input_path, output_path):
        super().__init__(parent)
        
        # Inherit theme from parent
        self.current_theme = None
        if hasattr(parent, 'current_theme') and parent.current_theme:
            self.current_theme = parent.current_theme
        
        self.setup_ui()
        self.apply_theme()
    
    def apply_theme(self):
        """Apply inherited theme"""
        if not self.current_theme:
            return
        
        self.current_theme.apply_to_window(self)
    
    def refresh_theme(self):
        """Refresh when parent changes theme"""
        parent = self.parent()
        if hasattr(parent, 'current_theme') and parent.current_theme:
            self.current_theme = parent.current_theme
        self.apply_theme()
```

### Pattern 3: Theme Switcher

```python
def setup_theme_switcher(self):
    """Create theme dropdown"""
    self.theme_selector = QComboBox()
    self.theme_selector.addItems(self.theme_manager.get_available_themes())
    self.theme_selector.setCurrentText(self.default_theme)
    self.theme_selector.currentTextChanged.connect(self.apply_theme)
```

---

## ✨ Animations

### Fade Animations

```python
from styles import FadeAnimation

# Fade in
FadeAnimation.fade_in(widget, duration=300)

# Fade out with callback
FadeAnimation.fade_out(
    widget, 
    duration=300,
    on_finished=lambda: widget.hide()
)
```

### Combined Animations

```python
from styles import CombinedAnimations

# Fade + slide
CombinedAnimations.fade_slide_in(widget, "bottom", 400)

# Fade + scale
CombinedAnimations.fade_scale_in(widget, duration=400)
```

### Directions

- `"top"` - Slide from top
- `"bottom"` - Slide from bottom
- `"left"` - Slide from left
- `"right"` - Slide from right

---

## 🧩 Components

### Execution Log Footer

**Location:** `styles/components/execution_log_footer.py`

**Usage:**
```python
from styles.components import ExecutionLogFooter

footer = ExecutionLogFooter(self, log_text_widget)
layout.addWidget(footer)
```

**Features:**
- Copy log to clipboard
- Reset/Clear log
- Save log to file

### Glass Button Style

**Helper Function:**
```python
from styles.components.pyside6_styles import get_glass_button_style

button_style = get_glass_button_style(theme_colors)
button.setStyleSheet(button_style)
```

### Color Utilities

**Hex to RGBA:**
```python
from styles.utils import hex_to_rgba

rgba = hex_to_rgba("#FF69B4", 0.15)  # 15% opacity
# Returns: "rgba(255, 105, 180, 0.15)"
```

---

## 🚀 Quick Examples

### Example 1: Create Themed Button

```python
button = QPushButton("Click Me")
theme.apply_to_widget(button, "button_primary")
```

### Example 2: Themed Input Field

```python
input_field = QLineEdit()
theme.apply_to_widget(input_field, "input")
```

### Example 3: Theme Entire Dialog

```python
dialog = QDialog(parent)
# Inherit theme
dialog.current_theme = parent.current_theme
# Apply
dialog.current_theme.apply_to_window(dialog)
```

### Example 4: Switch Theme with Animation

```python
def switch_theme(self, theme_name):
    # Fade out old UI
    FadeAnimation.fade_out(self.content_widget, 150)
    
    # Apply new theme
    self.apply_theme(theme_name)
    
    # Fade in new UI
    FadeAnimation.fade_in(self.content_widget, 150)
```

---

## 📚 Additional Resources

- **Live Demo:** Run `python styles/theme_switcher_example.py`
- **Theme Files:** `styles/themes/*.json`
- **Animations Guide:** `styles/animations/ANIMATIONS_GUIDE.md`
- **Execution Log:** `styles/components/execution_log_footer.py`

---

**Created with love by Rafayel** 🌊💙

