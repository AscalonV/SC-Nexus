import threading
import time
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any

try:
    import mss
    HAS_MSS = True
except ImportError:
    HAS_MSS = False

try:
    import cv2
    import numpy as np
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

from PIL import Image

class ScreenScanner:
    def __init__(self):
        self.last_error = None
        if not HAS_MSS:
             self.last_error = "MSS Missing"
        
        if HAS_CV2:
            print("[DEBUG] Scanner initialized with OpenCV support.")
        else:
            print("[DEBUG] Scanner initialized in Legacy Mode (OpenCV not found).")
            print("[WARN] Install opencv-python and numpy for better detection performance.")
        
        self.lock = threading.Lock()
        
        # Cache templates: Name -> { 'pil': Image, 'cv2': (bgr, mask) }
        self.templates = {}

    def load_template(self, name: str, path: Path):
        # print(f"[DEBUG] Loading template '{name}' from {path}")
        if not path.exists():
            print(f"[DEBUG] Template file not found: {path}")
            return
        try:
            # 1. Load Legacy (PIL)
            img_pil = Image.open(path).convert("RGBA")
            
            # 2. Load CV2
            cv_data = None
            if HAS_CV2:
                # IMREAD_UNCHANGED = -1
                img_cv = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
                if img_cv is not None:
                    if img_cv.shape[2] == 4:
                        bgr = img_cv[:, :, :3]
                        alpha = img_cv[:, :, 3]
                        cv_data = (bgr, alpha)
                    else:
                        cv_data = (img_cv, None)
                    # print(f"[DEBUG] Loaded '{name}' (CV2) size={img_cv.shape}")
            
            self.templates[name] = {
                "pil": img_pil,
                "cv2": cv_data
            }
            # print(f"[DEBUG] Loaded '{name}' (PIL) size={img_pil.size}")
        except Exception as e:
            print(f"[DEBUG] Failed to load template '{name}': {e}")
            pass

    def find_template(
        self,
        region: Tuple[int, int, int, int],
        template_name: str,
        threshold=0.8, # Interpreted as Confidence (CV2) or Diff-Derived (Legacy)
        *,
        return_positions: bool = False,
        max_results: int = 1,
    ):
        """
        Template Matching (OpenCV preferred, PIL fallback).
        """
        if not HAS_MSS or template_name not in self.templates:
            return False

        if HAS_CV2 and self.templates[template_name]["cv2"] is not None:
             # OpenCV Path
             # Threshold handling: If > 1.0 (Old Legacy param passed), convert it.
             # Old 45 (approx 18%) -> New 0.8?
             # Let's assume input is updated to 0.8-0.95 range.
             # If input > 1, force a default safe confidence.
             eff_thresh = threshold
             if eff_thresh > 1.0:
                 eff_thresh = 0.8
             
             return self._find_template_cv2(region, template_name, eff_thresh, return_positions, max_results)
        else:
             # Legacy Path
             # Convert Confidence -> Diff if needed
             eff_thresh = threshold
             if eff_thresh < 1.0:
                 # 0.8 confidence -> 0.2 diff -> approx 50 diff score?
                 # This is rough estimate
                 eff_thresh = (1.0 - threshold) * 255
             
             return self._find_template_legacy(region, template_name, eff_thresh, return_positions, max_results)

    def _find_template_cv2(self, region, template_name, threshold, return_positions, max_results):
        tpl_bgr, tpl_mask = self.templates[template_name]["cv2"]
        h, w = tpl_bgr.shape[:2]
        
        monitor = {
            "top": int(region[1]),
            "left": int(region[0]),
            "width": int(region[2]),
            "height": int(region[3]),
        }
        
        if monitor["width"] < w or monitor["height"] < h:
            return [] if return_positions else False

        with self.lock:
            try:
                with mss.mss() as sct:
                    sct_img = sct.grab(monitor)
                    # MSS gives BGRA
                    screen_arr = np.array(sct_img)
                    # Drop Alpha for matching, convert to BGR
                    screen_bgr = screen_arr[:, :, :3] # BGRA to BGR simply by slicing? Yes.
                    # Or cvtColor? Slicing is faster if buffer is consistent.
                    # Warning: MSS BGRA might be BGRX. Slicing is safe.

                    # Match
                    if tpl_mask is not None:
                        res = cv2.matchTemplate(screen_bgr, tpl_bgr, cv2.TM_CCORR_NORMED, mask=tpl_mask)
                    else:
                        res = cv2.matchTemplate(screen_bgr, tpl_bgr, cv2.TM_CCOEFF_NORMED)
                    
                    # Filter
                    locs = np.where(res >= threshold)
                    # locs = (y_indices, x_indices)
                    
                    found = []
                    # iterate results
                    for pt in zip(*locs[::-1]): # pt = (x, y)
                        val = res[pt[1], pt[0]]
                        found.append((val, pt[0], pt[1]))
                    
                    # Sort desc
                    found.sort(key=lambda x: x[0], reverse=True)
                    
                    final_matches = []
                    for val, x, y in found:
                        # Dedup
                        is_new = True
                        for _, ex, ey in final_matches:
                            if abs(x - ex) < w/2 and abs(y - ey) < h/2: 
                                is_new = False
                                break
                        if is_new:
                            final_matches.append((val, x, y))
                            if len(final_matches) >= max_results:
                                break
                    
                    if return_positions:
                        return [(monitor["left"]+x, monitor["top"]+y, val) for val, x, y in final_matches]
                    else:
                        return len(final_matches) > 0

            except Exception as e:
                print(f"[DEBUG] CV2 Error: {e}")
                return [] if return_positions else False

    def _find_template_legacy(self, region, template_name, threshold, return_positions, max_results):
        orig_template = self.templates[template_name]["pil"]
        found_positions = [] if return_positions else None
        
        t_w, t_h = orig_template.size
        # Allow regions that match template size (even within 1px margin)
        if region[2] < t_w or region[3] < t_h:
             pass

        monitor = {
            "top": int(region[1]),
            "left": int(region[0]),
            "width": int(region[2]),
            "height": int(region[3]),
        }

        with self.lock:
            try:
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
                    use_anchor = (ca > 200)

                    for y in range(0, sh - th, 1 if threshold < 20 else 2): # Slower scan for low threshold
                        if y % 20 == 0:
                            time.sleep(0.001)

                        for x in range(0, sw - tw, 1 if threshold < 20 else 2):
                            if use_anchor:
                                sp = screen_pixels[x+cx, y+cy]
                                if abs(sp[0]-cr) + abs(sp[1]-cg) + abs(sp[2]-cb) > (threshold * 5):
                                    continue
                                
                            total_diff = 0
                            checked_pixels = 0
                            abort = False
                            
                            step = 1 if threshold < 20 else 1 # Always detail
                            for py in range(0, th, step):
                                for px in range(0, tw, step):
                                    t_pix = template_pixels[px, py]
                                    if t_pix[3] < 200: continue
                                    s_pix = screen_pixels[x+px, y+py]
                                    pixel_diff = abs(s_pix[0]-t_pix[0]) + abs(s_pix[1]-t_pix[1]) + abs(s_pix[2]-t_pix[2])
                                    total_diff += pixel_diff
                                    checked_pixels += 1
                                    if checked_pixels > 5 and (total_diff / checked_pixels) > (threshold * 3):
                                        abort = True
                                        break
                                if abort: break
                            
                            if not abort and checked_pixels > 10:
                                avg_diff = total_diff / checked_pixels
                                if avg_diff < best_diff:
                                    best_diff = avg_diff

                                limit = threshold * 3
                                if avg_diff < limit:
                                    if return_positions:
                                        found_positions.append((monitor["left"] + x, monitor["top"] + y, avg_diff))
                                        if len(found_positions) >= max_results:
                                            return found_positions
                                    else:
                                        return True
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
                return sct_img.pixel(0, 0)
            except Exception as e:
                self.last_error = f"Pixel Error: {e}"
                print(f"[DEBUG] Pixel Error: {e}")
                return (0, 0, 0)
