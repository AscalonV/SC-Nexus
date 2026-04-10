"""
SCNexusApp — thin QApplication subclass that owns the module registry
and broadcasts global config changes to all registered modules.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtWidgets import (
    QApplication, QDialog, QDialogButtonBox, QFileDialog,
    QFormLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QWidget,
)
from PySide6.QtCore import Signal

from src.core.config import AppConfig
from src.core.module_base import ModuleBase

if TYPE_CHECKING:
    pass


class SCNexusApp(QApplication):
    """
    Application singleton.  Owns the module registry and the global config.
    Broadcasts `config_changed` whenever the user saves global settings.
    """

    config_changed: Signal = Signal(AppConfig)

    def __init__(self, argv: list[str]) -> None:
        super().__init__(argv)
        self._config: AppConfig = AppConfig.load()
        self._modules: dict[str, ModuleBase] = {}

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def config(self) -> AppConfig:
        return self._config

    # ------------------------------------------------------------------
    # Module registry
    # ------------------------------------------------------------------

    def register_module(self, module: ModuleBase) -> None:
        """Initialise and register a module.  Called once during startup."""
        module.initialize(self._config)
        self._modules[module.module_id] = module

    def modules(self) -> list[ModuleBase]:
        return list(self._modules.values())

    def get_module(self, module_id: str) -> ModuleBase | None:
        return self._modules.get(module_id)

    # ------------------------------------------------------------------
    # Global settings dialog
    # ------------------------------------------------------------------

    def open_global_settings(self, parent=None) -> None:
        """Show the global settings dialog (username + logs path)."""
        dlg = _GlobalSettingsDialog(self._config, parent)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._config = dlg.result_config
            self._config.save()
            self._broadcast_config()

    def _broadcast_config(self) -> None:
        """Propagate updated config to every module and emit the signal."""
        for module in self._modules.values():
            module.on_config_changed(self._config)
        self.config_changed.emit(self._config)

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------

    def shutdown_all(self) -> None:
        """Call shutdown() on every registered module."""
        for module in self._modules.values():
            try:
                module.shutdown()
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Global settings dialog
# ---------------------------------------------------------------------------

class _GlobalSettingsDialog(QDialog):
    def __init__(self, config: AppConfig, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Global Settings")
        self.setMinimumWidth(460)
        self.result_config: AppConfig = config.model_copy()

        layout = QVBoxLayout(self)

        form = QFormLayout()
        form.setSpacing(10)

        self._username = QLineEdit(config.username)
        form.addRow(QLabel("Username:"), self._username)

        path_row_widget = _PathRow(config.logs_path, self)
        self._path_row = path_row_widget
        form.addRow(QLabel("Logs path:"), path_row_widget)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_accept(self) -> None:
        self.result_config.username = self._username.text().strip()
        self.result_config.logs_path = self._path_row.path
        self.accept()


class _PathRow(QWidget):
    def __init__(self, initial: str, parent=None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._edit = QLineEdit(initial)
        layout.addWidget(self._edit, 1)

        btn = QPushButton("Browse…")
        btn.setFixedWidth(80)
        btn.clicked.connect(self._browse)
        layout.addWidget(btn)

    @property
    def path(self) -> str:
        return self._edit.text().strip()

    def _browse(self) -> None:
        chosen = QFileDialog.getExistingDirectory(
            self, "Select Star Conflict logs folder", self._edit.text()
        )
        if chosen:
            self._edit.setText(chosen)
