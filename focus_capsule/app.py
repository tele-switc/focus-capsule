"""Application entry point."""

from __future__ import annotations

import logging
import sys
import time
from collections.abc import Callable
from pathlib import Path
from types import TracebackType

from PyQt6.QtCore import QStandardPaths, Qt
from PyQt6.QtGui import QColor, QFont, QIcon, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import QApplication

from focus_capsule.dialogs import show_critical
from focus_capsule.main_window import MainWindow
from focus_capsule.styles import STYLESHEET

EXCEPTION_DIALOG_COOLDOWN_SECONDS = 60.0


class ExceptionHandler:
    """Log every uncaught error without repeatedly covering the UI with dialogs."""

    def __init__(
        self,
        log_path: Path,
        *,
        show_dialog: Callable[[object, str, str], None] = show_critical,
        clock: Callable[[], float] = time.monotonic,
    ):
        self._log_path = log_path
        self._show_dialog = show_dialog
        self._clock = clock
        self._last_dialog_at: dict[tuple[str, str, int], float] = {}
        self._dialog_active = False

    @staticmethod
    def _fingerprint(
        exc_type: type[BaseException],
        exc_traceback: TracebackType | None,
    ) -> tuple[str, str, int]:
        frame = exc_traceback
        while frame is not None and frame.tb_next is not None:
            frame = frame.tb_next
        location = frame.tb_frame.f_code.co_filename if frame is not None else ""
        line = frame.tb_lineno if frame is not None else 0
        return (f"{exc_type.__module__}.{exc_type.__qualname__}", location, line)

    def __call__(
        self,
        exc_type: type[BaseException],
        exc_value: BaseException,
        exc_traceback: TracebackType | None,
    ) -> None:
        logger = logging.getLogger("focus_capsule")
        logger.error(
            "Unhandled application error",
            exc_info=(exc_type, exc_value, exc_traceback),
        )

        fingerprint = self._fingerprint(exc_type, exc_traceback)
        now = self._clock()
        last_dialog_at = self._last_dialog_at.get(fingerprint)
        if self._dialog_active or (
            last_dialog_at is not None
            and now - last_dialog_at < EXCEPTION_DIALOG_COOLDOWN_SECONDS
        ):
            return

        self._last_dialog_at[fingerprint] = now
        self._dialog_active = True
        try:
            self._show_dialog(
                None,
                "专注舱遇到问题",
                "应用遇到意外错误。你的历史记录仍保存在本机。\n\n"
                f"诊断日志：{self._log_path}",
            )
        except Exception:
            logger.exception("Unable to display the application error dialog")
        finally:
            self._dialog_active = False


def _app_icon() -> QIcon:
    pixmap = QPixmap(128, 128)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor("#5B6FE8"))
    painter.setPen(QPen(QColor("#4758C8"), 3))
    painter.drawRoundedRect(8, 8, 112, 112, 28, 28)
    painter.setPen(QPen(QColor("#3B8D75"), 11, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    painter.drawArc(30, 30, 68, 68, 80 * 16, -285 * 16)
    painter.setBrush(QColor("#F4F3EF"))
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

    sys.excepthook = ExceptionHandler(log_path)

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
