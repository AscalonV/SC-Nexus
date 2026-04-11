"""
CombatAssistantSettingsView — QWidget subview shown inside the launchpad
QStackedWidget when the user clicks ⚙ Settings on the Combat Assistant tile.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSlider,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from ..module import CombatAssistantModule


_SCROLL_STYLE = """
QScrollArea { border: none; background: transparent; }
QScrollBar:vertical {
    background: #09121f;
    width: 12px;
    margin: 0;
    border-left: 1px solid #12253f;
}
QScrollBar::handle:vertical {
    background: #1e3050;
    min-height: 28px;
    border-radius: 5px;
    margin: 2px;
}
QScrollBar::handle:vertical:hover { background: #4fc3f7; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
    background: transparent;
    border: none;
}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: #09121f; }
"""


def _qss_url(path: Path) -> str:
    return path.resolve().as_posix()


_ASSET_DIR = Path(__file__).resolve().parent / "assets"
_CHECKBOX_OFF_URL = _qss_url(_ASSET_DIR / "checkbox_off.svg")
_CHECKBOX_ON_URL = _qss_url(_ASSET_DIR / "checkbox_on.svg")

_CHECKBOX_STYLE = f"""
QCheckBox {{
    color: #e8f0fe;
    font-size: 11px;
    spacing: 6px;
}}
QCheckBox::indicator {{
    width: 14px;
    height: 14px;
    image: url('{_CHECKBOX_OFF_URL}');
}}
QCheckBox::indicator:hover {{
    image: url('{_CHECKBOX_OFF_URL}');
}}
QCheckBox::indicator:checked {{
    image: url('{_CHECKBOX_ON_URL}');
}}
"""

_BOMB_REGION_LABELS = {
    "ally_roster_ingame": "In-Game Ally Bomb Area",
    "ally_roster_respawn": "Respawn Ally Bomb Area",
    "enemy_roster_ingame": "In-Game Enemy Bomb Area",
    "enemy_roster_respawn": "Respawn Enemy Bomb Area",
    "map_detect": "Map Detect Area",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _divider() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setStyleSheet("color: #24365c;")
    return line


def _h(*widgets: QWidget, spacing: int = 8) -> QHBoxLayout:
    lay = QHBoxLayout()
    lay.setSpacing(spacing)
    for w in widgets:
        lay.addWidget(w)
    return lay


# ---------------------------------------------------------------------------
# AgonyUserRow
# ---------------------------------------------------------------------------

class _AgonyUserRow(QWidget):
    remove_requested: Signal = Signal()

    def __init__(self, name: str = "", parent=None) -> None:
        super().__init__(parent)
        self._edit = QLineEdit(name)
        self._edit.setPlaceholderText("Username…")
        btn = QPushButton("✕")
        btn.setFixedWidth(28)
        btn.setStyleSheet("color: #ff5555; background: transparent;")
        btn.clicked.connect(self.remove_requested)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self._edit)
        lay.addWidget(btn)

    @property
    def username(self) -> str:
        return self._edit.text().strip()


# ---------------------------------------------------------------------------
# CombatAssistantSettingsView
# ---------------------------------------------------------------------------

class CombatAssistantSettingsView(QWidget):
    """
    Full-featured settings panel for the Combat Assistant module.

    Instantiated once by CombatAssistantModule.build_settings_panel().
    Communicates back to the module via direct method calls on ``_module``.
    """

    # Emitted when the master toggle inside this view changes, so the tile stays in sync.
    master_toggled: Signal = Signal(bool)

    def __init__(self, module: "CombatAssistantModule", parent=None) -> None:
        super().__init__(parent)
        self._module = module
        self.setStyleSheet(_CHECKBOX_STYLE)
        s = module.settings

        # ---- scroll area wrapping everything ----------------------------
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(_SCROLL_STYLE)

        inner = QWidget()
        self._root_lay = QVBoxLayout(inner)
        self._root_lay.setContentsMargins(16, 16, 16, 16)
        self._root_lay.setSpacing(14)
        scroll.setWidget(inner)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        # ---- master toggle ----------------------------------------------
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(10)

        self._master_chk = QCheckBox("Module Enabled")
        self._master_chk.setChecked(s.enabled)
        self._master_chk.stateChanged.connect(self._on_master_toggle)
        top_row.addWidget(self._master_chk)
        top_row.addStretch(1)

        self._move_overlay_btn = QPushButton()
        self._move_overlay_btn.clicked.connect(self._module.toggle_overlay_edit)
        top_row.addWidget(self._move_overlay_btn)

        self._root_lay.addLayout(top_row)
        self.refresh_overlay_edit_button(self._module.is_overlay_editing)
        self._root_lay.addWidget(_divider())

        # ---- feature cards ----------------------------------------------
        self._build_agony_card(s)
        self._build_game_start_card(s)
        self._build_torp_card(s)
        self._build_bomb_card(s)
        self._build_capture_card(s)
        self._root_lay.addStretch()

    # ------------------------------------------------------------------
    # Master toggle
    # ------------------------------------------------------------------

    def _on_master_toggle(self, state: int) -> None:
        enabled = bool(state)
        self._module.settings.enabled = enabled
        self._module.settings.save()
        self.master_toggled.emit(enabled)
        self._module.on_toggle(enabled)

    def sync_master(self, enabled: bool) -> None:
        """Called when the tile toggle updates the module; keeps checkbox in sync."""
        self._master_chk.blockSignals(True)
        self._master_chk.setChecked(enabled)
        self._master_chk.blockSignals(False)

    def refresh_overlay_edit_button(self, editing: bool) -> None:
        self._move_overlay_btn.setText("Finish Moving" if editing else "Move Tooltip")

    # ------------------------------------------------------------------
    # Agony card
    # ------------------------------------------------------------------

    def _build_agony_card(self, s) -> None:
        box = QGroupBox("Agony Buff")
        lay = QVBoxLayout(box)
        lay.setSpacing(8)

        self._agony_chk = QCheckBox("Enable")
        self._agony_chk.setChecked(s.agony_enabled)
        self._agony_chk.toggled.connect(lambda v: self._save_bool("agony_enabled", v))
        lay.addWidget(self._agony_chk)

        info = QLabel("Tracks 'BuffNearDeath_big'.\nActive: 12 s | Cooldown: 25 s")
        info.setStyleSheet("color: #9bb3d6; font-size: 11px;")
        lay.addWidget(info)

        lay.addWidget(QLabel("Additional usernames to track:"))

        self._agony_rows_layout = QVBoxLayout()
        self._agony_rows_layout.setSpacing(4)
        lay.addLayout(self._agony_rows_layout)

        self._agony_rows: list[_AgonyUserRow] = []
        for name in s.agony_extra_users:
            self._add_agony_row(name)

        btn_add = QPushButton("+ Add Username")
        btn_add.setStyleSheet("color: #4fc3f7; background: transparent;")
        btn_add.clicked.connect(lambda: self._add_agony_row(""))
        lay.addWidget(btn_add)

        self._root_lay.addWidget(box)

    def _add_agony_row(self, name: str) -> None:
        row = _AgonyUserRow(name)
        row.remove_requested.connect(lambda: self._remove_agony_row(row))
        row._edit.textChanged.connect(self._save_agony_users)
        self._agony_rows.append(row)
        self._agony_rows_layout.addWidget(row)

    def _remove_agony_row(self, row: _AgonyUserRow) -> None:
        self._agony_rows.remove(row)
        row.deleteLater()
        self._save_agony_users()

    def _save_agony_users(self) -> None:
        names = [r.username for r in self._agony_rows if r.username]
        self._module.settings.agony_extra_users = names
        self._module.settings.save()
        self._module.request_overlay_refresh()

    # ------------------------------------------------------------------
    # Game-start card
    # ------------------------------------------------------------------

    def _build_game_start_card(self, s) -> None:
        box = QGroupBox("Game Start Alert")
        lay = QVBoxLayout(box)

        self._game_start_chk = QCheckBox("Enable")
        self._game_start_chk.setChecked(s.game_start_enabled)
        self._game_start_chk.toggled.connect(
            lambda v: self._save_bool("game_start_enabled", v)
        )
        lay.addWidget(self._game_start_chk)

        info = QLabel(
            "Plays a sound when the game start is detected. Be carful with the volume"
        )
        info.setStyleSheet("color: #9bb3d6; font-size: 11px;")
        lay.addWidget(info)

        volume_row = QHBoxLayout()
        volume_label = QLabel("Volume")
        volume_label.setStyleSheet("color: #e8f0fe; font-size: 11px;")
        self._game_start_volume = QSlider(Qt.Orientation.Horizontal)
        self._game_start_volume.setRange(0, 100)
        self._game_start_volume.setValue(s.game_start_volume)
        self._game_start_volume.valueChanged.connect(self._save_game_start_volume)
        self._game_start_volume_value = QLabel(f"{s.game_start_volume}%")
        self._game_start_volume_value.setStyleSheet("color: #9bb3d6; font-size: 11px;")
        self._game_start_volume_value.setFixedWidth(40)
        volume_row.addWidget(volume_label)
        volume_row.addWidget(self._game_start_volume, 1)
        volume_row.addWidget(self._game_start_volume_value)
        lay.addLayout(volume_row)

        self._root_lay.addWidget(box)

    def _save_game_start_volume(self, value: int) -> None:
        self._module.settings.game_start_volume = value
        self._module.settings.save()
        self._game_start_volume_value.setText(f"{value}%")

    # ------------------------------------------------------------------
    # Torpedo card
    # ------------------------------------------------------------------

    def _build_torp_card(self, s) -> None:
        box = QGroupBox("Torpedo Timer")
        lay = QVBoxLayout(box)

        self._torp_chk = QCheckBox("Enable")
        self._torp_chk.setChecked(s.torp_enabled)
        self._torp_chk.toggled.connect(lambda v: self._save_bool("torp_enabled", v))
        lay.addWidget(self._torp_chk)

        info = QLabel("Tracks 'Spell_ClanShipTorpedo'.\nFirst wave: ~58.5 s | Subsequent: 65.5 s")
        info.setStyleSheet("color: #9bb3d6; font-size: 11px;")
        lay.addWidget(info)

        self._root_lay.addWidget(box)

    # ------------------------------------------------------------------
    # Bomb card
    # ------------------------------------------------------------------

    def _build_bomb_card(self, s) -> None:
        box = QGroupBox("Bomb Tracker")
        lay = QVBoxLayout(box)

        self._bomb_chk = QCheckBox("Enable")
        self._bomb_chk.setChecked(s.bomb_enabled)
        self._bomb_chk.toggled.connect(lambda v: self._save_bool("bomb_enabled", v))
        lay.addWidget(self._bomb_chk)

        info = QLabel(
            "Visual tracking of bomb icons.\n"
            "Calibrate separate ally/enemy roster areas for both in-game and respawn screens.\n"
            "Set the Map Detect area over the X close button on the map/respawn screen\n"
            "so the scanner knows which screen is active."
        )
        info.setStyleSheet("color: #9bb3d6; font-size: 11px;")
        lay.addWidget(info)

        row_ingame = QHBoxLayout()
        btn_ally_ingame = QPushButton("Set In-Game Ally")
        btn_ally_ingame.clicked.connect(lambda: self._module.calibrate_region("ally_roster_ingame"))
        btn_enemy_ingame = QPushButton("Set In-Game Enemy")
        btn_enemy_ingame.clicked.connect(lambda: self._module.calibrate_region("enemy_roster_ingame"))
        row_ingame.addWidget(btn_ally_ingame)
        row_ingame.addWidget(btn_enemy_ingame)
        lay.addLayout(row_ingame)

        row_respawn = QHBoxLayout()
        btn_ally_respawn = QPushButton("Set Respawn Ally")
        btn_ally_respawn.clicked.connect(lambda: self._module.calibrate_region("ally_roster_respawn"))
        btn_enemy_respawn = QPushButton("Set Respawn Enemy")
        btn_enemy_respawn.clicked.connect(lambda: self._module.calibrate_region("enemy_roster_respawn"))
        btn_preview = QPushButton("Preview Areas")
        btn_preview.clicked.connect(self._module.preview_regions)
        row_respawn.addWidget(btn_ally_respawn)
        row_respawn.addWidget(btn_enemy_respawn)
        row_respawn.addWidget(btn_preview)
        lay.addLayout(row_respawn)

        # Map detect calibration
        row_map = QHBoxLayout()
        btn_map_detect = QPushButton("Set Map Detect Area")
        btn_map_detect.setToolTip(
            "Open the map or respawn screen, then drag over the X close button."
        )
        btn_map_detect.clicked.connect(self._module.calibrate_map_reference)
        row_map.addWidget(btn_map_detect)
        row_map.addStretch()
        lay.addLayout(row_map)

        # Template capture
        lay.addWidget(_divider())
        tmpl_info = QLabel(
            "Enemy template is captured directly from the game.\n"
            "Ally template is rebuilt from the enemy silhouette to avoid\n"
            "background-dependent capture failures."
        )
        tmpl_info.setStyleSheet("color: #9bb3d6; font-size: 11px;")
        lay.addWidget(tmpl_info)

        row_tmpl = QHBoxLayout()
        btn_tmpl_ally = QPushButton("Rebuild Ally Template")
        btn_tmpl_ally.setToolTip("Rebuild the ally bomb template from the enemy silhouette")
        btn_tmpl_ally.clicked.connect(lambda: self._module.capture_bomb_template("ally"))
        btn_tmpl_enemy = QPushButton("Capture Enemy Template")
        btn_tmpl_enemy.setToolTip("Capture a new enemy bomb template from the game screen")
        btn_tmpl_enemy.clicked.connect(lambda: self._module.capture_bomb_template("enemy"))
        row_tmpl.addWidget(btn_tmpl_ally)
        row_tmpl.addWidget(btn_tmpl_enemy)
        lay.addLayout(row_tmpl)

        # Debug image toggle
        self._bomb_debug_chk = QCheckBox("Save debug images (for tuning)")
        self._bomb_debug_chk.setChecked(getattr(self._module, "_bomb_debug_images", False))
        self._bomb_debug_chk.toggled.connect(self._toggle_bomb_debug_images)
        self._bomb_debug_chk.setStyleSheet("color: #9bb3d6; font-size: 11px;")
        lay.addWidget(self._bomb_debug_chk)

        # Region status labels
        self._region_labels: dict[str, QLabel] = {}
        for key in (
            "ally_roster_ingame",
            "ally_roster_respawn",
            "enemy_roster_ingame",
            "enemy_roster_respawn",
            "map_detect",
        ):
            lbl = QLabel(self._region_text(key))
            lbl.setStyleSheet("color: #9bb3d6; font-family: Consolas; font-size: 11px;")
            self._region_labels[key] = lbl
            lay.addWidget(lbl)

        self._root_lay.addWidget(box)

    def _region_text(self, key: str) -> str:
        r = self._module.settings.regions.get(key)
        title = _BOMB_REGION_LABELS.get(key, key.replace("_", " ").title())
        if r:
            return f"{title}: ({r[0]}, {r[1]}) {r[2]}×{r[3]}"
        return f"{title}: Not Set"

    def refresh_regions(self) -> None:
        for key, lbl in self._region_labels.items():
            lbl.setText(self._region_text(key))

    def _toggle_bomb_debug_images(self, enabled: bool) -> None:
        self._module._bomb_debug_images = enabled

    # ------------------------------------------------------------------
    # Capture card
    # ------------------------------------------------------------------

    def _build_capture_card(self, s) -> None:
        box = QGroupBox("System Capture")
        lay = QVBoxLayout(box)

        self._capture_chk = QCheckBox("Enable")
        self._capture_chk.setChecked(s.capture_enabled)
        self._capture_chk.toggled.connect(lambda v: self._save_bool("capture_enabled", v))
        lay.addWidget(self._capture_chk)

        info = QLabel("Pixel monitoring of Dreadnought system points.\nTriggers sound alerts when white is detected (≥ 2 s).")
        info.setStyleSheet("color: #9bb3d6; font-size: 11px;")
        lay.addWidget(info)

        btn_lay = QHBoxLayout()
        self._point_labels: dict[str, QLabel] = {}
        for name, label_txt in [("cmd", "Command"), ("shield", "Shield"), ("weapon", "Weapon")]:
            col = QVBoxLayout()
            btn = QPushButton(f"Set {label_txt}")
            btn.clicked.connect(lambda checked=False, n=name: self._module.calibrate_point(n))
            col.addWidget(btn)
            lbl = QLabel(self._point_text(name))
            lbl.setStyleSheet("color: #9bb3d6; font-family: Consolas; font-size: 10px;")
            self._point_labels[name] = lbl
            col.addWidget(lbl)
            btn_lay.addLayout(col)
        lay.addLayout(btn_lay)

        preview_btn = QPushButton("Preview Points")
        preview_btn.clicked.connect(self._module.preview_points)
        lay.addWidget(preview_btn)

        self._root_lay.addWidget(box)

    def _point_text(self, name: str) -> str:
        pt = self._module.settings.points.get(name)
        if pt:
            return f"({pt[0]}, {pt[1]})"
        return "Not Set"

    def refresh_points(self) -> None:
        for name, lbl in self._point_labels.items():
            lbl.setText(self._point_text(name))

    # ------------------------------------------------------------------
    # Generic save helper
    # ------------------------------------------------------------------

    def _save_bool(self, field: str, value: bool) -> None:
        setattr(self._module.settings, field, value)
        self._module.settings.save()
        self._module.request_overlay_refresh()
