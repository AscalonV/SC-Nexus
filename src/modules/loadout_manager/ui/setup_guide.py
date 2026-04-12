"""
Setup Guide — step-by-step wizard for capturing the UI template images
that the automation engine needs to locate game elements on screen.

How it works
------------
The scanner (``automation/scanner.py``) uses OpenCV template matching to
find buttons and UI elements in the live game window.  It loads PNG
templates from ``ui/assets/``.  This guide walks the user through each
required template, lets them draw a rectangle over the game screen, and
saves the crop to ``ui/assets/{template_id}.png``.

Steps defined here map 1-to-1 to the names used in ``game_nav.py``:
  slot_1..4        → select_slot()
  faction_*        → select_faction()
  preset_1..3      → apply_preset()
  load_preset      → apply_preset() confirm
  confirm_yes      → generic confirm dialogs
  remove_all_modules → unequip_all()
  implant_ready    → wait_for_implant_ready()
"""

from __future__ import annotations

import io
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Optional

from PySide6.QtCore import QPoint, QRect, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from src.modules.loadout_manager.automation.scanner import LoadoutScanner
    from src.modules.loadout_manager.settings import LoadoutManagerSettings

# Templates are saved here — same folder the scanner reads from
_TEMPLATES_DIR = Path(__file__).parent / "assets"

# ── Step definitions ─────────────────────────────────────────────────


@dataclass
class TemplateStep:
    id: str
    title: str
    category: str
    description: str
    instructions: str
    required: bool = True
    capture_mode: str = "region"   # "region" → PNG crop  |  "coord" → single-click x,y
    # Runtime state
    captured: bool = field(default=False, init=False)


