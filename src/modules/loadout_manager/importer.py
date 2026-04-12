"""
Import AHK INI data (ships, builds, presets, Ellydium trees) into the
Loadout Manager SQLite database.

Handles:
- UTF-8 and UTF-16 LE encoded .ini files
- AHK section name convention (trailing ``|``)
- Crew values (1/2/3), preset slots, Ellydium node on/off states
- Ellydium tree definition files (node coordinates, costs, branches)
"""

from __future__ import annotations

import configparser
import re
from pathlib import Path
from typing import Callable

from src.modules.loadout_manager.database import (
    Build,
    EllydiumNodeDef,
    EllydiumNodeState,
    LoadoutDatabase,
    Preset,
    PresetSlot,
    Ship,
)
from src.modules.loadout_manager.settings import Coordinate, LoadoutManagerSettings

# Categories whose keys appear in build .ini files as ``Category_N=0|1``
_ELLYDIUM_CATEGORIES = (
    "Capacitor", "CPU", "Defence", "Engine",
    "Hull", "Offence", "Shield", "SpecMod", "Utility",
)

_NODE_KEY_RE = re.compile(
    r"^(" + "|".join(_ELLYDIUM_CATEGORIES) + r")_(\d+)$", re.IGNORECASE
)


# ── INI helpers ───────────────────────────────────────────────────────

def _read_ini(path: Path) -> configparser.ConfigParser:
    """Read an INI file, auto-detecting UTF-16 LE vs UTF-8 encoding."""
    cp = configparser.ConfigParser(interpolation=None)
    cp.optionxform = str  # preserve key case

    raw = path.read_bytes()
    if raw[:2] == b"\xff\xfe":
        # UTF-16 LE with BOM — skip the 2 BOM bytes then decode
        text = raw[2:].decode("utf-16-le")
    elif raw[:2] == b"\xfe\xff":
        # UTF-16 BE with BOM
        text = raw[2:].decode("utf-16-be")
    elif raw[:3] == b"\xef\xbb\xbf":
        # UTF-8 with BOM
        text = raw[3:].decode("utf-8")
    else:
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            text = raw.decode("utf-16-le", errors="replace")

    cp.read_string(text, source=str(path))
    return cp


def _strip_pipe(section: str) -> str:
    """Remove trailing ``|`` from AHK section names."""
    return section.rstrip("|").strip()


# ── Public import API ─────────────────────────────────────────────────

