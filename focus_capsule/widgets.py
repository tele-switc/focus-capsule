"""Small, reusable widgets that define Focus Capsule's visual signature."""

from __future__ import annotations

import math

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from focus_capsule import theme as T
from PyQt6.QtWidgets import QLabel, QSizePolicy, QWidget


class FocusRing(QWidget):
    """A calm circular progress indicator used before, during and after focus."""

    COLORS = {
        # 状态色走主题 token，深色专注模式下才不会与背景冲突
        "ready": "RING_READY",
        "running": "RING_RUNNING",
        "break": "RING_BREAK",
        "complete": "RING_COMPLETE",
        "stopped": "RING_STOPPED",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._progress = 0.0
        self._center_text = "25\n分钟"
        self._caption = "准备开始"
        self._state = "ready"
        self.setMinimumSize(220, 220)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setAccessibleName("专注进度")

    def set_progress(self, progress: float):
        self._progress = max(0.0, min(100.0, float(progress)))
        self.update()

    def set_center_text(self, text: str):
        self._center_text = text
        self.update()

    def set_caption(self, text: str):
        self._caption = text
        self.update()

    def set_state(self, state: str):
        self._state = state if state in self.COLORS else "ready"
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        side = min(self.width(), self.height())
        outer = QRectF(
            (self.width() - side) / 2 + 18,
            (self.height() - side) / 2 + 18,
            side - 36,
            side - 36,
        )

        track_pen = QPen(QColor(T.get("RING_TRACK")), 12)
        track_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(track_pen)
        painter.drawArc(outer, 0, 360 * 16)

        accent = QColor(T.get(self.COLORS[self._state]))
        progress_pen = QPen(accent, 12)
        progress_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(progress_pen)
        span = max(8.0 if self._progress == 0 else 0.0, self._progress) * 3.6
        painter.drawArc(outer, 90 * 16, -int(span * 16))

        if self._progress > 0:
            angle = math.radians(90 - span)
            radius = outer.width() / 2
            cx, cy = outer.center().x(), outer.center().y()
            marker_x = cx + math.cos(angle) * radius
            marker_y = cy - math.sin(angle) * radius
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(T.get("TEXT_PRIMARY")))
            painter.drawEllipse(QRectF(marker_x - 3, marker_y - 3, 6, 6))

        text_rect = outer.adjusted(28, 48, -28, -46)
        painter.setPen(QColor(T.get("TEXT_PRIMARY")))
        value_font = QFont(self.font())
        value_font.setPointSize(max(18, int(side * 0.095)))
        value_font.setWeight(QFont.Weight.DemiBold)
        value_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, -0.5)
        painter.setFont(value_font)
        painter.drawText(
            text_rect,
            Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
            self._center_text,
        )

        caption_rect = QRectF(outer.left(), outer.center().y() + 38, outer.width(), 28)
        painter.setPen(QColor(T.get("TEXT_TERTIARY")))
        caption_font = QFont(self.font())
        caption_font.setPointSize(10)
        caption_font.setWeight(QFont.Weight.Medium)
        painter.setFont(caption_font)
        painter.drawText(caption_rect, Qt.AlignmentFlag.AlignCenter, self._caption)


class StatLabel(QLabel):
    """A value label with tabular-number friendly sizing."""

    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setObjectName("statValue")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

