import tkinter as tk
import os
from tkinter import ttk, messagebox
import time
import re
import json
import threading
import queue
import ctypes
from pathlib import Path
from typing import List, Optional, Tuple, Dict

from ...config import AppConfig
from ..base import BaseModule
from ..combat_analysis.parser import (
    AURA_APPLY_RE,
    AURA_CANCEL_RE,
    GAME_END_RE,
    SESSION_START_RE,
    DAMAGE_HEAL_RE,
    _strip_id,
)
from .log_reader import LogTailer
from .overlay import OverlayWindow, CalibrationOverlay
from .scanner import ScreenScanner

# Sounds
SND_BOMB = "BombPickupF.wav"
SND_TORP = "TorpedosF.wav"
SND_CAPT_CMD = "EnemyAtCommandTowerF.wav"
SND_CAPT_SHIELD = "EnemyAtShieldEmitterF.wav"
SND_CAPT_WEAPON = "EnemyAtWeaponCoolerF.wav"

class CombatAssistantModule(BaseModule):
    name = "Combat Assistant"
    description = "Real-time combat assistance with overlays, tracking, and alerts."

    def __init__(self, app, config: AppConfig):
        self.app = app
        self.config = config
        self.frame: Optional[ttk.Frame] = None
        self._scan_after_id = None
        self._update_after_id = None
        self.settings_file = Path(__file__).parent / "settings.json"
        
        # --- State ---
        self.username_var = tk.StringVar(value=config.username)
        self.active_log_file_var = tk.StringVar(value="Waiting for log activity...")
        
        # Toggles
        self.enable_agony_var = tk.BooleanVar(value=False)
        self.enable_overlay_var = tk.BooleanVar(value=True)
        self.enable_bomb_var = tk.BooleanVar(value=False)
        self.enable_torp_var = tk.BooleanVar(value=False)
        self.enable_capture_var = tk.BooleanVar(value=False)
        
        # Agony State
        self.agony_active_until = 0.0
        self.agony_cooldown_until = 0.0
        self.agony_is_active = False
        
        # Agony Multi-User Support
        self.agony_users_vars: List[tk.StringVar] = []
        self.agony_ui_frame: Optional[ttk.Frame] = None
        # State: username -> {"active_until": float, "cooldown_until": float}
        self.agony_states: Dict[str, Dict[str, float]] = {}

        # Torpedo State
        self.torp_launch_time = 0.0
        self.torp_next_wave = 0.0

        # Bomb State
        self.bomb_enemy_carried = False
        self.bomb_ally_carried = False
        self.bomb_pickup_time = 0.0
        self.bomb_respawn_time = 0.0  # Enemy bomb respawn
        self.bomb_ally_respawn_time = 0.0 # Ally bomb respawn
        
        # Bomb Stability
        self.bomb_ally_last_seen = 0.0
        self.bomb_enemy_last_seen = 0.0
        self.BOMB_GRACE_PERIOD = 2.0

        # Create Scan Lock
        self.scan_lock = threading.Lock()
        
        # Capture State (Timestamps of last sound play to throttle)
        self.last_capture_sound: Dict[str, float] = {}
        self.capture_start_times: Dict[str, float] = {} # Track when white color started

        # Visibility Logic
        self.master_overlay_enabled = tk.BooleanVar(value=True) # User switch
        self.match_active_signal = False # Match start/end
        self.last_damage_time = 0.0 # Combat activity
        self._is_visible = False # Actual state
        
        # Backward compatibility for existing settings
        self.enable_overlay_var = self.master_overlay_enabled

        # Sound Queue
        self.sound_queue = queue.Queue()
        self._sound_thread = threading.Thread(target=self._sound_worker, daemon=True)
        self._sound_thread.start()

        # Overlay Position Defaults
        self.overlay_x = 100
        self.overlay_y = 100

        # Settings (Regions/Points)
        self.regions: Dict[str, Tuple[int,int,int,int]] = {}  # "ally_roster", "enemy_roster"
        self.points: Dict[str, Tuple[int,int]] = {} # "cmd", "shield", "weapon"
        self._load_settings()

        # Services
        self.tailer: Optional[LogTailer] = None
        self.overlay: Optional[OverlayWindow] = None
        self.scanner = ScreenScanner() 
        self._scan_thread: Optional[threading.Thread] = None
        
        # Assets
        self.assets_path = Path(__file__).parent / "assets"
        # Load assets in background
        def _load_assets():
            self.scanner.load_template("bomb_ally", self.assets_path / "Allied bomb logo.png")
            self.scanner.load_template("bomb_enemy", self.assets_path / "Enemy bomb logo.png")
        threading.Thread(target=_load_assets, daemon=True).start()

        # Focus State Tracking
        self._last_focus_state = None  # None, "game", or "other"

        # Match State
        self.match_is_conquest = False

        # Theme Colors (Matched to Combat Analysis)
        self.colors = {
            "bg": "#0b1224",
            "panel": "#111b33",
            "surface": "#16213f",
            "border": "#24365c",
            "accent": "#3de7ff",
            "accent_soft": "#7be8ff",
            "accent_dark": "#1b4f73",
            "text": "#e9f3ff",
            "muted": "#9bb3d6",
        }
        self.checkbox_imgs = {}

        # UI Elements
        self.agony_label: Optional[tk.Label] = None
        self.torp_label: Optional[tk.Label] = None
        self.bomb_ally_label: Optional[tk.Label] = None
        self.bomb_enemy_label: Optional[tk.Label] = None
        self.overlay_editing = False
        self.overlay_btn_text: Optional[tk.StringVar] = None
        
        self.debug_labels = {}
        self.region_labels = {}
        
        # Init Theme Resources
        self._ensure_check_images()

    def _ensure_check_images(self) -> None:
        if self.checkbox_imgs:
            return
        panel = self.colors["panel"]
        border = self.colors["border"]
        fill = self.colors["surface"]

        def make(on: bool) -> tk.PhotoImage:
            img = tk.PhotoImage(width=16, height=16)
            # Base fill skipped to allow transparency (shows button bg)
            # Inner box
            img.put(fill, to=(2, 2, 14, 14))
            # Border
            for x in range(0, 16):
                img.put(border, to=(x, 0))
                img.put(border, to=(x, 15))
            for y in range(0, 16):
                img.put(border, to=(0, y))
                img.put(border, to=(15, y))
            if on:
                # Simple X mark - White
                white = "#ffffff"
                for i in range(4, 12):
                    img.put(white, to=(i, i))
                    img.put(white, to=(i, 15 - i))
                    img.put(white, to=(i, i + 1))
                    img.put(white, to=(i, 14 - i))
            return img
            
        self.checkbox_imgs["off"] = make(False)
        self.checkbox_imgs["on"] = make(True)

    def _make_checkbox(self, parent, text: str, var: tk.Variable, command=None, bg_color=None) -> tk.Checkbutton:
        # Matches CombatAnalysisModule style
        if bg_color is None:
            bg_color = self.colors["panel"]
            
        chk = tk.Checkbutton(
            parent,
            text=text,
            variable=var,
            command=command,
            image=self.checkbox_imgs["off"],
            selectimage=self.checkbox_imgs["on"],
            compound="left",
            onvalue=True,
            offvalue=False,
            indicatoron=False,
            bd=0,
            relief="flat",
            highlightthickness=0,
            padx=4,
            pady=2,
            anchor="w",
            bg=bg_color,
            fg=self.colors["text"],
            activebackground=bg_color,
            activeforeground=self.colors["text"],
            selectcolor=bg_color,
            font=("Segoe UI", 9)
        )
        return chk

    def build(self, parent):
        self.frame = ttk.Frame(parent, style="App.TFrame")
        
        # --- Header ---
        controls = ttk.Frame(self.frame, style="Panel.TFrame", padding=10)
        controls.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(controls, text="Log File:", style="LabelMuted.TLabel").pack(side=tk.LEFT)
        ttk.Label(controls, textvariable=self.active_log_file_var, style="TLabel").pack(side=tk.LEFT, padx=(5, 20))
        
        ttk.Button(controls, text="Edit Overlay Pos", command=self._toggle_overlay_edit, style="TButton").pack(side=tk.RIGHT)
        
        self.overlay_btn_text = tk.StringVar(value=f"Overlay Master: {'ON' if self.master_overlay_enabled.get() else 'OFF'}")
        ttk.Button(controls, textvariable=self.overlay_btn_text, command=self._toggle_overlay_vis, style="TButton").pack(side=tk.RIGHT, padx=5)

        # --- Grid ---
        grid = ttk.Frame(self.frame, style="App.TFrame")
        grid.pack(fill=tk.BOTH, expand=True, padx=20)
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)
        # Two columns: Conquest, PvP

        # --- Group 1: Conquest ---
        # "Conquest: containing: Torpedo Timer, Bomb Tracker and System Capture"
        self.conquest_enabled = tk.BooleanVar(value=True)
        # We need a proper container that looks like a group.
        # But user wants "parts" to be in columns.
        
        col_conq = ttk.Frame(grid, style="App.TFrame")
        col_conq.grid(row=0, column=0, sticky="nsew", padx=10)
        
        # Header for Group
        h_conq = ttk.Frame(col_conq, style="App.TFrame")
        h_conq.pack(fill=tk.X, pady=(0, 5))
        self._make_checkbox(h_conq, "Conquest", self.conquest_enabled, 
            command=lambda: self._toggle_group("conquest"), bg_color=self.colors["bg"]).pack(side=tk.LEFT)
        
        # 1. Torpedoes (Inside Conquest)
        self._build_card(col_conq, 0, 0, "Torpedo Timer", self.enable_torp_var,
            "Tracks 'Spell_ClanShipTorpedo'.\nWave every 65.5s.", None, pack=True)

        # 2. Bomb Tracker
        b_card = self._build_card(col_conq, 0, 0, "Bomb Tracker", self.enable_bomb_var,
            "Visual tracking of bomb icons.\nRequires setup of team areas.",
            [("Set Ally Area", lambda: self._calibrate_region("ally_roster")),
             ("Set Enemy Area", lambda: self._calibrate_region("enemy_roster")),
             ("Show Areas", self._preview_regions)], # Added show areas button
             pack=True)
             
        # Add Region Labels (Append to b_card)
        r_frame = ttk.Frame(b_card, style="App.TFrame")
        r_frame.pack(fill=tk.X, pady=5)
        for key in ["ally_roster", "enemy_roster"]:
            lbl = ttk.Label(r_frame, text=f"{key.replace('_', ' ').capitalize()}: Not Set", style="LabelMuted.TLabel", font=("Consolas", 8))
            lbl.pack(anchor="w")
            self.region_labels[key] = lbl

        # 3. System Capture
        c_buttons = [("Set Command", lambda: self._calibrate_point("cmd")),
             ("Set Shield", lambda: self._calibrate_point("shield")),
             ("Set Weapon", lambda: self._calibrate_point("weapon")),
             ("Show Points", self._preview_points)] # Added show points button
             
        c_card = self._build_card(col_conq, 0, 0, "System Capture", self.enable_capture_var,
            "Pixel monitoring of Dreadnought systems.", c_buttons, pack=True)

        # Add Debug Labels (Append to c_card)
        curr_frame = ttk.Frame(c_card, style="App.TFrame")
        curr_frame.pack(fill=tk.X, pady=5)
        for key in ["cmd", "shield", "weapon"]:
            lbl = ttk.Label(curr_frame, text=f"{key.capitalize()}: -", style="LabelMuted.TLabel", font=("Consolas", 8))
            lbl.pack(anchor="w")
            self.debug_labels[key] = lbl
            
        # Initial UI Update
        self._update_region_labels()
        self._apply_debug_labels({})


        # --- Group 2: PvP ---
        # "PvP: containing: Agony buff"
        self.pvp_enabled = tk.BooleanVar(value=True)
        col_pvp = ttk.Frame(grid, style="App.TFrame")
        col_pvp.grid(row=0, column=1, sticky="nsew", padx=10)

        h_pvp = ttk.Frame(col_pvp, style="App.TFrame")
        h_pvp.pack(fill=tk.X, pady=(0, 5))
        self._make_checkbox(h_pvp, "PvP", self.pvp_enabled,
            command=lambda: self._toggle_group("pvp"), bg_color=self.colors["bg"]).pack(side=tk.LEFT)

        # 1. Agony
        agony_card = self._build_card(col_pvp, 0, 0, "Agony Buff", self.enable_agony_var, 
            "Tracks 'BuffNearDeath_big'.\nActive: 12s | CD: 25s",
            None, pack=True)
        self._render_agony_ui(agony_card)

        # Initialize Overlay
        if not self.overlay:
            self.overlay = OverlayWindow(self.app, x=self.overlay_x, y=self.overlay_y, on_move=self._on_overlay_move)
            self.overlay.set_target_position(self.overlay_x, self.overlay_y, apply=True)
            self._build_overlay_content()
            self._update_overlay_visibility()
            # Try to force a geometry update or resize hint if on different DPI?
            # self.overlay.update()
            # self.overlay.geometry(f"+{self.overlay_x}+{self.overlay_y}")

        # Services
        if not self.tailer:
            self.tailer = LogTailer(self.config.logs_path, self._on_log_lines)
            self.tailer.start()
            
        self._schedule_update()
        self._schedule_scan()
        
        # New Logic: Check current log file backwards for active match state
        # Delay slightly to ensure tailer has found file
        self.app.after(1000, self._check_match_state_from_log)

        return self.frame
    
    def _check_match_state_from_log(self):
        """
        Reads the current log file backwards to determine if we are in a match.
        Locates the last 'Start gameplay' or 'GAME END' event.
        """
        if not self.tailer or not self.tailer.current_file or not self.tailer.current_file.exists():
            # Retry if file not ready yet
            self.app.after(2000, self._check_match_state_from_log)
            return

        try:
            path = self.tailer.current_file
            is_conquest = False

            # Read a tail chunk (5 MB) to find the most recent boundary event.
            file_size = os.path.getsize(path)
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                seek_pos = max(0, file_size - 5 * 1024 * 1024)
                f.seek(seek_pos)
                lines = f.readlines()

                for line in reversed(lines):
                    # First boundary wins because we traverse from latest to oldest.
                    if (
                        GAME_END_RE.search(line)
                        or "Gameplay finished" in line
                        or "Session finished" in line
                        or "Quit application" in line
                    ):
                        self.match_active_signal = False
                        self.match_is_conquest = False
                        self.last_damage_time = 0.0
                        self._update_visibility_logic()
                        return

                    m_start = SESSION_START_RE.search(line)
                    if m_start or "Start gameplay" in line:
                        # Infer conquest from mode or explicit ClanShip marker.
                        mode = m_start.group("mode") if m_start else ""
                        is_conquest = "'ClanShip'" in line or mode == "ClanShip"

                        print("[DEBUG] Active match found in history!")
                        self.match_active_signal = True
                        self.match_is_conquest = is_conquest
                        self.last_damage_time = time.time()
                        self._update_visibility_logic()
                        return
        except Exception as e:
            print(f"Error checking log history: {e}")

    def _toggle_group(self, group):
        state = self.conquest_enabled.get() if group == "conquest" else self.pvp_enabled.get()
        if group == "conquest":
            self.enable_torp_var.set(state)
            self.enable_bomb_var.set(state)
            self.enable_capture_var.set(state)
        else:
            self.enable_agony_var.set(state)
        self._save_settings()

    def _build_card(self, parent, row, col, title, var, desc, buttons, pack=False):
        card = ttk.LabelFrame(parent, text=title, style="Card.TLabelframe", padding=10)
        # Support Packing instead of Grid for columns
        if pack:
            card.pack(fill=tk.X, pady=10, anchor="n")
        else:
            card.grid(row=row, column=col, sticky="nw", padx=10, pady=10)
        
        # Use custom checkbox style via _make_checkbox
        self._make_checkbox(card, "Enable", var, command=self._save_settings).pack(anchor="w")
        ttk.Label(card, text=desc, style="LabelMuted.TLabel", font=("Segoe UI", 9)).pack(anchor="w", pady=5)
        
        if buttons:
            btn_frame = ttk.Frame(card, style="App.TFrame")
            btn_frame.pack(fill=tk.X, pady=5)
            # Refactored button layout slightly to handle 4 buttons gracefully
            for i, (txt, cmd) in enumerate(buttons):
                btn = ttk.Button(btn_frame, text=txt, command=cmd, style="TButton")
                # Grid or Pack? Pack wraps badly. Grid is better if we know count.
                # Let's simple pack with wrap in mind? Or just allow horizontal scroll?
                # Actually, wrap frame if too many buttons.
                btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
                
        return card

    def _render_agony_ui(self, parent):
        # Frame for dynamic list
        f = ttk.Frame(parent, style="App.TFrame")
        f.pack(fill=tk.X, pady=5)
        self.agony_ui_frame = f
        
        # Render existing
        self._refresh_agony_ui()
        
        # Buttons (+/-)
        btn_frame = ttk.Frame(parent, style="App.TFrame")
        btn_frame.pack(fill=tk.X, pady=2)
        
        # Use a lambda that traces the save to ensure we save when adding/removing
        ttk.Button(btn_frame, text="+", command=self._add_agony_tracker, width=5).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="-", command=self._remove_agony_tracker, width=5).pack(side=tk.LEFT, padx=2)
        ttk.Label(btn_frame, text="Add Usernames", style="LabelMuted.TLabel").pack(side=tk.LEFT, padx=5)

    def _refresh_agony_ui(self):
        if not self.agony_ui_frame: return
        for w in self.agony_ui_frame.winfo_children(): w.destroy()
        
        for i, var in enumerate(self.agony_users_vars):
            row = ttk.Frame(self.agony_ui_frame, style="App.TFrame")
            row.pack(fill=tk.X, pady=2)
            ttk.Label(row, text=f"User {i+2}:", style="LabelMuted.TLabel", width=8).pack(side=tk.LEFT)
            e = ttk.Entry(row, textvariable=var)
            e.pack(side=tk.LEFT, fill=tk.X, expand=True)
            # Bind focus out to save? Or rely on explicit save elsewhere?
            # Since vars are bound, _save_settings reads them. 
            # But we need to trigger save when they type?
            # Usually we use a trace or binding.
            var.trace_add("write", lambda *args: self._save_settings())

    def _add_agony_tracker(self):
        self.agony_users_vars.append(tk.StringVar(value=""))
        self._refresh_agony_ui()
        self._save_settings()

    def _remove_agony_tracker(self):
        if self.agony_users_vars:
            self.agony_users_vars.pop()
            self._refresh_agony_ui()
            self._save_settings()

    def on_show(self):
        if self.tailer:
            self.tailer.update_root(self.config.logs_path)
            self.tailer.start()

    def on_hide(self):
        if self._scan_after_id:
            self.app.after_cancel(self._scan_after_id)
            self._scan_after_id = None
        
        if self._update_after_id:
            self.app.after_cancel(self._update_after_id)
            self._update_after_id = None
        
        self._save_settings()
        
        if self.tailer:
            self.tailer.stop()

        if self.overlay:
            self.overlay.destroy()
            self.overlay = None

    # --- Log Processing ---
    def _on_log_lines(self, lines: List[str]):
        self.app.after(0, self._process_lines, lines)

    def _process_lines(self, lines: List[str]):
        if self.tailer and self.tailer.current_file:
            # Include folder name and line count
            # Folder/Filename (Line X)
            folder = self.tailer.current_file.parent.name
            fname = self.tailer.current_file.name
            lc = self.tailer.line_count
            self.active_log_file_var.set(f"{folder}/{fname} (Line {lc})")
            
        current_username = self.config.username.lower()
        now = time.time()
        
        # Check for damage activity to keep overlay alive
        for line in lines:
            if DAMAGE_HEAL_RE.search(line):
                self.last_damage_time = now
                self._update_visibility_logic()

        for line in lines:
            # Match Start / Game Session Start
            # Reset/Start timers
            # User update: check for "Start gameplay"
            if "Start gameplay" in line:
                self.match_active_signal = True
                self.last_damage_time = now  # Treat match start as activity to avoid delayed show
                
                # Check for Conquest Mode (ClanShip)
                if "'ClanShip'" in line:
                    self.match_is_conquest = True
                    print("[DEBUG] Conquest Mode Detected (ClanShip)")
                else:
                    self.match_is_conquest = False
                
                self._update_visibility_logic()
                
                # User request: "Start timers for torpedos (norm interval) and both bombs (2 min)"
                # Modified: "reduce initial timer by 7s (torp) and 2s (bomb)"
                self.torp_launch_time = now
                self.torp_next_wave = now + 58.5 # 65.5 - 7
                
                # Both bombs spawn 2 min after start
                # Modified: "reduce by 2s" -> 118s
                self.bomb_respawn_time = now + 118.0
                self.bomb_ally_respawn_time = now + 118.0
                
                # Reset visual states
                self.bomb_enemy_carried = False
                self.bomb_ally_carried = False
                
            # Match End
            if GAME_END_RE.search(line):
                self.match_active_signal = False
                self.match_is_conquest = False # Reset
                self.agony_active_until = 0.0
                self.agony_cooldown_until = 0.0
                self.last_damage_time = 0.0
                self._update_visibility_logic()

            # Agony
            if self.enable_agony_var.get():
                m_apply = AURA_APPLY_RE.search(line) 
                
                if m_apply and m_apply.group("aura") == "BuffNearDeath_big":
                    target = _strip_id(m_apply.group("target")).lower()
                    
                    # 1. Check Main
                    if current_username and target == current_username:
                        self.agony_active_until = now + 12.0
                        self.agony_cooldown_until = now + 25.0
                    
                    # 2. Check Extras
                    for v in self.agony_users_vars:
                         val = v.get().strip()
                         if val and val.lower() == target:
                             self.agony_states[target] = {
                                 "active_until": now + 12.0,
                                 "cooldown_until": now + 25.0,
                                 "name": val
                             }

                m_cancel = AURA_CANCEL_RE.search(line)
                if m_cancel and m_cancel.group("aura") == "BuffNearDeath_big":
                    target = _strip_id(m_cancel.group("target")).lower()
                    
                    if current_username and target == current_username:
                        self.agony_active_until = 0.0
                        
                    if target in self.agony_states:
                        self.agony_states[target]["active_until"] = 0.0

            # Torpedoes
            if self.enable_torp_var.get():
                # Fix: Check for specific Cast event to avoid matching "Apply aura" or "Cancel aura" logic
                # which can happen seconds later and reset the timer.
                if "Spell 'Spell_ClanShipTorpedo'" in line:
                    # Debounce: Only set if last launch was > 15s ago
                    if (now - self.torp_launch_time) > 15.0: 
                        self.torp_launch_time = now
                        self.torp_next_wave = now + 65.5
                        self.overlay.show()
                        self._play_sound(SND_TORP)
                
            # Bomb (Log Fallback)
            if self.enable_bomb_var.get():
                # Check for various pick up messages
                # "Bomb taken by [Player]"
                # "Bomb dropped by [Player]"
                # "Bomb reset"
                # The user says "The bomb detection does not work".
                # If visuals fail, we rely on logs.
                # Common strings:
                # "The bomb has been taken by..." ?
                # "Bomb taken" ?
                # Let's try broader:
                if "Bomb" in line:
                    lower_line = line.lower()
                    if "taken" in lower_line or "picked up" in lower_line:
                        # Assuming enemy if we don't check name match yet
                        # But wait, if WE pick it up, we want Ally Carried.
                        # If THEY pick it up, we want Enemy Carried.
                        # "taken by <name>"
                        self._play_sound(SND_BOMB)
                        
                        # Determine team by name? 
                        # Hard without roster list.
                        # Simplified: Just set BOTH timers/warnings?? No.
                        # User said "bomb detection does not work" with visuals.
                        # Let's just trigger the timer reset whenever "taken".
                        # This at least gives a timer.
                        self.bomb_respawn_time = now + 120.0
                        self.bomb_ally_respawn_time = now + 120.0
                        
                        # Heuristic: If detecting player name logic was here...
                        # For now, just show CARRIED for Enemy as default "Panic" mode?
                        self.bomb_enemy_carried = True
                    elif "reset" in lower_line or "returned" in lower_line:
                        # Bomb returned
                        self.bomb_enemy_carried = False
                        self.bomb_ally_carried = False

    # --- Scanning & Visuals ---
    def _update_focus_debug(self):
        """Checks focus state and prints debug info only if state changes."""
        try:
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            if hwnd == 0:
                current_state = "unknown"
                current_window = "None"
            else:
                length = 256
                buff = ctypes.create_unicode_buffer(length)
                ctypes.windll.user32.GetClassNameW(hwnd, buff, length)
                current_window = buff.value
                
                if current_window == "game_main_window":
                    current_state = "game"
                else:
                    current_state = "other"
            
            # Print only on transition
            if self._last_focus_state != current_state:
                if current_state == "game":
                    print(f"[DEBUG] Game window FOCUSED ({current_window})")
                elif current_state == "other":
                     print(f"[DEBUG] Focus LOST. Current window: '{current_window}'")
                elif current_state == "unknown":
                     print(f"[DEBUG] Focus Unknown.")
                
                self._last_focus_state = current_state
                
        except Exception:
            pass

    def _schedule_scan(self):
        # Update focus debug regularly (outside thread to avoid print race conditions, though simple print is atomic enough)
        self._update_focus_debug()

        # We start a thread to run the scan logic, checking first if one is already running
        # This prevents UI Lag
        if not self.frame: return
        
        if self._scan_thread is None or not self._scan_thread.is_alive():
            # Capture variables in main thread (Tcl is not thread safe)
            bomb_on = self.enable_bomb_var.get()
            capture_on = self.enable_capture_var.get()
            
            self._scan_thread = threading.Thread(target=self._run_scan_thread, args=(bomb_on, capture_on), daemon=True)
            self._scan_thread.start()
            
        # Re-schedule check for thread completion or next run
        self._scan_after_id = self.app.after(500, self._schedule_scan)

    def _run_scan_thread(self, bomb_on, capture_on):
        # Heavy lifting here
        try:
            with self.scan_lock:
                 # Logic for features
                 if bomb_on:
                    self._scan_bombs()
                
                 if capture_on:
                     self._scan_capture()
                 else:
                     # Even if capture logic is disabled, if we have points set, we might want to update the debug labels 
                     # (show just coordinates) or do a passive scan?
                     # User asked for "detected color" to be displayed.
                     # If disabled, maybe we should still read the pixel ONLY for the UI if points are set?
                     # Let's check points.
                     if self.points:
                         # Minimal scan just for UI
                         debug_vals = {}
                         for name in ["cmd", "shield", "weapon"]:
                             if name in self.points:
                                 debug_vals[name] = self.scanner.get_pixel_color(*self.points[name])
                         self.app.after(0, self._apply_debug_labels, debug_vals)
        except Exception as e:
            print(f"[DEBUG] Error in scan thread: {e}")

    def _update_capture_debug(self):
        # This runs on main thread, quick check of LAST known values?
        # Or re-read? Re-reading is slow.
        # Let's just do the reading in the thread and pass data?
        # For now, simplistic: _update_capture_debug does the reading.
        # If user says window is lagging, we must move `get_pixel_color` calls too.
        
        # Let's move the logic into the thread, update SELF state, then here update UI.
        pass # Refactored into thread logic mostly
        
        # Quick hack: Only update debug labels if visible (user looking at settings)
        # But for now, let's keep it simple. If we move `_update_capture_debug` blindly it might still lag.
        # The main culprit is template matching loop (Python).
        
        # Refactoring `_update_capture_debug` to merely refresh UI if we can cache values.
        # Scanner cache?
        # Let's just read pixels in thread.
        pass

    def _has_multiple_bomb_icons(self, positions, min_distance: int = 10) -> bool:
        if not positions or len(positions) < 2:
            return False
        for i in range(len(positions)):
            for j in range(i + 1, len(positions)):
                dx = abs(positions[i][0] - positions[j][0])
                dy = abs(positions[i][1] - positions[j][1])
                if max(dx, dy) >= min_distance:
                    return True
        return False

    def _scan_bombs(self):
        # Runs in Thread
        
        # Only scan if we are reliably in a match to avoid lobby/hangar false positives
        if not self.match_active_signal:
            return
            
        now = time.time()

        def process_bomb(side: str, region_key: str, template_name: str, threshold: int, carried_attr: str, last_seen_attr: str, respawn_attr: str, play_sound: bool = False):
            if region_key not in self.regions:
                if int(now) % 10 == 0:
                    print(f"[DEBUG] '{region_key}' region not set, skipping {side} scan.")
                return

            matches = self.scanner.find_template(
                self.regions[region_key],
                template_name,
                threshold=threshold,
                return_positions=True,
                max_results=3,
            ) or []

            carried = getattr(self, carried_attr)
            respawn_time = getattr(self, respawn_attr)
            last_seen = getattr(self, last_seen_attr)

            if matches:
                if not carried:
                    print(f"[DEBUG] Bomb {side.upper()} detected (state change)")

                setattr(self, last_seen_attr, now)
                setattr(self, carried_attr, True)

                timer_active = now < respawn_time
                has_two_icons = self._has_multiple_bomb_icons(matches)

                should_start_timer = False
                if not carried:
                    # Only start a new timer if the previous one is not already running.
                    should_start_timer = not timer_active
                elif not timer_active and has_two_icons:
                    # Timer expired while the original bomb was still carried; a second icon means a new bomb spawned.
                    should_start_timer = True

                if should_start_timer:
                    setattr(self, respawn_attr, now + 120.0)
                    if play_sound:
                        self._play_sound(SND_BOMB)
            else:
                if (now - last_seen) > self.BOMB_GRACE_PERIOD:
                    if carried:
                        print(f"[DEBUG] Bomb {side.upper()} lost (grace period expired)")
                    setattr(self, carried_attr, False)

        process_bomb("ally", "ally_roster", "bomb_ally", 50, "bomb_ally_carried", "bomb_ally_last_seen", "bomb_ally_respawn_time", False)
        process_bomb("enemy", "enemy_roster", "bomb_enemy", 33, "bomb_enemy_carried", "bomb_enemy_last_seen", "bomb_respawn_time", True)

    def _scan_capture(self):
        # Runs in Thread
        # Check points for color change (Blue -> White/Gray)
        # Assuming Team Blue is friendly defaults. Capture means turning from Blue to White (neutralizing) or Red.
        
        debug_vals = {}
        now = time.time()
        
        for name, snd in [("cmd", SND_CAPT_CMD), ("shield", SND_CAPT_SHIELD), ("weapon", SND_CAPT_WEAPON)]:
            if name in self.points:
                pixel = self.scanner.get_pixel_color(*self.points[name])
                debug_vals[name] = pixel
                
                # Check if "White-ish" - High RGB
                # Or check if significantly different from "Normal Blue"
                # Simple heuristic: r > 200 and g > 200 and b > 200 (White)
                if pixel[0] > 200 and pixel[1] > 200 and pixel[2] > 200:
                    # White detected. Start timer if not running.
                    if name not in self.capture_start_times:
                        self.capture_start_times[name] = now
                    
                    # Check 2s Duration
                    if (now - self.capture_start_times[name]) >= 2.0:
                        # Trigger sound logic (cooldown handled inside _trigger_capture_sound)
                        self.app.after(0, self._trigger_capture_sound, name, snd)
                else:
                    # Not white - reset timer
                    if name in self.capture_start_times:
                        del self.capture_start_times[name]
                    
        # Update Debug UI safely
        self.app.after(0, self._apply_debug_labels, debug_vals)

    def _apply_debug_labels(self, vals):
        # Check global error state
        if self.scanner.last_error:
             lbl = self.debug_labels.get("cmd") # Hijack first label
             if lbl:
                 # ttk.Label does not support fg.
                 lbl.config(text=f"Error: {self.scanner.last_error}")
             return

        for key, lbl in self.debug_labels.items():
            if key in self.points:
                 x, y = self.points[key]
                 if key in vals:
                     # Detected color available
                     r, g, b = vals[key]
                     lbl.config(text=f"{key.capitalize()}: ({x}, {y}) - RGB({r}, {g}, {b})")
                 else:
                     # Coordinates set, but not scanning/active
                     lbl.config(text=f"{key.capitalize()}: ({x}, {y}) - Disabled/Not Scanning")
            else:
                lbl.config(text=f"{key.capitalize()}: Not Set")

    def _update_region_labels(self):
        for key, lbl in self.region_labels.items():
            if key in self.regions:
                r = self.regions[key]
                # rect: left, top, width, height
                lbl.config(text=f"{key.replace('_', ' ').capitalize()}: ({r[0]}, {r[1]}) {r[2]}x{r[3]}")
            else:
                lbl.config(text=f"{key.replace('_', ' ').capitalize()}: Not Set")

    def _trigger_capture_sound(self, name, filename):
        now = time.time()
        # Per-system cooldown check
        last = self.last_capture_sound.get(name, 0)
        if now - last > 20.0: # 20s cooldown
            self._play_sound(filename)
            self.last_capture_sound[name] = now

    def _is_game_foreground(self) -> bool:
        """Checks if the game window is currently in the foreground."""
        try:
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            if hwnd == 0:
                return False
            
            length = 256
            buff = ctypes.create_unicode_buffer(length)
            ctypes.windll.user32.GetClassNameW(hwnd, buff, length)
            current_class = buff.value
            
            # Check for Star Conflict window class "game_main_window"
            is_game = (current_class == "game_main_window")
            
            return is_game
        except Exception:
            return False

    def _sound_worker(self):
        while True:
            path_str = self.sound_queue.get()
            try:
                # Only play if game is focused
                if self._is_game_foreground():
                    import winsound
                    # SND_SYNC blocks, ensuring sequential playback
                    winsound.PlaySound(path_str, winsound.SND_SYNC | winsound.SND_FILENAME)
            except Exception:
                pass
            finally:
                self.sound_queue.task_done()

    def _play_sound(self, filename: str):
        path = Path(__file__).parent / "sounds" / filename
        if path.exists():
            self.sound_queue.put(str(path))

    # --- Overlay & UI ---
    def _schedule_update(self):
        if not self.frame: return
        
        self._update_visibility_logic()
        self._update_overlay_ui()
        self._update_after_id = self.app.after(100, self._schedule_update)

    def _update_visibility_logic(self):
        # Master Switch Check
        if not self.master_overlay_enabled.get():
             if self._is_visible:
                 self.overlay.hide() if self.overlay else None
                 self._is_visible = False
             return

        # If no match is active, keep overlay hidden to avoid flicker after match end.
        if not self.match_active_signal:
            if self._is_visible and self.overlay:
                self.overlay.hide()
            self._is_visible = False
            return

        # Logic Check
        # Show if (match started) OR (recent damage < 60s)
        # CRITICAL FIX: Even if match is "Active", we rely on log activity to decide if we are actually PLAYING.
        # But wait, user said "display message when program detects window is game".
        # This auto-hide request implies: "If I am afk in space (no damage) even in a match, maybe hide?"
        # The user's request: "auto hide works again, when no important log activity... is detected"
        # Since 'match_active_signal' stays True for the whole match 20mins+, this forces it ALWAYS on.
        # We need to qualify 'match_active_signal' with activity or just rely entirely on activity?
        # A compromise: If match_active_signal is True, we usually WANT it on.
        # But maybe the user means AFTER the match ends? 
        # Or maybe they specifically mean "If I haven't taken damage for X time, hide it".
        
        # User phrasing: "auto hide works again, when no important log activity ... is detected"
        # This suggests strictly time-based activity checking.
        
        now = time.time()
        
        # We treat 'match_active_signal' as a prerequisite, but activity as the trigger?
        # No, 'Start gameplay' IS a trigger.
        # Let's combine them: 
        # Visible IF: (Match Is Active) AND (Recent Activity < 60s)
        # But sitting in space waiting for bomb is idle. We don't want it to hide then.
        
        # Re-reading: "Wait for significant log activity... and check lines in reverse... until Start gameplay found"
        # The user seems to want the *Initial* appearance to be activity based.
        # But "auto hide" implies disappearing later.
        
        # Let's effectively change logic to:
        # Show IF: (Recent Damage < 60s)
        # The 'match_active_signal' is just state tracking.
        # However, we want it to show up when Bomb timer is running?
        # Let's stick to the user's specific text: "auto hide works again, when no important log activity"
        
        should_show = (now - self.last_damage_time < 60.0)
        
        if should_show and not self._is_visible:
             if self.overlay: self.overlay.show()
             self._is_visible = True
        elif not should_show and self._is_visible:
             if self.overlay: self.overlay.hide()
             self._is_visible = False

    def _update_overlay_ui(self):
        if not self.overlay or not self._is_visible:
            return
        if not self.overlay_editing:
            self.overlay.ensure_position()
            
        now = time.time()
        
        # Ensure multi lists exists
        if not hasattr(self, "agony_multi_labels"):
            self.agony_multi_labels = []

        # Unpack all to ensure strict order on repack
        self.agony_label.pack_forget()
        for l in self.agony_multi_labels:
            l.pack_forget()
        
        self.torp_label.pack_forget()
        self.bomb_ally_label.pack_forget()
        self.bomb_enemy_label.pack_forget()

        conquest_visible = False
        content_visible = False
        
        # 1. Agony
        if self.enable_agony_var.get() and self.match_active_signal:
            extras = [v.get().strip() for v in self.agony_users_vars if v.get().strip()]
            multi_mode = bool(extras)
            
            if not extras:
                # Single (Original) Mode
                self.agony_label.pack(anchor="w")
                content_visible = True
                if now < self.agony_active_until:
                    # Active -> Yellow
                    self.agony_label.config(text=f"Agony buff: ACTIVE {int(self.agony_active_until - now)}s", fg="#ffff33")
                elif now < self.agony_cooldown_until:
                    # CD -> Red
                    self.agony_label.config(text=f"Agony buff: CD {int(self.agony_cooldown_until - now)}s", fg="#ff3333")
                else:
                    # Ready -> Green
                    self.agony_label.config(text="Agony buff: READY", fg="#33ff33")
            else:
                # Multi User Mode
                self.agony_label.pack(anchor="w")
                content_visible = True
                self.agony_label.config(text="Agony buff:", fg="white")
                
                # Gather items
                items = []
                # Main
                main_name = self.config.username if self.config.username else "Main"
                items.append((main_name, self.agony_active_until, self.agony_cooldown_until))
                
                # Extras
                for name in extras:
                    state = self.agony_states.get(name.lower(), {})
                    items.append((name, state.get("active_until", 0.0), state.get("cooldown_until", 0.0)))
                
                # Ensure labels
                while len(self.agony_multi_labels) < len(items):
                    font_px = ("Segoe UI", -16, "bold")
                    l = tk.Label(self.overlay_left_frame, font=font_px, bg="black", fg="white")
                    self.agony_multi_labels.append(l)
                
                # Update
                for i, (name, active, cd) in enumerate(items):
                    lbl = self.agony_multi_labels[i]
                    lbl.pack(anchor="w", padx=(20, 0))
                    content_visible = True
                    
                    if now < active:
                        # Active -> Yellow
                        lbl.config(text=f"{name}: ACTIVE {int(active - now)}s", fg="#ffff33")
                    elif now < cd:
                        # CD -> Red
                        lbl.config(text=f"{name}: CD {int(cd - now)}s", fg="#ff3333")
                    else:
                        # Ready -> Green
                        lbl.config(text=f"{name}: READY", fg="#33ff33")
        else:
            multi_mode = False

        # 2. Torpedoes
        # Only show if enabled AND in Conquest mode (ClanShip)
        if self.enable_torp_var.get() and self.match_is_conquest:
            conquest_visible = True
            self.torp_label.pack(anchor="w")
            content_visible = True
            if now < self.torp_next_wave:
                rem = int(self.torp_next_wave - now)
                self.torp_label.config(text=f"Torpedos: {rem}s", fg="#ff8800")
            else:
                self.torp_label.config(text="Torpedos: READY", fg="#33ff33")

        # 3. Bombs
        # Only show if enabled AND in Conquest mode
        if self.enable_bomb_var.get() and self.match_is_conquest:
            conquest_visible = True
            self.bomb_ally_label.pack(anchor="w")
            self.bomb_enemy_label.pack(anchor="w")
            content_visible = True
            
            # Ally Bomb
            # Logic:
            # 1. Timer Active -> Show Timer (Red)
            # 2. Timer Finished -> Show Ready
            if now < self.bomb_ally_respawn_time:
                rem = int(self.bomb_ally_respawn_time - now)
                self.bomb_ally_label.config(text=f"Allied Bomb: {rem}s", fg="#ff3333")
            else:
                self.bomb_ally_label.config(text="Allied Bomb: READY", fg="#33ff33") # Green

            # Enemy Bomb
            # Logic:
            # 1. Timer Active -> Show Timer (Red)
            # 2. Timer Finished -> Show Ready
            if now < self.bomb_respawn_time:
                rem = int(self.bomb_respawn_time - now)
                self.bomb_enemy_label.config(text=f"Enemy Bomb: {rem}s", fg="#ff3333")
            else:
                self.bomb_enemy_label.config(text="Enemy Bomb: READY", fg="#33ff33")

        # If nothing is visible, hide immediately to avoid an empty black box lingering after matches
        if not content_visible:
            if self._is_visible and self.overlay:
                self.overlay.hide()
                self._is_visible = False
            return

        self._layout_overlay_frames(multi_mode, conquest_visible)

    def _build_overlay_content(self):
        if not self.overlay: return
        for w in self.overlay.container.winfo_children(): w.destroy()
        
        # Reset multi-label cache since we destroyed the window content
        self.agony_multi_labels = []

        # Two-column capable layout
        self.overlay.container.grid_columnconfigure(0, weight=1)
        self.overlay.container.grid_columnconfigure(1, weight=1)

        self.overlay_left_frame = tk.Frame(self.overlay.container, bg="black")
        self.overlay_right_frame = tk.Frame(self.overlay.container, bg="black")

        # Use pixel-sized fonts (negative size) so text doesn't rescale with DPI moves
        font_px = ("Segoe UI", -16, "bold")
        self.agony_label = tk.Label(self.overlay_left_frame, text="Agony buff: READY", font=font_px, bg="black", fg="white")
        self.torp_label = tk.Label(self.overlay_right_frame, text="Torpedos: READY", font=font_px, bg="black", fg="white")
        self.bomb_ally_label = tk.Label(self.overlay_right_frame, text="Allied Bomb: READY", font=font_px, bg="black", fg="white")
        self.bomb_enemy_label = tk.Label(self.overlay_right_frame, text="Enemy Bomb: READY", font=font_px, bg="black", fg="white")

    def _layout_overlay_frames(self, multi_mode: bool, show_conquest: bool):
        if not self.overlay:
            return

        # Reset geometry before re-applying
        if hasattr(self, "overlay_left_frame"):
            self.overlay_left_frame.grid_forget()
        if hasattr(self, "overlay_right_frame"):
            self.overlay_right_frame.grid_forget()

        if not hasattr(self, "overlay_left_frame") or not hasattr(self, "overlay_right_frame"):
            return

        if multi_mode and show_conquest:
            self.overlay_left_frame.grid(row=0, column=0, sticky="nw")
            self.overlay_right_frame.grid(row=0, column=1, sticky="nw", padx=(16, 0))
        else:
            self.overlay_left_frame.grid(row=0, column=0, sticky="nw")
            if show_conquest:
                self.overlay_right_frame.grid(row=1, column=0, sticky="nw", pady=(8, 0))

    def _toggle_overlay_vis(self):
        # Just toggle the master switch. Logic handles the rest.
        new_val = not self.master_overlay_enabled.get()
        self.master_overlay_enabled.set(new_val)
        if self.overlay_btn_text:
             self.overlay_btn_text.set(f"Overlay Master: {'ON' if new_val else 'OFF'}")
        self._update_visibility_logic() # Apply immediately
        self._save_settings()

    def _update_overlay_visibility(self):
        # Deprecated: Logic now inside _update_visibility_logic
        self._update_visibility_logic()

    def _on_overlay_move(self, x: int, y: int):
        if not self.overlay_editing:
            return
        self.overlay_x = x
        self.overlay_y = y
        if self.overlay:
            self.overlay.set_target_position(x, y)
        self._save_settings()

    def _toggle_overlay_edit(self):
        if self.overlay:
            mode = not getattr(self.overlay, "_is_editing", False)
            self.overlay.toggle_edit_mode(mode)
            self.overlay._is_editing = mode
            self.overlay_editing = mode
            if not mode:
                # Persist final position when leaving edit mode
                pos = self.overlay.get_physical_position()
                self.overlay_x, self.overlay_y = pos
                self.overlay.set_target_position(self.overlay_x, self.overlay_y)
                self._save_settings()
            if mode: self.overlay.show() 

    # --- Calibration ---
    def _calibrate_region(self, name: str):
        def cb(rect):
            self.regions[name] = rect
            self._save_settings()
            self._update_region_labels()
            messagebox.showinfo("Calibration", f"Region '{name}' set.")
        
        CalibrationOverlay(self.app, cb, selection_type="region")

    def _calibrate_point(self, name: str):
        def cb(rect):
            self.points[name] = (rect[0], rect[1])
            self._save_settings()
            # Refresh debug labels immediately
            self.app.after(0, self._apply_debug_labels, {})
            messagebox.showinfo("Calibration", f"Point '{name}' set.")
        
        CalibrationOverlay(self.app, cb, selection_type="point")

    def _preview_regions(self):
        """Show colored boxes for set regions temporarily"""
        self._show_preview_overlay(regions=self.regions)

    def _preview_points(self):
        """Show colored dots for set points temporarily"""
        self._show_preview_overlay(points=self.points)

    def _show_preview_overlay(self, regions=None, points=None):
        if not regions and not points:
             return
             
        # Create non-interactive transparent overlay
        win = tk.Toplevel(self.app)
        win.attributes("-alpha", 0.5)
        win.attributes("-topmost", True)
        win.attributes("-fullscreen", True)
        win.attributes("-transparentcolor", "black") # Windows only
        win.configure(bg="black")
        
        canvas = tk.Canvas(win, bg="black", highlightthickness=0)
        canvas.pack(fill=tk.BOTH, expand=True)

        if regions:
            for name, r in regions.items():
                # r = (x, y, w, h)
                # Tkinter canvas coords need conversion if stored as physical?
                # Actually, our CalibrationOverlay returns physical coords.
                # If we draw on fullscreen window, we need logic coords OR handle DPI.
                # Since we turned OFF scaling for app probably, or handling it manually.
                # Let's try drawing text + rect.
                
                # We need to map Physical -> Logical if Tkinter is scaled.
                # But earlier we found Tkinter coordinates in 'self.regions' are from 'GetCursorPos' (Physical).
                # To draw on Tkinter Canvas which *is* scaled, we might have issues.
                # BUT, if we create a canvas on a fullscreen window, Tkinter maps it to what it thinks is the screen.
                # It is safer to use the 'CalibrationOverlay' approach using ctypes logic or valid geometry.
                
                # Simplified: Just draw. If inaccurate, user will see offset (which serves as a calibration check too!)
                
                # Color code
                color = "#33ff33" if "ally" in name else "#ff3333"
                
                canvas.create_rectangle(r[0], r[1], r[0]+r[2], r[1]+r[3], outline=color, width=3)
                canvas.create_text(r[0], r[1]-10, text=name, fill=color, anchor="sw", font=("Consolas", 14, "bold"))

        if points:
            for name, (x, y) in points.items():
                color = "#3de7ff"
                r = 5
                canvas.create_oval(x-r, y-r, x+r, y+r, fill=color, outline=color)
                canvas.create_text(x+10, y, text=name, fill=color, anchor="w", font=("Consolas", 12, "bold"))

        # Auto-close
        win.after(10000, win.destroy)
        
        # Click to close
        canvas.bind("<Button-1>", lambda e: win.destroy())

    # --- Settings ---
    def _load_settings(self):
        if self.settings_file.exists():
            try:
                data = json.loads(self.settings_file.read_text())
                self.regions = {k: tuple(v) for k,v in data.get("regions", {}).items()}
                self.points = {k: tuple(v) for k,v in data.get("points", {}).items()}
                
                # Agony Users
                ag_users = data.get("agony_users", [])
                self.agony_users_vars = [tk.StringVar(value=u) for u in ag_users]
                
                self.enable_agony_var.set(data.get("agony", False))
                self.enable_bomb_var.set(data.get("bomb", False))
                self.enable_torp_var.set(data.get("torp", False))
                self.enable_capture_var.set(data.get("capture", False))
                self.enable_overlay_var.set(data.get("overlay", True))
                
                # Load Position
                pos = data.get("overlay_pos", [100, 100])
                self.overlay_x, self.overlay_y = pos[0], pos[1]
            except Exception:
                pass

    def _save_settings(self):
        # Update current pos if overlay exists and user is editing
        if self.overlay and self.overlay_editing:
            pos_x, pos_y = self.overlay.get_physical_position()
            self.overlay_x = pos_x
            self.overlay_y = pos_y
            self.overlay.set_target_position(self.overlay_x, self.overlay_y)
            
        data = {
            "regions": self.regions,
            "points": self.points,
            "agony": self.enable_agony_var.get(),
            "agony_users": [v.get() for v in self.agony_users_vars],
            "bomb": self.enable_bomb_var.get(),
            "torp": self.enable_torp_var.get(),
            "capture": self.enable_capture_var.get(),
            "overlay": self.enable_overlay_var.get(),
            "overlay_pos": [self.overlay_x, self.overlay_y]
        }
        self.settings_file.write_text(json.dumps(data, indent=2))
