from __future__ import annotations
from typing import Union

import cv2
import numpy as np
from PyQt6.QtGui import QImage, QPixmap, QPainter, QPainterPath
from PyQt6.QtCore import QRectF, Qt, QSize


def qpixmap_to_ndarray(pixmap: QPixmap | np.ndarray | None) -> Union[np.ndarray, None]:
    if pixmap is None:
        return None
    if isinstance(pixmap, np.ndarray):
        return pixmap
    image: QImage = pixmap.toImage().convertToFormat(QImage.Format.Format_RGBA8888)
    width = image.width()
    height = image.height()
    ptr = image.bits()
    ptr.setsize(width * height * 4)
    arr = np.array(ptr, dtype=np.uint8).reshape((height, width, 4))  # RGBA
    bgr = cv2.cvtColor(arr, cv2.COLOR_RGBA2BGR)
    return bgr



def cv2_to_qpixmap(cv_img: np.ndarray, fmt: bool = False) -> QPixmap:
    height, width, channel = cv_img.shape
    bytes_per_line: int = channel * width
    cv_img: np.ndarray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)

    if fmt:
        q_image: QImage = QImage(cv_img.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)
        q_pixmap = QPixmap.fromImage(q_image)
        return q_pixmap
    q_image: QImage = QImage(cv_img.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)
    q_pixmap = QPixmap.fromImage(q_image).scaled(236, 48)
    return q_pixmap



def rounded_pixmap(pixmap: QPixmap, radius: int = 15) -> QPixmap:
    size: QSize = pixmap.size()
    rounded = QPixmap(size)
    rounded.fill(Qt.GlobalColor.transparent)

    painter: QPainter = QPainter(rounded)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    path: QPainterPath = QPainterPath()
    path.addRoundedRect(QRectF(0, 0, size.width(), size.height()), radius, radius)
    painter.setClipPath(path)
    painter.drawPixmap(0, 0, pixmap)
    painter.end()

    return rounded



def apply_clahe_bgr(img: np.ndarray) -> np.ndarray:
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)

    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    cl = clahe.apply(l)

    merged = cv2.merge((cl, a, b))
    enhanced_img = cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)
    return enhanced_img



def resize_img(img_res: np.ndarray, w: int | None = None) -> np.ndarray:
    if w is not None:
        img_res = cv2.resize(img_res, (w, int(w * img_res.shape[0] / img_res.shape[1])))
    return img_res



