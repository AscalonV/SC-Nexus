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


def _check_admin_relaunch() -> None:
    """If self-torp is persisted-enabled and we are not admin, trigger UAC before Qt loads.

    This prevents the program from fully initialising twice (once without admin,
    once again after the elevated relaunch).  If the user denies/cancels the prompt
    we write enabled=False so that SelfTorpModule.initialize() will not ask again.
    """
    if sys.platform != "win32":
        return
    try:
        import ctypes as _ct
        if _ct.windll.shell32.IsUserAnAdmin():
            return  # already elevated – nothing to do
    except Exception:
        return

    import json as _json
    settings_path = Path(__file__).parent / "user_data" / "self_torp_settings.json"
    try:
        if not settings_path.exists():
            return
        data = _json.loads(settings_path.read_text(encoding="utf-8"))
        if not data.get("enabled", False):
            return
    except Exception:
        return

    # Self-torp is enabled but not elevated — ask for UAC right now.
    import subprocess as _sp
    args = _sp.list2cmdline(sys.argv)
    result = _ct.windll.shell32.ShellExecuteW(None, "runas", sys.executable, args, None, 1)
    if result > 32:
        sys.exit(0)  # elevated copy is launching; exit the non-elevated one

    # UAC was denied / cancelled — turn self-torp off so initialize() won't ask again.
    try:
        data["enabled"] = False
        settings_path.write_text(_json.dumps(data, indent=2), encoding="utf-8")
    except Exception:
        pass


def main() -> None:
    _check_admin_relaunch()
    _set_dpi_awareness()

    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QFont

    from src.core.app import SCNexusApp
    from src.launchpad.splash import run_splash_process
    from src.launchpad.window import LaunchpadWindow

    # Start the animated splash in its own OS process so its 25 fps timer
    # can never be starved by anything the main process does during loading.
    ready_event = multiprocessing.Event()
    splash_proc: multiprocessing.Process | None = None
    try:
        splash_proc = multiprocessing.Process(
            target=run_splash_process,
            args=(ready_event,),
            daemon=True,
        )
        splash_proc.start()
    except Exception:
        splash_proc = None

    app = SCNexusApp(sys.argv)
    app.setApplicationName("SC Nexus")
    app.setApplicationVersion("2.0.0")
    # AA_UseHighDpiPixmaps is enabled by default in PySide6 6.0+ — no-op call suppressed

    # Default font — clean sans-serif
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    window = LaunchpadWindow(app, ready_event=ready_event, splash_proc=splash_proc)
    # window.show() is called by _show_centered() once the splash process exits

    sys.exit(app.exec())


if __name__ == "__main__":
    multiprocessing.freeze_support()
    _setup_crash_log()
    main()
