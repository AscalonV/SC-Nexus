"""
Slot panel widget — one of the 4 ship equip slots.

Displays a ship selector (grouped by faction), build selector, enable
checkbox, and per-slot action buttons (Equip Ship / Crew / Both).
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from src.modules.loadout_manager.database import Build, LoadoutDatabase, Ship

# ── Style ─────────────────────────────────────────────────────────────

_SLOT_STYLE = """
QFrame#SlotPanel {
    background-color: #0e1b2d;
    border: 1px solid #1e3050;
    border-radius: 6px;
}
QFrame#SlotPanel:hover {
    border-color: #4fc3f7;
}
"""

_BTN_STYLE = """
QPushButton {
    background-color: #162a42;
    color: #e8f0fe;
    border: 1px solid #1e3050;
    border-radius: 4px;
    padding: 4px 10px;
    font-size: 11px;
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

_COMBO_STYLE = """
QComboBox {
    background-color: #162a42;
    color: #e8f0fe;
    border: 1px solid #1e3050;
    border-radius: 4px;
    padding: 4px 8px;
    min-width: 160px;
}
QComboBox:hover {
    border-color: #4fc3f7;
}
QComboBox::drop-down {
    border: none;
}
QComboBox QAbstractItemView {
    background-color: #0e1b2d;
    color: #e8f0fe;
    selection-background-color: #1f3b5c;
    border: 1px solid #1e3050;
}
"""

_STATUS_COLORS = {
    "idle": "#556677",
    "equipping": "#4fc3f7",
    "done": "#66bb6a",
    "error": "#ef5350",
}

_ASSETS_DIR = Path(__file__).parent / "assets"
_CHECK_SVG = (_ASSETS_DIR / "check_white.svg").as_posix()

_CHECKBOX_STYLE = f"""
QCheckBox::indicator {{
    width: 15px;
    height: 15px;
    border: 1px solid #4fc3f7;
    border-radius: 2px;
    background-color: #162a42;
}}
QCheckBox::indicator:checked {{
    background-color: #1a5276;
    image: url("{_CHECK_SVG}");
}}
QCheckBox::indicator:hover {{
    border-color: #81d4fa;
}}
"""


class SlotPanel(QFrame):
    """Single ship slot (1 of 4) with ship/build selectors and action buttons."""

    equip_ship_requested = Signal(int)    # slot_number
    equip_crew_requested = Signal(int)
    equip_both_requested = Signal(int)

    def __init__(self, slot_number: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("SlotPanel")
        self.setStyleSheet(_SLOT_STYLE)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)

        self._slot_number = slot_number
        self._ships: list["Ship"] = []
        self._builds: list["Build"] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 10)
        layout.setSpacing(0)

        # ── Header row ────────────────────────────────────────────────
        header = QHBoxLayout()
        header.setSpacing(8)
        header.setContentsMargins(0, 0, 0, 6)

        self._checkbox = QCheckBox()
        self._checkbox.setChecked(True)
        self._checkbox.setToolTip("Enable this slot")
        self._checkbox.setStyleSheet(_CHECKBOX_STYLE)
        header.addWidget(self._checkbox)

        slot_label = QLabel(f"Slot {slot_number}")
        slot_label.setStyleSheet("color: #4fc3f7; font-weight: bold; font-size: 13px;")
        header.addWidget(slot_label)

        header.addStretch(1)

        self._status_label = QLabel("Idle")
        self._status_label.setStyleSheet(f"color: {_STATUS_COLORS['idle']}; font-size: 11px;")
        header.addWidget(self._status_label)

        layout.addLayout(header)

        # Thin separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background-color: #1e3050; max-height: 1px; border: none;")
        layout.addWidget(sep)
        layout.addSpacing(7)

        # ── Ship row ──────────────────────────────────────────────────
        ship_row = QHBoxLayout()
        ship_row.setSpacing(6)
        ship_row.setContentsMargins(0, 0, 0, 0)
        ship_lbl = QLabel("Ship")
        ship_lbl.setStyleSheet("color: #8899aa; font-size: 11px;")
        ship_lbl.setFixedWidth(34)
        ship_row.addWidget(ship_lbl)
        self._ship_combo = QComboBox()
        self._ship_combo.setStyleSheet(_COMBO_STYLE)
        self._ship_combo.currentIndexChanged.connect(self._on_ship_changed)
        ship_row.addWidget(self._ship_combo, 1)
        layout.addLayout(ship_row)
        layout.addSpacing(5)

        # ── Build row ─────────────────────────────────────────────────
        build_row = QHBoxLayout()
        build_row.setSpacing(6)
        build_row.setContentsMargins(0, 0, 0, 0)
        build_lbl = QLabel("Build")
        build_lbl.setStyleSheet("color: #8899aa; font-size: 11px;")
        build_lbl.setFixedWidth(34)
        build_row.addWidget(build_lbl)
        self._build_combo = QComboBox()
        self._build_combo.setStyleSheet(_COMBO_STYLE)
        build_row.addWidget(self._build_combo, 1)
        layout.addLayout(build_row)
        layout.addSpacing(9)

        # ── Action buttons ────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(4)
        btn_row.setContentsMargins(0, 0, 0, 0)

        self._btn_ship = QPushButton("Equip Ship")
        self._btn_ship.setStyleSheet(_BTN_STYLE)
        self._btn_ship.clicked.connect(lambda: self.equip_ship_requested.emit(self._slot_number))
        btn_row.addWidget(self._btn_ship, 1)

        self._btn_crew = QPushButton("Equip Crew")
        self._btn_crew.setStyleSheet(_BTN_STYLE)
        self._btn_crew.clicked.connect(lambda: self.equip_crew_requested.emit(self._slot_number))
        btn_row.addWidget(self._btn_crew, 1)

        self._btn_both = QPushButton("Ship + Crew")
        self._btn_both.setStyleSheet(_BTN_STYLE)
        self._btn_both.clicked.connect(lambda: self.equip_both_requested.emit(self._slot_number))
        btn_row.addWidget(self._btn_both, 1)

        layout.addLayout(btn_row)

    # ── Properties ────────────────────────────────────────────────────

    @property
    def slot_number(self) -> int:
        return self._slot_number

    @property
    def is_enabled(self) -> bool:
        return self._checkbox.isChecked()

    @is_enabled.setter
    def is_enabled(self, value: bool) -> None:
        self._checkbox.setChecked(value)

    @property
    def selected_ship_name(self) -> str:
        return self._ship_combo.currentText()

    @property
    def selected_build_name(self) -> str:
        return self._build_combo.currentText()

    # ── Population ────────────────────────────────────────────────────

    def populate_ships(self, ships: list["Ship"]) -> None:
        """Fill the ship dropdown, optionally grouped by faction."""
        self._ships = ships
        self._ship_combo.blockSignals(True)
        self._ship_combo.clear()
        self._ship_combo.addItem("None")

        # Group by faction
        factions: dict[str, list[str]] = {}
        for s in ships:
            factions.setdefault(s.faction, []).append(s.name)

        for faction in ("Empire", "Federation", "Jericho", "Ellydium", "Unique", "None"):
            names = factions.get(faction, [])
            if not names:
                continue
            for name in sorted(names):
                self._ship_combo.addItem(name)

        self._ship_combo.blockSignals(False)

    def populate_builds(self, builds: list["Build"]) -> None:
        self._builds = builds
        self._build_combo.blockSignals(True)
        self._build_combo.clear()
        self._build_combo.addItem("None")
        for b in builds:
            self._build_combo.addItem(b.name)
        self._build_combo.blockSignals(False)

    def select_ship(self, name: str) -> None:
        idx = self._ship_combo.findText(name)
        if idx >= 0:
            self._ship_combo.setCurrentIndex(idx)

    def select_build(self, name: str) -> None:
        idx = self._build_combo.findText(name)
        if idx >= 0:
            self._build_combo.setCurrentIndex(idx)

    # ── Status ────────────────────────────────────────────────────────

    def set_status(self, status: str, message: str = "") -> None:
        """Update the slot status indicator."""
        color = _STATUS_COLORS.get(status, _STATUS_COLORS["idle"])
        text = message or status.capitalize()
        self._status_label.setText(text)
        self._status_label.setStyleSheet(f"color: {color}; font-size: 11px;")

    def set_buttons_enabled(self, enabled: bool) -> None:
        self._btn_ship.setEnabled(enabled)
        self._btn_crew.setEnabled(enabled)
        self._btn_both.setEnabled(enabled)

    # ── Signals ───────────────────────────────────────────────────────

    def _on_ship_changed(self, _index: int) -> None:
        """Notify parent that the ship changed (to reload builds)."""
        # The parent (main_view) connects to this via ship_combo
        pass

    @property
    def ship_combo(self) -> QComboBox:
        return self._ship_combo

    @property
    def build_combo(self) -> QComboBox:
        return self._build_combo

    @property
    def enabled_checkbox(self) -> QCheckBox:
        return self._checkbox
