"""Editor for independently selectable daily targets."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from focus_capsule.data_models import DEFAULT_CATEGORIES, AppConfig, DailyGoalTargets


class TargetMapEditor(QWidget):
    """Small add/remove editor for multiple named minute targets."""

    value_added = pyqtSignal()

    def __init__(
        self,
        choices: list[tuple[str, str]],
        value_suffix: str = " 分钟",
        parent=None,
    ):
        super().__init__(parent)
        self._choices = choices
        self._labels = {key: label for label, key in choices}
        self._values: dict[str, QSpinBox] = {}
        self._rows: dict[str, QWidget] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        add_row = QHBoxLayout()
        add_row.setSpacing(8)
        self._choice = QComboBox()
        for label, key in choices:
            self._choice.addItem(label, key)
        self._choice.setMinimumWidth(180)
        add_row.addWidget(self._choice, 1)

        self._minutes = QSpinBox()
        self._minutes.setRange(1, 1440)
        self._minutes.setValue(30)
        self._minutes.setSuffix(value_suffix)
        add_row.addWidget(self._minutes)

        self._add = QPushButton("添加")
        self._add.setObjectName("presetButton")
        self._add.setEnabled(bool(choices))
        self._add.clicked.connect(self._add_selected)
        add_row.addWidget(self._add)
        layout.addLayout(add_row)

        self._rows_layout = QVBoxLayout()
        self._rows_layout.setSpacing(6)
        layout.addLayout(self._rows_layout)

    def _add_selected(self) -> None:
        key = str(self._choice.currentData() or "")
        if not key:
            return
        if key in self._values:
            self._values[key].setValue(self._minutes.value())
            self.value_added.emit()
            return
        self._add_value(key, self._minutes.value())
        self.value_added.emit()

    def _add_value(self, key: str, value: int) -> None:
        row = QFrame()
        row.setObjectName("softPanel")
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(12, 8, 12, 8)
        label = QLabel(self._labels.get(key, key))
        label.setObjectName("body")
        row_layout.addWidget(label, 1)

        spin = QSpinBox()
        spin.setRange(1, 1440)
        spin.setValue(max(1, int(value)))
        spin.setSuffix(" 分钟")
        row_layout.addWidget(spin)

        remove = QPushButton("移除")
        remove.setObjectName("ghostButton")
        remove.clicked.connect(lambda _=False, item=key: self._remove(item))
        row_layout.addWidget(remove)

        self._values[key] = spin
        self._rows[key] = row
        self._rows_layout.addWidget(row)

    def _remove(self, key: str) -> None:
        self._values.pop(key, None)
        row = self._rows.pop(key, None)
        if row:
            row.deleteLater()

    def set_values(self, values: dict[str, int]) -> None:
        for key, value in values.items():
            if key in self._labels and key not in self._values:
                self._add_value(key, value)

    def values(self) -> dict[str, int]:
        return {key: spin.value() for key, spin in self._values.items()}


class DailyTargetsDialog(QDialog):
    targets_saved = pyqtSignal(object)

    def __init__(
        self,
        targets: DailyGoalTargets,
        app_config: AppConfig,
        parent=None,
    ):
        super().__init__(parent)
        self._targets = targets
        self._config = app_config
        self.setWindowTitle("设置今日目标")
        self.setModal(True)
        self.resize(760, 760)
        self.setMinimumSize(640, 560)
        self._setup_ui()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 20)
        root.setSpacing(12)

        title = QLabel("设置今日目标")
        title.setObjectName("pageTitle")
        root.addWidget(title)
        subtitle = QLabel("可以同时选择多个目标。未勾选的项目不会参与统计或评分。")
        subtitle.setObjectName("bodyMuted")
        subtitle.setWordWrap(True)
        root.addWidget(subtitle)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget()
        self._content_layout = QVBoxLayout(content)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(10)

        (
            self._distractions_enabled,
            self._distractions_value,
        ) = self._simple_target(
            "分心次数",
            "当天允许出现的最大分心次数。",
            "最多",
            " 次",
            0,
            999,
            self._targets.max_distractions,
            5,
        )
        (
            self._focus_enabled,
            self._focus_value,
        ) = self._simple_target(
            "总专注时长",
            "当天所有番茄钟和专注任务累计需要达到的时间。",
            "至少",
            " 分钟",
            1,
            1440,
            self._targets.total_focus_minutes,
            120,
        )

        category_choices = [(name, name) for name in DEFAULT_CATEGORIES]
        (
            self._category_focus_enabled,
            self._category_focus_editor,
        ) = self._map_target(
            "分类专注时长",
            "分别设置学习、工作、编程等分类需要专注多少分钟。",
            category_choices,
            self._targets.category_focus_minutes,
        )

        (
            self._sessions_enabled,
            self._sessions_value,
        ) = self._simple_target(
            "专注次数",
            "当天需要完整完成多少次番茄钟或专注任务。",
            "至少",
            " 次",
            1,
            99,
            self._targets.focus_sessions,
            4,
        )

        app_choices = sorted(
            (
                (item.display_name or item.process_name, item.process_name.casefold())
                for item in self._config.app_categories
                if item.process_name.strip()
            ),
            key=lambda pair: pair[0].casefold(),
        )
        (
            self._app_usage_enabled,
            self._app_usage_editor,
        ) = self._map_target(
            "单个应用使用限制",
            "限制指定应用当天最多可以使用多长时间。专注舱在后台运行时会累计使用时长。",
            app_choices,
            self._targets.app_usage_minutes,
        )
        (
            self._category_usage_enabled,
            self._category_usage_editor,
        ) = self._map_target(
            "分类应用使用限制",
            "限制某一类应用当天累计最多可以使用多长时间。",
            category_choices,
            self._targets.category_usage_minutes,
        )

        (
            self._unlocks_enabled,
            self._unlocks_value,
        ) = self._simple_target(
            "临时解锁次数",
            "限制当天暂停锁定或临时离开专注状态的总次数。",
            "最多",
            " 次",
            0,
            99,
            self._targets.max_temporary_unlocks,
            2,
        )

        self._content_layout.addStretch()
        scroll.setWidget(content)
        root.addWidget(scroll, 1)

        actions = QHBoxLayout()
        actions.addStretch()
        cancel = QPushButton("取消")
        cancel.setObjectName("ghostButton")
        cancel.clicked.connect(self.reject)
        actions.addWidget(cancel)
        save = QPushButton("保存今日目标")
        save.setObjectName("primaryButton")
        save.setMinimumWidth(150)
        save.clicked.connect(self._save)
        actions.addWidget(save)
        root.addLayout(actions)

    def _simple_target(
        self,
        title: str,
        description: str,
        prefix: str,
        suffix: str,
        minimum: int,
        maximum: int,
        current: int | None,
        default: int,
    ) -> tuple[QCheckBox, QSpinBox]:
        card = QFrame()
        card.setObjectName("sectionCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(7)

        enabled = QCheckBox(title)
        enabled.setChecked(current is not None)
        layout.addWidget(enabled)

        helper = QLabel(description)
        helper.setObjectName("bodyTertiary")
        helper.setWordWrap(True)
        layout.addWidget(helper)

        value_row = QHBoxLayout()
        prefix_label = QLabel(prefix)
        prefix_label.setObjectName("summaryKey")
        value_row.addWidget(prefix_label)
        value = QSpinBox()
        value.setRange(minimum, maximum)
        value.setValue(current if current is not None else default)
        value.setSuffix(suffix)
        value_row.addWidget(value)
        value_row.addStretch()
        layout.addLayout(value_row)
        value.valueChanged.connect(lambda _value: enabled.setChecked(True))

        self._content_layout.addWidget(card)
        return enabled, value

    def _map_target(
        self,
        title: str,
        description: str,
        choices: list[tuple[str, str]],
        current: dict[str, int],
    ) -> tuple[QCheckBox, TargetMapEditor]:
        card = QFrame()
        card.setObjectName("sectionCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(7)

        enabled = QCheckBox(title)
        enabled.setChecked(bool(current))
        layout.addWidget(enabled)
        helper = QLabel(description)
        helper.setObjectName("bodyTertiary")
        helper.setWordWrap(True)
        layout.addWidget(helper)

        editor = TargetMapEditor(choices)
        editor.set_values(current)
        editor.value_added.connect(lambda: enabled.setChecked(True))
        layout.addWidget(editor)
        self._content_layout.addWidget(card)
        return enabled, editor

    def _save(self) -> None:
        targets = DailyGoalTargets(
            max_distractions=(
                self._distractions_value.value()
                if self._distractions_enabled.isChecked()
                else None
            ),
            total_focus_minutes=(
                self._focus_value.value() if self._focus_enabled.isChecked() else None
            ),
            category_focus_minutes=(
                self._category_focus_editor.values()
                if self._category_focus_enabled.isChecked()
                else {}
            ),
            focus_sessions=(
                self._sessions_value.value()
                if self._sessions_enabled.isChecked()
                else None
            ),
            app_usage_minutes=(
                self._app_usage_editor.values()
                if self._app_usage_enabled.isChecked()
                else {}
            ),
            category_usage_minutes=(
                self._category_usage_editor.values()
                if self._category_usage_enabled.isChecked()
                else {}
            ),
            max_temporary_unlocks=(
                self._unlocks_value.value()
                if self._unlocks_enabled.isChecked()
                else None
            ),
        )
        self.targets_saved.emit(targets)
        self.accept()
