"""
TeamsView — player-card view showing Team A vs Team B.

Layout
------
  Top bar: Sort by ▾  |  Order ▾
  ┌──────────── QSplitter ────────────┐
  │  _TeamPanel A  │  _TeamPanel B   │
  │  ┌──────────┐  │  ┌──────────┐  │
  │  │_PlayerCard│  │  │_PlayerCard│  │
  │  │  ...      │  │  │  ...      │  │
  └──────────────────────────────────┘

Each _PlayerCard shows:
  Name label + [Show Breakdown] button
  4 × {label | progress bar | value} rows:
      Damage Dealt, Damage Taken, Healing Dealt, Self-Heal
"""
from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from src.modules.combat_analysis.parser import Fight, ParticipantStats

# ---------------------------------------------------------------------------
# Colours / style helpers
# ---------------------------------------------------------------------------
_BG      = "#0d1b2a"
_BG2     = "#080f1a"
_BORDER  = "#1e3050"
_ACCENT  = "#4fc3f7"
_TEXT    = "#e8f0fe"
_SUBTEXT = "#8899aa"
_TEAM_A  = "#4fc3f7"
_TEAM_B  = "#ef9a9a"
_WIN_CLR = "#ffd54f"

_COMBO_STYLE = (
    f"QComboBox{{background-color:{_BG};color:{_TEXT};border:1px solid {_BORDER};"
    f"border-radius:4px;padding:2px 6px;}}"
    f"QComboBox::drop-down{{border:none;}}"
    f"QComboBox QAbstractItemView{{background-color:{_BG};color:{_TEXT};"
    f"selection-background-color:#1a3560;}}"
)
_BTN_SMALL = (
    "QPushButton{background:transparent;color:#8899aa;border:1px solid #1e3050;"
    "border-radius:3px;padding:2px 6px;font-size:10px}"
    "QPushButton:hover{color:#e8f0fe;border-color:#4fc3f7}"
)

_SCROLL_STYLE = (
    "QScrollArea{border:none;background:transparent;}"
    "QScrollBar:vertical{background:#09121f;width:12px;margin:0;border-left:1px solid #12253f;}"
    "QScrollBar::handle:vertical{background:#1e3050;min-height:28px;border-radius:5px;margin:2px;}"
    "QScrollBar::handle:vertical:hover{background:#4fc3f7;}"
    "QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0;background:transparent;border:none;}"
    "QScrollBar::add-page:vertical,QScrollBar::sub-page:vertical{background:#09121f;}"
)

_SORT_OPTIONS = ["Damage dealt", "Damage taken", "Healing", "Self-heal"]
_ORDER_OPTIONS = ["Descending", "Ascending"]


def _fmt(v: float) -> str:
    if v >= 1_000_000:
        return f"{v/1_000_000:.1f}M"
    if v >= 1_000:
        return f"{v/1_000:.1f}k"
    return str(int(v))


def _bar_style(color: str) -> str:
    return (
        f"QProgressBar{{background-color:#0b1828;border:none;border-radius:3px;"
        f"height:8px;max-height:8px;}}"
        f"QProgressBar::chunk{{background-color:{color};border-radius:3px;}}"
    )


# ---------------------------------------------------------------------------
# _PlayerCard
# ---------------------------------------------------------------------------

