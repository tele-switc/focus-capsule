"""Calendar with daily locks, focus records and goal progress."""

from __future__ import annotations

import calendar
from datetime import date

from PyQt6.QtCore import QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from focus_capsule import theme as T
from focus_capsule.data_models import china_today

WEEKDAY_LABELS = ["一", "二", "三", "四", "五", "六", "日"]


def _format_minutes(minutes: int) -> str:
    minutes = max(0, int(minutes))
    hours, remainder = divmod(minutes, 60)
    if hours and remainder:
        return f"{hours} 小时 {remainder} 分钟"
    if hours:
        return f"{hours} 小时"
    return f"{remainder} 分钟"


def _format_metric_minutes(minutes: int) -> str:
    """Compact duration for the width-constrained daily detail headline."""
    minutes = max(0, int(minutes))
    hours, remainder = divmod(minutes, 60)
    if hours and remainder:
        return f"{hours}小时{remainder}分钟"
    if hours:
        return f"{hours}小时"
    return f"{remainder}分钟"


class CalendarCell(QWidget):
    clicked_date = pyqtSignal(date)

    def __init__(self, cell_date: date, parent=None):
        super().__init__(parent)
        self._date = cell_date
        self._focus_minutes = 0
        self._session_count = 0
        self._goal_percent: int | None = None
        self._goal_state = "none"
        self._is_today = False
        self._is_selected = False
        self._in_month = True
        self._hovered = False
        self.setMinimumSize(82, 64)
        # 纵向也使用 Expanding：让 6 行格子均分卡片高度，避免底部大片竖向空白
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMouseTracking(True)

    @property
    def cell_date(self) -> date:
        return self._date

    def set_data(
        self,
        minutes: int,
        sessions: int,
        goal_percent: int | None,
        goal_state: str,
        in_month: bool,
        is_today: bool,
        is_selected: bool,
    ) -> None:
        self._focus_minutes = max(0, int(minutes))
        self._session_count = max(0, int(sessions))
        self._goal_percent = goal_percent
        self._goal_state = goal_state
        self._in_month = in_month
        self._is_today = is_today
        self._is_selected = is_selected
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

    def _focus_color(self) -> QColor:
        current = T.current()
        if self._focus_minutes >= 180:
            return QColor(current["CAL_PEAK"])
        if self._focus_minutes >= 90:
            return QColor(current["CAL_HIGH"])
        return QColor(current["CAL_MED"])

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        current = T.current()
        width, height = self.width(), self.height()

        if self._is_today:
            fill = QColor(current["ACCENT"])
            fill.setAlphaF(0.08)
            painter.fillRect(self.rect(), fill)
        if self._hovered and self._in_month:
            fill = QColor(current["TEXT_PRIMARY"])
            fill.setAlphaF(0.03)
            painter.fillRect(self.rect(), fill)
        if self._is_selected:
            painter.setPen(QPen(QColor(current["ACCENT"]), 1.5))
            painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 8, 8)

        text_color = (
            current["TEXT_PRIMARY"] if self._in_month else current["TEXT_DISABLED"]
        )
        if self._is_today and self._in_month:
            text_color = current["ACCENT"]
        painter.setPen(QColor(text_color))
        font = QFont(painter.font())
        font.setPointSize(11)
        font.setWeight(QFont.Weight.Medium)
        painter.setFont(font)
        painter.drawText(
            QRectF(8, 6, width - 16, 18),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
            str(self._date.day),
        )

        if self._goal_state != "none" and self._in_month:
            marker = "✓" if self._goal_state == "complete" else (
                "!" if self._goal_state == "failed" else "•"
            )
            marker_color = (
                current["SUCCESS"]
                if self._goal_state == "complete"
                else current["DANGER"]
                if self._goal_state == "failed"
                else current["ACCENT"]
            )
            painter.setPen(QColor(marker_color))
            marker_font = QFont(painter.font())
            marker_font.setPointSize(10)
            marker_font.setWeight(QFont.Weight.Bold)
            painter.setFont(marker_font)
            painter.drawText(
                QRectF(width - 26, 5, 18, 18),
                Qt.AlignmentFlag.AlignCenter,
                marker,
            )

        if self._focus_minutes > 0 and self._in_month:
            value = _format_minutes(self._focus_minutes).replace(" 小时 ", "h").replace(
                " 小时", "h"
            ).replace(" 分钟", "m")
            painter.setPen(QColor(current["TEXT_TERTIARY"]))
            small = QFont(painter.font())
            small.setPointSize(8)
            small.setWeight(QFont.Weight.Normal)
            painter.setFont(small)
            painter.drawText(
                QRectF(8, height - 34, width - 16, 13),
                Qt.AlignmentFlag.AlignLeft,
                value,
            )
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(self._focus_color())
            focus_width = min(width - 16, max(4, self._focus_minutes * 0.45))
            painter.drawRoundedRect(QRectF(8, height - 18, focus_width, 3), 1.5, 1.5)

        if self._goal_percent is not None and self._in_month:
            painter.setPen(Qt.PenStyle.NoPen)
            track = QColor(current["RING_TRACK"])
            painter.setBrush(track)
            painter.drawRoundedRect(QRectF(8, height - 9, width - 16, 3), 1.5, 1.5)
            goal_color = (
                current["DANGER"]
                if self._goal_state == "failed"
                else current["SUCCESS"]
                if self._goal_state == "complete"
                else current["ACCENT"]
            )
            painter.setBrush(QColor(goal_color))
            goal_width = (width - 16) * max(0, min(100, self._goal_percent)) / 100
            painter.drawRoundedRect(QRectF(8, height - 9, goal_width, 3), 1.5, 1.5)


