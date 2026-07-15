"""Trend analysis page — weekly / monthly focus insights.

Renders a custom-painted bar-chart of the last 7 days, streak stats,
completion rate, top distractions, and category breakdown.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QColor, QPainter, QFont
from PyQt6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton,
    QSizePolicy, QVBoxLayout, QWidget,
)

from focus_capsule.data_models import china_today
from focus_capsule.trend_service import TrendService, TrendReport, DaySummary
from focus_capsule.theme import (
    WINDOW_BG, SURFACE_1, SURFACE_2, SURFACE_3, INPUT_BG,
    ACCENT, WARNING, SUCCESS, DANGER, INFO,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_TERTIARY,
    BORDER_SUBTLE, RADIUS_LG,
    FONT_PAGE_TITLE, FONT_SECTION, FONT_AUX, FONT_META,
    WEIGHT_TITLE, WEIGHT_SECTION,
)


class WeekBarChart(QWidget):
    """A simple 7-day focus-time bar chart painted with QPainter."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._summaries: list[DaySummary] = []
        self.setMinimumHeight(200)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_data(self, summaries: list[DaySummary]):
        self._summaries = summaries
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        if not self._summaries:
            p.setPen(QColor(TEXT_TERTIARY))
            f = QFont(p.font())
            f.setPointSize(12)
            p.setFont(f)
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
                       "还没有专注数据\n完成一轮专注后这里会显示你的趋势")
            return

        padding_l = 36
        padding_r = 16
        padding_t = 28
        padding_b = 28
        chart_w = w - padding_l - padding_r
        chart_h = h - padding_t - padding_b

        max_minutes = max(s.focus_minutes for s in self._summaries) or 1
        # round up to nearest 30
        max_minutes = ((max_minutes + 29) // 30) * 30

        # Grid lines
        p.setPen(QPen(QColor(BORDER_SUBTLE)))
        grid_pen = QColor(BORDER_SUBTLE)
        for i in range(4):
            y = padding_t + chart_h * i / 3
            grid_pen.setAlpha(40)
            p.setPen(grid_pen)
            p.drawLine(int(padding_l), int(y), int(w - padding_r), int(y))
            val = max_minutes * (1 - i / 3)
            p.setPen(QColor(TEXT_TERTIARY))
            f_grid = QFont(p.font())
            f_grid.setPointSize(9)
            p.setFont(f_grid)
            label = f"{int(val)}m"
            p.drawText(
                0, int(y - 7), padding_l - 2, 14,
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                label,
            )

        # Bars
        bar_w = chart_w / len(self._summaries) - 8
        today = china_today()

        for i, s in enumerate(self._summaries):
            bar_x = padding_l + i * (bar_w + 8) + 4
            bar_h = (s.focus_minutes / max(max_minutes, 1)) * chart_h if s.focus_minutes else 0
            bar_y = padding_t + chart_h - bar_h

            is_today = s.date == today
            is_weekend = s.date.weekday() >= 5

            if is_today:
                color = QColor(ACCENT)
            elif is_weekend:
                color = QColor(WARNING)
            else:
                color = QColor(INFO)

            if bar_h > 0:
                p.setBrush(color)
            else:
                # Empty days: faint indicator
                color.setAlpha(50)
                p.setBrush(color)
                bar_h = 2
                bar_y = padding_t + chart_h - bar_h

            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(QRectF(bar_x, bar_y, bar_w, bar_h), 4, 4)

            # Day label
            p.setPen(QColor(TEXT_SECONDARY if is_today else TEXT_TERTIARY))
            f_label = QFont(p.font())
            f_label.setPointSize(9)
            if is_today:
                f_label.setWeight(QFont.Weight.Bold)
            p.setFont(f_label)
            day_label = f"{s.date.month}/{s.date.day}"
            p.drawText(
                int(bar_x - 4), int(padding_t + chart_h + 4),
                int(bar_w + 8), 20,
                Qt.AlignmentFlag.AlignCenter,
                day_label,
            )

            # Minutes on top of bar
            if s.focus_minutes > 0 and bar_h > 20:
                p.setPen(QColor(TEXT_PRIMARY))
                f_val = QFont(p.font())
                f_val.setPointSize(9)
                f_val.setWeight(QFont.Weight.Medium)
                p.setFont(f_val)
                if s.focus_minutes >= 60:
                    hours = s.focus_minutes // 60
                    mins = s.focus_minutes % 60
                    val_text = f"{hours}h{mins}m" if mins else f"{hours}h"
                else:
                    val_text = f"{s.focus_minutes}m"
                p.drawText(
                    int(bar_x - 4), int(bar_y - 18),
                    int(bar_w + 8), 16,
                    Qt.AlignmentFlag.AlignCenter,
                    val_text,
                )

from PyQt6.QtGui import QPen


class TrendPage(QWidget):
    """Trend analysis page with bar chart, stats, and category breakdown."""

    def __init__(self, trend_service: TrendService, parent=None):
        super().__init__(parent)
        self._trend = trend_service
        self._setup_ui()
        self.refresh()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # Header
        header = QHBoxLayout()
        header.setSpacing(12)
        title = QLabel("趋势")
        title.setObjectName("pageTitle")
        header.addWidget(title)
        header.addStretch()
        self._range_label = QLabel("最近 7 天")
        self._range_label.setObjectName("subtitle")
        header.addWidget(self._range_label)
        layout.addLayout(header)

        subtitle = QLabel("追踪专注模式，发现可以改进的地方")
        subtitle.setObjectName("subtitle")
        layout.addWidget(subtitle)

        # Stats cards row
        stats_row = QHBoxLayout()
        stats_row.setSpacing(12)
        self._stat_total = self._stat_card(stats_row, "0m", "总专注时间")
        self._stat_avg = self._stat_card(stats_row, "0m", "日均")
        self._stat_streak = self._stat_card(stats_row, "0 天", "连续完成")
        self._stat_rate = self._stat_card(stats_row, "0%", "完成率")
        layout.addLayout(stats_row)

        # Bar chart
        chart_frame = QFrame()
        chart_frame.setObjectName("panel")
        chart_layout = QVBoxLayout(chart_frame)
        chart_layout.setContentsMargins(18, 14, 18, 14)
        chart_layout.setSpacing(10)
        chart_title = QLabel("每日专注时间")
        chart_title.setObjectName("sectionTitle")
        chart_layout.addWidget(chart_title)
        self._chart = WeekBarChart()
        chart_layout.addWidget(self._chart)
        layout.addWidget(chart_frame, 1)

        # Category breakdown
        cat_frame = QFrame()
        cat_frame.setObjectName("panel")
        cat_layout = QVBoxLayout(cat_frame)
        cat_layout.setContentsMargins(18, 14, 18, 14)
        cat_layout.setSpacing(10)
        cat_title = QLabel("分类统计")
        cat_title.setObjectName("sectionTitle")
        cat_layout.addWidget(cat_title)
        self._cat_container = QVBoxLayout()
        self._cat_container.setSpacing(6)
        cat_layout.addLayout(self._cat_container)
        layout.addWidget(cat_frame)

    @staticmethod
    def _stat_card(layout: QHBoxLayout, value: str, caption: str) -> QLabel:
        card = QFrame()
        card.setObjectName("statCard")
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        card.setMinimumHeight(64)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(14, 10, 14, 10)
        cl.setSpacing(2)
        val_label = QLabel(value)
        val_label.setObjectName("statValue")
        val_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        cap_label = QLabel(caption)
        cap_label.setObjectName("statCaption")
        cap_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        cl.addWidget(val_label)
        cl.addWidget(cap_label)
        layout.addWidget(card)
        return val_label

    def refresh(self):
        report = self._trend.get_trend(days=7)
        self._chart.set_data(report.days)

        # Stats
        total = report.total_focus_seconds
        hours = total // 3600
        mins = (total % 3600) // 60
        self._stat_total.setText(
            f"{hours}h {mins}m" if hours else f"{mins}m"
        )
        self._stat_avg.setText(f"{report.avg_daily_minutes:.0f}m")
        self._stat_streak.setText(f"{report.current_streak} 天")
        rate = sum(s.completion_rate for s in report.days) / max(1, len(report.days))
        self._stat_rate.setText(f"{rate:.0%}")

        # Category breakdown
        self._clear_layout(self._cat_container)
        if not report.category_breakdown:
            empty = QLabel("还没有分类数据")
            empty.setObjectName("hint")
            self._cat_container.addWidget(empty)
        else:
            max_secs = max(c.total_focus_seconds for c in report.category_breakdown) or 1
            for cat in report.category_breakdown[:8]:
                row = QHBoxLayout()
                row.setSpacing(10)
                cat_name = QLabel(cat.category)
                cat_name.setObjectName("summaryValue")
                cat_name.setFixedWidth(80)
                row.addWidget(cat_name)

                # Progress bar
                bar_bg = QFrame()
                bar_bg.setStyleSheet(
                    f"background:{INPUT_BG};border-radius:3px;max-height:6px;"
                )
                bar_bg.setFixedHeight(8)
                bar_layout = QHBoxLayout(bar_bg)
                bar_layout.setContentsMargins(0, 0, 0, 0)
                bar_layout.setSpacing(0)
                fill = QFrame()
                pct = int((cat.total_focus_seconds / max_secs) * 100)
                fill.setFixedHeight(6)
                fill.setStyleSheet(f"background:{ACCENT};border-radius:3px;min-width:{pct}%;")
                bar_layout.addWidget(fill)
                bar_layout.addStretch()
                row.addWidget(bar_bg, 1)

                mins = cat.total_focus_seconds // 60
                time_text = f"{mins}m" if mins < 60 else f"{mins // 60}h {mins % 60}m"
                time_label = QLabel(time_text)
                time_label.setObjectName("hint")
                time_label.setFixedWidth(60)
                time_label.setAlignment(Qt.AlignmentFlag.AlignRight)
                row.addWidget(time_label)

                self._cat_container.addLayout(row)

    @staticmethod
    def _clear_layout(layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                TrendPage._clear_layout(item.layout())
