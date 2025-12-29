# 🌊 GA4 Script Tools Suite

A professional GUI application for data analysts with beautiful PySide6 interface, automation tools, and comprehensive logging. Perfect for GA4 data collection, Looker Studio, and more.

<img width="1198" height="801" alt="image" src="https://github.com/user-attachments/assets/06d4790e-20a6-4a00-9bba-e0a5896df83b" />

<img width="949" height="799" alt="image" src="https://github.com/user-attachments/assets/180df297-28b6-4315-9365-991b5d29d37f" />

<img width="1200" height="800" alt="image" src="https://github.com/user-attachments/assets/7e6096bc-ac26-460c-b70a-851e0271f80c" />

<img width="998" height="820" alt="image" src="https://github.com/user-attachments/assets/e6081752-d1bb-484d-ade7-50867f5766c3" />

<img width="1194" height="798" alt="image" src="https://github.com/user-attachments/assets/3140707b-782f-4c4c-bac6-d8d1bc929de6" />

## ✨ Features

- **🎨 Glass Morphism UI** - Stunning transparent effects with backdrop blur
- **🌈 10 Beautiful Themes** - Switch between Ocean Sunset, Cosmic Dreams, Forest Whisper, and more
- **📊 Data Collection Tools** - Looker Studio extraction
- **🤖 Browser Automation** - Playwright-based browser automation
- **📝 Comprehensive Logging** - Real-time execution logs with session tracking
- **🎯 Modular Architecture** - Easy to extend and customize

## 🚀 Quick Start

### Prerequisites

