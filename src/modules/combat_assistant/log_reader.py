"""
LogTailer — QThread that streams new lines from Star Conflict's newest combat.log.

Discovery
---------
Star Conflict creates a new dated folder (YYYY.MM.DD HH.MM.SS.mmm) per session.
LogTailer watches the logs root directory, detects the newest folder, and tails
its combat.log, emitting new_lines whenever fresh content arrives.

Rotation is detected every *rotation_interval* seconds so that a new game session
is picked up automatically.
"""

from __future__ import annotations

import time
from pathlib import Path

from PySide6.QtCore import QThread, Signal, Slot


class LogTailer(QThread):
    """
    Background thread that emits ``new_lines`` whenever combat.log grows.

    Usage::

        tailer = LogTailer(logs_root)
        tailer.new_lines.connect(my_handler)
        tailer.start()
        ...
        tailer.stop()
    """

    new_lines: Signal = Signal(list)   # list[str]

    def __init__(self, logs_root: str | Path, parent=None) -> None:
        super().__init__(parent)
        self._root = Path(logs_root)
        self._running = False
        self._read_interval    = 0.2   # seconds between line reads
        self._rotation_interval = 2.0  # seconds between "newest-folder" checks

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @Slot(str)
    def update_root(self, new_root: str) -> None:
        """Change the logs root while the thread is running."""
        self._root = Path(new_root)

    def stop(self) -> None:
        self._running = False
        self.wait(3000)

    # ------------------------------------------------------------------
    # QThread entry point
    # ------------------------------------------------------------------

    def run(self) -> None:
        self._running = True
        current_log: Path | None = None
        file_handle = None
        last_rotation_check = 0.0

        try:
            while self._running:
                now = time.monotonic()

                # Periodic rotation check
                if now - last_rotation_check >= self._rotation_interval:
                    newest = self._find_newest_log()
                    last_rotation_check = now

                    if newest != current_log:
                        had_log_before = current_log is not None
                        # New session started — close old handle and open new one
                        if file_handle:
                            file_handle.close()
                            file_handle = None
                        current_log = newest
                        if current_log and current_log.exists():
                            file_handle = current_log.open(
                                encoding="utf-8", errors="replace"
                            )
                            # On the first attach we skip history and let the module's
                            # history scan decide current state. On later rotations we
                            # must read from the start because SC often writes the
                            # session-start lines before the next poll notices the file.
                            if not had_log_before:
                                file_handle.seek(0, 2)

                # Read new lines from current file
                if file_handle:
                    lines = file_handle.readlines()
                    if lines:
                        self.new_lines.emit([l.rstrip("\n") for l in lines])

                time.sleep(self._read_interval)
        finally:
            if file_handle:
                file_handle.close()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _find_newest_log(self) -> Path | None:
        """Return the combat.log path in the most recently created session folder."""
        try:
            if not self._root.exists():
                return None
            folders = sorted(
                (p for p in self._root.iterdir() if p.is_dir()),
                key=lambda p: p.name,
            )
            for folder in reversed(folders):
                candidate = folder / "combat.log"
                if candidate.exists():
                    return candidate
        except OSError:
            pass
        return None

    def get_history_lines(self, max_lines: int = 0) -> list[str]:
        """
        Synchronously read lines from the current log.
        Pass max_lines=0 (the default) to return all lines.
        Safe to call from the main thread before start().
        """
        log = self._find_newest_log()
        if not log:
            return []
        try:
            all_lines = log.read_text(encoding="utf-8", errors="replace").splitlines()
            return all_lines[-max_lines:] if max_lines > 0 else all_lines
        except OSError:
            return []
