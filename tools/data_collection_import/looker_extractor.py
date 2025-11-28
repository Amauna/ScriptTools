#!/usr/bin/env python3
"""
🌊 Looker Studio Data Extractor - PySide6 Edition 🌊
Extract multiple tables from Looker Studio with beautiful glass morphism UI
Uses proper QThread for Qt compatibility!
"""

import sys
import os
import time
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QFrame, QWidget, QLineEdit, QComboBox, QCheckBox, QFileDialog,
    QTextEdit, QMessageBox, QProgressBar, QDateEdit, QScrollArea
)
from PySide6.QtCore import Qt, QThread, Signal, QObject, QDate
from PySide6.QtGui import QFont, QIcon, QTextCursor

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
except ImportError:
    sync_playwright = None
    PlaywrightTimeoutError = Exception

# Import NEW theme system (with fallback for standalone execution)
try:
    from styles import ThemeLoader, get_theme_manager, hex_to_rgba, get_path_manager, get_log_manager
    from styles.components import ExecutionLogFooter, create_execution_log_footer
    THEME_AVAILABLE = True
except ImportError:
    # Add parent directory to path for standalone execution
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    try:
        from styles import ThemeLoader, get_theme_manager, hex_to_rgba, get_path_manager, get_log_manager
        from styles.components import ExecutionLogFooter, create_execution_log_footer
        THEME_AVAILABLE = True
    except ImportError:
        # Ultimate fallback
        THEME_AVAILABLE = False
        print("⚠️  Theme not available, using default styling")
        def hex_to_rgba(hex_color, alpha):
            return hex_color
        ExecutionLogFooter = None
        create_execution_log_footer = None
        get_log_manager = lambda: None

from tools.templates import PathConfigMixin


