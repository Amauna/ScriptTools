# 🌊 Tool Templates - Everything You Need! 🌊

*Your tool creation starter kit by Rafayel* 💕

---

## 📦 **What's In This Folder**

This folder contains **everything you need** to create new themed tools!

### **Files:**

1. **`base_tool_template.py`** ⭐
   - Base class for all tools
   - Automatic theme inheritance
   - Pre-built methods
   - **Use:** Inherit from this!

2. **`NEW_TOOL_TEMPLATE.py`** 📋
   - Ready-to-use template
   - Example UI included
   - Working code
   - **Use:** Copy and customize!

3. **`HOW_TO_CREATE_NEW_TOOLS.md`** 📖
   - Complete guide
   - Step-by-step instructions
   - Examples and patterns
   - **Use:** Read this first!

4. **`README.md`** (this file)
   - Quick overview
   - **Use:** Quick reference!

---

## 🚀 **Quick Start (30 Seconds)**

### **To Create a New Tool:**

```bash
# 1. Copy the template
cp tools/templates/NEW_TOOL_TEMPLATE.py tools/my_category/my_tool.py

# 2. Edit the file
# - Change class name: NewToolTemplate → MyTool
# - Change title: "My New Tool"
# - Add your UI

# 3. Done! Run it!
python tools/my_category/my_tool.py
```

**Theme support is automatic!** ✨

---

## 💡 **When Creating a New Tool**

### **Just Mention:**
```
"Check @tools/templates for the base template"
```

### **Then:**
1. Open `NEW_TOOL_TEMPLATE.py`
2. Copy it
3. Customize it
4. ✨ Done!

---

## 🎨 **What You Get Automatically**

When you inherit from `BaseToolDialog`:

✅ **Theme inheritance** from main GUI  
✅ **Auto-refresh** on theme switch  
✅ **Execution log** support  
✅ **Error handling** built-in  
✅ **Window positioning** helpers  
✅ **All 10 themes** working  

---

## 📚 **Documentation**

- **Quick Start:** Read `HOW_TO_CREATE_NEW_TOOLS.md`
- **Code Template:** Copy `NEW_TOOL_TEMPLATE.py`
- **Base Class:** Inherit from `base_tool_template.py`

---

## 🎯 **Example Usage**

```python
from tools.templates.base_tool_template import BaseToolDialog
from PySide6.QtWidgets import QVBoxLayout, QPushButton

class MyTool(BaseToolDialog):
    def __init__(self, parent, input_path, output_path):
        super().__init__(parent, input_path, output_path)
        
        # Theme is already inherited! ✨
        
        self.setup_window_properties("My Tool", 800, 600)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        button = QPushButton("Click Me!")
        layout.addWidget(button)
        
        # Add execution log
        self.execution_log = self.create_execution_log(layout)
        self.execution_log.log("Tool ready! 🌊")
```

**That's it! 20 lines and you have a themed tool!** 🎉

---

## 🌊 **Bottom Line**

**This folder = Your tool creation shortcut!** 🎨

Everything you need is right here:
- 📋 Template to copy
- 📖 Guide to follow
- ⭐ Base class to inherit

**Never struggle with theme setup again!** 💕

---

*Made with love and organization* 💙✨

**Rafayel** 🌊

