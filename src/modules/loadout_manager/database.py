"""
SQLite database layer for the Loadout Manager module.

Stores ships, builds (with crew assignments), Ellydium tree definitions
and node states, multi-slot presets, and cached template anchor positions.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from src.core.config import USER_DATA_DIR

DB_PATH: Path = USER_DATA_DIR / "loadout_manager.db"

# ── Factions ──────────────────────────────────────────────────────────

FACTIONS = ("Empire", "Federation", "Jericho", "Ellydium", "Unique")

# ── Data classes ──────────────────────────────────────────────────────


@dataclass
class Ship:
    id: int | None = None
    name: str = ""
    faction: str = "None"
    is_ellydium: bool = False
    click_x: int | None = None
    click_y: int | None = None
    scroll_amount: int = 0
    scroll_direction: str = ""
    scroll_amount2: int = 0
    scroll_direction2: str = ""
    click_x_ellydium: int | None = None
    click_y_ellydium: int | None = None


@dataclass
class Build:
    id: int | None = None
    ship_id: int = 0
    name: str = ""
    preset_slot: int = 1
    crew: list[int] = field(default_factory=lambda: [0] * 15)

    def crew_json(self) -> str:
        return json.dumps(self.crew)

    @staticmethod
    def crew_from_json(raw: str | None) -> list[int]:
        if not raw:
            return [0] * 15
        try:
            data = json.loads(raw)
            if isinstance(data, list) and len(data) == 15:
                return [int(v) for v in data]
        except (json.JSONDecodeError, ValueError):
            pass
        return [0] * 15


@dataclass
class EllydiumNodeDef:
    id: int | None = None
    ship_id: int = 0
    node_key: str = ""
    category: str = ""
    branch: int = 0
    cost: int = 0
    effect: str = ""


@dataclass
class EllydiumNodeState:
    id: int | None = None
    build_id: int = 0
    node_key: str = ""
    enabled: bool = False


@dataclass
class Preset:
    id: int | None = None
    name: str = ""
    sort_order: int = 0
    unequip: bool = False


@dataclass
class PresetSlot:
    id: int | None = None
    preset_id: int = 0
    slot_number: int = 1
    enabled: bool = False
    ship_id: int | None = None
    build_id: int | None = None


@dataclass
class TemplateAnchor:
    id: int | None = None
    element_name: str = ""
    x: int = 0
    y: int = 0
    confidence: float = 0.0
    last_detected: str = ""


# ── Schema ────────────────────────────────────────────────────────────

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS ships (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    name              TEXT    UNIQUE NOT NULL,
    faction           TEXT    NOT NULL DEFAULT 'None',
    is_ellydium       INTEGER NOT NULL DEFAULT 0,
    click_x           INTEGER,
    click_y           INTEGER,
    scroll_amount     INTEGER NOT NULL DEFAULT 0,
    scroll_direction  TEXT    NOT NULL DEFAULT '',
    scroll_amount2    INTEGER NOT NULL DEFAULT 0,
    scroll_direction2 TEXT    NOT NULL DEFAULT '',
    click_x_ellydium  INTEGER,
    click_y_ellydium  INTEGER
);

CREATE TABLE IF NOT EXISTS builds (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ship_id     INTEGER NOT NULL REFERENCES ships(id) ON DELETE CASCADE,
    name        TEXT    NOT NULL,
    preset_slot INTEGER NOT NULL DEFAULT 1,
    crew        TEXT    NOT NULL DEFAULT '[]',
    UNIQUE(ship_id, name)
);

CREATE TABLE IF NOT EXISTS ellydium_tree_defs (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    ship_id  INTEGER NOT NULL REFERENCES ships(id) ON DELETE CASCADE,
    node_key TEXT    NOT NULL,
    category TEXT    NOT NULL,
    branch   INTEGER NOT NULL DEFAULT 0,
    cost     INTEGER NOT NULL DEFAULT 0,
    effect   TEXT    NOT NULL DEFAULT '',
    UNIQUE(ship_id, node_key)
);

CREATE TABLE IF NOT EXISTS ellydium_node_states (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    build_id INTEGER NOT NULL REFERENCES builds(id) ON DELETE CASCADE,
    node_key TEXT    NOT NULL,
    enabled  INTEGER NOT NULL DEFAULT 0,
    UNIQUE(build_id, node_key)
);

CREATE TABLE IF NOT EXISTS presets (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT    UNIQUE NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    unequip    INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS preset_slots (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    preset_id   INTEGER NOT NULL REFERENCES presets(id) ON DELETE CASCADE,
    slot_number INTEGER NOT NULL,
    enabled     INTEGER NOT NULL DEFAULT 0,
    ship_id     INTEGER REFERENCES ships(id) ON DELETE SET NULL,
    build_id    INTEGER REFERENCES builds(id) ON DELETE SET NULL,
    UNIQUE(preset_id, slot_number)
);

CREATE TABLE IF NOT EXISTS template_anchors (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    element_name  TEXT    UNIQUE NOT NULL,
    x             INTEGER NOT NULL DEFAULT 0,
    y             INTEGER NOT NULL DEFAULT 0,
    confidence    REAL    NOT NULL DEFAULT 0.0,
    last_detected TEXT    NOT NULL DEFAULT ''
);
"""


