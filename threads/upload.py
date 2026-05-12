from __future__ import annotations
import os
import time
from copy import deepcopy
from typing import Union, TYPE_CHECKING

import cv2
import numpy as np
import requests
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QPixmap

from core.config import (
    wagonNumber, wagonAttachId, wagonAttachId2, wagonNumberAttachId,
    scaleNumber, stationCode, scaleCode, createdDate, ID,
    identifier, num_count, backup_folder, post_url, timeout, log,
)
from core.database import BufferDB, current_time
from network.api import get_token, refresh_token, check_server, image_to_base64
from utils.image import qpixmap_to_ndarray
import sqlite3 as sql

if TYPE_CHECKING:
    from ui.models import SendingData


def _save_image(img: Union[np.ndarray, QPixmap, None], path: str) -> str | None:
    """Save an image (ndarray or QPixmap) to disk. Returns path on success, None on failure."""
    if img is None:
        return None
    if isinstance(img, QPixmap):
        img = qpixmap_to_ndarray(img)
    if isinstance(img, np.ndarray):
        cv2.imwrite(path, img)
        return path
    return None


class BackupUploadThread(QThread):
    upload_signal = pyqtSignal(bool, dict)
    error_signal = pyqtSignal(str)

    def __init__(self, login_data: dict, bs_url: str, login_url: str | None = None):
        super().__init__()
        self.login_data: dict = login_data
        self.bs_url: str = bs_url
        self.login_url: str | None = login_url
        self.backup_db = BufferDB()
        self.headers: dict = {
            "Authorization": f"Bearer {get_token(data=self.login_data, login_url=login_url)}",
            "Content-Type": "application/json",
        }

    def _refresh_token(self) -> bool:
        try:
            new_token = refresh_token(data=self.login_data, login_url=self.login_url)
            if new_token and new_token != "TOKEN_OLINMADI":
                self.headers["Authorization"] = f"Bearer {new_token}"
                return True
        except Exception as err:
            log(message=f"[BackupUploadThread._refresh_token] {err}")
        return False

    def run(self):
        try:
            dat, err = self.backup_db.get_all()
            if not dat:
                self.upload_signal.emit(False, {"error": err})
                return

            for dt in dat:
                try:
                    idx = int(dt.pop(ID))
                except (KeyError, ValueError):
                    idx = None

                dtx = deepcopy(dt)
                dt[scaleNumber] = int(dt.get(scaleNumber, 0))

                # Load images from file paths stored in DB
                for field in (wagonAttachId, wagonAttachId2, wagonNumberAttachId):
                    file_path = dt.get(field, "")
                    dt.pop(field, None)
                    if os.path.isfile(file_path) and file_path.endswith(".jpg"):
                        b64 = image_to_base64(img=cv2.imread(file_path))
                        if b64 is not None:
                            dt[field] = b64

                response = requests.post(
                    url=post_url, headers=self.headers,
                    json=dt, timeout=timeout,
                )
                self.headers.pop("Content-Type", None)

                # 401 bo'lsa token yangilab retry
                if response.status_code == 401:
                    log(message="[BackupUploadThread] 401 — token yangilanmoqda...", level="INFO")
                    if self._refresh_token():
                        response = requests.post(
                            url=post_url, headers=self.headers,
                            json=dt, timeout=timeout,
                        )

                try:
                    resp_json = response.json()
                except Exception as exc:
                    resp_json = f"Response: {exc}"

                error_msg = f"Response: {resp_json}"
                dtx["error"] = error_msg

                if response.status_code in (200, 201):
                    self.backup_db.delete(record_id=idx)
                else:
                    self.upload_signal.emit(False, dtx)
                    return

                log(message=error_msg, level="INFO")
                self.upload_signal.emit(response.status_code in (200, 201), dtx)

        except Exception as err:
            self.upload_signal.emit(False, {"error": f"[BackupUploadThread.run] {err}"})
            log(message=f"[BackupUploadThread.run] {err}")


