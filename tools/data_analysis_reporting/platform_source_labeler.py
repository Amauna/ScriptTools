"""
🌊 Platform Source Labeler Tool
Scans CSV files and extracts unique Platform Sources based on Session source/medium/campaign patterns
Based on SQL pattern matching logic from GA4 analysis queries
"""

from __future__ import annotations

import sys
import re
import csv
from pathlib import Path
from typing import List, Set, Optional, Tuple

from PySide6.QtWidgets import (
    QApplication,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QFrame,
    QProgressBar,
)
from PySide6.QtCore import Qt, Signal, QObject, QThread
from PySide6.QtGui import QFont

from tools.templates import BaseToolDialog, PathConfigMixin

# Import theme system
try:
    from styles.components import ExecutionLogFooter, create_execution_log_footer
    THEME_AVAILABLE = True
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    try:
        from styles.components import ExecutionLogFooter, create_execution_log_footer
        THEME_AVAILABLE = True
    except ImportError:
        THEME_AVAILABLE = False
        ExecutionLogFooter = None
        create_execution_log_footer = None


# Platform Source Pattern Rules (derived from SQL CASE/WHEN logic)
# Order matters - first match wins (same as SQL CASE/WHEN)
PLATFORM_SOURCE_PATTERNS = [
    ("Bing", [r"bing"]),
    ("Direct", [
        r"\(direct\)",
        r"\(not set\)",
        r"direct_visitor",
        r"^direct$",
    ]),
    ("Aloha Find", [r"alohafind\.com"]),
    ("Alohafind", [r"^alohafind$"]),
    ("Ask", [r"ask\.com", r"^ask$"]),
    ("AOL", [r"^aol$"]),
    ("afterdarkmode", [r"afterdarkmode"]),
    ("Baidu", [r"baidu"]),
    ("Dnserrorassist", [r"dnserrorassist"]),
    ("Dogpile", [r"dogpile"]),
    ("Duckduckgo", [r"duckduckgo"]),
    ("Daum", [r"daum"]),
    ("Hotbot", [r"hotbot"]),
    ("Ecosia", [r"ecosia"]),
    ("Facebook", [
        r"facebook",
        r"^fb$",  # Abbreviation: fb, FB
        r"\bfb\b",  # Word boundary: fb in text
    ]),
    ("Google", [r"google"]),  # Exclusion handled in _classify_platform_source
    ("Gibiru", [r"gibiru"]),
    ("Instagram", [
        r"instagram",
        r"^ig$",  # Abbreviation: ig, IG
        r"\big\b",  # Word boundary: ig in text
    ]),
    ("Info.com", [r"info\.com"]),
    ("LinkedIn", [
        r"linkedin",
        r"^li$",  # Abbreviation: li, LI
        r"\bli\b",  # Word boundary: li in text
    ]),
    ("Livechat", [r"livechat"]),
    ("Medium", [r"medium"]),
    ("MetaGer", [r"metager"]),
    ("Metacrawler", [r"metacrawler"]),
    ("Onesearch", [r"onesearch"]),
    ("PCH", [r"pch\.com"]),
    ("Presearch", [r"presearch"]),
    ("Quora", [
        r"ans_",
        r"ans_quo",
        r"ans_qu",
        r"quora",
    ]),
    ("Substack", [r"c_substack"]),
    ("Reputation Management", [
        r"trustpilot",
        r"sitejabber",
        r"reviews\.io",
        r"revdex",
        r"scamadviser",
    ]),
    ("So.com", [r"so\.com"]),
    ("Seznam", [r"seznam"]),
    ("Sogou", [r"sogou"]),
    ("Snapchat", [
        r"snapchat",
        r"^sc$",  # Abbreviation: sc, SC
        r"\bsc\b",  # Word boundary: sc in text
    ]),
    ("Tiktok", [
        r"tiktok",
        r"^tt$",  # Abbreviation: tt, TT
        r"\btt\b",  # Word boundary: tt in text
    ]),
    ("Tineye", [r"tineye"]),
    ("Tipz.io", [r"tipz\.io"]),
    ("Twitter", [
        r"twitter",
        r"^t\.co$",
        r"^tw$",  # Abbreviation: tw, TW
        r"\btw\b",  # Word boundary: tw in text
    ]),
    ("Umbat", [r"umbat"]),
    ("Yahoo", [r"yahoo"]),
    ("Yandex", [
        r"yandex",
        r"ya\.ru",
    ]),
    ("Youtube", [
        r"youtube",
        r"YT Video",
        r"YT video",
        r"YouTube Comment",
        r"YT Channel",
        r"tl_y outube",
        r"Video Landing Page",
        r"YouTube",
        r"Youtube Video",
        r"rumble",
        r"^yt$",  # Abbreviation: yt, YT
        r"\byt\b",  # Word boundary: yt in text
    ]),
    ("Payment", [r"secureordering\.com"]),
    ("Brave", [r"brave\.com"]),
    ("Email Marketing", [r"tl-email"]),
    ("Threads", [r"tl_threads"]),
    ("Reddit", [
        r"reddit",
        r"Reddit",
        r"^rd$",  # Abbreviation: rd, RD
        r"\brd\b",  # Word boundary: rd in text
    ]),
    ("Bluesky", [r"tl_bluesky"]),
    ("Vocal Media", [r"vocal\.media"]),
    ("Backlink", []),  # Default fallback (must be last)
]

