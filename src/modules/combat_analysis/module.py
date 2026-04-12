"""
CombatAnalyzerModule — OPENABLE module.

Orchestrates log discovery, background parsing, caching, team inference,
winner detection, player API checking, display-name resolution, and
settings persistence. Wires data to CombatAnalyzerView.
"""
from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Callable, Optional

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFileDialog, QFormLayout
from PySide6.QtWidgets import QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

from src.core.config import AppConfig
from src.core.module_base import ModuleBase, ModuleType
from src.modules.combat_analysis.cache import CacheManager
from src.modules.combat_analysis.display_names import DisplayNameManager
from src.modules.combat_analysis.parser import (
    Fight, ParticipantStats,
    aggregate_stats, build_fights, find_combat_logs,
)
from src.modules.combat_analysis.settings import CombatAnalysisSettings
from src.modules.combat_analysis.ui.main_view import CombatAnalyzerView

GAME_MODE_MAP: dict[str, str] = {
    "FreeSpace":            "Open Space",
    "ClanShip":             "Conquest",
    "BombTheBase":          "Detonation",
    "TeamDeathMatch":       "Team Battle",
    "CaptureTheBase":       "Beacon Capture",
    "CaptureTheBase2":      "Four Lives",
    "Control":              "Domination",
    "KingOfTheHill":        "Beacon Hunt",
    "Sentinel":             "Combat Recon",
    "GreedyTeamDeathMatch": "Survival",
}

PIE_PALETTE: list[str] = [
    "#3de7ff", "#ff3d3d", "#ffff3d", "#ff3dff",
    "#ff9b3d", "#3d3dff", "#9b3dff", "#ff3d9b",
    "#d6ff3d", "#3dd6ff", "#ff5c5c", "#ffff5c",
    "#5c5cff", "#ff853d", "#ce3dff", "#ff3d66",
]


# ---------------------------------------------------------------------------
# Background workers
# ---------------------------------------------------------------------------

class _WorkerSignals(QObject):
    finished = Signal(list)              # list[Fight]
    progress = Signal(int, int, str)     # done, total, label
    error    = Signal(str)


class _ParseWorker(QRunnable):
    def __init__(self, log_files: list[Path], cache: CacheManager) -> None:
        super().__init__()
        self.setAutoDelete(True)
        self._files  = log_files
        self._cache  = cache
        self.signals = _WorkerSignals()

    @Slot()
    def run(self) -> None:
        all_fights: list[Fight] = []
        total = len(self._files)
        for i, lf in enumerate(self._files):
            cached = self._cache.get(lf)
            if cached is not None:
                all_fights.extend(cached)
            else:
                try:
                    fights = build_fights(lf)
                    self._cache.put(lf, fights)
                    all_fights.extend(fights)
                except Exception as exc:
                    self.signals.error.emit(f"{lf.name}: {exc}")
            self.signals.progress.emit(i + 1, total, lf.parent.name)
        all_fights.sort(key=lambda f: f.start, reverse=True)
        self.signals.finished.emit(all_fights)


class _CheckSignals(QObject):
    finished = Signal(dict)          # {name: bool}
    progress = Signal(str, int, int) # name, done, total


class _PlayerCheckWorker(QRunnable):
    def __init__(self, names: list[str], known: dict[str, bool]) -> None:
        super().__init__()
        self.setAutoDelete(True)
        self._names  = names
        self._known  = known
        self.signals = _CheckSignals()
        self._cancel = False

    def cancel(self) -> None:
        self._cancel = True

    @Slot()
    def run(self) -> None:
        results: dict[str, bool] = {}
        total = len(self._names)
        for i, name in enumerate(self._names):
            if self._cancel:
                break
            if name in self._known:
                results[name] = self._known[name]
            else:
                r = _api_check(name)
                if r is not None:
                    results[name] = r
            self.signals.progress.emit(name, i + 1, total)
        self.signals.finished.emit(results)


def _api_check(name: str) -> Optional[bool]:
    try:
        enc = urllib.parse.quote(name)
        url = f"https://gmt.star-conflict.com/pubapi/v1/userinfo.php?nickname={enc}"
        with urllib.request.urlopen(url, timeout=1.5) as resp:
            data = json.loads(resp.read().decode())
        if data.get("result") == "ok":
            return True
        if data.get("result") == "error":
            return False
        return None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Module
