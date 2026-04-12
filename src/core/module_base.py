"""
Abstract base class and type definitions for all SC Nexus modules.

Every module must subclass ModuleBase and declare its ModuleType.
The base class is a QObject so modules can own Qt signals and child QObjects.
"""

from __future__ import annotations

from abc import ABCMeta, abstractmethod
from enum import Enum, auto
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QWidget

if TYPE_CHECKING:
    from src.core.config import AppConfig


class ModuleType(Enum):
    """How a module is surfaced in the launchpad."""
    OPENABLE  = auto()   # Tile shows "Open" button → swaps main view via QStackedWidget
    TOGGLEABLE = auto()  # Tile shows toggle switch; module runs in background when on


# Combine QObject's Shiboken metaclass with ABCMeta so both coexist.
class _QObjectABCMeta(type(QObject), ABCMeta):
    pass


class ModuleBase(QObject, metaclass=_QObjectABCMeta):
    """
    Contract that every SC Nexus module must satisfy.

    Lifecycle
    ---------
    1. ``initialize(config)``  — called once at startup, before any UI is built.
    2. ``shutdown()``          — called on application close; stop threads, save state.

    OPENABLE modules also implement ``build_view()``.
    TOGGLEABLE modules also implement ``on_toggle()`` and optionally
    ``open_settings_dialog()`` (for popup dialogs) or ``build_settings_panel()``
    (for QStackedWidget sub-views).
    """

    # Emitting this updates the status line on the launchpad tile.
    status_changed: Signal = Signal(str)

    # ------------------------------------------------------------------
    # Identity (must be overridden)
    # ------------------------------------------------------------------

    @property
    @abstractmethod
    def module_id(self) -> str:
        """Unique snake_case identifier, e.g. ``"combat_analysis"``."""

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable name shown on the launchpad tile."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Short single-line description shown on the launchpad tile."""

    @property
    @abstractmethod
    def module_type(self) -> ModuleType:
        """Determines the tile's control layout."""

    # ------------------------------------------------------------------
    # Lifecycle (must be overridden)
    # ------------------------------------------------------------------

    @abstractmethod
    def initialize(self, config: "AppConfig") -> None:
        """
        One-time initialisation.  Receive the global config, start any
        background workers that should always run, etc.
        Do NOT build Qt widgets here.
        """

    @abstractmethod
    def shutdown(self) -> None:
        """Stop threads, flush pending saves, release resources."""

    # ------------------------------------------------------------------
    # OPENABLE interface
    # ------------------------------------------------------------------

    def build_view(self, parent: QWidget) -> QWidget:
        """
        Build and return the module's main QWidget.
        Called the first time the user opens the module.
        OPENABLE modules must override this.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} is OPENABLE but did not implement build_view()"
        )

    # ------------------------------------------------------------------
    # TOGGLEABLE interface
    # ------------------------------------------------------------------

    @property
    def is_enabled(self) -> bool:
        """
        Returns the persisted on/off state for TOGGLEABLE modules.
        Override in TOGGLEABLE modules that save an ``enabled`` field.
        """
        return False

    def on_toggle(self, enabled: bool) -> None:
        """
        Called when the user flips the tile toggle.
        TOGGLEABLE modules must override this.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} is TOGGLEABLE but did not implement on_toggle()"
        )

    def open_settings_dialog(self, parent: QWidget) -> None:
        """
        Open the module's settings as a modal QDialog.
        Override in TOGGLEABLE modules that use a popup (e.g. Self-Torp).
        Return None if the module has no popup settings.
        """

    def build_settings_panel(self, parent: QWidget) -> QWidget | None:
        """
        Build and return a QWidget shown as a QStackedWidget sub-view.
        Override in TOGGLEABLE modules that use an in-window settings page
        (e.g. Combat Assistant).  Return None to disable the Settings button.
        """
        return None

    def open_module_settings(self, parent: QWidget) -> bool:
        """
        Called when the header Settings button is clicked while this module is open.
        Return True if the module handled it (suppresses global settings fallback).
        Override in OPENABLE modules that want a module-specific settings menu/dialog.
        """
        return False

    @property
    def prefers_maximized(self) -> bool:
        """Return True to have the main window maximized when this module opens."""
        return False

    # ------------------------------------------------------------------
    # Config propagation
    # ------------------------------------------------------------------

    def on_config_changed(self, config: "AppConfig") -> None:
        """
        Called whenever the user saves global settings.
        Override to react to username / logs_path changes.
        """
