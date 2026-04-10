"""
CombatAnalyzerView — main UI widget for the Combat Analyzer module.

Layout
------
  ┌───────────────── top bar ───────────────────────────────────┐
  │ [Fights ▾]  [Modes ▾]  [⟳ Reload]  [Analyze All]           │
  │ [Clear Cache]  [Open File]  [All Logs]  ··· [⚙]  [scope]   │
  └─────────────────────────────────────────────────────────────┘
  ┌──── QTabWidget ──────────────────────────────────────────────┐
  │  ● Pie Chart  |  ○ Teams                                     │
  │  ┌───── pie controls ──────────────────────────────────────┐ │
  │  │ [Dmg Dealt] [Dmg Recv] [Heal Done] [Heal Recv]  [self] │ │
  │  │ Team A  Team B  Players  Non-players                    │ │
  │  └─────────────────────────────────────────────────────────┘ │
  │  ┌── QSplitter ────────────────────────────────────────────┐ │
  │  │ PieChartWidget │ _PieDetailPanel (scrollable)           │ │
  │  └─────────────────────────────────────────────────────────┘ │
  │  ─────────────────────────────────────────────────────────── │
  │  ○ Teams tab: TeamsView                                      │
  └─────────────────────────────────────────────────────────────┘
  status bar
  (loading overlay — absolute positioned)
"""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import re
from typing import Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QPen
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMenu,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QSizePolicy,
    QSplitter,
    QStyledItemDelegate,
    QTabWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.modules.combat_analysis.parser import CombatEvent, Fight, ParticipantStats
from src.modules.combat_analysis.settings import CombatAnalysisSettings
from src.modules.combat_analysis.ui.breakdown_dialog import BreakdownDialog
from src.modules.combat_analysis.ui.pie_chart import PieChartWidget, PieSegment
from src.modules.combat_analysis.ui.teams_view import TeamsView

# ---------------------------------------------------------------------------
# Styles
# ---------------------------------------------------------------------------
_BG      = "#080f1a"
_BG_BAR  = "#0b1420"
_BG2     = "#0d1b2a"
_BORDER  = "#1e3050"
_ACCENT  = "#4fc3f7"
_TEXT    = "#e8f0fe"
_SUBTEXT = "#8899aa"


def _qss_url(path: Path) -> str:
    return path.resolve().as_posix()


_ASSET_DIR = Path(__file__).resolve().parent / "assets"
_TOGGLE_OFF_URL = _qss_url(_ASSET_DIR / "toggle_off.svg")
_TOGGLE_ON_URL = _qss_url(_ASSET_DIR / "toggle_on.svg")

_COMBO_STYLE = (
    f"QComboBox{{background-color:{_BG2};color:{_TEXT};"
    f"border:1px solid {_BORDER};border-radius:4px;padding:3px 8px;min-width:230px;}}"
    f"QComboBox::drop-down{{border:none;}}"
    f"QComboBox QAbstractItemView{{background-color:{_BG2};color:{_TEXT};"
    f"selection-background-color:#1a3560;}}"
)
_BTN = (
    "QPushButton{background:transparent;color:#8899aa;border:1px solid #1e3050;"
    "border-radius:4px;padding:3px 12px}"
    "QPushButton:hover{color:#e8f0fe;border-color:#4fc3f7}"
)
_BTN_ACCENT = (
    f"QPushButton{{background-color:{_ACCENT};color:#000;border:none;"
    f"border-radius:4px;padding:3px 14px;font-weight:bold;}}"
    f"QPushButton:hover{{background-color:#81d4fa;}}"
)
_TAB = (
    f"QTabWidget::pane{{border:1px solid {_BORDER};background-color:{_BG};}}"
    f"QTabBar::tab{{background-color:{_BG_BAR};color:{_SUBTEXT};"
    f"padding:6px 20px;border:1px solid {_BORDER};border-bottom:none;margin-right:2px;}}"
    f"QTabBar::tab:selected{{background-color:{_BG};color:{_ACCENT};"
    f"border-top:2px solid {_ACCENT};}}"
)
_TREE = (
    f"QTreeWidget{{background-color:{_BG2};alternate-background-color:#0a1525;"
    f"color:{_TEXT};border:1px solid {_BORDER};border-radius:4px;outline:none;}}"
    f"QTreeWidget::item{{border-bottom:1px solid #12253f;padding:1px 4px;}}"
    f"QTreeWidget::item:selected{{background-color:#1a3560;}}"
    f"QHeaderView::section{{background-color:{_BORDER};color:{_ACCENT};"
    f"padding:4px 6px;border:none;border-right:1px solid #12253f;font-weight:bold;}}"
    "QScrollBar:vertical{background:#09121f;width:12px;margin:0;border-left:1px solid #12253f;}"
    "QScrollBar::handle:vertical{background:#1e3050;min-height:28px;border-radius:5px;margin:2px;}"
    "QScrollBar::handle:vertical:hover{background:#4fc3f7;}"
    "QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0;background:transparent;border:none;}"
    "QScrollBar::add-page:vertical,QScrollBar::sub-page:vertical{background:#09121f;}"
    "QScrollBar:horizontal{background:#09121f;height:12px;margin:0;border-top:1px solid #12253f;}"
    "QScrollBar::handle:horizontal{background:#1e3050;min-width:28px;border-radius:5px;margin:2px;}"
    "QScrollBar::handle:horizontal:hover{background:#4fc3f7;}"
    "QScrollBar::add-line:horizontal,QScrollBar::sub-line:horizontal{width:0;background:transparent;border:none;}"
    "QScrollBar::add-page:horizontal,QScrollBar::sub-page:horizontal{background:#09121f;}"
    "QTreeCornerButton::section{background:#09121f;border:1px solid #12253f;}"
)
_CB = (
    f"QCheckBox{{color:{_TEXT};font-size:11px;spacing:4px;}}"
    f"QCheckBox::indicator{{width:14px;height:14px;image:url('{_TOGGLE_OFF_URL}');}}"
    f"QCheckBox::indicator:hover{{image:url('{_TOGGLE_OFF_URL}');}}"
    f"QCheckBox::indicator:checked{{image:url('{_TOGGLE_ON_URL}');}}"
)
_RB = (
    f"QRadioButton{{color:{_TEXT};font-size:11px;spacing:6px;}}"
    f"QRadioButton:checked{{color:{_TEXT};font-weight:bold;}}"
    f"QRadioButton::indicator{{width:14px;height:14px;image:url('{_TOGGLE_OFF_URL}');}}"
    f"QRadioButton::indicator:hover{{image:url('{_TOGGLE_OFF_URL}');}}"
    f"QRadioButton::indicator:checked{{image:url('{_TOGGLE_ON_URL}');}}"
)
_LBL_SEC = f"color:{_ACCENT};font-weight:bold;font-size:10px;padding:1px 0;"