class _PlayerCard(QFrame):
    """Compact card widget for one player."""

    breakdown_requested = Signal(str)   # player name

    _ROWS = [
        ("Dmg Dealt",  "damage_dealt",  "#4fc3f7"),
        ("Dmg Taken",  "damage_taken",  "#ef9a9a"),
        ("Healing",    "healing_dealt", "#a5d6a7"),
        ("Self-Heal",  "self_heal",     "#ffe082"),
    ]

    def __init__(
        self,
        name:    str,
        stats:   ParticipantStats,
        maxvals: dict[str, float],
        name_fn: Callable[[str], str],
        color:   str,
        parent:  QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._name = name
        self.setStyleSheet(
            f"background-color: {_BG}; border: 1px solid {_BORDER};"
            f"border-left: 3px solid {color}; border-radius: 5px;"
        )
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(5)

        # --- Header row: name + breakdown button ---
        hdr = QHBoxLayout()
        hdr.setSpacing(6)
        name_lbl = QLabel(name_fn(name))
        name_lbl.setStyleSheet(f"color: {_TEXT}; font-weight: bold; font-size: 12px;")
        name_lbl.setWordWrap(False)
        hdr.addWidget(name_lbl, 1)
        bd_btn = QPushButton("Breakdown")
        bd_btn.setStyleSheet(_BTN_SMALL)
        bd_btn.setFixedHeight(20)
        bd_btn.clicked.connect(lambda: self.breakdown_requested.emit(self._name))
        hdr.addWidget(bd_btn)
        layout.addLayout(hdr)

        # --- Stat rows ---
        for label, attr, bar_color in self._ROWS:
            val    = getattr(stats, attr, 0.0)
            max_v  = maxvals.get(attr, 0.0)
            row    = QHBoxLayout()
            row.setSpacing(6)

            lbl = QLabel(label)
            lbl.setFixedWidth(62)
            lbl.setStyleSheet(f"color: {_SUBTEXT}; font-size: 10px;")
            row.addWidget(lbl)

            bar = QProgressBar()
            bar.setStyleSheet(_bar_style(bar_color))
            bar.setTextVisible(False)
            bar.setRange(0, 1000)
            frac = int(val / max_v * 1000) if max_v > 0 else 0
            bar.setValue(frac)
            row.addWidget(bar, 1)

            val_lbl = QLabel(_fmt(val))
            val_lbl.setFixedWidth(52)
            val_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            val_lbl.setStyleSheet(f"color: {_TEXT}; font-size: 10px;")
            row.addWidget(val_lbl)

            layout.addLayout(row)


# ---------------------------------------------------------------------------
# _TeamPanel
# ---------------------------------------------------------------------------

class _TeamPanel(QWidget):
    """Scrollable column of _PlayerCard widgets for one team."""

    breakdown_requested = Signal(str)

    def __init__(self, team_label: str, color: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._color = color
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self._header = QLabel(team_label)
        self._header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._header.setStyleSheet(
            f"color: {color}; font-size: 13px; font-weight: bold;"
            f"background-color: #0b1420; padding: 6px;"
            f"border-bottom: 1px solid {_BORDER};"
        )
        layout.addWidget(self._header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(_SCROLL_STYLE)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._cards_container = QWidget()
        self._cards_container.setStyleSheet("background: transparent;")
        self._cards_layout = QVBoxLayout(self._cards_container)
        self._cards_layout.setContentsMargins(8, 8, 8, 8)
        self._cards_layout.setSpacing(6)
        self._cards_layout.addStretch()
        scroll.setWidget(self._cards_container)
        layout.addWidget(scroll, 1)

        self._cards: list[_PlayerCard] = []

    def set_header(self, text: str, winner: bool = False) -> None:
        star = " ★" if winner else ""
        color = _WIN_CLR if winner else self._color
        self._header.setText(text + star)
        self._header.setStyleSheet(
            f"color: {color}; font-size: 13px; font-weight: bold;"
            f"background-color: #0b1420; padding: 6px;"
            f"border-bottom: 1px solid {_BORDER};"
        )

    def populate(
        self,
        players: list[str],
        stats:   dict[str, ParticipantStats],
        maxvals: dict[str, float],
        name_fn: Callable[[str], str],
        color_fn: Callable[[str], str] | None = None,
    ) -> None:
        layout = self._cards_layout
        # Clear old cards
        for card in self._cards:
            layout.removeWidget(card)
            card.deleteLater()
        self._cards.clear()
        # Remove stretch
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for name in players:
            if name not in stats:
                continue
            color = color_fn(name) if color_fn else self._color
            card = _PlayerCard(name, stats[name], maxvals, name_fn, color)
            card.breakdown_requested.connect(self.breakdown_requested)
            layout.addWidget(card)
            self._cards.append(card)

        layout.addStretch()

    def clear(self) -> None:
        for card in self._cards:
            card.deleteLater()
        self._cards.clear()


# ---------------------------------------------------------------------------
# TeamsView
# ---------------------------------------------------------------------------

class TeamsView(QWidget):
    """Side-by-side team view with player cards."""

    breakdown_requested: Signal = Signal(str)    # player name
    sort_changed:        Signal = Signal(str, str)  # sort_by, sort_order

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setStyleSheet(f"background-color: {_BG2};")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ---- Sort bar ----
        sort_bar = QFrame()
        sort_bar.setStyleSheet(
            f"background-color: #0b1420; border-bottom: 1px solid {_BORDER};"
        )
        sort_bar.setFixedHeight(40)
        bar_layout = QHBoxLayout(sort_bar)
        bar_layout.setContentsMargins(12, 0, 12, 0)
        bar_layout.setSpacing(8)

        bar_layout.addWidget(QLabel("Sort by:", styleSheet=f"color:{_SUBTEXT};font-size:11px;"))
        self._sort_combo = QComboBox()
        self._sort_combo.setStyleSheet(_COMBO_STYLE)
        self._sort_combo.addItems(_SORT_OPTIONS)
        self._sort_combo.setFixedWidth(130)
        bar_layout.addWidget(self._sort_combo)

        self._order_combo = QComboBox()
        self._order_combo.setStyleSheet(_COMBO_STYLE)
        self._order_combo.addItems(_ORDER_OPTIONS)
        self._order_combo.setFixedWidth(110)
        bar_layout.addWidget(self._order_combo)

        bar_layout.addStretch()
        root.addWidget(sort_bar)

        # ---- Team panels ----
        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._splitter.setChildrenCollapsible(False)
        self._splitter.setStyleSheet("background: transparent;")

        self._panel_a = _TeamPanel("Team A", _TEAM_A)
        self._panel_b = _TeamPanel("Team B", _TEAM_B)
        self._panel_a.breakdown_requested.connect(self.breakdown_requested)
        self._panel_b.breakdown_requested.connect(self.breakdown_requested)

        self._splitter.addWidget(self._panel_a)
        self._splitter.addWidget(self._panel_b)
        self._splitter.setStretchFactor(0, 1)
        self._splitter.setStretchFactor(1, 1)
        root.addWidget(self._splitter, 1)

        self._sort_combo.currentTextChanged.connect(self._emit_sort)
        self._order_combo.currentTextChanged.connect(self._emit_sort)

    def resizeEvent(self, event) -> None:  # noqa: N802
        self._equalize_panels()
        super().resizeEvent(event)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_sort(self, sort_by: str, sort_order: str) -> None:
        self._sort_combo.blockSignals(True)
        self._order_combo.blockSignals(True)
        idx = self._sort_combo.findText(sort_by)
        if idx >= 0:
            self._sort_combo.setCurrentIndex(idx)
        idx2 = self._order_combo.findText(sort_order)
        if idx2 >= 0:
            self._order_combo.setCurrentIndex(idx2)
        self._sort_combo.blockSignals(False)
        self._order_combo.blockSignals(False)

    def show_fight(
        self,
        fight:      Fight,
        stats:      dict[str, ParticipantStats],
        team_a:     list[str],
        team_b:     list[str],
        winner:     str | None,
        player_set: set[str],
        name_fn:    Callable[[str], str],
        color_fn:   Callable[[str], str] | None = None,
    ) -> None:
        sort_by    = self._sort_combo.currentText()
        sort_order = self._order_combo.currentText()
        reverse    = sort_order == "Descending"

        attr_map = {
            "Damage dealt": "damage_dealt",
            "Damage taken": "damage_taken",
            "Healing":      "healing_dealt",
            "Self-heal":    "self_heal",
        }
        attr = attr_map.get(sort_by, "damage_dealt")

        def _sorted(names: list[str]) -> list[str]:
            return sorted(
                names,
                key=lambda n: getattr(stats.get(n, ParticipantStats(n)), attr, 0.0),
                reverse=reverse,
            )

        sorted_a = _sorted(team_a)
        sorted_b = _sorted(team_b)

        # Max values across all players (for progress bar scale)
        all_stats = list(stats.values())
        maxvals = {
            "damage_dealt":  max((s.damage_dealt  for s in all_stats), default=1.0),
            "damage_taken":  max((s.damage_taken  for s in all_stats), default=1.0),
            "healing_dealt": max((s.healing_dealt for s in all_stats), default=1.0),
            "self_heal":     max((s.self_heal      for s in all_stats), default=1.0),
        }
        for k in maxvals:
            if maxvals[k] == 0:
                maxvals[k] = 1.0

        self._panel_a.set_header("Team A", winner == "A")
        self._panel_b.set_header("Team B", winner == "B")
        self._panel_a.populate(sorted_a, stats, maxvals, name_fn, color_fn)
        self._panel_b.populate(sorted_b, stats, maxvals, name_fn, color_fn)
        self._equalize_panels()

    def clear(self) -> None:
        self._panel_a.clear()
        self._panel_b.clear()

    def _equalize_panels(self) -> None:
        width = self._splitter.width()
        if width <= 0:
            return
        half = max(1, width // 2)
        self._splitter.setSizes([half, max(1, width - half)])

    # ------------------------------------------------------------------

    def _emit_sort(self) -> None:
        self.sort_changed.emit(
            self._sort_combo.currentText(),
            self._order_combo.currentText(),
        )
