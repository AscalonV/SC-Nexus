"""Legacy-aligned pie chart widget for the Combat Analyzer pie tab."""
from __future__ import annotations

import math
from typing import NamedTuple

from PySide6.QtCore import QPoint, QRect, Qt, Signal
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget


class PieSegment(NamedTuple):
    label: str
    value: float
    color: str


_BG = QColor("#080f1a")
_TEXT = QColor("#e8f0fe")
_MUTED = QColor("#8899aa")
_ACCENT = QColor("#4fc3f7")
_ACCENT_DARK = QColor("#1e3050")


def _darken(hex_color: str, factor: float = 0.3) -> QColor:
    color = QColor(hex_color)
    return QColor(
        int(color.red() * factor),
        int(color.green() * factor),
        int(color.blue() * factor),
    )


def _fmt(value: float) -> str:
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"{value / 1_000:.1f}K"
    return f"{value:.0f}"


class PieChartWidget(QWidget):
    wedge_selected: Signal = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._segments: list[PieSegment] = []
        self._angles: list[tuple[float, float]] = []
        self._selected = ""
        self._hover_idx = -1
        self._click_map: list[str] = []
        self._label_hits: list[tuple[QRect, str]] = []
        self._team_a_count = 0
        self._team_b_count = 0
        self._winner_team: str | None = None

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(220, 220)
        self.setMouseTracking(True)

    def set_data(self, segments: list[PieSegment]) -> None:
        self._segments = [segment for segment in segments if segment.value > 0]
        self._click_map = [segment.label for segment in self._segments]
        self._compute_angles()
        if self._selected and self._selected not in self._click_map:
            self._selected = ""
        self._hover_idx = -1
        self.update()

    def set_summary(self, team_a_count: int, team_b_count: int, winner_team: str | None) -> None:
        self._team_a_count = team_a_count
        self._team_b_count = team_b_count
        self._winner_team = winner_team
        self.update()

    def clear(self) -> None:
        self._segments = []
        self._angles = []
        self._click_map = []
        self._label_hits = []
        self._selected = ""
        self._hover_idx = -1
        self._team_a_count = 0
        self._team_b_count = 0
        self._winner_team = None
        self.update()

    def set_selected(self, name: str) -> None:
        self._selected = name
        self.update()

    @property
    def selected(self) -> str:
        return self._selected

    def paintEvent(self, _event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), _BG)

        if not self._segments:
            painter.setPen(_MUTED)
            painter.setFont(QFont("Segoe UI", 10))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No data")
            painter.end()
            return

        width = self.width()
        height = self.height()
        self._label_hits = []
        cx = width / 2
        cy = height / 2
        radius = min(width, height) * 0.33
        inner_radius = radius * 0.6
        label_radius = radius + 40
        total = sum(segment.value for segment in self._segments)

        painter.setPen(QPen(_ACCENT_DARK, 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(
            QRect(
                int(cx - radius - 5),
                int(cy - radius - 5),
                int(2 * radius + 10),
                int(2 * radius + 10),
            )
        )

        painter.setPen(_TEXT)
        summary_font = QFont("Segoe UI", 10)
        painter.setFont(summary_font)
        metrics = QFontMetrics(summary_font)
        team_a_text = f"Team A: {self._team_a_count}"
        team_b_text = f"Team B: {self._team_b_count}"
        team_a_rect = QRect(width - 140, 6, 130, 16)
        team_b_rect = QRect(width - 140, 20, 130, 16)
        painter.drawText(team_a_rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, team_a_text)
        painter.drawText(team_b_rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, team_b_text)
        painter.setPen(_ACCENT)
        if self._winner_team == "A":
            text_x = team_a_rect.right() - metrics.horizontalAdvance(team_a_text)
            painter.drawText(QRect(text_x - 16, team_a_rect.top(), 12, team_a_rect.height()), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, "★")
        if self._winner_team == "B":
            text_x = team_b_rect.right() - metrics.horizontalAdvance(team_b_text)
            painter.drawText(QRect(text_x - 16, team_b_rect.top(), 12, team_b_rect.height()), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, "★")

        labels_right: list[dict] = []
        labels_left: list[dict] = []

        for segment, (start_angle, span_angle) in zip(self._segments, self._angles):
            has_selection = bool(self._selected)
            is_selected = self._selected == segment.label if has_selection else False
            base_color = QColor(segment.color)
            draw_color = _darken(segment.color, 0.3) if (has_selection and not is_selected) else base_color

            painter.setBrush(draw_color)
            painter.setPen(QPen(_BG, 1))

            draw_span = max(span_angle, 0.5)
            painter.drawPie(
                QRect(int(cx - radius), int(cy - radius), int(2 * radius), int(2 * radius)),
                int((start_angle - draw_span) * 16),
                int(draw_span * 16),
            )

            mid_angle = (start_angle - span_angle / 2) % 360
            mid_radians = math.radians(mid_angle)
            rim_x = cx + math.cos(mid_radians) * radius
            rim_y = cy - math.sin(mid_radians) * radius
            ideal_x = cx + math.cos(mid_radians) * label_radius
            ideal_y = cy - math.sin(mid_radians) * label_radius
            is_right = mid_angle <= 90 or mid_angle >= 270

            entry = {
                "name": segment.label,
                "pct": (segment.value / total) if total else 0.0,
                "lx": ideal_x,
                "ly": ideal_y,
                "rim_x": rim_x,
                "rim_y": rim_y,
                "is_right": is_right,
                "col": _TEXT if (not has_selection or is_selected) else _MUTED,
            }
            if is_right:
                labels_right.append(entry)
            else:
                labels_left.append(entry)

        self._draw_inner_hole(painter, cx, cy, inner_radius)
        self._layout_labels(labels_right, cx, cy, radius, height, True)
        self._layout_labels(labels_left, cx, cy, radius, height, False)

        tail_len = 20
        painter.setPen(QPen(QColor("#5a7090"), 1))
        for label in labels_right + labels_left:
            tail_x = label["lx"] - tail_len if label["is_right"] else label["lx"] + tail_len
            painter.drawLine(int(label["rim_x"]), int(label["rim_y"]), int(tail_x), int(label["ly"]))
            painter.drawLine(int(tail_x), int(label["ly"]), int(label["lx"]), int(label["ly"]))

            text_x = label["lx"] + (5 if label["is_right"] else -5)
            rect = QRect(int(text_x) - (0 if label["is_right"] else 160), int(label["ly"] - 16), 160, 32)
            alignment = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            if not label["is_right"]:
                alignment = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            painter.setPen(label["col"])
            painter.setFont(QFont("Segoe UI", 9))
            painter.drawText(rect, alignment, f"{label['name']}\n{label['pct'] * 100:.1f}%")
            self._label_hits.append((rect.adjusted(-4, -2, 4, 2), label["name"]))

        self._draw_inner_hole(painter, cx, cy, inner_radius)
        if self._selected:
            center_value = next((segment.value for segment in self._segments if segment.label == self._selected), total)
            center_label = self._selected if len(self._selected) <= 12 else self._selected[:10] + "..."
        else:
            center_value = total
            center_label = "Total"
        painter.setPen(_MUTED)
        painter.setFont(QFont("Segoe UI", 10))
        painter.drawText(QRect(int(cx - inner_radius), int(cy - inner_radius), int(2 * inner_radius), int(inner_radius)), Qt.AlignmentFlag.AlignCenter, center_label)
        painter.setPen(_ACCENT)
        painter.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        painter.drawText(QRect(int(cx - inner_radius), int(cy - 2), int(2 * inner_radius), int(inner_radius)), Qt.AlignmentFlag.AlignCenter, _fmt(center_value))
        painter.end()

    def _draw_inner_hole(self, painter: QPainter, cx: float, cy: float, inner_radius: float) -> None:
        painter.setBrush(_BG)
        painter.setPen(QPen(_ACCENT_DARK, 1))
        painter.drawEllipse(QRect(int(cx - inner_radius), int(cy - inner_radius), int(2 * inner_radius), int(2 * inner_radius)))

    def _layout_labels(
        self,
        labels: list[dict],
        cx: float,
        cy: float,
        radius: float,
        height: int,
        is_right_group: bool,
    ) -> None:
        if not labels:
            return

        labels.sort(key=lambda label: label["ly"])
        min_dist = 32
        changed = True
        iterations = 0
        while changed and iterations < 20:
            changed = False
            iterations += 1

            for i in range(len(labels) - 1):
                if labels[i + 1]["ly"] < labels[i]["ly"] + min_dist:
                    labels[i + 1]["ly"] = labels[i]["ly"] + min_dist
                    changed = True

            if labels[-1]["ly"] > height - 10:
                labels[-1]["ly"] = height - 10
                changed = True
                for i in range(len(labels) - 1, 0, -1):
                    if labels[i - 1]["ly"] > labels[i]["ly"] - min_dist:
                        labels[i - 1]["ly"] = labels[i]["ly"] - min_dist

            if labels[0]["ly"] < 10:
                labels[0]["ly"] = 10
                changed = True
                for i in range(len(labels) - 1):
                    if labels[i + 1]["ly"] < labels[i]["ly"] + min_dist:
                        labels[i + 1]["ly"] = labels[i]["ly"] + min_dist

        tail_len = 20
        min_clearance = radius + 20
        min_radius_sq = (radius + 25) ** 2
        for label in labels:
            if is_right_group:
                min_x = cx + min_clearance + tail_len
                if label["lx"] < min_x:
                    label["lx"] = min_x
            else:
                max_x = cx - min_clearance - tail_len
                if label["lx"] > max_x:
                    label["lx"] = max_x

            dx = label["lx"] - cx
            dy = label["ly"] - cy
            dist_sq = dx * dx + dy * dy
            if dist_sq < min_radius_sq:
                required_dx = math.sqrt(max(0.0, min_radius_sq - dy * dy))
                if is_right_group:
                    label["lx"] = max(label["lx"], cx + required_dx)
                else:
                    label["lx"] = min(label["lx"], cx - required_dx)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        idx = self._hit_test(event.pos())
        if idx != self._hover_idx:
            self._hover_idx = idx
            self.update()

    def leaveEvent(self, _event) -> None:  # noqa: N802
        if self._hover_idx != -1:
            self._hover_idx = -1
            self.update()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() != Qt.MouseButton.LeftButton:
            return
        idx = self._hit_test(event.pos())
        if 0 <= idx < len(self._click_map):
            name = self._click_map[idx]
            self._selected = "" if self._selected == name else name
        else:
            self._selected = ""
        self.update()
        self.wedge_selected.emit(self._selected)

    def _compute_angles(self) -> None:
        total = sum(segment.value for segment in self._segments)
        if total == 0:
            self._angles = []
            return
        self._angles = []
        cursor = 90.0
        full_slice = len(self._segments) == 1
        for segment in self._segments:
            span = 360.0 * segment.value / total
            if full_slice:
                span = 359.999
            self._angles.append((cursor, span))
            cursor -= span

    def _hit_test(self, pos: QPoint) -> int:
        for rect, name in self._label_hits:
            if rect.contains(pos):
                try:
                    return self._click_map.index(name)
                except ValueError:
                    return -1
        if not self._angles:
            return -1
        width = self.width()
        height = self.height()
        cx = width / 2
        cy = height / 2
        radius = min(width, height) * 0.33
        inner_radius = radius * 0.60
        dx = pos.x() - cx
        dy = pos.y() - cy
        dist = math.hypot(dx, dy)
        if dist < inner_radius or dist > radius + 6:
            return -1
        angle = math.degrees(math.atan2(-dy, dx)) % 360
        for index, (start_angle, span_angle) in enumerate(self._angles):
            end_angle = (start_angle - span_angle) % 360
            if _in_range(angle, end_angle, start_angle % 360):
                return index
        return -1


def _in_range(angle: float, lo: float, hi: float) -> bool:
    if lo <= hi:
        return lo <= angle <= hi
    return angle >= lo or angle <= hi
