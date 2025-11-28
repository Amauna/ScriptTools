"""
🌊 URL Labeler Tool
Scans CSV files and extracts unique Topic Clusters based on URL patterns
Based on SQL pattern matching logic from GA4 analysis queries
"""

from __future__ import annotations

import sys
import re
import csv
from pathlib import Path
from typing import List, Set, Optional

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


# Topic Cluster Pattern Rules (derived from SQL CASE/WHEN logic)
TOPIC_CLUSTER_PATTERNS = [
    # Order matters - first match wins (same as SQL CASE/WHEN)
    ("Home Page", [
        r"\.com/$",
        r"\.net/$",
        r"\.com$",
        r"\.com/index\.",
    ]),
    ("Account Change Password", [
        r"/members/member_password",
        r"/members/new_password/",
    ]),
    ("Advanced Search", [
        r"search-foreign-women-seeking-men",
        r"/search2b\.", r"/search\.", r"/idsearch",
        r"seeking-men", r"-seeking-men",
    ]),
    ("Balance History Page", [r"/members/member_balance"]),
    ("Best Matchmakers", [r"/best-"]),
    ("Blocked Women Page", [r"/members/blocked_women"]),
    ("Confirm Account Page", [r"/members/confirm"]),
    ("Blog Landing Page", [r"/blog/"]),
    ("Culture Blog", [r"/culture/"]),
    ("Dating Blog", [r"/dating/"]),
    ("Executive Page", [r"/execu/"]),
    ("FAQ Pages", [r"/faq", r"/faqs", r"/frequently-asked-questions"]),
    ("Extra Photo", [r"/members/women_extraphoto"]),
    ("Extra Videos", [r"/members/women_extravideo"]),
    ("Featured Ladies", [r"/featured-ladies/"]),
    ("Fiancee Visa", [r"/fiancee-visa/"]),
    ("Forgot Password Page", [r"/members/forgot_password"]),
    ("Fund Viewing", [r"/members/member_addfunds", r"/gifts/", r"/gifts$"]),
    ("Fund Added", [r"/fund-added", r"/funds/added", r"/members/fund_added"]),
    ("Hotlist Page", [r"/members/women_hotlist"]),
    ("Inbox", [r"/members/mailbox"]),
    ("Ladies Membership Form", [r"/registration/onlineform"]),
    ("Ladies Profile Page", [r"/mp/", r"/asian-girls/"]),
    ("Live Show", [r"/ronna-lou-live", r"liveshow", r"/live/", r"/live$"]),
    ("LM Information", [r"/information/"]),
    ("Login Page", [r"/members/login", r"/members/home", r"/members/member_details"]),
    ("Members Profile", [r"/members/profile", r"/members/info", r"/members/remote"]),
    ("My Profile Page", [r"/members/member_profile"]),
    ("Newest Ladies Profile", [r"/new-", r"/newest-"]),
    ("Order form Page", [r"/order-form/"]),
    ("Our-process", [r"/our-process/", r"/our_process/"]),
    ("Personal Backgound Form", [r"/members/crim"]),
    ("Phone_translation", [r"/phone_translation/"]),
    ("Privacy Policy Page", [r"/members/privacy"]),
    ("Psychology Blog", [r"/psychology/"]),
    ("QTA Pages", [r"/questions-to-ask", r"/question-to-ask"]),
    ("Realities Blog", [r"/realities/"]),
    ("Registration Page", [r"/members/signup", r"/quick_register", r"/sign-up\.", r"/members/quick_signup"]),
    ("Search Worldwide", [r"/search-single-foreign-women-worldwide"]),
    ("Send Message", [r"/members/send"]),
    ("Single Club Tour Page", [r"_club"]),
    ("Success Stories", [r"/success_stories/", r"/success-stories/", r"/client-success-stories"]),
    ("T&C Page", [r"/members/terms"]),
    ("Tour Landing Page", [r"women-tour", r"/tours/", r"/tour/$"]),
    ("Tour", [r"/tour/[^/]"]),
    ("Tour Order", [r"/tour/order/"]),
    ("Tour Photos", [r"tour-photo", r"tour_photo", r"/best_tour_photos/"]),
    ("Tour Schedule", [r"tour-schedule"]),
    ("Tour Videos", [r"-videos", r"video-", r"/videos/"]),
    ("Travel Blog", [r"/travel/"]),
    ("Unsubscription Page", [r"/members/unsubscribe"]),
    ("Upgrade Account", [r"/members/member_platinum"]),
    ("User Photo Album", [r"/members/member_photos"]),
    ("Welcome Page", [r"/welcome/"]),
    ("Womens Page", [r"/women/"]),
    ("Women's Page", [r"/womens/", r"/women's/"]),
    ("About Us", [r"/about-", r"/all-about-", r"/more-about-"]),
    ("Service Page", []),  # Default fallback (must be last)
]

