"""Local foreground application usage tracking."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta
from pathlib import Path

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from focus_capsule.activity_events import (
    AFK_THRESHOLD_SECONDS,
    ActivityEventLog,
    AFK_PROCESS,
)
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

        # ── 区间事件存储（ActivityWatch 式 JSONL，失败静默降级）──
        try:
            self._events = ActivityEventLog(self._store.base_dir)
        except (OSError, AttributeError):
            logging.debug("activity event log unavailable", exc_info=True)
            self._events = None
        # 当前打开的前台区间：进程 / 窗口标题 / 开始时间（本地时区）
        self._ev_process = ""
        self._ev_title = ""
        self._ev_start: datetime | None = None
        # AFK 状态
        self._afk_start: datetime | None = None

    @staticmethod
    def _trackable(process_name: str) -> bool:
        process = str(process_name).strip().casefold()
        return bool(process and process != "__focus_capsule__")

    # ── 区间事件辅助 ──────────────────────────────────────────

    def _open_new_interval(self, process: str, title: str) -> None:
        """开始记录一个新前台区间。"""
        self._ev_process = process
        self._ev_title = str(title or "")
        self._ev_start = datetime.now().astimezone()

    def _close_open_interval(self, now: datetime | None = None) -> None:
        """把当前打开的前台区间落盘（每次前台切换写一条事件）。"""
        if self._events is None or self._ev_start is None or not self._ev_process:
            self._ev_start = None
            return
        end = now if now is not None else datetime.now().astimezone()
        if (end - self._ev_start).total_seconds() >= 1:
            try:
                self._events.append_event(
                    self._ev_process, self._ev_title, self._ev_start, end
                )
            except Exception:
                logging.debug("activity event append failed", exc_info=True)
        self._ev_start = None

    def _update_afk(self) -> None:
        """用 focus_guard.idle_seconds() 维护 AFK 区间的开/关。"""
        if self._events is None:
            return
        try:
            from focus_capsule.focus_guard import idle_seconds

            idle = int(idle_seconds())
        except Exception:
            return
        now = datetime.now().astimezone()
        if idle >= AFK_THRESHOLD_SECONDS:
            if self._afk_start is None:
                # 进入 AFK：先关闭前台区间，AFK 起点回退到最后一次输入
                self._close_open_interval(now - timedelta(seconds=idle))
                self._afk_start = now - timedelta(seconds=idle)
        elif self._afk_start is not None:
            # 离开 AFK：落盘一段 __afk__ 事件，并重新打开当前前台区间
            try:
                self._events.append_event(
                    AFK_PROCESS, "离开", self._afk_start, now
                )
            except Exception:
                logging.debug("afk event append failed", exc_info=True)
            self._afk_start = None
            if self._process and self._ev_start is None:
                self._open_new_interval(self._process, self._ev_title)

    # ── 事件回调 ──────────────────────────────────────────────

    def on_foreground_change(
        self,
        process_name: str,
        window_title: str = "",
        executable_path: str = "",
    ) -> None:
        process = str(process_name).strip().casefold()
        if process == self._process:
            return
        # 切换前：把上一段区间写入 JSONL
        self._close_open_interval()
        self.flush()
        self._process = process if self._trackable(process) else ""
        self._display_name = (
            Path(executable_path).stem
            if executable_path
            else Path(process).stem
        )
        self._date_str = china_today().isoformat()
        self._started = time.monotonic()
        if self._process and self._afk_start is None:
            self._open_new_interval(self._process, window_title)
        else:
            self._ev_start = None

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
            # 跨天：关闭当前区间，新的一天重新开始记录
            self._close_open_interval()
            self._date_str = current_date
            self._started = now
            if self._process and self._afk_start is None:
                self._open_new_interval(self._process, self._ev_title)

        # AFK 检测跟随 15 秒定时器轮询
        self._update_afk()

    def stop(self) -> None:
        self._timer.stop()
        self._close_open_interval()
        if self._afk_start is not None and self._events is not None:
            try:
                self._events.append_event(
                    AFK_PROCESS, "离开", self._afk_start, datetime.now().astimezone()
                )
            except Exception:
                logging.debug("afk event flush failed", exc_info=True)
            self._afk_start = None
        self.flush()
