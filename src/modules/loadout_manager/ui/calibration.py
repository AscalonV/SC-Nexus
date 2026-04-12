"""
Calibration Dialog — template scan/verification UI.

Lets users run all template scans, visualise confidence levels,
and manually adjust scale factors.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QDialog,
    QDoubleSpinBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from src.modules.loadout_manager.automation.scanner import LoadoutScanner
    from src.modules.loadout_manager.database import LoadoutDatabase
    from src.modules.loadout_manager.settings import LoadoutManagerSettings

_BTN = """
QPushButton {
    background-color: #162a42; color: #e8f0fe;
    border: 1px solid #1e3050; border-radius: 4px; padding: 5px 12px;
}
QPushButton:hover { background-color: #1f3b5c; border-color: #4fc3f7; }
QPushButton:disabled { color: #556677; background-color: #0b1420; }
"""

_TABLE = """
QTableWidget {
    background-color: #0e1b2d; color: #e8f0fe;
    border: 1px solid #1e3050; gridline-color: #1e3050;
}
QHeaderView::section {
    background-color: #162a42; color: #8899aa;
    border: 1px solid #1e3050; padding: 4px;
}
QTableWidget::item:selected { background-color: #1a5276; }
"""


class _ScanWorker(QThread):
    """Runs template calibration in a worker thread."""

    result_ready = Signal(str, float, int, int, float)  # name, confidence, x, y, scale
    finished_all = Signal()

    def __init__(self, scanner: "LoadoutScanner", parent=None) -> None:
        super().__init__(parent)
        self._scanner = scanner

    def run(self) -> None:
        templates = list(self._scanner._templates.keys())
        for name in templates:
            match = self._scanner.find_element(name, threshold=0.3)
            if match:
                self.result_ready.emit(
                    name, match.confidence, match.x, match.y, match.scale
                )
            else:
                self.result_ready.emit(name, 0.0, 0, 0, 1.0)
        self.finished_all.emit()


class CalibrationDialog(QDialog):
    """Template scan and scale verification dialog."""

    def __init__(
        self,
        scanner: "LoadoutScanner",
        db: "LoadoutDatabase",
        settings: "LoadoutManagerSettings",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._scanner = scanner
        self._db = db
        self._settings = settings
        self._worker: _ScanWorker | None = None

        self.setWindowTitle("Template Calibration")
        self.setMinimumSize(640, 420)
        self.setStyleSheet("background-color: #0b1420; color: #e8f0fe;")
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # Scale control
        scale_row = QHBoxLayout()
        scale_row.addWidget(QLabel("Template Scale:"))
        self._scale_spin = QDoubleSpinBox()
        self._scale_spin.setStyleSheet("""
QDoubleSpinBox {
    background-color: #162a42;
    color: #e8f0fe;
    border: 1px solid #1e3050;
    border-radius: 4px;
    padding: 4px 4px 4px 8px;
}
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
    subcontrol-origin: border;
    width: 22px;
    background-color: #1f3b5c;
    border-left: 1px solid #1e3050;
}
QDoubleSpinBox::up-button {
    subcontrol-position: top right;
    border-bottom: 1px solid #1e3050;
    border-top-right-radius: 4px;
}
QDoubleSpinBox::down-button {
    subcontrol-position: bottom right;
    border-bottom-right-radius: 4px;
}
QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {
    background-color: #2a5070;
}
QDoubleSpinBox::up-arrow  { width: 8px; height: 8px; }
QDoubleSpinBox::down-arrow { width: 8px; height: 8px; }
""")
        self._scale_spin.setRange(0.5, 2.0)
        self._scale_spin.setSingleStep(0.05)
        self._scale_spin.setValue(self._settings.template_scale)
        scale_row.addWidget(self._scale_spin)

        self._btn_apply_scale = QPushButton("Apply Scale")
        self._btn_apply_scale.setStyleSheet(_BTN)
        self._btn_apply_scale.clicked.connect(self._on_apply_scale)
        scale_row.addWidget(self._btn_apply_scale)

        self._btn_auto_scale = QPushButton("Auto-Detect")
        self._btn_auto_scale.setStyleSheet(_BTN)
        self._btn_auto_scale.clicked.connect(self._on_auto_detect)
        scale_row.addWidget(self._btn_auto_scale)

        scale_row.addStretch(1)
        layout.addLayout(scale_row)

        # Results table
        self._table = QTableWidget()
        self._table.setStyleSheet(_TABLE)
        self._table.setColumnCount(5)
        self._table.setHorizontalHeaderLabels(["Template", "Confidence", "X", "Y", "Scale"])
        header = self._table.horizontalHeader()
        if header:
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            for c in range(1, 5):
                header.setSectionResizeMode(c, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self._table, 1)

        # Bottom
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self._btn_scan = QPushButton("Run Full Scan")
        self._btn_scan.setStyleSheet(_BTN)
        self._btn_scan.clicked.connect(self._on_scan)
        btn_row.addWidget(self._btn_scan)

        self._btn_save = QPushButton("Save Anchors")
        self._btn_save.setStyleSheet(_BTN)
        self._btn_save.clicked.connect(self._on_save_anchors)
        btn_row.addWidget(self._btn_save)

        btn_row.addStretch(1)

        self._btn_close = QPushButton("Close")
        self._btn_close.setStyleSheet(_BTN)
        self._btn_close.clicked.connect(self.accept)
        btn_row.addWidget(self._btn_close)

        layout.addLayout(btn_row)

    def _on_apply_scale(self) -> None:
        scale = self._scale_spin.value()
        self._scanner.set_scale(scale)
        self._settings.template_scale = scale
        self._settings.save()

    def _on_auto_detect(self) -> None:
        best = self._scanner.calibrate_scale()
        if best:
            self._scale_spin.setValue(best)
            self._on_apply_scale()

    def _on_scan(self) -> None:
        if not self._scanner._templates:
            self._scanner.load_all_templates()

        if not self._scanner._templates:
            QMessageBox.warning(self, "No Templates", "No template images found in assets folder.")
            return

        self._table.setRowCount(0)
        self._btn_scan.setEnabled(False)

        self._worker = _ScanWorker(self._scanner, self)
        self._worker.result_ready.connect(self._on_result)
        self._worker.finished_all.connect(self._on_scan_done)
        self._worker.start()

    def _on_result(self, name: str, confidence: float, x: int, y: int, scale: float) -> None:
        row = self._table.rowCount()
        self._table.insertRow(row)
        self._table.setItem(row, 0, QTableWidgetItem(name))

        conf_item = QTableWidgetItem(f"{confidence:.3f}")
        if confidence >= 0.85:
            conf_item.setForeground(Qt.GlobalColor.green)
        elif confidence >= 0.6:
            conf_item.setForeground(Qt.GlobalColor.yellow)
        else:
            conf_item.setForeground(Qt.GlobalColor.red)
        self._table.setItem(row, 1, conf_item)

        self._table.setItem(row, 2, QTableWidgetItem(str(x)))
        self._table.setItem(row, 3, QTableWidgetItem(str(y)))
        self._table.setItem(row, 4, QTableWidgetItem(f"{scale:.2f}"))

    def _on_scan_done(self) -> None:
        self._btn_scan.setEnabled(True)

    def _on_save_anchors(self) -> None:
        from datetime import datetime

        from src.modules.loadout_manager.database import TemplateAnchor

        for row in range(self._table.rowCount()):
            name_item = self._table.item(row, 0)
            conf_item = self._table.item(row, 1)
            x_item = self._table.item(row, 2)
            y_item = self._table.item(row, 3)
            if not all((name_item, conf_item, x_item, y_item)):
                continue
            conf = float(conf_item.text())
            if conf < 0.5:
                continue
            anchor = TemplateAnchor(
                element_name=name_item.text(),
                x=int(x_item.text()),
                y=int(y_item.text()),
                confidence=conf,
                last_detected=datetime.now().isoformat(),
            )
            self._db.save_anchor(anchor)
