import base64
import ctypes
import os
import sys
import subprocess
from ctypes import wintypes
from typing import Union
from urllib.parse import urlparse
from PyQt6.QtCore import (
    Qt, QSize, QEvent, QRegularExpression, QObject,
)
from PyQt6.QtGui import (
    QIcon, QImage, QPixmap, QPainter, QPainterPath, QColor,
    QRegularExpressionValidator,
)
from PyQt6.QtNetwork import QLocalSocket, QLocalServer
from PyQt6.QtWidgets import (
    QApplication, QMessageBox,
)
from PyQt6.QtCore import QRectF
import cv2
import sqlite3
import numpy as np
import socket

from core.config import (
    APP_ID, BOUND_RATE, LOG_PATH, URL_NOT_FOUND,
    backup_folder, base_url, default_cam_url, default_distance, default_frame_count,
    default_password, default_station_code, default_scale_code, default_username,
    get_token_url, identifier, log, num_count, offset, table_name, timeout,
    top_offset, bottom_offset, left_offset, right_offset,
    min_frame_count, max_frame_count, min_distance, max_distance,
    files, static_password, DARK, LIGHT,
)
from core.cipher import Cipher
from ui.styles import (
    get_hover_color, get_text_color, get_bg_color, font,
)

# ---- Canonical network functions (re-exported for backward compatibility) ----
from network.api import (  # noqa: F401
    login, check_server, check_internet_connection, get_token, image_to_base64, get_base_url,
)

cipher: Cipher = Cipher()

application: QApplication = QApplication.instance() or QApplication([])
_screen_geom = application.primaryScreen().availableGeometry()
SCREEN_WIDTH: int = _screen_geom.width()
SCREEN_HEIGHT: int = _screen_geom.height()

WIDTH: int = int(SCREEN_WIDTH * 0.85)
HEIGHT: int = int(SCREEN_HEIGHT * 0.90)

try:
    window_icon: QIcon = QIcon("images/train.png")
except Exception:
    window_icon: QIcon | None = None


# ---------- Admin check ----------

def is_process_elevated() -> bool:
    if os.name != "nt":
        return hasattr(os, "geteuid") and os.geteuid() == 0
    try:
        TOKEN_QUERY = 0x0008
        TokenElevation = 20

        HANDLE = wintypes.HANDLE
        DWORD = wintypes.DWORD

        OpenProcessToken = ctypes.windll.advapi32.OpenProcessToken
        OpenProcessToken.argtypes = [HANDLE, wintypes.DWORD, ctypes.POINTER(HANDLE)]
        OpenProcessToken.restype = wintypes.BOOL

        GetTokenInformation = ctypes.windll.advapi32.GetTokenInformation
        GetTokenInformation.argtypes = [HANDLE, ctypes.c_uint, ctypes.c_void_p, DWORD, ctypes.POINTER(DWORD)]
        GetTokenInformation.restype = wintypes.BOOL

        CloseHandle = ctypes.windll.kernel32.CloseHandle
        CloseHandle.argtypes = [HANDLE]
        CloseHandle.restype = wintypes.BOOL

        h_process = ctypes.windll.kernel32.GetCurrentProcess()
        h_token = HANDLE()

        if not OpenProcessToken(h_process, TOKEN_QUERY, ctypes.byref(h_token)):
            return False
        try:
            elevation = DWORD()
            size = DWORD(ctypes.sizeof(elevation))
            ok = GetTokenInformation(h_token, TokenElevation,
                                     ctypes.byref(elevation), ctypes.sizeof(elevation),
                                     ctypes.byref(size))
            if not ok:
                return False
            return bool(elevation.value)
        finally:
            CloseHandle(h_token)

    except Exception as err:
        log(message=f"[is_process_elevated] {err}")
        try:
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception as err2:
            log(message=f"[is_process_elevated.fallback] {err2}")
            return False


# ---------- UI dialogs ----------

