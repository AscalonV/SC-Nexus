"""
BreakdownDialog — per-player combat breakdown popup.

Shows damage dealt / healing dealt / damage received tables for one player.
Sources can be individually toggled (weapon / ability filter).
"""
from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPen
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QStyledItemDelegate,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.modules.combat_analysis.parser import CombatEvent, Fight, ParticipantStats

# ---------------------------------------------------------------------------
# Styles
# ---------------------------------------------------------------------------
_BG      = "#080f1a"
_BG2     = "#0d1b2a"
_BORDER  = "#1e3050"
_ACCENT  = "#4fc3f7"
_TEXT    = "#e8f0fe"
_SUBTEXT = "#8899aa"
_SEL_BG  = "#1a3560"

_TREE_STYLE = f"""
QTreeWidget {{
    background-color: {_BG2};
    alternate-background-color: #0a1525;
    color: {_TEXT};
    border: 1px solid {_BORDER};
    border-radius: 4px;
    outline: none;
}}
QTreeWidget::item {{ border-bottom: 1px solid #12253f; padding: 1px 4px; }}
QTreeWidget::item:selected {{ background-color: {_SEL_BG}; }}
QHeaderView::section {{
    background-color: {_BORDER};
    color: {_ACCENT};
    padding: 4px 6px;
    border: none;
    border-right: 1px solid #12253f;
    font-weight: bold;
}}
QScrollBar:vertical {{ background: #09121f; width: 12px; margin: 0; border-left: 1px solid #12253f; }}
QScrollBar::handle:vertical {{ background: #1e3050; min-height: 28px; border-radius: 5px; margin: 2px; }}
QScrollBar::handle:vertical:hover {{ background: #4fc3f7; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; background: transparent; border: none; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: #09121f; }}
QScrollBar:horizontal {{ background: #09121f; height: 12px; margin: 0; border-top: 1px solid #12253f; }}
QScrollBar::handle:horizontal {{ background: #1e3050; min-width: 28px; border-radius: 5px; margin: 2px; }}
QScrollBar::handle:horizontal:hover {{ background: #4fc3f7; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; background: transparent; border: none; }}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: #09121f; }}
QTreeCornerButton::section {{ background: #09121f; border: 1px solid #12253f; }}
"""

_SCROLL_STYLE = f"""
QScrollArea {{ border: none; background: transparent; }}
QScrollBar:vertical {{ background: #09121f; width: 12px; margin: 0; border-left: 1px solid #12253f; }}
QScrollBar::handle:vertical {{ background: #1e3050; min-height: 28px; border-radius: 5px; margin: 2px; }}
QScrollBar::handle:vertical:hover {{ background: #4fc3f7; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; background: transparent; border: none; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: #09121f; }}
"""

_BTN_STYLE = (
    "QPushButton{background:transparent;color:#8899aa;border:1px solid #1e3050;"
    "border-radius:4px;padding:3px 10px}"
    "QPushButton:hover{color:#e8f0fe;border-color:#4fc3f7}"
)

_CB_STYLE = f"color: {_TEXT}; font-size: 11px;"
_LBL_STYLE = f"color: {_ACCENT}; font-weight: bold; font-size: 10px;"


def _fmt(v: float) -> str:
    if v >= 1_000_000:
        return f"{v/1_000_000:.2f}M"
    if v >= 1_000:
        return f"{v/1_000:.1f}k"
    return str(int(v))


# ---------------------------------------------------------------------------
# Sortable tree item
# ---------------------------------------------------------------------------

class _SortableItem(QTreeWidgetItem):
    """QTreeWidgetItem that sorts numeric columns by underlying float."""

    def __lt__(self, other: "QTreeWidgetItem") -> bool:
        tree = self.treeWidget()
        col = 0
        if tree is not None:
            sort_col = tree.property("_sort_column")
            if isinstance(sort_col, int):
                col = sort_col
        my_val  = self.data(col, Qt.ItemDataRole.UserRole)
        oth_val = other.data(col, Qt.ItemDataRole.UserRole)
        if isinstance(my_val, (int, float)) and isinstance(oth_val, (int, float)):
            return my_val < oth_val
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
# Breakdown dialog
# ---------------------------------------------------------------------------

