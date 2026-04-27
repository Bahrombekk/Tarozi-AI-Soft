from __future__ import annotations
from PyQt6.QtCore import Qt, QSize, QRegularExpression
from PyQt6.QtGui import (QIcon, QPixmap, QColor, QCursor,
                          QRegularExpressionValidator, QIntValidator, QDoubleValidator)
from PyQt6.QtWidgets import (QDialog, QLabel, QVBoxLayout, QHBoxLayout,
                              QPushButton, QWidget, QLineEdit, QCheckBox,
                              QGraphicsDropShadowEffect)
from ui.styles import get_styles, get_hover_color, get_text_color, get_bg_color
from ui.widgets import HiddenSwitch, Switch, ClickableQLineEdit
from core.config import *
try:
    from utils.helpers import (SCREEN_WIDTH, SCREEN_HEIGHT, window_icon,
                                view_icon, unview_icon, view_icon_light, unview_icon_light,
                                half_available)
except Exception:
    SCREEN_WIDTH, SCREEN_HEIGHT = 1920, 1080
    window_icon = view_icon = unview_icon = view_icon_light = unview_icon_light = None
    half_available = False

class EditLabelWidget(QLabel):

    def __init__(self, style_name: str, name: str = "default", ed: str = "cs"):
        super().__init__()
        self.style_name: str = style_name
        self.style_: str = get_styles(style_name=self.style_name)
        self.setContentsMargins(14, 8, 14, 8)
        self.setFixedSize(int(SCREEN_WIDTH * 0.34), int(SCREEN_WIDTH * 0.042))

        self.setObjectName("settings_edit_lbl")

        self.password_toggle_btn: QPushButton = QPushButton()

        if name == "theme":
            lt: QHBoxLayout = QHBoxLayout()
            lt.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
            lt.setSpacing(0)
            lt.setContentsMargins(0, 0, 0, 0)

            h1_lt: QHBoxLayout = QHBoxLayout()
            h1_lt.setContentsMargins(0, 0, 0, 0)
            h1_lt.setSpacing(8)
            h1_lt.setAlignment(Qt.AlignmentFlag.AlignRight)

            shadow: QGraphicsDropShadowEffect = QGraphicsDropShadowEffect(self)
            shadow.setBlurRadius(5)
            shadow.setOffset(0, 3)
            shadow.setColor(QColor(0, 0, 0, 26))
            shadow_light: QGraphicsDropShadowEffect = QGraphicsDropShadowEffect(self)
            shadow_light.setBlurRadius(5)
            shadow_light.setOffset(0, 3)
            shadow_light.setColor(QColor(0, 0, 0, 26))
            shadow_dark: QGraphicsDropShadowEffect = QGraphicsDropShadowEffect(self)
            shadow_dark.setBlurRadius(5)
            shadow_dark.setOffset(0, 3)
            shadow_dark.setColor(QColor(0, 0, 0, 26))

            self.additional_btn: QPushButton = QPushButton("Sozlamalar")
            self.additional_btn.setObjectName("auto")
            self.additional_btn.setGraphicsEffect(shadow)
            self.additional_btn.setCursor(Qt.CursorShape.PointingHandCursor)

            h1_lt.addWidget(self.additional_btn)

            v1_lt: QVBoxLayout = QVBoxLayout()
            v1_lt.setContentsMargins(0, 0, 0, 0)
            v1_lt.setSpacing(0)

            lt.addLayout(v1_lt, 6)
            lt.addLayout(h1_lt, 1)
            self.lbl: QLabel = QLabel("Qo'shimcha sozlamalar")
            self.lbl.setObjectName("settings_lbl")
            self.lbl.setContentsMargins(0, 3, 0, 3)
            self.edit: ClickableQLineEdit | QLineEdit = ClickableQLineEdit(ty=ed)
            self.edit.setObjectName("settings_edit")
            self.edit.setText("Qo'shimcha sozlamalarga kirish uchun parol kerak bo'ladi")
            self.edit.setDisabled(True)
            self.edit.setContentsMargins(0, 0, 0, 0)
            v1_lt.addWidget(self.lbl)
            v1_lt.addWidget(self.edit)
        elif name == "password":
            lt: QVBoxLayout = QVBoxLayout()
            lt.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
            lt.setSpacing(0)
            lt.setContentsMargins(0, 0, 0, 0)

            pw_lt: QHBoxLayout = QHBoxLayout()
            pw_lt.setContentsMargins(0, 0, 0, 0)
            pw_lt.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            self.password_toggle_btn.setObjectName("toggle_btn")
            if self.style_name == DARK:
                self.password_toggle_btn.setIcon(view_icon_light)
            else:
                self.password_toggle_btn.setIcon(view_icon)
            self.password_toggle_btn.setIconSize(QSize(20, 20))
            self.password_toggle_btn.setContentsMargins(0, 0, 0, 0)
            self.password_toggle_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

            pw_lt.addWidget(self.password_toggle_btn)

            self.lbl: QLabel = QLabel("Label")
            self.lbl.setObjectName("settings_lbl")
            self.lbl.setContentsMargins(0, 3, 0, 3)
            self.edit: ClickableQLineEdit | QLineEdit = ClickableQLineEdit(ty=ed)
            self.edit.setObjectName("settings_edit")
            self.edit.setDisabled(True)
            self.edit.setContentsMargins(0, 0, 0, 0)
            self.edit.setLayout(pw_lt)
            lt.addWidget(self.lbl)
            lt.addWidget(self.edit)
        else:
            lt: QVBoxLayout = QVBoxLayout()
            lt.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
            lt.setSpacing(0)
            lt.setContentsMargins(0, 0, 0, 0)
            self.lbl: QLabel = QLabel("Label")
            self.lbl.setObjectName("settings_lbl")
            self.lbl.setContentsMargins(0, 3, 0, 3)
            self.edit: ClickableQLineEdit | QLineEdit = QLineEdit()
            self.edit.setObjectName("settings_edit")
            self.edit.setDisabled(True)
            self.edit.setContentsMargins(0, 0, 0, 0)
            lt.addWidget(self.lbl)
            lt.addWidget(self.edit)
        self.edit.setContentsMargins(0, 5, 0, 0)
        self.setLayout(lt)

    def change_style(self, style_name: str):
        self.style_name: str = style_name
        self.style_: str = get_styles(style_name=self.style_name)
        self.setStyleSheet(self.style_)
        self.lbl.setStyleSheet(self.style_)
        self.edit.setStyleSheet(self.style_)
        if hasattr(self, "password_toggle_btn"):
            self.password_toggle_btn.setStyleSheet(self.style_)
        if hasattr(self, "additional_btn"):
            self.additional_btn.setStyleSheet(self.style_)



