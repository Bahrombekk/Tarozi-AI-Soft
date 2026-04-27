from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QKeySequence
from PyQt6.QtGui import QIcon, QShortcut
from PyQt6.QtWidgets import (
    QMainWindow, QApplication, QMessageBox,
)

from core.config import (
    log, AUTO, THEME, LIGHT, SEND_TIME, BASE_URL, LOGIN_URL, USERNAME, PASSWORD,
    STATION_CODE, default_send_time, default_username, default_password, default_station_code,
    get_token_url, base_url, window_title, crop_left, crop_right,
)
from core.database import BufferDB
from threads.workers import ScaleThread, LoginThread, ServerConnectionThread, ProgressThread, PingThread
from ui.models import SendingData
from ui.dialogs import ProgressBar
from ui.styles import get_styles
from ui.settings_manager import SettingsManager
from ui.widgets import _GlobalMouseReleaseFilter, BlurEffect, OverlayWidget
from utils.helpers import open_all_scales as _open_all_scales
from ui.app_mixins import BlurMixin, ThemeMixin
from ui.app_settings import PasswordSettingsMixin
from ui.app_cam_settings import CamSettingsMixin
from ui.app_video import VideoMixin
from ui.app_data import DataMixin
from ui.app_upload import UploadMixin
from ui.app_responses import ResponseMixin
from ui.app_builder import BuildMixin
from ui.app_window import WindowMixin
from ui.password_dialog import PasswordPromptDialog
from utils.helpers import (
    get_camera_url, get_max_frame_count, get_distance, get_is_line, get_half, get_side,
    ask_message,
)


def _get_window_icon():
    try:
        return QIcon("images/train.png")
    except (Exception, ValueError):
        return None


