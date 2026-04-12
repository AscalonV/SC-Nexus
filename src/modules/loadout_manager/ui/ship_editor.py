"""
Ship Editor — dialog for managing the ship list (CRUD + faction + click calibration).
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from PySide6.QtCore import QPoint, QRect, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QCursor, QFont, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from src.modules.loadout_manager.database import FACTIONS

if TYPE_CHECKING:
    from src.modules.loadout_manager.database import LoadoutDatabase
    from src.modules.loadout_manager.settings import LoadoutManagerSettings

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

_COMBO = """
QComboBox {
    background-color: #162a42; color: #e8f0fe;
    border: 1px solid #1e3050; border-radius: 4px; padding: 5px 8px;
}
QComboBox QAbstractItemView {
    background-color: #0e1b2d; color: #e8f0fe; selection-background-color: #1f3b5c;
}
"""

_SPIN = """
QSpinBox {
    background-color: #162a42; color: #e8f0fe;
    border: 1px solid #1e3050; border-radius: 4px;
    padding: 4px 6px;
    padding-right: 22px;
}
QSpinBox::up-button, QSpinBox::down-button {
    width: 20px;
    border: none;
    background-color: #1e3050;
    border-radius: 2px;
}
QSpinBox::up-button {
    subcontrol-origin: border;
    subcontrol-position: top right;
    margin: 2px 2px 1px 0px;
}
QSpinBox::down-button {
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    margin: 1px 2px 2px 0px;
}
QSpinBox::up-button:hover, QSpinBox::down-button:hover {
    background-color: #2a4a6e;
    border: 1px solid #4fc3f7;
}
QSpinBox::up-arrow {
    image: none;
    width: 0; height: 0;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-bottom: 5px solid #e8f0fe;
}
QSpinBox::down-arrow {
    image: none;
    width: 0; height: 0;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #e8f0fe;
}
"""

_INPUT = "background-color: #162a42; color: #e8f0fe; border: 1px solid #1e3050; border-radius: 4px; padding: 5px;"

_SCROLLBAR_QSS = (
    "QScrollBar:vertical { background: #0a1220; width: 8px; margin: 0; border-radius: 4px; }"
    "QScrollBar::handle:vertical { background: #2a4a6e; min-height: 24px; border-radius: 4px; }"
    "QScrollBar::handle:vertical:hover { background: #4fc3f7; }"
    "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }"
    "QScrollBar:horizontal { background: #0a1220; height: 8px; margin: 0; border-radius: 4px; }"
    "QScrollBar::handle:horizontal { background: #2a4a6e; min-width: 24px; border-radius: 4px; }"
    "QScrollBar::handle:horizontal:hover { background: #4fc3f7; }"
    "QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }"
)


# ── Coordinate selector overlay (reused from setup_guide) ─────────────

def _pin_window_to_virtual(widget: QWidget, rect: QRect) -> None:
    if sys.platform != "win32":
        return
    import ctypes
    HWND_TOPMOST = ctypes.c_void_p(-1)
    SWP_NOACTIVATE = 0x0010
    SWP_SHOWWINDOW = 0x0040
    ctypes.windll.user32.SetWindowPos(
        int(widget.winId()), HWND_TOPMOST,
        rect.x(), rect.y(), rect.width(), rect.height(),
        SWP_NOACTIVATE | SWP_SHOWWINDOW,
    )


class _ShipCoordSelector(QWidget):
    """Full-screen overlay for registering a ship's click coordinate."""

    coord_captured = Signal(int, int)
    cancelled = Signal()

    def __init__(self, frozen_pixmap: QPixmap, virt_rect: QRect) -> None:
        super().__init__(None, Qt.WindowType.FramelessWindowHint
                              | Qt.WindowType.WindowStaysOnTopHint)
        self._pixmap = frozen_pixmap
        self._virt_x = virt_rect.x()
        self._virt_y = virt_rect.y()
        self._hover: QPoint | None = None
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setMouseTracking(True)
        self.setGeometry(virt_rect)
        self.show()
        self.raise_()
        _pin_window_to_virtual(self, virt_rect)
        self.activateWindow()
        self.setFocus(Qt.FocusReason.ActiveWindowFocusReason)

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.drawPixmap(0, 0, self._pixmap)
        p.fillRect(self.rect(), QColor(0, 0, 0, 80))
        if self._hover:
            x, y = self._hover.x(), self._hover.y()
            pen = QPen(QColor("#4fc3f7"), 1, Qt.PenStyle.SolidLine)
            p.setPen(pen)
            p.drawLine(x, 0, x, self.height())
            p.drawLine(0, y, self.width(), y)
            p.setPen(QPen(QColor("#ffffff")))
            p.setFont(QFont("Consolas", 9))
            p.drawText(x + 8, y - 6, f"({self._virt_x + x}, {self._virt_y + y})")
        p.fillRect(0, 0, self.width(), 32, QColor(0, 0, 0, 180))
        p.setPen(QPen(QColor("#e8f0fe")))
        p.setFont(QFont("Segoe UI", 10))
        p.drawText(12, 21, "Click on the ship in the faction list — ESC to cancel")

    def mouseMoveEvent(self, ev) -> None:
        self._hover = ev.position().toPoint()
        self.update()

    def mousePressEvent(self, ev) -> None:
        if ev.button() == Qt.MouseButton.LeftButton:
            pt = ev.position().toPoint()
            self.close()
            self.coord_captured.emit(self._virt_x + pt.x(), self._virt_y + pt.y())

    def keyPressEvent(self, ev) -> None:
        if ev.key() == Qt.Key.Key_Escape:
            self.cancelled.emit()
            self.close()