TEMPLATE_STEPS: list[TemplateStep] = [
    # ── Ship slots (coordinate-based — appearance varies per ship) ──
    TemplateStep(
        id="slot_1",
        title="Ship Slot 1",
        category="Ship Slots",
        capture_mode="coord",
        description=(
            "The first ship slot button in your hangar / squad screen.\n\n"
            "These buttons are registered as screen coordinates rather than "
            "templates because their appearance changes based on the ship equipped."
        ),
        instructions=(
            "1. Open Star Conflict and navigate to the Hangar / Squad screen.\n"
            "2. Click 'Click to Register' below.\n"
            "3. The screen will freeze — click once directly on ship slot 1 "
            "(the leftmost slot number / icon).\n"
            "4. ESC cancels without saving."
        ),
    ),
    TemplateStep(
        id="slot_2",
        title="Ship Slot 2",
        category="Ship Slots",
        capture_mode="coord",
        description="The second ship slot button (slot 2 of 4).",
        instructions="Same screen. Click once on the slot 2 number / icon.",
    ),
    TemplateStep(
        id="slot_3",
        title="Ship Slot 3",
        category="Ship Slots",
        capture_mode="coord",
        description="The third ship slot button (slot 3 of 4).",
        instructions="Same screen. Click once on the slot 3 number / icon.",
    ),
    TemplateStep(
        id="slot_4",
        title="Ship Slot 4",
        category="Ship Slots",
        capture_mode="coord",
        description="The fourth ship slot button (slot 4 of 4).",
        instructions="Same screen. Click once on the slot 4 number / icon.",
    ),
    # ── Faction tabs (coordinate-based) ──────────────────────────────
    TemplateStep(
        id="faction_empire",
        title="Empire Faction Tab",
        category="Faction Tabs",
        capture_mode="coord",
        description=(
            "The 'Empire' filter tab in the ship-tree browser.\n\n"
            "After you click a ship slot the game shows a tree of available "
            "ships grouped by faction.  Click on the Empire tab to register "
            "its coordinate."
        ),
        instructions=(
            "1. Click a ship slot to open the ship-selection screen.\n"
            "2. Locate the faction filter tabs (usually at the top).\n"
            "3. Click 'Click to Register' and click on the Empire tab."
        ),
    ),
    TemplateStep(
        id="faction_federation",
        title="Federation Faction Tab",
        category="Faction Tabs",
        capture_mode="coord",
        description="The 'Federation' filter tab in the ship-tree browser.",
        instructions="Same screen. Click 'Click to Register' and click on the Federation tab.",
    ),
    TemplateStep(
        id="faction_jericho",
        title="Jericho Faction Tab",
        category="Faction Tabs",
        capture_mode="coord",
        description="The 'Jericho' filter tab in the ship-tree browser.",
        instructions="Same screen. Click 'Click to Register' and click on the Jericho tab.",
    ),
    TemplateStep(
        id="faction_ellydium",
        title="Ellydium Faction Tab",
        category="Faction Tabs",
        capture_mode="coord",
        description="The 'Ellydium' (Alien) filter tab in the ship-tree browser.",
        instructions="Same screen. Click 'Click to Register' and click on the Ellydium tab.",
    ),
    TemplateStep(
        id="faction_unique",
        title="Unique Faction Tab",
        category="Faction Tabs",
        capture_mode="coord",
        description="The 'Unique' filter tab in the ship-tree browser.",
        instructions="Same screen. Click 'Click to Register' and click on the Unique tab.",
    ),
    # ── Loadout preset buttons (coord-based) ──────────────────────────
    TemplateStep(
        id="preset_1",
        title="Loadout Preset 1",
        category="Loadout Presets",
        capture_mode="coord",
        description=(
            "The first preset/loadout slot button on the fitting screen.\n\n"
            "Registered as a coordinate because preset buttons show varying "
            "content depending on what is saved in each slot."
        ),
        instructions=(
            "1. Select any ship and open its fitting / loadout screen.\n"
            "2. Find the preset buttons (usually 1-4 or I-IV).\n"
            "3. Click 'Click to Register' and click once on preset button #1."
        ),
    ),
    TemplateStep(
        id="preset_2",
        title="Loadout Preset 2",
        category="Loadout Presets",
        capture_mode="coord",
        description="The second preset/loadout slot button.",
        instructions="Same screen. Click once on preset button #2.",
    ),
    TemplateStep(
        id="preset_3",
        title="Loadout Preset 3",
        category="Loadout Presets",
        capture_mode="coord",
        description="The third preset/loadout slot button.",
        instructions="Same screen. Click once on preset button #3.",
    ),
    TemplateStep(
        id="preset_4",
        title="Loadout Preset 4",
        category="Loadout Presets",
        capture_mode="coord",
        description="The fourth preset/loadout slot button.",
        instructions="Same screen. Click once on preset button #4.",
    ),
    TemplateStep(
        id="load_preset",
        title="Load / Apply Preset Button",
        category="Loadout Presets",
        capture_mode="coord",
        description=(
            "A secondary 'Load' or 'Apply' button that may appear after clicking "
            "a preset number.\n\n"
            "Skip this step if selecting a preset activates it immediately with a "
            "single click."
        ),
        instructions=(
            "1. On the fitting screen click any preset button.\n"
            "2. If a 'Load Preset' / 'Apply' button appears, click 'Click to Register' "
            "and click on that button.\n"
            "3. If no such button appears, click 'Skip'."
        ),
    ),
    # ── Navigation coordinates ────────────────────────────────────────
    TemplateStep(
        id="yes_coord",
        title="Yes / Confirm Button",
        category="Navigation",
        capture_mode="coord",
        description=(
            "A generic 'Yes' or 'Confirm' button that appears in various "
            "in-game dialogs (e.g. 'Replace modules?')."
        ),
        instructions=(
            "1. Trigger any Yes/Confirm dialog in the game (e.g. try to load "
            "a preset that would replace existing modules).\n"
            "2. Click 'Click to Register' and click on the 'Yes' / 'Confirm' button."
        ),
    ),
    TemplateStep(
        id="scroll_coord",
        title="Scroll Area",
        category="Navigation",
        capture_mode="coord",
        description=(
            "The area where the mouse should be positioned for scrolling "
            "through the ship list in the ship-tree browser.\n\n"
            "This is where the mouse will hover before sending scroll wheel "
            "events to navigate to ships that are off-screen."
        ),
        instructions=(
            "1. Open the ship-selection screen (click any slot).\n"
            "2. Click 'Click to Register' and click on a neutral area in "
            "the ship list (not on a ship, just on empty space in the list)."
        ),
    ),
    TemplateStep(
        id="back_coord",
        title="Back Button",
        category="Navigation",
        capture_mode="coord",
        description="The 'Back' button used to return from the ship-tree browser.",
        instructions=(
            "1. With the ship-selection screen open.\n"
            "2. Click 'Click to Register' and click on the 'Back' button."
        ),
    ),
    # ── Crew coordinates ──────────────────────────────────────────────
    TemplateStep(
        id="crew_button_a",
        title="Crew Button A",
        category="Crew",
        capture_mode="coord",
        description=(
            "The first crew selector button (A) in the crew assignment screen.\n\n"
            "The crew screen has 4 crew groups (A through D). Each controls "
            "which 15 crew members are shown in the grid."
        ),
        instructions=(
            "1. Open the crew screen (press C in the hangar).\n"
            "2. Click 'Click to Register' and click on crew tab A (the leftmost)."
        ),
    ),
    TemplateStep(
        id="crew_button_b",
        title="Crew Button B",
        category="Crew",
        capture_mode="coord",
        description="The second crew selector button (B).",
        instructions="Same screen. Click on crew tab B.",
    ),
    TemplateStep(
        id="crew_button_c",
        title="Crew Button C",
        category="Crew",
        capture_mode="coord",
        description="The third crew selector button (C).",
        instructions="Same screen. Click on crew tab C.",
    ),
    TemplateStep(
        id="crew_button_d",
        title="Crew Button D",
        category="Crew",
        capture_mode="coord",
        description="The fourth crew selector button (D).",
        instructions="Same screen. Click on crew tab D.",
    ),
    TemplateStep(
        id="crew_grid_start",
        title="Crew Grid — Top-Left Cell",
        category="Crew",
        capture_mode="coord",
        description=(
            "The top-left cell of the crew grid (Crew 1, Skill 1).\n\n"
            "The crew grid has 15 columns (one per crew member) and 3 rows "
            "(one per skill level). Only the top-left and bottom-right corners "
            "are needed — all other cells are calculated automatically."
        ),
        instructions=(
            "1. Open the crew screen and select any crew tab.\n"
            "2. Click 'Click to Register' and click on the first crew member's "
            "top skill (row 1, column 1 — the top-left cell in the grid)."
        ),
    ),
    TemplateStep(
        id="crew_grid_end",
        title="Crew Grid — Bottom-Right Cell",
        category="Crew",
        capture_mode="coord",
        description=(
            "The bottom-right cell of the crew grid (Crew 15, Skill 3).\n\n"
            "Together with the top-left cell, this defines the grid layout. "
            "All 45 cells are interpolated from these two corners."
        ),
        instructions=(
            "1. Same crew screen.\n"
            "2. Click 'Click to Register' and click on the last crew member's "
            "bottom skill (row 3, column 15 — the bottom-right cell)."
        ),
    ),
    TemplateStep(
        id="implant_coord",
        title="Implant Button",
        category="Crew",
        capture_mode="coord",
        description=(
            "The implant button on the crew screen. Its pixel color is checked "
            "to determine when the crew screen has finished loading."
        ),
        instructions=(
            "1. Open the crew screen.\n"
            "2. Click 'Click to Register' and click on the implant button / indicator."
        ),
    ),
    # ── Template captures (only for context menu items) ───────────────
    TemplateStep(
        id="remove_all_modules",
        title="Remove All Modules Button",
        category="Common Buttons",
        description=(
            "The context-menu item that strips all modules from the current "
            "loadout.\n\n"
            "Important: this option only appears after right-clicking the ship "
            "slot — the automation right-clicks automatically before "
            "searching for this button."
        ),
        instructions=(
            "1. Open the fitting screen for any ship.\n"
            "2. Right-click the ship slot to open its context menu.\n"
            "3. Capture the 'Remove all modules' / 'Unequip all' item in that menu."
        ),
    ),
]

# ── Styles ─────────────────────────────────────────────────────────────

