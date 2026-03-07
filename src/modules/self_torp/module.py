import json
import threading
import time
import sys
import subprocess
import ctypes
from ctypes import wintypes
from pathlib import Path
from typing import Optional, Tuple
import tkinter as tk
from tkinter import ttk, messagebox

from ...config import AppConfig, USER_DATA_DIR
from ..base import BaseModule

# Windows constants
WM_HOTKEY = 0x0312
WM_QUIT = 0x0012
MODIFIERS = {
    "ALT": 0x0001,
    "CONTROL": 0x0002,
    "CTRL": 0x0002,
    "SHIFT": 0x0004,
    "WIN": 0x0008,
    "WINDOWS": 0x0008,
}

INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008
MAPVK_VK_TO_VSC = 0

# Low-level hook constants
WH_KEYBOARD_LL = 13
WH_MOUSE_LL = 14
WM_KEYDOWN = 0x0100
WM_SYSKEYDOWN = 0x0104
WM_XBUTTONDOWN = 0x020B
WM_MOUSEWHEEL = 0x020A
XBUTTON1 = 0x0001
XBUTTON2 = 0x0002

VK_LOOKUP = {
    "BACKSPACE": 0x08,
    "MOUSE4": 0x05,  # XBUTTON1
    "MOUSE5": 0x06,  # XBUTTON2
    "SPACE": 0x20,
    "TAB": 0x09,
    "ENTER": 0x0D,
    "ESC": 0x1B,
    "ESCAPE": 0x1B,
    "UP": 0x26,
    "DOWN": 0x28,
    "LEFT": 0x25,
    "RIGHT": 0x27,
    "INS": 0x2D,
    "INSERT": 0x2D,
    "DEL": 0x2E,
    "DELETE": 0x2E,
    "HOME": 0x24,
    "END": 0x23,
    "PGUP": 0x21,
    "PGDN": 0x22,
    "PAGEUP": 0x21,
    "PAGEDOWN": 0x22,
    "BROWSER_BACK": 0xA6,
    "BROWSER_FORWARD": 0xA7,
}

# Function keys
for idx in range(1, 25):
    VK_LOOKUP[f"F{idx}"] = 0x6F + idx  # F1 starts at 0x70

# Numpad digits
for idx in range(10):
    VK_LOOKUP[f"NUM{idx}"] = 0x60 + idx

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
# Fallback for Python builds lacking wintypes.ULONG_PTR
ULONG_PTR = getattr(wintypes, "ULONG_PTR", ctypes.c_size_t)

# Define ctypes function signatures for 64-bit compatibility
LRESULT = ctypes.c_int64 if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_long
HHOOK = ctypes.c_void_p

user32.SetWindowsHookExW.argtypes = [ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint32]
user32.SetWindowsHookExW.restype = HHOOK

user32.CallNextHookEx.argtypes = [HHOOK, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM]
user32.CallNextHookEx.restype = LRESULT

user32.UnhookWindowsHookEx.argtypes = [HHOOK]
user32.UnhookWindowsHookEx.restype = wintypes.BOOL

kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
kernel32.GetModuleHandleW.restype = wintypes.HMODULE

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]


