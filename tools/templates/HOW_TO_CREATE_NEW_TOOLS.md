# 🌊 How to Create New Tools - Quick Guide 🌊

*Step-by-step guide*

## 🎯 The Easy Way (Using Template)

Creating a new tool is **super easy** now! Just follow these steps:

---

## 📋 **Step-by-Step Instructions**

### **Step 1: Copy the Template** 📝

Copy `tools/templates/NEW_TOOL_TEMPLATE.py` to your tool category folder:

```bash
# Example: Creating a new data export tool
Copy-Item tools/templates/NEW_TOOL_TEMPLATE.py tools/data_export_formatting/my_export_tool.py
```

### **Step 2: Rename the Class** ✏️

Open your new file and rename the class:

```python
# Change this:
class NewToolTemplate(BaseToolDialog):

# To this:
class MyExportTool(BaseToolDialog):
```

### **Step 3: Update Title & Description** 📝

```python
def __init__(self, parent, input_path, output_path):
    super().__init__(parent, input_path, output_path)
    
    # Change the title
    self.setup_window_properties(
        title="📊 My Export Tool",  # Your tool name
        width=900,
        height=700
    )
```

### **Step 4: Build Your UI** 🎨

Replace the example UI with your tool's interface:

```python
def setup_ui(self):
    """Create the tool's user interface"""
    main_layout = QVBoxLayout(self)
    
    # Add your widgets here
    # - Input fields
    # - Buttons
    # - Tables
    # - etc.
    
    # Optional: Add execution log
    self.execution_log = self.create_execution_log(main_layout)
```

### **Step 5: Allocate Your Run Directory & Add Logic** 💡

Before writing any files, ask the shared `PathManager` for a run directory. This keeps every tool’s outputs inside the governed `execution_test/Output` tree and prevents nested timestamp folders.

```python
from pathlib import Path

def do_your_action(self):
    """Your tool's main functionality"""

    info = self.allocate_run_directory(
        "My Export Tool",
        script_name=Path(__file__).name,
    )
    run_root = info["root"]
    success_dir = info.get("success")   # Optional specialised folders

    # Your core logic here — write outputs into run_root / success_dir

    if self.execution_log:
        self.log(f"📁 Run directory: {run_root}")
        self.log("Processing data...")
        self.log("✅ Done!")
```

> **Important:** Never hand-build timestamped folders. PathManager already normalises stale output paths from previous runs, so you always get a clean structure like `Output/My_Tool/<timestamp>/...`.

### **Step 6: Done!** 🎉

**That's it!** Your tool now has:
- ✅ Automatic theme inheritance
- ✅ Theme switching support
- ✅ Execution log component
- ✅ Error handling
- ✅ Beautiful styling

---

## 🎨 **What You Get Automatically**

When you inherit from `BaseToolDialog`, you automatically get:

### **Properties:**
```python
self.current_theme       # ThemeLoader instance
self.input_path          # Path object
self.output_path         # Path object
```

### **Methods:**
```python
self.apply_theme()       # Apply current theme
self.refresh_theme()     # Refresh when theme switches
self.create_execution_log(layout)  # Add execution log
self.setup_window_properties(title, width, height)  # Setup window
```

---

## 💡 **Quick Example**

Here's a minimal tool in ~30 lines:

```python
from tools.base_tool_template import BaseToolDialog
from PySide6.QtWidgets import QVBoxLayout, QPushButton

class QuickTool(BaseToolDialog):
    def __init__(self, parent, input_path, output_path):
        super().__init__(parent, input_path, output_path)
        
        self.setup_window_properties("Quick Tool", 600, 400)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        button = QPushButton("Click Me!")
        button.clicked.connect(self.on_click)
        layout.addWidget(button)
        
        # Add log
        self.execution_log = self.create_execution_log(layout)
    
    def on_click(self):
        self.log("Button clicked! ✨")
```

**That's it! 30 lines and you have a fully themed tool!** 🎉

---

## 🔧 **Advanced Customization**

### **Override apply_theme() for Custom Styling**

```python
def apply_theme(self):
    """Custom theme application"""
    # Call parent to apply window theme
    super().apply_theme()
    
    # Then customize specific widgets
    if self.current_theme:
        self.current_theme.apply_to_widget(self.my_button, "button_primary")
        self.current_theme.apply_to_widget(self.my_input, "input")
```

