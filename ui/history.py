from __future__ import annotations
from functools import partial
from typing import Union
from datetime import datetime, timezone, timedelta

_TZ_UZ = timezone(timedelta(hours=5))  # Asia/Tashkent = UTC+5 (no tzdata needed on Windows)
import cv2, os, time
import numpy as np
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap, QColor, QBrush
from PyQt6.QtWidgets import (QWidget, QLabel, QVBoxLayout, QHBoxLayout,
                              QPushButton, QTabWidget, QTreeWidget, QTreeWidgetItem)
from ui.styles import get_styles
from ui.dialogs import ImageDialog, ImageDialog2
from utils.image import cv2_to_qpixmap, qpixmap_to_ndarray
from utils.helpers import get_wagon_norm_tonn, get_wagon_type, current_time
from core.database import BufferDB
from core.config import (wagonNumber, scaleNumber, wagonAttachId, wagonAttachId2,
                          wagonNumberAttachId, createdDate, sentAt, ID,
                          identifier, num_count, log,
                          MONTH_NAMES_UZ, stationCode, scaleCode,
                          wagonType, normTon, extraTon)
from ui.styles import item_height
try:
    from utils.helpers import SCREEN_WIDTH, SCREEN_HEIGHT, show_message, history_folder
except Exception:
    SCREEN_WIDTH, SCREEN_HEIGHT = 1920, 1080
    show_message = None
    history_folder = "history"

