"""Distraction reminder and intentional-break windows."""

from __future__ import annotations

from typing import Callable, Optional

from PyQt6.QtCore import QObject, Qt, QTimer
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import QApplication, QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget


class OverlayService(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._overlay_window: OverlayWindow | None = None
        self._break_window: BreakWindow | None = None

    @staticmethod
    def _alive(window) -> bool:
        if window is None:
            return False
        try:
            return window.isVisible()
        except RuntimeError:
            return False

    def show_overlay(self, app_name: str, return_seconds: int = 3):
        if self._alive(self._overlay_window):
            return
        window = OverlayWindow(
            app_name,
            return_seconds,
            lock_until_switch=return_seconds >= 5,
        )
        self._overlay_window = window
        window.destroyed.connect(lambda: self._clear_overlay(window))
        window.show()
        window.raise_()
        window.activateWindow()

    def _clear_overlay(self, window):
        if self._overlay_window is window:
            self._overlay_window = None

    def hide_overlay(self):
        window, self._overlay_window = self._overlay_window, None
        if self._alive(window):
            window.allow_close()
            window.close()

    def show_break_window(
        self,
        max_minutes: int,
        on_tick: Optional[Callable[[int], None]] = None,
        on_end: Optional[Callable[[], None]] = None,
    ):
        self.hide_break_window()
        window = BreakWindow(max_minutes, on_tick, on_end)
        self._break_window = window
        window.destroyed.connect(lambda: self._clear_break(window))
        window.show()
        window.raise_()

    def _clear_break(self, window):
        if self._break_window is window:
            self._break_window = None

    def hide_break_window(self):
        window, self._break_window = self._break_window, None
        if self._alive(window):
            window.cancel()
            window.close()


class OverlayWindow(QWidget):
    def __init__(
        self,
        app_name: str,
        return_seconds: int = 3,
        lock_until_switch: bool = False,
        parent=None,
    ):
        super().__init__(parent)
        self._allow_close = False
        self._seconds_left = max(1, return_seconds)
        self._lock_until_switch = lock_until_switch
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        screen = QApplication.primaryScreen()
        if screen:
            self.setGeometry(screen.virtualGeometry())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.addStretch()

        center = QFrame()
        center.setFixedWidth(520)
        center.setStyleSheet(
            "QFrame{background:#101B2A;border:1px solid #2C3F5C;border-radius:22px;}"
        )
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(44, 38, 44, 38)
        center_layout.setSpacing(12)

        marker = QLabel("◉")
        marker.setAlignment(Qt.AlignmentFlag.AlignCenter)
        marker.setStyleSheet("color:#67CFBB;font-size:28px;")
        title = QLabel("这不在本轮专注计划中")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color:#F5F7FA;font-size:24px;font-weight:700;")
        friendly = self._friendly_app_name(app_name)
        subtitle = QLabel(f"请切回 {friendly}，继续刚才的目标")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color:#A4B1C2;font-size:14px;")
        self._countdown = QLabel()
        self._countdown.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._countdown.setStyleSheet("color:#718198;font-size:12px;")
        hint = QLabel("使用 Alt+Tab / ⌘+Tab 切换应用")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setStyleSheet("color:#617086;font-size:11px;")

        center_layout.addWidget(marker)
        center_layout.addWidget(title)
        center_layout.addWidget(subtitle)
        center_layout.addWidget(self._countdown)
        center_layout.addWidget(hint)
        layout.addWidget(center, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addStretch()

        self._update_countdown()
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._on_tick)
        self._timer.start()

    @staticmethod
    def _friendly_app_name(name: str) -> str:
        cleaned = name.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
        return cleaned[:-4] if cleaned.lower().endswith(".exe") else cleaned

    def _update_countdown(self):
        if self._seconds_left > 0:
            self._countdown.setText(f"提醒将在 {self._seconds_left} 秒后结束")
        elif self._lock_until_switch:
            self._countdown.setText("深度模式会保持拦截，直到你切回允许的应用")

    def _on_tick(self):
        self._seconds_left = max(0, self._seconds_left - 1)
        self._update_countdown()
        if self._seconds_left == 0:
            self._timer.stop()
            if not self._lock_until_switch:
                self.allow_close()
                self.close()

    def allow_close(self):
        self._allow_close = True

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(5, 9, 15, 232))

    def closeEvent(self, event):
        if not self._allow_close:
            event.ignore()
            return
        self._timer.stop()
        event.accept()


class BreakWindow(QWidget):
    def __init__(
        self,
        max_minutes: int,
        on_tick: Optional[Callable[[int], None]] = None,
        on_end: Optional[Callable[[], None]] = None,
        parent=None,
    ):
        super().__init__(parent)
        self._on_tick_callback = on_tick
        self._on_end_callback = on_end
        self._remaining = max(1, max_minutes * 60)
        self._finished = False
        self._cancelled = False
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setFixedSize(286, 84)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        screen = QApplication.primaryScreen()
        if screen:
            area = screen.availableGeometry()
            self.move(area.right() - self.width() - 18, area.top() + 18)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 12, 18, 12)
        layout.setSpacing(12)
        mark = QLabel("Ⅱ")
        mark.setFixedSize(36, 36)
        mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mark.setStyleSheet(
            "background:#3B2D1D;color:#F0C98F;border:1px solid #5A4529;"
            "border-radius:10px;font-size:14px;font-weight:700;"
        )
        labels = QVBoxLayout()
        labels.setSpacing(1)
        title = QLabel("临时离开")
        title.setStyleSheet("color:#E8EDF3;font-size:12px;font-weight:650;")
        self._timer_label = QLabel()
        self._timer_label.setStyleSheet("color:#F0C98F;font-size:18px;font-weight:700;")
        labels.addWidget(title)
        labels.addWidget(self._timer_label)
        layout.addWidget(mark)
        layout.addLayout(labels)
        layout.addStretch()
        self._refresh_label()

        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    def _refresh_label(self):
        minutes, seconds = divmod(max(0, self._remaining), 60)
        self._timer_label.setText(f"{minutes:02d}:{seconds:02d}")

    def _tick(self):
        if self._finished or self._cancelled:
            return
        self._remaining = max(0, self._remaining - 1)
        self._refresh_label()
        if self._on_tick_callback:
            self._on_tick_callback(self._remaining)
        if self._remaining == 0:
            self._finished = True
            self._timer.stop()
            if self._on_end_callback:
                self._on_end_callback()
            self.close()

    def cancel(self):
        self._cancelled = True
        self._timer.stop()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(16, 27, 42, 244))
        painter.setPen(QColor("#3C4D67"))
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 16, 16)

    def closeEvent(self, event):
        self._timer.stop()
        event.accept()

