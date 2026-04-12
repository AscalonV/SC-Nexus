"""
Template-based UI element scanner for the Loadout Manager.

Uses OpenCV template matching with multi-scale support to locate game
UI elements regardless of resolution.  Screen capture via ``mss``.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

import numpy as np

try:
    import cv2
    _HAVE_CV2 = True
except ImportError:
    _HAVE_CV2 = False

try:
    import mss
    _HAVE_MSS = True
except ImportError:
    _HAVE_MSS = False


# Pre-bundled template directory
_ASSETS_DIR = Path(__file__).parent.parent / "ui" / "assets"


class MatchResult:
    """Describes a successful template match."""
    __slots__ = ("x", "y", "w", "h", "confidence", "scale")

    def __init__(self, x: int, y: int, w: int, h: int,
                 confidence: float, scale: float) -> None:
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.confidence = confidence
        self.scale = scale

    @property
    def center(self) -> tuple[int, int]:
        return self.x + self.w // 2, self.y + self.h // 2

    def __repr__(self) -> str:
        return (f"MatchResult(x={self.x}, y={self.y}, "
                f"{self.w}x{self.h}, conf={self.confidence:.3f}, "
                f"scale={self.scale:.2f})")


class LoadoutScanner:
    """Screen scanner with multi-scale template matching for game UI."""

    # Scale factors to try during multi-scale matching
    SCALES = (0.75, 0.85, 0.90, 0.95, 1.0, 1.05, 1.10, 1.15, 1.25)

    def __init__(self, threshold: float = 0.80) -> None:
        self._threshold = threshold
        self._templates: dict[str, np.ndarray] = {}
        self._cached_scale: float | None = None

    # ── Template management ───────────────────────────────────────────

    def load_template(self, name: str, path: Path | None = None) -> bool:
        """Load a template image.  Returns True on success."""
        if not _HAVE_CV2:
            return False

        if path is None:
            path = _ASSETS_DIR / f"{name}.png"
        if not path.exists():
            return False

        img = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
        if img is None:
            return False

        self._templates[name] = img
        return True

    def load_all_templates(self) -> int:
        """Load all .png templates from the assets directory."""
        count = 0
        if _ASSETS_DIR.exists():
            for png in _ASSETS_DIR.glob("*.png"):
                if self.load_template(png.stem, png):
                    count += 1
        return count

    # ── Screen capture ────────────────────────────────────────────────

    def capture_screen(self) -> np.ndarray | None:
        """Capture the full primary monitor as a BGR numpy array."""
        if not _HAVE_MSS:
            return None
        with mss.mss() as sct:
            monitor = sct.monitors[1]  # primary monitor
            img = np.array(sct.grab(monitor))
        return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

    def capture_region(self, x: int, y: int, w: int, h: int) -> np.ndarray | None:
        """Capture a specific screen region as BGR."""
        if not _HAVE_MSS:
            return None
        with mss.mss() as sct:
            monitor = {"left": x, "top": y, "width": w, "height": h}
            img = np.array(sct.grab(monitor))
        return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

    def get_pixel_color(self, x: int, y: int) -> tuple[int, int, int] | None:
        """Get the (R, G, B) color of a single pixel."""
        img = self.capture_region(x, y, 1, 1)
        if img is None:
            return None
        b, g, r = img[0, 0]
        return int(r), int(g), int(b)

    # ── Template matching ─────────────────────────────────────────────

    def find_element(
        self,
        template_name: str,
        region: tuple[int, int, int, int] | None = None,
        threshold: float | None = None,
    ) -> MatchResult | None:
        """
        Find a single UI element on screen.

        Parameters
        ----------
        template_name : name of loaded template
        region : (x, y, w, h) to restrict search area, or None for full screen
        threshold : match confidence threshold (default: self._threshold)

        Returns
        -------
        MatchResult with the best match, or None if below threshold.
        """
        if not _HAVE_CV2:
            return None
        if template_name not in self._templates and not self.load_template(template_name):
            return None

        tmpl = self._templates[template_name]
        thr = threshold if threshold is not None else self._threshold

        if region:
            screen = self.capture_region(*region)
            offset_x, offset_y = region[0], region[1]
        else:
            screen = self.capture_screen()
            offset_x, offset_y = 0, 0

        if screen is None:
            return None

        # Convert template to BGR if needed
        if tmpl.shape[2] == 4:
            tmpl_bgr = tmpl[:, :, :3]
            tmpl_mask = tmpl[:, :, 3]
        else:
            tmpl_bgr = tmpl
            tmpl_mask = None

        # Determine which scales to try
        if self._cached_scale is not None:
            scales = (self._cached_scale,)
        else:
            scales = self.SCALES

        best: MatchResult | None = None

        for scale in scales:
            if scale != 1.0:
                th, tw = tmpl_bgr.shape[:2]
                new_w = max(1, int(tw * scale))
                new_h = max(1, int(th * scale))
                scaled_tmpl = cv2.resize(tmpl_bgr, (new_w, new_h), interpolation=cv2.INTER_AREA)
                scaled_mask = (
                    cv2.resize(tmpl_mask, (new_w, new_h), interpolation=cv2.INTER_AREA)
                    if tmpl_mask is not None else None
                )
            else:
                scaled_tmpl = tmpl_bgr
                scaled_mask = tmpl_mask

            th, tw = scaled_tmpl.shape[:2]
            if th > screen.shape[0] or tw > screen.shape[1]:
                continue

            if scaled_mask is not None:
                result = cv2.matchTemplate(screen, scaled_tmpl, cv2.TM_CCOEFF_NORMED, mask=scaled_mask)
            else:
                result = cv2.matchTemplate(screen, scaled_tmpl, cv2.TM_CCOEFF_NORMED)

            _, max_val, _, max_loc = cv2.minMaxLoc(result)

            if max_val >= thr and (best is None or max_val > best.confidence):
                best = MatchResult(
                    x=max_loc[0] + offset_x,
                    y=max_loc[1] + offset_y,
                    w=tw, h=th,
                    confidence=float(max_val),
                    scale=scale,
                )

        return best

    def find_best_element(
        self,
        template_name: str,
        region: tuple[int, int, int, int] | None = None,
    ) -> MatchResult | None:
        """Return the best available match even if it is below the normal threshold."""
        return self.find_element(template_name, region=region, threshold=-1.0)

    def find_all_elements(
        self,
        template_name: str,
        region: tuple[int, int, int, int] | None = None,
        threshold: float | None = None,
        max_results: int = 20,
    ) -> list[MatchResult]:
        """Find all instances of a template element on screen."""
        if not _HAVE_CV2:
            return []
        if template_name not in self._templates and not self.load_template(template_name):
            return []

        tmpl = self._templates[template_name]
        thr = threshold if threshold is not None else self._threshold

        if region:
            screen = self.capture_region(*region)
            offset_x, offset_y = region[0], region[1]
        else:
            screen = self.capture_screen()
            offset_x, offset_y = 0, 0

        if screen is None:
            return []

        if tmpl.shape[2] == 4:
            tmpl_bgr = tmpl[:, :, :3]
            tmpl_mask = tmpl[:, :, 3]
        else:
            tmpl_bgr = tmpl
            tmpl_mask = None

        scale = self._cached_scale or 1.0
        if scale != 1.0:
            th, tw = tmpl_bgr.shape[:2]
            new_w = max(1, int(tw * scale))
            new_h = max(1, int(th * scale))
            tmpl_bgr = cv2.resize(tmpl_bgr, (new_w, new_h), interpolation=cv2.INTER_AREA)
            if tmpl_mask is not None:
                tmpl_mask = cv2.resize(tmpl_mask, (new_w, new_h), interpolation=cv2.INTER_AREA)

        th, tw = tmpl_bgr.shape[:2]
        if th > screen.shape[0] or tw > screen.shape[1]:
            return []

        if tmpl_mask is not None:
            result = cv2.matchTemplate(screen, tmpl_bgr, cv2.TM_CCOEFF_NORMED, mask=tmpl_mask)
        else:
            result = cv2.matchTemplate(screen, tmpl_bgr, cv2.TM_CCOEFF_NORMED)

        matches: list[MatchResult] = []
        for _ in range(max_results):
            _, max_val, _, max_loc = cv2.minMaxLoc(result)
            if max_val < thr:
                break
            matches.append(MatchResult(
                x=max_loc[0] + offset_x,
                y=max_loc[1] + offset_y,
                w=tw, h=th,
                confidence=float(max_val),
                scale=scale,
            ))
            # Suppress this match region
            cx, cy = max_loc
            y1 = max(0, cy - th // 2)
            y2 = min(result.shape[0], cy + th // 2)
            x1 = max(0, cx - tw // 2)
            x2 = min(result.shape[1], cx + tw // 2)
            result[y1:y2, x1:x2] = 0

        return matches

    def wait_for_element(
        self,
        template_name: str,
        timeout_s: float = 5.0,
        poll_interval_s: float = 0.3,
        region: tuple[int, int, int, int] | None = None,
        threshold: float | None = None,
    ) -> MatchResult | None:
        """Poll the screen until the template is found or timeout."""
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            match = self.find_element(template_name, region, threshold)
            if match:
                return match
            time.sleep(poll_interval_s)
        return None

    def calibrate_scale(self, reference_template: str) -> float | None:
        """
        Auto-detect UI scale factor by matching a known template at
        multiple scales and caching the best-fit scale.
        """
        if reference_template not in self._templates and not self.load_template(reference_template):
            return None

        saved = self._cached_scale
        self._cached_scale = None  # force multi-scale search

        match = self.find_element(reference_template, threshold=0.70)
        if match:
            self._cached_scale = match.scale
            return match.scale

        self._cached_scale = saved
        return None

    def set_scale(self, scale: float) -> None:
        self._cached_scale = scale

    def reset_scale(self) -> None:
        self._cached_scale = None
