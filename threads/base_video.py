"""
Shared base class for VideoThread and AutoVideoThread.

Consolidates duplicated logic: frame capture (PyAV / OpenCV), pixmap conversion,
frame queue management, crop, and OCR number recognition.

Display architecture:
  - Capture thread fills self.frames at camera FPS
  - Inference thread runs YOLO at ~2-3 FPS → stores DRAW COMMANDS (not pixels)
  - Display loop runs at 10 FPS → takes latest raw frame, draws stored commands on it
  This gives smooth live video with persistent annotations.
"""
from __future__ import annotations
import queue
import threading
import time
from queue import Queue

import av
import cv2
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap

from core.config import (
    WAGON_MODEL_PATH, opencv_decoder, verbose, offset,
    wagonAttachId, wagonNumberAttachId, wagonNumber, BBOX, CONF,
    identifier, num_count, log,
    INFER_CONF, INFER_IMGSZ, DISPLAY_IMGSZ,
)
from utils.helpers import resize_img, apply_clahe_bgr

GRAB_SLEEP: float = 0.066


def to_pixmap(frame: np.ndarray) -> QPixmap:
    h, w = frame.shape[:2]
    if w > DISPLAY_IMGSZ:
        nh = int(h * DISPLAY_IMGSZ / w)
        frame = cv2.resize(frame, (DISPLAY_IMGSZ, nh), interpolation=cv2.INTER_LINEAR)
        h, w = nh, DISPLAY_IMGSZ
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    return QPixmap.fromImage(QImage(rgb.data, w, h, w * 3, QImage.Format.Format_RGB888))


# ---- Draw-command helpers ----

def apply_draw_commands(frame: np.ndarray, commands: list) -> np.ndarray:
    """Replay a list of draw commands onto a raw frame."""
    for cmd in commands:
        try:
            kind = cmd[0]
            if kind == "rect":
                _, pt1, pt2, color, thickness = cmd
                cv2.rectangle(frame, pt1, pt2, color, thickness)
            elif kind == "text":
                _, text, org, scale, color, thickness = cmd
                cv2.putText(frame, text, org, cv2.FONT_HERSHEY_TRIPLEX, scale, color, thickness)
            elif kind == "fill":
                # Semi-transparent filled rectangle
                _, pt1, pt2, color, alpha = cmd
                x1, y1 = pt1
                x2, y2 = pt2
                h, w = frame.shape[:2]
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(w, x2), min(h, y2)
                if x2 > x1 and y2 > y1:
                    roi = frame[y1:y2, x1:x2]
                    overlay = roi.copy()
                    cv2.rectangle(overlay, (0, 0), (roi.shape[1], roi.shape[0]), color, -1)
                    cv2.addWeighted(overlay, alpha, roi, 1 - alpha, 0, dst=roi)
        except Exception:
            pass
    return frame


