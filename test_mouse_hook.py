import ctypes
from ctypes import wintypes
import time
import threading
import sys

# Constants
WH_MOUSE_LL = 14
WM_MOUSEWHEEL = 0x020A
WM_XBUTTONDOWN = 0x020B
XBUTTON1 = 0x0001
XBUTTON2 = 0x0002

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

LRESULT = ctypes.c_int64 if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_long
HHOOK = ctypes.c_void_p

user32.SetWindowsHookExW.argtypes = [ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint32]
user32.SetWindowsHookExW.restype = HHOOK

user32.CallNextHookEx.argtypes = [HHOOK, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM]
user32.CallNextHookEx.restype = LRESULT

user32.UnhookWindowsHookEx.argtypes = [HHOOK]
user32.UnhookWindowsHookEx.restype = wintypes.BOOL

class MSLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("pt", wintypes.POINT),
        ("mouseData", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]

def main():
    print("Starting Mouse Hook Test...")
    print("Press Mouse4 (Back) or Mouse5 (Forward) or scroll the wheel.")
    print("Press CTRL+C in this terminal to Exit.")
    
    # Hook procedure
    def hook_proc(nCode, wParam, lParam):
        if nCode >= 0:
            try:
                if wParam == WM_XBUTTONDOWN:
                    data = ctypes.cast(lParam, ctypes.POINTER(MSLLHOOKSTRUCT)).contents
                    btn = (data.mouseData >> 16) & 0xFFFF
                    if btn == XBUTTON1:
                        print("DETECTED: Mouse4 (XBUTTON1)")
                    elif btn == XBUTTON2:
                        print("DETECTED: Mouse5 (XBUTTON2)")
                        
                elif wParam == WM_MOUSEWHEEL:
                    data = ctypes.cast(lParam, ctypes.POINTER(MSLLHOOKSTRUCT)).contents
                    delta = data.mouseData >> 16
                    if delta > 32767: delta -= 65536
                    direction = "UP" if delta > 0 else "DOWN"
                    print(f"DETECTED: Wheel {direction}")
            except Exception as e:
                print(f"Error in hook: {e}")
                
        return user32.CallNextHookEx(None, nCode, wParam, lParam)

    HOOKPROC = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)
    proc = HOOKPROC(hook_proc)
    
    hHook = user32.SetWindowsHookExW(WH_MOUSE_LL, proc, kernel32.GetModuleHandleW(None), 0)
    if not hHook:
        print("Failed to install hook!")
        return

    print("Hook installed. Listening...")

    # Message loop
    msg = wintypes.MSG()
    try:
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))
    except (KeyboardInterrupt, SystemExit):
        print("\nExiting...")
    
    user32.UnhookWindowsHookEx(hHook)
    print("Hook removed.")

if __name__ == "__main__":
    main()
