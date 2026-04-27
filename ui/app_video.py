from __future__ import annotations

from PyQt6.QtCore import QTimer

from core.config import (
    log, AUTO, BTN_DISABLE, D_CONF, R_CONF,
    default_det_conf, default_rec_conf,
    TOP, BOTTOM, LEFT, RIGHT, CAM_URL, LINE, HALF, FPS, DISTANCE, MAX_FRAME,
)
from threads.video import VideoThread
from threads.auto_video import AutoVideoThread
from utils.helpers import show_message


class VideoMixin:

    def _make_video_thread_left(self):
        if self.config.get(AUTO, False):
            vt = AutoVideoThread(data={
                CAM_URL: self.cam_url_1, LINE: self.is_line_1, HALF: self.is_half_1,
                FPS: self.fps_view_1, D_CONF: self.config.get(D_CONF, default_det_conf),
                R_CONF: self.config.get(R_CONF, default_rec_conf),
                DISTANCE: self.distance_1, MAX_FRAME: self.max_frame_count_1,
                TOP: self.top_1, BOTTOM: self.bottom_1, LEFT: self.left_1, RIGHT: self.right_1,
            })
            vt.image_signal.connect(self.update_frame_left)
            vt.data_signal.connect(self.get_auto_data_left)
            vt.error_signal.connect(self.get_error_message_left)
            vt.disconnected_signal.connect(self.disconnected_left)
        else:
            vt = VideoThread(
                cam_url=self.cam_url_1, lined=self.is_line_1, fps=self.fps_view_1,
                is_half=self.is_half_1, dist=self.distance_1,
                r_conf=self.config.get(R_CONF, default_rec_conf),
                d_conf=self.config.get(D_CONF, default_det_conf),
                crop=self.crop_1,
                side={TOP: self.top_1, LEFT: self.left_1,
                      BOTTOM: self.bottom_1, RIGHT: self.right_1},
            )
            vt.image_signal.connect(self.update_frame_left)
            vt.data_signal.connect(self.get_handle_data_left)
            vt.error_signal.connect(self.get_error_message_left)
            vt.disconnected_signal.connect(self.disconnected_left)
            vt.inner_signal.connect(self.inner_left)
        return vt

    def _make_video_thread_right(self):
        if self.config.get(AUTO, False):
            vt = AutoVideoThread(data={
                CAM_URL: self.cam_url_2, LINE: self.is_line_2, HALF: self.is_half_2,
                FPS: self.fps_view_2, D_CONF: self.config.get(D_CONF, default_det_conf),
                R_CONF: self.config.get(R_CONF, default_rec_conf),
                DISTANCE: self.distance_2, MAX_FRAME: self.max_frame_count_2,
                TOP: self.top_2, BOTTOM: self.bottom_2, LEFT: self.left_2, RIGHT: self.right_2,
            })
            vt.image_signal.connect(self.update_frame_right)
            vt.data_signal.connect(self.get_auto_data_right)
            vt.error_signal.connect(self.get_error_message_right)
            vt.disconnected_signal.connect(self.disconnected_right)
        else:
            vt = VideoThread(
                cam_url=self.cam_url_2, lined=self.is_line_2, fps=self.fps_view_2,
                is_half=self.is_half_2, dist=self.distance_2,
                r_conf=self.config.get(R_CONF, default_rec_conf),
                d_conf=self.config.get(D_CONF, default_det_conf),
                crop=self.crop_2,
                side={TOP: self.top_2, LEFT: self.left_2,
                      BOTTOM: self.bottom_2, RIGHT: self.right_2},
            )
            vt.image_signal.connect(self.update_frame_right)
            vt.data_signal.connect(self.get_handle_data_right)
            vt.error_signal.connect(self.get_error_message_right)
            vt.disconnected_signal.connect(self.disconnected_right)
            vt.inner_signal.connect(self.inner_right)
        return vt

    def start_video_left(self):
        try:
            self.running_left = not self.running_left
            self.left_widget.switch.setDisabled(True)
            if self.running_left:
                self.settings_widget.auto_switch.setDisabled(True)
                self.video_thread_left = self._make_video_thread_left()
                if self.is_line_1:
                    self.left_widget.frame_lbl.set_lines(
                        (self.top_1, self.left_1, self.bottom_1, self.right_1))
                if self.fps_view_1:
                    self.video_thread_left.fps_signal.connect(self.update_left_fps)
                    self.left_widget.frame_lbl.toggle_fps(view=True)
                self.left_widget.frame_lbl.btn.setDisabled(True)
                self.video_thread_left.start()
                QTimer.singleShot(2500, self.enable_left_switch)
                self.left_widget.state_lbl.setText("Kamera ishlamoqda")
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
                self.left_widget.frame_lbl.set_lines((None, None, None, None))
                self.last_data_left = {}
                if self.video_thread_left:
                    self.video_thread_left.stop()
                if not (self.video_thread_right and self.video_thread_right.running):
                    self.settings_widget.auto_switch.setDisabled(False)
            if not self.running_left:
                self.left_widget.frame_lbl.toggle_fps(view=False)
        except (Exception, ValueError) as err:
            log(message=f"[App.start_video_left] {err}")

    def start_video_right(self):
        try:
            self.running_right = not self.running_right
            self.right_widget.switch.setDisabled(True)
            if self.running_right:
                self.settings_widget.auto_switch.setDisabled(True)
                self.video_thread_right = self._make_video_thread_right()
                if self.fps_view_2:
                    self.video_thread_right.fps_signal.connect(self.update_right_fps)
                    self.right_widget.frame_lbl.toggle_fps(view=True)
                if self.is_line_2:
                    self.right_widget.frame_lbl.set_lines(
                        (self.top_2, self.left_2, self.bottom_2, self.right_2))
                self.right_widget.frame_lbl.btn.setDisabled(True)
                self.video_thread_right.start()
                QTimer.singleShot(2500, self.enable_right_switch)
                self.right_widget.state_lbl.setText("Kamera ishlamoqda")
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
                self.right_widget.frame_lbl.set_lines((None, None, None, None))
                self.last_data_right = {}
                self.last_image_right = None
                if self.video_thread_right:
                    self.video_thread_right.stop()
                if not (self.video_thread_left and self.video_thread_left.running):
                    self.settings_widget.auto_switch.setDisabled(False)
            if not self.running_right:
                self.right_widget.frame_lbl.toggle_fps(view=False)
        except (Exception, ValueError) as err:
            log(message=f"[App.start_video_right] {err}")

    def enable_left_switch(self):
        self.left_widget.switch.setDisabled(False)

    def enable_right_switch(self):
        self.right_widget.switch.setDisabled(False)

    def inner_left(self, ans: bool):
        if self.config.get(BTN_DISABLE, False):
            self.left_widget.frame_lbl.btn.setDisabled(not ans)

    def inner_right(self, ans: bool):
        if self.config.get(BTN_DISABLE, False):
            self.right_widget.frame_lbl.btn.setDisabled(not ans)

    def disconnected_left(self):
        if isinstance(self.video_thread_left, VideoThread):
            self.video_thread_left.stop()
        self.left_widget.state_lbl.setText("Kamera o'chgan")
        self.left_widget.frame_lbl.btn.setDisabled(False)
        self.left_widget.frame_lbl.clear()
        self.running_left = False
        self.last_data_left = {}
        self.left_widget.switch.setChecked(False)
        self.left_widget.switch.start_transition(0)

    def disconnected_right(self):
        if isinstance(self.video_thread_right, VideoThread):
            self.video_thread_right.stop()
        self.right_widget.state_lbl.setText("Kamera o'chgan")
        self.right_widget.frame_lbl.btn.setDisabled(False)
        self.right_widget.frame_lbl.clear()
        self.running_right = False
        self.last_data_right = {}
        self.right_widget.switch.setChecked(False)
        self.right_widget.switch.start_transition(0)
