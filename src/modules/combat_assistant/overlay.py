import tkinter as tk
from tkinter import ttk
import ctypes
from ctypes import wintypes
import sys

class OverlayWindow(tk.Toplevel):
    def __init__(self, parent, x=100, y=100):
        super().__init__(parent)
        # Defer overrideredirect to allow proper window manager placement
        self.withdraw()

        # DPI/base metrics
        self._base_dpi = 96
        self._base_phys_size = None
        self._lock_size_active = False
        self._last_monitor = None
        # DPI awareness contexts
        self._DPI_UNAWARE_GDI = ctypes.c_void_p(-5)  # DPI_AWARENESS_CONTEXT_UNAWARE_GDISCALED
        self._DPI_PER_MON_V2 = ctypes.c_void_p(-4)   # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2
        
        # Transparent background setup
        self.TRANS_COLOR = "#000001"
        self.configure(bg=self.TRANS_COLOR)
        self.attributes("-transparentcolor", self.TRANS_COLOR)
        self.attributes("-topmost", True)
        
        # Safe Geometry Set
        # If x is negative, ensure format "+-100" (which means X=-100) not "-100" (which means R=100)
        # Tkinter geometry: "WxH+X+Y". If X < 0, "+-X".
        sanitized_x = f"+{x}" if x >= 0 else f"{x}"
        sanitized_y = f"+{y}" if y >= 0 else f"{y}"
        # If negative, we still need the delimiter '+' unless the number itself has '-', but parsing `+ -100`?
        # Standard: "+-100+200".
        
        self.geometry(f"+{x}+{y}")
        self._target_x = x
        self._target_y = y
        
        self._dragging = False
        self._offset_x = 0
        self._offset_y = 0
        self._clickthrough = True
        
        # Main container
        self.container = tk.Frame(self, bg=self.TRANS_COLOR)
        self.container.pack(fill=tk.BOTH, expand=True)
        
        self.bind("<Button-1>", self._start_drag)
        self.bind("<B1-Motion>", self._do_drag)
        self.bind("<ButtonRelease-1>", self._stop_drag)
        self.bind("<Configure>", self._on_configure)
        
        self.set_clickthrough(True)
        
        # Finalize initialization
        self.after(100, self._finalize_init)

    def _finalize_init(self):
        self.overrideredirect(True)
        # Force position using SetWindowPos to bypass Tkinter's DPI scaling logic
        # This ensures the window appears exactly at the physical coords saved from last session.
        self._safe_place(self._target_x, self._target_y)

        # Capture baseline DPI/size after initial placement
        self._capture_base_metrics()
        self._lock_physical_size(force=True)
        
        if self.state() == 'normal': # If meant to be shown
             self.deiconify()
        self.set_clickthrough(self._clickthrough)

    def _safe_place(self, x, y):
        """Place window at specific physical coordinates using Windows API."""
        try:
            if sys.platform == "win32":
                ctx_prev = self._set_thread_dpi(self._DPI_UNAWARE_GDI)
                hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
                # SWP_NOSIZE (0x0001) | SWP_NOZORDER (0x0004) | SWP_NOACTIVATE (0x0010)
                ctypes.windll.user32.SetWindowPos(hwnd, 0, x, y, 0, 0, 0x0001 | 0x0004 | 0x0010)
                self._restore_thread_dpi(ctx_prev)
        except Exception:
            pass

    def _set_thread_dpi(self, ctx):
        if sys.platform != "win32":
            return None
        try:
            return ctypes.windll.user32.SetThreadDpiAwarenessContext(ctx)
        except Exception:
            return None

    def _restore_thread_dpi(self, prev_ctx):
        if sys.platform != "win32":
            return
        if prev_ctx:
            try:
                ctypes.windll.user32.SetThreadDpiAwarenessContext(prev_ctx)
            except Exception:
                pass

    def _get_window_dpi(self):
        if sys.platform != "win32":
            return 96
        try:
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            dpi = ctypes.windll.user32.GetDpiForWindow(hwnd)
            if dpi:
                return int(dpi)
        except Exception:
            pass
        return 96

    def _capture_base_metrics(self):
        if sys.platform != "win32":
            return
        try:
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            rect = wintypes.RECT()
            if ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                width = rect.right - rect.left
                height = rect.bottom - rect.top
                self._base_phys_size = (width, height)
                self._base_dpi = self._get_window_dpi()
        except Exception:
            pass

    def _lock_physical_size(self, force=False):
        """Resize overlay using DPI-unaware GDI scaling so physical size stays consistent per monitor."""
        if sys.platform != "win32":
            return
        if self._lock_size_active and not force:
            return
        try:
            self.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            rect = wintypes.RECT()
            monitor = None
            try:
                monitor = ctypes.windll.user32.MonitorFromWindow(hwnd, 2)  # MONITOR_DEFAULTTONEAREST
            except Exception:
                monitor = None
            # Only reapply when monitor changes or forced
            if not force and monitor and monitor == self._last_monitor:
                return
            self._last_monitor = monitor

            req_w = max(1, self.container.winfo_reqwidth())
            req_h = max(1, self.container.winfo_reqheight())
            ctx_prev = self._set_thread_dpi(self._DPI_UNAWARE_GDI)
            self._lock_size_active = True
            # SWP_NOMOVE | SWP_NOZORDER | SWP_NOACTIVATE
            ctypes.windll.user32.SetWindowPos(hwnd, 0, 0, 0, req_w, req_h, 0x0002 | 0x0004 | 0x0010)
            self._restore_thread_dpi(ctx_prev)
        except Exception:
            pass
        finally:
            self._lock_size_active = False

    def _on_configure(self, _event=None):
        # When DPI changes, Tk might try to resize; force back to baseline size
        if sys.platform != "win32":
            return
        self._lock_physical_size()

    def set_clickthrough(self, enable: bool):
        if sys.platform != "win32":
            return
            
        self._clickthrough = enable
        try:
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            # GWL_EXSTYLE = -20
            # WS_EX_LAYERED = 0x80000
            # WS_EX_TRANSPARENT = 0x20
            
            style = ctypes.windll.user32.GetWindowLongW(hwnd, -20)
            
            if enable:
                # Add transparent flag (clicks pass through)
                style = style | 0x80000 | 0x20
            else:
                # Remove transparent flag (clicks caught by window)
                style = (style | 0x80000) & ~0x20
                
            ctypes.windll.user32.SetWindowLongW(hwnd, -20, style)
        except Exception:
            pass

    def _do_drag(self, event):
        if self._dragging:
            dx = event.x_root - self._start_x_root
            dy = event.y_root - self._start_y_root
            
            new_x = self._start_win_x + dx
            new_y = self._start_win_y + dy
            
            # Use SetWindowPos for smooth dragging that ignores DPI weirdness
            try:
                if sys.platform == "win32":
                    hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
                    ctypes.windll.user32.SetWindowPos(hwnd, 0, new_x, new_y, 0, 0, 0x0001 | 0x0004 | 0x0010)
                else:
                    self.geometry(f"+{new_x}+{new_y}")
            except:
                self.geometry(f"+{new_x}+{new_y}")

    def _start_drag(self, event):
        if self._clickthrough: return
        self._dragging = True
        self._start_x_root = event.x_root
        self._start_y_root = event.y_root
        # Use winfo_rootx/y which returns physical coords in System Aware mode
        self._start_win_x = self.winfo_rootx()
        self._start_win_y = self.winfo_rooty()

    @property
    def runnable_x(self):
        # winfo_rootx is more reliable for screen coordinates on Windows
        if sys.platform == "win32":
            pos = self.get_physical_position()
            return pos[0]
        return self.winfo_rootx()

    @property
    def runnable_y(self):
        if sys.platform == "win32":
            pos = self.get_physical_position()
            return pos[1]
        return self.winfo_rooty()

    def get_physical_position(self):
        """Return top-left coords in physical pixels to survive mixed-DPI setups."""
        if sys.platform == "win32":
            try:
                hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
                rect = wintypes.RECT()
                if ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                    return (rect.left, rect.top)
            except Exception:
                pass
        # Fallback to Tk's coordinates (may be DPI-scaled)
        return (self.winfo_rootx(), self.winfo_rooty())

    def _stop_drag(self, event):
        self._dragging = False

    def toggle_edit_mode(self, editing: bool):
        self.set_clickthrough(not editing)
        if editing:
            self.configure(bg="#222222") # Visible background
            self.attributes("-transparentcolor", "") # Disable transparency key 
            # Note: Toggling transparency key off might not fully work without recreation on some systems,
            # but usually changing bg color to something other than trans key is enough if key is unset.
            # Actually, to make it fully opaque for editing:
            self.attributes("-transparentcolor", "")
            self.container.configure(bg="#222222")
            # Draw a border or title
        else:
            self.configure(bg=self.TRANS_COLOR)
            self.attributes("-transparentcolor", self.TRANS_COLOR)
            self.container.configure(bg=self.TRANS_COLOR)

    def show(self):
        self.deiconify()
        # Re-apply clickthrough after showing
        self.after(100, lambda: self.set_clickthrough(self._clickthrough))

    def hide(self):
        self.withdraw()