# Compile regex patterns for performance (case-insensitive to handle upper/lower case variations)
COMPILED_PATTERNS = [
    (platform_name, [re.compile(pattern, re.IGNORECASE) for pattern in patterns])
    for platform_name, patterns in PLATFORM_SOURCE_PATTERNS
]


def _normalize_column_name(name: str) -> str:
    """Normalize column name for matching"""
    return "".join(ch for ch in name.lower() if ch.isalnum())


def _find_session_columns(headers: List[str]) -> Tuple[Optional[int], Optional[int], Optional[int]]:
    """
    Find Session source, medium, and campaign column indices
    
    Returns:
        Tuple of (source_idx, medium_idx, campaign_idx)
    """
    source_idx = None
    medium_idx = None
    campaign_idx = None
    
    for idx, header in enumerate(headers):
        normalized = _normalize_column_name(header)
        
        if normalized in ["sessionsource", "session_source", "source"]:
            source_idx = idx
        elif normalized in ["sessionmedium", "session_medium", "medium"]:
            medium_idx = idx
        elif normalized in ["sessioncampaign", "session_campaign", "campaign"]:
            campaign_idx = idx
    
    return source_idx, medium_idx, campaign_idx


def _classify_platform_source(
    source: str,
    medium: Optional[str] = None,
    campaign: Optional[str] = None,
) -> str:
    """
    Classify a Platform Source based on source/medium/campaign patterns
    (case-insensitive with spacing normalization)
    
    Strategy:
    1. Check combined "source / medium" format first
    2. Check source alone
    3. Check campaign if needed
    4. Default to "Backlink"
    
    Handles spacing and case variations via regex normalization.
    """
    # Clean inputs: normalize spacing (multiple spaces to single space) and strip
    source_clean = re.sub(r'\s+', ' ', (source or "").strip())
    medium_clean = re.sub(r'\s+', ' ', (medium or "").strip()) if medium else ""
    campaign_clean = re.sub(r'\s+', ' ', (campaign or "").strip()) if campaign else ""
    
    if not source_clean:
        return "Backlink"
    
    # Create combined values for matching (normalized spacing)
    combined_source_medium = f"{source_clean} / {medium_clean}".strip() if medium_clean else source_clean
    combined_all = f"{source_clean} / {medium_clean} / {campaign_clean}".strip() if (medium_clean and campaign_clean) else combined_source_medium
    
    # Try each pattern in order (first match wins, like SQL CASE/WHEN)
    for platform_name, patterns in COMPILED_PATTERNS:
        if not patterns:  # Backlink fallback
            continue
        
        for pattern in patterns:
            # Special handling for Google exclusions (check before matching)
            if platform_name == "Google":
                if "docs.google.com" in source_clean.lower() or "mail.google.com" in source_clean.lower():
                    continue  # Skip Google patterns for docs/mail.google.com
            
            # Check combined values first (source/medium format)
            if medium_clean and pattern.search(combined_source_medium):
                return platform_name
            if campaign_clean and pattern.search(combined_all):
                return platform_name
            # Then check source alone
            if pattern.search(source_clean):
                return platform_name
            # Check campaign as fallback
            if campaign_clean and pattern.search(campaign_clean):
                return platform_name
    
    # Default fallback
    return "Backlink"


