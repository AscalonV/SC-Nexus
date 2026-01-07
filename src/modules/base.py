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
