import tkinter as tk
from tkinter import ttk
from typing import Dict

from .config import AppConfig, USER_DATA_DIR
from .modules.base import BaseModule
from .modules.combat_analysis.module import CombatModule
from .modules.combat_assistant.module import CombatAssistantModule
from .modules.player_stats.module import PlayerStatsModule
from .modules.self_torp.module import SelfTorpModule


class App(tk.Tk):
    """Main application window with a welcome screen and pluggable modules."""

    def __init__(self, config: AppConfig):
        super().__init__()
        self.title("SC Nexus")
        self.geometry("1100x700")
        self._maximize_window()
        self.config = config
        self.current_module = None

        self.colors = {
            "bg": "#0b1224",
            "panel": "#111b33",
            "surface": "#16213f",
            "border": "#24365c",
            "accent": "#3de7ff",
            "accent_soft": "#7be8ff",
            "text": "#e9f3ff",
            "muted": "#9bb3d6",
        }
        self._theme_ready = False
        self._init_theme()

        self.modules: Dict[str, BaseModule] = {
            "Combat Analyzer": CombatModule(self, self.config),
            "Combat Assistant": CombatAssistantModule(self, self.config),
            "Self-Torp": SelfTorpModule(self, self.config),
            # "Player Stats": PlayerStatsModule(self, self.config),
        }

        self.configure(bg=self.colors["bg"])
        self.container = ttk.Frame(self, style="App.TFrame")
        self.container.pack(fill=tk.BOTH, expand=True)

        self.navbar = ttk.Frame(self.container, padding=10, style="Panel.TFrame")
        self.navbar.pack(fill=tk.X, padx=10, pady=10)

        self.content = ttk.Frame(self.container, style="App.TFrame")
        self.content.pack(fill=tk.BOTH, expand=True)

        self._build_welcome()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_close(self):
        """Cleanup modules before exiting."""
        for module in self.modules.values():
            try:
                module.on_exit()
            except Exception:
                pass
        self.destroy()

    def _build_welcome(self) -> None:
        if self.current_module:
            self.current_module.on_hide()
            self.current_module = None

        for widget in self.navbar.winfo_children():
            widget.destroy()
        for widget in self.content.winfo_children():
            widget.destroy()

        C = self.colors
        panel_bg = C["panel"]

        # --- Navbar ---
        tk.Label(self.navbar, text="SC NEXUS", font=("Segoe UI", 12, "bold"),
                 bg=panel_bg, fg=C["accent"]).pack(side=tk.LEFT)
        tk.Label(self.navbar, text="  ·  Launchpad", font=("Segoe UI", 11),
                 bg=panel_bg, fg=C["muted"]).pack(side=tk.LEFT)
        ttk.Button(self.navbar, text="⚙  Settings",
                   command=self._open_global_settings,
                   style="Accent.TButton").pack(side=tk.RIGHT, padx=4)

        # --- Hero Section ---
        hero = tk.Frame(self.content, bg=C["bg"])
        hero.pack(fill=tk.X, padx=60, pady=(40, 0))
        tk.Label(hero, text="SC NEXUS", font=("Segoe UI", 34, "bold"),
                 bg=C["bg"], fg=C["accent"]).pack(anchor=tk.W)
        tk.Label(hero, text="MISSION CONTROL", font=("Segoe UI", 12, "bold"),
                 bg=C["bg"], fg=C["muted"]).pack(anchor=tk.W, pady=(2, 0))
        tk.Frame(self.content, height=1, bg=C["border"]).pack(fill=tk.X, padx=60, pady=(20, 30))

        # --- Module Tiles ---
        MODULE_META = {
            "Combat Analyzer":  {"color": "#3de7ff", "icon": "◈"},
            "Combat Assistant": {"color": "#4de88e", "icon": "◉"},
            "Self-Torp":        {"color": "#ff8c42", "icon": "◆"},
            "Player Stats":     {"color": "#b96aff", "icon": "◇"},
        }

        tile_grid = tk.Frame(self.content, bg=C["bg"])
        tile_grid.pack(padx=60, anchor=tk.W)

        TILE_W, TILE_H = 300, 220
        TILE_BG        = C["panel"]
        TILE_BG_HOVER  = C["surface"]
        BORDER_CLR     = C["border"]
        BORDER_HOVER   = C["accent"]

        row = 0
        col = 0
        max_cols = 3

        for name, module in self.modules.items():
            meta      = MODULE_META.get(name, {"color": C["accent"], "icon": "◎"})
            mod_color = meta["color"]
            mod_icon  = meta["icon"]

            status_text = ""
            status_fn = getattr(module, "tile_status", None)
            if callable(status_fn):
                try:
                    status_text = status_fn()
                except Exception:
                    pass
            elif isinstance(status_fn, str):
                status_text = status_fn

            desc = getattr(module, "description", "")

            # Outer border frame — 1-px colour border via padding
            tile_border = tk.Frame(tile_grid, bg=BORDER_CLR, padx=1, pady=1)
            tile_border.grid(row=row, column=col, padx=16, pady=16, sticky="nw")

            # Coloured accent strip at the top
            accent_strip = tk.Frame(tile_border, height=4, bg=mod_color)
            accent_strip.pack(fill=tk.X)

            # Main tile body
            tile_body = tk.Frame(tile_border, bg=TILE_BG, width=TILE_W, height=TILE_H)
            tile_body.pack_propagate(False)
            tile_body.pack(fill=tk.BOTH, expand=True)

            # Icon + heading row
            header_frame = tk.Frame(tile_body, bg=TILE_BG)
            header_frame.pack(fill=tk.X, padx=20, pady=(18, 0))

            l_icon = tk.Label(header_frame, text=mod_icon, font=("Segoe UI", 18),
                              bg=TILE_BG, fg=mod_color)
            l_icon.pack(side=tk.LEFT, anchor=tk.N, pady=(2, 0))

            heading_frame = tk.Frame(header_frame, bg=TILE_BG)
            heading_frame.pack(side=tk.LEFT, padx=(10, 0), fill=tk.X, expand=True)

            l_title = tk.Label(heading_frame, text=name, font=("Segoe UI", 13, "bold"),
                               bg=TILE_BG, fg=C["text"], anchor=tk.W)
            l_title.pack(anchor=tk.W)

            l_status = None
            if status_text:
                l_status = tk.Label(heading_frame, text=status_text, font=("Segoe UI", 9),
                                    bg=TILE_BG, fg=mod_color, anchor=tk.W)
                l_status.pack(anchor=tk.W)

            # Description
            l_desc = None
            if desc:
                l_desc = tk.Label(tile_body, text=desc, font=("Segoe UI", 10),
                                  wraplength=260, justify=tk.LEFT,
                                  bg=TILE_BG, fg=C["muted"], anchor=tk.W)
                l_desc.pack(anchor=tk.W, padx=20, pady=(12, 0))

            # Footer
            footer_frame = tk.Frame(tile_body, bg=TILE_BG)
            footer_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=16, pady=12)

            open_btn = None
            if getattr(module, "has_module_view", True):
                def _make_open_btn(parent, m=module, color=mod_color):
                    btn = tk.Button(parent, text="Open  →", font=("Segoe UI", 9, "bold"),
                                    bg=C["bg"], fg=color,
                                    activebackground=color, activeforeground=C["bg"],
                                    relief=tk.FLAT, bd=0, padx=10, pady=4,
                                    cursor="hand2",
                                    command=lambda mod=m: self.show_module(mod))
                    btn.pack(side=tk.RIGHT)
                    return btn
                open_btn = _make_open_btn(footer_frame)

            cog_btn = None
            if callable(getattr(module, "open_settings", None)):
                def _make_cog_btn(parent, m=module):
                    btn = tk.Button(parent, text="⚙", font=("Segoe UI", 10),
                                    bg=C["bg"], fg=C["muted"],
                                    activebackground=C["border"], activeforeground=C["text"],
                                    relief=tk.FLAT, bd=0, padx=6, pady=4,
                                    cursor="hand2",
                                    command=lambda mod=m: self._open_module_settings(mod))
                    btn.pack(side=tk.RIGHT, padx=(0, 6))
                    return btn
                cog_btn = _make_cog_btn(footer_frame)

            # Collect widgets for hover effects
            hover_bg_frames = [tile_body, header_frame, heading_frame, footer_frame]
            hover_labels    = [l_icon, l_title]
            if l_desc:
                hover_labels.append(l_desc)
            if l_status:
                hover_labels.append(l_status)

            # Mutable flag — avoids redundant .config() calls when mouse crosses
            # nested child boundaries (which fire Enter/Leave repeatedly).
            _state = [False]  # [hovered]

            def on_enter(e, b=tile_border, bf=hover_bg_frames, lf=hover_labels,
                         title=l_title, o=open_btn, cog=cog_btn, s=_state):
                if s[0]:
                    return
                s[0] = True
                b.config(bg=BORDER_HOVER)
                for f in bf:
                    f.config(bg=TILE_BG_HOVER)
                for lbl in lf:
                    lbl.config(bg=TILE_BG_HOVER)
                title.config(fg=C["accent_soft"])
                if o:
                    o.config(bg=TILE_BG_HOVER)
                if cog:
                    cog.config(bg=TILE_BG_HOVER)

            def on_leave(e, b=tile_border, bf=hover_bg_frames, lf=hover_labels,
                         title=l_title, o=open_btn, cog=cog_btn, s=_state):
                if not s[0]:
                    return
                # Only reset when the pointer actually leaves the outer border frame
                rx, ry = e.widget.winfo_rootx() + e.x, e.widget.winfo_rooty() + e.y
                bx, by = b.winfo_rootx(), b.winfo_rooty()
                if bx <= rx <= bx + b.winfo_width() and by <= ry <= by + b.winfo_height():
                    return
                s[0] = False
                b.config(bg=BORDER_CLR)
                for f in bf:
                    f.config(bg=TILE_BG)
                for lbl in lf:
                    lbl.config(bg=TILE_BG)
                title.config(fg=C["text"])
                if o:
                    o.config(bg=C["bg"])
                if cog:
                    cog.config(bg=C["bg"])

            def on_click(e, m=module):
                handled = False
                try:
                    handled = bool(m.on_tile_click())
                except Exception:
                    pass
                if not handled and getattr(m, "has_module_view", True):
                    self.show_module(m)

            # Bind hover and click to all non-button widgets
            click_widgets = [tile_border, accent_strip, tile_body,
                             header_frame, heading_frame, footer_frame,
                             l_icon, l_title]
            if l_desc:
                click_widgets.append(l_desc)
            if l_status:
                click_widgets.append(l_status)

            for w in click_widgets:
                w.bind("<Enter>", on_enter)
                w.bind("<Leave>", on_leave)
                w.bind("<Button-1>", on_click)

            col += 1
            if col >= max_cols:
                col = 0
                row += 1

    def _open_global_settings(self):
        win = tk.Toplevel(self)
        win.title("Settings")
        win.configure(bg=self.colors["bg"])
        win.resizable(False, False)

        w, h = 520, 330
        x = self.winfo_x() + (self.winfo_width() // 2) - (w // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (h // 2)
        win.geometry(f"{w}x{h}+{x}+{y}")

        # Accent strip at top
        tk.Frame(win, height=3, bg=self.colors["accent"]).pack(fill=tk.X)

        container = ttk.Frame(win, style="App.TFrame", padding=20)
        container.pack(fill=tk.BOTH, expand=True)

        tk.Label(container, text="Settings", font=("Segoe UI", 14, "bold"),
                 bg=self.colors["bg"], fg=self.colors["accent"]).grid(
                 row=0, column=0, columnspan=2, sticky="w", pady=(0, 12))

        # Username
        ttk.Label(container, text="Username:", style="LabelMuted.TLabel").grid(row=1, column=0, sticky="w", pady=8)

        user_var = tk.StringVar(value=self.config.username)
        def save_user(*_):
            self.config.username = user_var.get()
            self.config.save()
            # Update modules
            for module in self.modules.values():
                if hasattr(module, "username_var"):
                    module.username_var.set(user_var.get())

        user_var.trace_add("write", save_user)
        ttk.Entry(container, textvariable=user_var, style="Futuristic.TEntry", width=30).grid(row=1, column=1, sticky="w", padx=10)

        # Logs Path
        ttk.Label(container, text="Logs Path:", style="LabelMuted.TLabel").grid(row=2, column=0, sticky="w", pady=8)

        path_var = tk.StringVar(value=self.config.logs_path)

        def browse_path():
            from tkinter import filedialog
            from pathlib import Path
            p = filedialog.askdirectory(initialdir=path_var.get() or str(Path.home()))
            if p:
                path_var.set(p)
                self.config.logs_path = p
                self.config.save()
                for module in self.modules.values():
                    if hasattr(module, "logs_path_var"):
                        module.logs_path_var.set(p)

        path_frame = ttk.Frame(container, style="App.TFrame")
        path_frame.grid(row=2, column=1, sticky="ew", padx=10)
        ttk.Entry(path_frame, textvariable=path_var, state="readonly", style="Futuristic.TEntry").pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(path_frame, text="...", width=3, command=browse_path, style="TButton").pack(side=tk.LEFT, padx=(5, 0))

        # Separator
        tk.Frame(container, height=1, bg=self.colors["border"]).grid(
            row=3, column=0, columnspan=2, sticky="ew", pady=(12, 4))

        # Console Log
        ttk.Label(container, text="Console Log:", style="LabelMuted.TLabel").grid(row=4, column=0, sticky="w", pady=8)
        ttk.Button(container, text="Show Console", command=self._show_console,
                   style="TButton").grid(row=4, column=1, sticky="w", padx=10)

        ttk.Button(container, text="Close", command=win.destroy,
                   style="Accent.TButton").grid(row=5, column=1, sticky="e", pady=16)

    def _open_module_settings(self, module: BaseModule):
        handler = getattr(module, "open_settings", None)
        if callable(handler):
            try:
                handler()
            except Exception:
                pass

    def _show_console(self):
        try:
            import ctypes
            hwnd = ctypes.windll.kernel32.GetConsoleWindow()
            if hwnd:
                ctypes.windll.user32.ShowWindow(hwnd, 9)  # SW_RESTORE
        except Exception:
            pass

    def show_module(self, module: BaseModule) -> None:
        if self.current_module and self.current_module != module:
            self.current_module.on_hide()
        self.current_module = module

        for widget in self.navbar.winfo_children():
            widget.destroy()
        for widget in self.content.winfo_children():
            widget.destroy()

        back_btn = ttk.Button(self.navbar, text="← Back", command=self._build_welcome, style="Accent.TButton")
        back_btn.pack(side=tk.LEFT)
        ttk.Label(self.navbar, text=module.name, font=("Segoe UI", 12, "bold"), style="Section.TLabel").pack(side=tk.LEFT, padx=8)

        frame = module.build(self.content)
        frame.pack(fill=tk.BOTH, expand=True)
        module.on_show()

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
        style.configure("Section.TLabel", background=panel, foreground=accent)

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
            "Futuristic.TEntry",
            fieldbackground=surface,
            foreground=text,
            background=surface,
            bordercolor=border,
            darkcolor=border,
            lightcolor=border,
            selectbackground=accent,
            selectforeground=bg,
            padding=5,
        )
        style.map(
            "Futuristic.TEntry",
            fieldbackground=[("readonly", bg), ("disabled", bg)],
            bordercolor=[("focus", accent)],
        )

        # Tile Styles
        style.configure("TileBorder.TFrame", background=border)
        style.configure("TileBorderHover.TFrame", background=accent)
        
        style.configure("Tile.TFrame", background=panel)
        style.configure("TileHover.TFrame", background=surface)
        
        style.configure("TileTitle.TLabel", background=panel, foreground=accent)
        style.configure("TileTitleHover.TLabel", background=surface, foreground=accent_soft)
        
        style.configure("TileDesc.TLabel", background=panel, foreground=muted)
        style.configure("TileDescHover.TLabel", background=surface, foreground=text)

        self._theme_ready = True

    def _maximize_window(self) -> None:
        """Try to start the main window maximized across platforms."""
        try:
            self.state("zoomed")
            return
        except Exception:
            pass
        try:
            self.attributes("-zoomed", True)
            return
        except Exception:
            pass
        try:
            width = self.winfo_screenwidth()
            height = self.winfo_screenheight()
            self.geometry(f"{width}x{height}+0+0")
        except Exception:
            pass


