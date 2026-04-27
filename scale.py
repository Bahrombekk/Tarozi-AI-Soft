"""
Tarozi (tarvozi) bilan ishlash moduli.

Loyihada ishlatiladigan to'liq tarozi kodi:
  1. COM portlarni topish
  2. Serial ulanish ochish
  3. Og'irlikni o'qish (protokol: STX + "AB03" + ETX)
  4. ScaleThread — fonda doimiy o'qib, signal beruvchi thread
  5. UI da og'irlikni qabul qilish va ko'rsatish

Ulanish sxemasi:
  Tarozi qurilmasi  ──USB/RS-232──►  COM port  ──►  ScaleThread  ──signal──►  UI (scale_weight)
"""
from __future__ import annotations

import threading
from typing import Optional

import serial
import serial.tools.list_ports
from PyQt6.QtCore import QThread, pyqtSignal

from core.config import BOUND_RATE, scale_sleep_ms, log


# ──────────────────────────────────────────────
# 1. COM PORTLARNI TOPISH
# ──────────────────────────────────────────────

def find_all_scale_ports() -> list[str]:
    """
    Kompyuterga ulangan barcha COM portlarni qaytaradi.

    Returns:
        ['COM3', 'COM5', ...] — topilgan port nomlari ro'yxati
    """
    ports = serial.tools.list_ports.comports()
    return [p.device for p in ports if "COM" in p.device]


# ──────────────────────────────────────────────
# 2. SERIAL ULANISHLARNI OCHISH
# ──────────────────────────────────────────────

def open_all_scales() -> list[serial.Serial]:
    """
    Topilgan har bir COM portga serial ulanish ochadi.

    Serial sozlamalar (tarozi qurilmasi standartiga mos):
      - Baud rate : BOUND_RATE (odatda 9600)
      - Data bits : 8
      - Parity    : None
      - Stop bits : 1
      - Timeout   : 1 soniya

    Returns:
        Ochilgan Serial ob'ektlar ro'yxati. Ulanmagan portlar o'tkazib yuboriladi.
    """
    ports = find_all_scale_ports()
    serial_ports: list[serial.Serial] = []

    for port in ports:
        try:
            ser = serial.Serial(
                port=port,
                baudrate=BOUND_RATE,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=1,
            )
            serial_ports.append(ser)
            log(message=f"[open_all_scales] {port} ochildi", level="INFO")
        except Exception as err:
            log(message=f"[open_all_scales] {port} ochilmadi: {err}")

    return serial_ports


# ──────────────────────────────────────────────
# 3. OG'IRLIKNI O'QISH (PROTOKOL)
# ──────────────────────────────────────────────

# Tarozi protokoli (industrial RS-232 scale protocol):
#
# So'rov paketi:
#   [STX][A][B][0][3][ETX]
#   0x02  41 42 30 33  0x03
#
# Javob paketi (13 bayt):
#   Bayt  0   : STX       — 0x02
#   Bayt  1-2 : qurilma ID
#   Bayt  3   : sign      — '+' yoki '-'
#   Bayt  4-9 : og'irlik  — 6 ta ASCII raqam (masalan "020000" = 20000)
#   Bayt  10  : vergul    — kasr o'rni (0 = butun son)
#   Bayt  11  : status
#   Bayt  12  : ETX       — 0x03
#
# Misol: 0x02 .. .. '+' '0' '2' '0' '0' '0' '0' '0' .. 0x03
#        → sign='+', digits="020000", decimal=0  → og'irlik = 20000 kg

_SCALE_COMMAND: bytes = b"\x02AB03\x03"


