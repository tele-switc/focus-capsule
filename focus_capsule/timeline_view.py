"""ActivityWatch 式前台时间线视图（QPainter 自绘）。

- 日视图：每个应用一行，横向色条按起止时间定位，0–24 小时刻度轴。
- 周/月视图：同一组件按天刻度轴渲染。
- 颜色按分类名哈希到固定淡色板（低饱和 + alpha≈0.55），禁止饱和填充。
- AFK 区间（空闲超过 180 秒）用灰色底纹标出，主动/被动时间一眼可分。
- hover 显示 tooltip（应用名、窗口标题、时间段、时长），点击回调事件详情。
"""

from __future__ import annotations

import hashlib
from datetime import date, datetime, timedelta

from PyQt6.QtCore import QPoint, QRectF, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import QSizePolicy, QToolTip, QWidget

from focus_capsule import theme as T
from focus_capsule.activity_events import (
    AFK_PROCESS,
    AFK_THRESHOLD_SECONDS,
    compute_afk_segments,
)

# 淡色板：低饱和暖色系，绘制时统一压到 alpha≈0.55
CATEGORY_PALETTE = (
    "#A08458",  # 金
    "#7A9968",  # 绿
    "#B47A42",  # 琥珀
    "#8C9FB5",  # 蓝灰
    "#B58CA0",  # 藕粉
    "#9A8CB5",  # 灰紫
    "#6FA6A0",  # 鸭青
    "#C2A878",  # 麦色
    "#99866E",  # 咖灰
    "#88A888",  # 苔绿
)

BAR_ALPHA = 0.55
ROW_HEIGHT = 26
LABEL_WIDTH = 148
AXIS_HEIGHT = 26
MAX_ROWS = 14  # 超出部分合并为「其余应用」


def category_color(category: str, alpha: float = BAR_ALPHA) -> QColor:
    """分类名哈希到固定色板；淡色、低透明。"""
    digest = hashlib.md5(str(category).encode("utf-8")).hexdigest()
    base = QColor(CATEGORY_PALETTE[int(digest, 16) % len(CATEGORY_PALETTE)])
    base.setAlphaF(alpha)
    return base


def format_seconds(seconds: float) -> str:
    """把秒数格式化为中文习惯的 时长文本。"""
    total = int(max(0, round(seconds)))
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}小时{m:02d}分"
    if m:
        return f"{m}分{s:02d}秒" if total < 3600 else f"{m}分"
    return f"{s}秒"


def _hhmm(dt: datetime) -> str:
    return dt.strftime("%H:%M")


