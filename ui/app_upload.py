from __future__ import annotations

from copy import deepcopy

import numpy as np

from core.config import (
    log, identifier, num_count,
    AUTO, BTN_DISABLE, SCALE_CODE, STATION_CODE,
    USERNAME, PASSWORD, BASE_URL, UPLOAD_URL, LOGIN_URL,
    default_station_code, default_scale_code, default_username, default_password,
    post_url, base_url, get_token_url, min_send_kg,
    wagonNumber, wagonAttachId, wagonAttachId2, wagonNumberAttachId,
)
from core.database import current_time, BufferDB
from threads.upload import UploadThread
from ui.dialogs import ProgressBar, RepeatWagonDialog
from PyQt6.QtWidgets import QDialog
from utils.helpers import show_message
from utils.image import qpixmap_to_ndarray


def _fmt_time(iso: str) -> str:
    """'2026-05-12T13:12:01Z' (UTC) → lokal vaqt '18:12:01'"""
    try:
        import datetime as _dt
        utc_dt = _dt.datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=_dt.timezone.utc)
        return utc_dt.astimezone().strftime("%H:%M:%S")
    except Exception:
        try:
            return iso.split("T")[1].replace("Z", "").split(".")[0]
        except Exception:
            return iso


class UploadMixin:

    def _get_img_left(self):
        if isinstance(self.last_data_left.get(wagonAttachId), np.ndarray):
            return deepcopy(self.last_data_left[wagonAttachId])
        return qpixmap_to_ndarray(pixmap=self.last_image_left)

    def _get_img_right(self):
        if isinstance(self.last_data_right.get(wagonAttachId2), np.ndarray):
            return deepcopy(self.last_data_right[wagonAttachId2])
        return qpixmap_to_ndarray(pixmap=self.last_image_right)

    def _get_id_img_left(self):
        if isinstance(self.last_data_left.get(wagonNumberAttachId), np.ndarray):
            return deepcopy(self.last_data_left[wagonNumberAttachId])
        return None

    def _get_id_img_right(self):
        if isinstance(self.last_data_right.get(wagonNumberAttachId), np.ndarray):
            return deepcopy(self.last_data_right[wagonNumberAttachId])
        return None

    def _wagon_num_left(self) -> str:
        return self.last_data_left.get(wagonNumber) or identifier * num_count

    def _wagon_num_right(self) -> str:
        return self.last_data_right.get(wagonNumber) or identifier * num_count

    def upload_handle_data_left(self):
        if max(self.last_scale_weight) > min_send_kg:
            if self.video_thread_left and self.video_thread_left.running:
                wn = self._wagon_num_left()
                if wn in self.wagon_ids and identifier not in wn:
                    rec = BufferDB().get_today_wagon(wn)
                    dlg = RepeatWagonDialog(
                        style_name=self.style_name,
                        wagon_number=wn,
                        weighed_at=_fmt_time(rec["createdDate"]) if rec else None,
                        weight_kg=str(rec["scaleNumber"]) if rec else None,
                    )
                    if dlg.exec() != QDialog.DialogCode.Accepted:
                        return
                self.wagon_ids.append(wn)
                self.progressbar = ProgressBar()
                self.progressbar.change_style(style_name=self.style_name)
                self.progressbar.show()
                self.upload_left = True
                self.send()
            else:
                show_message(stl=self.style_name, message="Kamera ishga tushirilmagan.")
        else:
            show_message(stl=self.style_name,
                         message=f"O'lchash uchun minimal og'irlik: {min_send_kg:,} kg.")

    def upload_handle_data_right(self):
        if max(self.last_scale_weight) > min_send_kg:
            if self.video_thread_right and self.video_thread_right.running:
                wn = self._wagon_num_right()
                if wn in self.wagon_ids and identifier not in wn:
                    rec = BufferDB().get_today_wagon(wn)
                    dlg = RepeatWagonDialog(
                        style_name=self.style_name,
                        wagon_number=wn,
                        weighed_at=_fmt_time(rec["createdDate"]) if rec else None,
                        weight_kg=str(rec["scaleNumber"]) if rec else None,
                    )
                    if dlg.exec() != QDialog.DialogCode.Accepted:
                        return
                self.wagon_ids.append(wn)
                self.progressbar = ProgressBar()
                self.progressbar.change_style(style_name=self.style_name)
                self.progressbar.show()
                self.upload_right = True
                self.send()
            else:
                show_message(stl=self.style_name, message="Kamera ishga tushirilmagan.")
        else:
            show_message(stl=self.style_name,
                         message=f"O'lchash uchun minimal og'irlik: {min_send_kg:,} kg.")

    def _build_upload_thread(self, img, img2, img_num) -> UploadThread:
        return UploadThread(
            data=self.sending_data, img_id=img, img_id2=img2, img_number=img_num,
            bs_url=self.config.get(BASE_URL, base_url),
            login_data={"login": self.config.get(USERNAME, default_username),
                        "password": self.config.get(PASSWORD, default_password)},
            login_url=self.config.get(LOGIN_URL, get_token_url),
        )

    def send(self):
        try:
            if not self.config.get(AUTO, False):
                self.left_widget.frame_lbl.btn.setDisabled(True)
                self.right_widget.frame_lbl.btn.setDisabled(True)
            if max(self.last_scale_weight) <= min_send_kg:
                show_message(stl=self.style_name,
                             message=f"O'lchash uchun minimal og'irlik: {min_send_kg:,} kg.")
                if not self.config.get(AUTO, False):
                    self.left_widget.frame_lbl.btn.setDisabled(False)
                    self.right_widget.frame_lbl.btn.setDisabled(False)
                return
            wn_l = self._wagon_num_left()
            wn_r = self._wagon_num_right()
            if wn_l.count(identifier) == wn_r.count(identifier) == num_count:
                self._send_unrec()
                return
            img = self._get_img_left()
            img2 = self._get_img_right()
            if self.upload_right:
                if wn_r.count(identifier) <= wn_l.count(identifier):
                    self.sending_data.wagonNumber = wn_r
                    img_num = self._get_id_img_right()
                else:
                    self.sending_data.wagonNumber = wn_l
                    img_num = self._get_id_img_left()
            else:
                if wn_r.count(identifier) >= wn_l.count(identifier):
                    self.sending_data.wagonNumber = wn_l
                    img_num = self._get_id_img_left()
                else:
                    self.sending_data.wagonNumber = wn_r
                    img_num = self._get_id_img_right()
            self.sending_data.scaleNumber = max(self.last_scale_weight)
            self.sending_data.stationCode = self.config.get(STATION_CODE, default_station_code)
            self.sending_data.scaleCode = self.config.get(SCALE_CODE, default_scale_code)
            self.sending_data.createdDate = current_time()
            self.upload_thread = self._build_upload_thread(img, img2, img_num)
            self.upload_thread.message_signal.connect(self.get_upload_response)
            self.upload_thread.progress_signal.connect(self.fake_progressbar)
            self.upload_thread.start()
            self.upload_right = False
            self.upload_left = False
        except (Exception, ValueError) as err:
            log(message=f"[App.send] {err}")

    def _send_unrec(self):
        self.wagon_image = self._get_img_left()
        self.wagon_image2 = self._get_img_right()
        self.wagon_id_image = (self._get_id_img_left() if self.upload_right
                               else self._get_id_img_right())
        self.sending_data.wagonNumber = identifier * num_count
        self.sending_data.scaleNumber = max(self.last_scale_weight)
        self.sending_data.stationCode = self.config.get(STATION_CODE, default_station_code)
        self.sending_data.scaleCode = self.config.get(SCALE_CODE, default_scale_code)
        self.sending_data.createdDate = current_time()
        self.upload_thread = self._build_upload_thread(
            self.wagon_image, self.wagon_image2, self.wagon_id_image)
        self.upload_thread.message_signal.connect(self.get_upload_response)
        self.upload_thread.progress_signal.connect(self.fake_progressbar)
        self.upload_thread.start()
        self.upload_right = False
        self.upload_left = False

    def send_auto(self):
        try:
            self.sending_data.scaleNumber = max(self.last_scale_weight)
            self.sending_data.stationCode = self.config.get(STATION_CODE, default_station_code)
            self.sending_data.scaleCode = self.config.get(SCALE_CODE, default_scale_code)
            self.sending_data.createdDate = current_time()
            self.upload_thread = self._build_upload_thread(
                self.wagon_image, self.wagon_image2, self.wagon_id_image)
            self.upload_thread.message_signal.connect(self.get_upload_response)
            self.upload_thread.progress_signal.connect(self.fake_progressbar)
            self.upload_thread.start()
            self.is_timeout = True
            if self.video_thread_left:
                self.video_thread_left.is_timeout = True
            if self.video_thread_right:
                self.video_thread_right.is_timeout = True
            self.send_current_time = self.send_time
        except (Exception, ValueError) as err:
            log(message=f"[App.send_auto] {err}")
