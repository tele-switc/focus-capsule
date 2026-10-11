"""Local foreground application usage tracking."""

from __future__ import annotations

import time
from pathlib import Path

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from focus_capsule.data_models import china_today
from focus_capsule.data_store import DataStore


class ActivityTracker(QObject):
    """Accumulate per-app foreground seconds while Focus Capsule is running."""

    usage_updated = pyqtSignal(str)

    def __init__(self, data_store: DataStore, parent: QObject | None = None):
        super().__init__(parent)
        self._store = data_store
        self._process = ""
        self._display_name = ""
        self._date_str = china_today().isoformat()
        self._started = time.monotonic()
        self._timer = QTimer(self)
        self._timer.setInterval(15_000)
        self._timer.timeout.connect(self.flush)
        self._timer.start()

    @staticmethod
    def _trackable(process_name: str) -> bool:
        process = str(process_name).strip().casefold()
        return bool(process and process != "__focus_capsule__")

    def on_foreground_change(
        self,
        process_name: str,
        _window_title: str = "",
        executable_path: str = "",
    ) -> None:
        process = str(process_name).strip().casefold()
        if process == self._process:
            return
        self.flush()
        self._process = process if self._trackable(process) else ""
        self._display_name = (
            Path(executable_path).stem
            if executable_path
            else Path(process).stem
        )
        self._date_str = china_today().isoformat()
        self._started = time.monotonic()

    def flush(self) -> None:
        now = time.monotonic()
        elapsed = max(0, int(now - self._started))
        current_date = china_today().isoformat()
        if self._process and elapsed:
            self._store.add_app_usage(
                self._date_str,
                self._process,
                elapsed,
                self._display_name,
            )
            self.usage_updated.emit(self._process)
            self._started += elapsed
        else:
            self._started = now

        if current_date != self._date_str:
            self._date_str = current_date
            self._started = now

    def stop(self) -> None:
        self._timer.stop()
        self.flush()
