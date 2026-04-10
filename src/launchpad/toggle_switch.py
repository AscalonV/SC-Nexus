"""
ToggleSwitch — a custom on/off toggle control built with QPainter.

Replaces the absent QCheckBox toggle appearance in Qt and gives
a clean, modern feel that fits the dark SC Nexus theme.
"""

from __future__ import annotations

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QPoint,
    QPropertyAnimation,
    Qt,
    Signal,
)
from PySide6.QtGui import QColor, QPainter, QPainterPath
from PySide6.QtWidgets import QAbstractButton, QSizePolicy


_COLOR_ON  = QColor("#4fc3f7")
_COLOR_OFF = QColor("#2e4057")
_COLOR_KNOB = QColor("#ffffff")

_WIDTH  = 46
_HEIGHT = 24


class ToggleSwitch(QAbstractButton):
    """Animated toggle switch.  Drop-in replacement for QCheckBox when you
    want a pill-shaped on/off control."""

    toggled: Signal = Signal(bool)  # type: ignore[assignment]  # shadow parent

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setFixedSize(_WIDTH, _HEIGHT)

        # Knob position: 0 = fully left (off), 1 = fully right (on)
        self._knob_pos: float = 0.0

        self._anim = QPropertyAnimation(self, b"knob_pos", self)
        self._anim.setDuration(160)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutQuad)

        self.clicked.connect(self._on_clicked)

    # ------------------------------------------------------------------
    # Animated property
    # ------------------------------------------------------------------

    def _get_knob_pos(self) -> float:
        return self._knob_pos

    def _set_knob_pos(self, value: float) -> None:
        self._knob_pos = value
        self.update()

    knob_pos = Property(float, _get_knob_pos, _set_knob_pos)

    # ------------------------------------------------------------------
    # Interaction
    # ------------------------------------------------------------------

    def _on_clicked(self) -> None:
        target = 1.0 if self.isChecked() else 0.0
        self._anim.stop()
        self._anim.setStartValue(self._knob_pos)
        self._anim.setEndValue(target)
        self._anim.start()
        self.toggled.emit(self.isChecked())

    def setChecked(self, checked: bool) -> None:  # type: ignore[override]
        super().setChecked(checked)
        self._knob_pos = 1.0 if checked else 0.0
        self.update()

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        r = _HEIGHT / 2
        track_color = _COLOR_ON if self.isChecked() else _COLOR_OFF

        # Draw track (rounded rect)
        path = QPainterPath()
        path.addRoundedRect(0, 0, _WIDTH, _HEIGHT, r, r)
        p.fillPath(path, track_color)

        # Draw knob
        margin = 3
        knob_diam = _HEIGHT - 2 * margin
        travel = _WIDTH - knob_diam - 2 * margin
        knob_x = margin + int(self._knob_pos * travel)
        knob_y = margin

        p.setBrush(_COLOR_KNOB)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPoint(int(knob_x + knob_diam / 2), int(knob_y + knob_diam / 2)),
                      knob_diam // 2, knob_diam // 2)

        p.end()

    def sizeHint(self):  # noqa: N802
        from PySide6.QtCore import QSize
        return QSize(_WIDTH, _HEIGHT)
