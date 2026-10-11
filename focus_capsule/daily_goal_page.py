"""Today's overview page.

The page deliberately exposes a simple user flow:

1. Write one concrete task.
2. Check tasks off as they are finished.
3. Review progress backed by real task and focus-session data.

Internal agent stages are not presented to the user.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from focus_capsule.daily_targets_dialog import DailyTargetsDialog
from focus_capsule.data_models import (
    AppConfig,
    DailyGoal,
    DailyGoalTargets,
    GoalStatus,
    TaskItem,
    china_today,
)
from focus_capsule.data_store import DataStore


class DailyGoalPage(QWidget):
    """A clear, editable overview of today's work."""

    open_focus_plan_requested = pyqtSignal()

    EXAMPLE_TASKS = (
        "完成一份文档的第一稿",
        "学习或练习 45 分钟",
        "处理一件拖延很久的事",
    )

    def __init__(
        self,
        data_store: DataStore,
        trend_service: Optional[Any] = None,
        ai_service: Optional[Any] = None,
        config: Optional[Dict[str, Any]] = None,
        parent: Optional[QWidget] = None,
        progress_service: Optional[Any] = None,
    ):
        super().__init__(parent)
        self._data_store = data_store
        self._trend_service = trend_service
        self._ai_service = ai_service
        self._config = config or {}
        self._app_config = config if isinstance(config, AppConfig) else AppConfig()
        self._progress_service = progress_service
        self._goal: Optional[DailyGoal] = None

        self._init_ui()
        self._load_today_goal()

    # ── UI construction ──────────────────────────────────────

    def _init_ui(self) -> None:
        self.setObjectName("DailyGoalPage")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 28)
        main_layout.setSpacing(16)

        main_layout.addWidget(self._build_goal_card())

        body_layout = QHBoxLayout()
        body_layout.setSpacing(16)
        body_layout.addWidget(self._build_task_card(), 2)
        body_layout.addWidget(self._build_progress_card(), 1)
        main_layout.addLayout(body_layout)

        self.targets_card = self._build_targets_card()
        main_layout.addWidget(self.targets_card)

        self.report_card = self._build_report_card()
        self.report_card.hide()
        main_layout.addWidget(self.report_card)
        main_layout.addStretch()

    def _build_goal_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("sectionCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(10)

        heading_row = QHBoxLayout()
        eyebrow = QLabel("今天最重要的一件事")
        eyebrow.setObjectName("eyebrow")
        heading_row.addWidget(eyebrow)
        heading_row.addStretch()
        targets_button = QPushButton("设置今日目标")
        targets_button.setObjectName("presetButton")
        targets_button.setCursor(Qt.CursorShape.PointingHandCursor)
        targets_button.clicked.connect(self._open_targets_dialog)
        heading_row.addWidget(targets_button)
        layout.addLayout(heading_row)

        self.goal_heading = QLabel()
        self.goal_heading.setObjectName("heroGoal")
        self.goal_heading.setWordWrap(True)
        layout.addWidget(self.goal_heading)

        self.goal_help = QLabel()
        self.goal_help.setObjectName("bodyMuted")
        self.goal_help.setWordWrap(True)
        layout.addWidget(self.goal_help)

        input_row = QHBoxLayout()
        input_row.setSpacing(10)

        self.goal_input = QLineEdit()
        self.goal_input.setObjectName("goalInput")
        self.goal_input.setClearButtonEnabled(True)
        self.goal_input.setAccessibleName("今日任务输入框")
        self.goal_input.textChanged.connect(
            lambda text: self.submit_button.setEnabled(bool(text.strip()))
        )
        self.goal_input.returnPressed.connect(self._submit_input)
        input_row.addWidget(self.goal_input, 1)

        self.submit_button = QPushButton()
        self.submit_button.setObjectName("primaryButton")
        self.submit_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.submit_button.setMinimumWidth(132)
        self.submit_button.setEnabled(False)
        self.submit_button.clicked.connect(self._submit_input)
        input_row.addWidget(self.submit_button)
        layout.addLayout(input_row)

        self.input_hint = QLabel("尽量写成可以勾选完成的结果，例如“完成报告第一稿”。")
        self.input_hint.setObjectName("bodyTertiary")
        self.input_hint.setWordWrap(True)
        layout.addWidget(self.input_hint)

        self.preset_widget = QWidget()
        preset_layout = QHBoxLayout(self.preset_widget)
        preset_layout.setContentsMargins(0, 2, 0, 0)
        preset_layout.setSpacing(8)

        preset_label = QLabel("不知道写什么？")
        preset_label.setObjectName("bodyTertiary")
        preset_layout.addWidget(preset_label)

        for example in self.EXAMPLE_TASKS:
            button = QPushButton(example)
            button.setObjectName("presetButton")
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda _, text=example: self._use_example(text))
            preset_layout.addWidget(button)
        preset_layout.addStretch()
        layout.addWidget(self.preset_widget)

        self.status_label = QLabel()
        self.status_label.setObjectName("hint")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        return card

    def _build_task_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("sectionCard")
        card.setMinimumHeight(260)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(22, 20, 22, 22)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("今天的任务")
        title.setObjectName("sectionTitle")
        header.addWidget(title)
        header.addStretch()
        self.task_count_label = QLabel("0 项")
        self.task_count_label.setObjectName("hint")
        header.addWidget(self.task_count_label)
        layout.addLayout(header)

        self.task_layout = QVBoxLayout()
        self.task_layout.setSpacing(8)
        layout.addLayout(self.task_layout)
        layout.addStretch()
        return card

    def _build_progress_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("sectionCard")
        card.setMinimumWidth(280)
        card.setMaximumWidth(380)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(22, 20, 22, 22)
        layout.setSpacing(12)

        title = QLabel("今天的进展")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        self.completion_value = QLabel("0/0")
        self.completion_value.setObjectName("heroMetric")
        layout.addWidget(self.completion_value)

        completion_caption = QLabel("已完成任务")
        completion_caption.setObjectName("statCaption")
        layout.addWidget(completion_caption)

        self.task_progress = QProgressBar()
        self.task_progress.setRange(0, 100)
        self.task_progress.setValue(0)
        self.task_progress.setTextVisible(False)
        layout.addWidget(self.task_progress)
        layout.addSpacing(6)

        focus_row = QHBoxLayout()
        focus_key = QLabel("实际专注")
        focus_key.setObjectName("summaryKey")
        focus_row.addWidget(focus_key)
        focus_row.addStretch()
        self.focus_value = QLabel("0 分钟")
        self.focus_value.setObjectName("summaryValue")
        focus_row.addWidget(self.focus_value)
        layout.addLayout(focus_row)

        session_row = QHBoxLayout()
        session_key = QLabel("专注轮次")
        session_key.setObjectName("summaryKey")
        session_row.addWidget(session_key)
        session_row.addStretch()
        self.session_value = QLabel("0")
        self.session_value.setObjectName("summaryValue")
        session_row.addWidget(self.session_value)
        layout.addLayout(session_row)

        self.progress_note = QLabel()
        self.progress_note.setObjectName("bodyTertiary")
        self.progress_note.setWordWrap(True)
        layout.addWidget(self.progress_note)
        layout.addStretch()

        focus_button = QPushButton("去专注计划")
        focus_button.setObjectName("primaryButton")
        focus_button.setCursor(Qt.CursorShape.PointingHandCursor)
        focus_button.clicked.connect(self.open_focus_plan_requested.emit)
        layout.addWidget(focus_button)
        return card

    def _build_targets_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("sectionCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(22, 20, 22, 22)
        layout.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("今日目标进度")
        title.setObjectName("sectionTitle")
        header.addWidget(title)
        header.addStretch()
        self.targets_count_label = QLabel("0 项")
        self.targets_count_label.setObjectName("hint")
        header.addWidget(self.targets_count_label)
        layout.addLayout(header)

        self.targets_layout = QVBoxLayout()
        self.targets_layout.setSpacing(8)
        layout.addLayout(self.targets_layout)
        return card

    def _build_report_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("sectionCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(22, 20, 22, 22)
        layout.setSpacing(8)

        title = QLabel("今日复盘")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        self.report_text = QLabel()
        self.report_text.setObjectName("insightText")
        self.report_text.setWordWrap(True)
        self.report_text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.report_text)
        return card

    # ── Goal and task interaction ─────────────────────────────

    @staticmethod
    def _has_meaningful_goal(goal: Optional[DailyGoal]) -> bool:
        return bool(goal and (goal.title.strip() or any(t.title.strip() for t in goal.tasks)))

    def _load_today_goal(self) -> None:
        today = china_today().isoformat()
        loaded = self._data_store.get_goal_for_date(today)
        self._goal = loaded if self._has_meaningful_goal(loaded) else None
        self._render_goal_state()

    def _render_goal_state(self) -> None:
        has_goal = self._has_meaningful_goal(self._goal)
        if has_goal and self._goal:
            self.goal_heading.setText(self._goal.title or "今天的任务")
            self.goal_help.setText("把目标拆成几个能勾选完成的小任务，会更容易开始。")
            self.goal_input.setPlaceholderText("再添加一项具体任务")
            self.submit_button.setText("添加任务")
            self.preset_widget.hide()
            if not self.status_label.text():
                self.status_label.setText("任务会保存在本机，完成后直接勾选即可。")
        else:
            self.goal_heading.setText("今天想完成什么？")
            self.goal_help.setText("先写下一件最重要、今天能够完成的事。不需要一次规划得很完美。")
            self.goal_input.setPlaceholderText("例如：完成报告第一稿")
            self.submit_button.setText("创建今日任务")
            self.preset_widget.show()
            self.status_label.setText("输入后按 Enter，或点击右侧按钮创建。")

        self._populate_task_panel()
        self._update_progress_display()

    def _use_example(self, text: str) -> None:
        self.goal_input.setText(text)
        self.goal_input.setFocus(Qt.FocusReason.OtherFocusReason)
        self.goal_input.setCursorPosition(len(text))

    def _submit_input(self) -> None:
        title = self.goal_input.text().strip()
        if not title:
            self.status_label.setText("请先写下一项具体任务。")
            self.goal_input.setFocus(Qt.FocusReason.OtherFocusReason)
            return

        if not self._has_meaningful_goal(self._goal):
            self.create_new_goal(title, [title])
            self.status_label.setText("今日任务已创建。完成后直接勾选，或继续添加任务。")
        elif self._goal:
            existing = {task.title.strip().casefold() for task in self._goal.tasks}
            if title.casefold() in existing:
                self.status_label.setText("这项任务已经在今天的列表里了。")
                return
            self._goal.tasks.append(TaskItem(title=title))
            self._data_store.save_daily_goal(self._goal)
            self.goal_input.clear()
            self.status_label.setText("已添加到今天的任务。")
            self._render_goal_state()

    def _populate_task_panel(self) -> None:
        self._clear_layout(self.task_layout)
        tasks = self._goal.tasks if self._goal else []
        self.task_count_label.setText(f"{len(tasks)} 项")

        if not tasks:
            empty = QFrame()
            empty.setObjectName("softPanel")
            empty_layout = QVBoxLayout(empty)
            empty_layout.setContentsMargins(18, 18, 18, 18)
            empty_layout.setSpacing(4)

            empty_title = QLabel("还没有任务")
            empty_title.setObjectName("summaryGoal")
            empty_layout.addWidget(empty_title)

            empty_note = QLabel("在上方输入一件今天想完成的事，它会出现在这里。")
            empty_note.setObjectName("bodyMuted")
            empty_note.setWordWrap(True)
            empty_layout.addWidget(empty_note)
            self.task_layout.addWidget(empty)
            return

        for task in tasks:
            self.task_layout.addWidget(self._create_task_row(task))

    @staticmethod
    def _clear_layout(layout: QVBoxLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def _create_task_row(self, task: TaskItem) -> QFrame:
        row = QFrame()
        row.setObjectName("softPanel")
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(14, 10, 14, 10)

        checkbox = QCheckBox(task.title)
        checkbox.setChecked(task.status == GoalStatus.DONE)
        checkbox.setCursor(Qt.CursorShape.PointingHandCursor)
        checkbox.setAccessibleName(f"任务：{task.title}")
        checkbox.toggled.connect(lambda checked, item=task: self._toggle_task(item, checked))
        row_layout.addWidget(checkbox, 1)
        return row

    def _toggle_task(self, task: TaskItem, checked: bool) -> None:
        if not self._goal:
            return
        task.status = GoalStatus.DONE if checked else GoalStatus.TODO
        self._data_store.save_daily_goal(self._goal)
        self._update_progress_display()

        done, total = self._task_counts()
        if total and done == total:
            self.status_label.setText("今天的任务都完成了。")
        else:
            self.status_label.setText(f"已完成 {done}/{total} 项任务。")

    # ── Real progress and review data ─────────────────────────

    def _task_counts(self) -> tuple[int, int]:
        tasks = self._goal.tasks if self._goal else []
        done = sum(1 for task in tasks if task.status == GoalStatus.DONE)
        return done, len(tasks)

    def _today_summary(self) -> Optional[Any]:
        if not self._trend_service or not hasattr(self._trend_service, "get_today_summary"):
            return None
        try:
            return self._trend_service.get_today_summary()
        except Exception:
            return None

    @staticmethod
    def _format_minutes(minutes: int) -> str:
        minutes = max(0, int(minutes))
        hours, remainder = divmod(minutes, 60)
        if hours and remainder:
            return f"{hours} 小时 {remainder} 分钟"
        if hours:
            return f"{hours} 小时"
        return f"{remainder} 分钟"

    def _update_progress_display(self) -> None:
        done, total = self._task_counts()
        rate = round(done / total * 100) if total else 0
        self.completion_value.setText(f"{done}/{total}")
        self.task_progress.setValue(rate)

        summary = self._today_summary()
        focus_minutes = max(0, int(getattr(summary, "total_focus_seconds", 0))) // 60
        session_count = max(0, int(getattr(summary, "session_count", 0)))
        self.focus_value.setText(self._format_minutes(focus_minutes))
        self.session_value.setText(str(session_count))

        if not self._goal:
            note = "创建任务后，这里会显示完成进度。"
        elif not done and session_count == 0:
            note = "还没有产生专注数据；这里不会提前给你打分。"
        else:
            note = "这里的数据只来自你实际勾选的任务和已经结束的专注记录。"
        self.progress_note.setText(note)
        self._refresh_targets()
        self._refresh_report(summary)

    def _refresh_targets(self) -> None:
        self._clear_layout(self.targets_layout)
        progress = None
        if self._progress_service is not None:
            try:
                progress = self._progress_service.progress_for_date(china_today())
            except Exception:
                progress = None

        items = list(getattr(progress, "items", []) or [])
        self.targets_count_label.setText(f"{len(items)} 项")
        if not items:
            empty = QFrame()
            empty.setObjectName("softPanel")
            empty_layout = QVBoxLayout(empty)
            empty_layout.setContentsMargins(16, 14, 16, 14)
            empty_layout.setSpacing(3)
            empty_title = QLabel("还没有设置量化目标")
            empty_title.setObjectName("summaryGoal")
            empty_layout.addWidget(empty_title)
            empty_note = QLabel(
                "可以设置专注时长、次数、分心上限、应用使用限制或临时解锁次数。"
            )
            empty_note.setObjectName("bodyMuted")
            empty_note.setWordWrap(True)
            empty_layout.addWidget(empty_note)
            self.targets_layout.addWidget(empty)
            return

        for item in items:
            row = QFrame()
            row.setObjectName("softPanel")
            row_layout = QVBoxLayout(row)
            row_layout.setContentsMargins(14, 10, 14, 10)
            row_layout.setSpacing(6)

            line = QHBoxLayout()
            label = QLabel(item.label)
            label.setObjectName("summaryGoal")
            line.addWidget(label)
            line.addStretch()

            if item.direction == "maximum":
                suffix = "已超出" if item.status == "exceeded" else "限制内"
            else:
                suffix = "已完成" if item.status == "complete" else "进行中"
            value = QLabel(f"{item.value_text} · {suffix}")
            value.setObjectName("hint")
            line.addWidget(value)
            row_layout.addLayout(line)

            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(item.percent)
            bar.setTextVisible(False)
            row_layout.addWidget(bar)
            self.targets_layout.addWidget(row)

    def _open_targets_dialog(self) -> None:
        entry = self._data_store.get_today_goal()
        dialog = DailyTargetsDialog(entry.targets, self._app_config, self)
        dialog.targets_saved.connect(self._save_targets)
        dialog.exec()

    def _save_targets(self, targets: DailyGoalTargets) -> None:
        self._data_store.save_daily_targets(china_today().isoformat(), targets)
        self.status_label.setText("今日目标已保存，进度会根据真实记录自动更新。")
        self._refresh_targets()

    def _refresh_report(self, summary: Optional[Any]) -> None:
        session_count = max(0, int(getattr(summary, "session_count", 0)))
        if session_count == 0:
            self.report_card.hide()
            self.report_text.clear()
            return

        today = china_today().isoformat()
        report = None
        if hasattr(self._data_store, "get_report"):
            try:
                report = self._data_store.get_report(today)
            except Exception:
                report = None

        report_summary = str(getattr(report, "summary", "")).strip()
        if not report_summary:
            focus_minutes = max(0, int(getattr(summary, "total_focus_seconds", 0))) // 60
            completed = max(0, int(getattr(summary, "completed_count", 0)))
            report_summary = (
                f"今天已经进行了 {session_count} 轮专注，"
                f"累计 {self._format_minutes(focus_minutes)}。"
                f"其中完整完成 {completed} 轮。"
            )

        self.report_text.setText(report_summary)
        self.report_card.show()

    # ── Public API ────────────────────────────────────────────

    def reload_goal(self) -> None:
        self._load_today_goal()

    def refresh(self) -> None:
        self.reload_goal()

    def update_app_config(self, config: AppConfig) -> None:
        self._app_config = config
        self._config = config
        self._refresh_targets()

    def create_new_goal(
        self,
        title: str,
        tasks: List[str],
        priority: str = "medium",
    ) -> None:
        clean_title = title.strip()
        clean_tasks = [task.strip() for task in tasks if task.strip()]
        new_goal = DailyGoal(
            date=china_today().isoformat(),
            title=clean_title,
            tasks=[TaskItem(title=task, priority=priority) for task in clean_tasks],
        )
        self._data_store.save_daily_goal(new_goal)
        self._goal = new_goal
        self.goal_input.clear()
        self._render_goal_state()

    def start_autonomous_execution(self) -> None:
        """Backward-compatible entry point that opens the real focus planner."""
        self.status_label.setText("请在“专注计划”中选择应用和时长，然后开始专注。")
        self.open_focus_plan_requested.emit()


DailyGoalWidget = DailyGoalPage
