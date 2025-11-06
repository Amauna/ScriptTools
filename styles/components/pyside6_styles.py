"""
🌊 PySide6 Component Styles
Beautiful glass morphism, gradients, and modern styling for PySide6 widgets
"""

from typing import Dict

def hex_to_rgba(hex_color: str, alpha: float = 1.0) -> str:
    """Convert hex to rgba for Qt stylesheets"""
    hex_color = hex_color.lstrip('#')
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return f"rgba({r}, {g}, {b}, {alpha})"

def create_gradient(color1: str, color2: str, direction: str = "vertical") -> str:
    """
    Create QLinearGradient stylesheet
    
    Args:
        color1: Start color (hex)
        color2: End color (hex)
        direction: "vertical", "horizontal", "diagonal"
    
    Returns:
        QSS gradient string
    """
    if direction == "vertical":
        return f"qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {color1}, stop:1 {color2})"
    elif direction == "horizontal":
        return f"qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {color1}, stop:1 {color2})"
    else:  # diagonal
        return f"qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {color1}, stop:1 {color2})"

def get_glass_button_style(theme_colors: Dict, transparent: bool = True) -> str:
    """
    Create beautiful glass morphism button with blur effect
    
    Args:
        theme_colors: Theme color dictionary
        transparent: Use glass effect (recommended!)
    
    Returns:
        QSS stylesheet string
    """
    if transparent:
        # GORGEOUS glass morphism button! 💎
        bg_color = hex_to_rgba(theme_colors["primary"], 0.15)  # 15% opacity
        border_color = theme_colors["border"]
        text_color = theme_colors["text_primary"]
        hover_bg = hex_to_rgba(theme_colors["primary_hover"], 0.25)
        
        return f"""
            QPushButton {{
                background-color: {bg_color};
                border: 2px solid {border_color};
                border-radius: 8px;
                color: {text_color};
                padding: 8px 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {hover_bg};
                border-color: {theme_colors["border_focus"]};
            }}
            QPushButton:pressed {{
                background-color: {hex_to_rgba(theme_colors["primary"], 0.35)};
            }}
            QPushButton:disabled {{
                background-color: {hex_to_rgba(theme_colors["surface"], 0.3)};
                color: {hex_to_rgba(theme_colors["text_secondary"], 0.5)};
                border-color: {hex_to_rgba(theme_colors["border"], 0.3)};
            }}
        """
    else:
        # Solid button with gradient
        gradient = create_gradient(theme_colors["primary"], theme_colors["primary_hover"], "vertical")
        
        return f"""
            QPushButton {{
                background: {gradient};
                border: none;
                border-radius: 8px;
                color: {theme_colors["text_on_primary"]};
                padding: 8px 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: {theme_colors["primary_hover"]};
            }}
            QPushButton:pressed {{
                background: {theme_colors["primary"]};
            }}
            QPushButton:disabled {{
                background-color: {hex_to_rgba(theme_colors["surface_variant"], 0.5)};
                color: {hex_to_rgba(theme_colors["text_secondary"], 0.5)};
            }}
        """

def get_glass_frame_style(theme_colors: Dict, blur: bool = True) -> str:
    """
    Create glass morphism frame/panel with beautiful blur
    
    Args:
        theme_colors: Theme color dictionary
        blur: Enable blur effect
    
    Returns:
        QSS stylesheet string
    """
    bg_color = hex_to_rgba(theme_colors["surface"], 0.7)  # 70% opacity for glass effect
    border_color = hex_to_rgba(theme_colors["border"], 0.3)
    
    style = f"""
        QFrame {{
            background-color: {bg_color};
            border: 1px solid {border_color};
            border-radius: 12px;
            padding: 15px;
        }}
    """
    
    # Note: Qt StyleSheets don't support backdrop-filter (CSS3 property)
    # The glass effect is achieved through rgba transparency
    
    return style

def get_modern_input_style(theme_colors: Dict) -> str:
    """
    Create modern input field with smooth transitions
    
    Returns:
        QSS stylesheet string
    """
    return f"""
        QLineEdit {{
            background-color: {hex_to_rgba(theme_colors["surface"], 0.5)};
            border: 2px solid {theme_colors["border"]};
            border-radius: 6px;
            padding: 8px 12px;
            color: {theme_colors["text_primary"]};
            font-size: 11pt;
        }}
        QLineEdit:focus {{
            border-color: {theme_colors["border_focus"]};
            background-color: {hex_to_rgba(theme_colors["surface"], 0.8)};
        }}
        QLineEdit:hover {{
            border-color: {theme_colors["primary"]};
        }}
    """

