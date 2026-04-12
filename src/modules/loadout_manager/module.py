"""
LoadoutManagerModule — OPENABLE module.

Orchestrates the Loadout Manager: database, settings, automation, UI.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QFileDialog, QMessageBox, QWidget

from src.core.config import AppConfig
from src.core.module_base import ModuleBase, ModuleType
from src.modules.loadout_manager.database import LoadoutDatabase
from src.modules.loadout_manager.settings import LoadoutManagerSettings


class LoadoutManagerModule(ModuleBase):

    @property
    def module_id(self) -> str:
        return "loadout_manager"

    @property
    def display_name(self) -> str:
        return "Loadout Manager"

    @property
    def description(self) -> str:
        return "Manage ship builds, crew presets, and automate equipping"

    @property
    def module_type(self) -> ModuleType:
        return ModuleType.OPENABLE

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._config: AppConfig | None = None
        self._settings = LoadoutManagerSettings()
        self._db = LoadoutDatabase()
        self._view = None
        self._navigator = None
        self._scanner = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def initialize(self, config: AppConfig) -> None:
        self._config = config
        self._settings = LoadoutManagerSettings.load()
        self._db.open()

    def shutdown(self) -> None:
        if self._view:
            self._view.save_current_state()
        self._settings.save()
        self._db.close()

    def on_config_changed(self, config: AppConfig) -> None:
        self._config = config

    @property
    def prefers_maximized(self) -> bool:
        return False

    def open_module_settings(self, parent: QWidget) -> bool:
        from PySide6.QtGui import QCursor
        from PySide6.QtWidgets import QMenu
        menu = QMenu(parent)
        menu.setStyleSheet(
            "QMenu { background-color: #0b1420; color: #e8f0fe;"
            "  border: 1px solid #1e3050; padding: 4px; }"
            "QMenu::item { padding: 6px 20px; }"
            "QMenu::item:selected { background-color: #1f3b5c; }"
            "QMenu::separator { height: 1px; background: #1e3050; margin: 4px 0; }"
        )
        menu.addAction("Import AHK", self._on_import)
        menu.addAction("Setup Guide", self._on_setup_guide)
        menu.addSeparator()
        if self._view is not None:
            menu.addAction("Hotkeys", self._view._on_hotkeys)
        menu.exec(QCursor.pos())
        return True

    # ------------------------------------------------------------------
    # OPENABLE interface
    # ------------------------------------------------------------------

    def build_view(self, parent: QWidget) -> QWidget:
        from src.modules.loadout_manager.automation.game_nav import GameNavigator
        from src.modules.loadout_manager.automation.input_driver import InputDriver
        from src.modules.loadout_manager.automation.scanner import LoadoutScanner
        from src.modules.loadout_manager.ui.main_view import LoadoutMainView

        self._view = LoadoutMainView(self._db, self._settings, parent)

        # Wire up automation
        self._scanner = LoadoutScanner()
        if self._settings.template_scale != 1.0:
            self._scanner.set_scale(self._settings.template_scale)
        self._scanner.load_all_templates()

        driver = InputDriver()
        self._navigator = GameNavigator(driver, self._scanner, self._settings)
        self._view.set_navigator(self._navigator)

        # Connect toolbar signals
        self._view.import_requested.connect(self._on_import)
        self._view.manage_ships_requested.connect(self._on_manage_ships)
        self._view.manage_builds_requested.connect(self._on_manage_builds)
        self._view.settings_requested.connect(self._on_edit_presets)
        self._view.setup_guide_requested.connect(self._on_setup_guide)

        # Initial data load
        self._view.refresh_data()
        return self._view

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _on_import(self) -> None:
        if not self._view:
            return

        folder = QFileDialog.getExistingDirectory(
            self._view, "Select AHK Scripts Folder"
        )
        if not folder:
            return

        from src.modules.loadout_manager.importer import AHKImporter

        importer = AHKImporter(self._db, Path(folder), settings=self._settings)

        try:
            stats = importer.run()
            self._view.refresh_data()
            QMessageBox.information(
                self._view,
                "Import Complete",
                f"Imported {stats.get('ships', 0)} ships, "
                f"{stats.get('builds', 0)} builds, "
                f"{stats.get('presets', 0)} presets, "
                f"{stats.get('coordinates', 0)} coordinates.",
            )
        except Exception as exc:
            QMessageBox.critical(
                self._view, "Import Error", str(exc)
            )

    def _on_manage_ships(self) -> None:
        if not self._view:
            return
        from src.modules.loadout_manager.ui.ship_editor import ShipEditorDialog

        dlg = ShipEditorDialog(self._db, self._view, settings=self._settings)
        dlg.ships_changed.connect(self._view.refresh_data)
        dlg.exec()

    def _on_manage_builds(self) -> None:
        if not self._view:
            return
        from src.modules.loadout_manager.ui.build_editor import BuildEditorDialog

        # Open for the currently selected ship in slot 1 (fallback)
        ship_id = None
        ship_name = ""
        for slot in self._view._slots:
            name = slot.selected_ship_name
            if name and name != "None":
                ship = self._db.get_ship_by_name(name)
                if ship and ship.id is not None:
                    ship_id = ship.id
                    ship_name = ship.name
                    break

        if ship_id is None:
            ships = self._db.get_ships()
            if ships:
                ship_id = ships[0].id
                ship_name = ships[0].name

        if ship_id is None:
            QMessageBox.information(
                self._view, "No Ships", "Add ships first."
            )
            return

        dlg = BuildEditorDialog(self._db, ship_id, ship_name, self._view)
        dlg.builds_changed.connect(self._view.refresh_data)
        dlg.exec()

    def _on_edit_presets(self) -> None:
        if not self._view:
            return
        from src.modules.loadout_manager.ui.preset_editor import PresetEditorDialog

        dlg = PresetEditorDialog(self._db, self._view)
        dlg.presets_changed.connect(self._view.refresh_data)
        dlg.exec()

    def _on_calibrate(self) -> None:
        if not self._view or not self._scanner:
            return
        from src.modules.loadout_manager.ui.calibration import CalibrationDialog

        dlg = CalibrationDialog(self._scanner, self._db, self._settings, self._view)
        dlg.exec()

    def _on_setup_guide(self) -> None:
        if not self._view:
            return
        from src.modules.loadout_manager.ui.setup_guide import SetupGuideDialog

        dlg = SetupGuideDialog(self._settings, self._view, scanner=self._scanner)
        dlg.exec()
        if self._scanner:
            self._scanner.load_all_templates()
