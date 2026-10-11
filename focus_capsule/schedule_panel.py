"""Schedule rules UI panel for Focus Capsule.

Offers a compact editor for time-of-day rules that lock down to a whitelist.
All times are expressed and displayed in China Standard Time (UTC+8).
"""

from __future__ import annotations

import json

from PyQt6.QtCore import QSettings, Qt, QTime, pyqtSignal
from PyQt6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLayout,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from focus_capsule import theme as T
from focus_capsule.models import ScheduleRule
from focus_capsule.settings_panel import COMMON_APPS, InstalledAppPickerDialog


def _s():
    t = T.current()
    return f"""
QFrame#scheduleSection {{
    background-color: {t["SURFACE_1"]};
    border: 1px solid {t["BORDER_SUBTLE"]};
    border-radius: 14px;
}}

QLabel#scheduleTitle {{
    color: {t["TEXT_PRIMARY"]};
    font-size: 22px;
    font-weight: 600;
    letter-spacing: -0.3px;
}}

QLabel#scheduleSubtitle {{
    color: {t["TEXT_SECONDARY"]};
    font-size: 12px;
}}

QLabel#scheduleHint {{
    color: {t["TEXT_TERTIARY"]};
    font-size: 11px;
}}

QLabel#ruleLabel {{
    color: {t["TEXT_PRIMARY"]};
    font-size: 14px;
    font-weight: 600;
}}

QLabel#ruleApps {{
    color: {t["TEXT_SECONDARY"]};
    font-size: 13px;
}}

QTimeEdit {{
    min-height: 36px;
    background-color: {t["INPUT_BG"]};
    color: {t["TEXT_PRIMARY"]};
    border: 1px solid {t["BORDER_NORMAL"]};
    border-radius: 8px;
    padding: 0 8px;
    selection-background-color: {t["ACCENT_MUTED"]};
}}
QTimeEdit:hover {{ border-color: {t["BORDER_STRONG"]}; }}
QTimeEdit:focus {{ border: 2px solid {t["ACCENT"]}; }}

QFrame#ruleCard {{
    background-color: {t["SURFACE_1"]};
    border: 1px solid {t["BORDER_NORMAL"]};
    border-radius: 12px;
}}

QFrame#ruleCardActive {{
    background-color: {t["ACCENT_DARK_BG"]};
    border: 2px solid {t["ACCENT"]};
    border-radius: 12px;
}}

QCheckBox {{
    color: {t["TEXT_PRIMARY"]};
    font-size: 12px;
    spacing: 8px;
}}
QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1.5px solid {t["BORDER_STRONG"]};
    background: transparent;
}}
QCheckBox::indicator:checked {{
    background-color: {t["ACCENT"]};
    border-color: {t["ACCENT"]};
}}

QPushButton#addRuleButton {{
    min-height: 42px;
    background-color: transparent;
    color: {t["ACCENT_TEXT"]};
    border: 1px dashed {t["ACCENT_BORDER"]};
    border-radius: 10px;
    font-size: 14px;
    font-weight: 600;
}}
QPushButton#addRuleButton:hover {{
    background-color: {t["ACCENT_DARK_BG"]};
    border-color: {t["ACCENT"]};
}}
QPushButton#editRuleApps {{
    min-height: 32px;
    color: {t["ACCENT_TEXT"]};
    background-color: {t["SURFACE_1"]};
    border: 1px solid {t["BORDER_NORMAL"]};
    border-radius: 6px;
    padding: 0 10px;
    font-size: 12px;
}}
QPushButton#editRuleApps:hover {{
    background-color: {t["SURFACE_3"]};
    border-color: {t["BORDER_STRONG"]};
}}
QPushButton#deleteRule {{
    min-height: 32px;
    min-width: 32px;
    color: {t["DANGER"]};
    background-color: transparent;
    border: 1px solid {t["DANGER_BG"]};
    border-radius: 6px;
    font-size: 14px;
    font-weight: 700;
}}
QPushButton#deleteRule:hover {{
    background-color: {t["DANGER_BG"]};
    border-color: {t["DANGER"]};
}}
"""

SCHEDULE_STYLESHEET = ""  # populated lazily