class App(QMainWindow, BlurMixin, ThemeMixin, PasswordSettingsMixin, CamSettingsMixin,
          VideoMixin, DataMixin, UploadMixin, ResponseMixin, BuildMixin, WindowMixin):

    def __init__(self):
        super().__init__()
        app = QApplication.instance()
        _avail = app.primaryScreen().availableGeometry()
        sw = _avail.width()
        sh = _avail.height()
        self.screen_width, self.screen_height = sw, sh
        WIDTH, HEIGHT = int(sw * 0.85), int(sh * 0.90)

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window |
            Qt.WindowType.WindowMinimizeButtonHint | Qt.WindowType.WindowMaximizeButtonHint |
            Qt.WindowType.WindowCloseButtonHint)
        wi = _get_window_icon()
        if wi:
            self.setWindowIcon(wi)
        self.setWindowTitle(window_title)
        self.setGeometry((sw - WIDTH) // 2, (sh - HEIGHT) // 2, WIDTH, HEIGHT)

        self._init_state()
        self._init_settings(sw, sh)
        self._build_ui(sw, sh)
        self._init_threads()
        self._init_post_ui()

    def _init_state(self):
        self.last_login_status = False
        self.sent_left_auto = self.sent_right_auto = self.is_timeout = False
        self.wagon_ids: list[str] = []
        self.last_image_left = self.last_image_right = None
        self.last_data_left: dict = {}
        self.last_data_right: dict = {}
        self.sent_left_track_ids: list[int] = []
        self.sent_right_track_ids: list[int] = []
        self.backup_db = BufferDB()
        self.last_ttl: int = self.backup_db.get_total()
        self.backup_thread = None
        self.progressbar = ProgressBar()
        self.progress_thread = ProgressThread()
        self.progress_thread.value_signal.connect(self.fake_progressbar)

    def _init_settings(self, sw: int, sh: int):
        self.settings = SettingsManager(filename="settings/settings.bin")
        self.config: dict = self.settings.load()
        self.style_name: str = self.config.get(THEME, LIGHT)
        self.style_: str = get_styles(style_name=self.style_name)
        self.crop_1 = crop_left
        self.crop_2 = crop_right
        for side in ("top", "bottom", "left", "right"):
            for n in (1, 2):
                setattr(self, f"{side}_{n}", get_side(f"settings/{side}_{n}.bin"))
        for n in (1, 2):
            setattr(self, f"max_frame_count_{n}", get_max_frame_count(f"settings/frame_count_{n}.bin"))
            setattr(self, f"distance_{n}", get_distance(f"settings/distance_{n}.bin"))
            setattr(self, f"fps_view_{n}", get_is_line(f"settings/fps_{n}.bin"))
            setattr(self, f"is_half_{n}", get_half(f"settings/half_{n}.bin"))
            setattr(self, f"is_line_{n}", get_is_line(f"settings/line_{n}.bin"))
            setattr(self, f"cam_url_{n}", get_camera_url(f"settings/cam_{n}.bin"))
        send_second: int = self.config.get(SEND_TIME, default_send_time)
        self.save_thread_left = self.save_thread_right = None
        self.password_dialog = self.special_settings_dialog = None
        self.upload_thread = self.login_thread = None
        self.last_scale_weight: list[int] = [0]
        self.max_scale_weight: int = 5
        self.com_ports: list[str] = []
        self.scales: list = []
        self.sending_data = SendingData()
        self.send_time = self._time_format(send_second)
        self.send_current_time = self.send_time
        self.wagon_id_image = self.wagon_image = self.wagon_image2 = None
        self.running_1 = self.running_2 = False
        self.video_thread_left = self.video_thread_right = None
        self.running_left = self.running_right = False
        self.upload_left = self.upload_right = False

    def _init_threads(self):
        self.ping_thread = PingThread(
            station_code=self.config.get(STATION_CODE, default_station_code)
        )
        self.ping_thread.start()

        self.scale_thread = None
        QTimer.singleShot(500, self._start_scale_thread)

        self.server_connection_thread = ServerConnectionThread(
            bs_url=self.config.get(BASE_URL, base_url))
        self.server_connection_thread.connection_signal.connect(self.check_server_connection)
        self.server_connection_thread.start()

        if self.config.get(AUTO, False):
            self.left_widget.frame_lbl.btn.setDisabled(True)
            self.right_widget.frame_lbl.btn.setDisabled(True)

        QTimer.singleShot(1000, self.save_settings)
        self.timeout_timer = QTimer(self)
        self.timeout_timer.timeout.connect(self.stop_timeout)
        self.timeout_timer.start(1000)

        from core.config import DARK
        self.change_theme(ans=2 if self.style_name == DARK else 0)
        self.shortcut = QShortcut(QKeySequence("F5"), self)
        self.shortcut.activated.connect(self.insert_histories)

        self.login_thread = LoginThread(
            login_url=self.config.get(LOGIN_URL, get_token_url),
            data={"login": self.config.get(USERNAME, default_username),
                  "password": self.config.get(PASSWORD, default_password)}
        )
        self.login_thread.login_signal.connect(self.login_response)
        self.login_thread.start()
        self.insert_histories()

    def _start_scale_thread(self):
        self.find_scales()
        self.scale_thread = ScaleThread(scales=self.scales, com_ports=self.com_ports)
        self.scale_thread.scale_signal.connect(self.scale_weight)
        self.scale_thread.start()

    def _init_post_ui(self):
        self.blur_effect = BlurEffect(self)
        self.blur_animation = QPropertyAnimation(self.blur_effect, b"blurRadius", self)
        self.blur_animation.setDuration(150)
        self.blur_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.overlay = OverlayWidget(self)
        self.overlay.setGeometry(self.main_widget.geometry())
        self.overlay.hide()

        self._resizing = self._is_maximized = False
        self._anim = None
        self._normal_geometry = self._last_geometry = self.geometry()
        self._global_filter = _GlobalMouseReleaseFilter(self)

        self.title_widget.setMouseTracking(True)
        self.title_widget.installEventFilter(self)
        QApplication.instance().installEventFilter(self._global_filter)
        self.setMouseTracking(True)
        self.main_widget.setMouseTracking(True)
        self.installEventFilter(self)
        self.main_widget.installEventFilter(self)
        self.settings_widget.additional_widget.additional_btn.clicked.connect(self.ask_password_window)



# Re-export for backward compatibility with app_settings.py
_PasswordPromptDialog = PasswordPromptDialog
