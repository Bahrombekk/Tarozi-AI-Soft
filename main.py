import sys
import os
import threading
import ctypes

# Working directory ni to'g'rilash
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication, QSplashScreen, QMessageBox
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt
from PyQt6.QtNetwork import QLocalSocket, QLocalServer


def _is_elevated() -> bool:
    """cv2/numpy yuklamasdan turib admin huquqini tekshiradi."""
    if os.name != "nt":
        return hasattr(os, "geteuid") and os.geteuid() == 0
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def _show_admin_warning():
    """Og'ir importlarsiz oddiy ogohlantirish oynasi."""
    mb = QMessageBox()
    mb.setIcon(QMessageBox.Icon.Warning)
    mb.setWindowTitle("Ogohlantirish")
    mb.setText("Dasturni administrator huquqlari bilan oching!!!")
    mb.setStandardButtons(QMessageBox.StandardButton.Ok)
    mb.exec()


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Bitta nusxa tekshiruvi
    from core.config import APP_ID
    QLocalServer.removeServer(APP_ID)
    socket = QLocalSocket()
    socket.connectToServer(APP_ID)
    if socket.waitForConnected(200):
        socket.disconnectFromServer()
        print("Dastur allaqachon ishlamoqda!")
        sys.exit(0)

    server = QLocalServer()
    server.listen(APP_ID)

    # Admin tekshiruvi — og'ir import yo'q, splash dan oldin tez bajariladi
    if not _is_elevated():
        _show_admin_warning()
        sys.exit(1)

    # Splash screen — iloji boricha erta ko'rsatiladi
    splash_pix = QPixmap("images/train.png")
    if not splash_pix.isNull():
        splash_pix = splash_pix.scaledToWidth(400, Qt.TransformationMode.SmoothTransformation)
    else:
        splash_pix = QPixmap(400, 200)
        splash_pix.fill(Qt.GlobalColor.darkBlue)
    splash = QSplashScreen(splash_pix)
    splash.show()
    app.processEvents()

    # Ping — splash ko'ringandan keyin fonda yuboriladi
    def _send_startup_ping():
        try:
            import requests
            from ui.settings_manager import SettingsManager
            from core.config import STATION_CODE, default_station_code
            cfg = SettingsManager(filename="settings/settings.bin").data
            code = str(cfg.get(STATION_CODE, default_station_code))
            requests.post(
                url="https://ai-project.das-uty.uz/api/wagon-scale-values/ping",
                json={"stationCode": code},
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
        except Exception as e:
            print(f"[ping] {e}")

    threading.Thread(target=_send_startup_ping, daemon=True).start()

    # Og'ir importlar splash ko'rsatilgandan keyin yuklanadi
    from ui.main_window import App
    window = App()
    splash.finish(window)
    window.show()

    ret = app.exec()
    server.close()
    sys.exit(ret)


if __name__ == "__main__":
    main()
