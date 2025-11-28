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
                "session default channel group": "Session default channel grouping",
                "Session default channel Group": "Session default channel grouping",
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
