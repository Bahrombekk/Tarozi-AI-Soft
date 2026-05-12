from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING

import numpy as np
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtSlot
from PyQt6.QtGui import QIcon, QLineEdit
from PyQt6.QtWidgets import QApplication, QMessageBox, QDialog, QLineEdit

from core.config import (
    log, static_password, identifier, num_count,
    DARK, LIGHT, AUTO, THEME, SEND_TIME, STATION_CODE, SCALE_CODE,
    BASE_URL, LOGIN_URL, UPLOAD_URL, USERNAME, PASSWORD, D_CONF, R_CONF,
    BTN_DISABLE, SCALE_VIEW, default_send_time, default_station_code, default_scale_code,
    default_username, default_password, default_det_conf, default_rec_conf,
    get_token_url, post_url, base_url, min_send_kg,
    min_side, max_side, min_frame_count, max_frame_count, min_distance, max_distance,
    min_det_conf, max_det_conf, min_rec_conf, max_rec_conf,
    wagonNumber, wagonAttachId, wagonAttachId2, wagonNumberAttachId,
    scaleNumber, createdDate, sentAt, stationCode, scaleCode, t_id,
    TOP, BOTTOM, LEFT, RIGHT, CAM_URL, LINE, HALF, FPS, DISTANCE, MAX_FRAME,
)
from core.database import current_time
from core.cipher import cipher
from network.api import get_base_url
from threads.workers import LoginThread
from threads.upload import UploadThread, BackupUploadThread
from threads.video import VideoThread
from threads.auto_video import AutoVideoThread
from ui.widgets import BlurEffect, OverlayWidget
from utils.helpers import fix_luhn_code
from ui.models import SavingData
from ui.styles import get_styles
from utils.helpers import (
    show_message, ask_message, make_range_validator,
    get_side, get_camera_url, get_max_frame_count, get_distance, get_is_line, get_half,
)
from utils.image import cv2_to_qpixmap, qpixmap_to_ndarray, rounded_pixmap


# ---------------------------------------------------------------------------
# BlurMixin
# ---------------------------------------------------------------------------

class BlurMixin:
    def apply_blur(self, enable: bool):
        try:
            if enable:
                if hasattr(self, 'blur_effect') and isinstance(self.blur_effect, BlurEffect):
                    self.blur_effect.deleteLater()
                self.blur_effect = BlurEffect(self)
                self.main_widget.setGraphicsEffect(self.blur_effect)
                self.blur_animation = QPropertyAnimation(self.blur_effect, b"blurRadius", self)
                self.blur_animation.setDuration(150)
                self.blur_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
                self.blur_animation.setStartValue(0)
                self.blur_animation.setEndValue(10)
                self.blur_animation.start()
                self.overlay.setGeometry(0, 0, self.width(), self.height())
                self.overlay.show()
                self.overlay.raise_()
            else:
                if hasattr(self, 'blur_animation') and isinstance(self.blur_animation, QPropertyAnimation):
                    try:
                        self.blur_animation.finished.disconnect()
                    except (Exception, ValueError):
                        pass
                    self.blur_animation.setStartValue(10)
                    self.blur_animation.setEndValue(0)
                    self.blur_animation.finished.connect(self._on_blur_done)
                    self.blur_animation.start()
                self.overlay.hide()
        except (Exception, ValueError) as e:
            log(message=f"[BlurMixin.apply_blur] {e}")
            if hasattr(self, 'main_widget'):
                self.main_widget.setGraphicsEffect(None)
            if hasattr(self, 'overlay'):
                self.overlay.hide()

    @pyqtSlot()
    def _on_blur_done(self):
        try:
            if hasattr(self, 'blur_effect') and isinstance(self.blur_effect, BlurEffect):
                if self.blur_effect.blurRadius == 0:
                    self.main_widget.setGraphicsEffect(None)
                    self.blur_effect = None
        except (Exception, RuntimeError):
            pass


# ---------------------------------------------------------------------------
# ThemeMixin
# ---------------------------------------------------------------------------

class ThemeMixin:
    def change_theme(self, ans: int):
        thm = DARK if ans == 2 else LIGHT
        self.settings.patch(key=THEME, value=thm)
        self.config = self.settings.load()
        self.style_name = self.config.get(THEME, LIGHT)
        self.style_ = get_styles(style_name=self.style_name)
        for w in [self.title_widget, self.settings_widget, self.history_widget,
                  self.left_widget, self.right_widget, self.hor_left_widget,
                  self.hor_right_widget, self.table, self.status_widget]:
            w.change_style(style_name=self.style_name)
        self.setStyleSheet(self.style_)
        self.main_widget.setStyleSheet(self.style_)
        self.tab_widget.setStyleSheet(self.style_)
        self.cam_widget.setStyleSheet(self.style_)

    def change_auto(self, ans: int):
        for vt in [self.video_thread_left, self.video_thread_right]:
            if isinstance(vt, (VideoThread, AutoVideoThread)):
                if vt.running:
                    show_message(stl=self.style_name, title="Xabar",
                                 message="Avval videoni to'xtating")
                    return
        auto = (ans == 2)
        self.left_widget.frame_lbl.btn.setDisabled(auto)
        self.right_widget.frame_lbl.btn.setDisabled(auto)
        self.settings.patch(key=AUTO, value=auto)
        self.config = self.settings.load()

    def insert_histories(self):
        try:
            self.history_widget.load_history()
        except (Exception, ValueError) as err:
            log(message=f"[App.insert_histories] {err}")

    def stop_timeout(self):
        from utils.helpers import timer_back
        if self.is_timeout:
            self.send_current_time = timer_back(self.send_current_time)
            if self.send_current_time == "00:00:00":
                self.send_current_time = self.send_time
                self.is_timeout = False
            self.hor_right_widget.right_lbl.setText(self.send_current_time)

    def check_server_connection(self, ans: bool):
        ttl = self.backup_db.get_total()
        self.last_ttl = ttl
        self.status_widget.archive_count_lbl.setText(str(ttl))
        if ans and ttl > 0:
            self._upload_backup_data()

    def _upload_backup_data(self):
        self.left_widget.frame_lbl.btn.setDisabled(True)
        self.right_widget.frame_lbl.btn.setDisabled(True)
        self.backup_thread = BackupUploadThread(
            bs_url=self.config.get(UPLOAD_URL, post_url),
            login_data={"login": self.config.get(USERNAME, default_username),
                        "password": self.config.get(PASSWORD, default_password)},
            login_url=self.config.get(LOGIN_URL, get_token_url),
        )
        self.backup_thread.upload_signal.connect(self.backup_upload_response)
        self.backup_thread.error_signal.connect(self.backup_upload_error)
        self.backup_thread.start()

    def fake_progressbar(self, val: int):
        try:
            self.progressbar.progress.setValue(val)
        except (Exception, ValueError) as err:
            log(message=f"[App.fake_progressbar] {err}")

    def login_response(self, ans: bool, data: dict):
        self.last_login_status = ans
        try:
            success_icon = QIcon("images/success.png")
            fail_icon = QIcon("images/fail.png")
        except (Exception, ValueError):
            success_icon = QIcon()
            fail_icon = QIcon()
        if ans:
            self.status_widget.status_btn.setIcon(success_icon)
        else:
            self.status_widget.status_btn.setIcon(fail_icon)
            show_message(stl=self.style_name, message=f"Login qilib bo'lmadi. \n{data}")
        self.settings_widget.save_btn.setDisabled(False)
