"""
Pixel-based Ellydium tech tree automation.

Reads the current node states from the game screen by checking pixel
colours at known node positions, diffs against the desired build state,
and clicks nodes to apply the configuration.

5-phase sequence (matching AHK RunEllydiumPixelAutomation):
  1. Scan — read current node states from screen colours
  2. Diff — compare desired vs current
  3. Deactivate — click nodes that should be OFF but are currently ON
  4. Activate — click nodes to enable, branch-order (prerequisites first)
  5. Verify — re-scan to confirm final state matches desired
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Signal

from src.modules.loadout_manager.automation.input_driver import InputDriver, spin_sleep_ms
from src.modules.loadout_manager.automation.scanner import LoadoutScanner

if TYPE_CHECKING:
    from src.modules.loadout_manager.ellydium.tree_model import EllydiumTree
    from src.modules.loadout_manager.settings import EllydiumColors

log = logging.getLogger(__name__)


def _parse_color(hex_str: str) -> tuple[int, int, int]:
    """Parse '0xRRGGBB' or '#RRGGBB' to (R, G, B)."""
    s = hex_str.lstrip("#").replace("0x", "").replace("0X", "")
    if len(s) == 6:
        return int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)
    return 0, 0, 0


def _color_distance(c1: tuple[int, int, int], c2: tuple[int, int, int]) -> float:
    """Euclidean distance between two RGB colours."""
    return ((c1[0] - c2[0]) ** 2 + (c1[1] - c2[1]) ** 2 + (c1[2] - c2[2]) ** 2) ** 0.5


class TreeAutomation(QObject):
    """Automate Ellydium tech tree configuration via pixel detection."""

    progress = Signal(str)
    error = Signal(str)

    # Colour distance threshold for matching
    COLOR_TOLERANCE = 50.0

    def __init__(
        self,
        driver: InputDriver,
        scanner: LoadoutScanner,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._drv = driver
        self._scan = scanner
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def reset(self) -> None:
        self._cancelled = False

    # ── Phase 1: Scan ────────────────────────────────────────────────

    def scan_node_states(
        self,
        tree: "EllydiumTree",
        colors: "EllydiumColors",
        node_positions: dict[str, tuple[int, int]],
    ) -> dict[str, bool]:
        """
        Read current node states from the game screen.

        For each node, sample the pixel colour at its position and compare
        against the ON/OFF reference colours.

        Parameters
        ----------
        tree : tree definition (for node keys and categories)
        colors : reference ON/OFF colours from settings
        node_positions : dict of node_key → (screen_x, screen_y)

        Returns
        -------
        dict of node_key → is_enabled
        """
        normal_on = _parse_color(colors.normal_on)
        normal_off = _parse_color(colors.normal_off)
        spec_on = _parse_color(colors.spec_on)
        spec_off = _parse_color(colors.spec_off)

        states: dict[str, bool] = {}

        for key, node in tree.nodes.items():
            if key not in node_positions:
                continue

            x, y = node_positions[key]
            pixel = self._scan.get_pixel_color(x, y)
            if pixel is None:
                states[key] = False
                continue

            if node.is_spec_mod:
                d_on = _color_distance(pixel, spec_on)
                d_off = _color_distance(pixel, spec_off)
            else:
                d_on = _color_distance(pixel, normal_on)
                d_off = _color_distance(pixel, normal_off)

            states[key] = d_on < d_off and d_on < self.COLOR_TOLERANCE

        return states

    # ── Phase 2-5: Full automation ────────────────────────────────────

    def apply_tree(
        self,
        tree: "EllydiumTree",
        colors: "EllydiumColors",
        node_positions: dict[str, tuple[int, int]],
        click_delay_ms: int = 300,
        max_retries: int = 3,
    ) -> bool:
        """
        Full 5-phase automation: scan → diff → deactivate → activate → verify.

        Parameters
        ----------
        tree : desired tree state
        colors : reference ON/OFF colours
        node_positions : screen coordinates for each node
        click_delay_ms : delay after clicking each node
        max_retries : number of retry cycles

        Returns True if final state matches desired.
        """
        for attempt in range(max_retries):
            if self._cancelled:
                return False

            # Phase 1: scan
            self.progress.emit(f"Scanning node states (attempt {attempt + 1})…")
            current = self.scan_node_states(tree, colors, node_positions)

            # Phase 2: diff
            to_enable, to_disable = tree.diff(current)

            if not to_enable and not to_disable:
                self.progress.emit("Tree is already correct.")
                return True

            self.progress.emit(
                f"Changes needed: enable {len(to_enable)}, disable {len(to_disable)}"
            )

            # Phase 3: deactivate unwanted nodes
            for key in to_disable:
                if self._cancelled:
                    return False
                self._click_node(key, node_positions, click_delay_ms)

            # Phase 4: activate wanted nodes (sort by branch for prerequisites)
            to_enable_sorted = sorted(
                to_enable,
                key=lambda k: (tree.nodes[k].branch, tree.nodes[k].cost),
            )
            for key in to_enable_sorted:
                if self._cancelled:
                    return False

                node = tree.nodes[key]
                # SpecMod nodes may need special swap logic
                if node.is_spec_mod:
                    self._try_activate_spec_mod(key, tree, node_positions, click_delay_ms)
                else:
                    self._click_node(key, node_positions, click_delay_ms)

        # Phase 5: final verify
        self.progress.emit("Verifying final state…")
        final = self.scan_node_states(tree, colors, node_positions)
        to_enable, to_disable = tree.diff(final)

        if to_enable or to_disable:
            failed = to_enable + to_disable
            self.error.emit(f"Verification failed for {len(failed)} nodes: {failed}")
            return False

        self.progress.emit("Tree applied successfully.")
        return True

    # ── Node clicking ─────────────────────────────────────────────────

    def _click_node(
        self,
        key: str,
        positions: dict[str, tuple[int, int]],
        delay_ms: int,
    ) -> None:
        if key not in positions:
            self.error.emit(f"No position for node {key}")
            return
        x, y = positions[key]
        self.progress.emit(f"Clicking node {key} at ({x}, {y})")
        self._drv.click(x, y)
        spin_sleep_ms(delay_ms)

    def _try_activate_spec_mod(
        self,
        key: str,
        tree: "EllydiumTree",
        positions: dict[str, tuple[int, int]],
        delay_ms: int,
    ) -> None:
        """
        SpecMod nodes often require clicking twice (once to deselect the
        currently active SpecMod, once to activate the new one).
        """
        # Click the wanted node — this should swap the active SpecMod
        self._click_node(key, positions, delay_ms)
        # Give the game time to process the swap
        spin_sleep_ms(200)
