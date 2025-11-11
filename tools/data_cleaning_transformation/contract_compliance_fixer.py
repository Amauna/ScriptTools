"""
🛡️ Contract Compliance Fixer

Automatically applies safe, pre-defined corrections to CSV files flagged in the
harmonization failure report, then emits a summary of what was fixed.
"""

from __future__ import annotations

import csv
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import pandas as pd


@dataclass
class FixConfig:
    header_rename_map: Dict[str, str]
    duplicate_resolution: str  # "keep_first" or "keep_last"
    date_columns: List[str]
    date_input_formats: List[str]
    date_output_format: str


@dataclass
class FixResult:
    file_name: str
    status: str
    changes: List[str]
    error: Optional[str] = None


class ContractComplianceFixer:
    """
    Utility class for enforcing the harmonizer's contract prior to validation.

    Usage:
        fixer = ContractComplianceFixer()
        results = fixer.run(report_path="path/to/_harmonization_report.csv")
    """

    def __init__(
        self,
        harmonized_folder: Optional[Path] = None,
        config: Optional[FixConfig] = None,
    ) -> None:
        self.harmonized_folder = harmonized_folder or Path("harmonized")
        self.config = config or self._default_config()

    def _default_config(self) -> FixConfig:
        return FixConfig(
            header_rename_map={
                "Session default channel group": "Session default channel grouping",
                "session default channel grouping": "Session default channel grouping",
            },
            duplicate_resolution="keep_first",
            date_columns=["Date"],
            date_input_formats=[
                "%d-%b-%y",
                "%d-%b-%Y",
                "%m/%d/%Y",
                "%d/%m/%Y",
            ],
            date_output_format="%Y-%m-%d",
        )

    def run(self, report_path: Path) -> List[FixResult]:
        if not report_path.exists():
            raise FileNotFoundError(f"Report file not found: {report_path}")

        failures = self._parse_failure_report(report_path)
        results: List[FixResult] = []

        for failure in failures:
            file_path = self.harmonized_folder / failure["file"]
            if not file_path.exists():
                results.append(
                    FixResult(
                        file_name=failure["file"],
                        status="skipped",
                        changes=[],
                        error="File not found",
                    )
                )
                continue

            try:
                changes = self._apply_fixes(file_path, failure["reason"])
                results.append(
                    FixResult(
                        file_name=failure["file"],
                        status="fixed" if changes else "no_changes_needed",
                        changes=changes,
                    )
                )
            except Exception as exc:  # pragma: no cover - defensive guard
                results.append(
                    FixResult(
                        file_name=failure["file"],
                        status="error",
                        changes=[],
                        error=str(exc),
                    )
                )

        self._write_summary(results)
        return results

    def _parse_failure_report(self, report_path: Path) -> List[Dict[str, str]]:
        failures: List[Dict[str, str]] = []
        with report_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.reader(handle)
            next(reader, None)  # Skip header
            for row in reader:
                if not row:
                    continue
                file_name = row[0].strip()
                reason = row[1].strip() if len(row) > 1 else ""
                failures.append({"file": file_name, "reason": reason})
        return failures

    def _apply_fixes(self, file_path: Path, reason: str) -> List[str]:
        df = pd.read_csv(file_path, dtype=str, keep_default_na=False)
        changes: List[str] = []

        header_changes = self._fix_headers(df)
        if header_changes:
            changes.extend(header_changes)

        duplicate_changes = self._fix_duplicate_columns(df, reason)
        if duplicate_changes:
            changes.extend(duplicate_changes)

        date_changes = self._fix_dates(df)
        if date_changes:
            changes.extend(date_changes)

        if changes:
            df.to_csv(file_path, index=False, encoding="utf-8-sig")

        return changes

    def _fix_headers(self, df: pd.DataFrame) -> List[str]:
        changes: List[str] = []
        rename_map = {}

        for current_name in df.columns:
            normalized = current_name.strip()
            if normalized in self.config.header_rename_map:
                rename_map[current_name] = self.config.header_rename_map[normalized]

        if rename_map:
            df.rename(columns=rename_map, inplace=True)
            for old, new in rename_map.items():
                changes.append(f"Renamed column '{old}' to '{new}'")

        return changes

    def _fix_duplicate_columns(self, df: pd.DataFrame, reason: str) -> List[str]:
        if "Ambiguous" not in reason:
            return []

        normalized_map: Dict[str, List[str]] = {}
        for col in df.columns:
            normalized_map.setdefault(col.strip().lower(), []).append(col)

        changes: List[str] = []
        for normalized, columns in normalized_map.items():
            if len(columns) <= 1:
                continue

            if self.config.duplicate_resolution == "keep_first":
                to_keep = columns[0]
                to_drop = columns[1:]
            else:
                to_keep = columns[-1]
                to_drop = columns[:-1]

            df.drop(columns=to_drop, inplace=True)
            changes.append(
                f"Dropped duplicate column(s) {to_drop} (kept '{to_keep}') for '{normalized}'"
            )

        return changes

    def _fix_dates(self, df: pd.DataFrame) -> List[str]:
        changes: List[str] = []
        for column in self.config.date_columns:
            if column not in df.columns:
                continue

            original_series = df[column].copy()
            df[column] = df[column].apply(self._normalize_date)

            if not original_series.equals(df[column]):
                changes.append(f"Normalized date format in '{column}'")

        return changes

    def _normalize_date(self, value: str) -> str:
        value = value.strip()
        if not value:
            return value

        for fmt in self.config.date_input_formats:
            try:
                dt = datetime.strptime(value, fmt)
                return dt.strftime(self.config.date_output_format)
            except ValueError:
                continue
        return value

    def _write_summary(self, results: Iterable[FixResult]) -> None:
        report_path = self.harmonized_folder / "contract_compliance_report.csv"
        with report_path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["Filename", "Status", "Changes", "Error"])
            for result in results:
                writer.writerow(
                    [
                        result.file_name,
                        result.status,
                        " | ".join(result.changes),
                        result.error or "",
                    ]
                )