def ask_message(stl: str, title: str = "Tanlang", message: str = "Tanlang") -> int:
    msb = QMessageBox()
    msb.setIcon(QMessageBox.Icon.Question)
    msb.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
    msb.setMinimumWidth(250)
    msb.setMinimumHeight(200)
    bg_c = get_bg_color(style_name=stl)
    hv_c = get_hover_color(style_name=stl)
    txt_c = get_text_color(style_name=stl)
    msb.setStyleSheet(f"background-color: {bg_c}; color: {txt_c}; font-size: 18px;")
    btn_style = f"""
        QPushButton#yes_no_btn {{
            background: {bg_c}; color: {txt_c}; font-size: 16px;
        }}
        QPushButton#yes_no_btn:hover {{
            background: {hv_c};
        }}
    """
    yes_button = msb.button(QMessageBox.StandardButton.Yes)
    no_button = msb.button(QMessageBox.StandardButton.No)
    yes_button.setText("Ha")
    no_button.setText("Yo'q")
    yes_button.setObjectName("yes_no_btn")
    no_button.setObjectName("yes_no_btn")
    yes_button.setStyleSheet(btn_style)
    no_button.setStyleSheet(btn_style)
    if window_icon:
        msb.setWindowIcon(window_icon)
    msb.setText(message)
    msb.setWindowTitle(title)
    msb.setDefaultButton(no_button)
    return msb.exec()


def show_message(stl: str, message: str = "Xabar", title: str = "Xabar") -> int:
    msb = QMessageBox()
    msb.setIcon(QMessageBox.Icon.Information)
    msb.setStandardButtons(QMessageBox.StandardButton.Yes)
    msb.setMinimumWidth(250)
    msb.setMinimumHeight(200)
    bg_c = get_bg_color(style_name=stl)
    hv_c = get_hover_color(style_name=stl)
    txt_c = get_text_color(style_name=stl)
    msb.setStyleSheet(f"background-color: {bg_c}; color: {txt_c}; font-size: 18px;")
    btn_style = f"""
        QPushButton#yes_no_btn {{
            background: {bg_c}; color: {txt_c}; font-size: 16px;
        }}
        QPushButton#yes_no_btn:hover {{
            background: {hv_c};
        }}
    """
    yes_button = msb.button(QMessageBox.StandardButton.Yes)
    yes_button.setText("Ha")
    yes_button.setObjectName("yes_no_btn")
    yes_button.setStyleSheet(btn_style)
    if isinstance(window_icon, QIcon):
        msb.setWindowIcon(window_icon)
    msb.setText(message)
    msb.setWindowTitle(title)
    msb.setDefaultButton(QMessageBox.StandardButton.No)
    return msb.exec()


# ---------- Directories ----------

history_folder: str = "history"

for _dir in ("images", "models", "settings", backup_folder, history_folder):
    os.makedirs(_dir, exist_ok=True)

verbose: bool = False

# ---------- UI constants ----------

item_height: int = 80
icon_size: QSize = QSize(28, 28)
icon_size1: QSize = QSize(32, 32)
icon_size4: QSize = QSize(86, 42)

window_pixmap: QPixmap = QPixmap("images/icon.svg")

view_icon: QIcon = QIcon("images/view_eye.png")
unview_icon: QIcon = QIcon("images/unview_eye.png")
view_icon_light: QIcon = QIcon("images/view_eye_light.png")
unview_icon_light: QIcon = QIcon("images/unview_eye_light.png")
fail_icon: QIcon = QIcon("images/fail.png")
success_icon: QIcon = QIcon("images/success.png")
no_image_pixmap: QPixmap = QPixmap("images/no_image.png")
cam_frame: QPixmap = QPixmap("images/frame.png")
cam_frame_light: QPixmap = QPixmap("images/frame-light.png")
weight_pixmap: QPixmap = QPixmap("images/gentle.png")
time_pixmap: QPixmap = QPixmap("images/clock.png")


