import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Tuple
SOURCE_NOISE_RE = re.compile(r"^\(h:[^\)]*\)\s*")


def _clean_source(text: str) -> str:
    cleaned = SOURCE_NOISE_RE.sub("", text or "").strip()
    return cleaned


def _strip_id(text: str) -> str:
    if not text:
        return ""
    # Remove ID part
    text = text.split("|")[0]
    # Remove ship suffix (separated by tab or multiple spaces)
    parts = re.split(r"\t|\s{2,}", text)
    return parts[0].strip()


TIME_RE = re.compile(r"(?P<time>\d{2}:\d{2}:\d{2}(?:\.\d{1,3})?)")

# Matches lines like:
# 11:53:22.589  CMBT   | Damage            NPC22|0000001779 ->         AscalonV|0000001307  71.55 (h:0.00 s:71.55) Weapon...
# 11:53:22.645  CMBT   | Heal           AscalonV|0000001307 ->         AscalonV|0000001307  64.84 Module_Extreme...
DAMAGE_HEAL_RE = re.compile(
    r"(?P<time>\d{2}:\d{2}:\d{2}(?:\.\d{1,3})?).*?\b(?P<kind>Damage|Heal)\s+"
    r"(?P<actor>[^|]+)\|(?P<actor_id>\S+)\s*->\s*(?P<target>[^|]+)\|(?P<target_id>\S+)\s+"
    r"(?P<amount>\d+(?:\.\d+)?)(?:\s+(?P<source>.*))?",
    re.IGNORECASE,
)

KILL_RE = re.compile(
    r"(?P<time>\d{2}:\d{2}:\d{2}(?:\.\d{1,3})?).*?Killed\s+(?P<target>[^;]+);\s+killer\s+(?P<actor>[^\s]+)(?:\s+(?P<source>.*))?",
    re.IGNORECASE,
)

# Reward lines contain outcome (victory/defeat)
REWARD_RE = re.compile(
    r"(?P<time>\d{2}:\d{2}:\d{2}(?:\.\d{1,3})?).*?\bReward\s+(?P<actor>[^\t]+?)\s+\d+.*?for\s+(?P<result>victory|defeat)",
    re.IGNORECASE,
)

AURA_APPLY_RE = re.compile(
    r"(?P<time>\d{2}:\d{2}:\d{2}(?:\.\d{1,3})?).*?Apply aura '(?P<aura>[^']+)' id (?P<id>\d+) type (?P<type>[^\s]+) to '(?P<target>[^']+)'",
    re.IGNORECASE,
)

AURA_CANCEL_RE = re.compile(
    r"(?P<time>\d{2}:\d{2}:\d{2}(?:\.\d{1,3})?).*?Cancel aura '(?P<aura>[^']+)' id (?P<id>\d+) type (?P<type>[^\s]+) from '(?P<target>[^']+)'",
    re.IGNORECASE,
)

PARTICIPANT_RE = re.compile(
    r"(?P<time>\d{2}:\d{2}:\d{2}(?:\.\d{1,3})?).*?Participant\s+(?P<actor>[^\t]+)\t\s+(?P<ship>[^\t]+)",
    re.IGNORECASE,
)

SPAWN_RE = re.compile(
    r"(?P<time>\d{2}:\d{2}:\d{2}(?:\.\d{1,3})?).*?Spawn SpaceShip for (?P<actor>.+?)\s*\(.*?\)\.\s*'(?P<ship>[^']+)'",
    re.IGNORECASE,
)

# Legacy patterns kept for older logs.
EVENT_PATTERNS = [
    re.compile(
        r"(?P<actor>[\w\-\[\]\(\)\.]+)\s+(?:deals|hits|inflicts)\s+(?P<amount>\d+)\s+damage\s+(?:to|on)\s+(?P<target>[\w\-\[\]\(\)\.]+)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?P<actor>[\w\-\[\]\(\)\.]+)\s+(?:heals|repairs|restores)\s+(?P<amount>\d+)\s+(?:hp|health|hull|armor)?\s*(?:for|to)?\s+(?P<target>[\w\-\[\]\(\)\.]+)",
        re.IGNORECASE,
    ),
]


