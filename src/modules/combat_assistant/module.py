"""
CombatAssistantModule — TOGGLEABLE module that provides real-time combat
assistance via log-tailing, screen scanning, an overlay, and audio cues.

Features
--------
* Agony buff tracker (BuffNearDeath_big) — multi-user aware
* Torpedo wave timer (Conquest / ClanShip mode) — 58.5 s first, 65.5 s after
* Bomb tracker — screen template matching, with a log-based fallback
* System capture detector — pixel colour at 3 set screen points + sound alerts
"""

from __future__ import annotations

from dataclasses import dataclass, field
from html import escape
import json
import os
import queue
import re
import threading
import time
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, Qt, QTimer, Signal, Slot
from PySide6.QtWidgets import QApplication, QMessageBox, QWidget

from src.core.config import AppConfig
from src.core.module_base import ModuleBase, ModuleType
from src.modules.combat_assistant.log_reader import LogTailer
from src.modules.combat_assistant.scanner import ScreenScanner
from src.modules.combat_assistant.ui.overlay import (
    CalibrationOverlay,
    OverlayWindow,
    PreviewOverlay,
)
from src.modules.combat_assistant.ui.settings_view import CombatAssistantSettingsView

# ---- regexes replicated from parser (no circular dependency) ----------
# Actual SC log format uses single-quoted aura/target names and includes
# id/type fields:  Apply aura 'Name' id N type T to 'Target'
_AURA_APPLY_RE  = re.compile(
    r"Apply\s+aura\s+'(?P<aura>[^']+)'\s+id\s+\d+\s+type\s+\S+\s+to\s+'(?P<target>[^']+)'",
    re.IGNORECASE,
)
_AURA_CANCEL_RE = re.compile(
    r"Cancel\s+aura\s+'(?P<aura>[^']+)'\s+id\s+\d+\s+type\s+\S+\s+from\s+'(?P<target>[^']+)'",
    re.IGNORECASE,
)
_SESSION_START_RE = re.compile(r"Start\s+gameplay\s+'(?P<mode>[^']+)'", re.IGNORECASE)
_GAME_END_RE    = re.compile(r"Actual\s+game\s+time\s+[\d.]+", re.IGNORECASE)
_DAMAGE_RE      = re.compile(r"\bDamage\b")
_MEANINGFUL_ACTIVITY_RE = re.compile(
    r"\b(Damage|Heal|Killed|Reward|Participant|Spawn\s+SpaceShip)\b",
    re.IGNORECASE,
)

_MEANINGFUL_ACTIVITY_TIMEOUT = 10.0

# ---- Bomb constants ----------------------------------------------------
_BOMB_FIRST_SPAWN  = 118.0   # seconds after match start until first bomb spawns
_BOMB_RESPAWN      = 119.0   # seconds after pickup until the next bomb spawns
_BOMB_ALLY_THRESHOLD    = 0.75  # TM_CCORR_NORMED minimum for ally bomb icon
_BOMB_ENEMY_THRESHOLD   = 0.75  # TM_CCORR_NORMED minimum for enemy bomb icon
_BOMB_ALLY_SQDIFF_MAX   = 0.38  # TM_SQDIFF_NORMED maximum for ally bomb icon
_BOMB_ENEMY_SQDIFF_MAX  = 0.50  # TM_SQDIFF_NORMED maximum for enemy bomb icon
_BOMB_ALLY_COLOR_MAX_DIST  = 90.0
_BOMB_ENEMY_COLOR_MAX_DIST = 40.0
_BOMB_STREAK_PICKUP = 2   # consecutive ticks with higher count to confirm pickup (~2s)
_BOMB_STREAK_LOSS   = 6   # consecutive ticks with lower count to confirm loss (~6s)
_BOMB_MODE_CHANGE_LOSS_GRACE = 8.0  # ignore temporary count drops right after a mode switch

_BOMB_REGION_KEYS: dict[str, dict[str, str]] = {
    "ally": {
        "ingame":  "ally_roster_ingame",
        "respawn": "ally_roster_respawn",
    },
    "enemy": {
        "ingame":  "enemy_roster_ingame",
        "respawn": "enemy_roster_respawn",
    },
}

_LEGACY_BOMB_REGION_KEYS = {
    "ally_roster": _BOMB_REGION_KEYS["ally"]["ingame"],
    "enemy_roster": _BOMB_REGION_KEYS["enemy"]["ingame"],
}

_ID_RE = re.compile(r"\s*\|\s*\d+\s*$")


def _strip_id(name: str) -> str:
    return _ID_RE.sub("", name).strip()


# ---- sound files -------------------------------------------------------
_SOUNDS_DIR = Path(__file__).parent / "sounds"
SND_BOMB      = _SOUNDS_DIR / "BombPickupF.wav"
SND_TORP      = _SOUNDS_DIR / "TorpedosF.wav"
SND_CAPT_CMD   = _SOUNDS_DIR / "EnemyAtCommandTowerF.wav"
SND_CAPT_SHLD  = _SOUNDS_DIR / "EnemyAtShieldEmitterF.wav"
SND_CAPT_WPNC  = _SOUNDS_DIR / "EnemyAtWeaponCoolerF.wav"

_CAPTURE_SOUNDS: dict[str, Path] = {
    "cmd":    SND_CAPT_CMD,
    "shield": SND_CAPT_SHLD,
    "weapon": SND_CAPT_WPNC,
}


# ---------------------------------------------------------------------------
# Pydantic settings model
# ---------------------------------------------------------------------------

from pydantic import BaseModel, Field
from src.core.config import USER_DATA_DIR


class CombatAssistantSettings(BaseModel):
    enabled:           bool        = False
    overlay_x:         int         = 100
    overlay_y:         int         = 100
    agony_enabled:     bool        = False
    agony_extra_users: list[str]   = Field(default_factory=list)
    torp_enabled:      bool        = False
    bomb_enabled:      bool        = False
    capture_enabled:   bool        = False
    # calibration data
    regions:           dict[str, list[int]]  = Field(default_factory=dict)
    points:            dict[str, list[int]]  = Field(default_factory=dict)

    _path: Path = USER_DATA_DIR / "combat_assistant_settings.json"

    @classmethod
    def load(cls) -> "CombatAssistantSettings":
        p = USER_DATA_DIR / "combat_assistant_settings.json"
        if p.exists():
            try:
                raw = json.loads(p.read_text(encoding="utf-8"))
                regions = raw.get("regions") or {}
                if isinstance(regions, dict):
                    for legacy_key, new_key in _LEGACY_BOMB_REGION_KEYS.items():
                        if legacy_key in regions and new_key not in regions:
                            regions[new_key] = regions[legacy_key]
                    for legacy_key in _LEGACY_BOMB_REGION_KEYS:
                        regions.pop(legacy_key, None)
                    raw["regions"] = regions
                return cls.model_validate(raw)
            except Exception:
                pass
        return cls()

    def save(self) -> None:
        p = USER_DATA_DIR / "combat_assistant_settings.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(self.model_dump_json(indent=2), encoding="utf-8")