# ── DAO ───────────────────────────────────────────────────────────────

class LoadoutDatabase:
    """Data-access object wrapping a single SQLite connection."""

    def __init__(self, db_path: Path | None = None) -> None:
        self._path = db_path or DB_PATH
        self._conn: sqlite3.Connection | None = None

    # -- Connection lifecycle ------------------------------------------

    def open(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._path), check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.executescript(_SCHEMA_SQL)
        self._migrate()

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            raise RuntimeError("Database not open")
        return self._conn

    def _migrate(self) -> None:
        """Add columns introduced after initial schema creation."""
        cursor = self.conn.execute("PRAGMA table_info(ships)")
        existing = {row[1] for row in cursor.fetchall()}
        migrations = [
            ("click_x", "INTEGER"),
            ("click_y", "INTEGER"),
            ("scroll_amount", "INTEGER NOT NULL DEFAULT 0"),
            ("scroll_direction", "TEXT NOT NULL DEFAULT ''"),
            ("scroll_amount2", "INTEGER NOT NULL DEFAULT 0"),
            ("scroll_direction2", "TEXT NOT NULL DEFAULT ''"),
            ("click_x_ellydium", "INTEGER"),
            ("click_y_ellydium", "INTEGER"),
        ]
        for col_name, col_def in migrations:
            if col_name not in existing:
                self.conn.execute(f"ALTER TABLE ships ADD COLUMN {col_name} {col_def}")
        self.conn.commit()

    # ── Ships ─────────────────────────────────────────────────────────

    _SHIP_COLS = ("id, name, faction, is_ellydium, click_x, click_y, "
                  "scroll_amount, scroll_direction, scroll_amount2, scroll_direction2, "
                  "click_x_ellydium, click_y_ellydium")

    @staticmethod
    def _row_to_ship(r: tuple) -> Ship:
        return Ship(
            id=r[0], name=r[1], faction=r[2], is_ellydium=bool(r[3]),
            click_x=r[4], click_y=r[5],
            scroll_amount=r[6] or 0, scroll_direction=r[7] or "",
            scroll_amount2=r[8] or 0, scroll_direction2=r[9] or "",
            click_x_ellydium=r[10], click_y_ellydium=r[11],
        )

    def get_ships(self, faction: str | None = None) -> list[Ship]:
        if faction:
            rows = self.conn.execute(
                f"SELECT {self._SHIP_COLS} FROM ships "
                "WHERE faction = ? ORDER BY name",
                (faction,),
            ).fetchall()
        else:
            rows = self.conn.execute(
                f"SELECT {self._SHIP_COLS} FROM ships ORDER BY name"
            ).fetchall()
        return [self._row_to_ship(r) for r in rows]

    def get_ship_by_name(self, name: str) -> Ship | None:
        row = self.conn.execute(
            f"SELECT {self._SHIP_COLS} FROM ships WHERE name = ?",
            (name,),
        ).fetchone()
        if row:
            return self._row_to_ship(row)
        return None

    def get_ship_by_id(self, ship_id: int) -> Ship | None:
        row = self.conn.execute(
            f"SELECT {self._SHIP_COLS} FROM ships WHERE id = ?",
            (ship_id,),
        ).fetchone()
        if row:
            return self._row_to_ship(row)
        return None

    def save_ship(self, ship: Ship) -> int:
        if ship.id is not None:
            self.conn.execute(
                "UPDATE ships SET name=?, faction=?, is_ellydium=?, "
                "click_x=?, click_y=?, scroll_amount=?, scroll_direction=?, "
                "scroll_amount2=?, scroll_direction2=?, "
                "click_x_ellydium=?, click_y_ellydium=? WHERE id=?",
                (ship.name, ship.faction, int(ship.is_ellydium),
                 ship.click_x, ship.click_y,
                 ship.scroll_amount, ship.scroll_direction,
                 ship.scroll_amount2, ship.scroll_direction2,
                 ship.click_x_ellydium, ship.click_y_ellydium,
                 ship.id),
            )
            self.conn.commit()
            return ship.id
        cur = self.conn.execute(
            "INSERT INTO ships (name, faction, is_ellydium, "
            "click_x, click_y, scroll_amount, scroll_direction, "
            "scroll_amount2, scroll_direction2, "
            "click_x_ellydium, click_y_ellydium) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (ship.name, ship.faction, int(ship.is_ellydium),
             ship.click_x, ship.click_y,
             ship.scroll_amount, ship.scroll_direction,
             ship.scroll_amount2, ship.scroll_direction2,
             ship.click_x_ellydium, ship.click_y_ellydium),
        )
        self.conn.commit()
        ship.id = cur.lastrowid
        return ship.id  # type: ignore[return-value]

    def delete_ship(self, ship_id: int) -> None:
        self.conn.execute("DELETE FROM ships WHERE id = ?", (ship_id,))
        self.conn.commit()

    def rename_ship(self, ship_id: int, new_name: str) -> None:
        self.conn.execute("UPDATE ships SET name = ? WHERE id = ?", (new_name, ship_id))
        self.conn.commit()

    # ── Builds ────────────────────────────────────────────────────────

    def get_builds(self, ship_id: int) -> list[Build]:
        rows = self.conn.execute(
            "SELECT id, ship_id, name, preset_slot, crew FROM builds "
            "WHERE ship_id = ? ORDER BY name",
            (ship_id,),
        ).fetchall()
        return [
            Build(
                id=r[0], ship_id=r[1], name=r[2],
                preset_slot=r[3], crew=Build.crew_from_json(r[4]),
            )
            for r in rows
        ]

    def get_build_by_id(self, build_id: int) -> Build | None:
        row = self.conn.execute(
            "SELECT id, ship_id, name, preset_slot, crew FROM builds WHERE id = ?",
            (build_id,),
        ).fetchone()
        if row:
            return Build(
                id=row[0], ship_id=row[1], name=row[2],
                preset_slot=row[3], crew=Build.crew_from_json(row[4]),
            )
        return None

    def get_build_by_name(self, ship_id: int, build_name: str) -> Build | None:
        row = self.conn.execute(
            "SELECT id, ship_id, name, preset_slot, crew FROM builds "
            "WHERE ship_id = ? AND name = ?",
            (ship_id, build_name),
        ).fetchone()
        if row:
            return Build(
                id=row[0], ship_id=row[1], name=row[2],
                preset_slot=row[3], crew=Build.crew_from_json(row[4]),
            )
        return None

    def save_build(self, build: Build) -> int:
        crew_json = build.crew_json()
        if build.id is not None:
            self.conn.execute(
                "UPDATE builds SET ship_id=?, name=?, preset_slot=?, crew=? WHERE id=?",
                (build.ship_id, build.name, build.preset_slot, crew_json, build.id),
            )
            self.conn.commit()
            return build.id
        cur = self.conn.execute(
            "INSERT INTO builds (ship_id, name, preset_slot, crew) VALUES (?, ?, ?, ?)",
            (build.ship_id, build.name, build.preset_slot, crew_json),
        )
        self.conn.commit()
        build.id = cur.lastrowid
        return build.id  # type: ignore[return-value]

    def delete_build(self, build_id: int) -> None:
        self.conn.execute("DELETE FROM builds WHERE id = ?", (build_id,))
        self.conn.commit()

    def rename_build(self, build_id: int, new_name: str) -> None:
        self.conn.execute("UPDATE builds SET name = ? WHERE id = ?", (new_name, build_id))
        self.conn.commit()

    # ── Ellydium tree definitions ─────────────────────────────────────

    def get_tree_defs(self, ship_id: int) -> list[EllydiumNodeDef]:
        rows = self.conn.execute(
            "SELECT id, ship_id, node_key, category, branch, cost, effect "
            "FROM ellydium_tree_defs WHERE ship_id = ? ORDER BY node_key",
            (ship_id,),
        ).fetchall()
        return [
            EllydiumNodeDef(
                id=r[0], ship_id=r[1], node_key=r[2],
                category=r[3], branch=r[4], cost=r[5], effect=r[6],
            )
            for r in rows
        ]

    def save_tree_def(self, node_def: EllydiumNodeDef) -> int:
        if node_def.id is not None:
            self.conn.execute(
                "UPDATE ellydium_tree_defs SET ship_id=?, node_key=?, category=?, "
                "branch=?, cost=?, effect=? WHERE id=?",
                (node_def.ship_id, node_def.node_key, node_def.category,
                 node_def.branch, node_def.cost, node_def.effect, node_def.id),
            )
            self.conn.commit()
            return node_def.id
        cur = self.conn.execute(
            "INSERT OR REPLACE INTO ellydium_tree_defs "
            "(ship_id, node_key, category, branch, cost, effect) VALUES (?, ?, ?, ?, ?, ?)",
            (node_def.ship_id, node_def.node_key, node_def.category,
             node_def.branch, node_def.cost, node_def.effect),
        )
        self.conn.commit()
        node_def.id = cur.lastrowid
        return node_def.id  # type: ignore[return-value]

    def save_tree_defs_bulk(self, defs: list[EllydiumNodeDef]) -> None:
        self.conn.executemany(
            "INSERT OR REPLACE INTO ellydium_tree_defs "
            "(ship_id, node_key, category, branch, cost, effect) VALUES (?, ?, ?, ?, ?, ?)",
            [(d.ship_id, d.node_key, d.category, d.branch, d.cost, d.effect) for d in defs],
        )
        self.conn.commit()

    # ── Ellydium node states ──────────────────────────────────────────

    def get_node_states(self, build_id: int) -> dict[str, bool]:
        rows = self.conn.execute(
            "SELECT node_key, enabled FROM ellydium_node_states WHERE build_id = ?",
            (build_id,),
        ).fetchall()
        return {r[0]: bool(r[1]) for r in rows}

    def save_node_states(self, build_id: int, states: dict[str, bool]) -> None:
        self.conn.execute(
            "DELETE FROM ellydium_node_states WHERE build_id = ?", (build_id,),
        )
        self.conn.executemany(
            "INSERT INTO ellydium_node_states (build_id, node_key, enabled) VALUES (?, ?, ?)",
            [(build_id, key, int(val)) for key, val in states.items()],
        )
        self.conn.commit()

    # ── Presets ───────────────────────────────────────────────────────

    def get_presets(self) -> list[Preset]:
        rows = self.conn.execute(
            "SELECT id, name, sort_order, unequip FROM presets ORDER BY name COLLATE NOCASE"
        ).fetchall()
        return [
            Preset(id=r[0], name=r[1], sort_order=r[2], unequip=bool(r[3]))
            for r in rows
        ]

    def get_preset_by_name(self, name: str) -> Preset | None:
        row = self.conn.execute(
            "SELECT id, name, sort_order, unequip FROM presets WHERE name = ?",
            (name,),
        ).fetchone()
        if row:
            return Preset(id=row[0], name=row[1], sort_order=row[2], unequip=bool(row[3]))
        return None

    def save_preset(self, preset: Preset) -> int:
        if preset.id is not None:
            self.conn.execute(
                "UPDATE presets SET name=?, sort_order=?, unequip=? WHERE id=?",
                (preset.name, preset.sort_order, int(preset.unequip), preset.id),
            )
            self.conn.commit()
            return preset.id
        cur = self.conn.execute(
            "INSERT INTO presets (name, sort_order, unequip) VALUES (?, ?, ?)",
            (preset.name, preset.sort_order, int(preset.unequip)),
        )
        self.conn.commit()
        preset.id = cur.lastrowid
        return preset.id  # type: ignore[return-value]

    def delete_preset(self, preset_id: int) -> None:
        self.conn.execute("DELETE FROM presets WHERE id = ?", (preset_id,))
        self.conn.commit()

    def rename_preset(self, preset_id: int, new_name: str) -> None:
        self.conn.execute("UPDATE presets SET name = ? WHERE id = ?", (new_name, preset_id))
        self.conn.commit()

    # ── Preset slots ──────────────────────────────────────────────────

    def get_preset_slots(self, preset_id: int) -> list[PresetSlot]:
        rows = self.conn.execute(
            "SELECT id, preset_id, slot_number, enabled, ship_id, build_id "
            "FROM preset_slots WHERE preset_id = ? ORDER BY slot_number",
            (preset_id,),
        ).fetchall()
        return [
            PresetSlot(
                id=r[0], preset_id=r[1], slot_number=r[2],
                enabled=bool(r[3]), ship_id=r[4], build_id=r[5],
            )
            for r in rows
        ]

    def save_preset_slots(self, preset_id: int, slots: list[PresetSlot]) -> None:
        self.conn.execute(
            "DELETE FROM preset_slots WHERE preset_id = ?", (preset_id,),
        )
        self.conn.executemany(
            "INSERT INTO preset_slots "
            "(preset_id, slot_number, enabled, ship_id, build_id) "
            "VALUES (?, ?, ?, ?, ?)",
            [
                (preset_id, s.slot_number, int(s.enabled), s.ship_id, s.build_id)
                for s in slots
            ],
        )
        self.conn.commit()

    # ── Template anchors ──────────────────────────────────────────────

    def get_anchors(self) -> dict[str, TemplateAnchor]:
        rows = self.conn.execute(
            "SELECT id, element_name, x, y, confidence, last_detected "
            "FROM template_anchors"
        ).fetchall()
        return {
            r[1]: TemplateAnchor(
                id=r[0], element_name=r[1], x=r[2], y=r[3],
                confidence=r[4], last_detected=r[5],
            )
            for r in rows
        }

    def save_anchor(self, anchor: TemplateAnchor) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO template_anchors "
            "(element_name, x, y, confidence, last_detected) VALUES (?, ?, ?, ?, ?)",
            (anchor.element_name, anchor.x, anchor.y,
             anchor.confidence, anchor.last_detected),
        )
        self.conn.commit()

    def save_anchors_bulk(self, anchors: list[TemplateAnchor]) -> None:
        self.conn.executemany(
            "INSERT OR REPLACE INTO template_anchors "
            "(element_name, x, y, confidence, last_detected) VALUES (?, ?, ?, ?, ?)",
            [(a.element_name, a.x, a.y, a.confidence, a.last_detected) for a in anchors],
        )
        self.conn.commit()