@dataclass
class CombatEvent:
    timestamp: Optional[datetime]
    actor: str
    target: str
    event_type: str  # "damage" or "healing"
    amount: float
    raw: str
    source: str = ""
    actor_id: Optional[str] = None
    target_id: Optional[str] = None


@dataclass
class Fight:
    id: str
    file_path: Path
    start: Optional[datetime]
    end: Optional[datetime]
    events: List[CombatEvent] = field(default_factory=list)
    game_mode: str = "Unknown"
    actual_game_time_sec: Optional[float] = None


@dataclass
class ParticipantStats:
    name: str
    damage_dealt: float = 0.0
    damage_taken: float = 0.0
    healing_dealt: float = 0.0
    healing_taken: float = 0.0
    self_heal: float = 0.0
    healing_others: float = 0.0


def find_combat_logs(root: Path) -> List[Path]:
    """Locate all combat.log files inside dated folders."""
    if not root.exists():
        return []
    results: List[Path] = []
    for child in root.iterdir():
        if child.is_dir():
            log_file = child / "combat.log"
            if log_file.exists():
                results.append(log_file)
    results.sort()
    return results


def _parse_timestamp(line: str, folder_hint: Optional[str]) -> Optional[datetime]:
    match = TIME_RE.search(line)
    if not match:
        return None
    time_part = match.group("time")
    # If we have a folder hint like 2025.12.31 11.39.58.697 use its date portion.
    date_part = None
    if folder_hint:
        try:
            date_part = datetime.strptime(folder_hint[:10], "%Y.%m.%d").date()
        except Exception:
            date_part = None
    try:
        base = datetime.strptime(time_part.split(".")[0], "%H:%M:%S").time()
        if date_part:
            return datetime.combine(date_part, base)
        return datetime.strptime(time_part, "%H:%M:%S.%f")
    except Exception:
        return None


def _infer_event_type(pattern_index: int) -> str:
    return "damage" if pattern_index == 0 else "healing"


