"""Application category manager."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from focus_capsule.app_categories import merge_catalog_categories
from focus_capsule.data_models import DEFAULT_CATEGORIES, AppConfig
from focus_capsule.data_store import DataStore
from focus_capsule.icon_utils import discover_installed_apps


class AppCategoryDialog(QDialog):
    """Show every discovered app and let the user override its category."""

    categories_saved = pyqtSignal(object)

    def __init__(self, data_store: DataStore, parent=None):
        super().__init__(parent)
        self._store = data_store
        self._config = self._store.load_app_config()
        try:
            catalog = discover_installed_apps()
        except Exception:
            catalog = []
        self._config, changed = merge_catalog_categories(self._config, catalog)
        if changed:
            self._store.save_app_config(self._config)
        self._rows: list[tuple[QWidget, object, QComboBox]] = []

        self.setWindowTitle("应用分类")
        self.setModal(True)
        self.resize(760, 700)
        self.setMinimumSize(620, 520)
        self._setup_ui()

    @property
    def app_config(self) -> AppConfig:
        return self._config

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 20)
        root.setSpacing(12)

        title = QLabel("应用分类")
        title.setObjectName("pageTitle")
        root.addWidget(title)

        subtitle = QLabel(
            "系统已经按用途完成初步分类。你的修改会用于分类专注目标、使用限制和数据统计。"
        )
        subtitle.setObjectName("bodyMuted")
        subtitle.setWordWrap(True)
        root.addWidget(subtitle)

        self._search = QLineEdit()
        self._search.setObjectName("goalInput")
        self._search.setPlaceholderText("搜索应用或分类")
        self._search.setClearButtonEnabled(True)
        self._search.textChanged.connect(self._filter_rows)
        root.addWidget(self._search)

        self._count = QLabel()
        self._count.setObjectName("hint")
        root.addWidget(self._count)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        self._rows_layout = QVBoxLayout(content)
        self._rows_layout.setContentsMargins(0, 0, 0, 0)
        self._rows_layout.setSpacing(8)

        for app in self._config.app_categories:
            row = QFrame()
            row.setObjectName("softPanel")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(14, 10, 14, 10)
            row_layout.setSpacing(12)

            names = QVBoxLayout()
            names.setSpacing(2)
            display = QLabel(app.display_name or app.process_name)
            display.setObjectName("summaryGoal")
            names.addWidget(display)
            process = QLabel(app.process_name)
            process.setObjectName("bodyTertiary")
            names.addWidget(process)
            row_layout.addLayout(names, 1)

            category = QComboBox()
            category.addItems(DEFAULT_CATEGORIES)
            if app.category not in DEFAULT_CATEGORIES:
                category.addItem(app.category)
            category.setCurrentText(app.category or "其他")
            category.setMinimumWidth(150)
            category.setAccessibleName(f"{app.display_name}分类")
            row_layout.addWidget(category)

            self._rows_layout.addWidget(row)
            self._rows.append((row, app, category))

        self._rows_layout.addStretch()
        scroll.setWidget(content)
        root.addWidget(scroll, 1)

        actions = QHBoxLayout()
        actions.addStretch()
        cancel = QPushButton("取消")
        cancel.setObjectName("ghostButton")
        cancel.clicked.connect(self.reject)
        actions.addWidget(cancel)
        save = QPushButton("保存分类")
        save.setObjectName("primaryButton")
        save.setMinimumWidth(130)
        save.clicked.connect(self._save)
        actions.addWidget(save)
        root.addLayout(actions)
        self._filter_rows("")

    def _filter_rows(self, query: str) -> None:
        needle = query.strip().casefold()
        shown = 0
        for row, app, combo in self._rows:
            haystack = " ".join(
                (app.display_name, app.process_name, combo.currentText())
            ).casefold()
            visible = not needle or needle in haystack
            row.setVisible(visible)
            shown += int(visible)
        self._count.setText(f"共 {len(self._rows)} 个应用 · 当前显示 {shown} 个")

    def _save(self) -> None:
        for _row, app, combo in self._rows:
            app.category = combo.currentText()
        self._store.save_app_config(self._config)
        self.categories_saved.emit(self._config)
        self.accept()