def run_app() -> None:
    try:
        import ctypes
        import sys
        import subprocess
        import json
        
        # Reverting to System Aware (1).
        # Per-Monitor (2) causes the main window to be huge on low-DPI screens because Tkinter widgets don't auto-scale well.
        # We will handle Overlay positioning manually using SetWindowPos.
        ctypes.windll.shcore.SetProcessDpiAwareness(1)

        # Hide console window on startup
        try:
            hwnd = ctypes.windll.kernel32.GetConsoleWindow()
            if hwnd:
                ctypes.windll.user32.ShowWindow(hwnd, 0)  # SW_HIDE
        except Exception:
            pass

        # Early check for Self-Torp admin requirement
        st_settings_path = USER_DATA_DIR / "self_torp_settings.json"
        
        should_elevate = False
        if st_settings_path.exists():
            try:
                with open(st_settings_path, "r") as f:
                    data = json.load(f)
                    
                if data.get("enabled", False):
                    if not ctypes.windll.shell32.IsUserAnAdmin():
                        # MB_YESNO | MB_ICONQUESTION | MB_TOPMOST
                        result = ctypes.windll.user32.MessageBoxW(
                            None,
                            "Self-Torp module is enabled but requires Administrator privileges.\n\nRestart SC Nexus as Administrator?",
                            "Administrator Required",
                            0x04 | 0x20 | 0x40000
                        )
                        
                        if result == 6:  # IDYES
                            should_elevate = True
                        else:
                            # User declined, disable the module to prevent re-prompting
                            data["enabled"] = False
                            with open(st_settings_path, "w") as fw:
                                json.dump(data, fw, indent=2)
            except Exception:
                pass

        if should_elevate:
            try:
                ctypes.windll.shell32.ShellExecuteW(
                    None,
                    "runas",
                    sys.executable,
                    subprocess.list2cmdline(sys.argv),
                    None,
                    1
                )
                return
            except Exception:
                pass

    except Exception:
        pass

    config = AppConfig.load()
    app = App(config)
    app.mainloop()
    config.save()


if __name__ == "__main__":
    run_app()
