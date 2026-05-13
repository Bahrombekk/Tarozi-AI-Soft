from __future__ import annotations
from typing import Union
import cv2, os
import numpy as np
from PyQt6.QtCore import Qt, QSize, QTimer, QRectF
from PyQt6.QtGui import QPixmap, QPainter, QFont, QColor, QPen
from PyQt6.QtWidgets import (QDialog, QLabel, QVBoxLayout, QHBoxLayout,
                              QPushButton, QProgressBar, QScrollArea, QWidget,
                              QLineEdit, QFrame, QSizePolicy)
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
        self.lbl: QLabel = QLabel("Iltimos, kuting.\nMa'lumot tasdiqlanmoqda...")
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



class _CandidateCard(QFrame):
    """Bitta vagon uchun bosish mumkin bo'lgan kard."""

    def __init__(self, candidate: dict, style_name: str, parent=None):
        super().__init__(parent)
        from core.config import wagonNumber, wagonNumberAttachId, CONF
        from ui.theme import palettes, BG_COLOR2, BG_COLOR3, BORDER_COLOR, TEXT_COLOR, TEXT_COLOR2

        p = palettes[style_name]
        bg      = p[BG_COLOR2]
        bg_hov  = p[BG_COLOR3]
        border  = p[BORDER_COLOR]
        txt     = p[TEXT_COLOR]
        txt2    = p[TEXT_COLOR2]

        self._candidate = candidate
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedWidth(240)
        self.setObjectName("candidate_card")
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        self.setStyleSheet(f"""
            QFrame#candidate_card {{
                background: {bg};
                border: 2px solid {border};
                border-radius: 16px;
            }}
            QFrame#candidate_card:hover {{
                border: 2px solid #007CF0;
                background: {bg_hov};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        # Rasm
        img_lbl = QLabel()
        img_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nid = candidate.get(wagonNumberAttachId)
        if isinstance(nid, np.ndarray):
            pix = cv2_to_qpixmap(cv_img=nid)
            img_lbl.setPixmap(
                pix.scaledToWidth(210, Qt.TransformationMode.SmoothTransformation))
        else:
            img_lbl.setText("—")
            img_lbl.setStyleSheet(f"color:{txt2}; font-size:28px;")
        img_lbl.setFixedHeight(80)
        layout.addWidget(img_lbl)

        # Raqam badge
        wn = str(candidate.get(wagonNumber, "?"))
        num_lbl = QLabel(wn)
        num_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        num_lbl.setFont(QFont("Poppins", 20, QFont.Weight.Bold))
        num_lbl.setStyleSheet(f"""
            background: rgba(0,124,240,0.12);
            color: #007CF0;
            border-radius: 10px;
            padding: 6px 10px;
        """)
        layout.addWidget(num_lbl)

        # Ishonch foizi
        conf = candidate.get(CONF, 0)
        conf_lbl = QLabel(f"Ishonch: {conf * 100:.0f}%")
        conf_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        conf_lbl.setStyleSheet(f"color:{txt2}; font-size:13px;")
        layout.addWidget(conf_lbl)

        # Tanlash tugmasi
        btn = QPushButton("Tanlash")
        btn.setMinimumHeight(44)
        btn.setFont(QFont("Poppins", 14, QFont.Weight.Medium))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton {
                background: #007CF0;
                color: #fff;
                border-radius: 10px;
                border: none;
                padding: 8px;
            }
            QPushButton:hover {
                background: #005BB5;
            }
            QPushButton:pressed {
                background: #004A9A;
            }
        """)
        btn.clicked.connect(self._on_click)
        layout.addWidget(btn)

    def _on_click(self):
        dlg = self.window()
        if isinstance(dlg, WagonChoiceDialog):
            dlg._choose(self._candidate)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._on_click()
        super().mousePressEvent(event)


