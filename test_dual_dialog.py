"""
WagonChoiceDialog ni kamera kerak bo'lmagan holda sinash uchun.
Ishga tushirish: python test_dual_dialog.py
"""
import sys
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import cv2
from PyQt6.QtWidgets import QApplication, QDialog

from core.config import (
    wagonNumber, wagonAttachId, wagonNumberAttachId, BBOX, CONF, LIGHT
)


def _make_number_image(number: str, w: int = 320, h: int = 80) -> np.ndarray:
    """Vagon raqami yozilgan sintetik rasm yaratadi."""
    img = np.ones((h, w, 3), dtype=np.uint8) * 30
    cv2.putText(img, number, (10, h - 15),
                cv2.FONT_HERSHEY_DUPLEX, 1.6, (0, 230, 0), 2)
    return img


def _make_wagon_image(color: tuple, w: int = 640, h: int = 360) -> np.ndarray:
    """Shartli vagon asosiy rasmi."""
    img = np.ones((h, w, 3), dtype=np.uint8) * 50
    cv2.rectangle(img, (30, 60), (w - 30, h - 60), color, -1)
    return img


def build_mock_candidates() -> list:
    return [
        {
            wagonNumber: "28090348",
            wagonNumberAttachId: _make_number_image("28090348"),
            wagonAttachId: _make_wagon_image((40, 120, 200)),
            BBOX: [10, 20, 300, 200],
            CONF: 0.94,
        },
        {
            wagonNumber: "52616497",
            wagonNumberAttachId: _make_number_image("52616497"),
            wagonAttachId: _make_wagon_image((200, 80, 40)),
            BBOX: [320, 20, 610, 200],
            CONF: 0.91,
        },
    ]


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    from ui.dialogs import WagonChoiceDialog, RepeatWagonDialog

    style = sys.argv[1] if len(sys.argv) > 1 else LIGHT   # python test_dual_dialog.py DARK
    mode  = sys.argv[2] if len(sys.argv) > 2 else "dual"  # python test_dual_dialog.py DARK repeat

    if mode == "repeat":
        print(f"RepeatWagonDialog ochilmoqda ({style} tema)...")
        dlg = RepeatWagonDialog(
            style_name=style,
            wagon_number="76024827",
            weighed_at="11:46:21",
            weight_kg="87500",
        )  # COUNTDOWN_MS = 60_000 (60 soniya)
        result = dlg.exec()
        print("Ha bosildi" if result == QDialog.DialogCode.Accepted else "Yo'q bosildi / yopildi")
    else:
        candidates = build_mock_candidates()
        print(f"WagonChoiceDialog ochilmoqda ({style} tema)...")
        dlg = WagonChoiceDialog(style_name=style, candidates=candidates)
        result = dlg.exec()
        if result == QDialog.DialogCode.Accepted and dlg.selected:
            print(f"Tanlandi: {dlg.selected.get(wagonNumber)}")
        else:
            print("Bekor qilindi.")

    sys.exit(0)


if __name__ == "__main__":
    main()
