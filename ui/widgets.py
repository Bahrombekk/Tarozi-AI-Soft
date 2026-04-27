from __future__ import annotations
from PyQt6.QtCore import (Qt, QSize, QPoint, QRect, QPropertyAnimation,
                           QEasingCurve, pyqtProperty, QEvent, QObject)
from PyQt6.QtGui import (QIcon, QPixmap, QPainter, QColor, QMouseEvent, QCursor)
from PyQt6.QtWidgets import (
    QCheckBox, QLineEdit, QPushButton, QWidget, QLabel,
    QVBoxLayout, QHBoxLayout, QSizePolicy, QGraphicsBlurEffect, QDialog
)
from ui.styles import get_styles, get_bg_color, get_hover_color, get_text_color
from core.config import window_title, LIGHT, DARK
try:
    from utils.helpers import (SCREEN_WIDTH, SCREEN_HEIGHT, WIDTH, HEIGHT,
                                window_icon, window_pixmap,
                                view_icon, unview_icon, view_icon_light, unview_icon_light,
                                fail_icon, success_icon, no_image_pixmap,
                                cam_frame, cam_frame_light, weight_pixmap, time_pixmap,
                                icon_size, icon_size1, icon_size4, item_height, verbose)
except Exception:
    SCREEN_WIDTH, SCREEN_HEIGHT, WIDTH, HEIGHT = 1920, 1080, 1536, 886
    window_icon = window_pixmap = fail_icon = success_icon = no_image_pixmap = None
    cam_frame = cam_frame_light = weight_pixmap = time_pixmap = None
    view_icon = unview_icon = view_icon_light = unview_icon_light = None
    icon_size = QSize(28, 28); icon_size1 = QSize(32, 32); icon_size4 = QSize(86, 42)
    item_height = 80; verbose = False


class _GlobalMouseReleaseFilter(QObject):
    def __init__(self, parent):
        super().__init__(parent)

    def eventFilter(self, obj, ev):
        if ev.type() == QEvent.Type.MouseButtonRelease:
            self.parent().eventFilter(self.parent(), ev)
            return False
        return super().eventFilter(obj, ev)

