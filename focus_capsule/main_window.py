"""Focus Capsule primary planning window.

The Windows shell uses a readable navigation sidebar, compact context bar and
calm work canvas.  Navigation always shows labels instead of relying on glyphs.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction, QCloseEvent
from PyQt6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from focus_capsule import focus_guard
from focus_capsule import theme as T
from focus_capsule.activity_tracker import ActivityTracker
from focus_capsule.ai_report_service import AIReportService
from focus_capsule.ambient_background import AmbientBackground
from focus_capsule.app_categories import merge_catalog_categories
from focus_capsule.calendar_page import CalendarPage
from focus_capsule.category_dialog import AppCategoryDialog
from focus_capsule.controller import SessionController, SessionUpdate
from focus_capsule.daily_progress import DailyProgressService
from focus_capsule.data_models import china_today
from focus_capsule.data_store import DataStore
from focus_capsule.dialogs import ask_confirmation, show_information
from focus_capsule.exit_gate_dialog import ExitGateDialog
from focus_capsule.history_db import HistoryService
from focus_capsule.history_window import CompletionWindow, HistoryWindow
from focus_capsule.icon_utils import discover_installed_apps
from focus_capsule.models import FocusConfig, ScheduleRule
from focus_capsule.monitor import WindowMonitorThread
from focus_capsule.overlay import OverlayService
from focus_capsule.schedule_manager import ScheduleManager, _seconds_until_next_boundary
from focus_capsule.schedule_panel import SchedulePanel
from focus_capsule.session_view import SessionViewWindow
from focus_capsule.settings_panel import SettingsPanel
from focus_capsule.strict_lock import ClockGuard
from focus_capsule.trend_page import TrendPage
from focus_capsule.trend_service import TrendService

NAV_LABELS = ["今日概览", "专注计划", "日程锁定", "专注日历", "数据趋势"]
NAV_TOOLTIPS = ["查看并安排今天的任务", "配置专注会话", "按时间自动锁定", "每日专注记录", "专注数据分析"]

PAGE_TITLES = {
    0: ("今日概览", "安排任务并查看真实进度"),
    1: ("专注计划", "配置一次专注会话"),
    2: ("日程锁定", "按时间段自动起停专注"),
    3: ("专注日历", "每日专注记录与强度"),
    4: ("数据趋势", "时间线、分类与连续记录"),
}


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
        self._data_store = DataStore()
        self._app_config = self._data_store.load_app_config()
        try:
            self._app_config, categories_changed = merge_catalog_categories(
                self._app_config,
                discover_installed_apps(),
            )
            if categories_changed:
                self._data_store.save_app_config(self._app_config)
        except Exception:
            pass
        self._activity_tracker = ActivityTracker(self._data_store, self)
        self._exclusions = focus_guard.compile_exclusions(
            list(getattr(self._app_config, "focus_exclusions", []) or []) or None
        )
        self._overlay_service = OverlayService(
            self,
            exclusions=self._exclusions,
            guard_enabled=bool(getattr(self._app_config, "guard_enabled", True)),
        )
        self._window_monitor = WindowMonitorThread(self)
        self._session_controller = SessionController(
            self._history_service,
            self._overlay_service,
            self,
        )
        # 覆盖层被关闭后由控制器复查前台，避免「关掉弹层就一路放行」
        self._session_controller.attach_monitor(self._window_monitor)
        self._clock_guard = ClockGuard()
        self._settings_panel = SettingsPanel()
        self._schedule_manager = ScheduleManager(self)
        self._schedule_panel = SchedulePanel(self._schedule_manager, self)

        self._trend_service = TrendService(self._history_service, self._app_config)
        self._daily_progress = DailyProgressService(
            self._history_service,
            self._data_store,
            self._app_config,
        )
        self._ai_service = AIReportService(
            self._history_service, self._data_store, self._app_config
        )

        self._calendar_page = CalendarPage(
            self._trend_service,
            self,
            data_store=self._data_store,
            progress_service=self._daily_progress,
        )
        self._trend_page = TrendPage(self._trend_service, self)
        from focus_capsule.daily_goal_page import DailyGoalPage as DailyGoalWidget
        self._daily_goal_widget = DailyGoalWidget(
            self._data_store,
            self._trend_service,
            self._ai_service,
            self._app_config,
            self,
            progress_service=self._daily_progress,
        )

        self._session_controller.update_requested.connect(self._on_session_update)
        self._session_controller.session_completed.connect(self._on_session_completed)
        self._session_controller.session_completed.connect(self._on_session_record_saved)
        self._session_controller.tray_update.connect(self._on_tray_update)
        self._window_monitor.foreground_changed.connect(self._on_foreground_change)

        self._schedule_manager.rule_activated.connect(self._on_schedule_activated)
        self._schedule_manager.rule_released.connect(self._on_schedule_released)
        self._window_monitor.foreground_changed.connect(self._on_schedule_foreground_check)
        self._activity_tracker.usage_updated.connect(self._on_usage_updated)

        self._setup_ui()
        self._setup_tray()

        if hasattr(self._daily_goal_widget, "open_focus_plan_requested"):
            self._daily_goal_widget.open_focus_plan_requested.connect(self._show_settings)
        if hasattr(self._settings_panel, "config_changed"):
            self._settings_panel.config_changed.connect(self._on_config_changed)
        if hasattr(self._settings_panel, "manage_categories_requested"):
            self._settings_panel.manage_categories_requested.connect(
                self._open_category_manager
            )
        if hasattr(self._settings_panel, "start_clicked"):
            self._settings_panel.start_clicked.connect(self._start_session)
        if hasattr(self._schedule_panel, "rules_changed"):
            self._schedule_panel.rules_changed.connect(self._on_config_changed)
        if hasattr(self._settings_panel, "guard_settings_changed"):
            self._settings_panel.guard_settings_changed.connect(
                self._on_guard_settings_changed
            )

        self._center_window()

        self._window_monitor.start()
        self._load_and_start_schedule()
        self._clock_timer = QTimer(self)
        self._clock_timer.setInterval(60_000)
        self._clock_timer.timeout.connect(self._check_clock_integrity)
        self._clock_timer.start()

    def _check_clock_integrity(self) -> None:
        """改系统时间绕不过去：检测到倒退/跳变就终止当前锁定并记为破功。"""

        try:
            tampered, reason = self._clock_guard.check()
        except Exception:
            return
        if not tampered:
            return
        if self._session_controller.is_active:
            self._session_controller.terminate(force=True)
        self._schedule_manager.suppress_active_rule()
        if self._tray.isVisible():
            self._tray.showMessage(
                "检测到系统时间被调整",
                f"{reason}，本次锁定已终止并记录为破功。",
                QSystemTrayIcon.MessageIcon.Warning,
                6000,
            )

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

        self._ambient = AmbientBackground(central, orb_count=10)
        self._ambient.lower()

        nav_rail = self._build_nav_rail()
        root.addWidget(nav_rail)

        right_side = QVBoxLayout()
        right_side.setContentsMargins(0, 0, 0, 0)
        right_side.setSpacing(0)

        top_bar = self._build_top_bar()
        right_side.addWidget(top_bar)

        self._content_stack = QStackedWidget()
        self._content_stack.setObjectName("canvas")

        today_scroll = self._wrap_in_scroll(self._daily_goal_widget)
        self._content_stack.addWidget(today_scroll)
        self._settings_panel.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding,
        )
        pomodoro_scroll = self._wrap_in_scroll(self._settings_panel)
        self._content_stack.addWidget(pomodoro_scroll)
        schedule_scroll = self._wrap_in_scroll(self._schedule_panel)
        self._content_stack.addWidget(schedule_scroll)
        self._content_stack.addWidget(self._calendar_page)
        self._content_stack.addWidget(self._trend_page)

        right_side.addWidget(self._content_stack, 1)
        root.addLayout(right_side, 1)

        self._nav_group.button(0).setChecked(True)
        self._content_stack.setCurrentIndex(0)
        self._update_page_header(0)

    def _build_nav_rail(self) -> QFrame:
        rail = QFrame()
        rail.setObjectName("navRail")
        rail.setFixedWidth(T.NAV_WIDTH)
        rail.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

        layout = QVBoxLayout(rail)
        layout.setContentsMargins(16, 20, 16, 16)
        layout.setSpacing(6)

        brand_row = QHBoxLayout()
        brand_row.setSpacing(0)
        brand_name = QLabel("专注舱")
        brand_name.setObjectName("navBrand")
        brand_row.addWidget(brand_name, 1)
        layout.addLayout(brand_row)
        layout.addSpacing(28)

        section_label = QLabel("工作区")
        section_label.setObjectName("navSectionLabel")
        layout.addWidget(section_label)
        layout.addSpacing(4)

        self._nav_group = QButtonGroup(self)
        self._nav_group.setExclusive(True)

        for idx in range(5):
            btn = QPushButton(NAV_LABELS[idx])
            btn.setObjectName("navBtn")
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setProperty("navIndex", idx)
            btn.setToolTip(NAV_TOOLTIPS[idx])
            self._nav_group.addButton(btn, idx)
            layout.addWidget(btn)

        self._nav_group.idClicked.connect(self._set_page)

        layout.addStretch()

        local_card = QFrame()
        local_card.setObjectName("navLocalCard")
        local_layout = QVBoxLayout(local_card)
        local_layout.setContentsMargins(12, 10, 12, 10)
        local_layout.setSpacing(2)
        local_title = QLabel("●  本地专注空间")
        local_title.setObjectName("navLocalTitle")
        local_layout.addWidget(local_title)
        local_note = QLabel("记录只保存在这台电脑")
        local_note.setObjectName("navLocalNote")
        local_note.setWordWrap(True)
        local_layout.addWidget(local_note)
        layout.addWidget(local_card)
        layout.addSpacing(10)

        divider = QFrame()
        divider.setObjectName("navDivider")
        divider.setFixedHeight(1)
        layout.addWidget(divider)
        layout.addSpacing(6)

        history_btn = QPushButton("☷    历史记录")
        history_btn.setObjectName("navSecondaryBtn")
        history_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        history_btn.setToolTip("历史记录")
        history_btn.clicked.connect(self._show_history)
        layout.addWidget(history_btn)

        quit_btn = QPushButton("⏻    退出专注舱")
        quit_btn.setObjectName("navSecondaryBtn")
        quit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        quit_btn.setToolTip("退出")
        quit_btn.clicked.connect(self._quit_app)
        layout.addWidget(quit_btn)

        return rail

    def _build_top_bar(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("topBar")
        bar.setFixedHeight(T.TOP_BAR_HEIGHT)
        bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(32, 12, 28, 12)
        layout.setSpacing(16)

        title_box = QVBoxLayout()
        title_box.setSpacing(1)
        title_box.setContentsMargins(0, 0, 0, 0)

        self._page_title_label = QLabel("今日概览")
        self._page_title_label.setObjectName("pageTitle")
        title_box.addWidget(self._page_title_label)

        self._page_subtitle_label = QLabel("安排任务并查看真实进度")
        self._page_subtitle_label.setObjectName("pageSubtitle")
        title_box.addWidget(self._page_subtitle_label)

        layout.addLayout(title_box)

        self._date_label = QLabel("")
        self._date_label.setObjectName("dateChip")
        self._refresh_date_label()
        layout.addStretch()
        layout.addWidget(self._date_label)

        settings_btn = QPushButton("⚙  设置")
        settings_btn.setObjectName("topSettingsButton")
        settings_btn.setFixedHeight(36)
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
            f"{today.year} 年 {today.month} 月 {today.day} 日  ·  周{weekdays[weekday_idx]}"
        )

    def _update_page_header(self, page_id: int) -> None:
        title, subtitle = PAGE_TITLES.get(page_id, ("", ""))
        self._page_title_label.setText(title)
        self._page_subtitle_label.setText(subtitle)

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
        self._update_page_header(page_id)
        if page_id == 0:
            self._daily_goal_widget.reload_goal()
        elif page_id == 3:
            self._calendar_page.refresh()
        elif page_id == 4:
            self._trend_page.refresh()

    def _show_settings(self):
        self._nav_group.button(1).setChecked(True)
        self._set_page(1)

    def _refresh_global_style(self):
        app = QApplication.instance()
        if app:
            from focus_capsule.styles import _build_stylesheet
            app.setStyleSheet(_build_stylesheet())

    def _on_guard_settings_changed(self, enabled: bool, exclusions) -> None:
        """免打扰开关/清单改动即时生效，不必重启。"""

        patterns = focus_guard.compile_exclusions(list(exclusions or []) or None)
        self._exclusions = patterns
        self._overlay_service.set_guard_enabled(bool(enabled))
        self._overlay_service.set_exclusions(patterns)
        try:
            config = self._data_store.load_app_config()
            config.guard_enabled = bool(enabled)
            config.focus_exclusions = [str(item) for item in (exclusions or [])]
            self._app_config = config
            self._data_store.save_app_config(config)
        except Exception:
            pass

    def _on_config_changed(self, *_) -> None:
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
            show_information(self, "还差一步", "请先选择至少一个专注期间允许使用的应用。")
            return

        if hasattr(self._settings_panel, "save_config"):
            self._settings_panel.save_config()

        # 全局严格模式默认值（会话自身未指定时生效）
        if (
            getattr(config, "strict_level", "off") == "off"
            and str(getattr(self._app_config, "strict_level", "off") or "off") != "off"
        ):
            config.strict_level = self._app_config.strict_level
            config.strict_cooldown_minutes = int(
                getattr(self._app_config, "strict_cooldown_minutes", 5) or 5
            )
            config.strict_passcode_hash = str(
                getattr(self._app_config, "strict_passcode_hash", "") or ""
            )

        remaining_unlocks = self._daily_progress.remaining_unlocks_today()
        if remaining_unlocks is not None:
            config.max_esc = min(config.max_esc, remaining_unlocks)

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

    def _request_exit(self, scope_label: str) -> bool:
        """统一的「提前结束」流程；严格模式下要过冷静期/字符/口令。"""

        controller = self._session_controller
        if not controller.is_active:
            return False
        gate = controller.request_early_exit()
        if gate.policy.is_strict:
            dialog = ExitGateDialog(gate, self._session_view or self)
            if not dialog.exec():
                return False
            return bool(gate.released)
        return ask_confirmation(
            self._session_view or self,
            f"提前结束{scope_label}？",
            "当前进度会保存到历史记录，今天会记一次破功。",
            confirm_text="结束并保存",
            cancel_text="继续专注",
            destructive=True,
        )

    def _confirm_end_session(self):
        if self._request_exit("本次专注"):
            self._session_controller.terminate(force=True)

    def _hide_session_to_tray(self):
        if self._session_view:
            self._session_view.hide(to_tray=True)
        if self._tray.isVisible():
            self._tray.showMessage(
                "专注仍在继续", "点击托盘图标可重新打开专注窗口。",
                QSystemTrayIcon.MessageIcon.Information, 2500,
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
        self._overlay_service.hide_overlay()
        self._overlay_service.hide_break_window()
        if self._quitting:
            return
        completion = CompletionWindow(record)
        completion.show()
        completion.raise_()
        completion.activateWindow()
        completion.exec()
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _on_session_record_saved(self, record):
        completed = getattr(record, "outcome", "") == "completed"
        terminated = getattr(record, "outcome", "") == "terminated"
        achieved_minutes = max(0, getattr(record, "actual_focus_seconds", 0)) // 60
        self._data_store.update_today_goal_from_session(achieved_minutes, completed, terminated)
        self._daily_goal_widget.reload_goal()
        self._calendar_page.refresh()
        self._trend_page.refresh()

    def _on_foreground_change(
        self,
        process_name: str,
        window_title: str,
        executable_path: str = "",
        process_id: int = 0,
    ):
        self._activity_tracker.on_foreground_change(
            process_name,
            window_title,
            executable_path,
        )
        self._session_controller.on_foreground_change(
            process_name,
            window_title,
            executable_path,
            process_id,
        )

    def _on_usage_updated(self, process_name: str) -> None:
        if self._quitting or process_name == "__focus_capsule__":
            return
        # A foreground switch flushes the app that was just left. Only enforce
        # a limit when that app is still the active window; otherwise an old
        # app could cover the newly selected one with a stale blocking overlay.
        if self._window_monitor.last_process != process_name:
            return
        exceeded = self._daily_progress.exceeded_usage_limit(process_name)
        if exceeded is None:
            return
        self._overlay_service.show_usage_limit(process_name)
        label, used, limit = exceeded
        self._tray.setToolTip(f"专注舱 · {label} 已使用 {used}/{limit} 分钟")
        self._daily_goal_widget.reload_goal()

    def _open_category_manager(self) -> None:
        dialog = AppCategoryDialog(self._data_store, self)
        dialog.categories_saved.connect(self._on_categories_saved)
        dialog.exec()

    def _on_categories_saved(self, config) -> None:
        self._app_config = config
        self._trend_service.set_app_config(config)
        self._daily_progress.set_app_config(config)
        self._daily_goal_widget.update_app_config(config)
        self._calendar_page.refresh()
        self._trend_page.refresh()

    def _set_mode(self, mode_id: int) -> None:
        self._set_page(mode_id)

    # ------------------------------------------------------------------
    # Schedule enforcement
    # ------------------------------------------------------------------

    def _load_and_start_schedule(self) -> None:
        self._schedule_panel.load_rules()
        self._schedule_manager.start()

    def _on_schedule_activated(self, rule) -> None:
        if self._quitting or self._session_controller.is_active:
            return
        time_range = (
            f"{rule.start_hour:02d}:{rule.start_minute:02d}–"
            f"{rule.end_hour:02d}:{rule.end_minute:02d}"
        )
        self._tray.showMessage(
            "日程锁定已生效", f"{time_range} 期间只能使用已允许的应用",
            QSystemTrayIcon.MessageIcon.Information, 3000,
        )
        self._on_tray_update(True)
        self._schedule_panel.refresh_active_status()
        self._start_schedule_session(rule)

    def _on_schedule_released(self, _rule) -> None:
        if self._quitting:
            return
        if self._session_controller.is_active:
            self._session_controller.finish_scheduled_session()
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
            "日程锁定已解除", "锁定时段结束，可自由使用应用",
            QSystemTrayIcon.MessageIcon.Information, 2500,
        )
        self._on_tray_update(False)
        self._schedule_panel.refresh_active_status()

    def _enforce_active_schedule_for_current_window(self) -> None:
        if self._quitting or self._session_controller.is_active:
            return
        if self._window_monitor.is_focus_capsule_foreground:
            return
        process_name = self._window_monitor.last_process
        window_title = self._window_monitor.last_title
        executable_path = self._window_monitor.last_executable_path
        if process_name:
            self._on_schedule_foreground_check(
                process_name,
                window_title,
                executable_path,
                self._window_monitor.last_pid,
            )

    def _start_schedule_session(self, rule: ScheduleRule):
        if not rule.whitelisted_apps:
            show_information(self, "通知", "日程锁定规则不允许任何应用，请先设置允许的应用。")
            return
        remaining_seconds = max(60, _seconds_until_next_boundary(rule))
        config = FocusConfig(
            duration_minutes=max(1, (remaining_seconds + 59) // 60),
            mode=getattr(rule, "mode", "Deep") or "Deep",
            goal="通过日程锁定进行专注",
            whitelist=rule.whitelisted_apps,
            max_esc=getattr(rule, "max_esc", 0),
            esc_break_minutes=getattr(rule, "esc_break_minutes", 3),
            allowed_app_paths=dict(getattr(rule, "allowed_app_paths", {})),
            source="schedule",
            strict_level=getattr(rule, "strict_level", "off") or "off",
            strict_cooldown_minutes=getattr(rule, "strict_cooldown_minutes", 5),
            strict_passcode_hash=(
                getattr(rule, "strict_passcode_hash", "")
                or str(getattr(self._app_config, "strict_passcode_hash", "") or "")
            ),
            snooze_quota=getattr(rule, "snooze_quota", 2),
            schedule_label=getattr(rule, "label", "") or "日程锁定",
            schedule_start=f"{rule.start_hour:02d}:{rule.start_minute:02d}",
            schedule_end=f"{rule.end_hour:02d}:{rule.end_minute:02d}",
        )
        remaining_unlocks = self._daily_progress.remaining_unlocks_today()
        if remaining_unlocks is not None:
            config.max_esc = min(config.max_esc, remaining_unlocks)
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
        if self._request_exit("日程锁定"):
            self._session_controller.terminate(force=True)
            self._schedule_manager.suppress_active_rule()

    def _on_schedule_foreground_check(
        self,
        process_name: str,
        _window_title: str,
        executable_path: str = "",
        process_id: int = 0,
    ) -> None:
        if process_name == "__focus_capsule__":
            return
        if self._session_controller.is_active:
            return
        if not self._schedule_manager.is_active:
            return
        if not self._schedule_manager.is_process_allowed(
            process_name,
            executable_path,
            process_id,
        ):
            system_processes = {"explorer.exe", "shell.exe", "windows.ui.shell.lightswitch.exe"}
            if process_name in system_processes:
                return
            rule = self._schedule_manager.active_rule
            first_app = rule.whitelisted_apps[0] if rule and rule.whitelisted_apps else process_name
            if not self._overlay_service.is_overlay_visible():
                self._overlay_service.show_overlay(
                    first_app, return_seconds=5,
                    allowed_apps=rule.whitelisted_apps if rule else None,
                    allowed_app_paths=(
                        dict(getattr(rule, "allowed_app_paths", {})) if rule else None
                    ),
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

    def _on_tray_activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
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
            if not self._request_exit("专注"):
                return
            self._quitting = True
            self._session_controller.terminate(force=True)
        else:
            self._quitting = True
        T.set_focused(False)
        self._refresh_global_style()
        self._window_monitor.stop()
        self._activity_tracker.stop()
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