class BreakdownDialog(QDialog):
    """Per-player detailed stats dialog."""

    def __init__(
        self,
        player:     str,
        fight:      Fight,
        stats:      dict[str, ParticipantStats],
        player_set: set[str],
        name_fn:    Callable[[str], str] | None = None,
        parent:     QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._player     = player
        self._fight      = fight
        self._stats      = stats
        self._player_set = player_set
        self._name_fn    = name_fn or (lambda n: n)

        disp = self._name_fn(player)
        self.setWindowTitle(f"Breakdown — {disp}")
        self.resize(820, 600)
        self.setStyleSheet(
            f"background-color: {_BG}; color: {_TEXT};"
            f"font-family: 'Segoe UI'; font-size: 11px;"
        )

        self._source_checks: dict[str, QCheckBox] = {}
        self._recv_mode = "source"      # "total" | "source"
        self._out_mode  = "target"      # "target" | "source_total" | "source"

        self._build_ui()
        self._populate_sources()
        self._refresh_tables()

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # Title
        disp = self._name_fn(self._player)
        title = QLabel(disp)
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {_ACCENT};")
        root.addWidget(title)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        root.addWidget(splitter, 1)

        # ---- Left: sources filter panel ---
        left = QWidget()
        left.setFixedWidth(200)
        left.setStyleSheet(f"background-color: {_BG2}; border: 1px solid {_BORDER}; border-radius:4px;")
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(8, 8, 8, 8)
        left_layout.setSpacing(6)

        src_label = QLabel("Sources")
        src_label.setStyleSheet(_LBL_STYLE)
        left_layout.addWidget(src_label)

        btns = QHBoxLayout()
        btns.setSpacing(4)
        sel_all = QPushButton("All")
        sel_all.setStyleSheet(_BTN_STYLE)
        sel_all.setFixedHeight(22)
        sel_all.clicked.connect(self._select_all_sources)
        none_btn = QPushButton("None")
        none_btn.setStyleSheet(_BTN_STYLE)
        none_btn.setFixedHeight(22)
        none_btn.clicked.connect(self._deselect_all_sources)
        btns.addWidget(sel_all)
        btns.addWidget(none_btn)
        btns.addStretch()
        left_layout.addLayout(btns)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(_SCROLL_STYLE)
        self._sources_container = QWidget()
        self._sources_container.setStyleSheet("background: transparent;")
        self._sources_layout = QVBoxLayout(self._sources_container)
        self._sources_layout.setContentsMargins(0, 0, 0, 0)
        self._sources_layout.setSpacing(2)
        self._sources_layout.addStretch()
        scroll.setWidget(self._sources_container)
        left_layout.addWidget(scroll, 1)

        splitter.addWidget(left)

        # ---- Right: tables ---
        right = QWidget()
        right.setStyleSheet("background: transparent;")
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)

        # -- Outgoing mode radios --
        self._out_group      = QGroupBox("Outgoing damage — view by")
        self._out_group.setStyleSheet(
            f"QGroupBox{{color:{_SUBTEXT};border:1px solid {_BORDER};"
            f"border-radius:4px;margin-top:8px;padding-top:4px;}}"
            f"QGroupBox::title{{subcontrol-origin: margin;left:8px;}}"
        )
        out_bar = QHBoxLayout(self._out_group)
        out_bar.setContentsMargins(8, 4, 8, 4)
        out_bar.setSpacing(16)
        self._out_target_rb      = QRadioButton("Target total")
        self._out_src_total_rb   = QRadioButton("Source total")
        self._out_src_rb         = QRadioButton("Source detail")
        for rb in (self._out_target_rb, self._out_src_total_rb, self._out_src_rb):
            rb.setStyleSheet(f"color: {_TEXT};")
            out_bar.addWidget(rb)
        out_bar.addStretch()
        self._out_target_rb.setChecked(True)
        self._out_target_rb.toggled.connect(lambda _: self._on_out_mode("target"))
        self._out_src_total_rb.toggled.connect(lambda _: self._on_out_mode("source_total"))
        self._out_src_rb.toggled.connect(lambda _: self._on_out_mode("source"))
        right_layout.addWidget(self._out_group)

        # -- Damage dealt table --
        dmg_label = QLabel("Damage Dealt")
        dmg_label.setStyleSheet(_LBL_STYLE)
        right_layout.addWidget(dmg_label)
        self._dmg_tree = self._make_tree(["Target / Source", "Amount", "%"])
        right_layout.addWidget(self._dmg_tree, 2)

        # -- Healing dealt table --
        heal_label = QLabel("Healing Dealt")
        heal_label.setStyleSheet(_LBL_STYLE)
        right_layout.addWidget(heal_label)
        self._heal_tree = self._make_tree(["Target", "Amount", "%"])
        right_layout.addWidget(self._heal_tree, 1)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {_BORDER};")
        right_layout.addWidget(sep)

        # -- Received mode radios --
        self._recv_group = QGroupBox("Damage received — view by")
        self._recv_group.setStyleSheet(
            f"QGroupBox{{color:{_SUBTEXT};border:1px solid {_BORDER};"
            f"border-radius:4px;margin-top:8px;padding-top:4px;}}"
            f"QGroupBox::title{{subcontrol-origin: margin;left:8px;}}"
        )
        recv_bar = QHBoxLayout(self._recv_group)
        recv_bar.setContentsMargins(8, 4, 8, 4)
        recv_bar.setSpacing(16)
        self._recv_total_rb  = QRadioButton("Participant total")
        self._recv_source_rb = QRadioButton("Source")
        for rb in (self._recv_total_rb, self._recv_source_rb):
            rb.setStyleSheet(f"color: {_TEXT};")
            recv_bar.addWidget(rb)
        recv_bar.addStretch()
        self._recv_source_rb.setChecked(True)
        self._recv_total_rb.toggled.connect(lambda _: self._on_recv_mode("total"))
        self._recv_source_rb.toggled.connect(lambda _: self._on_recv_mode("source"))
        right_layout.addWidget(self._recv_group)

        # -- Damage received table --
        recv_label = QLabel("Damage Received")
        recv_label.setStyleSheet(_LBL_STYLE)
        right_layout.addWidget(recv_label)
        self._recv_tree = self._make_tree(["Attacker / Source", "Amount", "%"])
        right_layout.addWidget(self._recv_tree, 2)

        splitter.addWidget(right)
        splitter.setSizes([200, 620])

        # -- Close button --
        box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        box.setStyleSheet(_BTN_STYLE)
        box.rejected.connect(self.reject)
        root.addWidget(box)

    @staticmethod
    def _make_tree(headers: list[str]) -> QTreeWidget:
        t = QTreeWidget()
        t.setStyleSheet(_TREE_STYLE)
        t.setAlternatingRowColors(True)
        t.setRootIsDecorated(False)
        t.setSortingEnabled(True)
        t.setColumnCount(len(headers))
        t.setHeaderLabels(headers)
        t.setItemDelegate(_GridDelegate(t))
        from PySide6.QtWidgets import QHeaderView as _HV
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
        t.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        return t

    # ------------------------------------------------------------------
    # Sources
    # ------------------------------------------------------------------

    def _populate_sources(self) -> None:
        sources: set[str] = set()
        for ev in self._fight.events:
            if ev.actor == self._player or ev.target == self._player:
                if ev.source:
                    sources.add(ev.source)

        # Remove stretch, add checkboxes, re-add stretch
        layout = self._sources_layout
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for src in sorted(sources):
            cb = QCheckBox(src)
            cb.setChecked(True)
            cb.setStyleSheet(_CB_STYLE)
            cb.stateChanged.connect(lambda _s, _cb=cb: self._refresh_tables())
            self._source_checks[src] = cb
            layout.addWidget(cb)
        layout.addStretch()

    def _active_sources(self) -> set[str]:
        return {s for s, cb in self._source_checks.items() if cb.isChecked()}

    def _select_all_sources(self) -> None:
        for cb in self._source_checks.values():
            cb.setChecked(True)

    def _deselect_all_sources(self) -> None:
        for cb in self._source_checks.values():
            cb.setChecked(False)

    # ------------------------------------------------------------------
    # Mode toggles
    # ------------------------------------------------------------------

    def _on_out_mode(self, mode: str) -> None:
        self._out_mode = mode
        self._refresh_tables()

    def _on_recv_mode(self, mode: str) -> None:
        self._recv_mode = mode
        self._refresh_tables()

    # ------------------------------------------------------------------
    # Data computation
    # ------------------------------------------------------------------

    def _refresh_tables(self) -> None:
        active = self._active_sources()
        player = self._player

        # --- Gather raw events ---
        dmg_by_target:  dict[str, dict[str, float]] = {}  # target → {source: amt}
        heal_by_target: dict[str, float] = {}
        recv_by_actor:  dict[str, dict[str, float]] = {}  # attacker → {source: amt}

        for ev in self._fight.events:
            if not (ev.source in active or not ev.source):
                continue
            if ev.event_type == "damage":
                if ev.actor == player:
                    d = dmg_by_target.setdefault(ev.target, {})
                    d[ev.source or "?"] = d.get(ev.source or "?", 0.0) + ev.amount
                elif ev.target == player:
                    d = recv_by_actor.setdefault(ev.actor, {})
                    d[ev.source or "?"] = d.get(ev.source or "?", 0.0) + ev.amount
            elif ev.event_type == "heal":
                if ev.actor == player and ev.target != player:
                    heal_by_target[ev.target] = heal_by_target.get(ev.target, 0.0) + ev.amount

        # --- Damage dealt table ---
        self._dmg_tree.setSortingEnabled(False)
        self._dmg_tree.clear()
        mode = self._out_mode
        total_dmg = sum(sum(s.values()) for s in dmg_by_target.values())
        if mode == "target":
            for tgt, sources in sorted(dmg_by_target.items(), key=lambda x: -sum(x[1].values())):
                amt = sum(sources.values())
                _add_row(self._dmg_tree, self._name_fn(tgt), amt, total_dmg)
        elif mode == "source_total":
            agg: dict[str, float] = {}
            for sources in dmg_by_target.values():
                for src, v in sources.items():
                    agg[src] = agg.get(src, 0.0) + v
            for src, amt in sorted(agg.items(), key=lambda x: -x[1]):
                _add_row(self._dmg_tree, src, amt, total_dmg)
        else:  # source detail
            for tgt, sources in sorted(dmg_by_target.items(), key=lambda x: -sum(x[1].values())):
                parent_amt = sum(sources.values())
                parent_item = _add_row(self._dmg_tree, self._name_fn(tgt), parent_amt, total_dmg)
                parent_item.setExpanded(True)
                for src, amt in sorted(sources.items(), key=lambda x: -x[1]):
                    _add_child_row(parent_item, src, amt, parent_amt)
        self._dmg_tree.setSortingEnabled(True)
        self._dmg_tree.sortByColumn(1, Qt.SortOrder.DescendingOrder)

        # --- Healing dealt table ---
        self._heal_tree.setSortingEnabled(False)
        self._heal_tree.clear()
        total_heal = sum(heal_by_target.values())
        for tgt, amt in sorted(heal_by_target.items(), key=lambda x: -x[1]):
            _add_row(self._heal_tree, self._name_fn(tgt), amt, total_heal)
        self._heal_tree.setSortingEnabled(True)
        self._heal_tree.sortByColumn(1, Qt.SortOrder.DescendingOrder)

        # --- Damage received table ---
        self._recv_tree.setSortingEnabled(False)
        self._recv_tree.clear()
        total_recv = sum(sum(s.values()) for s in recv_by_actor.values())
        mode2 = self._recv_mode
        if mode2 == "total":
            for actor, sources in sorted(recv_by_actor.items(), key=lambda x: -sum(x[1].values())):
                amt = sum(sources.values())
                _add_row(self._recv_tree, self._name_fn(actor), amt, total_recv)
        else:  # source
            for actor, sources in sorted(recv_by_actor.items(), key=lambda x: -sum(x[1].values())):
                parent_amt = sum(sources.values())
                parent_item = _add_row(self._recv_tree, self._name_fn(actor), parent_amt, total_recv)
                parent_item.setExpanded(True)
                for src, amt in sorted(sources.items(), key=lambda x: -x[1]):
                    _add_child_row(parent_item, src, amt, parent_amt)
        self._recv_tree.setSortingEnabled(True)
        self._recv_tree.sortByColumn(1, Qt.SortOrder.DescendingOrder)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _add_row(tree: QTreeWidget, label: str, amount: float, total: float) -> QTreeWidgetItem:
    pct = (amount / total * 100) if total else 0.0
    item = _SortableItem([label, _fmt(amount), f"{pct:.1f}%"])
    item.setData(1, Qt.ItemDataRole.UserRole, amount)
    item.setData(2, Qt.ItemDataRole.UserRole, pct)
    item.setTextAlignment(1, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    item.setTextAlignment(2, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    tree.addTopLevelItem(item)
    return item


def _add_child_row(parent: QTreeWidgetItem, label: str, amount: float, parent_total: float) -> None:
    pct = (amount / parent_total * 100) if parent_total else 0.0
    item = _SortableItem([f"  {label}", _fmt(amount), f"{pct:.1f}%"])
    item.setData(1, Qt.ItemDataRole.UserRole, amount)
    item.setData(2, Qt.ItemDataRole.UserRole, pct)
    item.setTextAlignment(1, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    item.setTextAlignment(2, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    parent.addChild(item)
