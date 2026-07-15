"""Distraction reminder and intentional-break windows."""

from __future__ import annotations

from typing import Callable, Optional

from PyQt6.QtCore import QObject, Qt, QTimer
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import QApplication, QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from focus_capsule.theme import (
    ACCENT, SURFACE_1, BORDER_NORMAL, TEXT_PRIMARY, TEXT_SECONDARY,
    TEXT_TERTIARY, TEXT_DISABLED, FONT_PAGE_TITLE, FONT_SECTION,
    FONT_BODY, FONT_AUX, FONT_META, WEIGHT_TITLE, RADIUS_XL,
    BREAK_BG, BREAK_ACCENT, BREAK_LIGHT, WARNING,
)

HAS_WIN32_POLL = False
try:
    import win32gui
    import win32process
    HAS_WIN32_POLL = True
except ImportError:
    pass


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

    def show_overlay(self, app_name: str, return_seconds: int = 3, allowed_apps: list[str] | None = None):
        if self._alive(self._overlay_window):
            return
        window = OverlayWindow(
            app_name,
            return_seconds,
            lock_until_switch=return_seconds >= 5,
            allowed_apps=allowed_apps,
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
        allowed_apps: list[str] | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self._allow_close = False
        self._seconds_left = max(1, return_seconds)
        self._lock_until_switch = lock_until_switch
        self._allowed_apps = {a.strip().casefold() for a in (allowed_apps or [])}
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
            f"QFrame{{background:{SURFACE_1};border:1px solid {BORDER_NORMAL};border-radius:{RADIUS_XL}px;}}"
        )
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(44, 38, 44, 38)
        center_layout.setSpacing(12)

        marker = QLabel("◉")
        marker.setAlignment(Qt.AlignmentFlag.AlignCenter)
        marker.setStyleSheet(f"color:{ACCENT};font-size:28px;")
        title = QLabel("这不在本轮专注计划中")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"color:{TEXT_PRIMARY};font-size:{FONT_PAGE_TITLE}px;font-weight:{WEIGHT_TITLE};")
        friendly = self._friendly_app_name(app_name)
        subtitle = QLabel(f"请切回 {friendly}，继续刚才的目标")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(f"color:{TEXT_SECONDARY};font-size:{FONT_SECTION}px;")
        self._countdown = QLabel()
        self._countdown.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._countdown.setStyleSheet(f"color:{TEXT_TERTIARY};font-size:{FONT_BODY}px;")
        hint = QLabel("使用 Alt+Tab / ⌘+Tab 切换应用")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setStyleSheet(f"color:{TEXT_DISABLED};font-size:{FONT_AUX}px;")

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

        # When lock_until_switch is active (Deep mode), poll the foreground
        # window every second so the overlay can detect when the user switches
        # back to an allowed app and dismiss itself.
        if self._lock_until_switch and self._allowed_apps:
            self._poll_timer = QTimer(self)
            self._poll_timer.setInterval(800)
            self._poll_timer.timeout.connect(self._poll_foreground)
            self._poll_timer.start()
        else:
            self._poll_timer = None

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

    def _poll_foreground(self):
        """Check whether the user has switched back to an allowed app."""
        try:
            import psutil
            import os
            if HAS_WIN32_POLL:
                hwnd = win32gui.GetForegroundWindow()
                if not hwnd:
                    return
                # Skip our own overlay window
                if hwnd == int(self.winId()):
                    return
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                if not pid or pid == os.getpid():
                    return
                process_name = psutil.Process(pid).name().strip().casefold()
                if process_name in self._allowed_apps:
                    self._poll_timer.stop()
                    self.allow_close()
                    self.close()
        except Exception:
            pass

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
            f"background:{BREAK_BG};color:{BREAK_ACCENT};border:1px solid {WARNING};"
            f"border-radius:10px;font-size:14px;font-weight:700;"
        )
        labels = QVBoxLayout()
        labels.setSpacing(1)
        title = QLabel("临时离开")
        title.setStyleSheet(f"color:{TEXT_PRIMARY};font-size:12px;font-weight:650;")
        self._timer_label = QLabel()
        self._timer_label.setStyleSheet(f"color:{BREAK_ACCENT};font-size:18px;font-weight:700;")
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

