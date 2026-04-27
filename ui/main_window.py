from __future__ import annotations
import queue, threading, time, os, sys
from copy import deepcopy
from dataclasses import dataclass
from functools import partial
from typing import Union
import cv2, numpy as np
from PyQt6.QtCore import (Qt, QSize, QThread, pyqtSignal, QEvent, QTimer,
                           QPropertyAnimation, QEasingCurve, QRect, QObject, pyqtSlot, QLocale)
from PyQt6.QtGui import (QIcon, QImage, QPixmap, QPainter, QColor, QMouseEvent,
                          QCursor, QFont, QCloseEvent, QKeySequence, QShortcut,
                          QDoubleValidator, QRegularExpressionValidator)
from PyQt6.QtWidgets import (QApplication, QLabel, QVBoxLayout, QHBoxLayout,
                              QPushButton, QWidget, QMainWindow, QTabWidget,
                              QScrollArea, QSizePolicy, QMessageBox, QLineEdit)
from PyQt6.QtNetwork import QLocalSocket, QLocalServer
from core.config import *
from core.database import BufferDB, current_time
from network.api import check_server, check_internet_connection, get_token, image_to_base64
from ui.models import SendingData, SavingData
from ui.settings_manager import SettingsManager
from threads.video import VideoThread
from threads.auto_video import AutoVideoThread
from threads.upload import UploadThread, BackupUploadThread
from threads.workers import (ScaleThread, LoginThread, ServerConnectionThread,
                              SaveThread, ProgressThread, PingThread)
from ui.styles import get_styles, get_hover_color, get_text_color, get_bg_color
from ui.widgets import (Switch, HiddenSwitch, ClickableQLineEdit, HoverIconButton,
                        TransparentWidget, HorizontalWidget, StatusWidget, Title,
                        BlurEffect, OverlayWidget, _GlobalMouseReleaseFilter)
from ui.video_label import AspectRatioLabel, SideWidget
from ui.table import Table
from ui.history import HistoryWidget
from ui.settings_panel import (SettingsWidget, HiddenSettingsWidget, SpecialSettingsDialog,
                                EditLabelWidget, HiddenEditLabelSwitchWidget)
from ui.dialogs import ProgressBar, ImageDialog, ImageDialog2, PasswordDialog
from utils.image import cv2_to_qpixmap, qpixmap_to_ndarray, rounded_pixmap
from utils.helpers import (get_wagon_norm_tonn, get_wagon_type, get_side, get_camera_url,
                            get_max_frame_count, get_distance, get_is_line, get_half,
                            find_all_scale_ports, open_all_scales, check_files_exist,
                            ask_message, show_message, timer_back, get_base_url,
                            supports_half, half_available, get_gpu_name, is_process_elevated, current_time,
                            is_running, create_lock, make_range_validator,
                            window_icon, window_pixmap, weight_pixmap, time_pixmap,
                            view_icon, unview_icon, view_icon_light, unview_icon_light,
                            fail_icon, success_icon, no_image_pixmap,
                            cam_frame, cam_frame_light,
                            SCREEN_WIDTH, SCREEN_HEIGHT, WIDTH, HEIGHT,
                            fix_luhn_code)

sleep: float = 0.005
btn_disabled: bool = True
demo_video: bool = False



# SendingData, SavingData → ui.models
# SettingsManager → ui.settings_manager



