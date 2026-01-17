import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import concurrent.futures
import os
import pickle
import re
import math
import hashlib
import json
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from ...config import AppConfig
from ..base import BaseModule
from . import parser
from .display_names import DisplayNameManager


class CombatModule(BaseModule):
    name = "Combat Analyzer"
    description = (
        "Analyze Star Conflict combat.log files, split fights, and compare participant stats."
    )

    def __init__(self, app, config: AppConfig):
        self.app = app
        self.config = config
        self.frame: Optional[ttk.Frame] = None
        self.username_var = tk.StringVar(value=config.username)
        self.username_var.trace_add("write", lambda *_: self._persist_username())
        self.logs_path_var = tk.StringVar(value=config.logs_path)
        self.single_log_path: Optional[Path] = None
        self.log_scope_var = tk.StringVar(value="All logs in folder")
        self.fights: List[parser.Fight] = []
        self.all_fights: List[parser.Fight] = []
        self.selected_fight: Optional[parser.Fight] = None
        self.fight_var = tk.StringVar()
        self.game_mode_vars: Dict[str, tk.BooleanVar] = {}
        self.game_mode_popup: Optional[tk.Toplevel] = None
        self.status_var = tk.StringVar(value="Ready")
        self.progress: Optional[ttk.Progressbar] = None
        self.file_progress: Optional[ttk.Progressbar] = None
        self.loading = False
        self.reload_btn: Optional[ttk.Button] = None
        self.analyze_btn: Optional[ttk.Button] = None
        self.clear_cache_btn: Optional[ttk.Button] = None
        self.display_names_btn: Optional[ttk.Button] = None
        self._display_names_window: Optional[tk.Toplevel] = None
        self.show_all_logs_btn: Optional[ttk.Button] = None
        
        # Loading overlay state
        self.loading = False
        self._cancel_loading = False

        self.current_file_path: Optional[Path] = None
        self.team_frames: Dict[str, ttk.Frame] = {}
        self.sort_by_var = tk.StringVar(value="Damage dealt")
        self.sort_order_var = tk.StringVar(value="Descending")
        self.teams_canvas: Optional[tk.Canvas] = None
        self.teams_inner: Optional[ttk.Frame] = None
        self.fight_cache: Dict[str, Tuple[float, int, int, List[parser.Fight]]] = {}
        self.fight_cache_version = 9
        self.cache_file = Path(__file__).parent / "combat_cache.pkl"
        self._cache_lock = threading.Lock()
        self.player_check_cache: Dict[str, bool] = {}
        self._current_check_id = 0
        self.verifying_players = False
        self.tree_sort_states: Dict[ttk.Treeview, Tuple[str, bool]] = {}
        self.tree_sort_types: Dict[ttk.Treeview, Dict[str, str]] = {}
        self.tree_heading_labels: Dict[ttk.Treeview, Dict[str, str]] = {}
        self.stats_cache: Dict[str, Dict[str, parser.ParticipantStats]] = {}
        self.entity_profile_cache: Dict[str, Dict[str, Dict[str, Set[str]]]] = {}
        self.checkbox_imgs: Optional[Dict[str, tk.PhotoImage]] = None
        self.notebook: Optional[ttk.Notebook] = None
        self.teams_tab: Optional[ttk.Frame] = None
        self.pie_tab: Optional[ttk.Frame] = None
        self.pie_canvas: Optional[tk.Canvas] = None
        self.pie_details_frame: Optional[ttk.Frame] = None
        self.pie_stat_var = tk.StringVar(value="Damage dealt")
        self.pie_team_a_var = tk.BooleanVar(value=True)
        self.pie_team_b_var = tk.BooleanVar(value=True)
        self.pie_include_self_heal_var = tk.BooleanVar(value=True)
        self.pie_outgoing_mode_var = tk.StringVar(value="target")
        self.pie_selected_wedge: Optional[str] = None  # Name of the selected participant
        self.pie_data: List[dict] = [] # Store pie chart data for hit testing
        self.pie_details_header: Optional[ttk.Label] = None
        self.pie_details_tree_dmg: Optional[ttk.Treeview] = None
        self.pie_details_tree_heal: Optional[ttk.Treeview] = None
        self.pie_details_tree_recv: Optional[ttk.Treeview] = None
        self.pie_details_tree_heal_recv: Optional[ttk.Treeview] = None
        self.display_name_manager = DisplayNameManager(Path(__file__).parent)
        self.pie_sources_section: Optional[ttk.Frame] = None
        self.pie_sources_toggle_btn: Optional[ttk.Button] = None
        self.pie_sources_collapsed = True
        self._initial_popup_shown = False
        self._initial_popup_pending = False
        self._initial_popup: Optional[tk.Toplevel] = None
        
        # Persistent color cache for players
        self.player_color_cache: Dict[str, str] = {}
        self.pie_palette = [
            "#3de7ff", "#ff3d3d", "#ffff3d", "#ff3dff",
            "#ff9b3d", "#3d3dff", "#9b3dff", "#ff3d9b",
            "#d6ff3d", "#3dd6ff", "#ff5c5c", "#ffff5c",
            "#5c5cff", "#ff853d", "#ce3dff", "#ff3d66",
        ]
        
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
        self._theme_ready = False
        self._cancel_loading = False
        self._current_load_id = 0
        
        # Load cache in background to speed up startup
        threading.Thread(target=self._load_fight_cache, daemon=True).start()
        
        self.fight_box: Optional[ttk.Combobox] = None
        self._app_visibility_bound = False
        self._loading_overlay: Optional[ttk.Frame] = None
        self._overlay_progress: Optional[ttk.Progressbar] = None
        self._overlay_label_var = tk.StringVar(value="")
        self._overlay_sublabel_var = tk.StringVar(value="")

        self.GAME_MODE_MAP = {
            "FreeSpace": "Open Space",
            "ClanShip": "Conquest",
            "BombTheBase": "Detonation",
            "TeamDeathMatch": "Team Battle",
            "CaptureTheBase": "Beacon capture",
            "CaptureTheBase2": "Four lives",
            "Control": "Domination",
            "KingOfTheHill": "Beacon Hunt",
            "Sentinel": "Combat Recon",
            "GreedyTeamDeathMatch": "Survival",
        }

    def _open_settings_dialog(self):
        win = tk.Toplevel(self.app)
        win.title("Combat Analysis Settings")
        win.configure(bg=self.colors["bg"])
        win.resizable(False, False)
        
        # Center the window
        w, h = 500, 300
        x = self.app.winfo_x() + (self.app.winfo_width() // 2) - (w // 2)
        y = self.app.winfo_y() + (self.app.winfo_height() // 2) - (h // 2)
        win.geometry(f"{w}x{h}+{x}+{y}")
        
        container = ttk.Frame(win, style="App.TFrame", padding=20)
        container.pack(fill=tk.BOTH, expand=True)
        
        # Username
        ttk.Label(container, text="Username:", style="LabelMuted.TLabel").grid(row=0, column=0, sticky="w", pady=10)
        user_entry = ttk.Entry(container, textvariable=self.username_var, width=30, style="Futuristic.TEntry")
        user_entry.grid(row=0, column=1, sticky="w", padx=10, pady=10)
        
        # Logs Path
        ttk.Label(container, text="Logs path:", style="LabelMuted.TLabel").grid(row=1, column=0, sticky="w", pady=10)
        path_frame = ttk.Frame(container, style="App.TFrame")
        path_frame.grid(row=1, column=1, sticky="ew", padx=10, pady=10)
        
        log_entry = ttk.Entry(path_frame, textvariable=self.logs_path_var, style="Futuristic.TEntry")
        log_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(path_frame, text="...", width=3, command=self._browse_logs_path, style="TButton").pack(side=tk.LEFT, padx=(5, 0))
        
        # Actions
        ttk.Separator(container, orient=tk.HORIZONTAL).grid(row=2, column=0, columnspan=2, sticky="ew", pady=20)
        
        actions = ttk.Frame(container, style="App.TFrame")
        actions.grid(row=3, column=0, columnspan=2, sticky="ew")
        
        ttk.Button(actions, text="Display Names", command=self._open_display_name_editor, style="TButton").pack(side=tk.LEFT, padx=5)
        ttk.Button(actions, text="Debug Lines", command=self._show_fight_lines_debug, style="TButton").pack(side=tk.LEFT, padx=5)
        
        ttk.Button(actions, text="Close", command=win.destroy, style="Accent.TButton").pack(side=tk.RIGHT)

    def build(self, parent):
        self._init_theme()
        self.frame = ttk.Frame(parent, style="App.TFrame")

        # Top Control Bar
        top_bar = ttk.Frame(self.frame, padding=10, style="Panel.TFrame")
        top_bar.pack(fill=tk.X)
        
        # Left side: Fight Selector + Buttons
        # Fight Selector
        ttk.Label(top_bar, text="Select fight:", style="LabelMuted.TLabel").pack(side=tk.LEFT, padx=(0, 4))
        fight_box = ttk.Combobox(top_bar, textvariable=self.fight_var, state="readonly", width=40, style="Futuristic.TCombobox")
        fight_box.pack(side=tk.LEFT, padx=(0, 8))
        fight_box.bind("<<ComboboxSelected>>", lambda _e: self._on_fight_change())
        self.fight_box = fight_box
        
        # Game Modes
        self.game_mode_btn = ttk.Button(top_bar, text="Modes", command=self._toggle_game_mode_menu, style="TButton", width=6)
        self.game_mode_btn.pack(side=tk.LEFT, padx=2)
        
        ttk.Separator(top_bar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)

        # Buttons
        self.reload_btn = ttk.Button(top_bar, text="↻", width=3, command=self._reload_fights, style="Accent.TButton")
        self.reload_btn.pack(side=tk.LEFT, padx=2)

        self.analyze_btn = ttk.Button(top_bar, text="Analyze All", command=self._analyze_all_fights, style="Accent.TButton")
        self.analyze_btn.pack(side=tk.LEFT, padx=2)
        
        self.clear_cache_btn = ttk.Button(top_bar, text="Clear Cache", command=self._clear_all_caches, style="TButton")
        self.clear_cache_btn.pack(side=tk.LEFT, padx=2)

        ttk.Button(top_bar, text="Open File", command=self._open_log_file, style="TButton").pack(side=tk.LEFT, padx=2)
        self.show_all_logs_btn = ttk.Button(top_bar, text="All Logs", command=self._show_all_logs, style="TButton")
        self.show_all_logs_btn.pack(side=tk.LEFT, padx=2)

        # Right side: Settings Cog
        ttk.Button(top_bar, text="⚙", width=3, command=self._open_settings_dialog, style="TButton").pack(side=tk.RIGHT, padx=4)

        # Scope label
        ttk.Label(top_bar, textvariable=self.log_scope_var, style="LabelMuted.TLabel").pack(side=tk.RIGHT, padx=10)

        # Sort controls (Only for Teams tab)
        # Moved to Teams tab as requested
        self.sort_bar_frame = None # Placeholder if needed elsewhere

        # Notebook with Teams
        self.notebook = ttk.Notebook(self.frame, style="App.TNotebook")
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Pie tab
        self._build_pie_tab()

        # Teams tab
        teams_tab = ttk.Frame(self.notebook, style="App.TFrame")
        self.notebook.add(teams_tab, text="Teams")
        self.teams_tab = teams_tab

        # Sort Bar inside Teams Tab
        sort_bar = ttk.Frame(teams_tab, padding=(10, 10, 10, 6), style="Panel.TFrame")
        sort_bar.pack(fill=tk.X)
        ttk.Label(sort_bar, text="Sort by:", style="LabelMuted.TLabel").pack(side=tk.LEFT)
        sort_options = ["Damage dealt", "Damage taken", "Healing", "Self-heal"]
        sort_box = ttk.Combobox(
            sort_bar,
            textvariable=self.sort_by_var,
            state="readonly",
            values=sort_options,
            width=15,
            style="Futuristic.TCombobox",
        )
        sort_box.pack(side=tk.LEFT, padx=(4, 12))
        sort_box.bind("<<ComboboxSelected>>", lambda _e: self._on_sort_change())

        ttk.Label(sort_bar, text="Order:", style="LabelMuted.TLabel").pack(side=tk.LEFT)
        order_box = ttk.Combobox(
            sort_bar,
            textvariable=self.sort_order_var,
            state="readonly",
            values=["Descending", "Ascending"],
            width=12,
            style="Futuristic.TCombobox",
        )
        order_box.pack(side=tk.LEFT, padx=4)
        order_box.bind("<<ComboboxSelected>>", lambda _e: self._on_sort_change())

        teams_outer = ttk.Frame(teams_tab, padding=4, style="App.TFrame")
        teams_outer.pack(fill=tk.BOTH, expand=True)
        canvas = tk.Canvas(teams_outer, highlightthickness=0, bg=self.colors["bg"], bd=0)
        vsb = ttk.Scrollbar(teams_outer, orient=tk.VERTICAL, command=canvas.yview, style="Futuristic.Vertical.TScrollbar")
        canvas.configure(yscrollcommand=vsb.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self._enable_mousewheel_scroll(canvas)

        inner = ttk.Frame(canvas, style="App.TFrame")
        window_id = canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda _e, c=canvas: c.configure(scrollregion=c.bbox("all")))
        canvas.bind("<Configure>", lambda e, c=canvas, win=window_id: c.itemconfig(win, width=e.width))
        self.teams_canvas = canvas
        self.teams_inner = inner

        inner.columnconfigure(0, weight=1)
        inner.columnconfigure(1, weight=1)
        self.team_frames = {
            "A": self._build_team_column(inner, column=0),
            "B": self._build_team_column(inner, column=1),
        }

        # Default to Pie tab
        if self.pie_tab:
            self.notebook.select(self.pie_tab)
        else:
            self.notebook.select(self.teams_tab)

        # Status / progress (popup will show detailed progress; keep inline status text)
        status_bar = ttk.Frame(self.frame, padding=(10, 0, 10, 10), style="Panel.TFrame")
        status_bar.pack(fill=tk.X)
        ttk.Label(status_bar, textvariable=self.status_var, style="LabelMuted.TLabel").pack(side=tk.LEFT)

        self._update_log_scope_ui()
        return self.frame

    def on_show(self):
        # Initial popup logic removed as part of overlay refactor
        # Just Trigger reload
        self._reload_fights()

    def _browse_logs_path(self):
        path = filedialog.askdirectory(initialdir=self.logs_path_var.get() or str(Path.home()))
        if path:
            self.logs_path_var.set(path)
            self.config.logs_path = path
            self.config.save()
            self._reload_fights()

    def _open_log_file(self):
        if self.loading:
            return
        initial = self.single_log_path.parent if self.single_log_path else Path(self.logs_path_var.get() or Path.home())
        initial_dir = initial if initial.exists() else Path.home()
        file_path = filedialog.askopenfilename(
            initialdir=str(initial_dir),
            filetypes=[("Combat logs", "*.log"), ("All files", "*.*")],
        )
        if not file_path:
            return
        path = Path(file_path)
        if not path.exists():
            messagebox.showwarning("Missing file", f"File not found: {path}")
            return
        self.single_log_path = path
        self._update_log_scope_ui()
        self._reload_fights(forced_logs=[path])

    def _show_all_logs(self):
        if self.loading:
            return
        if not self.single_log_path:
            return
        self.single_log_path = None
        self._update_log_scope_ui()
        self._reload_fights()

    def _update_log_scope_ui(self):
        if self.single_log_path:
            self.log_scope_var.set(f"Single log: {self.single_log_path.name}")
            if self.show_all_logs_btn:
                self.show_all_logs_btn.state(["!disabled"])
        else:
            self.log_scope_var.set("All logs in folder")
            if self.show_all_logs_btn:
                self.show_all_logs_btn.state(["disabled"])

    def _show_fight_lines_debug(self):
        fight = self.selected_fight
        if not fight:
            messagebox.showinfo("Debug Lines", "Select a fight first.")
            return
        lines = self._extract_fight_lines(fight)
        top = tk.Toplevel(self.frame)
        top.title(f"Debug Lines - {fight.file_path.name}")
        top.geometry("900x600")
        top.configure(bg=self.colors["bg"])
        self._center_window(top, 900, 600)

        header = ttk.Frame(top, padding=8, style="Panel.TFrame")
        header.pack(fill=tk.X)
        ttk.Label(header, text=f"Lines for fight {fight.id} (matching time window)", style="Section.TLabel").pack(anchor=tk.W)
        ttk.Label(header, text=f"Total: {len(lines)}", style="LabelMuted.TLabel").pack(anchor=tk.W)

        body = ttk.Frame(top, padding=4, style="Panel.TFrame")
        body.pack(fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(body, orient=tk.VERTICAL, style="Futuristic.Vertical.TScrollbar")
        text = tk.Text(body, wrap="none", bg=self.colors["bg"], fg=self.colors["text"], insertbackground=self.colors["accent"], relief="flat")
        text.configure(font=("Consolas", 10))
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=text.yview)

        if lines:
            text.insert("1.0", "\n".join(lines))
        else:
            text.insert("1.0", "No lines matched the fight time window.")
        text.configure(state="disabled")

    def _extract_fight_lines(self, fight: parser.Fight) -> List[str]:
        """Return log lines whose timestamps fall inside the fight start/end window."""
        if not fight.file_path.exists():
            return []
        try:
            raw_lines = fight.file_path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except Exception:
            return []

        # Add a small padding to include session banners or trailing lines near the edges
        pad = timedelta(seconds=2)
        start_ts = (fight.start - pad) if fight.start else None
        end_ts = (fight.end + pad) if fight.end else None
        folder_hint = fight.file_path.parent.name

        results: List[str] = []
        for line in raw_lines:
            m = parser.TIME_RE.search(line)
            if not m:
                continue
            ts = parser._parse_timestamp(m.group("time"), folder_hint)  # type: ignore[attr-defined]
            if not ts or not start_ts or not end_ts:
                continue
            if start_ts <= ts <= end_ts:
                results.append(line)
        return results

    def _clear_all_caches(self):
        if not messagebox.askyesno("Clear Cache", "Are you sure you want to clear all caches?\nThis will force a re-analysis of all logs and re-verification of players."):
            return
            
        # Clear in-memory caches
        self.fight_cache.clear()
        self.stats_cache.clear()
        self.entity_profile_cache.clear()
        self.player_check_cache.clear()
        
        # Clear disk cache
        try:
            if self.cache_file.exists():
                os.remove(self.cache_file)
        except Exception as e:
            print(f"Error deleting cache file: {e}")
            
        # Reload
        self._reload_fights()

    def _analyze_all_fights(self) -> None:
        if self.loading or self.verifying_players:
            messagebox.showinfo("Analyze All", "Please wait for the current task to finish before analyzing all fights.")
            return

        if not self.all_fights:
            messagebox.showinfo("Analyze All", "Load combat logs first.")
            return

        unknown_names: Set[str] = set()
        for fight in self.all_fights:
            cache_key = f"{fight.file_path}::{fight.id}"
            stats = self.stats_cache.get(cache_key)
            if stats is None:
                stats = parser.aggregate_stats(fight)
                self.stats_cache[cache_key] = stats
            for name in stats.keys():
                cleaned = (name or "").strip()
                if not cleaned or cleaned.upper() == "N/A":
                    continue
                if cleaned in self.player_check_cache:
                    continue
                unknown_names.add(cleaned)

        if not unknown_names:
            messagebox.showinfo("Analyze All", "All fight participants are already cached.")
            return

        names_list = sorted(unknown_names)
        self._cancel_loading = False
        self._current_check_id += 1
        check_id = self._current_check_id
        self.verifying_players = True

        self._set_busy(True, "Analyzing all fights...")
        if self._overlay_progress:
            self._overlay_progress.stop()
            self._overlay_progress.configure(mode="determinate", maximum=len(names_list), value=0)
        self._overlay_label_var.set("Analyzing all fights...")
        self._overlay_sublabel_var.set("Preparing API checks")
        self.app.update_idletasks()

        threading.Thread(target=self._check_players_background, args=(names_list, check_id), daemon=True).start()

    def _reload_fights(self, forced_logs: Optional[List[Path]] = None):
        if self.loading:
            return
            
        # Invalidate any running player check
        self._current_check_id += 1
        self.verifying_players = False
        
        logs_override: Optional[List[Path]] = None
        if forced_logs is not None:
            logs_override = [Path(p) for p in forced_logs]
        elif self.single_log_path:
            logs_override = [self.single_log_path]

        if logs_override is not None:
            logs = [p for p in logs_override if p.exists()]
            if not logs:
                messagebox.showwarning("Missing file", "The selected log file could not be found.")
                self.single_log_path = None
                self._update_log_scope_ui()
                return
        else:
            # We defer the finding of logs to the background thread to avoid freezing UI
            logs = None

        self._set_busy(True, "Loading fights...")
        self._cancel_loading = False
        self._current_load_id += 1
        load_id = self._current_load_id
        
        # Capture current logs path from UI var safely
        current_logs_path_str = self.logs_path_var.get()

        def worker():
            import time
            try:
                if self._cancel_loading or self._current_load_id != load_id: return
                
                # If we need to find logs, do it here in the thread
                if logs_override:
                    selected_logs = list(logs_override)
                else:
                    root = Path(current_logs_path_str)
                    if not root.exists():
                        self.frame.after(0, lambda: messagebox.showwarning("Missing path", f"Path not found: {root}"))
                        self.frame.after(0, lambda: self._set_busy(False, "Ready"))
                        return
                    selected_logs = parser.find_combat_logs(root)

                total = len(selected_logs) or 1
                self.frame.after(0, lambda: self._init_progress(total))

                fights: List[parser.Fight] = []
                to_parse: List[Tuple[Path, Tuple[float, int]]] = []
                progress_count = 0
                last_ui_update = 0

                # Reuse cached logs if unchanged
                for log in selected_logs:
                    if self._cancel_loading or self._current_load_id != load_id: break
                    try:
                        st = log.stat()
                        sig = (st.st_mtime, st.st_size)
                    except Exception:
                        sig = None
                    cached = self.fight_cache.get(str(log))
                    if cached and sig and cached[0] == sig[0] and cached[1] == sig[1] and cached[2] == self.fight_cache_version:
                        fights.extend(cached[3])
                        progress_count += 1
                        now = time.time()
                        if now - last_ui_update > 0.05:
                            last_ui_update = now
                            self.frame.after(0, lambda v=progress_count, t=total, p=log: self._update_progress(v, t, p))
                            self.frame.after(0, lambda: self._update_file_progress(1, 1))
                    else:
                        to_parse.append((log, sig))

                # Force one update after cache check phase
                self.frame.after(0, lambda: self._update_progress(progress_count, total, Path("...")))

                if self._cancel_loading or self._current_load_id != load_id:
                    return

                if not to_parse:
                    self.frame.after(0, lambda: self._apply_fight_results(fights))
                    return

                start_idx = progress_count
                with concurrent.futures.ProcessPoolExecutor(max_workers=os.cpu_count() or 2) as pool:
                    future_to_meta = {pool.submit(parser.parse_file_quick, log): (log, sig) for log, sig in to_parse}
                    pending = set(future_to_meta.keys())
                    completed_count = 0

                    while pending:
                        if self._cancel_loading or self._current_load_id != load_id:
                            pool.shutdown(wait=False, cancel_futures=True)
                            break
                        
                        # Wait briefly to allow cancellation checks
                        done, _ = concurrent.futures.wait(pending, timeout=0.1, return_when=concurrent.futures.FIRST_COMPLETED)
                        
                        for future in done:
                            pending.remove(future)
                            log_path, sig = future_to_meta[future]
                            try:
                                parsed = future.result()
                                fights.extend(parsed)
                                if sig:
                                    self.fight_cache[str(log_path)] = (sig[0], sig[1], self.fight_cache_version, parsed)
                            except Exception:
                                pass
                            
                            completed_count += 1
                            current = start_idx + completed_count
                            now = time.time()
                            # Always update on the very last item, otherwise throttle
                            if completed_count == len(future_to_meta) or (now - last_ui_update > 0.05):
                                last_ui_update = now
                                self.frame.after(0, lambda v=current, t=total, p=log_path: self._update_progress(v, t, p))
                                self.frame.after(0, lambda: self._update_file_progress(1, 1))

                # Ensure final 100% progress is shown
                self.frame.after(0, lambda: self._update_progress(total, total, Path("Finishing...")))
                
                if self._cancel_loading or self._current_load_id != load_id:
                    return

                self.frame.after(10, lambda: self._apply_fight_results(fights))
            except Exception:
                # Fail safe to avoid stuck busy state
                self.frame.after(0, lambda: self._set_busy(False, "Error loading logs"))
            finally:
                if (self._cancel_loading or self._current_load_id != load_id) and self._current_load_id == load_id:
                     # Only clear busy if WE are the current loader (and we were cancelled)
                     self.frame.after(0, lambda: self._set_busy(False, "Cancelled"))

        threading.Thread(target=worker, daemon=True).start()

    def _apply_fight_results(self, fights: List[parser.Fight]):
        try:
            # Drop empty fights (no parsed events) to avoid blank entries.
            # Deduplicate by start time to handle duplicate log files.
            # If timestamps match, prefer the one with more events.
            
            # Filter out fights with very few events (likely noise or empty)
            valid_fights = [f for f in fights if f.events and len(f.events) > 5]
            
            # Sort by start time to enable linear deduplication
            valid_fights.sort(key=lambda f: f.start or datetime.min)
            
            unique_fights: List[parser.Fight] = []
            others: List[parser.Fight] = []

            for f in valid_fights:
                if not f.start:
                    others.append(f)
                    continue
                
                # Check against the last added fight for fuzzy matching
                if unique_fights:
                    last = unique_fights[-1]
                    # If start times are within 90 seconds, consider it the same fight
                    if last.start and abs((f.start - last.start).total_seconds()) < 90:
                        # Keep the one with more events
                        if len(f.events) > len(last.events):
                            unique_fights[-1] = f
                        continue
                
                unique_fights.append(f)
            
            self.all_fights = unique_fights + others
            
            # Clear cached aggregates when fight list changes
            self.stats_cache.clear()

            # Sort by start time desc (newest first), fallback to file name desc
            self.all_fights.sort(key=lambda f: (f.start or datetime.min, f.file_path.name), reverse=True)

            self._update_game_mode_menu()
            
            # Close popup BEFORE updating complex UI elements to ensure it disappears
            self.loading = False
            self.verifying_players = False
            self._set_busy(False, "Ready")
            self.frame.update_idletasks() # Force redraw

            prev_selection = self.selected_fight.id if self.selected_fight else None
            self._refresh_fight_list(preferred_fight_id=prev_selection)
            
            # Save cache in background to avoid UI freeze
            self._save_fight_cache()
        except Exception as e:
            print(f"Error applying fight results: {e}")
            messagebox.showerror("Error", f"Failed to process logs: {e}")
        finally:
            # Clear busy immediately so the loader popup closes reliably
            self.loading = False # Force flag off
            self.verifying_players = False # Force flag off
            self._set_busy(False, "Cancelled" if self._cancel_loading else "Ready")
            # Extra safety
            self._hide_loading_overlay()

    def _init_progress(self, total: int) -> None:
        self._set_busy(True, "Loading fights...")
        if self._overlay_progress:
            # Stop indeterminate animation to fix back-and-forth glitch
            self._overlay_progress.stop()
            self._overlay_progress.configure(mode="determinate", maximum=total, value=0)
        self._overlay_label_var.set(f"Loading fights... 0/{total}")
        self._overlay_sublabel_var.set("")
        self.current_file_path = None

    def _update_progress(self, value: int, total: int, file_path: Path) -> None:
        try:
            if self._overlay_progress and self._overlay_progress.winfo_exists():
                self._overlay_progress.configure(maximum=total)
                self._overlay_progress['value'] = value
        except tk.TclError:
            pass
        self._overlay_label_var.set(f"Loading fights... {value}/{total}")
        self.current_file_path = file_path

    def _reset_file_progress(self, total: int, file_path: Path) -> None:
        # No file-level progress bar in simple overlay, just text
        self.current_file_path = file_path
        self._overlay_sublabel_var.set(f"Current file: {file_path}")

    def _update_file_progress(self, value: int, total: int) -> None:
        # Just update debug text
        path_display = self.current_file_path if self.current_file_path else ""
        self._overlay_sublabel_var.set(f"Current file: {path_display} (done)")


    def _build_pie_tab(self):
        pie_tab = ttk.Frame(self.notebook, style="App.TFrame")
        self.notebook.add(pie_tab, text="Pie")
        self.pie_tab = pie_tab

        # 1:3 Ratio
        # Use uniform group to enforce strict ratio regardless of content size
        pie_tab.columnconfigure(0, weight=2, uniform="pie_cols")
        pie_tab.columnconfigure(1, weight=3, uniform="pie_cols")
        pie_tab.rowconfigure(0, weight=1)

        # Left Side - Boxed
        left_box = ttk.Labelframe(pie_tab, text="Chart", padding=10, style="Card.TLabelframe")
        left_box.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        # Controls
        controls = ttk.Frame(left_box, style="Panel.TFrame")
        controls.pack(fill=tk.X, pady=(0, 10))
        
        # Row 1: Stat Types
        row1 = ttk.Frame(controls, style="Panel.TFrame")
        row1.pack(fill=tk.X, pady=(0, 5))
        
        stats_frame = ttk.Frame(row1, style="Panel.TFrame")
        stats_frame.pack(side=tk.LEFT, anchor=tk.W, padx=5)

        self_heal_frame = ttk.Frame(row1, style="Panel.TFrame")
        self_heal_frame.pack(side=tk.RIGHT, anchor=tk.E, expand=True)
        
        stat_types = [("Damage dealt", "Damage dealt"), ("Damage received", "Damage received"), ("Healing done", "Healing"), ("Healing received", "Healing received")]
        
        self.pie_stat_vars = {}
        for label, val in stat_types:
            var = tk.BooleanVar(value=(val == self.pie_stat_var.get()))
            self.pie_stat_vars[val] = var
            cmd = lambda v=val: self._on_stat_checkbox_click(v)
            self._make_checkbox(stats_frame, label, var, cmd).pack(side=tk.LEFT, padx=2)

        self._make_checkbox(
            self_heal_frame,
            "Show self-heal",
            self.pie_include_self_heal_var,
            self._on_self_heal_toggle,
        ).pack(side=tk.RIGHT, padx=2)

        # Row 2: Filters
        row2 = ttk.Frame(controls, style="Panel.TFrame")
        row2.pack(fill=tk.X, pady=(0, 5))

        # Team Selectors
        teams_frame = ttk.Frame(row2, style="Panel.TFrame")
        teams_frame.pack(side=tk.LEFT, anchor=tk.W, padx=5)
        ttk.Label(teams_frame, text="Teams:", style="LabelMuted.TLabel").pack(side=tk.LEFT, padx=(0, 4))
        self._make_checkbox(teams_frame, "Team A", self.pie_team_a_var, self._refresh_pie).pack(side=tk.LEFT, padx=5)
        self._make_checkbox(teams_frame, "Team B", self.pie_team_b_var, self._refresh_pie).pack(side=tk.LEFT)

        # Target Type Selectors
        self.pie_target_player_var = tk.BooleanVar(value=True)
        self.pie_target_rest_var = tk.BooleanVar(value=True)
        
        targets_frame = ttk.Frame(row2, style="Panel.TFrame")
        targets_frame.pack(side=tk.LEFT, anchor=tk.W, padx=(20, 5))
        ttk.Label(targets_frame, text="Include Targets:", style="LabelMuted.TLabel").pack(side=tk.LEFT, padx=(0, 4))
        self._make_checkbox(targets_frame, "Player", self.pie_target_player_var, self._refresh_pie).pack(side=tk.LEFT, padx=5)
        self._make_checkbox(targets_frame, "Non-Player", self.pie_target_rest_var, self._refresh_pie).pack(side=tk.LEFT)

        # Canvas
        self.pie_canvas = tk.Canvas(left_box, bg=self.colors["bg"], highlightthickness=0)
        self.pie_canvas.pack(fill=tk.BOTH, expand=True)
        self.pie_canvas.bind("<Configure>", lambda e: self._draw_pie())
        self.pie_canvas.bind("<Button-1>", self._on_pie_click)

        # Right Side - Boxed
        right_box = ttk.Labelframe(pie_tab, text="Details", padding=10, style="Card.TLabelframe")
        right_box.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        
        self.pie_details_frame = ttk.Frame(right_box, style="App.TFrame")
        self.pie_details_frame.pack(fill=tk.BOTH, expand=True)
        
        self.pie_source_vars: Dict[str, tk.BooleanVar] = {}
        self.pie_current_player_sources: Optional[str] = None # Track fight+player context for source filters
        self.pie_sources_frame: Optional[ttk.Frame] = None

        self._build_pie_details_ui()
        
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

    def _build_pie_details_ui(self):
        # Header
        self.pie_details_header = ttk.Label(self.pie_details_frame, text="Select a slice to view details", font=("Segoe UI", 12, "bold"), style="Section.TLabel")
        self.pie_details_header.pack(anchor=tk.W, pady=(0, 10))

        # Sources Filter Frame (collapsible)
        self.pie_sources_section = ttk.Frame(self.pie_details_frame, style="Panel.TFrame")
        self.pie_sources_section.pack(fill=tk.X, pady=(0, 10))

        header = ttk.Frame(self.pie_sources_section, style="Panel.TFrame")
        header.pack(fill=tk.X)
        self.pie_sources_toggle_btn = ttk.Button(
            header,
            text="Sources ▸",
            command=self._toggle_pie_sources,
            style="Accent.TButton",
            padding=(6, 2),
        )
        self.pie_sources_toggle_btn.pack(side=tk.LEFT)

        self.pie_sources_frame = ttk.Labelframe(
            self.pie_sources_section,
            text="Sources",
            padding=6,
            style="Filter.TLabelframe",
        )
        self._apply_pie_sources_state()

        # Outgoing breakdown controls (shared for damage + healing tables)
        outgoing_controls = ttk.Frame(self.pie_details_frame, style="App.TFrame")
        outgoing_controls.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(outgoing_controls, text="Group outgoing breakdown by:", style="LabelMuted.TLabel").pack(side=tk.LEFT, padx=(0, 8))
        self._ensure_check_images()
        outgoing_options = (
            ("Target total", "target"),
            ("Source total", "source_total"),
            ("Source detail", "source"),
        )
        for text, value in outgoing_options:
            btn = tk.Radiobutton(
                outgoing_controls,
                text=text,
                variable=self.pie_outgoing_mode_var,
                value=value,
                command=self._refresh_pie_details_data,
                image=self.checkbox_imgs["off"],
                selectimage=self.checkbox_imgs["on"],
                compound="left",
                indicatoron=False,
                bd=0,
                relief="flat",
                highlightthickness=0,
                padx=4,
                pady=2,
                anchor="w",
                bg=self.colors["panel"],
                activebackground=self.colors["panel"],
                fg=self.colors["text"],
                activeforeground=self.colors["text"],
                selectcolor=self.colors["panel"],
            )
            self._style_toggle_button(btn)
            btn.pack(side=tk.LEFT, padx=4)

        # Container for tables
        container = ttk.Frame(self.pie_details_frame, style="App.TFrame")
        container.pack(fill=tk.BOTH, expand=True)
        container.columnconfigure(0, weight=1)
        container.columnconfigure(1, weight=1)
        container.rowconfigure(0, weight=1)
        # Row 1 is for controls, Row 2 for received tables
        container.rowconfigure(2, weight=1)

        # Tables
        # Row 0: Damage (Col 0) and Healing (Col 1)
        self.pie_details_tree_dmg = self._build_breakdown_table(
            container,
            0,
            "Damage Dealt",
            row=0,
            col_span=1,
            height=6,
            columns=("target", "source", "amount", "pct"),
            headings=("Target", "Source", "Amount", "% of total"),
            widths=(160, 220, 90, 90),
            sort_types=("str", "str", "num", "pct"),
        )

        self.pie_details_tree_heal = self._build_breakdown_table(
            container,
            1,
            "Healing Dealt",
            row=0,
            col_span=1,
            height=6,
            columns=("target", "source", "amount", "pct"),
            headings=("Target", "Source", "Amount", "% of total"),
            widths=(160, 220, 90, 90),
            sort_types=("str", "str", "num", "pct"),
        )
        
        # Received Damage Controls
        recv_controls = ttk.Frame(container, style="App.TFrame")
        recv_controls.grid(row=1, column=0, columnspan=2, sticky="w", pady=(10, 0))
        
        self.pie_received_mode_var = tk.StringVar(value="total")
        
        ttk.Label(recv_controls, text="Group incoming breakdown by:", style="LabelMuted.TLabel").pack(side=tk.LEFT, padx=(4, 8))
        
        self._ensure_check_images()
        incoming_options = (
            ("Participant total", "total"),
            ("Source total", "source_total"),
            ("Source detail", "source"),
        )
        for text, value in incoming_options:
            btn = tk.Radiobutton(
                recv_controls,
                text=text,
                variable=self.pie_received_mode_var,
                value=value,
                command=self._refresh_pie_details_data,
                image=self.checkbox_imgs["off"],
                selectimage=self.checkbox_imgs["on"],
                compound="left",
                indicatoron=False,
                bd=0,
                relief="flat",
                highlightthickness=0,
                padx=4,
                pady=2,
                anchor="w",
                bg=self.colors["panel"],
                activebackground=self.colors["panel"],
                fg=self.colors["text"],
                activeforeground=self.colors["text"],
                selectcolor=self.colors["panel"],
            )
            self._style_toggle_button(btn)
            btn.pack(side=tk.LEFT, padx=8)

        # Row 2: Received (Damage + Healing)
        self.pie_details_tree_recv = self._build_breakdown_table(
            container,
            0,
            "Damage Received",
            row=2,
            col_span=1,
            height=6,
            columns=("attacker", "source", "amount", "pct"),
            headings=("Attacker", "Source", "Amount", "% of total"),
            widths=(150, 220, 90, 90),
            sort_types=("str", "str", "num", "pct"),
        )
        self.pie_details_tree_heal_recv = self._build_breakdown_table(
            container,
            1,
            "Healing Received",
            row=2,
            col_span=1,
            height=6,
            columns=("healer", "source", "amount", "pct"),
            headings=("Healer", "Source", "Amount", "% of total"),
            widths=(150, 220, 90, 90),
            sort_types=("str", "str", "num", "pct"),
        )

    def _toggle_pie_sources(self) -> None:
        self.pie_sources_collapsed = not self.pie_sources_collapsed
        self._apply_pie_sources_state()

    def _apply_pie_sources_state(self) -> None:
        if not self.pie_sources_frame:
            return
        if self.pie_sources_collapsed:
            self.pie_sources_frame.pack_forget()
            if self.pie_sources_toggle_btn:
                self.pie_sources_toggle_btn.configure(text="Sources ▸")
        else:
            self.pie_sources_frame.pack(fill=tk.X, pady=(4, 10))
            if self.pie_sources_toggle_btn:
                self.pie_sources_toggle_btn.configure(text="Sources ▾")

    def _on_tab_changed(self, event):
        if self.notebook.select() == str(self.pie_tab):
            self._refresh_pie()

    def _on_stat_checkbox_click(self, selected_val):
        self.pie_stat_var.set(selected_val)
        for val, var in self.pie_stat_vars.items():
            var.set(val == selected_val)
        self._refresh_pie()

    def _on_self_heal_toggle(self):
        self.pie_current_player_sources = None
        self._refresh_pie()

    def _should_include_self_heal(self) -> bool:
        var = getattr(self, "pie_include_self_heal_var", None)
        return bool(var.get()) if var is not None else True

    def _is_self_heal_event(self, event: parser.CombatEvent) -> bool:
        if event.event_type != "healing":
            return False
        actor = (event.actor or "").strip()
        target = (event.target or "").strip()
        return bool(actor) and actor == target

    def _refresh_pie(self):
        if not self.selected_fight or not self.pie_canvas:
            return
        self._draw_pie()
        self._update_pie_details()

    def _draw_pie(self):
        canvas = self.pie_canvas
        canvas.delete("all")
        self.pie_data = []
        self.pie_click_map = {} # Map canvas item IDs to player names
        
        if not self.selected_fight:
            return

        width = canvas.winfo_width()
        height = canvas.winfo_height()
        if width < 50 or height < 50:
            return

        # Draw Team Counts + winner star (keep counts right-aligned; stars independent)
        stats = self.stats_cache.get(f"{self.selected_fight.file_path}::{self.selected_fight.id}")
        if stats:
            team_a, team_b = self._get_teams(self.selected_fight, stats)
            winner_team = self._determine_winner(team_a, team_b, stats, self.selected_fight)
            count_a = len(team_a)
            count_b = len(team_b)

            text_a = canvas.create_text(
                width - 10,
                10,
                text=f"Team A: {count_a}",
                anchor="ne",
                fill=self.colors["text"],
                font=("Segoe UI", 10),
            )
            text_b = canvas.create_text(
                width - 10,
                24,
                text=f"Team B: {count_b}",
                anchor="ne",
                fill=self.colors["text"],
                font=("Segoe UI", 10),
            )

            if winner_team == "A":
                ax0, ay0, ax1, ay1 = canvas.bbox(text_a)
                canvas.create_text(
                    ax0 - 6,
                    (ay0 + ay1) / 2,
                    text="★",
                    anchor="e",
                    fill=self.colors["accent"],
                    font=("Segoe UI", 10),
                )
            if winner_team == "B":
                bx0, by0, bx1, by1 = canvas.bbox(text_b)
                canvas.create_text(
                    bx0 - 6,
                    (by0 + by1) / 2,
                    text="★",
                    anchor="e",
                    fill=self.colors["accent"],
                    font=("Segoe UI", 10),
                )

        cx, cy = width / 2, height / 2
        # Reduce radius to make room for labels (33% of min dimension)
        radius = min(width, height) * 0.33
        inner_radius = radius * 0.6 # Donut hole size

        # Get data
        stat_type = self.pie_stat_var.get()
        teams = []
        if self.pie_team_a_var.get(): teams.append("A")
        if self.pie_team_b_var.get(): teams.append("B")
        
        if not teams:
            canvas.create_text(cx, cy, text="No teams selected", fill=self.colors["muted"], font=("Segoe UI", 12))
            return

        data = self._get_pie_data(stat_type, teams)
        if not data:
            canvas.create_text(cx, cy, text="No data", fill=self.colors["muted"], font=("Segoe UI", 12))
            return

        # Deselect if player not in new data
        if self.pie_selected_wedge and self.pie_selected_wedge not in data:
            self.pie_selected_wedge = None
            self._update_pie_details()
        total = sum(data.values())
        if total == 0:
            canvas.create_text(cx, cy, text="Total is 0", fill=self.colors["muted"], font=("Segoe UI", 12))
            return

        # Sort data
        sorted_data = sorted(data.items(), key=lambda x: x[1], reverse=True)
        
        start_angle = 90
        
        # Colors - Bright, distinct palette
        # Use class-level palette
        palette = self.pie_palette

        # Draw outer ring/glow for futuristic look
        canvas.create_oval(
            cx - radius - 5, cy - radius - 5,
            cx + radius + 5, cy + radius + 5,
            outline=self.colors["accent_dark"], width=1
        )

        # Prepare labels list for collision resolution
        labels_to_draw = []
        
        num_items = len(sorted_data)
        full_slice = num_items == 1
        current_angle = 90.0

        for i, (name, value) in enumerate(sorted_data):
            pct = (value / total)
            extent = pct * 360.0
            if full_slice:
                extent = 359.999
            
            # Ensure even tiny slices are drawn (min 0.5 degrees for visibility)
            # Using a separate variable for drawing to avoid messing up the angle calculation
            draw_extent = extent
            if draw_extent < 0.5: draw_extent = 0.5
            
            # Get consistent color for player
            if name not in self.player_color_cache:
                # Assign next available color from palette
                # We use the size of the cache to determine the index
                # This ensures consistent assignment order as new players are discovered
                color_idx = len(self.player_color_cache) % len(palette)
                self.player_color_cache[name] = palette[color_idx]
            
            base_color = self.player_color_cache[name]
            
            # Darken if not selected and something IS selected
            if self.pie_selected_wedge and self.pie_selected_wedge != name:
                color = self._darken_color(base_color, 0.3)
                outline = self.colors["bg"]
                width_outline = 1
            else:
                color = base_color
                outline = self.colors["bg"]
                width_outline = 1

            # Offset for selected wedge
            # User requested to remove "move out effect"
            offset = 0
            if self.pie_selected_wedge == name:
                # offset = 10 # Removed
                # outline = "white" # Removed white border
                # width_outline = 2
                pass
            
            mid_angle_rad = math.radians(current_angle - extent / 2)
            
            ox = math.cos(mid_angle_rad) * offset
            oy = math.sin(mid_angle_rad) * -offset 
            
            # Draw wedge
            item_id = canvas.create_arc(
                cx - radius + ox, cy - radius + oy,
                cx + radius + ox, cy + radius + oy,
                start=current_angle - draw_extent, extent=draw_extent,
                fill=color, outline=outline, width=width_outline,
                style=tk.PIESLICE,
                tags="wedge"
            )
            self.pie_click_map[item_id] = name
            
            self.pie_data.append({
                "name": name,
                "value": value,
                "start": current_angle - draw_extent,
                "extent": draw_extent,
                "id": item_id
            })
            
            # Collect Label info
            # Calculate ideal position
            # Radial placement
            label_radius = radius + 40 # Push out further
            angle_deg = (current_angle - extent / 2) % 360
            
            # Determine side based on angle for anchor
            is_right = False
            if angle_deg <= 90 or angle_deg >= 270:
                is_right = True
            
            labels_to_draw.append({
                "name": name,
                "pct": pct,
                "angle_deg": angle_deg,
                "is_right": is_right,
                "color": self.colors["text"] if (not self.pie_selected_wedge or self.pie_selected_wedge == name) else self.colors["muted"],
                "wedge_x": cx + math.cos(math.radians(angle_deg)) * radius, # Point on rim
                "wedge_y": cy - math.sin(math.radians(angle_deg)) * radius, # Point on rim (y inverted)
                "ideal_x": cx + math.cos(math.radians(angle_deg)) * label_radius,
                "ideal_y": cy - math.sin(math.radians(angle_deg)) * label_radius
            })

            current_angle -= extent

        # Draw Donut Hole
        canvas.create_oval(
            cx - inner_radius, cy - inner_radius,
            cx + inner_radius, cy + inner_radius,
            fill=self.colors["bg"], outline=self.colors["accent_dark"], width=1
        )
        
        # If selected wedge was not drawn (should not happen now), clear selection
        if self.pie_selected_wedge and self.pie_selected_wedge not in self.pie_click_map.values():
             self.pie_selected_wedge = None
             # Redraw to remove darkening effect
             # But we are inside _draw_pie, so we can't call it again recursively easily.
             # Instead, we should have checked this before drawing?
             # But we didn't know if it would be drawn.
             # Since we removed the skip, it SHOULD be drawn.
             pass
        
        # Center Text will be drawn last to ensure it's on top

        # Resolve label collisions (Radial + Vertical adjustment)
        # Split into left and right groups
        right_labels = [l for l in labels_to_draw if l["is_right"]]
        left_labels = [l for l in labels_to_draw if not l["is_right"]]
        
        # Sort by Y (top to bottom)
        right_labels.sort(key=lambda l: l["ideal_y"])
        left_labels.sort(key=lambda l: l["ideal_y"])
        
        def layout_radial_group(lbls, is_right_group):
            if not lbls: return
            
            # Initialize with ideal positions
            for l in lbls:
                l["x"] = l["ideal_x"]
                l["y"] = l["ideal_y"]
            
            # Resolve vertical collisions
            min_dist = 32 # Font size * 2 + padding for multiline text
            
            # Iterative push
            changed = True
            iterations = 0
            while changed and iterations < 20:
                changed = False
                iterations += 1
                
                # Push down
                for i in range(len(lbls) - 1):
                    if lbls[i+1]["y"] < lbls[i]["y"] + min_dist:
                        lbls[i+1]["y"] = lbls[i]["y"] + min_dist
                        changed = True
                
                # Push up from bottom boundary
                if lbls[-1]["y"] > height - 10:
                    lbls[-1]["y"] = height - 10
                    changed = True
                    # Propagate up
                    for i in range(len(lbls)-1, 0, -1):
                        if lbls[i-1]["y"] > lbls[i]["y"] - min_dist:
                            lbls[i-1]["y"] = lbls[i]["y"] - min_dist
                
                # Push down from top boundary
                if lbls[0]["y"] < 10:
                    lbls[0]["y"] = 10
                    changed = True
                    # Propagate down
                    for i in range(len(lbls) - 1):
                        if lbls[i+1]["y"] < lbls[i]["y"] + min_dist:
                            lbls[i+1]["y"] = lbls[i]["y"] + min_dist

            # Post-process: Ensure labels are far enough for the tail to clear the pie
            tail_len = 20
            min_clearance = radius + 20 # Distance from center that the tail start must clear
            
            for l in lbls:
                # Ensure tail start (tx) is outside min_clearance
                if is_right_group:
                    # tx = l["x"] - tail_len
                    # We want tx > cx + min_clearance
                    min_x = cx + min_clearance + tail_len
                    if l["x"] < min_x:
                        l["x"] = min_x
                else:
                    # tx = l["x"] + tail_len
                    # We want tx < cx - min_clearance
                    max_x = cx - min_clearance - tail_len
                    if l["x"] > max_x:
                        l["x"] = max_x
                
                # Repel from Pie (Safety check for vertical overlap with pie)
                dx = l["x"] - cx
                dy = l["y"] - cy
                dist_sq = dx*dx + dy*dy
                min_radius_sq = (radius + 25) ** 2
                
                if dist_sq < min_radius_sq:
                    req_dx = math.sqrt(max(0, min_radius_sq - dy*dy))
                    if is_right_group:
                        l["x"] = max(l["x"], cx + req_dx)
                    else:
                        l["x"] = min(l["x"], cx - req_dx)

        layout_radial_group(right_labels, True)
        layout_radial_group(left_labels, False)
        
        # Draw labels and lines
        tail_len = 20 # Define tail length for drawing
        
        for l in labels_to_draw:
            anchor = "w" if l["is_right"] else "e"
            
            # Calculate connector points
            # 1. Tail Start (Horizontal line start)
            if l["is_right"]:
                tx = l["x"] - tail_len
            else:
                tx = l["x"] + tail_len
            ty = l["y"]
            
            # Draw Polyline: Wedge -> TailStart -> Label
            # This creates a 2-segment line: Diagonal (Wedge->TailStart) then Horizontal (TailStart->Label)
            # Only 1 direction change (at TailStart)
            canvas.create_line(
                l["wedge_x"], l["wedge_y"],
                tx, ty,
                l["x"], l["y"],
                fill=self.colors["muted"], width=1
            )
            
            # Adjust text X slightly away from line end
            text_x = l["x"] + (5 if l["is_right"] else -5)
            
            justify = "left" if l["is_right"] else "right"
            label_text = f"{l['name']}\n{l['pct']*100:.1f}%"
            lbl_id = canvas.create_text(text_x, l["y"], text=label_text, fill=l["color"], font=("Segoe UI", 9), anchor=anchor, justify=justify, tags="label")
            self.pie_click_map[lbl_id] = l["name"]

        # Draw Center Text (Total or Selected)
        center_label = "Total"
        center_value = total
        
        if self.pie_selected_wedge:
            # Try to find value in data
            val = data.get(self.pie_selected_wedge)
            if val is not None:
                center_label = self.pie_selected_wedge
                center_value = val
                # Truncate name if too long to fit in hole
                if len(center_label) > 12:
                    center_label = center_label[:10] + "..."
        
        # Ensure the hole covers everything in the center
        canvas.create_oval(
            cx - inner_radius, cy - inner_radius,
            cx + inner_radius, cy + inner_radius,
            fill=self.colors["bg"], outline=self.colors["accent_dark"], width=1
        )

        canvas.create_text(cx, cy - 10, text=center_label, fill=self.colors["muted"], font=("Segoe UI", 10), justify="center")
        canvas.create_text(cx, cy + 10, text=self._format_number(center_value), fill=self.colors["accent"], font=("Segoe UI", 12, "bold"), justify="center")

    def _format_number(self, num: float) -> str:
        if num >= 1_000_000:
            return f"{num/1_000_000:.1f}M"
        if num >= 1_000:
            return f"{num/1_000:.1f}K"
        return f"{num:.0f}"

    def _get_pie_data(self, stat_type: str, teams: List[str]) -> Dict[str, float]:
        if not self.selected_fight:
            return {}
        
        cache_key = f"{self.selected_fight.file_path}::{self.selected_fight.id}"
        stats = self.stats_cache.get(cache_key)
        if stats is None:
            stats = parser.aggregate_stats(self.selected_fight)
            self.stats_cache[cache_key] = stats
            
        is_player = self._is_player_name
        team_a_list, team_b_list = self._get_teams(self.selected_fight, stats)

        target_players = set()
        if "A" in teams:
            target_players.update(team_a_list)
        if "B" in teams:
            target_players.update(team_b_list)
            
        if not target_players:
            return {}

        include_player = self.pie_target_player_var.get()
        include_rest = self.pie_target_rest_var.get()
        
        def is_allowed_entity(name: str) -> bool:
            is_p = is_player(name)
            if is_p and include_player: return True
            if not is_p and include_rest: return True
            return False

        include_self_heal = self._should_include_self_heal()

        data = {p: 0.0 for p in target_players}
        
        for ev in self.selected_fight.events:
            if stat_type == "Damage dealt":
                if ev.event_type != "damage": continue
                if ev.actor in data:
                    if is_allowed_entity(ev.target):
                        data[ev.actor] += ev.amount
                        
            elif stat_type == "Damage received":
                if ev.event_type != "damage": continue
                if ev.target in data:
                    if is_allowed_entity(ev.actor):
                        data[ev.target] += ev.amount
                        
            elif stat_type == "Healing":
                if ev.event_type != "healing": continue
                if not include_self_heal and self._is_self_heal_event(ev):
                    continue
                if ev.actor in data:
                    if is_allowed_entity(ev.target):
                        data[ev.actor] += ev.amount
                        
            elif stat_type == "Healing received":
                if ev.event_type != "healing": continue
                if not include_self_heal and self._is_self_heal_event(ev):
                    continue
                if ev.target in data:
                    if is_allowed_entity(ev.actor):
                        data[ev.target] += ev.amount

        return {k: v for k, v in data.items() if v > 0}
                
        return data

    def _on_pie_click(self, event):
        canvas = self.pie_canvas
        # Find which item was clicked (wedge or label)
        item = canvas.find_closest(event.x, event.y)
        if not item:
            return
            
        item_id = item[0]
        
        # Check if it's a mapped item (wedge or label)
        if hasattr(self, "pie_click_map") and item_id in self.pie_click_map:
            name = self.pie_click_map[item_id]
            
            if self.pie_selected_wedge == name:
                self.pie_selected_wedge = None # Deselect
            else:
                self.pie_selected_wedge = name
            
            self._draw_pie()
            self._update_pie_details()
            return
        
        # If clicked outside, deselect?
        self.pie_selected_wedge = None
        self._draw_pie()
        self._update_pie_details()

    def _update_pie_details(self):
        if not self.pie_details_header or not self.pie_sources_frame:
            return

        player = self.pie_selected_wedge
        fight = self.selected_fight

        if not player or not fight:
            self.pie_details_header.configure(text="Select a slice to view details")
            self._populate_tree(self.pie_details_tree_dmg, [])
            self._populate_tree(self.pie_details_tree_heal, [])
            self._populate_tree(self.pie_details_tree_recv, [])
            self._populate_tree(self.pie_details_tree_heal_recv, [])
            for child in self.pie_sources_frame.winfo_children():
                child.destroy()
            self.pie_current_player_sources = None
            self.pie_source_vars.clear()
            return

        self.pie_details_header.configure(text=f"Details for {player}")
        fight_key = f"{fight.file_path}::{fight.id}"
        context_key = f"{fight_key}::{player}" if fight_key else player

        if self.pie_current_player_sources != context_key:
            self.pie_current_player_sources = context_key
            self.pie_source_vars.clear()
            for child in self.pie_sources_frame.winfo_children():
                child.destroy()

            player_sources: List[str] = []
            seen_sources: Set[str] = set()
            for ev in fight.events:
                if ev.actor != player or ev.event_type not in ("damage", "healing"):
                    continue
                label = ev.source.strip() or "Unknown source"
                if label not in seen_sources:
                    seen_sources.add(label)
                    player_sources.append(label)
            player_sources.sort()

            if player_sources:
                controls = ttk.Frame(self.pie_sources_frame, style="Panel.TFrame")
                controls.pack(fill=tk.X, pady=(0, 6))

                def _set_all_sources(value: bool) -> None:
                    for var in self.pie_source_vars.values():
                        var.set(value)
                    self._refresh_pie_details_data()

                ttk.Button(controls, text="Select All", command=lambda: _set_all_sources(True), style="Accent.TButton").pack(side=tk.LEFT, padx=(0, 6))
                ttk.Button(controls, text="Unselect All", command=lambda: _set_all_sources(False), style="Accent.TButton").pack(side=tk.LEFT)

                list_frame = ttk.Frame(self.pie_sources_frame, style="Panel.TFrame")
                list_frame.pack(fill=tk.X)
                cols = 4
                for idx, src in enumerate(player_sources):
                    var = tk.BooleanVar(value=True)
                    self.pie_source_vars[src] = var
                    chk = tk.Checkbutton(
                        list_frame,
                        text=self._pretty_source_text(src),
                        variable=var,
                        command=self._refresh_pie_details_data,
                        image=self.checkbox_imgs["off"] if self.checkbox_imgs else None,
                        selectimage=self.checkbox_imgs["on"] if self.checkbox_imgs else None,
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
                        bg=self.colors["panel"],
                        activebackground=self.colors["panel"],
                        fg=self.colors["text"],
                        activeforeground=self.colors["text"],
                        selectcolor=self.colors["panel"],
                    )
                    self._style_toggle_button(chk)
                    chk.grid(row=idx // cols, column=idx % cols, sticky="w", padx=4, pady=2)
                for c in range(cols):
                    list_frame.columnconfigure(c, weight=1)
            else:
                ttk.Label(self.pie_sources_frame, text="No source info found; all entries shown").pack(anchor=tk.W)

        self._refresh_pie_details_data()

    def _refresh_pie_details_data(self):
        if not self.pie_selected_wedge or not self.selected_fight:
            return
            
        player = self.pie_selected_wedge
        fight = self.selected_fight
        
        # Get allowed sources
        allowed = None
        if self.pie_source_vars:
            allowed = {s for s, var in self.pie_source_vars.items() if var.get()}

        # Compute data
        data = self._compute_breakdown(player, fight, allowed)

        outgoing_mode = self.pie_outgoing_mode_var.get() if getattr(self, "pie_outgoing_mode_var", None) else "target"
        if outgoing_mode == "source":
            damage_rows = data["damage_detail"]
            healing_rows = data["healing_detail"]
            self._set_tree_display_columns(self.pie_details_tree_dmg, ("target", "source", "amount", "pct"))
            self._set_tree_display_columns(self.pie_details_tree_heal, ("target", "source", "amount", "pct"))
        elif outgoing_mode == "source_total":
            damage_rows = self._aggregate_source_rows(data["damage_detail"], data.get("damage_total", 0.0))
            healing_rows = self._aggregate_source_rows(data["healing_detail"], data.get("healing_total", 0.0))
            self._set_tree_display_columns(self.pie_details_tree_dmg, ("source", "amount", "pct"))
            self._set_tree_display_columns(self.pie_details_tree_heal, ("source", "amount", "pct"))
        else:
            damage_rows = [(t, "", amt, pct) for (t, amt, pct) in data["damage"]]
            healing_rows = [(t, "", amt, pct) for (t, amt, pct) in data["healing"]]
            self._set_tree_display_columns(self.pie_details_tree_dmg, ("target", "amount", "pct"))
            self._set_tree_display_columns(self.pie_details_tree_heal, ("target", "amount", "pct"))

        self._populate_tree(self.pie_details_tree_dmg, damage_rows)
        self._populate_tree(self.pie_details_tree_heal, healing_rows)
        
        # Handle Received Data View
        recv_raw = data["received"] # List[(attacker, source, amount, pct)]
        heal_recv_raw = data["healing_received"]
        received_mode = "source"
        if hasattr(self, "pie_received_mode_var") and self.pie_received_mode_var is not None:
            received_mode = self.pie_received_mode_var.get()

        if received_mode == "total":
            # Aggregate by attacker
            agg = {}
            total_val = 0.0
            for row in recv_raw:
                atk = row[0]
                val = row[2]
                agg[atk] = agg.get(atk, 0.0) + val
                total_val += val
            
            # Rebuild rows: (attacker, source, amount, pct)
            new_rows = []
            if total_val > 0:
                # Sort by amount desc
                sorted_agg = sorted(agg.items(), key=lambda x: x[1], reverse=True)
                for atk, val in sorted_agg:
                    new_rows.append((atk, "", val, val / total_val * 100.0))
            self._populate_tree(self.pie_details_tree_recv, new_rows)
            self._set_tree_display_columns(self.pie_details_tree_recv, ("attacker", "amount", "pct"))
            # Healing received aggregation
            heal_agg = {}
            heal_total = 0.0
            for row in heal_recv_raw:
                healer = row[0]
                val = row[2]
                heal_agg[healer] = heal_agg.get(healer, 0.0) + val
                heal_total += val
            heal_rows = []
            if heal_total > 0:
                for healer, val in sorted(heal_agg.items(), key=lambda x: x[1], reverse=True):
                    heal_rows.append((healer, "", val, val / heal_total * 100.0))
            self._populate_tree(self.pie_details_tree_heal_recv, heal_rows)
            self._set_tree_display_columns(self.pie_details_tree_heal_recv, ("healer", "amount", "pct"))
        elif received_mode == "source_total":
            dmg_source_rows = self._aggregate_source_rows(recv_raw, data.get("received_total", 0.0))
            heal_source_rows = self._aggregate_source_rows(heal_recv_raw, data.get("healing_received_total", 0.0))
            self._populate_tree(self.pie_details_tree_recv, dmg_source_rows)
            self._set_tree_display_columns(self.pie_details_tree_recv, ("source", "amount", "pct"))
            self._populate_tree(self.pie_details_tree_heal_recv, heal_source_rows)
            self._set_tree_display_columns(self.pie_details_tree_heal_recv, ("source", "amount", "pct"))
        else:
            self._populate_tree(self.pie_details_tree_recv, recv_raw)
            self._set_tree_display_columns(self.pie_details_tree_recv, ("attacker", "source", "amount", "pct"))
            self._populate_tree(self.pie_details_tree_heal_recv, heal_recv_raw)
            self._set_tree_display_columns(self.pie_details_tree_heal_recv, ("healer", "source", "amount", "pct"))

    def _build_team_column(self, parent: ttk.Frame, column: int) -> ttk.Frame:
        parent.rowconfigure(0, weight=1)
        col = ttk.Frame(parent, padding=6, style="Panel.TFrame")
        col.grid(row=0, column=column, sticky="nsew")
        return col

    def _render_team_panel(
        self,
        key: str,
        title: str,
        players: List[str],
        stats: Dict[str, parser.ParticipantStats],
        totals: Dict[str, float],
        fight: parser.Fight,
        is_player,
        winner_team: Optional[str] = None,
    ) -> None:
        frame = self.team_frames.get(key)
        if not frame:
            return
        for child in frame.winfo_children():
            child.destroy()

        count = len(players)
        prefix = "★ " if winner_team == key else ""
        display_title = f"{prefix}{title} ({count} Players)"

        ttk.Label(frame, text=display_title, font=("Segoe UI", 12, "bold"), style="Section.TLabel").pack(anchor=tk.W, pady=(0, 6))
        if not players:
            ttk.Label(frame, text="No players detected", style="LabelMuted.TLabel").pack(anchor=tk.W)
            return

        for name in players:
            st = stats.get(name)
            if not st:
                continue
            card = ttk.Labelframe(frame, text="", padding=8, style="Card.TLabelframe")
            card.pack(fill=tk.X, pady=4)
            title_row = ttk.Frame(card, style="Panel.TFrame")
            title_row.pack(fill=tk.X, pady=(0, 4))
            ttk.Label(title_row, text=name, style="PlayerName.TLabel", font=("Segoe UI", 12, "bold")).pack(side=tk.LEFT)
            btn_row = ttk.Frame(card, style="Panel.TFrame")
            btn_row.pack(fill=tk.X, pady=(0, 4))
            ttk.Button(
                btn_row,
                text="Show breakdown",
                command=lambda n=name: self._open_breakdown_window(n, fight, is_player),
                style="Accent.TButton",
            ).pack(side=tk.RIGHT)
            self._add_bar_row(card, "Damage dealt", st.damage_dealt, totals.get("damage_dealt", 0.0))
            self._add_bar_row(card, "Damage taken", st.damage_taken, totals.get("damage_taken", 0.0))
            self._add_bar_row(card, "Healing", st.healing_others, totals.get("healing_others", 0.0))
            self._add_bar_row(card, "Self-heal", st.self_heal, totals.get("self_heal", 0.0))

    def _add_bar_row(self, parent: ttk.Frame, label: str, value: float, total: float) -> None:
        row = ttk.Frame(parent, style="Panel.TFrame")
        row.pack(fill=tk.X, pady=2)
        row.columnconfigure(1, weight=1)
        ttk.Label(row, text=label, width=14, style="LabelMuted.TLabel").grid(column=0, row=0, sticky="w")

        max_val = total if total > 0 else 1.0
        pct = (value / max_val * 100) if max_val else 0.0
        pb = ttk.Progressbar(row, mode="determinate", maximum=100, value=min(max(pct, 0.0), 100.0), style="Futuristic.Horizontal.TProgressbar")
        pb.grid(column=1, row=0, sticky="ew", padx=6)

        ttk.Label(row, text=f"{value:.0f} ({pct:.0f}%)", width=14, anchor="e", style="LabelStrong.TLabel").grid(column=2, row=0, sticky="e")

    def _get_teams(self, fight: parser.Fight, stats: Dict[str, parser.ParticipantStats]) -> Tuple[List[str], List[str]]:
        is_player = self._is_player_name
        players = [p for p in stats.keys() if is_player(p)]

        # Seed teams from reward outcomes when available
        outcomes: Dict[str, str] = {}
        for ev in fight.events:
            if ev.event_type == "reward":
                res = (ev.source or "").lower()
                if res in {"victory", "defeat"}:
                    outcomes[ev.actor] = res
        winners = {p for p, res in outcomes.items() if res == "victory" and p in players}
        losers = {p for p, res in outcomes.items() if res == "defeat" and p in players}

        if outcomes and (winners or losers):
            team_a = sorted(winners)
            team_b = sorted(losers)
        else:
            team_a, team_b = self._infer_teams(fight, is_player, players, outcomes)
        
        user = self.username_var.get().strip()
        if user and user in players:
            in_a = user in team_a
            in_b = user in team_b
            if in_b and not in_a:
                team_a, team_b = team_b, team_a
        return team_a, team_b

    def _determine_winner(self, team_a: List[str], team_b: List[str], stats: Dict[str, parser.ParticipantStats], fight: parser.Fight) -> Optional[str]:
        """Winner from reward outcomes when available; fallback to damage-dealt heuristic."""
        if fight:
            outcomes: Dict[str, str] = {}
            for ev in fight.events:
                if ev.event_type == "reward":
                    res = (ev.source or "").lower()
                    if res in {"victory", "defeat"}:
                        outcomes[ev.actor] = res
            if outcomes:
                wins_a = sum(1 for p in team_a if outcomes.get(p) == "victory")
                wins_b = sum(1 for p in team_b if outcomes.get(p) == "victory")
                if wins_a != wins_b:
                    return "A" if wins_a > wins_b else "B"
                # If no victories recorded, prefer side with fewer defeats
                defeats_a = sum(1 for p in team_a if outcomes.get(p) == "defeat")
                defeats_b = sum(1 for p in team_b if outcomes.get(p) == "defeat")
                if defeats_a != defeats_b:
                    return "A" if defeats_a < defeats_b else "B"
        # Fallback heuristic
        if not stats:
            return None
        dmg_a = sum(stats[p].damage_dealt for p in team_a)
        dmg_b = sum(stats[p].damage_dealt for p in team_b)
        if dmg_a > dmg_b:
            return "A"
        if dmg_b > dmg_a:
            return "B"
        return None

    def _infer_teams(
        self,
        fight: parser.Fight,
        is_player,
        players: List[str],
        outcomes: Optional[Dict[str, str]] = None,
    ) -> Tuple[List[str], List[str]]:
        names: Set[str] = set(players)
        if not names:
            return [], []

        outcomes = outcomes or {}
        winners = {p for p, res in outcomes.items() if res == "victory" and p in names}
        losers = {p for p, res in outcomes.items() if res == "defeat" and p in names}

        opponents: Dict[str, Dict[str, float]] = {}
        for ev in fight.events:
            if ev.event_type != "damage":
                continue
            a = ev.actor.strip()
            b = ev.target.strip()
            if not (is_player(a) and is_player(b)):
                continue
            if a == b:
                continue
            opponents.setdefault(a, {}).setdefault(b, 0.0)
            opponents.setdefault(b, {}).setdefault(a, 0.0)
            opponents[a][b] += ev.amount
            opponents[b][a] += ev.amount

        def weight(n: str) -> float:
            return sum(opponents.get(n, {}).values())

        team_a: Set[str] = set(winners) if winners else set()
        team_b: Set[str] = set(losers) if losers else set()

        # Pick a seed not already placed
        remaining = names - team_a - team_b
        seed = None
        if remaining:
            seed = max(remaining, key=weight)
        if seed is None and names:
            seed = next(iter(names))
        if seed is not None:
            team_a.add(seed)

        queue = [seed] if seed else []

        while queue:
            cur = queue.pop()
            for opp, _w in sorted(opponents.get(cur, {}).items(), key=lambda kv: -kv[1]):
                if opp in team_a or opp in team_b:
                    continue
                if cur in team_a:
                    team_b.add(opp)
                else:
                    team_a.add(opp)
                queue.append(opp)

        # Assign remaining by who they fight more
        for n in names:
            if n in team_a or n in team_b:
                continue
            to_a = sum(opponents.get(n, {}).get(x, 0.0) + opponents.get(x, {}).get(n, 0.0) for x in team_a)
            to_b = sum(opponents.get(n, {}).get(x, 0.0) + opponents.get(x, {}).get(n, 0.0) for x in team_b)
            if to_a > to_b:
                team_b.add(n)
            elif to_b > to_a:
                team_a.add(n)
            else:
                (team_a if len(team_a) <= len(team_b) else team_b).add(n)

        if not team_b:
            ordered = sorted(names)
            half = len(ordered) // 2
            team_a = set(ordered[:half])
            team_b = set(ordered[half:])

        return sorted(team_a), sorted(team_b)

    def _set_busy(self, busy: bool, message: str) -> None:
        self.loading = busy
        self.status_var.set(message)
        state = tk.DISABLED if busy else tk.NORMAL
        
        # Disable/Enable controls
        for widget in [self.fight_box, self.reload_btn, self.analyze_btn, 
                      self.clear_cache_btn, self.display_names_btn]:
            if widget:
                widget.state(["disabled"] if busy else ["!disabled"])

        # Toggle Back button in main app navbar
        if hasattr(self.app, "navbar"):
            back_state = "disabled" if busy else "normal"
            try:
                for w in self.app.navbar.winfo_children():
                    if isinstance(w, ttk.Button) and "Back" in w.cget("text"):
                        w.configure(state=back_state)
            except Exception:
                pass

        if busy:
            self._show_loading_overlay(message)
        else:
            self._hide_loading_overlay()
            
        self.frame.update_idletasks()

    def _cancel_load(self):
        self._cancel_loading = True
        # Immediately hide the overlay to give instant feedback.
        # The background worker (if any) tracks _current_load_id or _cancel_loading and will exit.
        self._set_busy(False, "Cancelled")

    def _show_loading_overlay(self, message: str) -> None:
        if not self.frame:
            return
            
        # Create overlay if it doesn't exist
        if not self._loading_overlay or not self._loading_overlay.winfo_exists():
            # Use TileBorder for immediate popout effect (border color)
            self._loading_overlay = ttk.Frame(self.frame, style="TileBorder.TFrame")
            
            # Inner panel with background to look like a card
            inner = ttk.Frame(self._loading_overlay, style="Panel.TFrame")
            inner.pack(fill=tk.BOTH, expand=True, padx=2, pady=2) # 2px border
            
            # Content Container
            container = ttk.Frame(inner, style="Panel.TFrame", padding=30)
            container.pack(fill=tk.BOTH, expand=True)
            
            # Use a dummy spacer to enforce minimum width and prevent wiggling
            ttk.Frame(container, width=600, height=0, style="Panel.TFrame").pack()
            
            ttk.Label(container, text="ANALYZING LOGS", font=("Segoe UI", 16, "bold"), style="Section.TLabel").pack(pady=(0, 20))
            
            self._overlay_progress = ttk.Progressbar(container, mode="determinate", length=400, style="Futuristic.Horizontal.TProgressbar")
            self._overlay_progress.pack(pady=(0, 10))
            
            ttk.Label(container, textvariable=self._overlay_label_var, style="LabelMuted.TLabel", font=("Segoe UI", 10)).pack()
            ttk.Label(container, textvariable=self._overlay_sublabel_var, style="LabelMuted.TLabel", font=("Segoe UI", 9), wraplength=460, justify="center").pack(pady=(5, 10))
            
            ttk.Button(container, text="Cancel", command=self._cancel_load, style="Accent.TButton").pack(pady=(0, 20))

        # Show popup centered (floating window style)
        self._loading_overlay.place(relx=0.5, rely=0.5, anchor="center")
        self._loading_overlay.lift()
        self._loading_overlay.lift()
        self._overlay_label_var.set(message)
        self._overlay_sublabel_var.set("Please wait...")
        # Do not force indeterminate mode here. Specific tasks should configure the progress bar.
        # This prevents "bouncing" when switching tasks or updating messages.

    def _hide_loading_overlay(self) -> None:
        if self._loading_overlay:
            if self._overlay_progress:
                try:
                    self._overlay_progress.stop()
                except Exception:
                    pass
            try:
                self._loading_overlay.place_forget()
            except Exception:
                pass

    # Old methods removed as requested by user
    # _ensure_progress_popup, _position_progress_popup, _center_window (for popup), _schedule_progress_keepalive
    # _bind_app_visibility_events, _handle_app_visibility_event
    
    def _center_window(self, window: tk.Toplevel, width: int, height: int) -> None:
        """Center a toplevel over the main frame."""
        try:
            self.frame.update_idletasks()
            window.update_idletasks()
            parent_x = self.frame.winfo_rootx()
            parent_y = self.frame.winfo_rooty()
            parent_w = self.frame.winfo_width() or window.winfo_width() or width
            parent_h = self.frame.winfo_height() or window.winfo_height() or height
            x = parent_x + (parent_w - width) // 2
            y = parent_y + (parent_h - height) // 2
            window.geometry(f"{width}x{height}+{x}+{y}")
        except Exception:
            window.geometry(f"{width}x{height}")

    def _format_log_name(self, raw_name: Optional[str], default: str = "Unknown") -> str:
        """Apply display-name mapping while preserving trailing owner tags like "(User)"."""
        text = (raw_name or "").strip()
        if not text:
            return default

        owner = ""
        base = text
        match = re.match(r"^(.*?)(\([^()]*\))$", text)
        if match:
            base = match.group(1).rstrip()
            owner = match.group(2).strip()

        display = base or default
        if hasattr(self, "display_name_manager"):
            try:
                display = self.display_name_manager.get_display_name(display)
            except Exception:
                pass

        return f"{display} {owner}".strip() if owner else display

    def _get_entity_profile(self, fight: parser.Fight, entity_name: str) -> Dict[str, Set[str]]:
        if not entity_name:
            return {"main_ids": set(), "owned_ids": set()}

        fight_key = f"{fight.file_path}::{fight.id}"
        fight_cache = self.entity_profile_cache.setdefault(fight_key, {})
        cached = fight_cache.get(entity_name)
        if cached is not None:
            return cached

        main_ids: Set[str] = set()
        owned_ids: Set[str] = set()

        for ev in fight.events:
            if ev.actor == entity_name:
                actor_id = getattr(ev, "actor_id", None)
                target_id = getattr(ev, "target_id", None)
                if actor_id:
                    main_ids.add(actor_id)
                if target_id and actor_id and actor_id != target_id and ev.target == entity_name:
                    owned_ids.add(target_id)

        owned_ids -= main_ids
        profile = {"main_ids": main_ids, "owned_ids": owned_ids}
        fight_cache[entity_name] = profile
        return profile

    def _describe_entity_label(
        self,
        fight: parser.Fight,
        raw_name: Optional[str],
        entity_id: Optional[str],
    ) -> str:
        label = self._format_log_name(raw_name, default="Unknown")
        if not raw_name or not entity_id:
            return label

        profile = self._get_entity_profile(fight, raw_name)
        owned_ids: Set[str] = profile.get("owned_ids", set())
        if entity_id in owned_ids:
            return f"{label} (Owned object)"
        return label

    def _pretty_source_text(self, text: str) -> str:
        """Improve readability of source strings by spacing separators and parentheses."""
        s = self._format_log_name(text, default="Unknown source")

        s = re.sub(r"(?<=\S)\(", " (", s)
        s = s.replace("|", " | ")
        s = re.sub(r"\s+", " ", s).strip()
        return s

    def _darken_color(self, hex_color: str, factor: float = 0.4) -> str:
        """Darken a hex color by a factor (0.0 to 1.0)."""
        if not hex_color.startswith("#"):
            return hex_color
        try:
            r = int(hex_color[1:3], 16)
            g = int(hex_color[3:5], 16)
            b = int(hex_color[5:7], 16)
            r = int(r * factor)
            g = int(g * factor)
            b = int(b * factor)
            return f"#{r:02x}{g:02x}{b:02x}"
        except Exception:
            return hex_color

    def _init_theme(self) -> None:
        if self._theme_ready:
            return
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass

        bg = self.colors["bg"]
        panel = self.colors["panel"]
        surface = self.colors["surface"]
        border = self.colors["border"]
        accent = self.colors["accent"]
        accent_soft = self.colors["accent_soft"]
        text = self.colors["text"]
        muted = self.colors["muted"]

        style.configure("App.TFrame", background=bg)
        style.configure("Panel.TFrame", background=panel)
        style.configure("TLabel", background=bg, foreground=text)
        style.configure("LabelMuted.TLabel", background=panel, foreground=muted)
        style.configure("LabelStrong.TLabel", background=panel, foreground=text)
        style.configure("Section.TLabel", background=panel, foreground=accent)
        style.configure("PlayerName.TLabel", background=panel, foreground=self.colors["accent_soft"])

        style.configure(
            "Card.TLabelframe",
            background=panel,
            foreground=accent,
            bordercolor=border,
            lightcolor=border,
            darkcolor=border,
        )
        style.configure("Card.TLabelframe.Label", background=panel, foreground=accent)

        style.configure(
            "Filter.TLabelframe",
            background=panel,
            foreground=text,
            bordercolor=border,
            lightcolor=border,
            darkcolor=border,
        )
        style.configure("Filter.TLabelframe.Label", background=panel, foreground=accent)
        style.configure(
            "Filter.TCheckbutton",
            background=panel,
            foreground=text,
            indicatorcolor=text,
            indicatorbackground=surface,
            bordercolor=border,
        )
        style.map(
            "Filter.TCheckbutton",
            background=[("active", panel)],
            foreground=[("active", accent_soft)],
            indicatorcolor=[("selected", text), ("active", text)],
            indicatorbackground=[("selected", border), ("active", surface)],
        )

        style.configure(
            "Accent.TButton",
            background=surface,
            foreground=text,
            bordercolor=accent,
            focusthickness=1,
            focuscolor=accent,
            padding=6,
        )
        style.map(
            "Accent.TButton",
            background=[("pressed", accent), ("active", border)],
            foreground=[("pressed", bg), ("active", accent)],
            bordercolor=[("active", accent_soft)],
        )

        style.configure(
            "TButton",
            background=surface,
            foreground=text,
            bordercolor=border,
            focusthickness=1,
            focuscolor=accent,
            padding=6,
        )
        style.map(
            "TButton",
            background=[("pressed", accent), ("active", border)],
            foreground=[("pressed", bg), ("active", accent)],
        )

        style.configure(
            "TCombobox",
            background=surface,
            foreground=text,
            fieldbackground=surface,
            darkcolor=border,
            lightcolor=border,
            selectbackground=accent,
            selectforeground=bg,
            arrowcolor=accent,
            bordercolor=border,
            padding=5,
        )
        style.map(
            "TCombobox",
            background=[("active", border)],
            fieldbackground=[("active", border)],
            arrowcolor=[("active", accent_soft)],
            bordercolor=[("active", accent)],
        )

        style.configure(
            "Futuristic.TCombobox",
            fieldbackground=surface,
            background=surface,
            foreground=text,
            arrowcolor=accent,
            bordercolor=border,
        )
        style.map(
            "Futuristic.TCombobox",
            fieldbackground=[("readonly", surface), ("active", border)],
            foreground=[("disabled", muted)],
            bordercolor=[("focus", accent), ("active", accent)],
            arrowcolor=[("active", accent_soft)],
        )

        style.configure(
            "Futuristic.Treeview",
            background=surface,
            fieldbackground=surface,
            foreground=text,
            bordercolor=border,
            lightcolor=border,
            darkcolor=border,
            rowheight=22,
        )
        style.map(
            "Futuristic.Treeview",
            background=[("selected", "#1f375f")],
            foreground=[("selected", text)],
        )
        style.configure(
            "Futuristic.Treeview.Heading",
            background=panel,
            foreground=accent,
            bordercolor=border,
            lightcolor=border,
            darkcolor=border,
        )
        style.map(
            "Futuristic.Treeview.Heading",
            background=[("active", surface)],
            foreground=[("active", accent_soft)],
        )

        style.configure(
            "Futuristic.TEntry",
            fieldbackground=surface,
            foreground=text,
            bordercolor=border,
            insertcolor=accent,
        )
        style.map(
            "Futuristic.TEntry",
            foreground=[("disabled", muted)],
            bordercolor=[("focus", accent)],
        )

        style.configure(
            "Futuristic.Vertical.TScrollbar",
            background=panel,
            troughcolor=bg,
            bordercolor=border,
            arrowcolor=accent,
        )
        style.map(
            "Futuristic.Vertical.TScrollbar",
            background=[("active", surface)],
            arrowcolor=[("active", accent_soft)],
        )

        style.configure(
            "Futuristic.Horizontal.TProgressbar",
            troughcolor=panel,
            background=accent,
            bordercolor=border,
            lightcolor=border,
            darkcolor=border,
        )

        # Notebook styling
        style.configure(
            "App.TNotebook",
            background=bg,
            bordercolor=border,
            lightcolor=border,
            darkcolor=border,
            tabmargins=4,
        )
        style.configure(
            "App.TNotebook.Tab",
            background=panel,
            foreground=text,
            lightcolor=border,
            bordercolor=border,
            padding=(12, 8),
        )
        style.map(
            "App.TNotebook.Tab",
            background=[("selected", surface), ("active", surface)],
            foreground=[("selected", accent), ("active", accent_soft)],
            bordercolor=[("selected", accent), ("active", accent)],
            padding=[("selected", (14, 10))],
        )

        self._theme_ready = True

    def _ensure_check_images(self) -> None:
        if self.checkbox_imgs:
            return
        panel = self.colors["panel"]
        border = self.colors["border"]
        fill = self.colors["surface"]
        mark = self.colors["text"]

        def make(on: bool) -> tk.PhotoImage:
            img = tk.PhotoImage(width=16, height=16)
            # Base fill
            img.put(panel, to=(0, 0, 16, 16))
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

        self.checkbox_imgs = {"off": make(False), "on": make(True)}

    def _make_checkbox(self, parent, text: str, var: tk.Variable, command=None) -> tk.Checkbutton:
        self._ensure_check_images()
        chk = tk.Checkbutton(
            parent,
            text=text,
            variable=var,
            command=command,
            image=self.checkbox_imgs["off"] if self.checkbox_imgs else None,
            selectimage=self.checkbox_imgs["on"] if self.checkbox_imgs else None,
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
            bg=self.colors["panel"],
            activebackground=self.colors["panel"],
            fg=self.colors["text"],
            activeforeground=self.colors["text"],
            selectcolor=self.colors["panel"],
        )
        self._style_toggle_button(chk)
        return chk

    def _style_toggle_button(self, widget: tk.Widget) -> None:
        hover_bg = self.colors["surface"]
        hover_fg = self.colors["accent_soft"]
        try:
            base_bg = widget.cget("bg")
        except tk.TclError:
            base_bg = self.colors["panel"]
        try:
            base_fg = widget.cget("fg")
        except tk.TclError:
            base_fg = self.colors["text"]
        try:
            base_active_bg = widget.cget("activebackground")
        except tk.TclError:
            base_active_bg = base_bg
        try:
            base_active_fg = widget.cget("activeforeground")
        except tk.TclError:
            base_active_fg = base_fg

        def on_enter(_event):
            widget.configure(bg=hover_bg, activebackground=hover_bg, fg=hover_fg, activeforeground=hover_fg)

        def on_leave(_event):
            widget.configure(bg=base_bg, activebackground=base_active_bg, fg=base_fg, activeforeground=base_active_fg)

        widget.bind("<Enter>", on_enter, add="+")
        widget.bind("<Leave>", on_leave, add="+")

    def _close_progress_popup(self):
        # Deprecated: usage should be replaced by _hide_loading_overlay
        pass

    def _enable_mousewheel_scroll(self, canvas: tk.Canvas) -> None:
        def _on_enter(_e):
            canvas.bind_all("<MouseWheel>", self._on_mousewheel)
            canvas.bind_all("<Button-4>", self._on_mousewheel)  # Linux scroll up
            canvas.bind_all("<Button-5>", self._on_mousewheel)  # Linux scroll down

        def _on_leave(_e):
            canvas.unbind_all("<MouseWheel>")
            canvas.unbind_all("<Button-4>")
            canvas.unbind_all("<Button-5>")

        canvas.bind("<Enter>", _on_enter)
        canvas.bind("<Leave>", _on_leave)

    def _show_initial_popup(self) -> None:
        # User requested to remove the "loading" screen
        self._initial_popup = None
        self._initial_popup_shown = True
        self._initial_popup_pending = False
        return
        
        # Legacy code below is disabled


    def _close_initial_popup(self) -> None:
        if self._initial_popup and tk.Toplevel.winfo_exists(self._initial_popup):
            try:
                self._initial_popup.destroy()
            except Exception:
                pass
        self._initial_popup = None

    def _on_mousewheel(self, event):
        if not self.teams_canvas:
            return
        if event.num == 4:
            delta = -1
        elif event.num == 5:
            delta = 1
        else:
            delta = -1 * int(event.delta / 120) if event.delta else 0
        if delta:
            self.teams_canvas.yview_scroll(delta, "units")

    def _format_fight_label(self, fight: parser.Fight) -> str:
        base = f"{fight.start.strftime('%d.%m.%Y %H:%M')}" if fight.start else f"{fight.id}"
        raw_mode = getattr(fight, "game_mode", "Unknown")

        friendly_mode = self.GAME_MODE_MAP.get(raw_mode, "")
        has_mapping = raw_mode in self.GAME_MODE_MAP

        duration_str = ""
        actual_secs = getattr(fight, "actual_game_time_sec", None)
        if actual_secs and actual_secs > 0:
            total_seconds = int(round(actual_secs))
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            duration_str = f" - {minutes:02d}:{seconds:02d} min. (log)"
        elif fight.start and fight.end:
            duration = fight.end - fight.start
            total_seconds = int(duration.total_seconds())
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            duration_str = f" - {minutes:02d}:{seconds:02d} min."

        if friendly_mode:
            return f"{base} - {friendly_mode}{duration_str}"

        raw_mode_display = (raw_mode or "").strip()
        if not has_mapping and raw_mode_display and raw_mode_display.lower() != "unknown":
            # Surface the raw log term so new fight types remain identifiable.
            return f"{base} - {raw_mode_display} (log term){duration_str}"

        return f"{base}{duration_str}"

    def _clear_team_frames(self) -> None:
        for frame in self.team_frames.values():
            for child in frame.winfo_children():
                child.destroy()

    def _update_game_mode_menu(self) -> None:
        # Collect all unique game modes
        modes = set()
        for f in self.all_fights:
            mode = getattr(f, "game_mode", "") or "Unknown"
            if not mode:
                mode = "Unknown"
            modes.add(mode)
        
        # Prepare list with display names
        modes_with_names = []
        for mode in modes:
            name = self.GAME_MODE_MAP.get(mode, mode)
            modes_with_names.append((mode, name))
        
        # Sort by display name
        modes_with_names.sort(key=lambda x: x[1])
        
        # Initialize vars for new modes, default to True (unless disabled in config)
        for mode, _ in modes_with_names:
            if mode not in self.game_mode_vars:
                is_enabled = mode not in self.config.disabled_game_modes
                self.game_mode_vars[mode] = tk.BooleanVar(value=is_enabled)
        
        # If popup is open, refresh it
        if self.game_mode_popup and self.game_mode_popup.winfo_exists():
            self._build_game_mode_popup_content()

    def _toggle_game_mode_menu(self):
        if self.game_mode_popup and self.game_mode_popup.winfo_exists():
            self.game_mode_popup.destroy()
            self.game_mode_popup = None
            return

        self.game_mode_popup = tk.Toplevel(self.frame)
        self.game_mode_popup.overrideredirect(True)
        self.game_mode_popup.configure(bg=self.colors["border"])
        
        # Position it
        try:
            x = self.game_mode_btn.winfo_rootx()
            y = self.game_mode_btn.winfo_rooty() + self.game_mode_btn.winfo_height()
            self.game_mode_popup.geometry(f"+{x}+{y}")
        except Exception:
            pass

        self._build_game_mode_popup_content()
        
        # Bind click outside to close (simple version: bind to root)
        # For now, just let user toggle it off with the button

    def _build_game_mode_popup_content(self):
        if not self.game_mode_popup or not self.game_mode_popup.winfo_exists():
            return
            
        for child in self.game_mode_popup.winfo_children():
            child.destroy()
            
        # Inner frame with padding for border effect
        inner = ttk.Frame(self.game_mode_popup, style="Panel.TFrame")
        inner.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        
        # Collect modes again for display order
        modes = set()
        for f in self.all_fights:
            mode = getattr(f, "game_mode", "") or "Unknown"
            if not mode:
                mode = "Unknown"
            modes.add(mode)
            
        modes_with_names = []
        for mode in modes:
            name = self.GAME_MODE_MAP.get(mode, mode)
            modes_with_names.append((mode, name))
        modes_with_names.sort(key=lambda x: x[1])
        
        for mode, name in modes_with_names:
            if mode in self.game_mode_vars:
                cb = self._make_checkbox(
                    inner,
                    name,
                    self.game_mode_vars[mode],
                    self._on_game_mode_toggle
                )
                cb.pack(anchor="w", padx=5, pady=2)

    def _refresh_fight_list(self, preferred_fight_id: Optional[str] = None) -> None:
        filtered = []
        for f in self.all_fights:
            mode = getattr(f, "game_mode", "") or "Unknown"
            if not mode:
                mode = "Unknown"
            
            if mode in self.game_mode_vars and self.game_mode_vars[mode].get():
                filtered.append(f)
        
        self.fights = filtered

        if not self.fight_box:
            if not self.fights:
                self.selected_fight = None
            elif preferred_fight_id:
                for fight in self.fights:
                    if fight.id == preferred_fight_id:
                        self.selected_fight = fight
                        break
            return

        display = [self._format_fight_label(f) for f in self.fights]
        self.fight_box["values"] = display

        if not self.fights:
            self.fight_box.set("")
            self.selected_fight = None
            self._clear_team_frames()
            return

        target_index = 0
        if preferred_fight_id:
            for idx, fight in enumerate(self.fights):
                if fight.id == preferred_fight_id:
                    target_index = idx
                    break

        target_fight = self.fights[target_index]
        self.fight_box.current(target_index)
        if self.selected_fight is not target_fight:
            self._on_fight_change()

    def _on_game_mode_toggle(self) -> None:
        # Update config
        disabled = []
        for mode, var in self.game_mode_vars.items():
            if not var.get():
                disabled.append(mode)
        self.config.disabled_game_modes = disabled
        self.config.save()

        preferred = self.selected_fight.id if self.selected_fight else None
        self._refresh_fight_list(preferred_fight_id=preferred)

    def _on_sort_change(self):
        if self.loading:
            return
        self._render_stats()

    def _is_player_name(self, name: str) -> bool:
        if not name or not name.strip():
            return False
            
        # NPC-XX is always a non-player, even if previously cached differently
        if re.match(r"^NPC\d+$", name, re.IGNORECASE):
            self.player_check_cache[name] = False
            return False

        # Short-circuit cache after hard NPC rule so any stale value gets overwritten
        if name in self.player_check_cache:
            return self.player_check_cache[name]

        if name.upper() == "N/A":
            self.player_check_cache[name] = False
            return False
            
        # Check for obvious non-player patterns
        # 1. Contains parentheses (e.g. Module(Player))
        if "(" in name or ")" in name:
            self.player_check_cache[name] = False
            return False
            
        # 2. Contains multiple spaces (e.g. Player    Ship)
        if "  " in name:
            self.player_check_cache[name] = False
            return False
            
        # 3. Starts with common object prefixes
        lower_name = name.lower()
        if lower_name.startswith("ship_") or lower_name.startswith("module_") or lower_name.startswith("weapon_"):
            self.player_check_cache[name] = False
            return False

        api_result = self._check_player_api(name)
        if api_result is not None:
            self.player_check_cache[name] = api_result
            return api_result
        # On API failure, do not cache so we can retry or ask the user later
        return False

    def _check_player_api(self, name: str) -> Optional[bool]:
        """Return True/False on definitive API answers, None on network/timeout errors so we can ask the user."""
        try:
            encoded_name = urllib.parse.quote(name)
            url = f"https://gmt.star-conflict.com/pubapi/v1/userinfo.php?nickname={encoded_name}"
            # Keep timeout short to avoid long UI blocks and API hammering
            with urllib.request.urlopen(url, timeout=1.0) as response:
                data = json.loads(response.read().decode())

            if data.get("result") == "ok":
                return True
            if data.get("result") == "error" and data.get("text") == "Invalid username/nickname":
                return False
            # Unknown response: be conservative but allow manual resolution
            return None
        except Exception as e:
            # Do not cache failures; report later to the user for manual decision
            print(f"[player-check] API error for {name}: {e}")
            return None

    def _sort_team(self, team: List[str], stats: Dict[str, parser.ParticipantStats]) -> List[str]:
        metric_map = {
            "Damage dealt": "damage_dealt",
            "Damage taken": "damage_taken",
            "Healing": "healing_others",
            "Self-heal": "self_heal",
        }
        metric = metric_map.get(self.sort_by_var.get(), "damage_dealt")
        reverse = self.sort_order_var.get().lower().startswith("desc")
        return sorted(team, key=lambda n: getattr(stats.get(n), metric, 0.0), reverse=reverse)

    def _on_fight_change(self):
        idx = self.fight_box.current()
        if idx < 0 or idx >= len(self.fights):
            return
        self.selected_fight = self.fights[idx]
        self._ensure_players_checked_then_render()

    def _ensure_players_checked_then_render(self):
        if not self.selected_fight:
            return

        # Get all names involved
        cache_key = f"{self.selected_fight.file_path}::{self.selected_fight.id}"
        stats = self.stats_cache.get(cache_key)
        if stats is None:
            stats = parser.aggregate_stats(self.selected_fight)
            self.stats_cache[cache_key] = stats
            
        unknown_names = [n for n in stats.keys() if n not in self.player_check_cache and n.upper() != "N/A"]
        
        if not unknown_names:
            self._render_stats()
            if self.notebook and self.notebook.select() == str(self.pie_tab):
                self._refresh_pie()
            return

        # Start background check
        self._cancel_loading = False
        self._current_check_id += 1
        check_id = self._current_check_id
        self.verifying_players = True
        
        self._set_busy(True, "Verifying player identities...")
        self._overlay_label_var.set("Verifying player identities...")
        if self._overlay_progress:
            # Switch to determinate progress
            self._overlay_progress.stop()
            self._overlay_progress.configure(mode="determinate")
            self._overlay_progress["maximum"] = len(unknown_names)
            self._overlay_progress["value"] = 0
        
        # Force UI update to show popup immediately
        self.app.update_idletasks()
        
        threading.Thread(target=self._check_players_background, args=(unknown_names, check_id), daemon=True).start()

    def _check_players_background(self, names: List[str], check_id: int):
        max_workers = min(4, max(1, (os.cpu_count() or 4)))
        progress_count = 0
        failures: List[str] = []

        pool = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        try:
            future_map = {pool.submit(self._check_player_api, name): name for name in names}
            for future in concurrent.futures.as_completed(future_map):
                if self._cancel_loading or self._current_check_id != check_id:
                    pool.shutdown(wait=False, cancel_futures=True)
                    self.app.after(0, lambda f=list(failures): self._finish_player_check(check_id, f))
                    return
                name = future_map[future]
                try:
                    result = future.result()
                except Exception:
                    result = None
                if result is None:
                    failures.append(name)
                else:
                    self.player_check_cache[name] = bool(result)
                progress_count += 1
                current = progress_count
                self.app.after(0, lambda n=name, v=current: self._update_check_progress(n, v))
        finally:
            pool.shutdown(wait=False, cancel_futures=True)

        self.app.after(0, lambda f=list(failures): self._finish_player_check(check_id, f))

    def _update_check_progress(self, name, value):
        if not self._overlay_progress:
            return
        self._overlay_label_var.set(f"Checking API for: {name}")
        self._overlay_progress["value"] = value

    def _finish_player_check(self, check_id: int, failures: Optional[List[str]] = None):
        if self._current_check_id != check_id:
            return
            
        self.verifying_players = False
        self._set_busy(False, "Ready")
        
        # Save the updated player cache
        self._save_fight_cache()
        
        # If we had API failures, ask the user to classify manually
        if failures:
            names_text = "\n".join(sorted(set(failures)))
            if messagebox.askyesno(
                "Player Check Error",
                "Could not reach the player API for the following names:\n\n"
                f"{names_text}\n\nDo you want to set them manually now?",
            ):
                for name in sorted(set(failures)):
                    choice = messagebox.askyesnocancel(
                        "Set Player Status",
                        f"Treat '{name}' as a player?\nYes = Player, No = Non-player, Cancel = skip",
                    )
                    if choice is True:
                        self.player_check_cache[name] = True
                    elif choice is False:
                        self.player_check_cache[name] = False
                # Save any manual decisions immediately
                self._save_fight_cache()
            else:
                messagebox.showwarning(
                    "Player Check Skipped",
                    "Unresolved names were left uncached; they will be rechecked next time.",
                )

        self._render_stats()
        if self.notebook and self.notebook.select() == str(self.pie_tab):
            self._refresh_pie()

    def _render_stats(self):
        if not self.selected_fight:
            return
        cache_key = f"{self.selected_fight.file_path}::{self.selected_fight.id}"
        stats = self.stats_cache.get(cache_key)
        if stats is None:
            stats = parser.aggregate_stats(self.selected_fight)
            self.stats_cache[cache_key] = stats
        if self.teams_canvas:
            self.teams_canvas.yview_moveto(0)

            is_player = self._is_player_name

            team_a, team_b = self._get_teams(self.selected_fight, stats)
            team_a = self._sort_team(team_a, stats)
            team_b = self._sort_team(team_b, stats)

            winner_team = self._determine_winner(team_a, team_b, stats, self.selected_fight)

            def team_totals(team: List[str]) -> Dict[str, float]:
                return {
                    "damage_dealt": sum(stats[p].damage_dealt for p in team),
                    "damage_taken": sum(stats[p].damage_taken for p in team),
                    "healing_others": sum(stats[p].healing_others for p in team),
                    "self_heal": sum(stats[p].self_heal for p in team),
                }

            totals_a = team_totals(team_a)
            totals_b = team_totals(team_b)

            self._render_team_panel("A", "Team A", team_a, stats, totals_a, self.selected_fight, is_player, winner_team)
            self._render_team_panel("B", "Team B", team_b, stats, totals_b, self.selected_fight, is_player, winner_team)


    def _persist_username(self):
        name = self.username_var.get().strip()
        if name == self.config.username:
            return
        self.config.username = name
        try:
            self.config.save()
        except Exception:
            pass

    def _open_breakdown_window(self, player: str, fight: parser.Fight, is_player) -> None:
        top = tk.Toplevel(self.frame)
        top.title(f"{player} Breakdown")
        top.transient(self.frame)
        top.grab_set()
        self._center_window(top, width=900, height=720)
        top.configure(bg=self.colors["bg"])

        # Collect sources from player's outgoing damage events
        player_sources = []
        seen_sources = set()
        for ev in fight.events:
            if ev.actor != player or ev.event_type != "damage":
                continue
            label = ev.source.strip() or "Unknown source"
            if label not in seen_sources:
                seen_sources.add(label)
                player_sources.append(label)
        player_sources.sort()

        # State for selected sources
        source_vars: Dict[str, tk.BooleanVar] = {s: tk.BooleanVar(value=True) for s in player_sources}
        received_mode_var = tk.StringVar(value="total")

        self._ensure_check_images()

        def selected_sources() -> Optional[Set[str]]:
            if not source_vars:
                return None
            return {s for s, var in source_vars.items() if var.get()}

        def refresh():
            data = self._compute_breakdown(player, fight, selected_sources())
            self._populate_tree(damage_tree, data["damage"])
            self._populate_tree(healing_tree, data["healing"])
            
            # Handle Received Data View
            recv_raw = data["received"] # List[(attacker, source, amount, pct)]
            if received_mode_var.get() == "total":
                # Aggregate by attacker
                agg = {}
                total_val = 0.0
                for row in recv_raw:
                    atk = row[0]
                    val = row[2]
                    agg[atk] = agg.get(atk, 0.0) + val
                    total_val += val
                
                # Rebuild rows: (attacker, source, amount, pct)
                # We'll set source to "" or "All"
                new_rows = []
                if total_val > 0:
                    # Sort by amount desc
                    sorted_agg = sorted(agg.items(), key=lambda x: x[1], reverse=True)
                    for atk, val in sorted_agg:
                        new_rows.append((atk, "", val, val / total_val * 100.0))
                self._populate_tree(received_tree, new_rows)
            else:
                self._populate_tree(received_tree, recv_raw)

            totals_var.set(
                f"Damage dealt: {data['damage_total']:.0f} | Healing: {data['healing_total']:.0f} | Damage received: {data['received_total']:.0f}"
            )

        header = ttk.Label(top, text=f"Damage / Healing Breakdown for {player}", font=("Segoe UI", 10, "bold"), style="Section.TLabel")
        header.pack(anchor=tk.W, padx=10, pady=(10, 4))

        filters = ttk.Labelframe(top, text="Sources (Outgoing)", padding=6, style="Filter.TLabelframe")
        filters.pack(fill=tk.X, padx=10, pady=(0, 6))
        if player_sources:
            controls = ttk.Frame(filters, style="Panel.TFrame")
            controls.pack(fill=tk.X, pady=(0, 6))

            def _set_all_sources(value: bool) -> None:
                for var in source_vars.values():
                    var.set(value)
                refresh()

            ttk.Button(controls, text="Select All", command=lambda: _set_all_sources(True), style="Accent.TButton").pack(side=tk.LEFT, padx=(0, 6))
            ttk.Button(controls, text="Unselect All", command=lambda: _set_all_sources(False), style="Accent.TButton").pack(side=tk.LEFT)

            list_frame = ttk.Frame(filters, style="Panel.TFrame")
            list_frame.pack(fill=tk.X)
            cols = 2
            for idx, src in enumerate(player_sources):
                var = source_vars[src]
                chk = tk.Checkbutton(
                    list_frame,
                    text=self._pretty_source_text(src),
                    variable=var,
                    command=lambda: refresh(),
                    image=self.checkbox_imgs["off"] if self.checkbox_imgs else None,
                    selectimage=self.checkbox_imgs["on"] if self.checkbox_imgs else None,
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
                    bg=self.colors["panel"],
                    activebackground=self.colors["panel"],
                    fg=self.colors["text"],
                    activeforeground=self.colors["text"],
                    selectcolor=self.colors["panel"],
                )
                self._style_toggle_button(chk)
                chk.grid(row=idx // cols, column=idx % cols, sticky="w", padx=4, pady=2)
            for c in range(cols):
                list_frame.columnconfigure(c, weight=1)
        else:
            ttk.Label(filters, text="No source info found; all damage shown").pack(anchor=tk.W)

        container = ttk.Frame(top, padding=10, style="App.TFrame")
        container.pack(fill=tk.BOTH, expand=True)
        container.columnconfigure(0, weight=1)
        container.columnconfigure(1, weight=1)
        container.rowconfigure(0, weight=1)
        # Row 1 is for controls, Row 2 for received tree
        container.rowconfigure(2, weight=1)

        damage_tree = self._build_breakdown_table(
            container,
            0,
            "Damage Dealt",
            height=10,
            columns=("name", "amount", "pct"),
            sort_types=("str", "num", "pct"),
        )
        healing_tree = self._build_breakdown_table(
            container,
            1,
            "Healing Dealt",
            height=10,
            columns=("name", "amount", "pct"),
            sort_types=("str", "num", "pct"),
        )

        # Received Damage Controls
        recv_controls = ttk.Frame(container, style="App.TFrame")
        recv_controls.grid(row=1, column=0, columnspan=2, sticky="w", pady=(10, 0))
        
        ttk.Label(recv_controls, text="Received Damage by:", style="LabelMuted.TLabel").pack(side=tk.LEFT, padx=(4, 8))
        
        # Using Checkbuttons that behave like Radios as requested ("2 checkboxes")
        # But implementing as Radiobuttons for correct behavior
        self._ensure_check_images()
        modal_total_btn = tk.Radiobutton(
            recv_controls,
            text="Total damage (Player)",
            variable=received_mode_var,
            value="total",
            command=refresh,
            image=self.checkbox_imgs["off"],
            selectimage=self.checkbox_imgs["on"],
            compound="left",
            indicatoron=False,
            bd=0,
            relief="flat",
            highlightthickness=0,
            padx=4,
            pady=2,
            anchor="w",
            bg=self.colors["panel"],
            activebackground=self.colors["panel"],
            fg=self.colors["text"],
            activeforeground=self.colors["text"],
            selectcolor=self.colors["panel"],
        )
        self._style_toggle_button(modal_total_btn)
        modal_total_btn.pack(side=tk.LEFT, padx=8)

        modal_source_btn = tk.Radiobutton(
            recv_controls,
            text="Source",
            variable=received_mode_var,
            value="source",
            command=refresh,
            image=self.checkbox_imgs["off"],
            selectimage=self.checkbox_imgs["on"],
            compound="left",
            indicatoron=False,
            bd=0,
            relief="flat",
            highlightthickness=0,
            padx=4,
            pady=2,
            anchor="w",
            bg=self.colors["panel"],
            activebackground=self.colors["panel"],
            fg=self.colors["text"],
            activeforeground=self.colors["text"],
            selectcolor=self.colors["panel"],
        )
        self._style_toggle_button(modal_source_btn)
        modal_source_btn.pack(side=tk.LEFT, padx=8)

        received_tree = self._build_breakdown_table(
            container,
            0,
            "Damage Received",
            height=10,
            row=2,
            col_span=2,
            columns=("attacker", "source", "amount", "pct"),
            headings=("Attacker", "Source", "Amount", "% of total"),
            widths=(150, 220, 90, 90),
            sort_types=("str", "str", "num", "pct"),
        )

        totals_var = tk.StringVar(value="")
        ttk.Label(top, textvariable=totals_var, style="LabelStrong.TLabel").pack(anchor=tk.W, padx=10, pady=(0, 6))
        ttk.Button(top, text="Close", command=top.destroy, style="Accent.TButton").pack(pady=(0, 10))

        refresh()

    def _build_breakdown_table(
        self,
        parent: ttk.Frame,
        col: int,
        title: str,
        height: int = 12,
        row: int = 0,
        col_span: int = 1,
        columns: Tuple[str, ...] = ("name", "amount", "pct"),
        headings: Tuple[str, ...] = ("Name", "Amount", "% of total"),
        widths: Tuple[int, ...] = (200, 90, 90),
        sort_types: Tuple[str, ...] = ("str", "num", "pct"),
        style_name: str = "Card.TLabelframe",
    ) -> ttk.Treeview:
        frame = ttk.Labelframe(parent, text=title, padding=6, style=style_name)
        frame.grid(row=row, column=col, columnspan=col_span, sticky="nsew", padx=4, pady=4)
        for c in range(col, col + col_span):
            parent.columnconfigure(c, weight=1)
        parent.rowconfigure(row, weight=1)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)

        tree = ttk.Treeview(frame, columns=columns, show="headings", height=height, style="Futuristic.Treeview")
        col_types = list(sort_types) + ["str"] * max(0, len(columns) - len(sort_types))
        self.tree_sort_types[tree] = {}
        self.tree_heading_labels[tree] = {}
        for name, heading, width, col_type in zip(columns, headings, widths, col_types):
            self.tree_sort_types[tree][name] = col_type
            self.tree_heading_labels[tree][name] = heading
            tree.heading(name, text=heading, command=lambda n=name, ct=col_type: self._sort_tree(tree, n, ct))
            tree.column(
                name,
                width=width,
                anchor=tk.W if name in ("name", "attacker", "source", "healer", "target") else tk.E,
            )

        vsb = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=tree.yview, style="Futuristic.Vertical.TScrollbar")
        tree.configure(yscrollcommand=vsb.set)
        tree.grid(row=1, column=0, sticky="nsew")
        vsb.grid(row=1, column=1, sticky="ns")
        tree.bind("<Destroy>", lambda _e, t=tree: self._teardown_tree_sorting(t))
        return tree

    def _set_tree_display_columns(self, tree: Optional[ttk.Treeview], columns: Tuple[str, ...]) -> None:
        if not tree:
            return
        try:
            tree.configure(displaycolumns=columns)
        except tk.TclError:
            return

        width_map = {
            "target": 170,
            "source": 220,
            "amount": 100,
            "pct": 80,
            "attacker": 160,
            "healer": 160,
        }
        anchor_left = {"name", "attacker", "source", "healer", "target"}

        for col in tree["columns"]:
            width = width_map.get(col, 120)
            stretch = col in {"target", "source", "attacker", "healer"} and col in columns
            tree.column(
                col,
                width=width,
                stretch=stretch,
                anchor=tk.W if col in anchor_left else tk.E,
            )

        if "target" in columns and "source" not in columns:
            tree.column("target", width=260, stretch=True)

    def _aggregate_source_rows(
        self,
        rows: List[Tuple[str, str, float, float]],
        total: float,
    ) -> List[Tuple[str, str, float, float]]:
        if total <= 0:
            return []
        agg: Dict[str, float] = {}
        for row in rows:
            if len(row) < 4:
                continue
            label = row[1] or "Unknown source"
            agg[label] = agg.get(label, 0.0) + row[2]
        sorted_rows = sorted(agg.items(), key=lambda kv: kv[1], reverse=True)
        result = []
        for label, amount in sorted_rows:
            pct = (amount / total * 100.0) if total > 0 else 0.0
            result.append(("", label, amount, pct))
        return result

    def _populate_tree(self, tree: Optional[ttk.Treeview], rows: List[Tuple]) -> None:
        if tree is None:
            return
        tree.delete(*tree.get_children())
        if not rows:
            columns = tree["columns"] if tree["columns"] else ()
            if not columns:
                return
            placeholder = []
            last_idx = len(columns) - 1
            for idx, _col in enumerate(columns):
                if idx == 0:
                    placeholder.append("No data")
                elif idx == last_idx:
                    placeholder.append("0.0%")
                else:
                    placeholder.append("0")
            tree.insert("", tk.END, values=tuple(placeholder))
            return
        for row in rows:
            if len(row) == 3:
                name, amount, pct = row
                tree.insert("", tk.END, values=(name, f"{amount:.0f}", f"{pct:.1f}%"))
            elif len(row) == 4:
                attacker, source, amount, pct = row
                tree.insert("", tk.END, values=(attacker, source, f"{amount:.0f}", f"{pct:.1f}%"))
        self._apply_saved_sort(tree)

    def _apply_saved_sort(self, tree: ttk.Treeview) -> None:
        state = self.tree_sort_states.get(tree)
        if not state:
            return
        col, reverse = state
        col_type = self.tree_sort_types.get(tree, {}).get(col, "str")
        self._sort_tree(tree, col, col_type, toggle=False, force_reverse=reverse)

    def _sort_tree(
        self,
        tree: ttk.Treeview,
        col: str,
        col_type: str,
        toggle: bool = True,
        force_reverse: Optional[bool] = None,
    ) -> None:
        items = list(tree.get_children(""))
        if not items:
            return

        def parse_val(val: str):
            try:
                if col_type == "num":
                    return float(str(val).replace("%", "").replace(",", "").strip())
                if col_type == "pct":
                    return float(str(val).replace("%", "").replace(",", "").strip())
            except Exception:
                return 0.0
            return str(val).lower()

        prev_col, prev_reverse = self.tree_sort_states.get(tree, (None, True))
        if force_reverse is not None:
            reverse = force_reverse
        elif prev_col == col:
            reverse = (not prev_reverse) if toggle else prev_reverse
        else:
            reverse = True

        items.sort(key=lambda iid: parse_val(tree.set(iid, col)), reverse=reverse)
        for idx, iid in enumerate(items):
            tree.move(iid, "", idx)

        self.tree_sort_states[tree] = (col, reverse)
        self._update_heading_labels(tree, col, reverse)

    def _update_heading_labels(self, tree: ttk.Treeview, active_col: str, reverse: bool) -> None:
        labels = self.tree_heading_labels.get(tree, {})
        for col, base in labels.items():
            suffix = ""
            if col == active_col:
                suffix = " ↓" if reverse else " ↑"
            tree.heading(col, text=f"{base}{suffix}")

    def _teardown_tree_sorting(self, tree: ttk.Treeview) -> None:
        self.tree_sort_states.pop(tree, None)
        self.tree_sort_types.pop(tree, None)
        self.tree_heading_labels.pop(tree, None)

    def _compute_breakdown(
        self,
        player: str,
        fight: parser.Fight,
        allowed_sources: Optional[Set[str]],
    ) -> Dict[str, object]:
        dmg: Dict[str, float] = {}
        heal: Dict[str, float] = {}
        dmg_detail: Dict[Tuple[str, str], float] = {}
        heal_detail: Dict[Tuple[str, str], float] = {}
        received: Dict[Tuple[str, str], float] = {}
        healing_received: Dict[Tuple[str, str], float] = {}
        dmg_total = 0.0
        heal_total = 0.0
        received_total = 0.0
        healing_received_total = 0.0

        def clean(name: str) -> str:
            return self._format_log_name(name, default="Unknown")

        def describe_target(name: str, entity_id: Optional[str]) -> str:
            return self._describe_entity_label(fight, name, entity_id)

        def source_label(ev: parser.CombatEvent) -> str:
            return ev.source.strip() or "Unknown source"

        allowed = allowed_sources if allowed_sources else None
        
        include_player = self.pie_target_player_var.get()
        include_rest = self.pie_target_rest_var.get()

        def is_allowed_entity(raw_name: Optional[str]) -> bool:
            candidate = (raw_name or "").strip()
            if not candidate:
                return include_rest
            is_p = self._is_player_name(candidate)
            if is_p and include_player:
                return True
            if not is_p and include_rest:
                return True
            return False

        include_self_heal = self._should_include_self_heal()

        for ev in fight.events:
            is_self_heal_event = self._is_self_heal_event(ev)
            if ev.actor == player and ev.event_type == "damage":
                src = source_label(ev)
                src_ok = True if allowed is None else src in allowed
                if not src_ok:
                    continue
                if not is_allowed_entity(ev.target):
                    continue
                tgt = describe_target(ev.target, getattr(ev, "target_id", None))
                dmg_total += ev.amount
                dmg[tgt] = dmg.get(tgt, 0.0) + ev.amount
                dmg_detail[(tgt, src)] = dmg_detail.get((tgt, src), 0.0) + ev.amount
            elif ev.actor == player and ev.event_type == "healing":
                if not include_self_heal and is_self_heal_event:
                    continue
                if not is_allowed_entity(ev.target):
                    continue
                tgt = describe_target(ev.target, getattr(ev, "target_id", None))
                src = source_label(ev)
                src_ok = True if allowed is None else src in allowed
                if not src_ok:
                    continue
                heal_total += ev.amount
                heal[tgt] = heal.get(tgt, 0.0) + ev.amount
                heal_detail[(tgt, src)] = heal_detail.get((tgt, src), 0.0) + ev.amount
            if ev.target == player and ev.event_type == "damage":
                if not is_allowed_entity(ev.actor):
                    continue
                attacker = clean(ev.actor)
                target_label = describe_target(ev.target, getattr(ev, "target_id", None))
                base_target = clean(ev.target)
                attacker_display = attacker if target_label == base_target else f"{attacker} → {target_label}"
                src = source_label(ev)
                src_norm = src.lower().strip().strip("() ")
                if "crash" in src_norm or src_norm == "collision":
                    attacker_display = "Collision"
                    src = "Collision"
                received_total += ev.amount
                received[(attacker_display, src)] = received.get((attacker_display, src), 0.0) + ev.amount
            elif ev.target == player and ev.event_type == "healing":
                if not include_self_heal and is_self_heal_event:
                    continue
                if not is_allowed_entity(ev.actor):
                    continue
                healer = clean(ev.actor)
                target_label = describe_target(ev.target, getattr(ev, "target_id", None))
                base_target = clean(ev.target)
                healer_display = healer if target_label == base_target else f"{healer} → {target_label}"
                src = source_label(ev)
                healing_received_total += ev.amount
                healing_received[(healer_display, src)] = healing_received.get((healer_display, src), 0.0) + ev.amount

        def to_rows_kv(data: Dict[str, float], total: float) -> List[Tuple[str, float, float]]:
            if total <= 0:
                return []
            return sorted([(k, v, v / total * 100.0) for k, v in data.items()], key=lambda x: x[1], reverse=True)

        def to_rows_tuple(data: Dict[Tuple[str, str], float], total: float) -> List[Tuple[str, str, float, float]]:
            if total <= 0:
                return []
            return sorted(
                [(atk, self._pretty_source_text(src), v, v / total * 100.0) for (atk, src), v in data.items()],
                key=lambda x: x[2],
                reverse=True,
            )

        return {
            "damage": to_rows_kv(dmg, dmg_total),
            "healing": to_rows_kv(heal, heal_total),
            "received": to_rows_tuple(received, received_total),
            "healing_received": to_rows_tuple(healing_received, healing_received_total),
            "damage_detail": to_rows_tuple(dmg_detail, dmg_total),
            "healing_detail": to_rows_tuple(heal_detail, heal_total),
            "damage_total": dmg_total,
            "healing_total": heal_total,
            "received_total": received_total,
            "healing_received_total": healing_received_total,
        }

    def _load_fight_cache(self) -> None:
        if not self.cache_file.exists():
            return
        try:
            with open(self.cache_file, "rb") as f:
                data = pickle.load(f)
            if not isinstance(data, dict):
                return
            if data.get("version") != self.fight_cache_version:
                return
            entries = data.get("entries")
            if isinstance(entries, dict):
                self.fight_cache = entries
            
            # Load player cache
            player_cache = data.get("player_cache")
            if isinstance(player_cache, dict):
                self.player_check_cache = player_cache
        except Exception as e:
            print(f"Error loading cache: {e}")
            self.fight_cache = {}
            self.player_check_cache = {}

    def _save_fight_cache(self) -> None:
        # Snapshot data on the calling thread to avoid concurrency issues
        payload = {
            "version": self.fight_cache_version,
            "entries": self.fight_cache.copy(),
            "player_cache": self.player_check_cache.copy(),
        }
        
        def worker(data):
            with self._cache_lock:
                try:
                    self.cache_file.parent.mkdir(parents=True, exist_ok=True)
                    temp_file = self.cache_file.with_suffix(".tmp")
                    
                    # Ensure temp file is gone
                    if temp_file.exists():
                        try:
                            temp_file.unlink()
                        except OSError:
                            pass

                    with open(temp_file, "wb") as f:
                        pickle.dump(data, f)
                    
                    # Safe replace for Windows
                    if self.cache_file.exists():
                        try:
                            self.cache_file.unlink()
                        except OSError:
                            pass # If we can't delete, replace might fail too, but let's try
                    
                    temp_file.replace(self.cache_file)
                except Exception as e:
                    print(f"Error saving cache: {e}")

        threading.Thread(target=worker, args=(payload,), daemon=True).start()

    def _open_display_name_editor(self):
        if self._display_names_window and tk.Toplevel.winfo_exists(self._display_names_window):
            self._display_names_window.deiconify()
            self._display_names_window.lift()
            try:
                self._display_names_window.focus_force()
            except Exception:
                pass
            return

        win = tk.Toplevel(self.frame)
        win.withdraw()
        self._display_names_window = win
        win.title("Display Name Editor")
        win.geometry("800x600")
        win.configure(bg=self.colors["bg"])
        win.transient(self.app)
        win.lift(self.app)

        def _on_close():
            self._display_names_window = None
            win.destroy()
        win.protocol("WM_DELETE_WINDOW", _on_close)

        top = ttk.Frame(win, padding=10, style="Panel.TFrame")
        top.pack(fill=tk.X)
        top.columnconfigure(4, weight=1)

        hide_assigned_var = tk.BooleanVar(value=False)
        show_current_only_var = tk.BooleanVar(value=False)
        search_var = tk.StringVar()
        log_var = tk.StringVar()
        disp_var = tk.StringVar()
        refresh_job_id: Optional[str] = None

        tree_frame = ttk.Frame(win, style="Panel.TFrame", padding=10)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        tree = ttk.Treeview(
            tree_frame,
            columns=("log", "display"),
            show="headings",
            style="Futuristic.Treeview",
            selectmode="browse",
        )
        tree.heading("log", text="Log Name", anchor="w")
        tree.heading("display", text="Display Name", anchor="w")
        tree.column("log", width=360, anchor="w")
        tree.column("display", width=360, anchor="w")

        vsb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview, style="Futuristic.Vertical.TScrollbar")
        tree.configure(yscrollcommand=vsb.set)

        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        def refresh():
            mappings = self.display_name_manager.get_all_mappings()
            log_filter = search_var.get().strip().lower()
            selected_log = log_var.get()

            items: Set[str] = set(mappings.keys())

            def add_candidate(raw_value: Optional[str], bucket: Set[str]) -> None:
                text = (raw_value or "").strip()
                if not text:
                    return
                lowered = text.lower()
                if "totaldamage" in lowered or "mostdamagewith" in lowered:
                    return
                bucket.add(text)

            def harvest_from_fight(fight_obj: parser.Fight, bucket: Set[str]):
                for event in fight_obj.events:
                    add_candidate(event.source, bucket)
                    if event.event_type == "ship_info":
                        add_candidate(event.source, bucket)
                    add_candidate(event.actor, bucket)
                    add_candidate(event.target, bucket)

            for fight_obj in self.all_fights:
                harvest_from_fight(fight_obj, items)

            current_fight_names: Set[str] = set()
            if self.selected_fight:
                harvest_from_fight(self.selected_fight, current_fight_names)

            items = {name for name in items if name}

            for child in tree.get_children():
                tree.delete(child)

            restored_selection: Optional[str] = None
            for name in sorted(items, key=lambda value: value.lower()):
                disp_value = mappings.get(name, "")
                has_disp = name in mappings and disp_value != ""
                if hide_assigned_var.get() and has_disp:
                    continue

                if show_current_only_var.get() and self.selected_fight:
                    if current_fight_names and name not in current_fight_names:
                        continue

                if log_filter:
                    composite = f"{name} {disp_value}".lower()
                    if log_filter not in composite:
                        continue

                node_id = tree.insert("", "end", values=(name, disp_value if has_disp else ""))
                if name == selected_log:
                    restored_selection = node_id

            if restored_selection:
                tree.selection_set(restored_selection)
                tree.see(restored_selection)
            else:
                current = tree.selection()
                if current:
                    tree.selection_remove(*current)
                log_var.set("")
                disp_var.set("")

        self._ensure_check_images()

        def add_toggle(text: str, variable: tk.BooleanVar, column: int) -> None:
            chk = tk.Checkbutton(
                top,
                text=text,
                variable=variable,
                command=refresh,
                image=self.checkbox_imgs["off"],
                selectimage=self.checkbox_imgs["on"],
                compound="left",
                indicatoron=False,
                bd=0,
                relief="flat",
                highlightthickness=0,
                padx=4,
                pady=2,
                anchor="w",
                bg=self.colors["panel"],
                activebackground=self.colors["panel"],
                fg=self.colors["text"],
                activeforeground=self.colors["text"],
                selectcolor=self.colors["panel"],
            )
            self._style_toggle_button(chk)
            chk.grid(row=0, column=column, sticky="w", padx=(0, 12))

        add_toggle("Hide assigned", hide_assigned_var, 0)
        add_toggle("Current fight only", show_current_only_var, 1)

        ttk.Button(top, text="Refresh", command=refresh, style="TButton").grid(row=0, column=2, padx=(10, 0))
        ttk.Label(top, text="Search:", style="LabelMuted.TLabel").grid(row=0, column=3, sticky="e", padx=(20, 6))

        search_entry = ttk.Entry(top, textvariable=search_var, style="Futuristic.TEntry")
        search_entry.grid(row=0, column=4, sticky="ew")

        button_bar = ttk.Frame(top, style="Panel.TFrame")
        button_bar.grid(row=1, column=0, columnspan=5, sticky="w", pady=(8, 0))
        ttk.Button(button_bar, text="Export...", command=lambda: export_display_names(), style="Accent.TButton").pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(button_bar, text="Import...", command=lambda: import_display_names(), style="Accent.TButton").pack(side=tk.LEFT)

        def schedule_refresh(immediate: bool = False) -> None:
            nonlocal refresh_job_id
            if refresh_job_id:
                try:
                    win.after_cancel(refresh_job_id)
                except Exception:
                    pass
                refresh_job_id = None
            if immediate:
                refresh()
            else:
                refresh_job_id = win.after(200, refresh)

        search_var.trace_add("write", lambda *_: schedule_refresh())

        edit_frame = ttk.Frame(win, padding=10, style="Panel.TFrame")
        edit_frame.pack(fill=tk.X)
        edit_frame.columnconfigure(1, weight=1)
        
        ttk.Label(edit_frame, text="Log Name:", style="LabelMuted.TLabel").grid(row=0, column=0, sticky="w")
        e_log = ttk.Entry(edit_frame, textvariable=log_var, state="readonly", style="Futuristic.TEntry")
        e_log.grid(row=0, column=1, sticky="ew", padx=5)
        
        ttk.Label(edit_frame, text="Display Name:", style="LabelMuted.TLabel").grid(row=1, column=0, sticky="w")
        e_disp = ttk.Entry(edit_frame, textvariable=disp_var, style="Futuristic.TEntry")
        e_disp.grid(row=1, column=1, sticky="ew", padx=5)
        
        def on_select(_event):
            sel = tree.selection()
            if not sel:
                return
            values = tree.item(sel[0], "values")
            log_var.set(values[0])
            disp_var.set(values[1])

        tree.bind("<<TreeviewSelect>>", on_select)
        
        def save():
            log_name = log_var.get()
            disp_name = disp_var.get().strip()
            if not log_name:
                return
            self.display_name_manager.set_display_name(log_name, disp_name)
            refresh()
        
        ttk.Button(edit_frame, text="Save", command=save, style="Accent.TButton").grid(row=2, column=1, sticky="w", padx=5, pady=10)

        def export_display_names():
            path = filedialog.asksaveasfilename(
                title="Export Display Names",
                defaultextension=".json",
                filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
                initialfile="display_names.json",
            )
            if not path:
                return
            try:
                self.display_name_manager.export(Path(path))
                messagebox.showinfo("Export Complete", f"Display names exported to\n{path}")
            except Exception as exc:
                messagebox.showerror("Export Failed", f"Could not export display names:\n{exc}")

        def import_display_names():
            path = filedialog.askopenfilename(
                title="Import Display Names",
                filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
            )
            if not path:
                return
            try:
                with open(path, "r", encoding="utf-8") as f:
                    incoming = json.load(f)
            except Exception as exc:
                messagebox.showerror("Import Failed", f"Could not read file:\n{exc}")
                return

            if not isinstance(incoming, dict):
                messagebox.showerror("Import Failed", "Selected file does not contain a mapping object.")
                return

            normalized = {}
            for key, value in incoming.items():
                if not isinstance(key, str):
                    continue
                if not isinstance(value, str):
                    continue
                cleaned_key = key.strip()
                if not cleaned_key:
                    continue
                normalized[cleaned_key] = value.strip()

            if not normalized:
                messagebox.showinfo("Import Display Names", "No valid entries found in the selected file.")
                return

            existing = self.display_name_manager.get_all_mappings()
            pending_updates: Dict[str, str] = {}
            conflicts: Dict[str, Tuple[str, str]] = {}

            for key, value in normalized.items():
                if key not in existing:
                    pending_updates[key] = value
                elif existing[key] != value:
                    conflicts[key] = (existing[key], value)

            if conflicts:
                decisions = prompt_conflict_resolution(conflicts)
                if decisions is None:
                    return
                for key, action in decisions.items():
                    if action == "overwrite":
                        pending_updates[key] = normalized[key]
                    # skip leaves entry untouched

            if not pending_updates:
                messagebox.showinfo("Import Display Names", "Nothing to import; all entries already exist.")
                return

            applied = self.display_name_manager.bulk_update(pending_updates)
            refresh()
            messagebox.showinfo("Import Complete", f"Applied {applied} entries from import.")

        def prompt_conflict_resolution(conflicts: Dict[str, Tuple[str, str]]) -> Optional[Dict[str, str]]:
            dialog = tk.Toplevel(win)
            dialog.title("Resolve Conflicts")
            dialog.configure(bg=self.colors["bg"])
            self._center_window(dialog, width=700, height=420)
            dialog.grab_set()

            container = ttk.Frame(dialog, padding=10, style="Panel.TFrame")
            container.pack(fill=tk.BOTH, expand=True)

            ttk.Label(container, text="Choose how to handle existing entries: ", style="LabelMuted.TLabel").pack(anchor=tk.W, pady=(0, 8))

            canvas = tk.Canvas(container, highlightthickness=0, bg=self.colors["panel"])
            vsb = ttk.Scrollbar(container, orient=tk.VERTICAL, command=canvas.yview, style="Futuristic.Vertical.TScrollbar")
            canvas.configure(yscrollcommand=vsb.set)
            canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            vsb.pack(side=tk.RIGHT, fill=tk.Y)

            inner = ttk.Frame(canvas, style="Panel.TFrame")
            inner_id = canvas.create_window((0, 0), window=inner, anchor="nw")

            def _on_inner_config(event):
                canvas.configure(scrollregion=canvas.bbox("all"))

            def _on_canvas_config(event):
                canvas.itemconfigure(inner_id, width=event.width)

            inner.bind("<Configure>", _on_inner_config)
            canvas.bind("<Configure>", _on_canvas_config)

            headings = ("Log Name", "Current", "Incoming", "Action")
            for col, heading in enumerate(headings):
                ttk.Label(inner, text=heading, style="LabelStrong.TLabel").grid(row=0, column=col, sticky="w", padx=4, pady=(0, 4))

            action_vars: Dict[str, tk.StringVar] = {}
            options = ("overwrite", "skip")
            for row, (log_name, (current_val, new_val)) in enumerate(sorted(conflicts.items()), start=1):
                ttk.Label(inner, text=log_name, style="LabelMuted.TLabel").grid(row=row, column=0, sticky="w", padx=4, pady=2)
                ttk.Label(inner, text=current_val, style="TLabel").grid(row=row, column=1, sticky="w", padx=4, pady=2)
                ttk.Label(inner, text=new_val, style="TLabel").grid(row=row, column=2, sticky="w", padx=4, pady=2)
                var = tk.StringVar(value="overwrite")
                action_vars[log_name] = var
                combo = ttk.Combobox(
                    inner,
                    textvariable=var,
                    state="readonly",
                    values=["overwrite", "skip"],
                    width=10,
                    style="Futuristic.TCombobox",
                )
                combo.grid(row=row, column=3, sticky="w", padx=4, pady=2)

            result: Dict[str, str] = {}

            def apply_and_close():
                for key, var in action_vars.items():
                    result[key] = var.get()
                dialog.destroy()

            def cancel_and_close():
                result.clear()
                dialog.destroy()

            buttons = ttk.Frame(container, style="Panel.TFrame")
            buttons.pack(fill=tk.X, pady=(10, 0))
            ttk.Button(buttons, text="Cancel", command=cancel_and_close, style="TButton").pack(side=tk.RIGHT, padx=(6, 0))
            ttk.Button(buttons, text="Apply", command=apply_and_close, style="Accent.TButton").pack(side=tk.RIGHT)

            dialog.wait_window()
            return result or None

        refresh()
        self._center_window(win, width=800, height=600)
        win.deiconify()

