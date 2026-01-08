import tkinter as tk
from tkinter import ttk
import ctypes
from ctypes import wintypes
import sys

class OverlayWindow(tk.Toplevel):
    def __init__(self, parent, x=100, y=100, on_move=None):
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
        sanitized_x = f"+{x}"
        sanitized_y = f"+{y}"
        # If negative, we still need the delimiter '+' unless the number itself has '-', but parsing `+ -100`?
        # Standard: "+-100+200".
        
        self.geometry(f"{sanitized_x}{sanitized_y}")
        self._target_x = x
        self._target_y = y
        self._on_move = on_move
        self._last_notified_pos = None
        self._is_editing = False
        
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
                x = int(x)
                y = int(y)
                # Use DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 (-4) to ensure coordinates 
                # are treated as physical screen coordinates without virtualization/scaling.
                ctx_prev = self._set_thread_dpi(self._DPI_PER_MON_V2)
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
        if self._is_editing:
            self._notify_move()

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
        if self._clickthrough or not self._is_editing:
            return
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
        self._notify_move()

    def _notify_move(self):
        if not self._on_move:
            return
        if getattr(self, "_dragging", False):
            return
        if not self.winfo_ismapped():
            return
        if not self._is_editing:
            return
        pos = self.get_physical_position()
        if pos == self._last_notified_pos:
            return
        self._last_notified_pos = pos
        try:
            self._on_move(*pos)
        except Exception:
            pass

    def toggle_edit_mode(self, editing: bool):
        self._is_editing = editing
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
    def __init__(self, parent, callback, selection_type="region"):
        super().__init__(parent)
        self.callback = callback
        self.selection_type = selection_type # "region" or "point"

        # Determine Virtual Screen Geometry (Logical, for Tkinter placement)
        v_x = ctypes.windll.user32.GetSystemMetrics(76) # SM_XVIRTUALSCREEN
        v_y = ctypes.windll.user32.GetSystemMetrics(77) # SM_YVIRTUALSCREEN
        v_w = ctypes.windll.user32.GetSystemMetrics(78) # SM_CXVIRTUALSCREEN
        v_h = ctypes.windll.user32.GetSystemMetrics(79) # SM_CYVIRTUALSCREEN
        
        self.geometry(f"{v_w}x{v_h}+{v_x}+{v_y}")
        self.overrideredirect(True)
        
        self.attributes("-alpha", 0.3)
        self.attributes("-topmost", True)
        self.configure(bg="black", cursor="crosshair")
        
        # Logical Start (for drawing)
        self.start_x = 0
        self.start_y = 0
        
        # Physical Start (for result)
        self.p_start_x = 0
        self.p_start_y = 0
        
        self.rect_id = None
        self.processed = False
        
        self.canvas = tk.Canvas(self, bg="black", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        self.canvas.bind("<Button-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Escape>", lambda e: self.destroy())

    def _get_physical_cursor_pos(self):
        pt = wintypes.POINT()
        ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
        return pt.x, pt.y

    def _on_press(self, event):
        self.start_x = event.x
        self.start_y = event.y
        self.p_start_x, self.p_start_y = self._get_physical_cursor_pos()
        
        if self.rect_id:
            self.canvas.delete(self.rect_id)
            
        if self.selection_type == "point":
             # Visual feedback: Crosshair/Circle
             r = 5
             self.rect_id = self.canvas.create_oval(
                 self.start_x - r, self.start_y - r, self.start_x + r, self.start_y + r,
                 outline="cyan", width=2
             )
        else:
            self.rect_id = self.canvas.create_rectangle(
                self.start_x, self.start_y, self.start_x, self.start_y,
                outline="red", width=2
            )

    def _on_drag(self, event):
        if self.rect_id:
            if self.selection_type == "point":
                 r = 5
                 self.canvas.coords(self.rect_id, event.x - r, event.y - r, event.x + r, event.y + r)
            else:
                 self.canvas.coords(self.rect_id, self.start_x, self.start_y, event.x, event.y)

    def _on_release(self, event):
        if self.processed:
            return
        self.processed = True
        
        # Physical End
        p_end_x, p_end_y = self._get_physical_cursor_pos()
        
        x1, y1 = self.p_start_x, self.p_start_y
        x2, y2 = p_end_x, p_end_y
        
        # Normalize
        left, top = min(x1, x2), min(y1, y2)
        width, height = abs(x2 - x1), abs(y2 - y1)
        
        # Determine Data
        data = None
        if self.selection_type == "point":
            # Always treat release as point
            # Use release coords if dragged, or start if clicked? 
            # Cursor pos at release is best for "Point"
            data = (p_end_x, p_end_y, 0, 0)
        else:
            # Region (allow fallback to point if tiny?)
            if width < 5 and height < 5:
                # If they clicked in region mode, maybe they meant point?
                # But safer to just return a tiny region or 0-size?
                # Current usage expects rect. 
                data = (left, top, max(1, width), max(1, height))
            else:
                data = (left, top, width, height)

        # Destroy FIRST to ensure window closes before any blocking callback actions
        self.destroy()
        
        # Schedule callback on parent to allow event loop to process destroy
        if self.master:
             self.master.after(5, lambda: self.callback(data))