class App(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window |
            Qt.WindowType.WindowMinimizeButtonHint | Qt.WindowType.WindowMaximizeButtonHint |
            Qt.WindowType.WindowCloseButtonHint)

        self.last_login_status: bool = False
        self.sent_left_auto: bool = False
        self.sent_right_auto: bool = False
        self.is_timeout: bool = False
        self.wagon_ids: list[str] = []
        self.last_image_left: QPixmap | None = None
        self.last_image_right: QPixmap | None = None
        self.last_data_left: dict = {}
        self.last_data_right: dict = {}

        self.sent_left_track_ids: list[int] = []
        self.sent_right_track_ids: list[int] = []

        self.backup_db: BufferDB = BufferDB()
        self.last_ttl: int = self.backup_db.get_total()
        self.backup_thread: BackupUploadThread | None = None

        self.setWindowIcon(window_icon)
        self.setWindowTitle(window_title)
        self.setGeometry((SCREEN_WIDTH - WIDTH) // 2, (SCREEN_HEIGHT - HEIGHT) // 2, WIDTH, HEIGHT)

        self.progressbar: ProgressBar = ProgressBar()
        self.progress_thread: ProgressThread = ProgressThread()
        self.progress_thread.value_signal.connect(self.fake_progressbar)

        self.settings: SettingsManager = SettingsManager(filename="settings/settings.bin")
        self.config: dict = self.settings.load()
        self.style_name: str = self.config.get(THEME, LIGHT)
        self.style_: str = get_styles(style_name=self.style_name)

        self.crop_1: int = crop_left
        self.crop_2: int = crop_right

        self.top_1: int = get_side(file_path="settings/top_1.bin")
        self.bottom_1: int = get_side(file_path="settings/bottom_1.bin")
        self.left_1: int = get_side(file_path="settings/left_1.bin")
        self.right_1: int = get_side(file_path="settings/right_1.bin")

        self.top_2: int = get_side(file_path="settings/top_2.bin")
        self.bottom_2: int = get_side(file_path="settings/bottom_2.bin")
        self.left_2: int = get_side(file_path="settings/left_2.bin")
        self.right_2: int = get_side(file_path="settings/right_2.bin")

        self.max_frame_count_1: int = get_max_frame_count(file_path="settings/frame_count_1.bin")
        self.max_frame_count_2: int = get_max_frame_count(file_path="settings/frame_count_2.bin")

        self.distance_1: int = get_distance(file_path="settings/distance_1.bin")
        self.distance_2: int = get_distance(file_path="settings/distance_2.bin")

        self.fps_view_1: bool = get_is_line(file_path="settings/fps_1.bin")
        self.fps_view_2: bool = get_is_line(file_path="settings/fps_2.bin")

        self.is_half_1: bool = get_half(file_path="settings/half_1.bin")
        self.is_half_2: bool = get_half(file_path="settings/half_2.bin")

        self.is_line_1: bool = get_is_line(file_path="settings/line_1.bin")
        self.is_line_2: bool = get_is_line(file_path="settings/line_2.bin")

        send_second: int = self.config.get(SEND_TIME, default_send_time)

        self.cam_url_1: str = get_camera_url(file_path="settings/cam_1.bin")
        self.cam_url_2: str = get_camera_url(file_path="settings/cam_2.bin")

        self.save_thread_left: SaveThread | None = None
        self.save_thread_right: SaveThread | None = None

        self.password_dialog: PasswordDialog | None = None
        self.special_settings_dialog: SpecialSettingsDialog | None = None
        self.upload_thread: UploadThread | None = None
        self.login_thread: LoginThread | None = None
        self.last_scale_weight: list[int] = [0]
        self.max_scale_weight: int = 5

        self.com_ports: list[str] = []
        self.scales: list = []
        self.sending_data: SendingData = SendingData()

        self.send_time: str = self.time_format(tm=send_second)
        self.send_current_time: str = self.send_time
        self.wagon_id_image: Union[np.ndarray | None] = None
        self.wagon_image: Union[np.ndarray | None] = None
        self.wagon_image2: Union[np.ndarray | None] = None
        self.running_1: bool = False
        self.running_2: bool = False

        self.video_thread_left: AutoVideoThread | VideoThread | None = None
        self.video_thread_right: AutoVideoThread | VideoThread | None = None
        self.running_left: bool = False
        self.running_right: bool = False
        self.upload_left: bool = False
        self.upload_right: bool = False

        self.title_widget: Title = Title(
            style_name=self.style_name
        )
        self.title_widget.exit_btn.clicked.connect(self.close)
        self.title_widget.full_btn.clicked.connect(self.show_toggle)
        self.title_widget.hide_btn.clicked.connect(self.showMinimized)

        self.main_widget: QWidget = QWidget()
        self.main_widget.setObjectName("main_widget")
        main_layout: QVBoxLayout = QVBoxLayout()
        self.main_widget.setLayout(main_layout)
        self.setCentralWidget(self.main_widget)

        self.tab_widget: QTabWidget = QTabWidget()
        self.tab_widget.setObjectName("tab_widget")
        self.tab_widget.tabBar().setCursor(Qt.CursorShape.PointingHandCursor)

        self.status_widget: StatusWidget = StatusWidget(style_name=self.style_name)

        self.tab_widget.setCornerWidget(self.status_widget)

        lt: QVBoxLayout = QVBoxLayout()
        cam_lt: QHBoxLayout = QHBoxLayout()
        center_lt: QHBoxLayout = QHBoxLayout()
        lt.setSpacing(16)
        center_lt.setSpacing(16)
        cam_lt.setSpacing(16)

        self.cam_widget: QWidget = QWidget()
        self.cam_widget.setObjectName("cam_widget")
        self.cam_widget.setLayout(lt)

        self.settings_widget: SettingsWidget = SettingsWidget(
            style_name=self.style_name
        )
        self.settings_widget.auto_switch.edit.setDisabled(True)
        self.hidden_settings_widget: HiddenSettingsWidget | None = None

        self.settings_widget.station_code_widget.edit.setText(self.config.get(STATION_CODE, default_station_code))
        self.settings_widget.scale_code_widget.edit.setText(self.config.get(SCALE_CODE, default_scale_code))
        self.settings_widget.send_time_widget.edit.setText(str(self.config.get(SEND_TIME, default_send_time)))
        self.settings_widget.left_cam_widget.edit.setText(self.cam_url_1)
        self.settings_widget.right_cam_widget.edit.setText(self.cam_url_2)
        self.settings_widget.auto_switch.hidden_switch.setChecked(self.config.get(AUTO, False))
        self.settings_widget.auto_switch.hidden_switch.stateChanged.connect(self.change_auto)

        self.settings_widget.theme_widget.hidden_switch.setChecked(self.config.get(THEME, LIGHT) == DARK)
        self.settings_widget.theme_widget.hidden_switch.stateChanged.connect(self.change_theme)

        self.settings_widget.station_code_widget.edit.setDisabled(False)
        self.settings_widget.scale_code_widget.edit.setDisabled(False)
        self.settings_widget.send_time_widget.edit.setDisabled(False)

        self.settings_widget.left_cam_widget.lbl.mousePressEvent = self.settings_window_left
        self.settings_widget.right_cam_widget.lbl.mousePressEvent = self.settings_window_right

        self.settings_widget.save_btn.clicked.connect(self.save_settings)

        self.history_widget: HistoryWidget = HistoryWidget(
            style_name=self.style_name
        )

        self.left_widget: SideWidget = SideWidget(
            style_name=self.style_name
        )
        self.left_widget.side_lbl.setText("Chap kamera")
        self.left_widget.state_lbl.setText("Kamera o'chgan")

        self.right_widget: SideWidget = SideWidget(
            style_name=self.style_name
        )
        self.right_widget.side_lbl.setText("O'ng kamera")
        self.right_widget.state_lbl.setText("Kamera o'chgan")

        self.left_widget.frame_lbl.btn.setText("Tasdiqlash")
        self.right_widget.frame_lbl.btn.setText("Tasdiqlash")
        self.left_widget.frame_lbl.btn.clicked.connect(self.upload_handle_data_left)
        self.right_widget.frame_lbl.btn.clicked.connect(self.upload_handle_data_right)

        self.left_widget.switch.stateChanged.connect(self.start_video_left)
        self.right_widget.switch.stateChanged.connect(self.start_video_right)

        self.hor_left_widget: HorizontalWidget = HorizontalWidget(
            style_name=self.style_name,
        )
        self.hor_left_widget.left_icon_lbl.setPixmap(weight_pixmap)
        self.hor_left_widget.center_lbl.setText("Vagon og'irligi")
        self.hor_left_widget.right_lbl.setText("0 kg")
        self.hor_right_widget: HorizontalWidget = HorizontalWidget(
            style_name=self.style_name,
        )
        self.hor_right_widget.left_icon_lbl.setPixmap(time_pixmap)
        self.hor_right_widget.center_lbl.setText("Interval")
        self.hor_right_widget.right_lbl.setText(self.send_current_time)

        self.table: Table = Table(
            style_name=self.style_name
        )

        center_lt.addWidget(self.hor_left_widget)
        center_lt.addWidget(self.hor_right_widget)

        lt.addLayout(cam_lt, 6)
        lt.addLayout(center_lt, 1)
        lt.addWidget(self.table, 4)

        cam_lt.addWidget(self.left_widget, 1)
        cam_lt.addWidget(self.right_widget, 1)

        self.tab_widget.addTab(self.cam_widget, "Asosiy")
        self.tab_widget.addTab(self.settings_widget, "Sozlamalar")
        self.tab_widget.addTab(self.history_widget, "Tarix")

        self.setContentsMargins(0, 0, 0, 0)
        self.tab_widget.setContentsMargins(0, 0, 0, 0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.find_scales()

        if not self.config.get(SCALE_DISABLE, False):
            self.scale_thread: ScaleThread = ScaleThread(scales=self.scales, com_ports=self.com_ports)
            self.scale_thread.scale_signal.connect(self.scale_weight)
            self.scale_thread.start()

        self.server_connection_thread: ServerConnectionThread = ServerConnectionThread(
            bs_url=self.config.get(BASE_URL, base_url)
        )
        self.server_connection_thread.connection_signal.connect(self.check_server_connection)
        self.server_connection_thread.start()

        if self.config.get(AUTO, False):
            self.left_widget.frame_lbl.btn.setDisabled(True)
            self.right_widget.frame_lbl.btn.setDisabled(True)
        else:
            self.left_widget.frame_lbl.btn.setDisabled(False)
            self.right_widget.frame_lbl.btn.setDisabled(False)

        QTimer.singleShot(1000, lambda: self.save_settings())
        self.timeout_timer: QTimer = QTimer(self)
        self.timeout_timer.timeout.connect(self.stop_timeout)
        self.timeout_timer.start(1000)

        main_layout.addWidget(self.title_widget)
        main_layout.addWidget(self.tab_widget)

        self.change_theme(ans=2 if self.style_name == DARK else 0)

        self.shortcut: QShortcut = QShortcut(QKeySequence("F5"), self)
        self.shortcut.activated.connect(self.insert_histories)

        self.login_thread: LoginThread = LoginThread(
            login_url=self.config.get(LOGIN_URL, get_token_url),
            data={
                "login": self.config.get(USERNAME, default_username),
                "password": self.config.get(PASSWORD, default_password)
            }
        )
        self.login_thread.login_signal.connect(self.login_response)
        self.login_thread.start()
        self.insert_histories()

        self.ping_thread: PingThread = PingThread(
            station_code=str(self.config.get(STATION_CODE, default_station_code))
        )
        self.ping_thread.start()

        self.overlay: OverlayWidget = OverlayWidget(self)
        self.overlay.setGeometry(self.main_widget.geometry())
        self.overlay.hide()

        self._resizing: bool = False
        self._is_maximized: bool = False
        self._anim: QPropertyAnimation | None = None
        self._opacity_anim: QPropertyAnimation | None = None
        self._normal_geometry: QRect = self.geometry()
        self._last_geometry: QRect = self.geometry()
        self._global_filter: _GlobalMouseReleaseFilter = _GlobalMouseReleaseFilter(self)

        self.title_widget.setMouseTracking(True)
        self.title_widget.installEventFilter(self)

        QApplication.instance().installEventFilter(self._global_filter)
        self.setMouseTracking(True)
        self.main_widget.setMouseTracking(True)
        self.installEventFilter(self)
        self.main_widget.installEventFilter(self)

        self.settings_widget.additional_widget.additional_btn.clicked.connect(self.ask_password_window)

    def eventFilter(self, obj, ev):
        et = ev.type()

        if obj is self.title_widget:
            if et == QEvent.Type.MouseButtonDblClick and ev.button() == Qt.MouseButton.LeftButton:
                self.show_toggle()
                return True
            if et == QEvent.Type.MouseButtonPress and ev.button() == Qt.MouseButton.LeftButton:
                if self.windowHandle():
                    self.windowHandle().startSystemMove()
                    return True

        if et == QEvent.Type.MouseMove:
            if not self.isMaximized() and not getattr(self, "_is_maximized", False):
                pos = self.mapFromGlobal(ev.globalPosition().toPoint())
                self._update_cursor_shape(pos)
                ev.accept()
            else:
                self.unsetCursor()
            return False

        if et == QEvent.Type.MouseButtonPress and ev.button() == Qt.MouseButton.LeftButton:
            if not self.isMaximized() and not getattr(self, "_is_maximized", False):
                pos = self.mapFromGlobal(ev.globalPosition().toPoint())
                dirs = self._hit_test(pos)
                if dirs and self.windowHandle():
                    edges = self._qt_edges_from_direction(dirs)
                    if edges:
                        self._resizing = True
                        self.windowHandle().startSystemResize(edges)
                        return True

        if et == QEvent.Type.MouseButtonRelease:
            if self._resizing:
                self._resizing = False
                self.unsetCursor()
            try:
                pos = self.mapFromGlobal(ev.globalPosition().toPoint())
                self._update_cursor_shape(pos)
            except (Exception, ValueError):
                self.unsetCursor()
            return False

        return super(type(self), self).eventFilter(obj, ev)

    @staticmethod
    def _qt_edges_from_direction(d: str) -> Qt.Edge:
        edges = Qt.Edge(0)
        if 'left' in d:
            edges |= Qt.Edge.LeftEdge
        if 'right' in d:
            edges |= Qt.Edge.RightEdge
        if 'top' in d:
            edges |= Qt.Edge.TopEdge
        if 'bottom' in d:
            edges |= Qt.Edge.BottomEdge
        return edges

    def _hit_test(self, pos) -> Union[str | None]:
        x, y = pos.x(), pos.y()
        w, h = self.width(), self.height()
        bw = 5
        left = x <= bw
        right = x >= w - bw
        top = y <= bw
        bottom = y >= h - bw
        if top and left:
            return 'topleft'
        if top and right:
            return 'topright'
        if bottom and left:
            return 'bottomleft'
        if bottom and right:
            return 'bottomright'
        if left:
            return 'left'
        if right:
            return 'right'
        if top:
            return 'top'
        if bottom:
            return 'bottom'
        return None

    def _update_cursor_shape(self, pos):
        d = self._hit_test(pos)
        if d in ('left', 'right'):
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        elif d in ('top', 'bottom'):
            self.setCursor(Qt.CursorShape.SizeVerCursor)
        elif d in ('topleft', 'bottomright'):
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif d in ('topright', 'bottomleft'):
            self.setCursor(Qt.CursorShape.SizeBDiagCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def show_toggle(self):
        if self.isMinimized():
            self.showNormal()
            return
        if getattr(self, "_is_maximized", False):
            self._is_maximized = False
            self.showNormal()
            self.setGeometry(self._normal_geometry)
        else:
            self._normal_geometry = self.geometry()
            self._is_maximized = True
            avail = QApplication.primaryScreen().availableGeometry()
            self.setGeometry(avail)

    def apply_blur(self, enable: bool):
        try:
            if enable:
                self.overlay.setGeometry(0, 0, self.width(), self.height())
                self.overlay.show()
                self.overlay.raise_()
            else:
                self.overlay.hide()
        except (Exception, ValueError) as e:
            print(f"[MainApp.apply_blur error]: {e}")
            if hasattr(self, 'overlay'):
                self.overlay.hide()

    def change_theme(self, ans: int):
        if ans == 2:
            thm = DARK
        else:
            thm = LIGHT
        self.settings.patch(key=THEME, value=thm)
        self.config: dict = self.settings.load()
        self.style_name: str = self.config.get(THEME, LIGHT)
        self.style_: str = get_styles(style_name=self.style_name)

        self.title_widget.change_style(style_name=self.style_name)
        self.settings_widget.change_style(style_name=self.style_name)
        self.history_widget.change_style(style_name=self.style_name)
        self.left_widget.change_style(style_name=self.style_name)
        self.right_widget.change_style(style_name=self.style_name)
        self.hor_left_widget.change_style(style_name=self.style_name)
        self.hor_right_widget.change_style(style_name=self.style_name)
        self.table.change_style(style_name=self.style_name)
        self.status_widget.change_style(style_name=self.style_name)
        self.setStyleSheet(self.style_)
        self.main_widget.setStyleSheet(self.style_)
        self.tab_widget.setStyleSheet(self.style_)
        self.cam_widget.setStyleSheet(self.style_)

    @staticmethod
    def time_format(tm: int) -> str:
        return f"{tm // 3600:02}:{(tm % 3600) // 60:02}:{tm % 60:02}"

    def ask_password_window(self):
        try:
            self.apply_blur(enable=True)
            self.password_dialog: PasswordDialog = PasswordDialog(
                style_name=self.style_name
            )

            self.password_dialog.enter_btn.clicked.connect(
                lambda: self.check_password(
                    txt=self.password_dialog.password.edit.text().strip()
                )
            )
            self.password_dialog.password.edit.returnPressed.connect(
                lambda: self.check_password(
                    txt=self.password_dialog.password.edit.text().strip()
                )
            )
            self.password_dialog.back_btn.clicked.connect(self.password_dialog.close)
            self.password_dialog.closeEvent = self.password_dialog_close
            self.password_dialog.exec()
        except (Exception, ValueError) as err:
            print(f"[MainApp.ask_password_window] {err}")
            log(message=f"[MainApp.ask_password_window] {err}")

    def password_dialog_close(self, a0: QCloseEvent):
        if self.password_dialog.force_close:
            if self.password_dialog.isVisible():
                self.apply_blur(enable=False)
            a0.accept()
        else:
            a0.ignore()

    def check_password(self, txt: str):
        try:
            if txt == static_password:
                self.password_dialog.force_close = True
                self.password_dialog.close()
                self.apply_blur(enable=False)
                self.special_settings_dialog: SpecialSettingsDialog = SpecialSettingsDialog(
                    style_name=self.style_name
                )
                self.apply_blur(enable=True)
                self.special_settings_dialog.closeEvent = self.close_hidden_settings_window
                self.special_settings_dialog.d_r_conf.col1.edit.setText(str(self.config.get(D_CONF, default_det_conf)))
                self.special_settings_dialog.d_r_conf.col2.edit.setText(str(self.config.get(R_CONF, default_rec_conf)))
                self.special_settings_dialog.urls.col1.edit.setText(str(self.config.get(LOGIN_URL, get_token_url)))
                self.special_settings_dialog.urls.col2.edit.setText(str(self.config.get(UPLOAD_URL, post_url)))
                self.special_settings_dialog.scale_view.hidden_switch.setChecked(self.config.get(SCALE_VIEW, False))
                self.special_settings_dialog.btn_disable.hidden_switch.setChecked(self.config.get(BTN_DISABLE, True))
                self.special_settings_dialog.scale_disable.hidden_switch.setChecked(self.config.get(SCALE_DISABLE, False))
                self.special_settings_dialog.login_widget.edit.setText(str(self.config.get(USERNAME, default_username)))
                self.special_settings_dialog.password_widget.edit.setText(str(self.config.get(PASSWORD, default_password)))
                self.special_settings_dialog.back_btn.clicked.connect(self.special_settings_dialog.close)
                self.special_settings_dialog.password_widget.password_toggle_btn.clicked.connect(self.toggle_password_edit)

                self.special_settings_dialog.login_widget.edit.setDisabled(False)
                self.special_settings_dialog.password_widget.edit.setDisabled(False)

                if self.last_login_status:
                    self.special_settings_dialog.login_widget.lbl.setText("Login ✅")
                    self.special_settings_dialog.password_widget.lbl.setText("Parol ✅")
                else:
                    self.special_settings_dialog.login_widget.lbl.setText("Login ❌")
                    self.special_settings_dialog.password_widget.lbl.setText("Parol ❌")

                self.special_settings_dialog.save_btn.clicked.connect(
                    lambda: self.save_special_settings(
                        data={
                            BTN_DISABLE: self.special_settings_dialog.btn_disable.hidden_switch.isChecked(),
                            SCALE_VIEW: self.special_settings_dialog.scale_view.hidden_switch.isChecked(),
                            SCALE_DISABLE: self.special_settings_dialog.scale_disable.hidden_switch.isChecked(),
                            LOGIN_URL: self.special_settings_dialog.urls.col1.edit.text().strip(),
                            UPLOAD_URL: self.special_settings_dialog.urls.col2.edit.text().strip(),
                            D_CONF: self.special_settings_dialog.d_r_conf.col1.edit.text().strip(),
                            R_CONF: self.special_settings_dialog.d_r_conf.col2.edit.text().strip(),
                            USERNAME: self.special_settings_dialog.login_widget.edit.text().strip(),
                            PASSWORD: self.special_settings_dialog.password_widget.edit.text().strip(),
                        }
                    )
                )
                self.special_settings_dialog.exec()
            else:
                self.password_dialog.force_close = False
                QTimer.singleShot(1_000, self.restore_state)
                self.password_dialog.password.edit.setObjectName("wrong_password")
                self.password_dialog.password.edit.setStyleSheet(self.style_)
                QTimer.singleShot(2_000, self.clear_style)

        except (Exception, ValueError) as err:
            print(f"[MainApp.check_password] {err}")
            log(message=f"[MainApp.check_password] {err}")
            show_message(
                stl=self.style_name,
                title="Xatolik",
                message=f"[MainApp.check_password] {err}"
            )

    def restore_state(self):
        self.password_dialog.force_close = True

    def clear_style(self):
        self.password_dialog.password.edit.setObjectName("hidden1_settings_edit")
        self.password_dialog.password.edit.setStyleSheet(self.style_)

    def insert_data(self):
        try:
            self.history_widget.load_history()
        except (Exception, ValueError) as err:
            print(f"[MainApp.insert_data] {err}")
            log(message=f"[MainApp.insert_data] {err}")

    def insert_histories(self):
        self.insert_data()

    def change_auto(self, ans: int):
        if isinstance(self.video_thread_left, VideoThread | AutoVideoThread):
            if self.video_thread_left.running:
                show_message(
                    stl=self.style_name,
                    title="Xabar",
                    message=f"Avval videoni to'xtating [Chap]"
                )
                self.left_widget.switch.start_transition(2 if self.config.get(AUTO, False) else 0)
                return
        if isinstance(self.video_thread_right, VideoThread | AutoVideoThread):
            if self.video_thread_right.running:
                show_message(
                    stl=self.style_name,
                    title="Xabar",
                    message=f"Avval videoni to'xtating [O'ng]"
                )
                self.right_widget.switch.start_transition(2 if self.config.get(AUTO, False) else 0)
                return
        if ans == 2:
            auto: bool = True
            self.left_widget.frame_lbl.btn.setDisabled(True)
            self.right_widget.frame_lbl.btn.setDisabled(True)
        else:
            auto: bool = False
            self.left_widget.frame_lbl.btn.setDisabled(False)
            self.right_widget.frame_lbl.btn.setDisabled(False)
        self.settings.patch(key=AUTO, value=auto)
        self.config: dict = self.settings.load()

    def stop_timeout(self):
        if self.is_timeout:
            self.send_current_time = timer_back(self.send_current_time)
            if self.send_current_time == "00:00:00":
                self.send_current_time = self.send_time
                self.is_timeout: bool = False
            self.hor_right_widget.right_lbl.setText(self.send_current_time)

    def check_server_connection(self, ans: bool):
        ttl = self.backup_db.get_total()
        self.last_ttl = ttl
        self.status_widget.archive_count_lbl.setText(str(ttl))
        if ans:
            if ttl > 0:
                self.upload_backup_data()

    def upload_backup_data(self):
        self.left_widget.frame_lbl.btn.setDisabled(True)
        self.right_widget.frame_lbl.btn.setDisabled(True)
        self.backup_thread: BackupUploadThread = BackupUploadThread(
            bs_url=self.config.get(UPLOAD_URL, post_url),
            login_data={
                "login": self.config.get(USERNAME, default_username),
                "password": self.config.get(PASSWORD, default_password)
            }
        )
        self.backup_thread.upload_signal.connect(self.backup_upload_response)
        self.backup_thread.error_signal.connect(self.backup_upload_error)
        self.backup_thread.start()

    def settings_window_left(self, event: QMouseEvent):
        if (
                event.button() == Qt.MouseButton.MiddleButton and event.modifiers() & Qt.KeyboardModifier.ControlModifier and
                event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
            if self.video_thread_left is not None:
                if self.video_thread_left.running:
                    show_message(
                        stl=self.style_name,
                        title="Xabar",
                        message="Avval videoni to'xtating [Chap]"
                    )
                    return

            self.apply_blur(enable=True)
            self.hidden_settings_widget: HiddenSettingsWidget = HiddenSettingsWidget(
                style_name=self.style_name,
            )

            int50_validator: QRegularExpressionValidator = make_range_validator(
                a=min_side,
                b=max_side,
            )
            int100_validator: QRegularExpressionValidator = make_range_validator(
                a=min_frame_count,
                b=max_frame_count,
            )
            int20_validator: QRegularExpressionValidator = make_range_validator(
                a=min_distance,
                b=max_distance,
            )

            det_validator: QDoubleValidator = QDoubleValidator(min_det_conf, max_det_conf, 2, self)
            det_validator.setNotation(QDoubleValidator.Notation.StandardNotation)
            det_validator.setLocale(QLocale(QLocale.Language.English))

            rec_validator: QDoubleValidator = QDoubleValidator(min_rec_conf, max_rec_conf, 2, self)
            rec_validator.setNotation(QDoubleValidator.Notation.StandardNotation)
            rec_validator.setLocale(QLocale(QLocale.Language.English))

            self.hidden_settings_widget.top_bottom.col1.edit.setValidator(int50_validator)
            self.hidden_settings_widget.top_bottom.col2.edit.setValidator(int50_validator)
            self.hidden_settings_widget.left_right.col1.edit.setValidator(int50_validator)
            self.hidden_settings_widget.left_right.col2.edit.setValidator(int50_validator)

            self.hidden_settings_widget.top_bottom.col1.edit.setText(str(self.top_1))
            self.hidden_settings_widget.top_bottom.col2.edit.setText(str(self.bottom_1))
            self.hidden_settings_widget.left_right.col1.edit.setText(str(self.left_1))
            self.hidden_settings_widget.left_right.col2.edit.setText(str(self.right_1))

            self.hidden_settings_widget.frame_count_distance.col1.edit.setValidator(int100_validator)
            self.hidden_settings_widget.frame_count_distance.col2.edit.setValidator(int20_validator)

            self.hidden_settings_widget.frame_count_distance.col1.edit.setText(str(self.max_frame_count_1))
            self.hidden_settings_widget.frame_count_distance.col2.edit.setText(str(self.distance_1))

            self.hidden_settings_widget.fps_.hidden_switch.setChecked(self.fps_view_1)
            if half_available:
                self.hidden_settings_widget.half.hidden_switch.setChecked(self.is_half_1)
            else:
                self.hidden_settings_widget.half.hidden_switch.setChecked(False)
                self.hidden_settings_widget.half.hidden_switch.setDisabled(True)
                self.hidden_settings_widget.half.edit.setText(
                    f"Aniqlikni kuchaytirish mavjud emas \n({get_gpu_name()})")
            self.hidden_settings_widget.line.hidden_switch.setChecked(self.is_line_1)
            self.hidden_settings_widget.closeEvent = self.close_hidden_settings_window

            def get_data() -> SavingData:
                dt = SavingData()
                dt.top = int(self.hidden_settings_widget.top_bottom.col1.edit.text().strip())
                dt.left = int(self.hidden_settings_widget.left_right.col1.edit.text().strip())
                dt.right = int(self.hidden_settings_widget.left_right.col2.edit.text().strip())
                dt.bottom = int(self.hidden_settings_widget.top_bottom.col2.edit.text().strip())
                dt.max_frame = int(self.hidden_settings_widget.frame_count_distance.col1.edit.text().strip())
                dt.dist = int(self.hidden_settings_widget.frame_count_distance.col2.edit.text().strip())
                dt.is_fps = self.hidden_settings_widget.fps_.hidden_switch.isChecked()
                dt.is_line = self.hidden_settings_widget.line.hidden_switch.isChecked()
                dt.hf = self.hidden_settings_widget.half.hidden_switch.isChecked()
                return dt

            self.hidden_settings_widget.back_btn.clicked.connect(lambda: self.hidden_settings_widget.close())
            self.hidden_settings_widget.save_btn.clicked.connect(
                lambda: self.save_data_left(
                    data=get_data(), modal=self.hidden_settings_widget
                )
            )
            self.hidden_settings_widget.exec()

    def settings_window_right(self, event: QMouseEvent):
        if (
                event.button() == Qt.MouseButton.MiddleButton and event.modifiers() & Qt.KeyboardModifier.ControlModifier and
                event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
            if self.video_thread_right is not None:
                if self.video_thread_right.running:
                    show_message(
                        stl=self.style_name,
                        title="Xabar",
                        message="Avval videoni to'xtating [O'ng]"
                    )
                    return

            self.apply_blur(enable=True)
            self.hidden_settings_widget: HiddenSettingsWidget = HiddenSettingsWidget(
                style_name=self.style_name,
            )

            int50_validator: QRegularExpressionValidator = make_range_validator(
                a=min_side,
                b=max_side,
            )
            int100_validator: QRegularExpressionValidator = make_range_validator(
                a=min_frame_count,
                b=max_frame_count,
            )
            int20_validator: QRegularExpressionValidator = make_range_validator(
                a=min_distance,
                b=max_distance,
            )

            det_validator: QDoubleValidator = QDoubleValidator(min_det_conf, max_det_conf, 2, self)
            det_validator.setNotation(QDoubleValidator.Notation.StandardNotation)
            det_validator.setLocale(QLocale(QLocale.Language.English))

            rec_validator: QDoubleValidator = QDoubleValidator(min_rec_conf, max_rec_conf, 2, self)
            rec_validator.setNotation(QDoubleValidator.Notation.StandardNotation)
            rec_validator.setLocale(QLocale(QLocale.Language.English))

            self.hidden_settings_widget.top_bottom.col1.edit.setValidator(int50_validator)
            self.hidden_settings_widget.top_bottom.col2.edit.setValidator(int50_validator)
            self.hidden_settings_widget.left_right.col1.edit.setValidator(int50_validator)
            self.hidden_settings_widget.left_right.col2.edit.setValidator(int50_validator)

            self.hidden_settings_widget.top_bottom.col1.edit.setText(str(self.top_2))
            self.hidden_settings_widget.top_bottom.col2.edit.setText(str(self.bottom_2))
            self.hidden_settings_widget.left_right.col1.edit.setText(str(self.left_2))
            self.hidden_settings_widget.left_right.col2.edit.setText(str(self.right_2))

            self.hidden_settings_widget.frame_count_distance.col1.edit.setValidator(int100_validator)
            self.hidden_settings_widget.frame_count_distance.col2.edit.setValidator(int20_validator)

            self.hidden_settings_widget.frame_count_distance.col1.edit.setText(str(self.max_frame_count_2))
            self.hidden_settings_widget.frame_count_distance.col2.edit.setText(str(self.distance_2))

            self.hidden_settings_widget.fps_.hidden_switch.setChecked(self.fps_view_2)
            if half_available:
                self.hidden_settings_widget.half.hidden_switch.setChecked(self.is_half_2)
            else:
                self.hidden_settings_widget.half.hidden_switch.setChecked(False)
                self.hidden_settings_widget.half.hidden_switch.setDisabled(True)
                self.hidden_settings_widget.half.edit.setText(
                    f"Aniqlikni kuchaytirish mavjud emas \n({get_gpu_name()})")
            self.hidden_settings_widget.line.hidden_switch.setChecked(self.is_line_2)
            self.hidden_settings_widget.closeEvent = self.close_hidden_settings_window

            def get_data() -> SavingData:
                dt = SavingData()
                dt.top = int(self.hidden_settings_widget.top_bottom.col1.edit.text().strip())
                dt.left = int(self.hidden_settings_widget.left_right.col1.edit.text().strip())
                dt.right = int(self.hidden_settings_widget.left_right.col2.edit.text().strip())
                dt.bottom = int(self.hidden_settings_widget.top_bottom.col2.edit.text().strip())
                dt.max_frame = int(self.hidden_settings_widget.frame_count_distance.col1.edit.text().strip())
                dt.dist = int(self.hidden_settings_widget.frame_count_distance.col2.edit.text().strip())
                dt.is_fps = self.hidden_settings_widget.fps_.hidden_switch.isChecked()
                dt.is_line = self.hidden_settings_widget.line.hidden_switch.isChecked()
                dt.hf = self.hidden_settings_widget.half.hidden_switch.isChecked()
                return dt

            self.hidden_settings_widget.back_btn.clicked.connect(lambda: self.hidden_settings_widget.close())
            self.hidden_settings_widget.save_btn.clicked.connect(
                lambda: self.save_data_right(
                    data=get_data(),
                    modal=self.hidden_settings_widget
                )
            )
            self.hidden_settings_widget.exec()

    def close_hidden_settings_window(self, a0: QCloseEvent):
        self.apply_blur(enable=False)
        a0.accept()

    def save_data_left(self, data: SavingData, modal: QDialog):
        top = data.top
        left = data.left
        right = data.right
        bottom = data.bottom
        max_frame = data.max_frame
        dist = data.dist
        is_fps = data.is_fps
        is_line = data.is_line
        hf = data.hf

        self.is_line_1: bool = is_line
        cipher.write(
            file_path="settings/line_1.bin",
            data=[str(int(self.is_line_1))]
        )
        self.fps_view_1: bool = is_fps
        cipher.write(
            file_path="settings/fps_1.bin",
            data=[str(int(self.fps_view_1))]
        )
        self.is_half_1: bool = hf
        cipher.write(
            file_path="settings/half_1.bin",
            data=[str(int(self.is_half_1))]
        )

        if max_frame != "":
            max_frame = int(max_frame)
            if min_frame_count <= max_frame <= max_frame_count:
                self.max_frame_count_1: int = max_frame
                cipher.write(
                    file_path="settings/frame_count_1.bin",
                    data=[str(self.max_frame_count_1)]
                )

        if dist != "":
            dist = int(dist)
            if min_distance <= dist <= max_distance:
                self.distance_1: int = dist
                cipher.write(
                    file_path="settings/distance_1.bin",
                    data=[str(self.distance_1)]
                )

        if top != "":
            top = int(top)
            if min_side <= top <= max_side:
                self.top_1: int = top
                cipher.write(
                    file_path="settings/top_1.bin",
                    data=[str(self.top_1)]
                )

        if bottom != "":
            bottom = int(bottom)
            if min_side <= bottom <= max_side:
                self.bottom_1: int = bottom
                cipher.write(
                    file_path="settings/bottom_1.bin",
                    data=[str(self.bottom_1)]
                )

        if left != "":
            left = int(left)
            if min_side <= left <= max_side:
                self.left_1: int = left
                cipher.write(
                    file_path="settings/left_1.bin",
                    data=[str(self.left_1)]
                )

        if right != "":
            right = int(right)
            if min_side <= right <= max_side:
                self.right_1: int = right
                cipher.write(
                    file_path="settings/right_1.bin",
                    data=[str(self.right_1)]
                )
        self.config: dict = self.settings.load()
        modal.close()

    def save_data_right(self, data: SavingData, modal: QDialog):
        top = data.top
        left = data.left
        right = data.right
        bottom = data.bottom
        max_frame = data.max_frame
        dist = data.dist
        is_fps = data.is_fps
        is_line = data.is_line
        hf = data.hf

        self.is_line_2: bool = is_line
        cipher.write(
            file_path="settings/line_2.bin",
            data=[str(int(self.is_line_2))]
        )
        self.fps_view_2: bool = is_fps
        cipher.write(
            file_path="settings/fps_2.bin",
            data=[str(int(self.fps_view_2))]
        )
        self.is_half_2: bool = hf
        cipher.write(
            file_path="settings/half_2.bin",
            data=[str(int(self.is_half_2))]
        )

        if max_frame != "":
            max_frame = int(max_frame)
            if min_frame_count <= max_frame <= max_frame_count:
                self.max_frame_count_2: int = max_frame
                cipher.write(
                    file_path="settings/frame_count_2.bin",
                    data=[str(self.max_frame_count_2)]
                )

        if dist != "":
            dist = int(dist)
            if min_distance <= dist <= max_distance:
                self.distance_2: int = dist
                cipher.write(
                    file_path="settings/distance_2.bin",
                    data=[str(self.distance_2)]
                )

        if top != "":
            top = int(top)
            if min_side <= top <= max_side:
                self.top_2: int = top
                cipher.write(
                    file_path="settings/top_2.bin",
                    data=[str(self.top_2)]
                )

        if right != "":
            right = int(right)
            if min_side <= right <= max_side:
                self.right_2: int = right
                cipher.write(
                    file_path="settings/right_2.bin",
                    data=[str(self.right_2)]
                )

        if left != "":
            left = int(left)
            if min_side <= left <= max_side:
                self.left_2: int = left
                cipher.write(
                    file_path="settings/left_2.bin",
                    data=[str(self.left_2)]
                )

        if bottom != "":
            bottom = int(bottom)
            if min_side <= bottom <= max_side:
                self.bottom_2: int = bottom
                cipher.write(
                    file_path="settings/bottom_2.bin",
                    data=[str(self.bottom_2)]
                )
        self.config: dict = self.settings.load()
        modal.close()

    def toggle_password_edit(self):
        if isinstance(self.special_settings_dialog, SpecialSettingsDialog):
            if self.special_settings_dialog.password_widget.edit.echoMode() == QLineEdit.EchoMode.Password:
                self.special_settings_dialog.password_widget.edit.setEchoMode(QLineEdit.EchoMode.Normal)
                if self.style_name == DARK:
                    self.special_settings_dialog.password_widget.password_toggle_btn.setIcon(unview_icon_light)
                else:
                    self.special_settings_dialog.password_widget.password_toggle_btn.setIcon(unview_icon)
            else:
                self.special_settings_dialog.password_widget.edit.setEchoMode(QLineEdit.EchoMode.Password)
                if self.style_name == DARK:
                    self.special_settings_dialog.password_widget.password_toggle_btn.setIcon(view_icon_light)
                else:
                    self.special_settings_dialog.password_widget.password_toggle_btn.setIcon(view_icon)

    def fake_progressbar(self, val: int):
        try:
            self.progressbar.progress.setValue(val)
        except (Exception, ValueError) as err:
            log(message=f"[MainApp.fake_progressbar] {err}")

    def save_special_settings(self, data: dict):
        try:
            d_cnf = data.get(D_CONF, default_det_conf)
            r_cnf = data.get(R_CONF, default_rec_conf)

            if data.get(USERNAME, default_username) != "":
                self.settings.patch(key=USERNAME, value=data.get(USERNAME, default_username))
                self.config: dict = self.settings.load()

            if data.get(PASSWORD, default_password) != "":
                self.settings.patch(key=PASSWORD, value=data.get(PASSWORD, default_password))
                self.config: dict = self.settings.load()

            if data.get(LOGIN_URL, get_token_url) != "":
                self.settings.patch(key=LOGIN_URL, value=data.get(LOGIN_URL, get_token_url))
                self.config: dict = self.settings.load()

            if data.get(UPLOAD_URL, post_url) != "":
                self.settings.patch(key=UPLOAD_URL, value=data.get(UPLOAD_URL, post_url))
                self.config: dict = self.settings.load()

            if data.get(USERNAME, default_username) != "" and data.get(PASSWORD, default_password) != "":
                self.login_thread.stop()
                self.login_thread.wait(1000)
                self.login_thread: LoginThread = LoginThread(
                    login_url=self.config.get(LOGIN_URL, get_token_url),
                    data={
                        "login": self.config.get(USERNAME, default_username),
                        "password": self.config.get(PASSWORD, default_password)
                    }
                )
                self.login_thread.login_signal.connect(self.login_response)
                self.login_thread.start()
                self.server_connection_thread.base_url = get_base_url(url=self.config.get(LOGIN_URL, get_token_url))

            if r_cnf != "":
                r_cnf = float(r_cnf)
                if min_rec_conf <= r_cnf <= max_rec_conf:
                    self.settings.patch(key=R_CONF, value=r_cnf)

            if d_cnf != "":
                d_cnf = float(d_cnf)
                if min_det_conf <= d_cnf <= max_det_conf:
                    self.settings.patch(key=D_CONF, value=d_cnf)

            self.settings.patch(key=BASE_URL, value=get_base_url(url=data.get(LOGIN_URL, get_token_url)))
            self.settings.patch(key=BTN_DISABLE, value=data.get(BTN_DISABLE, True))
            self.settings.patch(key=SCALE_VIEW, value=data.get(SCALE_VIEW, False))
            self.settings.patch(key=SCALE_DISABLE, value=data.get(SCALE_DISABLE, False))
            self.config: dict = self.settings.load()
            self.special_settings_dialog.close()
        except (Exception, ValueError) as err:
            show_message(
                stl=self.style_name,
                title="Xatolik",
                message=f"[MainApp.save_special_settings] {err}"
            )
            log(message=f"[MainApp.save_special_settings] {err}")

    def save_settings(self):
        self.settings_widget.save_btn.setDisabled(True)
        self.save_send_time()
        self.save_station_code()
        self.save_scale_code()
        if self.video_thread_left is None:
            self.save_cam_url_left()
        else:
            if self.video_thread_left.running:
                show_message(
                    stl=self.style_name,
                    message="Saqlashdan avval videoni to'xtating. [Chap]"
                )
            else:
                self.save_cam_url_left()
        if self.video_thread_right is None:
            self.save_cam_url_right()
        else:
            if self.video_thread_right.running:
                show_message(
                    stl=self.style_name,
                    message="Saqlashdan avval videoni to'xtating. [O'ng]"
                )
            else:
                self.save_cam_url_right()

        self.settings_widget.save_btn.setDisabled(False)

    def login_response(self, ans: bool, data: dict):
        self.last_login_status: bool = ans
        if ans:
            self.status_widget.status_btn.setIcon(success_icon)
            if isinstance(self.special_settings_dialog, SpecialSettingsDialog):
                self.special_settings_dialog.login_widget.edit.setDisabled(True)
                self.special_settings_dialog.password_widget.edit.setDisabled(True)
                self.special_settings_dialog.password_widget.edit.setEchoMode(QLineEdit.EchoMode.Password)
                if self.style_name == DARK:
                    self.special_settings_dialog.password_widget.password_toggle_btn.setIcon(unview_icon_light)
                else:
                    self.special_settings_dialog.password_widget.password_toggle_btn.setIcon(unview_icon)
                self.special_settings_dialog.login_widget.lbl.setText("Login ✅")
                self.special_settings_dialog.password_widget.lbl.setText("Parol ✅")
        else:
            self.status_widget.status_btn.setIcon(fail_icon)
            if isinstance(self.special_settings_dialog, SpecialSettingsDialog):
                self.special_settings_dialog.login_widget.edit.setDisabled(False)
                self.special_settings_dialog.password_widget.edit.setDisabled(False)
                self.special_settings_dialog.login_widget.lbl.setText("Login ❌")
                self.special_settings_dialog.password_widget.lbl.setText("Parol ❌")
            show_message(
                stl=self.style_name,
                message=f"Login qilib bo'lmadi. \n{data}"
            )
        self.settings_widget.save_btn.setDisabled(False)

    def save_send_time(self):
        if self.settings_widget.send_time_widget.edit.text().strip() != "":
            if int(self.settings_widget.send_time_widget.edit.text().strip()) > 0:
                send_second: int = int(self.settings_widget.send_time_widget.edit.text().strip())
                self.settings.patch(key=SEND_TIME, value=send_second)
                self.config: dict = self.settings.load()
                log(message=f"Save Send Time: {send_second}", level="INFO")
                self.send_time = self.time_format(tm=send_second)
                self.send_current_time = self.send_time
                self.settings_widget.send_time_widget.edit.setText(str(self.config.get(SEND_TIME, default_send_time)))
                self.hor_right_widget.right_lbl.setText(self.send_current_time)

    def save_station_code(self):
        if self.settings_widget.station_code_widget.edit.text().strip() != "":
            station_code: str = self.settings_widget.station_code_widget.edit.text().strip()
            self.settings.patch(key=STATION_CODE, value=station_code)
            self.config: dict = self.settings.load()
            log(message=f"Save Station Code: {station_code}", level="INFO")

    def save_scale_code(self):
        if self.settings_widget.scale_code_widget.edit.text().strip() != "":
            scale_code: str = self.settings_widget.scale_code_widget.edit.text().strip()
            self.settings.patch(key=SCALE_CODE, value=scale_code)
            self.config: dict = self.settings.load()
            log(message=f"Save Scale Code: {scale_code}", level="INFO")

    def save_cam_url_left(self):
        if self.settings_widget.left_cam_widget.edit.text().strip() != "":
            txt: str = self.settings_widget.left_cam_widget.edit.text().strip()
            if os.path.isfile(txt):
                self.save_response_left(True)
            elif txt.startswith("rtsp://"):
                self.settings_widget.save_btn.setDisabled(True)
                self.settings_widget.left_cam_widget.edit.setDisabled(True)
                self.save_thread_left: SaveThread = SaveThread(url=txt)
                self.save_thread_left.save_signal.connect(self.save_response_left)
                self.save_thread_left.start()
            else:
                self.settings_widget.left_cam_widget.edit.setText(self.cam_url_1)

    def save_cam_url_right(self):
        if self.settings_widget.right_cam_widget.edit.text().strip() != "":
            txt: str = self.settings_widget.right_cam_widget.edit.text().strip()
            if os.path.isfile(txt):
                self.save_response_right(True)
            elif txt.startswith("rtsp://"):
                self.settings_widget.save_btn.setDisabled(True)
                self.settings_widget.right_cam_widget.edit.setDisabled(True)
                self.save_thread_right: SaveThread = SaveThread(url=txt)
                self.save_thread_right.save_signal.connect(self.save_response_right)
                self.save_thread_right.start()
            else:
                self.settings_widget.right_cam_widget.edit.setText(self.cam_url_2)

    def save_response_left(self, ans: bool):
        if ans:
            self.settings_widget.left_cam_widget.lbl.setText("Chap Kamera ✅")
            self.cam_url_1: str = self.settings_widget.left_cam_widget.edit.text().strip()
            log(message=f"[Chap] Save Camera URL: {self.cam_url_1}", level="INFO")
            cipher.write(file_path="settings/cam_1.bin", data=[self.cam_url_1])
            self.left_widget.switch.setDisabled(False)
            if self.video_thread_left is None:
                self.left_widget.switch.setChecked(True)
                self.left_widget.switch.start_transition(2)
            else:
                if not self.video_thread_left.running:
                    self.left_widget.switch.setChecked(True)
                    self.left_widget.switch.start_transition(2)
                else:
                    show_message(
                        stl=self.style_name,
                        title="Xabar",
                        message="Saqlashdan avval videoni to'xtating. [Chap]"
                    )
        else:
            self.settings_widget.left_cam_widget.lbl.setText("Chap Kamera ❌")
            show_message(
                stl=self.style_name,
                title="Xabar",
                message="Kamera bilan aloqa yo'q. [Chap]"
            )
            self.left_widget.switch.setDisabled(btn_disabled)
        self.settings_widget.left_cam_widget.edit.setDisabled(False)
        self.settings_widget.save_btn.setDisabled(False)

    def save_response_right(self, ans: bool):
        if ans:
            self.settings_widget.right_cam_widget.lbl.setText("O'ng Kamera ✅")
            self.cam_url_2: str = self.settings_widget.right_cam_widget.edit.text().strip()
            log(message=f"[O'ng] Save Camera URL: {self.cam_url_2}", level="INFO")
            cipher.write(file_path="settings/cam_2.bin", data=[self.cam_url_2])
            self.right_widget.switch.setDisabled(False)
            if self.video_thread_right is None:
                self.right_widget.switch.setChecked(True)
                self.right_widget.switch.start_transition(2)
            else:
                if not self.video_thread_right.running:
                    self.right_widget.switch.setChecked(True)
                    self.right_widget.switch.start_transition(2)
                else:
                    show_message(
                        stl=self.style_name,
                        title="Xabar",
                        message="Saqlashdan avval videoni to'xtating. [O'ng]"
                    )
        else:
            self.settings_widget.right_cam_widget.lbl.setText("O'ng Kamera ❌")
            show_message(
                stl=self.style_name,
                title="Xabar",
                message="Kamera bilan aloqa yo'q. [O'ng]"
            )
            self.right_widget.switch.setDisabled(btn_disabled)
        self.settings_widget.right_cam_widget.edit.setDisabled(False)
        self.settings_widget.save_btn.setDisabled(False)

    def enable_left_switch(self):
        self.left_widget.switch.setDisabled(False)

    def enable_right_switch(self):
        self.right_widget.switch.setDisabled(False)

    def start_video_left(self):
        try:
            self.running_left = not self.running_left
            self.left_widget.switch.setDisabled(True)
            if self.running_left:
                self.settings_widget.auto_switch.setDisabled(True)
                if demo_video:
                    self.cam_url_1 = "video_3.mp4"
                if self.config.get(AUTO, False):
                    self.video_thread_left = AutoVideoThread(
                        data={
                            CAM_URL: self.cam_url_1,
                            LINE: self.is_line_1,
                            HALF: self.is_half_1,
                            FPS: self.fps_view_1,
                            D_CONF: self.config.get(D_CONF, default_det_conf),
                            R_CONF: self.config.get(R_CONF, default_rec_conf),
                            DISTANCE: self.distance_1,
                            MAX_FRAME: self.max_frame_count_1,
                            TOP: self.top_1,
                            BOTTOM: self.bottom_1,
                            LEFT: self.left_1,
                            RIGHT: self.right_1,
                        }
                    )
                    self.video_thread_left.image_signal.connect(self.update_frame_left)
                    self.video_thread_left.data_signal.connect(self.get_auto_data_left)
                    self.video_thread_left.error_signal.connect(self.get_error_message_left)
                    self.video_thread_left.disconnected_signal.connect(self.disconnected_left)
                    self.video_thread_left.start()
                else:
                    self.video_thread_left = VideoThread(
                        cam_url=self.cam_url_1,
                        lined=self.is_line_1,
                        fps=self.fps_view_1,
                        is_half=self.is_half_1,
                        dist=self.distance_1,
                        r_conf=self.config.get(R_CONF, default_rec_conf),
                        d_conf=self.config.get(D_CONF, default_det_conf),
                        crop=self.crop_1,
                        side={
                            TOP: self.top_1,
                            LEFT: self.left_1,
                            BOTTOM: self.bottom_1,
                            RIGHT: self.right_1,
                        }
                    )
                    self.video_thread_left.image_signal.connect(self.update_frame_left)
                    self.video_thread_left.data_signal.connect(self.get_handle_data_left)
                    self.video_thread_left.error_signal.connect(self.get_error_message_left)
                    self.video_thread_left.disconnected_signal.connect(self.disconnected_left)
                    self.video_thread_left.inner_signal.connect(self.inner_left)
                    self.video_thread_left.start()
                if self.is_line_1:
                    self.left_widget.frame_lbl.set_lines(balloon_rect=(
                        self.top_1,
                        self.left_1,
                        self.bottom_1,
                        self.right_1
                    ))
                if self.fps_view_1:
                    self.video_thread_left.fps_signal.connect(self.update_left_fps)
                    self.left_widget.frame_lbl.toggle_fps(view=True)

                self.left_widget.frame_lbl.btn.setDisabled(True)
                QTimer.singleShot(2500, self.enable_left_switch)
                self.left_widget.state_lbl.setText("Kamera ishlamoqda")
                log(message="[Chap] Video Started", level="INFO")
            else:
                self.sent_left_track_ids.clear()
                self.left_widget.state_lbl.setText("Kamera o'chgan")
                self.left_widget.frame_lbl.number_lbl.clear()
                self.left_widget.frame_lbl.number_image_lbl.clear()
                if self.config.get(AUTO, False):
                    self.left_widget.frame_lbl.btn.setDisabled(True)
                self.left_widget.frame_lbl.clear()
                self.left_widget.frame_lbl.set_txt(txt="")
                self.left_widget.switch.setDisabled(False)

                self.last_image_left = None

                self.left_widget.frame_lbl.set_lines(balloon_rect=(None, None, None, None))
                self.last_data_left: dict = {}
                log(message="[Chap] Video Stopped", level="INFO")

                if self.video_thread_left is not None:
                    if isinstance(self.video_thread_left, VideoThread | AutoVideoThread):
                        self.video_thread_left.stop()

                if self.video_thread_right is not None:
                    if isinstance(self.video_thread_right, VideoThread | AutoVideoThread):
                        if not self.video_thread_right.running:
                            self.settings_widget.auto_switch.setDisabled(False)
                    else:
                        self.settings_widget.auto_switch.setDisabled(False)
                else:
                    self.settings_widget.auto_switch.setDisabled(False)

            if not self.running_left:
                self.left_widget.frame_lbl.toggle_fps(view=False)
        except (Exception, ValueError) as err:
            log(message=f"[MainApp.start_video_left] {err}")
            show_message(
                stl=self.style_name,
                title="Xatolik",
                message=f"[MainApp.start_video_left] {err}"
            )

    def start_video_right(self):
        try:
            self.running_right = not self.running_right
            self.right_widget.switch.setDisabled(True)
            if self.running_right:
                self.settings_widget.auto_switch.setDisabled(True)
                if demo_video:
                    self.cam_url_2 = "video_3.mp4"
                if self.config.get(AUTO, False):
                    self.video_thread_right = AutoVideoThread(
                        data={
                            CAM_URL: self.cam_url_2,
                            LINE: self.is_line_2,
                            HALF: self.is_half_2,
                            FPS: self.fps_view_2,
                            D_CONF: self.config.get(D_CONF, default_det_conf),
                            R_CONF: self.config.get(R_CONF, default_rec_conf),
                            DISTANCE: self.distance_2,
                            MAX_FRAME: self.max_frame_count_2,
                            TOP: self.top_2,
                            BOTTOM: self.bottom_2,
                            LEFT: self.left_2,
                            RIGHT: self.right_2,
                        }
                    )
                    self.video_thread_right.image_signal.connect(self.update_frame_right)
                    self.video_thread_right.data_signal.connect(self.get_auto_data_right)
                    self.video_thread_right.error_signal.connect(self.get_error_message_right)
                    self.video_thread_right.disconnected_signal.connect(self.disconnected_right)
                    self.video_thread_right.start()
                else:
                    self.video_thread_right = VideoThread(
                        cam_url=self.cam_url_2,
                        lined=self.is_line_2,
                        fps=self.fps_view_2,
                        is_half=self.is_half_2,
                        dist=self.distance_2,
                        r_conf=self.config.get(R_CONF, default_rec_conf),
                        d_conf=self.config.get(D_CONF, default_det_conf),
                        crop=self.crop_2,
                        side={
                            TOP: self.top_2,
                            LEFT: self.left_2,
                            BOTTOM: self.bottom_2,
                            RIGHT: self.right_2,
                        }
                    )
                    self.video_thread_right.image_signal.connect(self.update_frame_right)
                    self.video_thread_right.data_signal.connect(self.get_handle_data_right)
                    self.video_thread_right.error_signal.connect(self.get_error_message_right)
                    self.video_thread_right.disconnected_signal.connect(self.disconnected_right)
                    self.video_thread_right.inner_signal.connect(self.inner_right)
                    self.video_thread_right.start()
                if self.fps_view_2:
                    self.video_thread_right.fps_signal.connect(self.update_right_fps)
                    self.right_widget.frame_lbl.toggle_fps(view=True)
                if self.is_line_2:
                    self.right_widget.frame_lbl.set_lines(balloon_rect=(
                        self.top_2,
                        self.left_2,
                        self.bottom_2,
                        self.right_2
                    ))
                self.right_widget.frame_lbl.btn.setDisabled(True)
                QTimer.singleShot(2500, self.enable_right_switch)
                self.right_widget.state_lbl.setText("Kamera ishlamoqda")
                log(message="[O'ng] Video Started", level="INFO")
            else:
                self.sent_right_track_ids.clear()
                self.right_widget.state_lbl.setText("Kamera o'chgan")
                self.right_widget.frame_lbl.number_lbl.clear()
                self.right_widget.frame_lbl.number_image_lbl.clear()
                if self.config.get(AUTO, False):
                    self.right_widget.frame_lbl.btn.setDisabled(True)
                self.right_widget.frame_lbl.clear()
                self.right_widget.frame_lbl.toggle_fps(view=False)
                self.right_widget.frame_lbl.set_txt(txt="")
                self.right_widget.switch.setDisabled(False)
                self.right_widget.frame_lbl.set_lines(balloon_rect=(None, None, None, None))
                self.last_data_right: dict = {}
                log(message="[O'ng] Video Stopped", level="INFO")

                self.last_image_right = None

                if self.video_thread_right is not None:
                    if isinstance(self.video_thread_right, VideoThread):
                        self.video_thread_right.stop()
                if self.video_thread_right is not None:
                    if isinstance(self.video_thread_right, AutoVideoThread):
                        self.video_thread_right.stop()

                if self.video_thread_left is not None:
                    if isinstance(self.video_thread_left, VideoThread):
                        if not self.video_thread_left.running:
                            self.settings_widget.auto_switch.setDisabled(False)
                    elif isinstance(self.video_thread_left, AutoVideoThread):
                        if not self.video_thread_left.running:
                            self.settings_widget.auto_switch.setDisabled(False)
                    else:
                        self.settings_widget.auto_switch.setDisabled(False)
                else:
                    self.settings_widget.auto_switch.setDisabled(False)

            if not self.running_left:
                self.right_widget.frame_lbl.toggle_fps(view=False)
        except (Exception, ValueError) as err:
            log(message=f"[MainApp.start_video_right] {err}")
            show_message(
                stl=self.style_name,
                title="Xatolik",
                message=f"[MainApp.start_video_right] {err}"
            )

    def inner_left(self, ans: bool):
        if self.config.get(BTN_DISABLE, False):
            self.left_widget.frame_lbl.btn.setDisabled(not ans)

    def inner_right(self, ans: bool):
        if self.config.get(BTN_DISABLE, False):
            self.right_widget.frame_lbl.btn.setDisabled(not ans)

    def disconnected_right(self):
        if isinstance(self.video_thread_right, VideoThread):
            self.video_thread_right.stop()
        self.right_widget.state_lbl.setText("Kamera o'chgan")
        self.right_widget.frame_lbl.btn.setDisabled(False)
        self.right_widget.frame_lbl.clear()
        self.running_right: bool = False
        self.last_data_right: dict = {}
        log(message="[O'ng] Video Disconnected", level="WARNING")
        self.right_widget.switch.setChecked(False)
        self.right_widget.switch.start_transition(0)

    def disconnected_left(self):
        if isinstance(self.video_thread_left, VideoThread):
            self.video_thread_left.stop()
        self.left_widget.state_lbl.setText("Kamera o'chgan")
        self.left_widget.frame_lbl.btn.setDisabled(False)
        self.left_widget.frame_lbl.clear()
        self.running_left: bool = False
        self.last_data_left: dict = {}
        log(message="[Chap] Video Disconnected", level="WARNING")
        self.left_widget.switch.setChecked(False)
        self.left_widget.switch.start_transition(0)

    def update_frame_left(self, pixmap: QPixmap):
        if self.running_left:
            self.left_widget.frame_lbl.setPixmap(pixmap)
            self.last_image_left: QPixmap = pixmap

            if not self.config.get(BTN_DISABLE, False):
                self.left_widget.frame_lbl.btn.setDisabled(False)

            if self.config.get(AUTO, False):
                self.left_widget.frame_lbl.btn.setDisabled(True)
                self.wagon_image = qpixmap_to_ndarray(pixmap=pixmap)
        else:
            self.left_widget.frame_lbl.clear()

    def update_frame_right(self, pixmap: QPixmap):
        if self.running_right:
            self.right_widget.frame_lbl.setPixmap(pixmap)
            self.last_image_right: QPixmap = pixmap

            if not self.config.get(BTN_DISABLE, False):
                self.right_widget.frame_lbl.btn.setDisabled(False)

            if self.config.get(AUTO, False):
                self.right_widget.frame_lbl.btn.setDisabled(True)
                self.wagon_image2 = qpixmap_to_ndarray(pixmap=pixmap)
        else:
            self.right_widget.frame_lbl.clear()

    def send_unrec(self):
        if max(self.last_scale_weight) > min_send_kg:
            self.wagon_image = self.get_img_id_left()
            self.wagon_image2 = self.get_img_id_right()
            if self.upload_right:
                self.wagon_id_image = self.get_img_id_number_left()
            else:
                self.wagon_id_image = self.get_img_id_number_right()

            self.sending_data.wagonNumber = identifier * num_count
            self.sending_data.scaleNumber = max(self.last_scale_weight)
            self.sending_data.stationCode = self.config.get(STATION_CODE, default_station_code)
            self.sending_data.scaleCode = self.config.get(SCALE_CODE, default_scale_code)
            self.sending_data.createdDate = current_time()

            self.upload_thread: UploadThread = UploadThread(
                data=self.sending_data,
                img_id=self.wagon_image,
                img_id2=self.wagon_image2,
                img_number=self.wagon_id_image,
                bs_url=self.config.get(BASE_URL, base_url),
                login_data={
                    "login": self.config.get(USERNAME, default_username),
                    "password": self.config.get(PASSWORD, default_password),
                }
            )
            self.upload_thread.message_signal.connect(self.get_upload_response)
            self.upload_thread.progress_signal.connect(self.fake_progressbar)
            self.upload_thread.start()
            self.upload_right: bool = False
            self.upload_left: bool = False

    def get_handle_data_left(self, data: dict):
        if max(self.last_scale_weight) < min_send_kg:
            return
        self.last_data_left[wagonNumber] = data.get(wagonNumber)
        if self.last_data_left[wagonNumber].count(identifier) == 1:
            self.last_data_left[wagonNumber] = fix_luhn_code(code=str(self.last_data_left[wagonNumber]))

        self.last_data_left[wagonAttachId] = data.get(wagonAttachId)
        self.last_data_left[wagonNumberAttachId] = data.get(wagonNumberAttachId)

        self.left_widget.frame_lbl.number_lbl.setText(str(self.last_data_left[wagonNumber]))

        if isinstance(self.last_data_left.get(wagonNumberAttachId), np.ndarray):
            self.left_widget.frame_lbl.number_image_lbl.setPixmap(rounded_pixmap(
                pixmap=cv2_to_qpixmap(
                    cv_img=self.last_data_left.get(wagonNumberAttachId),
                ),
                radius=8,
            ))
        if isinstance(self.last_data_left.get(wagonNumberAttachId), QPixmap):
            self.left_widget.frame_lbl.number_image_lbl.setPixmap(rounded_pixmap(
                pixmap=self.last_data_left.get(wagonNumberAttachId),
                radius=8,
            ))

    def get_handle_data_right(self, data: dict):
        if max(self.last_scale_weight) < min_send_kg:
            return
        self.last_data_right[wagonNumber] = data.get(wagonNumber)

        if self.last_data_right[wagonNumber].count(identifier) == 1:
            self.last_data_right[wagonNumber] = fix_luhn_code(code=str(self.last_data_right[wagonNumber]))

        self.last_data_right[wagonAttachId2] = data.get(wagonAttachId)
        self.last_data_right[wagonNumberAttachId] = data.get(wagonNumberAttachId)

        self.right_widget.frame_lbl.number_lbl.setText(str(self.last_data_right[wagonNumber]))

        if isinstance(self.last_data_right[wagonNumberAttachId], np.ndarray):
            self.right_widget.frame_lbl.number_image_lbl.setPixmap(rounded_pixmap(
                pixmap=cv2_to_qpixmap(
                    cv_img=self.last_data_right.get(wagonNumberAttachId),
                ),
                radius=8,
            ))
        if isinstance(self.last_data_right.get(wagonNumberAttachId), QPixmap):
            self.right_widget.frame_lbl.number_image_lbl.setPixmap(rounded_pixmap(
                pixmap=self.last_data_right.get(wagonNumberAttachId),
                radius=8,
            ))

    def get_auto_data_left(self, data: dict):
        try:
            if self.is_timeout:
                return
            if max(self.last_scale_weight) < min_send_kg:
                return

            track_id: int | None = data.get(t_id)
            wagon_number: str = data.get(wagonNumber)

            if wagon_number is None:
                wagon_number = identifier * num_count
            if track_id is None:
                return
            if track_id in self.sent_left_track_ids:
                return

            if wagon_number.count(identifier) == 1:
                wagon_number = fix_luhn_code(code=wagon_number)

            if wagon_number in self.wagon_ids and wagon_number != identifier * num_count:
                return

            self.sent_left_track_ids.append(track_id)
            self.wagon_id_image = data.get(wagonNumberAttachId)
            self.sending_data.wagonNumber = wagon_number

            self.left_widget.frame_lbl.number_lbl.setText(wagon_number)

            if isinstance(self.wagon_id_image, np.ndarray):
                self.left_widget.frame_lbl.number_image_lbl.setPixmap(rounded_pixmap(
                    pixmap=cv2_to_qpixmap(
                        cv_img=self.wagon_id_image,
                    ),
                    radius=8,
                ))
            if isinstance(self.wagon_id_image, QPixmap):
                self.left_widget.frame_lbl.number_image_lbl.setPixmap(rounded_pixmap(
                    pixmap=self.wagon_id_image,
                    radius=8,
                ))
            self.sent_left_auto: bool = True
            self.send_auto()
        except (Exception, ValueError) as err:
            log(message=f"[MainApp.get_auto_data_left] {err}")
            print(f"[MainApp.get_auto_data_left] {err}")

    def get_auto_data_right(self, data: dict):
        try:
            if self.is_timeout:
                return
            if max(self.last_scale_weight) < min_send_kg:
                return

            track_id: int | None = data.get(t_id)
            wagon_number: str = data.get(wagonNumber)

            if wagon_number is None:
                wagon_number = identifier * num_count
            if track_id is None:
                return
            if track_id in self.sent_right_track_ids:
                return

            if wagon_number.count(identifier) == 1:
                wagon_number = fix_luhn_code(code=wagon_number)

            if wagon_number in self.wagon_ids and wagon_number != identifier * num_count:
                return

            self.sent_right_track_ids.append(track_id)
            self.wagon_id_image = data.get(wagonNumberAttachId)

            self.sending_data.wagonNumber = wagon_number

            self.right_widget.frame_lbl.number_lbl.setText(wagon_number)

            if isinstance(self.wagon_id_image, np.ndarray):
                self.right_widget.frame_lbl.number_image_lbl.setPixmap(rounded_pixmap(
                    pixmap=cv2_to_qpixmap(
                        cv_img=self.wagon_id_image,
                    ),
                    radius=8,
                ))
            if isinstance(self.wagon_id_image, QPixmap):
                self.right_widget.frame_lbl.number_image_lbl.setPixmap(rounded_pixmap(
                    pixmap=self.wagon_id_image,
                    radius=8,
                ))
            self.sent_right_auto: bool = True
            self.send_auto()
        except (Exception, ValueError) as err:
            log(message=f"[MainApp.get_auto_data_right] {err}")
            print(f"[MainApp.get_auto_data_right] {err}")

    def upload_handle_data_left(self):
        if max(self.last_scale_weight) > min_send_kg:
            if self.video_thread_left is not None:
                if self.video_thread_left.running:
                    if self.last_data_left.get(wagonNumber,
                                               identifier * num_count) in self.wagon_ids and identifier not in self.last_data_left.get(
                        wagonNumber, identifier * num_count):
                        ans: int = ask_message(
                            stl=self.style_name,
                            title="Savol",
                            message=f"{self.last_data_left.get(wagonNumber, identifier * num_count)} avval yuborilgan, yana yubormoqchimisiz?"
                        )
                        if ans != QMessageBox.StandardButton.Yes:
                            return
                    self.wagon_ids.append(self.last_data_left.get(wagonNumber, identifier * num_count))
                    self.progressbar: ProgressBar = ProgressBar()
                    self.progressbar.change_style(style_name=self.style_name)
                    self.progressbar.show()
                    self.upload_left: bool = True
                    self.send()
                else:
                    show_message(
                        stl=self.style_name,
                        message="Kamera yoqilmagan"
                    )
            else:
                show_message(
                    stl=self.style_name,
                    message="Kamera yoqilmagan"
                )
        else:
            show_message(
                stl=self.style_name,
                message=f"O'lchash uchun minimal og'irlik {min_send_kg:,} kg"
            )

    def upload_handle_data_right(self):
        if max(self.last_scale_weight) > min_send_kg:
            if self.video_thread_right is not None:
                if self.video_thread_right.running:
                    if self.last_data_right.get(wagonNumber,
                                                identifier * num_count) in self.wagon_ids and identifier not in self.last_data_right.get(
                        wagonNumber, identifier * num_count):
                        ans: int = ask_message(
                            stl=self.style_name,
                            title="So'rov",
                            message=f"{self.last_data_right.get(wagonNumber, identifier * num_count)} avval yuborilgan, yana yubormoqchimisiz?"
                        )
                        if ans != QMessageBox.StandardButton.Yes:
                            return
                    self.wagon_ids.append(self.last_data_right.get(wagonNumber, identifier * num_count))
                    self.progressbar: ProgressBar = ProgressBar()
                    self.progressbar.change_style(style_name=self.style_name)
                    self.progressbar.show()
                    self.upload_right: bool = True
                    self.send()
                else:
                    show_message(
                        stl=self.style_name,
                        message="Kamera yoqilmagan"
                    )
            else:
                show_message(
                    stl=self.style_name,
                    message="Kamera yoqilmagan"
                )
        else:
            show_message(
                stl=self.style_name,
                message=f"O'lchash uchun minimal og'irlik {min_send_kg:,} kg"
            )

    def get_wagon_numer_left(self) -> str:
        if self.last_data_left.get(wagonNumber) is not None:
            return self.last_data_left.get(wagonNumber)
        return identifier * num_count

    def get_wagon_numer_right(self) -> str:
        if self.last_data_right.get(wagonNumber) is not None:
            return self.last_data_right.get(wagonNumber)
        return identifier * num_count

    def get_img_id_left(self) -> Union[np.ndarray | None]:
        if isinstance(self.last_data_left.get(wagonAttachId), np.ndarray):
            return deepcopy(self.last_data_left.get(wagonAttachId))
        return qpixmap_to_ndarray(pixmap=self.last_image_left)

    def get_img_id_right(self) -> Union[np.ndarray | None]:
        if isinstance(self.last_data_right.get(wagonAttachId2), np.ndarray):
            return deepcopy(self.last_data_right.get(wagonAttachId2))
        return qpixmap_to_ndarray(pixmap=self.last_image_right)

    def get_img_id_number_left(self) -> Union[np.ndarray | None]:
        if isinstance(self.last_data_left.get(wagonNumberAttachId), np.ndarray):
            return deepcopy(self.last_data_left.get(wagonNumberAttachId))
        return None

    def get_img_id_number_right(self) -> Union[np.ndarray | None]:
        if isinstance(self.last_data_right.get(wagonNumberAttachId), np.ndarray):
            return deepcopy(self.last_data_right.get(wagonNumberAttachId))
        return None

    def find_scales(self):
        try:
            if self.config.get(SCALE_DISABLE, False):
                self.scales = []
                self.com_ports = []
                return
            self.scales = open_all_scales()
            self.com_ports: list[str] = [str(i.port) for i in self.scales]
        except Exception as err:
            log(message=f"[MainApp.find_scales] {err}")

    def scale_weight(self, massa: dict):
        try:
            vals: list[int] = list(massa.values())
            if massa:
                ms: int = sum(vals + [0])
                if min_send_kg > max(self.last_scale_weight):
                    self.sending_data.clear()
                    self.last_data_left: dict = {}
                    self.last_data_right: dict = {}
                    self.wagon_image: Union[np.ndarray | None] = None
                    self.wagon_image2: Union[np.ndarray | None] = None
                    self.wagon_id_image: Union[np.ndarray | None] = None
                    self.left_widget.frame_lbl.number_lbl.clear()
                    self.left_widget.frame_lbl.number_image_lbl.clear()
                    self.right_widget.frame_lbl.number_lbl.clear()
                    self.right_widget.frame_lbl.number_image_lbl.clear()

                if self.config.get(SCALE_VIEW, False):
                    sc_txt = f"{' + '.join([f'{key}({value})' for key, value in massa.items()])} = {ms} kg"
                else:
                    sc_txt = f"{' + '.join([f'{key}(*****)' for key, value in massa.items()])} = ***** kg"

                self.hor_left_widget.right_lbl.setText(sc_txt)

                self.last_scale_weight.append(ms)
                if len(self.last_scale_weight) > self.max_scale_weight:
                    self.last_scale_weight.pop(0)
            else:
                self.hor_left_widget.right_lbl.setText("0 kg")
        except (Exception, ValueError) as err:
            log(message=f"[MainApp.scale_weight] {err}")
            show_message(
                stl=self.style_name,
                message=f"[MainApp.scale_weight] Xatolik: {err}"
            )

    def send(self):
        try:
            if not self.config.get(AUTO, False):
                self.left_widget.frame_lbl.btn.setDisabled(True)
                self.right_widget.frame_lbl.btn.setDisabled(True)
            if max(self.last_scale_weight) > min_send_kg:
                if self.get_wagon_numer_right().count(identifier) == self.get_wagon_numer_left().count(
                        identifier) == num_count:
                    self.send_unrec()
                    return
                self.wagon_image = self.get_img_id_left()
                self.wagon_image2 = self.get_img_id_right()
                if self.upload_right:
                    if self.get_wagon_numer_right().count(identifier) <= self.get_wagon_numer_left().count(identifier):
                        self.sending_data.wagonNumber = self.get_wagon_numer_right()
                        self.wagon_id_image = self.get_img_id_number_right()
                    else:
                        self.sending_data.wagonNumber = self.get_wagon_numer_left()
                        self.wagon_id_image = self.get_img_id_number_left()
                else:
                    if self.get_wagon_numer_right().count(identifier) >= self.get_wagon_numer_left().count(identifier):
                        self.sending_data.wagonNumber = self.get_wagon_numer_left()
                        self.wagon_id_image = self.get_img_id_number_left()
                    else:
                        self.sending_data.wagonNumber = self.get_wagon_numer_right()
                        self.wagon_id_image = self.get_img_id_number_right()

                self.sending_data.scaleNumber = max(self.last_scale_weight)
                self.sending_data.stationCode = self.config.get(STATION_CODE, default_station_code)
                self.sending_data.scaleCode = self.config.get(SCALE_CODE, default_scale_code)
                self.sending_data.createdDate = current_time()

                self.upload_thread: UploadThread = UploadThread(
                    data=self.sending_data,
                    img_id=self.wagon_image,
                    img_id2=self.wagon_image2,
                    img_number=self.wagon_id_image,
                    bs_url=self.config.get(BASE_URL, base_url),
                    login_data={
                        "login": self.config.get(USERNAME, default_username),
                        "password": self.config.get(PASSWORD, default_password),
                    }
                )
                self.upload_thread.message_signal.connect(self.get_upload_response)
                self.upload_thread.progress_signal.connect(self.fake_progressbar)
                self.upload_thread.start()
                self.upload_right: bool = False
                self.upload_left: bool = False
            else:
                show_message(
                    stl=self.style_name,
                    message=f"[MainApp.send] O'lchash uchun minimal og'irlik {min_send_kg:,} kg"
                )
                if not self.config.get(AUTO, False):
                    self.left_widget.frame_lbl.btn.setDisabled(False)
                    self.right_widget.frame_lbl.btn.setDisabled(False)
        except (Exception, ValueError) as err:
            log(message=f"[MainApp.send] {err}")

    def send_auto(self):
        try:
            self.sending_data.scaleNumber = max(self.last_scale_weight)
            self.sending_data.stationCode = self.config.get(STATION_CODE, default_station_code)
            self.sending_data.scaleCode = self.config.get(SCALE_CODE, default_scale_code)
            self.sending_data.createdDate = current_time()

            self.upload_thread: UploadThread = UploadThread(
                data=self.sending_data,
                img_id=self.wagon_image,
                img_id2=self.wagon_image2,
                img_number=self.wagon_id_image,
                bs_url=self.config.get(BASE_URL, base_url),
                login_data={
                    "login": self.config.get(USERNAME, default_username),
                    "password": self.config.get(PASSWORD, default_password),
                }
            )
            self.upload_thread.message_signal.connect(self.get_upload_response)
            self.upload_thread.progress_signal.connect(self.fake_progressbar)
            self.upload_thread.start()
            self.is_timeout = True
            self.video_thread_left.is_timeout = True
            self.video_thread_right.is_timeout = True

            self.send_current_time: str = self.send_time
        except (Exception, ValueError) as err:
            log(message=f"[MainApp.send_auto] {err}")

    def update_left_fps(self, fps: str):
        self.left_widget.frame_lbl.set_txt(txt=fps)

    def update_right_fps(self, fps: str):
        self.right_widget.frame_lbl.set_txt(txt=fps)

    def get_upload_response(self, ans: bool, data: dict):
        ttl = self.backup_db.get_total()
        self.status_widget.archive_count_lbl.setText(str(ttl))
        if not self.config.get(AUTO, False) and not self.config.get(BTN_DISABLE, False):
            QTimer.singleShot(3_000, lambda: self.right_widget.frame_lbl.btn.setDisabled(False))
            QTimer.singleShot(3_000, lambda: self.left_widget.frame_lbl.btn.setDisabled(False))
        if isinstance(self.progressbar, ProgressBar):
            if self.progressbar.isVisible():
                self.progressbar.force_close()
                self.progressbar = None

        if isinstance(self.video_thread_left, AutoVideoThread):
            self.video_thread_left.is_timeout = False
        if isinstance(self.video_thread_right, AutoVideoThread):
            self.video_thread_right.is_timeout = False
        if ans:
            self.wagon_ids.append(self.sending_data.wagonNumber)
            dx = {
                wagonNumber: self.sending_data.wagonNumber,
                wagonAttachId: self.wagon_image,
                wagonAttachId2: self.wagon_image2,
                wagonNumberAttachId: self.wagon_id_image,
                scaleNumber: self.sending_data.scaleNumber,
            }

            dx_ = {
                wagonNumber: self.sending_data.wagonNumber,
                scaleNumber: self.sending_data.scaleNumber,
                createdDate: self.sending_data.createdDate,
                stationCode: self.config.get(STATION_CODE, default_station_code),
                scaleCode: self.config.get(SCALE_CODE, default_scale_code),
                wagonAttachId: self.wagon_image,
                wagonAttachId2: self.wagon_image2,
                wagonNumberAttachId: self.wagon_id_image,
            }
            if self.last_ttl == ttl:
                dx_[sentAt] = current_time()
                self.history_widget.add_row(data=dx_, sent=True)
            else:
                self.last_ttl = ttl
                self.history_widget.add_row(data=dx_)
            self.table.add_row(data=dx)
            # self.insert_histories()

            self.last_scale_weight: list[int] = [0]

            self.sending_data.clear()
            self.last_data_left: dict = {}
            self.last_data_right: dict = {}
            self.wagon_image: Union[np.ndarray | None] = None
            self.wagon_id_image: Union[np.ndarray | None] = None
        else:
            if self.config.get(AUTO, False):
                if self.sent_left_auto:
                    self.sent_left_track_ids.pop()
                else:
                    self.sent_right_track_ids.pop()
            self.sent_left_auto: bool = False
            self.sent_right_auto: bool = False
            self.upload_right: bool = False
            self.upload_left: bool = False
            self.is_timeout: bool = False
            self.send_current_time: str = self.send_time
            self.hor_right_widget.right_lbl.setText(self.send_current_time)

            log(message=f"[MainApp.get_upload_response] Yuborib bo'lmadi. >>> {data}")
            show_message(
                stl=self.style_name,
                message=f"Yuborib bo'lmadi. >>> {data}"
            )

    def backup_upload_response(self, ans: bool, data: dict):
        if not self.config.get(AUTO, False) and not self.config.get(BTN_DISABLE, False):
            QTimer.singleShot(3_000, lambda: self.right_widget.frame_lbl.btn.setDisabled(False))
            QTimer.singleShot(3_000, lambda: self.left_widget.frame_lbl.btn.setDisabled(False))
        ttl = self.backup_db.get_total()
        self.last_ttl = ttl
        self.status_widget.archive_count_lbl.setText(str(ttl))
        if ans:
            dx = {
                wagonNumber: data.get(wagonNumber),
                wagonAttachId: data.get(wagonAttachId),
                wagonAttachId2: data.get(wagonAttachId2),
                wagonNumberAttachId: data.get(wagonNumberAttachId),
                scaleNumber: data.get(scaleNumber),
            }
            self.table.add_row(data=dx)
            dx_ = {
                wagonNumber: self.sending_data.wagonNumber,
                scaleNumber: self.sending_data.scaleNumber,
                stationCode: self.sending_data.stationCode,
                scaleCode: self.sending_data.scaleCode,
                createdDate: self.sending_data.createdDate,
                sentAt: current_time(),
                wagonAttachId: self.wagon_image,
                wagonAttachId2: self.wagon_image2,
                wagonNumberAttachId: self.wagon_id_image,
            }
            self.history_widget.add_row(data=dx_)
            # self.insert_histories()
        else:
            log(message=f"[MainApp.backup_upload_response] Yuborib bo'lmadi. >>> {data.get('error', 'ERROR')} {data}")
            show_message(
                stl=self.style_name,
                message=f"Yuborib bo'lmadi. >>> {data.get('error', 'ERROR')} {data}"
            )

    def backup_upload_error(self, err: str):
        ttl = self.backup_db.get_total()
        self.last_ttl = ttl
        self.status_widget.archive_count_lbl.setText(str(ttl))
        log(message=f"[BackupUploadThread.run] Yuborib bo'lmadi. >>> {err}")
        show_message(
            stl=self.style_name,
            message=f"[BackupUploadThread.run] Yuborib bo'lmadi. >>> {err}"
        )
        if not self.config.get(AUTO, False):
            self.left_widget.frame_lbl.btn.setDisabled(False)
            self.right_widget.frame_lbl.btn.setDisabled(False)

    def get_error_message_left(self, msg: str):
        show_message(
            stl=self.style_name,
            message=f"Xatolik sodir bo'ldi. [Chap] \n{msg}"
        )

    def get_error_message_right(self, msg: str):
        show_message(
            stl=self.style_name,
            message=f"Xatolik sodir bo'ldi. [O'ng] \n{msg}"
        )

    def closeEvent(self, a0):
        try:
            ans: int = ask_message(
                stl=self.style_name,
                title="Chiqish",
                message="Dasturdan chiqishni xohlaysizmi?"
            )
            if ans == QMessageBox.StandardButton.Yes:
                def _stop(t):
                    if t is None:
                        return
                    try:
                        t.running = False
                        if not t.wait(2000):
                            t.terminate()
                    except Exception:
                        pass
                _stop(self.video_thread_left)
                _stop(self.video_thread_right)
                _stop(self.server_connection_thread)
                _stop(self.login_thread)
                if isinstance(self.scale_thread, ScaleThread):
                    _stop(self.scale_thread)
                try:
                    self.backup_db.close()
                except Exception:
                    pass
                log(message=f"[MainApp.closeEvent] Exit", level="INFO")
                a0.accept()
            else:
                a0.ignore()
        except (Exception, ValueError) as err:
            log(message=f"[MainApp.closeEvent] {err}")
            a0.accept()