class ClickableQLineEdit(QLineEdit):

    def __init__(self, ty: str = "cs"):
        super().__init__()
        self.ty: str = ty
        self.installEventFilter(self)

    def eventFilter(self, source, event):
        if self.ty == "cs":
            if source == self and event.type() == QEvent.Type.MouseButtonPress:
                if (isinstance(event, QMouseEvent) and
                        event.button() == Qt.MouseButton.LeftButton and
                        event.modifiers() & Qt.KeyboardModifier.ControlModifier and
                        event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
                    self.setDisabled(False)
                    return True
        if self.ty == "ca":
            if source == self and event.type() == QEvent.Type.MouseButtonPress:
                if (isinstance(event, QMouseEvent) and
                        event.button() == Qt.MouseButton.LeftButton and
                        event.modifiers() & Qt.KeyboardModifier.ControlModifier and
                        event.modifiers() & Qt.KeyboardModifier.AltModifier):
                    self.setDisabled(False)
                    return True
        return super().eventFilter(source, event)


class HoverIconButton(QPushButton):

    def __init__(self, icon: QIcon, size: int = 40, eye_icon: QIcon = None, parent=None):
        super().__init__(parent)
        self.setIcon(icon)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        lt: QVBoxLayout = QVBoxLayout()
        lt.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        self.setLayout(lt)

        self.eye_label: QLabel = QLabel()
        lt.addWidget(self.eye_label)
        if eye_icon is None:
            self.eye_label.setPixmap(QPixmap("images/unview_eye.png").scaled(
                size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            ))
        else:
            self.eye_label.setPixmap(eye_icon.pixmap(size, size))

        self.eye_label.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        self.eye_label.setStyleSheet(
            "background-color: rgba(255, 255, 255, 80); border-radius: 12px; padding: 0px; margin: 0px;")
        self.eye_label.setVisible(False)

    def enterEvent(self, event):
        self.eye_label.setVisible(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.eye_label.setVisible(False)
        super().leaveEvent(event)



class Switch(QCheckBox):

    def __init__(self, style_name: str, parent=None, size: int = 60):
        super().__init__(parent)
        self.style_name: str = style_name
        self.style_: str = get_styles(style_name=self.style_name)
        self._width = size + 5
        self._height = int(size * 0.55)
        self._margin = int(size * 0.07)
        self._circle_diameter = self._height - 2 * self._margin
        self._off_position = self._margin
        self._on_position = self._width - self._circle_diameter - self._margin - 10
        self.setFixedSize(self._width, self._height)
        self._handle_position = self._off_position
        self._animation = QPropertyAnimation(self, b"handle_position", self)
        self._animation.setDuration(200)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.stateChanged.connect(self.start_transition)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

    def change_style(self, style_name: str):
        self.style_name: str = style_name
        self.style_: str = get_styles(style_name=self.style_name)
        self.setStyleSheet(self.style_)

    def hitButton(self, pos: QPoint) -> bool:
        return QRect(0, 0, self.width(), self.height()).contains(pos)

    def start_transition(self, value):
        self._animation.stop()
        self._animation.setEndValue(self._on_position if value == Qt.CheckState.Checked.value else self._off_position)
        self._animation.start()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        effective_rect = self.rect().adjusted(0, 0, -10, 0)
        if not self.isEnabled():
            bg_color = QColor("#f00")
        elif self.isChecked():
            bg_color = QColor("#007CF0")
            # bg_color = QColor("#20F3A5")
        else:
            bg_color = QColor("#ccc")
        painter.setBrush(bg_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(effective_rect, self._height / 2, self._height / 2)
        painter.setBrush(QColor("white"))
        painter.drawEllipse(int(self._handle_position), self._margin, self._circle_diameter, self._circle_diameter)
        painter.end()

    def get_handle_position(self):
        return self._handle_position

    def set_handle_position(self, pos):
        self._handle_position = pos
        self.update()

    handle_position = pyqtProperty(int, fget=get_handle_position, fset=set_handle_position)



class HiddenSwitch(QCheckBox):

    def __init__(self, style_name: str, parent=None, size: int = 60):
        super().__init__(parent)
        self.style_name: str = style_name
        self.style_: str = get_styles(style_name=self.style_name)
        self._width = size + 5
        self._height = int(size * 0.55)
        self._margin = int(size * 0.07)
        self._circle_diameter = self._height - 2 * self._margin
        self._off_position = self._margin
        self._on_position = self._width - self._circle_diameter - self._margin - 10

        self._on_bg_color: QColor = QColor("#007CF0")
        self._off_bg_color: QColor = QColor("#ccc")
        self._dis_bg_color: QColor = QColor("#f00")

        self.setFixedSize(self._width, self._height)
        self._handle_position = self._off_position

        self._animation = QPropertyAnimation(self, b"handle_position", self)
        self._animation.setDuration(200)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        self.stateChanged.connect(self.start_transition)

    def change_style(self, style_name: str):
        self.style_name: str = style_name
        self.style_: str = get_styles(style_name=self.style_name)
        self._on_bg_color: QColor = QColor("#007CF0")
        self._off_bg_color: QColor = QColor("#ccc")
        self._dis_bg_color: QColor = QColor("#f00")
        self.update()

    def start_transition(self, value):
        if value == Qt.CheckState.Checked.value:
            self._animation.setEndValue(self._on_position)
        else:
            self._animation.setEndValue(self._off_position)
        self._animation.start()

    def paintEvent(self, event):
        painter: QPainter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        effective_rect = self.rect().adjusted(0, 0, -10, 0)

        if not self.isEnabled():
            bg_color = self._dis_bg_color
        elif self.isChecked():
            bg_color = self._on_bg_color
        else:
            bg_color = self._off_bg_color

        painter.setBrush(bg_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(effective_rect, self._height / 2, self._height / 2)

        painter.setBrush(QColor("white"))
        painter.drawEllipse(int(self._handle_position), self._margin, self._circle_diameter, self._circle_diameter)
        painter.end()

    def get_handle_position(self):
        return self._handle_position

    def set_handle_position(self, pos):
        self._handle_position = pos
        self.update()

    def mousePressEvent(self, event):
        event.accept()

    def mouseReleaseEvent(self, event):
        self.setChecked(not self.isChecked())
        self.clicked.emit(self.isChecked())

    handle_position = pyqtProperty(int, fget=get_handle_position, fset=set_handle_position)



class TransparentWidget(QWidget):

    def __init__(self, bd: str = "none", pd: str = "0px", mn: int = 2, rd: int = 16,
                 name: str = "none"):
        super().__init__()
        self.setObjectName("transparent_widget")
        self.setStyleSheet("""
            QWidget#transparent_widget {{
                background: transparent;
                border-radius: 30px;
            }}
        """)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.bg_layer: QWidget = QWidget(self)
        self.bg_layer.setObjectName(f"bg_layer_{name}")
        self.bg_layer.setStyleSheet(f"""
                QWidget#bg_layer_{name} {{
                    background: rgba(0, 10, 25, 190);
                    border-radius: {rd}px;
                    border: 1px solid {bd};
                    padding: {pd};
                    margin: 0px;
                }}
            """
                                    )
        self.bg_layer.setGeometry(0, 0, self.width(), self.height())

        self.content_layer: QWidget = QWidget(self)
        self.content_layer.setGeometry(0, 0, self.width(), self.height())
        self.content_layer.setObjectName("content_layer")
        self.content_layer.setStyleSheet("""
            QWidget#content_layer {
                background: transparent;
                border-radius: 16px;
            }
        """
                                         )
        self.setContentsMargins(mn, mn, mn, mn)

    def resizeEvent(self, event):
        self.bg_layer.setGeometry(self.rect())
        self.content_layer.setGeometry(self.rect())
        super().resizeEvent(event)



class HorizontalWidget(QWidget):

    def __init__(self, style_name: str):
        super().__init__()
        self.style_name: str = style_name
        self.style_: str = get_styles(style_name=self.style_name)
        lt: QHBoxLayout = QHBoxLayout()
        self.setLayout(lt)

        self.setObjectName("horizontal_widget")

        self.left_icon_lbl: QLabel = QLabel()
        self.left_icon_lbl.setObjectName("left_icon_lbl")
        self.left_icon_lbl.setFixedSize(QSize(int(SCREEN_HEIGHT * 0.05) + 12, int(SCREEN_HEIGHT * 0.05)))
        self.left_icon_lbl.setScaledContents(True)
        self.left_icon_lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)

        self.center_lbl: QLabel = QLabel()
        self.center_lbl.setObjectName("center_lbl")

        self.right_lbl: QLabel = QLabel()
        self.right_lbl.setObjectName("right_lbl")

        lt.addWidget(self.left_icon_lbl, alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        lt.addWidget(self.center_lbl, alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        lt.addWidget(self.right_lbl, alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.setFixedHeight(int(SCREEN_HEIGHT * 0.075))
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

    def change_style(self, style_name: str):
        self.style_name: str = style_name
        self.style_: str = get_styles(style_name=self.style_name)
        self.setStyleSheet(self.style_)
        self.left_icon_lbl.setStyleSheet(self.style_)
        self.center_lbl.setStyleSheet(self.style_)
        self.right_lbl.setStyleSheet(self.style_)



class StatusWidget(QWidget):

    def __init__(self, style_name: str):
        super().__init__()
        self.style_name: str = style_name
        self.style_: str = get_styles(style_name=self.style_name)
        self.lt: QHBoxLayout = QHBoxLayout()

        self.setObjectName("status_widget")
        self.setContentsMargins(0, 0, 0, 0)
        self.lt.setContentsMargins(0, 0, 0, 0)

        self.archive_count_lbl: QLabel = QLabel("0")
        self.archive_count_lbl.setObjectName("archive")
        self.archive_count_lbl.setFixedSize(QSize(60, 32))
        self.archive_count_lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)

        self.status_btn: QPushButton = QPushButton()
        self.status_btn.setIconSize(QSize(28, 28))
        self.status_btn.setFixedSize(QSize(36, 36))
        self.status_btn.setIcon(fail_icon)
        self.status_btn.setObjectName("status_btn")

        self.lt.addWidget(self.status_btn, alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.lt.addWidget(self.archive_count_lbl, alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.setLayout(self.lt)

    def change_style(self, style_name: str):
        self.style_name: str = style_name
        self.style_: str = get_styles(style_name=self.style_name)
        self.setStyleSheet(self.style_)
        self.status_btn.setStyleSheet(self.style_)
        self.archive_count_lbl.setStyleSheet(self.style_)



class Title(QWidget):

    def __init__(self, style_name: str):
        super().__init__()
        self.style_name: str = style_name
        self.style_: str = get_styles(style_name=self.style_name)
        self.lt: QHBoxLayout = QHBoxLayout()

        self.window_icon_lbl: QLabel = QLabel(window_title)
        self.window_icon_lbl.setObjectName("icon_lbl")
        self.window_icon_lbl.setFixedSize(icon_size4)
        self.window_icon_lbl.setScaledContents(True)
        self.window_icon_lbl.setPixmap(window_pixmap)

        self.title_lbl: QLabel = QLabel(window_title)
        self.title_lbl.setObjectName("title_lbl")

        self.exit_btn: QPushButton = QPushButton("×")
        self.full_btn: QPushButton = QPushButton("▢")
        self.hide_btn: QPushButton = QPushButton("–")

        self.login_status_btn: QPushButton = QPushButton()

        self.exit_btn.setFixedSize(QSize(42, 32))
        self.full_btn.setFixedSize(icon_size1)
        self.hide_btn.setFixedSize(icon_size1)
        self.login_status_btn.setFixedSize(icon_size1)
        self.login_status_btn.setIconSize(icon_size)

        self.login_status_btn.setObjectName("top_btn")
        self.full_btn.setObjectName("top_btn")
        self.hide_btn.setObjectName("top_btn")
        self.exit_btn.setObjectName("exit_btn")

        self.lt.addWidget(self.window_icon_lbl, alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.lt.addWidget(self.title_lbl, 1, alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.lt.addWidget(self.login_status_btn, alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.lt.addSpacing(25)
        self.lt.addWidget(self.hide_btn, alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.lt.addSpacing(25)
        self.lt.addWidget(self.full_btn, alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.lt.addSpacing(25)
        self.lt.addWidget(self.exit_btn, alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.setFixedHeight(60)
        self.setObjectName("title_widget")
        self.setLayout(self.lt)
        self.setContentsMargins(0, 0, 0, 0)
        self.lt.setContentsMargins(0, 0, 0, 0)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.change_style(style_name=self.style_name)

    def change_style(self, style_name: str):
        self.style_name: str = style_name
        self.style_: str = get_styles(style_name=self.style_name)
        self.setStyleSheet(self.style_)
        self.exit_btn.setStyleSheet(self.style_)
        self.full_btn.setStyleSheet(self.style_)
        self.hide_btn.setStyleSheet(self.style_)
        self.window_icon_lbl.setStyleSheet(self.style_)
        self.title_lbl.setStyleSheet(self.style_)



class BlurEffect(QGraphicsBlurEffect):

    @property
    def blurRadius(self):
        return self._blur_radius

    def __init__(self, parent=None):
        super().__init__(parent)
        self._blur_radius: int = 0
        self.setBlurRadius(self._blur_radius)

    @pyqtProperty(float)
    def blurRadius(self):
        return self._blur_radius

    @blurRadius.setter
    def blurRadius(self, value: int):
        self._blur_radius: int = value
        self.setBlurRadius(value)

    @property
    def blur_radius(self):
        return self._blur_radius


class OverlayWidget(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.painter: QPainter | None = None
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("background: rgba(0, 0, 0, 100);")

    def paintEvent(self, event):
        painter: QPainter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))
        painter.end()




