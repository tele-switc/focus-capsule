"""数据趋势页 — 时间线、分类占比与连续记录。

Continuous line chart with area fill, crosshair, interactive tooltip.
Selectable time ranges (7D / 30D / 90D / 6M / 1Y / ALL).
One hero metric, one comparison line, Agent insight below.
"""

from __future__ import annotations

import math
from datetime import date, datetime, timedelta

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
)
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from focus_capsule import theme as T
from focus_capsule.timeline_view import (
    DayBarChartWidget,
    TimelineView,
    category_color,
    format_seconds,
)
from focus_capsule.trend_service import DaySummary, TrendReport, TrendService

RANGE_LABELS = ["7D", "30D", "90D", "6M", "1Y", "ALL"]
RANGE_DAYS = {"7D": 7, "30D": 30, "90D": 90, "6M": 180, "1Y": 365, "ALL": 3650}

# 日 / 周 / 月视图切换（时间线 + 分类占比 + 应用排行随其聚合）
VIEW_LABELS = ["日", "周", "月"]
VIEW_DAYS = {"日": 1, "周": 7, "月": 30}

METRICS = [
    ("focus_time", "实际专注时间", "分钟"),
    ("completion_rate", "完成率", "%"),
    ("session_count", "专注会话数", "轮"),
    ("avg_session", "平均会话时长", "分钟"),
    ("distraction", "分心次数", "次"),
    ("unlock", "临时解锁", "次"),
]


