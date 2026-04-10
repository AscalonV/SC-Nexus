"""
Combat log parser for Star Conflict.

Pure logic — no Qt, no UI.  Safe to import inside multiprocessing workers.

Public API
----------
find_combat_logs(root)          → list[Path]
build_fights(log_file)          → list[Fight]
parse_file_quick(args)          → list[Fight]   (multiprocessing entry point)
aggregate_stats(fight)          → dict[str, ParticipantStats]
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Callable, Iterator

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class CombatEvent:
    timestamp:  datetime
    event_type: str          # "damage" | "heal" | "kill" | "reward" | "aura_apply" |
                             #  "aura_cancel" | "participant" | "spawn" | "session_start" |
                             #  "game_end"
    actor:      str = ""
    target:     str = ""
    amount:     float = 0.0
    source:     str = ""
    actor_id:   str = ""
    target_id:  str = ""
    raw:        str = ""


@dataclass
class ParticipantStats:
    name:           str
    damage_dealt:   float = 0.0
    damage_taken:   float = 0.0
    healing_dealt:  float = 0.0   # heals given to others
    healing_taken:  float = 0.0   # heals received (from others)
    self_heal:      float = 0.0
    kills:          int   = 0


@dataclass
class Fight:
    id:                   str
    file_path:            str
    start:                datetime
    end:                  datetime
    game_mode:            str = ""
    actual_game_time_sec: float = 0.0
    events:               list[CombatEvent] = field(default_factory=list)

    @property
    def duration_sec(self) -> float:
        return (self.end - self.start).total_seconds()

    @property
    def display_label(self) -> str:
        ts = self.start.strftime("%Y-%m-%d  %H:%M")
        mode = f"  [{self.game_mode}]" if self.game_mode else ""
        return f"{ts}{mode}"


# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------
# Timestamps in SC logs use HH:MM:SS.mmm (milliseconds present).
# All patterns use search() so leading garbage / extra spaces are tolerated.

_TS_PAT = r"\d{2}:\d{2}:\d{2}(?:\.\d+)?"   # matches HH:MM:SS or HH:MM:SS.mmm

# e.g. 14:27:06.042  CMBT   | Damage   n/a|-000000001 ->   AscalonV|868   787.03 (h:...) WeaponName|id
DAMAGE_HEAL_RE = re.compile(
    rf"(?P<ts>{_TS_PAT}).*?\b(?P<kind>Damage|Heal)\s+"
    r"(?P<actor>[^|\t]+)\|(?P<actor_id>\S+)\s*->\s*(?P<target>[^|\t]+)\|(?P<target_id>\S+)\s+"
    r"(?P<amount>[\d.]+)"
    r"(?:\s+(?P<source>.*))?$",
    re.IGNORECASE,
)

# e.g. 22:14:00.000  CMBT   | Reward  PlayerName  100  for  victory
REWARD_RE = re.compile(
    rf"(?P<ts>{_TS_PAT}).*?\bReward\s+(?P<actor>[^\t]+?)\s+\d+.*?for\s+(?P<result>victory|defeat)",
    re.IGNORECASE,
)

# e.g. 17:42:23.941  CMBT   | Killed C|1129;   killer C|822 Weapon
KILL_RE = re.compile(
    rf"(?P<ts>{_TS_PAT}).*?Killed\s+(?P<target>[^|;]+)\|(?P<target_id>\S+?);\s+"
    r"killer\s+(?P<killer>[^|\s]+)\|(?P<killer_id>\S+?)(?:\s+(?P<source>.*))?$",
    re.IGNORECASE,
)

# e.g. 14:26:56.015  CMBT   | ======= Start gameplay 'ClanShip' map '...' =======
SESSION_START_RE = re.compile(
    r"Start\s+gameplay\s+'(?P<mode>[^']+)'",
    re.IGNORECASE,
)

# e.g. 22:11:48.170  CMBT   | Gameplay finished. ... Actual game time 253.3 sec
GAME_END_RE = re.compile(
    rf"(?P<ts>{_TS_PAT}).*?Actual\s+game\s+time\s+(?P<secs>[\d.]+)",
    re.IGNORECASE,
)

# e.g. Apply aura 'BuffNearDeath_big' id 6 type AURA_NEAR_DEATH to 'PlayerName'
AURA_APPLY_RE = re.compile(
    r"Apply\s+aura\s+'(?P<aura>[^']+)'\s+id\s+\d+\s+type\s+\S+\s+to\s+'(?P<target>[^']+)'",
    re.IGNORECASE,
)

# e.g. Cancel aura 'BuffNearDeath_big' id 6 type AURA_NEAR_DEATH from 'PlayerName'
AURA_CANCEL_RE = re.compile(
    r"Cancel\s+aura\s+'(?P<aura>[^']+)'\s+id\s+\d+\s+type\s+\S+\s+from\s+'(?P<target>[^']+)'",
    re.IGNORECASE,
)

PARTICIPANT_RE = re.compile(
    r"Participant\s+(?P<actor>[^\t]+)", re.IGNORECASE
)
SPAWN_RE = re.compile(
    r"Spawn\s+SpaceShip\s+for\s+(?P<actor>[^\s(]+)", re.IGNORECASE
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _folder_date(path: Path) -> date | None:
    """Extract the date from a log folder name like '2024.05.31 14.22.10.123'."""
    try:
        parts = path.name.split(" ")[0].split(".")
        return date(int(parts[0]), int(parts[1]), int(parts[2]))
    except Exception:
        return None


def _parse_timestamp(hms: str, folder_hint: date | None) -> datetime:
    # Strip milliseconds if present (HH:MM:SS.mmm → HH:MM:SS)
    hms_clean = hms.split(".")[0]
    h, m, s = map(int, hms_clean.split(":"))
    d = folder_hint or date.today()
    return datetime(d.year, d.month, d.day, h, m, s)


def _strip_id(text: str) -> str:
    """Remove the '|ID' suffix from an actor/target string."""
    return text.split("|")[0].strip()


def _clean_source(text: str) -> str:
    """Remove '(h:x s:y)' annotations from a source string."""
    return re.sub(r"\([^)]*\)", "", text).strip()


def _stream_lines(path: Path) -> Iterator[str]:
    """Memory-efficient UTF-8 line iterator with ISO-8859-1 fallback."""
    try:
        with path.open(encoding="utf-8", errors="replace") as fh:
            yield from fh
    except OSError:
        return


# ---------------------------------------------------------------------------
# Event parsing
# ---------------------------------------------------------------------------

def parse_events(lines: Iterator[str], folder_hint: date | None) -> list[CombatEvent]:
    """Convert raw log lines into a list of CombatEvent objects."""
    events: list[CombatEvent] = []

    for raw in lines:
        line = raw.rstrip("\n")

        # ---- Damage / Heal ----------------------------------------
        m = DAMAGE_HEAL_RE.search(line)
        if m:
            raw_source = (m.group("source") or "").strip()
            # Strip (h:x s:y) annotations and trailing |id suffixes
            raw_source = re.sub(r"\([^)]*\)", "", raw_source).strip()
            raw_source = re.sub(r"\|\S+$", "", raw_source).strip()
            events.append(CombatEvent(
                timestamp  = _parse_timestamp(m.group("ts"), folder_hint),
                event_type = m.group("kind").lower(),
                actor      = _strip_id(m.group("actor").strip()),
                actor_id   = m.group("actor_id") or "",
                target     = _strip_id(m.group("target").strip()),
                target_id  = m.group("target_id") or "",
                amount     = float(m.group("amount")),
                source     = raw_source,
                raw        = line,
            ))
            continue

        # ---- Reward (victory / defeat) ----------------------------
        m = REWARD_RE.search(line)
        if m:
            events.append(CombatEvent(
                timestamp  = _parse_timestamp(m.group("ts"), folder_hint),
                event_type = "reward",
                actor      = _strip_id(m.group("actor").strip()),
                source     = m.group("result").lower(),
                raw        = line,
            ))
            continue

        # ---- Session start ----------------------------------------
        m = SESSION_START_RE.search(line)
        if m:
            # Extract timestamp separately (SESSION_START_RE has no ts group)
            ts_m = re.search(r"\d{2}:\d{2}:\d{2}(?:\.\d+)?", line)
            ts_str = ts_m.group(0) if ts_m else "00:00:00"
            events.append(CombatEvent(
                timestamp  = _parse_timestamp(ts_str, folder_hint),
                event_type = "session_start",
                source     = m.group("mode"),
                raw        = line,
            ))
            continue

        # ---- Kill -------------------------------------------------
        m = KILL_RE.search(line)
        if m:
            ts_m = re.search(r"\d{2}:\d{2}:\d{2}(?:\.\d+)?", line)
            ts_str = ts_m.group(0) if ts_m else "00:00:00"
            events.append(CombatEvent(
                timestamp  = _parse_timestamp(ts_str, folder_hint),
                event_type = "kill",
                target     = _strip_id(m.group("target").strip()),
                target_id  = m.group("target_id") or "",
                actor      = _strip_id(m.group("killer").strip()),
                actor_id   = m.group("killer_id") or "",
                raw        = line,
            ))
            continue

        # ---- Aura apply ------------------------------------------
        m = AURA_APPLY_RE.search(line)
        if m:
            ts_m = re.search(r"\d{2}:\d{2}:\d{2}(?:\.\d+)?", line)
            ts_str = ts_m.group(0) if ts_m else "00:00:00"
            events.append(CombatEvent(
                timestamp  = _parse_timestamp(ts_str, folder_hint),
                event_type = "aura_apply",
                source     = m.group("aura"),
                target     = m.group("target"),
                raw        = line,
            ))
            continue

        # ---- Aura cancel -----------------------------------------
        m = AURA_CANCEL_RE.search(line)
        if m:
            ts_m = re.search(r"\d{2}:\d{2}:\d{2}(?:\.\d+)?", line)
            ts_str = ts_m.group(0) if ts_m else "00:00:00"
            events.append(CombatEvent(
                timestamp  = _parse_timestamp(ts_str, folder_hint),
                event_type = "aura_cancel",
                source     = m.group("aura"),
                target     = m.group("target"),
                raw        = line,
            ))
            continue

        # ---- Game end --------------------------------------------
        m = GAME_END_RE.search(line)
        if m:
            events.append(CombatEvent(
                timestamp  = _parse_timestamp(m.group("ts"), folder_hint),
                event_type = "game_end",
                amount     = float(m.group("secs")),
                raw        = line,
            ))
            continue

    return events


# ---------------------------------------------------------------------------
# Fight segmentation
# ---------------------------------------------------------------------------

_MAX_GAP_SECONDS = 120


def split_into_fights(events: list[CombatEvent]) -> list[list[CombatEvent]]:
    """
    Split a flat event list into individual fight segments.

    Hard split on every ``session_start`` event.
    Soft split when the gap between consecutive combat events exceeds
    _MAX_GAP_SECONDS (120 s).
    """
    if not events:
        return []

    fights: list[list[CombatEvent]] = []
    current: list[CombatEvent] = []
    last_ts: datetime | None = None

    for ev in events:
        is_combat = ev.event_type in ("damage", "heal", "kill")

        if ev.event_type == "session_start":
            if current:
                fights.append(current)
            current = [ev]
            last_ts = ev.timestamp
            continue

        if is_combat and last_ts and (ev.timestamp - last_ts).total_seconds() > _MAX_GAP_SECONDS:
            if current:
                fights.append(current)
            current = []

        current.append(ev)
        if is_combat:
            last_ts = ev.timestamp

    if current:
        fights.append(current)

    return fights


# ---------------------------------------------------------------------------
# Stat aggregation
# ---------------------------------------------------------------------------

def aggregate_stats(fight: Fight) -> dict[str, ParticipantStats]:
    """Aggregate per-participant damage/healing/kill stats for a Fight."""
    stats: dict[str, ParticipantStats] = {}

    def _get(name: str) -> ParticipantStats:
        if name not in stats:
            stats[name] = ParticipantStats(name=name)
        return stats[name]

    for ev in fight.events:
        if ev.event_type == "damage":
            if ev.actor:
                _get(ev.actor).damage_dealt += ev.amount
            if ev.target:
                _get(ev.target).damage_taken += ev.amount

        elif ev.event_type == "heal":
            if ev.actor and ev.target:
                if ev.actor == ev.target:
                    _get(ev.actor).self_heal += ev.amount
                else:
                    _get(ev.actor).healing_dealt += ev.amount
                    _get(ev.target).healing_taken += ev.amount

        elif ev.event_type == "kill":
            # The last damage event before the kill attributes the kill
            if ev.target:
                _get(ev.target)  # ensure entry exists

    return stats


# ---------------------------------------------------------------------------
# High-level file building
# ---------------------------------------------------------------------------

def _make_fight_id(file_path: Path, start: datetime) -> str:
    return f"{file_path.parent.name}::{start.isoformat()}"


def build_fights(
    log_file: Path,
    progress_cb: Callable[[int, int], None] | None = None,
) -> list[Fight]:
    """
    Full pipeline for one combat.log file:
    read → parse → split → package into Fight objects.
    """
    folder_hint = _folder_date(log_file.parent)
    lines = list(_stream_lines(log_file))
    total = len(lines)

    if progress_cb:
        progress_cb(0, total)

    events = parse_events(iter(lines), folder_hint)

    if progress_cb:
        progress_cb(total, total)

    segments = split_into_fights(events)
    fights: list[Fight] = []

    for seg in segments:
        combat = [e for e in seg if e.event_type in ("damage", "heal", "kill")]
        if len(combat) < 2:
            continue

        start = seg[0].timestamp
        end   = combat[-1].timestamp

        # Game mode from the first session_start in the segment
        game_mode = next(
            (e.source for e in seg if e.event_type == "session_start"), ""
        )
        actual_time = next(
            (e.amount for e in seg if e.event_type == "game_end"), 0.0
        )

        fight = Fight(
            id                   = _make_fight_id(log_file, start),
            file_path            = str(log_file),
            start                = start,
            end                  = end,
            game_mode            = game_mode,
            actual_game_time_sec = actual_time,
            events               = seg,
        )
        fights.append(fight)

    return fights


# ---------------------------------------------------------------------------
# Multiprocessing entry point
# ---------------------------------------------------------------------------

def parse_file_quick(args: tuple[str, str]) -> list[Fight]:
    """
    Multiprocessing-safe entry point.  Accepts a tuple so it can be used
    with pool.map().

    args = (log_file_str, progress_file_str)
    progress_file_str may be "" to skip writing progress.
    """
    log_file_str, progress_file_str = args
    log_path = Path(log_file_str)

    total_lines = sum(1 for _ in _stream_lines(log_path))

    def _progress(done: int, total: int) -> None:
        if progress_file_str:
            try:
                Path(progress_file_str).write_text(f"{done}/{total}", encoding="utf-8")
            except OSError:
                pass

    return build_fights(log_path, progress_cb=_progress)


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

def find_combat_logs(root: str | Path) -> list[Path]:
    """
    Find all combat.log files under *root*.
    Star Conflict stores them in dated sub-folders:
        <root>/<YYYY.MM.DD HH.MM.SS.mmm>/combat.log
    Returns them sorted oldest-first.
    """
    root = Path(root)
    if not root.exists():
        return []

    found = sorted(root.rglob("combat.log"), key=lambda p: p.parent.name)
    return found
