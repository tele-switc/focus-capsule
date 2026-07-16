"""Accessible, responsive settings panel for Focus Capsule."""

from __future__ import annotations

import os
import sys
from collections.abc import Iterable
from pathlib import Path

from PyQt6.QtCore import QEvent, QPoint, QRect, QSettings, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QFontMetrics
from PyQt6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLayoutItem,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from focus_capsule.icon_utils import (
    app_pixmap,
    discover_installed_apps,
    resolve_windows_app_target,
    windows_shortcut_details,
)
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
            ("终端", "windowsterminal.exe"),
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
MIN_FOCUS_MINUTES = 1
MAX_FOCUS_MINUTES = (2**31 - 1) // 60


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
    selection-background-color: #5B6FE8;
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
    border: 2px solid #5B6FE8;
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
    border: 2px solid #5B6FE8;
    color: #e8fffa;
}

QPushButton#appIconTile {
    /* QSS width/height describe the content box; borders add 2 px. */
    min-width: 94px;
    max-width: 94px;
    min-height: 104px;
    max-height: 104px;
    border: 1px solid #2b3b50;
    border-radius: 12px;
    padding: 0;
    background-color: #141d27;
}

QPushButton#appIconTile:hover {
    border-color: #5B6FE8;
    background-color: #172233;
}

QPushButton#appIconTile:checked {
    border: 2px solid #5B6FE8;
    background-color: #17342F;
}

QWidget#appIconTilesScroll {
    border: none;
    background: transparent;
}

QLabel#appTileName {
    color: #b0bcc8;
    font-size: 12px;
    font-weight: 500;
}

QLabel#appTileCheck {
    min-width: 20px;
    max-width: 20px;
    min-height: 20px;
    max-height: 20px;
    color: #071510;
    background-color: #5B6FE8;
    border: 2px solid #17342f;
    border-radius: 10px;
    font-size: 12px;
    font-weight: bold;
}

QPushButton#appIconTile:checked QLabel#appTileName {
    color: #a8efe1;
}

