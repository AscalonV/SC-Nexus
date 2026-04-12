"""
SelfTorpSettingsDialog — QDialog popup for Self-Torp configuration.

Shows the current hotkey, first key, burst key, and a capture button.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QEvent, QTimer, Signal
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

_STYLE = """
QDialog { background-color: #080f1a; color: #e8f0fe; }
QLabel  { color: #e8f0fe; }
QLineEdit {
    background-color: #0d1b2a;
    color: #e8f0fe;
    border: 1px solid #1e3050;
    border-radius: 4px;
    padding: 4px 8px;
}
QPushButton {
    background-color: transparent;
    color: #8899aa;
    border: 1px solid #1e3050;
    border-radius: 4px;
    padding: 5px 14px;
}
QPushButton:hover { color: #e8f0fe; border-color: #4fc3f7; }
QPushButton#capture {
    background-color: #4fc3f7;
    color: #000;
    font-weight: bold;
    border: none;
}
QPushButton#capture:hover { background-color: #81d4fa; }
QSpinBox {
    background-color: #0d1b2a;
    color: #e8f0fe;
    border: 1px solid #1e3050;
    border-radius: 4px;
    padding: 4px 8px;
}
"""

_MS_SPIN_MAX = 2_147_483_647


class SelfTorpSettingsDialog(QDialog):
    """
    Modal settings popup.  Returns Accepted if the user clicked OK.

    Read results via ``result_hotkey``, ``result_first_key``, ``result_burst_key``.
    """

    def __init__(
        self,
        hotkey:    str,
        first_key: str,
        burst_key: str,
        burst_key_2: str = "",
        burst_count: int = 15,
        first_key_delay_ms: int = 50,
        burst_gap_ms: int = 1,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Self-Torp — Settings")
        self.setStyleSheet(_STYLE)
        self.setMinimumWidth(380)
        self.setWindowFlags(
            (self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
            | Qt.WindowType.WindowCloseButtonHint
        )

        self.result_hotkey    = hotkey
        self.result_first_key = first_key
        self.result_burst_key = burst_key
        self.result_burst_key_2 = burst_key_2
        self.result_burst_count = burst_count
        self.result_first_key_delay_ms = first_key_delay_ms
        self.result_burst_gap_ms = burst_gap_ms

        self._capturing = False
        self._capture_target: str = ""   # "hotkey" | "first" | "burst" | "burst2"

        layout = QVBoxLayout(self)
        form   = QFormLayout()
        form.setSpacing(10)

        # Hotkey row
        self._hotkey_edit = QLineEdit(hotkey)
        self._hotkey_edit.setReadOnly(True)
        hotkey_row = self._key_row(self._hotkey_edit, "hotkey")
        form.addRow("Trigger hotkey:", hotkey_row)

        # First key
        self._first_edit = QLineEdit(first_key)
        self._first_edit.setReadOnly(True)
        first_row = self._key_row(self._first_edit, "first")
        form.addRow("First key:", first_row)

        # Burst key
        self._burst_edit = QLineEdit(burst_key)
        self._burst_edit.setReadOnly(True)
        burst_row = self._key_row(self._burst_edit, "burst")
        form.addRow("Burst key:", burst_row)

        # Burst key 2 (optional)
        self._burst2_edit = QLineEdit(burst_key_2)
        self._burst2_edit.setReadOnly(True)
        self._burst2_edit.setPlaceholderText("(none)")
        burst2_row = self._key_row(self._burst2_edit, "burst2", clearable=True)
        form.addRow("Burst key 2:", burst2_row)

        # Burst count
        self._burst_count_spin = QSpinBox()
        self._burst_count_spin.setRange(5, 50)
        self._burst_count_spin.setValue(burst_count)
        self._burst_count_spin.setToolTip(
            "Retry count for single-key mode.\n"
            "When Burst key 2 is set, the module now sends one deterministic\n"
            "launch/detonate pair instead of spamming many repeats."
        )
        form.addRow("Burst count:", self._burst_count_spin)

        # First key delay
        self._delay_spin = QSpinBox()
        self._delay_spin.setRange(0, _MS_SPIN_MAX)
        self._delay_spin.setSuffix(" ms")
        self._delay_spin.setValue(first_key_delay_ms)
        form.addRow("First key delay:", self._delay_spin)

        # Burst gap
        self._gap_spin = QSpinBox()
        self._gap_spin.setRange(0, _MS_SPIN_MAX)
        self._gap_spin.setSuffix(" ms")
        self._gap_spin.setValue(burst_gap_ms)
        self._gap_spin.setToolTip(
            "Spin-wait delay between each burst press.\n"
            "0 = no gap (may miss detonation).\n"
            "1 ms matches fast-scroll timing and usually works.\n"
            "Raise to 3–5 ms if camera still resets."
        )
        form.addRow("Burst gap:", self._gap_spin)

        layout.addLayout(form)

        self._status_label = QLabel("")
        self._status_label.setStyleSheet("color: #4fc3f7; font-size: 11px;")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._status_label)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # ------------------------------------------------------------------
    # Row builder
    # ------------------------------------------------------------------

    def _key_row(self, edit: QLineEdit, target: str, clearable: bool = False) -> QWidget:
        row = QWidget()
        hl  = QHBoxLayout(row)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(6)
        hl.addWidget(edit, 1)

        btn = QPushButton("Capture")
        btn.setObjectName("capture")
        btn.clicked.connect(lambda: self._start_capture(target))
        hl.addWidget(btn)

        if clearable:
            clr = QPushButton("Clear")
            clr.clicked.connect(lambda: self._clear_key(target))
            hl.addWidget(clr)

        return row

    # ------------------------------------------------------------------
    # Key capture
    # ------------------------------------------------------------------

    def _start_capture(self, target: str) -> None:
        self._capture_target = target
        self._capturing = True
        self._status_label.setText("Press any key or button…")

        # Use application-level event filter — more reliable than grabKeyboard
        # on Windows where focus issues can swallow keyPressEvent.
        QApplication.instance().installEventFilter(self)

        # Auto-cancel after 10s
        self._capture_timer = QTimer(self)
        self._capture_timer.setSingleShot(True)
        self._capture_timer.timeout.connect(self._cancel_capture)
        self._capture_timer.start(10_000)

    def _cancel_capture(self) -> None:
        self._capturing = False
        QApplication.instance().removeEventFilter(self)
        self._status_label.setText("")

    def eventFilter(self, obj, event) -> bool:  # noqa: N802
        if self._capturing and event.type() == QEvent.Type.KeyPress:
            vk_qt = event.key()
            key_text = _qt_key_to_name(vk_qt)
            if not key_text:
                # For keys not in the static map (punctuation, umlauts, etc.)
                # use the actual character Qt reports for this key press.
                text = event.text()
                if text and len(text) == 1 and text.isprintable():
                    key_text = text
            if key_text:
                self._apply_capture(key_text)
                return True

        if self._capturing and event.type() == QEvent.Type.MouseButtonPress:
            key_text = _qt_mouse_button_to_name(event.button())
            if key_text:
                self._apply_capture(key_text)
                return True

        if self._capturing and event.type() == QEvent.Type.Wheel:
            delta_y = event.angleDelta().y()
            if delta_y > 0:
                self._apply_capture("WHEELUP")
                return True
            if delta_y < 0:
                self._apply_capture("WHEELDOWN")
                return True

        return super().eventFilter(obj, event)

    def keyPressEvent(self, event) -> None:  # noqa: N802
        # Prevent Escape from closing the dialog while capturing
        if self._capturing:
            return
        super().keyPressEvent(event)

    def _apply_capture(self, key_text: str) -> None:
        if self._capture_target == "hotkey":
            self._hotkey_edit.setText(key_text)
        elif self._capture_target == "first":
            self._first_edit.setText(key_text)
        elif self._capture_target == "burst":
            self._burst_edit.setText(key_text)
        elif self._capture_target == "burst2":
            self._burst2_edit.setText(key_text)

        self._cancel_capture()

    def _clear_key(self, target: str) -> None:
        if target == "burst2":
            self._burst2_edit.setText("")

    # ------------------------------------------------------------------
    # Accept
    # ------------------------------------------------------------------

    def _accept(self) -> None:
        self.result_hotkey    = self._hotkey_edit.text().strip()
        self.result_first_key = self._first_edit.text().strip()
        self.result_burst_key = self._burst_edit.text().strip()
        self.result_burst_key_2 = self._burst2_edit.text().strip()
        self.result_burst_count = self._burst_count_spin.value()
        self.result_first_key_delay_ms = self._delay_spin.value()
        self.result_burst_gap_ms = self._gap_spin.value()
        self.accept()


# ---------------------------------------------------------------------------
# Qt key → name mapping
# ---------------------------------------------------------------------------

def _qt_key_to_name(key: int) -> str:
    """Convert a Qt.Key value to the engine's key name string."""
    from PySide6.QtCore import Qt as _Qt

    _MAP: dict[int, str] = {
        _Qt.Key.Key_A: "A", _Qt.Key.Key_B: "B", _Qt.Key.Key_C: "C",
        _Qt.Key.Key_D: "D", _Qt.Key.Key_E: "E", _Qt.Key.Key_F: "F",
        _Qt.Key.Key_G: "G", _Qt.Key.Key_H: "H", _Qt.Key.Key_I: "I",
        _Qt.Key.Key_J: "J", _Qt.Key.Key_K: "K", _Qt.Key.Key_L: "L",
        _Qt.Key.Key_M: "M", _Qt.Key.Key_N: "N", _Qt.Key.Key_O: "O",
        _Qt.Key.Key_P: "P", _Qt.Key.Key_Q: "Q", _Qt.Key.Key_R: "R",
        _Qt.Key.Key_S: "S", _Qt.Key.Key_T: "T", _Qt.Key.Key_U: "U",
        _Qt.Key.Key_V: "V", _Qt.Key.Key_W: "W", _Qt.Key.Key_X: "X",
        _Qt.Key.Key_Y: "Y", _Qt.Key.Key_Z: "Z",
        _Qt.Key.Key_0: "0", _Qt.Key.Key_1: "1", _Qt.Key.Key_2: "2",
        _Qt.Key.Key_3: "3", _Qt.Key.Key_4: "4", _Qt.Key.Key_5: "5",
        _Qt.Key.Key_6: "6", _Qt.Key.Key_7: "7", _Qt.Key.Key_8: "8",
        _Qt.Key.Key_9: "9",
        _Qt.Key.Key_F1:  "F1",  _Qt.Key.Key_F2:  "F2",  _Qt.Key.Key_F3:  "F3",
        _Qt.Key.Key_F4:  "F4",  _Qt.Key.Key_F5:  "F5",  _Qt.Key.Key_F6:  "F6",
        _Qt.Key.Key_F7:  "F7",  _Qt.Key.Key_F8:  "F8",  _Qt.Key.Key_F9:  "F9",
        _Qt.Key.Key_F10: "F10", _Qt.Key.Key_F11: "F11", _Qt.Key.Key_F12: "F12",
        _Qt.Key.Key_Left:  "LEFT",  _Qt.Key.Key_Right: "RIGHT",
        _Qt.Key.Key_Up:    "UP",    _Qt.Key.Key_Down:  "DOWN",
        _Qt.Key.Key_Space: "SPACE", _Qt.Key.Key_Return: "RETURN",
        _Qt.Key.Key_Tab:   "TAB",   _Qt.Key.Key_Escape: "ESCAPE",
        _Qt.Key.Key_Insert: "INSERT", _Qt.Key.Key_Delete: "DELETE",
        _Qt.Key.Key_Home: "HOME",   _Qt.Key.Key_End: "END",
        _Qt.Key.Key_PageUp: "PRIOR", _Qt.Key.Key_PageDown: "NEXT",
    }
    return _MAP.get(key, "")


def _qt_mouse_button_to_name(button: Qt.MouseButton) -> str:
    if button == Qt.MouseButton.BackButton:
        return "MOUSE4"
    if button == Qt.MouseButton.ForwardButton:
        return "MOUSE5"
    return ""