# ---------- Event filter ----------

class _GlobalMouseReleaseFilter(QObject):
    def __init__(self, parent):
        super().__init__(parent)

    def eventFilter(self, obj, ev):
        if ev.type() == QEvent.Type.MouseButtonRelease:
            self.parent().eventFilter(self.parent(), ev)
            return False
        return super().eventFilter(obj, ev)


# ---------- Validators ----------

def make_range_validator(a: int, b: int) -> QRegularExpressionValidator:
    if a > b:
        a, b = b, a
    patterns = []
    if b < 10:
        patterns.append(f"[{a}-{b}]")
    else:
        for n in range(a, b + 1):
            patterns.append(str(n))
    pattern = "^(" + "|".join(patterns) + ")$"
    regex = QRegularExpression(pattern)
    return QRegularExpressionValidator(regex)


# ---------- Time helpers ----------

def current_time() -> str:
    import datetime as _dt
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def timer_back(tm: str) -> str:
    try:
        h, m, s = tm.split(":")[:3]
        vq = int(h) * 3600 + int(m) * 60 + int(s) - 1
        return f"{vq // 3600:02}:{(vq % 3600) // 60:02}:{vq % 60:02}"
    except Exception:
        return "00:00:10"


# ---------- URL / network helpers ----------

def get_ip_and_port(cam_url: str) -> tuple[str, int]:
    if not cam_url or not cam_url.strip():
        return "192.168.1.64", 554
    if not cam_url.lower().startswith("rtsp://"):
        cam_url = "rtsp://" + cam_url.lstrip("/")
    try:
        parsed = urlparse(cam_url)
        netloc = parsed.netloc
        if not netloc:
            return "192.168.1.64", 554
        if '@' in netloc:
            netloc = netloc.split('@')[-1]
        if ':' in netloc:
            host_part, port_part = netloc.rsplit(':', 1)
            try:
                port = int(port_part)
            except ValueError:
                port = 554
        else:
            host_part = netloc
            port = 554
        host = host_part.strip('[]')
        return host, port
    except Exception as err:
        log(message=f"[get_ip_and_port] RTSP URL parse error: {err}")
        return "192.168.1.64", 554


def get_ip(cam_url: str = default_cam_url) -> str:
    host, _ = get_ip_and_port(cam_url)
    return host


def get_port(cam_url: str = default_cam_url) -> int:
    _, port = get_ip_and_port(cam_url)
    return port


def check_rtsp_connection(ip: str, port: int = 554, tm: int = 2) -> bool:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(tm)
    try:
        sock.connect((ip, port))
        return True
    except (socket.error, socket.timeout):
        return False
    finally:
        sock.close()


# ---------- DB queries ----------

def get_wagon_norm_tonn(wagon_id: str) -> int:
    try:
        connection = sqlite3.connect(database=f"settings/{table_name}.sqlite3")
        cursor = connection.cursor()
        cursor.execute(
            f"SELECT wagon_norm_tonn FROM {table_name} WHERE wagon_number = ? LIMIT 1;",
            (wagon_id,),
        )
        row = cursor.fetchone()
        connection.close()
        return int(row[0]) if row else 0
    except Exception as err:
        log(message=f"[get_wagon_norm_tonn] {err}")
        return 0


# ---------- Wagon type ----------

_WAGON_TYPES = {
    "2": "Крытый",
    "3": "фитинговая платформа",
    "4": "Платформа",
    "5": "Газовая цистерна,\nмашина-вагон",
    "6": "Полувагон",
    "7": "Цистерна",
    "8": "Рефрижератор",
    "9": "Прочие фитинговые\n платформы",
}


def get_wagon_type(wagon_id: str) -> str:
    if wagon_id:
        return _WAGON_TYPES.get(wagon_id[0], "Неизвестный тип")
    return "Неизвестный тип"


