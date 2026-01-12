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

    def find_template(
        self,
        region: Tuple[int, int, int, int],
        template_name: str,
        threshold=50,
        *,
        return_positions: bool = False,
        max_results: int = 1,
    ):
        """
        Pure Python Template Matching with Multi-Scale support.

        region: (left, top, width, height)
        threshold: Max average pixel difference (0-255). Lower is stricter.
        return_positions: when True, collect up to `max_results` absolute (x, y) matches instead of
            short-circuiting on the first hit.
        """
        if not HAS_MSS or template_name not in self.templates:
            if not HAS_MSS: print("[DEBUG] MSS not available")
            if template_name not in self.templates: print(f"[DEBUG] Template '{template_name}' not loaded")
            return False

        orig_template = self.templates[template_name]
        found_positions = [] if return_positions else None
        
        # Check region vs template sizes for 1.0x
        # If region is smaller than even smallest scale, fail
        t_w, t_h = orig_template.size
        # Allow regions that match template size (even within 1px margin)
        if region[2] < t_w or region[3] < t_h:
             # Just warn, don't fail immediately, but matching will likely fail or crash if we don't handle bounds
             # Actually, the logic below (range(sh-th)) will just not loop if region < template
             pass

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
                
                # Performance: Only check 1.0 scale
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
                    # We want a very solid anchor to skip empty checking
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
                    # Anchor usage depends on high alpha (solid)
                    ca = c_pix[3] if len(c_pix) > 3 else 255
                    use_anchor = (ca > 200)

                    # Scan Screen for this Scale
                    # Optimization: Step size 2 for better precision
                    for y in range(0, sh - th, 2):
                        for x in range(0, sw - tw, 2):
                            if use_anchor:
                                sp = screen_pixels[x+cx, y+cy]
                                if abs(sp[0]-cr) + abs(sp[1]-cg) + abs(sp[2]-cb) > (threshold * 3):
                                    continue
                                
                            total_diff = 0
                            checked_pixels = 0
                            
                            # Check grid
                            abort = False
                            
                            for py in range(0, th, 2):
                                for px in range(0, tw, 2):
                                    t_pix = template_pixels[px, py]
                                    
                                    # CHECK 1: Alpha (Transparency)
                                    # Skip semi-transparent pixels
                                    if t_pix[3] < 200: continue

                                    # CHECK 2: Brightness (Ignore Dark Backgrounds)
                                    # If template pixel is very dark (sum RGB < 100), skip it.
                                    # This prevents matching the black 'empty' space of the icon against dark space backgrounds.
                                    if (t_pix[0] + t_pix[1] + t_pix[2]) < 100: continue
                                    
                                    s_pix = screen_pixels[x+px, y+py]
                                    pixel_diff = abs(s_pix[0]-t_pix[0]) + abs(s_pix[1]-t_pix[1]) + abs(s_pix[2]-t_pix[2])
                                    total_diff += pixel_diff
                                    checked_pixels += 1
                                    
                                    # Abort if bad match
                                    if checked_pixels > 5 and (total_diff / checked_pixels) > (threshold * 3):
                                        abort = True
                                        break
                                if abort: break
                            
                            # We need enough checked pixels to be confident.
                            if not abort and checked_pixels > 10:
                                avg_diff = total_diff / checked_pixels
                                if avg_diff < best_diff:
                                    best_diff = avg_diff

                                limit = threshold * 3
                                if avg_diff < limit or avg_diff < 200:
                                    print(f"[DEBUG] Potential '{template_name}' at ({x},{y}) - Diff: {avg_diff:.2f} (Pixels: {checked_pixels}) Limit: {limit}")

                                if avg_diff < limit:
                                    # Match Found!
                                    # print(f"[DEBUG] Found '{template_name}' at ({x},{y}) with diff {avg_diff:.2f}")
                                    if return_positions:
                                        found_positions.append((monitor["left"] + x, monitor["top"] + y))
                                        if len(found_positions) >= max_results:
                                            return found_positions
                                    else:
                                        return True
                
                # If we get here, no match found or not enough matches collected
                # print(f"[DEBUG] Scan '{template_name}' failed. Best Diff: {best_diff:.2f}")
                return found_positions if return_positions else False
            except Exception as e:
                self.last_error = f"Template Error: {e}"
                print(f"[DEBUG] Exception in find_template: {e}")
                return [] if return_positions else False

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