class TimelineView(QWidget):
    """按小时时间线：每应用一行横向色条 + AFK 灰色底纹 + hover tooltip。"""

    # 点击某个区间时回调事件 dict（process/title/start/end）
    event_clicked = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._events: list[dict] = []
        self._afk: list[tuple[datetime, datetime]] = []
        self._window_start: datetime | None = None
        self._window_end: datetime | None = None
        self._mode = "day"  # day=小时轴 / range=按天轴
        self._hover_index = -1
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.setMinimumHeight(AXIS_HEIGHT + ROW_HEIGHT * 3 + 16)

    # ── 数据入口 ──────────────────────────────────────────────

    def set_day(self, day: date, events: list[dict]) -> None:
        """日视图：0–24 小时轴，AFK 由显式事件 + 大空隙共同推导。"""
        start = datetime.combine(day, datetime.min.time()).astimezone()
        self._window_start = start
        self._window_end = start + timedelta(days=1)
        self._mode = "day"
        self._set_events(events)

    def set_range(self, start: datetime, end: datetime, events: list[dict]) -> None:
        """周/月视图：按天刻度轴渲染同一批事件。"""
        self._window_start = start
        self._window_end = end
        self._mode = "range"
        self._set_events(events)

    def _set_events(self, events: list[dict]) -> None:
        self._events = [
            ev for ev in events
            if ev.get("process") != AFK_PROCESS
            and (ev["end"] - ev["start"]).total_seconds() > 0
        ]
        afk_events = [ev for ev in events if ev.get("process") == AFK_PROCESS]
        self._afk = compute_afk_segments(
            afk_events + self._events,
            self._window_start,
            self._window_end,
            AFK_THRESHOLD_SECONDS,
        ) if self._window_start else []
        self._rebuild_rows()
        self._hover_index = -1
        self.update()

    def _rebuild_rows(self) -> None:
        """按进程分行，时长降序，超过 MAX_ROWS 合并为其余应用。"""
        by_process: dict[str, list[dict]] = {}
        for ev in self._events:
            by_process.setdefault(ev["process"], []).append(ev)
        ordered = sorted(
            by_process.items(),
            key=lambda item: -sum((e["end"] - e["start"]).total_seconds()
                                  for e in item[1]),
        )
        self._rows: list[tuple[str, list[dict]]] = []
        overflow: list[dict] = []
        for process, evs in ordered[:MAX_ROWS]:
            self._rows.append((process, evs))
            for ev in evs:
                ev["_row"] = len(self._rows) - 1
        for _process, evs in ordered[MAX_ROWS:]:
            overflow.extend(evs)
        if overflow:
            self._rows.append(("__others__", overflow))
            for ev in overflow:
                ev["_row"] = len(self._rows) - 1
        self._row_event_index: list[int] = []
        idx = 0
        for _label, evs in self._rows:
            for ev in evs:
                ev["_idx"] = idx
                idx += 1
        self.updateGeometry()

    def sizeHint(self):
        """有效尺寸：基类默认 sizeHint 为 (-1,-1)，需给出正的宽高再供布局使用。"""
        rows = max(3, len(self._rows)) if getattr(self, "_rows", None) else 3
        return QSize(max(self.width(), 320), AXIS_HEIGHT + ROW_HEIGHT * rows + 16)

    def minimumSizeHint(self):
        rows = max(3, len(self._rows)) if getattr(self, "_rows", None) else 3
        return QSize(240, AXIS_HEIGHT + ROW_HEIGHT * rows + 16)

    # ── 坐标映射 ──────────────────────────────────────────────

    def _chart_rect(self) -> QRectF:
        w, h = self.width(), self.height()
        return QRectF(LABEL_WIDTH, AXIS_HEIGHT, w - LABEL_WIDTH - 12,
                      h - AXIS_HEIGHT - 8)

    def _x_of(self, dt: datetime) -> float:
        rect = self._chart_rect()
        span = (self._window_end - self._window_start).total_seconds()
        frac = (dt - self._window_start).total_seconds() / max(1.0, span)
        return rect.left() + max(0.0, min(1.0, frac)) * rect.width()

    # ── 绘制 ──────────────────────────────────────────────────

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        t = T.current()

        if self._window_start is None or not self._rows:
            p.setPen(QColor(t["TEXT_TERTIARY"]))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
                       "这一天还没有活动区间记录")
            return

        rect = self._chart_rect()
        row_h = ROW_HEIGHT

        # AFK 灰色底纹（跨全部行）
        afk_colour = QColor(t["TEXT_TERTIARY"])
        afk_colour.setAlphaF(0.10)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(afk_colour)
        for s, e in self._afk:
            x1, x2 = self._x_of(s), self._x_of(e)
            if x2 <= rect.left() or x1 >= rect.right():
                continue
            p.drawRect(QRectF(max(x1, rect.left()), rect.top(),
                              min(x2, rect.right()) - max(x1, rect.left()),
                              row_h * len(self._rows)))

        # 刻度轴
        axis_pen = QColor(t["CHART_GRID"])
        text_pen = QColor(t["CHART_TEXT"])
        f = QFont(p.font())
        f.setPointSize(9)
        f.setWeight(QFont.Weight.Normal)
        p.setFont(f)
        ticks = self._axis_ticks()
        for dt, label in ticks:
            x = self._x_of(dt)
            p.setPen(QPen(axis_pen, 1))
            p.drawLine(int(x), int(rect.top()), int(x),
                       int(rect.top() + row_h * len(self._rows)))
            p.setPen(text_pen)
            p.drawText(QRectF(x - 20, 2, 40, AXIS_HEIGHT - 4),
                       Qt.AlignmentFlag.AlignCenter, label)

        # 行标签 + 色条
        for i, (process, evs) in enumerate(self._rows):
            y = rect.top() + i * row_h
            label = self._row_label(process, evs)
            p.setPen(QColor(t["TEXT_SECONDARY"]))
            p.drawText(QRectF(8, y, LABEL_WIDTH - 14, row_h),
                       Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                       label)
            for ev in evs:
                self._paint_bar(p, ev, y, i == self._hover_index, t)

        p.end()

    def _axis_ticks(self) -> list[tuple[datetime, str]]:
        span_days = (self._window_end - self._window_start).days or 1
        ticks: list[tuple[datetime, str]] = []
        if self._mode == "day":
            for hour in range(0, 25, 3):
                dt = self._window_start + timedelta(hours=hour)
                ticks.append((dt, f"{hour:02d}"))
        else:
            step = max(1, span_days // 7)
            dt = self._window_start
            while dt < self._window_end:
                ticks.append((dt, f"{dt.month}/{dt.day}"))
                dt += timedelta(days=step)
        return ticks

    def _row_label(self, process: str, evs: list[dict]) -> str:
        if process == "__others__":
            return "其余应用"
        names = {ev.get("display_name") for ev in evs if ev.get("display_name")}
        if names:
            return next(iter(names))[:14]
        from pathlib import Path as _P

        return _P(process).stem[:14]

    def _paint_bar(self, p: QPainter, ev: dict, row_y: float,
                   hovered: bool, t: dict) -> None:
        x1, x2 = self._x_of(ev["start"]), self._x_of(ev["end"])
        width = max(2.0, x2 - x1)
        colour = category_color(ev.get("category", "其他"))
        rect = QRectF(x1, row_y + 5, width, ROW_HEIGHT - 10)
        p.setPen(QPen(colour.darker(115), 1) if hovered else Qt.PenStyle.NoPen)
        p.setBrush(colour)
        p.drawRoundedRect(rect, 3, 3)

    # ── 交互 ──────────────────────────────────────────────────

    def _event_at(self, x: float, y: float) -> int:
        rect = self._chart_rect()
        if not self._rows or y < rect.top():
            return -1
        row = int((y - rect.top()) // ROW_HEIGHT)
        if row >= len(self._rows):
            return -1
        for ev in self._rows[row][1]:
            if self._x_of(ev["start"]) - 1 <= x <= self._x_of(ev["end"]) + 1:
                return ev.get("_idx", -1)
        return -1

    def _flat_events(self) -> list[dict]:
        result: list[dict] = []
        for _label, evs in getattr(self, "_rows", []):
            result.extend(evs)
        result.sort(key=lambda ev: ev.get("_idx", 0))
        return result

    def mouseMoveEvent(self, event):
        idx = self._event_at(event.position().x(), event.position().y())
        if idx != self._hover_index:
            self._hover_index = idx
            self.update()
        if idx >= 0:
            ev = self._flat_events()[idx]
            dur = format_seconds((ev["end"] - ev["start"]).total_seconds())
            title = ev.get("title") or ""
            text = (
                f"{ev.get('display_name') or ev['process']}"
                f"  {_hhmm(ev['start'])}–{_hhmm(ev['end'])}  {dur}"
            )
            if title:
                short = title if len(title) <= 60 else title[:57] + "…"
                text += f"\n{short}"
            QToolTip.showText(event.globalPosition().toPoint(), text, self)
        else:
            QToolTip.hideText()

    def leaveEvent(self, event):
        self._hover_index = -1
        QToolTip.hideText()
        self.update()

    def mousePressEvent(self, event):
        idx = self._event_at(event.position().x(), event.position().y())
        if idx >= 0:
            self.event_clicked.emit(dict(self._flat_events()[idx]))


class DayBarChartWidget(QWidget):
    """周/月视图的按天柱状图：细柱 + 淡色，顶部显示悬停日数值文本。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._days: list[tuple[date, int]] = []  # (日期, 前台秒数)
        self._hover = -1
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(150)

    def set_days(self, days: list[tuple[date, int]]) -> None:
        self._days = days
        self._hover = -1
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        t = T.current()
        w, h = self.width(), self.height()
        if not self._days:
            p.setPen(QColor(t["TEXT_TERTIARY"]))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "暂无数据")
            return

        pad_b, pad_t = 22, 14
        chart_h = h - pad_b - pad_t
        n = len(self._days)
        max_val = max(v for _d, v in self._days) or 1
        slot = (w - 16) / n
        bar_w = max(3.0, min(18.0, slot * 0.45))

        # 基线
        p.setPen(QPen(QColor(t["CHART_GRID"]), 1))
        base_y = pad_t + chart_h
        p.drawLine(8, int(base_y), int(w - 8), int(base_y))

        accent = QColor(t["CHART_PRIMARY"])
        accent.setAlphaF(0.55)
        faded = QColor(t["CHART_PRIMARY"])
        faded.setAlphaF(0.16)
        label_step = max(1, n // 8)
        f = QFont(p.font())
        f.setPointSize(9)
        p.setFont(f)
        for i, (d, v) in enumerate(self._days):
            cx = 8 + slot * (i + 0.5)
            bar_h = chart_h * (v / max_val) if v else 2
            colour = accent if i == self._hover or v else faded
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(colour)
            p.drawRoundedRect(QRectF(cx - bar_w / 2, base_y - bar_h,
                                     bar_w, max(2.0, bar_h)), 2, 2)
            if i % label_step == 0:
                p.setPen(QColor(t["CHART_TEXT"]))
                p.drawText(QRectF(cx - 24, base_y + 4, 48, 16),
                           Qt.AlignmentFlag.AlignCenter, f"{d.month}/{d.day}")
        p.end()

    def mouseMoveEvent(self, event):
        if not self._days:
            return
        n = len(self._days)
        slot = (self.width() - 16) / n
        idx = int(max(0.0, event.position().x() - 8) // slot)
        idx = min(n - 1, idx)
        if idx != self._hover:
            self._hover = idx
            self.update()
        d, v = self._days[idx]
        QToolTip.showText(
            event.globalPosition().toPoint(),
            f"{d.month}月{d.day}日  前台 {format_seconds(v)}",
            self,
        )

    def leaveEvent(self, event):
        self._hover = -1
        QToolTip.hideText()
        self.update()
