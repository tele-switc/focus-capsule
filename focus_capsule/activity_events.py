"""按天分文件的前台区间事件存储（ActivityWatch 式 JSONL）。

每次前台切换写一条 {process, title, start_iso, end_iso} 到
``activity_events_YYYY-MM-DD.jsonl``（与 DataStore 同一用户数据目录）。
只保留最近 30 天；所有写入失败一律静默降级，不影响主流程。

新代码统一使用本地时区（``datetime.now().astimezone()``），不再硬编码 CST。
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable

# 空闲超过该秒数视为 AFK（与 focus_guard.idle_seconds() 的判定阈值一致）
AFK_THRESHOLD_SECONDS = 180
# 事件文件保留天数
RETENTION_DAYS = 30
# AFK 区间在事件里的伪进程名
AFK_PROCESS = "__afk__"

FILE_PREFIX = "activity_events_"
FILE_SUFFIX = ".jsonl"


def local_now() -> datetime:
    """带本地时区偏移的当前时间。"""
    return datetime.now().astimezone()


def parse_event_dt(raw: object) -> datetime | None:
    """解析事件里的 ISO 时间串；naive 时间按本地时区补齐。"""
    if not isinstance(raw, str) or not raw.strip():
        return None
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.astimezone()
    return dt


class ActivityEventLog:
    """前台切换区间事件的 JSONL 读写器。"""

    def __init__(self, base_dir: Path | str):
        self._base = Path(base_dir)
        self._base.mkdir(parents=True, exist_ok=True)

    # ── 写 ────────────────────────────────────────────────────

    def _path_for_day(self, day_iso: str) -> Path:
        return self._base / f"{FILE_PREFIX}{day_iso}{FILE_SUFFIX}"

    def append_event(
        self,
        process: str,
        title: str,
        start: datetime,
        end: datetime,
    ) -> bool:
        """追加一条区间事件；按开始时间所在天落盘。失败静默返回 False。"""
        try:
            process = str(process).strip().casefold()
            if not process:
                return False
            start = start.astimezone()
            end = end.astimezone()
            if end < start:
                start, end = end, start
            record = {
                "process": process,
                "title": str(title or ""),
                "start_iso": start.isoformat(timespec="seconds"),
                "end_iso": end.isoformat(timespec="seconds"),
            }
            path = self._path_for_day(start.date().isoformat())
            with path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            self.prune()
            return True
        except (OSError, ValueError, TypeError):
            logging.debug("activity event write failed", exc_info=True)
            return False

    def prune(self, keep_days: int = RETENTION_DAYS) -> None:
        """删除超过保留期的事件文件；失败静默。"""
        try:
            cutoff = (local_now() - timedelta(days=keep_days)).date().isoformat()
            for path in self._base.glob(f"{FILE_PREFIX}*{FILE_SUFFIX}"):
                day_str = path.stem[len(FILE_PREFIX):]
                if day_str < cutoff:
                    path.unlink()
        except OSError:
            logging.debug("activity event prune failed", exc_info=True)

    # ── 读 ────────────────────────────────────────────────────

    def _read_file(self, path: Path) -> list[dict]:
        events: list[dict] = []
        if not path.exists():
            return events
        try:
            with path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        raw = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if not isinstance(raw, dict):
                        continue
                    start = parse_event_dt(raw.get("start_iso"))
                    end = parse_event_dt(raw.get("end_iso"))
                    process = str(raw.get("process", "")).strip().casefold()
                    if not process or start is None or end is None:
                        continue
                    events.append(
                        {
                            "process": process,
                            "title": str(raw.get("title", "")),
                            "start": start,
                            "end": end,
                        }
                    )
        except OSError:
            logging.debug("activity event read failed: %s", path, exc_info=True)
        return events

    def read_events(self, day: date) -> list[dict]:
        """读取某天的事件；同时扫描前一日文件以覆盖跨午夜区间。"""
        events = self._read_file(self._path_for_day(day.isoformat()))
        events.extend(
            self._read_file(self._path_for_day((day - timedelta(days=1)).isoformat()))
        )
        return events

    def read_events_range(self, start_day: date, end_day: date) -> list[dict]:
        """读取 [start_day, end_day] 闭区间内的事件文件。"""
        events: list[dict] = []
        day = start_day
        while day <= end_day:
            events.extend(self._read_file(self._path_for_day(day.isoformat())))
            day += timedelta(days=1)
        return events

    @staticmethod
    def clamp_events(
        events: Iterable[dict],
        window_start: datetime,
        window_end: datetime,
    ) -> list[dict]:
        """把事件裁剪到窗口内并按开始时间排序。"""
        clamped: list[dict] = []
        for ev in events:
            s = max(ev["start"], window_start)
            e = min(ev["end"], window_end)
            if (e - s).total_seconds() <= 0:
                continue
            item = dict(ev)
            item["start"] = s
            item["end"] = e
            clamped.append(item)
        clamped.sort(key=lambda item: item["start"])
        return clamped


def merge_adjacent(events: Iterable[dict]) -> list[dict]:
    """合并同进程首尾相接（间隔 ≤2 秒）的事件，减少碎片。"""
    merged: list[dict] = []
    for ev in sorted(events, key=lambda item: (item["process"], item["start"])):
        if (
            merged
            and merged[-1]["process"] == ev["process"]
            and merged[-1]["title"] == ev["title"]
            and (ev["start"] - merged[-1]["end"]).total_seconds() <= 2
        ):
            merged[-1]["end"] = max(merged[-1]["end"], ev["end"])
        else:
            merged.append(dict(ev))
    merged.sort(key=lambda item: item["start"])
    return merged


def compute_afk_segments(
    events: Iterable[dict],
    window_start: datetime,
    window_end: datetime,
    threshold_seconds: int = AFK_THRESHOLD_SECONDS,
) -> list[tuple[datetime, datetime]]:
    """推导 AFK 区间：显式 __afk__ 事件 + 相邻事件间超过阈值的空隙。

    返回按时间排序、互不重叠的 (start, end) 元组列表。
    """
    explicit: list[tuple[datetime, datetime]] = []
    foreground: list[dict] = []
    for ev in events:
        if ev["process"] == AFK_PROCESS:
            explicit.append((ev["start"], ev["end"]))
        else:
            foreground.append(ev)

    segments = list(explicit)
    cursor = window_start
    for ev in sorted(foreground, key=lambda item: item["start"]):
        if (ev["start"] - cursor).total_seconds() >= threshold_seconds:
            segments.append((cursor, ev["start"]))
        cursor = max(cursor, ev["end"])
    if (window_end - cursor).total_seconds() >= threshold_seconds:
        segments.append((cursor, window_end))

    # 合并重叠片段，保证互不嵌套
    merged: list[list[datetime]] = []
    for s, e in sorted(segments):
        if merged and s <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    return [(s, e) for s, e in merged]
