"""
DisplayNamesDialog — simple table editor for log-name → display-name mappings.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.modules.combat_analysis.display_names import DisplayNameManager

_STYLE = """
QDialog { background-color: #080f1a; }
QTableWidget {
    background-color: #0d1b2a;
    color: #e8f0fe;
    border: 1px solid #1e3050;
    gridline-color: #1e3050;
    selection-background-color: #1a3560;
    selection-color: #e8f0fe;
}
QTableWidget::item:selected { background-color: #1a3560; color: #e8f0fe; }
QScrollBar:vertical {
    background: #09121f;
    width: 12px;
    margin: 0;
    border-left: 1px solid #12253f;
}
QScrollBar::handle:vertical {
    background: #1e3050;
    min-height: 28px;
    border-radius: 5px;
    margin: 2px;
}
QScrollBar::handle:vertical:hover { background: #4fc3f7; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
    background: transparent;
    border: none;
}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: #09121f; }
QScrollBar:horizontal {
    background: #09121f;
    height: 12px;
    margin: 0;
    border-top: 1px solid #12253f;
}
QScrollBar::handle:horizontal {
    background: #1e3050;
    min-width: 28px;
    border-radius: 5px;
    margin: 2px;
}
QScrollBar::handle:horizontal:hover { background: #4fc3f7; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
    background: transparent;
    border: none;
}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: #09121f; }
QTableCornerButton::section { background: #09121f; border: 1px solid #12253f; }
QHeaderView::section {
    background-color: #1e3050;
    color: #4fc3f7;
    padding: 4px;
    border: none;
}
QLineEdit {
    background-color: #0d1b2a;
    color: #e8f0fe;
    border: 1px solid #1e3050;
    border-radius: 4px;
    padding: 3px 6px;
    selection-background-color: #1a3560;
    selection-color: #e8f0fe;
}
QPushButton {
    background-color: transparent;
    color: #8899aa;
    border: 1px solid #1e3050;
    border-radius: 4px;
    padding: 4px 12px;
}
QPushButton:hover { color: #e8f0fe; border-color: #4fc3f7; }
"""


class DisplayNamesDialog(QDialog):
    def __init__(self, manager: DisplayNameManager, known_names: list[str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._mgr = manager
        self._known_names = known_names
        self.setWindowTitle("Display Names")
        self.setMinimumSize(500, 400)
        self.setStyleSheet(_STYLE)

        layout = QVBoxLayout(self)

        self._table = QTableWidget(0, 2)
        self._table.setHorizontalHeaderLabels(["Log Name", "Display Name"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table.verticalHeader().setVisible(False)
        self._table.setAlternatingRowColors(True)
        layout.addWidget(self._table, 1)

        # Add row controls
        add_row = QHBoxLayout()
        self._log_edit  = QLineEdit()
        self._log_edit.setPlaceholderText("Log name…")
        self._disp_edit = QLineEdit()
        self._disp_edit.setPlaceholderText("Display name…")
        add_btn = QPushButton("Add")
        add_btn.clicked.connect(self._add_mapping)
        add_row.addWidget(self._log_edit, 1)
        add_row.addWidget(self._disp_edit, 1)
        add_row.addWidget(add_btn)
        layout.addLayout(add_row)

        del_btn = QPushButton("Delete selected")
        del_btn.clicked.connect(self._delete_selected)
        layout.addWidget(del_btn)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._populate()

    def _populate(self) -> None:
        self._table.setRowCount(0)
        mappings = self._mgr.get_all_mappings()
        names = set(self._known_names)
        names.update(mappings.keys())
        for log_name in sorted(names, key=str.lower):
            display = mappings.get(log_name, "")
            row = self._table.rowCount()
            self._table.insertRow(row)
            self._table.setItem(row, 0, QTableWidgetItem(log_name))
            self._table.setItem(row, 1, QTableWidgetItem(display))

    def _add_mapping(self) -> None:
        log_n  = self._log_edit.text().strip()
        disp_n = self._disp_edit.text().strip()
        if log_n:
            row = self._table.rowCount()
            self._table.insertRow(row)
            self._table.setItem(row, 0, QTableWidgetItem(log_n))
            self._table.setItem(row, 1, QTableWidgetItem(disp_n))
            self._log_edit.clear()
            self._disp_edit.clear()

    def _delete_selected(self) -> None:
        for item in reversed(self._table.selectedItems()):
            self._table.removeRow(item.row())

    def _save(self) -> None:
        # Collect current table state and apply as bulk update
        entries: dict[str, str] = {}
        for row in range(self._table.rowCount()):
            log_item  = self._table.item(row, 0)
            disp_item = self._table.item(row, 1)
            if log_item:
                entries[log_item.text()] = disp_item.text() if disp_item else ""
        self._mgr.mappings = {}
        self._mgr.bulk_update(entries)
        self.accept()
