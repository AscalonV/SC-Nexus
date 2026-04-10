"""
Application-wide configuration model and persistence helpers.

Pydantic v2 is used for validation and JSON serialisation.
All path helpers handle both normal (source) and frozen (PyInstaller) execution.
"""

from __future__ import annotations

import sys
from pathlib import Path

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def _get_root_dir() -> Path:
    """Return the application root directory for both frozen and dev runs."""
    if getattr(sys, "frozen", False):
        # PyInstaller sets sys.executable to the .exe path
        return Path(sys.executable).parent
    # Dev: this file lives at src/core/config.py → root is two levels up
    return Path(__file__).parent.parent.parent


ROOT_DIR: Path = _get_root_dir()
USER_DATA_DIR: Path = ROOT_DIR / "user_data"
CONFIG_FILE: Path = USER_DATA_DIR / "config.json"

_DEFAULT_LOGS = (
    Path.home() / "Documents" / "My Games" / "StarConflict" / "logs"
)


# ---------------------------------------------------------------------------
# Config model
# ---------------------------------------------------------------------------

class AppConfig(BaseModel):
    logs_path: str = Field(default_factory=lambda: str(_DEFAULT_LOGS))
    username: str = ""
    disabled_game_modes: list[str] = Field(default_factory=list)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    @classmethod
    def load(cls) -> "AppConfig":
        """Load config from disk, falling back to defaults on any error."""
        try:
            USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
            if CONFIG_FILE.exists():
                return cls.model_validate_json(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
        return cls()

    def save(self) -> None:
        """Persist the current config to disk."""
        USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(
            self.model_dump_json(indent=2), encoding="utf-8"
        )
