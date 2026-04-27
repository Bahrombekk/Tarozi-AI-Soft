import os
import datetime
import logging
from core.cipher import Cipher

cipher: Cipher = Cipher()
LOG_PATH: str = "log/logs.bin"
APP_ID: str = "TaroziAISoft_12345"

# ---------- Python logging ----------
_logger = logging.getLogger("tarozi")
if not _logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s — %(asctime)s"))
    _logger.addHandler(_handler)
    _logger.setLevel(logging.DEBUG)


def log(message: str, level: str = "ERROR") -> None:
    if not os.path.exists("log"):
        os.mkdir("log")
    # Standard logging
    _log_level = getattr(logging, level.upper(), logging.ERROR)
    _logger.log(_log_level, message)
    # Encrypted log file
    try:
        cipher.add_bin_data(file_path=LOG_PATH, data=f"[{level}] {message} >>> {datetime.datetime.now()}\n")
    except Exception as exc:
        _logger.warning("Failed to write encrypted log: %s", exc)


# Network
base_url: str = os.environ.get("TAROZI_BASE_DOMAIN", "ai-project.das-uty.uz")
post_url: str = os.environ.get("TAROZI_UPLOAD_URL", f"https://{base_url}/api/wagon-scale-values")
get_token_url: str = os.environ.get("TAROZI_LOGIN_URL", f"https://{base_url}/api/auth/device-login")

# ---------- Load overrides from config.json ----------
import json as _json

_config_json: dict = {}
_config_json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "settings", "config.json")
if os.path.isfile(_config_json_path):
    try:
        with open(_config_json_path, "r", encoding="utf-8") as _f:
            _config_json = _json.load(_f)
    except Exception:
        pass

# Serial / Scale
BOUND_RATE: int = _config_json.get("BOUND_RATE", 9600)
timeout: int = _config_json.get("timeout", 30)
scale_sleep_ms: int = _config_json.get("sleeppy", 1000)
offset: int = _config_json.get("offset", 6)
min_send_kg: int = _config_json.get("min_send_kg", 20_000)
verbose: bool = False
opencv_decoder: bool = False

# Inference constants (centralised)
INFER_CONF: float = 0.55
INFER_IMGSZ: int = 1280
DISPLAY_IMGSZ: int = 960

# Timing
default_send_time: int = 60
min_time: int = 15
max_time: int = 150

# Frame / Distance
default_frame_count: int = 128
min_frame_count: int = 64
max_frame_count: int = 1024
default_distance: int = 6
min_distance: int = 3
max_distance: int = 10

# Confidence
default_det_conf: float = 0.7
min_det_conf: float = 0.6
max_det_conf: float = 0.8
default_rec_conf: float = 0.75
min_rec_conf: float = 0.7
max_rec_conf: float = 0.85

# Crop / Side offsets
crop_left: int = 0
crop_right: int = 0
top_offset: int = 40
bottom_offset: int = 1
left_offset: int = 2
right_offset: int = 2
min_side: int = 1
max_side: int = 50

# Lines
default_left_line: int = 35
min_left_line: int = 5
max_left_line: int = 50
default_right_line: int = 65
min_right_line: int = 50
max_right_line: int = 95
line_color: tuple = (0, 255, 100)

# Image aspect
width_scale: int = 16
height_scale: int = 9
max_height_item: int = 40

# Wagon ID
identifier: str = "x"
num_count: int = 8
min_count: int = 5
table_name: str = "wagon_data"

# Field names
wagonType: str = "wagonType"
normTon: str = "normTon"
extraTon: str = "extraTon"
wagonAttachId: str = "wagonImage1Base64"
wagonAttachId2: str = "wagonImage2Base64"
wagonNumberAttachId: str = "wagonNumberImageBase64"
wagonNumber: str = "wagonNumber"
scaleNumber: str = "scaleNumber"
stationCode: str = "stationCode"
createdDate: str = "createdDate"
scaleCode: str = "scaleCode"
default_cam_url: str = "rtsp://admin:password@192.168.1.64:554"
default_station_code: str = "111111"
default_scale_code: str = "111111"
default_username: str = os.environ.get("TAROZI_USERNAME", "wagon")
default_password: str = os.environ.get("TAROZI_PASSWORD", "Test707$Wagon")
static_password: str = os.environ.get("TAROZI_STATIC_PASSWORD", "@1234@4321@")