def get_modern_textbox_style(theme_colors: Dict) -> str:
    """Create modern textbox/text edit styling"""
    return f"""
        QTextEdit, QPlainTextEdit {{
            background-color: {hex_to_rgba(theme_colors["surface_variant"], 0.8)};
            border: 1px solid {theme_colors["border"]};
            border-radius: 8px;
            padding: 10px;
            color: {theme_colors["text_primary"]};
            font-family: 'Consolas', monospace;
            font-size: 10pt;
        }}
        QTextEdit:focus, QPlainTextEdit:focus {{
            border-color: {theme_colors["border_focus"]};
        }}
    """

def get_modern_dropdown_style(theme_colors: Dict) -> str:
    """Create modern dropdown/combobox styling"""
    return f"""
        QComboBox {{
            background-color: {theme_colors["surface"]};
            border: 2px solid {theme_colors["border"]};
            border-radius: 6px;
            padding: 6px 12px;
            color: {theme_colors["text_primary"]};
            min-width: 150px;
        }}
        QComboBox:hover {{
            border-color: {theme_colors["primary"]};
        }}
        QComboBox:focus {{
            border-color: {theme_colors["border_focus"]};
        }}
        QComboBox::drop-down {{
            border: none;
            width: 30px;
        }}
        QComboBox::down-arrow {{
            image: none;
            border: none;
            width: 12px;
            height: 12px;
        }}
        QComboBox QAbstractItemView {{
            background-color: {theme_colors["surface"]};
            border: 2px solid {theme_colors["border"]};
            selection-background-color: {theme_colors["primary"]};
            selection-color: {theme_colors["text_on_primary"]};
            color: {theme_colors["text_primary"]};
            padding: 4px;
        }}
    """

def get_modern_checkbox_style(theme_colors: Dict) -> str:
    """Create modern checkbox/switch styling"""
    return f"""
        QCheckBox {{
            color: {theme_colors["text_primary"]};
            spacing: 8px;
        }}
        QCheckBox::indicator {{
            width: 20px;
            height: 20px;
            border: 2px solid {theme_colors["border"]};
            border-radius: 4px;
            background-color: {theme_colors["surface"]};
        }}
        QCheckBox::indicator:hover {{
            border-color: {theme_colors["primary"]};
        }}
        QCheckBox::indicator:checked {{
            background-color: {theme_colors["primary"]};
            border-color: {theme_colors["primary"]};
            image: url(none);  /* You can add checkmark icon here */
        }}
    """

def get_modern_scrollbar_style(theme_colors: Dict) -> str:
    """Create modern scrollbar styling"""
    return f"""
        QScrollBar:vertical {{
            background-color: {hex_to_rgba(theme_colors["surface"], 0.3)};
            width: 12px;
            margin: 0px;
            border-radius: 6px;
        }}
        QScrollBar::handle:vertical {{
            background-color: {theme_colors["primary"]};
            min-height: 30px;
            border-radius: 6px;
        }}
        QScrollBar::handle:vertical:hover {{
            background-color: {theme_colors["primary_hover"]};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
            background: none;
        }}
    """

