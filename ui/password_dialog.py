from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton

from ui.styles import get_styles


def _get_window_icon():
    try:
        return QIcon("images/train.png")
    except (Exception, ValueError):
        return None


class PasswordPromptDialog(QDialog):
    def __init__(self, style_name: str, screen_width: int = 1600, screen_height: int = 900):
        super().__init__()
        self.force_close: bool = True
        self.setStyleSheet(get_styles(style_name=style_name))
        self.setObjectName("hidden_settings")
        self.setWindowTitle("Maxsus sozlamalar")
        wi = _get_window_icon()
        if wi:
            self.setWindowIcon(wi)
        self.setFixedSize(int(screen_width * 0.30), int(screen_height * 0.18))
        wx, hy = int(screen_width * 0.26), int(screen_height * 0.075)
        from ui.settings_panel import HiddenEditLabelSwitchWidget
        main_layout = QVBoxLayout()
        main_layout.setSpacing(16)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        self.setLayout(main_layout)
        self.password = HiddenEditLabelSwitchWidget(style_name=style_name, w=wx, h=hy)
        self.password.edit.setContentsMargins(0, 15, 0, 0)
        self.password.lbl.setText("Parolni kiriting")
        self.password.edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.hidden_switch.stateChanged.connect(self._toggle_password)
        self.password.hidden_switch.setChecked(True)
        self.enter_btn = QPushButton("Kirish")
        self.enter_btn.setObjectName("save_btn")
        self.back_btn = QPushButton("Bekor qilish")
        self.back_btn.setObjectName("back_btn")
        h_lt = QHBoxLayout()
        h_lt.setSpacing(16)
        h_lt.setContentsMargins(0, 0, 0, 0)
        h_lt.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        h_lt.addWidget(self.back_btn)
        h_lt.addWidget(self.enter_btn)
        main_layout.addWidget(self.password)
        main_layout.addLayout(h_lt)

    def _toggle_password(self, ans: int):
        mode = QLineEdit.EchoMode.Password if ans == 2 else QLineEdit.EchoMode.Normal
        self.password.edit.setEchoMode(mode)
