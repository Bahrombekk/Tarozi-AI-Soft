from __future__ import annotations
import threading
from PyQt6.QtCore import QThread, pyqtSignal, QWaitCondition, QMutex
from core.config import (
    scale_sleep_ms, base_url, get_token_url, default_username, default_password, log
)
from network.api import check_internet_connection, check_server, login, ping
from utils.helpers import check_rtsp_connection, get_ip_and_port, read_weight, get_base_url


class ServerConnectionThread(QThread):
    connection_signal = pyqtSignal(bool)

    def __init__(self, bs_url: str = get_base_url()):
        super().__init__()
        self._stop_event = threading.Event()
        self._cond = QWaitCondition()
        self._mutex = QMutex()
        self.base_url: str = bs_url

    def run(self):
        while not self._stop_event.is_set():
            try:
                if not check_internet_connection():
                    self.connection_signal.emit(False)
                    self.msleep(9500)
                    continue
                res = check_server(domain_name=self.base_url)
                self.connection_signal.emit(res)
                self.msleep(53000)
            except Exception as err:
                log(message=f"[ServerConnectionThread.run] {err}")
                self.msleep(9500)

    def stop(self):
        self._stop_event.set()
        self.requestInterruption()
        self._cond.wakeOne()


class ProgressThread(QThread):
    value_signal = pyqtSignal(int)

    def __init__(self):
        super().__init__()

    def run(self):
        for i in range(1, 5):
            self.msleep(500)
            self.value_signal.emit(i)


class LoginThread(QThread):
    login_signal = pyqtSignal(bool, dict)

    def __init__(self, login_url: str, data: dict[str, str]):
        super().__init__()
        self._stop_event = threading.Event()
        self._cond = QWaitCondition()
        self._mutex = QMutex()
        self.login_url: str = login_url
        self.data: dict = data

        self.retry_no_internet_ms = 296_000
        self.success_sleep_ms = 3_500_000

    def run(self):
        try:
            while not self._stop_event.is_set() and not self.isInterruptionRequested():
                if not check_internet_connection():
                    self.login_signal.emit(False, {"response": "Internet Connection Failed"})
                    self._mutex.lock()
                    self._cond.wait(self._mutex, self.retry_no_internet_ms)
                    self._mutex.unlock()
                    continue

                try:
                    ans, data = login(url=self.login_url, data=self.data)
                except Exception as exc:
                    log(message=f"[LoginThread.login] {exc}")
                    ans, data = False, {"response": f"ERROR: {exc}"}

                self.login_signal.emit(ans, data)

                self._mutex.lock()
                self._cond.wait(self._mutex, self.success_sleep_ms)
                self._mutex.unlock()

        except Exception as err:
            log(message=f"[LoginThread.run] unexpected error: {err}")
            self.login_signal.emit(False, {"response": f"ERROR: {err}"})

    def stop(self):
        self._stop_event.set()
        self.requestInterruption()
        self._cond.wakeOne()


class SaveThread(QThread):
    save_signal = pyqtSignal(bool)

    def __init__(self, url: str):
        super().__init__()
        try:
            self.ip, self.port = get_ip_and_port(cam_url=url)
        except Exception:
            self.ip: str = "192.168.1.64"
            self.port: int = 554

    def run(self):
        try:
            result = check_rtsp_connection(ip=self.ip, port=self.port, tm=2)
            self.save_signal.emit(result)
        except Exception as err:
            log(message=f"[SaveThread.run] {err}")
            self.save_signal.emit(False)
        finally:
            self.finished.emit()


class ScaleThread(QThread):
    scale_signal = pyqtSignal(dict)
    error_signal = pyqtSignal(str)

    def __init__(self, scales: list, com_ports: list[str] | None = None):
        super().__init__()
        self.com_ports = com_ports or []
        self.scales = scales
        self._stop_event = threading.Event()
        try:
            for ser in self.scales:
                ser.timeout = 0.3
                ser.write_timeout = 0.5
        except Exception as err:
            log(message=f"[ScaleThread.__init__.set_timeout] {err}")

    def run(self):
        try:
            while not self._stop_event.is_set() and not self.isInterruptionRequested():
                massa: dict[str, int] = {p: 0 for p in self.com_ports}

                for ser in list(self.scales):
                    if self._stop_event.is_set() or self.isInterruptionRequested():
                        break
                    try:
                        port = str(ser.port)
                        weight = read_weight(ser)
                        massa[port] = weight
                    except Exception as err:
                        self.error_signal.emit(f"[ScaleThread.run] {ser.port}: aloqa yo'q. Xato: {err}")
                        log(message=f"[ScaleThread.run] {ser.port}: aloqa yo'q. Xato: {err}")

                if self._stop_event.is_set() or self.isInterruptionRequested():
                    break
                self.scale_signal.emit(massa)
                total = 0
                while total < scale_sleep_ms and not self._stop_event.is_set() and not self.isInterruptionRequested():
                    self.msleep(10)
                    total += 10
        finally:
            for ser in self.scales:
                try:
                    try:
                        ser.reset_input_buffer()
                        ser.reset_output_buffer()
                    except Exception as err:
                        log(message=f"[ScaleThread.run.finally] {err}")
                    ser.close()
                except Exception as err:
                    self.error_signal.emit(f"[ScaleThread.close] {err}")
                    log(message=f"[ScaleThread.close] {err}")

    def stop(self):
        self._stop_event.set()
        self.requestInterruption()
        try:
            for ser in self.scales:
                try:
                    ser.timeout = 0.05
                    ser.write_timeout = 0.3
                except Exception:
                    pass
            if not self.wait(1000):
                self.terminate()
                self.wait(500)
        except Exception as err:
            log(message=f"[ScaleThread.stop] {err}")



class PingThread(QThread):

    def __init__(self, station_code: str, interval_ms: int = 60_000):
        super().__init__()
        self._stop_event = threading.Event()
        self.station_code = station_code
        self.interval_ms = interval_ms

    def run(self):
        while not self._stop_event.is_set():
            try:
                ping(station_code=self.station_code)
            except Exception as err:
                log(message=f"[PingThread.run] {err}", level="ERROR")
            total = 0
            while total < self.interval_ms and not self._stop_event.is_set():
                self.msleep(200)
                total += 200

    def stop(self):
        self._stop_event.set()
        self.requestInterruption()
