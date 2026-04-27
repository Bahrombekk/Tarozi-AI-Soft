from __future__ import annotations

import numpy as np

from core.config import (
    log, identifier, num_count,
    AUTO, BTN_DISABLE,
    wagonNumber, wagonAttachId, wagonAttachId2, wagonNumberAttachId,
    t_id, min_send_kg,
)
from utils.helpers import fix_luhn_code
from utils.image import cv2_to_qpixmap, qpixmap_to_ndarray, rounded_pixmap
from utils.helpers import show_message


class DataMixin:

    def update_frame_left(self, pixmap):
        if self.running_left:
            self.left_widget.frame_lbl.setPixmap(pixmap)
            self.last_image_left = pixmap
            if not self.config.get(BTN_DISABLE, False):
                self.left_widget.frame_lbl.btn.setDisabled(False)
            if self.config.get(AUTO, False):
                self.left_widget.frame_lbl.btn.setDisabled(True)
                self.wagon_image = qpixmap_to_ndarray(pixmap=pixmap)
        else:
            self.left_widget.frame_lbl.clear()

    def update_frame_right(self, pixmap):
        if self.running_right:
            self.right_widget.frame_lbl.setPixmap(pixmap)
            self.last_image_right = pixmap
            if not self.config.get(BTN_DISABLE, False):
                self.right_widget.frame_lbl.btn.setDisabled(False)
            if self.config.get(AUTO, False):
                self.right_widget.frame_lbl.btn.setDisabled(True)
                self.wagon_image2 = qpixmap_to_ndarray(pixmap=pixmap)
        else:
            self.right_widget.frame_lbl.clear()

    def update_left_fps(self, fps: str):
        self.left_widget.frame_lbl.set_txt(txt=fps)

    def update_right_fps(self, fps: str):
        self.right_widget.frame_lbl.set_txt(txt=fps)

    def get_handle_data_left(self, data: dict):
        if max(self.last_scale_weight) < min_send_kg:
            return
        wn = data.get(wagonNumber)
        if wn and wn.count(identifier) == 1:
            wn = fix_luhn_code(wn)
        self.last_data_left[wagonNumber] = wn
        self.last_data_left[wagonAttachId] = data.get(wagonAttachId)
        self.last_data_left[wagonNumberAttachId] = data.get(wagonNumberAttachId)
        self.left_widget.frame_lbl.number_lbl.setText(str(wn))
        nid = self.last_data_left.get(wagonNumberAttachId)
        if isinstance(nid, np.ndarray):
            self.left_widget.frame_lbl.number_image_lbl.setPixmap(
                rounded_pixmap(cv2_to_qpixmap(cv_img=nid), radius=8))

    def get_handle_data_right(self, data: dict):
        if max(self.last_scale_weight) < min_send_kg:
            return
        wn = data.get(wagonNumber)
        if wn and wn.count(identifier) == 1:
            wn = fix_luhn_code(wn)
        self.last_data_right[wagonNumber] = wn
        self.last_data_right[wagonAttachId2] = data.get(wagonAttachId)
        self.last_data_right[wagonNumberAttachId] = data.get(wagonNumberAttachId)
        self.right_widget.frame_lbl.number_lbl.setText(str(wn))
        nid = self.last_data_right.get(wagonNumberAttachId)
        if isinstance(nid, np.ndarray):
            self.right_widget.frame_lbl.number_image_lbl.setPixmap(
                rounded_pixmap(cv2_to_qpixmap(cv_img=nid), radius=8))

    def get_auto_data_left(self, data: dict):
        try:
            if self.is_timeout or max(self.last_scale_weight) < min_send_kg:
                return
            track_id = data.get(t_id)
            wn = data.get(wagonNumber) or identifier * num_count
            if track_id is None or track_id in self.sent_left_track_ids:
                return
            if wn.count(identifier) == 1:
                wn = fix_luhn_code(wn)
            if wn in self.wagon_ids and wn != identifier * num_count:
                return
            self.sent_left_track_ids.append(track_id)
            self.wagon_id_image = data.get(wagonNumberAttachId)
            self.sending_data.wagonNumber = wn
            self.left_widget.frame_lbl.number_lbl.setText(wn)
            if isinstance(self.wagon_id_image, np.ndarray):
                self.left_widget.frame_lbl.number_image_lbl.setPixmap(
                    rounded_pixmap(cv2_to_qpixmap(cv_img=self.wagon_id_image), radius=8))
            self.sent_left_auto = True
            self.send_auto()
        except (Exception, ValueError) as err:
            log(message=f"[App.get_auto_data_left] {err}")

    def get_auto_data_right(self, data: dict):
        try:
            if self.is_timeout or max(self.last_scale_weight) < min_send_kg:
                return
            track_id = data.get(t_id)
            wn = data.get(wagonNumber) or identifier * num_count
            if track_id is None or track_id in self.sent_right_track_ids:
                return
            if wn.count(identifier) == 1:
                wn = fix_luhn_code(wn)
            if wn in self.wagon_ids and wn != identifier * num_count:
                return
            self.sent_right_track_ids.append(track_id)
            self.wagon_id_image = data.get(wagonNumberAttachId)
            self.sending_data.wagonNumber = wn
            self.right_widget.frame_lbl.number_lbl.setText(wn)
            if isinstance(self.wagon_id_image, np.ndarray):
                self.right_widget.frame_lbl.number_image_lbl.setPixmap(
                    rounded_pixmap(cv2_to_qpixmap(cv_img=self.wagon_id_image), radius=8))
            self.sent_right_auto = True
            self.send_auto()
        except (Exception, ValueError) as err:
            log(message=f"[App.get_auto_data_right] {err}")

    def get_error_message_left(self, msg: str):
        show_message(stl=self.style_name, message=f"Xatolik sodir bo'ldi. [Chap] \n{msg}")

    def get_error_message_right(self, msg: str):
        show_message(stl=self.style_name, message=f"Xatolik sodir bo'ldi. [O'ng] \n{msg}")