class PlatformSourceWorker(QObject):
    """Worker thread for scanning CSV files and extracting Platform Sources"""
    log_signal = Signal(str)
    progress_signal = Signal(int, int)  # current, total
    finished_signal = Signal(set)  # unique_platform_sources
    
    def __init__(self, input_folder: Path):
        super().__init__()
        self.input_folder = input_folder
        self.should_stop = False
    
    def run(self) -> None:
        """Scan CSV files and extract unique Platform Sources"""
        try:
            # Find all CSV files
            csv_files = list(self.input_folder.glob("*.csv"))
            csv_files = [f for f in csv_files if not f.name.endswith('.bak')]
            
            if not csv_files:
                self.log_signal.emit("⚠️ No CSV files found in folder!")
                self.finished_signal.emit(set())
                return
            
            self.log_signal.emit(f"📂 Found {len(csv_files)} CSV file(s)")
            self.log_signal.emit("")
            
            unique_platforms: Set[str] = set()
            total_rows = 0
            
            for idx, csv_file in enumerate(csv_files, 1):
                if self.should_stop:
                    break
                
                self.progress_signal.emit(idx, len(csv_files))
                self.log_signal.emit(f"[{idx}/{len(csv_files)}] Scanning: {csv_file.name}")
                
                try:
                    with csv_file.open("r", encoding="utf-8-sig", newline="") as f:
                        reader = csv.reader(f)
                        headers = next(reader, [])
                        
                        source_idx, medium_idx, campaign_idx = _find_session_columns(headers)
                        
                        if source_idx is None:
                            self.log_signal.emit(f"   ⚠️ No Session source column found (looking for Session source, session_source, etc.)")
                            continue
                        
                        file_platforms: Set[str] = set()
                        file_rows = 0
                        
                        for row in reader:
                            if len(row) <= source_idx:
                                continue
                            
                            source = row[source_idx] if source_idx < len(row) else ""
                            medium = row[medium_idx] if medium_idx and medium_idx < len(row) else None
                            campaign = row[campaign_idx] if campaign_idx and campaign_idx < len(row) else None
                            
                            if source and source.strip():
                                platform = _classify_platform_source(source, medium, campaign)
                                unique_platforms.add(platform)
                                file_platforms.add(platform)
                                file_rows += 1
                                total_rows += 1
                        
                        self.log_signal.emit(f"   ✓ Found {len(file_platforms)} unique platform(s) from {file_rows} row(s)")
                
                except Exception as e:
                    self.log_signal.emit(f"   ❌ Error reading {csv_file.name}: {str(e)}")
                    continue
            
            self.log_signal.emit("")
            self.log_signal.emit(f"✅ Scan complete! Found {len(unique_platforms)} unique Platform Source(s) from {total_rows} total row(s)")
            
            # Sort platforms for consistent display
            sorted_platforms = sorted(unique_platforms)
            self.finished_signal.emit(set(sorted_platforms))
        
        except Exception as e:
            self.log_signal.emit(f"❌ Error: {str(e)}")
            self.finished_signal.emit(set())