class WagonChoiceDialog(QDialog):
    """Ikkita to'liq 8-xonali vagon raqami aniqlanganda operator tanlash uchun dialog."""

    def __init__(self, style_name: str, candidates: list):
        super().__init__()
        from ui.theme import palettes, BG_COLOR, BG_COLOR2, TEXT_COLOR, TEXT_COLOR2, BORDER_COLOR

        self.setWindowTitle("Vagon raqamini tanlang")
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        # X tugmasi va Escape orqali yopishni o'chirish
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowCloseButtonHint)
        if window_icon:
            self.setWindowIcon(window_icon)
        self.selected: dict | None = None
        self._user_closed: bool = False

        p = palettes[style_name]
        bg   = p[BG_COLOR]
        bg2  = p[BG_COLOR2]
        txt  = p[TEXT_COLOR]
        txt2 = p[TEXT_COLOR2]
        brd  = p[BORDER_COLOR]

        self.setStyleSheet(f"""
            QDialog {{
                background: {bg};
            }}
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(20)

        # Sarlavha
        title = QLabel("To'g'ri vagon raqamini tanlang")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Poppins", 16, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {txt};")
        root.addWidget(title)

        subtitle = QLabel("Kamera ikkita to'liq raqam aniqladi. Iltimos, to'g'ri raqamni tanlang.")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet(f"color: {txt2}; font-size: 13px;")
        root.addWidget(subtitle)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {brd};")
        root.addWidget(sep)

        # Kardlar qatori
        cards_row = QHBoxLayout()
        cards_row.setSpacing(16)
        cards_row.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        for candidate in candidates:
            card = _CandidateCard(candidate=candidate, style_name=style_name)
            cards_row.addWidget(card)
        root.addLayout(cards_row)

        # Separator
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet(f"color: {brd};")
        root.addWidget(sep2)

        # Bekor qilish
        cancel_btn = QPushButton("Bekor qilish")
        cancel_btn.setMinimumHeight(40)
        cancel_btn.setFont(QFont("Poppins", 13))
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {txt2};
                border: 1px solid {brd};
                border-radius: 10px;
                padding: 6px 20px;
            }}
            QPushButton:hover {{
                background: {p['BG_COLOR3']};
            }}
        """)
        cancel_btn.clicked.connect(self._on_cancel)
        root.addWidget(cancel_btn, alignment=Qt.AlignmentFlag.AlignHCenter)

    def _on_cancel(self) -> None:
        self._user_closed = True
        self.reject()

    def _choose(self, candidate: dict) -> None:
        self._user_closed = True
        self.selected = candidate
        self.accept()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            return  # Escape bilan yopilmaydi
        super().keyPressEvent(event)

    def closeEvent(self, event):
        if self._user_closed:
            event.accept()
        else:
            event.ignore()  # X tugmasi orqali yopilmaydi