def parse_events(lines: Iterable[str], folder_hint: Optional[str]) -> List[CombatEvent]:
    events: List[CombatEvent] = []
    for line in lines:
        if "HangarShip" in line:
            continue
        # Damage / Heal
        m_new = DAMAGE_HEAL_RE.search(line)
        if m_new:
            kind = m_new.group("kind").lower()
            raw_actor = m_new.group("actor").strip()
            raw_target = m_new.group("target").strip()
            actor = _strip_id(raw_actor)
            target = _strip_id(raw_target)
            actor_id = (m_new.group("actor_id") or "").strip() or None
            target_id = (m_new.group("target_id") or "").strip() or None
            try:
                amount = float(m_new.group("amount"))
            except Exception:
                amount = 0.0
            timestamp = _parse_timestamp(m_new.group("time"), folder_hint)
            source = _clean_source(m_new.group("source") or "")
            events.append(
                CombatEvent(
                    timestamp=timestamp,
                    actor=actor,
                    target=target,
                    event_type="damage" if kind == "damage" else "healing",
                    amount=amount,
                    raw=line.strip(),
                    source=source,
                    actor_id=actor_id,
                    target_id=target_id,
                )
            )
            continue

        # Kill
        m_kill = KILL_RE.search(line)
        if m_kill:
            timestamp = _parse_timestamp(m_kill.group("time"), folder_hint)
            target = _strip_id(m_kill.group("target").strip())
            actor = _strip_id(m_kill.group("actor").strip())
            source = _clean_source(m_kill.group("source") or "")
            events.append(
                CombatEvent(
                    timestamp=timestamp,
                    actor=actor,
                    target=target,
                    event_type="kill",
                    amount=0.0,
                    raw=line.strip(),
                    source=source,
                )
            )
            continue

        # Reward outcome (victory/defeat)
        m_reward = REWARD_RE.search(line)
        if m_reward:
            timestamp = _parse_timestamp(m_reward.group("time"), folder_hint)
            actor = _strip_id(m_reward.group("actor").strip())
            result = (m_reward.group("result") or "").strip().lower()
            events.append(
                CombatEvent(
                    timestamp=timestamp,
                    actor=actor,
                    target="",
                    event_type="reward",
                    amount=0.0,
                    raw=line.strip(),
                    source=result,
                )
            )
            continue

        m_game_end = GAME_END_RE.search(line)
        if m_game_end:
            # Some lines omit a time-of-day prefix; store None when absent.
            timestamp = _parse_timestamp(m_game_end.groupdict().get("time") or "", folder_hint)
            try:
                secs = float(m_game_end.group("secs"))
            except Exception:
                secs = 0.0
            events.append(
                CombatEvent(
                    timestamp=timestamp,
                    actor="",
                    target="",
                    event_type="game_end",
                    amount=secs,
                    raw=line.strip(),
                    source="",
                )
            )
            continue

        # Aura Apply
        m_aura = AURA_APPLY_RE.search(line)
        if m_aura:
            timestamp = _parse_timestamp(m_aura.group("time"), folder_hint)
            target = _strip_id(m_aura.group("target").strip())
            aura_name = m_aura.group("aura")
            # We store aura name in source for consistency
            events.append(
                CombatEvent(
                    timestamp=timestamp,
                    actor="", # Unknown actor for aura apply in this line
                    target=target,
                    event_type="buff_apply",
                    amount=0.0,
                    raw=line.strip(),
                    source=aura_name,
                )
            )
            continue

        # Aura Cancel
        m_aura_cancel = AURA_CANCEL_RE.search(line)
        if m_aura_cancel:
            timestamp = _parse_timestamp(m_aura_cancel.group("time"), folder_hint)
            target = _strip_id(m_aura_cancel.group("target").strip())
            aura_name = m_aura_cancel.group("aura")
            events.append(
                CombatEvent(
                    timestamp=timestamp,
                    actor="",
                    target=target,
                    event_type="buff_cancel",
                    amount=0.0,
                    raw=line.strip(),
                    source=aura_name,
                )
            )
            continue

        # Participant Info
        m_part = PARTICIPANT_RE.search(line)
        if m_part:
            timestamp = _parse_timestamp(m_part.group("time"), folder_hint)
            actor = _strip_id(m_part.group("actor").strip())
            ship = m_part.group("ship").strip()
            events.append(
                CombatEvent(
                    timestamp=timestamp,
                    actor=actor,
                    target="",
                    event_type="ship_info",
                    amount=0.0,
                    raw=line.strip(),
                    source=ship,
                )
            )
            continue

        # Spawn
        m_spawn = SPAWN_RE.search(line)
        if m_spawn:
            timestamp = _parse_timestamp(m_spawn.group("time"), folder_hint)
            actor = m_spawn.group("actor").strip()
            ship = m_spawn.group("ship").strip()
            events.append(
                CombatEvent(
                    timestamp=timestamp,
                    actor=actor,
                    target="",
                    event_type="ship_spawn",
                    amount=0.0,
                    raw=line.strip(),
                    source=ship,
                )
            )
            continue

        for idx, pattern in enumerate(EVENT_PATTERNS):
            m = pattern.search(line)
            if not m:
                continue
            actor = m.group("actor")
            target = m.group("target")
            try:
                amount = float(m.group("amount"))
            except Exception:
                continue
            timestamp = _parse_timestamp(line, folder_hint)
            events.append(
                CombatEvent(
                    timestamp=timestamp,
                    actor=actor,
                    target=target,
                    event_type=_infer_event_type(idx),
                    amount=amount,
                    raw=line.strip(),
                    source="",
                )
            )
            break
    return events


def split_into_fights(events: List[CombatEvent], max_gap_seconds: int = 120) -> List[List[CombatEvent]]:
    """Heuristic split: start a new fight if time gap exceeds threshold or session boundaries are hit."""
    return split_into_fights_with_boundaries(events, session_starts=[], max_gap_seconds=max_gap_seconds)


# Regex to detect session starts like:
# 11:53:10.159  CMBT   | ======= Start gameplay 'FreeSpace' map 'factory_pirate...' =======
SESSION_START_RE = re.compile(r"Start gameplay\s+'(?P<mode>[^']+)'\s+map\s+'(?P<map>[^']+)'", re.IGNORECASE)
SESSION_CONNECT_RE = re.compile(r"Connect to game session", re.IGNORECASE)
GAME_END_RE = re.compile(
    r"(?:(?P<time>\d{2}:\d{2}:\d{2}(?:\.\d{1,3})?)\s+)?Actual\s+game\s+time\s+(?P<secs>\d+(?:\.\d+)?)\s*sec",
    re.IGNORECASE,
)


