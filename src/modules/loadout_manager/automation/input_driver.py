"""
Win32 SendInput wrapper for game UI automation.

Provides click, scroll, key-press, and cursor save/restore without
requiring administrator privileges.  Uses absolute mouse coordinates
and single-event SendInput calls.
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
from typing import Optional

# ── Win32 constants ───────────────────────────────────────────────────

INPUT_MOUSE = 0
INPUT_KEYBOARD = 1

MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_ABSOLUTE = 0x8000
MOUSEEVENTF_WHEEL = 0x0800

KEYEVENTF_KEYUP = 0x0002
WHEEL_DELTA = 120

SM_CXSCREEN = 0
SM_CYSCREEN = 1

# ── ctypes structures ─────────────────────────────────────────────────


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wt.WORD),
        ("wScan", wt.WORD),
        ("dwFlags", wt.DWORD),
        ("time", wt.DWORD),
        ("dwExtraInfo", ctypes.POINTER(wt.ULONG)),
    ]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wt.LONG),
        ("dy", wt.LONG),
        ("mouseData", wt.DWORD),
        ("dwFlags", wt.DWORD),
        ("time", wt.DWORD),
        ("dwExtraInfo", ctypes.POINTER(wt.ULONG)),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wt.DWORD),
        ("wParamL", wt.WORD),
        ("wParamH", wt.WORD),
    ]


class _INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("ki", KEYBDINPUT),
        ("mi", MOUSEINPUT),
        ("hi", HARDWAREINPUT),
    ]


class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", wt.DWORD),
        ("_input", _INPUT_UNION),
    ]


# ── Win32 API handles ─────────────────────────────────────────────────

_user32 = ctypes.windll.user32
_kernel32 = ctypes.windll.kernel32

# NOTE: Do NOT set _user32.SendInput.argtypes here.
# ctypes.windll.user32 is a shared singleton; stamping argtypes on it
# would break any other module (e.g. self_torp hotkey_engine) that also
# calls SendInput with its own INPUT struct definition.

_user32.GetCursorPos.argtypes = [ctypes.POINTER(wt.POINT)]
_user32.GetCursorPos.restype = wt.BOOL

_user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
_user32.SetCursorPos.restype = wt.BOOL

_user32.GetSystemMetrics.argtypes = [ctypes.c_int]
_user32.GetSystemMetrics.restype = ctypes.c_int

_user32.GetForegroundWindow.restype = wt.HWND
_user32.GetWindowTextW.argtypes = [wt.HWND, ctypes.c_wchar_p, ctypes.c_int]
_user32.GetWindowTextW.restype = ctypes.c_int

_user32.FindWindowW.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p]
_user32.FindWindowW.restype = wt.HWND

_user32.SetForegroundWindow.argtypes = [wt.HWND]
_user32.SetForegroundWindow.restype = wt.BOOL

_WNDENUMPROC = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
_user32.EnumWindows.argtypes = [_WNDENUMPROC, wt.LPARAM]
_user32.EnumWindows.restype = wt.BOOL

# PostMessage / MapVirtualKey — for ControlSend-style key injection
_user32.PostMessageW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]
_user32.PostMessageW.restype = wt.BOOL
_user32.MapVirtualKeyW.argtypes = [wt.UINT, wt.UINT]
_user32.MapVirtualKeyW.restype = wt.UINT

WM_KEYDOWN = 0x0100
WM_KEYUP   = 0x0101

def _post_key_to_hwnd(hwnd: int, vk: int) -> None:
    """
    Send a key-down + key-up pair directly to *hwnd* via PostMessage.

    Equivalent to AHK's ControlSend — bypasses the foreground-window
    requirement and goes straight into the target window's message queue.
    """
    if not hwnd:
        return
    scan = _user32.MapVirtualKeyW(vk, 0)  # MAPVK_VK_TO_VSC
    lp_down = (1) | (scan << 16)
    lp_up   = (1) | (scan << 16) | (1 << 30) | (1 << 31)
    _user32.PostMessageW(hwnd, WM_KEYDOWN, vk, lp_down)
    spin_sleep_ms(1)
    _user32.PostMessageW(hwnd, WM_KEYUP,   vk, lp_up)


_kernel32.QueryPerformanceFrequency.argtypes = [ctypes.POINTER(ctypes.c_longlong)]
_kernel32.QueryPerformanceFrequency.restype = wt.BOOL
_kernel32.QueryPerformanceCounter.argtypes = [ctypes.POINTER(ctypes.c_longlong)]
_kernel32.QueryPerformanceCounter.restype = wt.BOOL

_qpc_freq = ctypes.c_longlong()
_kernel32.QueryPerformanceFrequency(ctypes.byref(_qpc_freq))
_TICKS_PER_MS = _qpc_freq.value / 1000

# Virtual key codes
VK_ESCAPE = 0x1B
VK_RETURN = 0x0D
VK_TAB = 0x09
VK_BACK = 0x08

# Letter VK codes
_VK_MAP: dict[str, int] = {}
for _c in range(ord("A"), ord("Z") + 1):
    _VK_MAP[chr(_c).upper()] = _c
for _d in range(10):
    _VK_MAP[str(_d)] = 0x30 + _d
_VK_MAP.update({
    "ESCAPE": VK_ESCAPE, "ESC": VK_ESCAPE,
    "ENTER": VK_RETURN, "RETURN": VK_RETURN,
    "TAB": VK_TAB, "BACKSPACE": VK_BACK,
    "SPACE": 0x20,
    "F1": 0x70, "F2": 0x71, "F3": 0x72, "F4": 0x73,
    "F5": 0x74, "F6": 0x75, "F7": 0x76, "F8": 0x77,
    "F9": 0x78, "F10": 0x79, "F11": 0x7A, "F12": 0x7B,
})


# ── Helpers ───────────────────────────────────────────────────────────

def _send_inputs(events: list[INPUT]) -> None:
    if not events:
        return
    arr = (INPUT * len(events))(*events)
    _user32.SendInput(len(events), ctypes.cast(arr, ctypes.POINTER(INPUT)), ctypes.sizeof(INPUT))


def _to_absolute(x: int, y: int) -> tuple[int, int]:
    """Convert pixel coordinates to 0-65535 normalised absolute coords."""
    screen_w = _user32.GetSystemMetrics(SM_CXSCREEN)
    screen_h = _user32.GetSystemMetrics(SM_CYSCREEN)
    abs_x = int(x * 65536 / screen_w) + 1
    abs_y = int(y * 65536 / screen_h) + 1
    return abs_x, abs_y


def spin_sleep_ms(ms: float) -> None:
    """High-precision spin-sleep using QueryPerformanceCounter."""
    if ms <= 0:
        return
    target_ticks = int(ms * _TICKS_PER_MS)
    start = ctypes.c_longlong()
    now = ctypes.c_longlong()
    _kernel32.QueryPerformanceCounter(ctypes.byref(start))
    while True:
        _kernel32.QueryPerformanceCounter(ctypes.byref(now))
        if now.value - start.value >= target_ticks:
            break


# ── Public API ────────────────────────────────────────────────────────

class InputDriver:
    """Stateless input injection driver for game automation."""

    def __init__(self) -> None:
        self._saved_pos: Optional[tuple[int, int]] = None

    # ── Cursor ────────────────────────────────────────────────────────

    def save_cursor(self) -> None:
        pt = wt.POINT()
        _user32.GetCursorPos(ctypes.byref(pt))
        self._saved_pos = (pt.x, pt.y)

    def restore_cursor(self) -> None:
        if self._saved_pos:
            _user32.SetCursorPos(self._saved_pos[0], self._saved_pos[1])
            self._saved_pos = None

    def move_cursor(self, x: int, y: int) -> None:
        """Move the cursor to (x, y) without clicking."""
        _user32.SetCursorPos(x, y)

    def hide_cursor(self) -> None:
        """Move the cursor off-screen to the bottom-left so it is not visible."""
        screen_h = _user32.GetSystemMetrics(SM_CYSCREEN)
        _user32.SetCursorPos(-1, screen_h + 1)

    # ── Mouse ─────────────────────────────────────────────────────────

    def click(
        self,
        x: int,
        y: int,
        pre_move_delay_ms: float = 5,
        hold_ms: float = 12,
    ) -> None:
        """Move cursor to (x, y) in screen pixels and left-click."""
        abs_x, abs_y = _to_absolute(x, y)

        move = INPUT(type=INPUT_MOUSE)
        move._input.mi = MOUSEINPUT(
            dx=abs_x, dy=abs_y, mouseData=0,
            dwFlags=MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE,
            time=0, dwExtraInfo=None,
        )

        down = INPUT(type=INPUT_MOUSE)
        down._input.mi = MOUSEINPUT(
            dx=abs_x, dy=abs_y, mouseData=0,
            dwFlags=MOUSEEVENTF_LEFTDOWN | MOUSEEVENTF_ABSOLUTE,
            time=0, dwExtraInfo=None,
        )

        up = INPUT(type=INPUT_MOUSE)
        up._input.mi = MOUSEINPUT(
            dx=abs_x, dy=abs_y, mouseData=0,
            dwFlags=MOUSEEVENTF_LEFTUP | MOUSEEVENTF_ABSOLUTE,
            time=0, dwExtraInfo=None,
        )

        _send_inputs([move])
        spin_sleep_ms(pre_move_delay_ms)
        _send_inputs([down])
        spin_sleep_ms(hold_ms)
        _send_inputs([up])

    def right_click(self, x: int, y: int) -> None:
        abs_x, abs_y = _to_absolute(x, y)

        move = INPUT(type=INPUT_MOUSE)
        move._input.mi = MOUSEINPUT(
            dx=abs_x, dy=abs_y, mouseData=0,
            dwFlags=MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE,
            time=0, dwExtraInfo=None,
        )

        down = INPUT(type=INPUT_MOUSE)
        down._input.mi = MOUSEINPUT(
            dx=abs_x, dy=abs_y, mouseData=0,
            dwFlags=MOUSEEVENTF_RIGHTDOWN | MOUSEEVENTF_ABSOLUTE,
            time=0, dwExtraInfo=None,
        )

        up = INPUT(type=INPUT_MOUSE)
        up._input.mi = MOUSEINPUT(
            dx=abs_x, dy=abs_y, mouseData=0,
            dwFlags=MOUSEEVENTF_RIGHTUP | MOUSEEVENTF_ABSOLUTE,
            time=0, dwExtraInfo=None,
        )

        _send_inputs([move])
        spin_sleep_ms(5)
        _send_inputs([down, up])

    def scroll(self, x: int, y: int, direction: str, amount: int) -> None:
        """
        Scroll the mouse wheel at (x, y).

        Mirrors the AHK script exactly: left-click at the scroll coord to
        focus the ship list, then fire the wheel event — once per notch.

        Parameters
        ----------
        direction : "wheelUp" / "up"  or  "wheelDown" / "down"
        amount : number of scroll notches
        """
        abs_x, abs_y = _to_absolute(x, y)
        delta = WHEEL_DELTA if "up" in direction.lower() else -WHEEL_DELTA

        # Move cursor to scroll coordinate once before the loop
        move = INPUT(type=INPUT_MOUSE)
        move._input.mi = MOUSEINPUT(
            dx=abs_x, dy=abs_y, mouseData=0,
            dwFlags=MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE,
            time=0, dwExtraInfo=None,
        )
        _send_inputs([move])

        for _ in range(abs(amount)):
            # AHK: "Click, x y" — left-click to maintain focus on the list
            # Use bare down+up with minimal hold (cursor already at position)
            down = INPUT(type=INPUT_MOUSE)
            down._input.mi = MOUSEINPUT(
                dx=abs_x, dy=abs_y, mouseData=0,
                dwFlags=MOUSEEVENTF_LEFTDOWN | MOUSEEVENTF_ABSOLUTE,
                time=0, dwExtraInfo=None,
            )
            up = INPUT(type=INPUT_MOUSE)
            up._input.mi = MOUSEINPUT(
                dx=abs_x, dy=abs_y, mouseData=0,
                dwFlags=MOUSEEVENTF_LEFTUP | MOUSEEVENTF_ABSOLUTE,
                time=0, dwExtraInfo=None,
            )
            _send_inputs([down])
            spin_sleep_ms(1)
            _send_inputs([up])

            # AHK: "MouseClick, wheelUp/Down" — scroll at current position
            wheel = INPUT(type=INPUT_MOUSE)
            wheel._input.mi = MOUSEINPUT(
                dx=abs_x, dy=abs_y,
                mouseData=ctypes.c_ulong(delta & 0xFFFFFFFF).value,
                dwFlags=MOUSEEVENTF_WHEEL | MOUSEEVENTF_ABSOLUTE,
                time=0, dwExtraInfo=None,
            )
            _send_inputs([wheel])
            spin_sleep_ms(1)  # AHK: Sleep, 1

    # ── Keyboard ──────────────────────────────────────────────────────

    def send_key(self, key: str) -> None:
        """Send a single key press (down + up) by name."""
        vk = self.vk_for_key(key)
        if vk is None:
            return

        down = INPUT(type=INPUT_KEYBOARD)
        down._input.ki = KEYBDINPUT(wVk=vk, wScan=0, dwFlags=0, time=0, dwExtraInfo=None)

        up = INPUT(type=INPUT_KEYBOARD)
        up._input.ki = KEYBDINPUT(wVk=vk, wScan=0, dwFlags=KEYEVENTF_KEYUP, time=0, dwExtraInfo=None)

        _send_inputs([down, up])

    def control_send_key(self, key: str, title: str = "StarConflict") -> None:
        """
        Send *key* directly to *title* window via PostMessage (ControlSend style).

        Works even when the game window is not the foreground window.
        Falls back to SendInput if the window cannot be found.
        """
        vk = self.vk_for_key(key)
        if vk is None:
            return
        hwnd = InputDriver._find_window_partial(title)
        if hwnd:
            _post_key_to_hwnd(hwnd, vk)
        else:
            # Fallback to SendInput
            self.send_key(key)

    def send_keys_string(self, text: str, delay_ms: float = 30) -> None:
        """Type a string character by character."""
        for ch in text:
            vk = _user32.VkKeyScanW(ord(ch)) & 0xFF
            if vk != 0xFF:
                down = INPUT(type=INPUT_KEYBOARD)
                down._input.ki = KEYBDINPUT(wVk=vk, wScan=0, dwFlags=0, time=0, dwExtraInfo=None)
                up = INPUT(type=INPUT_KEYBOARD)
                up._input.ki = KEYBDINPUT(wVk=vk, wScan=0, dwFlags=KEYEVENTF_KEYUP, time=0, dwExtraInfo=None)
                _send_inputs([down, up])
                spin_sleep_ms(delay_ms)

    @staticmethod
    def vk_for_key(key: str) -> int | None:
        """Resolve a key name to a virtual key code."""
        return _VK_MAP.get(key.upper())

    # ── Game window ───────────────────────────────────────────────────

    @staticmethod
    def is_game_focused(title: str = "StarConflict") -> bool:
        """Check if the game window is the foreground window."""
        hwnd = _user32.GetForegroundWindow()
        buf = ctypes.create_unicode_buffer(256)
        _user32.GetWindowTextW(hwnd, buf, 256)
        return title.lower() in buf.value.lower()

    @staticmethod
    def _enum_window_titles() -> list[str]:
        """Return titles of all top-level windows (for diagnostics)."""
        titles: list[str] = []

        @_WNDENUMPROC
        def _cb(hwnd, _lparam):
            buf = ctypes.create_unicode_buffer(256)
            _user32.GetWindowTextW(hwnd, buf, 256)
            if buf.value:
                titles.append(buf.value)
            return True

        _user32.EnumWindows(_cb, 0)
        return titles

    @staticmethod
    def _find_window_partial(title: str) -> int:
        """Return the HWND of the first window whose title contains *title* (case-insensitive)."""
        result: list[int] = [0]
        needle = title.lower()

        @_WNDENUMPROC
        def _cb(hwnd, _lparam):
            buf = ctypes.create_unicode_buffer(256)
            _user32.GetWindowTextW(hwnd, buf, 256)
            if needle in buf.value.lower():
                result[0] = hwnd
                return False  # stop enumeration
            return True

        _user32.EnumWindows(_cb, 0)
        return result[0]

    @staticmethod
    def find_game_window(title: str = "StarConflict") -> int:
        """Return HWND of the game window, or 0 if not found."""
        return InputDriver._find_window_partial(title)

    @staticmethod
    def focus_game_window(title: str = "StarConflict") -> bool:
        """Bring the game window to the foreground."""
        hwnd = InputDriver._find_window_partial(title)
        if hwnd:
            _user32.SetForegroundWindow(hwnd)
            spin_sleep_ms(100)
            return True
        return False