class CalibrationOverlay(tk.Toplevel):
    "Fullscreen slightly opaque window to select regions."
    def __init__(self, parent, callback):
        super().__init__(parent)
        self.callback = callback
        self.attributes("-fullscreen", True)
        self.attributes("-alpha", 0.3)
        self.attributes("-topmost", True)
        self.configure(bg="black", cursor="crosshair")
        
        self.start_x = 0
        self.start_y = 0
        self.rect_id = None
        
        self.canvas = tk.Canvas(self, bg="black", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        self.canvas.bind("<Button-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Escape>", lambda e: self.destroy())

    def _on_press(self, event):
        self.start_x = event.x
        self.start_y = event.y
        if self.rect_id:
            self.canvas.delete(self.rect_id)
        self.rect_id = self.canvas.create_rectangle(
            self.start_x, self.start_y, self.start_x, self.start_y,
            outline="red", width=2
        )

    def _on_drag(self, event):
        if self.rect_id:
            self.canvas.coords(self.rect_id, self.start_x, self.start_y, event.x, event.y)

    def _on_release(self, event):
        x1, y1 = self.start_x, self.start_y
        x2, y2 = event.x, event.y
        # Normalize
        left, top = min(x1, x2), min(y1, y2)
        width, height = abs(x2 - x1), abs(y2 - y1)
        
        # If just a click (or tiny drag), treat as point
        if width < 5 and height < 5:
            self.callback((left, top, 0, 0)) # Point
        else:
            self.callback((left, top, width, height)) # Region
            
        self.destroy()