# Compile regex patterns for performance (case-insensitive to handle upper/lower case variations)
COMPILED_PATTERNS = [
    (cluster_name, [re.compile(pattern, re.IGNORECASE) for pattern in patterns])
    for cluster_name, patterns in TOPIC_CLUSTER_PATTERNS
]


def _normalize_column_name(name: str) -> str:
    """Normalize column name for matching"""
    return "".join(ch for ch in name.lower() if ch.isalnum())


def _find_url_column(headers: List[str]) -> Optional[int]:
    """Find the URL column index (FullURL, fullurl, Full URL, etc.)"""
    for idx, header in enumerate(headers):
        normalized = _normalize_column_name(header)
        if normalized in ["fullurl", "url", "pageurl"]:
            return idx
    return None


def _classify_url(url: str) -> str:
    """Classify a URL into a Topic Cluster based on patterns (case-insensitive with spacing normalization)"""
    if not url or not isinstance(url, str):
        return "Service Page"
    
    # Normalize spacing and case: strip, normalize multiple spaces to single space
    url_clean = re.sub(r'\s+', ' ', url.strip())
    if not url_clean:
        return "Service Page"
    
    # Try each pattern in order (first match wins, like SQL CASE/WHEN)
    # Patterns are case-insensitive (re.IGNORECASE) and handle spacing variations
    for cluster_name, patterns in COMPILED_PATTERNS:
        if not patterns:  # Service Page fallback
            continue
        for pattern in patterns:
            if pattern.search(url_clean):
                return cluster_name
    
    # Default fallback (handles spacing and case variations via regex normalization)
    return "Service Page"


class TopicClusterWorker(QObject):
    """Worker thread for scanning CSV files and extracting Topic Clusters"""
    log_signal = Signal(str)
    progress_signal = Signal(int, int)  # current, total
    finished_signal = Signal(set)  # unique_topic_clusters
    
    def __init__(self, input_folder: Path):
        super().__init__()
        self.input_folder = input_folder
        self.should_stop = False
    
    def run(self) -> None:
        """Scan CSV files and extract unique Topic Clusters"""
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
            
            unique_clusters: Set[str] = set()
            total_urls = 0
            
            for idx, csv_file in enumerate(csv_files, 1):
                if self.should_stop:
                    break
                
                self.progress_signal.emit(idx, len(csv_files))
                self.log_signal.emit(f"[{idx}/{len(csv_files)}] Scanning: {csv_file.name}")
                
                try:
                    with csv_file.open("r", encoding="utf-8-sig", newline="") as f:
                        reader = csv.reader(f)
                        headers = next(reader, [])
                        
                        url_col_idx = _find_url_column(headers)
                        if url_col_idx is None:
                            self.log_signal.emit(f"   ⚠️ No URL column found (looking for FullURL, fullurl, etc.)")
                            continue
                        
                        file_clusters: Set[str] = set()
                        file_urls = 0
                        
                        for row in reader:
                            if len(row) > url_col_idx:
                                url = row[url_col_idx]
                                if url and url.strip():
                                    cluster = _classify_url(url)
                                    unique_clusters.add(cluster)
                                    file_clusters.add(cluster)
                                    file_urls += 1
                                    total_urls += 1
                        
                        self.log_signal.emit(f"   ✓ Found {len(file_clusters)} unique cluster(s) from {file_urls} URL(s)")
                
                except Exception as e:
                    self.log_signal.emit(f"   ❌ Error reading {csv_file.name}: {str(e)}")
                    continue
            
            self.log_signal.emit("")
            self.log_signal.emit(f"✅ Scan complete! Found {len(unique_clusters)} unique Topic Cluster(s) from {total_urls} total URL(s)")
            
            # Sort clusters for consistent display
            sorted_clusters = sorted(unique_clusters)
            self.finished_signal.emit(set(sorted_clusters))
        
        except Exception as e:
            self.log_signal.emit(f"❌ Error: {str(e)}")
            self.finished_signal.emit(set())


