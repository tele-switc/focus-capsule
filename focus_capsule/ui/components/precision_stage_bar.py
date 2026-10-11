"""Precision Stage Bar — 执行弧."""

from enum import Enum

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

import focus_capsule.theme as T


def _t(key: str, default: str = "") -> str:
    return T.get(key, default)


class Stage(str, Enum):
    """自主执行阶段."""

    GOAL = "goal"
    PLAN = "plan"
    EXECUTE = "execute"
    VERIFY = "verify"
    REVIEW = "review"


# ── 中文标签 + 配色 ─────────────────────────────────────────────

_STAGE_LABELS = {
    "goal":    "目标",
    "plan":    "计划",
    "execute": "执行",
    "verify":  "验证",
    "review":  "复盘",
}

_STATUS_TEXTS = [
    "正在定义目标…",
    "正在制定策略…",
    "正在精确执行…",
    "正在验证结果…",
    "正在生成洞察…",
]


class PrecisionStageBar(QWidget):
    """中央执行弧：目标 → 计划 → 执行 → 验证 → 复盘."""

    STAGES = ["goal", "plan", "execute", "verify", "review"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_stage: int | None = None
        self._is_running = False
        self._is_complete = False
        self._stage_widgets = []
        self._setup_ui()

    def _setup_ui(self):
        self.setObjectName("PrecisionStageBar")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(5)

        # Title
        title = QLabel("Precision Agent OS")
        title.setFont(QFont("Microsoft YaHei UI", 14, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"color: {_t('ACCENT', '#A08458')};")
        title.setObjectName("stageBarTitle")
        layout.addWidget(title)

        # Stage container
        stage_container = QWidget()
        stage_layout = QHBoxLayout(stage_container)
        stage_layout.setContentsMargins(0, 0, 0, 0)
        stage_layout.setSpacing(0)

        for i, stage in enumerate(self.STAGES):
            widget = self._create_stage_node(_STAGE_LABELS[stage], i)
            self._stage_widgets.append(widget)
            stage_layout.addWidget(widget)

            if i < len(self.STAGES) - 1:
                connector = QLabel("───")
                connector.setObjectName("stageConnector")
                connector.setStyleSheet(f"color: {_t('TEXT_TERTIARY', '#9A9285')}; font-size: 14px;")
                stage_layout.addWidget(connector)

        layout.addWidget(stage_container)
        layout.addSpacing(5)

        # Status text
        self._status_label = QLabel("正在载入今日状态…")
        self._status_label.setFont(QFont("Microsoft YaHei UI", 10))
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_label.setObjectName("stageStatus")
        layout.addWidget(self._status_label)

        self._update_stages()

    def _create_stage_node(self, label_text: str, index: int) -> QWidget:
        node = QWidget()
        node.setObjectName(f"stageNode{index}")
        node.setMinimumWidth(80)
        node.setMaximumWidth(100)

        vlayout = QVBoxLayout(node)
        vlayout.setContentsMargins(8, 6, 8, 6)
        vlayout.setSpacing(4)

        name_label = QLabel(label_text)
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setFont(QFont("Microsoft YaHei UI", 9, QFont.Weight.Medium))
        name_label.setObjectName("stageName")
        vlayout.addWidget(name_label)

        return node

    def set_active_stage(self, stage_index: int):
        """Set the active stage with animation."""
        if isinstance(stage_index, Stage):
            stage_index = list(Stage).index(stage_index)
        if stage_index < 0 or stage_index >= len(self.STAGES):
            return

        self._current_stage = stage_index
        self._is_running = True
        self._is_complete = False
        self._update_stages()

        self._status_label.setText(_STATUS_TEXTS[stage_index])
        self._pulse_active_node()

    def _update_stages(self):
        accent = _t("ACCENT", "#A08458")
        success = _t("SUCCESS", "#7A9968")
        for i, widget in enumerate(self._stage_widgets):
            if self._is_complete or (
                self._current_stage is not None and i < self._current_stage
            ):
                # completed: green
                for sub in widget.findChildren(QLabel):
                    sub.setStyleSheet(f"color: {success}; font-weight: bold; padding: 6px;")
                widget.setFixedHeight(50)
            elif self._current_stage is not None and i == self._current_stage:
                # active: gradient
                for sub in widget.findChildren(QLabel):
                    sub.setStyleSheet(
                        f"color: white; font-weight: bold; padding: 6px; "
                        f"border-radius: 10px; background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {accent}, stop:1 {success});"
                    )
                widget.setFixedHeight(50)
            else:
                # pending
                for sub in widget.findChildren(QLabel):
                    sub.setStyleSheet(f"color: {_t('TEXT_TERTIARY', '#9A9285')}; padding: 6px;")
                widget.setFixedHeight(50)

    def _pulse_active_node(self):
        if self._current_stage is None or self._current_stage >= len(self._stage_widgets):
            return

        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.timeout.connect(timer.deleteLater)
        timer.start(200)

    @property
    def status_text(self) -> str:
        return self._status_label.text()

    def set_status(self, message: str) -> None:
        self._status_label.setText(str(message).strip() or "系统就绪")

    def set_ready(self, message: str = "系统就绪") -> None:
        self._current_stage = None
        self._is_running = False
        self._is_complete = False
        self._status_label.setText(message)
        self._update_stages()

    def set_error(self, message: str) -> None:
        self._is_running = False
        self._status_label.setText(f"无法继续：{message}")

    def set_complete(self, message: str = "今日流程已完成") -> None:
        self._current_stage = len(self.STAGES) - 1
        self._is_running = False
        self._is_complete = True
        self._status_label.setText(message)
        self._update_stages()

    def start_animation(self) -> None:
        self._is_running = True
        if self._current_stage is not None:
            self._status_label.setText(_STATUS_TEXTS[self._current_stage])

    def stop_animation(self) -> None:
        self._is_running = False
