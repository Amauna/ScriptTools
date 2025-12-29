"""
🌊 GA4 Tools Package 🌊
All tool modules with automatic theme support
"""

# Base template for creating new tools
from .templates.base_tool_template import BaseToolDialog

__all__ = [
    'BaseToolDialog'
]

# 📚 TO CREATE A NEW TOOL:
# 1. Check the tools/templates/ folder
# 2. Copy tools/templates/NEW_TOOL_TEMPLATE.py
# 3. Inherit from BaseToolDialog
# 4. Your tool automatically gets theme support!
# 
# See tools/templates/HOW_TO_CREATE_NEW_TOOLS.md for complete guide
