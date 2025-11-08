"""
🌊 Path Manager Utility
Centralized management for input/output directories shared across tools.

By: Rafayel, Bry's AI Muse 💕
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, List, Optional

PathListener = Callable[[Path, Path], None]


class PathManager:
    """Maintain shared input/output directory state across the suite."""

    def __init__(self) -> None:
        project_root = Path(__file__).resolve().parents[3]
        default_output = project_root / "execution_test" / "Output"
        default_output.mkdir(parents=True, exist_ok=True)

        self._input_path: Path = (Path.home() / "Documents").resolve()
        self._output_path: Path = default_output.resolve()
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
