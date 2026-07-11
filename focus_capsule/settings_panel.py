"""Accessible, responsive settings panel for Focus Capsule."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Iterable, Optional

from PyQt6.QtCore import QPoint, QRect, QSettings, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import (
    QButtonGroup,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLayoutItem,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from focus_capsule.icon_utils import app_icon, clear_icon_cache
from focus_capsule.models import FocusConfig


def _common_apps_for_platform() -> list[tuple[str, str]]:
    """Return friendly app names and the process identifiers used by the monitor."""
    if sys.platform == "darwin":
        return [
            ("Safari", "safari"),
            ("Chrome", "google chrome"),
            ("Firefox", "firefox"),
            ("VS Code", "visual studio code"),
            ("Word", "microsoft word"),
            ("Excel", "microsoft excel"),
            ("Outlook", "microsoft outlook"),
            ("Slack", "slack"),
            ("Terminal", "terminal"),
            ("iTerm", "iterm2"),
            ("PyCharm", "pycharm"),
            ("Edge", "microsoft edge"),
        ]
    if os.name == "nt":
        return [
            ("VS Code", "code.exe"),
            ("Chrome", "chrome.exe"),
            ("Edge", "msedge.exe"),
            ("Firefox", "firefox.exe"),
            ("Word", "winword.exe"),
            ("Excel", "excel.exe"),
            ("Outlook", "outlook.exe"),
            ("Slack", "slack.exe"),
            ("终端", "wt.exe"),
            ("记事本", "notepad.exe"),
            ("PyCharm", "pycharm64.exe"),
            ("IntelliJ", "idea64.exe"),
        ]
    return [
        ("VS Code", "code"),
        ("Chrome", "google-chrome"),
        ("Firefox", "firefox"),
        ("Slack", "slack"),
        ("终端", "terminal"),
        ("PyCharm", "pycharm"),
    ]


COMMON_APPS = _common_apps_for_platform()


PANEL_STYLESHEET = """
QWidget#settingsPanel,
QWidget#settingsContent,
QScrollArea#settingsScroll,
QScrollArea#settingsScroll > QWidget > QWidget {
    background: transparent;
}

QScrollArea#settingsScroll {
    border: none;
}

QLabel#settingsTitle {
    color: #f3f6f7;
    font-size: 22px;
    font-weight: bold;
}

QLabel#settingsSubtitle {
    color: #93a1af;
    font-size: 12px;
}

QFrame#settingsSection {
    background-color: #141d27;
    border: 1px solid #26323e;
    border-radius: 12px;
}

QLabel#sectionTitle {
    color: #eef3f4;
    font-size: 14px;
    font-weight: bold;
}

QLabel#sectionHint,
QLabel#fieldHint,
QLabel#selectedEmpty {
    color: #93a1af;
    font-size: 11px;
}

QLabel#selectedSummary {
    color: #cbd5da;
    font-size: 12px;
    font-weight: bold;
}

QLineEdit#goalInput,
QSpinBox#durationSpin,
QSpinBox#compactSpin {
    min-height: 38px;
    background-color: #0f171f;
    color: #f3f6f7;
    border: 1px solid #334250;
    border-radius: 8px;
    padding: 0 10px;
    selection-background-color: #67cfbb;
    selection-color: #081310;
}

QLineEdit#goalInput:hover,
QSpinBox#durationSpin:hover,
QSpinBox#compactSpin:hover {
    border-color: #516170;
}

QLineEdit#goalInput:focus,
QSpinBox#durationSpin:focus,
QSpinBox#compactSpin:focus {
    border: 2px solid #67cfbb;
}

QSpinBox#durationSpin::up-button,
QSpinBox#durationSpin::down-button,
QSpinBox#compactSpin::up-button,
QSpinBox#compactSpin::down-button {
    width: 18px;
    border: none;
    background: transparent;
}

QPushButton#durationChip,
QPushButton#appIconTile,
QPushButton#selectedAppChip {
    min-height: 38px;
    background-color: #192532;
    color: #cbd5da;
    border: 1px solid #334250;
    border-radius: 12px;
    padding: 0 15px;
}

QPushButton#durationChip:hover,
QPushButton#appIconTile:hover,
QPushButton#selectedAppChip:hover {
    background-color: #21303d;
    border-color: #536574;
    color: #f3f6f7;
}

