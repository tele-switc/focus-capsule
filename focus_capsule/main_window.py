"""Primary planning window and application lifecycle coordination."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QCloseEvent, QResizeEvent
from PyQt6.QtWidgets import (
    QApplication, QButtonGroup, QFrame, QHBoxLayout, QLabel,
    QMainWindow, QMenu, QPushButton, QScrollArea, QSizePolicy,
    QStackedWidget, QSystemTrayIcon, QVBoxLayout, QWidget,
)

from focus_capsule.controller import SessionController, SessionUpdate
from PyQt6.QtWidgets import QButtonGroup

from focus_capsule.ai_report_service import AIReportService
from focus_capsule.ambient_background import AmbientBackground
from focus_capsule.calendar_page import CalendarPage
from focus_capsule.data_models import AppConfig, china_today
from focus_capsule.data_store import DataStore
from focus_capsule.dialogs import ask_confirmation, show_information
from focus_capsule.history_db import HistoryService
from focus_capsule.history_window import CompletionWindow, HistoryWindow
from focus_capsule.models import FocusConfig
from focus_capsule.monitor import WindowMonitorThread
from focus_capsule.overlay import OverlayService
from focus_capsule.schedule_manager import ScheduleManager
from focus_capsule.schedule_panel import SchedulePanel
from focus_capsule.session_view import SessionViewWindow
from focus_capsule.settings_panel import SettingsPanel
from focus_capsule.theme import MODE_LABELS, TEXT_TERTIARY, ACCENT_DARK_BG, ACCENT
from focus_capsule.trend_page import TrendPage
from focus_capsule.trend_service import TrendService
from focus_capsule.widgets import FocusRing


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("专注舱 · Focus Capsule")
        self.setObjectName("appWindow")
        self.setMinimumSize(980, 680)
        self.resize(1240, 800)

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
            self._settings_panel.config_changed.connect(self._update_summary)
        if hasattr(self._settings_panel, "start_clicked"):
            self._settings_panel.start_clicked.connect(self._start_session)
        if hasattr(self._schedule_panel, "rules_changed"):
            self._schedule_panel.rules_changed.connect(self._update_summary)

        self._update_summary()
        self._center_window()

        # Start the window monitor for schedule enforcement and the schedule
        # manager itself.
        self._window_monitor.start()
        self._load_and_start_schedule()

    def _setup_ui(self):
        central = QWidget()
        central.setObjectName("appWindow")
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(24, 18, 24, 20)
        root.setSpacing(16)

        # ── Ambient background layer ────────────────────────────
        # Lives behind every other widget; transparent to mouse events.
        self._ambient = AmbientBackground(central, orb_count=14)
        self._ambient.lower()

        # ── Top bar ────────────────────────────────────────────
        top_bar = QHBoxLayout()
        top_bar.setSpacing(12)

        brand_mark = QLabel("◉")
        brand_mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand_mark.setFixedSize(38, 38)
        brand_mark.setStyleSheet(
            f"background:{ACCENT_DARK_BG};color:{ACCENT};border:1px solid #2D5B50;"
            f"border-radius:12px;font-size:18px;font-weight:700;"
        )
        top_bar.addWidget(brand_mark)

        brand_text = QVBoxLayout()
        brand_text.setSpacing(0)
        title = QLabel("专注舱")
        title.setObjectName("brandTitle")
        subtitle = QLabel("Focus Capsule · 把注意力留给真正重要的事")
        subtitle.setObjectName("brandSubtitle")
        brand_text.addWidget(title)
        brand_text.addWidget(subtitle)
        top_bar.addLayout(brand_text)
        top_bar.addStretch()

        privacy = QLabel("●  数据仅保存在本机")
        privacy.setObjectName("tinyMuted")
        privacy.setToolTip("专注记录不会上传到云端")
        top_bar.addWidget(privacy)

        history_button = QPushButton("历史记录")
        history_button.setObjectName("ghostButton")
        history_button.setAccessibleName("打开专注历史记录")
        history_button.clicked.connect(self._show_history)
        top_bar.addWidget(history_button)

        quit_button = QPushButton("退出")
        quit_button.setObjectName("ghostButton")
        quit_button.clicked.connect(self._quit_app)
        top_bar.addWidget(quit_button)
        root.addLayout(top_bar)

        divider = QFrame()
        divider.setObjectName("divider")
        divider.setFrameShape(QFrame.Shape.HLine)
        root.addWidget(divider)

        # ── Segmented navigation ───────────────────────────────
        nav_host = QFrame()
        nav_host.setObjectName("segmentedControl")
        nav_layout = QHBoxLayout(nav_host)
        nav_layout.setContentsMargins(4, 4, 4, 4)
        nav_layout.setSpacing(2)

        self._nav_group = QButtonGroup(self)
        self._nav_group.setExclusive(True)
        nav_items = [
            ("今日", 0),
            ("专注计划", 1),
            ("日程锁定", 2),
            ("日历", 3),
            ("趋势", 4),
        ]
        for label, idx in nav_items:
            btn = QPushButton(label)
            btn.setObjectName("segmentedBtn")
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self._nav_group.addButton(btn, idx)
            nav_layout.addWidget(btn)
        self._nav_group.idClicked.connect(self._set_page)
        root.addWidget(nav_host)

        # ── Page stack ─────────────────────────────────────────
        self._content_stack = QStackedWidget()

        # Page 0: Today (daily goal + summary side-by-side)
        today_page = self._build_today_page()
        self._content_stack.addWidget(today_page)

        # Page 1: Pomodoro (settings + summary)
        pomodoro_page = self._build_pomodoro_page()
        self._content_stack.addWidget(pomodoro_page)

        # Page 2: Schedule
        schedule_scroll = self._wrap_in_scroll(self._schedule_panel)
        self._content_stack.addWidget(schedule_scroll)

        # Page 3: Calendar
        self._content_stack.addWidget(self._calendar_page)

        # Page 4: Trend
        self._content_stack.addWidget(self._trend_page)

        root.addWidget(self._content_stack, 1)

        # Select default page
        self._nav_group.button(0).setChecked(True)
        self._content_stack.setCurrentIndex(0)

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

    def _build_today_page(self) -> QWidget:
        page = QWidget()
        layout = QHBoxLayout(page)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setSpacing(20)

        # Left: daily goal + report
        left_scroll = self._wrap_in_scroll(self._daily_goal_widget)
        layout.addWidget(left_scroll, 1)

        # Right: summary panel (same as pomodoro's summary)
        summary = self._build_summary_panel()
        layout.addWidget(summary, 0)

        return page

    def _build_pomodoro_page(self) -> QWidget:
        page = QWidget()
        layout = QHBoxLayout(page)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setSpacing(20)

        self._settings_panel.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding,
        )
        pomodoro_scroll = self._wrap_in_scroll(self._settings_panel)
        layout.addWidget(pomodoro_scroll, 1)

        summary = self._build_summary_panel()
        layout.addWidget(summary, 0)

        return page

    def _set_page(self, page_id: int) -> None:
        self._content_stack.setCurrentIndex(page_id)
        # Refresh pages that depend on fresh data
        if page_id == 0:
            self._daily_goal_widget.refresh()
        elif page_id == 3:
            self._calendar_page.refresh()
        elif page_id == 4:
            self._trend_page.refresh()

    def _build_summary_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("panel")
        panel.setMinimumWidth(300)
        panel.setMaximumWidth(340)
        panel.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(24, 24, 24, 22)
        layout.setSpacing(14)

        eyebrow = QLabel("本次计划")
        eyebrow.setObjectName("eyebrow")
        layout.addWidget(eyebrow)

        self._summary_goal = QLabel("先写下你要完成的事")
        self._summary_goal.setObjectName("summaryGoal")
        self._summary_goal.setWordWrap(True)
        self._summary_goal.setMinimumHeight(44)
        layout.addWidget(self._summary_goal)

        self._focus_ring = FocusRing()
        self._focus_ring.setMinimumSize(235, 235)
        self._focus_ring.setMaximumHeight(265)
        layout.addWidget(self._focus_ring, 1)

        meta = QFrame()
        meta.setObjectName("softPanel")
        meta_layout = QVBoxLayout(meta)
        meta_layout.setContentsMargins(14, 12, 14, 12)
        meta_layout.setSpacing(9)
        self._summary_mode = self._add_summary_row(meta_layout, "保护强度", "标准提醒")
        self._summary_apps = self._add_summary_row(meta_layout, "允许应用", "尚未选择")
        self._summary_break = self._add_summary_row(meta_layout, "临时离开", "2 次 · 每次 3 分钟")
        layout.addWidget(meta)

        self._summary_hint = QLabel("至少选择一个专注期间允许使用的应用")
        self._summary_hint.setObjectName("hint")
        self._summary_hint.setWordWrap(True)
        layout.addWidget(self._summary_hint)

        self._start_button = QPushButton("开始本次专注")
        self._start_button.setObjectName("primaryButton")
        self._start_button.setAccessibleName("开始本次专注")
        self._start_button.clicked.connect(self._on_start_clicked)
        layout.addWidget(self._start_button)
        return panel

    @staticmethod
    def _add_summary_row(layout: QVBoxLayout, key: str, value: str) -> QLabel:
        row = QHBoxLayout()
        key_label = QLabel(key)
        key_label.setObjectName("summaryKey")
        value_label = QLabel(value)
        value_label.setObjectName("summaryValue")
        value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        value_label.setWordWrap(True)
        row.addWidget(key_label)
        row.addStretch()
        row.addWidget(value_label, 1)
        layout.addLayout(row)
        return value_label

    def _update_summary(self, *_):
        config = self._settings_panel.get_config()
        goal = (getattr(config, "goal", "") or "").strip()
        self._summary_goal.setText(goal or "先写下你要完成的事")
        self._summary_goal.setStyleSheet("" if goal else f"color:{TEXT_TERTIARY};")

        self._focus_ring.set_progress(0)
        self._focus_ring.set_center_text(f"{config.duration_minutes}\n分钟")
        self._focus_ring.set_caption("已准备好")
        self._focus_ring.set_state("ready")

        self._summary_mode.setText(MODE_LABELS.get(config.mode, config.mode))
        app_count = len(config.whitelist)
        self._summary_apps.setText(f"{app_count} 个" if app_count else "尚未选择")
        if config.max_esc:
            self._summary_break.setText(
                f"{config.max_esc} 次 · 每次 {config.esc_break_minutes} 分钟"
            )
        else:
            self._summary_break.setText("不允许")

        ready = app_count > 0
        self._start_button.setEnabled(ready)
        self._summary_hint.setText(
            "准备完成。开始后仍可从专注窗口主动休息或提前结束。"
            if ready
            else "至少选择一个专注期间允许使用的应用"
        )

        # Tray status reflects schedule enforcement too
        if self._schedule_manager.is_active and not self._session_controller.is_active:
            rule = self._schedule_manager.active_rule
            if rule:
                self._tray.setToolTip(
                    f"专注舱 · 日程锁定中（{rule.start_hour:02d}:{rule.start_minute:02d}"
                    f"–{rule.end_hour:02d}:{rule.end_minute:02d}）"
                )

    def _on_start_clicked(self):
        self._start_session(self._settings_panel.get_config())

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
    # Legacy mode toggle compat — redirect to new segmented nav
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
