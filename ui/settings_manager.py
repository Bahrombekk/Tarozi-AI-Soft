"""Encrypted settings persistence."""
from __future__ import annotations
import os
from core.config import cipher, default_settings, log


class SettingsManager:

    def __init__(self, filename: str):
        self.file: str = filename
        self.data: dict = self.load()

    def load(self) -> dict:
        try:
            if os.path.exists(self.file):
                return cipher.read(self.file)
            else:
                self.data = default_settings
                self.save()
                return self.data
        except Exception as err:
            log(message=f"[SettingsManager.load] ERROR {err}")
            return {}

    def save(self) -> None:
        try:
            cipher.write(self.file, self.data)
        except Exception as err:
            log(message=f"[SettingsManager.save] {err}")

    def patch(self, key: str, value: int | str | float):
        try:
            self.data[key] = value
            self.save()
        except Exception as err:
            log(message=f"[SettingsManager.patch] {err}")
