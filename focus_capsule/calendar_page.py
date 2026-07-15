"""Calendar page — monthly heatmap of focus activity.

Renders a real calendar grid for the current CST month, colour-coding
each cell by how much focus time was accumulated that day.
"""

from __future__ import annotations

import calendar as _cal
from datetime import date, timedelta

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPen, QFont
from PyQt6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton,
    QSizePolicy, QVBoxLayout, QWidget,
)

from focus_capsule.data_models import china_today
from focus_capsule.trend_service import DaySummary
from focus_capsule.theme import (
    INPUT_BG, SURFACE_2, SURFACE_3,
    ACCENT, ACCENT_TEXT,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_TERTIARY, TEXT_DISABLED,
    BORDER_SUBTLE, RADIUS_MD,
    FONT_PAGE_TITLE, FONT_AUX, FONT_META,
    WEIGHT_TITLE, WEIGHT_SECTION,
)


WEEKDAY_LABELS = ["一", "二", "三", "四", "五", "六", "日"]


class CalendarCell(QFrame):
    """A single day cell in the calendar grid."""

    clicked_date = pyqtSignal(date)

    def __init__(self, cell_date: date, parent=None):
        super().__init__(parent)
        self._date = cell_date
        self._focus_minutes = 0
        self._session_count = 0
        self._is_today = False
        self._in_month = True
        self._hovered = False
        self.setMinimumSize(100, 76)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMouseTracking(True)

    @property
    def cell_date(self) -> date:
        return self._date

    def set_data(self, minutes: int, sessions: int, in_month: bool, is_today: bool):
        self._focus_minutes = minutes
        self._session_count = sessions
        self._in_month = in_month
        self._is_today = is_today
        self.update()

    def enterEvent(self, event):
        self._hovered = True
        self.update()

    def leaveEvent(self, event):
        self._hovered = False
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked_date.emit(self._date)

    def _bg_color(self) -> str:
        if self._is_today:
            return "#163a36"
        if not self._in_month:
            return INPUT_BG
        if self._focus_minutes >= 180:
            return "#1a473e"
        if self._focus_minutes >= 90:
            return "#133329"
        if self._focus_minutes > 0:
            return "#0f2620"
        return SURFACE_2

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        bg = self._bg_color()
        if self._hovered:
            bg = SURFACE_3
        p.setBrush(QColor(bg))
        border_color = QColor(ACCENT) if self._is_today else QColor(BORDER_SUBTLE)
        p.setPen(QPen(border_color, 2 if self._is_today else 1))
        p.drawRoundedRect(1, 1, w - 2, h - 2, 8, 8)

        # Day number
        p.setPen(QColor(TEXT_PRIMARY if self._in_month else TEXT_DISABLED))
        f = QFont(p.font())
        f.setPointSize(12)
        f.setWeight(QFont.Weight.DemiBold)
        p.setFont(f)
        p.drawText(8, 2, w - 16, 22,
                   Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
                   str(self._date.day))

        # Focus time + sessions
        if self._focus_minutes > 0 and self._in_month:
            if self._focus_minutes >= 60:
                hours = self._focus_minutes // 60
                mins = self._focus_minutes % 60
                time_text = f"{hours}h {mins}m" if mins else f"{hours}h"
            else:
                time_text = f"{self._focus_minutes}m"
            p.setPen(QColor(ACCENT_TEXT))
            f2 = QFont(p.font())
            f2.setPointSize(10)
            f2.setWeight(QFont.Weight.Medium)
            p.setFont(f2)
            p.drawText(8, h - 26, w - 16, 18,
                       Qt.AlignmentFlag.AlignLeft, time_text)
            p.setPen(QColor(TEXT_TERTIARY))
            f3 = QFont(p.font())
            f3.setPointSize(9)
            p.setFont(f3)
            p.drawText(8, h - 14, w - 16, 12,
                       Qt.AlignmentFlag.AlignLeft,
                       f"{self._session_count} 轮")