_OVERLAY = f"background-color:rgba(8,15,26,210);border-radius:8px;"
_PROG = (
    f"QProgressBar{{background-color:{_BORDER};color:{_TEXT};"
    f"border-radius:4px;text-align:center;}}"
    f"QProgressBar::chunk{{background-color:{_ACCENT};border-radius:4px;}}"
)

_PANEL_CARD = f"background-color:{_BG};border:1px solid {_BORDER};border-radius:4px;"

_STAT_OPTS = ["Damage dealt", "Damage received", "Healing done", "Healing received"]
_STAT_EV   = {
    # (event_type, direction): stat key
    "Damage dealt":      ("damage", "out"),
    "Damage received":   ("damage", "in"),
    "Healing done":      ("heal",   "out"),
    "Healing received":  ("heal",   "in"),
}


def _fmt(v: float) -> str:
    if v >= 1_000_000:
        return f"{v/1_000_000:.1f}M"
    if v >= 1_000:
        return f"{v/1_000:.1f}k"
    return str(int(v))


# ---------------------------------------------------------------------------
# _SortableItem
# ---------------------------------------------------------------------------
class _SortableItem(QTreeWidgetItem):
    def __lt__(self, other: "QTreeWidgetItem") -> bool:
        tree = self.treeWidget()
        col = 0
        if tree is not None:
            sort_col = tree.property("_sort_column")
            if isinstance(sort_col, int):
                col = sort_col
        a = self.data(col, Qt.ItemDataRole.UserRole)
        b = other.data(col, Qt.ItemDataRole.UserRole)
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            return a < b
        return self.text(col) < other.text(col)


class _GridDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index) -> None:
        super().paint(painter, option, index)
        painter.save()
        painter.setPen(QPen(QColor(_BORDER), 1))
        painter.drawLine(option.rect.topRight(), option.rect.bottomRight())
        painter.drawLine(option.rect.bottomLeft(), option.rect.bottomRight())
        painter.restore()