QPushButton#durationChip:focus,
QPushButton#appIconTile:focus,
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
    border-color: #5B6FE8;
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
    border: 2px solid #5B6FE8;
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
        parent: QWidget | None = None,
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

    def itemAt(self, index: int) -> QLayoutItem | None:
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index: int) -> QLayoutItem | None:
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
        parent: QWidget | None = None,
        columns: int = 6,
        h_spacing: int = 8,
        v_spacing: int = 10,
    ):
        super().__init__(parent)
        self._columns = columns
        self._h_spacing = h_spacing
        self._v_spacing = v_spacing
        self._tiles: list[QWidget] = []
        self._effective_columns = 1
        self._layout = QGridLayout(self)
        self._layout.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setHorizontalSpacing(self._h_spacing)
        self._layout.setVerticalSpacing(self._v_spacing)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumWidth(0)
        self.setFixedHeight(0)

    @property
    def columns(self) -> int:
        return self._columns

    @columns.setter
    def columns(self, value: int) -> None:
        self._columns = max(4, value)
        self._relayout()

    def add_tile(self, widget: QWidget) -> None:
        self._tiles.append(widget)
        widget.setParent(self)
        widget.show()
        self._relayout()

    def clear_tiles(self) -> None:
        while self._layout.count():
            self._layout.takeAt(0)
        for w in self._tiles:
            w.deleteLater()
        self._tiles.clear()
        self.setFixedHeight(0)
        self.updateGeometry()
        self.update()

    def _relayout(self) -> None:
        while self._layout.count():
            self._layout.takeAt(0)

        visible_tiles = [tile for tile in self._tiles if not tile.isHidden()]
        if not visible_tiles:
            self._effective_columns = 1
            self.setFixedHeight(0)
            self.updateGeometry()
            return

        tile_w = AppChip.TILE_W
        tile_h = AppChip.TILE_H
        available = max(tile_w, self.contentsRect().width())
        cols_that_fit = max(1, (available + self._h_spacing) // (tile_w + self._h_spacing))
        cols = max(1, min(self._columns, cols_that_fit))
        self._effective_columns = cols

        for index, tile in enumerate(visible_tiles):
            row, column = divmod(index, cols)
            self._layout.addWidget(tile, row, column, Qt.AlignmentFlag.AlignLeft)

        for column in range(cols):
            self._layout.setColumnStretch(column, 0)
        self._layout.setColumnStretch(cols, 1)

        rows = (len(visible_tiles) + cols - 1) // cols
        total_height = rows * tile_h + max(0, rows - 1) * self._v_spacing
        self.setFixedHeight(total_height)
        self.updateGeometry()

    def refresh(self) -> None:
        """Reflow after tiles have been shown or hidden."""
        self._relayout()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._relayout()

    def sizeHint(self) -> QSize:
        if not self._tiles:
            return QSize(0, 0)
        preferred_width = (
            self._columns * AppChip.TILE_W
            + max(0, self._columns - 1) * self._h_spacing
        )
        return QSize(preferred_width, self.height())


class AppChip(QPushButton):
    """Icon tile with app icon + label, like Windows "Open With" picker."""

    toggled_app = pyqtSignal(str, bool)

    ICON_SIZE = 44
    TILE_W = 96
    TILE_H = 106

    def __init__(
        self,
        display_name: str,
        process_name: str,
        custom_path: str = "",
        parent=None,
        *,
        icon_source: str = "",
        icon_index: int = 0,
    ):
        super().__init__(parent)
        self._display_name = display_name
        self._process_name = process_name
        self._custom_path = custom_path
        self._icon_source = icon_source
        self._icon_index = int(icon_index)
        self._selected = False
        self.setObjectName("appIconTile")
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMinimumSize(self.TILE_W, self.TILE_H)
        self.setMaximumSize(self.TILE_W, self.TILE_H)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setAccessibleDescription(f"专注期间允许使用 {display_name}")
        self.toggled.connect(self._on_toggled)
        self._refresh_accessibility(False)
        self._build_content()

    def sizeHint(self) -> QSize:
        return QSize(self.TILE_W, self.TILE_H)

    def minimumSizeHint(self) -> QSize:
        return QSize(self.TILE_W, self.TILE_H)

    @property
    def display_name(self) -> str:
        return self._display_name

    @property
    def process_name(self) -> str:
        return self._process_name

    @property
    def custom_path(self) -> str:
        return self._custom_path

    def _build_content(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 9, 5, 7)
        layout.setSpacing(6)

        self._icon_label = QLabel()
        self._icon_label.setFixedSize(self.ICON_SIZE, self.ICON_SIZE)
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.update_icon()
        layout.addWidget(self._icon_label, 0, Qt.AlignmentFlag.AlignCenter)

        metrics = QFontMetrics(self.font())
        visible_name = metrics.elidedText(
            self._display_name,
            Qt.TextElideMode.ElideRight,
            self.TILE_W - 14,
        )
        self._name_label = QLabel(visible_name)
        self._name_label.setObjectName("appTileName")
        self._name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._name_label.setWordWrap(False)
        self._name_label.setFixedWidth(self.TILE_W - 10)
        self._name_label.setFixedHeight(20)
        self._name_label.setToolTip(self._display_name)
        self._name_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(self._name_label)

        self._check_label = QLabel("✓", self)
        self._check_label.setObjectName("appTileCheck")
        self._check_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._check_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._check_label.move(self.TILE_W - 27, 7)
        self._check_label.hide()
        self._check_label.raise_()

    def _on_toggled(self, checked: bool) -> None:
        self._selected = checked
        self._check_label.setVisible(checked)
        self._refresh_accessibility(checked)
        self.toggled_app.emit(self._process_name, checked)

    def _refresh_accessibility(self, checked: bool) -> None:
        state = "已允许" if checked else "未允许"
        self.setAccessibleName(f"{self._display_name}，{state}")

    def set_selected(self, selected: bool) -> None:
        self.setChecked(selected)

    def update_icon(self) -> None:
        """Re-extract icon (e.g. after a custom app is added)."""
        self._icon_label.setPixmap(
            app_pixmap(
                self._process_name,
                self._custom_path,
                self.ICON_SIZE,
                icon_source=self._icon_source,
                icon_index=self._icon_index,
                device_pixel_ratio=float(self.devicePixelRatioF()),
            )
        )


class InstalledAppPickerDialog(QDialog):
    """Searchable icon catalog for installed apps not shown in the main grid."""

    def __init__(self, apps: list[dict], selected: Iterable[str], parent=None):
        super().__init__(parent)
        self._apps = list(apps)
        self._selected = {str(process).casefold() for process in selected}
        self._chosen: dict[str, dict] = {}
        self._tiles: list[AppChip] = []
        self.setObjectName("appPickerDialog")
        self.setWindowTitle("选择其他已安装应用")
        self.setModal(True)
        self.setMinimumSize(680, 520)
        self.resize(760, 620)
        self.setStyleSheet(PANEL_STYLESHEET)
        self._setup_ui()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 22)
        root.setSpacing(14)

        title = QLabel("选择其他已安装应用")
        title.setObjectName("settingsTitle")
        root.addWidget(title)
        subtitle = QLabel("这里只显示在这台电脑上检测到、且未放在常用区的软件。")
        subtitle.setObjectName("settingsSubtitle")
        subtitle.setWordWrap(True)
        root.addWidget(subtitle)

        self._search = QLineEdit()
        self._search.setObjectName("goalInput")
        self._search.setPlaceholderText("搜索应用名称、进程或路径")
        self._search.setClearButtonEnabled(True)
        self._search.setAccessibleName("搜索其他已安装应用")
        self._search.textChanged.connect(self._filter_tiles)
        self._search.installEventFilter(self)
        root.addWidget(self._search)

        scroll = QScrollArea()
        scroll.setObjectName("appPickerScroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 4, 4, 4)
        container_layout.setSpacing(0)
        container_layout.setSizeConstraint(QLayout.SizeConstraint.SetMinAndMaxSize)
        self._grid = IconGrid(container, columns=6, h_spacing=10, v_spacing=12)
        container_layout.addWidget(self._grid)
        scroll.setWidget(container)
        root.addWidget(scroll, 1)

        for info in self._apps:
            self._add_app_tile(info, str(info.get("process_name", "")).casefold() in self._selected)

        self._empty = QLabel("没有检测到更多应用。你仍可手动选择本机应用程序。")
        self._empty.setObjectName("selectedEmpty")
        self._empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty.setMinimumHeight(72)
        self._empty.setVisible(not self._tiles)
        root.addWidget(self._empty)

        footer = QHBoxLayout()
        self._count_label = QLabel()
        self._count_label.setObjectName("selectedSummary")
        footer.addWidget(self._count_label)
        self._browse_button = QPushButton("未找到？手动选择应用…")
        self._browse_button.setObjectName("ghostButton")
        self._browse_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._browse_button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._browse_button.setAccessibleName("从这台电脑手动选择应用程序")
        self._browse_button.clicked.connect(self._browse_apps)
        footer.addWidget(self._browse_button)
        footer.addStretch()
        cancel = QPushButton("取消")
        cancel.setObjectName("ghostButton")
        cancel.clicked.connect(self.reject)
        footer.addWidget(cancel)
        self._add_button = QPushButton("添加所选")
        self._add_button.setObjectName("primaryButton")
        self._add_button.setAccessibleName("添加所选应用")
        self._add_button.setEnabled(bool(self._selected))
        self._add_button.clicked.connect(self.accept)
        footer.addWidget(self._add_button)
        root.addLayout(footer)
        self._update_count()
        self._search.setFocus(Qt.FocusReason.OtherFocusReason)

    def _add_app_tile(self, info: dict, selected: bool) -> AppChip | None:
        display = str(info.get("display_name", "")).strip()
        process = str(info.get("process_name", "")).strip().casefold()
        path = str(info.get("custom_path", "")).strip()
        icon_source = str(info.get("icon_source", "")).strip()
        icon_index = int(info.get("icon_index", 0) or 0)
        if not display or not process:
            return None

        existing = next(
            (tile for tile in self._tiles if tile.process_name.casefold() == process),
            None,
        )
        if existing:
            if selected and not existing.isChecked():
                existing.setChecked(True)
            return existing

        normalized_info = {
            "display_name": display,
            "process_name": process,
            "custom_path": path,
        }
        if icon_source:
            normalized_info["icon_source"] = icon_source
            normalized_info["icon_index"] = icon_index
        app_user_model_id = str(info.get("app_user_model_id", "")).strip()
        if app_user_model_id:
            normalized_info["app_user_model_id"] = app_user_model_id
        tile = AppChip(
            display,
            process,
            path,
            self._grid,
            icon_source=icon_source,
            icon_index=icon_index,
        )
        tile.blockSignals(True)
        tile.set_selected(selected)
        tile.blockSignals(False)
        if selected:
            self._selected.add(process)
            self._chosen[process] = dict(normalized_info)
        tile.toggled_app.connect(
            lambda emitted_process, checked, app_info=normalized_info: self._on_tile_toggled(
                emitted_process,
                checked,
                app_info,
            )
        )
        tile.installEventFilter(self)
        self._tiles.append(tile)
        self._grid.add_tile(tile)
        return tile

    def _browse_apps(self) -> None:
        if os.name == "nt":
            selected_paths, _ = QFileDialog.getOpenFileNames(
                self,
                "手动选择应用程序",
                "",
                "Windows 应用 (*.exe *.lnk)",
            )
        elif sys.platform == "darwin":
            selected_paths, _ = QFileDialog.getOpenFileNames(
                self,
                "手动选择应用程序",
                "/Applications",
                "macOS 应用 (*.app)",
            )
        else:
            selected_paths, _ = QFileDialog.getOpenFileNames(
                self,
                "手动选择应用程序",
                "",
                "可执行文件 (*)",
            )
        if not selected_paths:
            return

        invalid_names: list[str] = []
        last_tile: AppChip | None = None
        self._search.clear()
        for selected_path in selected_paths:
            validated_path = SettingsPanel._validated_app_path(selected_path)
            if not validated_path:
                invalid_names.append(Path(selected_path).name)
                continue
            process, default_display = SettingsPanel._custom_app_identity(validated_path)
            source_path = Path(selected_path)
            display = (
                source_path.stem
                if source_path.suffix.casefold() == ".lnk"
                else default_display
            )
            info = {
                "display_name": display,
                "process_name": process.casefold(),
                "custom_path": validated_path,
            }
            if os.name == "nt" and source_path.suffix.casefold() == ".lnk":
                _target, icon_source, icon_index = windows_shortcut_details(selected_path)
                if icon_source:
                    info["icon_source"] = icon_source
                    info["icon_index"] = icon_index
            last_tile = self._add_app_tile(info, selected=True)

        self._grid.refresh()
        self._empty.setVisible(not self._tiles)
        self._update_count()
        if last_tile:
            last_tile.show()
            last_tile.setFocus(Qt.FocusReason.OtherFocusReason)
        if invalid_names:
            QMessageBox.warning(
                self,
                "无法添加应用",
                "请选择仍然存在且可以运行的应用程序。\n\n"
                + "未添加："
                + "、".join(invalid_names),
            )

    def eventFilter(self, watched, event) -> bool:
        if event.type() != QEvent.Type.KeyPress:
            return super().eventFilter(watched, event)

        visible_tiles = [tile for tile in self._tiles if not tile.isHidden()]
        key = event.key()
        if watched is self._search and key == Qt.Key.Key_Down and visible_tiles:
            visible_tiles[0].setFocus(Qt.FocusReason.TabFocusReason)
            return True
        if watched not in visible_tiles:
            return super().eventFilter(watched, event)

        index = visible_tiles.index(watched)
        columns = max(1, self._grid._effective_columns)
        offsets = {
            Qt.Key.Key_Left: -1,
            Qt.Key.Key_Right: 1,
            Qt.Key.Key_Up: -columns,
            Qt.Key.Key_Down: columns,
        }
        offset = offsets.get(key)
        if offset is None:
            return super().eventFilter(watched, event)
        target = index + offset
        if 0 <= target < len(visible_tiles):
            visible_tiles[target].setFocus(Qt.FocusReason.OtherFocusReason)
        return True

    def _on_tile_toggled(
        self,
        process_name: str,
        checked: bool,
        app_info: dict,
    ) -> None:
        normalized = process_name.casefold()
        if checked:
            self._selected.add(normalized)
            self._chosen[normalized] = dict(app_info)
        else:
            self._selected.discard(normalized)
            self._chosen.pop(normalized, None)
        self._update_count()

    def _filter_tiles(self, query: str) -> None:
        needle = query.strip().casefold()
        visible = 0
        for tile in self._tiles:
            haystack = " ".join(
                (tile.display_name, tile.process_name, tile.custom_path)
            ).casefold()
            matched = not needle or needle in haystack
            tile.setVisible(matched)
            visible += int(matched)
        self._grid.refresh()
        if needle:
            self._empty.setText(
                f"没有匹配“{query.strip()}”的已安装应用。"
                "你仍可手动选择。"
            )
        else:
            self._empty.setText("没有检测到更多应用。你仍可手动选择本机应用程序。")
        self._empty.setVisible(visible == 0)
        self._update_count(visible)

    def _update_count(self, visible: int | None = None) -> None:
        shown = len(self._tiles) if visible is None else visible
        self._count_label.setText(
            f"显示 {shown} 个 · 已选择 {len(self._chosen)} 个"
        )
        self._add_button.setEnabled(bool(self._chosen))

    def selected_apps(self) -> list[dict]:
        return list(self._chosen.values())


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
        self._installed_apps: list[dict] = []
        self._installed_by_process: dict[str, dict] = {}
        self._pinned_processes: set[str] = set()
        self._app_display_names = {process: name for name, process in COMMON_APPS}
        self._selected_apps_labels: list[QPushButton] = []
        self._load_installed_catalog()
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

    def _load_installed_catalog(self) -> None:
        """Load a normalized catalog containing only apps present on this device."""
        try:
            discovered = discover_installed_apps()
        except Exception:
            discovered = []

        installed: list[dict] = []
        by_process: dict[str, dict] = {}
        for raw in discovered:
            display = str(raw.get("display_name", "")).strip()
            process = str(raw.get("process_name", "")).strip().casefold()
            path = str(raw.get("custom_path", "")).strip()
            if not display or not process or not path:
                continue
            path_obj = Path(path)
            exists = path_obj.is_dir() if sys.platform == "darwin" else path_obj.is_file()
            if not exists:
                continue
            if os.name == "nt" and path_obj.suffix.casefold() != ".exe":
                continue
            if sys.platform == "darwin" and path_obj.suffix.casefold() != ".app":
                continue
            if process in by_process:
                continue
            info = {
                "display_name": display,
                "process_name": process,
                "custom_path": str(path_obj),
            }
            icon_source = str(raw.get("icon_source", "")).strip()
            if icon_source and Path(icon_source).is_file():
                info["icon_source"] = icon_source
                info["icon_index"] = int(raw.get("icon_index", 0) or 0)
            app_user_model_id = str(raw.get("app_user_model_id", "")).strip()
            if app_user_model_id:
                info["app_user_model_id"] = app_user_model_id
            installed.append(info)
            by_process[process] = info

        self._installed_apps = installed
        self._installed_by_process = by_process
        for process, info in by_process.items():
            self._app_display_names[process] = str(info["display_name"])

    def _primary_installed_apps(self) -> list[dict]:
        """Return only installed common apps; user-pinned extras are added later."""
        primary: list[dict] = []
        for friendly_name, process_name in COMMON_APPS:
            normalized = process_name.casefold()
            info = self._installed_by_process.get(normalized)
            if not info:
                continue
            item = dict(info)
            item["display_name"] = friendly_name
            primary.append(item)
        return primary

    def _add_primary_tile(self, info: dict, selected: bool = False) -> AppChip:
        process = str(info.get("process_name", "")).strip().casefold()
        existing = self._chip_widgets.get(process)
        if existing:
            if selected and not existing.isChecked():
                existing.blockSignals(True)
                existing.set_selected(True)
                existing.blockSignals(False)
            return existing

        display = str(info.get("display_name", process)).strip() or process
        path = str(info.get("custom_path", "")).strip()
        tile = AppChip(
            display,
            process,
            path,
            self,
            icon_source=str(info.get("icon_source", "")).strip(),
            icon_index=int(info.get("icon_index", 0) or 0),
        )
        tile.toggled_app.connect(self._on_chip_toggle)
        tile.blockSignals(True)
        tile.set_selected(selected)
        tile.blockSignals(False)
        self._icon_grid.add_tile(tile)
        self._chip_widgets[process] = tile
        self._app_display_names[process] = display
        return tile

    def _remaining_installed_apps(self) -> list[dict]:
        visible = {process.casefold() for process in self._chip_widgets}
        return [
            dict(info)
            for info in self._installed_apps
            if str(info.get("process_name", "")).casefold() not in visible
        ]

    def _refresh_other_apps_button(self) -> None:
        if not hasattr(self, "_other_apps_button"):
            return
        remaining = len(self._remaining_installed_apps())
        self._other_apps_button.setText(
            f"＋ 选择其他应用（{remaining}）"
            if remaining
            else "＋ 手动选择应用…"
        )
        self._other_apps_button.setEnabled(True)
        self._other_apps_button.setToolTip(
            "打开本机其余已安装软件的图标列表，也可手动选择程序"
            if remaining
            else "手动选择这台电脑上实际存在的应用程序"
        )

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
        section, layout = self._new_section(
            "专注多久？",
            "选择常用时长，或直接输入任意正整数分钟。",
        )

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
        custom_label = QLabel("自定义分钟")
        custom_label.setObjectName("fieldHint")
        custom_row.addWidget(custom_label)

        self._custom_min_spin = QSpinBox()
        self._custom_min_spin.setObjectName("durationSpin")
        self._custom_min_spin.setRange(MIN_FOCUS_MINUTES, MAX_FOCUS_MINUTES)
        self._custom_min_spin.setSingleStep(1)
        self._custom_min_spin.setAccelerated(True)
        self._custom_min_spin.setKeyboardTracking(False)
        self._custom_min_spin.setValue(25)
        self._custom_min_spin.setSuffix(" 分钟")
        self._custom_min_spin.setMinimumWidth(160)
        self._custom_min_spin.setAccessibleName("自定义专注时长")
        self._custom_min_spin.setAccessibleDescription("输入任意正整数分钟")
        self._custom_min_spin.valueChanged.connect(self._on_duration_changed)
        custom_row.addWidget(self._custom_min_spin)
        custom_row.addStretch()
        layout.addLayout(custom_row)
        return section

    def _build_apps_section(self) -> QFrame:
        section, layout = self._new_section(
            "专注时允许哪些应用？",
            "这里只显示这台电脑上已安装的软件。点选工作需要的应用，未选中的应用会按保护强度提醒或拦截。",
        )

        self._icon_grid = IconGrid(self, columns=6, h_spacing=8, v_spacing=10)

        for app_info in self._primary_installed_apps():
            self._add_primary_tile(app_info)

        layout.addWidget(self._icon_grid)

        if not self._chip_widgets:
            no_apps = QLabel("没有检测到可选择的已安装应用。")
            no_apps.setObjectName("selectedEmpty")
            no_apps.setWordWrap(True)
            layout.addWidget(no_apps)

        self._other_apps_button = QPushButton()
        self._other_apps_button.setObjectName("addAppButton")
        self._other_apps_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._other_apps_button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._other_apps_button.setAccessibleName("选择其他已安装应用")
        self._other_apps_button.setAccessibleDescription(
            "打开未显示在常用区的已安装应用图标列表"
        )
        self._other_apps_button.clicked.connect(self._open_app_picker)
        layout.addWidget(self._other_apps_button, 0, Qt.AlignmentFlag.AlignLeft)
        self._refresh_other_apps_button()

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
        section, layout = self._new_section(
            "保护强度", "每种强度都说明实际行为，随时可以在下次专注前调整。"
        )

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

    def _open_app_picker(self) -> None:
        remaining = self._remaining_installed_apps()
        dialog = InstalledAppPickerDialog(remaining, (), self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        selected_apps = dialog.selected_apps()
        if not selected_apps:
            return

        last_tile: AppChip | None = None
        previous_updating = self._updating
        self._updating = True
        try:
            for info in selected_apps:
                process = str(info.get("process_name", "")).strip().casefold()
                path = str(info.get("custom_path", "")).strip()
                display = str(info.get("display_name", process)).strip() or process
                if not process or not path:
                    continue
                validated_path = self._validated_app_path(path)
                if not validated_path:
                    continue
                path = validated_path
                self._pinned_processes.add(process)
                if path not in self._custom_apps:
                    self._custom_apps.append(path)
                self._custom_display_names[process] = display
                self._app_display_names[process] = display
                last_tile = self._add_primary_tile(info, selected=True)
                if process not in self._whitelist:
                    self._whitelist.append(process)
        finally:
            self._updating = previous_updating

        self._icon_grid.refresh()
        self._update_selected_display()
        self._refresh_other_apps_button()
        self._emit_config_changed()
        if last_tile:
            last_tile.setFocus(Qt.FocusReason.OtherFocusReason)

    @staticmethod
    def _custom_app_identity(file_path: str) -> tuple[str, str]:
        path = Path(file_path)
        if sys.platform == "darwin" and path.name.lower().endswith(".app"):
            display_name = path.name[:-4]
            return display_name.lower(), display_name
        display_name = path.stem or path.name
        identity_path = file_path
        if os.name == "nt" and path.suffix.casefold() == ".lnk":
            identity_path = resolve_windows_app_target(
                file_path,
                display_hint=display_name,
            )
        identity_name = Path(identity_path).name or path.name
        identifier = (
            identity_name.casefold() if os.name == "nt" else display_name.casefold()
        )
        return identifier, display_name

    @staticmethod
    def _validated_app_path(file_path: str) -> str:
        """Return a real launch target, or an empty string for stale saved entries."""
        path = Path(file_path)
        if sys.platform == "darwin":
            return str(path) if path.is_dir() and path.suffix.casefold() == ".app" else ""
        if os.name == "nt":
            target = resolve_windows_app_target(
                str(path),
                display_hint=path.stem,
            )
            target_path = Path(target)
            if target_path.is_file() and target_path.suffix.casefold() == ".exe":
                return str(target_path)
            return ""
        return str(path) if path.is_file() else ""

    def _remove_selected_app(self, process_name: str) -> None:
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
            requested_whitelist = [
                process.casefold()
                for process in self._deduplicated(getattr(config, "whitelist", []))
            ]
            custom_apps = getattr(config, "custom_apps", None)
            if custom_apps is not None:
                self._custom_apps = []

            self._custom_display_names.clear()
            for path in self._deduplicated(custom_apps or []):
                validated_path = self._validated_app_path(path)
                if not validated_path:
                    continue
                path_obj = Path(validated_path)
                identifier, display_name = self._custom_app_identity(validated_path)
                identifier = identifier.casefold()
                catalog_info = self._installed_by_process.get(identifier)
                resolved_display = (
                    str(catalog_info.get("display_name", display_name))
                    if catalog_info
                    else display_name
                )
                info = dict(catalog_info) if catalog_info else {
                    "display_name": resolved_display,
                    "process_name": identifier,
                    "custom_path": str(path_obj),
                }
                self._custom_apps.append(str(path_obj))
                self._pinned_processes.add(identifier)
                self._custom_display_names[identifier] = resolved_display
                self._app_display_names[identifier] = resolved_display
                if identifier not in self._installed_by_process:
                    self._installed_by_process[identifier] = info
                    self._installed_apps.append(info)
                self._add_primary_tile(info)

            # Migrate previously selected installed apps into the visible main
            # grid even when they predate pinned-app persistence.
            for process in requested_whitelist:
                info = self._installed_by_process.get(process)
                if info and process not in self._chip_widgets:
                    self._pinned_processes.add(process)
                    path = str(info.get("custom_path", ""))
                    if path and path not in self._custom_apps:
                        self._custom_apps.append(path)
                    self._add_primary_tile(info)

            available = set(self._installed_by_process)
            self._whitelist = [
                process for process in requested_whitelist if process in available
            ]

            self._goal_edit.setText(str(getattr(config, "goal", "") or ""))
            self._custom_min_spin.setValue(
                max(
                    MIN_FOCUS_MINUTES,
                    min(
                        MAX_FOCUS_MINUTES,
                        int(getattr(config, "duration_minutes", 25)),
                    ),
                )
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
            self._icon_grid.refresh()
            self._update_selected_display()
            self._refresh_other_apps_button()
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
