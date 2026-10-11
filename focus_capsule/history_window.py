"""History and session-result dialogs."""

from __future__ import annotations

from datetime import datetime

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from focus_capsule.dialogs import ask_confirmation
from focus_capsule.models import SessionRecord
from focus_capsule.theme import ACCENT
from focus_capsule.widgets import FocusRing

MODE_LABELS = {"Light": "轻柔", "Standard": "标准", "Deep": "深度"}


class HistoryWindow(QDialog):
    def __init__(self, history_service, parent=None):
        super().__init__(parent)
        self._history = history_service
        self.setWindowTitle("专注历史 · 专注舱")
        self.setObjectName("appWindow")
        self.setMinimumSize(760, 560)
        self.resize(920, 640)
        self._setup_ui()
        self._load_history()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(26, 24, 26, 26)
        root.setSpacing(18)

        header = QHBoxLayout()
        heading = QVBoxLayout()
        heading.setSpacing(3)
        title = QLabel("专注历史")
        title.setObjectName("pageTitle")
        subtitle = QLabel("回顾节奏，不评判某一次状态")
        subtitle.setObjectName("subtitle")
        heading.addWidget(title)
        heading.addWidget(subtitle)
        header.addLayout(heading)
        header.addStretch()
        clear_button = QPushButton("清空记录")
        clear_button.setObjectName("dangerButton")
        clear_button.clicked.connect(self._clear_history)
        header.addWidget(clear_button)
        close_button = QPushButton("完成")
        close_button.setObjectName("ghostButton")
        close_button.clicked.connect(self.accept)
        header.addWidget(close_button)
        root.addLayout(header)

        summaries = QHBoxLayout()
        summaries.setSpacing(12)
        self._session_total = self._summary_card(summaries, "0", "累计专注轮次")
        self._focus_total = self._summary_card(summaries, "0 分钟", "累计专注时间")
        self._completion_rate = self._summary_card(summaries, "0%", "完整完成率")
        root.addLayout(summaries)

        self._stack = QStackedWidget()
        empty = QFrame()
        empty.setObjectName("panel")
        empty_layout = QVBoxLayout(empty)
        empty_layout.setContentsMargins(40, 60, 40, 60)
        empty_layout.addStretch()
        empty_icon = QLabel("◌")
        empty_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_icon.setStyleSheet(f"color:{ACCENT};font-size:42px;")
        empty_title = QLabel("第一轮专注会显示在这里")
        empty_title.setObjectName("sectionTitle")
        empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_hint = QLabel("历史记录只保存在这台设备上。")
        empty_hint.setObjectName("hint")
        empty_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(empty_icon)
        empty_layout.addWidget(empty_title)
        empty_layout.addWidget(empty_hint)
        empty_layout.addStretch()
        self._stack.addWidget(empty)

        self._table = QTableWidget()
        self._table.setColumnCount(7)
        self._table.setHorizontalHeaderLabels(
            ["时间", "目标", "计划", "实际", "分心", "休息", "结果"]
        )
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setShowGrid(False)
        self._table.verticalHeader().setVisible(False)
        self._table.verticalHeader().setDefaultSectionSize(46)
        table_header = self._table.horizontalHeader()
        table_header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        table_header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for column in (2, 3, 4, 5, 6):
            table_header.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        self._stack.addWidget(self._table)
        root.addWidget(self._stack, 1)

    @staticmethod
    def _summary_card(layout: QHBoxLayout, value: str, caption: str) -> QLabel:
        card = QFrame()
        card.setObjectName("statCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 14, 18, 14)
        card_layout.setSpacing(3)
        value_label = QLabel(value)
        value_label.setObjectName("statValue")
        value_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        caption_label = QLabel(caption)
        caption_label.setObjectName("statCaption")
        card_layout.addWidget(value_label)
        card_layout.addWidget(caption_label)
        layout.addWidget(card, 1)
        return value_label

    def _load_history(self):
        records = self._history.load_history()
        self._session_total.setText(str(len(records)))
        total_seconds = sum(max(0, r.actual_focus_seconds) for r in records)
        if total_seconds >= 3600:
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            self._focus_total.setText(f"{hours} 小时 {minutes} 分")
        else:
            self._focus_total.setText(f"{total_seconds // 60} 分钟")
        completed = sum(1 for r in records if getattr(r, "outcome", "completed") == "completed")
        self._completion_rate.setText(f"{int(completed / len(records) * 100) if records else 0}%")

        if not records:
            self._table.setRowCount(0)
            self._stack.setCurrentIndex(0)
            return

        self._stack.setCurrentIndex(1)
        self._table.setRowCount(len(records))
        # Iterate in reverse to show most recent sessions first
        for row, record in enumerate(reversed(records)):
            try:
                started = datetime.fromisoformat(record.started_at)
                started_text = started.strftime("%m月%d日 %H:%M")
            except (TypeError, ValueError):
                started_text = "时间未知"
            goal = (getattr(record, "goal", "") or "未填写目标").strip()
            actual_minutes, actual_seconds = divmod(max(0, record.actual_focus_seconds), 60)
            outcome = getattr(record, "outcome", "completed")
            values = [
                started_text,
                goal,
                f"{record.duration_minutes} 分",
                f"{actual_minutes}:{actual_seconds:02d}",
                str(record.distraction_count),
                str(record.esc_used),
                "已完成" if outcome == "completed" else "提前结束",
            ]
            for column, text in enumerate(values):
                item = QTableWidgetItem(text)
                item.setToolTip(text)
                if column == 6:
                    item.setForeground(
                        QColor("#8BD6A8" if outcome == "completed" else "#F0A0A0")
                    )
                elif column in (4, 5):
                    item.setForeground(QColor("#9AA8BA"))
                self._table.setItem(row, column, item)

    def _clear_history(self):
        if self._table.rowCount() == 0:
            return
        confirmed = ask_confirmation(
            self,
            "清空全部历史记录？",
            "此操作无法撤销，但不会影响当前设置。",
            confirm_text="清空记录",
            cancel_text="保留记录",
            destructive=True,
        )
        if confirmed:
            self._history.clear_history()
            self._load_history()


class CompletionWindow(QDialog):
    def __init__(self, record: SessionRecord, parent=None):
        super().__init__(parent)
        self._record = record
        self.setWindowTitle("本轮结果 · 专注舱")
        self.setObjectName("appWindow")
        self.setModal(True)
        self.setMinimumSize(480, 560)
        self.resize(500, 600)
        self._setup_ui()
        self._center_window()

    def _setup_ui(self):
        outcome = getattr(self._record, "outcome", "completed")
        completed = outcome == "completed"
        # Defend against a zero/missing planned duration: fall back to 0% to
        # avoid a division-by-zero rather than surfacing a misleading 100%.
        planned_seconds = max(0, self._record.duration_minutes * 60)
        # Cap progress at 100% so records that ran over their planned duration
        # still render as a fully filled bar rather than overflowing the meter.
        progress = (
            min(100, int(self._record.actual_focus_seconds / planned_seconds * 100))
            if planned_seconds
            else 0
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(30, 28, 30, 28)
        root.setSpacing(14)

        badge = QLabel("完整完成" if completed else "已保存当前进度")
        badge.setObjectName("statusBadge" if completed else "breakBadge")
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(badge, 0, Qt.AlignmentFlag.AlignCenter)

        title = QLabel("这一轮，完成了" if completed else "这一轮先到这里")
        title.setObjectName("pageTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(title)
        goal = (getattr(self._record, "goal", "") or "专注本身就是一次明确的选择").strip()
        subtitle = QLabel(goal)
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setWordWrap(True)
        root.addWidget(subtitle)

        ring = FocusRing()
        ring.setFixedSize(230, 230)
        ring.set_progress(progress)
        ring.set_center_text(f"{progress}%")
        ring.set_caption("计划完成度")
        ring.set_state("complete" if completed else "stopped")
        root.addWidget(ring, 1, Qt.AlignmentFlag.AlignCenter)

        details = QFrame()
        details.setObjectName("softPanel")
        details_layout = QVBoxLayout(details)
        details_layout.setContentsMargins(16, 12, 16, 12)
        details_layout.setSpacing(8)
        focus_minutes, focus_seconds = divmod(max(0, self._record.actual_focus_seconds), 60)
        rows = [
            ("实际专注", f"{focus_minutes} 分 {focus_seconds} 秒"),
            ("分心提醒", f"{self._record.distraction_count} 次"),
            ("临时离开", f"{self._record.esc_used} 次"),
            ("保护强度", MODE_LABELS.get(self._record.mode, self._record.mode)),
        ]
        for key, value in rows:
            row = QHBoxLayout()
            key_label = QLabel(key)
            key_label.setObjectName("summaryKey")
            value_label = QLabel(value)
            value_label.setObjectName("summaryValue")
            row.addWidget(key_label)
            row.addStretch()
            row.addWidget(value_label)
            details_layout.addLayout(row)
        root.addWidget(details)

        done = QPushButton("返回首页")
        done.setObjectName("primaryButton")
        done.clicked.connect(self.accept)
        root.addWidget(done)

    def _center_window(self):
        screen = QApplication.primaryScreen()
        if not screen:
            return
        frame = self.frameGeometry()
        frame.moveCenter(screen.availableGeometry().center())
        self.move(frame.topLeft())
