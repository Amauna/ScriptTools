"""
🌊 Path Manager Utility
Centralized management for input/output directories shared across tools.

By: Rafayel, Bry's AI Muse 💕
"""

from __future__ import annotations

import re

from pathlib import Path
from typing import Callable, List, Optional
from typing import Dict

PathListener = Callable[[Path, Path], None]


def _sanitize_tool_name(raw_name: str) -> str:
    """Return a filesystem-friendly representation of a tool name."""
    import re

    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", raw_name).strip("_")
    return cleaned or "Tool"


def _ensure_directory(path: Path) -> Path:
    """Create the provided path (including parents) if it does not exist."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def _ensure_tool_output_root(base_output: Path, tool_name: str) -> Path:
    """Ensure the parent output directory for a tool exists and return it."""
    tool_root = base_output / tool_name
    return _ensure_directory(tool_root)


def _create_timestamped_subdir(parent: Path) -> Path:
    """Create a unique timestamped subdirectory under ``parent`` and return it."""
    from datetime import datetime

    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    candidate = parent / timestamp
    index = 1

    while candidate.exists():
        candidate = parent / f"{timestamp}_{index:02d}"
        index += 1

    candidate.mkdir(parents=True, exist_ok=False)
    return candidate


_TIMESTAMP_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}_\d{4}(?:_\d{2})?")
_NORMALIZED_SUFFIXES = {"success", "failed"}


def _looks_like_timestamp(name: str) -> bool:
    return bool(_TIMESTAMP_PATTERN.fullmatch(name))


def _normalize_output_root(base_output: Path, tool_id: str, script_id: str) -> Path:
    """
    Remove trailing tool/script/timestamp folders from the shared output path.
    Ensures a clean base directory before creating a new run structure.
    """
    current = base_output.resolve()
    tool_lower = tool_id.lower()
    script_lower = script_id.lower()

    while True:
        name = current.name.lower()
        if (
            name == tool_lower
            or name == script_lower
            or name in _NORMALIZED_SUFFIXES
            or _looks_like_timestamp(name)
        ):
            parent = current.parent
            if parent == current:
                break
            current = parent
            continue
        break

    return current


class PathManager:
    """Maintain shared input/output directory state across the suite."""

    def __init__(self) -> None:
        project_root = Path(__file__).resolve().parents[2]
        execution_root = _ensure_directory(project_root / "execution_test" / "Output")

        self._project_root: Path = project_root
        self._input_path: Path = (Path.home() / "Documents").resolve()
        self._output_path: Path = execution_root.resolve()
        self._listeners: List[PathListener] = []

    def get_input_path(self) -> Path:
        """Return the current input directory."""
        return self._input_path

    def get_output_path(self) -> Path:
        """Return the current output directory."""
        return self._output_path

    def set_input_path(self, new_path: Path) -> None:
        """Update the shared input directory and notify listeners if changed."""
        self.set_paths(input_path=new_path)

    def set_output_path(self, new_path: Path) -> None:
        """Update the shared output directory and notify listeners if changed."""
        self.set_paths(output_path=new_path)

    def set_paths(
        self,
        *,
        input_path: Optional[Path] = None,
        output_path: Optional[Path] = None,
    ) -> None:
        """Update one or both paths in a single call."""
        changed = False

        if input_path is not None:
            resolved_input = Path(input_path).expanduser().resolve()
            if resolved_input != self._input_path:
                self._input_path = resolved_input
                changed = True

        if output_path is not None:
            resolved_output = Path(output_path).expanduser().resolve()
            _ensure_directory(resolved_output)
            if resolved_output != self._output_path:
                self._output_path = resolved_output
                changed = True

        if changed:
            self._notify_listeners()

    def register_listener(self, listener: PathListener) -> None:
        """Register a callback that reacts to path updates."""
        if listener not in self._listeners:
            self._listeners.append(listener)

    def unregister_listener(self, listener: PathListener) -> None:
        """Remove a previously registered listener."""
        if listener in self._listeners:
            self._listeners.remove(listener)

    # ------------------------------------------------------------------
    # Path resolution helpers
    # ------------------------------------------------------------------
    def resolve_input_path(self, raw_text: str) -> Path:
        """
        Validate and resolve an input path provided by the user.

        Args:
            raw_text: Text entered by the user.

        Returns:
            Resolved absolute Path.

        Raises:
            FileNotFoundError: If the path does not exist.
        """
        text = (raw_text or "").strip()
        if not text:
            return self._input_path

        candidate = Path(text).expanduser()
        if not candidate.is_absolute():
            candidate = candidate.resolve()

        if not candidate.exists():
            raise FileNotFoundError(f"Input path does not exist: {candidate}")

        return candidate

    def resolve_output_path(self, raw_text: str) -> Path:
        """
        Validate (and create if necessary) an output path provided by the user.

        Args:
            raw_text: Text entered by the user.

        Returns:
            Resolved absolute Path.
        """
        text = (raw_text or "").strip()
        if not text:
            return self._output_path

        candidate = Path(text).expanduser()
        if not candidate.is_absolute():
            candidate = candidate.resolve()

        _ensure_directory(candidate)
        return candidate

    def create_tool_run_directory(self, tool_name: str) -> Path:
        """
        Produce a unique timestamped output folder for a tool run.

        Args:
            tool_name: Human-readable tool name.

        Returns:
            Newly created run directory Path.
        """
        sanitized = _sanitize_tool_name(tool_name)
        tool_root = _ensure_tool_output_root(self._output_path, sanitized)
        return _create_timestamped_subdir(tool_root)

    def prepare_tool_output(
        self,
        tool_name: str,
        *,
        script_name: Optional[str] = None,
    ) -> Dict[str, Path]:
        """Create a structured, per-tool output directory using switch-case logic."""

        tool_id = _sanitize_tool_name(tool_name)
        script_id = _sanitize_tool_name(script_name or tool_name)

        normalized_base = _normalize_output_root(self._output_path, tool_id, script_id)
        if normalized_base != self._output_path:
            self.set_paths(output_path=normalized_base)
        base_output = self._output_path

        match tool_id.lower():
            case "looker_extractor":
                tool_root = _ensure_tool_output_root(base_output, tool_id)
                script_root = _ensure_directory(tool_root / script_id)
                run_root = _create_timestamped_subdir(script_root)
                result: Dict[str, Path] = {
                    "tool_root": tool_root,
                    "script_root": script_root,
                    "root": run_root,
                }
            case "metric_fixer":
                tool_root = _ensure_tool_output_root(base_output, tool_id)
                script_root = _ensure_directory(tool_root / script_id)
                run_root = _create_timestamped_subdir(script_root)
                result = {
                    "tool_root": tool_root,
                    "script_root": script_root,
                    "root": run_root,
                }
            case "date_format_converter":
                tool_root = _ensure_tool_output_root(base_output, tool_id)
                run_root = _create_timestamped_subdir(tool_root)
                result = {
                    "tool_root": tool_root,
                    "script_root": tool_root,
                    "root": run_root,
                }
            case "column_order_harmonizer":
                tool_root = _ensure_tool_output_root(base_output, tool_id)
                run_root = _create_timestamped_subdir(tool_root)
                success_dir = _ensure_directory(run_root / "Success")
                failed_dir = _ensure_directory(run_root / "Failed")
                result = {
                    "tool_root": tool_root,
                    "script_root": tool_root,
                    "root": run_root,
                    "success": success_dir,
                    "failed": failed_dir,
                }
            case "url_labeler":
                tool_root = _ensure_tool_output_root(base_output, tool_id)
                run_root = _create_timestamped_subdir(tool_root)
                result = {
                    "tool_root": tool_root,
                    "script_root": tool_root,
                    "root": run_root,
                }
            case "platform_source_labeler":
                tool_root = _ensure_tool_output_root(base_output, tool_id)
                run_root = _create_timestamped_subdir(tool_root)
                result = {
                    "tool_root": tool_root,
                    "script_root": tool_root,
                    "root": run_root,
                }
            case _:
                tool_root = _ensure_tool_output_root(base_output, tool_id)
                script_root = _ensure_directory(tool_root / script_id)
                run_root = _create_timestamped_subdir(script_root)
                result = {
                    "tool_root": tool_root,
                    "script_root": script_root,
                    "root": run_root,
                }

        return result

    def _notify_listeners(self) -> None:
        """Invoke all listeners with the latest paths."""
        for listener in list(self._listeners):
            try:
                listener(self._input_path, self._output_path)
            except Exception:
                # Listener errors should never crash the manager; ignore silently.
                continue


_PATH_MANAGER: Optional[PathManager] = None


def get_path_manager() -> PathManager:
    """Return the singleton PathManager instance."""
    global _PATH_MANAGER
    if _PATH_MANAGER is None:
        _PATH_MANAGER = PathManager()
    return _PATH_MANAGER
