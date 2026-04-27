"""Data classes used across the UI layer."""
from __future__ import annotations
from dataclasses import dataclass
from core.config import (
    identifier, num_count, default_station_code, default_scale_code,
    default_frame_count, default_distance,
    top_offset, left_offset, right_offset, bottom_offset,
)
from core.database import current_time


@dataclass
class SendingData:
    wagonNumber: str = identifier * num_count
    scaleNumber: int = 0
    stationCode: str = default_station_code
    scaleCode: str = default_scale_code
    createdDate: str = current_time()

    def clear(self):
        self.wagonNumber = identifier * num_count
        self.scaleNumber = 0
        self.createdDate = current_time()


@dataclass
class SavingData:
    top: int = top_offset
    left: int = left_offset
    right: int = right_offset
    bottom: int = bottom_offset
    max_frame: int = default_frame_count
    dist: int = default_distance
    is_line: bool = True
    is_fps: bool = True
    hf: bool = False