class INPUTUnion(ctypes.Union):
    _fields_ = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT),
        ("hi", HARDWAREINPUT),
    ]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("u", INPUTUnion)]


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class MSLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("pt", wintypes.POINT),
        ("mouseData", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class SelfTorpModule(BaseModule):
    name = "Self-Torp"
    description = "Trigger a torpedo sequence from a global hotkey."
    has_module_view = False

    def __init__(self, app, config: AppConfig):
        self.app = app
        self.config = config
        self.frame: Optional[ttk.Frame] = None

        self.settings_path = USER_DATA_DIR / "self_torp_settings.json"
        self.hotkey_text = "Ctrl+Alt+T"
        self.first_key = "1"
        self.burst_key = "2"

        self.enabled = False
        self._listener_thread: Optional[threading.Thread] = None
        self._listener_thread_id: Optional[int] = None
        self._stop_event = threading.Event()
        self._hotkey_ready = threading.Event()
        self._hotkey_failed = threading.Event()
        self._fire_lock = threading.Lock()

        self._hotkey_spec = None  # dict with mods, kind, key (token), vk
        self._capturing_callback = None
        self._kb_hook = None
        self._mouse_hook = None
        self._kb_proc = None
        self._mouse_proc = None
        self._polling_thread: Optional[threading.Thread] = None

        self.HOTKEY_ID = 0x0A11

        self._settings_win: Optional[tk.Toplevel] = None
        self._initial_enable = False

        self._load_settings()
        
        if self._initial_enable:
            self.app.after(500, self._try_enable_startup)

    def _try_enable_startup(self):
        if ctypes.windll.shell32.IsUserAnAdmin():
            if self.enable():
                self._refresh_launchpad()
        else:
            if messagebox.askyesno(
                "Self-Torp",
                "Self-Torp was enabled but requires Administrator privileges.\nRestart as Administrator?",
                parent=self.app
            ):
                self._restart_as_admin()
            else:
                self.enabled = False
                self._save_settings()
                self._refresh_launchpad()

    def build(self, parent):
        C = self.app.colors
        self.frame = ttk.Frame(parent, style="App.TFrame")

        # --- Hero ---
        hero = tk.Frame(self.frame, bg=C["bg"])
        hero.pack(fill=tk.X, padx=60, pady=(40, 0))
        tk.Label(hero, text="SELF-TORP", font=("Segoe UI", 28, "bold"),
                 bg=C["bg"], fg="#ff8c42").pack(anchor=tk.W)
        tk.Label(hero, text="HOTKEY AUTOMATION", font=("Segoe UI", 11),
                 bg=C["bg"], fg=C["muted"]).pack(anchor=tk.W, pady=(2, 0))
        tk.Frame(self.frame, height=1, bg=C["border"]).pack(fill=tk.X, padx=60, pady=(16, 24))

        # --- Status Card ---
        area = tk.Frame(self.frame, bg=C["bg"])
        area.pack(padx=60, anchor=tk.W)
        card_bdr = tk.Frame(area, bg=C["border"], padx=1, pady=1)
        card_bdr.pack(anchor=tk.W)
        tk.Frame(card_bdr, height=3, bg="#ff8c42").pack(fill=tk.X)
        card = tk.Frame(card_bdr, bg=C["panel"], width=380, padx=20, pady=16)
        card.pack_propagate(False)
        card.pack()

        def _row(label, value, value_color=None):
            r = tk.Frame(card, bg=C["panel"])
            r.pack(fill=tk.X, pady=3)
            tk.Label(r, text=label, font=("Segoe UI", 10),
                     bg=C["panel"], fg=C["muted"]).pack(side=tk.LEFT)
            tk.Label(r, text=value, font=("Segoe UI", 10, "bold"),
                     bg=C["panel"], fg=value_color or C["text"]).pack(side=tk.RIGHT)

        _row("Status", "Enabled" if self.enabled else "Disabled",
             "#ff8c42" if self.enabled else C["muted"])
        _row("Hotkey", self.hotkey_text)
        _row("First key", self.first_key)
        _row("Burst key (×15)", self.burst_key)

        tk.Frame(card, height=1, bg=C["border"]).pack(fill=tk.X, pady=(8, 0))
        btn_row = tk.Frame(card, bg=C["panel"])
        btn_row.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(btn_row, text="⚙  Settings", command=self.open_settings,
                   style="TButton").pack(side=tk.RIGHT)
        tk.Label(card, text="Toggle on/off from the launchpad tile.",
                 font=("Segoe UI", 9), bg=C["panel"], fg=C["muted"]).pack(anchor=tk.W, pady=(8, 0))

        return self.frame

    def on_show(self):
        pass

    def on_hide(self):
        pass

    def on_exit(self):
        self._stop_listener()

    def tile_status(self) -> str:
        return "On" if self.enabled else "Off"

    def on_tile_click(self) -> bool:
        if self.enabled:
            self.disable()
        else:
            if not self.enable():
                return True
        self._refresh_launchpad()
        return True

    def open_settings(self):
        if self._settings_win and tk.Toplevel.winfo_exists(self._settings_win):
            self._settings_win.lift()
            self._settings_win.focus_force()
            return

        self._settings_win = tk.Toplevel(self.app)
        self._settings_win.title("Self-Torp Settings")
        self._settings_win.attributes("-topmost", True)
        self._settings_win.configure(bg=self.app.colors.get("bg", "#0b1224"))
        self._settings_win.resizable(False, False)

        w, h = 520, 360
        x = self.app.winfo_x() + (self.app.winfo_width() // 2) - (w // 2)
        y = self.app.winfo_y() + (self.app.winfo_height() // 2) - (h // 2)
        self._settings_win.geometry(f"{w}x{h}+{x}+{y}")

        tk.Frame(self._settings_win, height=3, bg="#ff8c42").pack(fill=tk.X)
        _hdr = tk.Frame(self._settings_win, bg=self.app.colors.get("bg", "#0b1224"), padx=16, pady=12)
        _hdr.pack(fill=tk.X)
        tk.Label(_hdr, text="Self-Torp Settings", font=("Segoe UI", 14, "bold"),
                 bg=self.app.colors.get("bg", "#0b1224"), fg="#ff8c42").pack(anchor=tk.W)
        tk.Frame(self._settings_win, height=1,
                 bg=self.app.colors.get("border", "#24365c")).pack(fill=tk.X)

        container = ttk.Frame(self._settings_win, style="App.TFrame", padding=16)
        container.pack(fill=tk.BOTH, expand=True)

        hotkey_var = tk.StringVar(value=self.hotkey_text)
        first_key_var = tk.StringVar(value=self.first_key)
        burst_key_var = tk.StringVar(value=self.burst_key)

        ttk.Label(container, text="Hotkey (single key, no modifiers)", style="LabelMuted.TLabel").grid(row=0, column=0, sticky="w", pady=6)
        hotkey_row = ttk.Frame(container, style="App.TFrame")
        hotkey_row.grid(row=0, column=1, sticky="ew", padx=(10, 0))
        hotkey_display = ttk.Label(hotkey_row, textvariable=hotkey_var, anchor="w", style="TileDesc.TLabel", relief="groove", padding=4)
        hotkey_display.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(hotkey_row, text="Capture", command=lambda: self._capture_hotkey(hotkey_var), width=8).pack(side=tk.LEFT, padx=(6, 0))

        ttk.Label(container, text="First key", style="LabelMuted.TLabel").grid(row=1, column=0, sticky="w", pady=6)
        ttk.Entry(container, textvariable=first_key_var, width=20).grid(row=1, column=1, sticky="w", padx=(10, 0))

        ttk.Label(container, text="Burst key (sent x15)", style="LabelMuted.TLabel").grid(row=2, column=0, sticky="w", pady=6)
        ttk.Entry(container, textvariable=burst_key_var, width=20).grid(row=2, column=1, sticky="w", padx=(10, 0))

        ttk.Label(
            container,
            text="Keys accept letters, digits, function keys, arrows, numpad (NUM1), and mouse buttons (Mouse4/Mouse5).",
            style="LabelMuted.TLabel",
            wraplength=360,
            justify=tk.LEFT,
        ).grid(row=3, column=0, columnspan=2, sticky="w", pady=(10, 4))

        btn_row = ttk.Frame(container, style="App.TFrame")
        btn_row.grid(row=4, column=0, columnspan=2, sticky="e", pady=(12, 0))

        def save():
            hk = hotkey_var.get().strip()
            fk = first_key_var.get().strip()
            bk = burst_key_var.get().strip()

            if not hk or not fk or not bk:
                messagebox.showerror("Self-Torp", "All fields are required.", parent=self._settings_win)
                return

            if not self._parse_hotkey(hk):
                messagebox.showerror("Self-Torp", "Invalid hotkey. Use a single key.", parent=self._settings_win)
                return

            if not self._to_vk(fk) or not self._to_vk(bk):
                messagebox.showerror("Self-Torp", "Invalid send keys. Use letters, digits, function keys, arrows, or NUM0-9.", parent=self._settings_win)
                return

            self.hotkey_text = hk
            self.first_key = fk
            self.burst_key = bk
            self._save_settings()

            if self.enabled:
                self.disable()
                self.enable()

            self._refresh_launchpad()
            if self._settings_win:
                self._settings_win.destroy()
            self._settings_win = None

        ttk.Button(btn_row, text="Save", command=save, style="Accent.TButton").pack(side=tk.RIGHT, padx=(8, 0))
        
        def cancel():
            if self._settings_win:
                self._settings_win.destroy()
            self._settings_win = None

        ttk.Button(btn_row, text="Cancel", command=cancel).pack(side=tk.RIGHT)

    def _capture_hotkey(self, target_var: tk.StringVar):
        cap = tk.Toplevel(self.app)
        cap.attributes("-topmost", True)
        cap.title("Press hotkey")
        cap.configure(bg=self.app.colors.get("bg", "#0b1224"))
        cap.resizable(False, False)
        cap.grab_set()
        cap.focus_force()

        w, h = 360, 180
        x = self.app.winfo_x() + (self.app.winfo_width() // 2) - (w // 2)
        y = self.app.winfo_y() + (self.app.winfo_height() // 2) - (h // 2)
        cap.geometry(f"{w}x{h}+{x}+{y}")

        frame = ttk.Frame(cap, style="App.TFrame", padding=16)
        frame.pack(fill=tk.BOTH, expand=True)
        info = ttk.Label(frame, text="Press any key or Mouse4/Mouse5", style="LabelMuted.TLabel")
        info.pack(pady=(8, 6))
        live = tk.StringVar(value="...")
        live_label = ttk.Label(frame, textvariable=live, font=("Segoe UI", 12, "bold"), style="TileTitle.TLabel")
        live_label.pack(pady=(6, 6))
        ttk.Label(frame, text="Esc to cancel", style="LabelMuted.TLabel").pack()

        def render_preview(token=None):
            live.set(token if token else "...")

        # Setup capture state
        capture_stop_event = threading.Event()
        self._capture_thread = None

        def capture_thread_loop():
            # Install hooks locally in this thread
            local_proc = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)(self._mouse_hook_fn)
            h_hook = user32.SetWindowsHookExW(WH_MOUSE_LL, local_proc, kernel32.GetModuleHandleW(None), 0)
            
            # Keep reference to proc to prevent GC
            self._capture_proc_ref = local_proc

            msg = wintypes.MSG()
            # Message pump
            while not capture_stop_event.is_set():
                if user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1): # PM_REMOVE
                    if msg.message == WM_QUIT:
                        break
                    user32.TranslateMessage(ctypes.byref(msg))
                    user32.DispatchMessageW(ctypes.byref(msg))
                else:
                    time.sleep(0.01)

            if h_hook:
                user32.UnhookWindowsHookEx(h_hook)
            self._capture_proc_ref = None

        def close(_evt=None):
            self._capturing_callback = None
            capture_stop_event.set()
            if self._capture_thread and self._capture_thread.is_alive():
                self._capture_thread.join(timeout=0.5)
            self._capture_thread = None
            try:
                cap.destroy()
            except Exception:
                pass

        def finalize(token):
            if not token:
                return
            target_var.set(token)
            close()

        # Install hooks if needed (for mouse buttons/wheel global capture)
        self._capturing_callback = finalize
        
        # Start capture thread
        self._capture_thread = threading.Thread(target=capture_thread_loop, daemon=True, name="CaptureHooks")
        self._capture_thread.start()

        def on_key(evt):
            token = self._keysym_to_token(evt.keysym)
            if not token:
                return
            if token in ("CTRL", "ALT", "SHIFT", "WIN"):
                return
            finalize(token)

        def on_wheel(evt):
            if evt.delta > 0:
                finalize("WHEEL_UP")
            else:
                finalize("WHEEL_DOWN")

        cap.bind("<KeyPress>", on_key)
        cap.bind("<MouseWheel>", on_wheel)
        cap.bind("<Escape>", lambda e: close())
        cap.bind("<FocusOut>", close)
        cap.protocol("WM_DELETE_WINDOW", close)

    def enable(self) -> bool:
        if self.enabled:
            return True

        if not ctypes.windll.shell32.IsUserAnAdmin():
            if messagebox.askyesno(
                "Administrator Required",
                "The Self-Torp module requires Administrator privileges to function in-game.\n\nDo you want to restart SC Nexus as Administrator now?",
                parent=self.app
            ):
                # Save enabled=True so it starts enabled next time
                self.enabled = True
                self._save_settings()
                self._restart_as_admin()
            return False

        spec = self._parse_hotkey(self.hotkey_text)
        if not spec:
            self._notify("Set a valid hotkey first (e.g. Ctrl+Alt+T or Mouse4).")
            return False

        self._hotkey_spec = spec

        self._stop_event.clear()
        self._hotkey_ready.clear()
        self._hotkey_failed.clear()

        def loop():
            self._listener_thread_id = kernel32.GetCurrentThreadId()
            ok = self._install_hooks()
            if not ok:
                self._hotkey_failed.set()
                self._hotkey_ready.set()
                return
            self._hotkey_ready.set()

            msg = wintypes.MSG()
            while not self._stop_event.is_set() and user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
                pass

            self._remove_hooks()

        self._listener_thread = threading.Thread(target=loop, daemon=True, name="SelfTorpHooks")
        self._listener_thread.start()

        self._hotkey_ready.wait(timeout=1.0)
        if self._hotkey_failed.is_set():
            self.disable()
            self._notify("Could not register hotkey hooks. Try a different combination.")
            return False

        self.enabled = True
        self._save_settings()
        return True

    def _stop_listener(self):
        self._stop_event.set()
        try:
            user32.PostThreadMessageW(self._listener_thread_id or 0, WM_QUIT, 0, 0)
        except Exception:
            pass
        if self._listener_thread and self._listener_thread.is_alive():
            self._listener_thread.join(timeout=1.5)

        # Stop polling thread if exists
        if self._polling_thread and self._polling_thread.is_alive():
            self._polling_thread.join(timeout=1.0)
        self._polling_thread = None

        self._listener_thread = None
        self._listener_thread_id = None
        self._hotkey_spec = None
        self._remove_hooks()

    def disable(self):
        self.enabled = False
        self._save_settings()
        self._stop_listener()

    def _restart_as_admin(self):
        try:
            # Cleanup hooks before restarting to avoid lag
            self._stop_listener()
            
            ctypes.windll.shell32.ShellExecuteW(
                None,
                "runas",
                sys.executable,
                subprocess.list2cmdline(sys.argv),
                None,
                1
            )
            self.app.quit()
        except Exception as e:
            self._notify(f"Failed to restart: {e}")

    def _fire_sequence_async(self):
        if self._fire_lock.locked():
            return
        threading.Thread(target=self._run_sequence, daemon=True, name="SelfTorpFire").start()

    def _run_sequence(self):
        if not self._fire_lock.acquire(blocking=False):
            return
        try:
            vk_first = self._to_vk(self.first_key)
            vk_burst = self._to_vk(self.burst_key)
            if not vk_first or not vk_burst:
                self._notify("Invalid send keys. Open settings and update them.")
                return

            self._send_press(vk_first)
            time.sleep(0.2)
            # Burst loop: "as fast as a free spinning mousewheel"
            # Mouse wheels can fire input very rapidly. We use a tiny sleep to avoid choking
            # the system message queue completely, but essentially run as fast as possible.
            for _ in range(15):
                self._send_press(vk_burst)
                time.sleep(0.002) 
        finally:
            self._fire_lock.release()

    def _install_hooks(self) -> bool:
        try:
            spec = self._hotkey_spec
            if not spec:
                return False

            kind = spec["kind"]
            key = spec.get("key")

            # 1. Keyboard -> Use Hook (Efficient)
            if kind == "keyboard":
                self._kb_proc = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)(self._kb_hook_fn)
                self._kb_hook = user32.SetWindowsHookExW(WH_KEYBOARD_LL, self._kb_proc, kernel32.GetModuleHandleW(None), 0)
                if not self._kb_hook:
                    return False

            # 2. Mouse Buttons -> Use Polling (No Lag)
            elif kind == "mouse" and key in ("MOUSE4", "MOUSE5"):
                # Start polling thread
                self._polling_thread = threading.Thread(target=self._poll_mouse_buttons, args=(key,), daemon=True, name="SelfTorpPoll")
                self._polling_thread.start()
                return True

            # 3. Mouse Wheel -> Must use Hook (Lag risk, but wheel has no state)
            elif kind == "mouse":
                self._mouse_proc = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)(self._mouse_hook_fn)
                self._mouse_hook = user32.SetWindowsHookExW(WH_MOUSE_LL, self._mouse_proc, kernel32.GetModuleHandleW(None), 0)
                if not self._mouse_hook:
                    return False

            return True
        except Exception:
            return False

    def _poll_mouse_buttons(self, key: str):
        # Map token to VK
        vk = 0
        if key == "MOUSE4":
            vk = 0x05 # VK_XBUTTON1
        elif key == "MOUSE5":
            vk = 0x06 # VK_XBUTTON2
        
        if not vk:
            return

        # Simple polling loop
        # We need to detect Rising Edge (Up -> Down)
        was_down = False
        
        while not self._stop_event.is_set():
            # GetAsyncKeyState MSB (bit 15) indicates strictly if key is currently down
            # returns short (16 bit)
            state = user32.GetAsyncKeyState(vk)
            is_down = (state & 0x8000) != 0
            
            if is_down and not was_down:
                # Rising edge
                self._fire_sequence_async()
            
            was_down = is_down
            time.sleep(0.01) # 100Hz polling

    def _remove_hooks(self):
        try:
            if self._kb_hook:
                user32.UnhookWindowsHookEx(self._kb_hook)
        except Exception:
            pass
        try:
            if self._mouse_hook:
                user32.UnhookWindowsHookEx(self._mouse_hook)
        except Exception:
            pass
        self._kb_hook = None
        self._mouse_hook = None
        self._kb_proc = None
        self._mouse_proc = None

    def _kb_hook_fn(self, nCode, wParam, lParam):
        if nCode == 0 and wParam in (WM_KEYDOWN, WM_SYSKEYDOWN):
            try:
                data = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
                
                # If capturing, let UI handle it (Tkinter has focus), do not fire hotkey
                if self._capturing_callback:
                    return user32.CallNextHookEx(self._kb_hook, nCode, wParam, lParam)

                if self._match_hotkey("keyboard", data.vkCode):
                    self._fire_sequence_async()
                    return 1  # swallow
            except Exception:
                pass
        return user32.CallNextHookEx(self._kb_hook, nCode, wParam, lParam)

    def _mouse_hook_fn(self, nCode, wParam, lParam):
        # Optimization: Fast path for Mouse Move (0x0200) to reduce lag
        if wParam == 0x0200:
            return user32.CallNextHookEx(self._mouse_hook, nCode, wParam, lParam)

        if nCode == 0:
            try:
                token = None
                if wParam == WM_XBUTTONDOWN:
                    data = ctypes.cast(lParam, ctypes.POINTER(MSLLHOOKSTRUCT)).contents
                    btn = (data.mouseData >> 16) & 0xFFFF
                    if btn == XBUTTON1:
                        token = "MOUSE4"
                    elif btn == XBUTTON2:
                        token = "MOUSE5"
                elif wParam == WM_MOUSEWHEEL:
                    data = ctypes.cast(lParam, ctypes.POINTER(MSLLHOOKSTRUCT)).contents
                    delta = data.mouseData >> 16
                    if delta > 32767:
                        delta -= 65536
                    token = "WHEEL_UP" if delta > 0 else "WHEEL_DOWN"

                if token:
                    # If capturing, feed to UI
                    if self._capturing_callback:
                        self.app.after(0, self._capturing_callback, token)
                        return 1  # swallow input during capture
                    
                    if self._match_hotkey("mouse", token):
                        self._fire_sequence_async()
                        return 1
            except Exception:
                pass
        return user32.CallNextHookEx(self._mouse_hook, nCode, wParam, lParam)

    def _current_mods(self) -> int:
        return 0  # Modifiers are now ignored

    def _match_hotkey(self, kind: str, code) -> bool:
        spec = self._hotkey_spec
        if not spec:
            return False
        if spec["kind"] != kind:
            return False
        if kind == "keyboard":
            if spec.get("vk") != code:
                return False
        else:
            if spec.get("key") != code:
                return False
        
        # We no longer check for modifiers (cur == req)
        return True

    def _send_press(self, vk: int):
        scan = user32.MapVirtualKeyW(vk, MAPVK_VK_TO_VSC)

        down = INPUT()
        down.type = INPUT_KEYBOARD
        down.u.ki = KEYBDINPUT(0, scan, KEYEVENTF_SCANCODE, 0, 0)

        up = INPUT()
        up.type = INPUT_KEYBOARD
        up.u.ki = KEYBDINPUT(0, scan, KEYEVENTF_SCANCODE | KEYEVENTF_KEYUP, 0, 0)

        arr = (INPUT * 2)(down, up)
        user32.SendInput(2, ctypes.byref(arr), ctypes.sizeof(INPUT))

    def _parse_hotkey(self, text: str):
        if not text:
            return None
        parts = [p.strip().upper() for p in text.split("+") if p.strip()]
        if not parts:
            return None

        # Take the last token as the actual key, ignoring any modifiers preceding it
        input_token = parts[-1]
        
        # Check if user typed a modifier purely by accident as the last token, we can reject or just try to use it.
        # But logic says we ignore modifiers. Let's see if we can just treat it as a key.
        # Actually, tokens like CTRL are not valid trigger keys in our _to_vk likely if it relies on printable chars
        # or special keys. But let's stick to the plan: Ignore modifiers from logic. 
        # Since we removed modifiers from capture, the text passed here will likely be "T" or "F9" without mods. 
        # But if user typed "Ctrl+T", parts[-1] is "T". If user typed "Ctrl", parts[-1] is "Ctrl".

        key_token = input_token

        if not key_token:
            return None

        mouse_tokens = {"MOUSE4", "MOUSE5", "WHEEL_UP", "WHEEL_DOWN"}
        if key_token in mouse_tokens:
            return {"mods": 0, "kind": "mouse", "key": key_token, "vk": None}

        vk = self._to_vk(key_token)
        if not vk:
            return None
        return {"mods": 0, "kind": "keyboard", "key": key_token, "vk": vk}

    def _to_vk(self, token: str) -> Optional[int]:
        if not token:
            return None
        token = token.strip().upper()
        if token in ("MOUSE4", "MOUSE5"):
            return None
        if token in VK_LOOKUP:
            return VK_LOOKUP[token]
        if len(token) == 1:
            ch = token.upper()
            if "A" <= ch <= "Z" or "0" <= ch <= "9":
                return ord(ch)
        return None

    def _keysym_to_token(self, keysym: str) -> Optional[str]:
        if not keysym:
            return None
        ks = keysym.upper()
        if ks in ("CONTROL_L", "CONTROL_R"):
            return "CTRL"
        if ks in ("ALT_L", "ALT_R", "META_L", "META_R"):
            return "ALT"
        if ks in ("SHIFT_L", "SHIFT_R"):
            return "SHIFT"
        if ks in ("SUPER_L", "SUPER_R", "WIN_L", "WIN_R"):
            return "WIN"
        if ks.startswith("F") and ks[1:].isdigit():
            return ks
        if ks.startswith("KP_") and ks[3:].isdigit():
            return f"NUM{ks[3:]}"
        arrow_map = {
            "LEFT": "LEFT",
            "RIGHT": "RIGHT",
            "UP": "UP",
            "DOWN": "DOWN",
        }
        if ks in arrow_map:
            return arrow_map[ks]
        page_map = {
            "PRIOR": "PGUP",
            "NEXT": "PGDN",
        }
        if ks in page_map:
            return page_map[ks]
        special = {
            "SPACE": "SPACE",
            "RETURN": "ENTER",
            "TAB": "TAB",
            "ESCAPE": "ESCAPE",
            "BACKSPACE": "BACKSPACE",
            "INSERT": "INSERT",
            "DELETE": "DELETE",
            "HOME": "HOME",
            "END": "END",
            "BROWSER_BACK": "BROWSER_BACK",
            "BROWSER_FORWARD": "BROWSER_FORWARD",
        }
        if ks in special:
            return special[ks]
        if len(ks) == 1 and (("A" <= ks <= "Z") or ("0" <= ks <= "9")):
            return ks
        return None

    def _load_settings(self):
        try:
            data = json.loads(self.settings_path.read_text(encoding="utf-8"))
            self.hotkey_text = data.get("hotkey", self.hotkey_text)
            self.first_key = data.get("first_key", self.first_key)
            self.burst_key = data.get("burst_key", self.burst_key)
            self._initial_enable = data.get("enabled", False)
        except FileNotFoundError:
            pass
        except Exception:
            pass

    def _save_settings(self):
        try:
            payload = {
                "hotkey": self.hotkey_text,
                "first_key": self.first_key,
                "burst_key": self.burst_key,
                "enabled": self.enabled
            }
            self.settings_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except Exception:
            pass

    def _refresh_launchpad(self):
        try:
            self.app.after(0, self.app._build_welcome)
        except Exception:
            pass

    def _notify(self, msg: str):
        try:
            messagebox.showerror("Self-Torp", msg)
        except Exception:
            pass

