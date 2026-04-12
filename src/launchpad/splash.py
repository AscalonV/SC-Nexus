"""
SplashScreen — futuristic loading overlay shown during application startup.

Displayed before the main LaunchpadWindow is created so the user sees a
polished boot screen instead of a blank white rectangle.

Call ``mark_ready(callback)`` once module initialisation is complete.
The splash stays visible for a brief "READY" phase, then closes itself
and invokes *callback* (typically ``main_window.show``).
"""

from __future__ import annotations

import math

from PySide6.QtCore import Qt, QRect, QTimer
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPen,
)
from PySide6.QtWidgets import QApplication, QWidget

# ---------------------------------------------------------------------------
# Layout constants
# ---------------------------------------------------------------------------

_W = 520
_H = 300

_BG        = "#04080f"
_ACCENT    = "#4fc3f7"
_ACCENT2   = "#00b0ff"
_TEXT      = "#e8f0fe"
_DIM       = "#8899aa"
_TRACK     = "#0b1e36"

# How many ticks (at 40 ms each) to stay on-screen after init is done
_READY_HOLD_TICKS = 14   # ~560 ms


class SplashScreen(QWidget):
    """Frameless, window-stays-on-top splash screen with animated decorations."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool          # no taskbar entry
        )
        self.setFixedSize(_W, _H)
        self._center_on_screen()

        self._tick: int        = 0
        self._scan_y: float    = 0.0   # sweeping scanline y
        self._shim_pos: float  = -0.35 # shimmer band x as fraction of bar width

        self._ready:     bool  = False
        self._done_tick: int   = -1
        self._callback         = None

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)
        self._timer.start(40)    # 25 fps

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def mark_ready(self, callback) -> None:
        """Signal that initialisation is complete.

        *callback* is invoked after a short READY display phase, just
        before the splash closes.
        """
        self._ready     = True
        self._done_tick = self._tick
        self._callback  = callback

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _center_on_screen(self) -> None:
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(
            screen.center().x() - _W // 2,
            screen.center().y() - _H // 2,
        )

    def _on_tick(self) -> None:
        self._tick     += 1
        self._scan_y    = (self._scan_y + 1.5) % _H
        self._shim_pos  = (self._shim_pos + 0.035) % 1.35  # wraps back to -0.35 effectively

        if self._ready and self._done_tick >= 0:
            if self._tick - self._done_tick >= _READY_HOLD_TICKS:
                self._timer.stop()
                self.close()
                if self._callback is not None:
                    self._callback()
                return

        self.update()

    # ------------------------------------------------------------------
    # Painting
    # ------------------------------------------------------------------

    def paintEvent(self, _event) -> None:   # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = _W, _H

        # ── Background ────────────────────────────────────────────────
        p.fillRect(0, 0, w, h, QColor(_BG))

        # ── Dot grid ──────────────────────────────────────────────────
        dot_c = QColor(79, 195, 247, 16)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(dot_c)
        step = 22
        for gx in range(step, w, step):
            for gy in range(step, h, step):
                p.drawEllipse(QRect(gx - 1, gy - 1, 2, 2))

        # ── Sweeping scanline ─────────────────────────────────────────
        sy = int(self._scan_y)
        p.fillRect(0, sy,     w, 1, QColor(79, 195, 247, 18))
        p.fillRect(0, sy - 1, w, 1, QColor(79, 195, 247,  7))

        # ── Outer border ──────────────────────────────────────────────
        m = 12
        p.setPen(QPen(QColor(_ACCENT), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(m, m, w - 2 * m, h - 2 * m)

        # ── Corner brackets ───────────────────────────────────────────
        clen = 22
        p.setPen(QPen(QColor(_ACCENT), 3))
        corners = [
            (m,         m,         1,  1),
            (w - m,     m,        -1,  1),
            (m,         h - m,     1, -1),
            (w - m,     h - m,    -1, -1),
        ]
        for cx, cy, dx, dy in corners:
            p.drawLine(cx, cy, cx + dx * clen, cy)
            p.drawLine(cx, cy, cx, cy + dy * clen)

        # ── Corner accent dots ────────────────────────────────────────
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 176, 255, 200))
        for cx, cy, _, __ in corners:
            p.drawEllipse(QRect(cx - 3, cy - 3, 6, 6))

        # ── Title: "SC NEXUS" ─────────────────────────────────────────
        title_font = QFont("Segoe UI", 40, QFont.Weight.Bold)
        p.setFont(title_font)
        # soft glow shadow
        p.setPen(QColor(0, 176, 255, 55))
        p.drawText(QRect(3, 57, w, 60), Qt.AlignmentFlag.AlignHCenter, "SC NEXUS")
        # main text
        p.setPen(QColor(_TEXT))
        p.drawText(QRect(0, 54, w, 60), Qt.AlignmentFlag.AlignHCenter, "SC NEXUS")

        # ── Subtitle ─────────────────────────────────────────────────
        sub_font = QFont("Segoe UI", 9)
        sub_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 5)
        p.setFont(sub_font)
        p.setPen(QColor(_ACCENT))
        p.drawText(QRect(0, 116, w, 22), Qt.AlignmentFlag.AlignHCenter, "NEXUS CONTROL SYSTEM")

        # ── Horizontal separator ──────────────────────────────────────
        sep_y = 147
        g = QLinearGradient(50, sep_y, w - 50, sep_y)
        g.setColorAt(0.0, QColor(79, 195, 247,   0))
        g.setColorAt(0.3, QColor(79, 195, 247, 200))
        g.setColorAt(0.7, QColor(79, 195, 247, 200))
        g.setColorAt(1.0, QColor(79, 195, 247,   0))
        p.setPen(QPen(QBrush(g), 1))
        p.drawLine(50, sep_y, w - 50, sep_y)

        # ── Loading bar track ─────────────────────────────────────────
        bar_x, bar_y, bar_w, bar_h = 50, 195, w - 100, 5
        p.setPen(Qt.PenStyle.NoPen)
        p.fillRect(bar_x, bar_y, bar_w, bar_h, QColor(_TRACK))

        # ── Loading bar fill ──────────────────────────────────────────
        if self._ready:
            # Solid fill left→right
            full_g = QLinearGradient(bar_x, 0, bar_x + bar_w, 0)
            full_g.setColorAt(0, QColor(26, 82, 118))
            full_g.setColorAt(1, QColor(79, 195, 247))
            p.fillRect(bar_x, bar_y, bar_w, bar_h, QBrush(full_g))
            # Bright right tip
            p.fillRect(bar_x + bar_w - 2, bar_y - 1, 2, bar_h + 2,
                       QColor(220, 240, 255, 230))
        else:
            # Shimmer: an animated bright band traverses the track
            band_w = int(bar_w * 0.38)
            bx = bar_x + int(self._shim_pos * bar_w) - band_w
            clip_l = max(bar_x, bx)
            clip_r = min(bar_x + bar_w, bx + band_w)
            if clip_r > clip_l:
                shim_g = QLinearGradient(bx, 0, bx + band_w, 0)
                shim_g.setColorAt(0.0, QColor(79, 195, 247,   0))
                shim_g.setColorAt(0.4, QColor(79, 195, 247, 180))
                shim_g.setColorAt(0.6, QColor(79, 195, 247, 200))
                shim_g.setColorAt(1.0, QColor(79, 195, 247,   0))
                p.fillRect(clip_l, bar_y, clip_r - clip_l, bar_h, QBrush(shim_g))

        # ── Pulsing dots ──────────────────────────────────────────────
        if not self._ready:
            dot_y = 222
            for i in range(3):
                phase = math.radians((self._tick * 10 + i * 120) % 360)
                alpha = int(80 + 100 * (1 + math.sin(phase)) / 2)
                dc = QColor(79, 195, 247, alpha)
                dx = w // 2 - 13 + i * 13
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(dc)
                p.drawEllipse(QRect(dx, dot_y, 8, 8))

        # ── Status text ───────────────────────────────────────────────
        status_font = QFont("Segoe UI", 8)
        status_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2)
        p.setFont(status_font)
        p.setPen(QColor(136, 153, 170, 190))
        status_text = "READY" if self._ready else "INITIALIZING ..."
        p.drawText(QRect(0, 240, w, 22), Qt.AlignmentFlag.AlignHCenter, status_text)

        # ── Version chip (bottom-right) ───────────────────────────────
        ver_font = QFont("Segoe UI", 8)
        p.setFont(ver_font)
        p.setPen(QColor(79, 195, 247, 80))
        p.drawText(QRect(0, 268, w - m - 6, 18), Qt.AlignmentFlag.AlignRight, "v2.0.0")

        p.end()


# ---------------------------------------------------------------------------
# Subprocess entry-point
# ---------------------------------------------------------------------------

def run_splash_process(ready_event) -> None:
    """Run the splash screen in an isolated subprocess.

    Launched by ``main.py`` via ``multiprocessing.Process``.
    Has its own ``QApplication`` so its animation timer can never be
    starved by whatever the main process is doing.

    The function polls *ready_event* every 50 ms; once it is set the
    splash transitions to READY, holds briefly, then exits.
    """
    import sys as _sys

    # Per-process DPI awareness (not inherited from parent on Windows).
    if _sys.platform == "win32":
        try:
            import ctypes as _ct
            _ct.windll.user32.SetProcessDpiAwarenessContext(-4)
        except Exception:
            try:
                _ct.windll.shcore.SetProcessDpiAwareness(2)
            except Exception:
                pass

    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QFont
    from PySide6.QtCore import QTimer

    app = QApplication([_sys.argv[0]])
    app.setApplicationName("SC Nexus")
    app.setFont(QFont("Segoe UI", 10))

    splash = SplashScreen()
    splash.show()

    def _poll() -> None:
        if ready_event.is_set():
            _poll_timer.stop()
            splash.mark_ready(app.quit)

    _poll_timer = QTimer()
    _poll_timer.timeout.connect(_poll)
    _poll_timer.start(50)

    app.exec()
