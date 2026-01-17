from abc import ABC, abstractmethod
from typing import Protocol

class BaseModule(ABC):
    """Common interface for all modules so we can swap them easily."""

    name: str
    description: str

    @abstractmethod
    def build(self, parent):
        """Return a Tk frame representing this module's UI."""

    @abstractmethod
    def on_show(self):
        """Called when the module is navigated to so it can refresh data."""

    def on_hide(self):
        """Called when navagating away from the module."""
        pass

    def on_exit(self):
        """Called when the application is closing."""
        pass

    # Optional launchpad hooks
    def on_tile_click(self) -> bool:
        """Handle launchpad tile clicks. Return True to prevent navigation."""
        return False

    def tile_status(self) -> str:
        """Optional short status line for the launchpad tile."""
        return ""
