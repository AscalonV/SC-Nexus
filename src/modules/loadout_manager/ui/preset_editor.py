"""
Preset Editor — CRUD dialog for multi-slot presets.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from src.modules.loadout_manager.database import LoadoutDatabase

_BTN_STYLE = """
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
"""

_LIST_STYLE = """
QListWidget {
    background-color: #0e1b2d;
    color: #e8f0fe;
    border: 1px solid #1e3050;
    border-radius: 4px;
    padding: 4px;
    font-size: 13px;
}
QListWidget::item {
    padding: 6px;
}
QListWidget::item:selected {
    background-color: #1a5276;
}
"""


class PresetEditorDialog(QDialog):
    """Dialog for creating, renaming, duplicating, and deleting presets."""

    presets_changed = Signal()

    def __init__(self, db: "LoadoutDatabase", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._db = db
        self.setWindowTitle("Manage Presets")
        self.setMinimumSize(400, 350)
        self.setStyleSheet("background-color: #0b1420; color: #e8f0fe;")
        self._build_ui()
        self._refresh()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        lbl = QLabel("Presets")
        lbl.setStyleSheet("font-size: 15px; font-weight: bold; color: #4fc3f7;")
        layout.addWidget(lbl)

        self._list = QListWidget()
        self._list.setStyleSheet(_LIST_STYLE)
        layout.addWidget(self._list, 1)

        # Action buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        self._btn_add = QPushButton("Add")
        self._btn_rename = QPushButton("Rename")
        self._btn_dup = QPushButton("Duplicate")
        self._btn_delete = QPushButton("Delete")

        for btn in (self._btn_add, self._btn_rename, self._btn_dup, self._btn_delete):
            btn.setStyleSheet(_BTN_STYLE)
            btn_row.addWidget(btn)

        layout.addLayout(btn_row)

        # Close
        self._btn_close = QPushButton("Close")
        self._btn_close.setStyleSheet(_BTN_STYLE)
        self._btn_close.clicked.connect(self.accept)
        layout.addWidget(self._btn_close, alignment=Qt.AlignmentFlag.AlignRight)

        # Connect
        self._btn_add.clicked.connect(self._on_add)
        self._btn_rename.clicked.connect(self._on_rename)
        self._btn_dup.clicked.connect(self._on_duplicate)
        self._btn_delete.clicked.connect(self._on_delete)

    def _refresh(self) -> None:
        self._list.clear()
        for p in self._db.get_presets():
            item = QListWidgetItem(p.name)
            item.setData(Qt.ItemDataRole.UserRole, p.id)
            self._list.addItem(item)

    def _selected_id(self) -> int | None:
        item = self._list.currentItem()
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    def _on_add(self) -> None:
        name, ok = QInputDialog.getText(self, "New Preset", "Name:")
        if not ok or not name.strip():
            return
        from src.modules.loadout_manager.database import Preset
        self._db.save_preset(Preset(name=name.strip()))
        self._refresh()
        self.presets_changed.emit()

    def _on_rename(self) -> None:
        pid = self._selected_id()
        if pid is None:
            return
        current = self._list.currentItem()
        old_name = current.text() if current else ""
        name, ok = QInputDialog.getText(self, "Rename Preset", "Name:", text=old_name)
        if not ok or not name.strip():
            return
        self._db.rename_preset(pid, name.strip())
        self._refresh()
        self.presets_changed.emit()

    def _on_duplicate(self) -> None:
        pid = self._selected_id()
        if pid is None:
            return
        preset = self._db.get_preset_by_name(
            self._list.currentItem().text() if self._list.currentItem() else ""
        )
        if preset is None or preset.id is None:
            return

        name, ok = QInputDialog.getText(
            self, "Duplicate Preset", "New name:", text=f"{preset.name} (copy)"
        )
        if not ok or not name.strip():
            return

        from src.modules.loadout_manager.database import Preset, PresetSlot

        new_preset = Preset(name=name.strip(), sort_order=preset.sort_order, unequip=preset.unequip)
        self._db.save_preset(new_preset)

        old_slots = self._db.get_preset_slots(preset.id)
        new_slots = [
            PresetSlot(
                preset_id=new_preset.id,  # type: ignore
                slot_number=s.slot_number,
                enabled=s.enabled,
                ship_id=s.ship_id,
                build_id=s.build_id,
            )
            for s in old_slots
        ]
        if new_preset.id is not None:
            self._db.save_preset_slots(new_preset.id, new_slots)

        self._refresh()
        self.presets_changed.emit()

    def _on_delete(self) -> None:
        pid = self._selected_id()
        if pid is None:
            return
        current = self._list.currentItem()
        name = current.text() if current else "this preset"
        reply = QMessageBox.question(
            self,
            "Delete Preset",
            f'Delete preset "{name}"?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._db.delete_preset(pid)
            self._refresh()
            self.presets_changed.emit()
