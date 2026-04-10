"""
Persistent settings for the Combat Analyzer module.
Saved to user_data/combat_analysis_settings.json between restarts.
"""
from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from src.core.config import USER_DATA_DIR

_SETTINGS_FILE: Path = USER_DATA_DIR / "combat_analysis_settings.json"


class CombatAnalysisSettings(BaseModel):
    # Teams tab
    sort_by:    str  = "Damage dealt"
    sort_order: str  = "Descending"

    # Pie tab – stat selection
    pie_stat:         str  = "Damage dealt"
    include_self_heal: bool = True

    # Pie tab – display filters
    outgoing_mode: str  = "target"    # "target" | "source_total" | "source"
    received_mode: str  = "total"     # "total"  | "source_total" | "source"
    pie_team_a:    bool = True
    pie_team_b:    bool = True
    pie_target_players: bool = True
    pie_target_rest:    bool = True

    # Persisted API verification cache — avoids re-checking every restart
    player_cache: dict[str, bool] = Field(default_factory=dict)

    @classmethod
    def load(cls) -> "CombatAnalysisSettings":
        try:
            if _SETTINGS_FILE.exists():
                return cls.model_validate_json(
                    _SETTINGS_FILE.read_text(encoding="utf-8")
                )
        except Exception:
            pass
        return cls()

    def save(self) -> None:
        USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
        _SETTINGS_FILE.write_text(
            self.model_dump_json(indent=2), encoding="utf-8"
        )
