"""
Persistent settings for the Loadout Manager module.

Non-data preferences (timing, colors, UI state) are stored here as JSON.
Ship/build/preset data lives in the SQLite database.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from src.core.config import USER_DATA_DIR

_SETTINGS_FILE: Path = USER_DATA_DIR / "loadout_manager_settings.json"


class Coordinate(BaseModel):
    x: int
    y: int


class EllydiumColors(BaseModel):
    normal_on: str = "0xDBFF9F"
    normal_off: str = "0x0B1C09"
    spec_on: str = "0x5CFEFF"
    spec_off: str = "0x000101"


class SlotSnapshot(BaseModel):
    enabled: bool = False
    ship_name: str = ""
    build_name: str = ""


class LoadoutManagerSettings(BaseModel):
    last_preset: str = ""
    last_slots: list[SlotSnapshot] = Field(
        default_factory=lambda: [SlotSnapshot() for _ in range(4)]
    )

    # Template matching (only used for Remove All Modules)
    template_scale: float = 1.0

    # Ellydium pixel detection colors
    ellydium_colors: EllydiumColors = Field(default_factory=EllydiumColors)

    # Automation timing
    game_window_title: str = "StarConflict"
    automation_delay_ms: int = 200
    scroll_delay_ms: int = 150
    crew_click_delay_ms: int = 20
    implant_timeout_ms: int = 3000

    # ── In-game navigation keys ───────────────────────────────────────
    # Keys the player has bound in Star Conflict for these functions.
    # Single-character strings (e.g. "T", "C") or key names ("ESCAPE").
    nav_key_ship_tree: str = "T"   # default in-game key to open ship fitting
    nav_key_crew: str = "C"        # default in-game key to open crew/implant window

    # ── Equip behaviour ───────────────────────────────────────────────
    # Unequip all modules from the slot before equipping a new ship.
    unequip_modules: bool = False
    # Extra wait (ms) added after ship-click and after preset confirmation
    # to account for server lag.  0 = no extra delay.
    server_delay_ms: int = 0

    # ── Automation hotkeys ────────────────────────────────────────────
    # Key names use Qt key sequence strings (e.g. "F5", "Ctrl+1", "Alt+E")
    hotkey_equip_all: str = "F5"
    hotkey_equip_slot1: str = ""
    hotkey_equip_slot2: str = ""
    hotkey_equip_slot3: str = ""
    hotkey_equip_slot4: str = ""
    hotkey_cancel: str = "Ctrl+F8"

    # ── Slot & preset coordinates ─────────────────────────────────────
    # Index 0 = slot/preset 1, index 3 = slot/preset 4.  None = not yet set.
    slot_coords: list[Optional[Coordinate]] = Field(
        default_factory=lambda: [None, None, None, None]
    )
    preset_coords: list[Optional[Coordinate]] = Field(
        default_factory=lambda: [None, None, None, None]
    )
    load_preset_coord: Optional[Coordinate] = None

    # ── Faction tab coordinates ───────────────────────────────────────
    faction_coords: dict[str, Coordinate] = Field(default_factory=dict)

    # ── Navigation coordinates ────────────────────────────────────────
    scroll_coord: Optional[Coordinate] = None
    back_coord: Optional[Coordinate] = None
    yes_coord: Optional[Coordinate] = None

    # ── Crew coordinates ──────────────────────────────────────────────
    crew_button_coords: list[Optional[Coordinate]] = Field(
        default_factory=lambda: [None, None, None, None]
    )
    # Two corner cells for grid interpolation (Crew1-1 top-left, Crew15-3 bottom-right)
    crew_grid_start: Optional[Coordinate] = None
    crew_grid_end: Optional[Coordinate] = None

    # ── Implant ───────────────────────────────────────────────────────
    implant_coord: Optional[Coordinate] = None
    implant_color: str = "0x23363D"

    # ── Ellydium ──────────────────────────────────────────────────────
    apply_ellydium_coord: Optional[Coordinate] = None

    # ── Derived helpers ───────────────────────────────────────────────

    def crew_grid_cell(self, position: int, skill: int) -> Coordinate | None:
        """
        Interpolate a crew grid cell coordinate from the two stored corners.

        Parameters
        ----------
        position : 1-15 (crew member column)
        skill : 1-3 (skill row)

        Returns None if the corners are not calibrated.
        """
        if self.crew_grid_start is None or self.crew_grid_end is None:
            return None
        if not (1 <= position <= 15 and 1 <= skill <= 3):
            return None
        sx, sy = self.crew_grid_start.x, self.crew_grid_start.y
        ex, ey = self.crew_grid_end.x, self.crew_grid_end.y
        col = position - 1  # 0..14
        row = skill - 1     # 0..2
        x = sx + round(col * (ex - sx) / 14)
        y = sy + round(row * (ey - sy) / 2)
        return Coordinate(x=x, y=y)

    @classmethod
    def load(cls) -> "LoadoutManagerSettings":
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
