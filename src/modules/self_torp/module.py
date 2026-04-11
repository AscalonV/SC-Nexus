"""
SelfTorpModule — TOGGLEABLE module.

On enable: validates admin privileges, starts HotkeyEngine.
Settings: QDialog popup (SelfTorpSettingsDialog).
Config persisted to user_data/self_torp_settings.json via Pydantic.
"""

from __future__ import annotations

import ctypes
import subprocess
import sys

from pydantic import BaseModel, Field
from PySide6.QtCore import QObject, Slot
from PySide6.QtWidgets import QMessageBox, QWidget

from src.core.config import AppConfig, USER_DATA_DIR
from src.core.module_base import ModuleBase, ModuleType
from src.modules.self_torp.hotkey_engine import HotkeyEngine
from src.modules.self_torp.ui.settings_dialog import SelfTorpSettingsDialog

_SETTINGS_FILE = USER_DATA_DIR / "self_torp_settings.json"


# ---------------------------------------------------------------------------
# Pydantic settings model
# ---------------------------------------------------------------------------

class SelfTorpSettings(BaseModel):
    enabled:           bool = False
    hotkey:            str  = Field(default="F4")
    first_key:         str  = Field(default="T")
    burst_key:         str  = Field(default="SPACE")
    burst_key_2:       str  = Field(default="")
    burst_count:       int  = Field(default=15)
    first_key_delay_ms: int = Field(default=0)
    burst_gap_ms:      int  = Field(default=1)

    @classmethod
    def load(cls) -> "SelfTorpSettings":
        try:
            if _SETTINGS_FILE.exists():
                return cls.model_validate_json(
                    _SETTINGS_FILE.read_text(encoding="utf-8")
                )
        except Exception:
            pass
        return cls()

    def save(self) -> None:
        try:
            USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
            _SETTINGS_FILE.write_text(self.model_dump_json(indent=2), encoding="utf-8")
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Module
# ---------------------------------------------------------------------------

class SelfTorpModule(ModuleBase):

    @property
    def module_id(self) -> str:        return "self_torp"
    @property
    def display_name(self) -> str:     return "Self-Torp"
    @property
    def description(self) -> str:      return "Global hotkey macro for rapid torpedo fire"
    @property
    def module_type(self) -> ModuleType: return ModuleType.TOGGLEABLE
    @property
    def is_enabled(self) -> bool:      return self._settings.enabled

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._settings: SelfTorpSettings = SelfTorpSettings()
        self._engine:   HotkeyEngine | None = None

    def initialize(self, config: AppConfig) -> None:
        self._settings = SelfTorpSettings.load()
        if self._settings.enabled:
            if _is_admin():
                self._try_start_engine()
            else:
                self.status_changed.emit("Needs admin")
                if not _relaunch_as_admin():
                    self._disable_module()

    def shutdown(self) -> None:
        self._stop_engine()
        self._settings.save()

    # ------------------------------------------------------------------
    # TOGGLEABLE interface
    # ------------------------------------------------------------------

    def on_toggle(self, enabled: bool) -> None:
        if enabled:
            if not _is_admin():
                if self._confirm_restart_as_admin() and _relaunch_as_admin():
                    return
                self._disable_module()
                return
            self._settings.enabled = True
            self._try_start_engine()
        else:
            self._disable_module()
            return
        self._settings.save()

    def open_settings_dialog(self, parent: QWidget) -> None:
        dlg = SelfTorpSettingsDialog(
            hotkey            = self._settings.hotkey,
            first_key         = self._settings.first_key,
            burst_key         = self._settings.burst_key,
            burst_key_2       = self._settings.burst_key_2,
            burst_count       = self._settings.burst_count,
            first_key_delay_ms = self._settings.first_key_delay_ms,
            burst_gap_ms      = self._settings.burst_gap_ms,
            parent            = parent,
        )
        if dlg.exec() == SelfTorpSettingsDialog.DialogCode.Accepted:
            self._settings.hotkey           = dlg.result_hotkey
            self._settings.first_key        = dlg.result_first_key
            self._settings.burst_key        = dlg.result_burst_key
            self._settings.burst_key_2      = dlg.result_burst_key_2
            self._settings.burst_count      = dlg.result_burst_count
            self._settings.first_key_delay_ms = dlg.result_first_key_delay_ms
            self._settings.burst_gap_ms     = dlg.result_burst_gap_ms
            self._settings.save()

            # Hot-reload engine if running
            if self._engine is not None:
                self._stop_engine()
                self._try_start_engine()

    # ------------------------------------------------------------------
    # Engine management
    # ------------------------------------------------------------------

    def _try_start_engine(self) -> None:
        if self._engine is not None:
            return
        try:
            engine = HotkeyEngine(self)
            engine.configure(
                self._settings.hotkey,
                self._settings.first_key,
                self._settings.burst_key,
                burst_key_name2=self._settings.burst_key_2,
                burst_count=self._settings.burst_count,
                first_key_delay_ms=self._settings.first_key_delay_ms,
                burst_gap_ms=self._settings.burst_gap_ms,
            )
            engine.hotkey_fired.connect(self._on_fired)
            engine.start()
            self._engine = engine
            self.status_changed.emit(
                f"Active — {self._settings.hotkey}"
            )
        except Exception as exc:
            self.status_changed.emit(f"Error: {exc}")

    def _stop_engine(self) -> None:
        if self._engine is not None:
            self._engine.stop()
            self._engine = None

    @Slot()
    def _on_fired(self) -> None:
        # Could emit a signal to UI here in the future
        pass

    # ------------------------------------------------------------------
    # Admin helpers
    # ------------------------------------------------------------------

    def _disable_module(self) -> None:
        self._settings.enabled = False
        self._stop_engine()
        self.status_changed.emit("Inactive")
        self._settings.save()

    def _confirm_restart_as_admin(self) -> bool:
        box = QMessageBox()
        box.setWindowTitle("Self-Torp")
        box.setText(
            "Self-Torp requires administrator privileges to install global keyboard hooks.\n\n"
            "Restart SC Nexus as administrator?"
        )
        box.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        box.setDefaultButton(QMessageBox.StandardButton.Yes)
        return box.exec() == QMessageBox.StandardButton.Yes


def _is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def _relaunch_as_admin() -> bool:
    exe = sys.executable
    args = subprocess.list2cmdline(sys.argv)
    result = ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, args, None, 1)
    if result <= 32:
        return False
    sys.exit(0)