QPushButton#durationChip:checked,
QPushButton#appIconTile:checked {
    background-color: #172821;
    border: 2px solid #67cfbb;
    color: #e8fffa;
}

QPushButton#appIconTile {
    min-height: 0px;
    border: 1px solid #2b3b50;
    border-radius: 12px;
    padding: 0;
    background-color: #141d27;
}

QPushButton#appIconTile:hover {
    border-color: #67cfbb;
    background-color: #172233;
}

QPushButton#appIconTile:checked {
    border: 2px solid #67cfbb;
    background-color: #17342F;
}

QWidget#appIconTilesScroll {
    border: none;
    background: transparent;
}

QLabel#appTileName {
    color: #b0bcc8;
    font-size: 11px;
    font-weight: 500;
}

QPushButton#appIconTile:checked QLabel#appTileName {
    color: #a8efe1;
}

QPushButton#durationChip:focus,
QPushButton#appChip:focus,
QPushButton#selectedAppChip:focus,
QPushButton#addAppButton:focus,
QPushButton#intensityChoice:focus {
    border: 2px solid #a8efe1;
}

QPushButton#selectedAppChip {
    min-height: 34px;
    color: #a8efe1;
    border-color: #36594f;
    padding: 0 12px;
}

QPushButton#addAppButton {
    min-height: 38px;
    background-color: transparent;
    color: #a8efe1;
    border: 1px dashed #4a6f65;
    border-radius: 8px;
    padding: 0 14px;
}

QPushButton#addAppButton:hover {
    background-color: #172821;
    border-color: #67cfbb;
}

QPushButton#intensityChoice {
    min-width: 148px;
    min-height: 64px;
    background-color: #192532;
    color: #cbd5da;
    border: 1px solid #334250;
    border-radius: 10px;
    padding: 10px 12px;
    text-align: left;
}

QPushButton#intensityChoice:hover {
    background-color: #21303d;
    border-color: #536574;
    color: #f3f6f7;
}

QPushButton#intensityChoice:checked {
    background-color: #172821;
    color: #e8fffa;
    border: 2px solid #67cfbb;
    font-weight: bold;
}

QFrame#compactControl {
    background-color: #0f171f;
    border: 1px solid #26323e;
    border-radius: 9px;
}

QScrollBar:vertical {
    width: 8px;
    background: transparent;
}