_SIDEBAR_STYLE = """
QListWidget {
    background-color: #0a1525;
    color: #8899aa;
    border: none;
    border-right: 1px solid #1e3050;
    padding: 4px 0;
    font-size: 12px;
}
QListWidget::item {
    padding: 7px 12px;
    border-bottom: 1px solid #0e1b2d;
}
QListWidget::item:selected {
    background-color: #1a3a55;
    color: #e8f0fe;
}
QListWidget::item:hover:!selected {
    background-color: #112233;
}
"""

_CONTENT_STYLE = "background-color: #0b1420; color: #e8f0fe;"

_BTN = """
QPushButton {
    background-color: #162a42; color: #e8f0fe;
    border: 1px solid #1e3050; border-radius: 4px; padding: 6px 14px;
}
QPushButton:hover { background-color: #1f3b5c; border-color: #4fc3f7; }
QPushButton:disabled { color: #556677; background-color: #0a1525; }
"""

_BTN_CAPTURE = """
QPushButton {
    background-color: #1a5276; color: #e8f0fe;
    border: 1px solid #4fc3f7; border-radius: 4px;
    padding: 8px 20px; font-weight: bold; font-size: 13px;
}
QPushButton:hover { background-color: #1f6d9a; }
QPushButton:disabled { color: #556677; background-color: #0a1525; border-color: #1e3050; }
"""

_STATUS_DONE = "color: #66bb6a; font-size: 11px;"
_STATUS_MISS = "color: #ef5350; font-size: 11px;"
_STATUS_OPT  = "color: #ff9800; font-size: 11px;"
_STATUS_IDLE = "color: #556677; font-size: 11px;"


# ── Overlay helpers ───────────────────────────────────────────────────

def _pin_window_to_virtual(widget: QWidget, rect: QRect) -> None:
    """
    Position *widget* to cover the virtual-screen *rect* using physical pixel
    coordinates, bypassing Qt's DPI scaling.  On non-Windows this is a no-op
    (``setGeometry`` is already correct there).
    """
    if sys.platform != "win32":
        return
    import ctypes
    HWND_TOPMOST  = ctypes.c_void_p(-1)
    SWP_NOACTIVATE = 0x0010
    SWP_SHOWWINDOW = 0x0040
    ctypes.windll.user32.SetWindowPos(
        int(widget.winId()), HWND_TOPMOST,
        rect.x(), rect.y(), rect.width(), rect.height(),
        SWP_NOACTIVATE | SWP_SHOWWINDOW,
    )


# ── Region selector overlay ───────────────────────────────────────────

class _RegionSelector(QWidget):
    """
    Full-screen transparent overlay.

    Captures a screenshot *before* showing (so the live game is visible
    as a frozen background), then lets the user drag a selection rectangle.
    On mouse release emits screen-space coordinates and closes.
    """

    region_captured = Signal(int, int, int, int)   # x, y, w, h
    cancelled       = Signal()

    def __init__(self, frozen_pixmap: QPixmap, virt_rect: QRect) -> None:
        super().__init__(None, Qt.WindowType.FramelessWindowHint
                              | Qt.WindowType.WindowStaysOnTopHint)
        self._pixmap  = frozen_pixmap
        self._origin: QPoint | None = None
        self._current: QPoint | None = None
        self._dragging = False
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        # Span the entire virtual desktop so all monitors are accessible.
        # showFullScreen() only covers a single monitor, which hides regions
        # on secondary monitors when the screenshot covers all of them.
        self.setGeometry(virt_rect)
        self.show()
        self.raise_()
        _pin_window_to_virtual(self, virt_rect)
        self.activateWindow()
        self.setFocus(Qt.FocusReason.ActiveWindowFocusReason)

    # ── Painting ──────────────────────────────────────────────────────

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        # Frozen screenshot as background
        p.drawPixmap(0, 0, self._pixmap)
        # Dark veil over unselected area
        p.fillRect(self.rect(), QColor(0, 0, 0, 100))

        if self._origin and self._current:
            rect = QRect(self._origin, self._current).normalized()
            # Punch-through (restore original colours inside selection)
            p.drawPixmap(rect, self._pixmap, rect)
            # Blue dashed border
            pen = QPen(QColor("#4fc3f7"), 2, Qt.PenStyle.DashLine)
            p.setPen(pen)
            p.drawRect(rect)
            # Size hint
            p.setPen(QPen(QColor("#ffffff")))
            p.setFont(QFont("Consolas", 9))
            label = f"{rect.width()} × {rect.height()}"
            p.drawText(rect.left() + 4, rect.bottom() - 6, label)

        # Instruction bar at top
        p.fillRect(0, 0, self.width(), 32, QColor(0, 0, 0, 180))
        p.setPen(QPen(QColor("#e8f0fe")))
        p.setFont(QFont("Segoe UI", 10))
        p.drawText(12, 21, "Draw a rectangle around the UI element — ESC to cancel")

    # ── Mouse ─────────────────────────────────────────────────────────

    def mousePressEvent(self, ev) -> None:
        if ev.button() == Qt.MouseButton.LeftButton:
            self._origin  = ev.position().toPoint()
            self._current = self._origin
            self._dragging = True

    def mouseMoveEvent(self, ev) -> None:
        if self._dragging:
            self._current = ev.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, ev) -> None:
        if ev.button() == Qt.MouseButton.LeftButton and self._dragging:
            self._dragging = False
            self._current  = ev.position().toPoint()
            rect = QRect(self._origin, self._current).normalized()
            self.close()
            if rect.width() > 8 and rect.height() > 8:
                self.region_captured.emit(rect.x(), rect.y(), rect.width(), rect.height())
            else:
                self.cancelled.emit()

    def keyPressEvent(self, ev) -> None:
        if ev.key() == Qt.Key.Key_Escape:
            self.cancelled.emit()
            self.close()


# ── Coordinate selector overlay ───────────────────────────────────────