# ---------------------------------------------------------------------------
# _PieDetailPanel
# ---------------------------------------------------------------------------
class _PieDetailPanel(QWidget):
    """Right-hand scrollable detail panel for the pie tab."""

    filters_changed: Signal = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._source_context = ""
        self._sources_collapsed = True
        self.source_checks: dict[str, QCheckBox] = {}

        self.setStyleSheet(f"background-color:{_BG};")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(8)
        self._header = QLabel("Select a slice to view details")
        self._header.setStyleSheet("color:#4fc3f7;font-weight:bold;font-size:12px;padding:0;")
        top_row.addWidget(self._header)
        top_row.addStretch()
        self._sources_toggle_btn = QPushButton("Sources ▸")
        self._sources_toggle_btn.setStyleSheet(_BTN)
        self._sources_toggle_btn.clicked.connect(self._toggle_sources)
        top_row.addWidget(self._sources_toggle_btn)
        root.addLayout(top_row)

        self._sources_body = QWidget()
        self._sources_body.setStyleSheet(f"background-color:{_BG2};border:1px solid {_BORDER};border-radius:4px;")
        body = QVBoxLayout(self._sources_body)
        body.setContentsMargins(8, 8, 8, 8)
        body.setSpacing(6)

        controls = QHBoxLayout()
        controls.setSpacing(6)
        self._sources_all_btn = QPushButton("Select All")
        self._sources_all_btn.setStyleSheet(_BTN)
        self._sources_all_btn.clicked.connect(lambda: self._set_all_sources(True))
        controls.addWidget(self._sources_all_btn)
        self._sources_none_btn = QPushButton("Unselect All")
        self._sources_none_btn.setStyleSheet(_BTN)
        self._sources_none_btn.clicked.connect(lambda: self._set_all_sources(False))
        controls.addWidget(self._sources_none_btn)
        controls.addStretch()
        body.addLayout(controls)

        self._sources_list = QVBoxLayout()
        self._sources_list.setContentsMargins(0, 0, 0, 0)
        self._sources_list.setSpacing(4)
        body.addLayout(self._sources_list)
        root.addWidget(self._sources_body)
        self._apply_sources_state()

        # -- Outgoing mode --
        out_row = QHBoxLayout()
        out_row.setContentsMargins(0, 0, 0, 0)
        out_row.setSpacing(8)
        out_label = QLabel("Group outgoing breakdown by:")
        out_label.setStyleSheet(_LBL_SEC)
        out_row.addWidget(out_label)
        self.rb_tgt  = QRadioButton("Target total")
        self.rb_src_total = QRadioButton("Source total")
        self.rb_src  = QRadioButton("Source detail")
        for rb in (self.rb_tgt, self.rb_src_total, self.rb_src):
            rb.setStyleSheet(_RB)
            out_row.addWidget(rb)
        out_row.addStretch()
        self.rb_tgt.setChecked(True)
        root.addLayout(out_row)

        top_tables = QGridLayout()
        top_tables.setContentsMargins(0, 0, 0, 0)
        top_tables.setHorizontalSpacing(8)
        top_tables.setVerticalSpacing(8)
        self.dmg_tree = _build_titled_tree_panel(
            top_tables,
            0,
            0,
            "Damage Dealt",
            ["Target", "Source", "Amount", "% of total"],
            [160, 220, 90, 90],
        )
        self.heal_tree = _build_titled_tree_panel(
            top_tables,
            0,
            1,
            "Healing Dealt",
            ["Target", "Source", "Amount", "% of total"],
            [160, 220, 90, 90],
        )
        root.addLayout(top_tables, 1)

        # -- Received mode --
        recv_row = QHBoxLayout()
        recv_row.setContentsMargins(0, 0, 0, 0)
        recv_row.setSpacing(8)
        recv_label = QLabel("Group incoming breakdown by:")
        recv_label.setStyleSheet(_LBL_SEC)
        recv_row.addWidget(recv_label)
        self.rb_recv_total = QRadioButton("Participant total")
        self.rb_recv_src_total = QRadioButton("Source total")
        self.rb_recv_src   = QRadioButton("Source detail")
        for rb in (self.rb_recv_total, self.rb_recv_src_total, self.rb_recv_src):
            rb.setStyleSheet(_RB)
            recv_row.addWidget(rb)
        recv_row.addStretch()
        self.rb_recv_total.setChecked(True)
        root.addLayout(recv_row)

        bottom_tables = QGridLayout()
        bottom_tables.setContentsMargins(0, 0, 0, 0)
        bottom_tables.setHorizontalSpacing(8)
        bottom_tables.setVerticalSpacing(8)
        self.rdmg_tree = _build_titled_tree_panel(
            bottom_tables,
            0,
            0,
            "Damage Received",
            ["Attacker", "Source", "Amount", "% of total"],
            [150, 220, 90, 90],
        )
        self.rheal_tree = _build_titled_tree_panel(
            bottom_tables,
            0,
            1,
            "Healing Received",
            ["Healer", "Source", "Amount", "% of total"],
            [150, 220, 90, 90],
        )
        root.addLayout(bottom_tables, 1)

    def clear(self) -> None:
        for t in (self.dmg_tree, self.heal_tree, self.rdmg_tree, self.rheal_tree):
            t.clear()
        self._header.setText("Select a slice to view details")
        self.clear_sources()

    def set_header_text(self, text: str) -> None:
        self._header.setText(text)

    def ensure_sources(self, context_key: str, sources: list[str]) -> None:
        if self._source_context == context_key:
            return
        self._source_context = context_key
        self.clear_sources(reset_context=False)
        if not sources:
            label = QLabel("No source info found; all entries shown")
            label.setStyleSheet(f"color:{_SUBTEXT};font-size:10px;")
            self._sources_list.addWidget(label)
            return

        row: QHBoxLayout | None = None
        for index, source in enumerate(sources):
            if index % 4 == 0:
                row = QHBoxLayout()
                row.setSpacing(6)
                self._sources_list.addLayout(row)
            cb = QCheckBox(source)
            cb.setStyleSheet(_CB)
            cb.setChecked(True)
            cb.stateChanged.connect(lambda _state: self.filters_changed.emit())
            self.source_checks[source] = cb
            if row is not None:
                row.addWidget(cb)
        if row is not None:
            row.addStretch()

    def selected_sources(self) -> set[str] | None:
        if not self.source_checks:
            return None
        return {src for src, cb in self.source_checks.items() if cb.isChecked()}

    def clear_sources(self, reset_context: bool = True) -> None:
        self.source_checks.clear()
        self._clear_layout(self._sources_list)
        if reset_context:
            self._source_context = ""

    def _toggle_sources(self) -> None:
        self._sources_collapsed = not self._sources_collapsed
        self._apply_sources_state()

    def _apply_sources_state(self) -> None:
        self._sources_body.setVisible(not self._sources_collapsed)
        self._sources_toggle_btn.setText("Sources ▸" if self._sources_collapsed else "Sources ▾")

    def _set_all_sources(self, enabled: bool) -> None:
        for cb in self.source_checks.values():
            cb.blockSignals(True)
            cb.setChecked(enabled)
            cb.blockSignals(False)
        self.filters_changed.emit()

    def _clear_layout(self, layout: QVBoxLayout | QHBoxLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            child_layout = item.layout()
            if child_layout is not None:
                self._clear_layout(child_layout)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()


def _make_tree(headers: list[str]) -> QTreeWidget:
    from PySide6.QtWidgets import QHeaderView as _HV
    t = QTreeWidget()
    t.setStyleSheet(_TREE)
    t.setAlternatingRowColors(True)
    t.setRootIsDecorated(False)
    t.setSortingEnabled(True)
    t.setColumnCount(len(headers))
    t.setHeaderLabels(headers)
    t.setItemDelegate(_GridDelegate(t))
    t.setProperty("_sort_column", 1 if len(headers) > 1 else 0)
    t.header().sortIndicatorChanged.connect(
        lambda section, _order, tree=t: tree.setProperty("_sort_column", section)
    )
    if len(headers) >= 4:
        t.header().setSectionResizeMode(0, _HV.ResizeMode.Stretch)
        t.header().setSectionResizeMode(1, _HV.ResizeMode.Stretch)
        t.header().setSectionResizeMode(2, _HV.ResizeMode.ResizeToContents)
        t.header().setSectionResizeMode(3, _HV.ResizeMode.ResizeToContents)
    elif len(headers) == 3:
        t.header().setSectionResizeMode(0, _HV.ResizeMode.Stretch)
        t.header().setSectionResizeMode(1, _HV.ResizeMode.ResizeToContents)
        t.header().setSectionResizeMode(2, _HV.ResizeMode.ResizeToContents)
    else:
        for c in range(len(headers)):
            t.header().setSectionResizeMode(c, _HV.ResizeMode.Stretch)
    t.setVerticalScrollMode(QTreeWidget.ScrollMode.ScrollPerPixel)
    t.setUniformRowHeights(True)
    t.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    return t


def _build_titled_tree_panel(
    layout: QGridLayout,
    row: int,
    column: int,
    title: str,
    headers: list[str],
    widths: list[int],
) -> QTreeWidget:
    frame = QFrame()
    frame.setStyleSheet(f"background-color:{_BG};border:1px solid {_BORDER};border-radius:4px;")
    frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    inner = QVBoxLayout(frame)
    inner.setContentsMargins(4, 4, 4, 4)
    inner.setSpacing(4)

    label = QLabel(title)
    label.setStyleSheet(_LBL_SEC)
    inner.addWidget(label)

    tree = _make_tree(headers)
    for index, width in enumerate(widths):
        tree.setColumnWidth(index, width)
    tree.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    inner.addWidget(tree, 1)

    layout.addWidget(frame, row, column)
    layout.setColumnStretch(column, 1)
    layout.setRowStretch(row, 1)
    return tree


# ---------------------------------------------------------------------------
# Main view
# ---------------------------------------------------------------------------

class CombatAnalyzerView(QWidget):
    """
    Main UI widget for the Combat Analyzer.

    Signals
    -------
    reload_requested        — Reload button
    open_file_requested     — Open File button
    show_all_logs_requested — All Logs button
    analyze_all_requested   — Analyze All button
    clear_cache_requested   — Clear Cache button
    settings_requested      — Settings cog button
    fight_selected(index)   — Fight combobox changed
    game_mode_toggled(mode, enabled)  — Modes menu action toggled
    sort_changed(sort_by, sort_order) — Teams sort changed
    """

    reload_requested:        Signal = Signal()
    open_file_requested:     Signal = Signal()
    show_all_logs_requested: Signal = Signal()
    analyze_all_requested:   Signal = Signal()
    clear_cache_requested:   Signal = Signal()
    settings_requested:      Signal = Signal()
    fight_selected:          Signal = Signal(int)
    game_mode_toggled:       Signal = Signal(str, bool)
    sort_changed:            Signal = Signal(str, str)

    def __init__(
        self,
        settings:      CombatAnalysisSettings,
        game_mode_map: dict[str, str],
        parent:        QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setStyleSheet(f"background-color:{_BG};")

        self._settings = settings
        self._game_mode_map = game_mode_map

        # Fight data (filled by show_fight)
        self._fight:      Fight | None                    = None
        self._stats:      dict[str, ParticipantStats]     = {}
        self._team_a:     list[str]                       = []
        self._team_b:     list[str]                       = []
        self._winner:     str | None                      = None
        self._player_set: set[str]                        = set()
        self._name_fn:    Callable[[str], str]            = lambda n: n
        self._color_fn:   Callable[[str], str] | None     = None

        self._selected_player: str = ""
        self._mode_actions:   dict[str, "QAction"] = {}   # type: ignore[name-defined]

        self._build_ui()

        # Apply saved settings
        self._teams_view.set_sort(settings.sort_by, settings.sort_order)
        self._set_pie_controls_from_settings()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_top_bar())

        self._tabs = QTabWidget()
        self._tabs.setStyleSheet(_TAB)
        root.addWidget(self._tabs, 1)

        self._tabs.addTab(self._build_pie_tab(), "Pie Chart")
        self._tabs.addTab(self._build_teams_tab(), "Teams")

        # Status bar
        self._status_bar = QLabel("Ready")
        self._status_bar.setStyleSheet(
            f"color:{_SUBTEXT};font-size:10px;padding:3px 12px;"
            f"border-top:1px solid {_BORDER};background-color:{_BG_BAR};"
        )
        root.addWidget(self._status_bar)

        # Loading overlay
        self._overlay = self._build_overlay()
        self._overlay.hide()

        self._tabs.currentChanged.connect(self._on_tab_changed)

    def _build_top_bar(self) -> QWidget:
        bar = QFrame()
        bar.setStyleSheet(
            f"background-color:{_BG_BAR};border-bottom:1px solid {_BORDER};"
        )
        bar.setFixedHeight(44)
        h = QHBoxLayout(bar)
        h.setContentsMargins(10, 0, 10, 0)
        h.setSpacing(6)

        # Fight selector
        self._fight_combo = QComboBox()
        self._fight_combo.setStyleSheet(_COMBO_STYLE)
        self._fight_combo.setPlaceholderText("— No fights loaded —")
        self._fight_combo.currentIndexChanged.connect(self._on_fight_changed)
        h.addWidget(self._fight_combo)

        # Game-mode filter button
        self._modes_btn = QPushButton("Modes ▾")
        self._modes_btn.setStyleSheet(_BTN)
        self._modes_menu = QMenu(self._modes_btn)
        self._modes_menu.setStyleSheet(
            f"QMenu{{background-color:{_BG2};color:{_TEXT};"
            f"border:1px solid {_BORDER};}}"
            f"QMenu::item:selected{{background-color:#1a3560;}}"
            f"QMenu::indicator{{width:13px;height:13px;}}"
        )
        self._modes_btn.setMenu(self._modes_menu)
        h.addWidget(self._modes_btn)

        _sep(h)

        # Action buttons
        btn_defs = [
            ("⟳ Reload",      self.reload_requested,        True),
            ("Analyze All",   self.analyze_all_requested,   False),
            ("Clear Cache",   self.clear_cache_requested,   False),
            ("Open File",     self.open_file_requested,     False),
            ("All Logs",      self.show_all_logs_requested, False),
        ]
        for label, sig, accent in btn_defs:
            btn = QPushButton(label)
            btn.setStyleSheet(_BTN_ACCENT if accent else _BTN)
            btn.clicked.connect(sig)
            h.addWidget(btn)

        h.addStretch(1)

        # Scope label
        self._scope_label = QLabel("")
        self._scope_label.setStyleSheet(f"color:{_SUBTEXT};font-size:10px;")
        h.addWidget(self._scope_label)

        # Settings
        self._settings_btn = QPushButton("⚙")
        self._settings_btn.setStyleSheet(_BTN)
        self._settings_btn.setToolTip("Settings")
        self._settings_btn.clicked.connect(self.settings_requested)
        h.addWidget(self._settings_btn)

        return bar

    def _build_pie_tab(self) -> QWidget:
        container = QWidget()
        container.setStyleSheet(f"background-color:{_BG};")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setStyleSheet("background:transparent;")
        self._pie_splitter = splitter

        left_panel = QFrame()
        left_panel.setStyleSheet(_PANEL_CARD)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(8, 8, 8, 8)
        left_layout.setSpacing(6)

        # -- Stat type checkboxes --
        ctrl1 = QHBoxLayout()
        ctrl1.setSpacing(14)
        stats_box = QHBoxLayout()
        stats_box.setSpacing(6)
        self._stat_cbs: dict[str, QCheckBox] = {}
        for stat in _STAT_OPTS:
            cb = QCheckBox(stat)
            cb.setStyleSheet(_CB)
            cb.setChecked(stat == self._settings.pie_stat)
            cb.stateChanged.connect(lambda _s, _st=stat: self._on_stat_clicked(_st))
            self._stat_cbs[stat] = cb
            stats_box.addWidget(cb)
        self._cb_self = QCheckBox("Show self-heal")
        self._cb_self.setStyleSheet(_CB)
        self._cb_self.setChecked(self._settings.include_self_heal)
        self._cb_self.stateChanged.connect(lambda _: self._refresh_pie())
        stats_box.addWidget(self._cb_self)
        ctrl1.addLayout(stats_box)
        ctrl1.addStretch()
        left_layout.addLayout(ctrl1)

        # -- Filter row --
        ctrl2 = QHBoxLayout()
        ctrl2.setSpacing(14)
        self._cb_team_a = QCheckBox("Team A")
        self._cb_team_b = QCheckBox("Team B")
        self._cb_players = QCheckBox("Player")
        self._cb_rest    = QCheckBox("Non-Player")
        for cb in (self._cb_team_a, self._cb_team_b, self._cb_players, self._cb_rest):
            cb.setStyleSheet(_CB)
            cb.setChecked(True)
        self._cb_team_a.stateChanged.connect(lambda _: self._refresh_pie())
        self._cb_team_b.stateChanged.connect(lambda _: self._refresh_pie())
        self._cb_players.stateChanged.connect(lambda _: self._refresh_pie())
        self._cb_rest.stateChanged.connect(lambda _: self._refresh_pie())
        ctrl2.addWidget(QLabel("Teams:", styleSheet=f"color:{_SUBTEXT};font-size:10px;"))
        ctrl2.addWidget(self._cb_team_a)
        ctrl2.addWidget(self._cb_team_b)
        ctrl2.addSpacing(18)
        ctrl2.addWidget(QLabel("Include Targets:", styleSheet=f"color:{_SUBTEXT};font-size:10px;"))
        ctrl2.addWidget(self._cb_players)
        ctrl2.addWidget(self._cb_rest)
        ctrl2.addStretch()
        left_layout.addLayout(ctrl2)

        self._pie_chart = PieChartWidget()
        self._pie_chart.wedge_selected.connect(self._on_wedge_selected)
        left_layout.addWidget(self._pie_chart, 1)
        splitter.addWidget(left_panel)

        self._detail_panel = _PieDetailPanel()
        self._detail_panel.setStyleSheet(_PANEL_CARD)
        # Only trigger on toggle-on to avoid double refresh (radio groups emit twice)
        self._detail_panel.rb_tgt.toggled.connect(lambda on: on and self._on_out_mode_changed())
        self._detail_panel.rb_src_total.toggled.connect(lambda on: on and self._on_out_mode_changed())
        self._detail_panel.rb_src.toggled.connect(lambda on: on and self._on_out_mode_changed())
        self._detail_panel.rb_recv_total.toggled.connect(lambda on: on and self._on_recv_mode_changed())
        self._detail_panel.rb_recv_src_total.toggled.connect(lambda on: on and self._on_recv_mode_changed())
        self._detail_panel.rb_recv_src.toggled.connect(lambda on: on and self._on_recv_mode_changed())
        self._detail_panel.filters_changed.connect(self._refresh_detail)
        splitter.addWidget(self._detail_panel)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)
        self._apply_pie_splitter_ratio()

        layout.addWidget(splitter, 1)
        return container

    def _build_teams_tab(self) -> QWidget:
        self._teams_view = TeamsView()
        self._teams_view.breakdown_requested.connect(self._on_breakdown_requested)
        self._teams_view.sort_changed.connect(self._on_sort_changed)
        return self._teams_view

    def _build_overlay(self) -> QWidget:
        overlay = QWidget(self)
        overlay.setStyleSheet(_OVERLAY)
        v = QVBoxLayout(overlay)
        v.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.setSpacing(10)

        self._prog_bar = QProgressBar()
        self._prog_bar.setStyleSheet(_PROG)
        self._prog_bar.setFixedWidth(320)
        self._prog_bar.setRange(0, 0)
        v.addWidget(self._prog_bar)

        self._prog_label = QLabel("Loading…")
        self._prog_label.setStyleSheet(f"color:{_TEXT};font-size:12px;background:transparent;")
        self._prog_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(self._prog_label)

        return overlay

    # ------------------------------------------------------------------
    # Public API (called by module)
    # ------------------------------------------------------------------

    def set_fights(self, labels: list[str]) -> None:
        self._fight_combo.blockSignals(True)
        self._fight_combo.clear()
        for lbl in labels:
            self._fight_combo.addItem(lbl)
        self._fight_combo.blockSignals(False)

    def select_fight(self, index: int) -> None:
        self._fight_combo.blockSignals(True)
        self._fight_combo.setCurrentIndex(index)
        self._fight_combo.blockSignals(False)
        self._on_fight_changed(index)

    def set_game_modes(self, modes: dict[str, str]) -> None:
        self._modes_menu.clear()
        self._mode_actions.clear()
        for key, display in sorted(modes.items(), key=lambda x: x[1]):
            action = self._modes_menu.addAction(display)
            action.setCheckable(True)
            action.setChecked(True)
            action.toggled.connect(lambda checked, k=key: self.game_mode_toggled.emit(k, checked))
            self._mode_actions[key] = action

    def set_disabled_modes(self, disabled: set[str]) -> None:
        for key, action in self._mode_actions.items():
            action.blockSignals(True)
            action.setChecked(key not in disabled)
            action.blockSignals(False)

    def show_loading(self, text: str = "Loading…") -> None:
        self._prog_bar.setRange(0, 0)
        self._prog_label.setText(text)
        self._overlay.setGeometry(self.rect())
        self._overlay.show()
        self._overlay.raise_()

    def hide_loading(self) -> None:
        self._overlay.hide()

    def update_progress(self, done: int, total: int, label: str = "") -> None:
        self._prog_bar.setRange(0, total)
        self._prog_bar.setValue(done)
        if label:
            self._prog_label.setText(label)

    def set_scope(self, filename: str | None) -> None:
        if filename:
            self._scope_label.setText(f"Log: {filename}")
        else:
            self._scope_label.setText("All logs")

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
        self._fight      = fight
        self._stats      = stats
        self._team_a     = team_a
        self._team_b     = team_b
        self._winner     = winner
        self._player_set = player_set
        self._name_fn    = name_fn
        self._color_fn   = color_fn

        self._selected_player = ""
        self._pie_chart.set_selected("")

        self._refresh_pie()
        self._teams_view.show_fight(
            fight, stats, team_a, team_b, winner, player_set, name_fn, color_fn
        )

    def _is_player_entity(self, name: str | None) -> bool:
        candidate = (name or "").strip()
        if not candidate:
            return False
        if re.match(r"^NPC\d+$", candidate, re.IGNORECASE):
            return False
        if candidate.upper() == "N/A":
            return False
        if "(" in candidate or ")" in candidate:
            return False
        if "  " in candidate:
            return False
        lowered = candidate.lower()
        if lowered.startswith("ship_") or lowered.startswith("module_") or lowered.startswith("weapon_"):
            return False
        return candidate in self._player_set

    def clear(self) -> None:
        self._fight_combo.clear()
        self._pie_chart.clear()
        self._detail_panel.clear()
        self._teams_view.clear()
        self._fight = None

    # ------------------------------------------------------------------
    # Resize
    # ------------------------------------------------------------------

    def resizeEvent(self, event) -> None:  # noqa: N802
        self._overlay.setGeometry(self.rect())
        self._apply_pie_splitter_ratio()
        self._refit_detail_trees()
        super().resizeEvent(event)

    def _apply_pie_splitter_ratio(self) -> None:
        splitter = getattr(self, "_pie_splitter", None)
        if splitter is None:
            return
        total = splitter.width()
        if total <= 0:
            return
        left = max(1, int(total * 0.4))
        splitter.setSizes([left, max(1, total - left)])

    def _refit_detail_trees(self) -> None:
        if not hasattr(self, "_detail_panel"):
            return
        for tree in (
            self._detail_panel.dmg_tree,
            self._detail_panel.heal_tree,
            self._detail_panel.rdmg_tree,
            self._detail_panel.rheal_tree,
        ):
            _fit_breakdown_tree_columns(tree, not tree.isColumnHidden(0), not tree.isColumnHidden(1))

    # ------------------------------------------------------------------
    # Internal slots
    # ------------------------------------------------------------------

    def _on_fight_changed(self, index: int) -> None:
        if index >= 0:
            self.fight_selected.emit(index)

    def _on_tab_changed(self, index: int) -> None:
        if index == 0:
            self._pie_chart.update()

    def _on_stat_clicked(self, stat: str) -> None:
        """Ensure only one stat checkbox is checked (radio-button behaviour)."""
        for s, cb in self._stat_cbs.items():
            cb.blockSignals(True)
            cb.setChecked(s == stat)
            cb.blockSignals(False)
        self._settings.pie_stat = stat
        self._settings.save()
        self._refresh_pie()

    def _on_wedge_selected(self, name: str) -> None:
        self._selected_player = name
        self._refresh_detail()

    def _on_breakdown_requested(self, player: str) -> None:
        if not self._fight:
            return
        dlg = BreakdownDialog(
            player     = player,
            fight      = self._fight,
            stats      = self._stats,
            player_set = self._player_set,
            name_fn    = self._name_fn,
            parent     = self,
        )
        dlg.exec()

    def _on_out_mode_changed(self) -> None:
        self._refresh_detail()

    def _on_recv_mode_changed(self) -> None:
        self._refresh_detail()

    def _on_sort_changed(self, sort_by: str, sort_order: str) -> None:
        self._settings.sort_by    = sort_by
        self._settings.sort_order = sort_order
        self._settings.save()
        self.sort_changed.emit(sort_by, sort_order)

    # ------------------------------------------------------------------
    # Pie data computation
    # ------------------------------------------------------------------

    def _current_stat(self) -> str:
        for s, cb in self._stat_cbs.items():
            if cb.isChecked():
                return s
        return "Damage dealt"

    def _refresh_pie(self) -> None:
        if not self._fight:
            self._pie_chart.clear()
            self._detail_panel.clear()
            return

        stat = self._current_stat()
        ev_type, direction = _STAT_EV.get(stat, ("damage", "out"))
        include_self = self._cb_self.isChecked()

        show_a    = self._cb_team_a.isChecked()
        show_b    = self._cb_team_b.isChecked()
        show_pl   = self._cb_players.isChecked()
        show_rest = self._cb_rest.isChecked()

        # Persist filter state to settings
        self._settings.include_self_heal    = include_self
        self._settings.pie_team_a           = show_a
        self._settings.pie_team_b           = show_b
        self._settings.pie_target_players   = show_pl
        self._settings.pie_target_rest      = show_rest

        team_a_set = set(self._team_a)
        team_b_set = set(self._team_b)

        target_players: set[str] = set()
        if show_a:
            target_players.update(team_a_set)
        if show_b:
            target_players.update(team_b_set)
        if not target_players:
            self._pie_chart.clear()
            self._detail_panel.clear()
            return

        totals: dict[str, float] = defaultdict(float)

        def allowed_entity(name: str | None) -> bool:
            is_player = self._is_player_entity(name)
            return (is_player and show_pl) or ((not is_player) and show_rest)

        for ev in self._fight.events:
            if ev.event_type != ev_type:
                continue

            if direction == "out":
                if ev.actor not in target_players:
                    continue
                if not include_self and ev.actor == ev.target:
                    continue
                if not allowed_entity(ev.target):
                    continue
                totals[ev.actor] += ev.amount
            else:
                if ev.target not in target_players:
                    continue
                if not include_self and ev.actor == ev.target:
                    continue
                if not allowed_entity(ev.actor):
                    continue
                totals[ev.target] += ev.amount

        segments: list[PieSegment] = []
        for name, val in sorted(totals.items(), key=lambda x: -x[1]):
            if val <= 0:
                continue
            color = self._color_fn(name) if self._color_fn else "#4fc3f7"
            segments.append(PieSegment(label=name, value=val, color=color))

        self._pie_chart.set_summary(len(self._team_a), len(self._team_b), self._winner)
        self._pie_chart.set_data(segments)

        # Restore selected player
        if self._selected_player:
            names = [s.label for s in segments]
            if self._selected_player in names:
                self._pie_chart.set_selected(self._selected_player)
            else:
                self._selected_player = ""

        self._refresh_detail()

    def _refresh_detail(self) -> None:
        if not self._fight or not self._selected_player:
            self._detail_panel.clear()
            return

        player = self._selected_player
        self._detail_panel.set_header_text(f"Details for {self._name_fn(player)}")

        player_sources: set[str] = set()
        for ev in self._fight.events:
            if ev.actor == player and ev.event_type in ("damage", "heal"):
                player_sources.add((ev.source or "Unknown source").strip() or "Unknown source")
        context_key = f"{self._fight.id}::{player}"
        self._detail_panel.ensure_sources(context_key, sorted(player_sources))

        include_players = self._cb_players.isChecked()
        include_rest = self._cb_rest.isChecked()
        include_self = self._cb_self.isChecked()
        allowed_sources = self._detail_panel.selected_sources()

        out_mode  = ("target"       if self._detail_panel.rb_tgt.isChecked()
                     else "source_total" if self._detail_panel.rb_src_total.isChecked()
                     else "source")
        recv_mode = ("total" if self._detail_panel.rb_recv_total.isChecked()
                     else "source_total" if self._detail_panel.rb_recv_src_total.isChecked()
                     else "source")

        # Persist mode state to settings
        self._settings.outgoing_mode = out_mode
        self._settings.received_mode = recv_mode

        dmg_by_tgt:  dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        heal_by_tgt: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        recv_by_act: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        rheal_by_act: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))

        def allowed_entity(name: str) -> bool:
            is_player = self._is_player_entity(name)
            return (is_player and include_players) or ((not is_player) and include_rest)

        for ev in self._fight.events:
            src = (ev.source or "Unknown source").strip() or "Unknown source"
            if ev.event_type == "damage":
                if ev.actor == player:
                    if allowed_sources is not None and src not in allowed_sources:
                        continue
                    if not allowed_entity(ev.target):
                        continue
                    dmg_by_tgt[ev.target][src] += ev.amount
                elif ev.target == player:
                    if not allowed_entity(ev.actor):
                        continue
                    recv_by_act[ev.actor][src] += ev.amount
            elif ev.event_type == "heal":
                if not include_self and ev.actor == ev.target:
                    continue
                if ev.actor == player:
                    if allowed_sources is not None and src not in allowed_sources:
                        continue
                    if not allowed_entity(ev.target):
                        continue
                    heal_by_tgt[ev.target][src] += ev.amount
                elif ev.target == player:
                    if not allowed_entity(ev.actor):
                        continue
                    rheal_by_act[ev.actor][src] += ev.amount

        # -- Damage dealt --
        t = self._detail_panel.dmg_tree
        t.setSortingEnabled(False)
        t.clear()
        total_dmg = sum(sum(s.values()) for s in dmg_by_tgt.values())
        if out_mode == "target":
            for tgt, srcs in sorted(dmg_by_tgt.items(), key=lambda x: -sum(x[1].values())):
                _add_breakdown_row(t, self._name_fn(tgt), "", sum(srcs.values()), total_dmg)
            _configure_breakdown_tree(t, "Target", True, False)
        elif out_mode == "source_total":
            agg: dict[str, float] = defaultdict(float)
            for srcs in dmg_by_tgt.values():
                for s, v in srcs.items():
                    agg[s] += v
            for src, amt in sorted(agg.items(), key=lambda x: -x[1]):
                _add_breakdown_row(t, "", src, amt, total_dmg)
            _configure_breakdown_tree(t, "Target", False, True)
        else:
            for tgt, srcs in sorted(dmg_by_tgt.items(), key=lambda x: -sum(x[1].values())):
                for src, amt in sorted(srcs.items(), key=lambda x: -x[1]):
                    _add_breakdown_row(t, self._name_fn(tgt), src, amt, total_dmg)
            _configure_breakdown_tree(t, "Target", True, True)
        t.setSortingEnabled(True)
        t.sortByColumn(2, Qt.SortOrder.DescendingOrder)
        _fit_breakdown_tree_columns(t, not t.isColumnHidden(0), not t.isColumnHidden(1))

        # -- Healing dealt --
        t2 = self._detail_panel.heal_tree
        t2.setSortingEnabled(False)
        t2.clear()
        total_heal = sum(sum(s.values()) for s in heal_by_tgt.values())
        if out_mode == "target":
            for tgt, srcs in sorted(heal_by_tgt.items(), key=lambda x: -sum(x[1].values())):
                _add_breakdown_row(t2, self._name_fn(tgt), "", sum(srcs.values()), total_heal)
            _configure_breakdown_tree(t2, "Target", True, False)
        elif out_mode == "source_total":
            agg_heal: dict[str, float] = defaultdict(float)
            for srcs in heal_by_tgt.values():
                for src, amt in srcs.items():
                    agg_heal[src] += amt
            for src, amt in sorted(agg_heal.items(), key=lambda x: -x[1]):
                _add_breakdown_row(t2, "", src, amt, total_heal)
            _configure_breakdown_tree(t2, "Target", False, True)
        else:
            for tgt, srcs in sorted(heal_by_tgt.items(), key=lambda x: -sum(x[1].values())):
                for src, amt in sorted(srcs.items(), key=lambda x: -x[1]):
                    _add_breakdown_row(t2, self._name_fn(tgt), src, amt, total_heal)
            _configure_breakdown_tree(t2, "Target", True, True)
        t2.setSortingEnabled(True)
        t2.sortByColumn(2, Qt.SortOrder.DescendingOrder)
        _fit_breakdown_tree_columns(t2, not t2.isColumnHidden(0), not t2.isColumnHidden(1))

        # -- Damage received --
        t3 = self._detail_panel.rdmg_tree
        t3.setSortingEnabled(False)
        t3.clear()
        total_recv = sum(sum(s.values()) for s in recv_by_act.values())
        if recv_mode == "total":
            for act, srcs in sorted(recv_by_act.items(), key=lambda x: -sum(x[1].values())):
                _add_breakdown_row(t3, self._name_fn(act), "", sum(srcs.values()), total_recv)
            _configure_breakdown_tree(t3, "Attacker", True, False)
        elif recv_mode == "source_total":
            agg_recv: dict[str, float] = defaultdict(float)
            for srcs in recv_by_act.values():
                for src, amt in srcs.items():
                    agg_recv[src] += amt
            for src, amt in sorted(agg_recv.items(), key=lambda x: -x[1]):
                _add_breakdown_row(t3, "", src, amt, total_recv)
            _configure_breakdown_tree(t3, "Attacker", False, True)
        else:
            for act, srcs in sorted(recv_by_act.items(), key=lambda x: -sum(x[1].values())):
                for src, amt in sorted(srcs.items(), key=lambda x: -x[1]):
                    _add_breakdown_row(t3, self._name_fn(act), src, amt, total_recv)
            _configure_breakdown_tree(t3, "Attacker", True, True)
        t3.setSortingEnabled(True)
        t3.sortByColumn(2, Qt.SortOrder.DescendingOrder)
        _fit_breakdown_tree_columns(t3, not t3.isColumnHidden(0), not t3.isColumnHidden(1))

        # -- Healing received --
        t4 = self._detail_panel.rheal_tree
        t4.setSortingEnabled(False)
        t4.clear()
        total_rheal = sum(sum(s.values()) for s in rheal_by_act.values())
        if recv_mode == "total":
            for act, srcs in sorted(rheal_by_act.items(), key=lambda x: -sum(x[1].values())):
                _add_breakdown_row(t4, self._name_fn(act), "", sum(srcs.values()), total_rheal)
            _configure_breakdown_tree(t4, "Healer", True, False)
        elif recv_mode == "source_total":
            agg_rheal: dict[str, float] = defaultdict(float)
            for srcs in rheal_by_act.values():
                for src, amt in srcs.items():
                    agg_rheal[src] += amt
            for src, amt in sorted(agg_rheal.items(), key=lambda x: -x[1]):
                _add_breakdown_row(t4, "", src, amt, total_rheal)
            _configure_breakdown_tree(t4, "Healer", False, True)
        else:
            for act, srcs in sorted(rheal_by_act.items(), key=lambda x: -sum(x[1].values())):
                for src, amt in sorted(srcs.items(), key=lambda x: -x[1]):
                    _add_breakdown_row(t4, self._name_fn(act), src, amt, total_rheal)
            _configure_breakdown_tree(t4, "Healer", True, True)
        t4.setSortingEnabled(True)
        t4.sortByColumn(2, Qt.SortOrder.DescendingOrder)
        _fit_breakdown_tree_columns(t4, not t4.isColumnHidden(0), not t4.isColumnHidden(1))

    # ------------------------------------------------------------------
    # Settings helpers
    # ------------------------------------------------------------------

    def _set_pie_controls_from_settings(self) -> None:
        s = self._settings
        for stat, cb in self._stat_cbs.items():
            cb.blockSignals(True)
            cb.setChecked(stat == s.pie_stat)
            cb.blockSignals(False)

        # Filter checkboxes — block signals so _refresh_pie() isn't triggered at init
        for cb, val in [
            (self._cb_team_a,  s.pie_team_a),
            (self._cb_team_b,  s.pie_team_b),
            (self._cb_players, s.pie_target_players),
            (self._cb_rest,    s.pie_target_rest),
            (self._cb_self,    s.include_self_heal),
        ]:
            cb.blockSignals(True)
            cb.setChecked(val)
            cb.blockSignals(False)

        # Restore outgoing/received radio buttons from settings
        dp = self._detail_panel
        for rb in (dp.rb_tgt, dp.rb_src_total, dp.rb_src, dp.rb_recv_total, dp.rb_recv_src_total, dp.rb_recv_src):
            rb.blockSignals(True)

        if s.outgoing_mode == "source_total":
            dp.rb_src_total.setChecked(True)
        elif s.outgoing_mode == "source":
            dp.rb_src.setChecked(True)
        else:
            dp.rb_tgt.setChecked(True)

        if s.received_mode == "total":
            dp.rb_recv_total.setChecked(True)
        elif s.received_mode == "source_total":
            dp.rb_recv_src_total.setChecked(True)
        else:
            dp.rb_recv_src.setChecked(True)

        for rb in (dp.rb_tgt, dp.rb_src_total, dp.rb_src, dp.rb_recv_total, dp.rb_recv_src_total, dp.rb_recv_src):
            rb.blockSignals(False)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sep(layout: QHBoxLayout) -> None:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.VLine)
    line.setStyleSheet(f"color: {_BORDER};")
    layout.addWidget(line)