class _ScrollCounterOverlay(QWidget):
    """Small floating badge near the cursor showing cumulative scroll count."""

    def __init__(self) -> None:
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedSize(80, 28)
        self._count = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._follow_cursor)
        self._timer.start(30)
        self.show()

    def update_count(self, delta: int) -> None:
        self._count += delta
        self.update()

    def reset(self) -> None:
        self._count = 0
        self.update()

    def _follow_cursor(self) -> None:
        pos = QCursor.pos()
        self.move(pos.x() + 16, pos.y() + 20)

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QColor(10, 20, 40, 200))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(self.rect(), 6, 6)
        if self._count == 0:
            text  = "0"
            color = QColor("#888888")
        elif self._count > 0:
            text  = f"\u2191 {self._count}"
            color = QColor("#66bb6a")
        else:
            text  = f"\u2193 {abs(self._count)}"
            color = QColor("#ef5350")
        p.setPen(color)
        p.setFont(QFont("Consolas", 11, QFont.Weight.Bold))
        p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, text)


class ShipEditorDialog(QDialog):
    """Dialog for managing ships — add, rename, edit faction, delete."""

    ships_changed = Signal()

    def __init__(self, db: "LoadoutDatabase", parent: QWidget | None = None,
                 settings: "LoadoutManagerSettings | None" = None) -> None:
        super().__init__(parent)
        self._db = db
        self._settings = settings
        self._selector: _ShipCoordSelector | None = None
        self._scroll_overlay: _ScrollCounterOverlay | None = None
        self._raw_registered: bool = False
        self._pending: dict[int, dict] = {}   # ship_id → pending field changes
        self._loading: bool = False            # True while programmatically populating form
        self.setWindowTitle("Manage Ships")
        self.setMinimumSize(640, 560)
        self.setStyleSheet("background-color: #0b1420; color: #e8f0fe;" + _SCROLLBAR_QSS)
        self._build_ui()
        self._refresh()
        self._start_scroll_monitor()

    def _build_ui(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # ── Left: faction filter + list + CRUD row ────────────────────
        left = QVBoxLayout()
        left.setSpacing(6)

        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Faction:"))
        self._faction_filter = QComboBox()
        self._faction_filter.setStyleSheet(_COMBO)
        self._faction_filter.addItem("All")
        for f in FACTIONS:
            self._faction_filter.addItem(f)
        self._faction_filter.currentTextChanged.connect(lambda _: self._refresh())
        filter_row.addWidget(self._faction_filter, 1)
        left.addLayout(filter_row)

        self._list = QListWidget()
        self._list.setStyleSheet(_LIST)
        self._list.currentItemChanged.connect(self._on_select)
        left.addWidget(self._list, 1)

        # CRUD buttons below list in one row
        crud_row = QHBoxLayout()
        crud_row.setSpacing(6)
        self._btn_add = QPushButton("Add Ship")
        self._btn_add.setStyleSheet(_BTN)
        self._btn_add.clicked.connect(self._on_add)
        self._btn_rename = QPushButton("Rename")
        self._btn_rename.setStyleSheet(_BTN)
        self._btn_rename.clicked.connect(self._on_rename)
        self._btn_delete = QPushButton("Delete")
        self._btn_delete.setStyleSheet(_BTN)
        self._btn_delete.clicked.connect(self._on_delete)
        for btn in (self._btn_add, self._btn_rename, self._btn_delete):
            crud_row.addWidget(btn)
        left.addLayout(crud_row)

        root.addLayout(left, 1)

        # ── Right: detail panel + Save Changes at bottom ──────────────
        right = QVBoxLayout()
        right.setSpacing(10)

        form = QFormLayout()
        form.setSpacing(6)
        self._name_edit = QLineEdit()
        self._name_edit.setStyleSheet(_INPUT)
        self._name_edit.setReadOnly(True)
        form.addRow("Name:", self._name_edit)

        self._faction_edit = QComboBox()
        self._faction_edit.setStyleSheet(_COMBO)
        for f in FACTIONS:
            self._faction_edit.addItem(f)
        self._faction_edit.currentIndexChanged.connect(self._mark_dirty)
        form.addRow("Faction:", self._faction_edit)

        self._elly_check = QCheckBox("Ellydium ship")
        self._elly_check.setStyleSheet("color: #e8f0fe;")
        self._elly_check.stateChanged.connect(self._mark_dirty)
        form.addRow(self._elly_check)

        right.addLayout(form)

        self._dirty_lbl = QLabel("● Unsaved changes")
        self._dirty_lbl.setStyleSheet("color: #f5a623; font-size: 11px;")
        self._dirty_lbl.setVisible(False)
        right.addWidget(self._dirty_lbl)

        # Click coordinate
        coord_hdr = QLabel("Click Coordinate")
        coord_hdr.setStyleSheet("font-size: 11px; font-weight: bold; color: #4fc3f7; margin-top: 8px;")
        right.addWidget(coord_hdr)

        coord_row = QHBoxLayout()
        self._coord_lbl = QLabel("—")
        self._coord_lbl.setStyleSheet("color: #8899aa; font-family: Consolas; font-size: 12px;")
        coord_row.addWidget(self._coord_lbl)
        self._btn_calibrate = QPushButton("Set Click Position")
        self._btn_calibrate.setStyleSheet(_BTN)
        self._btn_calibrate.setToolTip("Click on the ship in the faction list to register its position")
        self._btn_calibrate.clicked.connect(self._on_calibrate_click)
        coord_row.addWidget(self._btn_calibrate)
        right.addLayout(coord_row)

        # Scroll settings
        scroll_hdr = QLabel("Scroll Settings")
        scroll_hdr.setStyleSheet("font-size: 11px; font-weight: bold; color: #4fc3f7; margin-top: 8px;")
        right.addWidget(scroll_hdr)

        scroll_form = QFormLayout()
        scroll_form.setSpacing(4)

        self._scroll_amt = QSpinBox()
        self._scroll_amt.setStyleSheet(_SPIN)
        self._scroll_amt.setRange(0, 999)
        self._scroll_amt.valueChanged.connect(self._mark_dirty)
        scroll_form.addRow("Scroll amount:", self._scroll_amt)

        self._scroll_dir = QComboBox()
        self._scroll_dir.setStyleSheet(_COMBO)
        self._scroll_dir.addItems(["", "wheelUp", "wheelDown"])
        self._scroll_dir.currentIndexChanged.connect(self._mark_dirty)
        scroll_form.addRow("Scroll direction:", self._scroll_dir)

        self._scroll_amt2 = QSpinBox()
        self._scroll_amt2.setStyleSheet(_SPIN)
        self._scroll_amt2.setRange(0, 999)
        self._scroll_amt2.valueChanged.connect(self._mark_dirty)
        scroll_form.addRow("Scroll amount 2:", self._scroll_amt2)

        self._scroll_dir2 = QComboBox()
        self._scroll_dir2.setStyleSheet(_COMBO)
        self._scroll_dir2.addItems(["", "wheelUp", "wheelDown"])
        self._scroll_dir2.currentIndexChanged.connect(self._mark_dirty)
        scroll_form.addRow("Scroll direction 2:", self._scroll_dir2)

        right.addLayout(scroll_form)
        right.addStretch(1)

        self._btn_save = QPushButton("Save Changes")
        self._btn_save.setStyleSheet(_BTN)
        self._btn_save.clicked.connect(self._on_save)
        right.addWidget(self._btn_save)

        root.addLayout(right)

    def _refresh(self, keep_id: int | None = None) -> None:
        if keep_id is None:
            keep_id = self._selected_id()

        sel_filter = self._faction_filter.currentText()
        faction = sel_filter if sel_filter != "All" else None
        ships = self._db.get_ships(faction)

        sb = self._list.verticalScrollBar()
        scroll_pos = sb.value() if sb else 0

        self._list.blockSignals(True)
        self._list.clear()
        restore_item: QListWidgetItem | None = None
        for s in ships:
            pending = self._pending.get(s.id, {})
            faction_show = pending.get("faction", s.faction)
            suffix = " *" if s.id in self._pending else ""
            item = QListWidgetItem(f"{s.name}  [{faction_show}]{suffix}")
            item.setData(Qt.ItemDataRole.UserRole, s.id)
            self._list.addItem(item)
            if s.id == keep_id:
                restore_item = item
        self._list.blockSignals(False)

        if restore_item is not None:
            self._list.blockSignals(True)
            self._list.setCurrentItem(restore_item)
            self._list.blockSignals(False)

        if sb:
            sb.setValue(scroll_pos)

    def _on_select(self, current: QListWidgetItem | None, _prev=None) -> None:
        if current is None:
            return
        ship_id = current.data(Qt.ItemDataRole.UserRole)
        ship = self._db.get_ship_by_id(ship_id)
        if ship is None:
            return

        pending = self._pending.get(ship_id, {})

        self._loading = True
        self._name_edit.setText(ship.name)

        faction = pending.get("faction", ship.faction)
        idx = self._faction_edit.findText(faction)
        if idx >= 0:
            self._faction_edit.setCurrentIndex(idx)

        self._elly_check.setChecked(pending.get("is_ellydium", ship.is_ellydium))

        click_x = pending.get("click_x", ship.click_x)
        click_y = pending.get("click_y", ship.click_y)
        if click_x is not None and click_y is not None:
            self._coord_lbl.setText(f"({click_x}, {click_y})")
            self._coord_lbl.setStyleSheet("color: #66bb6a; font-family: Consolas; font-size: 12px;")
        else:
            self._coord_lbl.setText("—")
            self._coord_lbl.setStyleSheet("color: #8899aa; font-family: Consolas; font-size: 12px;")

        self._scroll_amt.setValue(pending.get("scroll_amount", ship.scroll_amount))
        dir_idx = self._scroll_dir.findText(pending.get("scroll_direction", ship.scroll_direction))
        self._scroll_dir.setCurrentIndex(dir_idx if dir_idx >= 0 else 0)
        self._scroll_amt2.setValue(pending.get("scroll_amount2", ship.scroll_amount2))
        dir_idx2 = self._scroll_dir2.findText(pending.get("scroll_direction2", ship.scroll_direction2))
        self._scroll_dir2.setCurrentIndex(dir_idx2 if dir_idx2 >= 0 else 0)

        self._loading = False
        self._update_dirty_indicator()

    def _selected_id(self) -> int | None:
        item = self._list.currentItem()
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    # ── Dirty tracking ────────────────────────────────────────────────

    def _mark_dirty(self) -> None:
        if self._loading:
            return
        sid = self._selected_id()
        if sid is None:
            return
        if sid not in self._pending:
            self._pending[sid] = {}
        self._pending[sid].update({
            "faction": self._faction_edit.currentText(),
            "is_ellydium": self._elly_check.isChecked(),
            "scroll_amount": self._scroll_amt.value(),
            "scroll_direction": self._scroll_dir.currentText(),
            "scroll_amount2": self._scroll_amt2.value(),
            "scroll_direction2": self._scroll_dir2.currentText(),
        })
        self._update_dirty_indicator()
        self._update_list_item(sid)

    def _update_dirty_indicator(self) -> None:
        sid = self._selected_id()
        self._dirty_lbl.setVisible(sid is not None and sid in self._pending)

    def _update_list_item(self, ship_id: int) -> None:
        ship = self._db.get_ship_by_id(ship_id)
        if ship is None:
            return
        pending = self._pending.get(ship_id, {})
        faction_show = pending.get("faction", ship.faction)
        suffix = " *" if ship_id in self._pending else ""
        for i in range(self._list.count()):
            item = self._list.item(i)
            if item and item.data(Qt.ItemDataRole.UserRole) == ship_id:
                self._list.blockSignals(True)
                item.setText(f"{ship.name}  [{faction_show}]{suffix}")
                self._list.blockSignals(False)
                break

    def _on_add(self) -> None:
        name, ok = QInputDialog.getText(self, "Add Ship", "Ship name:")
        if not ok or not name.strip():
            return
        from src.modules.loadout_manager.database import Ship
        ship = Ship(name=name.strip(), faction=self._faction_edit.currentText())
        self._db.save_ship(ship)
        self._refresh()
        self.ships_changed.emit()

    def _on_save(self) -> None:
        if not self._pending:
            return
        for sid, changes in list(self._pending.items()):
            ship = self._db.get_ship_by_id(sid)
            if ship is None:
                continue
            for key, val in changes.items():
                setattr(ship, key, val)
            self._db.save_ship(ship)
        self._pending.clear()
        self._refresh()
        self._update_dirty_indicator()
        self.ships_changed.emit()

    def _on_rename(self) -> None:
        sid = self._selected_id()
        if sid is None:
            return
        ship = self._db.get_ship_by_id(sid)
        if ship is None:
            return
        name, ok = QInputDialog.getText(self, "Rename Ship", "New name:", text=ship.name)
        if not ok or not name.strip():
            return
        self._db.rename_ship(sid, name.strip())
        self._refresh()
        self.ships_changed.emit()

    def _on_delete(self) -> None:
        sid = self._selected_id()
        if sid is None:
            return
        ship = self._db.get_ship_by_id(sid)
        if ship is None:
            return
        builds = self._db.get_builds(sid)
        msg = f'Delete ship "{ship.name}"?'
        if builds:
            msg += f"\nThis will also delete {len(builds)} build(s)."
        reply = QMessageBox.question(
            self, "Delete Ship", msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._pending.pop(sid, None)
            self._db.delete_ship(sid)
            self._refresh()
            self.ships_changed.emit()

    # ── Click coordinate calibration ──────────────────────────────────

    def _restore_geometry(self) -> None:
        self.show()
        if hasattr(self, "_saved_geom") and self._saved_geom is not None:
            self.setGeometry(self._saved_geom)
        self.raise_()
        self.activateWindow()

    def _on_calibrate_click(self) -> None:
        sid = self._selected_id()
        if sid is None:
            QMessageBox.information(self, "No Ship", "Select a ship first.")
            return
        self._saved_geom = self.geometry()
        self.hide()
        QTimer.singleShot(200, lambda: self._do_calibrate_screenshot(sid))

    def _do_calibrate_screenshot(self, ship_id: int) -> None:
        try:
            import mss
            import numpy as np
            from PySide6.QtGui import QImage
        except ImportError:
            QMessageBox.warning(
                self, "Missing Dependency",
                "The 'mss' package is required.  pip install mss",
            )
            self._restore_geometry()
            return

        with mss.mss() as sct:
            all_monitors = sct.monitors[0]
            shot = sct.grab(all_monitors)
            img_np = np.frombuffer(shot.raw, dtype=np.uint8)
            img_np = img_np.reshape((shot.height, shot.width, 4))
            h, w = img_np.shape[:2]
            qimg = QImage(img_np.data, w, h, w * 4, QImage.Format.Format_ARGB32)
            frozen = QPixmap.fromImage(qimg)

        virt_rect = QRect(
            all_monitors["left"], all_monitors["top"],
            all_monitors["width"], all_monitors["height"],
        )
        selector = _ShipCoordSelector(frozen, virt_rect)
        self._selector = selector
        selector.coord_captured.connect(
            lambda cx, cy, sid=ship_id: self._save_ship_coord(sid, cx, cy)
        )
        selector.cancelled.connect(self._on_calibrate_cancelled)

    def _save_ship_coord(self, ship_id: int, x: int, y: int) -> None:
        if ship_id not in self._pending:
            self._pending[ship_id] = {}
        self._pending[ship_id]["click_x"] = x
        self._pending[ship_id]["click_y"] = y
        self._coord_lbl.setText(f"({x}, {y})")
        self._coord_lbl.setStyleSheet("color: #66bb6a; font-family: Consolas; font-size: 12px;")
        self._update_dirty_indicator()
        self._update_list_item(ship_id)
        self._restore_geometry()

    def _on_calibrate_cancelled(self) -> None:
        self._restore_geometry()

    # ── Scroll counter overlay ────────────────────────────────────────

    def closeEvent(self, event) -> None:
        if self._pending:
            reply = QMessageBox.question(
                self, "Unsaved Changes",
                f"You have unsaved changes for {len(self._pending)} ship(s).\nSave before closing?",
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel,
            )
            if reply == QMessageBox.StandardButton.Save:
                self._on_save()
            elif reply == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return
        self._stop_scroll_monitor()
        super().closeEvent(event)

    def _start_scroll_monitor(self) -> None:
        """Register for system-wide Raw Input (non-blocking, unlike WH_MOUSE_LL)."""
        if sys.platform != "win32":
            return
        import ctypes
        import ctypes.wintypes as wt

        class RAWINPUTDEVICE(ctypes.Structure):
            _fields_ = [
                ("usUsagePage", wt.USHORT),
                ("usUsage",     wt.USHORT),
                ("dwFlags",     wt.DWORD),
                ("hwndTarget",  wt.HWND),
            ]

        RIDEV_INPUTSINK = 0x00000100   # receive input even when not in foreground
        rid = RAWINPUTDEVICE()
        rid.usUsagePage = 0x01          # Generic Desktop
        rid.usUsage     = 0x02          # Mouse
        rid.dwFlags     = RIDEV_INPUTSINK
        rid.hwndTarget  = int(self.winId())

        ok = ctypes.windll.user32.RegisterRawInputDevices(
            ctypes.byref(rid), 1, ctypes.sizeof(rid)
        )
        if ok:
            self._raw_registered = True
            self._scroll_overlay = _ScrollCounterOverlay()

    def _stop_scroll_monitor(self) -> None:
        if self._raw_registered:
            import ctypes
            import ctypes.wintypes as wt

            class RAWINPUTDEVICE(ctypes.Structure):
                _fields_ = [
                    ("usUsagePage", wt.USHORT),
                    ("usUsage",     wt.USHORT),
                    ("dwFlags",     wt.DWORD),
                    ("hwndTarget",  wt.HWND),
                ]

            RIDEV_REMOVE = 0x00000001
            rid = RAWINPUTDEVICE()
            rid.usUsagePage = 0x01
            rid.usUsage     = 0x02
            rid.dwFlags     = RIDEV_REMOVE
            rid.hwndTarget  = None
            ctypes.windll.user32.RegisterRawInputDevices(
                ctypes.byref(rid), 1, ctypes.sizeof(rid)
            )
            self._raw_registered = False

        if self._scroll_overlay is not None:
            self._scroll_overlay.close()
            self._scroll_overlay = None

    def nativeEvent(self, event_type, message) -> tuple:
        WM_INPUT = 0x00FF
        if self._raw_registered and event_type == b"windows_generic_MSG":
            import ctypes
            try:
                # MSG layout (64-bit): hwnd(8) | message_uint(4) | pad(4) | wParam(8) | lParam(8)
                # MSG layout (32-bit): hwnd(4) | message_uint(4) | wParam(4) | lParam(4)
                ptr = ctypes.sizeof(ctypes.c_void_p)  # 8 on 64-bit, 4 on 32-bit
                msg_addr   = int(message)
                msg_id     = ctypes.c_uint.from_address(msg_addr + ptr).value
                if msg_id == WM_INPUT:
                    lParam = ctypes.c_ssize_t.from_address(msg_addr + ptr * 3).value
                    self._process_raw_input(lParam)
            except Exception:
                pass
        return super().nativeEvent(event_type, message)

    def _process_raw_input(self, lParam: int) -> None:
        """Parse WM_INPUT and update the scroll counter."""
        if self._scroll_overlay is None:
            return
        import ctypes
        import ctypes.wintypes as wt
        import struct

        RID_INPUT               = 0x10000003
        RIM_TYPEMOUSE           = 0
        RI_MOUSE_WHEEL          = 0x0400
        RI_MOUSE_MIDDLE_DOWN    = 0x0010
        RI_MOUSE_RIGHT_DOWN     = 0x0004

        # RAWINPUTHEADER: dwType(4) + dwSize(4) + hDevice(ptr) + wParam(ptr)
        ptr         = ctypes.sizeof(ctypes.c_void_p)
        header_sz   = 8 + 2 * ptr
        # RAWMOUSE: usFlags(2) + pad(2) + usButtonFlags(2) + usButtonData(2) + ...
        btn_off     = header_sz + 4   # offset of usButtonFlags within the buffer

        sz = wt.UINT(0)
        ctypes.windll.user32.GetRawInputData(
            ctypes.c_void_p(lParam), RID_INPUT, None, ctypes.byref(sz), header_sz
        )
        if sz.value < btn_off + 4:
            return

        buf = (ctypes.c_byte * sz.value)()
        got = ctypes.windll.user32.GetRawInputData(
            ctypes.c_void_p(lParam), RID_INPUT, buf, ctypes.byref(sz), header_sz
        )
        if got != sz.value:
            return

        raw = bytes(buf)
        dw_type = struct.unpack_from('<I', raw, 0)[0]
        if dw_type != RIM_TYPEMOUSE:
            return

        btn_flags = struct.unpack_from('<H', raw, btn_off)[0]
        if btn_flags & RI_MOUSE_WHEEL:
            delta = struct.unpack_from('<h', raw, btn_off + 2)[0]  # signed
            self._scroll_overlay.update_count(1 if delta > 0 else -1)
        elif btn_flags & RI_MOUSE_MIDDLE_DOWN:
            self._scroll_overlay.reset()
        elif btn_flags & RI_MOUSE_RIGHT_DOWN:
            QTimer.singleShot(0, self._on_right_click_scroll_confirm)

    def _on_right_click_scroll_confirm(self) -> None:
        """Paste the current scroll counter into the right amount field, then start click calibration."""
        if self._scroll_overlay is None:
            return
        count = self._scroll_overlay._count
        if count == 0:
            return

        amount = abs(count)
        direction = "wheelUp" if count > 0 else "wheelDown"

        # Determine which scroll pass to fill: use pass 1 if empty/zero, else pass 2
        if self._scroll_amt.value() == 0 and self._scroll_dir.currentText() == "":
            self._scroll_amt.setValue(amount)
            idx = self._scroll_dir.findText(direction)
            if idx >= 0:
                self._scroll_dir.setCurrentIndex(idx)
        else:
            self._scroll_amt2.setValue(amount)
            idx = self._scroll_dir2.findText(direction)
            if idx >= 0:
                self._scroll_dir2.setCurrentIndex(idx)

        self._scroll_overlay.reset()

        # Auto-start click calibration for the currently selected ship
        sid = self._selected_id()
        if sid is not None:
            self._saved_geom = self.geometry()
            self.hide()
            QTimer.singleShot(200, lambda: self._do_calibrate_screenshot(sid))
