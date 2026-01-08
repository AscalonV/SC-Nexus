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
        self._local = threading.local()
        self.last_error = None
        if not HAS_MSS:
             self.last_error = "MSS Missing"
        
        self.lock = threading.Lock()
        
        # Cache templates: Name -> PIL.Image
        self.templates = {}

    @property
    def sct(self):
        if not HAS_MSS:
            return None
            
        if not hasattr(self._local, "instance"):
            try:
                self._local.instance = mss.mss()
            except Exception as e:
                self.last_error = f"MSS Init Error: {e}"
                return None
        return self._local.instance

    def load_template(self, name: str, path: Path):
        if not path.exists():
            return
        try:
            # Load with PIL, convert to RGBA
            img = Image.open(path).convert("RGBA")
            # Resize logic if needed? Assuming 1:1 match
            self.templates[name] = img
        except Exception:
            pass

    def find_template(self, region: Tuple[int, int, int, int], template_name: str, threshold=50) -> bool:
        """
        Pure Python Template Matching.
        region: (left, top, width, height)
        threshold: Max average pixel difference (0-255). Lower is stricter.
        """
        if not HAS_MSS or template_name not in self.templates:
            return False

        template_img = self.templates[template_name]
        tw, th = template_img.size
        
        # Check region size vs template size
        if region[2] < tw or region[3] < th:
             self.last_error = f"Region too small ({region[2]}x{region[3]}) for {template_name} ({tw}x{th})"
             return False

        # Monitor for mss
        # Use absolute coordinates (virtual screen) by omitting "mon" or setting it to -1 (if needed, but dict implies absolute)
        # Actually, mss grab(rect) uses absolute coords if rect is dict
        monitor = {
            "top": int(region[1]),
            "left": int(region[0]),
            "width": int(region[2]),
            "height": int(region[3]),
        }

        with self.lock:
            try:
                # Capture Screen
                sct_img = self.sct.grab(monitor)
                # Convert to PIL Info
                # mss BGRA -> RGB
                screen_img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                
                # We do a simplified check:
                # Iterate over the screen area
                # For each position, check if template matches
                
                sw, sh = screen_img.size
                
                # Optimization: Access pixel data directly
                screen_pixels = screen_img.load()
                template_pixels = template_img.load()
                
                # Scan
                # Loop through valid top-left positions
                # Limit scan to reasonable area (Roster boxes usually small?)
                # Assuming region passed IS strictly the roster box.
                
                # Optimization: Check center pixel of template first?
                cx, cy = tw // 2, th // 2
                c_pix = template_pixels[cx, cy]
                
                # Alpha check for center
                # Standard PIL pixel access (r, g, b, a)
                if len(c_pix) == 4 and c_pix[3] < 128:
                    # Center is transparent, bad anchor. Use 0,0
                   cx, cy = 0, 0
                   c_pix = template_pixels[0,0]

                # Extract center RGB
                cr, cg, cb = c_pix[0], c_pix[1], c_pix[2]
                
                for y in range(sh - th):
                    for x in range(sw - tw):
                        # Fast Anchor Check
                        sp = screen_pixels[x+cx, y+cy]
                        # Diff
                        if abs(sp[0]-cr) + abs(sp[1]-cg) + abs(sp[2]-cb) > (threshold * 3):
                            continue
                            
                        # Full Match Check
                        # Check specific points or full area?
                        # Let's check 4 corners and center first
                        # If pass, check all opaque pixels?
                        # Sampling 20 pixels is usually enough for UI icons
                        
                        match_score = 0
                        checked_pixels = 0
                        failed = False
                        
                        # Step 2: Check standard grid (every 2nd pixel)
                        for py in range(0, th, 2):
                            if failed: break
                            for px in range(0, tw, 2):
                                t_pix = template_pixels[px, py]
                                # Skip Transparent
                                if t_pix[3] < 50: continue
                                
                                s_pix = screen_pixels[x+px, y+py]
                                
                                diff = abs(s_pix[0]-t_pix[0]) + abs(s_pix[1]-t_pix[1]) + abs(s_pix[2]-t_pix[2])
                                if diff > (threshold * 3): # Per pixel RGB sum threshold
                                    failed = True
                                    break
                                checked_pixels += 1
                        
                        if not failed and checked_pixels > 5:
                            return True
                            
                return False
            except Exception as e:
                self.last_error = f"Template Error: {e}"
                # print(e)
                return False

    def get_pixel_color(self, x: int, y: int) -> Tuple[int, int, int]:
        """Returns (R, G, B)"""
        if not HAS_MSS or not self.sct:
            return (0, 0, 0)
            
        monitor = {
            "top": int(y),
            "left": int(x),
            "width": 1,
            "height": 1,
        }
        with self.lock:
            try:
                sct_img = self.sct.grab(monitor)
                # sct stores as BGRA, access raw
                # pixel is at [0][0]
                # data is accessible via sct_img.pixel(0, 0) -> (r, g, b)
                return sct_img.pixel(0, 0)
            except Exception as e:
                self.last_error = f"Pixel Error: {e}"
                return (0, 0, 0)