QScrollBar::handle:vertical {
    min-height: 30px;
    background: #3a4855;
    border-radius: 4px;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0;
}
"""


class FlowLayout(QLayout):
    """A small wrapping layout suitable for keyboard-accessible chips."""

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        margin: int = 0,
        horizontal_spacing: int = 8,
        vertical_spacing: int = 8,
    ):
        super().__init__(parent)
        self._items: list[QLayoutItem] = []
        self._horizontal_spacing = horizontal_spacing
        self._vertical_spacing = vertical_spacing
        self.setContentsMargins(margin, margin, margin, margin)

    def __del__(self):
        while self.takeAt(0):
            pass

    def addItem(self, item: QLayoutItem) -> None:
        self._items.append(item)

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, index: int) -> Optional[QLayoutItem]:
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index: int) -> Optional[QLayoutItem]:
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        return self._do_layout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect: QRect) -> None:
        super().setGeometry(rect)
        self._do_layout(rect, False)

    def sizeHint(self) -> QSize:
        return self.minimumSize()

    def minimumSize(self) -> QSize:
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(), margins.top() + margins.bottom())
        return size

    def _do_layout(self, rect: QRect, test_only: bool) -> int:
        """Lay out items in a flowing wrap within *rect*.

        Returns the total height required.
        """
        margins = self.contentsMargins()
        effective_rect = rect.adjusted(
            margins.left(), margins.top(), -margins.right(), -margins.bottom()
        )
        x = effective_rect.x()
        y = effective_rect.y()
        line_height = 0

        for item in self._items:
            wid = item.widget()
            if wid is not None and wid.isHidden():
                continue

            hint = item.sizeHint()
            next_x = x + hint.width() + self._horizontal_spacing

            if next_x - self._horizontal_spacing > effective_rect.right() and line_height > 0:
                x = effective_rect.x()
                y = y + line_height + self._vertical_spacing
                next_x = x + hint.width() + self._horizontal_spacing
                line_height = 0

            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), hint))

            x = next_x
            line_height = max(line_height, hint.height())

        total = y + line_height - rect.y() + margins.bottom()
        return total

    def clear_widgets(self) -> None:
        while self.count():
            item = self.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()


class IconGrid(QWidget):
    """A responsive grid layout for app icon tiles (like "Open With")."""

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        columns: int = 6,
        h_spacing: int = 12,
        v_spacing: int = 12,
    ):
        super().__init__(parent)
        self._columns = columns
        self._h_spacing = h_spacing
        self._v_spacing = v_spacing
        self._tiles: list[QWidget] = []
        self.setMinimumHeight(0)

    @property
    def columns(self) -> int:
        return self._columns

    @columns.setter
    def columns(self, value: int) -> None:
        self._columns = max(4, value)
        self._relayout()

    def add_tile(self, widget: QWidget) -> None:
        widget.setParent(self)
        self._tiles.append(widget)
        widget.show()
        self.updateGeometry()
        self._relayout()

    def clear_tiles(self) -> None:
        for w in self._tiles:
            w.deleteLater()
        self._tiles.clear()
        self.updateGeometry()
        self.update()

    def _relayout(self) -> None:
        if not self._tiles:
            self.setMinimumHeight(0)
            return

        tile_w = self._tiles[0].sizeHint().width() if self._tiles[0].sizeHint().width() > 0 else 84
        available = max(self.width(), tile_w * self._columns)
        cols = max(1, min(self._columns, (available + self._h_spacing) // (tile_w + self._h_spacing)))

        x = 0
        y = 0
        row_height = 0
        for i, tile in enumerate(self._tiles):
            if i > 0 and i % cols == 0:
                x = 0
                y += row_height + self._v_spacing
                row_height = 0
            tile.setGeometry(x, y, tile.sizeHint().width(), tile.sizeHint().height())
            x += tile.sizeHint().width() + self._h_spacing
            row_height = max(row_height, tile.sizeHint().height())

        total_height = y + row_height
        self.setMinimumHeight(total_height)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._relayout()

    def sizeHint(self) -> QSize:
        if not self._tiles:
            return QSize(0, 0)
        return QSize(self.width(), self.minimumHeight())

    def _do_layout(self, rect: QRect, test_only: bool) -> int:
        margins = self.contentsMargins()
        effective = rect.adjusted(
            margins.left(), margins.top(), -margins.right(), -margins.bottom()
        )
        x = effective.x()
        y = effective.y()
        line_height = 0

        for item in self._items:
            hint = item.sizeHint()
            next_x = x + hint.width() + self._horizontal_spacing
            if line_height and next_x - self._horizontal_spacing > effective.right() + 1:
                x = effective.x()
                y += line_height + self._vertical_spacing
                next_x = x + hint.width() + self._horizontal_spacing
                line_height = 0
            if not test_only:
                item.setGeometry(QRect(x, y, hint.width(), hint.height()))
            x = next_x
            line_height = max(line_height, hint.height())

        return y + line_height - rect.y() + margins.bottom()


class AppChip(QPushButton):
    """Icon tile with app icon + label, like Windows "Open With" picker."""

    toggled_app = pyqtSignal(str, bool)

    ICON_SIZE = 40
    TILE_W = 84
    TILE_H = 92

    def __init__(self, display_name: str, process_name: str, custom_path: str = "", parent=None):
        super().__init__(parent)
        self._display_name = display_name
        self._process_name = process_name
        self._custom_path = custom_path
        self._selected = False
        self.setObjectName("appIconTile")
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setFixedSize(self.TILE_W, self.TILE_H)
        self.setAccessibleDescription(f"专注期间允许使用 {display_name}")
        self.toggled.connect(self._on_toggled)
        self._refresh_accessibility(False)
        self._build_content()

    def _build_content(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 8, 4, 4)
        layout.setSpacing(4)

        self._icon_label = QLabel()
        self._icon_label.setFixedSize(self.ICON_SIZE, self.ICON_SIZE)
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon = app_icon(self._process_name, self._custom_path)
        self._icon_label.setPixmap(icon.pixmap(QSize(self.ICON_SIZE, self.ICON_SIZE)))
        layout.addWidget(self._icon_label, 0, Qt.AlignmentFlag.AlignCenter)

        self._name_label = QLabel(self._display_name)
        self._name_label.setObjectName("appTileName")
        self._name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._name_label.setWordWrap(False)
        self._name_label.setFixedWidth(self.TILE_W - 8)
        self._name_label.setFixedHeight(20)
        layout.addWidget(self._name_label)

    def _on_toggled(self, checked: bool) -> None:
        self._selected = checked
        self._refresh_accessibility(checked)
        self.toggled_app.emit(self._process_name, checked)

    def _refresh_accessibility(self, checked: bool) -> None:
        state = "已允许" if checked else "未允许"
        self.setAccessibleName(f"{self._display_name}，{state}")

    def set_selected(self, selected: bool) -> None:
        self.setChecked(selected)

    def update_icon(self) -> None:
        """Re-extract icon (e.g. after a custom app is added)."""
        icon = app_icon(self._process_name, self._custom_path)
        self._icon_label.setPixmap(icon.pixmap(QSize(self.ICON_SIZE, self.ICON_SIZE)))


class PresetButton(QPushButton):
    """Checkable duration preset retained for compatibility with the old panel."""

    selected = pyqtSignal(int)

    def __init__(self, label: str, minutes: int, parent=None):
        super().__init__(label, parent)
        self._minutes = minutes
        self.setObjectName("durationChip")
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName(f"专注 {minutes} 分钟")
        self.setAccessibleDescription("选择本次专注时长")
        self.clicked.connect(lambda _checked=False: self.selected.emit(self._minutes))

    def set_selected(self, selected: bool) -> None:
        self.setChecked(selected)


class IntensityCard(QPushButton):
    """Exclusive intensity choice implemented as an accessible button."""

    selected = pyqtSignal(str)

    def __init__(
        self,
        title: str,
        description: str,
        mode: str,
        icon: str,
        parent=None,
        default: bool = False,
    ):
        super().__init__(f"{icon}  {title}\n{description}", parent)
        self._mode = mode
        self._title = title
        self._selected = default
        self.setObjectName("intensityChoice")
        self.setCheckable(True)
        self.setChecked(default)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setAccessibleDescription(description)
        self.clicked.connect(lambda _checked=False: self.selected.emit(self._mode))
        self.toggled.connect(self._on_toggled)
        self._on_toggled(default)

    def _on_toggled(self, checked: bool) -> None:
        self._selected = checked
        state = "已选择" if checked else "未选择"
        self.setAccessibleName(f"{self._title}强度，{state}")

    def set_selected(self, selected: bool) -> None:
        self.setChecked(selected)


class SettingsPanel(QWidget):
    """Chinese-first configuration flow for creating a focus session."""

    start_clicked = pyqtSignal(object)  # Kept for MainWindow compatibility.
    config_changed = pyqtSignal(object)  # Emits FocusConfig after each user change.

    SETTINGS_ORGANIZATION = "FocusCapsule"
    SETTINGS_APPLICATION = "FocusCapsule"
    SETTINGS_GROUP = "session_defaults"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._updating = True
        self._whitelist: list[str] = []
        self._custom_apps: list[str] = []
        self._custom_display_names: dict[str, str] = {}
        self._preset_buttons: dict[str, PresetButton] = {}
        self._preset_by_minutes: dict[int, PresetButton] = {}
        self._intensity_cards: dict[str, IntensityCard] = {}
        self._chip_widgets: dict[str, AppChip] = {}
        self._app_display_names = {process: name for name, process in COMMON_APPS}
        self._selected_apps_labels: list[QPushButton] = []
        self._setup_ui()
        self.load_config()
        self._updating = False

    def _setup_ui(self) -> None:
        self.setObjectName("settingsPanel")
        self.setStyleSheet(PANEL_STYLESHEET)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        scroll = QScrollArea(self)
        scroll.setObjectName("settingsScroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        content.setObjectName("settingsContent")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(16, 12, 16, 20)
        layout.setSpacing(12)

        title = QLabel("开始一次专注")
        title.setObjectName("settingsTitle")
        layout.addWidget(title)

        subtitle = QLabel("选好目标与允许使用的应用，然后进入专注。")
        subtitle.setObjectName("settingsSubtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        layout.addWidget(self._build_goal_section())
        layout.addWidget(self._build_duration_section())
        layout.addWidget(self._build_apps_section())
        layout.addWidget(self._build_intensity_section())
        layout.addWidget(self._build_escape_section())
        layout.addStretch()

        scroll.setWidget(content)
        root.addWidget(scroll)

    def _new_section(self, title: str, hint: str = "") -> tuple[QFrame, QVBoxLayout]:
        section = QFrame()
        section.setObjectName("settingsSection")
        section_layout = QVBoxLayout(section)
        section_layout.setContentsMargins(14, 13, 14, 14)
        section_layout.setSpacing(9)

        heading = QLabel(title)
        heading.setObjectName("sectionTitle")
        section_layout.addWidget(heading)

        if hint:
            helper = QLabel(hint)
            helper.setObjectName("sectionHint")
            helper.setWordWrap(True)
            section_layout.addWidget(helper)

        return section, section_layout

    def _build_goal_section(self) -> QFrame:
        section, layout = self._new_section(
            "这次要完成什么？", "可选。写下一个清晰结果，专注时更容易回到正轨。"
        )
        self._goal_edit = QLineEdit()
        self._goal_edit.setObjectName("goalInput")
        self._goal_edit.setPlaceholderText("例如：完成报告第一稿")
        self._goal_edit.setClearButtonEnabled(True)
        self._goal_edit.setMaxLength(120)
        self._goal_edit.setAccessibleName("本次专注目标")
        self._goal_edit.setAccessibleDescription("可选，输入本次专注希望完成的结果")
        self._goal_edit.textChanged.connect(self._on_goal_changed)
        layout.addWidget(self._goal_edit)
        return section

    def _build_duration_section(self) -> QFrame:
        section, layout = self._new_section("专注多久？", "选择常用时长，或输入自定义分钟数。")

        preset_host = QWidget()
        preset_flow = FlowLayout(preset_host, horizontal_spacing=8, vertical_spacing=8)
        for minutes in (25, 45, 60, 90):
            label = f"{minutes} 分钟"
            button = PresetButton(label, minutes, self)
            button.selected.connect(self._on_preset_selected)
            preset_flow.addWidget(button)
            self._preset_buttons[label] = button
            self._preset_by_minutes[minutes] = button
        layout.addWidget(preset_host)

        custom_row = QHBoxLayout()
        custom_row.setSpacing(10)
        custom_label = QLabel("自定义")
        custom_label.setObjectName("fieldHint")
        custom_row.addWidget(custom_label)

        self._custom_min_spin = QSpinBox()
        self._custom_min_spin.setObjectName("durationSpin")
        self._custom_min_spin.setRange(5, 240)
        self._custom_min_spin.setSingleStep(5)
        self._custom_min_spin.setValue(25)
        self._custom_min_spin.setSuffix(" 分钟")
        self._custom_min_spin.setMinimumWidth(112)
        self._custom_min_spin.setAccessibleName("自定义专注时长")
        self._custom_min_spin.setAccessibleDescription("5 到 240 分钟")
        self._custom_min_spin.valueChanged.connect(self._on_duration_changed)
        custom_row.addWidget(self._custom_min_spin)
        custom_row.addStretch()
        layout.addLayout(custom_row)
        return section

    def _build_apps_section(self) -> QFrame:
        section, layout = self._new_section(
            "专注时允许哪些应用？",
            "点选工作需要的应用，像打开方式那样选择。未选中的应用会按保护强度提醒或拦截。",
        )

        self._icon_grid = IconGrid(self, columns=6, h_spacing=10, v_spacing=10)
        for display_name, process_name in COMMON_APPS:
            chip = AppChip(display_name, process_name, "", self)
            chip.toggled_app.connect(self._on_chip_toggle)
            self._icon_grid.add_tile(chip)
            self._chip_widgets[process_name] = chip
        layout.addWidget(self._icon_grid)

        add_custom_btn = QPushButton("＋ 选择其他应用")
        add_custom_btn.setObjectName("addAppButton")
        add_custom_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_custom_btn.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        add_custom_btn.setAccessibleName("选择其他应用")
        if sys.platform == "darwin":
            add_custom_btn.setAccessibleDescription("从应用程序中选择一个 app 应用")
        elif os.name == "nt":
            add_custom_btn.setAccessibleDescription("选择一个 exe 应用程序")
        else:
            add_custom_btn.setAccessibleDescription("选择一个可执行应用程序")
        add_custom_btn.clicked.connect(self._add_custom_app)
        layout.addWidget(add_custom_btn, 0, Qt.AlignmentFlag.AlignLeft)

        self._selected_summary = QLabel("已允许 0 个应用")
        self._selected_summary.setObjectName("selectedSummary")
        layout.addWidget(self._selected_summary)

        self._selected_apps_host = QWidget()
        self._selected_apps_layout = FlowLayout(
            self._selected_apps_host, horizontal_spacing=7, vertical_spacing=7
        )
        layout.addWidget(self._selected_apps_host)
        return section

    def _build_intensity_section(self) -> QFrame:
        section, layout = self._new_section("保护强度", "每种强度都说明实际行为，随时可以在下次专注前调整。")

        choices_host = QWidget()
        choices_flow = FlowLayout(choices_host, horizontal_spacing=9, vertical_spacing=9)
        self._mode_group = QButtonGroup(self)
        self._mode_group.setExclusive(True)

        choices = [
            ("Light", "轻度", "只记录分心，不打断当前操作", "○", False),
            ("Standard", "标准", "分心时给出柔和返回提醒", "◐", True),
            ("Deep", "深度", "用全屏提示保护专注时段", "●", False),
        ]
        for mode, title, description, icon, selected in choices:
            card = IntensityCard(title, description, mode, icon, self, default=selected)
            card.selected.connect(self._on_intensity_selected)
            self._mode_group.addButton(card)
            choices_flow.addWidget(card)
            self._intensity_cards[mode] = card

        layout.addWidget(choices_host)
        return section

    def _build_escape_section(self) -> QFrame:
        section, layout = self._new_section(
            "应急休息", "给真正需要离开的时刻留一个出口；休息期间专注计时暂停。"
        )

        controls_host = QWidget()
        controls_flow = FlowLayout(controls_host, horizontal_spacing=9, vertical_spacing=9)

        uses_control, uses_layout = self._compact_control("每次可休息")
        self._max_esc_spin = QSpinBox()
        self._max_esc_spin.setObjectName("compactSpin")
        self._max_esc_spin.setRange(0, 10)
        self._max_esc_spin.setValue(2)
        self._max_esc_spin.setSuffix(" 次")
        self._max_esc_spin.setMinimumWidth(86)
        self._max_esc_spin.setAccessibleName("应急休息次数")
        self._max_esc_spin.valueChanged.connect(self._on_escape_setting_changed)
        uses_layout.addWidget(self._max_esc_spin)
        controls_flow.addWidget(uses_control)

        duration_control, duration_layout = self._compact_control("每次最长")
        self._esc_break_spin = QSpinBox()
        self._esc_break_spin.setObjectName("compactSpin")
        self._esc_break_spin.setRange(1, 15)
        self._esc_break_spin.setValue(3)
        self._esc_break_spin.setSuffix(" 分钟")
        self._esc_break_spin.setMinimumWidth(104)
        self._esc_break_spin.setAccessibleName("应急休息时长")
        self._esc_break_spin.valueChanged.connect(self._on_escape_setting_changed)
        duration_layout.addWidget(self._esc_break_spin)
        controls_flow.addWidget(duration_control)

        layout.addWidget(controls_host)
        return section

    def _compact_control(self, label: str) -> tuple[QFrame, QHBoxLayout]:
        control = QFrame()
        control.setObjectName("compactControl")
        control_layout = QHBoxLayout(control)
        control_layout.setContentsMargins(10, 6, 8, 6)
        control_layout.setSpacing(9)
        text = QLabel(label)
        text.setObjectName("fieldHint")
        control_layout.addWidget(text)
        return control, control_layout

    def _on_goal_changed(self, _text: str) -> None:
        self._emit_config_changed()

    def _on_preset_selected(self, minutes: int) -> None:
        changed = self._custom_min_spin.value() != minutes
        self._custom_min_spin.setValue(minutes)
        self._sync_duration_buttons()
        if not changed:
            self._emit_config_changed()

    def _on_duration_changed(self, _minutes: int) -> None:
        self._sync_duration_buttons()
        self._emit_config_changed()

    def _sync_duration_buttons(self) -> None:
        current = self._custom_min_spin.value()
        for minutes, button in self._preset_by_minutes.items():
            button.set_selected(minutes == current)

    def _on_chip_toggle(self, process_name: str, selected: bool) -> None:
        if self._updating:
            return
        if selected and process_name not in self._whitelist:
            self._whitelist.append(process_name)
        elif not selected and process_name in self._whitelist:
            self._whitelist.remove(process_name)
        self._update_selected_display()
        self._emit_config_changed()

    def _on_intensity_selected(self, mode: str) -> None:
        if self._updating:
            return
        self._updating = True
        try:
            for candidate, card in self._intensity_cards.items():
                card.set_selected(candidate == mode)
        finally:
            self._updating = False
        self._emit_config_changed()

    def _on_escape_setting_changed(self, _value: int) -> None:
        self._emit_config_changed()

    def _add_custom_app(self) -> None:
        if sys.platform == "darwin":
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "选择应用",
                "/Applications",
                "macOS 应用 (*.app)",
            )
        elif os.name == "nt":
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "选择应用",
                "",
                "Windows 应用 (*.exe *.lnk)",
            )
        else:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "选择应用",
                "",
                "可执行文件 (*)",
            )

        if not file_path:
            return

        identifier, display_name = self._custom_app_identity(file_path)
        if file_path not in self._custom_apps:
            self._custom_apps.append(file_path)
        self._custom_display_names[identifier] = display_name
        self._app_display_names[identifier] = display_name

        common_chip = self._chip_widgets.get(identifier)
        if common_chip and not common_chip.isChecked():
            common_chip.setChecked(True)
            return

        # Add a new icon tile for the custom app
        if identifier not in self._chip_widgets:
            new_chip = AppChip(display_name, identifier, file_path, self)
            new_chip.toggled_app.connect(self._on_chip_toggle)
            self._icon_grid.add_tile(new_chip)
            self._chip_widgets[identifier] = new_chip
            clear_icon_cache()

        if identifier not in self._whitelist:
            self._whitelist.append(identifier)
        self._update_selected_display()
        self._emit_config_changed()

    def _custom_app_identity(self, file_path: str) -> tuple[str, str]:
        path = Path(file_path)
        if sys.platform == "darwin" and path.name.lower().endswith(".app"):
            display_name = path.name[:-4]
            return display_name.lower(), display_name
        display_name = path.stem or path.name
        identifier = path.name.lower() if os.name == "nt" else display_name.lower()
        return identifier, display_name

    def _remove_selected_app(self, process_name: str) -> None:
        self._custom_apps = [
            path
            for path in self._custom_apps
            if self._custom_app_identity(path)[0] != process_name
        ]
        self._custom_display_names.pop(process_name, None)

        chip = self._chip_widgets.get(process_name)
        if chip and chip.isChecked():
            chip.setChecked(False)
            return

        if process_name in self._whitelist:
            self._whitelist.remove(process_name)
        self._update_selected_display()
        self._emit_config_changed()

    def _update_selected_display(self) -> None:
        self._selected_apps_layout.clear_widgets()
        self._selected_apps_labels.clear()
        count = len(self._whitelist)
        self._selected_summary.setText(f"已允许 {count} 个应用")

        if not self._whitelist:
            empty = QLabel("还没有选择。请至少允许一个完成目标所需的应用。")
            empty.setObjectName("selectedEmpty")
            empty.setWordWrap(True)
            self._selected_apps_layout.addWidget(empty)
            return

        for process_name in self._whitelist:
            display_name = self._display_name_for(process_name)
            remove_button = QPushButton(f"{display_name}  ×")
            remove_button.setObjectName("selectedAppChip")
            remove_button.setCursor(Qt.CursorShape.PointingHandCursor)
            remove_button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            remove_button.setAccessibleName(f"移除已允许的应用 {display_name}")
            remove_button.setAccessibleDescription("按下后从本次允许应用中移除")
            remove_button.clicked.connect(
                lambda _checked=False, name=process_name: self._remove_selected_app(name)
            )
            self._selected_apps_layout.addWidget(remove_button)
            self._selected_apps_labels.append(remove_button)

    def _display_name_for(self, process_name: str) -> str:
        if process_name in self._custom_display_names:
            return self._custom_display_names[process_name]
        if process_name in self._app_display_names:
            return self._app_display_names[process_name]
        name = Path(process_name).stem.replace("_", " ").replace("-", " ").strip()
        return name.title() if name else process_name

    def _get_selected_intensity(self) -> str:
        for mode, card in self._intensity_cards.items():
            if card.isChecked():
                return mode
        return "Standard"

    def get_config(self) -> FocusConfig:
        config = FocusConfig(
            whitelist=list(self._whitelist),
            duration_minutes=self._custom_min_spin.value(),
            mode=self._get_selected_intensity(),
            max_esc=self._max_esc_spin.value(),
            esc_break_minutes=self._esc_break_spin.value(),
        )
        # FocusConfig is intentionally kept backward-compatible; these optional
        # fields are attached dynamically until the shared model adopts them.
        config.goal = self._goal_edit.text().strip()
        config.custom_apps = list(self._custom_apps)
        return config

    def set_config(self, config: FocusConfig) -> None:
        self._apply_config(config, emit=not self._updating)

    def _apply_config(self, config: FocusConfig, emit: bool) -> None:
        previous_updating = self._updating
        self._updating = True
        try:
            self._whitelist = self._deduplicated(getattr(config, "whitelist", []))
            custom_apps = getattr(config, "custom_apps", None)
            if custom_apps is not None:
                self._custom_apps = self._deduplicated(custom_apps)

            self._custom_display_names.clear()
            for path in self._custom_apps:
                identifier, display_name = self._custom_app_identity(path)
                self._custom_display_names[identifier] = display_name
                self._app_display_names[identifier] = display_name

            self._goal_edit.setText(str(getattr(config, "goal", "") or ""))
            self._custom_min_spin.setValue(
                max(5, min(240, int(getattr(config, "duration_minutes", 25))))
            )
            self._max_esc_spin.setValue(
                max(0, min(10, int(getattr(config, "max_esc", 2))))
            )
            self._esc_break_spin.setValue(
                max(1, min(15, int(getattr(config, "esc_break_minutes", 3))))
            )

            selected_mode = str(getattr(config, "mode", "Standard"))
            if selected_mode not in self._intensity_cards:
                selected_mode = "Standard"
            for mode, card in self._intensity_cards.items():
                card.set_selected(mode == selected_mode)
            for process_name, chip in self._chip_widgets.items():
                chip.set_selected(process_name in self._whitelist)

            self._sync_duration_buttons()
            self._update_selected_display()
        finally:
            self._updating = previous_updating

        if emit:
            self._emit_config_changed()

    def save_config(self) -> None:
        settings = QSettings(self.SETTINGS_ORGANIZATION, self.SETTINGS_APPLICATION)
        settings.beginGroup(self.SETTINGS_GROUP)
        config = self.get_config()
        settings.setValue("goal", getattr(config, "goal", ""))
        settings.setValue("duration_minutes", config.duration_minutes)
        settings.setValue("mode", config.mode)
        settings.setValue("max_esc", config.max_esc)
        settings.setValue("esc_break_minutes", config.esc_break_minutes)
        settings.setValue("whitelist", config.whitelist)
        settings.setValue("custom_apps", list(self._custom_apps))
        settings.endGroup()
        settings.sync()

    def load_config(self) -> FocusConfig:
        settings = QSettings(self.SETTINGS_ORGANIZATION, self.SETTINGS_APPLICATION)
        settings.beginGroup(self.SETTINGS_GROUP)
        config = FocusConfig(
            whitelist=self._as_string_list(settings.value("whitelist", [])),
            duration_minutes=self._as_int(settings.value("duration_minutes", 25), 25),
            mode=str(settings.value("mode", "Standard") or "Standard"),
            max_esc=self._as_int(settings.value("max_esc", 2), 2),
            esc_break_minutes=self._as_int(settings.value("esc_break_minutes", 3), 3),
        )
        config.goal = str(settings.value("goal", "") or "")
        config.custom_apps = self._as_string_list(settings.value("custom_apps", []))
        settings.endGroup()
        self._apply_config(config, emit=False)
        return config

    def _emit_config_changed(self) -> None:
        if self._updating:
            return
        self.save_config()
        self.config_changed.emit(self.get_config())

    @staticmethod
    def _as_string_list(value) -> list[str]:
        if value is None:
            return []
        if isinstance(value, (list, tuple)):
            return [str(item) for item in value if str(item)]
        text = str(value)
        return [text] if text else []

    @staticmethod
    def _as_int(value, default: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _deduplicated(values: Iterable[str]) -> list[str]:
        return list(dict.fromkeys(str(value) for value in values if str(value)))