class SettingsWidget(QWidget):

    def __init__(self, style_name: str):
        super().__init__()
        self.style_name: str = style_name
        self.style_: str = get_styles(style_name=self.style_name)
        main_layout: QVBoxLayout = QVBoxLayout()
        main_layout.setSpacing(16)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        self.setLayout(main_layout)
        self.setObjectName("settings_widget")

        h_lt: QHBoxLayout = QHBoxLayout()
        h_lt.setContentsMargins(0, 0, 0, 0)

        self.settings_lbl: QLabel = QLabel("Sozlamalar")
        self.settings_lbl.setObjectName("settings")

        self.save_btn: QPushButton = QPushButton("Saqlash")
        self.save_btn.setObjectName("save_btn")

        self.auto_switch: HiddenEditLabelSwitchWidget = HiddenEditLabelSwitchWidget(
            style_name=self.style_name,
            w=int(SCREEN_WIDTH * 0.34),
            h=int(SCREEN_HEIGHT * 0.065),
        )
        self.auto_switch.lbl.setText("Dasturni avtomatlashtirish")
        self.auto_switch.edit.setText("Sozlama yoqilganda dastur avtomatik ish bajaradi")

        h_lt.addWidget(self.settings_lbl, alignment=Qt.AlignmentFlag.AlignLeft)
        h_lt.addWidget(self.save_btn, alignment=Qt.AlignmentFlag.AlignRight)

        self.station_code_widget: EditLabelWidget = EditLabelWidget(
            style_name=self.style_name,
        )
        self.station_code_widget.lbl.setText("Stansiya kodi")

        self.scale_code_widget: EditLabelWidget = EditLabelWidget(
            style_name=self.style_name,
        )
        self.scale_code_widget.lbl.setText("Tarozi kodi")

        self.send_time_widget: EditLabelWidget = EditLabelWidget(
            style_name=self.style_name,
        )
        self.send_time_widget.lbl.setText(f"Interval (sekund: [{min_time}, {max_time}])")
        int_validator: QIntValidator = QIntValidator(min_time, max_time, self)
        self.send_time_widget.edit.setPlaceholderText(f"[{min_time}, {max_time}]")
        self.send_time_widget.edit.setValidator(int_validator)

        self.left_cam_widget: EditLabelWidget = EditLabelWidget(style_name=self.style_name)
        self.left_cam_widget.lbl.setText("Chap kamera")

        self.right_cam_widget: EditLabelWidget = EditLabelWidget(style_name=self.style_name)
        self.right_cam_widget.lbl.setText("O'ng kamera")

        self.theme_widget: HiddenEditLabelSwitchWidget = HiddenEditLabelSwitchWidget(
            style_name=self.style_name,
            w=int(SCREEN_WIDTH * 0.34),
            h=int(SCREEN_HEIGHT * 0.065),
        )
        self.theme_widget.lbl.setText("Mavzu")
        self.theme_widget.edit.setText("Tunggi rejim")
        self.theme_widget.edit.setReadOnly(True)

        self.additional_widget: EditLabelWidget = EditLabelWidget(
            name="theme",
            style_name=self.style_name,
            ed="no"
        )
        self.additional_widget.lbl.setText("Qo'shimcha sozlamalar")

        main_layout.addLayout(h_lt)
        main_layout.addWidget(self.theme_widget)
        main_layout.addWidget(self.additional_widget)
        main_layout.addWidget(self.station_code_widget)
        main_layout.addWidget(self.scale_code_widget)
        main_layout.addWidget(self.send_time_widget)
        main_layout.addWidget(self.left_cam_widget)
        main_layout.addWidget(self.right_cam_widget)
        main_layout.addWidget(self.auto_switch)

    def change_style(self, style_name: str):
        self.style_name: str = style_name
        self.style_: str = get_styles(style_name=self.style_name)
        self.auto_switch.change_style(style_name=self.style_name)
        self.theme_widget.change_style(style_name=self.style_name)
        self.additional_widget.change_style(style_name=self.style_name)
        self.left_cam_widget.change_style(style_name=self.style_name)
        self.right_cam_widget.change_style(style_name=self.style_name)
        self.send_time_widget.change_style(style_name=self.style_name)
        self.station_code_widget.change_style(style_name=self.style_name)
        self.scale_code_widget.change_style(style_name=self.style_name)
        self.settings_lbl.setStyleSheet(self.style_)
        self.save_btn.setStyleSheet(self.style_)
        self.setStyleSheet(self.style_)



