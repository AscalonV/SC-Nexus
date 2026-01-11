import threading
import time
from pathlib import Path
from typing import Optional, Tuple, List

# Try imports
try:
    import mss
    HAS_MSS = True
except ImportError:
    HAS_MSS = False

from PIL import Image

class ScreenScanner:
    def __init__(self):
        self.last_error = None
        if not HAS_MSS:
             self.last_error = "MSS Missing"
        
        self.lock = threading.Lock()
        
        # Cache templates: Name -> PIL.Image
        self.templates = {}

    def load_template(self, name: str, path: Path):
        print(f"[DEBUG] Loading template '{name}' from {path}")
        if not path.exists():
            print(f"[DEBUG] Template file not found: {path}")
            return
        try:
            # Load with PIL, convert to RGBA
            img = Image.open(path).convert("RGBA")
            # Resize logic if needed? Assuming 1:1 match
            self.templates[name] = img
            print(f"[DEBUG] Loaded '{name}' size={img.size}")
        except Exception as e:
            print(f"[DEBUG] Failed to load template '{name}': {e}")
            pass

    def find_template(self, region: Tuple[int, int, int, int], template_name: str, threshold=50) -> bool:
        """
        Pure Python Template Matching with Multi-Scale support.
        region: (left, top, width, height)
        threshold: Max average pixel difference (0-255). Lower is stricter.
        """
        if not HAS_MSS or template_name not in self.templates:
            if not HAS_MSS: print("[DEBUG] MSS not available")
            if template_name not in self.templates: print(f"[DEBUG] Template '{template_name}' not loaded")
            return False

        orig_template = self.templates[template_name]
        
        # Check region vs template sizes for 1.0x
        # If region is smaller than even smallest scale, fail
        t_w, t_h = orig_template.size
        if region[2] < (t_w * 0.5) or region[3] < (t_h * 0.5):
             self.last_error = f"Region too small"
             print(f"[DEBUG] Region too small for '{template_name}': Region={region[2]}x{region[3]}, Template={t_w}x{t_h}")
             return False

        monitor = {
            "top": int(region[1]),
            "left": int(region[0]),
            "width": int(region[2]),
            "height": int(region[3]),
        }

        with self.lock:
            try:
                # Use context manager for mss ensures thread safety and proper cleanup
                with mss.mss() as sct:
                    sct_img = sct.grab(monitor)
                
                screen_img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                screen_pixels = screen_img.load()
                sw, sh = screen_img.size
                
                # Updated: Scaling Support - DISABLED by default for performance
                # We try scales: 1.0 (Most likely for custom assets)
                # Adding more scales (1.25, 1.5) causes massive CPU spikes in pure Python
                scales = [1.0] 
                
                best_diff = 999
                
                for scale in scales:
                    if scale == 1.0:
                        template_img = orig_template
                    else:
                        new_size = (int(t_w * scale), int(t_h * scale))
                        template_img = orig_template.resize(new_size, Image.Resampling.LANCZOS)
                    
                    tw, th = template_img.size
                    if tw > sw or th > sh: continue

                    template_pixels = template_img.load()

                    # FIND VALID ANCHOR (Opaque Pixel)
                    cx, cy = -1, -1
                    for ay in range(0, th, 2):
                        for ax in range(0, tw, 2):
                            if template_pixels[ax, ay][3] > 200: 
                                cx, cy = ax, ay
                                break
                        if cx != -1: break
                    
                    if cx == -1: cx, cy = tw // 2, th // 2
                    
                    c_pix = template_pixels[cx, cy]
                    cr, cg, cb = c_pix[0], c_pix[1], c_pix[2]
                    ca = c_pix[3] if len(c_pix) > 3 else 255
                    use_anchor = (ca > 150)

                    # Scan Screen for this Scale
                    # Optimization: Step size 2 (Check every 2nd pixel). 
                    # The icon is ~30px wide, so we won't miss it.
                    # This reduces workload by 4x.
                    for y in range(0, sh - th, 2):
                        for x in range(0, sw - tw, 2):
                            if use_anchor:
                                sp = screen_pixels[x+cx, y+cy]
                                if abs(sp[0]-cr) + abs(sp[1]-cg) + abs(sp[2]-cb) > (threshold * 3):
                                    continue
                                
                            total_diff = 0
                            checked_pixels = 0
                            
                            # Check grid
                            # Optim: Abort early if diff gets too high
                            abort = False
                            max_total = (threshold * 3) # Per pixel average limit... wait.
                            # We want avg_diff < threshold*3.
                            # So total_diff < (checked * threshold * 3).
                            # We can't check total vs checked dynamically easily without accumulation.
                            
                            for py in range(0, th, 2):
                                for px in range(0, tw, 2):
                                    t_pix = template_pixels[px, py]
                                    if t_pix[3] < 50: continue
                                    
                                    s_pix = screen_pixels[x+px, y+py]
                                    pixel_diff = abs(s_pix[0]-t_pix[0]) + abs(s_pix[1]-t_pix[1]) + abs(s_pix[2]-t_pix[2])
                                    total_diff += pixel_diff
                                    checked_pixels += 1
                                    
                                    # Early abort heuristic (strict)
                                    # If current average is WAY off (e.g. > threshold*6) after 10 pixels
                                    if checked_pixels > 10 and (total_diff / checked_pixels) > (threshold * 6):
                                        abort = True
                                        break
                                if abort: break
                            
                            if not abort and checked_pixels > 5:
                                avg_diff = total_diff / checked_pixels
                                if avg_diff < best_diff:
                                    best_diff = avg_diff
                                    
                                if avg_diff < (threshold * 3):
                                    # Match Found!
                                    # print(f"[DEBUG] Found '{template_name}' at scale {scale} with diff {avg_diff:.2f}")
                                    return True
                
                # If we get here, no match found
                # print(f"[DEBUG] Scan '{template_name}' failed. Best Diff: {best_diff:.2f} (Threshold: {threshold*3})")
                return False
            except Exception as e:
                self.last_error = f"Template Error: {e}"
                print(f"[DEBUG] Exception in find_template: {e}")
                return False

    def get_pixel_color(self, x: int, y: int) -> Tuple[int, int, int]:
        """Returns (R, G, B)"""
        if not HAS_MSS:
            return (0, 0, 0)
            
        monitor = {
            "top": int(y),
            "left": int(x),
            "width": 1,
            "height": 1,
        }
        with self.lock:
            try:
                with mss.mss() as sct:
                    sct_img = sct.grab(monitor)
                # sct stores as BGRA, access raw
                # pixel is at [0][0]
                # data is accessible via sct_img.pixel(0, 0) -> (r, g, b)
                return sct_img.pixel(0, 0)
            except Exception as e:
                self.last_error = f"Pixel Error: {e}"
                print(f"[DEBUG] Pixel Error: {e}")
                return (0, 0, 0)
