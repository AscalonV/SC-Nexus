"""
High-level game navigation sequences for Star Conflict ship equipping.

Composes InputDriver (clicks, keys, scrolls) into atomic navigation
operations that mirror the AHK script's coordinate-based equip flow.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Signal

from src.modules.loadout_manager.automation.input_driver import InputDriver, spin_sleep_ms
from src.modules.loadout_manager.automation.scanner import LoadoutScanner, MatchResult

if TYPE_CHECKING:
    from src.modules.loadout_manager.database import Build, Ship
    from src.modules.loadout_manager.settings import LoadoutManagerSettings

log = logging.getLogger(__name__)


class EquipCancelled(Exception):
    """Raised when the equip sequence is cancelled by the user."""


def _clamp_search_region(
    x: int,
    y: int,
    w: int,
    h: int,
    screen: tuple[int, int] | None,
) -> tuple[int, int, int, int]:
    if screen is None:
        return x, y, w, h
    max_w, max_h = screen
    x = max(0, min(x, max_w - 1))
    y = max(0, min(y, max_h - 1))
    w = max(1, min(w, max_w - x))
    h = max(1, min(h, max_h - y))
    return x, y, w, h


class GameNavigator(QObject):
    """
    High-level game automation sequences.

    All methods block the calling thread and emit progress signals.
    Run on a QThread — never on the main/GUI thread.
    """

    progress = Signal(str)   # status message
    error = Signal(str)      # non-fatal error description
    step = Signal(int, int)  # (current_step, total_steps)

    _MIN_ACTION_DELAY_MS = 100
    _NAV_HOTKEY_REPEAT_COUNT = 5

    def __init__(
        self,
        driver: InputDriver,
        scanner: LoadoutScanner,
        settings: "LoadoutManagerSettings",
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._drv = driver
        self._scan = scanner
        self._settings = settings
        self._cancelled = False

    # ── Control ───────────────────────────────────────────────────────

    def cancel(self) -> None:
        self._cancelled = True

    def reset(self) -> None:
        self._cancelled = False

    def _check_cancel(self) -> bool:
        return self._cancelled

    def _wait(self, ms: int | None = None) -> None:
        delay_ms = ms if ms is not None else self._settings.automation_delay_ms
        delay_ms = max(delay_ms, self._MIN_ACTION_DELAY_MS)
        # Sleep in small chunks so cancellation takes effect quickly.
        _CHUNK_MS = 50.0
        remaining = float(delay_ms)
        while remaining > 0:
            if self._cancelled:
                raise EquipCancelled()
            spin_sleep_ms(min(_CHUNK_MS, remaining))
            remaining -= _CHUNK_MS
        if self._cancelled:
            raise EquipCancelled()

    def _send_repeated_nav_key(
        self,
        key: str,
        label: str,
        repeat_count: int | None = None,
    ) -> None:
        """Send a navigation hotkey multiple times with a safe gap between presses."""
        count = repeat_count if repeat_count is not None else self._NAV_HOTKEY_REPEAT_COUNT
        for attempt in range(count):
            self.progress.emit(
                f"{label} hotkey {attempt + 1}/{count}…"
            )
            self._drv.send_key(key)
            self._wait(self._MIN_ACTION_DELAY_MS)

    # ── Game focus ────────────────────────────────────────────────────

    def ensure_game_focus(self) -> bool:
        title = self._settings.game_window_title
        if InputDriver.is_game_focused(title):
            return True
        if InputDriver.focus_game_window(title):
            # Replicate AHK: WinActivate twice with 50ms gaps then wait
            self._wait(50)
            InputDriver.focus_game_window(title)
            self._wait(500)      # generous wait for game to be ready
            return True
        # Build a diagnostic list of visible window titles to help the user
        # confirm what title the game window actually reports.
        titles = InputDriver._enum_window_titles()
        sc_candidates = [t for t in titles if "star" in t.lower() or "conflict" in t.lower()]
        detail = (
            f"  Candidates: {sc_candidates}" if sc_candidates
            else f"  Open windows (first 10): {titles[:10]}"
        )
        self.error.emit(f"Game window '{title}' not found.\n{detail}")
        return False

    # ── Navigation primitives ─────────────────────────────────────────

    def open_ship_tree(self) -> bool:
        """Press ship-tree key 5 times to open ship fitting screen."""
        self.progress.emit("Opening ship fitting screen…")
        self._send_repeated_nav_key(self._settings.nav_key_ship_tree, "Ship tree")
        self._wait(200)
        return True

    def preparation(self) -> bool:
        """
        Preparation sequence: ESC → ENTER → ESC.
        Clears any open chat, confirm dialogs, windows, and menus.
        """
        self.progress.emit("Preparation: clearing windows…")
        self._drv.send_key("ESC")
        spin_sleep_ms(100)
        self._drv.send_key("ENTER")
        spin_sleep_ms(100)
        self._drv.send_key("ESC")
        spin_sleep_ms(100)
        return True

    def select_slot_hotkey(self, slot_num: int) -> bool:
        """Select slot 1-4 using the in-game numeric hotkeys, matching the AHK preset flow."""
        if slot_num < 1 or slot_num > 4:
            self.error.emit(f"Invalid slot hotkey {slot_num}.")
            return False
        self.progress.emit(f"Selecting slot {slot_num} via hotkey")
        self._drv.send_key(str(slot_num))
        self._wait(200)
        return True

    def click_element(
        self,
        template_name: str,
        timeout_s: float = 5.0,
        threshold: float | None = None,
        region: tuple[int, int, int, int] | None = None,
        detailed_errors: bool = True,
    ) -> bool:
        """Find a template on screen and click its center (only for remove_all_modules)."""
        self.progress.emit(f"Looking for {template_name}…")
        match = self._scan.wait_for_element(
            template_name,
            timeout_s=timeout_s,
            threshold=threshold,
            region=region,
        )
        if match is None:
            if not detailed_errors:
                self.error.emit(f"Could not find '{template_name}' on screen")
            else:
                best = self._scan.find_best_element(template_name, region=region)
                if best is None:
                    self.error.emit(f"Could not find '{template_name}' on screen")
                else:
                    self.error.emit(
                        f"Could not find '{template_name}' on screen "
                        f"(best={best.confidence:.3f}, scale={best.scale:.2f}, "
                        f"threshold={threshold if threshold is not None else self._scan._threshold:.2f})"
                    )
            return False
        cx, cy = match.center
        self._drv.click(cx, cy)
        self._wait()
        return True

    # ── Faction selection (coordinate-based) ──────────────────────────

    def select_faction(self, faction: str) -> bool:
        """Click the faction tab using stored coordinate."""
        self.progress.emit(f"Selecting faction: {faction}")
        coord = self._settings.faction_coords.get(faction)
        if coord is None:
            self.error.emit(
                f"No coordinate for faction '{faction}'. "
                f"Run Setup Guide or import AHK coordinates."
            )
            return False
        self._drv.click(coord.x, coord.y)
        self._wait()
        return True

    # ── Ship selection (coordinate + scroll) ──────────────────────────

    def select_ship(self, ship: "Ship") -> bool:
        """
        Navigate to a specific ship: faction tab → scroll → click ship coord.
        """
        self.progress.emit(f"Selecting ship: {ship.name}")

        # Select the right faction tab
        if ship.faction and ship.faction != "None":
            if not self.select_faction(ship.faction):
                return False
            self._wait(200)      # AHK: sleep, 200

        # Scroll to ship position
        scroll_coord = self._settings.scroll_coord
        if ship.scroll_amount and ship.scroll_direction and scroll_coord:
            self.progress.emit(f"Scrolling to {ship.name}…")
            self._drv.scroll(
                scroll_coord.x, scroll_coord.y,
                ship.scroll_direction, ship.scroll_amount,
            )

            # Secondary scroll (some ships need two passes)
            if ship.scroll_amount2 and ship.scroll_direction2:
                self._drv.scroll(
                    scroll_coord.x, scroll_coord.y,
                    ship.scroll_direction2, ship.scroll_amount2,
                )

        # Click ship coordinate
        if ship.click_x is None or ship.click_y is None:
            self.error.emit(
                f"No click coordinate for ship '{ship.name}'. "
                f"Use Manage Ships → Set Click Position to calibrate."
            )
            return False

        self._drv.click(ship.click_x, ship.click_y)
        # Move cursor off-screen so the ship info tooltip doesn't appear
        self._drv.hide_cursor()
        self._wait(1000)         # AHK: sleep, 1000 after ship click
        # Extra server-lag padding (user-configurable)
        if self._settings.server_delay_ms > 0:
            spin_sleep_ms(self._settings.server_delay_ms)

        return True

    # ── Slot selection ────────────────────────────────────────────────

    def select_slot(self, slot_num: int) -> bool:
        """Click ship slot 1-4 using stored coordinate."""
        self.progress.emit(f"Selecting slot {slot_num}")
        idx = slot_num - 1
        coords = self._settings.slot_coords
        if 0 <= idx < len(coords) and coords[idx] is not None:
            self._drv.click(coords[idx].x, coords[idx].y)
            self._wait()
            return True
        self.error.emit(f"No coordinate for slot {slot_num}. Run Setup Guide.")
        return False

    # ── Preset application (coordinate-based) ─────────────────────────

    def apply_preset(self, preset_num: int, slot_num: int | None = None) -> bool:
        """Click preset button using stored coordinate, then load/confirm."""
        self.progress.emit(f"Applying preset {preset_num}")

        if slot_num is not None:
            if not self.select_slot_hotkey(slot_num):
                return False

        idx = preset_num - 1
        preset_coords = self._settings.preset_coords
        if 0 <= idx < len(preset_coords) and preset_coords[idx] is not None:
            self._drv.click(preset_coords[idx].x, preset_coords[idx].y)
            self._wait(200)      # AHK: sleep, 200
        else:
            self.error.emit(f"No coordinate for preset {preset_num}. Run Setup Guide.")
            return False

        # Load / Apply button — AHK clicks it twice (sleep 100 then sleep 200)
        lp = self._settings.load_preset_coord
        if lp is not None:
            self._drv.click(lp.x, lp.y)
            self._wait(100)      # AHK: sleep, 100
            self._drv.click(lp.x, lp.y)
            self._wait(200)      # AHK: sleep, 200

        # Yes/Confirm dialog
        yc = self._settings.yes_coord
        if yc is not None:
            self._drv.click(yc.x, yc.y)
            self._wait(1000)     # AHK: sleep, 1000
            # Extra server-lag padding (user-configurable)
            if self._settings.server_delay_ms > 0:
                spin_sleep_ms(self._settings.server_delay_ms)

        return True

    def equip_ship(
        self,
        ship: "Ship",
        slot_num: int,
        unequip: bool = False,
    ) -> bool:
        """Change the ship in one slot, optionally unequipping first."""
        if self._check_cancel():
            raise EquipCancelled()

        if not self.ensure_game_focus():
            return False

        self._drv.save_cursor()
        try:
            self.preparation()

            if not self.open_ship_tree():
                return False

            if not self.select_slot(slot_num):
                return False

            if unequip and not self.unequip_all(slot_num):
                return False

            return self.select_ship(ship)
        finally:
            self._drv.restore_cursor()

    # ── Crew ──────────────────────────────────────────────────────────

    def open_crew_selector(self) -> bool:
        """Open crew/implant assignment screen."""
        self.progress.emit("Opening crew selector…")
        self._send_repeated_nav_key(self._settings.nav_key_crew, "Crew")
        self._wait(200)
        return True

    def _click_crew_button(self, button_idx: int) -> bool:
        """Click crew tab A-D (index 0-3)."""
        btns = self._settings.crew_button_coords
        if 0 <= button_idx < len(btns) and btns[button_idx] is not None:
            self._drv.click(btns[button_idx].x, btns[button_idx].y)
            self._wait(200)      # AHK: Sleep, 200
            return True
        self.error.emit(f"No coordinate for crew button {chr(65 + button_idx)}. Run Setup Guide.")
        return False

    def select_crew_member(self, position: int, skill: int) -> bool:
        """
        Click a crew grid cell using interpolated coordinates.

        position: 1-15 (crew member column)
        skill: 1-3 (skill row)
        """
        if skill < 1 or skill > 3 or position < 1 or position > 15:
            return False

        cell = self._settings.crew_grid_cell(position, skill)
        if cell is None:
            self.error.emit(
                "Crew grid corners not calibrated. Run Setup Guide."
            )
            return False

        self._drv.click(cell.x, cell.y)
        spin_sleep_ms(1)
        return True

    def wait_for_implant_ready(self) -> bool:
        """Wait for implant button to show the expected color (pixel check)."""
        impl_coord = self._settings.implant_coord
        if impl_coord is None:
            # No implant coord — just wait a fixed delay as fallback
            self._wait(500)
            return True

        target_hex = self._settings.implant_color.lstrip("0x").lstrip("#")
        try:
            tr = int(target_hex[0:2], 16)
            tg = int(target_hex[2:4], 16)
            tb = int(target_hex[4:6], 16)
        except (ValueError, IndexError):
            self._wait(500)
            return True

        deadline = time.monotonic() + self._settings.implant_timeout_ms / 1000
        while time.monotonic() < deadline:
            if self._check_cancel():
                raise EquipCancelled()
            color = self._scan.get_pixel_color(impl_coord.x, impl_coord.y)
            if color is not None:
                r, g, b = color
                # Allow some tolerance (±15 per channel)
                if abs(r - tr) <= 15 and abs(g - tg) <= 15 and abs(b - tb) <= 15:
                    return True
            time.sleep(0.05)  # 50ms chunks so cancel is noticed quickly

        self.error.emit("Implant selector timeout")
        return True  # Continue anyway — don't block the whole sequence

    # ── Unequip all ───────────────────────────────────────────────────

    def unequip_all(self, slot_num: int | None = None) -> bool:
        """Right-click the slot to open its context menu, then click 'Remove all modules'."""
        self.progress.emit("Removing all modules…")

        search_region: tuple[int, int, int, int] | None = None

        if slot_num is not None:
            idx = slot_num - 1
            coords = self._settings.slot_coords
            if 0 <= idx < len(coords) and coords[idx] is not None:
                sx, sy = coords[idx].x, coords[idx].y
                self._drv.right_click(sx, sy)
                # Move cursor off-screen immediately so it doesn't obscure the context-menu item
                self._drv.hide_cursor()
                screen = None
                snap = self._scan.capture_screen()
                if snap is not None:
                    screen = (snap.shape[1], snap.shape[0])
                search_region = _clamp_search_region(sx - 50, sy - 200, 500, 400, screen)

        # The context-menu entry may legitimately be absent when there is
        # nothing to remove. Treat that as a no-op instead of aborting the run.
        match = self._scan.wait_for_element(
            "remove_all_modules",
            timeout_s=1.0,
            threshold=0.80,
            region=search_region,
        )
        if match is None:
            self.progress.emit("Remove all modules entry not present; continuing.")
            return True

        cx, cy = match.center
        self._drv.click(cx, cy)
        self._wait(1000)  # wait for unequip animation — no confirm dialog
        return True

    # ── Full equip sequences ──────────────────────────────────────────

    def resolve(self) -> bool:
        """Step 6: press ESC to close remaining windows (e.g. crew)."""
        self.progress.emit("Closing remaining windows…")
        # Only ESC if the crew window appears to still be open (implant pixel check)
        impl_coord = self._settings.implant_coord
        if impl_coord is not None:
            color = self._scan.get_pixel_color(impl_coord.x, impl_coord.y)
            if color is not None:
                target_hex = self._settings.implant_color.lstrip("0x").lstrip("#")
                try:
                    tr = int(target_hex[0:2], 16)
                    tg = int(target_hex[2:4], 16)
                    tb = int(target_hex[4:6], 16)
                    r, g, b = color
                    # If pixel does NOT match implant-ready color the window is already closed
                    if abs(r - tr) > 15 or abs(g - tg) > 15 or abs(b - tb) > 15:
                        return True
                except (ValueError, IndexError):
                    pass
        self._drv.send_key("ESC")
        self._wait(self._MIN_ACTION_DELAY_MS)
        return True

    def equip_crew_slot(self, build: "Build", slot_num: int) -> bool:
        """
        Apply crew for one slot. Crew window must already be open.

        Clicks the crew button for this slot, walks the 15-member grid,
        then clicks the implant/apply button and waits for ready.
        """
        if self._check_cancel():
            raise EquipCancelled()

        # Mirror AHK mapping: slot 1/2/3/4 use crew buttons A/B/C/D.
        if not self._click_crew_button(slot_num - 1):
            return False

        for i, skill in enumerate(build.crew):
            if self._check_cancel():
                raise EquipCancelled()
            if skill < 1 or skill > 3:
                continue
            position = i + 1
            self.progress.emit(f"Setting crew {position}/15 → skill {skill}")
            self.step.emit(i, 15)
            self.select_crew_member(position, skill)

        # Click the Implant/Apply button and wait for the pixel color
        impl = self._settings.implant_coord
        if impl is not None:
            self._drv.click(impl.x, impl.y)
        self.wait_for_implant_ready()
        self._wait(500)  # settle delay after implant color confirms
        return True

    def equip_crew(self, build: "Build", slot_num: int = 1) -> bool:
        """Standalone crew equip: opens crew window, applies one slot, closes."""
        if self._check_cancel():
            raise EquipCancelled()

        if not self.ensure_game_focus():
            return False

        self._drv.save_cursor()
        try:
            if not self.open_crew_selector():
                return False
            if not self.equip_crew_slot(build, slot_num):
                return False
            self.resolve()
            return True
        finally:
            self._drv.restore_cursor()

    def equip_ship_and_preset(
        self,
        ship: "Ship",
        build: "Build",
        slot_num: int,
        unequip: bool = False,
    ) -> bool:
        """Full sequence: preparation → ship → preparation → preset."""
        if not self.equip_ship(ship, slot_num, unequip=unequip):
            return False
        self.preparation()
        if build.preset_slot:
            return self.apply_preset(build.preset_slot, slot_num)
        return True

    def equip_full(
        self,
        ship: "Ship",
        build: "Build",
        slot_num: int,
        unequip: bool = False,
        do_crew: bool = True,
    ) -> bool:
        """Full equip: ship + preset + optional crew."""
        if not self.equip_ship_and_preset(ship, build, slot_num, unequip):
            return False
        if do_crew and any(s > 0 for s in build.crew):
            return self.equip_crew(build, slot_num)
        return True
