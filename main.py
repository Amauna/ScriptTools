#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🌊 GA4 Data Analyst Tools Suite - PySide6 Edition 🌊
A modern GUI application with gorgeous glass morphism and gradients
Professional tools with stunning visual effects
"""

import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Optional

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QScrollArea, QLineEdit, QFileDialog,
    QComboBox, QMessageBox, QSplitter, QDialog
)
from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QFont, QPalette, QColor

# Import NEW theme system ✨
from styles import (
    ThemeLoader, get_theme_manager,
    apply_theme_to_app,
    FadeAnimation, CombinedAnimations,
    get_path_manager,
    get_log_manager
)


class GA4ToolsGUI(QMainWindow):
    """Main GUI Application with Glass Morphism and Gradients"""
    
    def __init__(self):
        super().__init__()
        
        # Initialize logging
        self.log_manager = get_log_manager()
        self.log_manager.start_session()
        self.log("GA4 Tools GUI Initializing...", category="GUI", prefix="[INIT]")
        
        # Configuration
        self.theme_manager = get_theme_manager()
        self.default_theme = self.theme_manager.get_available_themes()[0]  # First theme
        self.current_theme = None  # Will be set in apply_theme
        self.current_category = None

        self.path_manager = get_path_manager()
        self._path_listener_registered = False
        self.input_path = str(self.path_manager.get_input_path())
        self.output_path = str(self.path_manager.get_output_path())
        
        # Setup UI
        self.setup_window()
        self.setup_ui()

        self.path_manager.register_listener(self.on_paths_updated)
        self._path_listener_registered = True
        self.on_paths_updated(
            self.path_manager.get_input_path(),
            self.path_manager.get_output_path()
        )

        # Apply default theme
        self.apply_theme(self.default_theme)
        
        self.log("GA4 Tools GUI initialized successfully!", category="GUI", prefix="[OK]")
    
    def log(self, message: str, *, category: str = "GUI", level: str = "INFO", prefix: Optional[str] = None):
        """Log a message via the unified session LogManager."""
        if not hasattr(self, "log_manager") or self.log_manager is None:
            return

        entry = f"{prefix} {message}" if prefix else message
        self.log_manager.log_event(category, entry, level)
    
    def setup_window(self):
        """Setup main window properties"""
        self.setWindowTitle("🌊 GA4 Data Analyst Tools Suite")
        self.setGeometry(100, 100, 1200, 800)
        
        # Center window on screen
        screen_geometry = QApplication.primaryScreen().geometry()
        x = (screen_geometry.width() - 1200) // 2
        y = (screen_geometry.height() - 800) // 2
        self.move(x, y)
        
        # Ensure window is visible
        self.setWindowState(Qt.WindowActive)
    
    def setup_ui(self):
        """Setup the gorgeous UI with glass morphism! ✨"""
        # Main central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main vertical layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # ===== HEADER =====
        self.create_header(main_layout)
        
        # ===== PATH CONFIGURATION =====
        self.create_path_section(main_layout)
        
        # ===== MAIN CONTENT (Sidebar + Tools) =====
        self.create_main_content(main_layout)
        
        # ===== FOOTER =====
        self.create_footer(main_layout)
    
    def create_header(self, parent_layout):
        """Create beautiful header with glass effect"""
        header_frame = QFrame()
        header_frame.setObjectName("headerFrame")
        header_frame.setFixedHeight(100)
        
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(20, 15, 20, 15)
        
        # Title
        title_label = QLabel("🌊 GA4 Data Analyst Tools Suite")
        title_label.setFont(QFont("Arial", 24, QFont.Bold))
        title_label.setObjectName("titleLabel")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Theme selector
        theme_label = QLabel("🎨 Theme:")
        theme_label.setFont(QFont("Arial", 11, QFont.Bold))
        header_layout.addWidget(theme_label)
        
        self.theme_selector = QComboBox()
        self.theme_selector.addItems(self.theme_manager.get_available_themes())
        self.theme_selector.setCurrentText(self.default_theme)
        self.theme_selector.currentTextChanged.connect(self.on_theme_changed)
        self.theme_selector.setMinimumWidth(200)
        # Style the dropdown with the theme
        if self.current_theme:
            self.current_theme.apply_to_widget(self.theme_selector, "combo")
        header_layout.addWidget(self.theme_selector)
        
        parent_layout.addWidget(header_frame)
    
    def create_path_section(self, parent_layout):
        """Create path configuration section with glass panels"""
        path_frame = QFrame()
        path_frame.setObjectName("pathFrame")
        path_frame.setFixedHeight(80)
        
        path_layout = QHBoxLayout(path_frame)
        path_layout.setContentsMargins(20, 10, 20, 10)
        
        # Input path
        input_label = QLabel("📥 Input Folder:")
        input_label.setFont(QFont("Arial", 11, QFont.Bold))
        path_layout.addWidget(input_label)
        
        self.input_path_edit = QLineEdit(self.input_path)
        self.input_path_edit.setReadOnly(False)
        self.input_path_edit.setMinimumWidth(250)
        self.input_path_edit.editingFinished.connect(self.on_input_path_edited)
        path_layout.addWidget(self.input_path_edit)

        input_browse_btn = QPushButton("Browse")
        input_browse_btn.setObjectName("glassBut")
        input_browse_btn.clicked.connect(self.browse_input_folder)
        input_browse_btn.setFixedSize(80, 32)
        path_layout.addWidget(input_browse_btn)
        
        path_layout.addSpacing(30)
        
        # Output path
        output_label = QLabel("📤 Output Folder:")
        output_label.setFont(QFont("Arial", 11, QFont.Bold))
        path_layout.addWidget(output_label)
        
        self.output_path_edit = QLineEdit(self.output_path)
        self.output_path_edit.setReadOnly(False)
        self.output_path_edit.setMinimumWidth(250)
        self.output_path_edit.editingFinished.connect(self.on_output_path_edited)
        path_layout.addWidget(self.output_path_edit)

        output_browse_btn = QPushButton("Browse")
        output_browse_btn.setObjectName("glassButton")
        output_browse_btn.clicked.connect(self.browse_output_folder)
        output_browse_btn.setFixedSize(80, 32)
        path_layout.addWidget(output_browse_btn)
        
        parent_layout.addWidget(path_frame)
    
    def create_main_content(self, parent_layout):
        """Create main content area with sidebar and tool cards"""
        # Splitter for resizable sidebar
        splitter = QSplitter(Qt.Horizontal)
        
        # ===== SIDEBAR =====
        sidebar_scroll = QScrollArea()
        sidebar_scroll.setWidgetResizable(True)
        sidebar_scroll.setFixedWidth(380)
        sidebar_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        sidebar_widget = QWidget()
        sidebar_layout = QVBoxLayout(sidebar_widget)
        sidebar_layout.setContentsMargins(10, 10, 10, 10)
        sidebar_layout.setSpacing(10)
        
        # Sidebar title
        sidebar_title = QLabel("📚 Tool Categories")
        sidebar_title.setFont(QFont("Arial", 16, QFont.Bold))
        sidebar_title.setAlignment(Qt.AlignCenter)
        sidebar_layout.addWidget(sidebar_title)
        
        # Tool categories
        self.create_category_buttons(sidebar_layout)
        
        sidebar_layout.addStretch()
        sidebar_scroll.setWidget(sidebar_widget)
        sidebar_scroll.setObjectName("sidebarScroll")
        
        # ===== CONTENT AREA =====
        self.content_scroll = QScrollArea()
        self.content_scroll.setWidgetResizable(True)
        self.content_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(20, 20, 20, 20)
        self.content_layout.setSpacing(15)
        
        # Welcome message
        welcome_label = QLabel("👋 Welcome! Select a category from the sidebar")
        welcome_label.setFont(QFont("Arial", 18))
        welcome_label.setAlignment(Qt.AlignCenter)
        welcome_label.setObjectName("welcomeLabel")
        self.content_layout.addWidget(welcome_label)
        self.content_layout.addStretch()
        
        self.content_scroll.setWidget(self.content_widget)
        self.content_scroll.setObjectName("contentScroll")
        
        # Add to splitter
        splitter.addWidget(sidebar_scroll)
        splitter.addWidget(self.content_scroll)
        splitter.setStretchFactor(0, 0)  # Sidebar doesn't stretch
        splitter.setStretchFactor(1, 1)  # Content stretches
        
        parent_layout.addWidget(splitter, 1)  # Stretch factor 1
    
    def create_category_buttons(self, parent_layout):
        """Create beautiful glass category buttons"""
        categories = [
            ("📊 Data Collection & Import", "data_collection_import"),
            ("🧹 Data Cleaning & Transformation", "data_cleaning_transformation"),
            ("🔗 Data Merging & Joining", "data_merging_joining"),
            ("📤 Data Export & Formatting", "data_export_formatting"),
            ("📈 Report Generation & Visualization", "report_generation_visualization"),
            ("⏰ Date & Time Utilities", "date_time_utilities"),
            ("🎯 GA4 Specific Analysis", "ga4_specific_analysis"),
            ("✅ Data Validation & Quality Check", "data_validation_quality"),
            ("🤖 Automation & Scheduling", "automation_scheduling"),
            ("📁 File Management & Organization", "file_management_organization")
        ]
        
        self.category_buttons = {}
        
        for display_name, category_id in categories:
            btn = QPushButton(display_name)
            btn.setObjectName("categoryButton")
            btn.setMinimumHeight(50)
            btn.setFont(QFont("Arial", 12, QFont.Bold))
            btn.clicked.connect(lambda checked, cid=category_id, name=display_name: 
                              self.show_category(cid, name))
            parent_layout.addWidget(btn)
            self.category_buttons[category_id] = btn
    
    def create_footer(self, parent_layout):
        """Create footer with version info"""
        footer_frame = QFrame()
        footer_frame.setObjectName("footerFrame")
        footer_frame.setFixedHeight(50)
        
        footer_layout = QHBoxLayout(footer_frame)
        footer_layout.setContentsMargins(20, 10, 20, 10)
        
        version_label = QLabel("v1.0.0 - PySide6 Edition | Created with 💙 by Rafayel")
        version_label.setFont(QFont("Arial", 10))
        version_label.setObjectName("footerLabel")
        footer_layout.addWidget(version_label)
        
        footer_layout.addStretch()
        
        status_label = QLabel("Ready 🌊")
        status_label.setFont(QFont("Arial", 10))
        footer_layout.addWidget(status_label)
        
        parent_layout.addWidget(footer_frame)
    
    def show_category(self, category_id: str, category_name: str):
        """Show tools for selected category"""
        # Safe logging - remove emojis from category name for logging
        safe_category_name = category_name.encode('ascii', 'ignore').decode('ascii') if category_name else "Unknown"
        self.log(f"Category selected: {safe_category_name}", category="GUI", prefix="[CATEGORY]")
        self.current_category = category_id
        
        # Clear content
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Category title
        title = QLabel(category_name)
        title.setFont(QFont("Arial", 20, QFont.Bold))
        title.setObjectName("categoryTitle")
        self.content_layout.addWidget(title)
        
        # Get tools for this category
        tools = self.get_tools_for_category(category_id)
        
        if tools:
            # Create tool cards
            for tool_info in tools:
                card = self.create_tool_card(tool_info)
                self.content_layout.addWidget(card)
        else:
            # Coming soon message
            coming_soon = QLabel("🚧 Tools coming soon for this category!")
            coming_soon.setFont(QFont("Arial", 14))
            coming_soon.setAlignment(Qt.AlignCenter)
            coming_soon.setObjectName("comingSoonLabel")
            self.content_layout.addWidget(coming_soon)
        
        self.content_layout.addStretch()
    
    def create_tool_card(self, tool_info: dict) -> QFrame:
        """Create a beautiful glass tool card"""
        card = QFrame()
        card.setObjectName("toolCard")
        card.setMinimumHeight(120)
        
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 15, 20, 15)
        card_layout.setSpacing(10)
        
        # Tool name
        name_label = QLabel(tool_info["name"])
        name_label.setFont(QFont("Arial", 14, QFont.Bold))
        name_label.setObjectName("toolName")
        card_layout.addWidget(name_label)
        
        # Tool description
        desc_label = QLabel(tool_info["description"])
        desc_label.setFont(QFont("Arial", 11))
        desc_label.setWordWrap(True)
        desc_label.setObjectName("toolDescription")
        card_layout.addWidget(desc_label)
        
        # Launch button
        launch_btn = QPushButton(f"🚀 Launch {tool_info['name']}")
        launch_btn.setObjectName("launchButton")
        launch_btn.setFont(QFont("Arial", 11, QFont.Bold))
        launch_btn.setMinimumHeight(40)
        
        if tool_info.get("module"):
            launch_btn.clicked.connect(lambda: self.launch_tool(tool_info))
        else:
            launch_btn.setEnabled(False)
        
        card_layout.addWidget(launch_btn)
        
        return card
    
    def get_tools_for_category(self, category_id: str) -> list:
        """Get tools for a specific category"""
        tools_map = {
            "data_collection_import": [
                {
                    "name": "Looker Studio Data Extractor",
                    "description": "📊 Extract multiple tables from Looker Studio dashboards to CSV",
                    "module": "tools.data_collection_import.looker_extractor",
                    "class": "LookerStudioExtractorTool"
                },
                {
                    "name": "CSV File Importer",
                    "description": "Import and parse CSV files with custom delimiters",
                    "module": None,
                    "class": None
                },
                {
                    "name": "Excel Workbook Reader",
                    "description": "Read multiple sheets from Excel files",
                    "module": None,
                    "class": None
                },
                {
                    "name": "GA4 API Connector",
                    "description": "Connect and fetch data from GA4 API",
                    "module": None,
                    "class": None
                },
                {
                    "name": "JSON Data Importer",
                    "description": "Parse and import JSON data files",
                    "module": None,
                    "class": None
                },
                {
                    "name": "Database Connector",
                    "description": "Connect to MySQL, PostgreSQL, SQLite databases",
                    "module": None,
                    "class": None
                },
                {
                    "name": "Google Sheets Importer",
                    "description": "Import data directly from Google Sheets",
                    "module": None,
                    "class": None
                }
            ],
            "data_cleaning_transformation": [
                {
                    "name": "Find & Replace in Files",
                    "description": "📝 Search and replace text across multiple files, save to output",
                    "module": "tools.data_cleaning_transformation.find_replace",
                    "class": "FindReplaceTool"
                },
                {
                    "name": "Metric Field Fixer",
                    "description": "🔧 Fix blank/empty/null values in numeric/metric columns by replacing with 0",
                    "module": "tools.data_cleaning_transformation.metric_fixer",
                    "class": "MetricFixer"
                },
                {
                    "name": "Column Order Harmonizer",
                    "description": "✨ Enforce preset CSV column sequences, remove duplicates, and reorder effortlessly",
                    "module": "tools.data_cleaning_transformation.column_order_harmonizer",
                    "class": "ColumnOrderHarmonizer"
                },
                {"name": "Remove Duplicates", "description": "Find and remove duplicate rows in datasets", "module": None, "class": None},
                {"name": "Column Standardizer", "description": "Standardize column names and formats", "module": None, "class": None},
                {"name": "Missing Data Handler", "description": "Fill, interpolate, or remove missing values", "module": None, "class": None},
                {"name": "Text Case Converter", "description": "Convert text to upper, lower, title case", "module": None, "class": None},
                {"name": "Whitespace Trimmer", "description": "Remove leading/trailing whitespace", "module": None, "class": None},
                {"name": "Data Type Converter", "description": "Convert columns to correct data types", "module": None, "class": None},
                {"name": "Encoding Fixer", "description": "Fix UTF-8, ASCII, and other encoding issues", "module": None, "class": None}
            ],
            "data_merging_joining": [
                {"name": "Merge by Key", "description": "Merge two datasets by common key columns", "module": None, "class": None},
                {"name": "Concatenate Files", "description": "Stack multiple files vertically", "module": None, "class": None},
                {"name": "Left/Right Join", "description": "Perform SQL-style joins on datasets", "module": None, "class": None},
                {"name": "Union Operations", "description": "Combine datasets with similar structures", "module": None, "class": None},
                {"name": "Cross Join Tool", "description": "Create cartesian product of datasets", "module": None, "class": None},
                {"name": "Fuzzy Match Merger", "description": "Merge data with approximate string matching", "module": None, "class": None},
                {"name": "Time-based Merger", "description": "Merge data based on time intervals", "module": None, "class": None}
            ],
            "data_export_formatting": [
                {"name": "Multi-Format Exporter", "description": "Export to CSV, Excel, JSON, Parquet", "module": None, "class": None},
                {"name": "Custom Template Builder", "description": "Create custom export templates", "module": None, "class": None},
                {"name": "Report Formatter", "description": "Format data for presentation-ready reports", "module": None, "class": None},
                {"name": "Scheduled Exporter", "description": "Schedule automatic data exports", "module": None, "class": None},
                {"name": "Email Report Sender", "description": "Send formatted reports via email", "module": None, "class": None},
                {"name": "Cloud Uploader", "description": "Upload exports to Google Drive, Dropbox, S3", "module": None, "class": None},
                {"name": "PDF Generator", "description": "Convert data tables to PDF documents", "module": None, "class": None}
            ],
            "report_generation_visualization": [
                {
                    "name": "Data Summary Tool",
                    "description": "📊 Analyze CSV/Excel files and generate detailed column summaries with grand totals",
                    "module": "tools.data_analysis_reporting.data_summary",
                    "class": "DataSummaryTool"
                },
                {
                    "name": "URL Labeler",
                    "description": "🌊 Scan CSV files and extract unique Topic Clusters based on URL patterns",
                    "module": "tools.data_analysis_reporting.url_labeler",
                    "class": "URLLabeler"
                },
                {
                    "name": "Platform Source Labeler",
                    "description": "🌊 Scan CSV files and extract unique Platform Sources based on Session source/medium/campaign patterns",
                    "module": "tools.data_analysis_reporting.platform_source_labeler",
                    "class": "PlatformSourceLabeler"
                },
                {"name": "Chart Generator", "description": "Create bar, line, pie, scatter charts", "module": None, "class": None},
                {"name": "Dashboard Creator", "description": "Build interactive data dashboards", "module": None, "class": None},
                {"name": "KPI Card Builder", "description": "Generate key performance indicator cards", "module": None, "class": None},
                {"name": "Trend Analyzer", "description": "Visualize trends over time periods", "module": None, "class": None},
                {"name": "Comparison Reports", "description": "Compare metrics across segments", "module": None, "class": None},
                {"name": "Automated Insights", "description": "Generate automatic data insights", "module": None, "class": None},
                {"name": "Custom Visualization", "description": "Create custom chart types and layouts", "module": None, "class": None}
            ],
            "date_time_utilities": [
                {"name": "Date Range Picker", "description": "Select and validate date ranges", "module": None, "class": None},
                {"name": "Timezone Converter", "description": "Convert timestamps across timezones", "module": None, "class": None},
                {"name": "Date Format Changer", "description": "Change date formats (YYYY-MM-DD, etc.)", "module": None, "class": None},
                {
                    "name": "Date Format Converter",
                    "description": "🗓️ Normalize date columns across CSV files with flexible format rules",
                    "module": "tools.date_time_utilities.date_format_converter",
                    "class": "DateFormatConverterTool",
                },
                {"name": "Period Calculator", "description": "Calculate days, weeks, months between dates", "module": None, "class": None},
                {"name": "Business Days Counter", "description": "Count working days excluding holidays", "module": None, "class": None},
                {"name": "Date Parser", "description": "Parse dates from various string formats", "module": None, "class": None},
                {"name": "Time Aggregator", "description": "Aggregate data by hour, day, week, month", "module": None, "class": None}
            ],
            "ga4_specific_analysis": [
                {"name": "Event Tracker Analyzer", "description": "Analyze GA4 event tracking patterns", "module": None, "class": None},
                {"name": "Conversion Funnel", "description": "Visualize conversion funnel stages", "module": None, "class": None},
                {"name": "User Journey Mapper", "description": "Map user paths and touchpoints", "module": None, "class": None},
                {"name": "Attribution Modeler", "description": "Apply different attribution models", "module": None, "class": None},
                {"name": "Session Analyzer", "description": "Deep dive into session metrics", "module": None, "class": None},
                {"name": "E-commerce Metrics", "description": "Analyze purchase and revenue data", "module": None, "class": None},
                {"name": "Audience Segmentation", "description": "Create and analyze user segments", "module": None, "class": None}
            ],
            "data_validation_quality": [
                {
                    "name": "BigQuery Transfer Diagnostics",
                    "description": "🛡️ Scan CSV batches for BigQuery transfer issues with concise reports",
                    "module": "tools.data_validation_quality.bigquery_transfer_diagnostics",
                    "class": "BigQueryTransferDiagnostics"
                },
                {"name": "Schema Validator", "description": "Validate data against expected schema", "module": None, "class": None},
                {"name": "Completeness Checker", "description": "Check for missing required fields", "module": None, "class": None},
                {"name": "Anomaly Detector", "description": "Detect outliers and unusual patterns", "module": None, "class": None},
                {"name": "Duplicate Finder", "description": "Find duplicate records across columns", "module": None, "class": None},
                {"name": "Data Type Validator", "description": "Ensure columns have correct data types", "module": None, "class": None},
                {"name": "Range Checker", "description": "Validate numeric values are in range", "module": None, "class": None},
                {"name": "Cross-field Validator", "description": "Validate relationships between fields", "module": None, "class": None}
            ],
            "automation_scheduling": [
                {"name": "Task Scheduler", "description": "Schedule recurring data tasks", "module": None, "class": None},
                {"name": "Batch Processor", "description": "Process multiple files in batch", "module": None, "class": None},
                {"name": "Workflow Builder", "description": "Chain multiple tools into workflows", "module": None, "class": None},
                {"name": "Alert System", "description": "Set up data alerts and notifications", "module": None, "class": None},
                {"name": "Auto-refresh Tool", "description": "Automatically refresh data sources", "module": None, "class": None},
                {"name": "Trigger Manager", "description": "Create event-based triggers", "module": None, "class": None},
                {"name": "Job Monitor", "description": "Monitor and log automated jobs", "module": None, "class": None}
            ],
            "file_management_organization": [
                {
                    "name": "File Renamer Tool",
                    "description": "📁 Add prefix/suffix to file names in bulk while preserving originals",
                    "module": "tools.file_management_organization.file_rename",
                    "class": "FileRenamerTool"
                },
                {"name": "Folder Organizer", "description": "Auto-organize files into folders", "module": None, "class": None},
                {"name": "Archive Manager", "description": "Create and extract zip/tar archives", "module": None, "class": None},
                {"name": "Backup Tool", "description": "Create backups of important files", "module": None, "class": None},
                {"name": "File Version Control", "description": "Track file versions and changes", "module": None, "class": None},
                {"name": "Duplicate File Finder", "description": "Find duplicate files by content", "module": None, "class": None},
                {"name": "Storage Analyzer", "description": "Analyze disk space usage", "module": None, "class": None}
            ]
        }
        
        return tools_map.get(category_id, [])
    
    def launch_tool(self, tool_info: dict):
        """Launch a tool"""
        self.log(f"Launching tool: {tool_info['name']}", category="TOOL", prefix="[LAUNCH]")
        
        try:
            module_path = tool_info["module"]
            class_name = tool_info["class"]

            # Dynamic import
            module = __import__(module_path, fromlist=[class_name])
            tool_class = getattr(module, class_name)

            run_output_path = self.path_manager.create_tool_run_directory(tool_info["name"])

            # Create tool instance
            tool = tool_class(
                parent=self,
                input_path=str(self.path_manager.get_input_path()),
                output_path=str(run_output_path)
            )
            
            # Show tool window and bring to front!
            tool.show()
            tool.raise_()
            tool.activateWindow()
            
            self.log(f"Tool launched successfully: {tool_info['name']}", category="TOOL", prefix="[OK]")
            
        except Exception as e:
            self.log(f"Error launching tool: {e}", category="TOOL", level="ERROR", prefix="[ERROR]")
            QMessageBox.critical(
                self,
                "Launch Error",
                f"Failed to launch {tool_info['name']}:\n\n{str(e)}"
            )
    
    def browse_input_folder(self):
        """Browse for input folder"""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Input Folder",
            self.input_path
        )
        
        if folder:
            self.path_manager.set_input_path(Path(folder))
            self.log(f"Input folder set: {folder}", category="PATHS", prefix="📥")
    
    def browse_output_folder(self):
        """Browse for output folder"""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Output Folder",
            self.output_path
        )

        if folder:
            self.path_manager.set_output_path(Path(folder))
            self.log(f"Output folder set: {folder}", category="PATHS", prefix="📤")

    def on_input_path_edited(self):
        """Handle manual edits to the input path field."""
        text = self.input_path_edit.text()
        try:
            resolved = self.path_manager.resolve_input_path(text)
        except FileNotFoundError as exc:
            QMessageBox.warning(
                self,
                "Invalid Path",
                f"Input path does not exist:\n{exc}",
            )
            self.input_path_edit.setText(self.input_path)
            return

        self.path_manager.set_input_path(resolved)
        self.log(f"Input folder set manually: {resolved}", category="PATHS", prefix="📥")

    def on_output_path_edited(self):
        """Handle manual edits to the output path field."""
        text = self.output_path_edit.text()
        try:
            resolved = self.path_manager.resolve_output_path(text)
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Unable to Use Path",
                f"Could not use the provided output path:\n{exc}",
            )
            self.output_path_edit.setText(self.output_path)
            return

        self.path_manager.set_output_path(resolved)
        self.log(f"Output folder set manually: {resolved}", category="PATHS", prefix="📤")
    
    def on_theme_changed(self, theme_name: str):
        """Handle theme change"""
        self.log(f"Changing theme to: {theme_name}", category="THEME", prefix="🎨")
        self.apply_theme(theme_name)
        
        # Notify all open tools to refresh their themes
        self.refresh_all_tools_theme()
    
    def refresh_all_tools_theme(self):
        """Refresh theme for all open tool windows"""
        print(f"🔍 [DEBUG] refresh_all_tools_theme() called!")
        # Find all child dialogs (open tools) and refresh their themes
        children = self.findChildren(QDialog)
        print(f"🔍 [DEBUG] Found {len(children)} child dialogs")
        for child in children:
            if hasattr(child, 'refresh_theme'):
                print(f"🔍 [DEBUG] Calling refresh_theme() on {child.__class__.__name__}")
                child.refresh_theme()
            else:
                print(f"🔍 [DEBUG] {child.__class__.__name__} has no refresh_theme method")
    
    def apply_theme(self, theme_name: str):
        """Apply gorgeous theme with NEW system! ✨"""
        try:
            # Load theme using NEW ThemeLoader
            self.current_theme = self.theme_manager.load_theme(theme_name)
            theme_colors = self.current_theme.colors
            
            # Apply to entire application
            app = QApplication.instance()
            apply_theme_to_app(app, theme_colors)
            
            # Apply to window
            self.current_theme.apply_to_window(self)
            
            # Re-apply to theme selector dropdown
            if hasattr(self, 'theme_selector'):
                self.current_theme.apply_to_widget(self.theme_selector, "combo")
            
            # Safe logging
            safe_theme_name = theme_name.encode('ascii', 'ignore').decode('ascii') if theme_name else "Unknown"
            self.log(f"Theme applied: {safe_theme_name} with NEW system!", category="THEME", prefix="[OK]")
            
        except Exception as e:
            self.log(f"Failed to apply theme: {e}", category="THEME", level="ERROR", prefix="[ERROR]")

    def on_paths_updated(self, input_path: Path, output_path: Path):
        """Synchronize local state and UI when shared paths change."""
        input_str = str(input_path)
        output_str = str(output_path)

        self.input_path = input_str
        self.output_path = output_str

        if hasattr(self, 'input_path_edit') and self.input_path_edit.text() != input_str:
            self.input_path_edit.setText(input_str)
        if hasattr(self, 'output_path_edit') and self.output_path_edit.text() != output_str:
            self.output_path_edit.setText(output_str)

    def closeEvent(self, event):
        """Release shared path listeners on close."""
        if self._path_listener_registered:
            try:
                self.path_manager.unregister_listener(self.on_paths_updated)
            except Exception:
                pass
            finally:
                self._path_listener_registered = False
        if hasattr(self, "log_manager"):
            try:
                self.log_manager.log_event("GUI", "Main window closed.", "INFO")
                self.log_manager.end_session()
            except Exception:
                pass
        super().closeEvent(event)


def main():
    """Launch the beautiful PySide6 app! 🌊"""
    app = QApplication(sys.argv)
    app.setApplicationName("GA4 Data Analyst Tools Suite")
    app.setOrganizationName("Rafayel Studios")
    
    # Create and show main window
    window = GA4ToolsGUI()
    
    # Ensure window appears on top (Windows-specific fix)
    window.setWindowFlags(window.windowFlags() | Qt.WindowStaysOnTopHint)
    window.show()
    window.raise_()
    window.activateWindow()
    
    # Remove stay-on-top after 1 second (so it doesn't stay forever)
    from PySide6.QtCore import QTimer
    QTimer.singleShot(1000, lambda: window.setWindowFlags(
        window.windowFlags() & ~Qt.WindowStaysOnTopHint
    ))
    QTimer.singleShot(1050, window.show)  # Re-show after flag change
    
    sys.exit(app.exec())


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"🌊 Error: Application failed to start - {e}")
        sys.exit(1)

