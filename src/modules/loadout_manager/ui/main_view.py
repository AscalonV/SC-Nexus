"""
MainView — the OPENABLE module's primary page.

Layout:
  ┌─────────────────────────────────────────────┐
  │ Toolbar: Preset ▼  Load  Save │ Equip All  │
  ├─────────────────────────────────────────────┤
  │ SlotPanel 1                                  │
  │ SlotPanel 2                                  │
  │ SlotPanel 3                                  │
  │ SlotPanel 4                                  │
  ├─────────────────────────────────────────────┤
  │ Status log  │ Progress bar │ Cancel button   │
  └─────────────────────────────────────────────┘
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes as _wt
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QKeySequenceEdit,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.modules.loadout_manager.ui.slot_panel import SlotPanel

if TYPE_CHECKING:
    from src.modules.loadout_manager.database import LoadoutDatabase
    from src.modules.loadout_manager.settings import LoadoutManagerSettings


# ── Global cancel hotkey (fires even when game window is focused) ─────

class _GlobalCancelHotkey(QThread):
    """Registers a Win32 global hotkey and emits `triggered` when pressed."""

    triggered = Signal()

    _WM_HOTKEY   = 0x0312
    _WM_QUIT     = 0x0012
    _HOTKEY_ID   = 0x4C4D   # arbitrary unique ID for this app
    _MOD_NOREPEAT = 0x4000

    _VK_TABLE: dict[str, int] = {
        **{f"F{n}": 0x6F + n for n in range(1, 25)},
        **{c: ord(c) for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"},
        **{str(d): ord(str(d)) for d in range(10)},
        "ESC": 0x1B, "ESCAPE": 0x1B, "SPACE": 0x20, "RETURN": 0x0D, "TAB": 0x09,
        "INSERT": 0x2D, "DELETE": 0x2E, "HOME": 0x24, "END": 0x23,
        "PAGEUP": 0x21, "PAGEDOWN": 0x22,
        "LEFT": 0x25, "UP": 0x26, "RIGHT": 0x27, "DOWN": 0x28,
    }

    def __init__(self, key_str: str, parent=None) -> None:
        super().__init__(parent)
        self._key_str = key_str
        self._thread_id: int = 0

    @classmethod
    def _parse(cls, key_str: str) -> tuple[int, int]:
        """Return (vk, mod_flags) from a Qt-style key string like 'Ctrl+F8'."""
        MOD_ALT   = 0x0001
        MOD_CTRL  = 0x0002
        MOD_SHIFT = 0x0004
        MOD_WIN   = 0x0008
        mods = 0
        vk   = 0
        for part in key_str.split("+"):
            upper = part.strip().upper()
            if upper in ("CTRL", "CONTROL"):
                mods |= MOD_CTRL
            elif upper == "ALT":
                mods |= MOD_ALT
            elif upper == "SHIFT":
                mods |= MOD_SHIFT
            elif upper in ("META", "WIN"):
                mods |= MOD_WIN
            else:
                vk = cls._VK_TABLE.get(upper, 0)
                if not vk and len(part.strip()) == 1 and part.strip().isprintable():
                    res = ctypes.windll.user32.VkKeyScanW(ord(part.strip()))
                    if (res & 0xFFFF) != 0xFFFF:
                        vk = res & 0xFF
        return vk, mods

    def run(self) -> None:
        _user32  = ctypes.windll.user32
        _kernel32 = ctypes.windll.kernel32
        self._thread_id = int(_kernel32.GetCurrentThreadId())
        vk, mods = self._parse(self._key_str)
        if not vk:
            return
        mods |= self._MOD_NOREPEAT
        if not _user32.RegisterHotKey(None, self._HOTKEY_ID, mods, vk):
            return
        try:
            msg = _wt.MSG()
            while True:
                ret = _user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
                if ret <= 0:
                    break
                if msg.message == self._WM_HOTKEY and msg.wParam == self._HOTKEY_ID:
                    self.triggered.emit()
                _user32.TranslateMessage(ctypes.byref(msg))
                _user32.DispatchMessageW(ctypes.byref(msg))
        finally:
            _user32.UnregisterHotKey(None, self._HOTKEY_ID)

    def stop(self) -> None:
        if self._thread_id:
            ctypes.windll.user32.PostThreadMessageW(
                self._thread_id, self._WM_QUIT, 0, 0
            )


# ── Key settings dialog ───────────────────────────────────────────────

class _KeySettingsDialog(QDialog):
    """Dialog for editing game navigation keys and equip hotkeys."""

    _SHORTCUT_FIELDS = [
        ("hotkey_cancel",     "Cancel Equip"),
        ("hotkey_equip_all",   "Equip All"),
        ("hotkey_equip_slot1", "Equip Slot 1"),
        ("hotkey_equip_slot2", "Equip Slot 2"),
        ("hotkey_equip_slot3", "Equip Slot 3"),
        ("hotkey_equip_slot4", "Equip Slot 4"),
    ]

    _NAV_FIELDS = [
        ("nav_key_ship_tree", "Ship Tree key"),
        ("nav_key_crew",      "Crew Window key"),
    ]

    _FIELD_STYLE = (
        "background-color: #162a42; color: #e8f0fe;"
        "border: 1px solid #1e3050; border-radius: 4px; padding: 4px;"
    )

    def __init__(self, settings: "LoadoutManagerSettings", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._settings = settings
        self.setWindowTitle("Key Settings")
        self.setStyleSheet(
            "background-color: #0b1420; color: #e8f0fe;"
            "QScrollBar:vertical { background:#0a1220; width:8px; margin:0; border-radius:4px; }"
            "QScrollBar::handle:vertical { background:#2a4a6e; min-height:24px; border-radius:4px; }"
            "QScrollBar::handle:vertical:hover { background:#4fc3f7; }"
            "QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background:#0a1220; }"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }"
        )
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # ── Game navigation keys ──────────────────────────────────────
        nav_lbl = QLabel("Game Navigation Keys")
        nav_lbl.setStyleSheet("font-weight: bold; font-size: 13px; color: #4fc3f7;")
        layout.addWidget(nav_lbl)

        note1 = QLabel(
            "Enter the key you have bound in Star Conflict for each action."
            "\nSingle character (e.g. T) or key name (e.g. F3)."
        )
        note1.setStyleSheet("color: #8899aa; font-size: 11px;")
        layout.addWidget(note1)

        nav_form = QFormLayout()
        nav_form.setSpacing(8)
        self._nav_editors: dict[str, QLineEdit] = {}
        for field, label in self._NAV_FIELDS:
            ed = QLineEdit()
            ed.setStyleSheet(self._FIELD_STYLE)
            ed.setMaxLength(16)
            ed.setText(getattr(settings, field, ""))
            nav_form.addRow(label + ":", ed)
            self._nav_editors[field] = ed
        layout.addLayout(nav_form)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background-color: #1e3050; border: none; max-height: 1px;")
        layout.addWidget(sep)

        # ── App equip shortcuts ───────────────────────────────────────
        sc_lbl = QLabel("SC Nexus Equip Shortcuts")
        sc_lbl.setStyleSheet("font-weight: bold; font-size: 13px; color: #4fc3f7;")
        layout.addWidget(sc_lbl)

        note2 = QLabel("Click a field and press the desired key combination. Leave empty to disable.")
        note2.setStyleSheet("color: #8899aa; font-size: 11px;")
        layout.addWidget(note2)

        sc_form = QFormLayout()
        sc_form.setSpacing(8)
        self._sc_editors: dict[str, QKeySequenceEdit] = {}
        for field, label in self._SHORTCUT_FIELDS:
            ed = QKeySequenceEdit()
            ed.setStyleSheet(self._FIELD_STYLE)
            val = getattr(settings, field, "")
            if val:
                ed.setKeySequence(QKeySequence(val))
            sc_form.addRow(label + ":", ed)
            self._sc_editors[field] = ed
        layout.addLayout(sc_form)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.setStyleSheet("color: #e8f0fe;")
        btns.accepted.connect(self._accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _accept(self) -> None:
        for field, _ in self._NAV_FIELDS:
            val = self._nav_editors[field].text().strip()
            setattr(self._settings, field, val if val else "T" if "tree" in field else "C")
        for field, _ in self._SHORTCUT_FIELDS:
            ks = self._sc_editors[field].keySequence()
            setattr(self._settings, field, ks.toString() if not ks.isEmpty() else "")
        self._settings.save()
        self.accept()

# Keep the old name as an alias so any lingering references don't break
_HotkeyDialog = _KeySettingsDialog

# ── Styles ────────────────────────────────────────────────────────────

_TOOLBAR_STYLE = """
QFrame#Toolbar {
    background-color: #0b1420;
    border-bottom: 1px solid #1e3050;
    padding: 6px 12px;
}
"""

_BTN_ACCENT = """
QPushButton {
    background-color: #1a5276;
    color: #e8f0fe;
    border: 1px solid #4fc3f7;
    border-radius: 4px;
    padding: 6px 16px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #1f6d9a;
}
QPushButton:disabled {
    background-color: #0b1420;
    color: #556677;
    border-color: #1e3050;
}
"""

_BTN_NORMAL = """
QPushButton {
    background-color: #162a42;
    color: #e8f0fe;
    border: 1px solid #1e3050;
    border-radius: 4px;
    padding: 5px 12px;
}
QPushButton:hover {
    background-color: #1f3b5c;
    border-color: #4fc3f7;
}
QPushButton:disabled {
    color: #556677;
    background-color: #0b1420;
}
"""

_SPINBOX_STYLE = """
QSpinBox {
    background-color: #162a42;
    color: #e8f0fe;
    border: 1px solid #1e3050;
    border-radius: 4px;
    padding: 3px 6px;
    min-width: 56px;
}
QSpinBox:hover { border-color: #4fc3f7; }
QSpinBox::up-button, QSpinBox::down-button {
    width: 18px;
    background-color: #1f3b5c;
    border: none;
    border-left: 1px solid #1e3050;
}
QSpinBox::up-button:hover, QSpinBox::down-button:hover {
    background-color: #2a5080;
}
QSpinBox::up-arrow   { image: url(none); width: 0; height: 0; }
QSpinBox::down-arrow { image: url(none); width: 0; height: 0; }
"""

_ASSETS_DIR = Path(__file__).parent / "assets"
_CHECK_SVG  = (_ASSETS_DIR / "check_white.svg").as_posix()

_CHECKBOX_TOOLBAR_STYLE = f"""
QCheckBox {{
    color: #e8f0fe;
    font-size: 12px;
    spacing: 5px;
}}
QCheckBox::indicator {{
    width: 14px;
    height: 14px;
    border: 1px solid #4fc3f7;
    border-radius: 2px;
    background-color: #162a42;
}}
QCheckBox::indicator:checked {{
    background-color: #1a5276;
    image: url("{_CHECK_SVG}");
}}
QCheckBox::indicator:hover {{ border-color: #81d4fa; }}
"""

_COMBO_STYLE = """
QComboBox {
    background-color: #0b1420;
    color: #e8f0fe;
    border: 1px solid #1e3050;
    border-radius: 4px;
    padding: 5px 8px;
    min-width: 180px;
}
QComboBox:hover { border-color: #4fc3f7; }
QComboBox::drop-down { border: none; }
QComboBox QAbstractItemView {
    background-color: #0b1420;
    color: #e8f0fe;
    selection-background-color: #1a3a5a;
    selection-color: #e8f0fe;
    border: 1px solid #1e3050;
    outline: none;
}
QComboBox QAbstractItemView::item {
    padding: 4px 8px;
    background-color: transparent;
    border: none;
}
QComboBox QAbstractItemView::item:selected {
    background-color: #1a3a5a;
    border: none;
}
"""

_LOG_STYLE = """
QTextEdit {
    background-color: #060d17;
    color: #8899aa;
    border: 1px solid #1e3050;
    border-radius: 4px;
    font-family: Consolas, monospace;
    font-size: 11px;
    padding: 4px;
}
"""

_PROGRESS_STYLE = """
QProgressBar {
    background-color: #0b1420;
    border: 1px solid #1e3050;
    border-radius: 3px;
    text-align: center;
    color: #e8f0fe;
    font-size: 11px;
}
QProgressBar::chunk {
    background-color: #4fc3f7;
    border-radius: 2px;
}
"""


class _EquipWorker(QThread):
    """Runs equip sequences off the GUI thread."""

    log_message = Signal(str)
    slot_status = Signal(int, str, str)  # slot_number, status, message
    progress = Signal(int, int)          # current, total
    finished_ok = Signal()
    finished_err = Signal(str)
    finished_cancelled = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._task = None
        self._cancelled = False

    def configure(self, task, cancel_fn=None) -> None:
        self._task = task
        self._cancel_fn = cancel_fn
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True
        if self._cancel_fn:
            self._cancel_fn()

    def run(self) -> None:
        if self._task is None:
            return
        from src.modules.loadout_manager.automation.game_nav import EquipCancelled
        try:
            self._task()
            if not self._cancelled:
                self.finished_ok.emit()
            else:
                self.finished_cancelled.emit()
        except EquipCancelled:
            self.finished_cancelled.emit()
        except Exception as exc:
            if self._cancelled:
                self.finished_cancelled.emit()
            else:
                self.finished_err.emit(str(exc))


class LoadoutMainView(QWidget):
    """Primary page for the Loadout Manager module."""

    import_requested = Signal()
    manage_ships_requested = Signal()
    manage_builds_requested = Signal()
    settings_requested = Signal()
    setup_guide_requested = Signal()

    def __init__(
        self,
        db: "LoadoutDatabase",
        settings: "LoadoutManagerSettings",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._db = db
        self._settings = settings
        self._worker: _EquipWorker | None = None
        self._navigator = None  # set by module after construction
        self._global_cancel_hotkey: _GlobalCancelHotkey | None = None

        self.setStyleSheet(
            "QScrollBar:vertical { background:#0a1220; width:8px; margin:0; border-radius:4px; }"
            "QScrollBar::handle:vertical { background:#2a4a6e; min-height:24px; border-radius:4px; }"
            "QScrollBar::handle:vertical:hover { background:#4fc3f7; }"
            "QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background:#0a1220; }"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }"
            "QScrollBar:horizontal { background:#0a1220; height:8px; margin:0; border-radius:4px; }"
            "QScrollBar::handle:horizontal { background:#2a4a6e; min-width:24px; border-radius:4px; }"
            "QScrollBar::handle:horizontal:hover { background:#4fc3f7; }"
            "QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background:#0a1220; }"
            "QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width:0; }"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Toolbar
        layout.addWidget(self._build_toolbar())

        # Horizontal slot cards (slot 1 left → slot 4 right)
        slot_container = QWidget()
        slot_container.setStyleSheet("background-color: transparent;")
        self._slot_layout = QHBoxLayout(slot_container)
        self._slot_layout.setContentsMargins(16, 12, 16, 8)
        self._slot_layout.setSpacing(10)
        layout.addWidget(slot_container)

        # Build 4 slot panels
        self._slots: list[SlotPanel] = []
        for i in range(1, 5):
            slot = SlotPanel(i)
            slot.equip_ship_requested.connect(self._on_equip_ship)
            slot.equip_crew_requested.connect(self._on_equip_crew)
            slot.equip_both_requested.connect(self._on_equip_both)
            slot.ship_combo.currentIndexChanged.connect(
                lambda _, s=slot: self._on_slot_ship_changed(s)
            )
            self._slots.append(slot)
            self._slot_layout.addWidget(slot, 1)

        # Bottom status area — fills remaining space
        layout.addWidget(self._build_status_bar(), 1)

        # Apply hotkeys from settings
        self._shortcuts: list[QShortcut] = []
        self._apply_hotkeys()

    # ── Toolbar ───────────────────────────────────────────────────────

    def _build_toolbar(self) -> QWidget:
        toolbar = QFrame()
        toolbar.setObjectName("Toolbar")
        toolbar.setStyleSheet(_TOOLBAR_STYLE)
        toolbar.setFixedHeight(52)

        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(8)

        # Preset selector
        preset_lbl = QLabel("Preset:")
        preset_lbl.setStyleSheet("color: #8899aa; font-size: 12px;")
        layout.addWidget(preset_lbl)

        self._preset_combo = QComboBox()
        self._preset_combo.setStyleSheet(_COMBO_STYLE)
        self._preset_combo.currentTextChanged.connect(self._on_preset_selected)
        layout.addWidget(self._preset_combo)

        self._btn_load_preset = QPushButton("Load")
        self._btn_load_preset.setStyleSheet(_BTN_NORMAL)
        self._btn_load_preset.clicked.connect(self._on_load_preset)
        layout.addWidget(self._btn_load_preset)

        self._btn_save_preset = QPushButton("Save")
        self._btn_save_preset.setStyleSheet(_BTN_NORMAL)
        self._btn_save_preset.clicked.connect(self._on_save_preset)
        layout.addWidget(self._btn_save_preset)

        self._btn_edit_presets = QPushButton("Edit Presets")
        self._btn_edit_presets.setStyleSheet(_BTN_NORMAL)
        self._btn_edit_presets.clicked.connect(lambda: self.settings_requested.emit())
        layout.addWidget(self._btn_edit_presets)

        layout.addStretch(1)

        # Management buttons
        self._btn_ships = QPushButton("Ships")
        self._btn_ships.setStyleSheet(_BTN_NORMAL)
        self._btn_ships.clicked.connect(lambda: self.manage_ships_requested.emit())
        layout.addWidget(self._btn_ships)

        self._btn_builds = QPushButton("Builds")
        self._btn_builds.setStyleSheet(_BTN_NORMAL)
        self._btn_builds.clicked.connect(lambda: self.manage_builds_requested.emit())
        layout.addWidget(self._btn_builds)

        layout.addStretch(0)

        # Unequip Modules checkbox
        self._chk_unequip = QCheckBox("Unequip Modules")
        self._chk_unequip.setStyleSheet(_CHECKBOX_TOOLBAR_STYLE)
        self._chk_unequip.setToolTip(
            "Right-click slot and remove all modules before changing ships\n"
            "(same as AHK Unequip Modules checkbox)"
        )
        self._chk_unequip.setChecked(self._settings.unequip_modules)
        self._chk_unequip.toggled.connect(self._on_unequip_toggled)
        layout.addWidget(self._chk_unequip)

        layout.addSpacing(10)

        # Server delay spinbox
        srv_lbl = QLabel("Srv delay:")
        srv_lbl.setStyleSheet("color: #8899aa; font-size: 11px;")
        layout.addWidget(srv_lbl)

        self._spin_server_delay = QSpinBox()
        self._spin_server_delay.setStyleSheet(_SPINBOX_STYLE)
        self._spin_server_delay.setRange(0, 10000)
        self._spin_server_delay.setSingleStep(100)
        self._spin_server_delay.setSuffix(" ms")
        self._spin_server_delay.setToolTip(
            "Extra wait added after each server-dependent step\n"
            "(ship click, preset confirmation).\n"
            "Increase if the program moves on before the game finishes loading."
        )
        self._spin_server_delay.setValue(self._settings.server_delay_ms)
        self._spin_server_delay.valueChanged.connect(self._on_server_delay_changed)
        layout.addWidget(self._spin_server_delay)

        layout.addSpacing(6)

        # Equip All mega-button
        self._btn_equip_all = QPushButton("⚡ Equip All")
        self._btn_equip_all.setStyleSheet(_BTN_ACCENT)
        self._btn_equip_all.clicked.connect(self._on_equip_all)
        layout.addWidget(self._btn_equip_all)

        self._btn_equip_all_ships = QPushButton("⚓ All Ships")
        self._btn_equip_all_ships.setStyleSheet(_BTN_NORMAL)
        self._btn_equip_all_ships.setToolTip("Equip ships for all enabled slots (no crew)")
        self._btn_equip_all_ships.clicked.connect(self._on_equip_all_ships)
        layout.addWidget(self._btn_equip_all_ships)

        self._btn_equip_all_crew = QPushButton("👥 All Crew")
        self._btn_equip_all_crew.setStyleSheet(_BTN_NORMAL)
        self._btn_equip_all_crew.setToolTip("Equip crew for all enabled slots (no ship change)")
        self._btn_equip_all_crew.clicked.connect(self._on_equip_all_crew)
        layout.addWidget(self._btn_equip_all_crew)

        return toolbar

    # ── Hotkeys ───────────────────────────────────────────────────────

    def _apply_hotkeys(self) -> None:
        """Re-register all hotkeys from current settings."""
        for sc in self._shortcuts:
            sc.setEnabled(False)
            sc.deleteLater()
        self._shortcuts.clear()

        mapping = [
            (self._settings.hotkey_equip_all,   self._on_equip_all),
            (self._settings.hotkey_equip_slot1,  lambda: self._on_equip_both(1)),
            (self._settings.hotkey_equip_slot2,  lambda: self._on_equip_both(2)),
            (self._settings.hotkey_equip_slot3,  lambda: self._on_equip_both(3)),
            (self._settings.hotkey_equip_slot4,  lambda: self._on_equip_both(4)),
            (self._settings.hotkey_cancel,        self._on_cancel),
        ]
        for key_str, handler in mapping:
            if not key_str:
                continue
            ks = QKeySequence(key_str)
            if ks.isEmpty():
                continue
            sc = QShortcut(ks, self)
            sc.setContext(Qt.ShortcutContext.WindowShortcut)
            sc.activated.connect(handler)
            self._shortcuts.append(sc)

    def _on_hotkeys(self) -> None:
        dlg = _KeySettingsDialog(self._settings, self)
        if dlg.exec() == _KeySettingsDialog.DialogCode.Accepted:
            self._apply_hotkeys()

    def _on_unequip_toggled(self, checked: bool) -> None:
        self._settings.unequip_modules = checked
        self._settings.save()

    def _on_server_delay_changed(self, value: int) -> None:
        self._settings.server_delay_ms = value
        self._settings.save()

    # ── Status bar ────────────────────────────────────────────────────

    def _build_status_bar(self) -> QWidget:
        bar = QFrame()
        bar.setStyleSheet("background-color: #0b1420; border-top: 1px solid #1e3050;")
        bar.setMinimumHeight(80)

        layout = QVBoxLayout(bar)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(4)

        # Log text
        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setStyleSheet(_LOG_STYLE)
        layout.addWidget(self._log, 1)

        # Progress + cancel row
        row = QHBoxLayout()
        row.setSpacing(8)

        self._progress_bar = QProgressBar()
        self._progress_bar.setStyleSheet(_PROGRESS_STYLE)
        self._progress_bar.setFixedHeight(18)
        self._progress_bar.setValue(0)
        row.addWidget(self._progress_bar, 1)

        self._btn_cancel = QPushButton("Cancel")
        self._btn_cancel.setStyleSheet(_BTN_NORMAL)
        self._btn_cancel.setEnabled(False)
        self._btn_cancel.clicked.connect(self._on_cancel)
        row.addWidget(self._btn_cancel)

        layout.addLayout(row)

        return bar

    # ── Data population ───────────────────────────────────────────────

    def refresh_data(self) -> None:
        """Reload ships, builds, and presets from the database."""
        ships = self._db.get_ships()
        for slot in self._slots:
            slot.populate_ships(ships)

        self._refresh_presets()
        self._restore_last_state()

    def _refresh_presets(self) -> None:
        presets = self._db.get_presets()
        self._preset_combo.blockSignals(True)
        self._preset_combo.clear()
        self._preset_combo.addItem("")
        for p in presets:
            self._preset_combo.addItem(p.name)

        if self._settings.last_preset:
            idx = self._preset_combo.findText(self._settings.last_preset)
            if idx >= 0:
                self._preset_combo.setCurrentIndex(idx)
        self._preset_combo.blockSignals(False)

    def _restore_last_state(self) -> None:
        """Restore the 4-slot state from the last session."""
        for i, snap in enumerate(self._settings.last_slots):
            if i >= len(self._slots):
                break
            slot = self._slots[i]
            slot.is_enabled = snap.enabled
            if snap.ship_name:
                slot.select_ship(snap.ship_name)
            if snap.build_name:
                slot.select_build(snap.build_name)

    def save_current_state(self) -> None:
        """Persist current slot selections to settings."""
        from src.modules.loadout_manager.settings import SlotSnapshot

        snapshots = []
        for slot in self._slots:
            snapshots.append(SlotSnapshot(
                enabled=slot.is_enabled,
                ship_name=slot.selected_ship_name,
                build_name=slot.selected_build_name,
            ))
        self._settings.last_slots = snapshots
        self._settings.last_preset = self._preset_combo.currentText()
        self._settings.save()

    # ── Slot events ───────────────────────────────────────────────────

    def _on_slot_ship_changed(self, slot: SlotPanel) -> None:
        """Reload builds when a slot's ship selection changes."""
        ship_name = slot.selected_ship_name
        if not ship_name or ship_name == "None":
            slot.populate_builds([])
            return
        ship = self._db.get_ship_by_name(ship_name)
        if ship and ship.id is not None:
            builds = self._db.get_builds(ship.id)
            slot.populate_builds(builds)

    # ── Preset events ─────────────────────────────────────────────────

    def _on_preset_selected(self, name: str) -> None:
        pass  # Preview only — load button applies it

    def _on_load_preset(self) -> None:
        name = self._preset_combo.currentText()
        if not name:
            return
        preset = self._db.get_preset_by_name(name)
        if preset is None or preset.id is None:
            return

        slots = self._db.get_preset_slots(preset.id)
        for ps in slots:
            idx = ps.slot_number - 1
            if idx < 0 or idx >= len(self._slots):
                continue
            panel = self._slots[idx]
            panel.is_enabled = ps.enabled

            if ps.ship_id is not None:
                ship = self._db.get_ship_by_id(ps.ship_id)
                if ship:
                    panel.select_ship(ship.name)
                    # Trigger build reload
                    self._on_slot_ship_changed(panel)
                    if ps.build_id is not None:
                        build = self._db.get_build_by_id(ps.build_id)
                        if build:
                            panel.select_build(build.name)
            else:
                panel.select_ship("None")

        self._log_msg(f"Loaded preset: {name}")

    def _on_save_preset(self) -> None:
        name = self._preset_combo.currentText()
        if not name:
            return

        from src.modules.loadout_manager.database import Preset, PresetSlot

        preset = self._db.get_preset_by_name(name)
        if preset is None:
            preset = Preset(name=name, sort_order=self._preset_combo.currentIndex())
            self._db.save_preset(preset)

        slots: list[PresetSlot] = []
        for panel in self._slots:
            ship = self._db.get_ship_by_name(panel.selected_ship_name)
            build = None
            if ship and ship.id is not None:
                build = self._db.get_build_by_name(ship.id, panel.selected_build_name)

            slots.append(PresetSlot(
                preset_id=preset.id,  # type: ignore
                slot_number=panel.slot_number,
                enabled=panel.is_enabled,
                ship_id=ship.id if ship else None,
                build_id=build.id if build else None,
            ))

        self._db.save_preset_slots(preset.id, slots)  # type: ignore
        self._log_msg(f"Saved preset: {name}")

    # ── Equip actions ─────────────────────────────────────────────────

    def set_navigator(self, nav) -> None:
        """Set the GameNavigator instance for automation."""
        self._navigator = nav

    def _on_equip_ship(self, slot_num: int) -> None:
        self._run_equip([slot_num], do_crew=False)

    def _on_equip_crew(self, slot_num: int) -> None:
        self._run_equip([slot_num], do_ship=False)

    def _on_equip_both(self, slot_num: int) -> None:
        self._run_equip([slot_num])

    def _on_equip_all(self) -> None:
        enabled_slots = [
            s.slot_number for s in self._slots if s.is_enabled
        ]
        if not enabled_slots:
            self._log_msg("No slots enabled.")
            return
        self._run_equip(enabled_slots)

    def _on_equip_all_ships(self) -> None:
        enabled_slots = [
            s.slot_number for s in self._slots if s.is_enabled
        ]
        if not enabled_slots:
            self._log_msg("No slots enabled.")
            return
        self._run_equip(enabled_slots, do_crew=False)

    def _on_equip_all_crew(self) -> None:
        enabled_slots = [
            s.slot_number for s in self._slots if s.is_enabled
        ]
        if not enabled_slots:
            self._log_msg("No slots enabled.")
            return
        self._run_equip(enabled_slots, do_ship=False)

    def _run_equip(
        self,
        slot_numbers: list[int],
        do_ship: bool = True,
        do_crew: bool = True,
    ) -> None:
        if self._navigator is None:
            self._log_msg("Automation not configured.")
            return

        if self._worker and self._worker.isRunning():
            self._log_msg("Equip already in progress.")
            return

        nav = self._navigator
        nav.reset()

        def task():
            slot_tasks: list[tuple[int, object, object | None]] = []
            for sn in slot_numbers:
                idx = sn - 1
                if idx < 0 or idx >= len(self._slots):
                    continue

                panel = self._slots[idx]
                ship_name = panel.selected_ship_name
                build_name = panel.selected_build_name

                if not ship_name or ship_name == "None":
                    continue

                ship = self._db.get_ship_by_name(ship_name)
                if ship is None or ship.id is None:
                    continue

                build = self._db.get_build_by_name(ship.id, build_name) if build_name and build_name != "None" else None
                slot_tasks.append((sn, ship, build))

            if not slot_tasks:
                raise RuntimeError("No valid slot selections to equip.")

            def require(ok: bool, message: str) -> None:
                if not ok:
                    raise RuntimeError(message)

            require(nav.ensure_game_focus(), "Could not focus the game window.")
            nav._drv.save_cursor()
            try:
                # ── Step 1: Preparation ───────────────────────────────
                nav.preparation()

                if do_ship:
                    # ── Step 2: Select ships ──────────────────────────
                    require(nav.open_ship_tree(), "Could not open ship tree.")

                    for sn, ship, _build in slot_tasks:
                        require(nav.select_slot(sn), f"Could not select slot {sn}.")
                        if self._settings.unequip_modules:
                            require(nav.unequip_all(sn), f"Unequip phase failed for slot {sn}.")
                        require(
                            nav.select_ship(ship),
                            f"Ship phase failed for slot {sn}.",
                        )

                    # ── Step 3: Preparation ───────────────────────────
                    nav._drv.send_key("ESC")

                    # ── Step 4: Presets ────────────────────────────────
                    for sn, _ship, build in slot_tasks:
                        if build is None:
                            continue
                        if build.preset_slot:
                            require(
                                nav.apply_preset(build.preset_slot, sn),
                                f"Loadout phase failed for slot {sn}.",
                            )

                if do_crew:
                    # ── Step 5: Crew ──────────────────────────────────
                    crew_tasks = [
                        (sn, build) for sn, _ship, build in slot_tasks
                        if build is not None and any(s > 0 for s in build.crew)
                    ]
                    if crew_tasks:
                        require(nav.open_crew_selector(), "Could not open crew selector.")
                        for sn, build in crew_tasks:
                            require(
                                nav.equip_crew_slot(build, sn),
                                f"Crew phase failed for slot {sn}.",
                            )
                        # ── Step 6: Resolve ───────────────────────────
                        nav.resolve()
            finally:
                nav._drv.restore_cursor()

        self._worker = _EquipWorker(self)
        self._worker.configure(task, cancel_fn=nav.cancel)

        if self._navigator:
            self._navigator.progress.connect(self._log_msg)
            self._navigator.error.connect(lambda msg: self._log_msg(f"⚠ {msg}"))

        self._worker.finished_ok.connect(self._on_equip_done)
        self._worker.finished_err.connect(self._on_equip_error)
        self._worker.finished_cancelled.connect(self._on_equip_cancelled)

        self._set_equipping(True)
        self._worker.start()

    def _on_equip_done(self) -> None:
        self._set_equipping(False)
        self._log_msg("Equip sequence completed.")
        # Bring SC Nexus back to the front after the game was in focus
        win = self.window()
        if win:
            win.showNormal()
            win.raise_()
            win.activateWindow()

    def _on_equip_error(self, msg: str) -> None:
        self._set_equipping(False)
        self._log_msg(f"Equip failed: {msg}")

    def _on_equip_cancelled(self) -> None:
        self._set_equipping(False)
        self._log_msg("Cancelled.")
        win = self.window()
        if win:
            win.showNormal()
            win.raise_()
            win.activateWindow()

    def _on_cancel(self) -> None:
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            self._log_msg("Cancelling…")

    def _set_equipping(self, running: bool) -> None:
        self._btn_equip_all.setEnabled(not running)
        self._btn_equip_all_ships.setEnabled(not running)
        self._btn_equip_all_crew.setEnabled(not running)
        self._btn_cancel.setEnabled(running)
        for slot in self._slots:
            slot.set_buttons_enabled(not running)
        # Start/stop a global (system-wide) hotkey so cancel works while
        # the game window has focus.
        if running:
            key_str = self._settings.hotkey_cancel
            if key_str:
                self._global_cancel_hotkey = _GlobalCancelHotkey(key_str, self)
                self._global_cancel_hotkey.triggered.connect(self._on_cancel)
                self._global_cancel_hotkey.start()
        else:
            if self._global_cancel_hotkey is not None:
                self._global_cancel_hotkey.stop()
                self._global_cancel_hotkey.wait(500)
                self._global_cancel_hotkey = None

    # ── Logging ───────────────────────────────────────────────────────

    def _log_msg(self, msg: str) -> None:
        self._log.append(msg)
        sb = self._log.verticalScrollBar()
        if sb:
            sb.setValue(sb.maximum())
