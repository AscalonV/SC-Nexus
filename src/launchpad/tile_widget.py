"""
ModuleTile — the card widget shown in the launchpad hub for each module.

Clicking anywhere on the tile navigates to the module's view (OPENABLE)
or its settings (TOGGLEABLE).  TOGGLEABLE tiles also show a ToggleSwitch.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.core.module_base import ModuleBase, ModuleType
from src.launchpad.toggle_switch import ToggleSwitch

# Palette kept in one place — easy to retheme later
_ACCENT       = "#4fc3f7"   # light cyan
_BG_NORMAL    = "#0d1b2a"
_BG_HOVER     = "#112236"
_BORDER_NORMAL = "#1e3050"
_BORDER_HOVER  = "#4fc3f7"
_TEXT_PRIMARY  = "#e8f0fe"
_TEXT_SECONDARY = "#8899aa"


_TILE_STYLE = f"""
ModuleTile {{
    background-color: {_BG_NORMAL};
    border: 1px solid {_BORDER_NORMAL};
    border-radius: 8px;
}}
ModuleTile:hover {{
    background-color: {_BG_HOVER};
    border: 1px solid {_BORDER_HOVER};
}}
"""


class ModuleTile(QFrame):
    """
    A single launchpad card for one module.

    Clicking the tile body emits:
      open_requested      — for OPENABLE modules
      settings_requested  — for TOGGLEABLE modules

    Signals
    -------
    open_requested      — navigate to the module's main view
    settings_requested  — navigate to (or open) the module's settings
    toggle_requested(bool) — the user flipped the toggle switch (TOGGLEABLE)
    """

    open_requested:     Signal = Signal()
    settings_requested: Signal = Signal()
    toggle_requested:   Signal = Signal(bool)

    def __init__(self, module: ModuleBase, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._module = module
        self.setObjectName("ModuleTile")
        self.setStyleSheet(_TILE_STYLE)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(90)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._build_ui()

        # Connect module status updates to the status label
        module.status_changed.connect(self._on_status_changed)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(16)

        # Accent strip (left edge colour bar)
        strip = QFrame()
        strip.setFixedWidth(4)
        strip.setStyleSheet(f"background-color: {_ACCENT}; border-radius: 2px;")
        root.addWidget(strip)

        # Text block
        text_block = QVBoxLayout()
        text_block.setSpacing(3)

        name_label = QLabel(self._module.display_name)
        name_label.setStyleSheet(
            f"color: {_TEXT_PRIMARY}; font-size: 14px; font-weight: bold;"
        )
        text_block.addWidget(name_label)

        desc_label = QLabel(self._module.description)
        desc_label.setStyleSheet(f"color: {_TEXT_SECONDARY}; font-size: 11px;")
        desc_label.setWordWrap(True)
        text_block.addWidget(desc_label)

        self._status_label = QLabel("")
        self._status_label.setStyleSheet(f"color: {_ACCENT}; font-size: 10px;")
        text_block.addWidget(self._status_label)

        root.addLayout(text_block, 1)

        # TOGGLEABLE modules show a toggle switch on the right edge.
        # No explicit "Open" or "Settings" buttons — clicking the tile navigates.
        if self._module.module_type is ModuleType.TOGGLEABLE:
            self._toggle = ToggleSwitch()
            self._toggle.toggled.connect(self.toggle_requested)
            root.addWidget(self._toggle)

    # ------------------------------------------------------------------
    # Mouse click → navigate
    # ------------------------------------------------------------------

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            if self._module.module_type is ModuleType.OPENABLE:
                self.open_requested.emit()
            else:
                self.settings_requested.emit()
        super().mousePressEvent(event)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_toggle_state(self, enabled: bool) -> None:
        """Programmatically set the toggle (does NOT emit toggle_requested)."""
        if hasattr(self, "_toggle"):
            self._toggle.blockSignals(True)
            self._toggle.setChecked(enabled)
            self._toggle.blockSignals(False)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_status_changed(self, text: str) -> None:
        self._status_label.setText(text)
