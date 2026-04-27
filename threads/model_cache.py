"""
Shared YOLO model registry + PyTorch CPU thread limiter.

rec_model is loaded ONCE and reused by all camera threads.
det_model stays per-thread because track(persist=True) keeps per-camera tracker state.
"""
from __future__ import annotations
import threading

_lock = threading.Lock()
_rec_model = None
_torch_limited = False


def _limit_torch_threads():
    """
    By default PyTorch uses ALL CPU cores for inference.
    Limiting to 2 threads reduces CPU from ~80% to ~20-25%
    with barely noticeable speed difference for small YOLO models.
    """
    global _torch_limited
    if _torch_limited:
        return
    try:
        import torch
        cpu_count = max(1, (torch.get_num_threads() or 4) // 2)
        threads = min(cpu_count, 2)        # max 2 threads
        torch.set_num_threads(threads)
        torch.set_num_interop_threads(1)
        _torch_limited = True
    except Exception:
        pass


def get_shared_rec_model(device: str, is_half: bool = False):
    """Return (rec_model, lock). Model loaded once, shared between all cameras."""
    global _rec_model
    _limit_torch_threads()
    if _rec_model is None:
        with _lock:
            if _rec_model is None:
                from ultralytics import YOLO
                from core.config import WAGON_ID_MODEL_PATH
                _rec_model = YOLO(WAGON_ID_MODEL_PATH)
                _rec_model.to(device)
                if is_half:
                    try:
                        _rec_model.half()
                    except Exception:
                        pass
    return _rec_model, _lock
