import tkinter as tk
from tkinter import ttk
from typing import Dict

from .config import AppConfig
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

        ttk.Label(self.navbar, text="Launchpad", font=("Segoe UI", 12, "bold"), style="Section.TLabel").pack(side=tk.LEFT)

        # Center container for tiles
        tile_container = ttk.Frame(self.content, style="App.TFrame")
        tile_container.pack(anchor=tk.NW, padx=40, pady=40)

        row = 0
        col = 0
        max_cols = 3

        for name, module in self.modules.items():
            # Tile Frame (Border)
            tile_border = ttk.Frame(tile_container, style="TileBorder.TFrame", padding=1)
            tile_border.grid(row=row, column=col, padx=20, pady=20)

            # Inner Content
            tile = ttk.Frame(tile_border, style="Tile.TFrame", padding=20, width=280, height=200)
            tile.pack_propagate(False)
            tile.pack(fill=tk.BOTH, expand=True)

            status_text = ""
            status_fn = getattr(module, "tile_status", None)
            if callable(status_fn):
                try:
                    status_text = status_fn()
                except Exception:
                    status_text = ""
            elif isinstance(status_fn, str):
                status_text = status_fn

            inline_status = bool(status_text) and len(status_text) <= 8

            # Header with title (optional inline status)
            header = ttk.Frame(tile, style="Tile.TFrame")
            header.pack(fill=tk.X)

            title_text = f"{name} ({status_text})" if inline_status else name
            l_title = ttk.Label(header, text=title_text, font=("Segoe UI", 16, "bold"), style="TileTitle.TLabel")
            l_title.pack(side=tk.LEFT, anchor=tk.W, pady=(10, 10))

            desc = getattr(module, "description", "")
            l_desc = None
            if desc:
                l_desc = ttk.Label(tile, text=desc, wraplength=240, justify=tk.CENTER, style="TileDesc.TLabel")
                l_desc.pack(anchor=tk.CENTER)

            # Footer with optional settings cog aligned bottom-right
            footer = ttk.Frame(tile, style="Tile.TFrame")
            footer.pack(side=tk.BOTTOM, fill=tk.X, padx=(0, 4), pady=(8, 4))
            if callable(getattr(module, "open_settings", None)):
                ttk.Button(
                    footer,
                    text="⚙",
                    width=3,
                    command=lambda m=module: self._open_module_settings(m),
                    style="TButton"
                ).pack(side=tk.RIGHT)

            # Hover Effects & Click Binding
            l_status = None
            if status_text and not inline_status:
                l_status = ttk.Label(tile, text=status_text, justify=tk.LEFT, style="TileDesc.TLabel")
                l_status.pack(anchor=tk.W, pady=(0, 2))

            widgets = [tile, header, footer, l_title]
            if l_desc:
                widgets.append(l_desc)
            if l_status:
                widgets.append(l_status)

            def on_enter(e, w_list=widgets, border_frame=tile_border):
                border_frame.configure(style="TileBorderHover.TFrame")
                for w in w_list:
                    if "Title" in w.winfo_class() or "Title" in str(w.cget("style")):
                        w.configure(style="TileTitleHover.TLabel")
                    elif "Desc" in str(w.cget("style")):
                        w.configure(style="TileDescHover.TLabel")
                    else:
                        w.configure(style="TileHover.TFrame")

            def on_leave(e, w_list=widgets, border_frame=tile_border):
                border_frame.configure(style="TileBorder.TFrame")
                for w in w_list:
                    if "Title" in w.winfo_class() or "Title" in str(w.cget("style")):
                        w.configure(style="TileTitle.TLabel")
                    elif "Desc" in str(w.cget("style")):
                        w.configure(style="TileDesc.TLabel")
                    else:
                        w.configure(style="Tile.TFrame")

            def on_click(e, m=module):
                handled = False
                try:
                    handled = bool(m.on_tile_click())
                except Exception:
                    handled = False
                if not handled:
                    self.show_module(m)

            for w in widgets:
                w.bind("<Enter>", on_enter)
                w.bind("<Leave>", on_leave)
                w.bind("<Button-1>", on_click)

            col += 1
            if col >= max_cols:
                col = 0
                row += 1

        # Settings Button (Bottom Right)
        settings_frame = ttk.Frame(self.content, style="App.TFrame")
        settings_frame.place(relx=1.0, rely=1.0, anchor="se", x=-20, y=-20)
        
        ttk.Button(
            settings_frame, 
            text="⚙", 
            width=3, 
            command=self._open_global_settings,
            style="TButton"
        ).pack()

    def _open_global_settings(self):
        win = tk.Toplevel(self)
        win.title("Settings")
        win.configure(bg=self.colors["bg"])
        win.resizable(False, False)
        
        w, h = 500, 250
        x = self.winfo_x() + (self.winfo_width() // 2) - (w // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (h // 2)
        win.geometry(f"{w}x{h}+{x}+{y}")
        
        container = ttk.Frame(win, style="App.TFrame", padding=20)
        container.pack(fill=tk.BOTH, expand=True)
        
        # Username
        ttk.Label(container, text="Username:", style="LabelMuted.TLabel").grid(row=0, column=0, sticky="w", pady=10)
        
        user_var = tk.StringVar(value=self.config.username)
        def save_user(*_):
            self.config.username = user_var.get()
            self.config.save()
            # Update modules
            for module in self.modules.values():
                if hasattr(module, "username_var"):
                    module.username_var.set(user_var.get())
        
        user_var.trace_add("write", save_user)
        ttk.Entry(container, textvariable=user_var, style="Futuristic.TEntry", width=30).grid(row=0, column=1, sticky="w", padx=10)
        
        # Logs Path
        ttk.Label(container, text="Logs Path:", style="LabelMuted.TLabel").grid(row=1, column=0, sticky="w", pady=10)
        
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
        path_frame.grid(row=1, column=1, sticky="ew", padx=10)
        ttk.Entry(path_frame, textvariable=path_var, state="readonly", style="Futuristic.TEntry").pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(path_frame, text="...", width=3, command=browse_path, style="TButton").pack(side=tk.LEFT, padx=(5,0))
        
        ttk.Button(container, text="Close", command=win.destroy, style="Accent.TButton").grid(row=2, column=1, sticky="e", pady=20)

    def _open_module_settings(self, module: BaseModule):
        handler = getattr(module, "open_settings", None)
        if callable(handler):
            try:
                handler()
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
        # Reverting to System Aware (1).
        # Per-Monitor (2) causes the main window to be huge on low-DPI screens because Tkinter widgets don't auto-scale well.
        # We will handle Overlay positioning manually using SetWindowPos.
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    config = AppConfig.load()
    app = App(config)
    app.mainloop()
    config.save()


if __name__ == "__main__":
    run_app()