def read_weight(ser: serial.Serial) -> int:
    """
    Taroziga so'rov yuborib, og'irlikni kg da qaytaradi.

    Args:
        ser: Ochiq Serial ulanish

    Returns:
        Og'irlik (kg, butun son). Xato yoki noto'g'ri javobda 0.
    """
    try:
        ser.write(_SCALE_COMMAND)
        response: bytes = ser.read_until(expected=b"\x03")

        if not response:
            return 0

        # Paket to'g'riligini tekshirish
        if response[0] != 0x02 or response[-1] != 0x03:
            return 0

        sign_char: str  = chr(response[3])          # '+' yoki '-'
        digits_str: str = response[4:10].decode("ascii")  # "020000"
        decimal_pos: int = int(chr(response[10]))    # 0, 1, 2, ...

        weight_value: float = int(digits_str)
        if decimal_pos > 0:
            weight_value = weight_value / (10 ** decimal_pos)
        if sign_char == "-":
            weight_value = -weight_value

        return int(weight_value)

    except Exception as err:
        log(message=f"[read_weight] {err}")
        return 0


# ──────────────────────────────────────────────
# 4. SCALE THREAD — FONDA DOIMIY O'QISH
# ──────────────────────────────────────────────

class ScaleThread(QThread):
    """
    Barcha ulangan tarozilardan doimiy og'irlik o'qib, signal beruvchi thread.

    Signallar:
        scale_signal (dict)  — {port_nomi: og'irlik_kg, ...}
                               Masalan: {'COM3': 20000, 'COM5': 15000}
        error_signal (str)   — xato xabari

    Ishlash tartibi:
        1. Har bir COM portdan og'irlik o'qiladi
        2. Natijalar dict sifatida scale_signal orqali UI ga yuboriladi
        3. scale_sleep_ms (sozlamada belgilangan) kutiladi
        4. Takrorlanadi — stop() chaqirilgunga qadar

    Misol:
        thread = ScaleThread(scales=open_all_scales(), com_ports=['COM3'])
        thread.scale_signal.connect(my_handler)
        thread.start()
        ...
        thread.stop()
    """

    scale_signal = pyqtSignal(dict)   # {port: weight_kg}
    error_signal = pyqtSignal(str)

    def __init__(self,
                 scales: list[serial.Serial],
                 com_ports: Optional[list[str]] = None):
        super().__init__()
        self.scales: list[serial.Serial] = scales
        self.com_ports: list[str] = com_ports or []
        self._stop_event = threading.Event()

        # O'qish/yozish timeout ni qisqa qilamiz — thread tez to'xtasin
        for ser in self.scales:
            try:
                ser.timeout = 0.3
                ser.write_timeout = 0.5
            except Exception as err:
                log(message=f"[ScaleThread.__init__] {ser.port} timeout: {err}")

    def run(self):
        try:
            while not self._stop_event.is_set() and not self.isInterruptionRequested():

                # Har bir portdan og'irlik o'qish
                massa: dict[str, int] = {p: 0 for p in self.com_ports}
                for ser in list(self.scales):
                    if self._stop_event.is_set() or self.isInterruptionRequested():
                        break
                    try:
                        port = str(ser.port)
                        massa[port] = read_weight(ser)
                    except Exception as err:
                        msg = f"[ScaleThread] {ser.port}: aloqa yo'q — {err}"
                        self.error_signal.emit(msg)
                        log(message=msg)

                if self._stop_event.is_set() or self.isInterruptionRequested():
                    break

                self.scale_signal.emit(massa)

                # Keyingi o'qishgacha kutish (10ms bo'laklarda — tez to'xtash uchun)
                waited = 0
                while (waited < scale_sleep_ms
                       and not self._stop_event.is_set()
                       and not self.isInterruptionRequested()):
                    self.msleep(10)
                    waited += 10

        finally:
            self._close_all()

    def stop(self):
        """Threadni xavfsiz to'xtatadi."""
        self._stop_event.set()
        self.requestInterruption()
        # Timeout ni qisqartirib tezroq chiqishga yordam beramiz
        for ser in self.scales:
            try:
                ser.timeout = 0.05
                ser.write_timeout = 0.05
            except Exception:
                pass
        if not self.wait(1000):
            self.terminate()
            self.wait(500)

    def _close_all(self):
        """Barcha serial portlarni yopadi."""
        for ser in self.scales:
            try:
                ser.reset_input_buffer()
                ser.reset_output_buffer()
                ser.close()
                log(message=f"[ScaleThread] {ser.port} yopildi", level="INFO")
            except Exception as err:
                self.error_signal.emit(f"[ScaleThread.close] {err}")
                log(message=f"[ScaleThread.close] {err}")


