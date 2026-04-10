"""
ScreenScanner — template matching and pixel reading for Combat Assistant.

Prefers OpenCV (cv2 + mss) for speed; falls back to PIL if cv2 is absent.
All public methods are thread-safe.
"""

from __future__ import annotations

import math
import time
import threading
from pathlib import Path
from typing import Optional

# ---- Optional dependencies ----
try:
    import cv2
    import numpy as np
    import mss
    _HAVE_CV2 = True
except ImportError:
    _HAVE_CV2 = False

try:
    from PIL import Image, ImageGrab
    _HAVE_PIL = True
except ImportError:
    _HAVE_PIL = False

# Region type: (x, y, width, height) in physical screen pixels
Region  = tuple[int, int, int, int]
# Match result: (x_centre, y_centre, confidence)
Match   = tuple[int, int, float]


class ScreenScanner:
    """
    Wraps template matching and single-pixel colour reading.

    Parameters
    ----------
    threshold : float
        Minimum confidence (0–1) for a match to be reported.
        Defaults to 0.85.
    """

    def __init__(self, threshold: float = 0.85) -> None:
        self._threshold = threshold
        self._lock      = threading.Lock()
        self._templates: dict[str, object] = {}          # name → loaded template data
        self._template_ref_colors: dict[str, tuple] = {} # name → centre BGR
        self.last_error: str = ""

        if _HAVE_CV2:
            self._sct = mss.mss()

    # ------------------------------------------------------------------
    # Screen-mode detection (map/respawn vs ingame)
    # ------------------------------------------------------------------

    def capture_region_image(self, region: Region) -> Optional["np.ndarray"]:
        """Capture a screen region and return it as a BGR numpy array."""
        if not _HAVE_CV2:
            return None
        rx, ry, rw, rh = region
        monitor = {"left": rx, "top": ry, "width": rw, "height": rh}
        try:
            with mss.mss() as sct:
                shot = sct.grab(monitor)
            return np.array(shot)[:, :, :3]  # BGR
        except Exception as exc:
            self.last_error = str(exc)
            return None

    @staticmethod
    def compare_images(img_a: "np.ndarray", img_b: "np.ndarray") -> float:
        """Return normalised similarity (0-1) between two BGR images.

        Uses TM_CCOEFF_NORMED on identically-sized images.  If sizes
        differ the smaller is resized to match the larger.
        Returns 0.0 on any error.
        """
        if img_a is None or img_b is None:
            return 0.0
        try:
            if img_a.shape != img_b.shape:
                img_b = cv2.resize(img_b, (img_a.shape[1], img_a.shape[0]))
            result = cv2.matchTemplate(img_a, img_b, cv2.TM_CCOEFF_NORMED)
            return float(result[0, 0])
        except Exception:
            return 0.0

    # ------------------------------------------------------------------
    # Template management
    # ------------------------------------------------------------------

    def load_template(self, name: str, path: str | Path) -> bool:
        """Load and cache a template image from *path*."""
        with self._lock:
            try:
                p = Path(path)
                if not p.exists():
                    self.last_error = f"Template not found: {path}"
                    return False

                if _HAVE_CV2:
                    img = cv2.imread(str(p), cv2.IMREAD_UNCHANGED)
                    if img is None:
                        self.last_error = f"cv2 could not read: {path}"
                        return False
                    self._templates[name] = img
                    # Precompute alpha-masked reference colour for icon sanity checks.
                    if img.shape[2] == 4:
                        opaque_mask = img[:, :, 3] > 128
                        opaque_pixels = img[:, :, :3][opaque_mask]
                    else:
                        opaque_pixels = img[:, :, :3].reshape(-1, 3)
                    if opaque_pixels.size:
                        mean = opaque_pixels.mean(axis=0)
                        self._template_ref_colors[name] = (
                            float(mean[0]), float(mean[1]), float(mean[2])
                        )
                elif _HAVE_PIL:
                    self._templates[name] = Image.open(str(p)).convert("RGBA")
                else:
                    self.last_error = "Neither cv2 nor PIL available"
                    return False

                return True
            except Exception as exc:
                self.last_error = str(exc)
                return False

    # ------------------------------------------------------------------
    # Template search
    # ------------------------------------------------------------------

    def find_template(
        self,
        template_name: str,
        region: Region,
        *,
        threshold: float | None = None,
        match_mode: str = "default",
        multi: bool = False,
    ) -> list[Match]:
        """
        Search *region* for the named template.

        Returns
        -------
        list of (x_centre, y_centre, confidence) in physical screen coords.
        Empty list when nothing found.
        """
        with self._lock:
            tmpl = self._templates.get(template_name)
            if tmpl is None:
                self.last_error = f"Template not loaded: {template_name}"
                return []

            eff_threshold = self._threshold if threshold is None else threshold

            if _HAVE_CV2:
                return self._find_cv2(
                    tmpl,
                    region,
                    threshold=eff_threshold,
                    match_mode=match_mode,
                    multi=multi,
                )
            elif _HAVE_PIL:
                return self._find_pil(
                    tmpl,
                    region,
                    threshold=eff_threshold,
                    match_mode=match_mode,
                    multi=multi,
                )
            return []

    # ------------------------------------------------------------------
    # Pixel colour reading
    # ------------------------------------------------------------------

    def get_pixel_color(self, x: int, y: int) -> tuple[int, int, int] | None:
        """
        Return (R, G, B) of the physical pixel at screen coordinates (x, y).
        Returns None on failure.
        """
        with self._lock:
            try:
                if _HAVE_CV2:
                    with mss.mss() as sct:
                        shot = sct.grab({"left": x, "top": y, "width": 1, "height": 1})
                    px = shot.pixel(0, 0)   # (R, G, B, A) or (B, G, R)
                    # mss returns BGRA
                    return (px[2], px[1], px[0])
                elif _HAVE_PIL:
                    img = ImageGrab.grab(bbox=(x, y, x + 1, y + 1))
                    return img.getpixel((0, 0))[:3]
            except Exception as exc:
                self.last_error = str(exc)
            return None

    # ------------------------------------------------------------------
    # OpenCV backend
    # ------------------------------------------------------------------

    def _find_cv2(
        self,
        tmpl: "np.ndarray",
        region: Region,
        *,
        threshold: float,
        match_mode: str,
        multi: bool,
    ) -> list[Match]:
        rx, ry, rw, rh = region
        monitor = {"left": rx, "top": ry, "width": rw, "height": rh}

        try:
            with mss.mss() as sct:
                shot = sct.grab(monitor)
            screen = np.array(shot)   # BGRA
        except Exception as exc:
            self.last_error = str(exc)
            return []

        better_is_lower = match_mode == "sqdiff"

        # Handle template with or without alpha channel
        if tmpl.shape[2] == 4:
            mask = tmpl[:, :, 3]
            tmpl_bgr = tmpl[:, :, :3]
            method = cv2.TM_SQDIFF_NORMED if better_is_lower else cv2.TM_CCORR_NORMED
            result = cv2.matchTemplate(screen[:, :, :3], tmpl_bgr, method, mask=mask)
        else:
            method = cv2.TM_SQDIFF_NORMED if better_is_lower else cv2.TM_CCOEFF_NORMED
            result = cv2.matchTemplate(screen[:, :, :3], tmpl, method)

        th, tw = tmpl.shape[:2]
        matches: list[Match] = []

        if multi:
            locs = np.where(result <= threshold) if better_is_lower else np.where(result >= threshold)
            candidates = [
                (float(result[y, x]), int(x), int(y))
                for y, x in zip(*locs)
            ]
            candidates.sort(reverse=not better_is_lower)

            accepted: list[tuple[int, int]] = []
            for raw_score, x, y in candidates:
                cx = x + tw // 2
                cy = y + th // 2
                if any(abs(cx - prev_x) < tw // 2 and abs(cy - prev_y) < th // 2 for prev_x, prev_y in accepted):
                    continue
                accepted.append((cx, cy))
                conf = 1.0 - raw_score if better_is_lower else raw_score
                matches.append((rx + cx, ry + cy, conf))
        else:
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            if better_is_lower:
                if min_val <= threshold:
                    cx = min_loc[0] + tw // 2
                    cy = min_loc[1] + th // 2
                    matches.append((rx + cx, ry + cy, 1.0 - float(min_val)))
            else:
                if max_val >= threshold:
                    cx = max_loc[0] + tw // 2
                    cy = max_loc[1] + th // 2
                    matches.append((rx + cx, ry + cy, float(max_val)))

        return matches

    # ------------------------------------------------------------------
    # Bomb carrier detection (single-capture, dual-match + name hash)
    # ------------------------------------------------------------------

    # Name-crop defaults (pixels, relative to icon centre).
    _NAME_CROP_GAP   = 4     # px right of the icon edge before name starts
    _NAME_CROP_WIDTH = 120   # px to capture for the username text
    _NAME_CROP_HEIGHT = 20   # px height of the name crop

    @staticmethod
    def _compute_name_hash(
        gray: "np.ndarray",
        x: int,
        y: int,
        crop_w: int,
        crop_h: int,
    ) -> bytes:
        """
        Extract the text region at (x, y) from a grayscale image,
        binarize it to remove the varying background, and return a
        128-bit perceptual hash (16 bytes).

        The binarization uses adaptive thresholding so that bright text
        (white / team-coloured names) is isolated regardless of what the
        transparent game background looks like behind it.
        """
        h, w = gray.shape[:2]
        x0 = max(0, x)
        y0 = max(0, y - crop_h // 2)
        x1 = min(w, x + crop_w)
        y1 = min(h, y0 + crop_h)
        crop = gray[y0:y1, x0:x1]

        if crop.size == 0:
            return b"\x00" * 16

        # Binarize: bright text → white, everything else → black.
        # Use a fixed threshold (not OTSU) so the result is independent
        # of whatever the transparent game background looks like.
        _, binary = cv2.threshold(crop, 150, 255, cv2.THRESH_BINARY)

        # Resize to a fixed 16×8 grid for the hash.
        resized = cv2.resize(binary, (16, 8), interpolation=cv2.INTER_AREA)
        mean_val = resized.mean()
        bits = (resized > mean_val).flatten()

        # Pack 128 bits into 16 bytes.
        hash_bytes = bytearray(16)
        for i, bit in enumerate(bits):
            if bit:
                hash_bytes[i // 8] |= 1 << (i % 8)
        return bytes(hash_bytes)

    @staticmethod
    def hamming_distance(a: bytes, b: bytes) -> int:
        """Return the number of differing bits between two equal-length byte strings."""
        return sum(bin(x ^ y).count("1") for x, y in zip(a, b))

    def find_bomb_carriers(
        self,
        template_name: str,
        region: Region,
        *,
        threshold: float = 0.80,
        sqdiff_max: float = 0.40,
        color_max_dist: float = 40.0,
        debug_dir: Path | None = None,
        debug_tag: str = "",
    ) -> list[tuple[int, int, float, bytes, tuple[float, float, float]]]:
        """
        Find bomb icons in *region* and extract a perceptual hash of the
        carrier username next to each icon.

        Uses a single screen capture and dual matching (TM_CCORR_NORMED ≥
        *threshold* AND TM_SQDIFF_NORMED ≤ *sqdiff_max*) to reduce false
        positives.  Each detection is additionally validated by comparing
        the icon centre's mean BGR colour against the template's own centre
        colour; detections that deviate by more than *color_max_dist*
        (euclidean BGR) are discarded before entering the candidate pipeline.

        Parameters
        ----------
        debug_dir : Path or None
            If set, save annotated debug images (raw capture, heatmap,
            detections, name crops) into this directory.
        debug_tag : str
            Prefix for debug image filenames (e.g. "ally_ingame").

        Returns
        -------
        list of (screen_x, screen_y, confidence, name_hash, icon_color)
            Sorted top-to-bottom by y.  *icon_color* is the mean BGR
            sampled from a small patch at the icon centre.  Empty list
            when nothing found or when cv2 is unavailable.
        """
        if not _HAVE_CV2:
            return []

        with self._lock:
            tmpl = self._templates.get(template_name)
            if tmpl is None:
                self.last_error = f"Template not loaded: {template_name}"
                return []

            rx, ry, rw, rh = region

            # Expand the capture region horizontally so name-hash crops
            # can reach into the player name text that may sit outside
            # the narrow calibrated bomb-icon region.
            pad = self._NAME_CROP_WIDTH + self._NAME_CROP_GAP
            exp_left = min(pad, rx)                # don't go past x=0
            exp_right = pad                        # right side is unbounded in practice
            exp_rx = rx - exp_left
            exp_rw = rw + exp_left + exp_right
            monitor = {"left": exp_rx, "top": ry, "width": exp_rw, "height": rh}

            try:
                with mss.mss() as sct:
                    shot = sct.grab(monitor)
                screen = np.array(shot)  # BGRA
            except Exception as exc:
                self.last_error = str(exc)
                return []

            screen_bgr = screen[:, :, :3]
            th, tw = tmpl.shape[:2]

            # Template matching is restricted to the original calibrated
            # region.  Slice out the sub-image that corresponds to the
            # original (rx, ry, rw, rh) within the expanded capture.
            match_bgr = screen_bgr[:, exp_left:exp_left + rw]

            # --- Prepare mask if the template has an alpha channel ---
            if tmpl.shape[2] == 4:
                mask = tmpl[:, :, 3]
                tmpl_bgr = tmpl[:, :, :3]
            else:
                mask = None
                tmpl_bgr = tmpl

            # --- Pass 1: TM_CCORR_NORMED (higher is better) ---
            if mask is not None:
                score_result = cv2.matchTemplate(
                    match_bgr, tmpl_bgr, cv2.TM_CCORR_NORMED, mask=mask,
                )
            else:
                score_result = cv2.matchTemplate(
                    match_bgr, tmpl_bgr, cv2.TM_CCOEFF_NORMED,
                )

            # --- Pass 2: TM_SQDIFF_NORMED (lower is better) ---
            if mask is not None:
                shape_result = cv2.matchTemplate(
                    match_bgr, tmpl_bgr, cv2.TM_SQDIFF_NORMED, mask=mask,
                )
            else:
                shape_result = cv2.matchTemplate(
                    match_bgr, tmpl_bgr, cv2.TM_SQDIFF_NORMED,
                )

            # Collect score-pass candidates.
            score_locs = np.where(score_result >= threshold)
            score_set: list[tuple[int, int, float]] = []
            for sy, sx in zip(*score_locs):
                cx = int(sx) + tw // 2
                cy = int(sy) + th // 2
                conf = float(score_result[sy, sx])
                score_set.append((cx, cy, conf))

            if not score_set:
                # Save raw capture on miss so we can diagnose detection gaps
                if debug_dir is not None and _HAVE_CV2:
                    try:
                        debug_dir.mkdir(parents=True, exist_ok=True)
                        ts = time.strftime("%H%M%S")
                        prefix = f"{debug_tag}_{ts}" if debug_tag else ts
                        cv2.imwrite(str(debug_dir / f"{prefix}_miss_raw.png"), match_bgr)
                    except Exception:
                        pass
                return []

            # Collect shape-pass candidates.
            shape_locs = np.where(shape_result <= sqdiff_max)
            shape_set: set[tuple[int, int]] = set()
            for sy, sx in zip(*shape_locs):
                shape_set.add((int(sx) + tw // 2, int(sy) + th // 2))

            # Intersect: keep score hits that have a shape hit nearby.
            tol = max(tw, th)
            validated: list[tuple[int, int, float]] = []
            for cx, cy, conf in score_set:
                if any(
                    abs(cx - ox) <= tol and abs(cy - oy) <= tol
                    for ox, oy in shape_set
                ):
                    validated.append((cx, cy, conf))

            if not validated:
                if debug_dir is not None and _HAVE_CV2:
                    try:
                        debug_dir.mkdir(parents=True, exist_ok=True)
                        ts = time.strftime("%H%M%S")
                        prefix = f"{debug_tag}_{ts}" if debug_tag else ts
                        cv2.imwrite(str(debug_dir / f"{prefix}_miss_raw.png"), match_bgr)
                    except Exception:
                        pass
                return []

            # Deduplicate close matches (keep strongest).
            validated.sort(key=lambda m: m[2], reverse=True)
            accepted: list[tuple[int, int, float]] = []
            for cx, cy, conf in validated:
                if any(
                    abs(cx - px) < tw and abs(cy - py) < th
                    for px, py, _ in accepted
                ):
                    continue
                accepted.append((cx, cy, conf))

            # --- Column filter: bomb icons form a vertical column ---
            if len(accepted) > 1:
                anchor_x = accepted[0][0]  # strongest match sets x-anchor
                col_eps = rw * 0.12 if rw > 0 else 40
                accepted = [
                    m for m in accepted
                    if abs(m[0] - anchor_x) <= col_eps
                ]

            # Sort top-to-bottom.
            accepted.sort(key=lambda m: m[1])

            # --- Extract a grayscale copy of the EXPANDED capture for name hashes ---
            gray = cv2.cvtColor(screen, cv2.COLOR_BGRA2GRAY)
            name_x_offset = tw // 2 + self._NAME_CROP_GAP

            # --- Precompute alpha mask and dims for full-icon color sampling ---
            # Icon validation uses match_bgr (original region coordinates).
            mh, mw = match_bgr.shape[:2]
            tmpl_ref = self._template_ref_colors.get(template_name)
            tmpl_mask_bool = mask > 128 if mask is not None else None

            results: list[tuple[int, int, float, bytes, tuple[float, float, float]]] = []
            for cx, cy, conf in accepted:
                # cx, cy are in original-region coordinates (match_bgr).
                # Crop the full template-sized region for icon color validation.
                ix0 = cx - tw // 2
                iy0 = cy - th // 2
                if ix0 < 0 or iy0 < 0 or ix0 + tw > mw or iy0 + th > mh:
                    continue
                icon_crop = match_bgr[iy0:iy0 + th, ix0:ix0 + tw]
                # Compute mean BGR using only the template's opaque pixels.
                if tmpl_mask_bool is not None:
                    opaque = icon_crop[tmpl_mask_bool]
                    if not opaque.size:
                        continue
                    icon_color = tuple(float(v) for v in opaque.mean(axis=0))
                else:
                    icon_color = tuple(float(v) for v in icon_crop.mean(axis=(0, 1)))
                # Reject if icon colour deviates too far from the template reference.
                if tmpl_ref is not None:
                    cdist = math.sqrt(sum((a - b) ** 2 for a, b in zip(tmpl_ref, icon_color)))
                    if cdist > color_max_dist:
                        continue

                # Translate cx to expanded-capture coordinates for name hashing.
                ecx = cx + exp_left

                # Try RIGHT crop (name to the right of icon) and LEFT crop
                # (name to the left), pick whichever has more non-zero bits.
                hash_right = self._compute_name_hash(
                    gray,
                    ecx + name_x_offset,
                    cy,
                    self._NAME_CROP_WIDTH,
                    self._NAME_CROP_HEIGHT,
                )
                hash_left = self._compute_name_hash(
                    gray,
                    ecx - name_x_offset - self._NAME_CROP_WIDTH,
                    cy,
                    self._NAME_CROP_WIDTH,
                    self._NAME_CROP_HEIGHT,
                )
                bits_r = sum(bin(b).count("1") for b in hash_right)
                bits_l = sum(bin(b).count("1") for b in hash_left)
                name_hash = hash_right if bits_r >= bits_l else hash_left

                results.append((rx + cx, ry + cy, conf, name_hash, icon_color))

            # --- Optional debug image dump ---
            if debug_dir is not None and _HAVE_CV2:
                try:
                    debug_dir.mkdir(parents=True, exist_ok=True)
                    ts = time.strftime("%H%M%S")
                    prefix = f"{debug_tag}_{ts}" if debug_tag else ts

                    # 1. Raw expanded capture (shows name area too)
                    cv2.imwrite(str(debug_dir / f"{prefix}_raw.png"), screen_bgr)

                    # 2. Score heatmap (CCORR result normalised to 0-255)
                    heatmap = cv2.normalize(score_result, None, 0, 255, cv2.NORM_MINMAX)
                    heatmap = heatmap.astype(np.uint8)
                    heatmap_color = cv2.applyColorMap(heatmap, cv2.COLORMAP_JET)
                    cv2.imwrite(str(debug_dir / f"{prefix}_heatmap.png"), heatmap_color)

                    # 3. Annotated detections on the expanded capture
                    annotated = screen_bgr.copy()
                    for cx, cy, conf in accepted:
                        ecx = cx + exp_left
                        # Draw detection box (green)
                        x0 = ecx - tw // 2
                        y0 = cy - th // 2
                        cv2.rectangle(annotated, (x0, y0), (x0 + tw, y0 + th), (0, 255, 0), 1)
                        cv2.putText(annotated, f"{conf:.3f}", (x0, y0 - 3),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 255, 0), 1)
                        # Draw RIGHT name crop region (cyan)
                        nx0 = ecx + name_x_offset
                        ny0 = cy - self._NAME_CROP_HEIGHT // 2
                        cv2.rectangle(annotated, (nx0, ny0),
                                      (nx0 + self._NAME_CROP_WIDTH, ny0 + self._NAME_CROP_HEIGHT),
                                      (255, 255, 0), 1)
                        # Draw LEFT name crop region (magenta)
                        lnx0 = ecx - name_x_offset - self._NAME_CROP_WIDTH
                        cv2.rectangle(annotated, (max(0, lnx0), ny0),
                                      (ecx - name_x_offset, ny0 + self._NAME_CROP_HEIGHT),
                                      (255, 0, 255), 1)
                    cv2.imwrite(str(debug_dir / f"{prefix}_detections.png"), annotated)

                    # 4. Name crops + binarised hash grids (both directions)
                    for i, (cx, cy, conf) in enumerate(accepted):
                        ecx = cx + exp_left
                        for side_label, nx_start in [
                            ("R", ecx + name_x_offset),
                            ("L", ecx - name_x_offset - self._NAME_CROP_WIDTH),
                        ]:
                            nx0 = max(0, nx_start)
                            ny0 = max(0, cy - self._NAME_CROP_HEIGHT // 2)
                            nx1 = min(gray.shape[1], nx0 + self._NAME_CROP_WIDTH)
                            ny1 = min(gray.shape[0], ny0 + self._NAME_CROP_HEIGHT)
                            name_crop = gray[ny0:ny1, nx0:nx1]
                            if name_crop.size:
                                cv2.imwrite(str(debug_dir / f"{prefix}_name{i}{side_label}_gray.png"), name_crop)
                                _, binary = cv2.threshold(name_crop, 150, 255, cv2.THRESH_BINARY)
                                cv2.imwrite(str(debug_dir / f"{prefix}_name{i}{side_label}_bin.png"), binary)
                                resized = cv2.resize(binary, (16, 8), interpolation=cv2.INTER_AREA)
                                grid_vis = cv2.resize(resized, (160, 80), interpolation=cv2.INTER_NEAREST)
                                cv2.imwrite(str(debug_dir / f"{prefix}_name{i}{side_label}_hash.png"), grid_vis)
                except Exception:
                    pass  # debug images are best-effort

            return results

    # ------------------------------------------------------------------
    # Bomb icon counting (simplified — no name hashing)
    # ------------------------------------------------------------------

    def count_bomb_icons(
        self,
        template_name: str,
        region: Region,
        *,
        threshold: float = 0.80,
        sqdiff_max: float = 0.40,
        color_max_dist: float = 40.0,
        debug_dir: Path | None = None,
        debug_tag: str = "",
    ) -> tuple[int, list[tuple[int, int, float]], tuple[float, float]]:
        """
        Count bomb icons in *region* using dual-pass template matching.

        Like ``find_bomb_carriers`` but without any name-hash extraction
        or expanded capture.  Returns a simple count plus diagnostic info.

        Returns
        -------
        (count, positions, best_scores)
            *count*: number of validated bomb icons found.
            *positions*: list of ``(screen_x, screen_y, confidence)``.
            *best_scores*: ``(best_ccorr, best_sqdiff)`` — the best raw
            match scores across the whole region, even when below
            threshold. Useful for diagnosing near-misses.  ``(-1, -1)``
            if cv2 is unavailable or capture fails.
        """
        if not _HAVE_CV2:
            return (0, [], (-1.0, -1.0))

        with self._lock:
            tmpl = self._templates.get(template_name)
            if tmpl is None:
                self.last_error = f"Template not loaded: {template_name}"
                return (0, [], (-1.0, -1.0))

            rx, ry, rw, rh = region
            monitor = {"left": rx, "top": ry, "width": rw, "height": rh}

            try:
                with mss.mss() as sct:
                    shot = sct.grab(monitor)
                screen = np.array(shot)  # BGRA
            except Exception as exc:
                self.last_error = str(exc)
                return (0, [], (-1.0, -1.0))

            screen_bgr = screen[:, :, :3]
            th, tw = tmpl.shape[:2]

            # --- Prepare mask if the template has an alpha channel ---
            if tmpl.shape[2] == 4:
                mask = tmpl[:, :, 3]
                tmpl_bgr = tmpl[:, :, :3]
            else:
                mask = None
                tmpl_bgr = tmpl

            # --- Pass 1: TM_CCORR_NORMED (higher is better) ---
            if mask is not None:
                score_result = cv2.matchTemplate(
                    screen_bgr, tmpl_bgr, cv2.TM_CCORR_NORMED, mask=mask,
                )
            else:
                score_result = cv2.matchTemplate(
                    screen_bgr, tmpl_bgr, cv2.TM_CCOEFF_NORMED,
                )

            # --- Pass 2: TM_SQDIFF_NORMED (lower is better) ---
            if mask is not None:
                shape_result = cv2.matchTemplate(
                    screen_bgr, tmpl_bgr, cv2.TM_SQDIFF_NORMED, mask=mask,
                )
            else:
                shape_result = cv2.matchTemplate(
                    screen_bgr, tmpl_bgr, cv2.TM_SQDIFF_NORMED,
                )

            # --- Best raw scores (for diagnostics even on miss) ---
            best_ccorr = float(score_result.max()) if score_result.size else -1.0
            best_sqdiff = float(shape_result.min()) if shape_result.size else -1.0

            # Collect score-pass candidates.
            score_locs = np.where(score_result >= threshold)
            score_set: list[tuple[int, int, float]] = []
            for sy, sx in zip(*score_locs):
                cx = int(sx) + tw // 2
                cy = int(sy) + th // 2
                conf = float(score_result[sy, sx])
                score_set.append((cx, cy, conf))

            if not score_set:
                if debug_dir is not None:
                    try:
                        debug_dir.mkdir(parents=True, exist_ok=True)
                        ts = time.strftime("%H%M%S")
                        prefix = f"{debug_tag}_{ts}" if debug_tag else ts
                        cv2.imwrite(str(debug_dir / f"{prefix}_miss_raw.png"), screen_bgr)
                    except Exception:
                        pass
                return (0, [], (best_ccorr, best_sqdiff))

            # Collect shape-pass candidates.
            shape_locs = np.where(shape_result <= sqdiff_max)
            shape_set: set[tuple[int, int]] = set()
            for sy, sx in zip(*shape_locs):
                shape_set.add((int(sx) + tw // 2, int(sy) + th // 2))

            # Intersect: keep score hits that have a shape hit nearby.
            tol = max(tw, th)
            validated: list[tuple[int, int, float]] = []
            for cx, cy, conf in score_set:
                if any(
                    abs(cx - ox) <= tol and abs(cy - oy) <= tol
                    for ox, oy in shape_set
                ):
                    validated.append((cx, cy, conf))

            if not validated:
                if debug_dir is not None:
                    try:
                        debug_dir.mkdir(parents=True, exist_ok=True)
                        ts = time.strftime("%H%M%S")
                        prefix = f"{debug_tag}_{ts}" if debug_tag else ts
                        cv2.imwrite(str(debug_dir / f"{prefix}_miss_raw.png"), screen_bgr)
                    except Exception:
                        pass
                return (0, [], (best_ccorr, best_sqdiff))

            # Deduplicate close matches (keep strongest).
            validated.sort(key=lambda m: m[2], reverse=True)
            accepted: list[tuple[int, int, float]] = []
            for cx, cy, conf in validated:
                if any(
                    abs(cx - px) < tw and abs(cy - py) < th
                    for px, py, _ in accepted
                ):
                    continue
                accepted.append((cx, cy, conf))

            # --- Column filter: bomb icons form a vertical column ---
            if len(accepted) > 1:
                anchor_x = accepted[0][0]
                col_eps = rw * 0.12 if rw > 0 else 40
                accepted = [
                    m for m in accepted
                    if abs(m[0] - anchor_x) <= col_eps
                ]

            # Sort top-to-bottom.
            accepted.sort(key=lambda m: m[1])

            # --- Color validation against template reference ---
            mh, mw = screen_bgr.shape[:2]
            tmpl_ref = self._template_ref_colors.get(template_name)
            tmpl_mask_bool = mask > 128 if mask is not None else None
            ally_cyan_template: "np.ndarray | None" = None
            ally_edge_template: "np.ndarray | None" = None
            enemy_red_template: "np.ndarray | None" = None
            enemy_red_core_template: "np.ndarray | None" = None
            enemy_edge_template: "np.ndarray | None" = None
            ally_hsv_lo = np.array((70, 70, 70), dtype=np.uint8)
            ally_hsv_hi = np.array((115, 255, 255), dtype=np.uint8)
            enemy_red_lo_1 = np.array((0, 70, 70), dtype=np.uint8)
            enemy_red_hi_1 = np.array((15, 255, 255), dtype=np.uint8)
            enemy_red_lo_2 = np.array((165, 70, 70), dtype=np.uint8)
            enemy_red_hi_2 = np.array((180, 255, 255), dtype=np.uint8)

            if template_name == "bomb_ally" and tmpl_mask_bool is not None:
                tmpl_hsv = cv2.cvtColor(tmpl_bgr, cv2.COLOR_BGR2HSV)
                ally_cyan_template = cv2.inRange(tmpl_hsv, ally_hsv_lo, ally_hsv_hi) > 0
                ally_cyan_template &= tmpl_mask_bool
                tmpl_gray = cv2.cvtColor(tmpl_bgr, cv2.COLOR_BGR2GRAY)
                tmpl_gray[~tmpl_mask_bool] = 0
                ally_edge_template = cv2.Canny(tmpl_gray, 40, 120) > 0
            elif template_name == "bomb_enemy" and tmpl_mask_bool is not None:
                tmpl_hsv = cv2.cvtColor(tmpl_bgr, cv2.COLOR_BGR2HSV)
                enemy_red_template = (
                    (cv2.inRange(tmpl_hsv, enemy_red_lo_1, enemy_red_hi_1) > 0)
                    | (cv2.inRange(tmpl_hsv, enemy_red_lo_2, enemy_red_hi_2) > 0)
                )
                enemy_red_template &= tmpl_mask_bool

                core_mask = cv2.erode(
                    (tmpl_mask_bool.astype(np.uint8) * 255),
                    np.ones((3, 3), dtype=np.uint8),
                    iterations=2,
                ) > 0
                enemy_red_core_template = enemy_red_template & core_mask

                tmpl_gray = cv2.cvtColor(tmpl_bgr, cv2.COLOR_BGR2GRAY)
                tmpl_gray[~tmpl_mask_bool] = 0
                enemy_edge_template = cv2.Canny(tmpl_gray, 40, 120) > 0
                enemy_edge_template &= core_mask

            results: list[tuple[int, int, float]] = []
            for cx, cy, conf in accepted:
                ix0 = cx - tw // 2
                iy0 = cy - th // 2
                if ix0 < 0 or iy0 < 0 or ix0 + tw > mw or iy0 + th > mh:
                    continue
                icon_crop = screen_bgr[iy0:iy0 + th, ix0:ix0 + tw]
                if tmpl_mask_bool is not None:
                    opaque = icon_crop[tmpl_mask_bool]
                    if not opaque.size:
                        continue
                    icon_color = tuple(float(v) for v in opaque.mean(axis=0))
                else:
                    icon_color = tuple(float(v) for v in icon_crop.mean(axis=(0, 1)))
                if tmpl_ref is not None:
                    cdist = math.sqrt(sum((a - b) ** 2 for a, b in zip(tmpl_ref, icon_color)))
                    if cdist > color_max_dist:
                        continue

                # Ally icons are unstable under direct color-template matching.
                # Require the matched crop to also reproduce the bomb icon's
                # internal edge pattern; flat hull highlights can hit the color
                # template but do not reproduce the icon structure.
                if (
                    ally_cyan_template is not None
                    and ally_edge_template is not None
                    and tmpl_mask_bool is not None
                ):
                    icon_hsv = cv2.cvtColor(icon_crop, cv2.COLOR_BGR2HSV)
                    icon_cyan = cv2.inRange(icon_hsv, ally_hsv_lo, ally_hsv_hi) > 0
                    cyan_count = int(icon_cyan.sum())
                    if cyan_count == 0:
                        continue

                    overlap = int((icon_cyan & ally_cyan_template).sum())
                    cyan_recall = overlap / max(int(ally_cyan_template.sum()), 1)
                    if cyan_recall < 0.55:
                        continue

                    icon_gray = cv2.cvtColor(icon_crop, cv2.COLOR_BGR2GRAY)
                    icon_edges = cv2.Canny(icon_gray, 40, 120) > 0
                    edge_overlap = int((icon_edges & ally_edge_template).sum())
                    edge_precision = edge_overlap / max(int(icon_edges.sum()), 1)
                    edge_recall = edge_overlap / max(int(ally_edge_template.sum()), 1)

                    if edge_precision < 0.35 or edge_recall < 0.50:
                        continue

                if (
                    enemy_red_template is not None
                    and enemy_red_core_template is not None
                    and enemy_edge_template is not None
                ):
                    icon_hsv = cv2.cvtColor(icon_crop, cv2.COLOR_BGR2HSV)
                    icon_red = (
                        (cv2.inRange(icon_hsv, enemy_red_lo_1, enemy_red_hi_1) > 0)
                        | (cv2.inRange(icon_hsv, enemy_red_lo_2, enemy_red_hi_2) > 0)
                    )
                    red_count = int(icon_red.sum())
                    if red_count == 0:
                        continue

                    red_overlap = int((icon_red & enemy_red_template).sum())
                    red_precision = red_overlap / max(red_count, 1)

                    red_core_overlap = int((icon_red & enemy_red_core_template).sum())
                    red_core_recall = red_core_overlap / max(int(enemy_red_core_template.sum()), 1)

                    icon_gray = cv2.cvtColor(icon_crop, cv2.COLOR_BGR2GRAY)
                    icon_edges = cv2.Canny(icon_gray, 40, 120) > 0
                    edge_overlap = int((icon_edges & enemy_edge_template).sum())
                    edge_recall = edge_overlap / max(int(enemy_edge_template.sum()), 1)

                    if red_precision < 0.50 or red_core_recall < 0.80 or edge_recall < 0.45:
                        continue

                results.append((rx + cx, ry + cy, conf))

            # --- Optional debug image dump ---
            if debug_dir is not None:
                try:
                    debug_dir.mkdir(parents=True, exist_ok=True)
                    ts = time.strftime("%H%M%S")
                    prefix = f"{debug_tag}_{ts}" if debug_tag else ts
                    cv2.imwrite(str(debug_dir / f"{prefix}_raw.png"), screen_bgr)

                    annotated = screen_bgr.copy()
                    for screen_x, screen_y, conf in results:
                        cx = screen_x - rx
                        cy = screen_y - ry
                        x0 = cx - tw // 2
                        y0 = cy - th // 2
                        cv2.rectangle(annotated, (x0, y0), (x0 + tw, y0 + th), (0, 255, 0), 1)
                        cv2.putText(annotated, f"{conf:.3f}", (x0, y0 - 3),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 255, 0), 1)
                    cv2.imwrite(str(debug_dir / f"{prefix}_detections.png"), annotated)
                except Exception:
                    pass

            return (len(results), results, (best_ccorr, best_sqdiff))

    # ------------------------------------------------------------------
    # PIL backend (legacy fallback)
    # ------------------------------------------------------------------

    def _find_pil(
        self,
        tmpl: "Image.Image",
        region: Region,
        *,
        threshold: float,
        match_mode: str,
        multi: bool,
    ) -> list[Match]:
        """Pixel-by-pixel search — much slower than cv2, but dependency-free."""
        rx, ry, rw, rh = region
        try:
            screen = ImageGrab.grab(bbox=(rx, ry, rx + rw, ry + rh)).convert("RGB")
        except Exception as exc:
            self.last_error = str(exc)
            return []

        tmpl_rgb = tmpl.convert("RGB")
        tw, th   = tmpl_rgb.size
        sw, sh   = screen.size

        # Simple anchor-pixel early rejection
        anchor = tmpl_rgb.getpixel((0, 0))
        use_sqdiff = match_mode == "sqdiff"
        threshold_sum = int((threshold if use_sqdiff else (1 - threshold)) * 255 * 3 * tw * th)

        matches: list[Match] = []

        for y in range(sh - th):
            for x in range(sw - tw):
                if screen.getpixel((x, y)) != anchor:
                    continue
                diff = sum(
                    abs(screen.getpixel((x + dx, y + dy))[c] - tmpl_rgb.getpixel((dx, dy))[c])
                    for dy in range(th)
                    for dx in range(tw)
                    for c in range(3)
                )
                if diff <= threshold_sum:
                    conf = 1.0 - diff / max(1, 255 * 3 * tw * th)
                    matches.append((rx + x + tw // 2, ry + y + th // 2, conf))
                    if not multi:
                        return matches

        return matches
