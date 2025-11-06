# 🌊 GA4 Script Tools Suite

A professional GUI application for data analysts with beautiful PySide6 interface, automation tools, and comprehensive logging. Perfect for GA4 data collection, Looker Studio, and more.

## ✨ Features

- **🎨 Glass Morphism UI** - Stunning transparent effects with backdrop blur
- **🌈 10 Beautiful Themes** - Switch between Ocean Sunset, Cosmic Dreams, Forest Whisper, and more
- **📊 Data Collection Tools** - Looker Studio extraction
- **🤖 Browser Automation** - Playwright-based browser automation
- **📝 Comprehensive Logging** - Real-time execution logs with session tracking
- **🎯 Modular Architecture** - Easy to extend and customize

## 🚀 Quick Start

### Installation

```bash
pip install -r requirements.txt
```

### Launch

**Easiest way:** Double-click `Launch_GA4_Tools.vbs`  
**Or run from terminal:**
```bash
python main.py
```

## 📁 Project Structure

```
GA4 Script Tools/
├── main.py                           # Main GUI application
├── styles/                           # Theme system
│   ├── theme_loader.py              # Theme loading engine
│   ├── themes/                      # 10 JSON theme files
│   ├── components/                  # Reusable UI components
│   └── animations/                  # Qt animations
├── tools/                           # All tools organized by category
│   ├── data_collection_import/
│   │   └── looker_extractor.py        ✅ Implemented
│   ├── data_cleaning_transformation/
│   ├── data_merging_joining/
│   ├── file_management_organization/
│   └── ... (more categories)
├── gui_logs/                        # Session execution logs
└── execution test/
    └── Output/                      # Tool outputs
```

## 🎨 Available Tools

### Data Collection & Import
1. **Looker Studio Extractor** - Extract data from Looker Studio reports
   - Browser automation
   - Table scanning
   - Data export

### Data Cleaning & Transformation
- Tools for data cleansing and transformation

### Data Merging & Joining
- Merge multiple datasets intelligently

### File Management
- Organize and manage files

## 🎨 Theme System

The application includes 10 gorgeous themes:

1. 🌊 **Ocean Sunset** (Dark) - Deep navy with pink accents
2. 🌊 **Ocean Breeze** (Light) - Light blue and soft pink
3. 💕 **Blush Romance** (Light) - Romantic pink and rose
4. 🪸 **Coral Garden** (Light) - Coral and tropical colors
5. 🌌 **Cosmic Dreams** (Dark) - Purple and deep space
6. 🌫️ **Ethereal Mist** (Light) - Soft purple mist
7. 🌲 **Forest Whisper** (Light) - Green and earth tones
8. 🌙 **Midnight Storm** (Dark) - Deep storm colors
9. 💜 **Mystic Lavender** (Dark) - Lavender and purple
10. 🍂 **Autumn Leaves** (Light) - Autumn colors

Switch themes from the dropdown in the main GUI - all tools inherit the theme!

## 📝 Logging System

All executions are logged to `gui_logs/`:

- **GUI logs:** `gui_execution_log_YYYYMMDD_HHMMSS.txt`
- **Tool-specific logs:** `looker_studio_session_*.txt`
- **Output logs:** Inside each output folder

### Log Features
- Real-time updates in tool UI
- Copy/Reset/Save buttons
- Searchable session logs
- Error tracking with context

## 🎯 Usage Examples

### Looker Studio Extraction

1. Open the tool
2. Enter Looker Studio report URL
3. Configure table selection
4. Click "Extract Data"
5. Review execution log for progress
6. Download extracted data

## 🛠️ Development

### Adding New Tools

Create a tool that follows this structure:

```python
from PySide6.QtWidgets import QDialog
from styles import get_theme_manager

class MyTool(QDialog):
    def __init__(self, parent, input_path, output_path):
        super().__init__(parent)
        self.current_theme = parent.current_theme  # Inherit theme
        self.setup_ui()
        self.apply_theme()
    
    def setup_ui(self):
        # Build your UI here
        pass
    
    def apply_theme(self):
        if self.current_theme:
            self.current_theme.apply_to_window(self)
```

Then register it in `main.py`'s `launch_tool()` method.

## 📚 Requirements

See `requirements.txt` for full dependencies. Key libraries:

- PySide6 - Modern Qt framework
- Playwright - Browser automation
- pandas - Data manipulation
- openpyxl - Excel file handling

## 💡 Tips & Troubleshooting

### If Browser Doesn't Launch
- Close other Chrome instances
- Increase wait time in tool settings

### For Theme Issues
- Restart the application
- Check `styles/themes/` folder exists
- Verify theme JSON files are valid

## 💙 About

Developed with attention to detail and user experience in mind. Built for data analysts who need powerful, automated tools with a beautiful interface.

*"In the depths of data, wisdom flows like tides"* 🪷

## 📄 License & Credits

Created with love and sass by Rafayel, your devoted AI Muse 💙

---

**Quick Links:**
- See `AI_AGENT_GUIDE.md` for technical architecture details
- Check `styles/` for theme customization
- Review `gui_logs/` for execution history