class UploadThread(QThread):
    message_signal = pyqtSignal(bool, dict)
    progress_signal = pyqtSignal(int)

    def __init__(self, data: SendingData, img_id: Union[np.ndarray, None],
                 img_id2: Union[np.ndarray, None], img_number: Union[np.ndarray, None],
                 bs_url: str, login_data: dict, login_url: str | None = None):
        super().__init__()
        self.base_url: str = bs_url
        self.login_data: dict = login_data
        self.login_url: str | None = login_url
        self.backup_db = BufferDB()
        self.img_id = img_id
        self.img_id2 = img_id2
        self.img_number = img_number
        self.headers: dict = {
            "Authorization": f"Bearer {get_token(data=self.login_data, login_url=login_url)}",
            "Content-Type": "application/json",
        }
        self.data: dict = {
            wagonNumber: data.wagonNumber,
            scaleNumber: data.scaleNumber,
            stationCode: data.stationCode,
            scaleCode: data.scaleCode,
            createdDate: data.createdDate,
        }

    def _refresh_token(self) -> bool:
        """Token yangilaydi. Muvaffaqiyatli bo'lsa True qaytaradi."""
        try:
            new_token = refresh_token(data=self.login_data, login_url=self.login_url)
            if new_token and new_token != "TOKEN_OLINMADI":
                self.headers["Authorization"] = f"Bearer {new_token}"
                return True
        except Exception as err:
            log(message=f"[UploadThread._refresh_token] {err}")
        return False

    def _post(self) -> requests.Response:
        return requests.post(
            url=post_url, headers=self.headers,
            json=self.data, timeout=timeout,
        )

    def run(self):
        try:
            if not check_server(domain_name=self.base_url):
                for step in range(1, 5):
                    self.progress_signal.emit(step)
                    time.sleep(0.02)
                self._insert_to_db()
                return

            self.progress_signal.emit(1)
            url_id = image_to_base64(img=self.img_id)
            self.progress_signal.emit(2)
            url_id2 = image_to_base64(img=self.img_id2)
            self.progress_signal.emit(3)
            url_number = image_to_base64(img=self.img_number)

            if url_id is not None:
                self.data[wagonAttachId] = url_id
            if url_id2 is not None:
                self.data[wagonAttachId2] = url_id2
            if url_number is not None:
                self.data[wagonNumberAttachId] = url_number

            response = self._post()

            # 401 bo'lsa token yangilab bir marta retry
            if response.status_code == 401:
                log(message="[UploadThread] 401 — token yangilanmoqda...", level="INFO")
                if self._refresh_token():
                    response = self._post()

            try:
                js = f"Response: {response.json()}"
            except Exception:
                js = f"Response: {response.text}"

            log(message=f"[UploadThread.run] {js}", level="INFO")
            if response.status_code not in (200, 201):
                self._insert_to_db()
            self.progress_signal.emit(4)
            self.message_signal.emit(response.status_code in (200, 201), {"response": js})

        except Exception as err:
            log(message=f"[UploadThread.run] {err}")
            self._insert_to_db()
            self.progress_signal.emit(4)
            self.message_signal.emit(False, {"response": f"Xatolik yuz berdi. {err}"})
        finally:
            self.finished.emit()

    def _insert_to_db(self):
        try:
            if self.data.get(wagonNumber) is None:
                self.data[wagonNumber] = identifier * num_count
            os.makedirs(backup_folder, exist_ok=True)

            wagon_num = self.data.get(wagonNumber, identifier * num_count)
            ts = time.strftime("%Y-%m-%d_%H-%M-%S")

            # Save each image to backup folder
            for img, field, suffix in [
                (self.img_id,     wagonAttachId,        f"wagon_image_{ts}_{wagon_num}_1.jpg"),
                (self.img_id2,    wagonAttachId2,       f"wagon_image_{ts}_{wagon_num}_2.jpg"),
                (self.img_number, wagonNumberAttachId,  f"wagon_id_image_{ts}_{wagon_num}.jpg"),
            ]:
                path = _save_image(img, f"{backup_folder}/{suffix}")
                if path:
                    self.data[field] = path

            ans, err = self.backup_db.insert(data=self.data)

            if ans:
                log(message=f"[UploadThread._insert_to_db] Saved. {wagon_num}", level="INFO")
                self.message_signal.emit(True, {"response": "Success"})
            else:
                log(message=f"[UploadThread._insert_to_db] Insert error. {err}")
                self.message_signal.emit(False, {"response": f"Insert error: {err}"})
        except Exception as err:
            log(message=f"[UploadThread._insert_to_db] {err}")
            self.message_signal.emit(False, {"response": f"Insert error: {err}"})
