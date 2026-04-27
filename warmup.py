from __future__ import annotations

import numpy as np
import torch
from ultralytics import YOLO

from core.config import WAGON_MODEL_PATH, WAGON_ID_MODEL_PATH

WAGON_MODEL_IMGSZ: int = 1024
WAGON_ID_MODEL_IMGSZ: int = 800

_temp_frame: np.ndarray = np.zeros((1080, 1920, 3), dtype=np.uint8)

YOLO(model=WAGON_MODEL_PATH, task="detect", verbose=False).track(
    source=[_temp_frame for _ in range(4)],
    tracker="bytetrack.yaml", half=True, stream=False,
    device=0 if torch.cuda.is_available() else "cpu",
    persist=True, conf=0.75, imgsz=WAGON_MODEL_IMGSZ, iou=0.3,
)
YOLO(model=WAGON_ID_MODEL_PATH, task="detect", verbose=False).predict(
    source=_temp_frame, conf=0.75, imgsz=WAGON_ID_MODEL_IMGSZ,
)