def main(argv: List[str]) -> None:
    if len(argv) < 2:
        print("Usage: python contract_compliance_fixer.py <harmonization_report.csv>")
        raise SystemExit(1)

    report_path = Path(argv[1])
    fixer = ContractComplianceFixer()
    results = fixer.run(report_path)

    print("Contract compliance fixer completed.")
    for result in results:
        if result.status == "error":
            print(f"[ERROR] {result.file_name}: {result.error}")
        elif result.status == "fixed":
            print(f"[FIXED] {result.file_name}: {', '.join(result.changes)}")
        elif result.status == "no_changes_needed":
            print(f"[OK] {result.file_name}: no changes needed.")
        else:
            print(f"[SKIPPED] {result.file_name}: {result.error or 'Unknown reason'}")


if __name__ == "__main__":  # pragma: no cover - manual execution only
    main(sys.argv)
"""
🩺 Contract Compliance Fixer
Automates safe, auditable corrections for CSV files flagged by the Column Order Harmonizer.
"""

from __future__ import annotations

import csv
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import pandas as pd

DEFAULT_HEADER_RENAMES: Dict[str, str] = {
    "Session default channel group": "Session default channel grouping",
    "session default channel group": "Session default channel grouping",
    "Session default channel Group": "Session default channel grouping",
}

DEFAULT_DATE_COLUMNS = ["Date"]
DEFAULT_DATE_PATTERNS = ["%Y-%m-%d", "%d-%b-%y", "%m/%d/%Y", "%d/%m/%Y"]
DEFAULT_BATCH_SIZE = 50

@dataclass
class FixSummary:
    file: str
    status: str
    issues_detected: List[str] = field(default_factory=list)
    fixes_applied: List[str] = field(default_factory=list)

@dataclass
class ComplianceConfig:
    header_renames: Dict[str, str] = field(default_factory=lambda: DEFAULT_HEADER_RENAMES.copy())
    date_columns: List[str] = field(default_factory=lambda: DEFAULT_DATE_COLUMNS[:])
    date_patterns: List[str] = field(default_factory=lambda: DEFAULT_DATE_PATTERNS[:])
    preserve_original: bool = True
    backup_suffix: str = ".bak"