class AHKImporter:
    """Imports AHK loadout data into the Loadout Manager database."""

    def __init__(
        self,
        db: LoadoutDatabase,
        ahk_root: Path,
        settings: LoadoutManagerSettings | None = None,
        progress: Callable[[str, int, int], None] | None = None,
    ) -> None:
        self._db = db
        self._root = ahk_root
        self._settings = settings
        self._progress = progress or (lambda msg, cur, total: None)

        self._settings_dir = ahk_root / "Settings"
        self._builds_dir = ahk_root / "Builds"
        self._ellydium_dir = ahk_root / "Builds" / "Ellydium"

    # ── Main entry point ──────────────────────────────────────────────

    def run(self) -> dict[str, int]:
        """
        Execute full import.  Returns counts of imported items.
        """
        counts: dict[str, int] = {
            "ships": 0, "builds": 0, "presets": 0,
            "ellydium_defs": 0, "ellydium_states": 0,
            "coordinates": 0,
        }

        # Step 1: Ships (including click coords + scroll data)
        self._progress("Importing ships…", 0, 5)
        counts["ships"] = self._import_ships()

        # Step 2: Builds (and Ellydium node states)
        self._progress("Importing builds…", 1, 5)
        b, e = self._import_builds()
        counts["builds"] = b
        counts["ellydium_states"] = e

        # Step 3: Ellydium tree definitions
        self._progress("Importing Ellydium trees…", 2, 5)
        counts["ellydium_defs"] = self._import_ellydium_tree_defs()

        # Step 4: Presets
        self._progress("Importing presets…", 3, 5)
        counts["presets"] = self._import_presets()

        # Step 5: UI coordinates → settings
        self._progress("Importing coordinates…", 4, 5)
        counts["coordinates"] = self._import_coordinates()

        self._progress("Import complete.", 5, 5)
        return counts

    # ── Ships (ShipList.ini) ──────────────────────────────────────────

    def _import_ships(self) -> int:
        ship_list_path = self._settings_dir / "ShipList.ini"
        if not ship_list_path.exists():
            return 0

        cp = _read_ini(ship_list_path)
        count = 0

        for section in cp.sections():
            name = _strip_pipe(section)
            if not name or name.lower() == "none":
                continue

            faction = cp.get(section, "Faction", fallback="None")
            is_ellydium = faction.lower() == "ellydium"

            # Parse click coordinates
            raw_x = cp.get(section, "x", fallback="")
            raw_y = cp.get(section, "y", fallback="")
            click_x: int | None = None
            click_y: int | None = None
            if raw_x and raw_x.lower() != "none":
                try:
                    click_x = int(raw_x)
                except ValueError:
                    pass
            if raw_y and raw_y.lower() != "none":
                try:
                    click_y = int(raw_y)
                except ValueError:
                    pass

            # Parse scroll data
            scroll_amt_raw = cp.get(section, "Scroll_amount", fallback="")
            scroll_dir = cp.get(section, "Scroll", fallback="")
            scroll_amt2_raw = cp.get(section, "Scroll_amount2", fallback="")
            scroll_dir2 = cp.get(section, "Scroll2", fallback="")

            scroll_amount = 0
            if scroll_amt_raw:
                try:
                    scroll_amount = int(scroll_amt_raw)
                except ValueError:
                    pass

            scroll_amount2 = 0
            if scroll_amt2_raw:
                try:
                    scroll_amount2 = int(scroll_amt2_raw)
                except ValueError:
                    pass

            # Parse Ellydium-specific coordinates
            raw_xe = cp.get(section, "x_ellydium", fallback="")
            raw_ye = cp.get(section, "y_ellydium", fallback="")
            click_x_elly: int | None = None
            click_y_elly: int | None = None
            if raw_xe:
                try:
                    click_x_elly = int(raw_xe)
                except ValueError:
                    pass
            if raw_ye:
                try:
                    click_y_elly = int(raw_ye)
                except ValueError:
                    pass

            existing = self._db.get_ship_by_name(name)
            if existing:
                # Always refresh AHK-derived data (treat ShipList.ini as authoritative)
                existing.faction = faction
                existing.is_ellydium = is_ellydium
                if click_x is not None:
                    existing.click_x = click_x
                    existing.click_y = click_y
                existing.scroll_amount = scroll_amount
                existing.scroll_direction = scroll_dir
                existing.scroll_amount2 = scroll_amount2
                existing.scroll_direction2 = scroll_dir2
                if click_x_elly is not None:
                    existing.click_x_ellydium = click_x_elly
                    existing.click_y_ellydium = click_y_elly
                self._db.save_ship(existing)
                continue

            self._db.save_ship(Ship(
                name=name,
                faction=faction,
                is_ellydium=is_ellydium,
                click_x=click_x,
                click_y=click_y,
                scroll_amount=scroll_amount,
                scroll_direction=scroll_dir,
                scroll_amount2=scroll_amount2,
                scroll_direction2=scroll_dir2,
                click_x_ellydium=click_x_elly,
                click_y_ellydium=click_y_elly,
            ))
            count += 1

        return count

    # ── Builds (Builds/*.ini) ─────────────────────────────────────────

    def _import_builds(self) -> tuple[int, int]:
        if not self._builds_dir.exists():
            return 0, 0

        build_count = 0
        elly_count = 0

        ini_files = sorted(self._builds_dir.glob("*.ini"))
        for i, ini_path in enumerate(ini_files):
            ship_name = ini_path.stem
            if ship_name.lower() == "none":
                continue
            self._progress(f"Importing builds: {ship_name}", i, len(ini_files))

            ship = self._db.get_ship_by_name(ship_name)
            if ship is None:
                # Ship not in ShipList — create it as Unknown
                ship = Ship(name=ship_name, faction="Empire")
                self._db.save_ship(ship)

            cp = _read_ini(ini_path)

            for section in cp.sections():
                build_name = _strip_pipe(section)
                if not build_name or build_name.lower() == "none":
                    continue

                existing = self._db.get_build_by_name(ship.id, build_name)  # type: ignore[arg-type]
                if existing:
                    continue

                # Parse crew assignments
                crew: list[int] = []
                for ci in range(1, 16):
                    raw = cp.get(section, f"Crew{ci}", fallback="0")
                    try:
                        crew.append(int(raw) if raw else 0)
                    except ValueError:
                        crew.append(0)

                # Parse preset slot
                preset_raw = cp.get(section, "Preset", fallback="1")
                try:
                    preset_slot = int(preset_raw)
                except ValueError:
                    preset_slot = 1

                build = Build(
                    ship_id=ship.id,  # type: ignore[arg-type]
                    name=build_name,
                    preset_slot=preset_slot,
                    crew=crew,
                )
                self._db.save_build(build)
                build_count += 1

                # Parse Ellydium node states (Category_N = 0|1)
                node_states: dict[str, bool] = {}
                for key in cp.options(section):
                    if _NODE_KEY_RE.match(key):
                        raw_val = cp.get(section, key, fallback="0")
                        try:
                            node_states[key] = int(raw_val) != 0
                        except ValueError:
                            node_states[key] = False

                if node_states and build.id is not None:
                    self._db.save_node_states(build.id, node_states)
                    elly_count += len(node_states)

        return build_count, elly_count

    # ── Ellydium tree definitions (Builds/Ellydium/*.ini) ─────────────

    def _import_ellydium_tree_defs(self) -> int:
        if not self._ellydium_dir.exists():
            return 0

        count = 0
        # Import from both the root Ellydium dir and Template subdir
        for search_dir in (self._ellydium_dir, self._ellydium_dir / "Template"):
            if not search_dir.exists():
                continue

            for ini_path in sorted(search_dir.glob("*.ini")):
                ship_name = ini_path.stem
                ship = self._db.get_ship_by_name(ship_name)
                if ship is None:
                    continue

                cp = _read_ini(ini_path)
                defs: list[EllydiumNodeDef] = []

                for section in cp.sections():
                    key = section.strip()

                    # Skip the points section — import it separately
                    if key.lower() == "ship_tree_points":
                        continue

                    # Must match Category_N format
                    if not _NODE_KEY_RE.match(key):
                        continue

                    m = _NODE_KEY_RE.match(key)
                    if not m:
                        continue

                    category = m.group(1)
                    defs.append(EllydiumNodeDef(
                        ship_id=ship.id,  # type: ignore[arg-type]
                        node_key=key,
                        category=category,
                        branch=int(cp.get(section, "Branch", fallback="0")),
                        cost=int(cp.get(section, "Cost", fallback="0")),
                        effect=cp.get(section, "Effect", fallback=""),
                    ))

                if defs:
                    self._db.save_tree_defs_bulk(defs)
                    count += len(defs)

                # Import tree point thresholds as metadata
                if cp.has_section("Ship_tree_Points"):
                    pts = cp["Ship_tree_Points"]
                    max_pts = int(pts.get("Max", "0"))
                    # Store as a special node def with category="TreePoints"
                    meta: list[EllydiumNodeDef] = []
                    meta.append(EllydiumNodeDef(
                        ship_id=ship.id,  # type: ignore[arg-type]
                        node_key="TreePoints_Max",
                        category="TreePoints",
                        branch=0,
                        cost=max_pts,
                        effect="Maximum points",
                    ))
                    for tree_key in pts:
                        if tree_key.lower().startswith("tree"):
                            tree_num = tree_key.replace("Tree", "").replace("tree", "")
                            try:
                                threshold = int(pts[tree_key])
                            except ValueError:
                                continue
                            meta.append(EllydiumNodeDef(
                                ship_id=ship.id,  # type: ignore[arg-type]
                                node_key=f"TreePoints_Branch{tree_num}",
                                category="TreePoints",
                                branch=int(tree_num),
                                cost=threshold,
                                effect=f"Branch {tree_num} unlock threshold",
                            ))
                    if meta:
                        self._db.save_tree_defs_bulk(meta)

        return count

    # ── Presets (Preferences.ini) ─────────────────────────────────────

    def _import_presets(self) -> int:
        prefs_path = self._settings_dir / "Preferences.ini"
        if not prefs_path.exists():
            return 0

        cp = _read_ini(prefs_path)
        count = 0

        for idx, section in enumerate(cp.sections()):
            preset_name = _strip_pipe(section)
            if not preset_name or preset_name.lower() == "none":
                continue

            existing = self._db.get_preset_by_name(preset_name)
            if existing:
                continue

            unequip_raw = cp.get(section, "Unequip", fallback="0")
            try:
                unequip = int(unequip_raw) != 0
            except ValueError:
                unequip = False

            preset = Preset(
                name=preset_name,
                sort_order=idx,
                unequip=unequip,
            )
            self._db.save_preset(preset)

            # Build 4 slots
            slots: list[PresetSlot] = []
            for sn in range(1, 5):
                enabled_raw = cp.get(section, f"Checked{sn}", fallback="0")
                ship_name = cp.get(section, f"Ship{sn}", fallback="None")
                build_name = cp.get(section, f"Build{sn}", fallback="None")

                try:
                    enabled = int(enabled_raw) != 0
                except ValueError:
                    enabled = False

                ship_id = None
                build_id = None

                if ship_name and ship_name.lower() != "none":
                    ship = self._db.get_ship_by_name(ship_name)
                    if ship:
                        ship_id = ship.id
                        if build_name and build_name.lower() != "none":
                            build = self._db.get_build_by_name(ship.id, build_name)  # type: ignore[arg-type]
                            if build:
                                build_id = build.id

                slots.append(PresetSlot(
                    preset_id=preset.id,  # type: ignore[arg-type]
                    slot_number=sn,
                    enabled=enabled,
                    ship_id=ship_id,
                    build_id=build_id,
                ))

            self._db.save_preset_slots(preset.id, slots)  # type: ignore[arg-type]
            count += 1

        return count

    # ── UI Coordinates (Coordinates.ini → settings) ────────────────────

    def _import_coordinates(self) -> int:
        """Import UI coordinates from Coordinates.ini into settings."""
        if self._settings is None:
            return 0

        coords_path = self._settings_dir / "Coordinates.ini"
        if not coords_path.exists():
            return 0

        cp = _read_ini(coords_path)
        count = 0
        s = self._settings

        def _coord(section: str) -> Coordinate | None:
            if not cp.has_section(section):
                return None
            try:
                x = int(cp.get(section, "x"))
                y = int(cp.get(section, "y"))
                return Coordinate(x=x, y=y)
            except (ValueError, configparser.NoOptionError):
                return None

        # Faction tabs
        for faction in ("Empire", "Federation", "Jericho", "Ellydium", "Unique"):
            c = _coord(faction)
            if c is not None:
                s.faction_coords[faction] = c
                count += 1

        # Ship slots
        for i in range(1, 5):
            c = _coord(f"Slot{i}")
            if c is not None:
                s.slot_coords[i - 1] = c
                count += 1

        # Presets
        for i in range(1, 5):
            c = _coord(f"Preset{i}")
            if c is not None:
                s.preset_coords[i - 1] = c
                count += 1

        # Load Preset, Yes, Scroll, Back
        c = _coord("Load Preset")
        if c is not None:
            s.load_preset_coord = c
            count += 1

        c = _coord("Yes")
        if c is not None:
            s.yes_coord = c
            count += 1

        c = _coord("Scroll")
        if c is not None:
            s.scroll_coord = c
            count += 1

        c = _coord("Back")
        if c is not None:
            s.back_coord = c
            count += 1

        # Crew buttons (A-D → indices 0-3)
        for i, label in enumerate(("Crew_A", "Crew_B", "Crew_C", "Crew_D")):
            c = _coord(label)
            if c is not None:
                s.crew_button_coords[i] = c
                count += 1

        # Crew grid corners for interpolation
        c = _coord("Crew1-1")
        if c is not None:
            s.crew_grid_start = c
            count += 1

        c = _coord("Crew15-3")
        if c is not None:
            s.crew_grid_end = c
            count += 1

        # Implant
        if cp.has_section("Implant"):
            c = _coord("Implant")
            if c is not None:
                s.implant_coord = c
                count += 1
            color = cp.get("Implant", "implant_color", fallback="")
            if color:
                s.implant_color = color

        # Apply Ellydium
        c = _coord("Apply_Ellydium")
        if c is not None:
            s.apply_ellydium_coord = c
            count += 1

        # Ellydium colors
        if cp.has_section("Setup_Colors"):
            sec = "Setup_Colors"
            s.ellydium_colors.normal_on = cp.get(sec, "Normal_ON", fallback=s.ellydium_colors.normal_on)
            s.ellydium_colors.normal_off = cp.get(sec, "Normal_OFF", fallback=s.ellydium_colors.normal_off)
            s.ellydium_colors.spec_on = cp.get(sec, "Spec_ON", fallback=s.ellydium_colors.spec_on)
            s.ellydium_colors.spec_off = cp.get(sec, "Spec_OFF", fallback=s.ellydium_colors.spec_off)

        s.save()
        return count
