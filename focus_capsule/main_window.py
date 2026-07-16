"""Primary planning window and application lifecycle coordination.

UI redesign v3.0 — left navigation rail + lightweight top bar + open canvas.
"""

from __future__ import annotations

from datetime import date

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QCloseEvent, QResizeEvent
from PyQt6.QtWidgets import (
    QApplication, QButtonGroup, QFrame, QHBoxLayout, QLabel,
    QMainWindow, QMenu, QPushButton, QScrollArea, QSizePolicy,
    QStackedWidget, QSystemTrayIcon, QVBoxLayout, QWidget,
)

from focus_capsule import theme as T
from focus_capsule.controller import SessionController, SessionUpdate
from focus_capsule.ai_report_service import AIReportService
from focus_capsule.ambient_background import AmbientBackground
from focus_capsule.calendar_page import CalendarPage
from focus_capsule.data_models import AppConfig, china_today
from focus_capsule.data_store import DataStore
from focus_capsule.dialogs import ask_confirmation, show_information
from focus_capsule.history_db import HistoryService
from focus_capsule.history_window import CompletionWindow, HistoryWindow
from focus_capsule.models import FocusConfig, ScheduleRule
from focus_capsule.monitor import WindowMonitorThread
from focus_capsule.overlay import OverlayService
from focus_capsule.schedule_manager import ScheduleManager
from focus_capsule.schedule_panel import SchedulePanel
from focus_capsule.session_view import SessionViewWindow
from focus_capsule.settings_panel import SettingsPanel
from focus_capsule.trend_page import TrendPage
from focus_capsule.trend_service import TrendService


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("专注舱 · Focus Capsule")
        self.setObjectName("appWindow")
        self.setMinimumSize(1024, 700)
        self.resize(1440, 900)

        self._quitting = False
        self._session_view: SessionViewWindow | None = None
        self._history_service = HistoryService()
        self._overlay_service = OverlayService(self)
        self._window_monitor = WindowMonitorThread(self)
        self._session_controller = SessionController(
            self._history_service,
            self._overlay_service,
            self,
        )
        self._settings_panel = SettingsPanel()
        self._schedule_manager = ScheduleManager(self)
        self._schedule_panel = SchedulePanel(self._schedule_manager, self)

        # v2.1 services
        self._data_store = DataStore()
        self._app_config = self._data_store.load_app_config()
        self._trend_service = TrendService(self._history_service, self._app_config)
        self._ai_service = AIReportService(
            self._history_service, self._data_store, self._app_config
        )

        # v2.1 UI pages
        self._calendar_page = CalendarPage(self._trend_service, self)
        self._trend_page = TrendPage(self._trend_service, self)
        from focus_capsule.daily_goal_page import DailyGoalWidget
        self._daily_goal_widget = DailyGoalWidget(
            self._data_store, self._trend_service, self._ai_service, self._app_config, self
        )

        # Session update → update today's goal
        self._session_controller.update_requested.connect(self._on_session_update)
        self._session_controller.session_completed.connect(self._on_session_completed)
        self._session_controller.session_completed.connect(self._on_session_record_saved)
        self._session_controller.tray_update.connect(self._on_tray_update)
        self._window_monitor.foreground_changed.connect(self._on_foreground_change)

        # Schedule enforcement wiring
        self._schedule_manager.rule_activated.connect(self._on_schedule_activated)
        self._schedule_manager.rule_released.connect(self._on_schedule_released)
        self._window_monitor.foreground_changed.connect(self._on_schedule_foreground_check)

        self._setup_ui()
        self._setup_tray()

        if hasattr(self._settings_panel, "config_changed"):
            self._settings_panel.config_changed.connect(self._on_config_changed)
        if hasattr(self._settings_panel, "start_clicked"):
            self._settings_panel.start_clicked.connect(self._start_session)
        if hasattr(self._schedule_panel, "rules_changed"):
            self._schedule_panel.rules_changed.connect(self._on_config_changed)

        self._center_window()

        # Start the window monitor for schedule enforcement and the schedule
        # manager itself.
        self._window_monitor.start()
        self._load_and_start_schedule()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _setup_ui(self):
        central = QWidget()
        central.setObjectName("appWindow")
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Ambient background layer ────────────────────────────
        # Lives behind every other widget; transparent to mouse events.
        self._ambient = AmbientBackground(central, orb_count=14)
        self._ambient.lower()

        # ── Left navigation rail ────────────────────────────────
        nav_rail = self._build_nav_rail()
        root.addWidget(nav_rail)

        # ── Right side: top bar + content canvas ────────────────
        right_side = QVBoxLayout()
        right_side.setContentsMargins(0, 0, 0, 0)
        right_side.setSpacing(0)

        # Top bar
        top_bar = self._build_top_bar()
        right_side.addWidget(top_bar)

        # Content canvas (QStackedWidget)
        self._content_stack = QStackedWidget()
        self._content_stack.setObjectName("canvas")

        # Page 0: Today (daily goal widget, scrollable)
        today_scroll = self._wrap_in_scroll(self._daily_goal_widget)
        self._content_stack.addWidget(today_scroll)

        # Page 1: Focus Plan (settings panel, scrollable)
        self._settings_panel.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding,
        )
        pomodoro_scroll = self._wrap_in_scroll(self._settings_panel)
        self._content_stack.addWidget(pomodoro_scroll)

        # Page 2: Schedule
        schedule_scroll = self._wrap_in_scroll(self._schedule_panel)
        self._content_stack.addWidget(schedule_scroll)

        # Page 3: Calendar
        self._content_stack.addWidget(self._calendar_page)

        # Page 4: Trend
        self._content_stack.addWidget(self._trend_page)

        right_side.addWidget(self._content_stack, 1)
        root.addLayout(right_side, 1)

        # Select default page
        self._nav_group.button(0).setChecked(True)
        self._content_stack.setCurrentIndex(0)
        self._update_page_title(0)

    def _build_nav_rail(self) -> QFrame:
        rail = QFrame()
        rail.setObjectName("navRail")
        rail.setFixedWidth(76)
        rail.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

        layout = QVBoxLayout(rail)
        layout.setContentsMargins(10, 12, 10, 12)
        layout.setSpacing(6)

        # Navigation button group (exclusive)
        self._nav_group = QButtonGroup(self)
        self._nav_group.setExclusive(True)

        nav_items = [
            ("今日", 0),
            ("专注", 1),
            ("日程", 2),
            ("日历", 3),
            ("趋势", 4),
        ]
        for label, idx in nav_items:
            btn = QPushButton(label)
            btn.setObjectName("navBtn")
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self._nav_group.addButton(btn, idx)
            layout.addWidget(btn)

        self._nav_group.idClicked.connect(self._set_page)

        # Spacer pushing history + quit to bottom
        layout.addStretch()

        # History button
        history_btn = QPushButton("历史")
        history_btn.setObjectName("navBtn")
        history_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        history_btn.clicked.connect(self._show_history)
        layout.addWidget(history_btn)

        # Quit button
        quit_btn = QPushButton("退出")
        quit_btn.setObjectName("navBtn")
        quit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        quit_btn.clicked.connect(self._quit_app)
        layout.addWidget(quit_btn)

        return rail

    def _build_top_bar(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("topBar")
        bar.setFixedHeight(44)
        bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(12)

        # Dynamic page title
        self._page_title_label = QLabel("今日")
        self._page_title_label.setObjectName("pageTitle")
        self._page_title_label.setStyleSheet(
            f"font-size:{T.FONT_PAGE_TITLE - 8}px; font-weight:{T.WEIGHT_TITLE};"
        )
        layout.addWidget(self._page_title_label)

        # Date string
        self._date_label = QLabel("")
        self._date_label.setStyleSheet(
            f"color:{T.TEXT_TERTIARY}; font-size:{T.FONT_BODY_SMALL}px;"
        )
        self._refresh_date_label()
        layout.addWidget(self._date_label)

        layout.addStretch()

        # Privacy indicator
        privacy = QLabel("●  数据仅保存在本机")
        privacy.setObjectName("tinyMuted")
        privacy.setToolTip("专注记录不会上传到云端")
        layout.addWidget(privacy)

        # Settings gear
        settings_btn = QPushButton("⚙")
        settings_btn.setObjectName("ghostButton")
        settings_btn.setFixedSize(36, 36)
        settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        settings_btn.setToolTip("设置")
        settings_btn.clicked.connect(self._show_settings)
        layout.addWidget(settings_btn)

        return bar

    def _refresh_date_label(self):
        today = china_today()
        weekdays = ["一", "二", "三", "四", "五", "六", "日"]
        weekday_idx = today.weekday()
        self._date_label.setText(
            f"{today.year}年{today.month}月{today.day}日 · 周{weekdays[weekday_idx]}"
        )

    def _update_page_title(self, page_id: int) -> None:
        titles = {
            0: "今日",
            1: "专注计划",
            2: "日程锁定",
            3: "日历",
            4: "趋势",
        }
        self._page_title_label.setText(titles.get(page_id, ""))

    def _wrap_in_scroll(self, widget: QWidget) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QScrollArea > QWidget > QWidget { background: transparent; }"
        )
        scroll.setWidget(widget)
        return scroll

    def _set_page(self, page_id: int) -> None:
        self._content_stack.setCurrentIndex(page_id)
        self._update_page_title(page_id)
        # Refresh pages that depend on fresh data
        if page_id == 0:
            self._daily_goal_widget.refresh()
        elif page_id == 3:
            self._calendar_page.refresh()
        elif page_id == 4:
            self._trend_page.refresh()

    def _show_settings(self):
        """Jump to the Focus Plan page where settings live."""
        self._nav_group.button(1).setChecked(True)
        self._set_page(1)

    def _refresh_global_style(self):
        """Rebuild and re-apply the QSS after a theme switch (e.g. focus mode)."""
        app = QApplication.instance()
        if app:
            from focus_capsule.styles import _build_stylesheet
            app.setStyleSheet(_build_stylesheet())

    # ------------------------------------------------------------------
    # Config change handler (replaces old _update_summary)
    # ------------------------------------------------------------------

    def _on_config_changed(self, *_) -> None:
        """Called when settings panel or schedule panel changes.

        With the summary panel removed, this now only updates the tray
        tooltip to reflect schedule enforcement status.
        """
        if self._schedule_manager.is_active and not self._session_controller.is_active:
            rule = self._schedule_manager.active_rule
            if rule and hasattr(self, "_tray"):
                self._tray.setToolTip(
                    f"专注舱 · 日程锁定中（{rule.start_hour:02d}:{rule.start_minute:02d}"
                    f"–{rule.end_hour:02d}:{rule.end_minute:02d}）"
                )

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    def _start_session(self, config: FocusConfig):
        if not config.whitelist:
            show_information(
                self,
                "还差一步",
                "请先选择至少一个专注期间允许使用的应用。",
            )
            return

        if hasattr(self._settings_panel, "save_config"):
            self._settings_panel.save_config()

        T.set_focused(True)
        self._refresh_global_style()

        try:
            self._session_view = SessionViewWindow(config)
            self._session_view.break_requested.connect(self._session_controller.handle_escape)
            self._session_view.end_requested.connect(self._confirm_end_session)
            self._session_view.hide_requested.connect(self._hide_session_to_tray)
            self._session_controller.start_session(config)
            self._window_monitor.start()
            self._session_view.show()
            self._session_view.raise_()
            self.hide()
        except Exception:
            T.set_focused(False)
            self._refresh_global_style()
            if self._session_view:
                self._session_view.finish_and_close()
                self._session_view = None
            self.showNormal()
            raise

    def _confirm_end_session(self):
        if not self._session_controller.is_active:
            return
        confirmed = ask_confirmation(
            self._session_view or self,
            "提前结束本次专注？",
            "当前进度会保存到历史记录。",
            confirm_text="结束并保存",
            cancel_text="继续专注",
            destructive=True,
        )
        if confirmed:
            self._session_controller.terminate()

    def _hide_session_to_tray(self):
        if self._session_view:
            self._session_view.hide(to_tray=True)
        if self._tray.isVisible():
            self._tray.showMessage(
                "专注仍在继续",
                "点击托盘图标可重新打开专注窗口。",
                QSystemTrayIcon.MessageIcon.Information,
                2500,
            )

    def _on_session_update(self, update: SessionUpdate):
        if self._session_view:
            self._session_view.update_from_session(update)

    def _on_session_completed(self, record):
        if self._session_view:
            self._session_view.finish_and_close()
            self._session_view = None

        T.set_focused(False)
        self._refresh_global_style()

        # Do NOT stop the window monitor here — it needs to keep running
        # for schedule-based enforcement. Only hide the session-specific
        # overlay.
        self._overlay_service.hide_overlay()
        self._overlay_service.hide_break_window()

        if self._quitting:
            return

        # Use an independent top-level dialog: the planning window is hidden
        # during a session, and some window managers also hide its child
        # dialogs when the parent is not visible.
        completion = CompletionWindow(record)
        completion.show()
        completion.raise_()
        completion.activateWindow()
        completion.exec()
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _on_session_record_saved(self, record):
        """Update daily goals, trend, calendar with the new record."""
        completed = getattr(record, "outcome", "") == "completed"
        terminated = getattr(record, "outcome", "") == "terminated"
        achieved_minutes = max(0, getattr(record, "actual_focus_seconds", 0)) // 60
        self._data_store.update_today_goal_from_session(
            achieved_minutes, completed, terminated
        )
        # refresh any currently-visible pages
        self._daily_goal_widget.refresh()
        self._calendar_page.refresh()
        self._trend_page.refresh()

    def _on_foreground_change(self, process_name: str, window_title: str):
        self._session_controller.on_foreground_change(process_name, window_title)

    # ------------------------------------------------------------------
    # Legacy mode toggle compat — redirect to new page system
    # ------------------------------------------------------------------

    def _set_mode(self, mode_id: int) -> None:
        """Legacy callback — now routes to the new page system."""
        self._set_page(mode_id)

    # ------------------------------------------------------------------
    # Schedule enforcement
    # ------------------------------------------------------------------

    def _load_and_start_schedule(self) -> None:
        """Load persisted rules into the manager and start the ticker."""
        self._schedule_panel.load_rules()
        self._schedule_manager.start()

    def _on_schedule_activated(self, rule) -> None:
        """Called when a schedule rule becomes active."""
        if self._quitting or self._session_controller.is_active:
            return
        time_range = (
            f"{rule.start_hour:02d}:{rule.start_minute:02d}–"
            f"{rule.end_hour:02d}:{rule.end_minute:02d}"
        )
        self._tray.showMessage(
            "日程锁定已生效",
            f"{time_range} 期间只能使用已允许的应用",
            QSystemTrayIcon.MessageIcon.Information,
            3000,
        )
        self._on_tray_update(True)
        self._schedule_panel.refresh_active_status()
        self._start_schedule_session(rule)

    def _on_schedule_released(self, _rule) -> None:
        """Called when a schedule rule's time window ends."""
        if self._quitting:
            return
        if self._session_controller.is_active:
            self._session_controller.terminate()
        if self._session_view:
            self._session_view.finish_and_close()
            self._session_view = None
        self._overlay_service.hide_overlay()
        T.set_focused(False)
        self._refresh_global_style()
        self.showNormal()
        self.raise_()
        self.activateWindow()
        self._tray.showMessage(
            "日程锁定已解除",
            "锁定时段结束，可自由使用应用",
            QSystemTrayIcon.MessageIcon.Information,
            2500,
        )
        self._on_tray_update(False)
        self._schedule_panel.refresh_active_status()

    def _enforce_active_schedule_for_current_window(self) -> None:
        """Apply a newly active rule without blocking an already allowed app."""
        if self._quitting or self._session_controller.is_active:
            return
        if self._window_monitor.is_focus_capsule_foreground:
            return
        process_name = self._window_monitor.last_process
        window_title = self._window_monitor.last_title
        if process_name:
            self._on_schedule_foreground_check(process_name, window_title)

    def _start_schedule_session(self, rule: ScheduleRule):
        """Start a focused session based on an activated schedule rule."""
        if not rule.whitelisted_apps:
            show_information(
                self,
                "通知",
                "日程锁定规则不允许任何应用，请先设置允许的应用。",
            )
            return

        config = FocusConfig(
            duration_minutes=60,
            mode="Deep",
            goal="通过日程锁定进行专注",
            whitelist=rule.whitelisted_apps,
            max_esc=getattr(rule, "max_esc", 0),
            esc_break_minutes=getattr(rule, "esc_break_minutes", 3),
        )

        T.set_focused(True)
        self._refresh_global_style()

        try:
            self._session_view = SessionViewWindow(config)
            self._session_view.break_requested.connect(self._session_controller.handle_escape)
            self._session_view.end_requested.connect(self._confirm_schedule_end)
            self._session_view.hide_requested.connect(self._hide_session_to_tray)
            self._session_controller.start_session(config)
            self._window_monitor.start()
            self._session_view.show()
            self._session_view.raise_()
            self.hide()
        except Exception:
            T.set_focused(False)
            self._refresh_global_style()
            if self._session_view:
                self._session_view.finish_and_close()
                self._session_view = None
            self.showNormal()
            raise

    def _confirm_schedule_end(self):
        if not self._session_controller.is_active:
            return
        confirmed = ask_confirmation(
            self._session_view or self,
            "提前结束日程锁定？",
            "日程锁定期间专注的进度会保存到历史记录。",
            confirm_text="结束并保存",
            cancel_text="继续专注",
            destructive=True,
        )
        if confirmed:
            self._session_controller.terminate()
            self._schedule_manager.suppress_active_rule()

    def _on_schedule_foreground_check(self, process_name: str, _window_title: str) -> None:
        """Check foreground app against schedule rules when no manual session is active."""
        if self._session_controller.is_active:
            return
        if not self._schedule_manager.is_active:
            return
        if not self._schedule_manager.is_process_allowed(process_name):
            system_processes = {"explorer.exe", "shell.exe", "windows.ui.shell.lightswitch.exe"}
            if process_name in system_processes:
                return
            rule = self._schedule_manager.active_rule
            first_app = rule.whitelisted_apps[0] if rule and rule.whitelisted_apps else process_name
            if not self._overlay_service._alive(self._overlay_service._overlay_window):
                self._overlay_service.show_overlay(
                    first_app,
                    return_seconds=5,
                    allowed_apps=rule.whitelisted_apps if rule else None,
                )
            self._tray.setToolTip("专注舱 · 日程锁定中")
        else:
            self._overlay_service.hide_overlay()

    # ------------------------------------------------------------------
    # Tray
    # ------------------------------------------------------------------

    def _setup_tray(self):
        self._tray = QSystemTrayIcon(QApplication.instance().windowIcon(), self)
        self._tray.setToolTip("专注舱")
        tray_menu = QMenu()
        self._tray_show_action = QAction("打开专注舱", self)
        self._tray_show_action.triggered.connect(self._show_from_tray)
        tray_menu.addAction(self._tray_show_action)
        self._tray_show_session_action = QAction("打开专注窗口", self)
        self._tray_show_session_action.triggered.connect(self._show_session_from_tray)
        self._tray_show_session_action.setVisible(False)
        tray_menu.addAction(self._tray_show_session_action)
        tray_menu.addSeparator()
        history_action = tray_menu.addAction("历史记录")
        history_action.triggered.connect(self._show_history)
        quit_action = tray_menu.addAction("退出")
        quit_action.triggered.connect(self._quit_app)
        self._tray.setContextMenu(tray_menu)
        self._tray.activated.connect(self._on_tray_activated)
        if QSystemTrayIcon.isSystemTrayAvailable():
            self._tray.show()

    def _on_tray_update(self, active: bool):
        self._tray.setToolTip("专注舱 · 专注进行中" if active else "专注舱")
        self._tray_show_session_action.setVisible(active)
        self._tray_show_action.setText("打开专注舱")

    def _on_tray_activated(self, reason):
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            if self._session_controller.is_active:
                self._show_session_from_tray()
            else:
                self._show_from_tray()

    def _show_from_tray(self):
        if self._session_controller.is_active and self._session_view:
            self._session_view.show_normal()
            self._session_view.raise_()
            self._session_view.activateWindow()
        else:
            self.showNormal()
            self.raise_()
            self.activateWindow()

    def _show_session_from_tray(self):
        if self._session_controller.is_active and self._session_view:
            self._session_view.show_normal()
            self._session_view.raise_()
            self._session_view.activateWindow()
        elif self._schedule_manager.is_active and self._schedule_manager.active_rule:
            self._start_schedule_session(self._schedule_manager.active_rule)
        else:
            self.showNormal()
            self.raise_()
            self.activateWindow()

    def _show_history(self):
        dialog = HistoryWindow(self._history_service, self)
        dialog.exec()

    # ------------------------------------------------------------------
    # Window events
    # ------------------------------------------------------------------

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, '_ambient') and self._ambient is not None:
            central = self.centralWidget()
            if central is not None:
                self._ambient.setGeometry(0, 0, central.width(), central.height())

    def _center_window(self):
        screen = QApplication.primaryScreen()
        if not screen:
            return
        frame = self.frameGeometry()
        frame.moveCenter(screen.availableGeometry().center())
        self.move(frame.topLeft())

    # ------------------------------------------------------------------
    # Quit / close
    # ------------------------------------------------------------------

    def _quit_app(self):
        if self._quitting:
            return
        if self._session_controller.is_active:
            confirmed = ask_confirmation(
                self._session_view or self,
                "结束专注并退出？",
                "当前专注仍在进行。退出前会保存现有进度。",
                confirm_text="结束并退出",
                cancel_text="继续专注",
                destructive=True,
            )
            if not confirmed:
                return
            self._quitting = True
            self._session_controller.terminate()
        else:
            self._quitting = True

        T.set_focused(False)
        self._refresh_global_style()
        self._window_monitor.stop()
        self._schedule_manager.stop()
        self._overlay_service.hide_overlay()
        self._overlay_service.hide_break_window()
        if self._session_view:
            self._session_view.finish_and_close()
        self._tray.hide()
        QApplication.quit()

    def closeEvent(self, event: QCloseEvent):
        if self._session_controller.is_active:
            self.hide()
            event.ignore()
            return
        self._quit_app()
        event.accept() if self._quitting else event.ignore()