def get_app_stylesheet(theme_colors: Dict) -> str:
    """
    Get complete application stylesheet with glass morphism and modern design
    
    Returns:
        Complete QSS stylesheet string
    """
    return f"""
        /* Main Application Window - Beautiful gradient background */
        QMainWindow, QDialog {{
            background: {create_gradient(theme_colors["background"], theme_colors["surface"], "vertical")};
        }}
        
        /* Tool Dialogs */
        QDialog[objectName="toolDialog"] {{
            background: {create_gradient(theme_colors["background"], theme_colors["surface"], "vertical")};
        }}
        
        /* Glass Morphism Cards/Frames */
        QFrame {{
            background-color: {hex_to_rgba(theme_colors["surface"], 0.7)};
            border: 1px solid {hex_to_rgba(theme_colors["border"], 0.3)};
            border-radius: 12px;
        }}
        
        /* Labels */
        QLabel {{
            color: {theme_colors["text_primary"]};
            background-color: transparent;
            border: none !important;
            outline: none !important;
        }}
        
        /* Buttons */
        {get_glass_button_style(theme_colors, transparent=True)}
        
        /* Input Fields */
        {get_modern_input_style(theme_colors)}
        
        /* Text Boxes */
        {get_modern_textbox_style(theme_colors)}
        
        /* Dropdowns */
        {get_modern_dropdown_style(theme_colors)}
        
        /* Checkboxes */
        {get_modern_checkbox_style(theme_colors)}
        
        /* Scrollbars */
        {get_modern_scrollbar_style(theme_colors)}
        
        /* Progress Bar */
        QProgressBar {{
            background-color: {hex_to_rgba(theme_colors["surface_variant"], 0.5)};
            border: 1px solid {theme_colors["border"]};
            border-radius: 10px;
            height: 20px;
            text-align: center;
            color: {theme_colors["text_primary"]};
        }}
        QProgressBar::chunk {{
            background: {create_gradient(theme_colors["primary"], theme_colors["primary_hover"], "horizontal")};
            border-radius: 10px;
        }}
        
        /* ========== DATA SUMMARY TOOL SPECIFIC STYLES ========== */
        
        /* Section Titles */
        QLabel[objectName="sectionTitle"] {{
            color: {theme_colors["primary"]};
            font-weight: bold;
            font-size: 14px;
            border: none;
            background: transparent;
            margin-bottom: 15px;
        }}
        
        /* Info Labels */
        QLabel[objectName="infoLabel"] {{
            color: {theme_colors["text_secondary"]};
            margin: 10px 0;
            border: none !important;
            outline: none !important;
            background: transparent;
        }}
        
        /* Chart Display */
        QLabel[objectName="chartDisplay"] {{
            color: {theme_colors["primary"]};
            margin: 5px 0;
            border: none !important;
            outline: none !important;
            background: transparent;
        }}
        
        /* Glass Frames */
        QWidget[objectName="glassFrame"] {{
            background-color: {hex_to_rgba(theme_colors["surface"], 0.7)};
            border: 1px solid {hex_to_rgba(theme_colors["border"], 0.3)};
            border-radius: 10px;
            padding: 15px;
        }}
        
        /* Tables */
        QTableWidget[objectName="tableWidget"] {{
            background-color: {hex_to_rgba(theme_colors["surface"], 0.9)};
            border: 1px solid {hex_to_rgba(theme_colors["border"], 0.3)};
            border-radius: 10px;
            gridline-color: {hex_to_rgba(theme_colors["border"], 0.2)};
            color: {theme_colors["text_primary"]};
        }}
        QTableWidget[objectName="tableWidget"]::item {{
            padding: 8px;
            border-bottom: 1px solid {hex_to_rgba(theme_colors["border"], 0.1)};
        }}
        QTableWidget[objectName="tableWidget"]::item:selected {{
            background-color: {hex_to_rgba(theme_colors["primary"], 0.3)};
        }}
        QTableWidget[objectName="tableWidget"] QHeaderView::section {{
            background-color: {hex_to_rgba(theme_colors["primary"], 0.8)};
            color: {theme_colors["text_on_primary"]};
            padding: 10px;
            border: 1px solid {hex_to_rgba(theme_colors["border"], 0.3)};
            font-weight: bold;
            font-size: 10px;
            border-radius: 6px;
        }}
        
        /* Tabs */
        QTabWidget[objectName="tabWidget"]::pane {{
            border: 1px solid {hex_to_rgba(theme_colors["border"], 0.3)};
            border-radius: 10px;
            background-color: {hex_to_rgba(theme_colors["surface"], 0.8)};
        }}
        QTabWidget[objectName="tabWidget"] QTabBar::tab {{
            background-color: {hex_to_rgba(theme_colors["surface"], 0.6)};
            color: {theme_colors["text_primary"]};
            padding: 10px 20px;
            margin-right: 2px;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
            border: 1px solid {hex_to_rgba(theme_colors["border"], 0.3)};
        }}
        QTabWidget[objectName="tabWidget"] QTabBar::tab:selected {{
            background-color: {hex_to_rgba(theme_colors["primary"], 0.8)};
            color: {theme_colors["text_on_primary"]};
        }}
        QTabWidget[objectName="tabWidget"] QTabBar::tab:hover {{
            background-color: {hex_to_rgba(theme_colors["primary"], 0.5)};
        }}
        
        /* Modern Dropdown */
        QComboBox[objectName="modernDropdown"] {{
            background-color: {hex_to_rgba(theme_colors["surface"], 0.8)};
            border: 1px solid {hex_to_rgba(theme_colors["border"], 0.4)};
            border-radius: 8px;
            padding: 8px;
            color: {theme_colors["text_primary"]};
            min-width: 200px;
        }}
        QComboBox[objectName="modernDropdown"]::drop-down {{
            border: none;
        }}
        QComboBox[objectName="modernDropdown"]::down-arrow {{
            image: none;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 5px solid {theme_colors["text_primary"]};
            margin-right: 10px;
        }}
        QComboBox[objectName="modernDropdown"] QAbstractItemView {{
            background-color: {hex_to_rgba(theme_colors["surface"], 0.95)};
            border: 1px solid {hex_to_rgba(theme_colors["border"], 0.3)};
            color: {theme_colors["text_primary"]};
            selection-background-color: {hex_to_rgba(theme_colors["primary"], 0.3)};
        }}
        
        /* ========== LOOKER STUDIO TOOL SPECIFIC STYLES ========== */
        
        /* Tool Title */
        QLabel[objectName="toolTitle"] {{
            color: {theme_colors["primary"]};
            font-weight: bold;
            font-size: 16px;
            margin-bottom: 20px;
            border: none;
            background: transparent;
        }}
        
        /* URL Input */
        QLineEdit[objectName="urlInput"] {{
            background-color: {hex_to_rgba(theme_colors["surface"], 0.5)};
            border: 2px solid {theme_colors["border"]};
            border-radius: 6px;
            padding: 8px 12px;
            color: {theme_colors["text_primary"]};
        }}
        QLineEdit[objectName="urlInput"]:focus {{
            border-color: {theme_colors["border_focus"]};
        }}
        
        /* Browser Combo */
        QComboBox[objectName="browserCombo"] {{
            background-color: {hex_to_rgba(theme_colors["surface"], 0.7)};
            border: 2px solid {theme_colors["border"]};
            border-radius: 6px;
            padding: 6px 12px;
            color: {theme_colors["text_primary"]};
        }}
        
        /* Wait Time Input */
        QLineEdit[objectName="waitTimeInput"] {{
            background-color: {hex_to_rgba(theme_colors["surface"], 0.5)};
            border: 2px solid {theme_colors["border"]};
            border-radius: 6px;
            padding: 6px 12px;
            color: {theme_colors["text_primary"]};
        }}
        
        /* Date Input */
        QDateEdit[objectName="dateInput"] {{
            background-color: transparent;
            border: 1px solid {hex_to_rgba(theme_colors["border"], 0.4)};
            border-radius: 6px;
            padding: 4px 8px;
            color: {theme_colors["text_primary"]};
            text-align: center;
        }}
        QDateEdit[objectName="dateInput"]:focus {{
            border-color: {theme_colors["border_focus"]};
            background-color: {hex_to_rgba(theme_colors["surface"], 0.2)};
        }}
        QDateEdit[objectName="dateInput"]:hover {{
            background-color: {hex_to_rgba(theme_colors["surface"], 0.1)};
        }}
        
        /* Preset Buttons */
        QPushButton[objectName="presetButton"] {{
            background-color: {hex_to_rgba(theme_colors["surface"], 0.6)};
            border: 1px solid {hex_to_rgba(theme_colors["border"], 0.4)};
            border-radius: 6px;
            color: {theme_colors["text_primary"]};
            padding: 6px 12px;
            font-weight: bold;
        }}
        QPushButton[objectName="presetButton"]:hover {{
            background-color: {hex_to_rgba(theme_colors["primary"], 0.2)};
            border-color: {theme_colors["border_focus"]};
            color: {theme_colors["primary"]};
        }}
        QPushButton[objectName="presetButton"]:pressed {{
            background-color: {hex_to_rgba(theme_colors["primary"], 0.3)};
            border-color: {theme_colors["primary"]};
        }}
        
        /* Action Buttons */
        QPushButton[objectName="actionButton"] {{
            background-color: {hex_to_rgba(theme_colors["primary"], 0.15)};
            border: 2px solid {theme_colors["border"]};
            border-radius: 8px;
            color: {theme_colors["text_primary"]};
            padding: 10px 16px;
            font-weight: bold;
        }}
        QPushButton[objectName="actionButton"]:hover {{
            background-color: {hex_to_rgba(theme_colors["primary_hover"], 0.25)};
            border-color: {theme_colors["border_focus"]};
        }}
        QPushButton[objectName="actionButton"]:disabled {{
            background-color: {hex_to_rgba(theme_colors["surface"], 0.3)};
            color: {hex_to_rgba(theme_colors["text_secondary"], 0.5)};
            border-color: {hex_to_rgba(theme_colors["border"], 0.3)};
        }}
        
        /* Log Buttons */
        QPushButton[objectName="logButton"] {{
            background-color: transparent;
            border: 2px solid {theme_colors["primary"]};
            border-radius: 8px;
            color: {theme_colors["text_primary"]};
            padding: 6px 12px;
            font-weight: bold;
        }}
        QPushButton[objectName="logButton"]:hover {{
            background-color: {hex_to_rgba(theme_colors["primary_hover"], 0.15)};
        }}
        
        /* Log Text */
        QTextEdit[objectName="logText"] {{
            background-color: {hex_to_rgba(theme_colors["surface"], 0.6)};
            border: 1px solid {hex_to_rgba(theme_colors["border"], 0.3)};
            border-radius: 8px;
            color: {theme_colors["text_primary"]};
            padding: 10px;
        }}
        
        /* Output Label */
        QLabel[objectName="outputLabel"] {{
            color: {theme_colors["text_secondary"]};
            border: none !important;
            outline: none !important;
            background: transparent;
        }}
        
        /* Status Label */
        QLabel[objectName="statusLabel"] {{
            color: {theme_colors["text_secondary"]};
            border: none !important;
            outline: none !important;
            background: transparent;
        }}
        
        /* Progress Bar */
        QProgressBar[objectName="progressBar"] {{
            background-color: {hex_to_rgba(theme_colors["surface_variant"], 0.5)};
            border: 1px solid {theme_colors["border"]};
            border-radius: 10px;
            height: 20px;
            text-align: center;
            color: {theme_colors["text_primary"]};
        }}
        QProgressBar[objectName="progressBar"]::chunk {{
            background: {create_gradient(theme_colors["primary"], theme_colors["primary_hover"], "horizontal")};
            border-radius: 10px;
        }}
        
        /* ========== MAIN GUI SPECIFIC COMPONENTS ========== */
        
        /* Header Frame */
        QFrame[objectName="headerFrame"] {{
            background-color: {hex_to_rgba(theme_colors["surface"], 0.7)};
            border: 1px solid {hex_to_rgba(theme_colors["border"], 0.3)};
            border-radius: 12px;
        }}
        
        /* Path Frame */
        QFrame[objectName="pathFrame"] {{
            background-color: {hex_to_rgba(theme_colors["surface"], 0.6)};
            border: 1px solid {hex_to_rgba(theme_colors["border"], 0.25)};
            border-radius: 10px;
        }}
        
        /* Footer Frame */
        QFrame[objectName="footerFrame"] {{
            background-color: {hex_to_rgba(theme_colors["surface"], 0.5)};
            border: 1px solid {hex_to_rgba(theme_colors["border"], 0.2)};
            border-radius: 10px;
        }}
        
        /* Sidebar Scroll Area */
        QScrollArea[objectName="sidebarScroll"] {{
            background-color: {hex_to_rgba(theme_colors["surface"], 0.8)};
            border: 1px solid {theme_colors["border"]};
            border-radius: 15px;
        }}
        QScrollArea[objectName="sidebarScroll"] QWidget {{
            background-color: transparent;
        }}
        
        /* Content Scroll Area */
        QScrollArea[objectName="contentScroll"] {{
            background-color: transparent;
            border: none;
        }}
        QScrollArea[objectName="contentScroll"] QWidget {{
            background-color: transparent;
        }}
        
        /* Category Buttons */
        QPushButton[objectName="categoryButton"] {{
            background-color: {hex_to_rgba(theme_colors["primary"], 0.15)};
            border: 2px solid {theme_colors["border"]};
            border-radius: 8px;
            color: {theme_colors["text_primary"]};
            padding: 10px 15px;
            font-size: 12pt;
            font-weight: bold;
            text-align: left;
            min-height: 50px;
        }}
        QPushButton[objectName="categoryButton"]:hover {{
            background-color: {hex_to_rgba(theme_colors["primary_hover"], 0.25)};
            border-color: {theme_colors["border_focus"]};
        }}
        QPushButton[objectName="categoryButton"]:pressed {{
            background-color: {hex_to_rgba(theme_colors["primary"], 0.35)};
        }}
        
        /* Tool Cards */
        QFrame[objectName="toolCard"] {{
            background-color: {hex_to_rgba(theme_colors["surface"], 0.75)};
            border: 2px solid {hex_to_rgba(theme_colors["border"], 0.4)};
            border-radius: 12px;
        }}
        
        /* Launch Buttons */
        QPushButton[objectName="launchButton"] {{
            background-color: {hex_to_rgba(theme_colors["primary"], 0.15)};
            border: 2px solid {theme_colors["primary"]};
            border-radius: 8px;
            color: {theme_colors["text_primary"]};
            padding: 10px 20px;
            font-size: 11pt;
            font-weight: bold;
            min-height: 40px;
        }}
        QPushButton[objectName="launchButton"]:hover {{
            background-color: {hex_to_rgba(theme_colors["primary_hover"], 0.25)};
            border-color: {theme_colors["border_focus"]};
        }}
        QPushButton[objectName="launchButton"]:pressed {{
            background-color: {hex_to_rgba(theme_colors["primary"], 0.35)};
        }}
        QPushButton[objectName="launchButton"]:disabled {{
            background-color: {hex_to_rgba(theme_colors["surface"], 0.3)};
            color: {hex_to_rgba(theme_colors["text_secondary"], 0.5)};
            border-color: {hex_to_rgba(theme_colors["border"], 0.3)};
        }}
        
        /* Glass Buttons (Browse, etc.) */
        QPushButton[objectName="glassButton"] {{
            background-color: {hex_to_rgba(theme_colors["primary"], 0.15)};
            border: 2px solid {theme_colors["border"]};
            border-radius: 8px;
            color: {theme_colors["text_primary"]};
            padding: 6px 12px;
            font-weight: bold;
        }}
        QPushButton[objectName="glassButton"]:hover {{
            background-color: {hex_to_rgba(theme_colors["primary_hover"], 0.25)};
            border-color: {theme_colors["border_focus"]};
        }}
        
        /* Special Labels */
        QLabel[objectName="titleLabel"] {{
            color: {theme_colors["primary"]};
            border: none;
            background: transparent;
        }}
        QLabel[objectName="footerLabel"] {{
            color: {theme_colors["text_secondary"]};
            border: none !important;
            outline: none !important;
            background: transparent;
        }}
        QLabel[objectName="categoryTitle"] {{
            color: {theme_colors["primary"]};
            border: none;
            background: transparent;
        }}
        QLabel[objectName="toolName"] {{
            color: {theme_colors["text_primary"]};
            border: none;
            background: transparent;
        }}
        QLabel[objectName="toolDescription"] {{
            color: {theme_colors["text_secondary"]};
            border: none !important;
            outline: none !important;
            background: transparent;
        }}
        QLabel[objectName="welcomeLabel"] {{
            color: {theme_colors["text_secondary"]};
            border: none !important;
            outline: none !important;
            background: transparent;
        }}
        QLabel[objectName="comingSoonLabel"] {{
            color: {theme_colors["text_secondary"]};
            border: none !important;
            outline: none !important;
            background: transparent;
        }}
        
        /* Theme ComboBox */
        QComboBox {{
            background-color: {hex_to_rgba(theme_colors["surface"], 0.7)};
            border: 2px solid {theme_colors["border"]};
            border-radius: 6px;
            padding: 6px 12px;
            color: {theme_colors["text_primary"]};
            min-width: 200px;
        }}
        QComboBox:hover {{
            border-color: {theme_colors["primary"]};
        }}
        QComboBox::drop-down {{
            border: none;
            width: 30px;
        }}
        QComboBox QAbstractItemView {{
            background-color: {theme_colors["surface"]};
            border: 2px solid {theme_colors["border"]};
            selection-background-color: {theme_colors["primary"]};
            selection-color: {theme_colors["text_on_primary"]};
            color: {theme_colors["text_primary"]};
            padding: 4px;
        }}
        
        /* Help Text */
        QLabel[objectName="helpText"] {{
            color: {theme_colors["text_secondary"]};
            font-style: italic;
            border: none !important;
            outline: none !important;
            background: transparent;
        }}
        
        /* Data Summary Tool Styles */
        QLabel[objectName="statLabel"] {{
            color: {theme_colors["text_secondary"]};
            min-width: 120px;
            border: none !important;
            outline: none !important;
            background: transparent;
        }}
        
        QLabel[objectName="valueLabel"] {{
            color: {theme_colors["text_primary"]};
            margin-bottom: 5px;
            border: none !important;
            outline: none !important;
            background: transparent;
        }}
        
        QLabel[objectName="metricLabel"] {{
            color: {theme_colors["text_secondary"]};
            border: none !important;
            outline: none !important;
            background: transparent;
        }}
        
        QLabel[objectName="sectionTitle"] {{
            color: {theme_colors["primary"]};
            margin-top: 20px;
            margin-bottom: 10px;
            border: none;
            background: transparent;
        }}
        
        QLabel[objectName="fileLabel"] {{
            color: {theme_colors["text_primary"]};
            border: none !important;
            outline: none !important;
            background: transparent;
        }}
        
        QLabel[objectName="summaryLabel"] {{
            color: {theme_colors["text_secondary"]};
            border: none !important;
            outline: none !important;
            background: transparent;
        }}
        
        QWidget[objectName="metricCard"] {{
            background-color: {hex_to_rgba(theme_colors["surface"], 0.8)};
            border: 1px solid {hex_to_rgba(theme_colors["border"], 0.3)};
            border-radius: 10px;
            padding: 15px;
        }}
        
        QWidget[objectName="dataContainer"] {{
            background-color: {hex_to_rgba(theme_colors["surface"], 0.8)};
            border: 1px solid {hex_to_rgba(theme_colors["border"], 0.3)};
            border-radius: 8px;
            padding: 10px;
            margin: 5px;
        }}
        
        QTableWidget[objectName="dataTable"] {{
            background-color: {hex_to_rgba(theme_colors["surface"], 0.9)};
            border: 1px solid {hex_to_rgba(theme_colors["border"], 0.5)};
            border-radius: 8px;
            gridline-color: {hex_to_rgba(theme_colors["border"], 0.3)};
            color: {theme_colors["text_primary"]};
        }}
        QTableWidget[objectName="dataTable"]::item {{
            padding: 6px;
            border-bottom: 1px solid {hex_to_rgba(theme_colors["border"], 0.1)};
        }}
        QTableWidget[objectName="dataTable"]::item:selected {{
            background-color: {hex_to_rgba(theme_colors["primary"], 0.3)};
        }}
        QTableWidget[objectName="dataTable"] QHeaderView::section {{
            background-color: {hex_to_rgba(theme_colors["primary"], 0.7)};
            color: {theme_colors["text_on_primary"]};
            padding: 8px;
            border: 1px solid {hex_to_rgba(theme_colors["border"], 0.3)};
            font-weight: bold;
            font-size: 9px;
            border-radius: 4px;
        }}
        
        QLabel[objectName="previewLabel"] {{
            padding: 8px;
            background-color: {hex_to_rgba(theme_colors["surface"], 0.1)};
            border-radius: 4px;
        }}
        
        /* Execution Log Footer Styles */
        QFrame[objectName="executionLogFooter"] {{
            background-color: {hex_to_rgba(theme_colors["surface"], 0.7)};
            border: 1px solid {hex_to_rgba(theme_colors["border"], 0.3)};
            border-radius: 12px;
            margin-top: 10px;
        }}
        
        QLabel[objectName="logTitle"] {{
            color: {theme_colors["text_primary"]};
            font-weight: bold;
            border: none !important;
            outline: none !important;
            background: transparent;
        }}
        
        QPushButton[objectName="logButton"] {{
            background-color: {hex_to_rgba(theme_colors["primary"], 0.8)};
            color: {theme_colors["text_on_primary"]};
            border: 1px solid {hex_to_rgba(theme_colors["primary"], 0.5)};
            border-radius: 6px;
            font-weight: bold;
            padding: 5px 10px;
        }}
        
        QPushButton[objectName="logButton"]:hover {{
            background-color: {theme_colors["primary_hover"]};
            border-color: {theme_colors["primary_hover"]};
        }}
        
        QPushButton[objectName="logButton"]:pressed {{
            background-color: {theme_colors["primary"]};
        }}
        
        QPushButton[objectName="logButton"]:disabled {{
            background-color: {hex_to_rgba(theme_colors["text_secondary"], 0.5)};
            color: {hex_to_rgba(theme_colors["text_secondary"], 0.7)};
            border-color: {hex_to_rgba(theme_colors["text_secondary"], 0.3)};
        }}
    """