class HiddenEditLabelSwitchWidget(QLabel):

    def __init__(self, style_name: str, w: int = int(SCREEN_WIDTH * 0.32), h: int = int(SCREEN_HEIGHT * 0.045)):
        super().__init__()
        self.style_name: str = style_name
        self.style_: str = get_styles(style_name=self.style_name)
        self.setContentsMargins(16, 12, 16, 12)

        if w > 0:
            self.setFixedSize(w, h)

        self.setObjectName("hidden_settings_edit_lbl")

        v1_lt: QVBoxLayout = QVBoxLayout()
        v1_lt.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        v1_lt.setSpacing(0)
        v1_lt.setContentsMargins(0, 0, 0, 0)

        v2_lt: QVBoxLayout = QVBoxLayout()
        v2_lt.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        v2_lt.setSpacing(0)
        v2_lt.setContentsMargins(0, 0, 0, 0)

        h_lt: QHBoxLayout = QHBoxLayout()
        h_lt.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        h_lt.setSpacing(0)
        h_lt.setContentsMargins(0, 0, 0, 0)

        self.lbl: QLabel = QLabel()
        self.lbl.setObjectName("hidden1_settings_lbl")

        self.edit: QLineEdit = QLineEdit()
        self.edit.setObjectName("hidden1_settings_edit")

        self.hidden_switch: HiddenSwitch = HiddenSwitch(
            style_name=self.style_name,
            size=45,
        )
        v2_lt.addWidget(self.hidden_switch, alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignVCenter)

        h_lt.addLayout(v1_lt, 99)
        h_lt.addLayout(v2_lt, 1)
        v1_lt.addWidget(self.lbl)
        v1_lt.addWidget(self.edit)
        self.setLayout(h_lt)
        self.change_style(style_name=self.style_name)

    def change_style(self, style_name: str):
        self.style_name: str = style_name
        self.style_: str = get_styles(style_name=self.style_name)
        self.hidden_switch.change_style(style_name=self.style_name)
        self.lbl.setStyleSheet(self.style_)
        self.edit.setStyleSheet(self.style_)
        self.setStyleSheet(self.style_)