# ---------- Image helpers ----------

def resize_img(img_res: np.ndarray, w: int | None = None) -> np.ndarray:
    if w is not None:
        img_res = cv2.resize(img_res, (w, int(w * img_res.shape[0] / img_res.shape[1])))
    return img_res


def apply_clahe_bgr(img: np.ndarray) -> np.ndarray:
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l_ch, a_ch, b_ch = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    cl = clahe.apply(l_ch)
    merged = cv2.merge((cl, a_ch, b_ch))
    return cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)


def rounded_pixmap(pixmap: QPixmap, radius: int = 15) -> QPixmap:
    size = pixmap.size()
    rounded = QPixmap(size)
    rounded.fill(Qt.GlobalColor.transparent)
    painter = QPainter(rounded)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    path = QPainterPath()
    path.addRoundedRect(QRectF(0, 0, size.width(), size.height()), radius, radius)
    painter.setClipPath(path)
    painter.drawPixmap(0, 0, pixmap)
    painter.end()
    return rounded


def cv2_to_qpixmap(cv_img: np.ndarray, fmt: bool = False) -> QPixmap:
    height, width, channel = cv_img.shape
    bytes_per_line = channel * width
    cv_img = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
    q_image = QImage(cv_img.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)
    if fmt:
        return QPixmap.fromImage(q_image)
    return QPixmap.fromImage(q_image).scaled(236, 48)


def qpixmap_to_ndarray(pixmap: Union[QPixmap, np.ndarray, None]) -> np.ndarray | None:
    if pixmap is None:
        return None
    if isinstance(pixmap, np.ndarray):
        return pixmap
    image = pixmap.toImage().convertToFormat(QImage.Format.Format_RGBA8888)
    width = image.width()
    height = image.height()
    ptr = image.bits()
    ptr.setsize(width * height * 4)
    arr = np.array(ptr, dtype=np.uint8).reshape((height, width, 4))
    return cv2.cvtColor(arr, cv2.COLOR_RGBA2BGR)


# ---------- Serial / scale ----------

def find_all_scale_ports() -> list[str]:
    import serial.tools.list_ports
    ports = serial.tools.list_ports.comports()
    return [p.device for p in ports if "COM" in p.device]


def open_all_scales() -> list:
    import serial as _serial
    ports = find_all_scale_ports()
    serial_ports: list = []
    for port in ports:
        try:
            ser = _serial.Serial(
                port, baudrate=BOUND_RATE, bytesize=_serial.EIGHTBITS,
                parity=_serial.PARITY_NONE,
                stopbits=_serial.STOPBITS_ONE, timeout=1,
            )
            serial_ports.append(ser)
        except Exception as err:
            log(message=f"[open_all_scales] {err}")
    return serial_ports


def read_weight(ser) -> int:
    try:
        command: bytes = b"\x02AB03\x03"
        ser.write(command)
        response: bytes = ser.read_until(expected=b"\x03")
        if not response:
            return 0
        if response[0] == 0x02 and response[-1] == 0x03:
            sign_char = chr(response[3])
            digits_str = response[4:10].decode("ascii")
            decimal_pos = int(chr(response[10]))
            weight_value = int(digits_str)
            if decimal_pos > 0:
                weight_value = weight_value / (10 ** decimal_pos)
            if sign_char == "-":
                weight_value = -weight_value
            return int(weight_value)
        return 0
    except Exception as err:
        log(message=f"[read_weight] {err}")
    return 0


# ---------- Settings file helpers ----------

def get_camera_url(file_path: str) -> str:
    try:
        if not os.path.exists(file_path):
            cipher.write(file_path=file_path, data=[default_cam_url])
            return default_cam_url
        data = cipher.read_bin_file(file_path=file_path)[0]
        return data
    except Exception:
        return default_cam_url


