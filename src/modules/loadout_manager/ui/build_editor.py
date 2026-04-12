"""
Build Editor — dialog for editing a build's crew, preset slot, and Ellydium tree.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QGridLayout,
    QGroupBox,
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
    from src.modules.loadout_manager.database import Build, LoadoutDatabase

# Assets: src/modules/loadout_manager/assets/{N}-{A|B|C}.png
_ASSETS_DIR = Path(__file__).parent.parent / "assets"
_VARIANTS = ("A", "B", "C")   # row 0=A (value 1), row 1=B (value 2), row 2=C (value 3)
_ICON_SIZE = 40                # px — rendered size of each crew icon cell

_BTN = """
QPushButton {
    background-color: #162a42; color: #e8f0fe;
    border: 1px solid #1e3050; border-radius: 4px; padding: 5px 12px;
}
QPushButton:hover { background-color: #1f3b5c; border-color: #4fc3f7; }
"""

_LIST = """
QListWidget {
    background-color: #0e1b2d; color: #e8f0fe;
    border: 1px solid #1e3050; border-radius: 4px; padding: 4px;
}
QListWidget::item { padding: 5px; }
QListWidget::item:selected { background-color: #1a5276; }
"""

_INPUT = "background-color: #162a42; color: #e8f0fe; border: 1px solid #1e3050; border-radius: 4px; padding: 5px;"

_CELL_NORMAL = (
    "QLabel { border: 2px solid transparent; border-radius: 3px; "
    "background-color: #0e1b2d; }"
)
_CELL_SELECTED = (
    "QLabel { border: 2px solid #4fc3f7; border-radius: 3px; "
    "background-color: #1a3a55; }"
)
_CELL_HOVER = (
    "QLabel { border: 2px solid #335577; border-radius: 3px; "
    "background-color: #112233; }"
)


_COMBO = """
QComboBox {
    background-color: #162a42; color: #e8f0fe;
    border: 1px solid #1e3050; border-radius: 4px; padding: 5px 8px;
}
QComboBox QAbstractItemView {
    background-color: #0e1b2d; color: #e8f0fe; selection-background-color: #1f3b5c;
}
"""

# ── Crew cell widget ─────────────────────────────────────────────────

class _CrewCell(QLabel):
    """Single clickable cell in the 15×3 crew grid."""

    def __init__(self, slot: int, variant: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._slot = slot        # 1-15
        self._variant = variant  # A / B / C
        self._selected = False

        img_path = _ASSETS_DIR / f"{slot}-{variant}.png"
        pix = QPixmap(str(img_path))
        if not pix.isNull():
            self.setPixmap(
                pix.scaled(_ICON_SIZE, _ICON_SIZE,
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation)
            )
        else:
            self.setText(f"{slot}{variant}")
            self.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.setFixedSize(_ICON_SIZE + 4, _ICON_SIZE + 4)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(_CELL_NORMAL)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    @property
    def selected(self) -> bool:
        return self._selected

    def set_selected(self, value: bool) -> None:
        self._selected = value
        self.setStyleSheet(_CELL_SELECTED if value else _CELL_NORMAL)

    def enterEvent(self, event) -> None:
        if not self._selected:
            self.setStyleSheet(_CELL_HOVER)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self.setStyleSheet(_CELL_SELECTED if self._selected else _CELL_NORMAL)
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            # Find the parent editor and notify it
            p = self.parent()
            while p is not None:
                if isinstance(p, BuildEditorDialog):
                    p.on_cell_clicked(self._slot, self._variant)
                    return
                p = p.parent()
        super().mousePressEvent(event)


# ── Dialog ───────────────────────────────────────────────────────────

class BuildEditorDialog(QDialog):
    """Dialog for editing builds (crew grid, preset slot) for a given ship."""

    builds_changed = Signal()

    def __init__(
        self,
        db: "LoadoutDatabase",
        ship_id: int,
        ship_name: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._db = db
        self._ship_id = ship_id
        self._current_build: "Build | None" = None

        # _cells[slot][variant] = _CrewCell  (slot 1-15, variant A/B/C)
        self._cells: dict[int, dict[str, _CrewCell]] = {}
        # Current crew: index 0-14 → value 0 (empty), 1 (A), 2 (B), 3 (C)
        self._crew: list[int] = [0] * 15

        self.setWindowTitle(f"Builds — {ship_name}" if ship_name else "Builds")
        # Width: 15 cells × 44px + 14 gaps × 3px + row-label + groupbox padding + left panel + margins
        # ≈ 702 + 42 + 19 + 12 + 32 + 200 + 12 + 32 = ~1051px; height fits 3 rows + chrome
        self.setMinimumSize(1060, 460)
        self.setStyleSheet(
            "background-color: #0b1420; color: #e8f0fe;"
            "QScrollBar:vertical { background:#0a1220; width:8px; margin:0; border-radius:4px; }"
            "QScrollBar::handle:vertical { background:#2a4a6e; min-height:24px; border-radius:4px; }"
            "QScrollBar::handle:vertical:hover { background:#4fc3f7; }"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }"
            "QScrollBar:horizontal { background:#0a1220; height:8px; margin:0; border-radius:4px; }"
            "QScrollBar::handle:horizontal { background:#2a4a6e; min-width:24px; border-radius:4px; }"
            "QScrollBar::handle:horizontal:hover { background:#4fc3f7; }"
            "QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width:0; }"
        )
        self._build_ui()
        self._refresh_list()

    def _build_ui(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # ── Left: build list ──────────────────────────────────────────
        left = QVBoxLayout()
        left.setSpacing(6)

        lbl = QLabel("Builds")
        lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #4fc3f7;")
        left.addWidget(lbl)

        self._list = QListWidget()
        self._list.setStyleSheet(_LIST)
        self._list.currentItemChanged.connect(self._on_select)
        left.addWidget(self._list, 1)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        for attr, label, slot in (
            ("_btn_add",    "Add",    self._on_add),
            ("_btn_rename", "Rename", self._on_rename),
            ("_btn_delete", "Delete", self._on_delete),
        ):
            btn = QPushButton(label)
            btn.setStyleSheet(_BTN)
            btn.clicked.connect(slot)
            btn_row.addWidget(btn)
            setattr(self, attr, btn)

        left.addLayout(btn_row)
        root.addLayout(left, 0)

        # ── Right: detail + crew + actions ───────────────────────────
        right = QVBoxLayout()
        right.setSpacing(10)

        self._name_label = QLabel("")
        self._name_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #e8f0fe;")
        right.addWidget(self._name_label)

        # Preset slot selector (0 = no preset, 1–4)
        slot_row = QHBoxLayout()
        slot_lbl = QLabel("Preset Slot:")
        slot_lbl.setStyleSheet("color: #8899aa;")
        slot_row.addWidget(slot_lbl)
        self._slot_combo = QComboBox()
        self._slot_combo.setStyleSheet(_COMBO)
        self._slot_combo.addItems([str(i) for i in range(5)])  # 0, 1, 2, 3, 4
        self._slot_combo.setFixedWidth(80)
        slot_row.addWidget(self._slot_combo)
        slot_row.addStretch(1)
        right.addLayout(slot_row)

        # Crew grid inside a GroupBox + HScrollArea
        crew_group = QGroupBox("Crew  (click to assign, click again to clear)")
        crew_group.setStyleSheet(
            "QGroupBox { color: #4fc3f7; border: 1px solid #1e3050; border-radius: 4px; "
            "margin-top: 8px; padding-top: 16px; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 10px; }"
        )
        crew_outer = QVBoxLayout(crew_group)
        crew_outer.setContentsMargins(6, 4, 6, 6)

        grid_widget = QWidget()
        grid_widget.setStyleSheet("background-color: transparent;")
        grid = QGridLayout(grid_widget)
        grid.setSpacing(3)
        grid.setContentsMargins(0, 0, 0, 0)

        # Column headers (slot numbers)
        for col in range(15):
            hdr = QLabel(str(col + 1))
            hdr.setFixedWidth(_ICON_SIZE + 4)
            hdr.setAlignment(Qt.AlignmentFlag.AlignCenter)
            hdr.setStyleSheet("color: #556677; font-size: 10px;")
            grid.addWidget(hdr, 0, col + 1)

        # Row labels + cells
        for row_idx, variant in enumerate(_VARIANTS):
            row_lbl = QLabel(variant)
            row_lbl.setFixedWidth(16)
            row_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            row_lbl.setStyleSheet("color: #8899aa; font-size: 11px; font-weight: bold;")
            grid.addWidget(row_lbl, row_idx + 1, 0)

            for col in range(15):
                slot_num = col + 1
                cell = _CrewCell(slot_num, variant)
                grid.addWidget(cell, row_idx + 1, col + 1)
                self._cells.setdefault(slot_num, {})[variant] = cell

        crew_outer.addWidget(grid_widget)
        right.addWidget(crew_group)

        # ── Buttons row ───────────────────────────────────────────────
        action_row = QHBoxLayout()
        action_row.setSpacing(8)

        self._btn_save = QPushButton("Save Build")
        self._btn_save.setStyleSheet(_BTN)
        self._btn_save.clicked.connect(self._on_save)
        action_row.addWidget(self._btn_save)

        self._btn_clear_crew = QPushButton("Clear Crew")
        self._btn_clear_crew.setStyleSheet(_BTN)
        self._btn_clear_crew.clicked.connect(self._on_clear_crew)
        action_row.addWidget(self._btn_clear_crew)

        action_row.addStretch(1)

        self._btn_close = QPushButton("Close")
        self._btn_close.setStyleSheet(_BTN)
        self._btn_close.clicked.connect(self.accept)
        action_row.addWidget(self._btn_close)

        right.addLayout(action_row)
        root.addLayout(right, 1)

    # ── Cell interaction ──────────────────────────────────────────────

    def on_cell_clicked(self, slot: int, variant: str) -> None:
        """Called by _CrewCell on click.  Toggles selection for that column."""
        idx = slot - 1
        current_val = self._crew[idx]
        new_val = _VARIANTS.index(variant) + 1  # A→1, B→2, C→3

        if current_val == new_val:
            # Clicking current selection → clear
            new_val = 0

        self._crew[idx] = new_val
        self._sync_cells_for_slot(slot)

    def _sync_cells_for_slot(self, slot: int) -> None:
        """Update cell highlight states for a single column."""
        idx = slot - 1
        selected_val = self._crew[idx]
        for row_idx, variant in enumerate(_VARIANTS):
            cell = self._cells.get(slot, {}).get(variant)
            if cell:
                cell.set_selected(selected_val == row_idx + 1)

    def _sync_all_cells(self) -> None:
        for slot in range(1, 16):
            self._sync_cells_for_slot(slot)

    # ── List / DB helpers ─────────────────────────────────────────────

    def _refresh_list(self) -> None:
        builds = self._db.get_builds(self._ship_id)
        self._list.blockSignals(True)
        self._list.clear()
        for b in builds:
            item = QListWidgetItem(b.name)
            item.setData(Qt.ItemDataRole.UserRole, b.id)
            self._list.addItem(item)
        self._list.blockSignals(False)

    def _on_select(self, current: QListWidgetItem | None, _prev=None) -> None:
        if current is None:
            self._current_build = None
            return
        build_id = current.data(Qt.ItemDataRole.UserRole)
        build = self._db.get_build_by_id(build_id)
        if build is None:
            return
        self._current_build = build
        self._name_label.setText(build.name)
        self._slot_combo.setCurrentIndex(max(0, min(4, build.preset_slot)))
        self._crew = list(build.crew) if build.crew else [0] * 15
        # Ensure 15 elements
        while len(self._crew) < 15:
            self._crew.append(0)
        self._sync_all_cells()

    def _on_add(self) -> None:
        name, ok = QInputDialog.getText(self, "Add Build", "Build name:")
        if not ok or not name.strip():
            return
        from src.modules.loadout_manager.database import Build
        build = Build(ship_id=self._ship_id, name=name.strip())
        self._db.save_build(build)
        self._refresh_list()
        self.builds_changed.emit()

    def _on_rename(self) -> None:
        if self._current_build is None or self._current_build.id is None:
            return
        name, ok = QInputDialog.getText(
            self, "Rename Build", "New name:", text=self._current_build.name
        )
        if not ok or not name.strip():
            return
        self._db.rename_build(self._current_build.id, name.strip())
        self._refresh_list()
        self.builds_changed.emit()

    def _on_delete(self) -> None:
        if self._current_build is None or self._current_build.id is None:
            return
        reply = QMessageBox.question(
            self,
            "Delete Build",
            f'Delete build "{self._current_build.name}"?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._db.delete_build(self._current_build.id)
            self._current_build = None
            self._refresh_list()
            self.builds_changed.emit()

    def _on_save(self) -> None:
        if self._current_build is None:
            return
        self._current_build.preset_slot = self._slot_combo.currentIndex()
        self._current_build.crew = list(self._crew)
        self._db.save_build(self._current_build)
        self.builds_changed.emit()

    def _on_clear_crew(self) -> None:
        self._crew = [0] * 15
        self._sync_all_cells()