class CalendarPage(QWidget):
    """Monthly calendar heatmap of focus activity."""

    day_selected = pyqtSignal(date)

    def __init__(self, trend_service, parent=None):
        super().__init__(parent)
        self._trend = trend_service
        today = china_today()
        self._view_year = today.year
        self._view_month = today.month
        self._day_summaries: dict[date, DaySummary] = {}
        self._setup_ui()
        self.refresh()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        # Header row
        header = QHBoxLayout()
        header.setSpacing(12)
        title = QLabel("日历")
        title.setObjectName("pageTitle")
        header.addWidget(title)
        header.addStretch()

        self._month_label = QLabel()
        self._month_label.setObjectName("sectionTitle")
        header.addWidget(self._month_label)

        prev_btn = QPushButton("‹")
        prev_btn.setFixedSize(32, 32)
        prev_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        prev_btn.setToolTip("上个月")
        prev_btn.clicked.connect(self._prev_month)
        header.addWidget(prev_btn)

        today_btn = QPushButton("今天")
        today_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        today_btn.clicked.connect(self._go_today)
        header.addWidget(today_btn)

        next_btn = QPushButton("›")
        next_btn.setFixedSize(32, 32)
        next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        next_btn.setToolTip("下个月")
        next_btn.clicked.connect(self._next_month)
        header.addWidget(next_btn)
        layout.addLayout(header)

        subtitle = QLabel("每日专注时间一览 · 颜色越深代表当天专注时间越长")
        subtitle.setObjectName("subtitle")
        layout.addWidget(subtitle)

        # Weekday header row
        weekday_row = QHBoxLayout()
        weekday_row.setSpacing(6)
        for label in WEEKDAY_LABELS:
            lbl = QLabel(label)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(
                f"color:{TEXT_TERTIARY};font-size:{FONT_AUX}px;"
                f"font-weight:600;padding:4px 0;"
            )
            weekday_row.addWidget(lbl, 1)
        layout.addLayout(weekday_row)

        # Calendar grid container
        self._grid_frame = QFrame()
        self._grid_frame.setObjectName("panel")
        self._grid_layout = QVBoxLayout(self._grid_frame)
        self._grid_layout.setContentsMargins(10, 10, 10, 10)
        self._grid_layout.setSpacing(6)
        self._grid = QGridLayout()
        self._grid.setSpacing(6)
        self._grid_layout.addLayout(self._grid)
        layout.addWidget(self._grid_frame, 1)

        # Legend
        legend = QHBoxLayout()
        legend.addStretch()
        legend_label_lo = QLabel("少")
        legend_label_lo.setStyleSheet(f"color:{TEXT_TERTIARY};font-size:{FONT_META}px;")
        legend.addWidget(legend_label_lo)
        for i in range(5):
            bar = QFrame()
            bar.setFixedSize(14, 10)
            if i >= 3:
                color = "#1a473e"
            elif i >= 2:
                color = "#133329"
            elif i >= 1:
                color = "#0f2620"
            else:
                color = SURFACE_2
            bar.setStyleSheet(f"background:{color};border-radius:2px;border:1px solid {BORDER_SUBTLE};")
            legend.addWidget(bar)
        legend_label_hi = QLabel("多")
        legend_label_hi.setStyleSheet(f"color:{TEXT_TERTIARY};font-size:{FONT_META}px;")
        legend.addWidget(legend_label_hi)
        legend.addStretch()
        layout.addLayout(legend)

    def refresh(self):
        """Reload data and rebuild the grid."""
        summaries = self._trend.get_day_summaries(days=31)
        self._day_summaries = {s.date: s for s in summaries}

        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._month_label.setText(f"{self._view_year} 年 {self._view_month} 月")

        today = china_today()
        month_days = _cal.monthcalendar(self._view_year, self._view_month)
        # monthcalendar returns weeks where Monday=0..Sunday=6 (we use Mon start)

        for row_idx, week in enumerate(month_days):
            for col_idx, day_num in enumerate(week):
                if day_num == 0:
                    # Day belongs to adjacent month
                    in_month = False
                    if row_idx == 0:
                        # Previous month
                        prev_m = self._view_month - 1
                        prev_y = self._view_year
                        if prev_m < 1:
                            prev_m = 12
                            prev_y -= 1
                        prev_days = _cal.monthcalendar(prev_y, prev_m)
                        day_num = prev_days[-1][col_idx] if col_idx < len(prev_days[-1]) else 1
                        cell_date = date(prev_y, prev_m, day_num)
                    else:
                        # Next month
                        next_m = self._view_month + 1
                        next_y = self._view_year
                        if next_m > 12:
                            next_m = 1
                            next_y += 1
                        next_days = _cal.monthcalendar(next_y, next_m)
                        day_num = next_days[0][col_idx] if col_idx < len(next_days[0]) else 1
                        cell_date = date(next_y, next_m, day_num)
                else:
                    cell_date = date(self._view_year, self._view_month, day_num)
                    in_month = True

                summary = self._day_summaries.get(cell_date)
                minutes = summary.focus_minutes if summary else 0
                sessions = summary.session_count if summary else 0
                is_today = cell_date == today

                cell = CalendarCell(cell_date)
                cell.set_data(minutes, sessions, in_month, is_today)
                cell.clicked_date.connect(self._on_day_clicked)
                self._grid.addWidget(cell, row_idx, col_idx)
                self._grid.setColumnStretch(col_idx, 1)

    def _prev_month(self):
        self._view_month -= 1
        if self._view_month < 1:
            self._view_month = 12
            self._view_year -= 1
        self.refresh()

    def _next_month(self):
        self._view_month += 1
        if self._view_month > 12:
            self._view_month = 1
            self._view_year += 1
        self.refresh()

    def _go_today(self):
        today = china_today()
        self._view_year = today.year
        self._view_month = today.month
        self.refresh()

    def _on_day_clicked(self, clicked_date: date):
        self.day_selected.emit(clicked_date)