- **Python 3.12.x** (Required - PySide6 compatibility)
  - Download from [python.org/downloads/windows](https://www.python.org/downloads/windows/)
  - During installation, check **"Add Python to PATH"**
  - Verify installation: `python --version` (should show 3.12.x)

### Installation

1. **Create Virtual Environment** (in project root):
   ```powershell
   python -m venv venv
   ```

2. **Activate Virtual Environment**:
   ```powershell
   .\venv\Scripts\Activate.ps1
   ```
   You should see `(venv)` in your prompt.

3. **Upgrade pip**:
   ```powershell
   python -m pip install --upgrade pip
   ```

4. **Install Dependencies**:
   ```powershell
   pip install -r requirements.txt
   ```

5. **Verify Installation**:
   ```powershell
   python -m pip show PySide6
   ```
   You should see PySide6 version metadata.

### Launch

**Recommended (with console output):**
```powershell
python main.py
```

**Alternative (silent launcher):**
- Double-click `Launch_GA4_Tools.vbs`  
- Or run: `cscript Launch_GA4_Tools.vbs`

> 💡 **Note:** Always activate the virtual environment before running the application. For detailed setup instructions, see [`SETUP_GUIDE.md`](SETUP_GUIDE.md).

## 📁 Project Structure

```
GA4 Script Tools/
├── main.py                           # Main GUI application
├── styles/                           # Theme system
│   ├── theme_loader.py              # Theme loading engine
│   ├── themes/                      # 10 JSON theme files
│   ├── components/                  # Reusable UI components
│   └── animations/                  # Qt animations
├── styles/utils/path_manager.py     # Centralised input/output routing (switch-case controlled)
├── tools/                           # All tools organized by category
│   ├── data_collection_import/
│   │   └── looker_extractor.py        ✅ Implemented
│   ├── data_cleaning_transformation/
│   ├── data_merging_joining/
│   ├── file_management_organization/
│   └── ... (more categories)
├── gui_logs/                        # Session execution logs
└── execution_test/
    └── Output/                      # Tool outputs (per-tool/script/timestamp folders)
```

### Output Directory Layout (auto-managed)

```
execution_test/Output/
├── Looker_Extractor/
│   └── looker_extractor_py/
│       └── 2025-11-12_0814/
│           ├── exported_table_1.csv
│           └── logs/
├── Column_Order_Harmonizer/
│   └── 2025-11-13_1137/
│       ├── Success/
│       ├── Failed/
│       └── _harmonization_report.txt
├── Metric_Fixer/
│   └── metric_fixer_py/
│       └── 2025-11-12_0820/
├── Date_Format_Converter/
│   └── 2025-11-13_1201/
│       ├── Converted/
│       └── _date_conversion_report.csv
└── ...
```

All timestamps and subfolders are produced by `PathManager.prepare_tool_output(...)`; individual tools never manually compose paths. When inheriting `BaseToolDialog`, prefer the helper `self.allocate_run_directory(...)` to keep UI paths in sync automatically. PathManager normalises any lingering tool/timestamp suffixes from previous runs before minting a new directory, keeping the tree flat and predictable.

## 🎨 Available Tools

**Status Legend:** ✅ Complete | ✨ Beta - Optimization in Progress

See the [Tool Feature Matrix](#-tool-feature-matrix) section below for detailed information on each tool.

## 🧰 Tool Feature Matrix

**Status Legend:** ✅ Complete | ✨ Beta - Optimization in Progress

### 📥 Data Collection & Import
- **✅ `looker_extractor.py` — Looker Studio Extractor**
  - 🌐 Playwright-driven browser automation (Chromium, Firefox, WebKit) with headless toggle and graceful credential prompts.
  - 🔍 Table discovery wizard scans Looker Studio pages, previews columns, and lets analysts cherry-pick targets before export.
  - 💾 Streams multiple CSV downloads into timestamped folders, rotates outputs automatically, and persists run summaries in the execution log footer.
  - ⚙️ Runs extraction flows on background threads while syncing the shared `PathManager` output path to keep the UI responsive.
  - 📅 Supports date range filtering with preset options (Today, Last 7/14/30 days, This month, etc.)

### 🧼 Data Cleaning & Transformation
- **✅ `column_order_harmonizer.py` — Column Order Harmonizer**
  - 📁 Scans the input folder for CSVs, displaying column counts and status per file at a glance.
  - 🧭 Applies curated presets (or custom sequences) to reorder headers, strip duplicates, and append any remaining columns intelligently.
  - 🧱 Guarantees canonical GA4 ordering (and fills missing columns with blanks) before anything hits diagnostics or BigQuery.
  - 🔄 Executes harmonization in a QThread worker with live progress, status updates, and execution log streaming.
  - ✍️ Writes harmonised datasets into timestamped `Success/` folders, moves rejects to `Failed/`, and emits a `_harmonization_report.txt` with precise failure reasons.
- **✅ `find_replace.py` — BigQuery CSV Cleaner**
  - 🔎 Analyzes CSV structure, detecting numeric columns, null/empty hot spots, and BigQuery-incompatible values.
  - 🧼 Applies configurable cleaning (null handling, empty-string normalisation) alongside targeted find/replace operations.
  - 🖥️ Offers side-by-side file selection, preview statistics, and a rich log panel with copy/save shortcuts.
  - 🚀 Processes batches on a background thread, writing detailed execution logs and summaries into the output directory.
- **✅ `metric_fixer.py` — Metric Field Fixer**
  - 📊 Scans GA4 exports to detect metric columns with inconsistent blanks, "null" strings, or mis-scaled percentage values.
  - ✅ Lets analysts review findings per file, choose exactly which columns to repair, and preview replacements before committing.
  - 🔧 Generates cleaned CSVs via background workers, with live progress bars, granular logging, and success/failure counts.
  - 🛡️ Preserves originals by writing fixed files to dedicated output folders and documenting every change in the execution log.
- **✅ `metric_fixer_batch.py` — Metric Field Fixer (Batch CLI)**
  - ⚡ Schema-driven CLI that enforces GA4 metric types across entire folders without opening the GUI.
  - 🧠 Canonicalises header aliases (e.g. "Event name", `event_name`) and normalises integers, engagement percentages, and two-decimal revenue values.
  - 🧾 Emits clean CSV (and optional Parquet) plus a JSONL manifest with per-file coercion stats for auditing or GUI inspection.
  - 🔁 Supports `--resume`, worker throttling, dry runs, and schema overrides via `schemas/metric_schema_v1.yaml`.

#### Metric Fixer Batch CLI — Quick Start

Run from an activated virtual environment (Python 3.12+):

```powershell
# Smoke test (reads files, no writes)
python tools\data_cleaning_transformation\metric_fixer_batch.py `
    --input  "C:\path\to\raw_csv" `
    --output "C:\path\to\clean_outputs" `
    --schema "schemas\metric_schema_v1.yaml" `
    --dry-run --limit 5 --workers 1 --no-parquet

# Full batch run
python tools\data_cleaning_transformation\metric_fixer_batch.py `
    --input  "C:\path\to\raw_csv" `
    --output "C:\path\to\clean_outputs" `
    --schema "schemas\metric_schema_v1.yaml" `
    --workers 2
```

- Clean CSVs land in `<output>/clean_csv/`. Enable Parquet by omitting `--no-parquet`.
- Every run writes a log to `<output>/logs/metric_fixer_batch.log` and a manifest `metric_fixer_manifest_<timestamp>.jsonl`.
- Use `--resume` to skip files already processed successfully, `--only` to target specific filenames, and tune `--workers` to match machine resources.
- PyYAML is required when loading the schema (`pip install PyYAML` if it is missing).

### 📊 Data Analysis & Reporting
- **✅ `data_summary.py` — Data Summary Tool**
  - 📈 Performs per-file exploratory summaries, auto-detecting metrics such as totals, engagement rates, and user counts.
  - 🪟 Presents interactive tables, grand totals, and metric cards inside a scrollable "glass" dashboard.
  - 🔁 Runs analysis in background threads with progress tracking, cancellation safety, and PathManager-powered input sync.
  - 💾 Exports summary tables to CSV and logs each run in the Execution Log footer for auditability.

### 📁 File Management & Organization
- **✅ `file_rename.py` — File Renamer Tool**
  - 🔍 Scans folders, previews file lists, and supports multi-select with "Select All/None" shortcuts.
  - ✏️ Applies prefix/suffix patterns with live previews so renaming rules stay predictable.
  - ♻️ Generates output copies instead of destructive renames, anchoring paths through the shared PathManager.
  - 📓 Captures every action in the execution log with reset/copy/save utilities for repeatable workflows.
- **✅ `youtube_channel_folder_renamer.py` — YouTube Channel Folder Renamer**
  - 📺 Copy channel CSVs to a production-ready naming scheme.

### 🕒 Date & Time Utilities
- **✅ `tools/date_time_utilities/date_format_converter.py` — Date Format Converter (GUI)**
  - 🧠 Auto-detects date columns across hundreds of CSVs and surfaces format distribution instantly—no manual column picking required.
  - 🗂️ Clusters files by detected date format; divergent CSVs appear under their own tabs with per-format checkboxes and file-level toggles for surgical selection.
  - 🎯 Converts non-baseline formats by default; enable the baseline tab (or individual files) with a single click before launching the batch.
  - 🪄 Streams each file chunk-by-chunk (configurable chunk size) so large datasets stay under memory limits while the UI stays responsive.
  - ⚡ Respects `workers` to fan out conversion across CPU cores via the shared engine, honouring resume, dry-run, and keep-original options.
  - 📊 Surfaces live progress (success, skip, failure counts), emits detailed summaries/manifest links, and includes total-byte telemetry for auditing.
  - 📋 Conversion settings include preset pickers for both input and output formats—toggle a preset and the fields update instantly.
  - **GUI:** Launch via the suite (`Date & Time Utilities → Date Format Converter`) or run `python tools\date_time_utilities\date_format_converter.py`.

### ✅ Data Validation & Quality
- **✅ `bigquery_transfer_diagnostics.py` — BigQuery Transfer Diagnostics**
  - 🛡️ Verifies every CSV against the canonical GA4 schema, flags misordered or missing headers, and highlights numeric cast failures before upload.
  - 🔍 Reports the exact row/column causing trouble (e.g. decimals in `Engaged sessions`) with a minimalist `diagnostic_report.txt`.
  - 📊 Supports filterable result tables (pass/warn/fail) and mirrors findings into the execution log for easy auditing.

### 📊 Additional Reporting Tools
- **✅ `url_labeler.py` — URL Labeler**
  - 🌊 Scan CSV files and extract unique Topic Clusters based on URL patterns.
- **✅ `platform_source_labeler.py` — Platform Source Labeler**
  - 🌊 Scan CSV files and extract unique Platform Sources based on Session source/medium/campaign patterns.

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

All executions are logged to `gui_logs/` via the unified `LogManager`:

- **Session logs:** `gui_session_log_YYYYMMDD_HHMMSSA.txt` (entire GUI run, sequence letter resets daily)
- **Tool session logs:** `looker_studio_session_*.txt`, `file_summary_session_*.txt`, etc.
- **Output artifacts:** `execution_log.txt` (inside each run folder under `execution_test/Output`)

### Log Features
- Real-time updates in every tool footer (Copy / Reset / Save remain local-only)
- Resetting a footer never erases the session log — the unified log is append-only
- Searchable, timestamped records for workflows, theme switches, and path changes
- Error tracking with context for rapid diagnosis

## 🎯 Usage Examples

### Looker Studio Extraction

1. Open the tool
2. Enter Looker Studio report URL
3. Configure table selection
4. Click "Extract Data"
5. Review execution log for progress
6. Download extracted data

## 🛠️ Development

### Output Path Governance

Every tool that writes files **must** obtain its run directory through the central `PathManager` switch-case. This guarantees consistent namespaces, script-tagging, and harmonised subfolders (e.g. `Success/Failed` for the harmonizer).

```python
from pathlib import Path
from styles import get_path_manager

info = get_path_manager().prepare_tool_output(
    "My Tool Name",
    script_name=Path(__file__).name,
)
run_root = info["root"]
# Optional specialised folders: info.get("success"), info.get("failed"), ...
```

- **Never** hand-build timestamped folders inside tool code.
- PathManager automatically strips residual tool/timestamp folders from legacy runs—avoid resetting output paths manually.
- Always log the chosen `run_root` so downstream automations can find outputs (the helper does this by default).
- Call `_sync_path_edits(self.input_path, run_root)` (or rely on `allocate_run_directory(..., sync_paths=True)` which handles it) to keep UI fields up to date.

### Adding New Tools

Start from the template so you inherit theme + logging + path governance automatically:

```python
from pathlib import Path
from PySide6.QtWidgets import QVBoxLayout, QLabel

from tools.templates import BaseToolDialog, PathConfigMixin


class MyTool(PathConfigMixin, BaseToolDialog):
    PATH_CONFIG = {"show_input": True, "show_output": True}

    def __init__(self, parent, input_path: str, output_path: str):
        super().__init__(parent, input_path, output_path)
        self.setup_window_properties("✨ My Tool")
        self.setup_ui()
        self.apply_theme()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Your UI goes here!"))

        # Obtain a dedicated run directory for this execution
        info = self.allocate_run_directory(
            "My Tool Name",
            script_name=Path(__file__).name,
        )
        run_root = info["root"]
        # Optional specialised folders: info.get("success"), info.get("failed"), ...
```

Then add the tool to the registry in `main.py`.

## 📚 Requirements

- **Python 3.12.x** (Required - PySide6 compatibility)

See `requirements.txt` for full dependencies. Key libraries:

- **PySide6** (≥6.6.0) - Modern Qt framework for GUI
- **Pillow** (≥10.0.0) - Image processing
- **pandas** (≥2.0.0) - Data manipulation
- **PyYAML** (≥6.0.0) - YAML parsing (for metric fixer batch tool)
- **playwright** (≥1.40.0) - Browser automation

## 💡 Tips & Troubleshooting

### Setup Issues

- **Python not found?** Use `py --version` on Windows to check if Python is installed, or install Python 3.12.x from [python.org](https://www.python.org/downloads/windows/)
- **Virtual environment not activating?** Make sure you're in the project root and run `.\venv\Scripts\Activate.ps1`
- **Wrong Python version?** Use `where python` to check which Python is active. Ensure you're using Python 3.12.x
- **Package installation fails?** Make sure the virtual environment is activated (you should see `(venv)` in your prompt)
- **Need detailed setup help?** See [`SETUP_GUIDE.md`](SETUP_GUIDE.md) for comprehensive setup instructions

### Runtime Issues

- **Browser doesn't launch?**
  - Close other Chrome instances
  - Increase wait time in tool settings
  - Ensure Playwright browsers are installed: `python -m playwright install`

- **Theme issues?**
  - Restart the application
  - Check `styles/themes/` folder exists
  - Verify theme JSON files are valid

## 💙 About

Developed with attention to detail and user experience in mind. Built for data analysts who need powerful, automated tools with a beautiful interface.

*"In the depths of data, wisdom flows like tides"* 🪷

## 📄 License & Credits

Created by the development team

---

**Quick Links:**
- 📖 [`SETUP_GUIDE.md`](SETUP_GUIDE.md) - Comprehensive setup instructions
- 🔧 [`AI_AGENT_GUIDE.md`](AI_AGENT_GUIDE.md) - Technical architecture details
- 🎨 `styles/` - Theme customization
- 📝 `gui_logs/` - Execution history
