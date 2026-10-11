"""Distraction reminder and intentional-break windows.

覆盖层借鉴 Stretchly 的出口策略：只在弹层生命周期的前 30% 提供一次「延后」，
严格模式下连延后也不给；同时接入 :mod:`focus_capsule.focus_guard`，在全屏演示、
系统专注模式、锁屏和免打扰清单命中时不弹层（照常计时，只免打断）。
"""

from __future__ import annotations

from typing import Callable, Optional

from PyQt6.QtCore import (
    QEasingCurve,
    QEvent,
    QObject,
    QPropertyAnimation,
    Qt,
    QTimer,
    pyqtSignal,
)
from PyQt6.QtGui import QColor, QKeyEvent, QPainter
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from focus_capsule import focus_guard
from focus_capsule.process_matching import ProcessMatcher
from focus_capsule.theme import (
    ACCENT,
    BORDER_NORMAL,
    BREAK_ACCENT,
    BREAK_BG,
    FONT_AUX,
    FONT_BODY,
    FONT_PAGE_TITLE,
    FONT_SECTION,
    RADIUS_LG,
    RADIUS_XL,
    SURFACE_1,
    TEXT_DISABLED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_TERTIARY,
    WARNING,
    WEIGHT_TITLE,
    hex_alpha,
)

HAS_WIN32_POLL = False
try:
    import win32gui
    import win32process

    HAS_WIN32_POLL = True
except ImportError:
    pass

# 延后策略（借鉴 Stretchly：只允许一次、且只在弹层前段可用）
SNOOZE_MINUTES = 5
SNOOZE_WINDOW_RATIO = 0.30
FADE_IN_MS = 150