class _RingWidget(QWidget):
    """Aylana countdown animatsiyasi (30s → 0)."""

    def __init__(self, total_ms: int = 30_000, parent=None):
        super().__init__(parent)
        self._total = total_ms
        self._elapsed = 0
        self.setFixedSize(110, 110)

    def set_elapsed(self, ms: int) -> None:
        self._elapsed = min(ms, self._total)
        self.update()

    def seconds_left(self) -> int:
        return max(0, (self._total - self._elapsed + 999) // 1000)

    def is_done(self) -> bool:
        return self._elapsed >= self._total

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        thickness = 9
        m = thickness // 2 + 3
        rect = QRectF(m, m, w - 2 * m, h - 2 * m)

        # Fon aylana
        p.setPen(QPen(QColor("#3A3F4B"), thickness))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(rect)

        # Progress arc — tepadan soat sohasi bo'yicha qisqaradi
        progress = 1.0 - self._elapsed / max(1, self._total)
        span = int(progress * 360 * 16)
        color = QColor("#007CF0") if not self.is_done() else QColor("#00C954")
        pen = QPen(color, thickness)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        if span > 0:
            p.drawArc(rect, 90 * 16, span)

        # Markazda soniya
        secs = self.seconds_left()
        p.setPen(color)
        p.setFont(QFont("Poppins", 22, QFont.Weight.Bold))
        p.drawText(rect, Qt.AlignmentFlag.AlignCenter,
                   str(secs) if not self.is_done() else "✓")
        p.end()


class RepeatWagonDialog(QDialog):
    """Avval yuborilgan vagon uchun 30 soniyali countdown dialog."""

    COUNTDOWN_MS = 60_000
    TICK_MS      = 100

    def __init__(self, style_name: str, wagon_number: str,
                 weighed_at: str | None = None, weight_kg: str | None = None):
        super().__init__()
        from ui.theme import palettes, BG_COLOR, BG_COLOR2, BG_COLOR3, TEXT_COLOR, TEXT_COLOR2, BORDER_COLOR

        self.setWindowTitle("Qayta tortishni tasdiqlash")
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        if window_icon:
            self.setWindowIcon(window_icon)

        p    = palettes[style_name]
        bg   = p[BG_COLOR]
        bg2  = p[BG_COLOR2]
        txt  = p[TEXT_COLOR]
        txt2 = p[TEXT_COLOR2]
        brd  = p[BORDER_COLOR]
        bg3  = p[BG_COLOR3]

        self.setStyleSheet(f"QDialog {{ background: {bg}; }}")
        self.setMinimumWidth(540)
        self.setMaximumWidth(600)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Sariq ogohlantirish banner ──────────────────────────────────
        banner = QFrame()
        banner.setFixedHeight(72)
        banner.setStyleSheet("background: #E07800; border-radius: 0px;")
        banner_lt = QHBoxLayout(banner)
        banner_lt.setContentsMargins(24, 0, 24, 0)

        warn_lbl = QLabel("⚠")
        warn_lbl.setFont(QFont("Poppins", 28))
        warn_lbl.setStyleSheet("color: #fff; background: transparent;")
        banner_lt.addWidget(warn_lbl)
        banner_lt.addSpacing(10)

        ban_text = QLabel("Ushbu vagon bugun ro'yxatga olingan.")
        ban_text.setFont(QFont("Poppins", 14, QFont.Weight.Bold))
        ban_text.setStyleSheet("color: #fff; background: transparent;")
        banner_lt.addWidget(ban_text)
        banner_lt.addStretch()
        root.addWidget(banner)

        # ── Asosiy kontent ──────────────────────────────────────────────
        body = QWidget()
        body.setStyleSheet(f"background: {bg};")
        body_lt = QVBoxLayout(body)
        body_lt.setContentsMargins(28, 20, 28, 24)
        body_lt.setSpacing(14)

        # Vagon raqami badge
        badge = QLabel(wagon_number)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setFont(QFont("Poppins", 34, QFont.Weight.Bold))
        badge.setStyleSheet("""
            background: rgba(0,124,240,0.12);
            color: #007CF0;
            border-radius: 16px;
            padding: 12px 24px;
        """)
        body_lt.addWidget(badge)

        # Ma'lumot kartasi ─────────────────────────────────────────────
        info_card = QFrame()
        info_card.setStyleSheet(f"""
            QFrame {{
                background: {bg2};
                border-left: 4px solid #007CF0;
                border-top: 1px solid {brd};
                border-right: 1px solid {brd};
                border-bottom: 1px solid {brd};
                border-radius: 12px;
            }}
        """)
        info_lt = QVBoxLayout(info_card)
        info_lt.setContentsMargins(18, 14, 18, 14)
        info_lt.setSpacing(10)

        def _info_row(icon_path: str, label: str, value: str):
            row = QHBoxLayout()
            ic = QLabel()
            pix = QPixmap(icon_path).scaled(22, 22, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            ic.setPixmap(pix)
            ic.setFixedWidth(28)
            ic.setAlignment(Qt.AlignmentFlag.AlignCenter)
            ic.setStyleSheet("background: transparent; border: none;")
            lb = QLabel(label)
            lb.setFont(QFont("Poppins", 13))
            lb.setStyleSheet(f"color: {txt2}; background: transparent; border: none;")
            vl = QLabel(value)
            vl.setFont(QFont("Poppins", 15, QFont.Weight.Bold))
            vl.setStyleSheet(f"color: {txt}; background: transparent; border: none;")
            row.addWidget(ic)
            row.addWidget(lb)
            row.addStretch()
            row.addWidget(vl)
            return row

        time_str   = weighed_at or "—"
        try:
            weight_str = f"{int(weight_kg):,} kg".replace(",", " ") if weight_kg else "—"
        except Exception:
            weight_str = f"{weight_kg} kg" if weight_kg else "—"

        info_lt.addLayout(_info_row("images/clock.png", "Avvalgi tortish vaqti:", time_str))

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"border: none; background: {brd}; max-height: 1px;")
        info_lt.addWidget(sep)

        info_lt.addLayout(_info_row("images/scale.svg", "Avvalgi og'irlik:", weight_str))
        body_lt.addWidget(info_card)

        # Savol + izoh ─────────────────────────────────────────────────
        q_lbl = QLabel("Ushbu vagonni qayta tortishni davom ettirasizmi?")
        q_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        q_lbl.setFont(QFont("Poppins", 15, QFont.Weight.Bold))
        q_lbl.setStyleSheet(f"color: {txt};")
        body_lt.addWidget(q_lbl)

        hint_lbl = QLabel("Tasdiqlash tugmasi 60 soniyadan so'ng faollashadi.")
        hint_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint_lbl.setWordWrap(True)
        hint_lbl.setMaximumWidth(500)
        hint_lbl.setFont(QFont("Poppins", 12))
        hint_lbl.setStyleSheet(f"color: {txt2};")
        body_lt.addWidget(hint_lbl)

        # Aylana timer — markazda ────────────────────────────────────
        self._ring = _RingWidget(total_ms=self.COUNTDOWN_MS)
        body_lt.addWidget(self._ring, alignment=Qt.AlignmentFlag.AlignHCenter)

        # Tugmalar — to'liq kenglik ──────────────────────────────────
        self._yes_btn = QPushButton("Tasdiqlash - 60s")
        self._yes_btn.setMinimumHeight(54)
        self._yes_btn.setFont(QFont("Poppins", 14, QFont.Weight.Bold))
        self._yes_btn.setCursor(Qt.CursorShape.ForbiddenCursor)
        self._yes_btn.setEnabled(False)
        self._yes_btn.setStyleSheet("""
            QPushButton:disabled {
                background: #3A3A3A;
                color: #666;
                border-radius: 14px;
                padding: 10px;
                border: none;
            }
            QPushButton:enabled {
                background: #007CF0;
                color: #fff;
                border-radius: 14px;
                padding: 10px;
                border: none;
            }
            QPushButton:enabled:hover { background: #005BB5; }
            QPushButton:enabled:pressed { background: #004A9A; }
        """)
        self._yes_btn.clicked.connect(self.accept)
        body_lt.addWidget(self._yes_btn)

        no_btn = QPushButton("Bekor qilish")
        no_btn.setMinimumHeight(46)
        no_btn.setFont(QFont("Poppins", 13))
        no_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        no_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {txt2};
                border: 1px solid {brd};
                border-radius: 14px;
                padding: 8px;
            }}
            QPushButton:hover {{ background: {bg3}; color: {txt}; }}
        """)
        no_btn.clicked.connect(self.reject)
        body_lt.addWidget(no_btn)

        root.addWidget(body)

        # --- Timer ---
        self._elapsed_ms = 0
        self._timer = QTimer(self)
        self._timer.setInterval(self.TICK_MS)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    def _tick(self) -> None:
        self._elapsed_ms += self.TICK_MS
        self._ring.set_elapsed(self._elapsed_ms)
        remaining = max(0, (self.COUNTDOWN_MS - self._elapsed_ms + 999) // 1000)
        if self._elapsed_ms >= self.COUNTDOWN_MS:
            self._timer.stop()
            self._yes_btn.setEnabled(True)
            self._yes_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self._yes_btn.setText("Tasdiqlash")
        else:
            self._yes_btn.setText(f"Tasdiqlash - {remaining}s")

    def closeEvent(self, event):
        self._timer.stop()
        super().closeEvent(event)


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