def _add_breakdown_row(tree: QTreeWidget, primary: str, source: str, amount: float, total: float) -> QTreeWidgetItem:
    pct = (amount / total * 100) if total else 0.0
    item = _SortableItem([primary, source, _fmt(amount), f"{pct:.1f}%"])
    item.setData(2, Qt.ItemDataRole.UserRole, amount)
    item.setData(3, Qt.ItemDataRole.UserRole, pct)
    item.setTextAlignment(2, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    item.setTextAlignment(3, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    tree.addTopLevelItem(item)
    return item


def _configure_breakdown_tree(tree: QTreeWidget, primary_header: str, show_primary: bool, show_source: bool) -> None:
    tree.headerItem().setText(0, primary_header)
    tree.headerItem().setText(1, "Source")
    tree.headerItem().setText(2, "Amount")
    tree.headerItem().setText(3, "% of total")

    tree.setColumnHidden(0, not show_primary)
    tree.setColumnHidden(1, not show_source)
    tree.setColumnHidden(2, False)
    tree.setColumnHidden(3, False)

    if show_primary and show_source:
        tree.setColumnWidth(0, 150)
        tree.setColumnWidth(1, 200)
    elif show_primary:
        tree.setColumnWidth(0, 320)
    elif show_source:
        tree.setColumnWidth(1, 320)
    tree.setColumnWidth(2, 90)
    tree.setColumnWidth(3, 90)
    _fit_breakdown_tree_columns(tree, show_primary, show_source)


def _fit_breakdown_tree_columns(tree: QTreeWidget, show_primary: bool, show_source: bool) -> None:
    available = max(tree.viewport().width(), tree.width() - 8, 260)
    amount_width = max(70, tree.sizeHintForColumn(2) + 14)
    pct_width = max(78, tree.sizeHintForColumn(3) + 14)
    text_space = max(120, available - amount_width - pct_width - 8)

    if show_primary and show_source:
        primary = max(100, int(text_space * 0.42))
        source = max(120, text_space - primary)
        tree.setColumnWidth(0, primary)
        tree.setColumnWidth(1, source)
    elif show_primary:
        tree.setColumnWidth(0, text_space)
    elif show_source:
        tree.setColumnWidth(1, text_space)

    tree.setColumnWidth(2, amount_width)
    tree.setColumnWidth(3, pct_width)
