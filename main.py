"""
SC Nexus — application entry point.

Sets up multiprocessing freeze support (required for PyInstaller + multiprocessing),
configures Windows DPI awareness, then launches the Qt application.
"""

from __future__ import annotations

import multiprocessing
import sys
import traceback
from pathlib import Path


def _setup_crash_log() -> None:
    """Route unhandled exceptions to user_data/crash.log (no console with pythonw)."""
    log_path = Path(__file__).parent / "user_data" / "crash.log"

    def _excepthook(exc_type, exc_value, exc_tb):
        try:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with log_path.open("a", encoding="utf-8") as f:
                import datetime
                f.write(f"\n{'='*60}\n{datetime.datetime.now()}\n")
                traceback.print_exception(exc_type, exc_value, exc_tb, file=f)
        except Exception:
            pass
        # Also try to show a Qt message box if Qt is running
        try:
            from PySide6.QtWidgets import QApplication, QMessageBox
            app = QApplication.instance()
            if app:
                msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
                box = QMessageBox()
                box.setWindowTitle("SC Nexus — Unhandled Error")
                box.setText(f"An unexpected error occurred:\n\n{msg[:1200]}")
                box.setIcon(QMessageBox.Icon.Critical)
                box.exec()
        except Exception:
            pass

    sys.excepthook = _excepthook


def _set_dpi_awareness() -> None:
    """Enable Per-Monitor v2 DPI awareness on Windows (no-op on other OS)."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = -4
        ctypes.windll.user32.SetProcessDpiAwarenessContext(-4)
    except Exception:
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
        except Exception:
            pass


def main() -> None:
    _set_dpi_awareness()

    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QFont

    from src.core.app import SCNexusApp
    from src.launchpad.window import LaunchpadWindow

    app = SCNexusApp(sys.argv)
    app.setApplicationName("SC Nexus")
    app.setApplicationVersion("2.0.0")
    # AA_UseHighDpiPixmaps is enabled by default in PySide6 6.0+ — no-op call suppressed

    # Default font — clean sans-serif
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    window = LaunchpadWindow(app)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    multiprocessing.freeze_support()
    _setup_crash_log()
    main()