class URLLabeler(PathConfigMixin, BaseToolDialog):
    """URL Labeler Tool - Displays unique Topic Clusters from CSV files"""
    
    PATH_CONFIG = {
        "show_input": True,
        "show_output": False,
        "include_open_buttons": True,
        "input_label": "📥 Input Folder:",
    }
    
    def __init__(self, parent, input_path: str, output_path: str) -> None:
        super().__init__(parent, input_path, output_path)
        
        self.topic_clusters: List[str] = []
        self.worker_thread: Optional[QThread] = None
        self.worker: Optional[TopicClusterWorker] = None
        self.is_scanning = False
        
        self.setup_window_properties(
            title="🌊 URL Labeler",
            width=800,
            height=700,
        )
        
        self._build_ui()
        self.apply_theme()
        
        if self.execution_log:
            self.log("🌊 URL Labeler ready. Select input folder and click Scan.")
    
    def _build_ui(self) -> None:
        """Build the user interface"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(12)
        
        # Header
        header = QLabel("🌊 URL Labeler")
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
        
        # Topic Clusters list
        list_frame = QFrame()
        list_frame.setObjectName("glassFrame")
        list_layout = QVBoxLayout(list_frame)
        list_layout.setContentsMargins(10, 10, 10, 10)
        list_layout.setSpacing(8)
        
        list_label = QLabel("📋 Detected Topic Clusters:")
        list_label.setFont(QFont("Arial", 12, QFont.Bold))
        list_layout.addWidget(list_label)
        
        self.cluster_list = QListWidget()
        self.cluster_list.setAlternatingRowColors(True)
        list_layout.addWidget(self.cluster_list)
        
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
        self.cluster_list.clear()
        self.topic_clusters = []
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
        self.worker = TopicClusterWorker(input_path)
        self.worker.moveToThread(self.worker_thread)
        
        # Connect signals - IMPORTANT: Don't connect finished to quit directly
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
    
    def _on_scan_finished(self, clusters: Set[str]) -> None:
        """Handle scan completion"""
        self.is_scanning = False
        self.scan_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        self.topic_clusters = sorted(clusters)
        
        # Populate list
        self.cluster_list.clear()
        for cluster in self.topic_clusters:
            item = QListWidgetItem(cluster)
            self.cluster_list.addItem(item)
        
        # Enable buttons
        has_clusters = len(self.topic_clusters) > 0
        self.copy_button.setEnabled(has_clusters)
        self.save_button.setEnabled(has_clusters)
        self.reset_button.setEnabled(has_clusters)
        
        if self.execution_log:
            if has_clusters:
                self.log(f"✅ Found {len(self.topic_clusters)} unique Topic Cluster(s)")
            else:
                self.log("⚠️ No Topic Clusters found")
    
    def copy_to_clipboard(self) -> None:
        """Copy Topic Clusters to clipboard"""
        if not self.topic_clusters:
            return
        
        text = "\n".join(self.topic_clusters)
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        
        if self.execution_log:
            self.log(f"📋 Copied {len(self.topic_clusters)} Topic Cluster(s) to clipboard")
        
        QMessageBox.information(self, "Copied", f"Copied {len(self.topic_clusters)} Topic Cluster(s) to clipboard!")
    
    def save_to_file(self) -> None:
        """Save Topic Clusters to file"""
        if not self.topic_clusters:
            return
        
        # Get output directory
        run_info = self.allocate_run_directory(
            "URL Labeler",
            script_name=Path(__file__).name,
        )
        output_dir = Path(run_info["root"])
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save to file
        output_file = output_dir / "topic_clusters.txt"
        with output_file.open("w", encoding="utf-8") as f:
            f.write("Topic Clusters\n")
            f.write("=" * 60 + "\n\n")
            for cluster in self.topic_clusters:
                f.write(f"{cluster}\n")
        
        if self.execution_log:
            self.log(f"💾 Saved {len(self.topic_clusters)} Topic Cluster(s) to: {output_file}")
        
        QMessageBox.information(
            self,
            "Saved",
            f"Saved {len(self.topic_clusters)} Topic Cluster(s) to:\n{output_file}"
        )
    
    def reset_list(self) -> None:
        """Reset the list"""
        reply = QMessageBox.question(
            self,
            "Reset List",
            "Clear all Topic Clusters from the list?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        
        if reply == QMessageBox.Yes:
            self.cluster_list.clear()
            self.topic_clusters = []
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
URLLabelerTool = URLLabeler


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
    
    tool = URLLabeler(
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