# ---------------------------------------------------------------------------

class CombatAnalyzerModule(ModuleBase):

    @property
    def module_id(self)    -> str:        return "combat_analysis"
    @property
    def display_name(self) -> str:        return "Combat Analyzer"
    @property
    def description(self)  -> str:        return "Parse and visualise Star Conflict combat logs"
    @property
    def module_type(self)  -> ModuleType: return ModuleType.OPENABLE
    @property
    def prefers_maximized(self) -> bool:  return True

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._config:   AppConfig | None         = None
        self._settings: CombatAnalysisSettings   = CombatAnalysisSettings()
        self._view:     CombatAnalyzerView | None = None
        self._cache     = CacheManager()
        self._names     = DisplayNameManager()
        self._pool      = QThreadPool.globalInstance()

        self._all_fights:  list[Fight]                      = []
        self._fights:      list[Fight]                      = []
        self._stats_cache: dict[str, dict[str, ParticipantStats]] = {}
        self._player_cache: dict[str, bool]                 = {}
        self._color_cache:  dict[str, str]                  = {}

        self._single_log: Path | None = None

        # Current fight state
        self._current_fight:  Fight | None = None
        self._current_team_a: list[str]    = []
        self._current_team_b: list[str]    = []
        self._current_winner: str | None   = None
        self._current_player_set: set[str] = set()

        self._check_worker: _PlayerCheckWorker | None = None
        self._check_id = 0

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def initialize(self, config: AppConfig) -> None:
        self._config   = config
        self._settings = CombatAnalysisSettings.load()
        # Restore API-verified player identities from last session
        self._player_cache = {
            name: False if self._is_forced_non_player(name) else bool(is_player)
            for name, is_player in self._settings.player_cache.items()
        }

    def shutdown(self) -> None:
        # Persist player identity cache so we don't re-check on next launch
        self._settings.player_cache = dict(self._player_cache)
        self._settings.save()
        self._pool.waitForDone(3000)
        self._cache.flush()

    def on_config_changed(self, config: AppConfig) -> None:
        self._config = config

    # ------------------------------------------------------------------
    # OPENABLE interface
    # ------------------------------------------------------------------

    def build_view(self, parent: QWidget) -> QWidget:
        self._view = CombatAnalyzerView(
            settings      = self._settings,
            game_mode_map = GAME_MODE_MAP,
            parent        = parent,
        )
        v = self._view

        v.reload_requested.connect(self._reload)
        v.open_file_requested.connect(self._on_open_file)
        v.show_all_logs_requested.connect(self._on_show_all_logs)
        v.analyze_all_requested.connect(self._on_analyze_all)
        v.clear_cache_requested.connect(self._on_clear_cache)
        v.settings_requested.connect(lambda: self._open_settings(v))
        v.fight_selected.connect(self._on_fight_selected)
        v.game_mode_toggled.connect(self._on_game_mode_toggled)
        v.sort_changed.connect(self._on_sort_changed)

        if self._config:
            v.set_disabled_modes(set(self._config.disabled_game_modes))

        self._reload()
        return v

    # ------------------------------------------------------------------
    # Parse pipeline
    # ------------------------------------------------------------------

    def _reload(self, logs_override: list[Path] | None = None) -> None:
        if not self._config or not self._view:
            return

        if self._single_log and logs_override is None:
            logs_override = [self._single_log]

        if logs_override is not None:
            log_files = [p for p in logs_override if p.exists()]
        else:
            log_files = find_combat_logs(Path(self._config.logs_path))

        if not log_files:
            self.status_changed.emit("No logs found")
            self._view.hide_loading()
            return

        self._view.show_loading(f"Scanning {len(log_files)} log files…")
        self.status_changed.emit("Loading…")

        worker = _ParseWorker(log_files, self._cache)
        worker.signals.finished.connect(self._on_parse_done)
        worker.signals.progress.connect(self._on_parse_progress)
        worker.signals.error.connect(lambda m: self.status_changed.emit(f"Warning: {m}"))
        self._pool.start(worker)

    @Slot(list)
    def _on_parse_done(self, fights: list[Fight]) -> None:
        if not self._view:
            return

        # Deduplicate: within 90 s keep the richer fight
        valid = [f for f in fights if f.events and len(f.events) > 5]
        valid.sort(key=lambda f: f.start)
        unique: list[Fight] = []
        for f in valid:
            if (unique and f.start and unique[-1].start and
                    abs((f.start - unique[-1].start).total_seconds()) < 90):
                if len(f.events) > len(unique[-1].events):
                    unique[-1] = f
            else:
                unique.append(f)
        unique.sort(key=lambda f: f.start, reverse=True)

        self._all_fights = unique
        self._stats_cache.clear()
        self._update_game_mode_menu()
        self._refresh_fight_list()
        self._view.hide_loading()
        self._cache.flush()
        self.status_changed.emit(f"{len(self._fights)} fights loaded")

    @Slot(int, int, str)
    def _on_parse_progress(self, done: int, total: int, label: str) -> None:
        if self._view:
            self._view.update_progress(done, total, f"Parsing: {label}")

    # ------------------------------------------------------------------
    # Game-mode filter
    # ------------------------------------------------------------------

    def _update_game_mode_menu(self) -> None:
        if not self._view:
            return
        modes: dict[str, str] = {}
        for f in self._all_fights:
            m = (f.game_mode or "Unknown").strip() or "Unknown"
            modes[m] = GAME_MODE_MAP.get(m, m)
        self._view.set_game_modes(modes)

    @Slot(str, bool)
    def _on_game_mode_toggled(self, mode: str, enabled: bool) -> None:
        if not self._config:
            return
        disabled = set(self._config.disabled_game_modes)
        if enabled:
            disabled.discard(mode)
        else:
            disabled.add(mode)
        self._config.disabled_game_modes = sorted(disabled)
        self._config.save()
        preferred = self._current_fight.id if self._current_fight else None
        self._refresh_fight_list(preferred_id=preferred)

    def _refresh_fight_list(self, preferred_id: str | None = None) -> None:
        if not self._config or not self._view:
            return
        disabled = set(self._config.disabled_game_modes)
        self._fights = [
            f for f in self._all_fights
            if (f.game_mode or "Unknown") not in disabled
        ]
        labels = [self._format_fight_label(f) for f in self._fights]
        self._view.set_fights(labels)

        if not self._fights:
            self._current_fight = None
            return

        idx = 0
        if preferred_id:
            for i, f in enumerate(self._fights):
                if f.id == preferred_id:
                    idx = i
                    break
        self._view.select_fight(idx)

    # ------------------------------------------------------------------
    # Fight selection
    # ------------------------------------------------------------------

    @Slot(int)
    def _on_fight_selected(self, index: int) -> None:
        if not self._view or index < 0 or index >= len(self._fights):
            return

        fight = self._fights[index]
        self._current_fight = fight

        if fight.id not in self._stats_cache:
            self._stats_cache[fight.id] = aggregate_stats(fight)
        stats = self._stats_cache[fight.id]
        self._mark_forced_non_players(stats)

        username = (self._config.username if self._config else "").strip()
        unchecked = [
            n for n in stats
            if n and n.upper() != "N/A" and not self._is_forced_non_player(n) and n not in self._player_cache
        ]
        if unchecked:
            self._start_player_check(unchecked, fight, stats, username)
        else:
            self._render_fight(fight, stats, username)

    def _render_fight(
        self,
        fight: Fight,
        stats: dict[str, ParticipantStats],
        username: str,
    ) -> None:
        if not self._view:
            return

        self._mark_forced_non_players(stats)
        player_set = {n for n, is_p in self._player_cache.items() if is_p and not self._is_forced_non_player(n)}
        team_a, team_b = self._infer_teams(fight, stats, username, player_set)
        winner = self._determine_winner(fight, team_a, team_b, stats)

        self._current_team_a     = team_a
        self._current_team_b     = team_b
        self._current_winner     = winner
        self._current_player_set = player_set

        self._view.show_fight(
            fight      = fight,
            stats      = stats,
            team_a     = team_a,
            team_b     = team_b,
            winner     = winner,
            player_set = player_set,
            name_fn    = self._names.get,
            color_fn   = self._get_player_color,
        )

    # ------------------------------------------------------------------
    # Sort
    # ------------------------------------------------------------------

    @Slot(str, str)
    def _on_sort_changed(self, sort_by: str, sort_order: str) -> None:
        self._settings.sort_by    = sort_by
        self._settings.sort_order = sort_order
        self._settings.save()
        if self._current_fight and self._view:
            fight = self._current_fight
            stats = self._stats_cache.get(fight.id, {})
            username = (self._config.username if self._config else "").strip()
            self._render_fight(fight, stats, username)

    # ------------------------------------------------------------------
    # Player API check
    # ------------------------------------------------------------------

    def _start_player_check(
        self,
        names: list[str],
        fight: Fight | None,
        stats: dict[str, ParticipantStats],
        username: str,
    ) -> None:
        if not self._view:
            return
        self._check_id += 1
        if self._check_worker:
            self._check_worker.cancel()

        self._view.show_loading("Verifying player identities…")
        worker = _PlayerCheckWorker(names, self._player_cache)
        self._check_worker = worker
        my_id = self._check_id

        @Slot(dict)
        def _done(results: dict[str, bool]) -> None:
            if my_id != self._check_id or not self._view:
                return
            self._player_cache.update({
                name: False if self._is_forced_non_player(name) else is_player
                for name, is_player in results.items()
            })
            self._view.hide_loading()
            if fight is not None:
                self._render_fight(fight, stats, username)

        @Slot(str, int, int)
        def _prog(name: str, done: int, total: int) -> None:
            if self._view:
                self._view.update_progress(done, total, f"Checking: {name}")

        worker.signals.finished.connect(_done)
        worker.signals.progress.connect(_prog)
        self._pool.start(worker)

    # ------------------------------------------------------------------
    # Team inference
    # ------------------------------------------------------------------

    def _infer_teams(
        self,
        fight: Fight,
        stats: dict[str, ParticipantStats],
        username: str,
        player_set: set[str],
    ) -> tuple[list[str], list[str]]:
        players = [p for p in stats if p in player_set] if player_set else list(stats.keys())
        if not players:
            players = list(stats.keys())

        # Seed from reward outcomes
        outcomes: dict[str, str] = {}
        for ev in fight.events:
            if ev.event_type == "reward" and ev.source in ("victory", "defeat"):
                outcomes[ev.actor] = ev.source
        winners = {p for p, r in outcomes.items() if r == "victory" and p in players}
        losers  = {p for p, r in outcomes.items() if r == "defeat"  and p in players}

        if outcomes and (winners or losers):
            team_a = sorted(winners)
            team_b = sorted(losers)
            remaining = set(players) - winners - losers
            for n in sorted(remaining):
                (team_a if len(team_a) <= len(team_b) else team_b).append(n)
        else:
            # Damage-graph inference
            opp: dict[str, dict[str, float]] = {}
            for ev in fight.events:
                if ev.event_type != "damage":
                    continue
                a, b = ev.actor, ev.target
                if a not in players or b not in players or a == b:
                    continue
                opp.setdefault(a, {}).setdefault(b, 0.0)
                opp[a][b] += ev.amount

            a_set: set[str] = set()
            b_set: set[str] = set()
            remaining = set(players)
            if remaining:
                seed = max(remaining, key=lambda n: sum(opp.get(n, {}).values()))
                a_set.add(seed)
                remaining.discard(seed)
                queue = [seed]
                while queue:
                    cur = queue.pop()
                    for opp_name in sorted(opp.get(cur, {}), key=lambda x: -opp.get(cur, {}).get(x, 0)):
                        if opp_name in a_set or opp_name in b_set:
                            continue
                        (b_set if cur in a_set else a_set).add(opp_name)
                        remaining.discard(opp_name)
                        queue.append(opp_name)
                for n in sorted(remaining):
                    a_pull = sum(opp.get(n, {}).get(x, 0) + opp.get(x, {}).get(n, 0) for x in a_set)
                    b_pull = sum(opp.get(n, {}).get(x, 0) + opp.get(x, {}).get(n, 0) for x in b_set)
                    (a_set if a_pull <= b_pull else b_set).add(n)
                if not b_set:
                    ordered = sorted(players)
                    half = max(1, len(ordered) // 2)
                    a_set, b_set = set(ordered[:half]), set(ordered[half:])
            team_a, team_b = sorted(a_set), sorted(b_set)

        # Ensure username is on Team A
        if username and username in players:
            if username in team_b and username not in team_a:
                team_a, team_b = team_b, team_a

        return team_a, team_b

    # ------------------------------------------------------------------
    # Winner detection
    # ------------------------------------------------------------------

    def _determine_winner(
        self,
        fight: Fight,
        team_a: list[str],
        team_b: list[str],
        stats: dict[str, ParticipantStats],
    ) -> str | None:
        outcomes: dict[str, str] = {}
        for ev in fight.events:
            if ev.event_type == "reward" and ev.source in ("victory", "defeat"):
                outcomes[ev.actor] = ev.source
        if outcomes:
            wa = sum(1 for p in team_a if outcomes.get(p) == "victory")
            wb = sum(1 for p in team_b if outcomes.get(p) == "victory")
            if wa != wb:
                return "A" if wa > wb else "B"
            da = sum(1 for p in team_a if outcomes.get(p) == "defeat")
            db = sum(1 for p in team_b if outcomes.get(p) == "defeat")
            if da != db:
                return "A" if da < db else "B"
        dmg_a = sum(stats[p].damage_dealt for p in team_a if p in stats)
        dmg_b = sum(stats[p].damage_dealt for p in team_b if p in stats)
        if dmg_a > dmg_b: return "A"
        if dmg_b > dmg_a: return "B"
        return None

    # ------------------------------------------------------------------
    # Toolbar actions
    # ------------------------------------------------------------------

    @Slot()
    def _on_open_file(self) -> None:
        if not self._view:
            return
        initial = str(self._single_log.parent if self._single_log else
                      Path(self._config.logs_path if self._config else "."))
        path, _ = QFileDialog.getOpenFileName(
            self._view, "Open combat log", initial,
            "Combat logs (*.log);;All files (*.*)"
        )
        if not path:
            return
        p = Path(path)
        self._single_log = p
        self._view.set_scope(p.name)
        self._reload(logs_override=[p])

    @Slot()
    def _on_show_all_logs(self) -> None:
        self._single_log = None
        if self._view:
            self._view.set_scope(None)
        self._reload()

    @Slot()
    def _on_analyze_all(self) -> None:
        if not self._all_fights or not self._view:
            return
        all_names: set[str] = set()
        for fight in self._all_fights:
            s = self._stats_cache.get(fight.id)
            if s is None:
                s = aggregate_stats(fight)
                self._stats_cache[fight.id] = s
            self._mark_forced_non_players(s)
            for n in s:
                if n and n.upper() != "N/A" and not self._is_forced_non_player(n) and n not in self._player_cache:
                    all_names.add(n)
        if all_names and self._current_fight:
            self._start_player_check(
                sorted(all_names),
                self._current_fight,
                self._stats_cache.get(self._current_fight.id, {}),
                (self._config.username if self._config else "").strip(),
            )

    @Slot()
    def _on_clear_cache(self) -> None:
        self._cache.clear()
        self._stats_cache.clear()
        self._player_cache.clear()
        self._color_cache.clear()
        self._reload()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_player_color(self, name: str) -> str:
        if name not in self._color_cache:
            self._color_cache[name] = PIE_PALETTE[len(self._color_cache) % len(PIE_PALETTE)]
        return self._color_cache[name]

    def _is_forced_non_player(self, name: str | None) -> bool:
        candidate = (name or "").strip()
        if not candidate:
            return True
        if re.match(r"^NPC\d+$", candidate, re.IGNORECASE):
            return True
        if candidate.upper() == "N/A":
            return True
        if "(" in candidate or ")" in candidate:
            return True
        if "  " in candidate:
            return True
        lowered = candidate.lower()
        return (
            lowered.startswith("ship_")
            or lowered.startswith("module_")
            or lowered.startswith("weapon_")
        )

    def _mark_forced_non_players(self, names) -> None:
        for name in names:
            if self._is_forced_non_player(name):
                self._player_cache[name] = False

    def _format_fight_label(self, fight: Fight) -> str:
        ts = fight.start.strftime("%d.%m.%Y %H:%M") if fight.start else fight.id
        mode    = fight.game_mode or "Unknown"
        friendly = GAME_MODE_MAP.get(mode, mode)
        secs = fight.actual_game_time_sec or 0.0
        if secs > 0:
            m, s = divmod(int(round(secs)), 60)
            dur = f" — {m:02d}:{s:02d}"
        elif fight.start and fight.end:
            m, s = divmod(int((fight.end - fight.start).total_seconds()), 60)
            dur = f" — {m:02d}:{s:02d}"
        else:
            dur = ""
        return f"{ts}  [{friendly}]{dur}"

    # ------------------------------------------------------------------
    # Settings dialog
    # ------------------------------------------------------------------

    def _open_settings(self, parent: QWidget) -> None:
        dlg = _SettingsDialog(
            config       = self._config,
            name_manager = self._names,
            known_names  = self._collect_display_name_candidates(),
            known_names_provider = self._collect_display_name_candidates,
            parent       = parent,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            if self._config:
                self._config.logs_path = dlg.logs_path
                self._config.username  = dlg.username
                self._config.save()
            self._names.save()
            self._reload()

    def _collect_display_name_candidates(self) -> list[str]:
        names: set[str] = set(self._names.get_all_mappings().keys())

        def add_candidate(value: str | None) -> None:
            text = (value or "").strip()
            if not text:
                return
            lowered = text.lower()
            if "totaldamage" in lowered or "mostdamagewith" in lowered:
                return
            names.add(text)

        for fight in self._all_fights:
            for event in fight.events:
                add_candidate(event.source)
                add_candidate(event.actor)
                add_candidate(event.target)

        return sorted(names, key=str.lower)


# ---------------------------------------------------------------------------
# Settings dialog
# ---------------------------------------------------------------------------

_BTN = ("QPushButton{background:transparent;color:#8899aa;border:1px solid #1e3050;"
        "border-radius:4px;padding:4px 12px}"
        "QPushButton:hover{color:#e8f0fe;border-color:#4fc3f7}")


class _SettingsDialog(QDialog):
    def __init__(
        self,
        config: AppConfig | None,
        name_manager: DisplayNameManager,
        known_names: list[str],
        known_names_provider: Callable[[], list[str]] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Combat Analyzer — Settings")
        self.setMinimumWidth(440)
        self._names    = name_manager
        self._known_names = known_names
        self._known_names_provider = known_names_provider
        self.logs_path = config.logs_path if config else ""
        self.username  = config.username  if config else ""

        layout = QVBoxLayout(self)
        form   = QFormLayout()
        self._username_edit = QLineEdit(self.username)
        form.addRow("Username:", self._username_edit)

        path_row = QWidget()
        ph = QFormLayout(path_row)
        ph.setContentsMargins(0, 0, 0, 0)
        self._path_edit = QLineEdit(self.logs_path)
        browse = QPushButton("Browse…")
        browse.setStyleSheet(_BTN)
        browse.clicked.connect(self._browse)
        ph.addRow(self._path_edit)
        ph.addRow(browse)
        form.addRow("Logs path:", path_row)
        layout.addLayout(form)

        dn = QPushButton("Edit display names…")
        dn.setStyleSheet(_BTN)
        dn.clicked.connect(self._edit_names)
        layout.addWidget(dn)

        bb = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        bb.accepted.connect(self._accept)
        bb.rejected.connect(self.reject)
        layout.addWidget(bb)

    def _browse(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "Select logs folder", self._path_edit.text())
        if d:
            self._path_edit.setText(d)

    def _accept(self) -> None:
        self.logs_path = self._path_edit.text().strip()
        self.username  = self._username_edit.text().strip()
        self.accept()

    def _edit_names(self) -> None:
        from src.modules.combat_analysis.ui.display_names_dialog import DisplayNamesDialog
        if self._known_names_provider is not None:
            self._known_names = self._known_names_provider()
        dlg = DisplayNamesDialog(self._names, self._known_names, self)
        dlg.exec()