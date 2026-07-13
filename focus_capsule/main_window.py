"""Primary planning window and application lifecycle coordination."""

from __future__ import annotations

from PyQt6.QtCore import Qt
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
    QSizePolicy,
    QStackedWidget,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from focus_capsule.controller import SessionController, SessionUpdate
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
from focus_capsule.widgets import FocusRing

MODE_LABELS = {
    "Light": "轻柔记录",
    "Standard": "标准提醒",
    "Deep": "深度拦截",
}


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("专注舱 · Focus Capsule")
        self.setObjectName("appWindow")
        self.setMinimumSize(900, 620)
        self.resize(1120, 740)

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

        self._session_controller.update_requested.connect(self._on_session_update)
        self._session_controller.session_completed.connect(self._on_session_completed)
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
        root.setContentsMargins(30, 22, 30, 26)
        root.setSpacing(20)

        header = QHBoxLayout()
        header.setSpacing(12)

        brand_mark = QLabel("◉")
        brand_mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand_mark.setFixedSize(42, 42)
        brand_mark.setStyleSheet(
            "background:#17342F;color:#77D9C6;border:1px solid #2D5B50;"
            "border-radius:13px;font-size:20px;font-weight:700;"
        )
        header.addWidget(brand_mark)

        brand_text = QVBoxLayout()
        brand_text.setSpacing(1)
        title = QLabel("专注舱")
        title.setObjectName("brandTitle")
        subtitle = QLabel("Focus Capsule · 把注意力留给真正重要的事")
        subtitle.setObjectName("brandSubtitle")
        brand_text.addWidget(title)
        brand_text.addWidget(subtitle)
        header.addLayout(brand_text)
        header.addStretch()

        privacy = QLabel("●  数据仅保存在本机")
        privacy.setObjectName("tinyMuted")
        privacy.setToolTip("专注记录不会上传到云端")
        header.addWidget(privacy)

        history_button = QPushButton("历史记录")
        history_button.setObjectName("ghostButton")
        history_button.setAccessibleName("打开专注历史记录")
        history_button.clicked.connect(self._show_history)
        header.addWidget(history_button)

        quit_button = QPushButton("退出")
        quit_button.setObjectName("ghostButton")
        quit_button.clicked.connect(self._quit_app)
        header.addWidget(quit_button)
        root.addLayout(header)

        divider = QFrame()
        divider.setObjectName("divider")
        divider.setFrameShape(QFrame.Shape.HLine)
        root.addWidget(divider)

        content = QHBoxLayout()
        content.setSpacing(22)

        self._settings_panel.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        self._schedule_panel.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        # Exclusive mode switch between a manual focus plan and scheduled lock.
        self._mode_container = QFrame()
        self._mode_container.setObjectName("softPanel")
        mode_layout = QHBoxLayout(self._mode_container)
        mode_layout.setContentsMargins(6, 4, 6, 4)
        mode_layout.setSpacing(4)

        self._btn_pomodoro_mode = QPushButton("专注计划")
        self._btn_pomodoro_mode.setObjectName("primaryButton")
        self._btn_pomodoro_mode.setCheckable(True)
        self._btn_pomodoro_mode.setChecked(True)
        self._btn_pomodoro_mode.setAccessibleName("切换到专注计划")

        self._btn_schedule_mode = QPushButton("日程锁定")
        self._btn_schedule_mode.setObjectName("ghostButton")
        self._btn_schedule_mode.setCheckable(True)
        self._btn_schedule_mode.setAccessibleName("切换到日程锁定")

        self._mode_group = QButtonGroup(self)
        self._mode_group.setExclusive(True)
        self._mode_group.addButton(self._btn_pomodoro_mode, 0)
        self._mode_group.addButton(self._btn_schedule_mode, 1)
        self._mode_group.idClicked.connect(self._set_mode)
        mode_layout.addWidget(self._btn_pomodoro_mode)
        mode_layout.addWidget(self._btn_schedule_mode)
        root.addWidget(self._mode_container)

        # Content containers
        self._content_stack_pomodoro = QWidget()
        pomodoro_layout = QHBoxLayout(self._content_stack_pomodoro)
        pomodoro_layout.setContentsMargins(0, 0, 0, 0)
        pomodoro_layout.setSpacing(22)
        pomodoro_layout.addWidget(self._settings_panel, 1)

        self._content_stack_schedule = QWidget()
        schedule_layout = QHBoxLayout(self._content_stack_schedule)
        schedule_layout.setContentsMargins(0, 0, 0, 0)
        schedule_layout.setSpacing(22)
        schedule_layout.addWidget(self._schedule_panel, 1)

        summary = self._build_summary_panel()
        pomodoro_layout.addWidget(summary, 0)

        # Empty placeholder for schedule tab so summary panel is only shown in pomodoro
        self._content_stack_schedule_layout = schedule_layout

        self._content_stack = QStackedWidget()
        self._content_stack.addWidget(self._content_stack_pomodoro)
        self._content_stack.addWidget(self._content_stack_schedule)
        content.addWidget(self._content_stack, 1)
        root.addLayout(content, 1)

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
        self._summary_goal.setStyleSheet("" if goal else "color:#718097;")

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

    def _on_foreground_change(self, process_name: str, window_title: str):
        self._session_controller.on_foreground_change(process_name, window_title)

    # ------------------------------------------------------------------
    # Mode toggle
    # ------------------------------------------------------------------

    def _set_mode(self, mode_id: int) -> None:
        schedule_mode = mode_id == 1
        self._btn_pomodoro_mode.setChecked(not schedule_mode)
        self._btn_schedule_mode.setChecked(schedule_mode)
        self._content_stack.setCurrentIndex(1 if schedule_mode else 0)

        if schedule_mode:
            self._btn_pomodoro_mode.setObjectName("ghostButton")
            self._btn_schedule_mode.setObjectName("primaryButton")
        else:
            self._btn_pomodoro_mode.setObjectName("primaryButton")
            self._btn_schedule_mode.setObjectName("ghostButton")
        for btn in (self._btn_pomodoro_mode, self._btn_schedule_mode):
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self._update_summary()

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
            max_esc=0,
            esc_break_minutes=3,
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
                self._overlay_service.show_overlay(first_app, return_seconds=5)
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
