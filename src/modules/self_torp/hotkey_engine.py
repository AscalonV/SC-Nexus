"""
HotkeyEngine — Windows global hotkey listener and SendInput burst engine.

Runs inside a QThread so it owns a Windows message loop.  All inter-thread
communication happens exclusively through Qt signals.

Key types supported
-------------------
  • Keyboard keys: letters (A-Z), digits (0-9), F1-F24, arrows, numpad, special
  • Mouse extra buttons: Mouse4 (XBUTTON1), Mouse5 (XBUTTON2) — polled at ~100Hz
  • Mouse wheel: Up / Down — hooked via WH_MOUSE_LL

Admin privileges are required to install low-level hooks.
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import threading
import time
from typing import Callable

from PySide6.QtCore import QThread, Signal, Slot

# ---------------------------------------------------------------------------
# ctypes structures for SendInput
# ---------------------------------------------------------------------------

LLKHF_INJECTED = 0x10

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk",         wt.WORD),
        ("wScan",       wt.WORD),
        ("dwFlags",     wt.DWORD),
        ("time",        wt.DWORD),
        ("dwExtraInfo", ctypes.POINTER(wt.ULONG)),
    ]

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx",          wt.LONG),
        ("dy",          wt.LONG),
        ("mouseData",   wt.DWORD),
        ("dwFlags",     wt.DWORD),
        ("time",        wt.DWORD),
        ("dwExtraInfo", ctypes.POINTER(wt.ULONG)),
    ]

class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg",    wt.DWORD),
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
        ("type",    wt.DWORD),
        ("_input",  _INPUT_UNION),
    ]

INPUT_KEYBOARD  = 1
INPUT_MOUSE     = 0
KEYEVENTF_KEYUP = 0x0002

MOUSEEVENTF_XDOWN = 0x0080
MOUSEEVENTF_XUP   = 0x0100
MOUSEEVENTF_WHEEL = 0x0800
WHEEL_DELTA       = 120

class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode",      wt.DWORD),
        ("scanCode",    wt.DWORD),
        ("flags",       wt.DWORD),
        ("time",        wt.DWORD),
        ("dwExtraInfo", ctypes.POINTER(wt.ULONG)),
    ]


class MSLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("pt",          wt.POINT),
        ("mouseData",   wt.DWORD),
        ("flags",       wt.DWORD),
        ("time",        wt.DWORD),
        ("dwExtraInfo", ctypes.POINTER(wt.ULONG)),
    ]

# ---------------------------------------------------------------------------
# Timer resolution (winmm)
# ---------------------------------------------------------------------------

_winmm = ctypes.windll.winmm

# ---------------------------------------------------------------------------
# Virtual key code table
# ---------------------------------------------------------------------------

_VK_MAP: dict[str, int] = {
    # Letters
    **{c: ord(c) for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"},
    # Digits
    **{str(d): ord(str(d)) for d in range(10)},
    # Function keys
    **{f"F{n}": 0x6F + n for n in range(1, 25)},
    # Arrows
    "LEFT": 0x25, "UP": 0x26, "RIGHT": 0x27, "DOWN": 0x28,
    # Numpad
    **{f"NUMPAD{n}": 0x60 + n for n in range(10)},
    "MULTIPLY": 0x6A, "ADD": 0x6B, "SUBTRACT": 0x6D, "DECIMAL": 0x6E, "DIVIDE": 0x6F,
    # Misc
    "SPACE": 0x20, "RETURN": 0x0D, "TAB": 0x09, "ESCAPE": 0x1B,
    "INSERT": 0x2D, "DELETE": 0x2E, "HOME": 0x24, "END": 0x23,
    "PRIOR": 0x21, "NEXT": 0x22,
    # Mouse extra
    "MOUSE4": None,   # polled via GetAsyncKeyState(VK_XBUTTON1)
    "MOUSE5": None,
    "WHEELUP":   None,
    "WHEELDOWN": None,
}

_VK_XBUTTON1 = 0x05
_VK_XBUTTON2 = 0x06
_XBUTTON1    = 0x0001
_XBUTTON2    = 0x0002


def vk_for_key(key_name: str) -> int | None:
    """Return the Windows VK code, or None for mouse/wheel keys."""
    k = key_name.upper()
    if k in _VK_MAP:
        return _VK_MAP[k]
    # Single printable character not in the static table (e.g. '.', ',', 'ä', 'ö', 'ü').
    # VkKeyScanW resolves to the VK code for the key that produces this character
    # on the user's current keyboard layout.
    if len(key_name) == 1 and key_name.isprintable():
        result = _user32.VkKeyScanW(ord(key_name))
        if (result & 0xFFFF) != 0xFFFF:   # 0xFFFF / -1 means not found
            return result & 0xFF           # low byte = VK code
    return None


def _is_wheel_key(key_name: str) -> bool:
    return key_name.upper() in ("WHEELUP", "WHEELDOWN")


def _is_xbutton_key(key_name: str) -> bool:
    return key_name.upper() in ("MOUSE4", "MOUSE5")


# ---------------------------------------------------------------------------
# HotkeyEngine
# ---------------------------------------------------------------------------

_user32 = ctypes.windll.user32

# ---------------------------------------------------------------------------
# High-precision spin-sleep via QueryPerformanceCounter
# ---------------------------------------------------------------------------
_kernel32 = ctypes.windll.kernel32

_qpc_freq = ctypes.c_longlong()
_kernel32.QueryPerformanceFrequency(ctypes.byref(_qpc_freq))
_QPC_US_TICKS: float = _qpc_freq.value / 1_000_000.0  # counter ticks per microsecond


def _qpc_now() -> int:
    t = ctypes.c_longlong()
    _kernel32.QueryPerformanceCounter(ctypes.byref(t))
    return t.value


def _spin_sleep_us(us: int) -> None:
    """Spin-wait for `us` microseconds using QueryPerformanceCounter."""
    end = _qpc_now() + int(us * _QPC_US_TICKS)
    while _qpc_now() < end:
        pass

WH_KEYBOARD_LL = 13
WH_MOUSE_LL    = 14
WM_KEYDOWN     = 0x0100
WM_SYSKEYDOWN  = 0x0104
WM_MOUSEWHEEL  = 0x020A
WM_XBUTTONDOWN = 0x020B
HC_ACTION      = 0

THREAD_PRIORITY_HIGHEST = 2


class HotkeyEngine(QThread):
    """
    Background QThread that owns the Windows message loop and monitors
    for hotkey presses.

    Signals
    -------
    hotkey_fired — emitted (on this thread) when the trigger key is detected.
    """

    hotkey_fired: Signal = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._hotkey_vk:  int | None = None    # trigger VK code (None = mouse/wheel)
        self._hotkey_name: str = ""
        self._first_vk:   int | None = None
        self._burst_vk:   int | None = None
        self._burst_vk2:  int | None = None
        self._first_name:  str = ""
        self._burst_name:  str = ""
        self._burst_name2: str = ""
        self._burst_count: int = 15
        self._first_key_delay_s: float = 0.05
        self._burst_gap_us: int = 1000

        self._active = False
        self._fire_lock = threading.Lock()
        self._fire_event = threading.Event()
        self._hook_kb:   int = 0
        self._hook_ms:   int = 0
        self._thread_id: int | None = None
        self._poll_thread:   threading.Thread | None = None
        self._worker_thread: threading.Thread | None = None
        self._last_trigger_tick: int = 0

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def configure(
        self,
        hotkey_name: str,
        first_key_name: str,
        burst_key_name: str,
        burst_key_name2: str = "",
        burst_count: int = 15,
        first_key_delay_ms: int = 50,
        burst_gap_ms: int = 1,
    ) -> None:
        self._hotkey_name  = hotkey_name.upper()
        self._first_name   = first_key_name.upper()
        self._burst_name   = burst_key_name.upper()
        self._burst_name2  = burst_key_name2.upper() if burst_key_name2 else ""
        self._burst_count  = max(1, burst_count)
        self._first_key_delay_s = max(0.0, first_key_delay_ms / 1000.0)
        self._burst_gap_us = max(0, burst_gap_ms * 1000)
        self._hotkey_vk    = vk_for_key(hotkey_name)
        self._first_vk     = vk_for_key(first_key_name)
        self._burst_vk     = vk_for_key(burst_key_name)
        self._burst_vk2    = vk_for_key(burst_key_name2) if burst_key_name2 else None

    # ------------------------------------------------------------------
    # QThread entry point
    # ------------------------------------------------------------------

    def run(self) -> None:
        self._active = True
        self._thread_id = int(ctypes.windll.kernel32.GetCurrentThreadId())

        # Request 1ms timer resolution for accurate sleeps
        _winmm.timeBeginPeriod(1)

        self._install_hooks()
        self._start_poll_thread()
        self._start_worker_thread()

        # Windows message loop — required to receive hook callbacks
        msg = wt.MSG()
        while self._active:
            ret = _user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if ret <= 0:
                break
            _user32.TranslateMessage(ctypes.byref(msg))
            _user32.DispatchMessageW(ctypes.byref(msg))

        self._uninstall_hooks()
        _winmm.timeEndPeriod(1)
        self._thread_id = None

    def stop(self) -> None:
        self._active = False
        self._fire_event.set()  # wake worker so it can exit
        # Post WM_QUIT to unblock GetMessageW
        if self._thread_id is not None:
            _user32.PostThreadMessageW(self._thread_id, 0x0012, 0, 0)
        self.wait(3000)

    # ------------------------------------------------------------------
    # Hooks
    # ------------------------------------------------------------------

    def _install_hooks(self) -> None:
        LowLevelMouseProc   = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_int, wt.WPARAM, ctypes.POINTER(MSLLHOOKSTRUCT))
        LowLevelKeyboardProc = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_int, wt.WPARAM, ctypes.POINTER(KBDLLHOOKSTRUCT))

        self._kb_proc   = LowLevelKeyboardProc(self._keyboard_hook)
        self._mouse_proc = LowLevelMouseProc(self._mouse_hook)

        hmod = ctypes.windll.kernel32.GetModuleHandleW(None)
        self._hook_kb = _user32.SetWindowsHookExW(WH_KEYBOARD_LL, self._kb_proc, hmod, 0)
        self._hook_ms = _user32.SetWindowsHookExW(WH_MOUSE_LL,    self._mouse_proc, hmod, 0)

    def _uninstall_hooks(self) -> None:
        if self._hook_kb:
            _user32.UnhookWindowsHookEx(self._hook_kb)
        if self._hook_ms:
            _user32.UnhookWindowsHookEx(self._hook_ms)

    def _keyboard_hook(self, nCode: int, wParam: int, lParam) -> int:
        if nCode == HC_ACTION and wParam in (WM_KEYDOWN, WM_SYSKEYDOWN):
            ks = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
            # Ignore injected keystrokes (our own SendInput calls)
            if not (ks.flags & LLKHF_INJECTED):
                if self._hotkey_vk is not None and ks.vkCode == self._hotkey_vk:
                    self._fire()
        return _user32.CallNextHookEx(self._hook_kb, nCode, wParam, lParam)

    def _mouse_hook(self, nCode: int, wParam: int, lParam) -> int:
        if nCode == HC_ACTION and wParam == WM_MOUSEWHEEL:
            wheel_data = lParam.contents.mouseData
            delta_word = (wheel_data >> 16) & 0xFFFF
            delta = ctypes.c_short(delta_word).value
            if self._hotkey_name == "WHEELUP" and delta > 0:
                self._fire()
            elif self._hotkey_name == "WHEELDOWN" and delta < 0:
                self._fire()

        if nCode == HC_ACTION and wParam == WM_XBUTTONDOWN:
            button_word = (lParam.contents.mouseData >> 16) & 0xFFFF
            if self._hotkey_name == "MOUSE4" and button_word == _XBUTTON1:
                self._fire()
            elif self._hotkey_name == "MOUSE5" and button_word == _XBUTTON2:
                self._fire()

        return _user32.CallNextHookEx(self._hook_ms, nCode, wParam, lParam)

    # ------------------------------------------------------------------
    # Mouse button polling (Mouse4 / Mouse5 can't be caught reliably in hook)
    # ------------------------------------------------------------------

    def _start_poll_thread(self) -> None:
        if self._hotkey_name not in ("MOUSE4", "MOUSE5"):
            return

        vk = _VK_XBUTTON1 if self._hotkey_name == "MOUSE4" else _VK_XBUTTON2
        last_state = False

        def _poll() -> None:
            nonlocal last_state
            _kernel32.SetThreadPriority(_kernel32.GetCurrentThread(), THREAD_PRIORITY_HIGHEST)
            while self._active:
                state = bool(_user32.GetAsyncKeyState(vk) & 0x8000)
                if state and not last_state:
                    self._fire()
                last_state = state
                time.sleep(0.001)

        self._poll_thread = threading.Thread(target=_poll, daemon=True)
        self._poll_thread.start()

    # ------------------------------------------------------------------
    # Persistent worker thread
    # ------------------------------------------------------------------

    def _start_worker_thread(self) -> None:
        def _worker() -> None:
            _kernel32.SetThreadPriority(_kernel32.GetCurrentThread(), THREAD_PRIORITY_HIGHEST)
            while self._active:
                self._fire_event.wait()
                if not self._active:
                    break
                self._fire_event.clear()
                try:
                    self._execute_burst()
                    self.hotkey_fired.emit()
                except Exception:
                    pass  # Never let a burst error kill the worker thread
                finally:
                    self._fire_lock.release()

        self._worker_thread = threading.Thread(target=_worker, daemon=True)
        self._worker_thread.start()

    # ------------------------------------------------------------------
    # Fire sequence
    # ------------------------------------------------------------------

    def _fire(self) -> None:
        now = _qpc_now()
        # Deduplicate hook + polling fallback triggers for the same physical press.
        if self._last_trigger_tick and (now - self._last_trigger_tick) < int(5_000 * _QPC_US_TICKS):
            return
        self._last_trigger_tick = now

        if not self._fire_lock.acquire(blocking=False):
            return  # already firing
        self._fire_event.set()

    def _execute_burst(self) -> None:
        # --- First key (module selection) ---
        if self._first_name:
            _send_action(self._first_name)
            if self._first_key_delay_s > 0:
                time.sleep(self._first_key_delay_s)

        # --- Burst: separate SendInput calls with a precise spin-sleep between each.
        #
        # Why separate calls instead of one big batch:
        # SendInput injects all events atomically into the queue. The game drains
        # the entire queue in one pump cycle before running its state-update step,
        # so a 0-gap batch means the torpedo is still in 'launching' state when the
        # second press arrives and the detonation input is silently dropped.
        # A spin-sleep gap lets the game's own message-loop iteration (and therefore
        # its state transition from 'launching' → 'in-flight') complete between presses.
        #
        # Dual-key mode: overlapping hold pattern [vk1↓ vk2↓ vk1↑ vk2↑] in one
        # SendInput call.  vk1 launches; vk2 detonates while vk1 is still held.
        # They are different VK codes so there is no repeat-suppression / debounce.
        # -------------------------------------------------------------------

        if self._burst_name and self._burst_name2:
            # Dual-key mode is the reliability path: one deterministic pair is
            # enough to launch and detonate. Repeating many pairs only widens
            # the window where the torpedo camera can flash and reset aim.
            _send_action_pair(self._burst_name, self._burst_name2)

        elif self._burst_name or self._burst_name2:
            action_name = self._burst_name or self._burst_name2
            for i in range(self._burst_count):
                _send_action(action_name)
                if i < self._burst_count - 1 and self._burst_gap_us > 0:
                    _spin_sleep_us(self._burst_gap_us)


# ---------------------------------------------------------------------------
# SendInput helpers
# ---------------------------------------------------------------------------

def _send_inputs(events: list[INPUT]) -> None:
    if not events:
        return
    InputArray = INPUT * len(events)
    inputs = InputArray()
    for index, event in enumerate(events):
        inputs[index] = event
    _user32.SendInput(len(events), ctypes.byref(inputs), ctypes.sizeof(INPUT))


def _keyboard_events(vk: int) -> list[INPUT]:
    key_down = INPUT(type=INPUT_KEYBOARD)
    key_down._input.ki = KEYBDINPUT(wVk=vk, wScan=0, dwFlags=0, time=0, dwExtraInfo=None)
    key_up = INPUT(type=INPUT_KEYBOARD)
    key_up._input.ki = KEYBDINPUT(wVk=vk, wScan=0, dwFlags=KEYEVENTF_KEYUP, time=0, dwExtraInfo=None)
    return [key_down, key_up]


def _wheel_events(key_name: str) -> list[INPUT]:
    wheel = INPUT(type=INPUT_MOUSE)
    delta = WHEEL_DELTA if key_name.upper() == "WHEELUP" else -WHEEL_DELTA
    wheel._input.mi = MOUSEINPUT(
        dx=0,
        dy=0,
        mouseData=ctypes.c_ulong(delta & 0xFFFFFFFF).value,
        dwFlags=MOUSEEVENTF_WHEEL,
        time=0,
        dwExtraInfo=None,
    )
    return [wheel]


def _xbutton_events(key_name: str) -> list[INPUT]:
    button_flag = _XBUTTON1 if key_name.upper() == "MOUSE4" else _XBUTTON2
    button_down = INPUT(type=INPUT_MOUSE)
    button_down._input.mi = MOUSEINPUT(
        dx=0,
        dy=0,
        mouseData=button_flag,
        dwFlags=MOUSEEVENTF_XDOWN,
        time=0,
        dwExtraInfo=None,
    )
    button_up = INPUT(type=INPUT_MOUSE)
    button_up._input.mi = MOUSEINPUT(
        dx=0,
        dy=0,
        mouseData=button_flag,
        dwFlags=MOUSEEVENTF_XUP,
        time=0,
        dwExtraInfo=None,
    )
    return [button_down, button_up]


def _events_for_action(action_name: str) -> list[INPUT]:
    if not action_name:
        return []

    if _is_wheel_key(action_name):
        return _wheel_events(action_name)
    if _is_xbutton_key(action_name):
        return _xbutton_events(action_name)

    vk = vk_for_key(action_name)
    if vk is None:
        return []
    return _keyboard_events(vk)


def _send_action(action_name: str) -> None:
    _send_inputs(_events_for_action(action_name))


def _send_key(vk: int) -> None:
    """Single key press+release as one 2-event SendInput call."""
    _send_inputs(_keyboard_events(vk))


def _send_overlapping_pair(vk1: int, vk2: int) -> None:
    """Send [vk1↓, vk2↓, vk1↑, vk2↑] in a single 4-event SendInput call.

    vk1 launches the torpedo; vk2 detonates while vk1 is still physically
    held.  Because they are different VK codes the game sees them as two
    independent presses with no repeat-suppression between them.
    """
    _send_inputs([
        _keyboard_events(vk1)[0],
        _keyboard_events(vk2)[0],
        _keyboard_events(vk1)[1],
        _keyboard_events(vk2)[1],
    ])


def _send_action_pair(action1: str, action2: str) -> None:
    vk1 = vk_for_key(action1)
    vk2 = vk_for_key(action2)
    if vk1 is not None and vk2 is not None:
        _send_overlapping_pair(vk1, vk2)
        return

    _send_inputs(_events_for_action(action1) + _events_for_action(action2))