class CalendarPage(QWidget):
    """Month calendar with a detailed daily inspector."""

    day_selected = pyqtSignal(date)

    def __init__(
        self,
        trend_service,
        parent=None,
        data_store=None,
        progress_service=None,
    ):
        super().__init__(parent)
        self._trend = trend_service
        self._data_store = data_store
        self._progress_service = progress_service
        today = china_today()
        self._view_year = today.year
        self._view_month = today.month
        self._selected_date: date | None = today
        self._metrics: dict[date, object] = {}
        self._goal_progress: dict[date, object] = {}
        self._cells: dict[date, CalendarCell] = {}
        self._setup_ui()
        self.refresh()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(18)

        calendar_panel = QFrame()
        calendar_panel.setObjectName("sectionCard")
        left = QVBoxLayout(calendar_panel)
        left.setContentsMargins(22, 20, 22, 18)
        left.setSpacing(14)

        header = QHBoxLayout()
        self._month_label = QLabel()
        self._month_label.setObjectName("sectionTitle")
        header.addWidget(self._month_label)
        header.addStretch()
        for text, tooltip, handler in (
            ("◀", "上个月", self._prev_month),
            ("● 今天", "回到今天", self._go_today),
            ("▶", "下个月", self._next_month),
        ):
            button = QPushButton(text)
            button.setObjectName("presetButton")
            button.setToolTip(tooltip)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(handler)
            header.addWidget(button)
        left.addLayout(header)

        # 星期表头与日期格子共用同一个 QGridLayout（第 0 行为表头），
        # 保证列宽完全一致、不再整体错位；表头在 refresh() 中重建。
        self._grid = QGridLayout()
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setSpacing(0)
        left.addLayout(self._grid, 1)

        legend = QLabel("细线：专注时长　　底部进度：当天目标　　✓ 完成　! 超出限制")
        legend.setObjectName("bodyTertiary")
        legend.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left.addWidget(legend)
        layout.addWidget(calendar_panel, 3)

        self._detail_panel = QFrame()
        self._detail_panel.setObjectName("detailPanel")
        detail_root = QVBoxLayout(self._detail_panel)
        detail_root.setContentsMargins(0, 0, 0, 0)

        detail_scroll = QScrollArea()
        detail_scroll.setWidgetResizable(True)
        detail_scroll.setFrameShape(QFrame.Shape.NoFrame)
        detail_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        detail_content = QWidget()
        detail = QVBoxLayout(detail_content)
        detail.setContentsMargins(24, 20, 24, 20)
        detail.setSpacing(11)

        eyebrow = QLabel("每日记录")
        eyebrow.setObjectName("eyebrow")
        detail.addWidget(eyebrow)
        self._detail_title = QLabel()
        self._detail_title.setObjectName("sectionTitle")
        detail.addWidget(self._detail_title)
        self._detail_subtitle = QLabel()
        self._detail_subtitle.setObjectName("bodyTertiary")
        detail.addWidget(self._detail_subtitle)

        divider = QFrame()
        divider.setObjectName("divider")
        detail.addWidget(divider)

        self._detail_focus = QLabel("0 分钟")
        self._detail_focus.setObjectName("calendarHeroMetric")
        self._detail_focus.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Preferred,
        )
        detail.addWidget(self._detail_focus)
        focus_caption = QLabel("总专注时间")
        focus_caption.setObjectName("statCaption")
        detail.addWidget(focus_caption)
        self._detail_sessions = QLabel()
        self._detail_sessions.setObjectName("body")
        detail.addWidget(self._detail_sessions)
        self._detail_interruptions = QLabel()
        self._detail_interruptions.setObjectName("body")
        detail.addWidget(self._detail_interruptions)
        self._detail_unlocks = QLabel()
        self._detail_unlocks.setObjectName("body")
        detail.addWidget(self._detail_unlocks)

        detail.addSpacing(6)
        target_title = QLabel("当天目标")
        target_title.setObjectName("sectionTitle")
        detail.addWidget(target_title)
        self._targets_layout = QVBoxLayout()
        self._targets_layout.setSpacing(7)
        detail.addLayout(self._targets_layout)

        detail.addSpacing(6)
        lock_title = QLabel("日程锁定")
        lock_title.setObjectName("sectionTitle")
        detail.addWidget(lock_title)
        self._locks_layout = QVBoxLayout()
        self._locks_layout.setSpacing(6)
        detail.addLayout(self._locks_layout)

        detail.addSpacing(6)
        usage_title = QLabel("应用使用")
        usage_title.setObjectName("sectionTitle")
        detail.addWidget(usage_title)
        self._usage_layout = QVBoxLayout()
        self._usage_layout.setSpacing(5)
        detail.addLayout(self._usage_layout)
        detail.addStretch()

        detail_scroll.setWidget(detail_content)
        detail_root.addWidget(detail_scroll)
        layout.addWidget(self._detail_panel, 2)

    @staticmethod
    def _clear_layout(layout: QVBoxLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                # deleteLater() alone leaves the old row visible until the next
                # event-loop pass. Hide it immediately so rapid refreshes never
                # paint old and new rows on top of each other.
                widget.hide()
                widget.deleteLater()
                continue
            child_layout = item.layout()
            if child_layout:
                CalendarPage._clear_layout(child_layout)
                child_layout.deleteLater()

    def _view_dates(self) -> list[date]:
        weeks = calendar.Calendar(firstweekday=0).monthdatescalendar(
            self._view_year,
            self._view_month,
        )
        return [day for week in weeks for day in week]

    def refresh(self) -> None:
        dates = self._view_dates()
        self._metrics = {}
        self._goal_progress = {}
        if self._progress_service is not None:
            self._metrics = self._progress_service.metrics_for_dates(dates)
            self._goal_progress = {
                day: self._progress_service.progress_for_date(
                    day,
                    self._metrics[day],
                )
                for day in dates
            }
        else:
            summaries = self._trend.get_day_summaries(days=400)
            self._metrics = {summary.date: summary for summary in summaries}

        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                # 立即 hide：deleteLater 要等事件循环，截图/快速刷新时
                # 旧格子会残留在旧几何位置上露出半个数字
                item.widget().hide()
                item.widget().deleteLater()
        self._cells.clear()
        self._month_label.setText(f"{self._view_year} 年 {self._view_month} 月")

        weeks = calendar.Calendar(firstweekday=0).monthdatescalendar(
            self._view_year,
            self._view_month,
        )
        # 第 0 行：星期表头，与日期格子同列同宽，左缘与格子内日期数字对齐
        self._grid.setRowStretch(0, 0)
        for column_index, text in enumerate(WEEKDAY_LABELS):
            label = QLabel(text)
            label.setObjectName("hint")
            label.setContentsMargins(8, 0, 0, 6)
            label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom)
            self._grid.addWidget(label, 0, column_index)

        today = china_today()
        for row_index, week in enumerate(weeks):
            self._grid.setRowStretch(row_index + 1, 1)
            for column_index, day in enumerate(week):
                metrics = self._metrics.get(day)
                focus_minutes = (
                    int(getattr(metrics, "total_focus_seconds", 0)) // 60
                    if metrics is not None
                    else int(getattr(metrics, "focus_minutes", 0) or 0)
                )
                sessions = int(
                    getattr(
                        metrics,
                        "session_count",
                        0,
                    )
                )
                progress = self._goal_progress.get(day)
                cell = CalendarCell(day)
                cell.set_data(
                    focus_minutes,
                    sessions,
                    getattr(progress, "percent", None),
                    str(getattr(progress, "state", "none")),
                    day.month == self._view_month,
                    day == today,
                    day == self._selected_date,
                )
                cell.clicked_date.connect(self._on_day_clicked)
                # 格子整体下移一行：第 0 行留给星期表头，保证列对齐
                self._grid.addWidget(cell, row_index + 1, column_index)
                self._grid.setColumnStretch(column_index, 1)
                self._cells[day] = cell

        if self._selected_date is None:
            self._selected_date = today
        self._update_detail(self._selected_date)

    def _prev_month(self) -> None:
        if self._view_month == 1:
            self._view_year -= 1
            self._view_month = 12
        else:
            self._view_month -= 1
        selected_day = self._selected_date.day if self._selected_date else 1
        self._selected_date = date(
            self._view_year,
            self._view_month,
            min(selected_day, calendar.monthrange(self._view_year, self._view_month)[1]),
        )
        self.refresh()

    def _next_month(self) -> None:
        if self._view_month == 12:
            self._view_year += 1
            self._view_month = 1
        else:
            self._view_month += 1
        selected_day = self._selected_date.day if self._selected_date else 1
        self._selected_date = date(
            self._view_year,
            self._view_month,
            min(selected_day, calendar.monthrange(self._view_year, self._view_month)[1]),
        )
        self.refresh()

    def _go_today(self) -> None:
        today = china_today()
        self._view_year = today.year
        self._view_month = today.month
        self._selected_date = today
        self.refresh()

    def _on_day_clicked(self, clicked_date: date) -> None:
        self._selected_date = clicked_date
        self.day_selected.emit(clicked_date)
        for day, cell in self._cells.items():
            metrics = self._metrics.get(day)
            progress = self._goal_progress.get(day)
            focus_minutes = int(getattr(metrics, "total_focus_seconds", 0)) // 60
            cell.set_data(
                focus_minutes,
                int(getattr(metrics, "session_count", 0)),
                getattr(progress, "percent", None),
                str(getattr(progress, "state", "none")),
                day.month == self._view_month,
                day == china_today(),
                day == clicked_date,
            )
        self._update_detail(clicked_date)

    def _update_detail(self, target_date: date) -> None:
        metrics = self._metrics.get(target_date)
        progress = self._goal_progress.get(target_date)
        if metrics is None and self._progress_service is not None:
            metrics = self._progress_service.metrics_for_date(target_date)
            progress = self._progress_service.progress_for_date(target_date, metrics)

        weekdays = ["一", "二", "三", "四", "五", "六", "日"]
        self._detail_title.setText(f"{target_date.month} 月 {target_date.day} 日")
        self._detail_subtitle.setText(
            f"{target_date.year} 年 · 周{weekdays[target_date.weekday()]}"
        )
        focus_seconds = max(0, int(getattr(metrics, "total_focus_seconds", 0)))
        self._detail_focus.setText(_format_metric_minutes(focus_seconds // 60))
        sessions = max(0, int(getattr(metrics, "session_count", 0)))
        completed = max(
            0,
            int(
                getattr(
                    metrics,
                    "completed_sessions",
                    getattr(metrics, "completed_count", 0),
                )
            ),
        )
        self._detail_sessions.setText(f"专注记录 {sessions} 次 · 完整完成 {completed} 次")
        distractions = max(0, int(getattr(metrics, "distraction_count", 0)))
        self._detail_interruptions.setText(f"分心 {distractions} 次")
        unlocks = max(0, int(getattr(metrics, "temporary_unlocks", 0)))
        self._detail_unlocks.setText(f"临时解锁 {unlocks} 次")

        self._clear_layout(self._targets_layout)
        items = list(getattr(progress, "items", []) or [])
        if not items:
            empty = QLabel("当天没有设置量化目标")
            empty.setObjectName("bodyTertiary")
            self._targets_layout.addWidget(empty)
        else:
            for item in items:
                row = QFrame()
                row.setObjectName("softPanel")
                row_layout = QVBoxLayout(row)
                row_layout.setContentsMargins(12, 8, 12, 8)
                row_layout.setSpacing(5)
                line = QHBoxLayout()
                name = QLabel(item.label)
                name.setObjectName("body")
                line.addWidget(name)
                line.addStretch()
                state_text = (
                    "超出限制"
                    if item.status == "exceeded"
                    else "完成"
                    if item.status == "complete"
                    else "限制内"
                    if item.status == "safe"
                    else "进行中"
                )
                value = QLabel(f"{item.value_text} · {state_text}")
                value.setObjectName("hint")
                line.addWidget(value)
                row_layout.addLayout(line)
                bar = QProgressBar()
                bar.setRange(0, 100)
                bar.setValue(item.percent)
                bar.setTextVisible(False)
                row_layout.addWidget(bar)
                self._targets_layout.addWidget(row)

        self._clear_layout(self._locks_layout)
        locks = list(getattr(metrics, "scheduled_locks", []) or [])
        if not locks:
            empty = QLabel("当天没有日程锁定记录")
            empty.setObjectName("bodyTertiary")
            self._locks_layout.addWidget(empty)
        else:
            for lock in locks:
                try:
                    start = lock.started_at[11:16]
                    end = lock.ended_at[11:16]
                except (AttributeError, TypeError):
                    start, end = "", ""
                label = QLabel(
                    f"{lock.label}　{start}–{end}　实际 {_format_minutes(lock.actual_minutes)}"
                )
                label.setObjectName("body")
                label.setWordWrap(True)
                self._locks_layout.addWidget(label)

        self._clear_layout(self._usage_layout)
        usage = dict(getattr(metrics, "app_usage_seconds", {}) or {})
        if not usage:
            empty = QLabel("当天没有应用使用记录")
            empty.setObjectName("bodyTertiary")
            self._usage_layout.addWidget(empty)
        else:
            names = getattr(
                self._data_store.get_activity(target_date.isoformat())
                if self._data_store is not None
                else None,
                "app_display_names",
                {},
            )
            for process, seconds in sorted(
                usage.items(),
                key=lambda pair: pair[1],
                reverse=True,
            )[:5]:
                row = QHBoxLayout()
                app = QLabel(names.get(process, process))
                app.setObjectName("body")
                row.addWidget(app)
                row.addStretch()
                value = QLabel(_format_minutes(seconds // 60))
                value.setObjectName("hint")
                row.addWidget(value)
                self._usage_layout.addLayout(row)