class OverlayService(QObject):
    closed = pyqtSignal()
    snoozed = pyqtSignal(int)
    suppressed = pyqtSignal(str)

    def __init__(self, parent=None, exclusions=None, guard_enabled: bool = True):
        super().__init__(parent)
        self._windows: list[OverlayWindow] = []
        self._break_window: BreakWindow | None = None
        self._exclusions = exclusions
        self._guard_enabled = guard_enabled
        self._snooze_until: float = 0.0
        self._building = False

    # -- helpers ---------------------------------------------------------

    @staticmethod
    def _alive(window) -> bool:
        if window is None:
            return False
        try:
            return window.isVisible()
        except RuntimeError:
            return False

    def _clear_overlay(self, window):
        if window in self._windows:
            self._windows.remove(window)
        if not self._windows:
            self.closed.emit()

    def is_snoozing(self) -> bool:
        import time

        return time.monotonic() < self._snooze_until

    def set_guard_enabled(self, enabled: bool) -> None:
        self._guard_enabled = bool(enabled)

    @property
    def _overlay_window(self):
        """兼容旧代码/测试：返回当前第一个存活覆盖窗（多屏时为主动窗）。"""

        return self._windows[0] if self._windows else None

    def is_overlay_visible(self) -> bool:
        return any(self._alive(window) for window in self._windows)

    def set_exclusions(self, patterns) -> None:
        self._exclusions = patterns

    def snooze_remaining(self) -> int:
        import time

        return max(0, int(self._snooze_until - time.monotonic()))

    def guard_available(self) -> bool:
        """探测当前环境，返回抑制原因（空串表示可以弹）。"""

        if not self._guard_enabled:
            return ""
        state = focus_guard.probe(self._exclusions)
        if state.should_suppress:
            return state.reason_label
        return ""

    # -- distraction overlay --------------------------------------------

    def show_overlay(
        self,
        app_name: str,
        return_seconds: int = 3,
        allowed_apps: list[str] | None = None,
        allowed_app_paths: dict[str, str] | None = None,
        strict: bool = False,
        snooze_used: int = 0,
        snooze_quota: int = 2,
        on_snooze: Callable[[int], None] | None = None,
    ) -> bool:
        """弹出接管层。返回 False 表示被运行环境抑制或正在延后期。"""

        if any(self._alive(window) for window in self._windows):
            return True
        if self._building:
            # 正在建窗时收到 destroyed→closed 级联，绝不能重入再建一层
            return False
        if self.is_snoozing():
            return False
        reason = self.guard_available()
        if reason:
            self.suppressed.emit(reason)
            return False

        windows = self._build_overlays(
            title_text="这不在本轮专注计划中",
            subtitle_text=f"请切回 {OverlayWindow._friendly_app_name(app_name)}，继续刚才的目标",
            return_seconds=return_seconds,
            lock_until_switch=return_seconds >= 5,
            allowed_apps=allowed_apps,
            allowed_app_paths=allowed_app_paths,
            strict=strict,
            snooze_used=snooze_used,
            snooze_quota=snooze_quota,
            on_snooze=on_snooze,
        )
        return bool(windows)

    def show_usage_limit(
        self,
        app_name: str,
        allowed_apps: list[str] | None = None,
        allowed_app_paths: dict[str, str] | None = None,
    ) -> bool:
        """Block a daily-limited app until the user switches away from it."""

        if any(self._alive(window) for window in self._windows):
            return True
        reason = self.guard_available()
        if reason:
            self.suppressed.emit(reason)
            return False
        windows = self._build_overlays(
            title_text="今日使用额度已用完",
            subtitle_text=f"{OverlayWindow._friendly_app_name(app_name)} 已达到今天设置的上限，请切换到其他应用",
            return_seconds=5,
            lock_until_switch=True,
            allowed_apps=allowed_apps,
            allowed_app_paths=allowed_app_paths,
            blocked_apps=[app_name],
            strict=True,
        )
        return bool(windows)

    def _build_overlays(
        self,
        title_text: str,
        subtitle_text: str,
        return_seconds: int,
        lock_until_switch: bool,
        allowed_apps: list[str] | None,
        allowed_app_paths: dict[str, str] | None,
        blocked_apps: list[str] | None = None,
        strict: bool = False,
        snooze_used: int = 0,
        snooze_quota: int = 2,
        on_snooze: Callable[[int], None] | None = None,
    ) -> list["OverlayWindow"]:
        """每台显示器各开一个覆盖窗（Stretchly allScreens 行为）。"""

        created: list[OverlayWindow] = []
        self._building = True
        try:
            for screen in QApplication.screens():
                window = OverlayWindow(
                    title_text=title_text,
                    subtitle_text=subtitle_text,
                    return_seconds=return_seconds,
                    lock_until_switch=lock_until_switch,
                    allowed_apps=allowed_apps,
                    allowed_app_paths=allowed_app_paths,
                    blocked_apps=blocked_apps,
                    strict=strict,
                    snooze_used=snooze_used,
                    snooze_quota=snooze_quota,
                    geometry=screen.geometry(),
                )
                window.destroyed.connect(lambda _=None, w=window: self._clear_overlay(w))
                window.snooze_requested.connect(self._on_snooze_requested)
                if on_snooze:
                    window.snooze_requested.connect(on_snooze)
                window.snooze_requested.connect(lambda m: self.snoozed.emit(m))
                window.show()
                window.raise_()
                if not created:
                    # 只在主窗抢焦点，其余屏仅覆盖，避免多屏焦点抖动
                    window.activateWindow()
                created.append(window)
        finally:
            self._building = False
        self._windows = created
        return created

    def _on_snooze_requested(self, minutes: int) -> None:
        import time

        self._snooze_until = time.monotonic() + minutes * 60

    def hide_overlay(self):
        windows, self._windows = self._windows, []
        for window in windows:
            if self._alive(window):
                window.allow_close()
                window.close()

    # -- break window ----------------------------------------------------

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
    snooze_requested = pyqtSignal(int)

    def __init__(
        self,
        return_seconds: int = 3,
        lock_until_switch: bool = False,
        allowed_apps: list[str] | None = None,
        allowed_app_paths: dict[str, str] | None = None,
        blocked_apps: list[str] | None = None,
        title_text: str = "",
        subtitle_text: str = "",
        strict: bool = False,
        snooze_used: int = 0,
        snooze_quota: int = 2,
        geometry=None,
        parent=None,
    ):
        super().__init__(parent)
        self._allow_close = False
        self._seconds_total = max(1, return_seconds)
        self._seconds_left = self._seconds_total
        self._lock_until_switch = lock_until_switch
        self._strict = strict
        self._snooze_used = snooze_used
        self._snooze_quota = snooze_quota
        self._process_matcher = ProcessMatcher(allowed_apps or [], allowed_app_paths or {})
        self._blocked_processes = {
            str(process).strip().casefold()
            for process in (blocked_apps or [])
            if str(process).strip()
        }
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        if geometry is not None:
            self.setGeometry(geometry)
        else:
            screen = QApplication.primaryScreen()
            if screen:
                self.setGeometry(screen.geometry())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.addStretch()

        center = QFrame()
        center.setFixedWidth(540)
        center.setStyleSheet(
            f"QFrame{{background:{SURFACE_1};border:1px solid {BORDER_NORMAL};"
            f"border-radius:{RADIUS_XL}px;}}"
        )
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(44, 38, 44, 38)
        center_layout.setSpacing(12)

        marker = QLabel("◉")
        marker.setAlignment(Qt.AlignmentFlag.AlignCenter)
        marker.setStyleSheet(f"color:{ACCENT};font-size:26px;")
        title = QLabel(title_text or "这不在本轮专注计划中")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(
            f"color:{TEXT_PRIMARY};font-size:{FONT_PAGE_TITLE}px;font-weight:{WEIGHT_TITLE};"
        )
        subtitle = QLabel(subtitle_text)
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(f"color:{TEXT_SECONDARY};font-size:{FONT_SECTION}px;")
        self._countdown = QLabel()
        self._countdown.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._countdown.setStyleSheet(f"color:{TEXT_TERTIARY};font-size:{FONT_BODY}px;")

        center_layout.addWidget(marker)
        center_layout.addWidget(title)
        center_layout.addWidget(subtitle)
        center_layout.addWidget(self._countdown)

        # 出口按钮：Enter 返回专注，Esc 延后（严格模式两者都不给）
        actions = QHBoxLayout()
        actions.setSpacing(10)
        actions.addStretch()
        self._snooze_btn = None
        if self._can_snooze():
            self._snooze_btn = QPushButton(f"延后 {SNOOZE_MINUTES} 分钟")
            self._snooze_btn.setObjectName("overlayGhostButton")
            self._snooze_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self._snooze_btn.setStyleSheet(self._ghost_style())
            self._snooze_btn.clicked.connect(self._request_snooze)
            actions.addWidget(self._snooze_btn)
        back = QPushButton("返回专注")
        back.setObjectName("overlayPrimaryButton")
        back.setCursor(Qt.CursorShape.PointingHandCursor)
        back.setStyleSheet(self._primary_style())
        back.setDefault(True)
        back.clicked.connect(self._return_to_focus)
        actions.addWidget(back)
        actions.addStretch()
        center_layout.addSpacing(6)
        center_layout.addLayout(actions)

        hint = QLabel(self._hint_text())
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setStyleSheet(f"color:{TEXT_DISABLED};font-size:{FONT_AUX}px;")
        center_layout.addWidget(hint)

        layout.addWidget(center, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addStretch()

        self._update_countdown()
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._on_tick)
        self._timer.start()

        if self._lock_until_switch and ((allowed_apps or []) or self._blocked_processes):
            self._poll_timer = QTimer(self)
            self._poll_timer.setInterval(800)
            self._poll_timer.timeout.connect(self._poll_foreground)
            self._poll_timer.start()
        else:
            self._poll_timer = None

        # 渐显（Stretchly 是立即出现，这里 150ms 淡入更不刺眼）
        self.setWindowOpacity(0.0)
        self._fade = QPropertyAnimation(self, b"windowOpacity", self)
        self._fade.setDuration(FADE_IN_MS)
        self._fade.setStartValue(0.0)
        self._fade.setEndValue(1.0)
        self._fade.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._fade.start()
        self._fade.finished.connect(self._fade.deleteLater)
        QTimer.singleShot(0, self._focus_default)

    # -- presentation helpers -------------------------------------------

    @staticmethod
    def _friendly_app_name(name: str) -> str:
        cleaned = str(name).rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
        return cleaned[:-4] if cleaned.lower().endswith(".exe") else cleaned

    def _can_snooze(self) -> bool:
        if self._strict:
            return False
        if self._snooze_used >= self._snooze_quota:
            return False
        return True

    def _in_snooze_window(self) -> bool:
        """延后只在弹层生命周期的前 30% 可用（对齐 Stretchly 的 postponableDurationPercent）。"""

        if self._lock_until_switch:
            return True
        elapsed = self._seconds_total - self._seconds_left
        return elapsed <= max(1, int(self._seconds_total * SNOOZE_WINDOW_RATIO))

    def _hint_text(self) -> str:
        if self._strict:
            return "严格模式：本次专注不可跳过"
        if self._snooze_btn is not None:
            left = self._snooze_quota - self._snooze_used
            return f"Enter 返回专注 · Esc 延后（本次会话还可延后 {left} 次）"
        return "Enter 返回专注 · 使用 Alt+Tab / ⌘+Tab 切换应用"

    def _primary_style(self) -> str:
        return (
            f"QPushButton{{background:{hex_alpha(ACCENT, 0.12)};color:{ACCENT};"
            f"border:1px solid {hex_alpha(ACCENT, 0.35)};border-radius:{RADIUS_LG}px;"
            f"padding:9px 22px;font-size:{FONT_BODY}px;font-weight:600;}}"
            f"QPushButton:hover{{background:{hex_alpha(ACCENT, 0.18)};}}"
            f"QPushButton:focus{{border:1px solid {ACCENT};}}"
        )

    def _ghost_style(self) -> str:
        return (
            f"QPushButton{{background:transparent;color:{TEXT_SECONDARY};"
            f"border:1px solid {BORDER_NORMAL};border-radius:{RADIUS_LG}px;"
            f"padding:9px 18px;font-size:{FONT_BODY}px;}}"
            f"QPushButton:hover{{background:{hex_alpha(ACCENT, 0.06)};color:{TEXT_PRIMARY};}}"
        )

    def _focus_default(self):
        """把键盘焦点交给「返回专注」，让 Enter/Esc 立即可用。

        offscreen 平台（CI 与截图自检）里对半透明无边框 Tool 窗的子控件调用
        setFocus 会直接段错误，因此只在真实桌面平台上执行。
        """

        app = QApplication.instance()
        if app is not None and app.platformName() == "offscreen":
            return
        target = self._snooze_btn if self._snooze_btn is not None else None
        if target is None:
            target = self.findChild(QPushButton, "overlayPrimaryButton")
        if target is not None:
            target.setFocus(Qt.FocusPolicy.OtherFocusReason)

    # -- behaviour --------------------------------------------------------

    def _update_countdown(self):
        if self._seconds_left > 0:
            self._countdown.setText(f"{self._seconds_left} 秒后自动关闭")
        elif self._lock_until_switch:
            if self._blocked_processes:
                self._countdown.setText("切换到其他应用后会自动关闭")
            else:
                self._countdown.setText("深度模式会保持拦截，直到你切回允许的应用")
        else:
            self._countdown.setText("")

    def _on_tick(self):
        self._seconds_left = max(0, self._seconds_left - 1)
        self._update_countdown()
        if self._seconds_left == 0:
            self._timer.stop()
            if not self._lock_until_switch:
                self.allow_close()
                self.close()
            elif self._snooze_btn is not None and self._in_snooze_window():
                pass

    def _return_to_focus(self):
        self.allow_close()
        self.close()

    def _request_snooze(self):
        if not self._can_snooze() or not self._in_snooze_window():
            return
        self.snooze_requested.emit(SNOOZE_MINUTES)
        self.allow_close()
        self.close()

    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._return_to_focus()
            event.accept()
            return
        if key == Qt.Key.Key_Escape:
            if self._snooze_btn is not None and self._in_snooze_window():
                self._request_snooze()
            event.accept()
            return
        if key in (Qt.Key.Key_Tab, Qt.Key.Key_Backtab):
            QWidget.keyPressEvent(self, event)
            return
        super().keyPressEvent(event)

    def changeEvent(self, event: QEvent):
        # 延后窗口期一过就把按钮收掉，避免「随时可逃」的错觉
        if event.type() == QEvent.Type.Show and self._snooze_btn is not None:
            if not self._in_snooze_window():
                self._snooze_btn.setVisible(False)
        super().changeEvent(event)

    def _poll_foreground(self):
        """Check whether the user has switched back to an allowed app."""

        try:
            import os

            import psutil

            if HAS_WIN32_POLL:
                hwnd = win32gui.GetForegroundWindow()
                if not hwnd:
                    return
                if hwnd == int(self.winId()):
                    return
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                if not pid or pid == os.getpid():
                    return
                process = psutil.Process(pid)
                process_name = process.name().strip().casefold()
                try:
                    executable_path = process.exe()
                except (psutil.AccessDenied, psutil.NoSuchProcess, OSError):
                    executable_path = ""
                switched_from_blocked = (
                    self._blocked_processes and process_name not in self._blocked_processes
                )
                switched_to_allowed = (
                    not self._blocked_processes
                    and self._process_matcher.is_allowed(process_name, executable_path, int(pid))
                )
                if switched_from_blocked or switched_to_allowed:
                    self._poll_timer.stop()
                    self.allow_close()
                    self.close()
        except Exception:
            pass

    def allow_close(self):
        self._allow_close = True

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(244, 241, 234, 46))

    def closeEvent(self, event):
        if not self._allow_close:
            event.ignore()
            return
        self._timer.stop()
        if self._poll_timer is not None:
            self._poll_timer.stop()
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
        self.setFixedSize(300, 84)
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
            f"background:{BREAK_BG};color:{BREAK_ACCENT};border:1px solid {hex_alpha(WARNING, 0.35)};"
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
        painter.setBrush(QColor(244, 241, 234, 244))
        painter.setPen(QColor(ACCENT))
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 16, 16)

    def closeEvent(self, event):
        self._timer.stop()
        event.accept()
