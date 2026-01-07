import time
import os
import threading
from pathlib import Path
from typing import Callable, List, Optional
from datetime import datetime

class LogTailer:
    """
    Watches the logs directory for the newest 'combat.log' and streams new lines.
    Handles log rotation (new game session starting).
    """
    def __init__(self, logs_root: str, callback: Callable[[List[str]], None], check_interval_ms: int = 200):
        self.logs_root = Path(logs_root)
        self.callback = callback
        self.interval = check_interval_ms / 1000.0
        self.running = False
        self.current_file: Optional[Path] = None
        self.line_count = 0
        self._file_handle = None
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._last_rotation_check = 0
        self.ROTATION_CHECK_INTERVAL = 2.0  # Check for new folders every 2 seconds

    def start(self):
        if self.running:
            return
        self.running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True, name="LogTailerThread")
        self._thread.start()

    def stop(self):
        self.running = False
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self._close_file()

    def update_root(self, new_root: str):
        self.logs_root = Path(new_root)

    def _loop(self):
        while not self._stop_event.is_set():
            now = time.time()
            
            # Check for new log file (rotation)
            if now - self._last_rotation_check > self.ROTATION_CHECK_INTERVAL:
                self._check_for_newest_log()
                self._last_rotation_check = now

            # Read new lines if we have a file
            if self._file_handle:
                lines = self._read_new_lines()
                if lines:
                    try:
                        self.callback(lines)
                    except Exception:
                        pass # avoid crashing thread if callback fails

            time.sleep(self.interval)

    def _check_for_newest_log(self):
        """Find the folder with the latest timestamp name and open its combat.log"""
        if not self.logs_root.exists():
            return

        # Folders are named like YYYY.MM.DD HH.MM.SS.mmm usually
        # We look for folders containing combat.log
        candidates = []
        try:
            for child in self.logs_root.iterdir():
                if child.is_dir() and (child / "combat.log").exists():
                    candidates.append(child)
        except OSError:
            return

        if not candidates:
            return

        # Sort by name (which acts as timestamp sort) 
        # or mtime if names aren't reliable. SC logs usually sortable by name.
        candidates.sort(key=lambda p: p.name, reverse=True)
        newest_folder = candidates[0]
        target_log = newest_folder / "combat.log"

        if self.current_file != target_log:
            # Rotation detected
            self._switch_to_file(target_log)

    def _switch_to_file(self, path: Path):
        self._close_file()
        try:
            self.current_file = path
            
            # Count existing lines
            try:
                with open(path, "rb") as f:
                    self.line_count = sum(1 for _ in f)
            except Exception:
                self.line_count = 0

            self._file_handle = open(path, "r", encoding="utf-8", errors="ignore")
            # Seek to end immediately so we don't parse old history on startup
            self._file_handle.seek(0, 2) 
        except Exception as e:
            print(f"LogTailer error opening {path}: {e}")
            self.current_file = None

    def _close_file(self):
        if self._file_handle:
            try:
                self._file_handle.close()
            except Exception:
                pass
            self._file_handle = None

    def _read_new_lines(self) -> List[str]:
        if not self._file_handle:
            return []
        
        lines = []
        try:
            # Read all available
            while True:
                line = self._file_handle.readline()
                if not line:
                    break
                lines.append(line)
            
            self.line_count += len(lines)
        except Exception:
            pass
        return lines
