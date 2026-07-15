"""Daily goal and AI daily report page.

Shows today's progress toward a configurable daily focus goal,
the AI-generated (or local fallback) daily report, and quick links
to view past reports.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton,
    QSizePolicy, QVBoxLayout, QWidget, QSpinBox,
)

from focus_capsule.data_models import DailyReport, DailyGoalEntry, AppConfig, china_today
from focus_capsule.data_store import DataStore
from focus_capsule.ai_report_service import AIReportService
from focus_capsule.trend_service import TrendService
from focus_capsule.theme import (
    SURFACE_1, SURFACE_2, SURFACE_3, INPUT_BG,
    ACCENT, ACCENT_DARK_BG, WARNING, SUCCESS, DANGER,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_TERTIARY,
    BORDER_SUBTLE, RADIUS_LG, RADIUS_MD,
    FONT_PAGE_TITLE, FONT_SECTION, FONT_AUX, FONT_META,
    WEIGHT_TITLE, WEIGHT_SECTION,
)


class DailyGoalWidget(QWidget):
    """Shows daily goal progress ring, goal setting, and AI report."""

    def __init__(
        self,
        data_store: DataStore,
        trend_service: TrendService,
        ai_service: AIReportService,
        app_config: AppConfig,
        parent=None,
    ):
        super().__init__(parent)
        self._store = data_store
        self._trend = trend_service
        self._ai = ai_service
        self._config = app_config
        self._setup_ui()
        self.refresh()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setSpacing(18)

        # Header
        layout.setObjectName("DailyGoalWidget")

        # Header
        header = QHBoxLayout()
        title = QLabel("每日目标")
        title.setObjectName("pageTitle")
        header.addWidget(title)
        header.addStretch()
        generate_btn = QPushButton("生成今日日报")
        generate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        generate_btn.clicked.connect(self._generate_report)
        header.addWidget(generate_btn)
        layout.addLayout(header)

        subtitle = QLabel("设定每天想达成的专注时间，看看你是否离目标更近一步")
        subtitle.setObjectName("subtitle")
        layout.addWidget(subtitle)

        # Goal + progress card
        goal_card = QFrame()
        goal_card.setObjectName("panel")
        goal_layout = QVBoxLayout(goal_card)
        goal_layout.setContentsMargins(22, 18, 22, 18)
        goal_layout.setSpacing(14)

        goal_header = QHBoxLayout()
        goal_title = QLabel("今日进度")
        goal_title.setObjectName("sectionTitle")
        goal_header.addWidget(goal_title)
        goal_header.addStretch()
        self._goal_switch_btn = QPushButton("关闭目标")
        self._goal_switch_btn.setObjectName("ghostButton")
        self._goal_switch_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._goal_switch_btn.clicked.connect(self._toggle_goal)
        goal_header.addWidget(self._goal_switch_btn)
        goal_layout.addLayout(goal_header)

        # Progress bar
        progress_row = QHBoxLayout()
        progress_row.setSpacing(10)
        self._goal_progress_bg = QFrame()
        self._goal_progress_bg.setFixedHeight(10)
        self._goal_progress_bg.setStyleSheet(f"background:{INPUT_BG};border-radius:5px;")
        prog_layout = QHBoxLayout(self._goal_progress_bg)
        prog_layout.setContentsMargins(0, 0, 0, 0)
        self._goal_probar_fill = QFrame()
        self._goal_probar_fill.setFixedHeight(8)
        self._goal_probar_fill.setStyleSheet(f"background:{ACCENT};border-radius:4px;")
        prog_layout.addWidget(self._goal_probar_fill)
        prog_layout.addStretch()
        progress_row.addWidget(self._goal_progress_bg, 1)
        goal_layout.addLayout(progress_row)

        # Stats row
        stats_row = QHBoxLayout()
        stats_row.setSpacing(20)
        self._goal_achieved_label = QLabel("0 分钟")
        self._goal_achieved_label.setObjectName("statValue")
        stats_row.addWidget(self._goal_achieved_label)
        slash = QLabel(" / ")
        slash.setStyleSheet(f"color:{TEXT_TERTIARY};")
        stats_row.addWidget(slash)
        self._goal_target_label = QLabel("120 分钟")
        self._goal_target_label.setObjectName("summaryValue")
        stats_row.addWidget(self._goal_target_label)
        stats_row.addStretch()
        self._goal_pct_label = QLabel("0%")
        self._goal_pct_label.setObjectName("summaryValue")
        self._goal_pct_label.setStyleSheet(f"color:{ACCENT};")
        stats_row.addWidget(self._goal_pct_label)
        goal_layout.addLayout(stats_row)

        # Target setting
        target_row = QHBoxLayout()
        target_row.setSpacing(10)
        target_label = QLabel("每日目标：")
        target_label.setObjectName("hint")
        target_row.addWidget(target_label)
        self._target_spin = QSpinBox()
        self._target_spin.setRange(10, 480)
        self._target_spin.setSingleStep(10)
        self._target_spin.setSuffix(" 分钟")
        self._target_spin.setMinimumWidth(120)
        self._target_spin.setValue(self._config.daily_goal_minutes)
        self._target_spin.valueChanged.connect(self._on_target_changed)
        target_row.addWidget(self._target_spin)
        target_row.addStretch()
        goal_layout.addLayout(target_row)

        layout.addWidget(goal_card)

        # AI report card
        report_card = QFrame()
        report_card.setObjectName("panel")
        report_layout = QVBoxLayout(report_card)
        report_layout.setContentsMargins(22, 18, 22, 18)
        report_layout.setSpacing(12)

        report_header = QHBoxLayout()
        report_title = QLabel("今日日报")
        report_title.setObjectName("sectionTitle")
        report_header.addWidget(report_title)
        report_header.addStretch()
        self._report_source_label = QLabel("本地规则")
        self._report_source_label.setObjectName("hint")
        report_header.addWidget(self._report_source_label)
        report_layout.addLayout(report_header)

        self._report_summary = QLabel("还没有生成今日日报。点击上方按钮可以生成。")
        self._report_summary.setObjectName("summaryGoal")
        self._report_summary.setWordWrap(True)
        report_layout.addWidget(self._report_summary)

        self._highlights_label = QLabel()
        self._highlights_label.setWordWrap(True)
        report_layout.addWidget(self._highlights_label)

        self._suggestions_label = QLabel()
        self._suggestions_label.setWordWrap(True)
        report_layout.addWidget(self._suggestions_label)

        layout.addWidget(report_card, 1)

    def refresh(self):
        # Update goal progress
        today = china_today()
        goal_entry = self._store.get_today_goal()
        today_summary = self._trend.get_today_summary()
        achieved = today_summary.focus_minutes

        target = goal_entry.target_minutes or self._config.daily_goal_minutes
        self._target_spin.setValue(target)
        self._goal_target_label.setText(f"{target} 分钟")
        self._goal_achieved_label.setText(f"{achieved} 分钟")
        pct = min(1.0, achieved / target) if target else 0
        self._goal_pct_label.setText(f"{pct:.0%}")
        self._goal_probar_fill.setStyleSheet(
            f"background:{ACCENT};border-radius:4px;min-width:{int(pct * 200)}px;"
        )

        # Switch button text
        self._goal_switch_btn.setText("关闭目标" if self._config.daily_goal_enabled else "开启目标")

        # Load report
        report = self._store.get_report(today.isoformat())
        self._display_report(report)

    def _display_report(self, report: Optional[DailyReport]):
        if not report:
            self._report_summary.setText("还没有生成今日日报。点击上方按钮可以生成。")
            self._highlights_label.setText("")
            self._suggestions_label.setText("")
            self._report_source_label.setText("")
            return

        self._report_summary.setText(report.summary or "")
        self._report_source_label.setText(
            "AI 生成" if report.source == "ai" else "本地生成"
        )

        highlights_text = ""
        if report.highlights:
            highlights_text = "亮点\n" + "\n".join(f"  · {h}" for h in report.highlights)
        self._highlights_label.setText(highlights_text)
        self._highlights_label.setStyleSheet(f"color:{TEXT_SECONDARY};font-size:{FONT_AUX}px;")

        suggestions_text = ""
        if report.suggestions:
            suggestions_text = "建议\n" + "\n".join(f"  · {s}" for s in report.suggestions)
        self._suggestions_label.setText(suggestions_text)
        self._suggestions_label.setStyleSheet(f"color:{TEXT_SECONDARY};font-size:{FONT_AUX}px;")

    def _generate_report(self):
        report = self._ai.generate_for_today()
        self._display_report(report)

    def _toggle_goal(self):
        self._config.daily_goal_enabled = not self._config.daily_goal_enabled
        self._store.save_app_config(self._config)
        self.refresh()

    def _on_target_changed(self, value: int):
        self._config.daily_goal_minutes = value
        self._store.save_app_config(self._config)
        # Update today's goal entry
        entry = self._store.get_today_goal()
        entry.target_minutes = value
        self._store.save_goal(entry)
        self.refresh()
