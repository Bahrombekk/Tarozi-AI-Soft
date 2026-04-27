from __future__ import annotations
from typing import Union
import cv2, os
import numpy as np
from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QPixmap, QPainter, QFont, QColor
from PyQt6.QtWidgets import (QDialog, QLabel, QVBoxLayout, QHBoxLayout,
                              QPushButton, QProgressBar, QScrollArea, QWidget,
                              QLineEdit)
from ui.styles import get_styles, get_text_color
from utils.image import cv2_to_qpixmap
from core.config import (timeout, log)
_default_font: str = "Arial"
try:
    from utils.helpers import SCREEN_WIDTH, SCREEN_HEIGHT, window_icon, no_image_pixmap
except Exception:
    SCREEN_WIDTH, SCREEN_HEIGHT = 1920, 1080
    window_icon = None; no_image_pixmap = None

# Late import to avoid circular dependency
def _get_hidden_edit_label_switch_widget():
    from ui.settings_panel import HiddenEditLabelSwitchWidget
    return HiddenEditLabelSwitchWidget

class ProgressBar(QDialog):

    def __init__(self):
        super().__init__()
        self.allow_close: bool = False
        self.setWindowTitle("Tasdiqlash")
        self.setContentsMargins(0, 0, 0, 0)
        self.resize(300, 150)
        self.setWindowIcon(window_icon)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.layout: QVBoxLayout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.lbl: QLabel = QLabel("Iltimos kutib turing.\n Tasdiqlanmoqda...")
        self.lbl.setObjectName("side_lbl")
        self.lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        self.progress: QProgressBar = QProgressBar()
        self.progress.setRange(0, 4)
        self.progress.setMinimumWidth(240)
        self.progress.setValue(0)
        self.layout.addWidget(self.lbl, alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        self.layout.addWidget(self.progress, alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)

    def showEvent(self, a0):
        self.progress.setValue(0)

        def cls():
            self.allow_close = True

        QTimer.singleShot(timeout * 1000, cls)

    def closeEvent(self, event):
        if self.allow_close:
            event.accept()
        else:
            event.ignore()

    def force_close(self):
        self.allow_close = True
        self.close()

    def change_style(self, style_name: str):
        stl: str = get_styles(style_name=style_name)
        self.setStyleSheet(stl)
        self.lbl.setStyleSheet(stl)
        self.progress.setStyleSheet(stl)



class ImageDialog(QDialog):

    def __init__(self, style_name: str, _title: str, pixmap: QPixmap | np.ndarray | str | None):
        super().__init__()
        self.setSizeGripEnabled(True)
        self.setWindowIcon(window_icon)
        self.setWindowTitle(_title)
        self.style_name: str = style_name
        self.style_: str = get_styles(style_name=self.style_name)
        self.setStyleSheet(self.style_)

        if pixmap is None:
            self.pix = no_image_pixmap

        if isinstance(pixmap, str):
            pixmap = pixmap.strip()
            if os.path.isfile(pixmap) and pixmap.endswith((".jpg", ".png", ".webp", ".jpeg")):
                self.pix: QPixmap = QPixmap(pixmap)
        if isinstance(pixmap, QPixmap):
            self.pix: QPixmap = pixmap
        if isinstance(pixmap, np.ndarray):
            self.pix: QPixmap = cv2_to_qpixmap(cv_img=pixmap)

        self.setContentsMargins(0, 0, 0, 0)
        self.setMaximumSize(int(SCREEN_WIDTH * 0.70), int(SCREEN_HEIGHT * 0.70))
        self.setMinimumSize(int(SCREEN_WIDTH * 0.40), int(SCREEN_HEIGHT * 0.40))

        if isinstance(self.pix, QPixmap):
            if self.width() > self.pix.width():
                self.scale_factor: float = 1.0
            else:
                self.scale_factor: float = 0.6
        else:
            self.scale_factor: float = 0.6
        self.offset_x = 0
        self.offset_y = 0
        self._drag_pos = None

    def paintEvent(self, a0):
        if not hasattr(self, "pix"):
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        scaled = self.pix.scaled(
            int(self.pix.width() * self.scale_factor),
            int(self.pix.height() * self.scale_factor),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        x = (self.width() - scaled.width()) // 2 + self.offset_x
        y = (self.height() - scaled.height()) // 2 + self.offset_y

        painter.drawPixmap(x, y, scaled)
        painter.end()

    def wheelEvent(self, event):
        angle = event.angleDelta().y()
        factor = 1.25 if angle > 0 else 0.8
        new_scale = self.scale_factor * factor

        if 0.2 < new_scale < 5:
            self.scale_factor = new_scale
            self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.position()

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None:
            diff = event.position() - self._drag_pos
            self.offset_x += int(diff.x())
            self.offset_y += int(diff.y())
            self._drag_pos = event.position()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = None



class ImageDialog2(QDialog):

    def __init__(self, style_name: str, _title: str, images: list[QPixmap | np.ndarray | str | None]):
        super().__init__()
        self.setSizeGripEnabled(True)
        self.setWindowIcon(window_icon)
        self.setWindowTitle(_title)
        self.style_name: str = style_name
        self.style_: str = get_styles(style_name=self.style_name)
        self.setStyleSheet(self.style_)

        self.pixmaps: list[QPixmap] = []
        for img in images:
            if img is None:
                continue
            elif isinstance(img, str):
                img = img.strip()
                if os.path.isfile(img) and img.endswith((".jpg", ".png", ".webp", ".jpeg")):
                    self.pixmaps.append(QPixmap(img))
            elif isinstance(img, QPixmap):
                self.pixmaps.append(img)
            elif isinstance(img, np.ndarray):
                self.pixmaps.append(cv2_to_qpixmap(cv_img=img))

        if not self.pixmaps:
            self.pixmaps.append(no_image_pixmap)

        self.current_index = 0
        self.pix = self.pixmaps[0]

        self.setContentsMargins(0, 0, 0, 0)
        self.setMaximumSize(int(SCREEN_WIDTH * 0.70), int(SCREEN_HEIGHT * 0.70))
        self.setMinimumSize(int(SCREEN_WIDTH * 0.40), int(SCREEN_HEIGHT * 0.40))

        if self.width() > self.pix.width():
            self.scale_factor: float = 1.0
        else:
            self.scale_factor: float = 0.4

        self.offset_x = 0
        self.offset_y = 0
        self._drag_pos = None

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Left, Qt.Key.Key_A):
            self.current_index = (self.current_index - 1) % len(self.pixmaps)
            self.pix = self.pixmaps[self.current_index]
            self.offset_x = 0
            self.offset_y = 0
            self.update()
        elif event.key() in (Qt.Key.Key_Right, Qt.Key.Key_D):
            self.current_index = (self.current_index + 1) % len(self.pixmaps)
            self.pix = self.pixmaps[self.current_index]
            self.offset_x = 0
            self.offset_y = 0
            self.update()

    def paintEvent(self, a0):
        try:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

            scaled = self.pix.scaled(
                int(self.pix.width() * self.scale_factor),
                int(self.pix.height() * self.scale_factor),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )

            x = (self.width() - scaled.width()) // 2 + self.offset_x
            y = (self.height() - scaled.height()) // 2 + self.offset_y

            painter.drawPixmap(x, y, scaled)

            painter.setPen(QColor(get_text_color(style_name=self.style_name)))
            painter.setFont(QFont(_default_font, 16, QFont.Weight.Bold))
            painter.drawText(10, 30, f"{self.current_index + 1}/{len(self.pixmaps)}")

            painter.end()
        except (Exception, RuntimeError) as e:
            print(f"[ImageDialog2.paintEvent] {e}")
            log(message=f"[ImageDialog2.paintEvent] {e}")

    def wheelEvent(self, event):
        angle = event.angleDelta().y()
        factor = 1.25 if angle > 0 else 0.8
        new_scale = self.scale_factor * factor

        if 0.2 < new_scale < 5:
            self.scale_factor = new_scale
            self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.position()

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None:
            diff = event.position() - self._drag_pos
            self.offset_x += int(diff.x())
            self.offset_y += int(diff.y())
            self._drag_pos = event.position()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = None



class PasswordDialog(QDialog):

    def __init__(self, style_name: str):
        super().__init__()
        self.force_close: bool = True
        self.style_name: str = style_name
        self.style_: str = get_styles(style_name=self.style_name)
        main_layout: QVBoxLayout = QVBoxLayout()
        main_layout.setSpacing(16)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        self.setFixedSize(int(SCREEN_WIDTH * 0.30), int(SCREEN_HEIGHT * 0.18))
        self.setLayout(main_layout)
        self.setObjectName("hidden_settings")
        self.setWindowTitle("Maxsus sozlamalar")
        self.setWindowIcon(window_icon)
        wx: int = int(SCREEN_WIDTH * 0.26)
        hy: int = int(SCREEN_HEIGHT * 0.075)

        HiddenEditLabelSwitchWidget = _get_hidden_edit_label_switch_widget()
        self.password: HiddenEditLabelSwitchWidget = HiddenEditLabelSwitchWidget(
            style_name=self.style_name,
            w=wx, h=hy,
        )
        self.password.edit.setContentsMargins(0, 15, 0, 0)

        self.password.lbl.setText("Parolni kiriting")
        self.password.edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.hidden_switch.stateChanged.connect(self.toggle_password)
        self.password.hidden_switch.setChecked(True)

        self.enter_btn: QPushButton = QPushButton("Kirish")
        self.enter_btn.setObjectName("save_btn")

        self.back_btn: QPushButton = QPushButton("Bekor qilish")
        self.back_btn.setObjectName("back_btn")

        h_lt: QHBoxLayout = QHBoxLayout()
        h_lt.setSpacing(16)
        h_lt.setContentsMargins(0, 0, 0, 0)
        h_lt.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)

        h_lt.addWidget(self.back_btn)
        h_lt.addWidget(self.enter_btn)

        main_layout.addWidget(self.password)
        main_layout.addLayout(h_lt)
        self.change_style(style_name=self.style_name)

    def toggle_password(self, ans: int):
        if ans == 2:
            self.password.edit.setEchoMode(QLineEdit.EchoMode.Password)
        else:
            self.password.edit.setEchoMode(QLineEdit.EchoMode.Normal)

    def change_style(self, style_name: str):
        self.style_name: str = style_name
        self.style_: str = get_styles(style_name=self.style_name)
        self.setStyleSheet(self.style_)

        self.enter_btn.setStyleSheet(self.style_)
        self.back_btn.setStyleSheet(self.style_)
        self.password.change_style(style_name=self.style_name)