class ContractComplianceFixer:
    REPORT_FILENAME = "_harmonization_report.csv"
    FIX_REPORT_FILENAME = "_contract_compliance_report.csv"

    def __init__(
        self,
        harmonized_dir: Path,
        report_path: Optional[Path] = None,
        config: Optional[ComplianceConfig] = None,
    ) -> None:
        self.harmonized_dir = Path(harmonized_dir)
        self.report_path = report_path or (self.harmonized_dir / self.REPORT_FILENAME)
        self.config = config or ComplianceConfig()
        self.logger = logging.getLogger(self.__class__.__name__)

    # --- Public API -----------------------------------------------------------------
    def run(self) -> Path:
        entries = self._read_failure_report()
        summaries: List[FixSummary] = []

        for entry in entries:
            file_name, reason = entry
            csv_path = self.harmonized_dir / file_name
            summary = FixSummary(file=file_name, status="skipped")
            summary.issues_detected.append(reason)

            if not csv_path.exists():
                summary.status = "missing"
                summary.fixes_applied.append("File not found")
                summaries.append(summary)
                continue

            try:
                if self.config.preserve_original:
                    self._create_backup(csv_path)

                df = pd.read_csv(csv_path, dtype=str, keep_default_na=False)
                fixes: List[str] = []

                if "Missing" in reason or "FAILED" in reason:
                    fixes.extend(self._apply_header_renames(df))

                if "Ambiguous" in reason:
                    fixes.extend(self._resolve_duplicate_headers(df))

                if any(keyword in reason.lower() for keyword in ["date", "format"]):
                    fixes.extend(self._normalize_dates(df))

                df.to_csv(csv_path, index=False, encoding="utf-8-sig")
                summary.status = "fixed"
                summary.fixes_applied.extend(fixes)
            except Exception as exc:
                summary.status = "error"
                summary.fixes_applied.append(str(exc))
                self.logger.exception("Failed to fix %s", file_name)

            summaries.append(summary)

        return self._write_fix_report(summaries)

    # --- Internal helpers -----------------------------------------------------------
    def _read_failure_report(self) -> List[tuple[str, str]]:
        if not self.report_path.exists():
            raise FileNotFoundError(
                f"Failure report not found at {self.report_path}. Run the harmonizer first."
            )

        entries: List[tuple[str, str]] = []
        with self.report_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.reader(handle)
            next(reader, None)
            for row in reader:
                if len(row) >= 2:
                    entries.append((row[0], row[1]))
        return entries

    def _create_backup(self, csv_path: Path) -> None:
        backup_path = csv_path.with_suffix(csv_path.suffix + self.config.backup_suffix)
        if not backup_path.exists():
            backup_path.write_bytes(csv_path.read_bytes())

    def _apply_header_renames(self, df: pd.DataFrame) -> List[str]:
        fixes: List[str] = []
        rename_map = {
            col: self.config.header_renames[col]
            for col in df.columns
            if col in self.config.header_renames
        }
        if rename_map:
            df.rename(columns=rename_map, inplace=True)
            for source, target in rename_map.items():
                fixes.append(f"Renamed column '{source}' -> '{target}'")
        return fixes

    def _resolve_duplicate_headers(self, df: pd.DataFrame) -> List[str]:
        fixes: List[str] = []
        normalized_seen: Dict[str, str] = {}
        columns_to_drop: List[str] = []

        for col in df.columns:
            normalized = col.strip().lower()
            if normalized in normalized_seen:
                columns_to_drop.append(col)
            else:
                normalized_seen[normalized] = col

        if columns_to_drop:
            df.drop(columns=columns_to_drop, inplace=True)
            for col in columns_to_drop:
                fixes.append(f"Dropped duplicate column '{col}'")
        return fixes

    def _normalize_dates(self, df: pd.DataFrame) -> List[str]:
        fixes: List[str] = []
        for col in self.config.date_columns:
            if col not in df.columns:
                continue
            try:
                df[col] = df[col].apply(self._parse_date)
                fixes.append(f"Normalized date column '{col}'")
            except Exception:
                fixes.append(f"Failed to normalize date column '{col}'")
        return fixes

    def _parse_date(self, value: str) -> str:
        value = (value or "").strip()
        if not value:
            return value
        for pattern in self.config.date_patterns:
            try:
                return datetime.strptime(value, pattern).strftime("%Y-%m-%d")
            except ValueError:
                continue
        return value

    def _write_fix_report(self, summaries: Iterable[FixSummary]) -> Path:
        report_path = self.harmonized_dir / self.FIX_REPORT_FILENAME
        with report_path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["file", "status", "issues_detected", "fixes_applied"])
            for summary in summaries:
                writer.writerow(
                    [
                        summary.file,
                        summary.status,
                        "; ".join(summary.issues_detected),
                        "; ".join(summary.fixes_applied),
                    ]
                )
        return report_path

if __name__ == "__main__":
    harmonized_path = Path("harmonized")
    fixer = ContractComplianceFixer(harmonized_path)
    report = fixer.run()
    print(f"Contract compliance report written to: {report}")