class PlatformSourceLabeler(PathConfigMixin, BaseToolDialog):
    """Platform Source Labeler Tool - Displays unique Platform Sources from CSV files"""
    
    PATH_CONFIG = {
        "show_input": True,
        "show_output": False,
        "include_open_buttons": True,
        "input_label": "📥 Input Folder:",
    }
    
    def __init__(self, parent, input_path: str, output_path: str) -> None:
        super().__init__(parent, input_path, output_path)
        
        self.platform_sources: List[str] = []
        self.worker_thread: Optional[QThread] = None
        self.worker: Optional[PlatformSourceWorker] = None
        self.is_scanning = False
        
        self.setup_window_properties(
            title="🌊 Platform Source Labeler",
            width=800,
            height=700,
        )
        
        self._build_ui()
        self.apply_theme()
        
        if self.execution_log:
            self.log("🌊 Platform Source Labeler ready. Select input folder and click Scan.")
    
    def _build_ui(self) -> None:
        """Build the user interface"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(12)
        
        # Header
        header = QLabel("🌊 Platform Source Labeler")
        header.setFont(QFont("Arial", 20, QFont.Bold))
        header.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(header)
        
        # Path controls
        self.build_path_controls(
            main_layout,
            show_input=True,
            show_output=False,
            include_open_buttons=True,
        )
        
        # Control buttons
        control_frame = QFrame()
        control_layout = QHBoxLayout(control_frame)
        control_layout.setContentsMargins(8, 8, 8, 8)
        control_layout.setSpacing(10)
        
        self.scan_button = QPushButton("🔍 Scan CSV Files")
        self.scan_button.setMinimumHeight(36)
        self.scan_button.clicked.connect(self.start_scan)
        control_layout.addWidget(self.scan_button)
        
        control_layout.addStretch()
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%v / %m files")
        control_layout.addWidget(self.progress_bar)
        
        main_layout.addWidget(control_frame)
        
        # Platform Sources list
        list_frame = QFrame()
        list_frame.setObjectName("glassFrame")
        list_layout = QVBoxLayout(list_frame)
        list_layout.setContentsMargins(10, 10, 10, 10)
        list_layout.setSpacing(8)
        
        list_label = QLabel("📋 Detected Platform Sources:")
        list_label.setFont(QFont("Arial", 12, QFont.Bold))
        list_layout.addWidget(list_label)
        
        self.platform_list = QListWidget()
        self.platform_list.setAlternatingRowColors(True)
        list_layout.addWidget(self.platform_list)
        
        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        self.copy_button = QPushButton("📋 Copy")
        self.copy_button.setEnabled(False)
        self.copy_button.clicked.connect(self.copy_to_clipboard)
        button_layout.addWidget(self.copy_button)
        
        self.save_button = QPushButton("💾 Save")
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self.save_to_file)
        button_layout.addWidget(self.save_button)
        
        self.reset_button = QPushButton("🔄 Reset")
        self.reset_button.setEnabled(False)
        self.reset_button.clicked.connect(self.reset_list)
        button_layout.addWidget(self.reset_button)
        
        button_layout.addStretch()
        
        list_layout.addLayout(button_layout)
        main_layout.addWidget(list_frame, stretch=1)
        
        # Execution log
        self.execution_log = self.create_execution_log(main_layout)
    
    def start_scan(self) -> None:
        """Start scanning CSV files"""
        if self.is_scanning:
            return
        
        input_path = self.input_path
        if not input_path or not input_path.exists():
            QMessageBox.warning(self, "Input Folder Missing", "Please select a valid input folder.")
            return
        
        # Check for CSV files
        csv_files = list(input_path.glob("*.csv"))
        csv_files = [f for f in csv_files if not f.name.endswith('.bak')]
        
        if not csv_files:
            QMessageBox.information(self, "No CSV Files", "No CSV files found in the selected folder.")
            return
        
        self.is_scanning = True
        self.scan_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(csv_files))
        self.progress_bar.setValue(0)
        
        # Clear previous results
        self.platform_list.clear()
        self.platform_sources = []
        self.copy_button.setEnabled(False)
        self.save_button.setEnabled(False)
        self.reset_button.setEnabled(False)
        
        if self.execution_log:
            self.log(f"🔍 Starting scan of {len(csv_files)} CSV file(s)...")
        
        # Clean up any existing worker thread first
        if self.worker_thread and self.worker_thread.isRunning():
            self.worker.should_stop = True
            self.worker_thread.quit()
            self.worker_thread.wait(2000)
        
        # Create worker thread
        self.worker_thread = QThread()
        self.worker = PlatformSourceWorker(input_path)
        self.worker.moveToThread(self.worker_thread)
        
        # Connect signals
        self.worker_thread.started.connect(self.worker.run)
        self.worker.log_signal.connect(self.log)
        self.worker.progress_signal.connect(self._on_progress_update)
        self.worker.finished_signal.connect(self._on_scan_finished)
        
        # Only quit thread after we've handled the finished signal
        self.worker.finished_signal.connect(lambda: self.worker_thread.quit())
        
        # Clean up worker and thread after they finish (but don't close dialog)
        self.worker_thread.finished.connect(self._cleanup_worker)
        
        self.worker_thread.start()
    
    def _cleanup_worker(self) -> None:
        """Clean up worker thread resources"""
        if self.worker:
            self.worker.deleteLater()
            self.worker = None
        if self.worker_thread:
            self.worker_thread.deleteLater()
            self.worker_thread = None
    
    def _on_progress_update(self, current: int, total: int) -> None:
        """Update progress bar"""
        self.progress_bar.setMaximum(max(total, 1))
        self.progress_bar.setValue(min(current, total))
    
    def _on_scan_finished(self, platforms: Set[str]) -> None:
        """Handle scan completion"""
        self.is_scanning = False
        self.scan_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        self.platform_sources = sorted(platforms)
        
        # Populate list
        self.platform_list.clear()
        for platform in self.platform_sources:
            item = QListWidgetItem(platform)
            self.platform_list.addItem(item)
        
        # Enable buttons
        has_platforms = len(self.platform_sources) > 0
        self.copy_button.setEnabled(has_platforms)
        self.save_button.setEnabled(has_platforms)
        self.reset_button.setEnabled(has_platforms)
        
        if self.execution_log:
            if has_platforms:
                self.log(f"✅ Found {len(self.platform_sources)} unique Platform Source(s)")
            else:
                self.log("⚠️ No Platform Sources found")
    
    def copy_to_clipboard(self) -> None:
        """Copy Platform Sources to clipboard"""
        if not self.platform_sources:
            return
        
        text = "\n".join(self.platform_sources)
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        
        if self.execution_log:
            self.log(f"📋 Copied {len(self.platform_sources)} Platform Source(s) to clipboard")
        
        QMessageBox.information(self, "Copied", f"Copied {len(self.platform_sources)} Platform Source(s) to clipboard!")
    
    def save_to_file(self) -> None:
        """Save Platform Sources to file"""
        if not self.platform_sources:
            return
        
        # Get output directory
        run_info = self.allocate_run_directory(
            "Platform Source Labeler",
            script_name=Path(__file__).name,
        )
        output_dir = Path(run_info["root"])
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save to file
        output_file = output_dir / "platform_sources.txt"
        with output_file.open("w", encoding="utf-8") as f:
            f.write("Platform Sources\n")
            f.write("=" * 60 + "\n\n")
            for platform in self.platform_sources:
                f.write(f"{platform}\n")
        
        if self.execution_log:
            self.log(f"💾 Saved {len(self.platform_sources)} Platform Source(s) to: {output_file}")
        
        QMessageBox.information(
            self,
            "Saved",
            f"Saved {len(self.platform_sources)} Platform Source(s) to:\n{output_file}"
        )
    
    def reset_list(self) -> None:
        """Reset the list"""
        reply = QMessageBox.question(
            self,
            "Reset List",
            "Clear all Platform Sources from the list?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        
        if reply == QMessageBox.Yes:
            self.platform_list.clear()
            self.platform_sources = []
            self.copy_button.setEnabled(False)
            self.save_button.setEnabled(False)
            self.reset_button.setEnabled(False)
            
            if self.execution_log:
                self.log("🔄 List reset")
    
    def closeEvent(self, event) -> None:  # noqa: N802
        """Handle window close"""
        if self.worker and self.worker_thread and self.worker_thread.isRunning():
            self.worker.should_stop = True
            self.worker_thread.quit()
            self.worker_thread.wait(2000)
        super().closeEvent(event)


# Alias for compatibility
PlatformSourceLabelerTool = PlatformSourceLabeler


def main() -> None:
    """Standalone test"""
    import sys
    
    app = QApplication(sys.argv)
    
    class DummyParent:
        def __init__(self):
            from styles import get_theme_manager
            try:
                theme_manager = get_theme_manager()
                themes = theme_manager.get_available_themes()
                self.current_theme = (
                    theme_manager.load_theme(themes[0]) if themes else None
                )
            except Exception:
                self.current_theme = None
    
    parent = DummyParent()
    from styles import get_path_manager
    path_manager = get_path_manager()
    
    tool = PlatformSourceLabeler(
        parent,
        input_path=str(path_manager.get_input_path()),
        output_path=str(path_manager.get_output_path()),
    )
    tool.show()
    tool.raise_()
    tool.activateWindow()
    sys.exit(app.exec())


if __name__ == "__main__":  # pragma: no cover
    main()