class HistoryWidget(QWidget):

    def __init__(self, style_name: str):
        super().__init__()
        self.style_name: str = style_name
        self.style_: str = get_styles(style_name=self.style_name)
        self.trees_by_month: dict[str, QTreeWidget] = {}
        self.image_dialog: ImageDialog2 | None = None

        self.lt: QVBoxLayout = QVBoxLayout()
        self.tabs: QTabWidget = QTabWidget()
        self.tabs.setObjectName("tab_widget")
        self.lt.addWidget(self.tabs)

        self.backup_db: BufferDB = BufferDB()

        width: int = self.width()

        self.widths: list[int] = [
            int(width * 0.058),
            int(width * 0.080),
            int(width * 0.104),
            int(width * 0.104),
            int(width * 0.104),
            int(width * 0.104),
            int(width * 0.150),
            int(width * 0.150),
            int(width * 0.150),
        ]

        self.headers: list[str] = [
            "ID",
            "Vagon \nraqami",
            "Vagon \nrasmlari",
            "O'lchangan \nog'irlik (t)",
            "Norma (t)",
            "Ortiqcha yuk (t)",
            "Vagon turi",
            "O'lchangan vaqt",
            "Yuborilgan vaqt"
        ]

        self.history_dir: str = history_folder
        os.makedirs(self.history_dir, exist_ok=True)

        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setLayout(self.lt)
        self.setContentsMargins(0, 0, 0, 0)
        self.lt.setContentsMargins(0, 0, 0, 0)
        self.tabs.setContentsMargins(0, 0, 0, 0)
        self.setObjectName("history_widget")

    @staticmethod
    def _month_label(year: int, month: int) -> str:
        return f"{MONTH_NAMES_UZ[month - 1]}, {year}-yil"

    @staticmethod
    def _make_month_key(dt_str: str | None) -> tuple[str, int, int]:
        try:
            if dt_str is None:
                raise ValueError()
            utc_dt = datetime.fromisoformat(str(dt_str).replace("Z", "+00:00"))
            uz_dt = utc_dt.astimezone(_TZ_UZ)
            y, m = uz_dt.year, uz_dt.month
        except (Exception, ValueError):
            now = datetime.now(_TZ_UZ)
            y, m = now.year, now.month
        return f"{y:04d}-{m:02d}", y, m

    def _create_tree_for_month(self, month_key: str, year: int, month: int) -> QTreeWidget:
        tree: QTreeWidget = QTreeWidget()
        tree.header().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        tree.setStyleSheet(self.style_)
        tree.setColumnCount(len(self.headers))
        tree.setHeaderLabels(self.headers)
        tree.setRootIsDecorated(False)
        tree.setAlternatingRowColors(False)
        tree.setSelectionBehavior(QTreeWidget.SelectionBehavior.SelectRows)
        tree.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)
        tree.header().setStretchLastSection(True)
        tree.header().setMinimumHeight(item_height)
        for i, w in enumerate(self.widths):
            tree.setColumnWidth(i, w)

        label = self._month_label(year, month)
        self.tabs.addTab(tree, label)
        self.trees_by_month[month_key] = tree

        return tree

    def current_tree(self) -> Union[QTreeWidget | None]:
        idx = self.tabs.currentIndex()
        if idx < 0:
            return None
        return self.tabs.widget(idx)

    def load_history(self) -> None:
        try:
            for _ in range(self.tabs.count()):
                self.tabs.removeTab(0)
            self.trees_by_month.clear()

            months, err = self.backup_db.get_all_history()

            if err:
                print(f"[HistoryWidget.load_history] {err}")
                log(message=f"[HistoryWidget.load_history] {err}")
                return

            now = datetime.now(_TZ_UZ)
            now_key = f"{now.year:04d}-{now.month:02d}"

            if not months:
                self._create_tree_for_month(now_key, now.year, now.month)
                if self.tabs.count() > 0:
                    self.tabs.setCurrentIndex(0)
                return

            sorted_keys = sorted(months.keys())

            for month_key in sorted_keys:
                try:
                    parts = month_key.split("-")
                    if len(parts) != 2:
                        continue

                    y = int(parts[0])
                    mon = int(parts[1])

                    if (y, mon) > (now.year, now.month):
                        continue

                    tree: QTreeWidget = self._create_tree_for_month(month_key, y, mon)
                    rows_list = months.get(month_key, []) or []

                    tree.setUpdatesEnabled(False)

                    for row_dict in rows_list:
                        self._append_visual_row_to_tree(tree, row_dict)

                    tree.setUpdatesEnabled(True)
                    tree.scrollToTop()

                except (Exception, ValueError) as e:
                    print(f"[HistoryWidget.load_history month: {month_key}] {e}")
                    log(message=f"[HistoryWidget.load_history month: {month_key}] {e}")
                    continue

            keys_list = list(self.trees_by_month.keys())
            if now_key in keys_list:
                idx_to_select = keys_list.index(now_key)
            else:
                idx_to_select = len(keys_list) - 1 if keys_list else 0

            if self.tabs.count() > 0:
                self.tabs.setCurrentIndex(idx_to_select)
        except (Exception, ValueError) as err:
            print(f"[HistoryWidget.load_history] {err}")
            log(message=f"[HistoryWidget.load_history] {err}")

        self.change_style(style_name=self.style_name)

    def add_row(self, data: dict, sent: bool = False):
        try:
            os.makedirs(self.history_dir, exist_ok=True)
            idx = int(data.get(ID, 0) or 0)
            wagon_number = str(data.get(wagonNumber, identifier * num_count))
            scale_number = int(data.get(scaleNumber, 0) or 0)
            created_date = data.get(createdDate, current_time())
            sent_at = data.get(sentAt, "Yuborilmagan")
            wagon_type = get_wagon_type(wagon_id=wagon_number)

            norm_ton = get_wagon_norm_tonn(wagon_id=wagon_number)
            extra_ton = 0
            try:
                if norm_ton != 0:
                    extra_ton = norm_ton - int(scale_number)
            except (Exception, ValueError):
                extra_ton = 0

            wagon_img = data.get(wagonAttachId)
            wagon_img2 = data.get(wagonAttachId2)
            wagon_id_img = data.get(wagonNumberAttachId)

            tm = time.strftime("%Y-%m-%d_%H.%M.%S")

            row_data = {
                ID: idx,
                wagonNumber: wagon_number,
                scaleNumber: scale_number,
                wagonType: wagon_type,
                normTon: norm_ton,
                extraTon: extra_ton,
                createdDate: created_date,
                sentAt: sent_at,
            }

            if isinstance(wagon_img, np.ndarray):
                img_name = os.path.join(self.history_dir, f"wagon_{wagon_number}_{idx}_{tm}_1.jpg")
                cv2.imwrite(img_name, wagon_img)
                row_data[wagonAttachId] = img_name
            elif isinstance(wagon_img, QPixmap):
                img_name = os.path.join(self.history_dir, f"wagon_{wagon_number}_{idx}_{tm}_1.jpg")
                cv2.imwrite(img_name, qpixmap_to_ndarray(pixmap=wagon_img))
                row_data[wagonAttachId] = img_name
            elif isinstance(wagon_img, str) and os.path.exists(wagon_img):
                row_data[wagonAttachId] = wagon_img

            if isinstance(wagon_img2, np.ndarray):
                img_name2 = os.path.join(self.history_dir, f"wagon_{wagon_number}_{idx}_{tm}_2.jpg")
                cv2.imwrite(img_name2, wagon_img2)
                row_data[wagonAttachId2] = img_name2
            elif isinstance(wagon_img2, QPixmap):
                img_name2 = os.path.join(self.history_dir, f"wagon_{wagon_number}_{idx}_{tm}_2.jpg")
                cv2.imwrite(img_name2, qpixmap_to_ndarray(pixmap=wagon_img2))
                row_data[wagonAttachId2] = img_name2
            elif isinstance(wagon_img2, str) and os.path.exists(wagon_img2):
                row_data[wagonAttachId2] = wagon_img2

            if isinstance(wagon_id_img, np.ndarray):
                img_id_name = os.path.join(self.history_dir, f"id_{wagon_number}_{idx}_{tm}.jpg")
                cv2.imwrite(img_id_name, wagon_id_img)
                row_data[wagonNumberAttachId] = img_id_name
            elif isinstance(wagon_id_img, QPixmap):
                img_id_name = os.path.join(self.history_dir, f"id_{wagon_number}_{idx}_{tm}.jpg")
                cv2.imwrite(img_id_name, qpixmap_to_ndarray(wagon_id_img))
                row_data[wagonNumberAttachId] = img_id_name
            elif isinstance(wagon_id_img, str) and os.path.exists(wagon_id_img):
                row_data[wagonNumberAttachId] = wagon_id_img

            if sent:
                dx_ = {
                    wagonNumber: wagon_number,
                    scaleNumber: scale_number,
                    stationCode: data.get(stationCode),
                    scaleCode: data.get(scaleCode),
                    wagonAttachId: row_data.get(wagonAttachId),
                    wagonAttachId2: row_data.get(wagonAttachId2),
                    wagonNumberAttachId: row_data.get(wagonNumberAttachId),
                    createdDate: created_date,
                    sentAt: sent_at,
                }
                real_id, er = self.backup_db.insert_history(data=dx_)
                if er:
                    show_message(
                        stl=self.style_name,
                        title="Xatolik",
                        message=f"[HistoryWidget.backup_db.insert_history] {er}"
                    )
                elif real_id:
                    # DB tomonidan berilgan haqiqiy ID ni ishlatamiz
                    idx = int(real_id)
                    row_data[ID] = idx

            month_key, y, m = self._make_month_key(row_data.get(createdDate))
            tree = self.trees_by_month.get(month_key)
            if tree is None:
                tree = self._create_tree_for_month(month_key, y, m)

            self._append_visual_row_to_tree(tree, row_data)
            tree.scrollToTop()

            now = datetime.now(_TZ_UZ)
            now_key = f"{now.year:04d}-{now.month:02d}"
            if month_key == now_key:
                keys = list(self.trees_by_month.keys())
                idx = keys.index(month_key)
                self.tabs.setCurrentIndex(idx)

        except (Exception, ValueError) as err:
            log(message=f"[HistoryWidget.add_row] {err}")
            print(f"[HistoryWidget.add_row] {err}")

    def _append_visual_row_to_tree(self, tree: QTreeWidget, row_data: dict) -> None:
        try:
            item: QTreeWidgetItem = QTreeWidgetItem()
            item.setText(0, str(row_data.get(ID, 0)))
            item.setTextAlignment(0, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)

            item.setText(1, str(row_data.get(wagonNumber, identifier * num_count)))
            item.setTextAlignment(1, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)

            tree.insertTopLevelItem(0, item)

            images = [
                row_data.get(wagonAttachId),
                row_data.get(wagonAttachId2),
                row_data.get(wagonNumberAttachId),
            ]

            btn_images = self._make_combined_image_button(
                paths=images,
                icon_sz=QSize(160, 64),
                title="Vagon rasmlari"
            )
            tree.setItemWidget(item, 2, btn_images)
            tree.viewport().update()

            norm_ton = get_wagon_norm_tonn(wagon_id=str(row_data.get(wagonNumber, identifier * num_count)))
            scale_num = int(row_data.get(scaleNumber, 0))
            extra_kg = scale_num - norm_ton

            if extra_kg > 0:
                extra_text = f"+{extra_kg / 1000:,.1f} t".replace(",", " ")
            else:
                extra_text = f"{extra_kg / 1000:,.1f} t".replace(",", " ")

            scale_text = f"{scale_num / 1000:,.1f} t".replace(",", " ")
            norm_text = f"{norm_ton / 1000:,.1f} t".replace(",", " ")

            item.setText(3, scale_text)
            item.setTextAlignment(3, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)

            item.setText(4, norm_text)
            item.setTextAlignment(4, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)

            item.setText(5, extra_text)
            item.setTextAlignment(5, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)

            if extra_kg >= 2000:
                color = QColor("#E53935")
            elif extra_kg > 0:
                color = QColor("#FDD835")
            else:
                color = QColor("#43A047")

            item.setForeground(5, QBrush(color))
            item.setData(5, Qt.ItemDataRole.UserRole, extra_kg)

            typ: str = get_wagon_type(wagon_id=row_data.get(wagonNumber, identifier * num_count))
            item.setText(6, typ)
            item.setTextAlignment(6, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)

            item.setText(7, self.utc_to_utc_5(dt_str=row_data.get(createdDate)))
            item.setTextAlignment(7, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)

            item.setText(8, self.utc_to_utc_5(dt_str=row_data.get(sentAt, "Yuborilmagan")))
            item.setTextAlignment(8, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)

        except (Exception, ValueError) as err:
            print(f"[HistoryWidget._append_visual_row_to_tree] {err}")
            log(message=f"[HistoryWidget._append_visual_row_to_tree] {err}")

    @staticmethod
    def utc_to_utc_5(dt_str: str | None) -> str:
        if dt_str is None:
            return "---"
        if "Yuborilmagan" in dt_str:
            return dt_str
        try:
            utc_dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
            uz_dt = utc_dt.astimezone(_TZ_UZ)
            fmt = uz_dt.isoformat().split("+")[0]
            fmt = fmt.replace("T", "\n")
            return fmt
        except (Exception, ValueError):
            return dt_str or "---"

    def _make_combined_image_button(self, paths: list[str | None], icon_sz: QSize, title: str) -> QPushButton:
        btn: QPushButton = QPushButton("Rasm")
        btn.setObjectName("image_btn")
        btn.setStyleSheet(self.style_)
        btn.setIconSize(icon_sz)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(partial(self._open_images_modal, title=title, paths=paths))
        return btn

    def _open_images_modal(self, title: str, paths: list[str | QPixmap | np.ndarray | None]) -> None:
        try:
            self.image_dialog: ImageDialog2 = ImageDialog2(
                style_name=self.style_name,
                _title=title,
                images=paths
            )
            self.image_dialog.exec()
        except (Exception, ValueError) as err:
            log(message=f"[HistoryWidget._open_images_modal] {err}")

    def resizeEvent(self, a0):
        width: int = self.width()
        self.widths: list[int] = [
            int(width * 0.058),
            int(width * 0.080),
            int(width * 0.104),
            int(width * 0.104),
            int(width * 0.104),
            int(width * 0.104),
            int(width * 0.150),
            int(width * 0.150),
            int(width * 0.150),
        ]

        for tree in self.trees_by_month.values():
            for i, w in enumerate(self.widths):
                tree.setColumnWidth(i, w)

    def change_style(self, style_name: str) -> None:
        self.style_name: str = style_name
        self.style_: str = get_styles(style_name=self.style_name)
        self.setStyleSheet(self.style_)
        self.tabs.setStyleSheet(self.style_)

        for month_key, tree in self.trees_by_month.items():
            tree.setStyleSheet(self.style_)

            for i in range(tree.topLevelItemCount()):
                item = tree.topLevelItem(i)
                if item:
                    extra_kg = item.data(5, Qt.ItemDataRole.UserRole)
                    if extra_kg is not None:
                        if extra_kg >= 2000:
                            color = QColor("#E53935")
                        elif extra_kg > 0:
                            color = QColor("#FDD835")
                        else:
                            color = QColor("#43A047")
                        item.setForeground(5, QBrush(color))

                    w = tree.itemWidget(item, 2)
                    if w:
                        w.setStyleSheet(self.style_)

        if self.image_dialog:
            self.image_dialog.setStyleSheet(self.style_)

