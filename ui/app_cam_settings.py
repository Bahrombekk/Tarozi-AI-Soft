from __future__ import annotations
import os

from PyQt6.QtWidgets import QDialog

from core.cipher import cipher
from core.config import (
    log,
    SEND_TIME, STATION_CODE, SCALE_CODE, AUTO,
    default_send_time, default_station_code, default_scale_code,
    min_side, max_side, min_frame_count, max_frame_count, min_distance, max_distance,
)
from threads.workers import SaveThread
from ui.models import SavingData
from ui.settings_panel import HiddenSettingsWidget, half_available, _get_gpu_name
from utils.helpers import show_message, make_range_validator


def _is_valid_video_source(path: str) -> bool:
    """Check if path is a valid RTSP URL or a local video file."""
    if path.startswith("rtsp://"):
        return True
    return os.path.isfile(path)


class CamSettingsMixin:

    def save_settings(self):
        self.settings_widget.save_btn.setDisabled(True)
        self._save_send_time()
        self._save_station_code()
        self._save_scale_code()
        for vt, save_fn in [
            (self.video_thread_left, self._save_cam_url_left),
            (self.video_thread_right, self._save_cam_url_right)
        ]:
            if vt is None:
                save_fn()
            elif vt.running:
                show_message(stl=self.style_name, message="Saqlashdan avval videoni to'xtating.")
            else:
                save_fn()
        self.settings_widget.save_btn.setDisabled(False)

    def _save_send_time(self):
        txt = self.settings_widget.send_time_widget.edit.text().strip()
        if txt and int(txt) > 0:
            sec = int(txt)
            self.settings.patch(key=SEND_TIME, value=sec)
            self.config = self.settings.load()
            self.send_time = self._time_format(sec)
            self.send_current_time = self.send_time
            self.hor_right_widget.right_lbl.setText(self.send_current_time)

    def _save_station_code(self):
        txt = self.settings_widget.station_code_widget.edit.text().strip()
        if txt:
            self.settings.patch(key=STATION_CODE, value=txt)
            self.config = self.settings.load()

    def _save_scale_code(self):
        txt = self.settings_widget.scale_code_widget.edit.text().strip()
        if txt:
            self.settings.patch(key=SCALE_CODE, value=txt)
            self.config = self.settings.load()

    def _save_cam_url_left(self):
        txt = self.settings_widget.left_cam_widget.edit.text().strip()
        if not txt:
            return
        if os.path.isfile(txt):
            # Local video file — no connection check needed
            self._save_response_left(True)
        elif txt.startswith("rtsp://"):
            self.settings_widget.save_btn.setDisabled(True)
            self.settings_widget.left_cam_widget.edit.setDisabled(True)
            self.save_thread_left = SaveThread(url=txt)
            self.save_thread_left.save_signal.connect(self._save_response_left)
            self.save_thread_left.start()
        else:
            self.settings_widget.left_cam_widget.edit.setText(self.cam_url_1)

    def _save_cam_url_right(self):
        txt = self.settings_widget.right_cam_widget.edit.text().strip()
        if not txt:
            return
        if os.path.isfile(txt):
            # Local video file — no connection check needed
            self._save_response_right(True)
        elif txt.startswith("rtsp://"):
            self.settings_widget.save_btn.setDisabled(True)
            self.settings_widget.right_cam_widget.edit.setDisabled(True)
            self.save_thread_right = SaveThread(url=txt)
            self.save_thread_right.save_signal.connect(self._save_response_right)
            self.save_thread_right.start()
        else:
            self.settings_widget.right_cam_widget.edit.setText(self.cam_url_2)

    def _save_response_left(self, ans: bool):
        if ans:
            self.settings_widget.left_cam_widget.lbl.setText("Chap Kamera \u2705")
            self.cam_url_1 = self.settings_widget.left_cam_widget.edit.text().strip()
            cipher.write("settings/cam_1.bin", [self.cam_url_1])
            self.left_widget.switch.setDisabled(False)
            if self.video_thread_left is None or not self.video_thread_left.running:
                self.left_widget.switch.setChecked(True)
                self.left_widget.switch.start_transition(2)
        else:
            self.settings_widget.left_cam_widget.lbl.setText("Chap Kamera \u274c")
            show_message(stl=self.style_name, message="Chap kamera bilan aloqa mavjud emas.")
            self.left_widget.switch.setDisabled(True)
        self.settings_widget.left_cam_widget.edit.setDisabled(False)
        self.settings_widget.save_btn.setDisabled(False)

    def _save_response_right(self, ans: bool):
        if ans:
            self.settings_widget.right_cam_widget.lbl.setText("O'ng Kamera \u2705")
            self.cam_url_2 = self.settings_widget.right_cam_widget.edit.text().strip()
            cipher.write("settings/cam_2.bin", [self.cam_url_2])
            self.right_widget.switch.setDisabled(False)
            if self.video_thread_right is None or not self.video_thread_right.running:
                self.right_widget.switch.setChecked(True)
                self.right_widget.switch.start_transition(2)
        else:
            self.settings_widget.right_cam_widget.lbl.setText("O'ng Kamera \u274c")
            show_message(stl=self.style_name, message="O'ng kamera bilan aloqa mavjud emas.")
            self.right_widget.switch.setDisabled(True)
        self.settings_widget.right_cam_widget.edit.setDisabled(False)
        self.settings_widget.save_btn.setDisabled(False)

    def settings_window_left(self, event):
        from PyQt6.QtCore import Qt as Qt_
        if (event.button() == Qt_.MouseButton.MiddleButton and
                event.modifiers() & Qt_.KeyboardModifier.ControlModifier and
                event.modifiers() & Qt_.KeyboardModifier.ShiftModifier):
            if self.video_thread_left and self.video_thread_left.running:
                show_message(stl=self.style_name, message="Avval chap kamera videosini to'xtating.")
                return
            self.apply_blur(enable=True)
            self._open_hidden_settings(side="left")

    def settings_window_right(self, event):
        from PyQt6.QtCore import Qt as Qt_
        if (event.button() == Qt_.MouseButton.MiddleButton and
                event.modifiers() & Qt_.KeyboardModifier.ControlModifier and
                event.modifiers() & Qt_.KeyboardModifier.ShiftModifier):
            if self.video_thread_right and self.video_thread_right.running:
                show_message(stl=self.style_name, message="Avval o'ng kamera videosini to'xtating.")
                return
            self.apply_blur(enable=True)
            self._open_hidden_settings(side="right")

    def _open_hidden_settings(self, side: str):
        sw, sh = self.screen_width, self.screen_height
        self.hidden_settings_widget = HiddenSettingsWidget(
            style_name=self.style_name, screen_width=sw, screen_height=sh)
        hw = self.hidden_settings_widget
        iv = make_range_validator(min_side, max_side)
        ifc = make_range_validator(min_frame_count, max_frame_count)
        idc = make_range_validator(min_distance, max_distance)
        for edit in [hw.top_bottom.col1.edit, hw.top_bottom.col2.edit,
                     hw.left_right.col1.edit, hw.left_right.col2.edit]:
            edit.setValidator(iv)
        hw.frame_count_distance.col1.edit.setValidator(ifc)
        hw.frame_count_distance.col2.edit.setValidator(idc)
        if side == "left":
            t, b, l, r = self.top_1, self.bottom_1, self.left_1, self.right_1
            mf, dist = self.max_frame_count_1, self.distance_1
            fps_v, half_v, line_v = self.fps_view_1, self.is_half_1, self.is_line_1
        else:
            t, b, l, r = self.top_2, self.bottom_2, self.left_2, self.right_2
            mf, dist = self.max_frame_count_2, self.distance_2
            fps_v, half_v, line_v = self.fps_view_2, self.is_half_2, self.is_line_2
        hw.top_bottom.col1.edit.setText(str(t))
        hw.top_bottom.col2.edit.setText(str(b))
        hw.left_right.col1.edit.setText(str(l))
        hw.left_right.col2.edit.setText(str(r))
        hw.frame_count_distance.col1.edit.setText(str(mf))
        hw.frame_count_distance.col2.edit.setText(str(dist))
        hw.fps_.hidden_switch.setChecked(fps_v)
        hw.half.hidden_switch.setChecked(half_v if half_available else False)
        if not half_available:
            hw.half.hidden_switch.setDisabled(True)
            hw.half.edit.setText(f"Aniqlikni kuchaytirish mavjud emas \n({_get_gpu_name()})")
        hw.line.hidden_switch.setChecked(line_v)
        hw.closeEvent = self._close_hidden_settings_window

        def _get_saving_data() -> SavingData:
            dt = SavingData()
            try:
                dt.top = int(hw.top_bottom.col1.edit.text().strip())
                dt.bottom = int(hw.top_bottom.col2.edit.text().strip())
                dt.left = int(hw.left_right.col1.edit.text().strip())
                dt.right = int(hw.left_right.col2.edit.text().strip())
                dt.max_frame = int(hw.frame_count_distance.col1.edit.text().strip())
                dt.dist = int(hw.frame_count_distance.col2.edit.text().strip())
                dt.is_fps = hw.fps_.hidden_switch.isChecked()
                dt.is_line = hw.line.hidden_switch.isChecked()
                dt.hf = hw.half.hidden_switch.isChecked()
            except (Exception, ValueError):
                pass
            return dt

        hw.back_btn.clicked.connect(hw.close)
        if side == "left":
            hw.save_btn.clicked.connect(lambda: self._save_data_side("left", _get_saving_data(), hw))
        else:
            hw.save_btn.clicked.connect(lambda: self._save_data_side("right", _get_saving_data(), hw))
        hw.exec()

    def _save_data_side(self, side: str, data: SavingData, modal: QDialog):
        def _write(path, val):
            cipher.write(file_path=path, data=[str(val)])

        n = 1 if side == "left" else 2
        _write(f"settings/line_{n}.bin", int(data.is_line))
        _write(f"settings/fps_{n}.bin", int(data.is_fps))
        _write(f"settings/half_{n}.bin", int(data.hf))
        if side == "left":
            self.is_line_1, self.fps_view_1, self.is_half_1 = data.is_line, data.is_fps, data.hf
        else:
            self.is_line_2, self.fps_view_2, self.is_half_2 = data.is_line, data.is_fps, data.hf
        bounds = [
            (data.max_frame, min_frame_count, max_frame_count,
             f"max_frame_count_{n}", f"settings/frame_count_{n}.bin"),
            (data.dist, min_distance, max_distance,
             f"distance_{n}", f"settings/distance_{n}.bin"),
            (data.top, min_side, max_side, f"top_{n}", f"settings/top_{n}.bin"),
            (data.bottom, min_side, max_side, f"bottom_{n}", f"settings/bottom_{n}.bin"),
            (data.left, min_side, max_side, f"left_{n}", f"settings/left_{n}.bin"),
            (data.right, min_side, max_side, f"right_{n}", f"settings/right_{n}.bin"),
        ]
        for val, mn, mx, attr, path in bounds:
            if mn <= val <= mx:
                setattr(self, attr, val)
                _write(path, val)
        self.config = self.settings.load()
        modal.close()