class _CoordSelector(QWidget):
    """
    Full-screen overlay for registering a single click coordinate.

    Shows a frozen screenshot as background with crosshair cursor.
    On left-click emits the screen position and closes.
    """

    coord_captured = Signal(int, int)   # x, y
    cancelled      = Signal()

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
        # Span the entire virtual desktop (same fix as _RegionSelector).
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
            # Show the physical screen coordinate (offset by virtual screen origin)
            p.drawText(x + 8, y - 6, f"({self._virt_x + x}, {self._virt_y + y})")

        p.fillRect(0, 0, self.width(), 32, QColor(0, 0, 0, 180))
        p.setPen(QPen(QColor("#e8f0fe")))
        p.setFont(QFont("Segoe UI", 10))
        p.drawText(12, 21, "Click on the UI element to register its coordinate — ESC to cancel")

    def mouseMoveEvent(self, ev) -> None:
        self._hover = ev.position().toPoint()
        self.update()

    def mousePressEvent(self, ev) -> None:
        if ev.button() == Qt.MouseButton.LeftButton:
            pt = ev.position().toPoint()
            self.close()
            # Emit physical screen coordinates (widget-local + virtual screen origin)
            self.coord_captured.emit(self._virt_x + pt.x(), self._virt_y + pt.y())

    def keyPressEvent(self, ev) -> None:
        if ev.key() == Qt.Key.Key_Escape:
            self.cancelled.emit()
            self.close()


# ── Single step content widget ────────────────────────────────────────

