"""Application entry point."""

from __future__ import annotations

import logging
import os
from pathlib import Path
import sys

from PyQt6.QtCore import QStandardPaths, Qt
from PyQt6.QtGui import QColor, QFont, QIcon, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import QApplication

from focus_capsule.dialogs import show_critical
from focus_capsule.main_window import MainWindow
from focus_capsule.styles import STYLESHEET


def _app_icon() -> QIcon:
    pixmap = QPixmap(128, 128)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor("#122033"))
    painter.setPen(QPen(QColor("#2D425F"), 3))
    painter.drawRoundedRect(8, 8, 112, 112, 30, 30)
    painter.setPen(QPen(QColor("#67CFBB"), 11, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    painter.drawArc(30, 30, 68, 68, 80 * 16, -285 * 16)
    painter.setBrush(QColor("#F5F7FA"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(57, 57, 14, 14)
    painter.end()
    return QIcon(pixmap)


def _configure_logging() -> Path:
    data_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
    path = Path(data_dir or Path.home() / ".focus-capsule")
    path.mkdir(parents=True, exist_ok=True)
    log_path = path / "focus-capsule.log"
    logging.basicConfig(
        filename=log_path,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        encoding="utf-8",
    )
    return log_path


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Focus Capsule")
    app.setApplicationDisplayName("专注舱")
    app.setOrganizationName("FocusCapsule")
    app.setQuitOnLastWindowClosed(False)
    app.setStyle("Fusion")

    if sys.platform == "darwin":
        family, point_size = "PingFang SC", 13
    elif sys.platform == "win32":
        family, point_size = "Microsoft YaHei UI", 10
    else:
        family, point_size = "Noto Sans CJK SC", 11
    font = QFont(family, point_size)
    font.setStyleHint(QFont.StyleHint.SansSerif)
    app.setFont(font)
    app.setStyleSheet(STYLESHEET)
    app.setWindowIcon(_app_icon())

    log_path = _configure_logging()

    def handle_exception(exc_type, exc_value, exc_traceback):
        logging.getLogger("focus_capsule").exception(
            "Unhandled application error",
            exc_info=(exc_type, exc_value, exc_traceback),
        )
        show_critical(
            None,
            "专注舱遇到问题",
            f"应用遇到意外错误。你的历史记录仍保存在本机。\n\n诊断日志：{log_path}",
        )

    sys.excepthook = handle_exception

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
