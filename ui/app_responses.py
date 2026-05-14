from __future__ import annotations

from PyQt6.QtCore import QTimer

from core.config import (
    log, AUTO, BTN_DISABLE, STATION_CODE, SCALE_CODE, SCALE_VIEW,
    default_station_code, default_scale_code, min_send_kg,
    wagonNumber, wagonAttachId, wagonAttachId2, wagonNumberAttachId,
    scaleNumber, createdDate, sentAt, stationCode, scaleCode,
)
from core.database import current_time
from threads.auto_video import AutoVideoThread
from ui.dialogs import ProgressBar
from utils.helpers import show_message


class ResponseMixin:

    def get_upload_response(self, ans: bool, data: dict):
        ttl = self.backup_db.get_total()
        self.status_widget.archive_count_lbl.setText(str(ttl))
        if not self.config.get(AUTO, False) and not self.config.get(BTN_DISABLE, False):
            QTimer.singleShot(3_000, lambda: self.right_widget.frame_lbl.btn.setDisabled(False))
            QTimer.singleShot(3_000, lambda: self.left_widget.frame_lbl.btn.setDisabled(False))
        if isinstance(self.progressbar, ProgressBar) and self.progressbar.isVisible():
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
                wagonAttachId: self.wagon_image, wagonAttachId2: self.wagon_image2,
                wagonNumberAttachId: self.wagon_id_image,
                scaleNumber: self.sending_data.scaleNumber,
            }
            dx_ = {
                wagonNumber: self.sending_data.wagonNumber,
                scaleNumber: self.sending_data.scaleNumber,
                createdDate: self.sending_data.createdDate,
                stationCode: self.config.get(STATION_CODE, default_station_code),
                scaleCode: self.config.get(SCALE_CODE, default_scale_code),
                wagonAttachId: self.wagon_image, wagonAttachId2: self.wagon_image2,
                wagonNumberAttachId: self.wagon_id_image,
            }
            if self.last_ttl == ttl:
                dx_[sentAt] = current_time()
                self.history_widget.add_row(data=dx_, sent=True)
            else:
                self.last_ttl = ttl
                self.history_widget.add_row(data=dx_)
            self.table.add_row(data=dx)
            self.last_scale_weight = [0]
            self.sending_data.clear()
            self.last_data_left = {}
            self.last_data_right = {}
            self.wagon_image = None
            self.wagon_id_image = None
        else:
            if self.config.get(AUTO, False):
                if self.sent_left_auto and self.sent_left_track_ids:
                    self.sent_left_track_ids.pop()
                elif self.sent_right_track_ids:
                    self.sent_right_track_ids.pop()
            self.sent_left_auto = False
            self.sent_right_auto = False
            self.upload_right = False
            self.upload_left = False
            self.is_timeout = False
            self.send_current_time = self.send_time
            self.hor_right_widget.right_lbl.setText(self.send_current_time)
            show_message(stl=self.style_name, message=f"Ma'lumot yuborilmadi. Tafsilotlar: {data}")

    def backup_upload_response(self, ans: bool, data: dict):
        if not self.config.get(AUTO, False) and not self.config.get(BTN_DISABLE, False):
            QTimer.singleShot(3_000, lambda: self.right_widget.frame_lbl.btn.setDisabled(False))
            QTimer.singleShot(3_000, lambda: self.left_widget.frame_lbl.btn.setDisabled(False))
        ttl = self.backup_db.get_total()
        self.last_ttl = ttl
        self.status_widget.archive_count_lbl.setText(str(ttl))
        if ans:
            dx = {wagonNumber: data.get(wagonNumber), wagonAttachId: data.get(wagonAttachId),
                  wagonAttachId2: data.get(wagonAttachId2),
                  wagonNumberAttachId: data.get(wagonNumberAttachId),
                  scaleNumber: data.get(scaleNumber)}
            self.table.add_row(data=dx)
            dx_ = {wagonNumber: self.sending_data.wagonNumber,
                   scaleNumber: self.sending_data.scaleNumber,
                   stationCode: self.sending_data.stationCode,
                   scaleCode: self.sending_data.scaleCode,
                   createdDate: self.sending_data.createdDate, sentAt: current_time(),
                   wagonAttachId: self.wagon_image, wagonAttachId2: self.wagon_image2,
                   wagonNumberAttachId: self.wagon_id_image}
            self.history_widget.add_row(data=dx_)
        else:
            err_msg = data.get('error', 'ERROR')
            show_message(stl=self.style_name,
                         message=f"Ma'lumot yuborilmadi. Tafsilotlar: {err_msg} {data}")

    def backup_upload_error(self, err: str):
        ttl = self.backup_db.get_total()
        self.last_ttl = ttl
        self.status_widget.archive_count_lbl.setText(str(ttl))
        show_message(stl=self.style_name,
                     message=f"Arxivdagi ma'lumotni yuborish amalga oshmadi. Tafsilotlar: {err}")
        if not self.config.get(AUTO, False):
            self.left_widget.frame_lbl.btn.setDisabled(False)
            self.right_widget.frame_lbl.btn.setDisabled(False)

    def scale_weight(self, massa: dict):
        try:
            if massa:
                ms = sum(massa.values())
                if min_send_kg > max(self.last_scale_weight):
                    self.sending_data.clear()
                    self.last_data_left = {}
                    self.last_data_right = {}
                    self.wagon_image = None
                    self.wagon_image2 = None
                    self.wagon_id_image = None
                    self.left_widget.frame_lbl.number_lbl.clear()
                    self.left_widget.frame_lbl.number_image_lbl.clear()
                    self.right_widget.frame_lbl.number_lbl.clear()
                    self.right_widget.frame_lbl.number_image_lbl.clear()
                if self.config.get(SCALE_VIEW, False):
                    sc_txt = f"{' + '.join([f'{k}({v})' for k, v in massa.items()])} = {ms} kg"
                else:
                    sc_txt = f"{' + '.join([f'{k}(*****)' for k in massa])} = ***** kg"
                self.hor_left_widget.right_lbl.setText(sc_txt)
                self.last_scale_weight.append(ms)
                if len(self.last_scale_weight) > self.max_scale_weight:
                    self.last_scale_weight.pop(0)
            else:
                if self.config.get("SCALE_DISABLE", False):
                    self.com_port_status = "O'chirilgan"
                elif not self.com_ports:
                    self.com_port_status = "COM port topilmadi"
                self.hor_left_widget.right_lbl.setText("0 kg")
        except (Exception, ValueError) as err:
            self.com_port_status = "Xatolik"
            log(message=f"[App.scale_weight] {err}")
