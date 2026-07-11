"""Focused, always-available session dashboard."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCloseEvent, QCursor, QKeyEvent
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from focus_capsule.controller import SessionUpdate
from focus_capsule.models import FocusConfig, SessionStatus
from focus_capsule.widgets import FocusRing


MODE_LABELS = {
    "Light": "轻柔",
    "Standard": "标准",
    "Deep": "深度",
}


class SessionViewWindow(QWidget):
    break_requested = pyqtSignal()
    end_requested = pyqtSignal()
    hide_requested = pyqtSignal()

    def __init__(self, config: FocusConfig, parent=None):
        super().__init__(parent)
        self._config = config
        self._allow_close = False
        self.setObjectName("appWindow")
        self.setWindowTitle("专注进行中 · 专注舱")
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)
        self.setMinimumSize(500, 610)
        self.resize(560, 680)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._setup_ui()
        self._center_window()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 24)
        root.setSpacing(16)

        top = QHBoxLayout()
        self._status_label = QLabel("专注进行中")
        self._status_label.setObjectName("statusBadge")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_label.setAccessibleName("当前状态：专注进行中")
        top.addWidget(self._status_label)
        top.addStretch()
        hide_button = QPushButton("隐藏到托盘")
        hide_button.setObjectName("ghostButton")
        hide_button.setToolTip("计时和保护仍会继续")
        hide_button.clicked.connect(self.hide_requested)
        top.addWidget(hide_button)
        root.addLayout(top)

        goal = (getattr(self._config, "goal", "") or "").strip()
        self._goal_label = QLabel(goal or "保持在允许的应用中，完成这一轮专注")
        self._goal_label.setObjectName("pageTitle")
        self._goal_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._goal_label.setWordWrap(True)
        self._goal_label.setMaximumHeight(74)
        root.addWidget(self._goal_label)

        self._ring = FocusRing()
        self._ring.setMinimumSize(270, 270)
        self._ring.setMaximumSize(310, 310)
        self._ring.set_progress(0)
        self._ring.set_center_text(f"{self._config.duration_minutes:02d}:00")
        self._ring.set_caption("剩余时间")
        self._ring.set_state("running")
        root.addWidget(self._ring, 1, Qt.AlignmentFlag.AlignCenter)

        self._progress = QProgressBar()
        self._progress.setRange(0, 1000)
        self._progress.setValue(0)
        self._progress.setTextVisible(False)
        root.addWidget(self._progress)

        self._elapsed_label = QLabel("已专注 00:00")
        self._elapsed_label.setObjectName("hint")
        self._elapsed_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self._elapsed_label)

        stats = QHBoxLayout()
        stats.setSpacing(10)
        self._distraction_value = self._stat_card(stats, "0", "分心次数")
        self._escape_value = self._stat_card(
            stats,
            str(self._config.max_esc),
            "可休息次数",
        )
        self._mode_value = self._stat_card(
            stats,
            MODE_LABELS.get(self._config.mode, self._config.mode),
            "保护强度",
        )
        root.addLayout(stats)

        self._break_panel = QFrame()
        self._break_panel.setObjectName("breakPanel")
        break_layout = QHBoxLayout(self._break_panel)
        break_layout.setContentsMargins(14, 10, 14, 10)
        break_title = QLabel("正在临时离开")
        break_title.setStyleSheet("color:#F0C98F;font-weight:650;")
        self._break_timer = QLabel("03:00 后自动继续")
        self._break_timer.setStyleSheet("color:#F5D9AF;font-weight:700;")
        self._break_timer.setAlignment(Qt.AlignmentFlag.AlignRight)
        break_layout.addWidget(break_title)
        break_layout.addStretch()
        break_layout.addWidget(self._break_timer)
        self._break_panel.hide()
        root.addWidget(self._break_panel)

        controls = QHBoxLayout()
        controls.setSpacing(10)
        self._break_button = QPushButton(f"临时离开（余 {self._config.max_esc} 次）")
        self._break_button.setAccessibleName("开始一次临时休息")
        self._break_button.setToolTip("也可以按 Esc")
        self._break_button.clicked.connect(self.break_requested)
        self._break_button.setEnabled(self._config.max_esc > 0)
        controls.addWidget(self._break_button, 1)

        end_button = QPushButton("提前结束")
        end_button.setObjectName("dangerButton")
        end_button.setAccessibleName("提前结束本次专注")
        end_button.clicked.connect(self.end_requested)
        controls.addWidget(end_button)
        root.addLayout(controls)

        allowed = ", ".join(self._friendly_app_name(app) for app in self._config.whitelist[:4])
        if len(self._config.whitelist) > 4:
            allowed += f" 等 {len(self._config.whitelist)} 个应用"
        allowed_label = QLabel(f"本轮允许：{allowed}")
        allowed_label.setObjectName("tinyMuted")
        allowed_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        allowed_label.setWordWrap(True)
        root.addWidget(allowed_label)

    @staticmethod
    def _stat_card(layout: QHBoxLayout, value: str, caption: str) -> QLabel:
        card = QFrame()
        card.setObjectName("statCard")
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        card.setMinimumHeight(76)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(10, 9, 10, 9)
        card_layout.setSpacing(2)
        value_label = QLabel(value)
        value_label.setObjectName("summaryValue")
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        caption_label = QLabel(caption)
        caption_label.setObjectName("statCaption")
        caption_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(value_label)
        card_layout.addWidget(caption_label)
        layout.addWidget(card)
        return value_label

    @staticmethod
    def _friendly_app_name(name: str) -> str:
        cleaned = name.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
        return cleaned[:-4] if cleaned.lower().endswith(".exe") else cleaned

    def update_from_session(self, update: SessionUpdate):
        remaining = max(0, update.total - update.elapsed)
        minutes, seconds = divmod(remaining, 60)
        elapsed_minutes, elapsed_seconds = divmod(max(0, update.elapsed), 60)
        progress = (update.elapsed / update.total * 100.0) if update.total else 0.0

        self._ring.set_progress(progress)
        self._ring.set_center_text(f"{minutes:02d}:{seconds:02d}")
        self._progress.setValue(int(progress * 10))
        self._elapsed_label.setText(f"已专注 {elapsed_minutes:02d}:{elapsed_seconds:02d}")
        self._distraction_value.setText(str(update.distraction_count))
        self._escape_value.setText(str(update.esc_remaining))
        self._mode_value.setText(MODE_LABELS.get(update.mode, update.mode))

        if update.status == SessionStatus.BREAK:
            self._status_label.setText("临时休息")
            self._status_label.setObjectName("breakBadge")
            self._ring.set_state("break")
            self._ring.set_caption("休息结束后继续")
            break_minutes, break_seconds = divmod(max(0, update.break_remaining), 60)
            self._break_timer.setText(f"{break_minutes:02d}:{break_seconds:02d} 后自动继续")
            self._break_panel.show()
            self._break_button.setEnabled(False)
        else:
            self._status_label.setText("专注进行中")
            self._status_label.setObjectName("statusBadge")
            self._ring.set_state("running")
            self._ring.set_caption("剩余时间")
            self._break_panel.hide()
            self._break_button.setText(f"临时离开（余 {update.esc_remaining} 次）")
            self._break_button.setEnabled(update.esc_remaining > 0)

        self._status_label.style().unpolish(self._status_label)
        self._status_label.style().polish(self._status_label)
        self._status_label.setAccessibleName(f"当前状态：{self._status_label.text()}")

    def _center_window(self):
        screen = QApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
        if not screen:
            return
        frame = self.frameGeometry()
        frame.moveCenter(screen.availableGeometry().center())
        self.move(frame.topLeft())

    def finish_and_close(self):
        self._allow_close = True
        self.close()

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Escape and self._break_button.isEnabled():
            self.break_requested.emit()
            event.accept()
            return
        super().keyPressEvent(event)

    def closeEvent(self, event: QCloseEvent):
        if self._allow_close:
            event.accept()
            return
        self.hide_requested.emit()
        self.hide()
        event.ignore()

