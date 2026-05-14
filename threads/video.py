from __future__ import annotations
import queue
import time
import numpy as np
from PyQt6.QtCore import pyqtSignal

from core.config import (
    WAGON_MODEL_PATH, verbose, offset,
    wagonAttachId, wagonNumberAttachId, wagonNumber, BBOX, CONF,
    identifier, num_count, TOP, BOTTOM, LEFT, RIGHT, log,
    top_offset, bottom_offset, left_offset, right_offset,
    INFER_CONF, INFER_IMGSZ,
)
from threads.base_video import BaseVideoThread
from utils.helpers import resize_img, apply_clahe_bgr
import cv2


class VideoThread(BaseVideoThread):
    data_signal = pyqtSignal(dict)
    dual_signal = pyqtSignal(list)
    inner_signal = pyqtSignal(bool)

    def __init__(self, cam_url: str, lined: bool, fps: bool, is_half: bool,
                 dist: int, r_conf: float, d_conf: float, side: dict[str, int], crop: int = 0):
        super().__init__(cam_url=cam_url, fps_view=fps, is_half=is_half,
                         r_conf=r_conf, d_conf=d_conf, crop=crop)
        from ultralytics import YOLO

        self.cnt: int = 1
        self.lined: bool = lined
        self.threshold: int = dist
        self.max_count: int = 3

        # det_model — per camera (tracker state is per instance)
        self.det_model = YOLO(WAGON_MODEL_PATH)
        self.det_model.to(self.device)
        if self.is_half:
            self.det_model.half()

        self.saved_track_ids: dict = {}
        self.side: dict[str, int] = side
        self.track_ids: dict[int, list[list[int]]] = {}

    def run(self):
        self._start_capture_and_infer()

    def _inference_loop(self):
        """frame o'qi → detect → annotate → emit. Lag = 0."""
        from threads.base_video import apply_draw_commands, to_pixmap
        start_time = time.time()
        self._best_data: dict = {}
        while self.running:
            try:
                frame = self.frames.get(timeout=0.1)
            except queue.Empty:
                continue
            try:
                cmds, data = self._detect(img=frame)
                annotated = apply_draw_commands(frame.copy(), cmds) if cmds else frame
                self.image_signal.emit(to_pixmap(annotated))
                if self.fps_view:
                    now = time.time()
                    self.fps_signal.emit(f"FPS: {1 / max(0.01, now - start_time):.1f}")
                    start_time = now

                wagon_present = BBOX in data
                current_wn = data.get(wagonNumber, identifier * num_count)
                best_wn = self._best_data.get(wagonNumber, identifier * num_count)

                # Vagon kadrda turgan paytda eng yaxshi (kamroq x) raqamni saqlaymiz
                if wagon_present and current_wn.count(identifier) < best_wn.count(identifier):
                    self._best_data = data

                # Emisiya uchun: vagon bor → eng yaxshi ma'lumot; yo'q → joriy (clear)
                emit_data = self._best_data if (wagon_present and self._best_data) else data
                is_valid = (emit_data.get(wagonNumber, identifier * num_count).count(identifier) <= 3
                            or emit_data.get("candidates"))

                self.cnt += 1
                if self.cnt % self.max_count == 0:
                    self.cnt = 1
                    if is_valid:
                        self._had_detection = True
                        self.data_signal.emit(emit_data)
                    elif getattr(self, "_had_detection", False) and not wagon_present:
                        # Vagon kadrdan chiqdi — displayni tozalaymiz
                        self._had_detection = False
                        self._best_data = {}
                        self.data_signal.emit(data)
            except Exception as err:
                log(message=f"[VideoThread._inference_loop] {err}")

    def _detect(self, img: np.ndarray) -> tuple[list, dict]:
        """Run detection. Returns (draw_commands, data_dict)."""
        cmds: list = []
        coords: list[dict] = []
        inners: list[bool] = []
        try:
            top = self.side.get(TOP, top_offset)
            bottom = self.side.get(BOTTOM, bottom_offset)
            left = self.side.get(LEFT, left_offset)
            right = self.side.get(RIGHT, right_offset)
            img_h, img_w = img.shape[:2]
            top = int(img_h * top / 100)
            bottom = img_h - int(img_h * bottom / 100)
            left = int(img_w * left / 100)
            right = img_w - int(img_w * right / 100)
            overlay = img.copy()
            with self.lock:
                results = self.det_model(source=img, verbose=verbose, half=self.is_half,
                                         conf=INFER_CONF, imgsz=INFER_IMGSZ)
                for result in results:
                    for det in result.boxes:
                        bbox = det.xyxy[0].cpu().numpy().astype(int)
                        x_min, y_min, x_max, y_max = bbox
                        conf = float(det.conf[0].item())
                        cls = int(det.cls[0].item())
                        if cls == 1:
                            out = x_min <= left or x_max >= right or y_min < top or y_max > bottom
                            inners.append(not out)
                            color = (0, 0, 255) if out else (0, 255, 0)
                            cmds.append(("rect", (x_min, y_min), (x_max, y_max), color, 4))
                            continue
                        visible_w = min(img_w, x_max) - max(0, x_min)
                        if (conf >= self.d_conf and y_min > 5 and y_max < img_h - 5
                                and visible_w > 50):
                            x1 = max(0, x_min - offset - 4)
                            y1 = max(0, y_min - offset - 4)
                            x2 = min(img_w, x_max + offset + 4)
                            y2 = min(img_h, y_max + offset + 4)
                            crop = np.ascontiguousarray(overlay[y1:y2, x1:x2])
                            crop = resize_img(crop, w=800)
                            nums, crop = self.recognise_numbers(frame=apply_clahe_bgr(crop))
                            coords.append({wagonAttachId: img, wagonNumberAttachId: crop,
                                           wagonNumber: nums, BBOX: [x_min, y_min, x_max, y_max], CONF: conf})
                            cmds.append(("fill", (x_min, y_min), (x_max, y_max), (255, 0, 0), 0.5))
                            label = f"num:{nums} c:{conf:.2f}"
                            label_w = int(len(label) * 11)
                            text_x = max(0, min(x_min, img_w - label_w))
                            cmds.append(("text", label,
                                         (text_x, max(20, y_min - 10)), 0.8, (255, 0, 0), 2))
                self.inner_signal.emit(True in inners)
                if coords:
                    coords.sort(key=lambda x: (x[wagonNumber].count(identifier), -x[CONF],
                                               x[BBOX][0], x[BBOX][1]))
                    full_valid = [c for c in coords
                                  if c[wagonNumber].count(identifier) == 0
                                  and len(c[wagonNumber]) == num_count]
                    best = coords[0]

                    if len(full_valid) >= 2:
                        best = dict(best)
                        best["candidates"] = full_valid

                    return cmds, best
            return cmds, {wagonAttachId: img}
        except Exception as err:
            log(message=f"[VideoThread._detect] {err}")
            return cmds, {wagonAttachId: img}