def get_station_name(file_path: str) -> str:
    try:
        if not os.path.isfile(file_path):
            cipher.write(file_path=file_path, data=["---"])
            return "---"
        return cipher.read_bin_file(file_path)[0]
    except Exception:
        return "---"


def get_is_line(file_path: str) -> bool:
    try:
        if not os.path.isfile(file_path):
            cipher.write(file_path=file_path, data=["1"])
            return True
        return int(cipher.read_bin_file(file_path)[0]) == 1
    except Exception:
        return True


def get_half(file_path: str) -> bool:
    try:
        if not os.path.isfile(file_path):
            cipher.write(file_path=file_path, data=["0"])
            return False
        return int(cipher.read_bin_file(file_path)[0]) == 1
    except Exception:
        return False


def get_username(file_path: str = "settings/username.bin") -> str:
    try:
        if not os.path.isfile(file_path):
            cipher.write(file_path=file_path, data=[default_username])
            return default_username
        return str(cipher.read_bin_file(file_path)[0])
    except Exception:
        return default_username


def get_password(file_path: str = "settings/password.bin") -> str:
    try:
        if not os.path.isfile(file_path):
            cipher.write(file_path=file_path, data=[default_password])
            return default_password
        return str(cipher.read_bin_file(file_path)[0])
    except Exception:
        return default_password


def get_auto(file_path: str) -> bool:
    try:
        if not os.path.isfile(file_path):
            cipher.write(file_path=file_path, data=["0"])
            return False
        return int(cipher.read_bin_file(file_path)[0]) == 1
    except Exception:
        return False


def get_side(file_path: str) -> int:
    try:
        if "top" in file_path:
            default = top_offset
        elif "left" in file_path:
            default = left_offset
        elif "right" in file_path:
            default = right_offset
        else:
            default = bottom_offset
        if not os.path.isfile(file_path):
            cipher.write(file_path=file_path, data=[str(default)])
            return default
        return int(cipher.read_bin_file(file_path)[0])
    except Exception:
        return 6


def get_max_frame_count(file_path: str) -> int:
    try:
        if not os.path.isfile(file_path):
            cipher.write(file_path=file_path, data=[str(default_frame_count)])
            return default_frame_count
        val = int(cipher.read_bin_file(file_path)[0])
        if min_frame_count <= val <= max_frame_count:
            return val
        return default_frame_count
    except Exception:
        return default_frame_count


def get_distance(file_path: str) -> int:
    try:
        if not os.path.isfile(file_path):
            cipher.write(file_path=file_path, data=[str(default_distance)])
            return default_distance
        val = int(cipher.read_bin_file(file_path)[0])
        if min_distance <= val <= max_distance:
            return val
        return default_distance
    except Exception:
        return default_distance


# ---------- Luhn ----------

def calculate_luhn_check_digit(code7: str) -> str:
    digits = [int(c) for c in code7]
    checksum = 0
    for i in range(7):
        digit = digits[i]
        if i % 2 == 0:
            digit *= 2
            if digit > 9:
                digit -= 9
        checksum += digit
    return str((10 - (checksum % 10)) % 10)


def fix_luhn_code(code: str) -> str:
    if len(code) != 8:
        return code
    if identifier not in code:
        code7 = code[:7]
        return code7 + calculate_luhn_check_digit(code7)
    indices = [i for i, c in enumerate(code) if c == identifier]
    if len(indices) > 2:
        return code
    import itertools
    for repl in itertools.product('0123456789', repeat=len(indices)):
        candidate = list(code)
        for idx, val in zip(indices, repl):
            candidate[idx] = val
        if candidate[0] in {'0', '1'}:
            continue
        candidate7 = ''.join(candidate[:7])
        correct_check = calculate_luhn_check_digit(candidate7)
        full_code = candidate7 + correct_check
        if ''.join(candidate) == full_code:
            return full_code
    return code


def check_luhn_code(code: str) -> bool:
    if len(code) != 8 or not code.isdigit():
        return False
    return code[-1] == calculate_luhn_check_digit(code[:7])