class BaseVideoThread(QThread):
    """Common functionality shared by manual and auto video threads."""

    image_signal = pyqtSignal(QPixmap)
    error_signal = pyqtSignal(str)
    disconnected_signal = pyqtSignal()
    fps_signal = pyqtSignal(str)

    def __init__(self, cam_url: str, fps_view: bool, is_half: bool,
                 r_conf: float, d_conf: float, crop: int = 0):
        super().__init__()
        import torch
        from utils.helpers import supports_half
        from threads.model_cache import get_shared_rec_model, _limit_torch_threads
        _limit_torch_threads()

        _cuda = torch.cuda.is_available()
        _half_ok = supports_half() if _cuda else False

        self.device: str = "cuda" if _cuda else "cpu"
        self.crop: int = crop
        self.r_conf: float = r_conf
        self.d_conf: float = d_conf
        self.fps_view: bool = fps_view
        self.is_half: bool = is_half and _half_ok
        self.cam_url: str = cam_url
        self.running: bool = False
        self.lock = threading.Lock()

        # rec_model — shared singleton across all cameras
        self.rec_model, self.rec_lock = get_shared_rec_model(self.device, self.is_half)

        self.frames: Queue[np.ndarray] = Queue(maxsize=2)
        self.latest_frame: np.ndarray | None = None

        self.thread: threading.Thread | None = None

    # ---- Frame queue management ----

    def _push_frame(self, frame: np.ndarray) -> None:
        try:
            self.latest_frame = frame.copy()
            if self.frames.full():
                try:
                    self.frames.get_nowait()
                except queue.Empty:
                    pass
            self.frames.put_nowait(frame)
        except Exception:
            pass

    def _crop_frame(self, frame: np.ndarray) -> np.ndarray:
        if self.crop > 0:
            try:
                f_h, f_w = frame.shape[:2]
                c = int(f_w * self.crop / 100)
                frame = frame[0:f_h, c:f_w - c]
            except Exception:
                pass
        return frame

    def _prepare_frame(self, frame: np.ndarray) -> np.ndarray:
        if not frame.flags["C_CONTIGUOUS"]:
            frame = np.ascontiguousarray(frame)
        return self._crop_frame(frame)

    # ---- Stream capture (PyAV) ----

    def capture_pyav(self) -> None:
        retry_delay = 1.5
        max_delay = 15.0
        while self.running:
            container = None
            try:
                container = av.open(self.cam_url, options={
                    "rtsp_transport": "tcp", "rtsp_flags": "prefer_tcp",
                    "stimeout": "30000000", "fflags": "nobuffer+discardcorrupt",
                    "flags": "low_delay", "reorder_queue_size": "0", "max_delay": "0",
                })
                retry_delay = 1.0
                stream = container.streams.video[0]
                try:
                    cam_fps = float(stream.average_rate or stream.base_rate or 25)
                    if cam_fps <= 0 or cam_fps > 120:
                        cam_fps = 25.0
                except Exception:
                    cam_fps = 25.0
                frame_interval = 1.0 / cam_fps
                last_frame_time = time.time()
                for pkt in container.decode(video=0):
                    if not self.running:
                        break
                    try:
                        frame = pkt.to_ndarray(format="bgr24")
                    except Exception as err:
                        log(message=f"[{self.__class__.__name__}.capture_pyav] decode error: {err}")
                        continue
                    self._push_frame(self._prepare_frame(frame))
                    now = time.time()
                    elapsed = now - last_frame_time
                    sleep_time = frame_interval - elapsed
                    if sleep_time > 0:
                        time.sleep(sleep_time)
                    last_frame_time = time.time()
            except Exception as err:
                log(message=f"[{self.__class__.__name__}.capture_pyav] stream error: {err}")
                try:
                    self.disconnected_signal.emit()
                except Exception:
                    pass
                time.sleep(retry_delay)
                retry_delay = min(max_delay, retry_delay * 2.0)
            finally:
                if container:
                    try:
                        container.close()
                    except Exception:
                        pass
            if self.running:
                time.sleep(0.5)

    # ---- Stream capture (OpenCV) ----

    def capture_opencv(self) -> None:
        retry_delay = 1.5
        max_delay = 15.0
        fail_threshold = 5
        while self.running:
            cap = None
            try:
                cap = cv2.VideoCapture(self.cam_url, cv2.CAP_FFMPEG)
                try:
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 2)
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                    cap.set(cv2.CAP_PROP_FPS, 15)
                except Exception:
                    pass
                if not cap.isOpened():
                    raise RuntimeError("VideoCapture open failed")
                retry_delay = 1.0
                fails = 0
                while self.running:
                    if not cap.grab():
                        fails += 1
                        if fails >= fail_threshold:
                            raise RuntimeError("Too many grab failures")
                        time.sleep(0.01)
                        continue
                    ret, frame = cap.retrieve()
                    if not ret or frame is None:
                        fails += 1
                        if fails >= fail_threshold:
                            raise RuntimeError("Too many retrieve failures")
                        time.sleep(0.01)
                        continue
                    fails = 0
                    self._push_frame(self._prepare_frame(frame))
                    time.sleep(GRAB_SLEEP)
            except Exception as err:
                log(message=f"[{self.__class__.__name__}.capture_opencv] stream error: {err}")
                try:
                    self.disconnected_signal.emit()
                except Exception:
                    pass
                time.sleep(retry_delay)
                retry_delay = min(max_delay, retry_delay * 2.0)
            finally:
                if cap:
                    try:
                        cap.release()
                    except Exception:
                        pass

    # ---- OCR: recognise wagon number digits in a cropped frame ----

    def recognise_numbers(self, frame: np.ndarray) -> tuple[str, np.ndarray]:
        coords: list = []
        try:
            frame_h, frame_w = frame.shape[:2]
            with self.rec_lock:
                results = self.rec_model(
                    source=frame, verbose=verbose, conf=INFER_CONF,
                    half=self.is_half, imgsz=INFER_IMGSZ,
                )
            for result in results:
                for det in result.boxes:
                    bbox = det.xyxy[0].cpu().numpy().astype(int)
                    x_min, y_min, x_max, y_max = bbox
                    cls = int(det.cls[0].item())
                    conf = float(det.conf[0].item())
                    if (x_min >= offset and x_max <= frame_w - offset
                            and y_min >= offset and y_max <= frame_h - offset):
                        coords.append([cls, [x_min, y_min, x_max, y_max], conf])
            if coords:
                coords.sort(key=lambda x: -x[2])
                if len(coords) > 8:
                    coords = coords[:8]
                coords.sort(key=lambda x: x[1][0])
                num = ""
                for cls, box, cnf in coords:
                    if cnf >= self.r_conf:
                        clr = (0, 255, 0)
                        num += str(cls)
                    elif cnf >= 0.60:
                        clr = (255, 0, 255)
                        num += str(cls)
                    else:
                        clr = (0, 0, 255)
                        num += identifier
                    x_min, y_min, x_max, y_max = box
                    cv2.rectangle(frame, (x_min, y_min), (x_max, y_max), clr, 1)
                    cv2.putText(frame, f"{cls}:{cnf:.2f}", (x_min, y_min - 10),
                                cv2.FONT_HERSHEY_TRIPLEX, 0.6, clr, 1)
                if len(num) >= 5:
                    if len(num) < 8:
                        num += (8 - len(num)) * identifier
                    return num, frame
            return identifier * num_count, frame
        except Exception as err:
            log(message=f"[{self.__class__.__name__}.recognise_numbers] {err}")
            return identifier * num_count, frame

    # ---- Main display + inference loop ----

    def _start_capture_and_infer(self):
        """
        GPU tez (RTX 5090 ~15ms) — bitta loop:
        frame o'qi → detect → annotate → ko'rsat. Lag = 0.
        """
        self.running = True
        target = self.capture_opencv if opencv_decoder else self.capture_pyav
        self.thread = threading.Thread(target=target, daemon=True)
        self.thread.start()
        self._inference_loop()

    def _inference_loop(self):
        """Override in subclass for custom inference behaviour."""
        raise NotImplementedError

    def stop(self):
        self.running = False
        if not self.wait(2000):
            self.terminate()