def find_session_starts(lines: List[str], folder_hint: Optional[str]) -> List[Tuple[datetime, str]]:
    """Collect timestamps and modes for gameplay session starts."""
    starts: List[Tuple[datetime, str]] = []
    for line in lines:
        m = SESSION_START_RE.search(line)
        if m:
            ts = _parse_timestamp(line, folder_hint)
            if ts:
                starts.append((ts, m.group("mode")))
            continue
            
        if SESSION_CONNECT_RE.search(line):
            ts = _parse_timestamp(line, folder_hint)
            if ts:
                starts.append((ts, "Unknown"))
    return starts


def split_into_fights_with_boundaries(
    events: List[CombatEvent],
    session_starts: List[datetime],
    max_gap_seconds: int = 120,
) -> List[List[CombatEvent]]:
    if not events:
        return []
    fights: List[List[CombatEvent]] = []
    current: List[CombatEvent] = []
    last_time: Optional[datetime] = None
    gap = timedelta(seconds=max_gap_seconds)

    session_starts = sorted(session_starts)
    boundary_idx = 0

    for ev in events:
        ev_time = ev.timestamp
        # Hard split on session boundaries.
        while boundary_idx < len(session_starts) and ev_time and ev_time >= session_starts[boundary_idx]:
            if current:
                fights.append(current)
                current = []
            boundary_idx += 1
        # Gap-based split.
        if last_time and ev_time and (ev_time - last_time) > gap:
            fights.append(current)
            current = []
        current.append(ev)
        if ev_time:
            last_time = ev_time
    if current:
        fights.append(current)
    return fights


def build_fights(log_file: Path) -> List[Fight]:
    folder_hint = log_file.parent.name
    lines = log_file.read_text(encoding="utf-8", errors="ignore").splitlines()
    events = parse_events(lines, folder_hint)
    session_info = find_session_starts(lines, folder_hint)
    
    # Extract just timestamps for splitting
    session_timestamps = [s[0] for s in session_info]
    
    fights = split_into_fights_with_boundaries(events, session_starts=session_timestamps)
    results: List[Fight] = []
    for idx, fight_events in enumerate(fights):
        start = fight_events[0].timestamp if fight_events else None
        end = fight_events[-1].timestamp if fight_events else None
        actual_time = None
        for ev in reversed(fight_events):
            if ev.event_type == "game_end":
                actual_time = ev.amount
                break
        
        # Determine mode
        mode = "Unknown"
        if start:
            for s_time, s_mode in session_info:
                if s_time <= start:
                    mode = s_mode
                else:
                    break
        
        # Filter out noise fights (e.g. Hangar activity or minor events without damage/healing)
        if mode == "Unknown":
            has_substance = any(e.event_type in ("damage", "healing", "kill", "reward", "game_end") for e in fight_events)
            if not has_substance:
                continue

        results.append(
            Fight(
                id=f"{log_file.name}-fight-{idx+1}",
                file_path=log_file,
                start=start,
                end=end,
                events=fight_events,
                game_mode=mode,
                actual_game_time_sec=actual_time,
            )
        )
    return results


def aggregate_stats(fight: Fight) -> Dict[str, ParticipantStats]:
    stats: Dict[str, ParticipantStats] = {}

    def ensure(name: str) -> Optional[ParticipantStats]:
        if not name:
            return None
        if name not in stats:
            stats[name] = ParticipantStats(name=name)
        return stats[name]

    for ev in fight.events:
        if ev.event_type == "damage":
            actor_stat = ensure(ev.actor)
            target_stat = ensure(ev.target)
            if actor_stat: actor_stat.damage_dealt += ev.amount
            if target_stat: target_stat.damage_taken += ev.amount
        elif ev.event_type == "healing":
            actor_stat = ensure(ev.actor)
            target_stat = ensure(ev.target)
            if actor_stat: actor_stat.healing_dealt += ev.amount
            if target_stat: target_stat.healing_taken += ev.amount
            if actor_stat:
                if ev.actor == ev.target:
                    actor_stat.self_heal += ev.amount
                else:
                    actor_stat.healing_others += ev.amount
        elif ev.event_type == "kill":
            # Ensure participants exist for kills
            ensure(ev.actor)
            ensure(ev.target)
        # Ignore ship_info, buff_apply, buff_cancel for stats aggregation
        
    return stats


