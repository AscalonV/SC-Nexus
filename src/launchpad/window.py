"""
LaunchpadWindow — the application's single QMainWindow.

Navigation model
----------------
A QStackedWidget forms the central widget:
  index 0  — HUB (tile grid of all modules)
  index 1+ — module views / settings panels (pushed on demand)

The header bar persists across all pages and provides:
  • App name / version
  • "← Back" button (hidden on hub)
  • "⚙ Global Settings" button
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from src.core.module_base import ModuleBase, ModuleType
from src.launchpad.tile_widget import ModuleTile

# ------------------------------------------------------------------
# Style constants
# ------------------------------------------------------------------

_BG_APP      = "#080f1a"
_BG_HEADER   = "#0b1420"
_BG_HUB      = "#080f1a"
_ACCENT      = "#4fc3f7"
_TEXT_PRIMARY  = "#e8f0fe"
_TEXT_SECONDARY = "#8899aa"
_BORDER      = "#1e3050"

_HEADER_STYLE = f"""
    background-color: {_BG_HEADER};
    border-bottom: 1px solid {_BORDER};
"""

_BACK_BTN_STYLE = f"""
QPushButton {{
    background-color: transparent;
    color: {_ACCENT};
    border: none;
    font-size: 13px;
    padding: 4px 10px;
}}
QPushButton:hover {{ color: #81d4fa; }}
"""

_SETTINGS_BTN_STYLE = f"""
QPushButton {{
    background-color: transparent;
    color: {_TEXT_SECONDARY};
    border: 1px solid {_BORDER};
    border-radius: 5px;
    padding: 4px 12px;
}}
QPushButton:hover {{
    color: {_TEXT_PRIMARY};
    border-color: {_ACCENT};
}}
"""

_WINDOW_STYLE = f"background-color: {_BG_APP};"


class LaunchpadWindow(QMainWindow):
    """Main application window with a persistent header and stacked navigation."""

    def __init__(self, app: "SCNexusApp", ready_event=None, splash_proc=None) -> None:  # type: ignore[name-defined]
        super().__init__()
        self._app = app
        self._ready_event = ready_event
        self._splash_proc = splash_proc
        self._tiles: dict[str, ModuleTile] = {}
        self._view_cache: dict[str, QWidget] = {}  # module_id → built widget
        self._nav_stack: list[str] = []  # names for the back-button label
        self._current_module: ModuleBase | None = None
        self._hub_geometry = None  # saved before entering a module

        self.setWindowTitle("SC Nexus")
        self.setMinimumSize(720, 500)
        self.setStyleSheet(_WINDOW_STYLE)

        self._build_ui()
        # Defer module initialization so the window appears immediately.
        # QTimer.singleShot(0) fires after the first event-loop iteration,
        # by which point show() has been processed and the window is visible.
        QTimer.singleShot(0, self._deferred_init)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        self.setCentralWidget(root)

        # Header
        header = self._build_header()
        root_layout.addWidget(header)

        # Stack
        self._stack = QStackedWidget()
        root_layout.addWidget(self._stack, 1)

        # Hub page (index 0)
        self._hub_page = self._build_hub_page()
        self._stack.addWidget(self._hub_page)

    def _build_header(self) -> QWidget:
        header = QFrame()
        header.setStyleSheet(_HEADER_STYLE)
        header.setFixedHeight(52)

        layout = QHBoxLayout(header)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(10)

        # Back button (hidden initially)
        self._back_btn = QPushButton("← Back")
        self._back_btn.setStyleSheet(_BACK_BTN_STYLE)
        self._back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._back_btn.clicked.connect(self._on_back)
        self._back_btn.setVisible(False)
        layout.addWidget(self._back_btn)

        # App title
        self._title_lbl = QLabel("SC Nexus")
        self._title_lbl.setStyleSheet(
            f"color: {_ACCENT}; font-size: 18px; font-weight: bold; letter-spacing: 1px;"
        )
        layout.addWidget(self._title_lbl)

        layout.addStretch(1)

        # Global settings
        self._global_settings_btn = QPushButton("⚙ Settings")
        self._global_settings_btn.setStyleSheet(_SETTINGS_BTN_STYLE)
        self._global_settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._global_settings_btn.clicked.connect(self._on_settings_btn)
        layout.addWidget(self._global_settings_btn)

        return header

    def _build_hub_page(self) -> QWidget:
        """Build the scrollable tile grid hub."""
        container = QWidget()
        container.setStyleSheet(f"background-color: {_BG_HUB};")

        outer = QVBoxLayout(container)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background-color: transparent;")
        outer.addWidget(scroll)

        inner = QWidget()
        inner.setStyleSheet("background-color: transparent;")
        scroll.setWidget(inner)

        self._hub_layout = QVBoxLayout(inner)
        self._hub_layout.setContentsMargins(32, 24, 32, 24)
        self._hub_layout.setSpacing(14)
        self._hub_layout.addStretch(1)  # tiles are inserted before this

        return container

    # ------------------------------------------------------------------
    # Module registration
    # ------------------------------------------------------------------

    def _deferred_init(self) -> None:
        """Kick off one-module-per-tick async registration chain."""
        from src.modules.combat_analysis.module import CombatAnalyzerModule
        from src.modules.combat_assistant.module import CombatAssistantModule
        from src.modules.loadout_manager.module import LoadoutManagerModule
        from src.modules.self_torp.module import SelfTorpModule

        self._pending_modules: list = [
            CombatAnalyzerModule,
            CombatAssistantModule,
            LoadoutManagerModule,
            SelfTorpModule,
        ]
        QTimer.singleShot(0, self._register_next_module)

    def _register_next_module(self) -> None:
        """Register one module then schedule the next tick, keeping the event loop free."""
        if self._pending_modules:
            module_cls = self._pending_modules.pop(0)
            module = module_cls()
            self._app.register_module(module)
            QTimer.singleShot(0, self._register_next_module)
            return
        # All modules registered — build the hub.
        self._populate_hub()
        if self._ready_event is not None:
            # Signal the splash subprocess to transition to READY, then wait
            # for it to exit before showing the main window.
            self._ready_event.set()
            self._poll_splash_done()
        else:
            self._show_centered()

    def _poll_splash_done(self) -> None:
        """Check every 50 ms until the splash subprocess has exited, then show."""
        if self._splash_proc is not None and self._splash_proc.is_alive():
            QTimer.singleShot(50, self._poll_splash_done)
        else:
            self._show_centered()

    def _show_centered(self) -> None:
        """Show the main window centered on the primary screen."""
        screen = QApplication.primaryScreen().availableGeometry()
        self.adjustSize()
        fg = self.frameGeometry()
        self.move(
            screen.center().x() - fg.width() // 2,
            screen.center().y() - fg.height() // 2,
        )
        self.show()

    def _populate_hub(self) -> None:
        """Create a ModuleTile for each registered module and insert into the hub."""
        stretch_item = self._hub_layout.takeAt(self._hub_layout.count() - 1)

        for module in self._app.modules():
            tile = ModuleTile(module, self._hub_page)
            self._tiles[module.module_id] = tile
            self._hub_layout.addWidget(tile)

            if module.module_type is ModuleType.OPENABLE:
                tile.open_requested.connect(
                    lambda m=module: self._show_module_view(m)
                )

            else:  # TOGGLEABLE
                tile.set_toggle_state(module.is_enabled)
                tile.toggle_requested.connect(
                    lambda enabled, m=module: self._on_toggle(m, enabled)
                )
                tile.settings_requested.connect(
                    lambda m=module: self._on_settings(m)
                )

        # Re-add the stretch
        self._hub_layout.addStretch(1)

    # ------------------------------------------------------------------
    # Navigation helpers
    # ------------------------------------------------------------------

    def _show_module_view(self, module: ModuleBase) -> None:
        """Push the module's main view onto the stack."""
        mid = module.module_id
        if mid not in self._view_cache:
            view = module.build_view(self._stack)
            self._stack.addWidget(view)
            self._view_cache[mid] = view

        # Save hub geometry before resizing
        self._hub_geometry = self.geometry()
        self._current_module = module
        self._title_lbl.setText(module.display_name)

        self._stack.setCurrentWidget(self._view_cache[mid])
        if getattr(module, 'prefers_maximized', False):
            if not self.isMaximized():
                self.showMaximized()
        else:
            if self.isMaximized():
                self.showNormal()
            self.adjustSize()
            if module.module_id == "loadout_manager":
                screen = QApplication.primaryScreen().availableGeometry()
                fg = self.frameGeometry()
                self.move(
                    screen.center().x() - fg.width() // 2,
                    screen.center().y() - fg.height() // 2,
                )
        self._nav_stack.append(module.display_name)
        self._update_back_button()

    def _show_settings_panel(self, module: ModuleBase) -> None:
        """Push the module's settings sub-view onto the stack."""
        key = f"{module.module_id}:settings"
        if key not in self._view_cache:
            panel = module.build_settings_panel(self._stack)
            if panel is None:
                return
            self._stack.addWidget(panel)
            self._view_cache[key] = panel

        self._hub_geometry = self.geometry()
        self._current_module = module
        self._stack.setCurrentWidget(self._view_cache[key])
        if getattr(module, 'prefers_maximized', False):
            if not self.isMaximized():
                self.showMaximized()
        else:
            if self.isMaximized():
                self.showNormal()
        self._nav_stack.append(f"{module.display_name} Settings")
        self._update_back_button()

    def show_hub(self) -> None:
        if self._current_module is not None:
            if getattr(self._current_module, 'prefers_maximized', False):
                # Coming back from a maximized module — restore and center.
                self.showNormal()
                self.adjustSize()
                if self._hub_geometry is not None:
                    self.setGeometry(self._hub_geometry)
                else:
                    screen = QApplication.primaryScreen().availableGeometry()
                    fg = self.frameGeometry()
                    self.move(
                        screen.center().x() - fg.width() // 2,
                        screen.center().y() - fg.height() // 2,
                    )
            elif self._hub_geometry is not None:
                self.showNormal()
                self.setGeometry(self._hub_geometry)
        self._current_module = None
        self._title_lbl.setText("SC Nexus")
        self.setWindowTitle("SC Nexus")
        self._stack.setCurrentWidget(self._hub_page)
        self._nav_stack.clear()
        self._update_back_button()

    def _on_back(self) -> None:
        if not self._nav_stack:
            return
        self._nav_stack.pop()
        if self._nav_stack:
            # Go back one in the navigation history
            # For simplicity: always go to hub on back press
            pass
        self.show_hub()

    def _update_back_button(self) -> None:
        visible = bool(self._nav_stack)
        self._back_btn.setVisible(visible)
        if visible:
            parent_name = self._nav_stack[-2] if len(self._nav_stack) > 1 else "Home"
            self._back_btn.setText(f"← {parent_name}")

    # ------------------------------------------------------------------
    # Module event handlers
    # ------------------------------------------------------------------

    def _on_settings_btn(self) -> None:
        """Route Settings button to module settings or global settings."""
        if self._current_module is not None:
            if self._current_module.open_module_settings(self):
                return
        self._app.open_global_settings(self)

    def _on_toggle(self, module: ModuleBase, enabled: bool) -> None:
        module.on_toggle(enabled)
        tile = self._tiles.get(module.module_id)
        if tile is not None:
            tile.set_toggle_state(module.is_enabled)

    def _on_settings(self, module: ModuleBase) -> None:
        """Route to popup dialog or stacked sub-view depending on the module."""
        # Prefer popup dialog first (e.g. Self-Torp)
        if module.open_settings_dialog.__func__ is not ModuleBase.open_settings_dialog:
            module.open_settings_dialog(self)
            return
        # Fall back to sub-view panel (e.g. Combat Assistant)
        self._show_settings_panel(module)

    # ------------------------------------------------------------------
    # Window lifecycle
    # ------------------------------------------------------------------

    def closeEvent(self, event) -> None:
        self._app.shutdown_all()
        event.accept()
