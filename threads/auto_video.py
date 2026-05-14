from __future__ import annotations
import queue
import numpy as np
import cv2
from PyQt6.QtCore import pyqtSignal

from core.config import (
    WAGON_MODEL_PATH, verbose, offset,
    wagonAttachId, wagonNumberAttachId, wagonNumber, BBOX, CONF, t_id,
    identifier, num_count, min_count, TOP, BOTTOM, LEFT, RIGHT, log,
    top_offset, bottom_offset, left_offset, right_offset,
    default_rec_conf, default_det_conf, default_frame_count, default_distance, default_cam_url,
    R_CONF, D_CONF, FPS, HALF, CAM_URL, DISTANCE, MAX_FRAME, CROP_SIDE,
    INFER_CONF, INFER_IMGSZ,
)
from threads.base_video import BaseVideoThread
from utils.helpers import resize_img, apply_clahe_bgr


class AutoVideoThread(BaseVideoThread):
    data_signal = pyqtSignal(dict)

    def __init__(self, data: dict):
        cam_url = data.get(CAM_URL, default_cam_url)
        fps_view = data.get(FPS, True)
        is_half = data.get(HALF, False)
        r_conf = data.get(R_CONF, default_rec_conf)
        d_conf = data.get(D_CONF, default_det_conf)
        crop = data.get(CROP_SIDE, 0)

        super().__init__(cam_url=cam_url, fps_view=fps_view, is_half=is_half,
                         r_conf=r_conf, d_conf=d_conf, crop=crop)
        from ultralytics import YOLO

        self.last_img_width: int | None = None
        self.is_timeout: bool = False
        self.sort_path: str = "botsort.yaml"
        self.threshold: int = data.get(DISTANCE, default_distance)
        self.max_count: int = data.get(MAX_FRAME, default_frame_count)

        # det_model — per camera (botsort tracker state is per instance)
        self.det_model = YOLO(WAGON_MODEL_PATH)
        self.det_model.to(self.device)
        if self.is_half:
            try:
                self.det_model.half()
            except Exception:
                pass

        self.saved_track_ids: set[int] = set()
        self.track_ids: dict[int, list[list[int]]] = {}
        self.top: int = data.get(TOP, top_offset)
        self.bottom: int = data.get(BOTTOM, bottom_offset)
        self.left: int = data.get(LEFT, left_offset)
        self.right: int = data.get(RIGHT, right_offset)

    def run(self):
        self._start_capture_and_infer()

    def _inference_loop(self):
        """frame o'qi → detect → annotate → emit. Lag = 0."""
        from threads.base_video import apply_draw_commands, to_pixmap
        import time as _time
        start_time = _time.time()
        while self.running:
            try:
                frame = self.frames.get(timeout=0.1)
            except queue.Empty:
                continue
            try:
                cmds, data_out = self._detect(img=frame)
                annotated = apply_draw_commands(frame.copy(), cmds) if cmds else frame
                self.image_signal.emit(to_pixmap(annotated))
                if self.fps_view:
                    now = _time.time()
                    self.fps_signal.emit(f"FPS: {1 / max(0.01, now - start_time):.1f}")
                    start_time = now
                if data_out is not None:
                    self.data_signal.emit(data_out)
            except Exception as err:
                log(message=f"[AutoVideoThread._inference_loop] {err}")

    def check_stopped(self, track_id: int) -> tuple[int, int, bool]:
        """Check if a tracked wagon has stopped (barely moved over max_count frames)."""
        frames = self.track_ids[track_id]
        count = len(frames)
        if count == 0:
            return 0, 0, False
        dx = abs(frames[0][0] - frames[-1][0])
        if count >= self.max_count:
            if dx <= self.threshold:
                return count, dx, True
        return count, dx, False

    def _detect(self, img: np.ndarray) -> tuple[list, dict | None]:
        """Run detection + tracking. Returns (draw_commands, data_to_emit_or_None)."""
        cmds: list = []
        coords: list[dict] = []
        data_out: dict | None = None
        try:
            img_h, img_w = img.shape[:2]
            if self.last_img_width != img_w:
                self.last_img_width = img_w
            top = int(img_h * self.top / 100)
            bottom = img_h - int(img_h * self.bottom / 100)
            left = int(img_w * self.left / 100)
            right = img_w - int(img_w * self.right / 100)
            overlay = img.copy()
            detected: list = []
            with self.lock:
                results = self.det_model.track(
                    source=img, verbose=verbose, half=self.is_half,
                    persist=True, tracker=self.sort_path, conf=INFER_CONF, imgsz=INFER_IMGSZ,
                )
                for result in results:
                    for det in result.boxes:
                        bbox = det.xyxy[0].cpu().numpy().astype(int)
                        conf = float(det.conf[0].item())
                        cls = int(det.cls[0].item())
                        track_id = int(det.id[0].item()) if det.id is not None else None
                        detected.append([cls, conf, track_id, bbox])

                if detected:
                    detected.sort(key=lambda x: x[0])

                for cls, conf, track_id, bbox in detected:
                    x_min, y_min, x_max, y_max = bbox
                    if conf < self.d_conf:
                        continue
                    if cls == 1:
                        if x_min < left or x_max > right or y_min < top or y_max > bottom:
                            cmds.append(("rect", (x_min, y_min), (x_max, y_max), (0, 0, 255), 2))
                            cmds.append(("text", f"id:{track_id}", (x_min, y_min - 10), 0.8, (255, 0, 0), 2))
                            continue
                        if track_id is None:
                            continue

                        # Skip wagons that were already sent
                        if track_id in self.saved_track_ids:
                            cmds.append(("rect", (x_min, y_min), (x_max, y_max), (0, 200, 200), 2))
                            cmds.append(("text", f"SENT id:{track_id}", (x_min, y_min - 10), 0.8, (0, 200, 200), 2))
                            continue

                        if track_id not in self.track_ids:
                            self.track_ids[track_id] = []
                        self.track_ids[track_id].append([x_min, y_min, x_max, y_max])
                        if len(self.track_ids[track_id]) > self.max_count + 2:
                            self.track_ids[track_id].pop(0)
                        dst = 0
                        if not self.is_timeout:
                            ln, dst, ans = self.check_stopped(track_id=track_id)
                            # Progress bar
                            pw = int(abs(x_max - x_min) * (ln / self.max_count))
                            cmds.append(("fill", (x_min, y_min), (x_min + pw, y_max), (255, 0, 0), 0.5))
                            if dst > self.threshold:
                                self.track_ids[track_id].clear()
                            elif ans:
                                if coords:
                                    coords.sort(key=lambda x: (x[wagonNumber].count(identifier),
                                                               -x[CONF], x[BBOX][0], x[BBOX][1]))
                                    coords[0][t_id] = track_id
                                    data_out = coords[0]
                                else:
                                    data_out = {wagonAttachId: img}
                                self.saved_track_ids.add(track_id)
                                del self.track_ids[track_id]
                        if len(self.track_ids) > 10:
                            oldest = min(self.track_ids, key=lambda k: len(self.track_ids[k]))
                            del self.track_ids[oldest]
                        cmds.append(("rect", (x_min, y_min), (x_max, y_max), (0, 255, 0), 2))
                        cmds.append(("text", f"PR({dst}/{self.threshold}) id:{track_id}",
                                     (x_min, y_min - 10), 0.8, (255, 0, 0), 2))
                        continue

                    if (x_min > 5 and x_max < img_w - 5 and y_min > 5 and y_max < img_h - 5
                            and conf >= self.d_conf and x_max - x_min > 50 and cls == 0):
                        crop_f = np.ascontiguousarray(
                            overlay[max(0, y_min - offset - 4):min(img_h, y_max + offset + 4),
                                    max(0, x_min - offset - 4):min(img_w, x_max + offset + 4)]
                        )
                        crop_f = resize_img(crop_f, w=800)
                        nums, crop_f = self.recognise_numbers(frame=apply_clahe_bgr(crop_f))
                        coords.append({wagonAttachId: img, wagonNumberAttachId: crop_f,
                                        wagonNumber: nums, BBOX: [x_min, y_min, x_max, y_max], CONF: conf})
                        cmds.append(("fill", (x_min, y_min), (x_max, y_max), (255, 0, 0), 0.5))
                        cmds.append(("text", f"id:{track_id} num:{nums} c:{conf:.2f}",
                                     (x_min, y_min - 10), 0.8, (255, 0, 0), 2))

                # Clean saved_track_ids: remove IDs no longer visible
                current_ids = {d[2] for d in detected if d[2] is not None}
                self.saved_track_ids &= current_ids
        except Exception as err:
            log(message=f"[AutoVideoThread._detect] {err}")
        return cmds, data_out
