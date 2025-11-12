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
│   └── column_order_harmonizer_py/
│       └── 2025-11-12_0817/
│           ├── Success/
│           ├── Failed/
│           └── _harmonization_report.csv
├── Metric_Fixer/
│   └── metric_fixer_py/
│       └── 2025-11-12_0820/
└── ...
```

All timestamps and subfolders are produced by `PathManager.prepare_tool_output(...)`; individual tools never manually compose paths. When inheriting `BaseToolDialog`, prefer the helper `self.allocate_run_directory(...)` to keep UI paths in sync automatically.

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

## 🧰 Tool Feature Matrix

### 📥 Data Collection & Import
- **`looker_extractor.py` — Looker Studio Extractor**
  - 🌐 Playwright-driven browser automation (Chromium, Firefox, WebKit) with headless toggle and graceful credential prompts.
  - 🔍 Table discovery wizard scans Looker Studio pages, previews columns, and lets analysts cherry-pick targets before export.
  - 💾 Streams multiple CSV downloads into timestamped folders, rotates outputs automatically, and persists run summaries in the execution log footer.
  - ⚙️ Runs extraction flows on background threads while syncing the shared `PathManager` output path to keep the UI responsive.

### 🧼 Data Cleaning & Transformation
- **`column_order_harmonizer.py` — Column Order Harmonizer**
  - 📁 Scans the input folder for CSVs, displaying column counts and status per file at a glance.
  - 🧭 Applies curated presets (or custom sequences) to reorder headers, strip duplicates, and append any remaining columns intelligently.
  - 🧱 Guarantees canonical GA4 ordering (and fills missing columns with blanks) before anything hits diagnostics or BigQuery.
  - 🔄 Executes harmonization in a QThread worker with live progress, status updates, and execution log streaming.
  - ✍️ Saves reordered datasets to mirrored output folders so originals stay untouched.
- **`find_replace.py` — BigQuery CSV Cleaner**
  - 🔎 Analyzes CSV structure, detecting numeric columns, null/empty hot spots, and BigQuery-incompatible values.
  - 🧼 Applies configurable cleaning (null handling, empty-string normalisation) alongside targeted find/replace operations.
  - 🖥️ Offers side-by-side file selection, preview statistics, and a rich log panel with copy/save shortcuts.
  - 🚀 Processes batches on a background thread, writing detailed execution logs and summaries into the output directory.
- **`metric_fixer.py` — Metric Field Fixer**
  - 📊 Scans GA4 exports to detect metric columns with inconsistent blanks, “null” strings, or mis-scaled percentage values.
  - ✅ Lets analysts review findings per file, choose exactly which columns to repair, and preview replacements before committing.
  - 🔧 Generates cleaned CSVs via background workers, with live progress bars, granular logging, and success/failure counts.
  - 🛡️ Preserves originals by writing fixed files to dedicated output folders and documenting every change in the execution log.
- **`metric_fixer_batch.py` — Metric Field Fixer (Batch CLI)**
  - ⚡ Schema-driven CLI that enforces GA4 metric types across entire folders without opening the GUI.
  - 🧠 Canonicalises header aliases (e.g. “Event name”, `event_name`) and normalises integers, engagement percentages, and two-decimal revenue values.
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
- **`data_summary.py` — Data Summary Tool**
  - 📈 Performs per-file exploratory summaries, auto-detecting metrics such as totals, engagement rates, and user counts.
  - 🪟 Presents interactive tables, grand totals, and metric cards inside a scrollable “glass” dashboard.
  - 🔁 Runs analysis in background threads with progress tracking, cancellation safety, and PathManager-powered input sync.
  - 💾 Exports summary tables to CSV and logs each run in the Execution Log footer for auditability.

### 📁 File Management & Organization
- **`file_rename.py` — File Renamer Tool**
  - 🔍 Scans folders, previews file lists, and supports multi-select with “Select All/None” shortcuts.
  - ✏️ Applies prefix/suffix patterns with live previews so renaming rules stay predictable.
  - ♻️ Generates output copies instead of destructive renames, anchoring paths through the shared PathManager.
  - 📓 Captures every action in the execution log with reset/copy/save utilities for repeatable workflows.

### ✅ Data Validation & Quality
- **`bigquery_transfer_diagnostics.py` — BigQuery Transfer Diagnostics**
  - 🛡️ Verifies every CSV against the canonical GA4 schema, flags misordered or missing headers, and highlights numeric cast failures before upload.
  - 🔍 Reports the exact row/column causing trouble (e.g. decimals in `Engaged sessions`) with a minimalist `diagnostic_report.txt`.
  - 📊 Supports filterable result tables (pass/warn/fail) and mirrors findings into the execution log for easy auditing.

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