# Streaming helpers for per-file progress
def stream_lines(path: Path, chunk_size: int = 1024 * 1024) -> Iterable[str]:
    buffer = ""
    with path.open("r", encoding="utf-8", errors="ignore", buffering=chunk_size) as f:
        for data in iter(lambda: f.read(chunk_size), ""):
            buffer += data
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                yield line
    if buffer:
        yield buffer


def count_lines_fast(path: Path) -> int:
    try:
        with path.open("rb") as f:
            return sum(buf.count(b"\n") for buf in iter(lambda: f.read(1024 * 1024), b"")) or 1
    except Exception:
        return 1


def build_fights_stream(
    log_file: Path,
    total_lines: int,
    progress_cb: Optional[Callable[[int, int], None]] = None,
    progress_every: int = 5000,
) -> List[Fight]:
    folder_hint = log_file.parent.name
    events: List[CombatEvent] = []
    session_info: List[Tuple[datetime, str]] = []
    lines_read = 0

    for line in stream_lines(log_file):
        lines_read += 1
        # progress_every may be 0 when no progress callback is used (parse_file_quick)
        if progress_cb and progress_every and (lines_read % progress_every == 0):
            progress_cb(lines_read, total_lines)

        m_start = SESSION_START_RE.search(line)
        if m_start:
            ts = _parse_timestamp(line, folder_hint)
            if ts:
                session_info.append((ts, m_start.group("mode")))
        elif SESSION_CONNECT_RE.search(line):
            ts = _parse_timestamp(line, folder_hint)
            if ts:
                session_info.append((ts, "Unknown"))

        m_new = DAMAGE_HEAL_RE.search(line)
        if m_new:
            kind = m_new.group("kind").lower()
            raw_actor = m_new.group("actor").strip()
            raw_target = m_new.group("target").strip()
            actor = _strip_id(raw_actor)
            target = _strip_id(raw_target)
            actor_id = (m_new.group("actor_id") or "").strip() or None
            target_id = (m_new.group("target_id") or "").strip() or None
            try:
                amount = float(m_new.group("amount"))
            except Exception:
                amount = 0.0
            timestamp = _parse_timestamp(m_new.group("time"), folder_hint)
            source = _clean_source(m_new.group("source") or "")
            events.append(
                CombatEvent(
                    timestamp=timestamp,
                    actor=actor,
                    target=target,
                    event_type="damage" if kind == "damage" else "healing",
                    amount=amount,
                    raw="",
                    source=source,
                    actor_id=actor_id,
                    target_id=target_id,
                )
            )
            continue

        # Kill
        m_kill = KILL_RE.search(line)
        if m_kill:
            timestamp = _parse_timestamp(m_kill.group("time"), folder_hint)
            target = _strip_id(m_kill.group("target").strip())
            actor = _strip_id(m_kill.group("actor").strip())
            source = _clean_source(m_kill.group("source") or "")
            events.append(
                CombatEvent(
                    timestamp=timestamp,
                    actor=actor,
                    target=target,
                    event_type="kill",
                    amount=0.0,
                    raw="",
                    source=source,
                )
            )
            continue

        m_reward = REWARD_RE.search(line)
        if m_reward:
            timestamp = _parse_timestamp(m_reward.group("time"), folder_hint)
            actor = _strip_id(m_reward.group("actor").strip())
            result = (m_reward.group("result") or "").strip().lower()
            events.append(
                CombatEvent(
                    timestamp=timestamp,
                    actor=actor,
                    target="",
                    event_type="reward",
                    amount=0.0,
                    raw="",
                    source=result,
                )
            )
            continue

        m_game_end = GAME_END_RE.search(line)
        if m_game_end:
            timestamp = _parse_timestamp(m_game_end.groupdict().get("time") or "", folder_hint)
            try:
                secs = float(m_game_end.group("secs"))
            except Exception:
                secs = 0.0
            events.append(
                CombatEvent(
                    timestamp=timestamp,
                    actor="",
                    target="",
                    event_type="game_end",
                    amount=secs,
                    raw="",
                    source="",
                )
            )
            continue

        # Aura Apply
        m_aura = AURA_APPLY_RE.search(line)
        if m_aura:
            timestamp = _parse_timestamp(m_aura.group("time"), folder_hint)
            target = _strip_id(m_aura.group("target").strip())
            aura_name = m_aura.group("aura")
            events.append(
                CombatEvent(
                    timestamp=timestamp,
                    actor="",
                    target=target,
                    event_type="buff_apply",
                    amount=0.0,
                    raw="",
                    source=aura_name,
                )
            )
            continue

        # Aura Cancel
        m_aura_cancel = AURA_CANCEL_RE.search(line)
        if m_aura_cancel:
            timestamp = _parse_timestamp(m_aura_cancel.group("time"), folder_hint)
            target = _strip_id(m_aura_cancel.group("target").strip())
            aura_name = m_aura_cancel.group("aura")
            events.append(
                CombatEvent(
                    timestamp=timestamp,
                    actor="",
                    target=target,
                    event_type="buff_cancel",
                    amount=0.0,
                    raw="",
                    source=aura_name,
                )
            )
            continue

        # Participant Info
        m_part = PARTICIPANT_RE.search(line)
        if m_part:
            timestamp = _parse_timestamp(m_part.group("time"), folder_hint)
            actor = _strip_id(m_part.group("actor").strip())
            ship = m_part.group("ship").strip()
            events.append(
                CombatEvent(
                    timestamp=timestamp,
                    actor=actor,
                    target="",
                    event_type="ship_info",
                    amount=0.0,
                    raw="",
                    source=ship,
                )
            )
            continue

        for idx, pattern in enumerate(EVENT_PATTERNS):
            m = pattern.search(line)
            if not m:
                continue
            actor = m.group("actor")
            target = m.group("target")
            try:
                amount = float(m.group("amount"))
            except Exception:
                amount = 0.0
            timestamp = _parse_timestamp(line, folder_hint)
            events.append(
                CombatEvent(
                    timestamp=timestamp,
                    actor=actor,
                    target=target,
                    event_type=_infer_event_type(idx),
                    amount=amount,
                    raw="",
                    source="",
                )
            )
            break

    if progress_cb and progress_every:
        progress_cb(lines_read, total_lines)

    session_timestamps = [s[0] for s in session_info]
    fights = split_into_fights_with_boundaries(events, session_starts=session_timestamps)
    results: List[Fight] = []
    for idx, fight_events in enumerate(fights):
        start = fight_events[0].timestamp if fight_events else None
        end = fight_events[-1].timestamp if fight_events else None
        actual_time = None
        for ev in reversed(fight_events):
            if ev.event_type == "game_end":
                actual_time = ev.amount
                break
        
        # Determine mode
        mode = "Unknown"
        if start:
            for s_time, s_mode in session_info:
                if s_time <= start:
                    mode = s_mode
                else:
                    break
        
        # Filter out noise fights (e.g. Hangar activity or minor events without damage/healing)
        if mode == "Unknown":
            has_substance = any(e.event_type in ("damage", "healing", "kill", "reward", "game_end") for e in fight_events)
            if not has_substance:
                continue

        results.append(
            Fight(
                id=f"{log_file.name}-fight-{idx+1}",
                file_path=log_file,
                start=start,
                end=end,
                events=fight_events,
                game_mode=mode,
                actual_game_time_sec=actual_time,
            )
        )
    return results


def parse_file_quick(log_file: Path) -> List[Fight]:
    """Parse a single log file with streaming and no callbacks (suitable for multiprocessing)."""
    total_lines = count_lines_fast(log_file)
    return build_fights_stream(log_file, total_lines=total_lines, progress_cb=None, progress_every=0)


def load_all_fights(root: Path, progress_cb=None) -> List[Fight]:
    fights: List[Fight] = []
    logs = find_combat_logs(root)
    total = len(logs)
    for idx, log_file in enumerate(logs, 1):
        fights.extend(build_fights(log_file))
        if progress_cb:
            progress_cb(idx, total)
    fights.sort(key=lambda f: (f.start or datetime.min, f.file_path))
    return fights