# File paths
backup_folder: str = "backup"
db_name: str = "settings/wagon_data.sqlite3"
backup_db_name: str = "settings/backup_data.sqlite3"
WAGON_MODEL_PATH: str = "models/wagon_id.pt"
WAGON_ID_MODEL_PATH: str = "models/wagon_id_number.pt"

# DB field keys
ID: str = "id"
sentAt: str = "sentAt"
t_id: str = "track_id"

# Settings keys
LANG = "LANG"; THEME = "THEME"; SCALE_VIEW = "SCALE_VIEW"; BTN_DISABLE = "BTN_DISABLE"; SCALE_DISABLE = "SCALE_DISABLE"
AUTO = "AUTO"; SEND_TIME = "SEND_TIME"; STATION_CODE = "STATION_CODE"; SCALE_CODE = "SCALE_CODE"
USERNAME = "USERNAME"; PASSWORD = "PASSWORD"; BASE_URL = "BASE_URL"; LOGIN_URL = "LOGIN_URL"
UPLOAD_URL = "UPLOAD_URL"; URL_NOT_FOUND = "URL_NOT_FOUND"; MAX_FRAME = "MAX_FRAME"
DISTANCE = "DISTANCE"; HALF = "HALF"; FPS = "FPS"; LINE = "LINE"
D_CONF = "D_CONF"; R_CONF = "R_CONF"; TOP = "TOP"; BOTTOM = "BOTTOM"
LEFT = "LEFT"; LEFT_LINE = "LEFT_LINE"; RIGHT = "RIGHT"; RIGHT_LINE = "RIGHT_LINE"
BBOX = "BBOX"; CONF = "CONF"; CAM_URL = "CAM_URL"; CROP_SIDE = "CROP_SIDE"

# Theme / Lang
DARK = "DARK"; LIGHT = "LIGHT"; UZBEK = "UZBEK"; RUSSIAN = "RUSSIAN"; ENGLISH = "ENGLISH"
window_title: str = "Tarozi AI"
theme_list: list = [DARK, LIGHT]
lang_list: list = [UZBEK, RUSSIAN, ENGLISH]

MONTH_NAMES_UZ: list = [
    "Yanvar", "Fevral", "Mart", "Aprel", "May", "Iyun",
    "Iyul", "Avgust", "Sentabr", "Oktabr", "Noyabr", "Dekabr"
]

default_settings: dict = {
    AUTO: False,
    BASE_URL: f"https://{base_url}",
    LOGIN_URL: get_token_url,
    UPLOAD_URL: post_url,
    D_CONF: default_det_conf, R_CONF: default_rec_conf,
    STATION_CODE: default_station_code, SCALE_CODE: default_scale_code,
    USERNAME: os.environ.get("TAROZI_APP_USERNAME", "tarozi"),
    PASSWORD: os.environ.get("TAROZI_APP_PASSWORD", "Tarozi2025"),
    SEND_TIME: 75, LANG: UZBEK, THEME: LIGHT,
    SCALE_VIEW: False, BTN_DISABLE: True, SCALE_DISABLE: False,
}

files: list = [
    db_name,
    "images/frame.png", "images/frame-light.png",
    "images/no_image.png", "images/train.png",
    "images/gentle.png", "images/clock.png",
    "images/success.png", "images/fail.png",
    "images/Moon.svg", "images/Sun.svg", "images/icon.svg",
    "images/unview_eye.png", "images/view_eye.png",
    "images/view_eye_light.png", "images/unview_eye_light.png",
    "models/wagon_id.pt", "models/wagon_id_number.pt",
]
