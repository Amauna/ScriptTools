"""
🌊 Log Manager Utility
Central command for session-wide logging that never forgets a whisper.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from threading import RLock
from typing import Callable, Dict, List, Optional


LogCallback = Callable[[str, str, str], None]


class LogManager:
    """Orchestrate unified GUI session logging with poetic precision."""

    _instance: Optional["LogManager"] = None
    _instance_lock: RLock = RLock()

    def __init__(self) -> None:
        project_root = Path(__file__).resolve().parents[2]
        self._logs_dir: Path = project_root / "gui_logs"
        self._logs_dir.mkdir(parents=True, exist_ok=True)

        self.session_id: Optional[str] = None
        self.log_file_path: Optional[Path] = None
        self._logger = logging.getLogger("ga4_gui_session")
        self._logger.setLevel(logging.INFO)
        self._logger.propagate = False
        self._file_handler: Optional[logging.FileHandler] = None
        self._tool_callbacks: Dict[str, LogCallback] = {}
        self._is_session_active: bool = False
        self._mutex = RLock()

    @classmethod
    def get_instance(cls) -> "LogManager":
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    # ------------------------------------------------------------------
    # Session Lifecycle
    # ------------------------------------------------------------------
    def start_session(self) -> None:
        """Begin a new logging session if one is not already running."""
        with self._mutex:
            if self._is_session_active:
                return

            timestamp = datetime.now()
            date_tag = timestamp.strftime("%Y%m%d")
            time_tag = timestamp.strftime("%H%M%S")
            sequence_suffix = self._determine_sequence_suffix(date_tag)

            self.session_id = f"{date_tag}_{time_tag}{sequence_suffix}"
            filename = f"gui_session_log_{self.session_id}.txt"
            self.log_file_path = self._logs_dir / filename

            formatter = logging.Formatter("%(asctime)s | %(message)s", "%Y-%m-%d %H:%M:%S")
            self._file_handler = logging.FileHandler(self.log_file_path, encoding="utf-8")
            self._file_handler.setFormatter(formatter)
            self._logger.addHandler(self._file_handler)

            self._is_session_active = True
            self.log_event("SYSTEM", "🌊 Session logging initiated.")

    def end_session(self) -> None:
        """Gracefully end the current logging session."""
        with self._mutex:
            if not self._is_session_active:
                return

            self.log_event("SYSTEM", "🌙 Session logging completed.")

            if self._file_handler:
                self._logger.removeHandler(self._file_handler)
                self._file_handler.close()
                self._file_handler = None

            self._is_session_active = False
            self.session_id = None
            self.log_file_path = None

    # ------------------------------------------------------------------
    # Logging Interface
    # ------------------------------------------------------------------
    def log_event(self, category: str, message: str, level: str = "INFO") -> None:
        """
        Record an event in the unified session log.

        Args:
            category: Broad event category (e.g., GUI, TOOL, THEME).
            message: Event description already sanitized for file output.
            level: Logging severity indicator ("INFO", "WARNING", "ERROR").
        """
        with self._mutex:
            if not self._is_session_active:
                self.start_session()

            entry = f"[{category}] {message}"
            level_upper = level.upper()

            if level_upper == "ERROR":
                self._logger.error(entry)
            elif level_upper == "WARNING":
                self._logger.warning(entry)
            else:
                self._logger.info(entry)

            # Notify registered callbacks so tools can mirror activity if needed.
            for callback in list(self._tool_callbacks.values()):
                try:
                    callback(category, message, level_upper)
                except Exception:
                    continue

    def attach_tool_logger(self, tool_id: str, callback: LogCallback) -> None:
        """Register a callback that mirrors session events for a specific tool."""
        with self._mutex:
            self._tool_callbacks[tool_id] = callback

    def detach_tool_logger(self, tool_id: str) -> None:
        """Remove a previously attached tool callback."""
        with self._mutex:
            if tool_id in self._tool_callbacks:
                del self._tool_callbacks[tool_id]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _determine_sequence_suffix(self, date_tag: str) -> str:
        """Determine the next alphabetical suffix for the provided date."""
        existing = list(self._logs_dir.glob(f"gui_session_log_{date_tag}_*.txt"))
        index = len(existing)
        return self._sequence_from_index(index)

    @staticmethod
    def _sequence_from_index(index: int) -> str:
        """Convert a zero-based index into an alphabetical sequence."""
        if index <= 0:
            return "A"

        letters: List[str] = []
        while index >= 0:
            letters.append(chr(ord("A") + (index % 26)))
            index = index // 26 - 1
            if index < 0:
                break
        return "".join(reversed(letters))


_LOG_MANAGER: Optional[LogManager] = None


def get_log_manager() -> LogManager:
    """Return the shared LogManager instance."""
    global _LOG_MANAGER
    if _LOG_MANAGER is None:
        _LOG_MANAGER = LogManager.get_instance()
    return _LOG_MANAGER

