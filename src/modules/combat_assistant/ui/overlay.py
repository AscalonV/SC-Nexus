"""
OverlayWindow — transparent, always-on-top, click-through combat overlay.

CalibrationOverlay — fullscreen semi-transparent overlay for selecting
                     screen regions or single points.

Both windows use Windows API calls for DPI-aware physical pixel positioning
and WS_EX_TRANSPARENT click-through behaviour.
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import sys
from PySide6.QtCore import QPoint, QRect, QSize, Qt, Signal, QTimer
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QApplication, QWidget

# ---------------------------------------------------------------------------
# Windows API helpers (no-op on non-Windows)
# ---------------------------------------------------------------------------

_IS_WIN = sys.platform == "win32"

GWL_EXSTYLE          = -20
WS_EX_TRANSPARENT    = 0x00000020
WS_EX_LAYERED        = 0x00080000
WS_EX_TOOLWINDOW     = 0x00000080
SWP_NOMOVE           = 0x0002
SWP_NOSIZE           = 0x0001
SWP_NOZORDER         = 0x0004
SWP_NOACTIVATE       = 0x0010
SWP_SHOWWINDOW       = 0x0040
SWP_FRAMECHANGED     = 0x0020
HWND_TOPMOST         = ctypes.c_void_p(-1)  # must be pointer-sized; plain int -1 zero-extends to 0xFFFFFFFF on x64 → SetWindowPos fails silently

_user32   = ctypes.windll.user32   if _IS_WIN else None
_DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = -4
SM_XVIRTUALSCREEN = 76
SM_YVIRTUALSCREEN = 77
SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79


def _get_hwnd(widget: QWidget) -> int:
    return int(widget.winId())


def _set_click_through(hwnd: int, enable: bool) -> None:
    if not _IS_WIN:
        return
    style = _user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    if enable:
        style |= WS_EX_TRANSPARENT | WS_EX_LAYERED
    else:
        style &= ~WS_EX_TRANSPARENT
        style |= WS_EX_LAYERED
    _user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
    # SWP_NOZORDER preserves the window's Z-order (do not demote from TOPMOST)
    _user32.SetWindowPos(
        hwnd, 0, 0, 0, 0, 0,
        SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED,
    )
def _set_window_pos_physical(hwnd: int, x: int, y: int, w: int, h: int) -> None:
    """Move window to physical pixel coordinates, bypassing DPI scaling."""
    if not _IS_WIN:
        return
    _user32.SetWindowPos(hwnd, HWND_TOPMOST, x, y, w, h, SWP_NOACTIVATE | SWP_SHOWWINDOW)


def _get_window_pos_physical(hwnd: int) -> tuple[int, int] | None:
    if not _IS_WIN:
        return None
    rect = wt.RECT()
    if _user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return (rect.left, rect.top)
    return None


def _get_cursor_pos_physical() -> tuple[int, int]:
    if not _IS_WIN:
        return (0, 0)
    pt = wt.POINT()
    _user32.GetCursorPos(ctypes.byref(pt))
    return (pt.x, pt.y)


def _get_virtual_screen_geometry() -> QRect:
    if _IS_WIN:
        x = _user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
        y = _user32.GetSystemMetrics(SM_YVIRTUALSCREEN)
        w = _user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)
        h = _user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)
        return QRect(x, y, w, h)

    screens = QApplication.screens()
    if not screens:
        return QRect(0, 0, 1920, 1080)

    rect = screens[0].geometry()
    for screen in screens[1:]:
        rect = rect.united(screen.geometry())
    return rect


# ---------------------------------------------------------------------------
# OverlayWindow
# ---------------------------------------------------------------------------

TRANSPARENT_COLOR = "#010101"   # near-black as the colour-key for transparency


class OverlayWindow(QWidget):
    """
    Frameless, always-on-top, semi-transparent overlay.

    Modes
    -----
    Edit mode (edit_mode=True):  draggable, opaque enough to interact with.
    Play mode (edit_mode=False): click-through so it doesn't block the game.

    Usage::

        overlay = OverlayWindow()
        overlay.show()
        overlay.set_edit_mode(True)   # let user drag it
        overlay.set_edit_mode(False)  # restore click-through
    """

    position_changed: Signal = Signal(int, int)   # physical (x, y)

    def __init__(self, parent=None) -> None:
        super().__init__(
            parent,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        self._edit_mode  = False
        self._bg_color = QColor("#000000")
        self._border_color = QColor("#000000")
        self._border_width = 0
        self._phys_x = 50
        self._phys_y = 50
        self._drag_cursor0: tuple[int, int] | None = None  # cursor pos at drag start
        self._drag_window0: tuple[int, int] | None = None  # window pos at drag start
        self._drag_pos: QPoint | None = None               # non-Windows Qt fallback

        # Content layout managed externally — callers add widgets to self.
        self.setMinimumSize(QSize(0, 0))

        # Drift correction timer (every 2s, re-assert physical position)
        self._drift_timer = QTimer(self)
        self._drift_timer.timeout.connect(self._enforce_position)
        self._drift_timer.start(2000)

        # Drag poll timer — Windows only; polls GetAsyncKeyState instead of relying
        # on Qt mouse events (Tool windows don't reliably receive WM_LBUTTONDOWN).
        self._drag_poll_timer = QTimer(self)
        self._drag_poll_timer.setInterval(16)          # ~60 fps
        self._drag_poll_timer.timeout.connect(self._on_drag_poll)

        self._apply_mode_style()

    # ------------------------------------------------------------------
    # Position
    # ------------------------------------------------------------------

    def move_to_physical(self, x: int, y: int) -> None:
        self._phys_x = x
        self._phys_y = y
        self._enforce_position()

    def _enforce_position(self) -> None:
        if self.isVisible() and _IS_WIN:
            _set_window_pos_physical(
                _get_hwnd(self),
                self._phys_x, self._phys_y,
                self.width(), self.height(),
            )

    def get_physical_position(self) -> tuple[int, int]:
        if _IS_WIN and self.isVisible():
            pos = _get_window_pos_physical(_get_hwnd(self))
            if pos is not None:
                self._phys_x, self._phys_y = pos
        return (self._phys_x, self._phys_y)

    # ------------------------------------------------------------------
    # Edit / play mode
    # ------------------------------------------------------------------

    def set_edit_mode(self, enabled: bool) -> None:
        self._edit_mode = enabled
        if enabled:
            self._drift_timer.stop()
            if _IS_WIN:
                self._drag_poll_timer.start()
        else:
            self._drift_timer.start(2000)
            if _IS_WIN:
                self._drag_poll_timer.stop()
            self._drag_cursor0 = None
            self._drag_window0 = None
            self._drag_pos = None
        self._apply_mode_style()
        if _IS_WIN:
            _set_click_through(_get_hwnd(self), not enabled)
            QTimer.singleShot(60, self._reapply_click_through)
        self.setCursor(
            Qt.CursorShape.SizeAllCursor if enabled else Qt.CursorShape.ArrowCursor
        )

    def _reapply_click_through(self) -> None:
        """Ensure the WS_EX_TRANSPARENT state matches the current edit mode."""
        if _IS_WIN and self.isVisible():
            _set_click_through(_get_hwnd(self), not self._edit_mode)

    def _on_drag_poll(self) -> None:
        """
        Poll-based drag (Windows only, ~60 fps).

        Uses GetAsyncKeyState + geometric hit testing instead of Qt mouse
        events or WindowFromPoint.  This is reliable even when WS_EX_TRANSPARENT
        briefly flickers back (Qt or the OS may re-set it), because we enforce
        the correct EXSTYLE on every tick before checking cursor position.
        """
        if not self._edit_mode:
            return
        hwnd = _get_hwnd(self)

        # ── Always enforce click-through is DISABLED in edit mode ───────
        ex = _user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        if ex & WS_EX_TRANSPARENT:
            _set_click_through(hwnd, False)

        left_held = bool(_user32.GetAsyncKeyState(0x01) & 0x8000)  # VK_LBUTTON

        if left_held:
            cx, cy = _get_cursor_pos_physical()
            if self._drag_cursor0 is None:
                # Geometric hit test — works even if WS_EX_TRANSPARENT was
                # momentarily set (WindowFromPoint would return wrong HWND).
                rect = wt.RECT()
                _user32.GetWindowRect(hwnd, ctypes.byref(rect))
                if rect.left <= cx < rect.right and rect.top <= cy < rect.bottom:
                    self._drag_cursor0 = (cx, cy)
                    self._drag_window0 = (rect.left, rect.top)
            else:
                # Drag in progress — move window.
                nx = self._drag_window0[0] + (cx - self._drag_cursor0[0])
                ny = self._drag_window0[1] + (cy - self._drag_cursor0[1])
                _user32.SetWindowPos(
                    hwnd, HWND_TOPMOST, nx, ny,
                    self.width(), self.height(), SWP_NOACTIVATE,
                )
                self._phys_x = nx
                self._phys_y = ny
        else:
            # Button released — end drag.
            if self._drag_cursor0 is not None:
                self._drag_cursor0 = None
                self._drag_window0 = None

    def _apply_mode_style(self) -> None:
        if self._edit_mode:
            self._bg_color = QColor("#222222")
            self._border_color = QColor("#4fc3f7")
            self._border_width = 2
        else:
            self._bg_color = QColor("#000000")
            self._border_color = QColor("#000000")
            self._border_width = 0
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = self.rect().adjusted(
            self._border_width // 2,
            self._border_width // 2,
            -self._border_width // 2,
            -self._border_width // 2,
        )
        painter.setBrush(self._bg_color)
        if self._border_width > 0:
            painter.setPen(QPen(self._border_color, self._border_width))
        else:
            painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(rect, 8, 8)
        super().paintEvent(event)

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self._enforce_position()
        if _IS_WIN:
            # Defer so Qt finishes applying window attributes before we touch EXSTYLE.
            QTimer.singleShot(0, self._reapply_click_through)

    # Non-Windows Qt mouse drag fallback (unused on Windows; polling handles it).

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if not _IS_WIN and self._edit_mode and event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if not _IS_WIN and self._edit_mode and self._drag_pos is not None:
            if event.buttons() & Qt.MouseButton.LeftButton:
                delta = event.globalPosition().toPoint() - self._drag_pos
                self.move(self.pos() + delta)
                self._drag_pos = event.globalPosition().toPoint()
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if not _IS_WIN and self._edit_mode and event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = None
            pos = self.pos()
            self._phys_x, self._phys_y = pos.x(), pos.y()
            event.accept()
        else:
            super().mouseReleaseEvent(event)


# ---------------------------------------------------------------------------
# CalibrationOverlay
# ---------------------------------------------------------------------------

class CalibrationOverlay(QWidget):
    """
    Fullscreen, semi-transparent overlay for selecting a screen region or point.

    Emits ``region_selected(x, y, w, h)`` or ``point_selected(x, y)``
    using physical screen coordinates, then closes automatically.

    Call ``start_region()`` or ``start_point()``.
    """

    region_selected: Signal = Signal(int, int, int, int)
    point_selected:  Signal = Signal(int, int)
    cancelled:       Signal = Signal()

    _TIMEOUT_MS = 10_000

    def __init__(self, parent=None) -> None:
        super().__init__(
            parent,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowOpacity(0.35)
        self.setStyleSheet("background-color: #102030;")
        self.setCursor(Qt.CursorShape.CrossCursor)

        self._mode: str = ""           # "region" | "point"
        self._armed = False
        self._left_was_down = False
        self._press_pt: QPoint | None = None
        self._current_pt: QPoint | None = None
        self._press_physical: tuple[int, int] | None = None

        self._timeout = QTimer(self)
        self._timeout.setSingleShot(True)
        self._timeout.timeout.connect(self._on_cancel)

        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(16)
        self._poll_timer.timeout.connect(self._on_poll)

    # ------------------------------------------------------------------
    # Start modes
    # ------------------------------------------------------------------

    def start_region(self) -> None:
        self._mode = "region"
        self._show_fullscreen()

    def start_point(self) -> None:
        self._mode = "point"
        self._show_fullscreen()

    def _show_fullscreen(self) -> None:
        self._armed = False
        self._left_was_down = False
        geom = _get_virtual_screen_geometry()
        self.setGeometry(geom)
        self.show()
        self.raise_()
        if _IS_WIN:
            _set_window_pos_physical(
                _get_hwnd(self),
                geom.x(),
                geom.y(),
                geom.width(),
                geom.height(),
            )
        self.activateWindow()
        self.setFocus(Qt.FocusReason.ActiveWindowFocusReason)
        if _IS_WIN:
            self._poll_timer.start()
        else:
            self.grabMouse()
            self.grabKeyboard()
        QTimer.singleShot(150, self._arm_input)
        self._timeout.start(self._TIMEOUT_MS)

    def _arm_input(self) -> None:
        self._armed = True

    def _on_poll(self) -> None:
        if not _IS_WIN or not self._armed:
            return

        left_down = bool(_user32.GetAsyncKeyState(0x01) & 0x8000)
        px, py = _get_cursor_pos_physical()
        global_pt = QPoint(px, py)

        if self._mode == "point":
            if left_down and not self._left_was_down:
                self.point_selected.emit(px, py)
                self.close()
                return
            self._left_was_down = left_down
            return

        if left_down and not self._left_was_down:
            self._press_physical = (px, py)
            self._press_pt = global_pt
            self._current_pt = global_pt
            self.update()
        elif left_down and self._press_physical is not None:
            self._current_pt = global_pt
            self.update()
        elif not left_down and self._left_was_down and self._press_physical is not None:
            x1, y1 = self._press_physical
            x2, y2 = px, py
            x = min(x1, x2)
            y = min(y1, y2)
            w = abs(x2 - x1)
            h = abs(y2 - y1)
            if w > 4 and h > 4:
                self.region_selected.emit(x, y, w, h)
            self.close()
            return

        self._left_was_down = left_down

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if not self._armed and event.key() != Qt.Key.Key_Escape:
            event.accept()
            return
        if event.key() == Qt.Key.Key_Escape:
            self._on_cancel()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if _IS_WIN:
            event.accept()
            return
        if not self._armed:
            event.accept()
            return
        if event.button() == Qt.MouseButton.LeftButton:
            if self._mode == "point":
                px, py = _get_cursor_pos_physical()
                self.point_selected.emit(px, py)
                self.close()
            else:
                self._press_pt = event.globalPosition().toPoint()
                self._press_physical = _get_cursor_pos_physical()

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if _IS_WIN:
            event.accept()
            return
        if not self._armed:
            event.accept()
            return
        if self._mode == "region" and self._press_pt:
            self._current_pt = event.globalPosition().toPoint()
            self.update()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if _IS_WIN:
            event.accept()
            return
        if not self._armed:
            event.accept()
            return
        if self._mode == "region" and self._press_pt and event.button() == Qt.MouseButton.LeftButton:
            x2, y2 = _get_cursor_pos_physical()
            x1, y1 = self._press_physical or (x2, y2)
            x = min(x1, x2)
            y = min(y1, y2)
            w = abs(x2 - x1)
            h = abs(y2 - y1)
            if w > 4 and h > 4:
                self.region_selected.emit(x, y, w, h)
            self.close()

    def paintEvent(self, event) -> None:  # noqa: N802
        if self._mode == "region" and self._press_pt and self._current_pt:
            p = QPainter(self)
            p.setPen(QPen(QColor("#4fc3f7"), 2))
            r = QRect(self._press_pt, self._current_pt).normalized()
            # Map to widget-local coords
            tl = self.mapFromGlobal(r.topLeft())
            br = self.mapFromGlobal(r.bottomRight())
            p.drawRect(QRect(tl, br))
            p.end()

    def _on_cancel(self) -> None:
        self.cancelled.emit()
        self.close()

    def closeEvent(self, event) -> None:  # noqa: N802
        self._timeout.stop()
        self._poll_timer.stop()
        self._armed = False
        if not _IS_WIN:
            self.releaseMouse()
            self.releaseKeyboard()
        self._press_pt = None
        self._current_pt = None
        self._press_physical = None
        super().closeEvent(event)


class PreviewOverlay(QWidget):
    """Temporary fullscreen overlay that previews saved regions or points."""

    _TIMEOUT_MS = 2500

    def __init__(
        self,
        regions: dict[str, list[int]] | None = None,
        points: dict[str, list[int]] | None = None,
        parent=None,
    ) -> None:
        super().__init__(
            parent,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self._regions = regions or {}
        self._points = points or {}

        self._timeout = QTimer(self)
        self._timeout.setSingleShot(True)
        self._timeout.timeout.connect(self.close)

    def show_preview(self) -> None:
        self.setGeometry(_get_virtual_screen_geometry())
        self.show()
        self.raise_()
        self._timeout.start(self._TIMEOUT_MS)

    def _to_local(self, x: int, y: int) -> tuple[int, int]:
        geom = self.geometry()
        return (x - geom.x(), y - geom.y())

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.close()

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() == Qt.Key.Key_Escape:
            self.close()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 40))

        for name, region in self._regions.items():
            if len(region) != 4:
                continue
            x, y, w, h = region
            local_x, local_y = self._to_local(x, y)
            color = QColor("#33ff33") if "ally" in name else QColor("#ff3333")
            painter.setPen(QPen(color, 3))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(local_x, local_y, w, h)
            painter.setPen(QPen(color, 1))
            painter.drawText(local_x, max(16, local_y - 8), name.replace("_", " ").title())

        for name, point in self._points.items():
            if len(point) != 2:
                continue
            x, y = point
            local_x, local_y = self._to_local(x, y)
            color = QColor("#3de7ff")
            painter.setPen(QPen(color, 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(local_x - 6, local_y - 6, 12, 12)
            painter.drawLine(local_x - 10, local_y, local_x + 10, local_y)
            painter.drawLine(local_x, local_y - 10, local_x, local_y + 10)
            painter.drawText(local_x + 12, local_y - 10, name.title())

        painter.end()

    def closeEvent(self, event) -> None:  # noqa: N802
        self._timeout.stop()
        super().closeEvent(event)