# ---------- IoU ----------

def bbox_iou(box1, box2) -> float:
    x1_min, y1_min, x1_max, y1_max = box1
    x2_min, y2_min, x2_max, y2_max = box2
    inter_x_min = max(x1_min, x2_min)
    inter_y_min = max(y1_min, y2_min)
    inter_x_max = min(x1_max, x2_max)
    inter_y_max = min(y1_max, y2_max)
    inter_area = max(0, inter_x_max - inter_x_min) * max(0, inter_y_max - inter_y_min)
    box1_area = (x1_max - x1_min) * (y1_max - y1_min)
    box2_area = (x2_max - x2_min) * (y2_max - y2_min)
    union_area = box1_area + box2_area - inter_area
    return inter_area / union_area if union_area != 0 else 0.0


def filter_overlap(coords: list[list], iou_thresh: float = 0.35) -> list[list]:
    filtered: list = []
    coords = sorted(coords, key=lambda x: (x[1][0], -x[2]))
    for current in coords:
        overlap_found = False
        for kept in filtered:
            if bbox_iou(current[1], kept[1]) > iou_thresh:
                overlap_found = True
                break
        if not overlap_found:
            filtered.append(current)
    return filtered


# ---------- GPU ----------

def supports_half() -> bool:
    try:
        import torch as _torch
        if not _torch.cuda.is_available():
            return False
        major, minor = _torch.cuda.get_device_capability()
        # Blackwell (sm_100, major=10+) — half precision muammo chiqaradi
        if major >= 10:
            return False
        if major < 7:
            return False
        dev = _torch.device("cuda:0")
        x = _torch.randn(1, 3, 64, 64, device=dev, dtype=_torch.float16)
        m = _torch.nn.Conv2d(3, 8, 3, padding=1).to(dev).half()
        m(x)
        _torch.cuda.synchronize()
        return True
    except Exception:
        return False


def get_gpu_name() -> str:
    try:
        import torch
        if torch.cuda.is_available():
            idx = torch.cuda.current_device()
            return torch.cuda.get_device_name(idx)
    except Exception:
        pass
    try:
        import pynvml
        pynvml.nvmlInit()
        h = pynvml.nvmlDeviceGetHandleByIndex(0)
        name = pynvml.nvmlDeviceGetName(h)
        pynvml.nvmlShutdown()
        return name.decode() if isinstance(name, bytes) else str(name)
    except Exception:
        pass
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            stderr=subprocess.STDOUT, text=True, timeout=3,
        )
        lines = [line.strip() for line in out.splitlines() if line.strip()]
        if lines:
            return lines[0]
    except Exception:
        pass
    try:
        if sys.platform.startswith("win"):
            out = subprocess.check_output(
                ["wmic", "path", "win32_VideoController", "get", "Name"],
                text=True, timeout=3,
            )
            lines = [line.strip() for line in out.splitlines() if line.strip() and "Name" not in line]
            if lines:
                for line in lines:
                    upper = line.upper()
                    if any(v in upper for v in ("NVIDIA", "AMD", "RADEON", "INTEL")):
                        return line
                return lines[0]
    except Exception:
        pass
    return "No GPU (CPU only)"


# ---------- File check ----------

def check_files_exist() -> list[str]:
    return [path for path in files if not os.path.exists(path)]


# ---------- Instance lock ----------

def is_running() -> bool:
    sock = QLocalSocket()
    sock.connectToServer(APP_ID)
    return sock.waitForConnected(100)


def create_lock() -> QLocalServer:
    server = QLocalServer()
    server.removeServer(APP_ID)
    server.listen(APP_ID)
    return server


# ---------- CUDA availability ----------

try:
    import torch as _torch
    cuda_available: bool = _torch.cuda.is_available()
    del _torch
except Exception:
    cuda_available: bool = False
half_available: bool = False
