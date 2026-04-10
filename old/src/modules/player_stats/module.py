import tkinter as tk
from tkinter import ttk, messagebox
import urllib.request
import urllib.parse
import json
import threading
import math
from typing import Dict, List, Optional, Any

from ...config import AppConfig
from ..base import BaseModule

class PlayerStatsModule(BaseModule):
    name = "Player Stats"
    description = "View and compare player statistics from Star Conflict API."

    def __init__(self, app, config: AppConfig):
        self.app = app
        self.config = config
        self.frame: Optional[ttk.Frame] = None
        self.players_data: List[Dict[str, Any]] = []
        self.max_players = 4
        self.loading = False
        
        # UI Elements
        self.input_var = tk.StringVar()
        self.cards_container: Optional[ttk.Frame] = None
        self.add_btn: Optional[ttk.Button] = None

    def build(self, parent):
        self.frame = ttk.Frame(parent, style="App.TFrame")
        
        # Control Panel
        control_panel = ttk.Frame(self.frame, style="Panel.TFrame", padding=10)
        control_panel.pack(fill=tk.X, pady=(0, 20))
        
        ttk.Label(control_panel, text="Nickname:", style="LabelMuted.TLabel").pack(side=tk.LEFT, padx=(0, 10))
        
        entry = ttk.Entry(control_panel, textvariable=self.input_var, width=30)
        entry.pack(side=tk.LEFT, padx=(0, 10))
        entry.bind("<Return>", lambda e: self.add_player())
        
        self.add_btn = ttk.Button(control_panel, text="Add Player", command=self.add_player, style="Accent.TButton")
        self.add_btn.pack(side=tk.LEFT)
        
        ttk.Button(control_panel, text="Clear All", command=self.clear_all).pack(side=tk.LEFT, padx=10)

        # Stats Container
        self.cards_container = ttk.Frame(self.frame, style="App.TFrame")
        self.cards_container.pack(fill=tk.BOTH, expand=True, padx=20)
        
        # Initial render
        self._render_cards()
        
        return self.frame

    def on_show(self):
        pass

    def add_player(self):
        nickname = self.input_var.get().strip()
        if not nickname:
            return
            
        if len(self.players_data) >= self.max_players:
            messagebox.showwarning("Limit Reached", f"You can only compare up to {self.max_players} players.")
            return

        # Check if already added
        for p in self.players_data:
            if p.get("data", {}).get("nick", "").lower() == nickname.lower():
                messagebox.showinfo("Info", "Player already added.")
                return

        self.loading = True
        self.add_btn.configure(state="disabled")
        
        thread = threading.Thread(target=self._fetch_player_data, args=(nickname,))
        thread.daemon = True
        thread.start()

    def _fetch_player_data(self, nickname: str):
        url = f"https://gmt.star-conflict.com/pubapi/v1/userinfo.php?nickname={urllib.parse.quote(nickname)}"
        try:
            with urllib.request.urlopen(url) as response:
                data = json.loads(response.read().decode())
                
            # The API returns a JSON. Structure needs to be checked. 
            # Assuming standard response format based on request.
            # If "result" is "ok" or similar.
            
            # Let's assume the data is the user info directly or wrapped.
            # Based on typical SC API, it might return "data" field.
            
            self.app.after(0, self._handle_success, data, nickname)
            
        except Exception as e:
            self.app.after(0, self._handle_error, str(e))

    def _handle_success(self, data: Dict, requested_nick: str):
        self.loading = False
        if self.add_btn:
            self.add_btn.configure(state="normal")
            
        # Basic validation of response
        # The API usually returns something like {"result": "ok", "data": {...}} or just the data
        # If the user doesn't exist, it might return an error or empty data.
        
        # Note: I don't have the exact API response structure, so I'll try to be robust.
        # If 'data' key exists, use it.
        player_info = data.get("data", data)
        
        # Check for nickName (API uses camelCase)
        if not player_info or "nickName" not in player_info:
             messagebox.showerror("Error", f"Player '{requested_nick}' not found or API error.")
             return

        self.players_data.append(data)
        self.input_var.set("")
        self._render_cards()

    def _handle_error(self, error_msg: str):
        self.loading = False
        if self.add_btn:
            self.add_btn.configure(state="normal")
        messagebox.showerror("API Error", f"Failed to fetch data: {error_msg}")

    def clear_all(self):
        self.players_data = []
        self._render_cards()

    def remove_player(self, index: int):
        if 0 <= index < len(self.players_data):
            self.players_data.pop(index)
            self._render_cards()

    def _render_cards(self):
        if not self.cards_container:
            return
            
        for widget in self.cards_container.winfo_children():
            widget.destroy()
            
        if not self.players_data:
            ttk.Label(self.cards_container, text="Add players to view stats", style="LabelMuted.TLabel", font=("Segoe UI", 14)).pack(pady=50)
            return

        # Grid layout for cards
        for i, p_data in enumerate(self.players_data):
            self._create_player_card(p_data, i)

    def _create_player_card(self, full_data: Dict, index: int):
        data = full_data.get("data", full_data)
        
        # Main Card Frame
        card = ttk.LabelFrame(self.cards_container, text=f" {data.get('nickName', 'Unknown')} ", style="Card.TLabelframe", padding=10)
        card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # --- Header ---
        header_frame = ttk.Frame(card, style="Panel.TFrame")
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Rank & Clan
        rank = data.get("accountRank", "?")
        clan_data = data.get("clan", {})
        clan_tag = clan_data.get("tag", "")
        clan_name = clan_data.get("name", "")
        
        top_line = ttk.Frame(header_frame, style="Panel.TFrame")
        top_line.pack(fill=tk.X)
        
        if clan_tag:
            ttk.Label(top_line, text=f"[{clan_tag}]", foreground=self.app.colors["accent"], font=("Segoe UI", 11, "bold")).pack(side=tk.LEFT)
        if clan_name:
            ttk.Label(top_line, text=f" {clan_name}", style="LabelMuted.TLabel").pack(side=tk.LEFT)
            
        ttk.Label(top_line, text=f"Rank {rank}", style="LabelMuted.TLabel").pack(side=tk.RIGHT)
        
        # Eff Rating & Karma
        eff = data.get("effRating", 0)
        karma = data.get("openWorld", {}).get("karma", 0)
        
        info_line = ttk.Frame(header_frame, style="Panel.TFrame")
        info_line.pack(fill=tk.X, pady=(5, 0))
        ttk.Label(info_line, text=f"Eff. Rating: {eff:.0f}", font=("Segoe UI", 10)).pack(side=tk.LEFT)
        ttk.Label(info_line, text=f"Karma: {karma}", font=("Segoe UI", 10)).pack(side=tk.RIGHT)

        # --- Content Stack (No Tabs) ---
        content_frame = ttk.Frame(card, style="App.TFrame")
        content_frame.pack(fill=tk.BOTH, expand=True)

        # Section 1: PvP
        self._build_pvp_section(content_frame, data.get("pvp", {}))
        
        ttk.Separator(content_frame, orient="horizontal").pack(fill=tk.X, pady=10)

        # Section 2: PvE
        self._build_pve_section(content_frame, data.get("pve", {}))
        
        ttk.Separator(content_frame, orient="horizontal").pack(fill=tk.X, pady=10)

        # Section 3: Other
        self._build_other_section(content_frame, data)

        # Remove Button
        ttk.Button(card, text="Remove", command=lambda idx=index: self.remove_player(idx)).pack(side=tk.BOTTOM, pady=(10, 0), fill=tk.X)

    def _build_pvp_section(self, parent, stats):
        ttk.Label(parent, text="PvP Stats", style="Section.TLabel").pack(anchor="w", pady=(0, 5))
        
        if not stats:
            ttk.Label(parent, text="No PvP Data", style="LabelMuted.TLabel").pack()
            return

        # Helper
        def get_val(k): return float(stats.get(k, 0))
        
        battles = get_val("gamePlayed")
        wins = get_val("gameWin")
        kills = get_val("totalKill")
        deaths = get_val("totalDeath")
        assists = get_val("totalAssists")
        dmg = get_val("totalDmgDone")
        healing = get_val("totalHealingDone")
        
        if battles == 0:
            ttk.Label(parent, text="No Battles", style="LabelMuted.TLabel").pack()
            return

        winrate = (wins / battles) * 100
        kd = kills / max(1, deaths)
        kda = (kills + assists) / max(1, deaths)
        avg_dmg = dmg / battles
        avg_heal = healing / battles

        # Layout: Chart Left, Stats Right
        container = ttk.Frame(parent, style="App.TFrame")
        container.pack(fill=tk.X)
        
        # Left: Winrate Pie
        chart_frame = ttk.Frame(container, style="App.TFrame")
        chart_frame.pack(side=tk.LEFT, padx=(0, 10))
        self._draw_pie_chart(chart_frame, winrate, "Winrate", size=70)
        
        # Right: Stats Grid
        grid = ttk.Frame(container, style="App.TFrame")
        grid.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        rows = [
            ("Battles", f"{int(battles):,}"),
            ("K/D", f"{kd:.2f}"),
            ("K/D/A", f"{kda:.2f}"),
            ("Avg Dmg", self._format_number(avg_dmg)),
            ("Avg Heal", self._format_number(avg_heal)),
        ]
        
        for i, (k, v) in enumerate(rows):
            ttk.Label(grid, text=k, style="LabelMuted.TLabel", font=("Segoe UI", 8)).grid(row=i, column=0, sticky="w")
            ttk.Label(grid, text=v, font=("Segoe UI", 9, "bold")).grid(row=i, column=1, sticky="e", padx=(5, 0))

    def _build_pve_section(self, parent, stats):
        ttk.Label(parent, text="PvE Stats", style="Section.TLabel").pack(anchor="w", pady=(0, 5))
        
        if not stats:
            ttk.Label(parent, text="No PvE Data", style="LabelMuted.TLabel").pack()
            return
            
        # Top Stats Row
        top_row = ttk.Frame(parent, style="App.TFrame")
        top_row.pack(fill=tk.X, pady=(0, 5))
        
        def add_stat(p, label, val):
            f = ttk.Frame(p, style="App.TFrame")
            f.pack(side=tk.LEFT, expand=True)
            ttk.Label(f, text=label, style="LabelMuted.TLabel", font=("Segoe UI", 8)).pack()
            ttk.Label(f, text=str(val), font=("Segoe UI", 9, "bold")).pack()

        add_stat(top_row, "Atk Lvl", stats.get("unlimPve_playerAttackLevel", 0))
        add_stat(top_row, "Def Lvl", stats.get("unlimPve_playerDefenceLevel", 0))
        add_stat(top_row, "Max Wave", stats.get("wavePve_maxWave", 0))

        # Mission Levels (Compact List)
        missions_frame = ttk.Frame(parent, style="App.TFrame")
        missions_frame.pack(fill=tk.BOTH, expand=True)
        
        canvas = tk.Canvas(missions_frame, bg=self.app.colors["bg"], highlightthickness=0, height=100)
        scrollbar = ttk.Scrollbar(missions_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas, style="App.TFrame")
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        missions = stats.get("unlimPve_missionLevels", {})
        for i, (m_name, lvl) in enumerate(missions.items()):
            clean_name = m_name.replace("pve_", "").replace("_", " ").title()
            # Shorten names for compact view
            if len(clean_name) > 20: clean_name = clean_name[:18] + ".."
            
            ttk.Label(scrollable_frame, text=clean_name, style="LabelMuted.TLabel", font=("Segoe UI", 8)).grid(row=i, column=0, sticky="w", pady=1)
            ttk.Label(scrollable_frame, text=str(lvl), font=("Segoe UI", 8, "bold")).grid(row=i, column=1, sticky="e", padx=10, pady=1)

    def _build_other_section(self, parent, data):
        coop = data.get("coop", {})
        clan = data.get("clan", {})
        
        grid = ttk.Frame(parent, style="App.TFrame")
        grid.pack(fill=tk.X)
        
        # Co-op Column
        coop_frame = ttk.Frame(grid, style="App.TFrame")
        coop_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ttk.Label(coop_frame, text="Co-op", style="Section.TLabel", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        
        c_battles = coop.get("gamePlayed", 0)
        c_wins = coop.get("gameWin", 0)
        c_wr = (c_wins / c_battles * 100) if c_battles > 0 else 0
        
        ttk.Label(coop_frame, text=f"{c_battles} Battles", style="LabelMuted.TLabel", font=("Segoe UI", 8)).pack(anchor="w")
        ttk.Label(coop_frame, text=f"{c_wr:.1f}% WR", style="LabelMuted.TLabel", font=("Segoe UI", 8)).pack(anchor="w")

        # Clan Column
        if clan:
            clan_frame = ttk.Frame(grid, style="App.TFrame")
            clan_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0))
            ttk.Label(clan_frame, text="Clan Ratings", style="Section.TLabel", font=("Segoe UI", 9, "bold")).pack(anchor="w")
            
            ttk.Label(clan_frame, text=f"PvP: {self._format_number(clan.get('pvpRating', 0))}", style="LabelMuted.TLabel", font=("Segoe UI", 8)).pack(anchor="w")
            ttk.Label(clan_frame, text=f"PvE: {self._format_number(clan.get('pveRating', 0))}", style="LabelMuted.TLabel", font=("Segoe UI", 8)).pack(anchor="w")

    def _draw_pie_chart(self, parent, percentage, label, size=100):
        # Simple Canvas Pie Chart
        canvas = tk.Canvas(parent, width=size, height=size+20, bg=self.app.colors["bg"], highlightthickness=0)
        canvas.pack()
        
        # Background circle
        canvas.create_oval(5, 5, size-5, size-5, outline=self.app.colors["border"], width=2)
        
        # Arc
        angle = (percentage / 100) * 360
        if angle > 0:
            canvas.create_arc(5, 5, size-5, size-5, start=90, extent=-angle, outline=self.app.colors["accent"], width=4, style="arc")
            
        # Text
        canvas.create_text(size/2, size/2, text=f"{percentage:.0f}%", fill=self.app.colors["text"], font=("Segoe UI", 9, "bold"))
        canvas.create_text(size/2, size+10, text=label, fill=self.app.colors["muted"], font=("Segoe UI", 7))

    def _format_number(self, num):
        if num >= 1_000_000:
            return f"{num/1_000_000:.1f}M"
        if num >= 1_000:
            return f"{num/1_000:.1f}k"
        return f"{num:.0f}"

