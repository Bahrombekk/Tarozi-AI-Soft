from __future__ import annotations
from functools import partial
from typing import Union
import cv2, os
import numpy as np
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import (QWidget, QLabel, QHBoxLayout, QVBoxLayout,
                              QScrollArea, QPushButton)
from ui.styles import get_styles, item_height
from ui.widgets import HoverIconButton
from ui.dialogs import ImageDialog
from utils.image import cv2_to_qpixmap, qpixmap_to_ndarray, rounded_pixmap
from utils.helpers import get_wagon_norm_tonn, get_wagon_type, current_time
from core.config import (wagonNumber, scaleNumber, wagonAttachId, wagonAttachId2,
                          wagonNumberAttachId, createdDate, identifier, num_count, log)
try:
    from utils.helpers import SCREEN_WIDTH, SCREEN_HEIGHT
except Exception:
    SCREEN_WIDTH, SCREEN_HEIGHT = 1920, 1080

class Table(QWidget):

    def __init__(self, style_name: str):
        super().__init__()
        self.style_name: str = style_name
        self.style_: str = get_styles(style_name=self.style_name)
        self.main_lt: QVBoxLayout = QVBoxLayout()
        self.header_lt: QHBoxLayout = QHBoxLayout()
        self.main_lt.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.main_lt.addLayout(self.header_lt)
        self.setLayout(self.main_lt)
        self.main_lt.setSpacing(0)

        self.image_dialog: ImageDialog | None = None

        self.widths: dict[str, int] = {
            "id": int(SCREEN_WIDTH * 0.042),
            "wagon_id": int(SCREEN_WIDTH * 0.064),
            "image": int(SCREEN_WIDTH * 0.084),
            "image2": int(SCREEN_WIDTH * 0.084),
            "image_id": int(SCREEN_WIDTH * 0.148),
            "weight": int(SCREEN_WIDTH * 0.084),
            "norm": int(SCREEN_WIDTH * 0.084),
            "extra": int(SCREEN_WIDTH * 0.084),
            "type": int(SCREEN_WIDTH * 0.105),
            "date": int(SCREEN_WIDTH * 0.105)
        }

        self.row_id: int = 0

        self.images: dict[str, QPixmap] = {}

        self.id_lbl: QLabel = QLabel("ID")
        self.id_lbl.setObjectName("header_l")
        self.id_lbl.setStyleSheet(self.style_)
        self.id_lbl.setFixedWidth(self.widths.get("id"))
        self.id_lbl.setFixedHeight(item_height)

        self.wagon_id_lbl: QLabel = QLabel("Vagon ID")
        self.wagon_id_lbl.setObjectName("header")
        self.wagon_id_lbl.setStyleSheet(self.style_)
        self.wagon_id_lbl.setFixedWidth(self.widths.get("wagon_id"))
        self.wagon_id_lbl.setFixedHeight(item_height)

        self.wagon_image_lbl: QLabel = QLabel("Vagon rasmi")
        self.wagon_image_lbl.setObjectName("header")
        self.wagon_image_lbl.setStyleSheet(self.style_)
        self.wagon_image_lbl.setFixedWidth(self.widths.get("image"))
        self.wagon_image_lbl.setFixedHeight(item_height)

        self.wagon_image2_lbl: QLabel = QLabel("Vagon rasmi 2")
        self.wagon_image2_lbl.setObjectName("header")
        self.wagon_image2_lbl.setStyleSheet(self.style_)
        self.wagon_image2_lbl.setFixedWidth(self.widths.get("image2"))
        self.wagon_image2_lbl.setFixedHeight(item_height)

        self.wagon_id_image_lbl: QLabel = QLabel("Vagon raqami")
        self.wagon_id_image_lbl.setObjectName("header_id")
        self.wagon_id_image_lbl.setStyleSheet(self.style_)
        self.wagon_id_image_lbl.setFixedWidth(self.widths.get("image_id"))
        self.wagon_id_image_lbl.setFixedHeight(item_height)

        self.weight_lbl: QLabel = QLabel("O'lchangan \nog'irlik (tonna)")
        self.weight_lbl.setObjectName("header")
        self.weight_lbl.setStyleSheet(self.style_)
        self.weight_lbl.setFixedWidth(self.widths.get("weight"))
        self.weight_lbl.setFixedHeight(item_height)

        self.weight_norm_lbl: QLabel = QLabel("Yuk normasi\n(tonna)")
        self.weight_norm_lbl.setObjectName("header")
        self.weight_norm_lbl.setStyleSheet(self.style_)
        self.weight_norm_lbl.setFixedWidth(self.widths.get("norm"))
        self.weight_norm_lbl.setFixedHeight(item_height)

        self.weight_extra_lbl: QLabel = QLabel("Ortiqcha yuk\n(tonna)")
        self.weight_extra_lbl.setObjectName("header")
        self.weight_extra_lbl.setStyleSheet(self.style_)
        self.weight_extra_lbl.setFixedWidth(self.widths.get("extra"))
        self.weight_extra_lbl.setFixedHeight(item_height)

        self.wagon_type_lbl: QLabel = QLabel("Vagon turi")
        self.wagon_type_lbl.setObjectName("header")
        self.wagon_type_lbl.setStyleSheet(self.style_)
        self.wagon_type_lbl.setFixedWidth(self.widths.get("type"))
        self.wagon_type_lbl.setFixedHeight(item_height)

        self.date_time_lbl: QLabel = QLabel("Sana va vaqt")
        self.date_time_lbl.setObjectName("header_r")
        self.date_time_lbl.setStyleSheet(self.style_)
        self.date_time_lbl.setFixedHeight(item_height)

        self.header_lt.addWidget(self.id_lbl)
        self.header_lt.addWidget(self.wagon_id_lbl)
        self.header_lt.addWidget(self.wagon_image_lbl)
        self.header_lt.addWidget(self.wagon_image2_lbl)
        self.header_lt.addWidget(self.wagon_id_image_lbl)
        self.header_lt.addWidget(self.weight_lbl)
        self.header_lt.addWidget(self.weight_norm_lbl)
        self.header_lt.addWidget(self.weight_extra_lbl)
        self.header_lt.addWidget(self.wagon_type_lbl)
        self.header_lt.addWidget(self.date_time_lbl)
        self.header_lt.setSpacing(0)

        self.scroll_content: QWidget = QWidget()
        self.layout__: QVBoxLayout = QVBoxLayout(self.scroll_content)
        self.scroll_content.setObjectName("central")
        self.scroll_content.setStyleSheet(self.style_)
        self.layout__.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.layout__.setSpacing(0)
        self.layout__.setContentsMargins(0, 0, 0, 0)
        self.scroll_area: QScrollArea = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.scroll_area.setWidget(self.scroll_content)
        self.scroll_area.setStyleSheet(self.style_)
        self.main_lt.addWidget(self.scroll_area)

    def add_row(self, data: dict):
        self.clear_except_last()
        lt: QHBoxLayout = QHBoxLayout()
        lt.setContentsMargins(0, 0, 0, 0)
        lt.setSpacing(0)

        wd: QWidget = QWidget()
        wd.setObjectName("item_row")
        wd.setStyleSheet(self.style_)
        wd.setContentsMargins(0, 3, 0, 3)
        wd.setLayout(lt)

        wagon_number: str = str(data.get(wagonNumber, identifier * num_count))
        scale_number: int = int(data.get(scaleNumber, 0))
        folder_name: str = "success"
        norm_ton: int = get_wagon_norm_tonn(wagon_id=wagon_number)

        dateTime: str = str(data.get(createdDate, current_time()))
        wagon_type: str = get_wagon_type(wagon_number)

        wagon_image_np: Union[np.ndarray | QPixmap | str | None] = data.get(
            wagonAttachId, np.zeros((720, 1280, 3), dtype=np.uint8))
        wagon_image_np2: Union[np.ndarray | QPixmap | str | None] = data.get(
            wagonAttachId2, np.zeros((720, 1280, 3), dtype=np.uint8))
        wagon_id_image_np: Union[np.ndarray | QPixmap | str | None] = data.get(
            wagonNumberAttachId, np.zeros((720, 1280, 3), dtype=np.uint8))
        ###############################
        if isinstance(wagon_image_np, QPixmap):
            wagon_image_np = qpixmap_to_ndarray(wagon_image_np)
        if isinstance(wagon_image_np, str):
            if os.path.exists(wagon_image_np):
                wagon_image_np = cv2.imread(wagon_image_np)
            else:
                wagon_image_np = np.zeros((720, 1280, 3), dtype=np.uint8)
        if wagon_image_np is None:
            wagon_image_np = np.zeros((720, 1280, 3), dtype=np.uint8)
        ###############################
        if isinstance(wagon_image_np2, QPixmap):
            wagon_image_np2 = qpixmap_to_ndarray(wagon_image_np2)
        if isinstance(wagon_image_np2, str):
            if os.path.exists(wagon_image_np2):
                wagon_image_np2 = cv2.imread(wagon_image_np2)
            else:
                wagon_image_np2 = np.zeros((720, 1280, 3), dtype=np.uint8)
        if wagon_image_np2 is None:
            wagon_image_np2 = np.zeros((720, 1280, 3), dtype=np.uint8)

        if isinstance(wagon_id_image_np, QPixmap):
            wagon_id_image_np = qpixmap_to_ndarray(wagon_id_image_np)
        if isinstance(wagon_id_image_np, str):
            if os.path.exists(wagon_id_image_np):
                wagon_id_image_np = cv2.imread(wagon_id_image_np)
            else:
                wagon_id_image_np = np.zeros((720, 1280, 3), dtype=np.uint8)
        if wagon_id_image_np is None:
            wagon_id_image_np = np.zeros((720, 1280, 3), dtype=np.uint8)

        if not os.path.exists(folder_name):
            os.mkdir(folder_name)

        img_name: str = f"{folder_name}/wagon_image_{wagon_number}_{self.row_id}_1.jpg"
        img_name2: str = f"{folder_name}/wagon_image_{wagon_number}_{self.row_id}_2.jpg"
        img_id_name: str = f"{folder_name}/wagon_id_image_{wagon_number}_{self.row_id}.jpg"

        cv2.imwrite(img_name, wagon_image_np)
        cv2.imwrite(img_name2, wagon_image_np2)
        cv2.imwrite(img_id_name, wagon_id_image_np)

        wagonImage = cv2_to_qpixmap(wagon_image_np, fmt=True)
        wagonImage2 = cv2_to_qpixmap(wagon_image_np2, fmt=True)
        wagonIdImage = cv2_to_qpixmap(wagon_id_image_np, fmt=False)

        wx: int = int(SCREEN_WIDTH * 0.061)
        wx2: int = int(SCREEN_WIDTH * 0.124)
        hy: int = int(SCREEN_HEIGHT * 0.061)
        hy2: int = int(SCREEN_HEIGHT * 0.045)

        wagonImage: QPixmap = wagonImage.scaled(
            wx, hy, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        )
        wagonImage2: QPixmap = wagonImage2.scaled(
            wx, hy, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        )
        wagonIdImage: QPixmap = wagonIdImage.scaled(
            wx2, hy2, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        )
        wagonImage = rounded_pixmap(pixmap=wagonImage, radius=8)
        wagonImage2 = rounded_pixmap(pixmap=wagonImage2, radius=8)
        wagonIdImage = rounded_pixmap(pixmap=wagonIdImage, radius=8)
        wagonImage: QIcon = QIcon(wagonImage)
        wagonImage2: QIcon = QIcon(wagonImage2)
        wagonIdImage: QIcon = QIcon(wagonIdImage)

        id_lbl: QLabel = QLabel("Vagon ID")
        id_lbl.setObjectName("item_l")
        id_lbl.setStyleSheet(self.style_)
        id_lbl.setFixedWidth(self.widths.get("id"))
        id_lbl.setFixedHeight(item_height)
        id_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        wagon_id_lbl: QLabel = QLabel("Vagon ID")
        wagon_id_lbl.setObjectName("item")
        wagon_id_lbl.setStyleSheet(self.style_)
        wagon_id_lbl.setFixedWidth(self.widths.get("wagon_id"))
        wagon_id_lbl.setFixedHeight(item_height)
        wagon_id_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        wagon_image_btn: HoverIconButton = HoverIconButton(icon=wagonImage, size=30)
        wagon_image_btn.setObjectName("item_image")
        wagon_image_btn.setStyleSheet(self.style_)
        wagon_image_btn.setIconSize(QSize(wx, hy))
        wagon_image_btn.setFixedWidth(self.widths.get("image"))
        wagon_image_btn.setFixedHeight(item_height)
        wagon_image_btn.clicked.connect(
            partial(
                self._open_image_modal, title="Vagon rasmi", path=img_name,
            )
        )

        wagon_image_btn2: HoverIconButton = HoverIconButton(icon=wagonImage2, size=30)
        wagon_image_btn2.setObjectName("item_image")
        wagon_image_btn2.setStyleSheet(self.style_)
        wagon_image_btn2.setIconSize(QSize(wx, hy))
        wagon_image_btn2.setFixedWidth(self.widths.get("image2"))
        wagon_image_btn2.setFixedHeight(item_height)
        wagon_image_btn2.clicked.connect(
            partial(
                self._open_image_modal, title="Vagon raqami", path=img_name2,
            )
        )

        wagon_id_image_btn: HoverIconButton = HoverIconButton(icon=wagonIdImage, size=30)
        wagon_id_image_btn.setObjectName("item_id_image")
        wagon_id_image_btn.setStyleSheet(self.style_)
        wagon_id_image_btn.setIconSize(QSize(wx2, hy2))
        wagon_id_image_btn.setFixedWidth(self.widths.get("image_id"))
        wagon_id_image_btn.setFixedHeight(item_height)
        wagon_id_image_btn.clicked.connect(
            partial(
                self._open_image_modal, title="Vagon raqami", path=img_id_name,
            )
        )

        weight_lbl: QLabel = QLabel()
        weight_lbl.setObjectName("item")
        weight_lbl.setStyleSheet(self.style_)
        weight_lbl.setFixedWidth(self.widths.get("weight"))
        weight_lbl.setFixedHeight(item_height)
        weight_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        weight_norm_lbl: QLabel = QLabel()
        weight_norm_lbl.setObjectName("item")
        weight_norm_lbl.setStyleSheet(self.style_)
        weight_norm_lbl.setFixedWidth(self.widths.get("norm"))
        weight_norm_lbl.setFixedHeight(item_height)
        weight_norm_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        weight_extra_lbl: QLabel = QLabel()
        weight_extra_lbl.setObjectName("item")
        weight_extra_lbl.setStyleSheet(self.style_)
        weight_extra_lbl.setFixedWidth(self.widths.get("extra"))
        weight_extra_lbl.setFixedHeight(item_height)

        weight_extra_lt: QHBoxLayout = QHBoxLayout()
        weight_extra_lt.setSpacing(0)
        weight_extra_lt.setContentsMargins(0, 0, 0, 0)
        weight_extra_lt.setAlignment(Qt.AlignmentFlag.AlignLeft)
        weight_extra_lbl.setLayout(weight_extra_lt)

        massa_lbl: QLabel = QLabel()
        kg_lbl: QLabel = QLabel(" t")

        extra_ton: int = 0
        try:
            if norm_ton != 0:
                extra_ton: int = norm_ton - int(scale_number)
        except (Exception, ValueError):
            pass

        if int(extra_ton) < -2_000:
            massa_lbl.setObjectName("item_massa_red")
            kg_lbl.setObjectName("item_kg_red")
            massa_lbl.setText(f"+{-1 * int(extra_ton) / 1000:,.1f}".replace(",", " "))
        elif int(extra_ton) < 0:
            massa_lbl.setObjectName("item_massa_yel")
            kg_lbl.setObjectName("item_kg_yel")
            massa_lbl.setText(f"+{-1 * int(extra_ton) / 1000:,.1f}".replace(",", " "))
        else:
            massa_lbl.setObjectName("item_massa_green")
            kg_lbl.setObjectName("item_kg_green")
            massa_lbl.setText(f"{-1 * int(extra_ton) / 1000:,.1f}".replace(",", " "))
        kg_lbl.setStyleSheet(self.style_)
        massa_lbl.setStyleSheet(self.style_)
        massa_lbl.setContentsMargins(0, 0, 0, 0)
        massa_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        kg_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        weight_extra_lt.addWidget(massa_lbl)
        weight_extra_lt.addWidget(kg_lbl)

        wagon_type_lbl: QLabel = QLabel()
        wagon_type_lbl.setObjectName("item")
        wagon_type_lbl.setStyleSheet(self.style_)
        wagon_type_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        wagon_type_lbl.setFixedWidth(self.widths.get("type"))

        date_time_lbl: QLabel = QLabel()
        date_time_lbl.setObjectName("item")
        date_time_lbl.setStyleSheet(self.style_)
        date_time_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self.row_id += 1
        id_lbl.setText(str(self.row_id))
        wagon_id_lbl.setText(wagon_number)
        wagon_id_lbl.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        weight_lbl.setText(f"{int(scale_number) / 1000:,.1f} t".replace(",", " "))

        if norm_ton == 0:
            weight_norm_lbl.setText("Aniqlanmadi")
        else:
            weight_norm_lbl.setText(f"{int(norm_ton) / 1000:,.1f} t".replace(",", " "))

        wagon_type_lbl.setText(wagon_type)
        date_time_lbl.setText(dateTime.replace("Z", "").replace("T", "\n"))
        date_time_lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)

        lt.addWidget(id_lbl)
        lt.addWidget(wagon_id_lbl)
        lt.addWidget(wagon_image_btn)
        lt.addWidget(wagon_image_btn2)
        lt.addWidget(wagon_id_image_btn)
        lt.addWidget(weight_lbl)
        lt.addWidget(weight_norm_lbl)
        lt.addWidget(weight_extra_lbl)
        lt.addWidget(wagon_type_lbl)
        lt.addWidget(date_time_lbl)

        self.scroll_area.verticalScrollBar().setValue(0)

        self.layout__.insertWidget(0, wd)

    def clear_except_last(self, keep: int = 9):
        count = self.layout__.count()
        to_remove = max(0, count - keep)
        for i in range(to_remove):
            item = self.layout__.takeAt(0)
            if item is None:
                continue
            w = item.widget()
            if w is not None:
                w.deleteLater()
                continue
            lay = item.layout()
            if lay is not None:
                self._delete_layout_recursive(lay)
                continue

    def _delete_layout_recursive(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
                continue
            child_layout = item.layout()
            if child_layout:
                self._delete_layout_recursive(child_layout)

    def _open_image_modal(self, title: str, path: Union[str | QPixmap | np.ndarray | None] = None):
        try:
            self.image_dialog = ImageDialog(style_name=self.style_name, _title=title, pixmap=path)
            self.image_dialog.exec()
        except (Exception, ValueError) as err:
            log(message=f"[HistoryWidget._open_image_modal] {err}")

    def change_style(self, style_name: str):
        self.style_name: str = style_name
        self.style_: str = get_styles(style_name=self.style_name)
        self.setStyleSheet(self.style_)
        self.id_lbl.setStyleSheet(self.style_)
        self.wagon_id_lbl.setStyleSheet(self.style_)
        self.wagon_type_lbl.setStyleSheet(self.style_)
        self.wagon_image_lbl.setStyleSheet(self.style_)
        self.wagon_image2_lbl.setStyleSheet(self.style_)
        self.wagon_id_image_lbl.setStyleSheet(self.style_)
        self.weight_lbl.setStyleSheet(self.style_)
        self.weight_extra_lbl.setStyleSheet(self.style_)
        self.weight_norm_lbl.setStyleSheet(self.style_)
        self.scroll_area.setStyleSheet(self.style_)
        self.scroll_content.setStyleSheet(self.style_)
        self.date_time_lbl.setStyleSheet(self.style_)

        row_count = self.layout__.count()
        for i in range(row_count):
            try:
                item = self.layout__.itemAt(i)
                if item is None:
                    continue
                row_widget = item.widget()
                if row_widget is None:
                    continue
                try:
                    row_widget.setStyleSheet(self.style_)
                except (Exception, ValueError):
                    pass
                for j in range(row_widget.layout().count()):
                    try:
                        child_item = row_widget.layout().itemAt(j)
                        if child_item is None:
                            continue
                        child = child_item.widget()
                        if child is None:
                            continue
                        child.setStyleSheet(self.style_)
                    except (Exception, ValueError):
                        pass
            except (Exception, ValueError):
                pass