class ScanAndExtractWorker(QObject):
    """QThread worker for BOTH scanning AND extraction - ONE thread!"""
    
    # Signals
    log_signal = Signal(str)
    progress_signal = Signal(int)
    status_signal = Signal(str)
    scan_complete_signal = Signal(list)  # List of found tables
    scan_failed_signal = Signal(str)
    extraction_complete_signal = Signal(int, str)  # tables_extracted, output_dir
    extraction_failed_signal = Signal(str)
    
    def __init__(self, url, browser_type, headless, wait_time, output_path, enable_date_filter=False, start_date=None, end_date=None):
        super().__init__()
        self.url = url
        self.browser_type = browser_type
        self.headless = headless
        self.wait_time = wait_time
        self.output_path = output_path
        self.enable_date_filter = enable_date_filter
        self.start_date = start_date
        self.end_date = end_date
        
        # Browser objects
        self.playwright = None
        self.browser = None
        self.browser_context = None
        self.page = None
        self.found_tables = []
        
        # Control flag for extraction
        self.should_extract = False
        self.is_waiting = False
        
        # Store all log messages for file export
        self.execution_log = []
    
    def log(self, message: str):
        """Log message (emits signal and stores for file export)"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        self.execution_log.append(formatted_message)
        self.log_signal.emit(message)
    
    def run_scan(self):
        """Run scan and emit results - SCANS ALL PAGES!"""
        try:
            self.log_signal.emit("="*60)
            self.log_signal.emit("🔍 SCANNING PAGE FOR TABLES...")
            self.log_signal.emit("="*60)
            self.log_signal.emit(f"URL: {self.url}")
            self.progress_signal.emit(20)
            
            # Launch Playwright
            self.log_signal.emit("🔍 Starting Playwright...")
            self.playwright = sync_playwright().start()
            self.log_signal.emit("✅ Playwright started!")
            
            # Launch browser
            self.log_signal.emit(f"Launching {self.browser_type} browser...")
            
            launch_args = [
                '--lang=en-US',
                '--accept-lang=en-US,en;q=0.9',
                '--disable-features=Translate'
            ]
            
            if self.browser_type == 'firefox':
                self.browser = self.playwright.firefox.launch(
                    headless=self.headless,
                    args=launch_args,
                    firefox_user_prefs={
                        'intl.accept_languages': 'en-US, en',
                        'intl.locale.requested': 'en-US'
                    }
                )
            elif self.browser_type == 'webkit':
                self.browser = self.playwright.webkit.launch(headless=self.headless, args=launch_args)
            else:
                self.browser = self.playwright.chromium.launch(headless=self.headless, args=launch_args)
            
            self.log_signal.emit("✅ Browser launched!")
            self.progress_signal.emit(30)
            
            # Create context and page
            self.browser_context = self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                locale='en-US',
                timezone_id='America/New_York',
                extra_http_headers={
                    'Accept-Language': 'en-US,en;q=0.9'
                }
            )
            self.page = self.browser_context.new_page()
            self.page.set_extra_http_headers({'Accept-Language': 'en-US,en;q=0.9'})
            self.log_signal.emit("✅ Page created!")
            
            # Force English language by adding ?hl=en parameter to URL
            url_to_load = self.url
            if 'lookerstudio.google.com' in self.url or 'datastudio.google.com' in self.url:
                # Check if URL already has hl parameter
                if '?hl=' not in self.url and '&hl=' not in self.url:
                    separator = '&' if '?' in self.url else '?'
                    url_to_load = f"{self.url}{separator}hl=en"
                    self.log_signal.emit("🌐 Loading page with English language parameter (?hl=en)...")
                else:
                    self.log_signal.emit("🌐 URL already has language parameter")
            
            # Navigate with English parameter
            self.log_signal.emit(f"Navigating to dashboard: {url_to_load}")
            self.page.goto(url_to_load)
            self.progress_signal.emit(50)
            
            # Wait for load
            self.log_signal.emit(f"Waiting {self.wait_time} seconds...")
            self.page.wait_for_load_state('domcontentloaded', timeout=30000)
            time.sleep(self.wait_time)
            self.progress_signal.emit(60)
            self.log_signal.emit("✅ Page loaded successfully in English")
            
            # Apply date range filter if enabled
            if self.enable_date_filter and self.start_date and self.end_date:
                self.log_signal.emit("📅 Applying date range filter...")
                self._apply_date_range_filter()
            
            # Detect ALL navigation pages
            self.log_signal.emit("")
            self.log_signal.emit("🔍 Detecting navigation pages...")
            navigation_pages = self._get_navigation_pages(self.page)
            
            if len(navigation_pages) > 1:
                self.log_signal.emit(f"Found {len(navigation_pages)} pages: {[p['label'] for p in navigation_pages]}")
                self.log_signal.emit("")
            else:
                self.log_signal.emit("Single page detected - no navigation needed")
                self.log_signal.emit("")
            
            self.progress_signal.emit(70)
            
            # SCAN ALL PAGES!
            all_tables = []
            for page_idx, page_info in enumerate(navigation_pages):
                if page_idx > 0:  # Navigate to subsequent pages
                    self.log_signal.emit(f"📄 Navigating to page: {page_info['label']}")
                    if not self._navigate_to_page(self.page, page_info['id']):
                        self.log_signal.emit(f"⚠️ Could not navigate to {page_info['label']}, skipping...")
                        continue
                    
                    # Reapply date range filter after page navigation
                    if self.enable_date_filter and self.start_date and self.end_date:
                        self.log_signal.emit("📅 Reapplying date range filter after page navigation...")
                        self._apply_date_range_filter()
                
                self.log_signal.emit("")
                self.log_signal.emit(f"🔍 Scanning page: {page_info['label']}")
                self.log_signal.emit("-"*60)
                
                # Find tables on this page
                table_wrappers = self.page.query_selector_all('table-wrapper')
                self.log_signal.emit(f"Found {len(table_wrappers)} <table-wrapper> elements")
                self.log_signal.emit("")
                
                page_tables_found = 0
                
                for idx, wrapper in enumerate(table_wrappers):
                    try:
                        if not wrapper.is_visible():
                            continue
                        
                        # Get chart title
                        chart_title = "Untitled"
                        try:
                            chart_title_text = self.page.evaluate('''(el) => {
                                let p = el.parentElement;
                                for (let i = 0; i < 8; i++) {
                                    if (!p) break;
                                    const titleEl = p.querySelector('chart-title .chart-title, chart-title div.chart-title');
                                    if (titleEl) {
                                        const text = (titleEl.innerText || titleEl.textContent || '').trim();
                                        if (text) return text;
                                    }
                                    p = p.parentElement;
                                }
                                return null;
                            }''', wrapper)
                            
                            if chart_title_text:
                                chart_title = chart_title_text
                        except:
                            pass
                        
                        # Count rows
                        rows = wrapper.query_selector_all('.tableBody .row')
                        cells = wrapper.query_selector_all('.cell')
                        
                        page_tables_found += 1
                        
                        # Store table info with page context
                        table_info = {
                            'selector': 'table-wrapper',
                            'index': len(all_tables) + page_tables_found,
                            'chart_title': chart_title,
                            'page_label': page_info['label'],
                            'page_id': page_info['id'],
                            'rows': len(rows),
                            'cells': len(cells)
                        }
                        all_tables.append(table_info)
                        
                        self.log_signal.emit(f"✓ Table #{len(all_tables)}: {chart_title}")
                    
                    except:
                        continue
                
                self.log_signal.emit("-"*60)
                self.log_signal.emit(f"✅ Page '{page_info['label']}' complete! Found {page_tables_found} table(s)")
                self.log_signal.emit("")
                
                # Update progress
                progress = 70 + int((page_idx + 1) / len(navigation_pages) * 20)
                self.progress_signal.emit(progress)
            
            # Store all found tables
            self.found_tables = all_tables
            
            self.log_signal.emit("="*60)
            self.log_signal.emit(f"✅ SCAN COMPLETE! Found {len(all_tables)} table(s) across {len(navigation_pages)} page(s)")
            self.log_signal.emit("")
            
            if len(all_tables) > 0:
                self.log_signal.emit("✅ Scan complete! Browser is OPEN!")
                self.status_signal.emit(f"Ready to extract {len(all_tables)} tables from {len(navigation_pages)} pages")
                self.progress_signal.emit(100)
                self.scan_complete_signal.emit([f"{t['chart_title']} (Page: {t['page_label']})" for t in all_tables])
                
                # WAIT HERE for extraction signal (browser stays open!)
                self.log_signal.emit("")
                self.log_signal.emit("⏸️  Waiting for extraction command...")
                self.is_waiting = True
                
                # Poll for extraction signal (check every 100ms)
                while not self.should_extract:
                    time.sleep(0.1)
                
                self.is_waiting = False
                self.log_signal.emit("✅ Extraction signal received! Starting extraction...")
                
                # Continue with extraction in SAME thread!
                self._do_extraction()
            else:
                self.log_signal.emit("⚠️ No tables found")
                self.close_browser()
                self.scan_failed_signal.emit("No tables found")
        
        except Exception as e:
            self.log_signal.emit(f"❌ Scan Error: {str(e)}")
            import traceback
            self.log_signal.emit(f"{traceback.format_exc()}")
            self.close_browser()
            self.scan_failed_signal.emit(str(e))
    
    def _get_navigation_pages(self, page):
        """Extract all navigation pages from Looker Studio"""
        try:
            nav_links = page.query_selector_all('xap-nav-link')
            pages = []
            
            for link in nav_links:
                try:
                    page_id = link.get_attribute('id')
                    page_label_elem = link.query_selector('.xap-nav-item-label .mat-mdc-list-text')
                    page_label = page_label_elem.inner_text().strip() if page_label_elem else f"Page {len(pages) + 1}"
                    is_active = 'xap-nav-item-active' in link.get_attribute('class')
                    
                    if page_id:
                        pages.append({
                            'id': page_id,
                            'label': page_label,
                            'is_active': is_active
                        })
                except:
                    continue
            
            if not pages:  # If no navigation found, treat as single page
                pages = [{'id': 'page_1', 'label': 'Main Page', 'is_active': True}]
            
            return pages
        except Exception as e:
            self.log_signal.emit(f"⚠️ Could not detect navigation pages: {str(e)}")
            return [{'id': 'page_1', 'label': 'Main Page', 'is_active': True}]
    
    def _navigate_to_page(self, page, page_id):
        """Navigate to a specific page by clicking navigation link"""
        try:
            nav_link = page.query_selector(f'xap-nav-link[id="{page_id}"]')
            if nav_link:
                self.log_signal.emit(f"  └─ Found navigation link for page ID: {page_id}")
                nav_link.click()
                page.wait_for_load_state('domcontentloaded', timeout=10000)
                time.sleep(3)  # Wait for page to load
                
                # Verify we're on correct page
                current_pages = self._get_navigation_pages(page)
                for page_info in current_pages:
                    if page_info.get('is_active', False) and page_info['id'] == page_id:
                        self.log_signal.emit(f"  └─ ✓ Successfully navigated to page: {page_info['label']}")
                        return True
                
                self.log_signal.emit(f"  └─ ⚠️ Navigation may have failed")
                return False
            else:
                self.log_signal.emit(f"  └─ ⚠️ Navigation link not found for page ID: {page_id}")
                return False
        except Exception as e:
            self.log_signal.emit(f"⚠️ Could not navigate to page {page_id}: {str(e)}")
            return False
    
    def _apply_date_range_filter(self):
        """Apply date range filter to Looker Studio dashboard"""
        try:
            # Look for date range picker button
            date_picker_selectors = [
                'button.ng2-date-picker-button',
                'button[aria-label*="date"]',
                'button[class*="date"]',
                '.date-text',
                'ng2-date-input button',
                'ga-date-range-picker-wrapper button'
            ]
            
            date_picker_button = None
            for selector in date_picker_selectors:
                try:
                    date_picker_button = self.page.query_selector(selector)
                    if date_picker_button:
                        break
                except:
                    continue
            
            if not date_picker_button:
                self.log_signal.emit("  └─ ⚠️ No date range picker found - dashboard may not have date filters")
                return
            
            # Click to open date picker
            self.log_signal.emit("  └─ 📅 Opening date range picker...")
            date_picker_button.click()
            time.sleep(2)
            
            # Look for the date picker dialog
            dialog_selectors = [
                '.ng2-date-picker-dialog',
                '.canvas-date-picker-dialog',
                'ng2-date-picker-dialog',
                '[class*="date-picker-dialog"]'
            ]
            
            dialog = None
            for selector in dialog_selectors:
                try:
                    dialog = self.page.query_selector(selector)
                    if dialog:
                        break
                except:
                    continue
            
            if not dialog:
                self.log_signal.emit("  └─ ⚠️ Date picker dialog not found")
                return
            
            self.log_signal.emit("  └─ 📅 Date picker dialog opened")
            
            # Set start date
            self.log_signal.emit(f"  └─ 📅 Setting start date: {self.start_date}")
            self._set_date_in_calendar('start', self.start_date)
            
            # Set end date
            self.log_signal.emit(f"  └─ 📅 Setting end date: {self.end_date}")
            self._set_date_in_calendar('end', self.end_date)
            
            # Click Apply button - look in the dialog (exact HTML match)
            apply_selectors = [
                '.footer-buttons .apply-button',
                '.footer-buttons button.apply-button',
                'button.apply-button',
                '.footer-buttons button:last-child',
                'button[class*="apply"]',
                'button:has-text("Apply")',
                'button[aria-label*="Apply"]',
                'button[class*="primary"]',
                'button[class*="confirm"]',
                '.mat-button:has-text("Apply")',
                'button[type="submit"]'
            ]
            
            apply_button = None
            for selector in apply_selectors:
                try:
                    apply_button = self.page.query_selector(selector)
                    if apply_button:
                        button_text = apply_button.text_content().lower()
                        if 'apply' in button_text or 'confirm' in button_text or 'ok' in button_text:
                            break
                except:
                    continue
            
            if apply_button:
                self.log_signal.emit("  └─ 📅 Applying date range...")
                apply_button.click()
                time.sleep(3)
                self.log_signal.emit("  └─ ✅ Date range applied successfully!")
            else:
                self.log_signal.emit("  └─ ⚠️ Apply button not found - trying to close dialog")
                # Try pressing Enter or Escape
                self.page.keyboard.press('Enter')
                time.sleep(1)
                self.page.keyboard.press('Escape')
                time.sleep(1)
            
        except Exception as e:
            self.log_signal.emit(f"  └─ ⚠️ Date filter error: {str(e)}")
    
    def _set_date_in_calendar(self, date_type, target_date):
        """Set date in DUAL calendar based on EXACT HTML structure"""
        try:
            # Format date for aria-label matching (e.g., "Sep 21, 2025")
            target_month_short = target_date.strftime('%b').upper()  # SEP
            target_month_full = target_date.strftime('%B').upper()  # SEPTEMBER
            target_day = target_date.day  # 21
            target_year = target_date.year  # 2025
            aria_label_pattern = f"{target_date.strftime('%b')} {target_day}, {target_year}"  # Sep 21, 2025
            
            self.log_signal.emit(f"    └─ 📅 Looking for date: {aria_label_pattern}")
            
            # Find the correct calendar wrapper based on EXACT HTML structure
            if date_type == 'start':
                calendar_wrapper_selector = '.start-date-picker.calendar-wrapper'
            else:  # end
                calendar_wrapper_selector = '.end-date-picker.calendar-wrapper'
            
            calendar_wrapper = self.page.query_selector(calendar_wrapper_selector)
            
            if not calendar_wrapper:
                self.log_signal.emit(f"    └─ ⚠️ {date_type.title()} calendar wrapper not found")
                return
            
            self.log_signal.emit(f"    └─ ✅ Found {date_type} calendar wrapper")
            
            # Check current month/year in this calendar
            # <span aria-hidden="true">SEP 2025</span> inside button.mat-calendar-period-button
            period_button = calendar_wrapper.query_selector('button.mat-calendar-period-button')
            if period_button:
                current_period = period_button.text_content().strip()
                self.log_signal.emit(f"    └─ 📅 Current calendar shows: {current_period}")
                
                # Check if we need to navigate to a different month/year
                expected_period = f"{target_month_short} {target_year}"
                if expected_period not in current_period:
                    self.log_signal.emit(f"    └─ 📅 Need to navigate from '{current_period}' to '{expected_period}'")
                    
                    # Click the period button to open year/month selector
                    try:
                        self.log_signal.emit(f"    └─ 📅 Clicking month/year button to open selector...")
                        period_button.click()
                        time.sleep(1)
                        
                        # Now look for the target year button
                        # The year buttons appear after clicking the period button
                        year_buttons = calendar_wrapper.query_selector_all('button')
                        year_found = False
                        
                        for button in year_buttons:
                            try:
                                button_text = button.text_content().strip()
                                if str(target_year) == button_text:
                                    self.log_signal.emit(f"    └─ 📅 Found year button: {target_year}, clicking...")
                                    button.click()
                                    time.sleep(1)
                                    year_found = True
                                    break
                            except:
                                continue
                        
                        if not year_found:
                            self.log_signal.emit(f"    └─ ⚠️ Year {target_year} not found in year selector")
                        
                        # After selecting year, now select the month
                        month_buttons = calendar_wrapper.query_selector_all('button')
                        month_found = False
                        
                        for button in month_buttons:
                            try:
                                button_text = button.text_content().strip().upper()
                                # Month buttons might be "JAN", "FEB", "MAR", etc.
                                if target_month_short in button_text or target_month_full[:3] in button_text:
                                    self.log_signal.emit(f"    └─ 📅 Found month button: {button_text}, clicking...")
                                    button.click()
                                    time.sleep(1)
                                    month_found = True
                                    break
                            except:
                                continue
                        
                        if not month_found:
                            self.log_signal.emit(f"    └─ ⚠️ Month {target_month_short} not found in month selector")
                        
                        if year_found and month_found:
                            self.log_signal.emit(f"    └─ ✅ Successfully navigated to {expected_period}")
                        
                    except Exception as e:
                        self.log_signal.emit(f"    └─ ⚠️ Error navigating to month/year: {str(e)}")
            
            # Now find and click the day button using aria-label (EXACT HTML match)
            # <button aria-label="Sep 21, 2025">
            day_button = calendar_wrapper.query_selector(f'button[aria-label="{aria_label_pattern}"]')
            
            if day_button:
                self.log_signal.emit(f"    └─ 📅 Clicking day button: {aria_label_pattern}")
                day_button.click()
                time.sleep(1)
                self.log_signal.emit(f"    └─ ✅ {date_type.title()} date set successfully!")
            else:
                self.log_signal.emit(f"    └─ ⚠️ Day button with aria-label '{aria_label_pattern}' not found")
                
                # Fallback: try to find by text content
                day_buttons = calendar_wrapper.query_selector_all('button.mat-calendar-body-cell')
                self.log_signal.emit(f"    └─ 📅 Trying fallback: found {len(day_buttons)} day buttons")
                
                for button in day_buttons:
                    try:
                        button_text = button.text_content().strip()
                        button_aria = button.get_attribute('aria-label') or ''
                        if button_text == str(target_day) and target_month_short[:3] in button_aria.upper():
                            self.log_signal.emit(f"    └─ 📅 Found day {target_day} by text content, clicking...")
                            button.click()
                            time.sleep(1)
                            self.log_signal.emit(f"    └─ ✅ {date_type.title()} date set successfully (fallback)!")
                            break
                    except Exception as e:
                        continue
            
        except Exception as e:
            self.log_signal.emit(f"    └─ ⚠️ Error setting {date_type} date: {str(e)}")
    
    def trigger_extraction(self):
        """Called from main thread to start extraction"""
        self.should_extract = True
    
    def _do_extraction(self):
        """Do the actual extraction using Looker Studio's native Export - SAME THREAD!"""
        # Initialize extraction statistics
        extraction_stats = {
            'start_time': datetime.now(),
            'url': self.url,
            'browser': self.browser_type,
            'headless': self.headless,
            'wait_time': self.wait_time,
            'date_filter_enabled': self.enable_date_filter,
            'start_date': self.start_date.strftime('%Y-%m-%d') if self.start_date else None,
            'end_date': self.end_date.strftime('%Y-%m-%d') if self.end_date else None,
            'tables': [],
            'total_rows': 0,
            'errors': []
        }
        
        try:
            self.log_signal.emit("")
            self.log_signal.emit("="*60)
            self.log_signal.emit("🚀 EXTRACTING TABLES (Using Looker Export)...")
            self.log_signal.emit("="*60)
            self.log_signal.emit("Using Looker Studio's native Export feature...")
            self.log_signal.emit("This downloads ALL data, not just visible rows!")
            self.log_signal.emit("")
            self.progress_signal.emit(10)
            
            # Create output directory
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_dir = Path(self.output_path) / f"looker_data_{timestamp}"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            self.log_signal.emit(f"Output: {output_dir}")
            self.log_signal.emit("")
            
            extraction_stats['output_dir'] = str(output_dir)
            extraction_stats['timestamp'] = timestamp
            
            # Detect ALL navigation pages
            self.log_signal.emit("🔍 Detecting navigation pages for extraction...")
            navigation_pages = self._get_navigation_pages(self.page)
            
            if len(navigation_pages) > 1:
                self.log_signal.emit(f"Found {len(navigation_pages)} pages: {[p['label'] for p in navigation_pages]}")
                self.log_signal.emit("")
            else:
                self.log_signal.emit("Single page detected - no navigation needed")
                self.log_signal.emit("")
            
            self.progress_signal.emit(20)
            
            # Extract from ALL pages
            tables_extracted = 0
            global_table_counter = 0
            
            for page_idx, page_info in enumerate(navigation_pages):
                # Always check current page before navigating
                self.log_signal.emit(f"🎯 Processing page {page_idx + 1}/{len(navigation_pages)}: {page_info['label']}")
                
                # Navigate to the page if not already on it
                try:
                    current_pages_check = self._get_navigation_pages(self.page)
                    current_active_idx = 0
                    for i, page_check in enumerate(current_pages_check):
                        if page_check.get('is_active', False):
                            current_active_idx = i
                            break
                    
                    self.log_signal.emit(f"📍 Currently on page: {current_pages_check[current_active_idx]['label']} (index {current_active_idx})")
                    
                    # Navigate if needed
                    if page_idx != current_active_idx:
                        self.log_signal.emit(f"📄 Navigating to page: {page_info['label']}")
                        if not self._navigate_to_page(self.page, page_info['id']):
                            self.log_signal.emit(f"⚠️ Could not navigate to {page_info['label']}, skipping...")
                            continue
                        
                        # Reapply date range filter after page navigation during extraction
                        if self.enable_date_filter and self.start_date and self.end_date:
                            self.log_signal.emit("📅 Reapplying date range filter after page navigation...")
                            self._apply_date_range_filter()
                    else:
                        self.log_signal.emit(f"📍 Already on page: {page_info['label']}")
                
                except Exception as e:
                    self.log_signal.emit(f"⚠️ Error checking current page: {e}")
                    self.log_signal.emit(f"📄 Attempting navigation to page: {page_info['label']}")
                    if not self._navigate_to_page(self.page, page_info['id']):
                        self.log_signal.emit(f"⚠️ Could not navigate to {page_info['label']}, skipping...")
                        continue
                
                self.log_signal.emit("")
                self.log_signal.emit(f"🚀 Extracting from page: {page_info['label']}")
                self.log_signal.emit("-"*60)
                
                # Get all table-wrappers for current page
                table_wrappers = self.page.query_selector_all('table-wrapper')
                self.log_signal.emit(f"  └─ Found {len(table_wrappers)} table-wrapper elements on this page")
                
                for idx, wrapper in enumerate(table_wrappers):
                    try:
                        if not wrapper.is_visible():
                            continue
                        
                        global_table_counter += 1
                        
                        # Update progress
                        total_pages = len(navigation_pages)
                        page_progress = (page_idx / total_pages) * 70
                        table_progress = (idx / len(table_wrappers)) * (70 / total_pages) if len(table_wrappers) > 0 else 0
                        progress = 20 + int(page_progress + table_progress)
                        self.progress_signal.emit(progress)
                        
                        # Get chart title
                        chart_title = f"table_{global_table_counter}"
                        try:
                            chart_title_text = self.page.evaluate('''(el) => {
                                let p = el.parentElement;
                                for (let i = 0; i < 8; i++) {
                                    if (!p) break;
                                    const titleEl = p.querySelector('chart-title .chart-title, chart-title div.chart-title');
                                    if (titleEl) {
                                        const text = (titleEl.innerText || titleEl.textContent || '').trim();
                                        if (text) return text;
                                    }
                                    p = p.parentElement;
                                }
                                return null;
                            }''', wrapper)
                            
                            if chart_title_text:
                                chart_title = chart_title_text.strip()
                        except:
                            pass
                        
                        self.log_signal.emit(f"Processing Table #{global_table_counter}: {chart_title}")
                        
                        # Right-click table
                        self.log_signal.emit(f"  └─ Right-clicking...")
                        wrapper.click(button='right')
                        
                        # Wait for context menu
                        self.log_signal.emit(f"  └─ Waiting for menu...")
                        self.page.wait_for_selector('.cdk-overlay-pane', timeout=10000, state='visible')
                        time.sleep(0.5)
                        
                        # Click Export
                        self.log_signal.emit(f"  └─ Clicking Export...")
                        export_btn = None
                        
                        try:
                            export_btn = self.page.wait_for_selector('button[data-test-id="Export"]', timeout=3000, state='visible')
                        except:
                            try:
                                export_btn = self.page.wait_for_selector('button:has-text("Export")', timeout=3000, state='visible')
                            except:
                                try:
                                    export_btn = self.page.wait_for_selector('button[mat-menu-item]:has-text("Export")', timeout=3000, state='visible')
                                except:
                                    pass
                        
                        if not export_btn:
                            self.log_signal.emit(f"  └─ ⚠️ Export button not found, skipping")
                            continue
                        
                        export_btn.click()
                        time.sleep(1)
                        
                        # Set filename
                        self.log_signal.emit(f"  └─ Setting filename: {chart_title}")
                        filename_input = self.page.wait_for_selector('input.export-name-field', timeout=5000)
                        if filename_input:
                            filename_input.click()
                            filename_input.fill('')
                            filename_input.type(chart_title)
                        
                        # Download
                        self.log_signal.emit(f"  └─ Downloading...")
                        
                        try:
                            with self.page.expect_download() as download_info:
                                export_dialog_btn = self.page.wait_for_selector(
                                    'mat-dialog-actions button[mat-raised-button]',
                                    timeout=5000
                                )
                                if export_dialog_btn:
                                    export_dialog_btn.click()
                            
                            download = download_info.value
                            
                            filename = f"{chart_title}.csv"
                            download_path = output_dir / filename
                            download.save_as(download_path)
                            
                            self.log_signal.emit(f"  └─ ✓ Downloaded: {filename}")
                            
                            # Get row count and track statistics
                            try:
                                df = pd.read_csv(download_path)
                                rows = len(df)
                                cols = len(df.columns)
                                self.log_signal.emit(f"  └─ ✓ {rows:,} rows × {cols} columns")
                                
                                # Track stats
                                extraction_stats['tables'].append({
                                    'index': global_table_counter,
                                    'chart_title': chart_title,
                                    'filename': filename,
                                    'page_label': page_info['label'],
                                    'rows': rows,
                                    'columns': cols,
                                    'column_names': list(df.columns)
                                })
                                extraction_stats['total_rows'] += rows
                            except Exception as e:
                                self.log_signal.emit(f"  └─ ⚠️ Could not read CSV: {str(e)}")
                                extraction_stats['tables'].append({
                                    'index': global_table_counter,
                                    'chart_title': chart_title,
                                    'filename': filename,
                                    'page_label': page_info['label'],
                                    'rows': 0,
                                    'columns': 0,
                                    'column_names': []
                                })
                            
                            tables_extracted += 1
                            self.log_signal.emit("")
                            time.sleep(1)
                        
                        except Exception as download_error:
                            error_msg = f"Download failed for {chart_title}: {str(download_error)}"
                            self.log_signal.emit(f"  └─ ⚠️ {error_msg}")
                            extraction_stats['errors'].append(error_msg)
                            # Try to close dialog
                            try:
                                cancel_btn = self.page.query_selector('button:has-text("Cancel")')
                                if cancel_btn:
                                    cancel_btn.click()
                                time.sleep(0.3)
                            except:
                                pass
                            continue
                    
                    except Exception as e:
                        error_msg = f"Error processing table {global_table_counter}: {str(e)}"
                        self.log_signal.emit(f"⚠️ {error_msg}")
                        extraction_stats['errors'].append(error_msg)
                        continue
                
                self.log_signal.emit("-"*60)
                self.log_signal.emit(f"✅ Page '{page_info['label']}' extraction complete!")
                self.log_signal.emit("")
                
                # Update progress
                page_progress_final = 20 + int(((page_idx + 1) / len(navigation_pages)) * 70)
                self.progress_signal.emit(page_progress_final)
            
            self.progress_signal.emit(100)
            self.log_signal.emit("="*60)
            
            # Save execution log and summary
            extraction_stats['end_time'] = datetime.now()
            extraction_stats['duration'] = (extraction_stats['end_time'] - extraction_stats['start_time']).total_seconds()
            extraction_stats['tables_extracted'] = tables_extracted
            extraction_stats['pages_processed'] = len(navigation_pages)
            
            self._save_execution_log(output_dir, extraction_stats)
            
            # Close browser after extraction
            self.close_browser()
            
            if tables_extracted > 0:
                self.log_signal.emit(f"✅ SUCCESS! Extracted {tables_extracted} table(s) across {len(navigation_pages)} page(s)!")
                self.log_signal.emit(f"📁 Output: {output_dir}")
                self.extraction_complete_signal.emit(tables_extracted, str(output_dir))
            else:
                self.log_signal.emit("⚠️ No tables extracted")
                self.extraction_failed_signal.emit("No tables extracted")
        
        except Exception as e:
            self.log_signal.emit(f"❌ Extraction Error: {str(e)}")
            import traceback
            self.log_signal.emit(f"{traceback.format_exc()}")
            self.close_browser()
            self.extraction_failed_signal.emit(str(e))
    
    def close_browser(self):
        """Close browser"""
        try:
            if self.page:
                self.page.close()
            if self.browser_context:
                self.browser_context.close()
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
            self.log_signal.emit("Browser closed.")
        except:
            pass
    
    def _save_execution_log(self, output_dir: Path, stats: dict):
        """Save comprehensive execution log and summary"""
        try:
            # Save to output directory
            log_file = output_dir / "execution_log.txt"
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write("="*80 + "\n")
                f.write("🌊 LOOKER STUDIO DATA EXTRACTOR - EXECUTION LOG\n")
                f.write("="*80 + "\n\n")
                
                # Write all log messages
                for log_entry in self.execution_log:
                    f.write(f"{log_entry}\n")
            
            self.log_signal.emit(f"📝 Execution log saved: execution_log.txt")
            
            # Save detailed summary
            summary_file = output_dir / "extraction_summary.txt"
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write("="*80 + "\n")
                f.write("📊 LOOKER STUDIO DATA EXTRACTION SUMMARY\n")
                f.write("="*80 + "\n\n")
                
                # Execution Details
                f.write("EXECUTION DETAILS:\n")
                f.write("-" * 80 + "\n")
                f.write(f"Start Time:        {stats['start_time'].strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"End Time:          {stats['end_time'].strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Duration:          {stats['duration']:.2f} seconds\n")
                f.write(f"Dashboard URL:     {stats['url']}\n")
                f.write(f"Browser:           {stats['browser']}\n")
                f.write(f"Headless Mode:     {stats['headless']}\n")
                f.write(f"Page Wait Time:    {stats['wait_time']} seconds\n")
                f.write(f"Date Filter:       {'Enabled' if stats.get('date_filter_enabled', False) else 'Disabled'}\n")
                if stats.get('date_filter_enabled', False):
                    f.write(f"Date Range:        {stats.get('start_date', 'N/A')} to {stats.get('end_date', 'N/A')}\n")
                f.write(f"Output Directory:  {output_dir}\n\n")
                
                # Extraction Results
                f.write("EXTRACTION RESULTS:\n")
                f.write("-" * 80 + "\n")
                f.write(f"Total Tables Found:     {len(stats['tables'])}\n")
                f.write(f"Tables Extracted:       {stats['tables_extracted']}\n")
                f.write(f"Pages Processed:        {stats.get('pages_processed', 1)}\n")
                f.write(f"Total Rows Extracted:   {stats['total_rows']:,}\n")
                f.write(f"Errors Encountered:     {len(stats['errors'])}\n\n")
                
                # Table Details
                if stats['tables']:
                    f.write("EXTRACTED TABLES:\n")
                    f.write("=" * 80 + "\n\n")
                    
                    for table in stats['tables']:
                        f.write(f"Table #{table['index']}: {table['chart_title']}\n")
                        f.write(f"  Page:       {table.get('page_label', 'Unknown')}\n")
                        f.write(f"  File:       {table['filename']}\n")
                        f.write(f"  Rows:       {table['rows']:,}\n")
                        f.write(f"  Columns:    {table['columns']}\n")
                        if table['column_names']:
                            f.write(f"  Column Names:\n")
                            for col in table['column_names']:
                                f.write(f"    - {col}\n")
                        f.write("\n")
                
                # Errors
                if stats['errors']:
                    f.write("\n")
                    f.write("ERRORS ENCOUNTERED:\n")
                    f.write("=" * 80 + "\n")
                    for i, error in enumerate(stats['errors'], 1):
                        f.write(f"{i}. {error}\n")
                    f.write("\n")
                
                # Footer
                f.write("="*80 + "\n")
                f.write("End of Summary Report\n")
                f.write("="*80 + "\n")
            
            self.log_signal.emit(f"📊 Summary report saved: extraction_summary.txt")
            
            # Also save a copy to gui_logs folder
            try:
                gui_logs_dir = Path(self.output_path).parent.parent / "gui_logs"
                gui_logs_dir.mkdir(parents=True, exist_ok=True)
                
                session_log = gui_logs_dir / f"looker_studio_session_{stats['timestamp']}.txt"
                with open(session_log, 'w', encoding='utf-8') as f:
                    f.write("="*80 + "\n")
                    f.write(f"🌊 LOOKER STUDIO EXTRACTION SESSION - {stats['timestamp']}\n")
                    f.write("="*80 + "\n\n")
                    
                    f.write(f"Status: {'✅ SUCCESS' if stats['tables_extracted'] > 0 else '⚠️ FAILED'}\n")
                    f.write(f"Extracted: {stats['tables_extracted']} table(s)\n")
                    f.write(f"Total Rows: {stats['total_rows']:,}\n")
                    f.write(f"Duration: {stats['duration']:.2f} seconds\n")
                    f.write(f"Errors: {len(stats['errors'])}\n")
                    f.write(f"Output: {output_dir}\n")
                    f.write(f"\nFull logs saved in output directory.\n")
                
                self.log_signal.emit(f"📁 Session log saved to gui_logs/")
            except Exception as e:
                self.log_signal.emit(f"⚠️ Could not save to gui_logs: {str(e)}")
            
        except Exception as e:
            self.log_signal.emit(f"⚠️ Warning: Could not save execution log - {str(e)}")



class LookerStudioExtractorTool(PathConfigMixin, QDialog):
    """Main dialog for the Looker Studio extractor tool."""

    PATH_CONFIG = {
        "show_input": False,
        "show_output": True,
        "include_open_buttons": True,
        "output_label": "📤 Output Folder:",
    }

    def __init__(self, parent=None, input_path: str | None = None, output_path: str | None = None):
        super().__init__(parent)

        self.path_manager = get_path_manager()
        self._path_listener_registered = False

        resolved_input = Path(input_path).expanduser().resolve() if input_path else self.path_manager.get_input_path()
        resolved_output = Path(output_path).expanduser().resolve() if output_path else self.path_manager.get_output_path()

        self.input_path = resolved_input
        self.output_path = resolved_output
        self.is_extracting = False
        self.is_scanning = False
        self.found_tables = []

        if input_path:
            self.path_manager.set_input_path(resolved_input)
        if output_path:
            self.path_manager.set_output_path(resolved_output)

        # Unified worker (handles both scan and extraction in ONE thread!)
        self.worker = None
        self.worker_thread = None
        self.execution_log_messages = []  # Local storage for log messages (renamed to avoid conflict with widget)

        self.log_manager = None
        self.log_category = f"TOOL:{self.__class__.__name__}"
        try:
            if callable(get_log_manager):
                self.log_manager = get_log_manager()
        except Exception:
            self.log_manager = None

        # Get theme - Inherit from parent (main GUI) using NEW system! ✨
        self.current_theme = None
        if THEME_AVAILABLE:
            # Try to inherit theme from parent (main GUI)
            if hasattr(parent, 'current_theme') and parent.current_theme:
                self.current_theme = parent.current_theme
                safe_theme_name = self.current_theme.theme_name.encode('ascii', 'ignore').decode('ascii')
                print(f"✅ [THEME] Inherited from parent: {safe_theme_name}")
            else:
                # Fallback: load default theme
                theme_manager = get_theme_manager()
                themes = theme_manager.get_available_themes()
                if themes:
                    self.current_theme = theme_manager.load_theme(themes[0])
                    print(f"✅ [THEME] Loaded default: {themes[0]}")
        
        # Setup UI
        self.setup_window()
        self.setup_ui()
        
        # Apply theme after getting correct theme from parent
        self.apply_theme()

        self.path_manager.register_listener(self._handle_paths_changed)
        self._path_listener_registered = True
        self._handle_paths_changed(
            self.path_manager.get_input_path(),
            self.path_manager.get_output_path()
        )
        self._sync_path_edits(
            Path(self.input_path),
            Path(self.output_path)
        )

        # Initial log
        self.log("Tool initialized! Ready to extract from Looker Studio!")
        self.log("[WORKFLOW]:")
        self.log("  1. Click 'Scan Page' -> Opens browser, finds tables, STAYS OPEN")
        self.log("  2. Review scan results")
        self.log("  3. Click 'Extract Tables' -> Downloads CSVs, closes browser")
        self.log("")
    
    def setup_window(self):
        """Setup window"""
        self.setWindowTitle("🌊 Looker Studio Data Extractor")
        self.setGeometry(100, 100, 950, 800)
        
        # Set object name for proper theme styling
        self.setObjectName("toolDialog")  # Apply global dialog styling
        
        # Set window flags to show all controls (minimize, maximize, close)
        self.setWindowFlags(Qt.Window | Qt.WindowMinMaxButtonsHint | Qt.WindowCloseButtonHint)
        
        # Center on screen
        screen_geometry = self.screen().geometry()
        x = (screen_geometry.width() - 950) // 2
        y = (screen_geometry.height() - 800) // 2
        self.move(x, y)
    
    def setup_ui(self):
        """Setup UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # Title
        title = QLabel("🌊 Looker Studio Data Extractor")
        title.setFont(QFont("Arial", 24, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setObjectName("toolTitle")
        main_layout.addWidget(title)
        
        # Create scroll area for main content
        scroll_area = QScrollArea()
        scroll_area.setObjectName("contentScroll")  # Apply global scroll area styling
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        # No hardcoded styles - inherit from global theme! ✨
        
        # Create content widget for scroll area
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(15)
        
        # Path Section
        self.build_path_controls(
            content_layout,
            show_input=False,
            show_output=True,
            include_open_buttons=True,
            output_label="📤 Output Folder:",
        )

        content_layout.addWidget(path_frame)

        # URL Section
        url_frame = QFrame()
        url_frame.setObjectName("glassFrame")
        url_layout = QVBoxLayout(url_frame)
        url_layout.setContentsMargins(15, 15, 15, 15)
        
        url_label = QLabel("📍 Dashboard URL:")
        url_label.setFont(QFont("Arial", 13, QFont.Bold))
        url_layout.addWidget(url_label)
        
        self.url_entry = QLineEdit()
        self.url_entry.setText("https://lookerstudio.google.com/reporting/df3de77e-6a24-4d6b-9631-d0e8d94aa06d/page/kIs5C")
        self.url_entry.setPlaceholderText("https://lookerstudio.google.com/reporting/...")
        self.url_entry.setObjectName("urlInput")
        self.url_entry.setMinimumHeight(35)
        url_layout.addWidget(self.url_entry)

        content_layout.addWidget(url_frame)
    
        # Settings Section
        settings_frame = QFrame()
        settings_frame.setObjectName("glassFrame")
        settings_layout = QHBoxLayout(settings_frame)
        settings_layout.setContentsMargins(15, 15, 15, 15)
        settings_layout.setSpacing(20)
        
        # Left - Settings
        left_column = QWidget()
        left_layout = QVBoxLayout(left_column)
        left_layout.setSpacing(10)
        
        settings_label = QLabel("⚙️ Settings")
        settings_label.setFont(QFont("Arial", 13, QFont.Bold))
        left_layout.addWidget(settings_label)
        
        browser_label = QLabel("Browser:")
        browser_label.setFont(QFont("Arial", 11))
        left_layout.addWidget(browser_label)
        
        self.browser_combo = QComboBox()
        self.browser_combo.addItems(["chromium", "firefox", "webkit"])
        self.browser_combo.setObjectName("browserCombo")
        left_layout.addWidget(self.browser_combo)
        
        headless_container = QWidget()
        headless_layout = QHBoxLayout(headless_container)
        headless_layout.setContentsMargins(0, 0, 0, 0)
        
        headless_label = QLabel("Headless Mode:")
        headless_label.setFont(QFont("Arial", 11))
        headless_layout.addWidget(headless_label)
        
        self.headless_checkbox = QCheckBox("Run in background")
        self.headless_checkbox.setChecked(False)
        headless_layout.addWidget(self.headless_checkbox)
        headless_layout.addStretch()
        
        left_layout.addWidget(headless_container)
        
        # Wait Time Section (Left)
        wait_container = QWidget()
        wait_layout = QVBoxLayout(wait_container)
        wait_layout.setSpacing(5)
        
        wait_label = QLabel("Page Wait Time (sec):")
        wait_label.setFont(QFont("Arial", 11))
        wait_layout.addWidget(wait_label)
        
        self.wait_time_entry = QLineEdit("15")
        self.wait_time_entry.setObjectName("waitTimeInput")
        self.wait_time_entry.setFixedWidth(80)
        wait_layout.addWidget(self.wait_time_entry)
        
        wait_note = QLabel("💡 15-20 sec recommended")
        wait_note.setFont(QFont("Arial", 9))
        wait_note.setObjectName("helpText")  # Let theme handle the color
        wait_layout.addWidget(wait_note)
        
        # Date Range Section (Right) - More space from wait time
        date_container = QWidget()
        date_layout = QVBoxLayout(date_container)
        date_layout.setSpacing(5)
        date_layout.setContentsMargins(0, 0, 0, 0)  # No margins - LEVEL alignment with other content
        
        # Date Range Header - checkbox closer to text (NORMAL alignment)
        date_header_layout = QHBoxLayout()
        date_label = QLabel("📅 Date Range Filter:")
        date_label.setFont(QFont("Arial", 11))
        date_header_layout.addWidget(date_label)
        
        self.enable_date_filter = QCheckBox("Enable")
        self.enable_date_filter.setChecked(False)
        self.enable_date_filter.setFont(QFont("Arial", 10))
        date_header_layout.addWidget(self.enable_date_filter)
        date_header_layout.addStretch()
        
        date_header_container = QWidget()
        date_header_container.setLayout(date_header_layout)
        date_layout.addWidget(date_header_container)
        
        # Date inputs with transparent styling and consistent alignment
        self.start_date_entry = QDateEdit()
        self.start_date_entry.setDate(QDate.currentDate().addDays(-7))
        self.start_date_entry.setCalendarPopup(True)
        self.start_date_entry.setFixedSize(120, 25)  # Fixed height for alignment
        self.start_date_entry.setFont(QFont("Arial", 8))
        self.start_date_entry.setObjectName("dateInput")  # Apply transparent styling
        self.start_date_entry.setAlignment(Qt.AlignCenter)  # Center text vertically
        
        self.end_date_entry = QDateEdit()
        self.end_date_entry.setDate(QDate.currentDate())
        self.end_date_entry.setCalendarPopup(True)
        self.end_date_entry.setFixedSize(120, 25)  # Fixed height for alignment
        self.end_date_entry.setFont(QFont("Arial", 8))
        self.end_date_entry.setObjectName("dateInput")  # Apply transparent styling
        self.end_date_entry.setAlignment(Qt.AlignCenter)  # Center text vertically
        
        # Date inputs with labels ABOVE inputs (PROPER INDENTATION like the picture)
        date_inputs_layout = QHBoxLayout()
        date_inputs_layout.setSpacing(20)  # Space between Start and End sections
        date_inputs_layout.setContentsMargins(0, 0, 0, 0)  # No margins
        
        # Start Date section (vertical layout) - INDENTED like in the picture
        start_section = QVBoxLayout()
        start_section.setSpacing(2)  # Minimal spacing between label and input
        start_section.setContentsMargins(0, 0, 0, 0)  # No margins
        
        start_label = QLabel("Start Date:")
        start_label.setFont(QFont("Arial", 9))
        start_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)  # Left align, center vertically
        start_label.setContentsMargins(0, 0, 0, 0)  # No margins
        start_label.setFixedHeight(16)  # Fixed height for consistent alignment
        start_section.addWidget(start_label)
        start_section.addWidget(self.start_date_entry)
        
        start_container = QWidget()
        start_container.setLayout(start_section)
        start_container.setContentsMargins(0, 0, 0, 0)  # No margins
        date_inputs_layout.addWidget(start_container)
        
        # End Date section (vertical layout) - INDENTED like in the picture
        end_section = QVBoxLayout()
        end_section.setSpacing(2)  # Minimal spacing between label and input
        end_section.setContentsMargins(0, 0, 0, 0)  # No margins
        
        end_label = QLabel("End Date:")
        end_label.setFont(QFont("Arial", 9))
        end_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)  # Left align, center vertically
        end_label.setContentsMargins(0, 0, 0, 0)  # No margins
        end_label.setFixedHeight(16)  # Fixed height for consistent alignment
        end_section.addWidget(end_label)
        end_section.addWidget(self.end_date_entry)
        
        end_container = QWidget()
        end_container.setLayout(end_section)
        end_container.setContentsMargins(0, 0, 0, 0)  # No margins
        date_inputs_layout.addWidget(end_container)
        
        date_inputs_layout.addStretch()
        
        # Date inputs container - INDENTED to match the picture layout
        date_inputs_container = QWidget()
        date_inputs_container.setLayout(date_inputs_layout)
        date_inputs_container.setContentsMargins(20, 0, 0, 0)  # LEFT INDENTATION like in the picture
        date_layout.addWidget(date_inputs_container)
        
        # Preset buttons (bigger and more readable with glass morphism styling)
        presets_layout = QGridLayout()
        presets_layout.setSpacing(5)  # Keep current spacing
        
        # First row of presets
        today_btn = QPushButton("Today")
        today_btn.clicked.connect(self.set_today)
        today_btn.setFixedSize(100, 32)  # Bigger for readability
        today_btn.setFont(QFont("Arial", 10))  # Bigger font
        today_btn.setObjectName("presetButton")  # Apply glass morphism styling
        presets_layout.addWidget(today_btn, 0, 0)
        
        yesterday_btn = QPushButton("Yesterday")
        yesterday_btn.clicked.connect(self.set_yesterday)
        yesterday_btn.setFixedSize(100, 32)
        yesterday_btn.setFont(QFont("Arial", 10))
        yesterday_btn.setObjectName("presetButton")
        presets_layout.addWidget(yesterday_btn, 0, 1)
        
        last_7_btn = QPushButton("Last 7 days")
        last_7_btn.clicked.connect(self.set_last_7_days)
        last_7_btn.setFixedSize(100, 32)
        last_7_btn.setFont(QFont("Arial", 10))
        last_7_btn.setObjectName("presetButton")
        presets_layout.addWidget(last_7_btn, 0, 2)
        
        # Second row of presets
        last_14_btn = QPushButton("Last 14 days")
        last_14_btn.clicked.connect(self.set_last_14_days)
        last_14_btn.setFixedSize(100, 32)
        last_14_btn.setFont(QFont("Arial", 10))
        last_14_btn.setObjectName("presetButton")
        presets_layout.addWidget(last_14_btn, 1, 0)
        
        last_30_btn = QPushButton("Last 30 days")
        last_30_btn.clicked.connect(self.set_last_30_days)
        last_30_btn.setFixedSize(100, 32)
        last_30_btn.setFont(QFont("Arial", 10))
        last_30_btn.setObjectName("presetButton")
        presets_layout.addWidget(last_30_btn, 1, 1)
        
        this_month_btn = QPushButton("This month")
        this_month_btn.clicked.connect(self.set_this_month)
        this_month_btn.setFixedSize(100, 32)
        this_month_btn.setFont(QFont("Arial", 10))
        this_month_btn.setObjectName("presetButton")
        presets_layout.addWidget(this_month_btn, 1, 2)
        
        presets_container = QWidget()
        presets_container.setLayout(presets_layout)
        date_layout.addWidget(presets_container)
        
        # Help text (NORMAL alignment)
        date_help = QLabel("💡 Auto-sets date filters in dashboards")
        date_help.setFont(QFont("Arial", 8))
        date_help.setObjectName("helpText")  # Let theme handle the color and style
        date_layout.addWidget(date_help)
        
        # Main layout with more space between sections - LEVEL alignment
        main_wait_date_layout = QHBoxLayout()
        main_wait_date_layout.setSpacing(30)  # More space between sections
        main_wait_date_layout.setContentsMargins(0, 0, 0, 0)  # No margins - LEVEL alignment
        main_wait_date_layout.addWidget(wait_container)
        main_wait_date_layout.addWidget(date_container)
        
        wait_date_container = QWidget()
        wait_date_container.setLayout(main_wait_date_layout)
        wait_date_container.setContentsMargins(0, 0, 0, 0)  # No margins - LEVEL alignment
        left_layout.addWidget(wait_date_container)
        
        left_layout.addStretch()
        
        # Right - Actions
        right_column = QWidget()
        right_layout = QVBoxLayout(right_column)
        right_layout.setSpacing(10)
        
        actions_label = QLabel("⚡ Actions")
        actions_label.setFont(QFont("Arial", 13, QFont.Bold))
        actions_label.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(actions_label)
        right_layout.addSpacing(15)
        
        self.scan_btn = QPushButton("🔍 Scan Page")
        self.scan_btn.setObjectName("actionButton")
        self.scan_btn.setFont(QFont("Arial", 11, QFont.Bold))
        self.scan_btn.setMinimumHeight(40)
        self.scan_btn.setFixedWidth(180)
        self.scan_btn.clicked.connect(self.scan_page)
        right_layout.addWidget(self.scan_btn)
        
        self.extract_btn = QPushButton("🚀 Extract Tables")
        self.extract_btn.setObjectName("actionButton")
        self.extract_btn.setFont(QFont("Arial", 11, QFont.Bold))
        self.extract_btn.setMinimumHeight(40)
        self.extract_btn.setFixedWidth(180)
        self.extract_btn.setEnabled(False)
        self.extract_btn.clicked.connect(self.extract_tables)
        right_layout.addWidget(self.extract_btn)
        
        open_btn = QPushButton("📁 Open Output")
        open_btn.setObjectName("actionButton")
        open_btn.setFont(QFont("Arial", 11, QFont.Bold))
        open_btn.setMinimumHeight(40)
        open_btn.setFixedWidth(180)
        open_btn.clicked.connect(self.open_output_folder)
        right_layout.addWidget(open_btn)
        
        right_layout.addStretch()
        
        settings_layout.addWidget(left_column, 1)
        settings_layout.addWidget(right_column, 0)
        
        content_layout.addWidget(settings_frame)
    
        # Progress Section
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("progressBar")
        self.progress_bar.setMinimumHeight(20)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        content_layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("Ready to scan Looker Studio dashboard")
        self.status_label.setFont(QFont("Arial", 12))
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setObjectName("statusLabel")
        content_layout.addWidget(self.status_label)
    
        # Execution Log Footer - Using the new reusable component! ✨
        try:
            from styles.components.execution_log import create_execution_log_footer
            self.execution_log = create_execution_log_footer(self, str(self.output_path))
            content_layout.addWidget(self.execution_log, 1)
            
            # Connect signals for additional functionality
            self.execution_log.log_cleared.connect(self.on_log_cleared)
            self.execution_log.log_saved.connect(self.on_log_saved)
            
        except ImportError:
            # Fallback to old log section if component not available
            log_frame = QFrame()
            log_frame.setObjectName("glassFrame")
            log_layout = QVBoxLayout(log_frame)
            log_layout.setContentsMargins(15, 10, 15, 15)
            
            log_title = QLabel("📋 Extraction Log")
            log_title.setFont(QFont("Arial", 13, QFont.Bold))
            log_layout.addWidget(log_title)
            
            self.log_text = QTextEdit()
            self.log_text.setObjectName("logText")
            self.log_text.setReadOnly(True)
            self.log_text.setMinimumHeight(200)
            self.log_text.setFont(QFont("Consolas", 9))
            log_layout.addWidget(self.log_text)
            
            content_layout.addWidget(log_frame, 1)
        
        # Set content widget to scroll area and add to main layout
        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area, 1)
    
    def log(self, message: str, level: str = "INFO"):
        """Log with timestamp and propagate to unified session log."""
        if self.log_manager:
            try:
                self.log_manager.log_event(self.log_category, message, level)
            except Exception:
                pass

        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        self.execution_log_messages.append(formatted_message)

        if self.worker and hasattr(self.worker, "execution_log"):
            self.worker.execution_log.append(formatted_message)

        if hasattr(self, 'execution_log') and hasattr(self.execution_log, 'log'):
            self.execution_log.log(message)
        elif hasattr(self, 'log_text'):
            self.log_text.append(formatted_message)
    
    def set_today(self):
        """Set date range to today only"""
        today = QDate.currentDate()
        self.end_date_entry.setDate(today)
        self.start_date_entry.setDate(today)
    
    def set_yesterday(self):
        """Set date range to yesterday only"""
        yesterday = QDate.currentDate().addDays(-1)
        self.end_date_entry.setDate(yesterday)
        self.start_date_entry.setDate(yesterday)
    
    def set_last_7_days(self):
        """Set date range to last 7 days"""
        today = QDate.currentDate()
        self.end_date_entry.setDate(today)
        self.start_date_entry.setDate(today.addDays(-7))
    
    def set_last_14_days(self):
        """Set date range to last 14 days"""
        today = QDate.currentDate()
        self.end_date_entry.setDate(today)
        self.start_date_entry.setDate(today.addDays(-14))
    
    def set_last_30_days(self):
        """Set date range to last 30 days"""
        today = QDate.currentDate()
        self.end_date_entry.setDate(today)
        self.start_date_entry.setDate(today.addDays(-30))
    
    def set_this_month(self):
        """Set date range to current month"""
        today = QDate.currentDate()
        self.end_date_entry.setDate(today)
        # First day of current month
        first_day = QDate(today.year(), today.month(), 1)
        self.start_date_entry.setDate(first_day)
    
    def on_log_cleared(self):
        """Called when execution log is cleared"""
        # Clear worker logs too if available
        if self.worker:
            self.worker.execution_log.clear()

        if self.log_manager:
            try:
                self.log_manager.log_event(self.log_category, "Execution log cleared by user.", "INFO")
            except Exception:
                pass
    
    def on_log_saved(self, file_path: str):
        """Called when execution log is saved"""
        self.show_message("Saved!", f"Log saved to:\n{file_path}", "success")
        if self.log_manager:
            try:
                self.log_manager.log_event(self.log_category, f"Execution log saved to: {file_path}", "INFO")
            except Exception:
                pass
    
    # Legacy methods for backward compatibility (will be removed in future)
    def copy_log(self):
        """Copy log - Legacy method"""
        if hasattr(self, 'execution_log') and hasattr(self.execution_log, 'copy_log'):
            self.execution_log.copy_log()
        else:
            from PySide6.QtWidgets import QApplication
            clipboard = QApplication.clipboard()
            clipboard.setText(self.log_text.toPlainText())
            self.show_message("Copied!", "Log copied to clipboard!", "success")
    
    def reset_log(self):
        """Reset log - Legacy method"""
        if hasattr(self, 'execution_log') and hasattr(self.execution_log, 'reset_log'):
            self.execution_log.reset_log()
        else:
            self.log_text.clear()
            self.execution_log_messages.clear()
            self.log("Log cleared!")
    
    def save_log(self):
        """Save log - Legacy method"""
        if hasattr(self, 'execution_log') and hasattr(self.execution_log, 'save_log'):
            self.execution_log.save_log()
        else:
            try:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                log_dir = Path(self.output_path) / "logs"
                log_dir.mkdir(parents=True, exist_ok=True)
                
                log_file = log_dir / f"looker_studio_log_{timestamp}.txt"
                with open(log_file, 'w', encoding='utf-8') as f:
                    f.write("="*80 + "\n")
                    f.write("Looker Studio Data Extractor - Log\n")
                    f.write("="*80 + "\n\n")
                    for log_entry in self.execution_log_messages:
                        f.write(f"{log_entry}\n")
                
                self.show_message("Saved!", f"Log saved to:\n{log_file}", "success")
            except Exception as e:
                self.show_message("Error", f"Failed to save log: {str(e)}", "error")
    
    def scan_page(self):
        """Scan page using QThread"""
        self.log("[SCAN] Scan button clicked!")
        
        if self.is_scanning:
            self.show_message("In Progress", "Scan already in progress!", "warning")
            return
        
        if sync_playwright is None:
            self.show_message("Missing Dependency", "Playwright not installed!\n\nRun: pip install playwright\nThen: playwright install", "error")
            return
        
        url = self.url_entry.text().strip()
        if not url:
            self.show_message("Missing URL", "Please enter a URL!", "warning")
            return
        
        if not url.startswith("http"):
            self.show_message("Invalid URL", "URL must start with http:// or https://", "warning")
            return
        
        self.log(f"[OK] Starting scan for: {url}")
        self.is_scanning = True
        self.scan_btn.setEnabled(False)
        self.scan_btn.setText("⏳ Scanning...")
        self.progress_bar.setValue(10)
        self.found_tables = []
        
        # Get date range settings
        enable_date_filter = self.enable_date_filter.isChecked()
        start_date = self.start_date_entry.date().toPython() if enable_date_filter else None
        end_date = self.end_date_entry.date().toPython() if enable_date_filter else None
        
        # Create QThread and worker (ONE thread for scan AND extraction!)
        self.log("[OK] Creating unified QThread worker...")
        self.worker_thread = QThread()
        self.worker = ScanAndExtractWorker(
            url=url,
            browser_type=self.browser_combo.currentText(),
            headless=self.headless_checkbox.isChecked(),
            wait_time=int(self.wait_time_entry.text()),
            output_path=self.output_path,
            enable_date_filter=enable_date_filter,
            start_date=start_date,
            end_date=end_date
        )
        
        # Move worker to thread
        self.worker.moveToThread(self.worker_thread)
        
        # Connect signals
        self.worker.log_signal.connect(self.log)
        self.worker.progress_signal.connect(self.progress_bar.setValue)
        self.worker.status_signal.connect(self.status_label.setText)
        self.worker.scan_complete_signal.connect(self.on_scan_complete)
        self.worker.scan_failed_signal.connect(self.on_scan_failed)
        self.worker.extraction_complete_signal.connect(self.on_extraction_complete)
        self.worker.extraction_failed_signal.connect(self.on_extraction_failed)
        
        # Connect thread lifecycle
        self.worker_thread.started.connect(self.worker.run_scan)
        self.worker_thread.finished.connect(self.on_worker_thread_finished)
        
        # Start!
        self.log("[OK] Starting unified QThread...")
        self.worker_thread.start()
    
    def on_scan_complete(self, tables):
        """Called when scan completes successfully"""
        self.found_tables = tables
        
        # Reset scan button to be reusable
        self.is_scanning = False
        self.scan_btn.setEnabled(True)
        self.scan_btn.setText("🔍 Scan Page")
        
        # Enable extract button
        self.extract_btn.setEnabled(True)
        
        self.log("[WARNING] Browser is STILL OPEN - Click 'Extract Tables' to download!")
        self.show_message("Scan Complete! 🎉", f"Found {len(tables)} table(s)!\n\nBrowser is OPEN.\n\nClick 'Extract Tables' to download CSVs.", "success")
    
    def on_scan_failed(self, error_msg):
        """Called when scan fails"""
        # Reset scan button to be reusable even after failure
        self.is_scanning = False
        self.scan_btn.setEnabled(True)
        self.scan_btn.setText("🔍 Scan Page")
        
        self.show_message("Scan Failed", f"Error: {error_msg}\n\nTry:\n• Increase wait time\n• Disable headless mode\n• Check if logged in", "warning")
    
    def on_worker_thread_finished(self):
        """Called when unified QThread finishes (after extraction)"""
        self.log("[INFO] Worker thread finished")
        
        # Only clean up worker - don't override button states
        # Button states are already set by on_extraction_complete/on_extraction_failed
        if self.worker:
            self.worker.deleteLater()
        if self.worker_thread:
            self.worker_thread.deleteLater()
    
    def extract_tables(self):
        """Trigger extraction - worker is waiting for this signal!"""
        if not self.worker or not self.worker.page:
            self.show_message("No Browser", "Please scan first!", "warning")
            return
        
        if not self.found_tables:
            self.show_message("No Tables", "No tables found!", "warning")
            return
        
        self.log("[OK] Extract button clicked!")
        self.is_extracting = True
        self.scan_btn.setEnabled(False)
        self.extract_btn.setEnabled(False)
        self.extract_btn.setText("⏳ Extracting...")
        
        # Signal the worker to continue with extraction (SAME thread!)
        self.log("Signaling worker to start extraction...")
        self.worker.trigger_extraction()
    
    def on_extraction_complete(self, tables_extracted, output_dir):
        """Called when extraction completes"""
        # Reset BOTH buttons to be reusable
        self.is_extracting = False
        self.is_scanning = False
        
        # Re-enable scan button for reuse
        self.scan_btn.setEnabled(True)
        self.scan_btn.setText("🔍 Scan Page")
        
        # Re-enable extract button for reuse
        self.extract_btn.setEnabled(True)
        self.extract_btn.setText("🚀 Extract Tables")
        
        self.show_message(
            "Extraction Complete! 🎉",
            f"Successfully extracted {tables_extracted} table(s)!\n\n"
            f"Output folder:\n{output_dir}",
            "success"
        )
    
    def on_extraction_failed(self, error_msg):
        """Called when extraction fails"""
        # Reset BOTH buttons to be reusable even after failure
        self.is_extracting = False
        self.is_scanning = False
        
        # Re-enable scan button for reuse
        self.scan_btn.setEnabled(True)
        self.scan_btn.setText("🔍 Scan Page")
        
        # Re-enable extract button for reuse
        self.extract_btn.setEnabled(True)
        self.extract_btn.setText("🚀 Extract Tables")
        
        self.show_message("Extraction Failed", f"Error: {error_msg}", "error")
    
    def closeEvent(self, event):
        """Cleanup on close"""
        if self._path_listener_registered:
            try:
                self.path_manager.unregister_listener(self._handle_paths_changed)
            except Exception:
                pass
            finally:
                self._path_listener_registered = False

        self.log("[INFO] Closing tool - cleaning up browser...")
        if self.worker:
            self.worker.close_browser()
        if self.worker_thread and self.worker_thread.isRunning():
            self.worker_thread.quit()
            self.worker_thread.wait()
        super().closeEvent(event)
    
    def show_message(self, title: str, message: str, msg_type: str = "info"):
        """Show message"""
        if msg_type == "error":
            QMessageBox.critical(self, title, message)
        elif msg_type == "warning":
            QMessageBox.warning(self, title, message)
        else:
            QMessageBox.information(self, title, message)
    
    def apply_theme(self):
        """Apply theme using NEW system! ✨"""
        if not THEME_AVAILABLE or not self.current_theme:
            return
        
        try:
            # Apply theme to this dialog window
            self.current_theme.apply_to_window(self)
            
            # Safe logging
            safe_theme_name = self.current_theme.theme_name.encode('ascii', 'ignore').decode('ascii')
            print(f"✅ [THEME] Applied to tool: {safe_theme_name}")
            
        except Exception as e:
            print(f"⚠️ [THEME] Error applying theme: {e}")
    
    def refresh_theme(self):
        """Refresh theme when user switches - Inherit from parent! ✨"""
        print(f"🔄 [THEME] refresh_theme() called!")
        
        if not THEME_AVAILABLE:
            return
        
        try:
            # Get theme from parent (main GUI)
            parent = self.parent()
            if hasattr(parent, 'current_theme') and parent.current_theme:
                self.current_theme = parent.current_theme
                safe_theme_name = self.current_theme.theme_name.encode('ascii', 'ignore').decode('ascii')
                print(f"✅ [THEME] Inherited from parent: {safe_theme_name}")
            else:
                print(f"⚠️ [THEME] Parent has no theme, keeping current")
            
            # Reapply theme
            self.apply_theme()
            
        except Exception as e:
            print(f"⚠️ [THEME] Error refreshing theme: {e}")

    def _handle_paths_changed(self, input_path: Path, output_path: Path) -> None:
        self.input_path = input_path
        self.output_path = output_path
        self._sync_path_edits(input_path, output_path)
        if hasattr(self, 'execution_log') and hasattr(self.execution_log, 'set_output_path'):
            self.execution_log.set_output_path(str(output_path))


def main():
    """Test standalone"""
    from PySide6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    class DummyParent:
        current_theme_name = "🌊 Ocean Sunset"  # Default theme for testing
    
    parent = DummyParent()
    
    tool = LookerStudioExtractorTool(
        parent,
        str(Path.home() / "Documents"),
        str(Path(__file__).parent.parent.parent / "execution_test" / "Output")
    )
    
    tool.show()
    tool.raise_()
    tool.activateWindow()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