# ──────────────────────────────────────────────
# 5. UI DA ISHLATILADIGAN KOD (app_responses.py)
# ──────────────────────────────────────────────
#
# Quyidagi kod `ResponseMixin` klassiga tegishli.
# ScaleThread.scale_signal → self.scale_weight() ga ulanadi.
#
# Ulanish (app.py / main_window.py da):
#
#   self.scales   = open_all_scales()
#   self.com_ports = [str(s.port) for s in self.scales]
#   self.scale_thread = ScaleThread(scales=self.scales, com_ports=self.com_ports)
#   self.scale_thread.scale_signal.connect(self.scale_weight)
#   self.scale_thread.start()
#
# ──────────────────────────────────────────────
#
#   def scale_weight(self, massa: dict):
#       """
#       ScaleThread dan kelgan og'irlikni qabul qiladi.
#
#       Args:
#           massa: {port_nomi: og'irlik_kg}
#                  Masalan: {'COM3': 20000, 'COM5': 15000}
#                  Bo'sh dict = tarozi nol ko'rsatyapti
#       """
#       try:
#           if massa:
#               ms = sum(massa.values())   # Barcha tarozilar yig'indisi (kg)
#
#               # Yig'indi min_send_kg dan kam bo'lsa — ma'lumotlarni tozalaymiz
#               # (vagon yo'q yoki tarozi chegaradan past)
#               if min_send_kg > max(self.last_scale_weight):
#                   self.sending_data.clear()
#                   self.last_data_left = {}
#                   self.last_data_right = {}
#                   self.wagon_image = self.wagon_image2 = None
#                   ...
#
#               # Ekranda ko'rsatish
#               if self.config.get(SCALE_VIEW, False):
#                   # Haqiqiy qiymat ko'rsatiladi
#                   sc_txt = f"{' + '.join([f'{k}({v})' for k, v in massa.items()])} = {ms} kg"
#               else:
#                   # Xavfsizlik uchun yashiriladi
#                   sc_txt = f"{' + '.join([f'{k}(*****)' for k in massa])} = ***** kg"
#
#               self.hor_left_widget.right_lbl.setText(sc_txt)
#
#               # Tarixi saqlanadi (so'nggi max_scale_weight ta o'lchamdan maksimum ishlatiladi)
#               self.last_scale_weight.append(ms)
#               if len(self.last_scale_weight) > self.max_scale_weight:
#                   self.last_scale_weight.pop(0)
#           else:
#               self.hor_left_widget.right_lbl.setText("0 kg")
#       except Exception as err:
#           log(message=f"[scale_weight] {err}")
#
# Yuborishda (app_upload.py da):
#   self.sending_data.scaleNumber = max(self.last_scale_weight)
#   # → so'nggi 5 ta o'lchamdagi eng katta qiymat serverga yuboriladi


# ──────────────────────────────────────────────
# TAROZI PROTOKOLI TUZILISHI (vizual)
# ──────────────────────────────────────────────
#
#  So'rov: b"\x02AB03\x03"
#  ┌──────┬───┬───┬───┬───┬──────┐
#  │ 0x02 │ A │ B │ 0 │ 3 │ 0x03 │
#  │ STX  │   cmd   │   │  ETX  │
#  └──────┴───┴───┴───┴───┴──────┘
#
#  Javob: 13 bayt
#  ┌──────┬─────┬──────┬────────────────────┬─────────┬────────┬──────┐
#  │ 0x02 │ ID  │ sign │   6 ta raqam        │ kasr    │ status │ 0x03 │
#  │  [0] │[1-2]│  [3] │     [4 - 9]         │  [10]   │  [11]  │ [12] │
#  │ STX  │     │ +/-  │ "020000" = 20000 kg │   0     │        │ ETX  │
#  └──────┴─────┴──────┴────────────────────┴─────────┴────────┴──────┘
#
#  Hisoblash:
#    weight = int("020000") = 20000
#    decimal = 0  →  20000 / 10^0 = 20000 kg
#    sign = '+'  →  +20000 kg
