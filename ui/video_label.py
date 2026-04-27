from __future__ import annotations
from PyQt6.QtCore import Qt, QSize, QRectF, pyqtProperty
from PyQt6.QtGui import QPixmap, QPainter, QColor, QPen, QFont
from PyQt6.QtWidgets import (QLabel, QVBoxLayout, QHBoxLayout, QPushButton,
                              QWidget, QSizePolicy)
from ui.styles import get_styles, get_text_color, get_text_bg_color, font
from ui.widgets import Switch, TransparentWidget
from utils.image import rounded_pixmap
from core.config import (width_scale, height_scale, identifier, num_count, LIGHT, log)
try:
    from utils.helpers import SCREEN_WIDTH, SCREEN_HEIGHT, cam_frame, cam_frame_light
except Exception:
    SCREEN_WIDTH, SCREEN_HEIGHT = 1920, 1080
    cam_frame = cam_frame_light = None

class AspectRatioLabel(QLabel):

    def __init__(self, style_name: str, w_ratio: int = width_scale, h_ratio: int = height_scale,
                 balloon_rect: tuple[int | None, int | None, int | None, int | None] = (None, None, None, None),
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.style_name: str = style_name
        self.style_: str = get_styles(style_name=self.style_name)
        self._w_ratio: int = w_ratio
        self._h_ratio: int = h_ratio
        self.is_pix: bool = False
        self.draw_text: str = ""
        self.balloon_color: QColor = QColor("#42f7c0")
        self._text_bg_color: QColor = QColor(get_text_bg_color(style_name=self.style_name))
        self._text_color: QColor = QColor(get_text_color(style_name=self.style_name))
        self.line_width: int = 2
        self.balloon_rect: tuple[int | None, int | None, int | None, int | None] = balloon_rect
        lt: QVBoxLayout = QVBoxLayout()
        h_lt: QHBoxLayout = QHBoxLayout()
        lt.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom)

        row_lt: QHBoxLayout = QHBoxLayout()
        self.center_lt: QVBoxLayout = QVBoxLayout()
        self.center_lt.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        self.center_lt.setSpacing(1)

        self.row_widget: TransparentWidget = TransparentWidget()
        self.row_widget.setLayout(row_lt)
        self.row_widget.setFixedHeight(max(40, int(SCREEN_HEIGHT * 0.065)))
        self.row_widget.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed))

        wx2: int = int(SCREEN_WIDTH * 0.1)
        hy2: int = int(SCREEN_HEIGHT * 0.045)

        self.toggle_icon_lbl: QLabel = QLabel()
        self.toggle_icon_lbl.setObjectName("toggle_lbl")
        self.toggle_icon_lbl.setFixedSize(int(SCREEN_HEIGHT * 0.06), int(SCREEN_HEIGHT * 0.06))
        self.toggle_icon_lbl.setScaledContents(True)

        self.toggle_lbl: QLabel = QLabel("Kamera o'chirilgan")
        self.toggle_lbl.setObjectName("toggle_lbl")

        self.center_lt.addWidget(self.toggle_icon_lbl, 2,
                                 alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom)
        self.center_lt.addWidget(self.toggle_lbl, 2,
                                 alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)

        lt.addLayout(self.center_lt)
        lt.addLayout(h_lt)
        h_lt.addWidget(self.row_widget, 1)

        self.number_text_lbl: QLabel = QLabel("Vagon raqami")
        self.number_text_lbl.setObjectName("number_text")
        self.number_text_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.number_image_lbl: QLabel = QLabel()
        self.number_image_lbl.setObjectName("number_image")
        self.number_image_lbl.setFixedSize(QSize(wx2, hy2))
        self.number_image_lbl.setScaledContents(True)

        self.number_lbl: QLabel = QLabel(identifier * num_count)
        self.number_lbl.setObjectName("number")
        self.number_lbl.setFixedSize(QSize(wx2, hy2))
        self.number_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.btn: QPushButton = QPushButton("Tasdiqlash")
        self.btn.setObjectName("save_btn")

        row_lt.addWidget(self.number_text_lbl, alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        row_lt.addSpacing(16)
        row_lt.addWidget(self.number_image_lbl)
        row_lt.addSpacing(16)
        row_lt.addWidget(self.number_lbl, alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        row_lt.addSpacing(16)
        row_lt.addWidget(self.btn, alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.setScaledContents(False)  # paintEvent handles scaling with aspect ratio preserved
        policy: QSizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Ignored)
        self.setLayout(lt)
        self.setSizePolicy(policy)

    def clear(self):
        self.is_pix: bool = False
        self.row_widget.hide()
        self.toggle_lbl.show()
        self.toggle_icon_lbl.show()
        super().clear()

    def toggle_fps(self, view: bool):
        if view:
            self.draw_text = "FPS: 0.0"
        else:
            self.draw_text = ""
        self.update()

    def change_style(self, style_name: str):
        self.style_name: str = style_name
        self.style_: str = get_styles(style_name=self.style_name)
        self._text_bg_color: QColor = QColor(get_text_bg_color(style_name=self.style_name))
        self._text_color: QColor = QColor(get_text_color(style_name=self.style_name))
        self.setStyleSheet(self.style_)
        self.toggle_lbl.setStyleSheet(self.style_)
        self.toggle_icon_lbl.setStyleSheet(self.style_)
        self.btn.setStyleSheet(self.style_)
        if self.style_name == LIGHT:
            self.toggle_icon_lbl.setPixmap(cam_frame)
        else:
            self.toggle_icon_lbl.setPixmap(cam_frame_light)

    def set_lines(self, balloon_rect: tuple[int | None, int | None, int | None, int | None] = (None, None, None, None)):
        self.balloon_rect = balloon_rect
        self.update()

    def set_txt(self, txt: str):
        self.draw_text: str = txt
        self.update()

    def setPixmap(self, a0: QPixmap):
        frame_lbl_width: int = self.width()
        pixmap_width: int = a0.width()
        radius: int = int(pixmap_width * 16 / frame_lbl_width)
        a0 = rounded_pixmap(a0, radius=radius)
        self.is_pix: bool = True
        if self.toggle_lbl.isVisible():
            self.row_widget.show()
            self.toggle_lbl.hide()
            self.toggle_icon_lbl.hide()

        super().setPixmap(a0)

    def paintEvent(self, event):
        painter: QPainter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # Draw pixmap scaled to fill label keeping aspect ratio
        pix = self.pixmap()
        if pix and not pix.isNull():
            scaled = pix.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio,
                                Qt.TransformationMode.SmoothTransformation)
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)

        balloon_top, balloon_left, balloon_bottom, balloon_right = self.balloon_rect

        w: int = self.width()
        h: int = self.height()

        if all([r is not None for r in self.balloon_rect]):
            balloon_left_px = int(w * balloon_left / 100)
            balloon_right_px = w - int(w * balloon_right / 100)
            balloon_top_px = int(h * balloon_top / 100)
            balloon_bottom_px = h - int(h * balloon_bottom / 100)

            balloon_pen = QPen(QColor(self.balloon_color))
            balloon_pen.setWidth(self.line_width)
            painter.setPen(balloon_pen)

            painter.drawRoundedRect(balloon_left_px, balloon_top_px, balloon_right_px - balloon_left_px,
                                    balloon_bottom_px - balloon_top_px, 6, 6)
        if self.draw_text:
            painter.setFont(QFont(font, 10, weight=QFont.Weight.Bold))

            metrics = painter.fontMetrics()
            text_width = metrics.horizontalAdvance(self.draw_text)
            text_height = metrics.height()
            ascent = metrics.ascent()

            padding = 4
            rect_x = 10 - padding
            rect_y = 24 - ascent - padding
            rect_w = text_width + padding * 3
            rect_h = text_height + padding * 2

            painter.setBrush(QColor(self._text_bg_color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(rect_x, rect_y, rect_w, rect_h, 6, 6)

            painter.setPen(QColor(self._text_color))
            painter.drawText(10, 24, self.draw_text)

        painter.end()

    def resizeEvent(self, event):
        if self.is_pix:
            self.row_widget.show()
            self.toggle_lbl.hide()
            self.toggle_icon_lbl.hide()
        else:
            self.row_widget.hide()
            self.toggle_lbl.show()
            self.toggle_icon_lbl.show()

        # Maintain aspect ratio, but cap at 52% of screen height
        w = event.size().width()
        ideal_h = int(w * self._h_ratio / self._w_ratio)
        max_h = int(SCREEN_HEIGHT * 0.52)
        h = min(ideal_h, max_h)
        if h != self.height():
            self.setFixedHeight(h)

        super().resizeEvent(event)


class SideWidget(QWidget):

    def __init__(self, style_name: str):
        super().__init__()
        self.style_name: str = style_name
        self.style_: str = get_styles(style_name=self.style_name)
        self.lt: QVBoxLayout = QVBoxLayout()
        self.h_lt: QHBoxLayout = QHBoxLayout()
        self.setLayout(self.lt)
        self.setObjectName("side_widget")
        self.setMinimumWidth(200)  # just enough to be usable, layout handles the rest
        self.lt.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignTop)
        self.lt.setSpacing(15)
        self.h_lt.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)

        self.state_lbl: QLabel = QLabel()
        self.state_lbl.setObjectName("state_lbl")
        self.state_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignCenter)

        self.side_lbl: QLabel = QLabel()
        self.side_lbl.setObjectName("side_lbl")
        self.side_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        self.switch: Switch = Switch(
            style_name=self.style_name,
            size=45,
        )

        self.frame_lbl: AspectRatioLabel = AspectRatioLabel(
            style_name=self.style_name,
        )
        self.frame_lbl.setObjectName("frame_lbl")

        self.lt.addLayout(self.h_lt, 1)
        self.lt.addWidget(self.frame_lbl, 10)
        self.lt.addStretch(1)
        self.h_lt.addWidget(self.side_lbl, 99, alignment=Qt.AlignmentFlag.AlignLeft)
        self.h_lt.addWidget(self.state_lbl, 1)
        self.h_lt.addWidget(self.switch, alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setContentsMargins(10, 10, 10, 10)

    def change_style(self, style_name: str):
        self.style_name: str = style_name
        self.style_: str = get_styles(style_name=self.style_name)
        self.setStyleSheet(self.style_)
        self.switch.change_style(style_name=self.style_name)
        self.frame_lbl.change_style(style_name=self.style_name)
        self.side_lbl.setStyleSheet(self.style_)
        self.state_lbl.setStyleSheet(self.style_)