class LineChartWidget(QWidget):
    """Continuous line chart with area fill, crosshair, tooltip."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._summaries: list[DaySummary] = []
        self._metric_idx = 0
        self._show_comparison = False
        self._hover_x = -1
        self._hover_y = -1
        self.setMinimumHeight(280)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMouseTracking(True)
        self._target_line: float | None = None
        self._avg_line: float | None = None

    def set_data(self, summaries: list[DaySummary], metric_idx: int = 0):
        self._summaries = summaries
        self._metric_idx = metric_idx
        self._hover_x = -1
        self.update()

    def set_ref_lines(self, target: float | None = None, avg: float | None = None):
        self._target_line = target
        self._avg_line = avg
        self.update()

    def _get_metric_value(self, s: DaySummary) -> float:
        if self._metric_idx == 0:
            return s.focus_minutes
        if self._metric_idx == 1:
            return s.completion_rate * 100
        if self._metric_idx == 2:
            return s.session_count
        if self._metric_idx == 3:
            return s.focus_minutes / max(1, s.session_count) if s.session_count else 0
        if self._metric_idx == 4:
            return getattr(s, "distraction_count", 0)
        if self._metric_idx == 5:
            return getattr(s, "unlock_count", 0)
        return 0

    def _metric_label(self, val: float) -> str:
        key, name, unit = METRICS[self._metric_idx]
        if unit == "%":
            return f"{val:.0f}{unit}"
        if unit == "分钟":
            if val >= 60:
                return f"{int(val // 60)}h{int(val % 60)}m" if val % 60 else f"{int(val // 60)}h"
            return f"{int(val)}m"
        return f"{int(val)}{unit}"

    def mouseMoveEvent(self, event):
        self._hover_x = event.position().x()
        self._hover_y = event.position().y()
        self.update()

    def leaveEvent(self, event):
        self._hover_x = -1
        self._hover_y = -1
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        t = T.current()
        w, h = self.width(), self.height()

        if not self._summaries or len(self._summaries) < 2:
            p.setPen(QColor(t["TEXT_TERTIARY"]))
            f = QFont(p.font())
            f.setPointSize(13)
            p.setFont(f)
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
                       "还没有足够的专注数据进行趋势分析")
            return

        pad_l, pad_r, pad_t, pad_b = 44, 16, 16, 28
        chart_w = w - pad_l - pad_r
        chart_h = h - pad_t - pad_b

        values = [self._get_metric_value(s) for s in self._summaries]
        max_val = max(values) if values else 1
        if max_val == 0:
            max_val = 1
        # Round up for nice gridlines
        if max_val > 10:
            max_val = math.ceil(max_val / 10) * 10
        else:
            max_val = max(1, math.ceil(max_val))

        # Horizontal grid lines + Y labels
        grid_pen = QColor(t["CHART_GRID"])
        p.setPen(QPen(grid_pen, 1))
        for i in range(5):
            y = pad_t + chart_h * i / 4
            p.drawLine(int(pad_l), int(y), int(w - pad_r), int(y))
            val = max_val * (1 - i / 4)
            p.setPen(QColor(t["CHART_TEXT"]))
            gf = QFont(p.font())
            gf.setPointSize(9)
            gf.setWeight(QFont.Weight.Normal)
            p.setFont(gf)
            p.drawText(QRectF(0, y - 7, pad_l - 4, 14),
                       Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                       self._metric_label(val))
            p.setPen(QPen(grid_pen, 1))

        # Area fill + line path
        n = len(self._summaries)
        pts = []
        for i, val in enumerate(values):
            x = pad_l + chart_w * i / (n - 1) if n > 1 else pad_l
            y = pad_t + chart_h * (1 - val / max_val)
            pts.append((x, y))

        # Area fill
        fill_path = QPainterPath()
        fill_path.moveTo(pts[0][0], pad_t + chart_h)
        for x, y in pts:
            fill_path.lineTo(x, y)
        fill_path.lineTo(pts[-1][0], pad_t + chart_h)
        fill_path.closeSubpath()
        gradient = QLinearGradient(0, pad_t, 0, pad_t + chart_h)
        # 淡色渐变填充（顶部 16% → 底部 3%），避免大面积饱和色块
        fill_top = QColor(t["CHART_PRIMARY"])
        fill_top.setAlphaF(0.16)
        fill_bottom = QColor(t["CHART_PRIMARY"])
        fill_bottom.setAlphaF(0.03)
        gradient.setColorAt(0, fill_top)
        gradient.setColorAt(1, fill_bottom)
        p.fillPath(fill_path, QBrush(gradient))

        # Line
        line_path = QPainterPath()
        line_path.moveTo(pts[0][0], pts[0][1])
        for x, y in pts[1:]:
            line_path.lineTo(x, y)
        line_pen = QPen(QColor(t["CHART_PRIMARY"]), 2)
        line_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        line_pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(line_pen)
        p.drawPath(line_path)

        # Reference lines — target
        if self._target_line and self._target_line > 0 and self._target_line <= max_val:
            ty = pad_t + chart_h * (1 - self._target_line / max_val)
            ref_pen = QPen(QColor(t["CHART_SECONDARY"]), 1, Qt.PenStyle.DashLine)
            p.setPen(ref_pen)
            p.drawLine(int(pad_l), int(ty), int(w - pad_r), int(ty))
            p.setPen(QColor(t["CHART_SECONDARY"]))
            rf = QFont(p.font())
            rf.setPointSize(9)
            p.setFont(rf)
            p.drawText(QRectF(w - pad_r - 60, ty - 14, 56, 12),
                       Qt.AlignmentFlag.AlignRight, "目标")

        # Reference line — average
        if self._avg_line and self._avg_line > 0 and self._avg_line <= max_val:
            ay = pad_t + chart_h * (1 - self._avg_line / max_val)
            avg_pen = QPen(QColor(t["CHART_TERTIARY"]), 1, Qt.PenStyle.DashLine)
            p.setPen(avg_pen)
            p.drawLine(int(pad_l), int(ay), int(w - pad_r), int(ay))
            p.setPen(QColor(t["CHART_TERTIARY"]))
            af = QFont(p.font())
            af.setPointSize(9)
            p.setFont(af)
            p.drawText(QRectF(w - pad_r - 60, ay + 2, 56, 12),
                       Qt.AlignmentFlag.AlignRight, "平均")

        # X labels — sparse
        p.setPen(QColor(t["CHART_TEXT"]))
        xf = QFont(p.font())
        xf.setPointSize(9)
        xf.setWeight(QFont.Weight.Normal)
        p.setFont(xf)
        label_step = max(1, n // 7)
        for i in range(0, n, label_step):
            s = self._summaries[i]
            x = pad_l + chart_w * i / (n - 1) if n > 1 else pad_l
            lbl = f"{s.date.month}/{s.date.day}"
            p.drawText(QRectF(x - 20, pad_t + chart_h + 4, 40, 16),
                       Qt.AlignmentFlag.AlignCenter, lbl)

        # Crosshair + tooltip
        if self._hover_x >= pad_l and self._hover_x <= w - pad_r:
            # Find nearest data point
            best_i = 0
            best_dist = float("inf")
            for i, (x, y) in enumerate(pts):
                d = abs(x - self._hover_x)
                if d < best_dist:
                    best_dist = d
                    best_i = i
            cx, cy = pts[best_i]

            # Crosshair
            cross_pen = QPen(QColor(t["CHART_CROSSHAIR"]), 1)
            cross_pen.setStyle(Qt.PenStyle.DashLine)
            p.setPen(cross_pen)
            p.drawLine(int(cx), int(pad_t), int(cx), int(pad_t + chart_h))
            p.drawLine(int(pad_l), int(cy), int(w - pad_r), int(cy))

            # Point
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(t["CHART_PRIMARY"]))
            p.drawEllipse(QRectF(cx - 4, cy - 4, 8, 8))
            p.setBrush(QColor(t["SURFACE_2"]))
            p.drawEllipse(QRectF(cx - 2.5, cy - 2.5, 5, 5))

            # Tooltip
            s = self._summaries[best_i]
            val = self._get_metric_value(s)
            tip_text = f"{s.date.month}/{s.date.day}  {self._metric_label(val)}"
            tip_rect = p.fontMetrics().boundingRect(tip_text)
            tip_w = tip_rect.width() + 16
            tip_h = tip_rect.height() + 8
            tip_x = min(cx + 10, w - tip_w - 4)
            tip_y = max(cy - tip_h - 6, pad_t + 2)

            p.setBrush(QColor(t["SURFACE_2"]))
            p.setPen(QPen(QColor(t["TEXT_TERTIARY"]), 1))
            p.drawRoundedRect(QRectF(tip_x, tip_y, tip_w, tip_h), 6, 6)
            p.setPen(QColor(t["TEXT_PRIMARY"]))
            tf = QFont(p.font())
            tf.setPointSize(10)
            tf.setWeight(QFont.Weight.Medium)
            p.setFont(tf)
            p.drawText(QRectF(tip_x + 8, tip_y, tip_w - 16, tip_h),
                       Qt.AlignmentFlag.AlignVCenter, tip_text)


class TrendPage(QWidget):
    """Professional data terminal for focus analytics."""

    def __init__(self, trend_service: TrendService, parent=None):
        super().__init__(parent)
        self._trend = trend_service
        self._range_idx = 0
        self._metric_idx = 0
        self._view_idx = 0
        self._setup_ui()
        self.refresh()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(16)

        # ── Time range segmented control ───────────────────────
        controls_row = QHBoxLayout()
        controls_row.setSpacing(0)

        # 日/周/月视图切换
        view_seg = QFrame()
        view_seg.setObjectName("segmentedControl")
        view_layout = QHBoxLayout(view_seg)
        view_layout.setContentsMargins(2, 2, 2, 2)
        view_layout.setSpacing(0)
        self._view_btns = []
        for i, label in enumerate(VIEW_LABELS):
            btn = QPushButton(label)
            btn.setObjectName("segmentedBtn")
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            if i == 0:
                btn.setChecked(True)
            btn.clicked.connect(lambda checked, idx=i: self._set_view(idx))
            view_layout.addWidget(btn)
            self._view_btns.append(btn)
        controls_row.addWidget(view_seg)
        controls_row.addSpacing(16)

        # Range selector
        range_seg = QFrame()
        range_seg.setObjectName("segmentedControl")
        range_layout = QHBoxLayout(range_seg)
        range_layout.setContentsMargins(2, 2, 2, 2)
        range_layout.setSpacing(0)
        self._range_btns = []
        for i, label in enumerate(RANGE_LABELS):
            btn = QPushButton(label)
            btn.setObjectName("segmentedBtn")
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            if i == 0:
                btn.setChecked(True)
            btn.clicked.connect(lambda checked, idx=i: self._set_range(idx))
            range_layout.addWidget(btn)
            self._range_btns.append(btn)
        controls_row.addWidget(range_seg)
        controls_row.addSpacing(16)

        # Metric selector
        metric_seg = QFrame()
        metric_seg.setObjectName("segmentedControl")
        metric_layout = QHBoxLayout(metric_seg)
        metric_layout.setContentsMargins(2, 2, 2, 2)
        metric_layout.setSpacing(0)
        self._metric_btns = []
        for i, (key, name, unit) in enumerate(METRICS):
            btn = QPushButton(name)
            btn.setObjectName("segmentedBtn")
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            if i == 0:
                btn.setChecked(True)
            btn.clicked.connect(lambda checked, idx=i: self._set_metric(idx))
            metric_layout.addWidget(btn)
            self._metric_btns.append(btn)
        controls_row.addWidget(metric_seg, 1)
        controls_row.addStretch()
        layout.addLayout(controls_row)

        # ── Hero metric + line chart ─────────────────────────────
        chart_panel = QFrame()
        chart_panel.setObjectName("sectionCard")
        chart_panel_layout = QVBoxLayout(chart_panel)
        chart_panel_layout.setContentsMargins(24, 22, 24, 20)
        chart_panel_layout.setSpacing(0)
        chart_layout = QHBoxLayout()
        chart_layout.setSpacing(24)

        # Left: hero metric column
        hero_col = QVBoxLayout()
        hero_col.setSpacing(4)
        hero_col.setContentsMargins(0, 8, 0, 0)

        _, metric_name, _ = METRICS[self._metric_idx]
        self._hero_label = QLabel(metric_name)
        self._hero_label.setStyleSheet(
            f"color:{T.get('TEXT_TERTIARY')}; font-size:12px; font-weight:{T.WEIGHT_BODY};"
            f" letter-spacing:0.5px;"
        )
        hero_col.addWidget(self._hero_label)

        self._hero_value = QLabel("—")
        self._hero_value.setStyleSheet(
            f"color:{T.get('TEXT_PRIMARY')}; font-size:{T.FONT_HERO}px;"
            f" font-weight:{T.WEIGHT_MEDIUM}; font-family:{T.FONT_FAMILY_NUM};"
            f" letter-spacing:-1.5px;"
        )
        hero_col.addWidget(self._hero_value)

        self._hero_sub = QLabel("")
        self._hero_sub.setStyleSheet(
            f"color:{T.get('TEXT_SECONDARY')}; font-size:13px; font-weight:{T.WEIGHT_BODY};"
        )
        hero_col.addWidget(self._hero_sub)

        hero_col.addSpacing(12)

        # Compact summary stats (no cards)
        self._stat_total = self._compact_stat(hero_col, "总专注", "—")
        self._stat_avg = self._compact_stat(hero_col, "日均", "—")
        self._stat_streak = self._compact_stat(hero_col, "连续完成", "—")

        hero_col.addStretch()
        chart_layout.addLayout(hero_col, 1)

        # Right: line chart
        self._chart = LineChartWidget()
        chart_layout.addWidget(self._chart, 3)

        chart_panel_layout.addLayout(chart_layout)

        # ── 时间线 / 按天柱状 ───────────────────────────────────
        timeline_panel = QFrame()
        timeline_panel.setObjectName("sectionCard")
        timeline_col = QVBoxLayout(timeline_panel)
        timeline_col.setContentsMargins(24, 18, 24, 16)
        timeline_col.setSpacing(10)

        timeline_head = QHBoxLayout()
        self._timeline_title = QLabel("活动时间线")
        self._timeline_title.setObjectName("eyebrow")
        timeline_head.addWidget(self._timeline_title)
        timeline_head.addStretch()
        self._range_summary_label = QLabel("")
        self._range_summary_label.setStyleSheet(
            f"color:{T.get('TEXT_SECONDARY')}; font-size:13px;"
        )
        timeline_head.addWidget(self._range_summary_label)
        timeline_col.addLayout(timeline_head)

        self._timeline = TimelineView()
        self._timeline.event_clicked.connect(self._on_event_clicked)
        timeline_col.addWidget(self._timeline)

        self._day_bars = DayBarChartWidget()
        self._day_bars.setVisible(False)
        timeline_col.addWidget(self._day_bars)

        self._insight_text_tiny = QLabel("")
        self._insight_text_tiny.setStyleSheet(
            f"color:{T.get('TEXT_TERTIARY')}; font-size:12px;"
        )
        timeline_col.addWidget(self._insight_text_tiny)

        # ── 分类占比（横向细色条）──────────────────────────────
        share_panel = QFrame()
        share_panel.setObjectName("sectionCard")
        share_col = QVBoxLayout(share_panel)
        share_col.setContentsMargins(24, 18, 24, 16)
        share_col.setSpacing(8)
        share_title = QLabel("分类占比")
        share_title.setObjectName("eyebrow")
        share_col.addWidget(share_title)
        self._share_rows_host = QVBoxLayout()
        self._share_rows_host.setSpacing(6)
        share_col.addLayout(self._share_rows_host)
        self._share_empty = QLabel("暂无分类数据")
        self._share_empty.setStyleSheet(
            f"color:{T.get('TEXT_TERTIARY')}; font-size:12px;"
        )
        share_col.addWidget(self._share_empty)

        # ── 应用排行（淡色块图标）──────────────────────────────
        rank_panel = QFrame()
        rank_panel.setObjectName("sectionCard")
        rank_col = QVBoxLayout(rank_panel)
        rank_col.setContentsMargins(24, 18, 24, 16)
        rank_col.setSpacing(8)
        rank_title = QLabel("应用排行")
        rank_title.setObjectName("eyebrow")
        rank_col.addWidget(rank_title)
        self._rank_rows_host = QVBoxLayout()
        self._rank_rows_host.setSpacing(6)
        rank_col.addLayout(self._rank_rows_host)
        self._rank_empty = QLabel("暂无应用记录")
        self._rank_empty.setStyleSheet(
            f"color:{T.get('TEXT_TERTIARY')}; font-size:12px;"
        )
        rank_col.addWidget(self._rank_empty)

        # ── Agent insight ────────────────────────────────────────
        insight_card = QFrame()
        insight_card.setObjectName("sectionCard")
        insight_col = QVBoxLayout(insight_card)
        insight_col.setContentsMargins(20, 14, 20, 14)
        insight_col.setSpacing(4)

        insight_key = QLabel("专注洞察")
        insight_key.setObjectName("eyebrow")
        insight_col.addWidget(insight_key)

        self._insight_text = QLabel("加载数据中…")
        self._insight_text.setObjectName("insightText")
        self._insight_text.setWordWrap(True)
        self._insight_text.setStyleSheet(
            f"color:{T.get('TEXT_SECONDARY')}; font-size:15px; line-height:1.6;"
        )
        insight_col.addWidget(self._insight_text)

        # ── 下部内容装进滚动区，避免小窗口下互相挤压 ────────────
        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(16)
        body_layout.addWidget(chart_panel)
        body_layout.addWidget(timeline_panel)
        body_layout.addWidget(share_panel)
        body_layout.addWidget(rank_panel)
        body_layout.addWidget(insight_card)
        body_layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QScrollArea > QWidget > QWidget { background: transparent; }"
        )
        scroll.setWidget(body)
        layout.addWidget(scroll, 1)

    @staticmethod
    def _compact_stat(layout: QVBoxLayout, label: str, value: str) -> QLabel:
        row = QHBoxLayout()
        row.setSpacing(0)
        lbl = QLabel(label)
        lbl.setStyleSheet(
            f"color:{T.get('TEXT_TERTIARY')}; font-size:12px; font-weight:{T.WEIGHT_BODY};"
        )
        lbl.setFixedWidth(60)
        val = QLabel(value)
        val.setStyleSheet(
            f"color:{T.get('TEXT_PRIMARY')}; font-size:15px; font-weight:{T.WEIGHT_SECTION};"
            f" font-family:{T.FONT_FAMILY_NUM};"
        )
        row.addWidget(lbl)
        row.addWidget(val)
        layout.addLayout(row)
        return val

    def _set_range(self, idx: int):
        self._range_idx = idx
        for i, btn in enumerate(self._range_btns):
            btn.setChecked(i == idx)
        self.refresh()

    def _set_metric(self, idx: int):
        self._metric_idx = idx
        for i, btn in enumerate(self._metric_btns):
            btn.setChecked(i == idx)
        _, name, _ = METRICS[idx]
        self._hero_label.setText(name)
        self.refresh()

    def _set_view(self, idx: int):
        self._view_idx = idx
        for i, btn in enumerate(self._view_btns):
            btn.setChecked(i == idx)
        self._refresh_bottom()

    @staticmethod
    def _clear_layout(layout) -> None:
        """清空动态行容器里的旧控件。"""
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)

    def _on_event_clicked(self, event: dict) -> None:
        """点击时间线某段：详情回调（当前写入底部提示行）。"""
        dur = format_seconds((event["end"] - event["start"]).total_seconds())
        title = event.get("title") or ""
        detail = (
            f"已选中：{event.get('display_name') or event['process']}"
            f" · {event['start'].strftime('%H:%M')}–"
            f"{event['end'].strftime('%H:%M')} · {dur}"
        )
        if title:
            detail += f" · {title[:40]}"
        self._insight_text_tiny.setText(detail)

    def _refresh_bottom(self) -> None:
        """按日/周/月视图刷新：时间线、聚合摘要、分类占比、应用排行。"""
        view = VIEW_LABELS[self._view_idx]
        days = VIEW_DAYS[view]
        today = datetime.now().astimezone().date()
        start = today - timedelta(days=days - 1)

        # ── 时间线 / 按天柱状 ──
        if view == "日":
            self._timeline.setVisible(True)
            self._day_bars.setVisible(False)
            self._timeline_title.setText("活动时间线 · 今天（0–24 时）")
            try:
                events = self._trend.get_day_events(today)
            except OSError:
                events = []
            self._timeline.set_day(today, events)
        else:
            self._timeline.setVisible(False)
            self._day_bars.setVisible(True)
            self._timeline_title.setText(f"按天前台时长 · {view}视图")
            daily = self._trend.get_daily_activity_seconds(start, today)
            self._day_bars.set_days(daily)

        # ── 聚合摘要（总时长 / 日均 / 完成率 / 连续达标 / 破功 / 分类 Top5）──
        try:
            summary = self._trend.get_range_summary(start, today)
            parts = [
                f"总专注 {format_seconds(summary.total_focus_seconds)}",
                f"日均 {summary.avg_daily_minutes:.0f} 分",
                f"完成率 {summary.completion_rate:.0%}",
            ]
            # 连续达标 / 破功留痕：全量历史口径，不受当前 7/30/90… 窗口限制
            get_streak = getattr(self._trend, "get_streak_summary", None)
            if callable(get_streak):
                streak = get_streak()
                parts.append(f"连续达标 {streak.current_streak} 天")
                parts.append(f"破功 {len(streak.broken_days)} 天")
            top5 = summary.category_top5[:5]
            if top5 and top5[0].total_focus_seconds:
                share = self._trend.get_category_share(start, today)
                total = sum(item["seconds"] for item in share) or 1
                top_txt = "、".join(
                    f"{c.category} {c.total_focus_seconds / total:.0%}"
                    for c in top5
                )
                parts.append(f"分类 Top5：{top_txt}")
            self._range_summary_label.setText("  ·  ".join(parts))
        except OSError:
            self._range_summary_label.setText("")

        # ── 分类占比：横向细色条 + 百分比 ──
        self._clear_layout(self._share_rows_host)
        share = self._trend.get_category_share(start, today)
        if not share:
            self._share_empty.setVisible(True)
            self._share_rows_host.addWidget(self._share_empty)
        else:
            self._share_empty.setVisible(False)
            max_ratio = max(item["ratio"] for item in share) or 1.0
            for item in share[:8]:
                self._share_rows_host.addWidget(
                    self._make_share_row(item["category"], item["ratio"], max_ratio)
                )

        # ── 应用排行：淡色块图标 + 名称 + 时长 ──
        self._clear_layout(self._rank_rows_host)
        ranking = self._trend.get_app_usage_ranking(start, today)
        if not ranking:
            self._rank_empty.setVisible(True)
            self._rank_rows_host.addWidget(self._rank_empty)
        else:
            self._rank_empty.setVisible(False)
            for item in ranking[:10]:
                self._rank_rows_host.addWidget(
                    self._make_rank_row(
                        item["display_name"], item["category"],
                        item["seconds"], item["ratio"],
                    )
                )

    def _make_share_row(self, category: str, ratio: float, max_ratio: float) -> QWidget:
        """一条细色条表示分类占比；淡色、不饱和填充。"""
        t = T.current()
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(10)
        name = QLabel(category)
        name.setFixedWidth(72)
        name.setStyleSheet(
            f"color:{T.get('TEXT_SECONDARY')}; font-size:12px;"
        )
        track = QFrame()
        track.setFixedHeight(6)
        track.setMinimumWidth(80)
        track.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        track.setStyleSheet(
            f"background:{T.get('BORDER_SUBTLE')}; border-radius:3px;"
        )
        inner = QHBoxLayout(track)
        inner.setContentsMargins(0, 0, 0, 0)
        fill = QFrame()
        colour = category_color(category, 0.55)
        fill.setFixedHeight(6)
        fill.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        # 宽度按相对占比伸缩；父容器 resize 时至少保留 4px
        fill.setMinimumWidth(max(4, int(160 * (ratio / max_ratio))))
        fill.setStyleSheet(
            f"background:{colour.name(QColor.NameFormat.HexArgb)};"
            f" border-radius:3px;"
        )
        inner.addWidget(fill)
        inner.addStretch()
        pct = QLabel(f"{ratio:.1%}")
        pct.setFixedWidth(52)
        pct.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        pct.setStyleSheet(
            f"color:{T.get('TEXT_PRIMARY')}; font-size:12px;"
            f" font-family:{T.FONT_FAMILY_NUM};"
        )
        h.addWidget(name)
        h.addWidget(track, 1)
        h.addWidget(pct)
        return row

    def _make_rank_row(
        self, display_name: str, category: str, seconds: int, ratio: float
    ) -> QWidget:
        """应用排行一行：图标方块 = 6% 淡底 + 1px 细边框（无粗黑边）。"""
        colour = category_color(category, 0.06)
        border = QColor(T.get("BORDER_NORMAL"))
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(10)
        tile = QFrame()
        tile.setFixedSize(26, 26)
        tile.setStyleSheet(
            f"background:{colour.name(QColor.NameFormat.HexArgb)};"
            f" border:1px solid {border.name(QColor.NameFormat.HexArgb)};"
            f" border-radius:6px;"
        )
        tile_layout = QHBoxLayout(tile)
        tile_layout.setContentsMargins(0, 0, 0, 0)
        letter = QLabel((display_name or "?")[:1].upper())
        letter.setAlignment(Qt.AlignmentFlag.AlignCenter)
        letter.setStyleSheet(
            f"color:{category_color(category, 0.95).darker(120).name()};"
            f" font-size:12px; font-weight:{T.WEIGHT_SECTION}; background:transparent;"
            f" border:none;"
        )
        tile_layout.addWidget(letter)
        name = QLabel(display_name or category)
        name.setStyleSheet(f"color:{T.get('TEXT_PRIMARY')}; font-size:13px;")
        cat = QLabel(category)
        cat.setStyleSheet(f"color:{T.get('TEXT_TERTIARY')}; font-size:11px;")
        dur = QLabel(format_seconds(seconds))
        dur.setStyleSheet(
            f"color:{T.get('TEXT_SECONDARY')}; font-size:12px;"
            f" font-family:{T.FONT_FAMILY_NUM};"
        )
        pct = QLabel(f"{ratio:.0%}")
        pct.setFixedWidth(40)
        pct.setAlignment(Qt.AlignmentFlag.AlignRight)
        pct.setStyleSheet(
            f"color:{T.get('TEXT_TERTIARY')}; font-size:12px;"
            f" font-family:{T.FONT_FAMILY_NUM};"
        )
        h.addWidget(tile)
        h.addWidget(name)
        h.addWidget(cat)
        h.addStretch()
        h.addWidget(dur)
        h.addWidget(pct)
        return row

    def refresh(self):
        days = RANGE_DAYS.get(RANGE_LABELS[self._range_idx], 7)
        report = self._trend.get_trend(days=days)
        self._chart.set_data(report.days, self._metric_idx)
        self._refresh_bottom()

        # Hero metric
        key, name, unit = METRICS[self._metric_idx]
        if key == "focus_time":
            total = report.total_focus_seconds
            hours = total // 3600
            mins = (total % 3600) // 60
            self._hero_value.setText(
                f"{hours}h{mins}m" if hours else f"{mins}m"
            )
            self._hero_sub.setText(f"近 {days} 天累计")
            self._stat_total.setText(f"{hours}h{mins}m" if hours else f"{mins}m")
            self._stat_avg.setText(f"{report.avg_daily_minutes:.0f}m")
            self._stat_streak.setText(f"{report.current_streak}天")

            # Reference lines
            avg = report.avg_daily_minutes
            target = getattr(report, "daily_goal", None)
            self._chart.set_ref_lines(target=target, avg=avg)

            # Agent insight
            self._generate_insight(report)

        elif key == "completion_rate":
            rate = sum(s.completion_rate for s in report.days) / max(1, len(report.days))
            self._hero_value.setText(f"{rate:.0%}")
            self._hero_sub.setText(f"近 {days} 天平均")
            self._chart.set_ref_lines(target=1.0, avg=None)
            self._insight_text.setText("完成率反映专注会话达成预期的比例。")

        else:
            self._hero_value.setText("—")
            self._hero_sub.setText(f"近 {days} 天")
            self._chart.set_ref_lines()
            self._insight_text.setText("")

    def _generate_insight(self, report: TrendReport):
        if not report.days:
            self._insight_text.setText("暂无足够数据生成洞察。")
            return

        total = report.total_focus_seconds
        avg = report.avg_daily_minutes
        streak = report.current_streak

        # Analyse volatility
        vals = [s.focus_minutes for s in report.days]
        if len(vals) > 1:
            mean = sum(vals) / len(vals)
            variance = sum((v - mean) ** 2 for v in vals) / len(vals)
            stddev = math.sqrt(variance)
            cv = stddev / mean if mean > 0 else 0
        else:
            cv = 0

        # Find best and worst days
        if vals:
            best_idx = vals.index(max(vals))
            worst_idx = vals.index(min(vals))
            best_day = report.days[best_idx]
            worst_day = report.days[worst_idx]
        else:
            best_day = worst_day = None

        parts = []
        parts.append(f"近 {len(report.days)} 天总专注 {int(total // 60)} 分钟，日均 {avg:.0f} 分钟。")
        if streak > 0:
            parts.append(f"已连续 {streak} 天完成目标。")
        if cv > 0.5 and avg > 0:
            parts.append("波动较大，建议保持更规律的开始时间。")
        else:
            parts.append("数据稳定，专注节奏良好。")
        if best_day and worst_day and best_day.focus_minutes > 0:
            parts.append(
                f"最佳日 {best_day.date.month}/{best_day.date.day} 完成 "
                f"{best_day.focus_minutes} 分钟。"
            )

        self._insight_text.setText(" ".join(parts))
