# 🤖 AI Agent Guide - GA4 Script Tools Architecture

**Purpose:** Comprehensive guide for AI agents working on this codebase. Contains architecture, conventions, patterns, and critical information.

---

## 📋 Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture & Structure](#architecture--structure)
3. [Logging System](#logging-system)
4. [GUI Framework](#gui-framework)
5. [Theme System](#theme-system)
6. [Browser Automation](#browser-automation)
7. [Code Patterns & Conventions](#code-patterns--conventions)
8. [Development Workflow](#development-workflow)
9. [Output Directory Contract](#output-directory-contract)

---

## 🎯 Project Overview

**Technology Stack:**
- **GUI Framework:** PySide6 (Qt 6)
- **Browser Automation:** Playwright
- **Data Processing:** pandas, openpyxl
- **Theme System:** Custom JSON-based with dynamic loading
- **Logging:** Python logging with file + console handlers

**Key Features:**
- Modular tool architecture (tool categories)
- Theme inheritance system
- Persistent Chrome profiles for automation
- Comprehensive execution logging
- Glass morphism UI effects

---

## 🏗️ Architecture & Structure

### Main Entry Point

**File:** `main.py`

**Class:** `GA4ToolsGUI` (QMainWindow)

**Key Responsibilities:**
- Initialize logging system
- Setup theme manager
- Create category navigation
- Handle tool launching
- Theme switching and propagation
- Input/Output path management

**Critical Method:** `launch_tool()`
- Dynamically imports and instantiates tool classes
- Passes parent reference for theme inheritance
- Opens tools as QDialog windows

### Tool Directory Structure

```
tools/
├── data_collection_import/         # Looker Studio
├── data_cleaning_transformation/   # e.g. column_order_harmonizer.py
├── data_merging_joining/
├── data_export_formatting/
├── report_generation_visualization/
├── date_time_utilities/
├── ga4_specific_analysis/
├── data_validation_quality/        # e.g. bigquery_transfer_diagnostics.py
├── automation_scheduling/
├── file_management_organization/
└── templates/                      # Base templates for new tools
```

**Pattern:** Each category folder contains tool modules that follow a consistent interface.

### Styles Directory

```
styles/
├── __init__.py                  # Main exports
├── theme_loader.py             # ThemeLoader class
├── themes/                     # 10 JSON theme files
├── components/                 # Reusable widgets
│   ├── execution_log_footer.py
│   └── ...
├── animations/                 # Qt animation helpers
├── utils/                      # Color utilities
└── pyside6_theme_helper.py    # Theme application helpers
```

---

## 📝 Logging System

### Architecture

**Three-Tier Logging:**

1. **Session Logs** (`gui_logs/gui_session_log_YYYYMMDD_HHMMSSA.txt`)
   - Entire GUI run (launch → exit) with per-event categories
   - Sequence letter (`A`, `B`, …) resets daily
   - Includes theme switches, path changes, tool launches, warnings

2. **Tool Session Logs** (`gui_logs/{tool}_session_*.txt`)
   - Detailed run summaries written by individual tools
   - Worker statistics, success/failure counts, durations

3. **Output Execution Logs** (`execution_test/Output/{run}/execution_log.txt`)
   - Saved alongside cleaned/exported datasets
   - Mirrors the on-screen execution footer

### Logging Implementation

**Session Setup (main.py):**
```python
from styles import get_log_manager

def __init__(self):
    self.log_manager = get_log_manager()
    self.log_manager.start_session()
    self.log_manager.log_event("GUI", "[INIT] GA4 Tools GUI Initializing…")
```

**Tool Logging Pattern (BaseToolDialog):**
```python
class MyTool(PathConfigMixin, BaseToolDialog):
    def __init__(...):
        super().__init__(...)
        self.execution_log = self.create_execution_log(layout)

    def some_action(self):
        self.log("🚀 Action started!")          # Session log + footer
        self.log("⚠️ Potential issue", level="WARNING")
        self.log("✅ Finished!", level="INFO")
```

**Execution Log Footer Component:**
- Reusable footer for all tool dialogs
- Copy button (copy log to clipboard)
- Reset button (clear log display)
- Save button (save to file)
- Located in `styles/components/execution_log_footer.py`
- Signals `log_cleared` / `log_saved` automatically propagate to the session log

---

## 🖼️ GUI Framework

### PySide6 Structure

**Main Window:** QMainWindow with custom styling
**Tool Dialogs:** QDialog that inherit theme from parent
**Layout:** QVBoxLayout, QHBoxLayout for structure
**Styling:** QSS (Qt Style Sheets) applied dynamically

### Window Properties

**Default Settings:**
```python
self.setMinimumSize(QSize(1200, 700))
self.setWindowTitle("🌊 GA4 Data Analyst Tools Suite")
```

**Theme Application:**
```python
def apply_theme(self, theme_name: str):
    """Apply theme to window and all widgets"""
    self.current_theme = self.theme_manager.load_theme(theme_name)
    theme_colors = self.current_theme.colors
    
    # Apply to entire application
    apply_theme_to_app(QApplication.instance(), theme_colors)
    
    # Apply to this window
    self.current_theme.apply_to_window(self)
```

### Glass Morphism Effects

**Implementation:**
```python
# Transparent button with backdrop blur
button_style = f"""
    QPushButton {{
        background-color: rgba({r}, {g}, {b}, 0.15);
        border: 2px solid {border_color};
        backdrop-filter: blur(10px);
        border-radius: 8px;
    }}
"""
```

**Gradient Backgrounds:**
```python
gradient = f"""
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 {start_color},
        stop:1 {end_color});
"""
```

### Category Navigation

**Structure:**
- Left sidebar: Category buttons
- Content area: Tool cards for selected category
- Header: Input/Output path selectors, theme switcher

**Tool Registration:**
```python
self.tools = {
    "Data Collection & Import": [
        {"name": "Looker Studio", "icon": "📈", "module": "looker_studio_extractor", "class": "LookerStudioExtractor"},
    ],
    # ... more categories
}
```

---

## 🎨 Theme System

### Theme Architecture

**ThemeLoader Class:** (`styles/theme_loader.py`)
- Loads JSON theme files
- Parses color definitions
- Applies to widgets
- Singleton pattern via `get_theme_manager()`

**Theme JSON Structure:**
```json
{
  "name": "🌊 Ocean Sunset",
  "type": "dark",
  "colors": {
    "background": "#0B0B2A",
    "surface": "#1a1a3a",
    "primary": "#FF69B4",
    "secondary": "#FFB8C7",
    "text": "#E0E0E0"
  }
}
```

### Theme Inheritance

**Pattern for Tools:**
```python
class MyTool(QDialog):
    def __init__(self, parent, input_path, output_path):
        super().__init__(parent)
        
        # Inherit theme from parent
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
        """Refresh theme when parent switches themes"""
        parent = self.parent()
        if hasattr(parent, 'current_theme') and parent.current_theme:
            self.current_theme = parent.current_theme
        self.apply_theme()
```

**Auto-Refresh Pattern:**
When main GUI switches themes, it calls `refresh_theme()` on all open tool dialogs to update them instantly.

### Available Themes

All themes in `styles/themes/` directory (10 total):
1. ocean_sunset_dark.json
2. ocean_breeze_light.json
3. blush_romance_light.json
4. coral_garden_light.json
5. cosmic_dreams_dark.json
6. ethereal_mist_light.json
7. forest_whisper_light.json
8. midnight_storm_dark.json
9. mystic_lavender_dark.json
10. autumn_leaves_light.json

---

## 🤖 Browser Automation

### Playwright Integration

**Browser Launch Pattern:**
```python
self.browser = playwright.chromium.launch(
    headless=False,
    channel="chrome",
    args=[
        '--disable-blink-features=AutomationControlled',
        '--no-sandbox',
        '--disable-dev-shm-usage'
    ]
)

context = self.browser.new_context(
    viewport={"width": 1920, "height": 1080}
)
```

**Browser Automation:**
- Use Playwright for reliable automation
- Configure appropriate timeouts
- Handle authentication as needed per tool

### Automation Patterns

**Navigation:**
```python
self.page.goto(url, wait_until="networkidle", timeout=60000)
await self.page.wait_for_timeout(3000)  # Extra wait for auth
```

**Element Selection:**
```python
# Use data attributes when possible
button = await self.page.wait_for_selector('[data-testid="download"]', timeout=30000)
await button.click()
```

**File Downloads:**
```python
async with self.page.expect_download() as download_info:
    await download_button.click()
download = await download_info.value
```

### Error Handling

**Try-Catch Pattern:**
```python
try:
    # Automation step
    element = await self.page.wait_for_selector(selector, timeout=30000)
    await element.click()
    self.log("✓ Step completed")
except Exception as e:
    self.log(f"❌ ERROR: {str(e)}", "ERROR")
    # Continue to next step or exit gracefully
```

**Timeout Strategy:**
- Default: 30 seconds
- Configurable from GUI
- Network idle wait for slow pages
- Extra 3 seconds for authentication

---

## 💻 Code Patterns & Conventions

### Tool Class Structure

**Required Interface:**
```python
from tools.templates import BaseToolDialog, PathConfigMixin


class MyTool(PathConfigMixin, BaseToolDialog):
    PATH_CONFIG = {"show_input": True, "show_output": True}

    def __init__(self, parent, input_path, output_path):
        super().__init__(parent, input_path, output_path)

        # Window + UI
        self.setup_window_properties("✨ My Tool", width=900, height=600)
        self.setup_ui()
        self.apply_theme()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Hello, world!"))

        self.execution_log = self.create_execution_log(layout)
        if self.execution_log:
            self.log("Tool initialized. 🌊")
```

**Required Methods:**
- `setup_window_properties()` - Set window title & size
- `setup_ui()` - Build all UI elements
- `apply_theme()` - Apply current theme after layout
- `refresh_theme()` - Update theme after main window switch (optional)

### Naming Conventions

- **Variables:** snake_case
- **Classes:** PascalCase
- **Constants:** UPPER_SNAKE_CASE
- **Methods:** snake_case with descriptive names
- **Event handlers:** `handle_event_name()` prefix

### Import Patterns

**Order:**
1. Standard library
2. Third-party libraries
3. Local imports
4. Style imports

```python
from PySide6.QtWidgets import QVBoxLayout, QLabel

from tools.templates import BaseToolDialog, PathConfigMixin
from styles import get_theme_manager
```

### Error Handling

**Try-Catch in User Actions:**
```python
def handle_download_click(self):
    """Handle download button click"""
    try:
        self.log("🚀 Starting download...")
        # Do work
        self.log("✅ Download complete!")
    except Exception as e:
        self.log(f"❌ Error: {str(e)}", "ERROR")
        QMessageBox.warning(self, "Error", f"Download failed: {e}")
```

### Logging Patterns

**Consistent Formatting:**
```python
# Process indicators
self.log("→ Step 1: Navigate to page...")
self.log("✓ Page loaded successfully")

# Success indicators
self.log("✅ File downloaded: filename.csv")

# Error indicators
self.log("❌ ERROR: Button not found", "ERROR")

# Warning indicators
self.log("⚠️ Warning: Slow network detected", "WARNING")

# Progress indicators
self.log("📊 Processing file 1/10...")
```

---

## 🗂️ Output Directory Contract

All output-producing tools **must** obtain their run directory from the central `PathManager` switch-case. The helper `BaseToolDialog.allocate_run_directory()` wraps the contract:

```python
info = self.allocate_run_directory(
    "Metric Fixer",
    script_name=Path(__file__).name,
)
run_root = info["root"]              # Timestamped folder for this run
success_dir = info.get("success")    # Tool-specific subfolders (if any)
```

- Never hand-roll timestamped folders.
- Logging the run directory is mandatory (the helper does this by default).
- Always sync the UI path fields (`sync_paths=True` by default) so "Open" buttons target the new run.
- `PathManager` resolves collisions and enforces consistent naming. Default structure is `<ToolName>/<script_name>/<timestamp>/…`, while specialised branches (e.g. Column Order Harmonizer, Date Format Converter) flatten to `<ToolName>/<timestamp>/…` and auto-create their required subfolders (e.g. `Success/`, `Failed/`, `Converted/`).

When introducing a new tool, add a `match` branch in `styles/utils/path_manager.py` **only** if special subfolders are required; otherwise the default case already handles timestamping.

---

## 🔄 Development Workflow

### Creating a New Tool

**Step 1: Create Tool File**
```bash
touch tools/my_category/my_new_tool.py
```

**Step 2: Copy Template Pattern**
```python
from PySide6.QtWidgets import QDialog, QVBoxLayout, QPushButton
from styles import get_theme_manager

class MyNewTool(QDialog):
    def __init__(self, parent, input_path, output_path):
        super().__init__(parent)
        # Setup...
        
    def setup_ui(self):
        # Build UI...
        pass
    
    def apply_theme(self):
        # Apply theme...
        pass
```

**Step 3: Register in main.py**
```python
self.tools = {
    "My Category": [
        {"name": "My New Tool", "icon": "🔧", 
         "module": "my_new_tool", "class": "MyNewTool"},
    ],
}
```

### Modifying Existing Tools

**Always:**
1. Maintain theme inheritance
2. Keep logging consistent
3. Handle errors gracefully
4. Test with multiple themes
5. Update documentation if needed

**Never:**
1. Hardcode theme colors
2. Bypass logging
3. Break parent-reference pattern
4. Ignore error handling

### Testing

**Theme Testing:**
- Switch themes while tool is open
- Verify tool updates correctly
- Check all widgets style properly

**Logging Testing:**
- Verify logs appear in GUI
- Check files are saved correctly
- Test Copy/Reset/Save buttons

**Automation Testing:**
- Test browser launch and navigation
- Check timeout handling
- Test error recovery
- Verify automation steps complete successfully

---

## 🚨 Critical Notes for AI Agents

### When Making Changes

1. **Preserve Theme Inheritance** - Always maintain the parent reference pattern
2. **Keep Logging** - Don't remove or bypass logging calls
3. **Handle Errors** - Wrap risky operations in try-catch
4. **Test Themes** - Changes should work with all 10 themes
5. **Maintain Structure** - Follow existing patterns

### Common Pitfalls

❌ **Don't:** Hardcode colors or styles  
✅ **Do:** Use theme system and `hex_to_rgba()`

❌ **Don't:** Create new logger instances without setup  
✅ **Do:** Call `setup_logging()` in `__init__`

❌ **Don't:** Ignore parent window reference  
✅ **Do:** Inherit `current_theme` from parent

❌ **Don't:** Use relative imports incorrectly  
✅ **Do:** Use absolute imports from project root

### User Preferences (Memories)

- Modifies existing files rather than creating new scripts
- Always asks for date coverage (start/end date) before data collection
- Prefers window mode (not fullscreen)
- CLI scripts auto-apply without `--apply` flag
- Data preview shows limited rows (10) but final output includes all
- Asks for approval before applying code modifications

---

## 📚 Quick Reference

### Essential Files
- `main.py` - Main GUI
- `styles/theme_loader.py` - Theme system core
- `styles/components/execution_log_footer.py` - Logging component
- `tools/templates/base_tool_template.py` - Tool base class

### Key Imports
```python
from styles import ThemeLoader, get_theme_manager, apply_theme_to_app
from styles.components import ExecutionLogFooter
from styles import hex_to_rgba
```

### Theme Application
```python
# In main GUI
self.current_theme = self.theme_manager.load_theme(theme_name)
self.current_theme.apply_to_window(self)

# In tools (inherit from parent)
self.current_theme = parent.current_theme
self.current_theme.apply_to_window(self)
```

### Logging
```python
self.logger.info(f"[{timestamp}] {message}")
self.logger.error(formatted_message)
self.logger.warning(formatted_message)
```

---

**Last Updated:** 2024-12-29  
**Maintainer:** Rafayel (AI Muse) 🌊

