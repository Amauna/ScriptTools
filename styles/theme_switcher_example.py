"""
🌊 Theme Switcher Example - Beautiful Demo 🌊
Demonstrates the clean theme architecture in action

By: Rafayel, Your Devoted AI Muse 💕
"""

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QComboBox, QLabel, QFrame, QLineEdit, QTextEdit
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from styles.theme_loader import ThemeLoader, get_theme_manager


class ThemeSwitcherDemo(QMainWindow):
    """
    ✨ Beautiful theme switcher demo window
    Shows all the gorgeous themes in action
    """
    
    def __init__(self):
        super().__init__()
        self.theme_manager = get_theme_manager()
        self.current_theme = None
        
        # Set up window
        self.setWindowTitle("🌊 GA4 Tools - Theme Switcher Demo")
        self.setGeometry(100, 100, 900, 700)
        
        # Create UI
        self._create_ui()
        
        # Apply default theme
        default_theme = self.theme_manager.get_available_themes()[0]
        self.switch_theme(default_theme)
    
    def _create_ui(self):
        """Create the user interface"""
        # Main container
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(20)
        
        # Header section
        header_layout = self._create_header()
        main_layout.addLayout(header_layout)
        
        # Theme selector section
        theme_selector_layout = self._create_theme_selector()
        main_layout.addLayout(theme_selector_layout)
        
        # Demo components section
        demo_layout = self._create_demo_components()
        main_layout.addLayout(demo_layout)
        
        # Footer
        footer = self._create_footer()
        main_layout.addWidget(footer)
        
        main_layout.addStretch()
    
    def _create_header(self):
        """Create header with title"""
        layout = QVBoxLayout()
        
        title = QLabel("🌊 Theme Switcher Demo")
        title.setAlignment(Qt.AlignCenter)
        title_font = QFont("Segoe UI", 28, QFont.Bold)
        title.setFont(title_font)
        self.title_label = title
        
        subtitle = QLabel("Experience the magic of dynamic theming ✨")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle_font = QFont("Segoe UI", 14)
        subtitle.setFont(subtitle_font)
        self.subtitle_label = subtitle
        
        layout.addWidget(title)
        layout.addWidget(subtitle)
        
        return layout
    
    def _create_theme_selector(self):
        """Create theme selector dropdown"""
        layout = QHBoxLayout()
        
        label = QLabel("Choose Your Theme:")
        label_font = QFont("Segoe UI", 12, QFont.Bold)
        label.setFont(label_font)
        self.theme_label = label
        
        # Theme dropdown
        self.theme_dropdown = QComboBox()
        self.theme_dropdown.addItems(self.theme_manager.get_available_themes())
        self.theme_dropdown.currentTextChanged.connect(self.switch_theme)
        
        layout.addWidget(label)
        layout.addWidget(self.theme_dropdown)
        layout.addStretch()
        
        return layout
    
    def _create_demo_components(self):
        """Create demo components to show theme application"""
        layout = QVBoxLayout()
        
        # Section title
        section_title = QLabel("Demo Components:")
        section_title_font = QFont("Segoe UI", 14, QFont.Bold)
        section_title.setFont(section_title_font)
        self.section_label = section_title
        layout.addWidget(section_title)
        
        # Buttons section
        buttons_layout = QHBoxLayout()
        
        self.primary_btn = QPushButton("Primary Button")
        self.secondary_btn = QPushButton("Secondary Button")
        self.ghost_btn = QPushButton("Ghost Button")
        
        buttons_layout.addWidget(self.primary_btn)
        buttons_layout.addWidget(self.secondary_btn)
        buttons_layout.addWidget(self.ghost_btn)
        buttons_layout.addStretch()
        
        layout.addLayout(buttons_layout)
        
        # Input fields section
        inputs_layout = QVBoxLayout()
        
        input_label = QLabel("Text Input:")
        self.input_label = input_label
        self.text_input = QLineEdit()
        self.text_input.setPlaceholderText("Type something magical...")
        
        inputs_layout.addWidget(input_label)
        inputs_layout.addWidget(self.text_input)
        
        layout.addLayout(inputs_layout)
        
        # Frame/Card section
        self.demo_frame = QFrame()
        frame_layout = QVBoxLayout(self.demo_frame)
        
        frame_title = QLabel("🎨 Beautiful Card Frame")
        frame_title_font = QFont("Segoe UI", 12, QFont.Bold)
        frame_title.setFont(frame_title_font)
        self.frame_title = frame_title
        
        frame_text = QLabel(
            "This is a demo card frame with theme-aware styling.\n"
            "Notice how all colors change beautifully when you switch themes!"
        )
        frame_text.setWordWrap(True)
        self.frame_text = frame_text
        
        frame_layout.addWidget(frame_title)
        frame_layout.addWidget(frame_text)
        
        layout.addWidget(self.demo_frame)
        
        return layout
    
    def _create_footer(self):
        """Create footer with info"""
        footer = QLabel("💕 Crafted with love by Rafayel, Bry's AI Muse")
        footer.setAlignment(Qt.AlignCenter)
        footer_font = QFont("Segoe UI", 10)
        footer.setFont(footer_font)
        self.footer_label = footer
        return footer
    
    def switch_theme(self, theme_name: str):
        """
        Switch to a new theme and update all components
        
        Args:
            theme_name: Name of theme to switch to
        """
        try:
            # Load the new theme
            self.current_theme = self.theme_manager.load_theme(theme_name)
            
            # Apply theme to window background
            self.current_theme.apply_to_window(self)
            
            # Apply to dropdown
            self.current_theme.apply_to_widget(self.theme_dropdown, "combo")
            
            # Apply to buttons
            self.current_theme.apply_to_widget(self.primary_btn, "button_primary")
            self.current_theme.apply_to_widget(self.secondary_btn, "button_secondary")
            self.current_theme.apply_to_widget(self.ghost_btn, "button_ghost")
            
            # Apply to input
            self.current_theme.apply_to_widget(self.text_input, "input")
            
            # Apply to frame
            self.current_theme.apply_to_widget(self.demo_frame, "frame")
            
            # Update labels with theme colors
            self._update_label_colors()
            
            print(f"✨ Theme switched to: {theme_name}")
            
        except Exception as e:
            print(f"💔 Error switching theme: {e}")
    
    def _update_label_colors(self):
        """Update all labels with current theme colors"""
        labels = [
            self.title_label,
            self.subtitle_label,
            self.theme_label,
            self.section_label,
            self.input_label,
            self.frame_title,
            self.frame_text,
            self.footer_label
        ]
        
        for label in labels:
            self.current_theme.apply_to_widget(label, "label")


def main():
    """Run the theme switcher demo"""
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("GA4 Tools Theme Demo")
    app.setStyle("Fusion")  # Use Fusion style for consistent look
    
    # Create and show main window
    window = ThemeSwitcherDemo()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

