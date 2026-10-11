"""PRECISION AGENT OS — Trends as professional data terminal.

Continuous line chart with area fill, crosshair, interactive tooltip.
Selectable time ranges (7D / 30D / 90D / 6M / 1Y / ALL).
One hero metric, one comparison line, Agent insight below.
"""

from __future__ import annotations

import math

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
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from focus_capsule import theme as T
from focus_capsule.trend_service import DaySummary, TrendReport, TrendService

RANGE_LABELS = ["7D", "30D", "90D", "6M", "1Y", "ALL"]
RANGE_DAYS = {"7D": 7, "30D": 30, "90D": 90, "6M": 180, "1Y": 365, "ALL": 3650}

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
        fill_top = QColor(t["CHART_FILL"])
        fill_top.setAlphaF(0.72)
        fill_bottom = QColor(t["CHART_FILL"])
        fill_bottom.setAlphaF(0.08)
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
        self._setup_ui()
        self.refresh()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(16)

        # ── Time range segmented control ───────────────────────
        controls_row = QHBoxLayout()
        controls_row.setSpacing(0)

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
        layout.addWidget(chart_panel, 1)

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
        layout.addWidget(insight_card)

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

    def refresh(self):
        days = RANGE_DAYS.get(RANGE_LABELS[self._range_idx], 7)
        report = self._trend.get_trend(days=days)
        self._chart.set_data(report.days, self._metric_idx)

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
