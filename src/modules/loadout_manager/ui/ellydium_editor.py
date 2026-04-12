"""
Ellydium Tree Editor — visual editor for Ellydium tech-tree node states.

Shows categories as tabs, nodes as toggle checkboxes with point cost
and color coding, branch unlock status, and copy/paste support.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src.modules.loadout_manager.ellydium.tree_model import (
    CATEGORY_COLORS,
    EXCLUSIVE_CATEGORIES,
    NODE_CATEGORIES,
    EllydiumTree,
)

if TYPE_CHECKING:
    from src.modules.loadout_manager.database import LoadoutDatabase

_BTN = """
QPushButton {
    background-color: #162a42; color: #e8f0fe;
    border: 1px solid #1e3050; border-radius: 4px; padding: 5px 12px;
}
QPushButton:hover { background-color: #1f3b5c; border-color: #4fc3f7; }
QPushButton:disabled { color: #556677; background-color: #0b1420; }
"""

_BTN_APPLY = """
QPushButton {
    background-color: #1a5276; color: #e8f0fe;
    border: 1px solid #4fc3f7; border-radius: 4px; padding: 6px 16px;
    font-weight: bold;
}
QPushButton:hover { background-color: #1f6d9a; }
QPushButton:disabled { color: #556677; background-color: #0b1420; border-color: #1e3050; }
"""


class EllydiumEditorDialog(QDialog):
    """Visual tech-tree editor for Ellydium ships."""

    apply_to_game_requested = Signal(int, dict)  # build_id, states

    def __init__(
        self,
        db: "LoadoutDatabase",
        ship_id: int,
        build_id: int,
        ship_name: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._db = db
        self._ship_id = ship_id
        self._build_id = build_id
        self._tree: EllydiumTree | None = None
        self._checkboxes: dict[str, QCheckBox] = {}
        self._clipboard: dict[str, bool] | None = None

        self.setWindowTitle(f"Ellydium Tree — {ship_name}" if ship_name else "Ellydium Tree")
        self.setMinimumSize(700, 520)
        self.setStyleSheet("background-color: #0b1420; color: #e8f0fe;")

        self._build_ui()
        self._load_tree()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # Info bar
        info_row = QHBoxLayout()
        self._lbl_total = QLabel("Total: 0 pts")
        self._lbl_total.setStyleSheet("font-size: 13px; color: #4fc3f7; font-weight: bold;")
        info_row.addWidget(self._lbl_total)
        self._lbl_remaining = QLabel("Remaining: 0 pts")
        self._lbl_remaining.setStyleSheet("font-size: 13px; color: #8899aa;")
        info_row.addWidget(self._lbl_remaining)
        info_row.addStretch(1)
        layout.addLayout(info_row)

        # Tab widget for categories
        self._tabs = QTabWidget()
        self._tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #1e3050; background-color: #0e1b2d; }
            QTabBar::tab {
                background-color: #162a42; color: #8899aa;
                border: 1px solid #1e3050; padding: 6px 14px;
            }
            QTabBar::tab:selected { background-color: #1a5276; color: #e8f0fe; }
        """)
        layout.addWidget(self._tabs, 1)

        # Bottom buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self._btn_copy = QPushButton("Copy State")
        self._btn_copy.setStyleSheet(_BTN)
        self._btn_copy.clicked.connect(self._on_copy)
        btn_row.addWidget(self._btn_copy)

        self._btn_paste = QPushButton("Paste State")
        self._btn_paste.setStyleSheet(_BTN)
        self._btn_paste.setEnabled(False)
        self._btn_paste.clicked.connect(self._on_paste)
        btn_row.addWidget(self._btn_paste)

        self._btn_clear = QPushButton("Clear All")
        self._btn_clear.setStyleSheet(_BTN)
        self._btn_clear.clicked.connect(self._on_clear)
        btn_row.addWidget(self._btn_clear)

        btn_row.addStretch(1)

        self._btn_save = QPushButton("Save")
        self._btn_save.setStyleSheet(_BTN)
        self._btn_save.clicked.connect(self._on_save)
        btn_row.addWidget(self._btn_save)

        self._btn_apply = QPushButton("Apply to Game")
        self._btn_apply.setStyleSheet(_BTN_APPLY)
        self._btn_apply.clicked.connect(self._on_apply)
        btn_row.addWidget(self._btn_apply)

        self._btn_close = QPushButton("Close")
        self._btn_close.setStyleSheet(_BTN)
        self._btn_close.clicked.connect(self.accept)
        btn_row.addWidget(self._btn_close)

        layout.addLayout(btn_row)

    def _load_tree(self) -> None:
        defs = self._db.get_tree_defs(self._ship_id)
        states = self._db.get_node_states(self._build_id)

        if not defs:
            self._tree = None
            self._tabs.addTab(QLabel("No tree definitions found."), "Info")
            return

        self._tree = EllydiumTree.from_database(defs, states)
        self._populate_tabs()
        self._update_point_labels()

    def _populate_tabs(self) -> None:
        if self._tree is None:
            return

        self._tabs.clear()
        self._checkboxes.clear()

        # Group nodes by category
        categories: dict[str, list] = {}
        for key, node in self._tree.nodes.items():
            cat = node.definition.category
            categories.setdefault(cat, []).append((key, node))

        for cat_name in NODE_CATEGORIES:
            if cat_name not in categories:
                continue

            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(scroll.Shape.NoFrame)

            page = QWidget()
            grid = QGridLayout(page)
            grid.setSpacing(8)
            grid.setContentsMargins(10, 10, 10, 10)

            color = CATEGORY_COLORS.get(cat_name, "#e8f0fe")
            is_exclusive = cat_name in EXCLUSIVE_CATEGORIES

            nodes = sorted(categories[cat_name], key=lambda x: (x[1].definition.branch, x[0]))

            for i, (key, node) in enumerate(nodes):
                row, col = divmod(i, 3)

                cb = QCheckBox(f"{key}  ({node.definition.cost} pts)")
                cb.setChecked(node.enabled)
                cb.setStyleSheet(f"color: {color}; font-size: 12px;")
                cb.stateChanged.connect(lambda state, k=key: self._on_node_toggled(k, state))
                grid.addWidget(cb, row, col)
                self._checkboxes[key] = cb

            if is_exclusive:
                note = QLabel(f"⚠ {cat_name}: only one option per branch may be active")
                note.setStyleSheet("color: #ff9800; font-size: 11px; padding: 4px;")
                grid.addWidget(note, grid.rowCount(), 0, 1, 3)

            scroll.setWidget(page)
            self._tabs.addTab(scroll, cat_name)

    def _on_node_toggled(self, key: str, state: int) -> None:
        if self._tree is None:
            return

        enabled = state == Qt.CheckState.Checked.value
        ok, msg = self._tree.toggle_node(key, enabled)
        if not ok:
            # Revert
            cb = self._checkboxes.get(key)
            if cb:
                cb.blockSignals(True)
                cb.setChecked(not enabled)
                cb.blockSignals(False)
            if msg:
                QMessageBox.warning(self, "Cannot Toggle", msg)
            return

        # Sync all checkboxes (exclusive toggles may have changed other nodes)
        for k, cb in self._checkboxes.items():
            node = self._tree.nodes.get(k)
            if node and cb.isChecked() != node.enabled:
                cb.blockSignals(True)
                cb.setChecked(node.enabled)
                cb.blockSignals(False)

        self._update_point_labels()

    def _update_point_labels(self) -> None:
        if self._tree is None:
            return
        self._lbl_total.setText(f"Total: {self._tree.total_cost} pts")
        self._lbl_remaining.setText(f"Remaining: {self._tree.remaining_points} pts")

    def _on_copy(self) -> None:
        if self._tree is None:
            return
        self._clipboard = self._tree.get_state()
        self._btn_paste.setEnabled(True)

    def _on_paste(self) -> None:
        if self._tree is None or self._clipboard is None:
            return
        self._tree.paste_state(self._clipboard)
        self._sync_checkboxes()
        self._update_point_labels()

    def _on_clear(self) -> None:
        if self._tree is None:
            return
        self._tree.clear_all()
        self._sync_checkboxes()
        self._update_point_labels()

    def _sync_checkboxes(self) -> None:
        if self._tree is None:
            return
        for k, cb in self._checkboxes.items():
            node = self._tree.nodes.get(k)
            if node:
                cb.blockSignals(True)
                cb.setChecked(node.enabled)
                cb.blockSignals(False)

    def _on_save(self) -> None:
        if self._tree is None:
            return
        states = self._tree.get_state()
        self._db.save_node_states(self._build_id, states)

    def _on_apply(self) -> None:
        if self._tree is None:
            return
        self._on_save()
        self.apply_to_game_requested.emit(self._build_id, self._tree.get_state())
