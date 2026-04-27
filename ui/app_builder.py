from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTabWidget

from core.config import (
    DARK, LIGHT, AUTO, THEME, SEND_TIME, STATION_CODE, SCALE_CODE,
    default_send_time, default_station_code, default_scale_code,
)
from ui.history import HistoryWidget
from ui.main_window import TitleWidget, StatusWidget
from ui.settings_panel import SettingsWidget
from ui.table import Table
from ui.video_label import SideWidget
from ui.widgets import HorizontalWidget


class BuildMixin:

    def _build_ui(self, sw: int, sh: int):
        self.title_widget = TitleWidget(style_name=self.style_name)
        self.title_widget.exit_btn.clicked.connect(self.close)
        self.title_widget.full_btn.clicked.connect(self.show_toggle)
        self.title_widget.hide_btn.clicked.connect(self.showMinimized)

        self.main_widget = QWidget()
        self.main_widget.setObjectName("main_widget")
        main_layout = QVBoxLayout()
        self.main_widget.setLayout(main_layout)
        self.setCentralWidget(self.main_widget)

        self.tab_widget = QTabWidget()
        self.tab_widget.setObjectName("tab_widget")
        self.tab_widget.tabBar().setCursor(Qt.CursorShape.PointingHandCursor)
        self.status_widget = StatusWidget(style_name=self.style_name)
        self.tab_widget.setCornerWidget(self.status_widget)

        lt = QVBoxLayout()
        cam_lt = QHBoxLayout()
        center_lt = QHBoxLayout()
        lt.setSpacing(16)
        center_lt.setSpacing(16)
        cam_lt.setSpacing(16)

        self.cam_widget = QWidget()
        self.cam_widget.setObjectName("cam_widget")
        self.cam_widget.setLayout(lt)

        self.settings_widget = SettingsWidget(style_name=self.style_name,
                                              screen_width=sw, screen_height=sh)
        self.settings_widget.auto_switch.edit.setDisabled(True)
        self.hidden_settings_widget = None
        self.settings_widget.station_code_widget.edit.setText(
            self.config.get(STATION_CODE, default_station_code))
        self.settings_widget.scale_code_widget.edit.setText(
            self.config.get(SCALE_CODE, default_scale_code))
        self.settings_widget.send_time_widget.edit.setText(
            str(self.config.get(SEND_TIME, default_send_time)))
        self.settings_widget.left_cam_widget.edit.setText(self.cam_url_1)
        self.settings_widget.right_cam_widget.edit.setText(self.cam_url_2)
        self.settings_widget.auto_switch.hidden_switch.setChecked(self.config.get(AUTO, False))
        self.settings_widget.auto_switch.hidden_switch.stateChanged.connect(self.change_auto)
        self.settings_widget.theme_widget.hidden_switch.setChecked(
            self.config.get(THEME, LIGHT) == DARK)
        self.settings_widget.theme_widget.hidden_switch.stateChanged.connect(self.change_theme)
        self.settings_widget.left_cam_widget.lbl.mousePressEvent = self.settings_window_left
        self.settings_widget.right_cam_widget.lbl.mousePressEvent = self.settings_window_right
        self.settings_widget.save_btn.clicked.connect(self.save_settings)

        self.history_widget = HistoryWidget(style_name=self.style_name)

        self.left_widget = SideWidget(style_name=self.style_name, screen_width=sw, screen_height=sh)
        self.left_widget.side_lbl.setText("Chap kamera")
        self.left_widget.state_lbl.setText("Kamera o'chgan")
        self.right_widget = SideWidget(style_name=self.style_name, screen_width=sw, screen_height=sh)
        self.right_widget.side_lbl.setText("O'ng kamera")
        self.right_widget.state_lbl.setText("Kamera o'chgan")
        self.left_widget.frame_lbl.btn.setText("Tasdiqlash")
        self.right_widget.frame_lbl.btn.setText("Tasdiqlash")
        self.left_widget.frame_lbl.btn.clicked.connect(self.upload_handle_data_left)
        self.right_widget.frame_lbl.btn.clicked.connect(self.upload_handle_data_right)
        self.left_widget.switch.stateChanged.connect(self.start_video_left)
        self.right_widget.switch.stateChanged.connect(self.start_video_right)

        try:
            from PyQt6.QtGui import QPixmap
            weight_pixmap = QPixmap("images/gentle.png")
            time_pixmap = QPixmap("images/clock.png")
        except (Exception, ValueError):
            from PyQt6.QtGui import QPixmap
            weight_pixmap = QPixmap()
            time_pixmap = QPixmap()

        self.hor_left_widget = HorizontalWidget(style_name=self.style_name,
                                                screen_width=sw, screen_height=sh)
        self.hor_left_widget.left_icon_lbl.setPixmap(weight_pixmap)
        self.hor_left_widget.center_lbl.setText("Vagon og'irligi")
        self.hor_left_widget.right_lbl.setText("0 kg")
        self.hor_right_widget = HorizontalWidget(style_name=self.style_name,
                                                  screen_width=sw, screen_height=sh)
        self.hor_right_widget.left_icon_lbl.setPixmap(time_pixmap)
        self.hor_right_widget.center_lbl.setText("Interval")
        self.hor_right_widget.right_lbl.setText(self.send_current_time)
        self.table = Table(style_name=self.style_name, screen_width=sw, screen_height=sh)

        center_lt.addWidget(self.hor_left_widget)
        center_lt.addWidget(self.hor_right_widget)
        lt.addLayout(cam_lt, 5)
        lt.addLayout(center_lt, 1)
        lt.addWidget(self.table, 5)
        cam_lt.addWidget(self.left_widget, 1)
        cam_lt.addWidget(self.right_widget, 1)

        self.tab_widget.addTab(self.cam_widget, "Asosiy")
        self.tab_widget.addTab(self.settings_widget, "Sozlamalar")
        self.tab_widget.addTab(self.history_widget, "Tarix")

        self.setContentsMargins(0, 0, 0, 0)
        self.tab_widget.setContentsMargins(0, 0, 0, 0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.title_widget)
        main_layout.addWidget(self.tab_widget)