@dataclass
class _BombSide:
    """All bomb tracking state for one team (ally or enemy)."""
    spawn_times: list[float] = field(default_factory=list)
    available: int = 0
    carried: int = 0               # number of bombs currently being carried
    last_raw_count: int = -1       # raw icon count from previous tick (-1 = no scan)
    stable_count: int = -1         # debounced/confirmed count (-1 = unknown)
    streak: int = 0                # consecutive ticks with same raw count
    last_scan_time: float = 0.0    # timestamp of last successful scan


# ---------------------------------------------------------------------------
# CombatAssistantModule
# ---------------------------------------------------------------------------

class CombatAssistantModule(ModuleBase):
    """TOGGLEABLE — runs silently in the background when enabled."""

    overlay_refresh_requested: Signal = Signal()

    # ModuleBase
    module_id    = "combat_assistant"
    display_name = "Combat Assistant"
    description  = "Real-time overlay: agony buff, torpedos, bomb tracker, capture alerts."
    module_type  = ModuleType.TOGGLEABLE

    @property
    def is_enabled(self) -> bool:
        return self.settings.enabled

    def __init__(self) -> None:
        super().__init__()
        self.settings: CombatAssistantSettings = CombatAssistantSettings.load()

        # --- Services ---
        self._tailer:  Optional[LogTailer]    = None
        self._overlay: Optional[OverlayWindow] = None
        self._scanner: ScreenScanner          = ScreenScanner()
        self._settings_view: Optional[CombatAssistantSettingsView] = None
        self._overlay_editing = False

        # --- Match state ---
        self._match_active    = False
        self._match_conquest  = False
        self._last_damage_ts  = 0.0
        self._last_meaningful_ts = 0.0
        self._in_hangar = True

        # --- Agony state (per-user) ---
        # key: lower-cased username → {active_until, cooldown_until}
        self._agony: dict[str, dict[str, float]] = {}

        # --- Torpedo state ---
        self._torp_launch_ts:   float = 0.0
        self._torp_next_wave:   float = 0.0

        # --- Bomb state ---
        self._bomb_sides: dict[str, _BombSide] = {
            "ally":  _BombSide(),
            "enemy": _BombSide(),
        }
        self._bomb_debug_enabled = True
        self._bomb_debug_log_path = USER_DATA_DIR / "combat_assistant_bomb_debug.log"
        self._bomb_debug_images = False
        self._bomb_debug_frames_dir = USER_DATA_DIR / "_bomb_debug_frames"
        self._map_ref_image: object = None  # numpy array or None; loaded lazily
        self._bomb_map_open: bool | None = None  # cached per-tick result
        self._map_mode_cache: str = "ingame"  # hysteresis: last confident screen mode
        self._bomb_mode_changed_at: float = 0.0

        # --- Capture state ---
        self._capture_white_since: dict[str, float] = {}
        self._capture_last_sound:  dict[str, float] = {}
        self._capture_pixel_debug: dict[str, tuple] = {}

        # --- Scan lock (prevents overlap between QTimer ticks) ---
        self._scan_lock = threading.Lock()
        self._scan_running = False

        # --- Sound queue (daemon thread; plays sequentially) ---
        self._snd_queue: queue.Queue[Path] = queue.Queue()
        self._snd_thread = threading.Thread(
            target=self._sound_worker, daemon=True, name="snd-worker"
        )
        self._snd_thread.start()

        # --- QTimer for periodic scan (1 s) ---
        self._scan_timer = QTimer(self)
        self._scan_timer.setInterval(1000)
        self._scan_timer.timeout.connect(self._on_tick)
        self.overlay_refresh_requested.connect(self._update_overlay)

        # --- CalibrationOverlay reference (only one can be open) ---
        self._calib_overlay: Optional[CalibrationOverlay] = None
        self._preview_overlay: Optional[PreviewOverlay] = None

    # ------------------------------------------------------------------
    # ModuleBase interface
    # ------------------------------------------------------------------

    def initialize(self, config: AppConfig) -> None:
        self._config = config
        status = "Enabled" if self.settings.enabled else "Disabled"
        self.status_changed.emit(status)
        if self.settings.enabled:
            self._start()

    def shutdown(self) -> None:
        self._stop()

    def on_config_changed(self, config: AppConfig) -> None:
        self._config = config
        if self._tailer is not None:
            self._tailer.update_root(config.logs_path)

    def on_toggle(self, enabled: bool) -> None:
        self.settings.enabled = enabled
        self.settings.save()
        if enabled:
            self._start()
        else:
            self._stop()
        self.status_changed.emit("Enabled" if enabled else "Disabled")
        # Keep settings view in sync
        if self._settings_view:
            self._settings_view.sync_master(enabled)

    def build_settings_panel(self, parent: QWidget) -> QWidget:
        view = CombatAssistantSettingsView(self, parent)
        self._settings_view = view
        view.master_toggled.connect(self._on_settings_toggle)
        return view

    # ------------------------------------------------------------------
    # Start / Stop
    # ------------------------------------------------------------------

    def _start(self) -> None:
        """Start tailer, load assets, show overlay, start scan timer."""
        config = getattr(self, "_config", None)
        if config is None:
            return

        # Log tailer
        if self._tailer is None:
            self._tailer = LogTailer(config.logs_path)
            self._tailer.new_lines.connect(self._process_lines)
        else:
            self._tailer.update_root(config.logs_path)
        if not self._tailer.isRunning():
            self._tailer.start()

        # Template assets
        assets = Path(__file__).parent / "assets"
        def _load():
            enemy_path = assets / "Enemy bomb logo.png"
            ally_path = assets / "Allied bomb logo.png"
            self._rebuild_ally_bomb_template_from_enemy(enemy_path, ally_path)
            self._scanner.load_template("bomb_enemy", enemy_path)
            self._scanner.load_template("bomb_ally", ally_path)
        threading.Thread(target=_load, daemon=True).start()

        # Overlay
        if self._overlay is None:
            self._build_overlay()
        self._overlay.move_to_physical(self.settings.overlay_x, self.settings.overlay_y)
        self._overlay.set_edit_mode(self._overlay_editing)
        self._update_overlay()

        # Scan timer
        self._scan_timer.start()

        # History scan
        QTimer.singleShot(1200, self._check_match_from_history)

    def _stop(self) -> None:
        self._scan_timer.stop()
        if self._tailer:
            self._tailer.stop()
            self._tailer = None
        if self._overlay:
            self._overlay_editing = False
            self._overlay.set_edit_mode(False)
            self._overlay.hide()
        self._sync_overlay_edit_state()

    # ------------------------------------------------------------------
    # Overlay construction
    # ------------------------------------------------------------------

    def _build_overlay(self) -> None:
        from PySide6.QtWidgets import QGridLayout, QLabel, QVBoxLayout, QWidget

        self._overlay = OverlayWindow()
        self._overlay.position_changed.connect(self._on_overlay_moved)

        self._ov_left_col = QWidget(self._overlay)
        self._ov_left_col.setStyleSheet("background: transparent;")
        self._ov_right_col = QWidget(self._overlay)
        self._ov_right_col.setStyleSheet("background: transparent;")

        # Inner layout — labels populated each tick
        self._ov_agony_lbl  = QLabel(self._ov_left_col)
        self._ov_torp_lbl   = QLabel(self._ov_right_col)
        self._ov_b_ally_lbl = QLabel(self._ov_right_col)
        self._ov_b_ene_lbl  = QLabel(self._ov_right_col)

        base_style = "color: white; font: bold 10pt 'Consolas'; background: transparent;"
        for lbl in (
            self._ov_agony_lbl,
            self._ov_torp_lbl,
            self._ov_b_ally_lbl,
            self._ov_b_ene_lbl,
        ):
            lbl.setStyleSheet(base_style)
            lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            lbl.hide()

        left_lay = QVBoxLayout(self._ov_left_col)
        left_lay.setContentsMargins(0, 0, 0, 0)
        left_lay.setSpacing(2)
        left_lay.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        left_lay.addWidget(self._ov_agony_lbl)

        right_lay = QVBoxLayout(self._ov_right_col)
        right_lay.setContentsMargins(0, 0, 0, 0)
        right_lay.setSpacing(2)
        right_lay.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        right_lay.addWidget(self._ov_torp_lbl)
        right_lay.addWidget(self._ov_b_ally_lbl)
        right_lay.addWidget(self._ov_b_ene_lbl)

        lay = QGridLayout(self._overlay)
        lay.setContentsMargins(10, 6, 10, 6)
        lay.setHorizontalSpacing(16)
        lay.setVerticalSpacing(8)
        lay.addWidget(
            self._ov_left_col,
            0,
            0,
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft,
        )
        self._overlay.set_edit_mode(self._overlay_editing)

    @staticmethod
    def _format_overlay_rows(
        rows: list[tuple[str, str, str]],
        *,
        min_name_width: int = 0,
        min_status_width: int = 0,
        gap_spaces: int = 2,
    ) -> str:
        if not rows:
            return ""

        name_width = max(max(len(name) for name, _, _ in rows), min_name_width)
        status_width = max(max(len(status) for _, status, _ in rows), min_status_width)
        html_rows: list[str] = []
        for name, status, color in rows:
            padded_name = escape(name.ljust(name_width)).replace(" ", "&nbsp;")
            padded_status = escape(status.ljust(status_width)).replace(" ", "&nbsp;")
            separator = "&nbsp;" * gap_spaces
            html_rows.append(
                "<div style='white-space:pre; margin:0; padding:0; line-height:1.2;'>"
                f"<span style='color:white;'>{padded_name}</span>"
                + separator
                +
                f"<span style='color:{color};'>{padded_status}</span>"
                "</div>"
            )

        return "".join(html_rows)

    # ------------------------------------------------------------------
    # Bomb helpers (new name-hash based tracker)
    # ------------------------------------------------------------------

    def _bomb_debug(self, side: str, message: str) -> None:
        if not self._bomb_debug_enabled:
            return
        line = f"[{time.strftime('%H:%M:%S')}] [BOMB][{side.upper()}] {message}"
        print(line)
        try:
            USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
            with self._bomb_debug_log_path.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")
        except Exception:
            pass

    def _reset_bomb_state(self, *, now: float | None = None, match_start: bool = False) -> None:
        now = time.time() if now is None else now
        if match_start:
            try:
                USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
                self._bomb_debug_log_path.write_text("", encoding="utf-8")
            except Exception:
                pass
        for side, state in self._bomb_sides.items():
            state.spawn_times = [now + _BOMB_FIRST_SPAWN] if match_start else []
            state.available = 0
            state.carried = 0
            state.last_raw_count = -1
            state.stable_count = -1
            state.streak = 0
            state.last_scan_time = 0.0
            self._bomb_debug(
                side,
                f"reset match_start={match_start} spawn_times={[max(0, int(t - now)) for t in state.spawn_times]}",
            )
        self._map_mode_cache = "ingame"
        self._bomb_mode_changed_at = now

    def _bootstrap_bomb_from_history(self, now: float) -> None:
        for side, state in self._bomb_sides.items():
            if state.available or state.spawn_times or state.carried:
                continue
            state.available = 1
            self._bomb_debug(side, "history bootstrap: assuming bomb available")

    # ------------------------------------------------------------------
    # Map/respawn screen detection
    # ------------------------------------------------------------------

    _MAP_REF_IMAGE_PATH = USER_DATA_DIR / "map_detect_reference.png"
    _MAP_DETECT_THRESHOLD = 0.80  # similarity above which we say "map is open"

    def _load_map_ref_image(self) -> None:
        """Load the saved reference image from disk (once)."""
        if self._map_ref_image is not None:
            return
        p = self._MAP_REF_IMAGE_PATH
        if p.exists():
            try:
                import cv2
                img = cv2.imread(str(p), cv2.IMREAD_COLOR)
                if img is not None:
                    self._map_ref_image = img
            except Exception:
                pass

    def _save_map_ref_image(self, img: "np.ndarray") -> None:
        """Save a reference image to disk and cache it."""
        try:
            import cv2
            self._MAP_REF_IMAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(self._MAP_REF_IMAGE_PATH), img)
            self._map_ref_image = img
        except Exception:
            pass

    def _is_map_open(self) -> bool | None:
        """Check if the map/respawn screen is currently showing.

        Uses hysteresis to avoid oscillating between modes during
        screen transitions.  High similarity (≥ 0.80) → respawn,
        low similarity (≤ 0.20) → ingame.  In between, reuse the
        last confident result.

        Returns True if respawn/map, False if ingame, None if not calibrated.
        """
        region_vals = self.settings.regions.get("map_detect")
        if not region_vals or len(region_vals) != 4:
            return None
        self._load_map_ref_image()
        if self._map_ref_image is None:
            return None
        region = tuple(region_vals)
        current = self._scanner.capture_region_image(region)
        if current is None:
            return None
        similarity = ScreenScanner.compare_images(self._map_ref_image, current)

        # Hysteresis thresholds
        if similarity >= 0.80:
            new_mode = "respawn"
        elif similarity <= 0.20:
            new_mode = "ingame"
        else:
            # Uncertain — keep previous mode
            new_mode = self._map_mode_cache

        if new_mode != self._map_mode_cache:
            self._bomb_debug("map", f"mode change {self._map_mode_cache}→{new_mode} sim={similarity:.3f}")
            self._map_mode_cache = new_mode
            self._bomb_mode_changed_at = time.time()

        self._bomb_debug("map", f"similarity={similarity:.3f} mode={self._map_mode_cache}")
        return self._map_mode_cache == "respawn"

    def _count_bomb_icons(self, side: str) -> tuple[int, list[tuple[int, int, float]], tuple[float, float]]:
        """Count bomb icons in the appropriate roster region.

        Uses the map-detect reference with hysteresis to determine which
        screen is active (ingame vs respawn).  If not calibrated, tries both.

        Returns (count, positions, best_scores).
        """
        template = f"bomb_{side}"
        threshold = _BOMB_ALLY_THRESHOLD if side == "ally" else _BOMB_ENEMY_THRESHOLD
        sqdiff_max = _BOMB_ALLY_SQDIFF_MAX if side == "ally" else _BOMB_ENEMY_SQDIFF_MAX
        color_max_dist = _BOMB_ALLY_COLOR_MAX_DIST if side == "ally" else _BOMB_ENEMY_COLOR_MAX_DIST
        debug_dir = self._bomb_debug_frames_dir if self._bomb_debug_images else None

        # Determine which screen modes to scan
        map_open = self._bomb_map_open
        if map_open is True:
            modes_to_scan = ("respawn",)
        elif map_open is False:
            modes_to_scan = ("ingame",)
        else:
            modes_to_scan = ("ingame", "respawn")

        total_count = 0
        all_positions: list[tuple[int, int, float]] = []
        best_ccorr = -1.0
        best_sqdiff = -1.0

        for screen_mode in modes_to_scan:
            region_key = _BOMB_REGION_KEYS[side][screen_mode]
            region_vals = self.settings.regions.get(region_key)
            if not region_vals or len(region_vals) != 4:
                continue
            region = tuple(region_vals)
            count, positions, scores = self._scanner.count_bomb_icons(
                template, region, threshold=threshold, sqdiff_max=sqdiff_max,
                color_max_dist=color_max_dist, debug_dir=debug_dir,
                debug_tag=f"{side}_{screen_mode}",
            )
            total_count += count
            all_positions.extend(positions)
            if scores[0] > best_ccorr:
                best_ccorr = scores[0]
            if best_sqdiff < 0 or (scores[1] >= 0 and scores[1] < best_sqdiff):
                best_sqdiff = scores[1]

        return (total_count, all_positions, (best_ccorr, best_sqdiff))

    def _layout_overlay_columns(
        self,
        agony_visible: bool,
        multi_mode: bool,
        conquest_visible: bool,
    ) -> None:
        if self._overlay is None:
            return

        lay = self._overlay.layout()
        if lay is None:
            return

        lay.removeWidget(self._ov_left_col)
        lay.removeWidget(self._ov_right_col)
        lay.addWidget(
            self._ov_left_col,
            0,
            0,
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft,
        )
        self._ov_left_col.setVisible(agony_visible)

        if conquest_visible:
            if multi_mode:
                lay.addWidget(
                    self._ov_right_col,
                    0,
                    1,
                    Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft,
                )
            else:
                lay.addWidget(
                    self._ov_right_col,
                    1,
                    0,
                    Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft,
                )
            self._ov_right_col.show()
        else:
            self._ov_right_col.hide()

    def _on_overlay_moved(self, px: int, py: int) -> None:
        self.settings.overlay_x = px
        self.settings.overlay_y = py
        self.settings.save()

    def _sync_overlay_edit_state(self) -> None:
        if self._settings_view:
            self._settings_view.refresh_overlay_edit_button(self._overlay_editing)

    def request_overlay_refresh(self) -> None:
        self.overlay_refresh_requested.emit()

    def _has_recent_meaningful_activity(self, *, now: float | None = None) -> bool:
        now = time.time() if now is None else now
        return (now - self._last_meaningful_ts) < _MEANINGFUL_ACTIVITY_TIMEOUT

    def _mark_meaningful_activity(self, now: float) -> None:
        self._last_damage_ts = now
        self._last_meaningful_ts = now
        self._in_hangar = False

    def _update_overlay_visibility(self, content_visible: bool) -> None:
        if self._overlay is None:
            return

        if self._overlay_editing:
            if not self._overlay.isVisible():
                self._overlay.show()
            return

        recent_meaningful = self._has_recent_meaningful_activity()
        should_show = (
            self.settings.enabled
            and self._match_active
            and content_visible
            and self._is_game_foreground()
            and recent_meaningful
            and not self._in_hangar
        )

        if should_show:
            self._overlay.move_to_physical(self.settings.overlay_x, self.settings.overlay_y)
            if not self._overlay.isVisible():
                self._overlay.show()
        elif self._overlay.isVisible():
            self._overlay.hide()

    # ------------------------------------------------------------------
    # Settings toggle (from settings view master checkbox)
    # ------------------------------------------------------------------

    @Slot(bool)
    def _on_settings_toggle(self, enabled: bool) -> None:
        # settings_view already saved; just sync the internal state
        if enabled != self.settings.enabled:
            self.on_toggle(enabled)

    # ------------------------------------------------------------------
    # Periodic tick (500 ms)
    # ------------------------------------------------------------------

    @Slot()
    def _on_tick(self) -> None:
        # Offload heavy scanning to a thread; update overlay in this thread after
        if self._scan_running:
            return

        now = time.time()
        bomb_on    = self.settings.bomb_enabled
        capture_on = self.settings.capture_enabled
        recent_meaningful = self._has_recent_meaningful_activity(now=now)

        if self._match_active and not self._overlay_editing and not recent_meaningful:
            self._capture_white_since.clear()
            self.request_overlay_refresh()
            return

        if not (bomb_on and self._match_active) and not (capture_on or self.settings.points):
            self.request_overlay_refresh()
            return

        self._scan_running = True

        def _work():
            try:
                if bomb_on and self._match_active and self._is_game_foreground():
                    self._scan_bombs()
                if capture_on or self.settings.points:
                    self._scan_capture(capture_on)
            finally:
                self._scan_running = False
                self.request_overlay_refresh()

        threading.Thread(target=_work, daemon=True).start()

    # ------------------------------------------------------------------
    # Log processing
    # ------------------------------------------------------------------

    @Slot(list)
    def _process_lines(self, lines: list[str]) -> None:
        now = time.time()
        username = getattr(self, "_config", None)
        username = (username.username if username else "").lower()
        overlay_needs_refresh = False

        for line in lines:
            if "Hangar" in line:
                self._in_hangar = True
                overlay_needs_refresh = True

            # Activity heartbeat (filter out hangar noise)
            if "Hangar" not in line and _MEANINGFUL_ACTIVITY_RE.search(line):
                self._mark_meaningful_activity(now)

            # ---- Match boundaries ----------------------------------------
            if "Start gameplay" in line:
                self._match_active    = True
                self._mark_meaningful_activity(now)
                m = _SESSION_START_RE.search(line)
                self._match_conquest  = (
                    "'ClanShip'" in line or (m and m.group("mode") == "ClanShip")
                )
                self._bomb_debug("ally", f"match start detected conquest={self._match_conquest}")
                self._bomb_debug("enemy", f"match start detected conquest={self._match_conquest}")
                # Torpedo — first wave shortened by 7 s
                self._torp_launch_ts  = now
                self._torp_next_wave  = now + 58.5
                self._reset_bomb_state(now=now, match_start=True)
                overlay_needs_refresh = True

            if _GAME_END_RE.search(line) or any(
                t in line for t in ("Gameplay finished", "Session finished", "Quit application")
            ):
                self._match_active    = False
                self._match_conquest  = False
                self._last_damage_ts  = 0.0
                self._last_meaningful_ts = 0.0
                self._in_hangar = True
                self._agony           = {}
                self._torp_launch_ts  = 0.0
                self._torp_next_wave  = 0.0
                self._bomb_debug("ally", "match end detected; clearing state")
                self._bomb_debug("enemy", "match end detected; clearing state")
                self._reset_bomb_state(now=now, match_start=False)
                overlay_needs_refresh = True

            # ---- Agony ---------------------------------------------------
            if self.settings.agony_enabled:
                m = _AURA_APPLY_RE.search(line)
                if m and m.group("aura") == "BuffNearDeath_big":
                    target = _strip_id(m.group("target")).lower()
                    if target and (target == username or target in [
                        u.lower() for u in [username] + self.settings.agony_extra_users
                    ]):
                        self._mark_meaningful_activity(now)
                        self._agony[target] = {
                            "active_until":   now + 12.0,
                            "cooldown_until": now + 25.0,
                        }
                        overlay_needs_refresh = True

                m = _AURA_CANCEL_RE.search(line)
                if m and m.group("aura") == "BuffNearDeath_big":
                    target = _strip_id(m.group("target")).lower()
                    if target in self._agony:
                        self._mark_meaningful_activity(now)
                        self._agony[target]["active_until"] = 0.0
                        overlay_needs_refresh = True

            # ---- Torpedoes -----------------------------------------------
            if self.settings.torp_enabled and "Spell 'Spell_ClanShipTorpedo'" in line:
                if (now - self._torp_launch_ts) > 15.0:
                    self._mark_meaningful_activity(now)
                    self._torp_launch_ts = now
                    self._torp_next_wave = now + 65.5
                    self._play_sound(SND_TORP)
                    overlay_needs_refresh = True

        if overlay_needs_refresh:
            self.request_overlay_refresh()

    # ------------------------------------------------------------------
    # History scan (detect if match was already in progress on startup)
    # ------------------------------------------------------------------

    def _check_match_from_history(self) -> None:
        if self._tailer is None:
            return
        lines = self._tailer.get_history_lines()
        now = time.time()
        for line in reversed(lines):
            if _GAME_END_RE.search(line) or any(
                t in line for t in ("Gameplay finished", "Session finished", "Quit application")
            ):
                return  # match ended before we started
            m = _SESSION_START_RE.search(line)
            if m or "Start gameplay" in line:
                self._match_active   = True
                self._mark_meaningful_activity(now)
                self._match_conquest = "'ClanShip'" in line or (m and m.group("mode") == "ClanShip")
                if self._match_conquest:
                    self._bootstrap_bomb_from_history(now)
                return

    # ------------------------------------------------------------------
    # Bomb scanning (runs on worker thread)
    # ------------------------------------------------------------------

    def _scan_bombs(self) -> None:
        """Count-based bomb tracker with asymmetric debouncing.

        Each tick:
        1. Process due spawn timers.
        2. Count bomb icons via template matching.
        3. Debounce: require _BOMB_STREAK_PICKUP consecutive ticks for
           count increase, _BOMB_STREAK_LOSS for decrease.
        4. On stable count change, update carried/available and schedule
           respawn timers.
        """
        now = time.time()

        # Detect screen mode once per tick (shared across ally/enemy)
        self._bomb_map_open = self._is_map_open()
        mode_changed_recently = (now - self._bomb_mode_changed_at) < _BOMB_MODE_CHANGE_LOSS_GRACE

        for side, state in self._bomb_sides.items():
            # 1. Process due spawn timers --------------------------------
            due = [t for t in state.spawn_times if t <= now]
            if due:
                state.spawn_times = [t for t in state.spawn_times if t > now]
                state.available += len(due)
                self._bomb_debug(
                    side,
                    f"spawn timer(s) fired count={len(due)} available={state.available} "
                    f"pending={len(state.spawn_times)}",
                )

            # 2. Count bomb icons ----------------------------------------
            raw_count, positions, best_scores = self._count_bomb_icons(side)
            effective_raw_count = raw_count
            if (
                mode_changed_recently
                and state.stable_count >= 0
                and raw_count < state.stable_count
            ):
                effective_raw_count = state.stable_count
                self._bomb_debug(
                    side,
                    f"suppressing loss during mode grace raw={raw_count} stable={state.stable_count} "
                    f"mode={self._map_mode_cache}",
                )

            # 3. Debounce with asymmetric streaks ------------------------
            if effective_raw_count == state.last_raw_count:
                state.streak += 1
            else:
                state.streak = 1
                state.last_raw_count = effective_raw_count

            # Determine required streak based on direction
            if state.stable_count < 0:
                # First scan — accept immediately
                needed = 1
            elif effective_raw_count > state.stable_count:
                needed = _BOMB_STREAK_PICKUP  # fast for pickups
            elif effective_raw_count < state.stable_count:
                needed = _BOMB_STREAK_LOSS    # slow for losses
            else:
                needed = 1  # same count, always stable

            prev_stable = state.stable_count

            if state.streak >= needed:
                state.stable_count = effective_raw_count

            state.last_scan_time = now

            # 4. React to stable count changes ---------------------------
            if state.stable_count != prev_stable and prev_stable >= 0:
                delta = state.stable_count - prev_stable
                if delta > 0:
                    # New pickup(s)
                    state.carried += delta
                    state.available = max(0, state.available - delta)
                    for _ in range(delta):
                        state.spawn_times.append(now + _BOMB_RESPAWN)
                    state.spawn_times.sort()
                    if side == "enemy":
                        self._play_sound(SND_BOMB)
                    self._mark_meaningful_activity(now)
                    self._bomb_debug(
                        side,
                        f"pickup delta={delta} carried={state.carried} "
                        f"available={state.available} pending={len(state.spawn_times)}",
                    )
                elif delta < 0:
                    # Carrier(s) lost bomb
                    lost = abs(delta)
                    state.carried = max(0, state.carried - lost)
                    self._bomb_debug(
                        side,
                        f"loss delta={delta} carried={state.carried} "
                        f"available={state.available}",
                    )

            # 5. Tick summary for debug ----------------------------------
            pending = [max(0, int(t - now)) for t in sorted(state.spawn_times)]
            self._bomb_debug(
                side,
                f"tick raw={raw_count} effective={effective_raw_count} stable={state.stable_count} streak={state.streak} "
                f"carried={state.carried} available={state.available} pending={pending} "
                f"ccorr={best_scores[0]:.3f} sqdiff={best_scores[1]:.3f} "
                f"mode={self._map_mode_cache}",
            )

    # ------------------------------------------------------------------
    # Capture scanning (runs on worker thread)
    # ------------------------------------------------------------------

    def _scan_capture(self, active: bool) -> None:
        now = time.time()
        debug: dict[str, tuple] = {}

        for name, snd_path in _CAPTURE_SOUNDS.items():
            pt = self.settings.points.get(name)
            if not pt:
                continue
            pixel = self._scanner.get_pixel_color(pt[0], pt[1])
            debug[name] = pixel

            if not active:
                continue

            r, g, b = pixel
            is_white = r > 200 and g > 200 and b > 200
            if is_white:
                if name not in self._capture_white_since:
                    self._capture_white_since[name] = now
                elif (now - self._capture_white_since[name]) >= 2.0:
                    last = self._capture_last_sound.get(name, 0.0)
                    if (now - last) > 20.0:
                        self._play_sound(snd_path)
                        self._capture_last_sound[name] = now
            else:
                self._capture_white_since.pop(name, None)

        self._capture_pixel_debug = debug

    # ------------------------------------------------------------------
    # Overlay update (always on Qt main thread via QTimer.singleShot)
    # ------------------------------------------------------------------

    @Slot()
    def _update_overlay(self) -> None:
        if self._overlay is None:
            return

        now = time.time()
        any_visible = False
        agony_visible = False
        conquest_visible = False
        multi_mode = False

        # ---- Agony ---------------------------------------------------
        if self.settings.agony_enabled and self._match_active:
            cfg = getattr(self, "_config", None)
            tracked_users: list[tuple[str, str]] = []
            seen_users: set[str] = set()

            username = (cfg.username if cfg else "").strip()
            if username:
                tracked_users.append((username, username.lower()))
                seen_users.add(username.lower())
            else:
                tracked_users.append(("Self", ""))

            for raw_name in self.settings.agony_extra_users:
                display_name = raw_name.strip()
                if not display_name:
                    continue
                lookup_name = display_name.lower()
                if lookup_name in seen_users:
                    continue
                tracked_users.append((display_name, lookup_name))
                seen_users.add(lookup_name)

            multi_mode = len(tracked_users) > 1

            lines: list[str] = []
            for display_name, lookup_name in tracked_users:
                state = self._agony.get(lookup_name, {}) if lookup_name else {}
                act   = state.get("active_until",   0.0)
                cd    = state.get("cooldown_until",  0.0)
                if now < act:
                    color = "#ffff33"
                    status = f"ACTIVE {int(act - now)} s"
                elif now < cd:
                    color = "#ff3333"
                    status = f"CD {int(cd - now)} s"
                else:
                    color = "#33ff33"
                    status = "READY"
                lines.append((display_name, status, color))
            self._ov_agony_lbl.setText(
                self._format_overlay_rows(lines, min_status_width=12, gap_spaces=1)
            )
            self._ov_agony_lbl.setTextFormat(
                __import__("PySide6.QtCore", fromlist=["Qt"]).Qt.TextFormat.RichText
            )
            self._ov_agony_lbl.show()
            agony_visible = True
            any_visible = True
        else:
            self._ov_agony_lbl.hide()

        conquest_rows: list[tuple[str, str, str]] = []

        # ---- Torpedoes -----------------------------------------------
        if self.settings.torp_enabled and self._match_conquest:
            conquest_visible = True
            if now < self._torp_next_wave:
                rem = int(self._torp_next_wave - now)
                conquest_rows.append(("Torpedos", f"{rem} s", "#ff8800"))
            else:
                conquest_rows.append(("Torpedos", "READY", "#33ff33"))

        # ---- Bombs ---------------------------------------------------
        if self.settings.bomb_enabled and self._match_conquest:
            conquest_visible = True
            for side, tag in (("ally", "Allied Bomb"), ("enemy", "Enemy Bomb")):
                state = self._bomb_sides[side]
                if state.available > 0:
                    conquest_rows.append((tag, "READY", "#33ff33"))
                elif state.spawn_times:
                    rem = max(0, int(min(state.spawn_times) - now))
                    conquest_rows.append((tag, f"{rem} s", "#ff3333"))
                else:
                    conquest_rows.append((tag, "...", "#9bb3d6"))

        if conquest_rows:
            self._ov_torp_lbl.setText(
                self._format_overlay_rows(conquest_rows, min_name_width=11, min_status_width=7)
            )
            self._ov_torp_lbl.setTextFormat(
                __import__("PySide6.QtCore", fromlist=["Qt"]).Qt.TextFormat.RichText
            )
            self._ov_torp_lbl.show()
            any_visible = True
        else:
            self._ov_torp_lbl.hide()

        self._ov_b_ally_lbl.hide()
        self._ov_b_ene_lbl.hide()

        self._layout_overlay_columns(agony_visible, multi_mode, conquest_visible)
        layout = self._overlay.layout()
        if layout is not None:
            layout.activate()
        self._overlay.adjustSize()
        self._update_overlay_visibility(any_visible)

    # ------------------------------------------------------------------
    # Sound
    # ------------------------------------------------------------------

    def _play_sound(self, path: Path) -> None:
        if path.exists():
            self._snd_queue.put(path)

    def _sound_worker(self) -> None:
        import ctypes
        while True:
            path = self._snd_queue.get()
            try:
                # Only play when Star Conflict is in the foreground
                if self._is_game_foreground():
                    import winsound
                    winsound.PlaySound(str(path), winsound.SND_SYNC | winsound.SND_FILENAME)
            except Exception:
                pass
            finally:
                self._snd_queue.task_done()

    @staticmethod
    def _is_game_foreground() -> bool:
        try:
            import ctypes
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            if hwnd == 0:
                return False
            class_buf = ctypes.create_unicode_buffer(256)
            title_buf = ctypes.create_unicode_buffer(256)
            ctypes.windll.user32.GetClassNameW(hwnd, class_buf, 256)
            ctypes.windll.user32.GetWindowTextW(hwnd, title_buf, 256)
            class_name = class_buf.value.strip()
            title = title_buf.value.strip().lower()
            return class_name == "game_main_window" or "star conflict" in title
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Calibration helpers (called from settings view)
    # ------------------------------------------------------------------

    def calibrate_region(self, key: str) -> None:
        """Open fullscreen CalibrationOverlay for region selection."""
        if self._calib_overlay is not None:
            return  # already open
        cal = CalibrationOverlay()
        self._calib_overlay = cal

        def _on_region(x, y, w, h):
            self.settings.regions[key] = [x, y, w, h]
            self.settings.save()
            if self._settings_view:
                self._settings_view.refresh_regions()
            _cleanup()

        def _cleanup():
            self._calib_overlay = None

        cal.region_selected.connect(_on_region)
        cal.region_selected.connect(lambda *_: cal.deleteLater())
        cal.cancelled.connect(_cleanup)
        cal.destroyed.connect(_cleanup)
        cal.start_region()

    def calibrate_point(self, key: str) -> None:
        """Open fullscreen CalibrationOverlay for single-point selection."""
        if self._calib_overlay is not None:
            return
        cal = CalibrationOverlay()
        self._calib_overlay = cal

        def _on_point(x, y):
            self.settings.points[key] = [x, y]
            self.settings.save()
            if self._settings_view:
                self._settings_view.refresh_points()
            _cleanup()

        def _cleanup():
            self._calib_overlay = None

        cal.point_selected.connect(_on_point)
        cal.point_selected.connect(lambda *_: cal.deleteLater())
        cal.cancelled.connect(_cleanup)
        cal.destroyed.connect(_cleanup)
        cal.start_point()

    def calibrate_map_reference(self) -> None:
        """Calibrate the map-detect region: user drags an area over the X button
        on the map/respawn screen, then a reference screenshot is immediately
        captured and saved."""
        if self._calib_overlay is not None:
            return
        cal = CalibrationOverlay()
        self._calib_overlay = cal

        def _on_region(x, y, w, h):
            self.settings.regions["map_detect"] = [x, y, w, h]
            self.settings.save()
            # Immediately capture and save the reference image
            region = (x, y, w, h)
            img = self._scanner.capture_region_image(region)
            if img is not None:
                self._save_map_ref_image(img)
            if self._settings_view:
                self._settings_view.refresh_regions()
            _cleanup()

        def _cleanup():
            self._calib_overlay = None

        cal.region_selected.connect(_on_region)
        cal.region_selected.connect(lambda *_: cal.deleteLater())
        cal.cancelled.connect(_cleanup)
        cal.destroyed.connect(_cleanup)
        cal.start_region()

    def preview_regions(self) -> None:
        """Briefly show a fullscreen overlay that marks calibrated regions."""
        if not self.settings.regions:
            return
        overlay = PreviewOverlay(regions=self.settings.regions)
        self._preview_overlay = overlay
        overlay.destroyed.connect(lambda *_: setattr(self, "_preview_overlay", None))
        overlay.show_preview()

    def preview_points(self) -> None:
        if not self.settings.points:
            return
        overlay = PreviewOverlay(points=self.settings.points)
        self._preview_overlay = overlay
        overlay.destroyed.connect(lambda *_: setattr(self, "_preview_overlay", None))
        overlay.show_preview()

    # ------------------------------------------------------------------
    # Template capture (called from settings view)
    # ------------------------------------------------------------------

    def _rebuild_ally_bomb_template_from_enemy(
        self,
        enemy_path: Path,
        ally_path: Path,
    ) -> bool:
        """Build the ally bomb template by recolouring the enemy silhouette.

        The ally icon has the same stable shape as the enemy icon but a cyan
        tint. Capturing the ally icon directly from gameplay proved unreliable
        because the icon sits over arbitrary backgrounds. Rebuilding it from the
        known-good enemy asset removes that dependency entirely.
        """
        try:
            import cv2
            import numpy as np
        except ImportError:
            return False

        enemy_img = cv2.imread(str(enemy_path), cv2.IMREAD_UNCHANGED)
        if enemy_img is None or enemy_img.ndim != 3 or enemy_img.shape[2] != 4:
            return False

        ally_img = enemy_img.copy()
        ally_bgr = ally_img[:, :, :3]
        alpha = ally_img[:, :, 3] > 0

        # Recolour only the red-tinted pixels. Dark interior details and the
        # alpha silhouette stay intact, which preserves the icon structure.
        b_chan = ally_bgr[:, :, 0].astype("int16")
        g_chan = ally_bgr[:, :, 1].astype("int16")
        r_chan = ally_bgr[:, :, 2].astype("int16")
        tint_mask = alpha & (r_chan >= g_chan + 12) & (r_chan >= b_chan + 12) & (r_chan >= 40)
        if not np.any(tint_mask):
            tint_mask = alpha

        hsv = cv2.cvtColor(ally_bgr, cv2.COLOR_BGR2HSV)
        # OpenCV hue 90-95 is bright cyan. Preserve S/V so the original shading
        # and antialiasing survive the recolour.
        hsv[:, :, 0][tint_mask] = 92
        hsv[:, :, 1][tint_mask] = np.maximum(hsv[:, :, 1][tint_mask], 170)
        hsv[:, :, 2][tint_mask] = np.maximum(hsv[:, :, 2][tint_mask], 150)
        ally_img[:, :, :3] = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)

        ally_path.parent.mkdir(parents=True, exist_ok=True)
        return bool(cv2.imwrite(str(ally_path), ally_img))

    def capture_bomb_template(self, side: str) -> None:
        """Refresh a bomb-icon template.

        Enemy templates are captured from calibrated regions using HSV
        segmentation. Ally templates are rebuilt from the enemy silhouette,
        which is more reliable than trying to isolate a cyan icon over an
        arbitrary gameplay background.
        """
        try:
            import cv2
            import numpy as np
        except ImportError:
            QMessageBox.warning(
                None, "Missing dependency",
                "OpenCV (cv2) is required for template capture.",
            )
            return

        assets_dir = Path(__file__).parent / "assets"
        if side == "ally":
            enemy_path = assets_dir / "Enemy bomb logo.png"
            ally_path = assets_dir / "Allied bomb logo.png"
            if not self._rebuild_ally_bomb_template_from_enemy(enemy_path, ally_path):
                QMessageBox.warning(
                    None, "Template build failed",
                    "Could not rebuild the allied bomb template from the enemy asset.",
                )
                return
            self._scanner.load_template("bomb_ally", ally_path)
            QMessageBox.information(
                None, "Template saved",
                f"Rebuilt allied bomb template from enemy silhouette.\nSaved to: {ally_path}",
            )
            return

        # Collect all calibrated regions for this side
        captures: list[tuple[str, "np.ndarray"]] = []
        for screen_mode in ("ingame", "respawn"):
            region_key = _BOMB_REGION_KEYS[side][screen_mode]
            region_vals = self.settings.regions.get(region_key)
            if not region_vals or len(region_vals) != 4:
                continue
            img = self._scanner.capture_region_image(tuple(region_vals))
            if img is not None:
                captures.append((screen_mode, img))

        if not captures:
            QMessageBox.warning(
                None, "No regions calibrated",
                f"Calibrate at least one {side} bomb region first.",
            )
            return

        # HSV ranges for bomb icon color detection
        if side == "ally":
            # Cyan: H≈65-120 (wider range), permissive S/V to capture the
            # full icon including slightly desaturated shades.
            hsv_ranges = [((65, 65, 65), (120, 255, 255))]
        else:
            # Red wraps around in HSV: H≈0-12 or H≈168-180
            hsv_ranges = [
                ((0, 65, 65), (12, 255, 255)),
                ((168, 65, 65), (180, 255, 255)),
            ]

        # Bomb icon tile is ~30-45px; score candidates by closeness to ideal.
        _IDEAL_SIZE = 35  # pixels (approx bomb icon/tile dimension)
        best_icon = None
        best_score = float("inf")
        best_source = ""
        _ingame_done = False   # track when ingame pass finishes

        # Save all captures for debug regardless
        debug_dir = USER_DATA_DIR / "_template_captures"
        debug_dir.mkdir(parents=True, exist_ok=True)

        # captures is ordered ingame first (see collection loop above).
        # If ingame yields a candidate we skip respawn entirely to avoid
        # false positives from cyan sky backgrounds on the respawn screen.
        for source, img_bgr in captures:
            if _ingame_done and best_icon is not None:
                break  # already found a clean ingame icon — skip respawn

            cv2.imwrite(str(debug_dir / f"{side}_{source}.png"), img_bgr)

            hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
            mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
            for lo, hi in hsv_ranges:
                mask |= cv2.inRange(hsv, np.array(lo), np.array(hi))

            # 5×5 close merges nearby parts of same icon (bomb has internal
            # gaps that split under a smaller kernel).
            kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            kernel_open  = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel_close, iterations=2)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN,  kernel_open,  iterations=1)

            cv2.imwrite(str(debug_dir / f"{side}_{source}_mask.png"), mask)

            # For the ally respawn region, the top half is dominated by
            # a large cyan sky background; restrict search to lower half.
            search_y_start = 0
            if source == "respawn" and side == "ally":
                search_y_start = img_bgr.shape[0] // 2

            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cand_idx = 0
            for cnt in contours:
                x, y, w, h = cv2.boundingRect(cnt)
                # Skip blobs in the restricted header zone
                if (y + h // 2) < search_y_start:
                    continue
                # Max 55px per side (icon tile including border frame)
                if w < 12 or h < 12 or w > 55 or h > 55:
                    continue
                # Aspect ratio roughly square-ish (bomb icon is ~1:1)
                aspect = w / max(h, 1)
                if aspect < 0.6 or aspect > 1.7:
                    continue
                # Fill ratio: bomb icon is fairly dense, not a thin outline
                fill = cv2.contourArea(cnt) / (w * h)
                if fill < 0.25:
                    continue
                # Save every valid candidate for diagnostics
                pad_d = 5
                _dx0 = max(0, x - pad_d); _dy0 = max(0, y - pad_d)
                _dx1 = min(img_bgr.shape[1], x + w + pad_d)
                _dy1 = min(img_bgr.shape[0], y + h + pad_d)
                cv2.imwrite(
                    str(debug_dir / f"{side}_{source}_cand{cand_idx}_{w}x{h}.png"),
                    img_bgr[_dy0:_dy1, _dx0:_dx1],
                )
                cand_idx += 1
                # Score: prefer size closest to ideal
                size_dev = abs((w + h) / 2 - _IDEAL_SIZE)
                if size_dev < best_score:
                    best_score = size_dev
                    # Crop with small padding
                    pad = 3
                    x0 = max(0, x - pad)
                    y0 = max(0, y - pad)
                    x1 = min(img_bgr.shape[1], x + w + pad)
                    y1 = min(img_bgr.shape[0], y + h + pad)
                    icon_bgr = img_bgr[y0:y1, x0:x1]
                    bgra = cv2.cvtColor(icon_bgr, cv2.COLOR_BGR2BGRA)
                    # Alpha: filled contour dilated by ~9px so the match
                    # area includes the dark interior detail pixels of the
                    # icon, not just the bright cyan outline.  This makes
                    # template matching compare the full icon structure.
                    contour_alpha = np.zeros(img_bgr.shape[:2], dtype=np.uint8)
                    cv2.drawContours(contour_alpha, [cnt], -1, 255, cv2.FILLED)
                    dil_k = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9))
                    contour_alpha = cv2.dilate(contour_alpha, dil_k, iterations=1)
                    bgra[:, :, 3] = contour_alpha[y0:y1, x0:x1]
                    best_icon = bgra
                    best_source = source

            if source == "ingame":
                _ingame_done = True

        if best_icon is None:
            QMessageBox.warning(
                None, "No bomb icon found",
                f"Could not detect a {side} bomb icon in the captured regions.\n\n"
                f"Make sure a bomb is being carried (icon visible in the roster), "
                f"then try again.\n\n"
                f"Raw captures and masks saved to:\n{debug_dir}",
            )
            return

        # Save the new template
        template_name = "Allied bomb logo.png" if side == "ally" else "Enemy bomb logo.png"
        template_path = assets_dir / template_name
        cv2.imwrite(str(template_path), best_icon)

        # Reload in scanner
        scanner_key = f"bomb_{side}"
        self._scanner.load_template(scanner_key, template_path)

        h, w = best_icon.shape[:2]
        QMessageBox.information(
            None, "Template saved",
            f"Captured {side} bomb template ({w}×{h}px) from {best_source} region.\n"
            f"Saved to: {template_path}",
        )

    # ------------------------------------------------------------------
    # Overlay edit mode (called from tile if wired up later)
    # ------------------------------------------------------------------

    @property
    def is_overlay_editing(self) -> bool:
        return self._overlay_editing

    def toggle_overlay_edit(self) -> None:
        if self._overlay is None:
            self._build_overlay()
        if self._overlay is None:
            return

        self._overlay_editing = not self._overlay_editing
        self._sync_overlay_edit_state()

        if self._overlay_editing:
            self._overlay.set_edit_mode(True)
            self._overlay.move_to_physical(self.settings.overlay_x, self.settings.overlay_y)
            self._overlay.show()
            self._overlay.raise_()
            return

        self._overlay.set_edit_mode(False)
        px, py = self._overlay.get_physical_position()
        self.settings.overlay_x = px
        self.settings.overlay_y = py
        self.settings.save()
        self._update_overlay()