class HiddenEditLabelWidget(QLabel):

    def __init__(self, style_name: str, w: int = int(SCREEN_WIDTH * 0.15), h: int = int(SCREEN_HEIGHT * 0.045)):
        super().__init__()
        self.style_name: str = style_name
        self.style_: str = get_styles(style_name=self.style_name)
        self.setContentsMargins(14, 8, 14, 8)
        self.setFixedSize(w, h)

        self.setObjectName("hidden_settings_edit_lbl")

        lt: QVBoxLayout = QVBoxLayout()
        lt.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        lt.setSpacing(0)
        lt.setContentsMargins(0, 0, 0, 0)

        self.lbl: QLabel = QLabel()
        self.lbl.setObjectName("hidden_settings_lbl")

        self.edit: QLineEdit = QLineEdit()
        self.edit.setObjectName("hidden_settings_edit")

        lt.addWidget(self.lbl)
        lt.addWidget(self.edit)
        self.setLayout(lt)

    def change_style(self, style_name: str):
        self.style_name: str = style_name
        self.style_: str = get_styles(style_name=self.style_name)
        self.setStyleSheet(self.style_)
        self.lbl.setStyleSheet(self.style_)
        self.edit.setStyleSheet(self.style_)



class HiddenEditLabelWidget2(QLabel):

    def __init__(self, style_name: str, w: int = int(SCREEN_WIDTH * 0.32), h: int = int(SCREEN_HEIGHT * 0.05)):
        super().__init__()
        self.style_name: str = style_name
        self.style_: str = get_styles(style_name=self.style_name)
        self.setContentsMargins(0, 8, 14, 0)
        self.setFixedSize(w, h + 20)

        self.setObjectName("hidden_settings2_edit_lbl")

        lt: QHBoxLayout = QHBoxLayout()
        lt.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        lt.setSpacing(30)
        lt.setContentsMargins(0, 0, 0, 0)

        self.help_col1_lbl: QLabel = QLabel("help text 1")
        self.help_col1_lbl.setObjectName("hidden_help_settings_lbl")

        self.help_col2_lbl: QLabel = QLabel("help text 2")
        self.help_col2_lbl.setObjectName("hidden_help_settings_lbl")

        self.col1: HiddenEditLabelWidget = HiddenEditLabelWidget(
            style_name=self.style_name,
            w=int(self.width() * 0.49),
            h=int(self.height() * 0.7),
        )
        self.col2: HiddenEditLabelWidget = HiddenEditLabelWidget(
            style_name=self.style_name,
            w=int(self.width() * 0.49),
            h=int(self.height() * 0.7),
        )

        self.col1.edit.setContentsMargins(0, 10, 0, 0)
        self.col2.edit.setContentsMargins(0, 10, 0, 0)

        v1_lt: QVBoxLayout = QVBoxLayout()
        v2_lt: QVBoxLayout = QVBoxLayout()
        v1_lt.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        v2_lt.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        v1_lt.addWidget(self.col1, alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        v1_lt.addSpacing(30)
        v1_lt.addWidget(self.help_col1_lbl)

        v2_lt.addWidget(self.col2, alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        v2_lt.addSpacing(30)
        v2_lt.addWidget(self.help_col2_lbl)

        lt.addLayout(v1_lt, 1)
        lt.addLayout(v2_lt, 1)
        self.setLayout(lt)

    def change_style(self, style_name: str):
        self.style_name: str = style_name
        self.style_: str = get_styles(style_name=self.style_name)
        self.setStyleSheet(self.style_)
        self.help_col1_lbl.setStyleSheet(self.style_)
        self.help_col2_lbl.setStyleSheet(self.style_)
        self.col1.change_style(style_name=self.style_name)
        self.col2.change_style(style_name=self.style_name)



class HiddenSettingsWidget(QDialog):

    def __init__(self, style_name: str):
        super().__init__()
        self.style_name: str = style_name
        self.style_: str = get_styles(style_name=self.style_name)
        main_layout: QVBoxLayout = QVBoxLayout()
        main_layout.setSpacing(16)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        self.setFixedSize(int(SCREEN_WIDTH * 0.34), int(SCREEN_HEIGHT * 0.70))
        self.setLayout(main_layout)
        self.setObjectName("hidden_settings")
        self.setWindowTitle("Sozlamalar")
        self.setWindowIcon(window_icon)
        wx = int(SCREEN_WIDTH * 0.32)
        hy = int(SCREEN_HEIGHT * 0.075)
        self.top_bottom: HiddenEditLabelWidget2 = HiddenEditLabelWidget2(
            style_name=self.style_name,
            w=wx, h=hy,
        )
        self.left_right: HiddenEditLabelWidget2 = HiddenEditLabelWidget2(
            style_name=self.style_name,
            w=wx, h=hy,
        )
        self.frame_count_distance: HiddenEditLabelWidget2 = HiddenEditLabelWidget2(
            style_name=self.style_name,
            w=wx, h=hy,
        )
        self.line: HiddenEditLabelSwitchWidget = HiddenEditLabelSwitchWidget(
            style_name=self.style_name,
            w=wx, h=hy,
        )
        self.half: HiddenEditLabelSwitchWidget = HiddenEditLabelSwitchWidget(
            style_name=self.style_name,
            w=wx, h=hy,
        )
        self.fps_: HiddenEditLabelSwitchWidget = HiddenEditLabelSwitchWidget(
            style_name=self.style_name,
            w=wx, h=hy,
        )

        self.half.hidden_switch.setChecked(False)
        self.half.hidden_switch.setDisabled(not half_available)

        self.top_bottom.col1.lbl.setText("Tepadan")
        self.top_bottom.col1.edit.setText(str(top_offset))
        self.top_bottom.help_col1_lbl.setText(f"[{min_side}% - {max_side}%]")

        self.top_bottom.col2.lbl.setText("Pastdan")
        self.top_bottom.col2.edit.setText(str(bottom_offset))
        self.top_bottom.help_col2_lbl.setText(f"[{min_side}% - {max_side}%]")

        self.left_right.col1.lbl.setText("Chapdan")
        self.left_right.col1.edit.setText(str(left_offset))
        self.left_right.help_col1_lbl.setText(f"[{min_side}% - {max_side}%]")

        self.left_right.col2.lbl.setText("O'ngdan")
        self.left_right.col2.edit.setText(str(right_offset))
        self.left_right.help_col2_lbl.setText(f"[{min_side}% - {max_side}%]")

        self.frame_count_distance.col1.lbl.setText("Kadrlar soni")
        self.frame_count_distance.col1.edit.setText(str(default_frame_count))
        self.frame_count_distance.help_col1_lbl.setText(f"{min_frame_count} - {max_frame_count}")

        self.frame_count_distance.col2.lbl.setText("Oraliq")
        self.frame_count_distance.col2.edit.setText(str(default_distance))
        self.frame_count_distance.help_col2_lbl.setText(f"{min_distance} - {max_distance}")

        self.line.lbl.setText("Chiziq")
        self.line.edit.setText("Kameradagi chiqizlarni ko'rsatish")
        self.line.edit.setReadOnly(True)

        self.half.lbl.setText("Yarim aniqlik")
        self.half.edit.setText("Sun'iy intellekt orqali aniqlikni kuchaytirish")
        self.half.edit.setReadOnly(True)

        self.fps_.lbl.setText("FPS")
        self.fps_.edit.setText("FPS ko'rsatish")
        self.fps_.edit.setReadOnly(True)

        self.save_btn: QPushButton = QPushButton("Saqlash")
        self.save_btn.setObjectName("save_btn")

        self.back_btn: QPushButton = QPushButton("Bekor qilish")
        self.back_btn.setObjectName("back_btn")

        h_lt: QHBoxLayout = QHBoxLayout()
        h_lt.setSpacing(16)
        h_lt.setContentsMargins(0, 0, 0, 0)
        h_lt.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)

        h_lt.addWidget(self.back_btn)
        h_lt.addWidget(self.save_btn)

        main_layout.addWidget(self.top_bottom)
        main_layout.addWidget(self.left_right)
        main_layout.addWidget(self.frame_count_distance)
        main_layout.addWidget(self.line)
        main_layout.addWidget(self.half)
        main_layout.addWidget(self.fps_)
        main_layout.addLayout(h_lt)
        self.change_style(style_name=self.style_name)

    def change_style(self, style_name: str):
        self.style_name: str = style_name
        self.style_: str = get_styles(style_name=self.style_name)
        self.setStyleSheet(self.style_)

        self.save_btn.setStyleSheet(self.style_)
        self.back_btn.setStyleSheet(self.style_)

        self.top_bottom.change_style(style_name=self.style_name)
        self.left_right.change_style(style_name=self.style_name)
        self.frame_count_distance.change_style(style_name=self.style_name)
        self.line.change_style(style_name=self.style_name)
        self.half.change_style(style_name=self.style_name)
        self.fps_.change_style(style_name=self.style_name)



class SpecialSettingsDialog(QDialog):

    def __init__(self, style_name: str):
        super().__init__()
        self.style_name: str = style_name
        self.style_: str = get_styles(style_name=self.style_name)
        main_layout: QVBoxLayout = QVBoxLayout()
        main_layout.setSpacing(16)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        self.setFixedSize(int(SCREEN_WIDTH * 0.64), int(SCREEN_HEIGHT * 0.80))
        self.setLayout(main_layout)
        self.setObjectName("hidden_settings")
        self.setWindowTitle("Maxsus sozlamalar")
        self.setWindowIcon(window_icon)
        wx: int = int(SCREEN_WIDTH * 0.58)
        hy: int = int(SCREEN_HEIGHT * 0.07)

        self.d_r_conf: HiddenEditLabelWidget2 = HiddenEditLabelWidget2(
            style_name=self.style_name,
            w=wx, h=hy
        )
        self.urls: HiddenEditLabelWidget2 = HiddenEditLabelWidget2(
            style_name=self.style_name,
            w=wx, h=hy
        )
        self.login_widget: EditLabelWidget = EditLabelWidget(
            style_name=self.style_name,
            ed=""
        )
        self.login_widget.lbl.setText("Login")
        self.login_widget.setFixedWidth(wx)
        self.password_widget: EditLabelWidget = EditLabelWidget(
            style_name=self.style_name,
            name="password",
            ed=""
        )
        self.password_widget.lbl.setText("Parol")
        self.password_widget.edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_widget.setFixedWidth(wx)
        self.scale_view: HiddenEditLabelSwitchWidget = HiddenEditLabelSwitchWidget(
            style_name=self.style_name,
            w=wx, h=hy,
        )
        self.btn_disable: HiddenEditLabelSwitchWidget = HiddenEditLabelSwitchWidget(
            style_name=self.style_name,
            w=wx, h=hy,
        )
        self.scale_disable: HiddenEditLabelSwitchWidget = HiddenEditLabelSwitchWidget(
            style_name=self.style_name,
            w=wx, h=hy,
        )

        self.d_r_conf.col1.lbl.setText("ID aniqligi")
        self.d_r_conf.col1.edit.setText(str(default_det_conf))
        self.d_r_conf.help_col1_lbl.setText(f"{min_det_conf} - {max_det_conf}")

        self.d_r_conf.col2.lbl.setText("Raqam aniqligi")
        self.d_r_conf.col2.edit.setText(str(default_rec_conf))
        self.d_r_conf.help_col2_lbl.setText(f"{min_rec_conf} - {max_rec_conf}")

        self.urls.col1.lbl.setText("Login URL")
        self.urls.help_col1_lbl.setText("https://<DOMAIN>/api/auth/login")

        self.urls.col2.lbl.setText("Post URL")
        self.urls.help_col2_lbl.setText("https://<DOMAIN>/api/post/url")

        self.scale_view.lbl.setText("Tarozi raqami")
        self.scale_view.edit.setText("Tarozi raqamini ko'rsatish")
        self.scale_view.edit.setReadOnly(True)

        self.btn_disable.lbl.setText("Tasdiqlash tugmasi")
        self.btn_disable.edit.setText("Tasdiqlash tugmasini o'chirib qo'yish")
        self.btn_disable.edit.setReadOnly(True)

        self.scale_disable.lbl.setText("COM Port (tarozi)")
        self.scale_disable.edit.setText("COM Portni o'chirib qo'yish (tarozi ulanmaydi)")
        self.scale_disable.edit.setReadOnly(True)

        self.save_btn: QPushButton = QPushButton("Saqlash")
        self.save_btn.setObjectName("save_btn")

        self.back_btn: QPushButton = QPushButton("Bekor qilish")
        self.back_btn.setObjectName("back_btn")

        h_lt: QHBoxLayout = QHBoxLayout()
        h_lt.setSpacing(16)
        h_lt.setContentsMargins(0, 0, 0, 0)
        h_lt.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)

        h_lt.addWidget(self.back_btn)
        h_lt.addWidget(self.save_btn)

        main_layout.addWidget(self.d_r_conf)
        main_layout.addWidget(self.urls)
        main_layout.addWidget(self.login_widget)
        main_layout.addWidget(self.password_widget)
        main_layout.addWidget(self.scale_view)
        main_layout.addWidget(self.btn_disable)
        main_layout.addWidget(self.scale_disable)
        main_layout.addLayout(h_lt)
        self.change_style(style_name=self.style_name)

    def change_style(self, style_name: str):
        self.style_name: str = style_name
        self.style_: str = get_styles(style_name=self.style_name)
        self.setStyleSheet(self.style_)

        self.save_btn.setStyleSheet(self.style_)
        self.back_btn.setStyleSheet(self.style_)
        self.d_r_conf.change_style(style_name=self.style_name)
        self.scale_view.change_style(style_name=self.style_name)
        self.btn_disable.change_style(style_name=self.style_name)
        self.scale_disable.change_style(style_name=self.style_name)
        self.login_widget.change_style(style_name=self.style_name)
        self.password_widget.change_style(style_name=self.style_name)