def _schedule_stylesheet() -> str:
    """Return the full schedule-panel stylesheet, evaluated lazily."""
    return _s()


def _format_hour_minute(hour: int, minute: int) -> str:
    return f"{hour:02d}:{minute:02d}"


class SchedulePanel(QWidget):
    """Panel listing, creating, editing and deleting schedule rules."""

    rules_changed = pyqtSignal()

    SETTINGS_ORGANIZATION = "FocusCapsule"
    SETTINGS_APPLICATION = "FocusCapsule"
    SETTINGS_GROUP = "schedule_rules"

    def __init__(self, schedule_manager, parent=None):
        super().__init__(parent)
        self._manager = schedule_manager
        self._installed_apps: list[dict] = []
        self._app_display_names = {process: name for name, process in COMMON_APPS}
        self._installed_by_process: dict[str, dict] = {}
        self._loading = False
        self._status_labels: dict[int, QLabel] = {}
        self._app_labels: dict[int, QLabel] = {}
        self._intensity_cards: dict[int, list] = {}
        self.setObjectName("schedulePanel")
        self.setStyleSheet(_schedule_stylesheet())
        self._load_installed_catalog()
        self._setup_ui()
        self.load_rules()

    def _load_installed_catalog(self) -> None:
        from focus_capsule.icon_utils import discover_installed_apps

        try:
            discovered = discover_installed_apps()
        except Exception:
            discovered = []
        for raw in discovered:
            process = str(raw.get("process_name", "")).strip().casefold()
            display = str(raw.get("display_name", "")).strip()
            if process and display:
                self._installed_by_process[process] = dict(raw)
                self._app_display_names[process] = display

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 20)
        root.setSpacing(12)

        header = QVBoxLayout()
        header.setSpacing(6)
        title = QLabel("自动锁定时段")
        title.setObjectName("scheduleTitle")
        subtitle = QLabel("按中国时间定时锁定，到点自动切换允许的应用")
        subtitle.setObjectName("scheduleSubtitle")
        hint = QLabel("时间均按中国时间（UTC+8）计算。到了锁定时段，只有所选应用可以使用。")
        hint.setObjectName("scheduleHint")
        hint.setWordWrap(True)
        header.addWidget(title)
        header.addWidget(subtitle)
        header.addWidget(hint)
        header.setContentsMargins(0, 4, 0, 8)
        root.addLayout(header)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background:transparent;")

        self._rules_container = QWidget()
        self._rules_layout = QVBoxLayout(self._rules_container)
        self._rules_layout.setContentsMargins(0, 0, 2, 0)
        self._rules_layout.setSpacing(10)
        self._rules_layout.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
        scroll.setWidget(self._rules_container)
        root.addWidget(scroll, 1)

        self._add_button = QPushButton("＋ 添加时段规则")
        self._add_button.setObjectName("addRuleButton")
        self._add_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._add_button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._add_button.clicked.connect(self._add_rule)
        root.addWidget(self._add_button)

        self._empty_label = QLabel(
            "还没有日程规则。点击上方按钮添加一个时段，例如 9~10 点只能用 VS Code。"
        )
        self._empty_label.setObjectName("scheduleHint")
        self._empty_label.setWordWrap(True)
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self._empty_label)

        self._refresh_rules_list()

    def _refresh_rules_list(self) -> None:
        while self._rules_layout.count():
            item = self._rules_layout.takeAt(0)
            if item and item.widget():
                widget = item.widget()
                widget.setParent(None)
                widget.deleteLater()

        rules = self._manager.rules
        active = self._manager.active_rule
        self._empty_label.setVisible(not rules)

        for index, rule in enumerate(rules):
            card = self._build_rule_card(index, rule, rule is active)
            self._rules_layout.addWidget(card)
        self._rules_layout.addStretch()

    def _build_rule_card(self, index: int, rule: ScheduleRule, is_active: bool) -> QFrame:
        card = QFrame()
        card.setObjectName("ruleCardActive" if is_active else "ruleCard")
        card.setMinimumHeight(154)
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 10, 14, 12)
        layout.setSpacing(8)

        top = QHBoxLayout()
        top.setSpacing(10)

        enabled_check = QCheckBox()
        enabled_check.setChecked(rule.enabled)
        enabled_check.toggled.connect(
            lambda checked, idx=index: self._on_rule_enabled(idx, checked)
        )
        top.addWidget(enabled_check)

        time_start = QTimeEdit()
        time_start.setDisplayFormat("HH:mm")
        time_start.setTime(QTime(rule.start_hour, rule.start_minute))
        time_start.setAccessibleName("规则开始时间（中国时间）")

        time_end = QTimeEdit()
        time_end.setDisplayFormat("HH:mm")
        time_end.setTime(QTime(rule.end_hour, rule.end_minute))
        time_end.setAccessibleName("规则结束时间（中国时间）")

        time_start.timeChanged.connect(
            lambda _time, idx=index, start=time_start, end=time_end: self._on_time_changed(
                idx, start, end
            )
        )
        time_end.timeChanged.connect(
            lambda _time, idx=index, start=time_start, end=time_end: self._on_time_changed(
                idx, start, end
            )
        )

        arrow = QLabel("→")
        arrow.setStyleSheet(f"color:{T.TEXT_TERTIARY};font-size:{T.FONT_SECTION}px;")

        top.addWidget(time_start)
        top.addWidget(arrow)
        top.addWidget(time_end)
        top.addStretch()

        status_label = QLabel()
        status_label.setStyleSheet(f"font-size:{T.FONT_META}px;")
        if is_active:
            status_label.setText("● 锁定中")
            status_label.setStyleSheet(f"color:{T.ACCENT};font-size:{T.FONT_META}px;font-weight:{T.WEIGHT_BUTTON};")
        else:
            status_label.setText("待命")
            status_label.setStyleSheet(f"color:{T.TEXT_TERTIARY};font-size:{T.FONT_META}px;")
        top.addWidget(status_label)

        self._status_labels = getattr(self, "_status_labels", {})
        self._status_labels[index] = status_label

        layout.addLayout(top)

        apps_row = QHBoxLayout()
        apps_row.setSpacing(8)

        if rule.label:
            label = QLabel(rule.label)
        else:
            apps_text = ", ".join(
                self._display_name_for(a) for a in rule.whitelisted_apps
            ) or "未设置（全部锁定）"
            label = QLabel(f"允许：{apps_text}")
        label.setObjectName("ruleApps")
        label.setWordWrap(True)
        apps_row.addWidget(label, 1)

        self._app_labels = getattr(self, "_app_labels", {})
        self._app_labels[index] = label

        edit_apps = QPushButton("选择应用")
        edit_apps.setObjectName("editRuleApps")
        edit_apps.setCursor(Qt.CursorShape.PointingHandCursor)
        edit_apps.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        edit_apps.setAccessibleName(f"编辑规则 {index + 1} 的允许应用")
        edit_apps.clicked.connect(lambda _checked=False, idx=index: self._edit_rule_apps(idx))
        apps_row.addWidget(edit_apps)

        delete_btn = QPushButton("✕")
        delete_btn.setObjectName("deleteRule")
        delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        delete_btn.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        delete_btn.setAccessibleName(f"删除规则 {index + 1}")
        delete_btn.setToolTip("删除此规则")
        delete_btn.clicked.connect(lambda _checked=False, idx=index: self._delete_rule(idx))
        apps_row.addWidget(delete_btn)

        layout.addLayout(apps_row)

        # Intensity & escape settings row
        settings_row = QHBoxLayout()
        settings_row.setSpacing(12)

        # Intensity selector
        intensity_label = QLabel("强度：")
        intensity_label.setObjectName("scheduleHint")
        intensity_label.setFixedWidth(40)
        settings_row.addWidget(intensity_label)

        intensity_group = QButtonGroup(card)
        intensity_group.setExclusive(True)
        intensity_cards = []
        for mode_key, mode_label in (
            ("Light", "轻度"),
            ("Standard", "标准"),
            ("Deep", "深度"),
        ):
            btn = QPushButton(mode_label)
            btn.setCheckable(True)
            btn.setMinimumWidth(72)
            btn.setMinimumHeight(34)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {T.INPUT_BG};
                    color: {T.TEXT_SECONDARY};
                    border: 1px solid {T.BORDER_NORMAL};
                    border-radius: {T.RADIUS_MD}px;
                    font-size: {T.FONT_BODY}px;
                    font-weight: {T.WEIGHT_BUTTON};
                    padding: 4px 14px;
                }}
                QPushButton:checked {{
                    background-color: {T.ACCENT_DARK_BG};
                    color: {T.ACCENT_TEXT};
                    border: 2px solid {T.ACCENT};
                }}
                QPushButton:hover {{
                    border-color: {T.BORDER_STRONG};
                    background-color: {T.SURFACE_3};
                }}
            """)
            btn.clicked.connect(
                lambda _checked=False, m=mode_key, idx=index: self._on_intensity_selected(idx, m)
            )
            intensity_group.addButton(btn)
            intensity_cards.append(btn)
            settings_row.addWidget(btn)

        # Sync intensity selection to rule's current mode
        current_mode = getattr(rule, "mode", "Deep")
        for i, mode_key in enumerate(("Light", "Standard", "Deep")):
            intensity_cards[i].setChecked(mode_key == current_mode)

        settings_row.addStretch()

        # Escape count
        esc_label = QLabel("休息：")
        esc_label.setObjectName("scheduleHint")
        esc_label.setFixedWidth(36)
        settings_row.addWidget(esc_label)

        esc_spin = QSpinBox()
        esc_spin.setObjectName("compactSpin")
        esc_spin.setRange(0, 10)
        esc_spin.setValue(rule.max_esc if hasattr(rule, "max_esc") else 0)
        esc_spin.setSuffix(" 次")
        esc_spin.setMinimumWidth(72)
        esc_spin.setKeyboardTracking(False)
        esc_spin.valueChanged.connect(
            lambda _v, _idx=index, _spin=esc_spin: self._on_escape_changed(_idx, "max_esc", _spin)
        )
        settings_row.addWidget(esc_spin)

        # Break duration
        dur_label = QLabel("/ ")
        dur_label.setObjectName("scheduleHint")
        settings_row.addWidget(dur_label)

        dur_spin = QSpinBox()
        dur_spin.setObjectName("compactSpin")
        dur_spin.setRange(1, 15)
        dur_spin.setValue(rule.esc_break_minutes if hasattr(rule, "esc_break_minutes") else 3)
        dur_spin.setSuffix(" 分钟")
        dur_spin.setMinimumWidth(72)
        dur_spin.setKeyboardTracking(False)
        dur_spin.valueChanged.connect(
            lambda _v, _idx=index, _spin=dur_spin: self._on_escape_changed(_idx, "esc_break_minutes", _spin)
        )
        settings_row.addWidget(dur_spin)

        # 严格模式（该条排程专用）
        strict_label = QLabel("退出：")
        strict_label.setObjectName("scheduleHint")
        strict_label.setFixedWidth(36)
        settings_row.addWidget(strict_label)

        strict_combo = QComboBox()
        strict_combo.setObjectName("compactSelect")
        strict_combo.addItem("不锁定", "off")
        strict_combo.addItem("冷静期", "cooldown")
        strict_combo.addItem("随机字符", "phrase")
        strict_combo.addItem("口令", "passcode")
        strict_combo.setMinimumWidth(96)
        current_strict = str(getattr(rule, "strict_level", "off") or "off")
        combo_index = strict_combo.findData(current_strict)
        strict_combo.setCurrentIndex(max(0, combo_index))
        strict_combo.currentIndexChanged.connect(
            lambda _v, _idx=index, _combo=strict_combo: self._on_strict_changed(_idx, _combo)
        )
        settings_row.addWidget(strict_combo)

        cooldown_spin = QSpinBox()
        cooldown_spin.setObjectName("compactSpin")
        cooldown_spin.setRange(1, 240)
        cooldown_spin.setValue(int(getattr(rule, "strict_cooldown_minutes", 5) or 5))
        cooldown_spin.setSuffix(" 分")
        cooldown_spin.setMinimumWidth(72)
        cooldown_spin.setKeyboardTracking(False)
        cooldown_spin.setVisible(current_strict == "cooldown")
        cooldown_spin.setToolTip("冷静期内不能结束锁定，期间专注照常计时")
        cooldown_spin.valueChanged.connect(
            lambda _v, _idx=index, _spin=cooldown_spin: self._on_cooldown_changed(_idx, _spin)
        )
        settings_row.addWidget(cooldown_spin)
        if not hasattr(self, "_cooldown_spins"):
            self._cooldown_spins = {}
        self._cooldown_spins[index] = cooldown_spin

        settings_row.addStretch()
        layout.addLayout(settings_row)

        # Store intensity buttons reference for sync
        self._intensity_cards = getattr(self, "_intensity_cards", {})
        self._intensity_cards[index] = intensity_cards

        return card

    def _display_name_for(self, process_name: str) -> str:
        if process_name in self._app_display_names:
            return self._app_display_names[process_name]
        from pathlib import Path

        name = Path(process_name).stem.replace("_", " ").replace("-", " ").strip()
        return name.title() if name else process_name

    def _add_rule(self) -> None:
        rule = ScheduleRule(
            start_hour=9,
            start_minute=0,
            end_hour=10,
            end_minute=0,
            whitelisted_apps=[],
            mode="Deep",
            max_esc=0,
            esc_break_minutes=3,
            # A newly-created empty rule must never begin locking immediately.
            enabled=False,
        )
        self._manager.add_rule(rule)
        self.save_rules()
        self._refresh_rules_list()
        self.rules_changed.emit()

    def _delete_rule(self, index: int) -> None:
        if not self._confirm_delete():
            return
        self._manager.remove_rule(index)
        self._app_labels.clear()
        self._status_labels.clear()
        self.save_rules()
        self._refresh_rules_list()
        self.rules_changed.emit()

    def _confirm_delete(self) -> bool:
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Question)
        box.setWindowTitle("删除此规则？")
        box.setText("确认删除这个日程锁定规则？")
        confirm = box.addButton("删除", QMessageBox.ButtonRole.AcceptRole)
        cancel = box.addButton("取消", QMessageBox.ButtonRole.RejectRole)
        confirm.setObjectName("dangerButton")
        cancel.setObjectName("ghostButton")
        box.setDefaultButton(cancel)
        box.setEscapeButton(cancel)
        box.exec()
        return box.clickedButton() is confirm

    def _on_rule_enabled(self, index: int, enabled: bool) -> None:
        if self._loading:
            return
        rules = self._manager.rules
        if 0 <= index < len(rules):
            rule = rules[index]
            rule.enabled = enabled
            self._manager.update_rule(index, rule)
            self.save_rules()
            self._refresh_rules_list()
            self.rules_changed.emit()

    def _on_time_changed(
        self,
        index: int,
        start_editor: QTimeEdit,
        end_editor: QTimeEdit,
    ) -> None:
        if self._loading:
            return
        rules = self._manager.rules
        if 0 <= index < len(rules):
            rule = rules[index]
            start_time = start_editor.time()
            end_time = end_editor.time()
            rule.start_hour = start_time.hour()
            rule.start_minute = start_time.minute()
            rule.end_hour = end_time.hour()
            rule.end_minute = end_time.minute()
            self._manager.update_rule(index, rule)
            self.save_rules()
            self.rules_changed.emit()

    def _on_intensity_selected(self, index: int, mode: str) -> None:
        if self._loading:
            return
        rules = self._manager.rules
        if 0 <= index < len(rules):
            rule = rules[index]
            rule.mode = mode
            # Sync button states
            cards = self._intensity_cards.get(index, [])
            for i, mode_key in enumerate(("Light", "Standard", "Deep")):
                if i < len(cards):
                    cards[i].setChecked(mode_key == mode)
            self._manager.update_rule(index, rule)
            self.save_rules()
            self.rules_changed.emit()

    def _on_escape_changed(self, index: int, field: str, spin: QSpinBox) -> None:
        if self._loading:
            return
        rules = self._manager.rules
        if 0 <= index < len(rules):
            rule = rules[index]
            if field == "max_esc":
                rule.max_esc = spin.value()
            elif field == "esc_break_minutes":
                rule.esc_break_minutes = spin.value()
            self._manager.update_rule(index, rule)
            self.save_rules()
            self.rules_changed.emit()

    def _on_strict_changed(self, index: int, combo: QComboBox) -> None:
        if self._loading:
            return
        rules = self._manager.rules
        if not 0 <= index < len(rules):
            return
        rule = rules[index]
        rule.strict_level = str(combo.currentData() or "off")
        spin = getattr(self, "_cooldown_spins", {}).get(index)
        if spin is not None:
            spin.setVisible(rule.strict_level == "cooldown")
        self._manager.update_rule(index, rule)
        self.save_rules()
        self.rules_changed.emit()

    def _on_cooldown_changed(self, index: int, spin: QSpinBox) -> None:
        if self._loading:
            return
        rules = self._manager.rules
        if not 0 <= index < len(rules):
            return
        rule = rules[index]
        rule.strict_cooldown_minutes = spin.value()
        self._manager.update_rule(index, rule)
        self.save_rules()
        self.rules_changed.emit()

    def _edit_rule_apps(self, index: int) -> None:
        rules = self._manager.rules
        if not (0 <= index < len(rules)):
            return
        rule = rules[index]

        available_by_process = {
            process.casefold(): dict(info)
            for process, info in self._installed_by_process.items()
        }
        for friendly_name, process_name in COMMON_APPS:
            normalized = process_name.casefold()
            if normalized not in self._installed_by_process:
                continue
            available_by_process[normalized]["display_name"] = friendly_name

        # Preserve existing selections even if an app was uninstalled or no
        # longer appears in discovery; the user can still remove it explicitly.
        for process_name in rule.whitelisted_apps:
            normalized = process_name.casefold()
            available_by_process.setdefault(
                normalized,
                {
                    "display_name": self._display_name_for(normalized),
                    "process_name": normalized,
                    "custom_path": "",
                },
            )

        dialog = InstalledAppPickerDialog(
            list(available_by_process.values()),
            rule.whitelisted_apps,
            self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        selected = dialog.selected_apps()
        rule.whitelisted_apps = list(
            dict.fromkeys(
                str(info.get("process_name", "")).strip().casefold()
                for info in selected
                if str(info.get("process_name", "")).strip()
            )
        )
        rule.allowed_app_paths = {
            str(info.get("process_name", "")).strip().casefold(): str(
                info.get("custom_path", "")
            ).strip()
            for info in selected
            if str(info.get("process_name", "")).strip()
            and str(info.get("custom_path", "")).strip()
        }
        self._manager.update_rule(index, rule)
        self.save_rules()
        self._refresh_rules_list()
        self.rules_changed.emit()

    def save_rules(self) -> None:
        settings = QSettings(self.SETTINGS_ORGANIZATION, self.SETTINGS_APPLICATION)
        settings.beginGroup(self.SETTINGS_GROUP)
        payload = [rule.to_dict() for rule in self._manager.rules]
        settings.setValue("rules", json.dumps(payload, ensure_ascii=False))
        settings.endGroup()
        settings.sync()

    def load_rules(self) -> None:
        settings = QSettings(self.SETTINGS_ORGANIZATION, self.SETTINGS_APPLICATION)
        settings.beginGroup(self.SETTINGS_GROUP)
        raw = settings.value("rules", "")
        settings.endGroup()

        rules: list[ScheduleRule] = []
        if raw:
            try:
                data = json.loads(raw)
                if isinstance(data, list):
                    for item in data:
                        try:
                            rule = ScheduleRule.from_dict(item)
                            refreshed_paths = dict(rule.allowed_app_paths)
                            for process in rule.whitelisted_apps:
                                info = self._installed_by_process.get(process, {})
                                current_path = str(info.get("custom_path", "")).strip()
                                if current_path:
                                    refreshed_paths[process] = current_path
                            rule.allowed_app_paths = refreshed_paths
                            rules.append(rule)
                        except (TypeError, ValueError):
                            continue
            except (json.JSONDecodeError, TypeError, ValueError):
                pass
        self._loading = True
        try:
            self._manager.set_rules(rules)
        finally:
            self._loading = False
        self._refresh_rules_list()

    def refresh_active_status(self) -> None:
        self._refresh_rules_list()