### **Add Theme-Aware Widgets**

```python
def setup_ui(self):
    layout = QVBoxLayout(self)
    
    # Create widgets
    button = QPushButton("Save")
    
    # Apply theme to widget
    if self.current_theme:
        self.current_theme.apply_to_widget(button, "button_primary")
    
    layout.addWidget(button)
```

---

## 📁 **Tool Category Folders**

Create your tool in the appropriate category:

- `tools/data_collection_import/` - Data collection tools
- `tools/data_analysis_reporting/` - Analysis tools
- `tools/data_cleaning_transformation/` - Cleaning tools
- `tools/data_export_formatting/` - Export tools
- `tools/data_merging_joining/` - Merging tools
- `tools/data_validation_quality/` - Validation tools
- `tools/file_management_organization/` - File management
- `tools/date_time_utilities/` - Date/time tools
- `tools/ga4_specific_analysis/` - GA4 specific tools
- `tools/automation_scheduling/` - Automation tools
- `tools/report_generation_visualization/` - Reporting tools

---

## ✅ **Checklist for New Tools**

When creating a new tool, make sure to:

- [ ] Inherit from `BaseToolDialog`
- [ ] Call `super().__init__(parent, input_path, output_path)`
- [ ] Call `self.setup_window_properties(title, width, height)`
- [ ] Create your UI in `setup_ui()` method
- [ ] Optionally add execution log with `self.create_execution_log(layout)`
- [ ] Test standalone with the `main()` function
- [ ] **DO NOT** manually implement theme methods (they're inherited!)

---

## 🎯 **Common Patterns**

### **Pattern 1: Simple Tool**

```python
class SimpleTool(BaseToolDialog):
    def __init__(self, parent, input_path, output_path):
        super().__init__(parent, input_path, output_path)
        self.setup_window_properties("Simple Tool", 600, 400)
        self.setup_ui()
    
    def setup_ui(self):
        # Your UI here
        pass
```

### **Pattern 2: Tool with Worker Thread**

```python
class WorkerTool(BaseToolDialog):
    def __init__(self, parent, input_path, output_path):
        super().__init__(parent, input_path, output_path)
        
        self.worker = None
        self.worker_thread = None
        
        self.setup_window_properties("Worker Tool", 800, 600)
        self.setup_ui()
    
    def setup_ui(self):
        # Your UI + execution log
        layout = QVBoxLayout(self)
        # ... your widgets ...
        self.execution_log = self.create_execution_log(layout)
```

### **Pattern 3: Tool with Custom Theme Application**

```python
class CustomThemedTool(BaseToolDialog):
    def apply_theme(self):
        # Apply base theme
        super().apply_theme()
        
        # Custom widget styling
        if self.current_theme:
            self.current_theme.apply_to_widget(self.save_btn, "button_primary")
            self.current_theme.apply_to_widget(self.cancel_btn, "button_secondary")
```

---

## 🌊 **Benefits of Using BaseToolDialog**

| Benefit | Description |
|---------|-------------|
| **No Setup** | Theme system works out of the box |
| **Auto-Sync** | Updates when main GUI theme changes |
| **Less Code** | ~50 lines less per tool |
| **Consistent** | All tools behave the same way |
| **Maintainable** | Fix bugs in one place |
| **Error-Safe** | Built-in error handling |

Looking for a concrete model? Check out `tools/date_time_utilities/date_format_converter.py`. It uses `allocate_run_directory()` to create timestamped `Converted/` folders, logs every conversion, and stays fully compliant with the PathManager contract.

---

## 🚀 **Quick Start**

```bash
# 1. Copy template
cp tools/templates/NEW_TOOL_TEMPLATE.py tools/my_category/my_tool.py

# 2. Edit the file
# - Change class name
# - Update title
# - Build your UI

# 3. Run it!
python tools/my_category/my_tool.py
```

---

## 💝 **That's It!**

You now have a **fully themed, beautiful tool** with:
- 🎨 All 10 themes supported
- 🔄 Auto-refresh on theme switch
- 📝 Execution log support
- 💪 Error handling
- ✨ Clean, organized code

**Creating new tools is now as easy as copy-paste-edit!** 🎉

---

*Made with love for easier tool creation* 💕

**Questions?** Check the template file or refer to the documentation.