class _StepPage(QWidget):
    """Content area for one template step (region or coord capture)."""

    capture_requested = Signal()
    skip_requested    = Signal()

    def __init__(
        self,
        step: TemplateStep,
        get_coord: "Callable[[], tuple[int, int] | None] | None" = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._step = step
        self._get_coord = get_coord
        self._is_coord = (step.capture_mode == "coord")
        self.setStyleSheet(_CONTENT_STYLE)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(12)

        # Title
        title = QLabel(step.title)
        title.setStyleSheet("font-size: 17px; font-weight: bold; color: #4fc3f7;")
        root.addWidget(title)

        # Category badge
        mode_badge = "Coordinate" if self._is_coord else "Template"
        cat = QLabel(f"Category: {step.category}  ·  "
                     f"{'Required' if step.required else 'Optional'}  ·  {mode_badge}")
        cat.setStyleSheet(
            "font-size: 11px; color: #8899aa; "
            "background-color: #0e1b2d; border-radius: 3px; padding: 2px 8px;"
        )
        root.addWidget(cat)

        # Divider
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("border: 1px solid #1e3050;")
        root.addWidget(line)

        # Description
        desc = QLabel(step.description)
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #c8d8e8; font-size: 13px; line-height: 1.5;")
        root.addWidget(desc)

        # Instructions
        inst_title = QLabel("How to capture:")
        inst_title.setStyleSheet("font-size: 12px; font-weight: bold; color: #8899aa; margin-top: 8px;")
        root.addWidget(inst_title)

        inst = QTextEdit()
        inst.setReadOnly(True)
        inst.setPlainText(step.instructions)
        inst.setStyleSheet(
            "background-color: #060d17; color: #8899aa; "
            "border: 1px solid #1e3050; border-radius: 4px; "
            "font-size: 12px; padding: 8px;"
        )
        inst.setFixedHeight(110)
        root.addWidget(inst)

        # Status / preview area
        prev_row = QHBoxLayout()

        if self._is_coord:
            # Coordinate display box
            coord_box = QFrame()
            coord_box.setStyleSheet(
                "background-color: #060d17; border: 1px solid #1e3050; border-radius: 4px;"
            )
            coord_box.setFixedSize(200, 100)
            coord_inner = QVBoxLayout(coord_box)
            coord_inner.setContentsMargins(8, 8, 8, 8)
            coord_inner.setAlignment(Qt.AlignmentFlag.AlignCenter)
            coord_hdr = QLabel("Registered coordinate")
            coord_hdr.setStyleSheet("color: #445566; font-size: 10px;")
            coord_hdr.setAlignment(Qt.AlignmentFlag.AlignCenter)
            coord_inner.addWidget(coord_hdr)
            self._coord_value_lbl = QLabel("—")
            self._coord_value_lbl.setStyleSheet(
                "color: #445566; font-size: 18px; font-family: Consolas;"
            )
            self._coord_value_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            coord_inner.addWidget(self._coord_value_lbl)
            prev_row.addWidget(coord_box)
        else:
            # Template image preview
            self._preview_lbl = QLabel("No image captured yet")
            self._preview_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._preview_lbl.setStyleSheet(
                "background-color: #060d17; color: #445566; "
                "border: 1px solid #1e3050; border-radius: 4px; font-size: 11px;"
            )
            self._preview_lbl.setFixedSize(200, 100)
            prev_row.addWidget(self._preview_lbl)

        self._status_lbl = QLabel("")
        self._status_lbl.setWordWrap(True)
        self._status_lbl.setStyleSheet(_STATUS_IDLE)
        self._status_lbl.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        prev_row.addWidget(self._status_lbl, 1)

        root.addLayout(prev_row)
        root.addStretch(1)

        # Buttons
        btn_row = QHBoxLayout()
        btn_label = "⊕  Click to Register" if self._is_coord else "Capture Region"
        self._btn_capture = QPushButton(btn_label)
        self._btn_capture.setStyleSheet(_BTN_CAPTURE)
        self._btn_capture.clicked.connect(self.capture_requested.emit)
        btn_row.addWidget(self._btn_capture)

        if not step.required:
            btn_skip = QPushButton("Skip (optional)")
            btn_skip.setStyleSheet(_BTN)
            btn_skip.clicked.connect(self.skip_requested.emit)
            btn_row.addWidget(btn_skip)

        btn_row.addStretch(1)
        root.addLayout(btn_row)

        # Load existing capture if available
        self._refresh_preview()

    def _refresh_preview(self) -> None:
        if self._is_coord:
            coord = self._get_coord() if self._get_coord else None
            if coord:
                x, y = coord
                self._coord_value_lbl.setText(f"({x}, {y})")
                self._coord_value_lbl.setStyleSheet(
                    "color: #66bb6a; font-size: 16px; font-family: Consolas;"
                )
                self._step.captured = True
                self._status_lbl.setText("✓  Coordinate registered")
                self._status_lbl.setStyleSheet(_STATUS_DONE)
            else:
                self._coord_value_lbl.setText("—")
                self._coord_value_lbl.setStyleSheet(
                    "color: #445566; font-size: 18px; font-family: Consolas;"
                )
                self._step.captured = False
                self._status_lbl.setText(
                    "No coordinate set." if self._step.required
                    else "Not set (optional)."
                )
                self._status_lbl.setStyleSheet(
                    _STATUS_MISS if self._step.required else _STATUS_OPT
                )
        else:
            path = _TEMPLATES_DIR / f"{self._step.id}.png"
            if path.exists():
                pix = QPixmap(str(path))
                if not pix.isNull():
                    self._preview_lbl.setPixmap(
                        pix.scaled(198, 98,
                                   Qt.AspectRatioMode.KeepAspectRatio,
                                   Qt.TransformationMode.SmoothTransformation)
                    )
                    self._step.captured = True
                    self._status_lbl.setText("✓  Template captured")
                    self._status_lbl.setStyleSheet(_STATUS_DONE)
                    return
            self._step.captured = False
            self._status_lbl.setText(
                "No template yet." if self._step.required
                else "Not captured (optional)."
            )
            self._status_lbl.setStyleSheet(
                _STATUS_MISS if self._step.required else _STATUS_OPT
            )

    def mark_captured(self, coord: tuple[int, int] | None = None) -> None:
        """Called by the dialog after a successful capture."""
        if self._is_coord and coord is not None:
            x, y = coord
            self._coord_value_lbl.setText(f"({x}, {y})")
            self._coord_value_lbl.setStyleSheet(
                "color: #66bb6a; font-size: 16px; font-family: Consolas;"
            )
            self._step.captured = True
            self._status_lbl.setText("✓  Coordinate registered")
            self._status_lbl.setStyleSheet(_STATUS_DONE)
        else:
            self._refresh_preview()


# ── Welcome page ───────────────────────────────────────────────────────

class _WelcomePage(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setStyleSheet(_CONTENT_STYLE)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 32, 40, 32)
        layout.setSpacing(16)

        title = QLabel("Automation Setup Guide")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #4fc3f7;")
        layout.addWidget(title)

        intro = QLabel(
            "This guide helps you register the screen coordinates and capture "
            "the template images the automation engine needs to interact with "
            "Star Conflict.\n\n"
            "How the automation works:\n"
            " • Most UI elements are located by screen coordinates you click "
            "on during this guide\n"
            " • One element (Remove All Modules) uses template matching — you "
            "capture a screenshot region\n"
            " • Coordinates only need to be re-registered if you change resolution\n\n"
            "What you will register:\n"
            " • Ship slot buttons (4 slots in your squad screen)\n"
            " • Faction filter tabs (Empire, Federation, Jericho, Ellydium, Unique)\n"
            " • Loadout preset buttons (1-4) and Load Preset\n"
            " • Navigation buttons (Yes/Confirm, Scroll area, Back)\n"
            " • Crew tab buttons (A-D) and crew grid corners\n"
            " • Implant button coordinate\n\n"
            "Tips:\n"
            " • The game must be running and visible when you click 'Click to Register'\n"
            " • Click precisely on the center of each button\n"
            " • If you imported AHK coordinates, most steps will already be filled in\n\n"
            "Select a step from the left panel to begin."
        )
        intro.setWordWrap(True)
        intro.setStyleSheet("color: #c8d8e8; font-size: 13px; line-height: 1.6;")
        layout.addWidget(intro)
        layout.addStretch(1)


# ── Summary page ───────────────────────────────────────────────────────

class _SummaryPage(QWidget):
    rescan_requested = Signal()

    def __init__(
        self,
        steps: list[TemplateStep],
        settings: "LoadoutManagerSettings | None" = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._steps = steps
        self._settings = settings
        self.setStyleSheet(_CONTENT_STYLE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        title = QLabel("Summary")
        title.setStyleSheet("font-size: 17px; font-weight: bold; color: #4fc3f7;")
        layout.addWidget(title)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setStyleSheet("background-color: transparent;")
        layout.addWidget(self._scroll, 1)

        self._inner = QWidget()
        self._inner.setStyleSheet("background-color: transparent;")
        self._inner_layout = QVBoxLayout(self._inner)
        self._inner_layout.setSpacing(4)
        self._scroll.setWidget(self._inner)

        btn_row = QHBoxLayout()
        btn_rescan = QPushButton("Refresh Status")
        btn_rescan.setStyleSheet(_BTN)
        btn_rescan.clicked.connect(self.rescan_requested.emit)
        btn_row.addWidget(btn_rescan)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)

        self.refresh()

    def refresh(self) -> None:
        # Clear
        while self._inner_layout.count():
            item = self._inner_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        required_ok = 0
        required_total = sum(1 for s in self._steps if s.required)

        for step in self._steps:
            if step.capture_mode == "coord" and self._settings is not None:
                ok = self._check_coord(step.id)
            else:
                path = _TEMPLATES_DIR / f"{step.id}.png"
                ok = path.exists()
            if ok and step.required:
                required_ok += 1

            row = QHBoxLayout()
            row.setSpacing(10)
            icon = QLabel("✓" if ok else ("○" if not step.required else "✗"))
            icon.setFixedWidth(20)
            icon.setStyleSheet(
                _STATUS_DONE if ok else
                (_STATUS_OPT if not step.required else _STATUS_MISS)
            )
            row.addWidget(icon)

            name = QLabel(f"[{step.category}]  {step.title}")
            name.setStyleSheet(f"color: {'#c8d8e8' if ok else '#668899'}; font-size: 12px;")
            row.addWidget(name, 1)

            if ok and step.capture_mode != "coord":
                path = _TEMPLATES_DIR / f"{step.id}.png"
                pix = QPixmap(str(path))
                thumb = QLabel()
                thumb.setPixmap(pix.scaled(60, 30,
                                           Qt.AspectRatioMode.KeepAspectRatio,
                                           Qt.TransformationMode.SmoothTransformation))
                row.addWidget(thumb)

            wrapper = QWidget()
            wrapper.setStyleSheet("background-color: transparent;")
            wrapper.setLayout(row)
            self._inner_layout.addWidget(wrapper)

        self._inner_layout.addStretch(1)

        # Overall status bar
        pct = int(required_ok / required_total * 100) if required_total else 100
        msg = (f"{required_ok}/{required_total} required items configured  ({pct}% ready)")
        color = "#66bb6a" if required_ok == required_total else "#ff9800"
        status = QLabel(msg)
        status.setStyleSheet(f"color: {color}; font-size: 13px; font-weight: bold; padding: 8px 0;")
        self._inner_layout.insertWidget(0, status)

    def _check_coord(self, step_id: str) -> bool:
        s = self._settings
        if s is None:
            return False
        if step_id.startswith("slot_"):
            idx = int(step_id[-1]) - 1
            return 0 <= idx < len(s.slot_coords) and s.slot_coords[idx] is not None
        if step_id.startswith("preset_"):
            idx = int(step_id[-1]) - 1
            return 0 <= idx < len(s.preset_coords) and s.preset_coords[idx] is not None
        if step_id == "load_preset":
            return s.load_preset_coord is not None
        if step_id.startswith("faction_"):
            faction_map = {
                "faction_empire": "Empire",
                "faction_federation": "Federation",
                "faction_jericho": "Jericho",
                "faction_ellydium": "Ellydium",
                "faction_unique": "Unique",
            }
            fk = faction_map.get(step_id)
            return fk is not None and fk in s.faction_coords
        if step_id == "yes_coord":
            return s.yes_coord is not None
        if step_id == "scroll_coord":
            return s.scroll_coord is not None
        if step_id == "back_coord":
            return s.back_coord is not None
        if step_id.startswith("crew_button_"):
            label_map = {"crew_button_a": 0, "crew_button_b": 1, "crew_button_c": 2, "crew_button_d": 3}
            idx = label_map.get(step_id)
            return idx is not None and 0 <= idx < len(s.crew_button_coords) and s.crew_button_coords[idx] is not None
        if step_id == "crew_grid_start":
            return s.crew_grid_start is not None
        if step_id == "crew_grid_end":
            return s.crew_grid_end is not None
        if step_id == "implant_coord":
            return s.implant_coord is not None
        return False


# ── Main dialog ────────────────────────────────────────────────────────

class SetupGuideDialog(QDialog):
    """Step-by-step template capture wizard."""

    def __init__(
        self,
        settings: "LoadoutManagerSettings",
        parent: QWidget | None = None,
        scanner: "LoadoutScanner | None" = None,
    ) -> None:
        super().__init__(parent)
        self._settings = settings
        self._scanner = scanner
        self.setWindowTitle("Automation Setup Guide")
        self.setMinimumSize(900, 620)
        self.setStyleSheet("background-color: #0b1420; color: #e8f0fe;")

        # Create step objects fresh each open so captured state is re-read
        self._steps = [TemplateStep(
            id=s.id, title=s.title, category=s.category,
            description=s.description, instructions=s.instructions,
            required=s.required, capture_mode=s.capture_mode,
        ) for s in TEMPLATE_STEPS]

        _TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)

        self._selector: _RegionSelector | _CoordSelector | None = None
        self._pending_step_idx: int | None = None
        self._page_widgets: list[QWidget] = []

        self._build_ui()

    # ── UI construction ───────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet("QSplitter::handle { background-color: #1e3050; }")
        root.addWidget(splitter)

        # ── Left: sidebar ─────────────────────────────────────────────
        self._sidebar = QListWidget()
        self._sidebar.setStyleSheet(_SIDEBAR_STYLE)
        self._sidebar.setMaximumWidth(230)
        self._sidebar.setMinimumWidth(180)

        # Welcome entry
        self._sidebar.addItem("  ▶  Introduction")
        self._sidebar.item(0).setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))

        prev_category = ""
        for step in self._steps:
            if step.category != prev_category:
                sep = QListWidgetItem(f"  {step.category}")
                sep.setFlags(Qt.ItemFlag.NoItemFlags)
                sep.setForeground(QColor("#4fc3f7"))
                f = sep.font()
                f.setPointSize(9)
                f.setItalic(True)
                sep.setFont(f)
                self._sidebar.addItem(sep)
                prev_category = step.category

            dot = "●" if step.required else "○"
            self._sidebar.addItem(f"  {dot}  {step.title}")

        # Summary entry
        self._sidebar.addItem("  ◆  Summary")

        self._sidebar.currentRowChanged.connect(self._on_sidebar_change)
        splitter.addWidget(self._sidebar)

        # ── Right: stacked pages ──────────────────────────────────────
        right = QWidget()
        right.setStyleSheet(_CONTENT_STYLE)
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # Page container (manual show/hide since QStackedWidget has sizing issues)
        self._content_area = QWidget()
        self._content_area.setStyleSheet(_CONTENT_STYLE)
        content_layout = QVBoxLayout(self._content_area)
        content_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(self._content_area, 1)

        # Bottom close bar
        close_bar = QFrame()
        close_bar.setStyleSheet("background-color: #0a1525; border-top: 1px solid #1e3050;")
        close_bar.setFixedHeight(44)
        close_bl = QHBoxLayout(close_bar)
        close_bl.setContentsMargins(16, 0, 16, 0)
        close_bl.addStretch(1)
        btn_close = QPushButton("Close")
        btn_close.setStyleSheet(_BTN)
        btn_close.clicked.connect(self.accept)
        close_bl.addWidget(btn_close)
        right_layout.addWidget(close_bar)

        splitter.addWidget(right)
        splitter.setSizes([200, 700])

        # Build pages
        welcome = _WelcomePage()
        self._page_widgets.append(welcome)
        content_layout.addWidget(welcome)

        for i, step in enumerate(self._steps):
            get_coord = (
                (lambda sid=step.id: self._get_coord_for_step(sid))
                if step.capture_mode == "coord" else None
            )
            page = _StepPage(step, get_coord=get_coord)
            if step.capture_mode == "coord":
                page.capture_requested.connect(lambda idx=i: self._start_coord_capture(idx))
            else:
                page.capture_requested.connect(lambda idx=i: self._start_capture(idx))
            page.skip_requested.connect(lambda idx=i: self._on_skip(idx))
            page.hide()
            self._page_widgets.append(page)
            content_layout.addWidget(page)

        summary = _SummaryPage(self._steps, settings=self._settings)
        summary.rescan_requested.connect(summary.refresh)
        summary.hide()
        self._page_widgets.append(summary)
        content_layout.addWidget(summary)

        self._summary_page = summary
        self._current_page_idx = 0
        self._show_page(0)

        # Populate sidebar checkmarks for already-configured steps
        self._update_sidebar_status()

        # Select first sidebar item
        self._sidebar.setCurrentRow(0)

    def _show_page(self, page_idx: int) -> None:
        for i, w in enumerate(self._page_widgets):
            if i == page_idx:
                w.show()
            else:
                w.hide()
        self._current_page_idx = page_idx

    def _on_sidebar_change(self, row: int) -> None:
        """Map sidebar row → page index (skipping category separator rows)."""
        if row < 0:
            return

        item = self._sidebar.item(row)
        if item is None:
            return
        # Category separators are non-selectable; shouldn't reach here, but guard
        if not (item.flags() & Qt.ItemFlag.ItemIsEnabled):
            return

        # row 0 = welcome, last row = summary
        # Pages list: [welcome, ...steps..., summary]
        if row == 0:
            self._show_page(0)
            return
        if row == self._sidebar.count() - 1:
            self._summary_page.refresh()
            self._show_page(len(self._page_widgets) - 1)
            return

        # Map row to step index (skip separator rows)
        step_count = 0
        for r in range(1, row):
            item = self._sidebar.item(r)
            if item and bool(item.flags() & Qt.ItemFlag.ItemIsEnabled):
                step_count += 1
        # step_count is 0-based index into self._steps
        if step_count < len(self._steps):
            self._show_page(step_count + 1)   # +1 for welcome

    # ── Coordinate helpers ────────────────────────────────────────────

    def _get_coord_for_step(self, step_id: str) -> tuple[int, int] | None:
        s = self._settings
        if step_id.startswith("slot_"):
            idx = int(step_id[-1]) - 1
            coords = s.slot_coords
            if 0 <= idx < len(coords) and coords[idx] is not None:
                return (coords[idx].x, coords[idx].y)
        elif step_id.startswith("preset_"):
            idx = int(step_id[-1]) - 1
            coords = s.preset_coords
            if 0 <= idx < len(coords) and coords[idx] is not None:
                return (coords[idx].x, coords[idx].y)
        elif step_id == "load_preset" and s.load_preset_coord is not None:
            return (s.load_preset_coord.x, s.load_preset_coord.y)
        elif step_id.startswith("faction_"):
            faction_map = {
                "faction_empire": "Empire",
                "faction_federation": "Federation",
                "faction_jericho": "Jericho",
                "faction_ellydium": "Ellydium",
                "faction_unique": "Unique",
            }
            fk = faction_map.get(step_id)
            if fk and fk in s.faction_coords:
                c = s.faction_coords[fk]
                return (c.x, c.y)
        elif step_id == "yes_coord" and s.yes_coord is not None:
            return (s.yes_coord.x, s.yes_coord.y)
        elif step_id == "scroll_coord" and s.scroll_coord is not None:
            return (s.scroll_coord.x, s.scroll_coord.y)
        elif step_id == "back_coord" and s.back_coord is not None:
            return (s.back_coord.x, s.back_coord.y)
        elif step_id.startswith("crew_button_"):
            label_map = {"crew_button_a": 0, "crew_button_b": 1, "crew_button_c": 2, "crew_button_d": 3}
            idx = label_map.get(step_id)
            if idx is not None and 0 <= idx < len(s.crew_button_coords) and s.crew_button_coords[idx] is not None:
                return (s.crew_button_coords[idx].x, s.crew_button_coords[idx].y)
        elif step_id == "crew_grid_start" and s.crew_grid_start is not None:
            return (s.crew_grid_start.x, s.crew_grid_start.y)
        elif step_id == "crew_grid_end" and s.crew_grid_end is not None:
            return (s.crew_grid_end.x, s.crew_grid_end.y)
        elif step_id == "implant_coord" and s.implant_coord is not None:
            return (s.implant_coord.x, s.implant_coord.y)
        return None

    def _set_coord_for_step(self, step_id: str, x: int, y: int) -> None:
        from src.modules.loadout_manager.settings import Coordinate
        coord = Coordinate(x=x, y=y)
        s = self._settings
        if step_id.startswith("slot_"):
            idx = int(step_id[-1]) - 1
            if 0 <= idx < len(s.slot_coords):
                s.slot_coords[idx] = coord
        elif step_id.startswith("preset_"):
            idx = int(step_id[-1]) - 1
            if 0 <= idx < len(s.preset_coords):
                s.preset_coords[idx] = coord
        elif step_id == "load_preset":
            s.load_preset_coord = coord
        elif step_id.startswith("faction_"):
            faction_map = {
                "faction_empire": "Empire",
                "faction_federation": "Federation",
                "faction_jericho": "Jericho",
                "faction_ellydium": "Ellydium",
                "faction_unique": "Unique",
            }
            fk = faction_map.get(step_id)
            if fk:
                s.faction_coords[fk] = coord
        elif step_id == "yes_coord":
            s.yes_coord = coord
        elif step_id == "scroll_coord":
            s.scroll_coord = coord
        elif step_id == "back_coord":
            s.back_coord = coord
        elif step_id.startswith("crew_button_"):
            label_map = {"crew_button_a": 0, "crew_button_b": 1, "crew_button_c": 2, "crew_button_d": 3}
            idx = label_map.get(step_id)
            if idx is not None and 0 <= idx < len(s.crew_button_coords):
                s.crew_button_coords[idx] = coord
        elif step_id == "crew_grid_start":
            s.crew_grid_start = coord
        elif step_id == "crew_grid_end":
            s.crew_grid_end = coord
        elif step_id == "implant_coord":
            s.implant_coord = coord
        s.save()

    def _start_coord_capture(self, step_idx: int) -> None:
        """Hide dialog, take screenshot, show _CoordSelector for a single click."""
        try:
            import mss
            import numpy as np
            from PySide6.QtGui import QImage
        except ImportError:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self, "Missing Dependency",
                "The 'mss' package is required for screen capture.\n"
                "Install it with:  pip install mss"
            )
            return
        self._pending_step_idx = step_idx
        self.hide()
        QTimer.singleShot(200, lambda: self._do_coord_screenshot(step_idx))

    def _do_coord_screenshot(self, step_idx: int) -> None:
        try:
            import mss
            import numpy as np
            from PySide6.QtGui import QImage
        except ImportError:
            self.show()
            return

        with mss.mss() as sct:
            all_monitors = sct.monitors[0]
            shot = sct.grab(all_monitors)
            img_np = np.frombuffer(shot.raw, dtype=np.uint8)
            img_np = img_np.reshape((shot.height, shot.width, 4))
            h, w = img_np.shape[:2]
            qimg = QImage(img_np.data, w, h, w * 4, QImage.Format.Format_ARGB32)
            frozen = QPixmap.fromImage(qimg)

        self._frozen_pixmap = frozen
        virt_rect = QRect(
            all_monitors["left"], all_monitors["top"],
            all_monitors["width"], all_monitors["height"],
        )
        selector = _CoordSelector(frozen, virt_rect)
        self._selector = selector
        selector.coord_captured.connect(
            lambda cx, cy, idx=step_idx: self._save_coord(cx, cy, idx)
        )
        selector.cancelled.connect(self._on_capture_cancelled)

    def _save_coord(self, x: int, y: int, step_idx: int) -> None:
        step = self._steps[step_idx]
        self._set_coord_for_step(step.id, x, y)
        page = self._page_widgets[step_idx + 1]  # +1 for welcome
        if isinstance(page, _StepPage):
            page.mark_captured((x, y))
        self._update_sidebar_status()
        self.show()

    # ── Capture flow ──────────────────────────────────────────────────

    def _start_capture(self, step_idx: int) -> None:
        """Hide dialog, take screenshot, show overlay."""
        try:
            import mss
            import mss.tools
            import numpy as np
            from PySide6.QtGui import QImage
        except ImportError:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self, "Missing Dependency",
                "The 'mss' package is required for screen capture.\n"
                "Install it with:  pip install mss"
            )
            return

        self._pending_step_idx = step_idx
        self.hide()

        # Give the window time to disappear before screenshotting
        QTimer.singleShot(200, lambda: self._do_screenshot(step_idx))

    def _do_screenshot(self, step_idx: int) -> None:
        try:
            import mss
            import numpy as np
            from PySide6.QtGui import QImage
        except ImportError:
            self.show()
            return

        with mss.mss() as sct:
            # Capture all monitors combined
            all_monitors = sct.monitors[0]
            shot = sct.grab(all_monitors)
            img_np = np.frombuffer(shot.raw, dtype=np.uint8)
            img_np = img_np.reshape((shot.height, shot.width, 4))  # BGRA
            # Convert to QPixmap
            h, w = img_np.shape[:2]
            qimg = QImage(img_np.data, w, h, w * 4, QImage.Format.Format_ARGB32)
            frozen = QPixmap.fromImage(qimg)

        self._frozen_pixmap = frozen
        virt_rect = QRect(
            all_monitors["left"], all_monitors["top"],
            all_monitors["width"], all_monitors["height"],
        )
        self._selector = _RegionSelector(frozen, virt_rect)
        self._selector.region_captured.connect(
            lambda x, y, rw, rh, idx=step_idx: self._save_capture(x, y, rw, rh, idx)
        )
        self._selector.cancelled.connect(self._on_capture_cancelled)

    def _save_capture(self, x: int, y: int, w: int, h: int, step_idx: int) -> None:
        """Crop the frozen screenshot and save as a template PNG."""
        if self._frozen_pixmap is None:
            self.show()
            return

        cropped = self._frozen_pixmap.copy(x, y, w, h)
        step = self._steps[step_idx]
        out_path = _TEMPLATES_DIR / f"{step.id}.png"
        _TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
        cropped.save(str(out_path), "PNG")
        if self._scanner is not None:
            self._scanner.load_template(step.id, out_path)

        # Refresh step page preview
        page = self._page_widgets[step_idx + 1]  # +1 for welcome
        if isinstance(page, _StepPage):
            page.mark_captured()

        self._update_sidebar_status()
        self.show()

    def _on_capture_cancelled(self) -> None:
        self.show()

    def _on_skip(self, step_idx: int) -> None:
        # Move to the next step
        next_row = self._sidebar.currentRow() + 1
        if next_row < self._sidebar.count():
            self._sidebar.setCurrentRow(next_row)

    def _update_sidebar_status(self) -> None:
        """Update the ✓/●/○ indicators in the sidebar for each step."""
        step_row = 1  # sidebar row (skip Welcome row=0)
        for step in self._steps:
            # Skip category header rows
            while step_row < self._sidebar.count():
                item = self._sidebar.item(step_row)
                if item and bool(item.flags() & Qt.ItemFlag.ItemIsEnabled):
                    break
                step_row += 1

            item = self._sidebar.item(step_row)
            if item:
                if step.capture_mode == "coord":
                    ok = self._get_coord_for_step(step.id) is not None
                else:
                    path = _TEMPLATES_DIR / f"{step.id}.png"
                    ok = path.exists()
                if ok:
                    item.setForeground(QColor("#66bb6a"))
                    item.setText(f"  \u2713  {step.title}")
                else:
                    item.setForeground(QColor(
                        "#ef5350" if step.required else "#ff9800"
                    ))
                    dot = "\u25cf" if step.required else "\u25cb"
                    item.setText(f"  {dot}  {step.title}")
            step_row += 1
