"""Antigravity-style dynamic environment background.

A lightweight custom-painted QWidget that renders soft, slowly drifting
ambient orbs across the window background.  Mouse movement applies a gentle
parallax offset, and the frame-rate adapts automatically:
30 FPS while active, 18 FPS while idle, and 8 FPS when the window is in the
background.  No QtWebEngine, no Canvas, no JavaScript — QPainter only.
"""

from __future__ import annotations

import math
import random
from typing import Optional

from PyQt6.QtCore import (
    QElapsedTimer, QPointF, QSize, Qt, QTimer,
)
from PyQt6.QtGui import (
    QColor, QCursor, QPainter, QPaintEvent, QRadialGradient,
)
from PyQt6.QtWidgets import QSizePolicy, QWidget

from focus_capsule.theme import WINDOW_BG

ORB_COLOURS = [
    QColor("#67CFBB"),
    QColor("#8EADD4"),
    QColor("#E6B46B"),
    QColor("#8BD6A8"),
    QColor("#4A6FA5"),
    QColor("#35786D"),
]


class _Orb:
    __slots__ = ("x", "y", "radius", "colour", "vx", "vy",
                 "phase", "alpha", "par_factor", "bound_w", "bound_h")

    def __init__(self, x, y, radius, colour, speed, angle, bound_w, bound_h):
        self.x = x
        self.y = y
        self.radius = radius
        self.colour = colour
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.phase = random.uniform(0, 2 * math.pi)
        self.alpha = random.uniform(0.04, 0.12)
        self.par_factor = 0.2 + (radius / 300) ** 2 * 0.5
        self.bound_w = bound_w
        self.bound_h = bound_h

    def update(self, elapsed: float):
        self.x += self.vx
        self.y += self.vy
        if self.x < -self.radius or self.x > self.bound_w + self.radius:
            self.vx = -self.vx
        if self.y < -self.radius or self.y > self.bound_h + self.radius:
            self.vy = -self.vy
        self.alpha = max(0.02, min(0.15,
                                   self.alpha + math.sin(elapsed * 0.4 + self.phase) * 0.004))


class _StaticOrb:
    __slots__ = ("x", "y", "radius", "colour", "alpha")

    def __init__(self, x, y, radius, colour):
        self.x = x
        self.y = y
        self.radius = radius
        self.colour = colour
        self.alpha = random.uniform(0.02, 0.05)

    def update(self, _elapsed: float):
        self.alpha = max(0.01, min(0.06,
                                   self.alpha + random.uniform(-0.0008, 0.0008)))


class AmbientBackground(QWidget):
    """Soft drifting ambient background that sits behind all other widgets."""

    def __init__(self, parent: Optional[QWidget] = None, orb_count: int = 14):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._rng = random.Random(42)
        self._orbs: list[_Orb] = []
        self._orbs_static: list[_StaticOrb] = []
        self._is_active = True
        self._is_background = False
        self._mouse_x = 0.0
        self._mouse_y = 0.0
        self._target_mouse_x = 0.0
        self._target_mouse_y = 0.0
        self._active_fps = 30
        self._idle_fps = 18
        self._background_fps = 8
        self._frame_timer = QTimer(self)
        self._frame_timer.timeout.connect(self._tick)
        self._elapsed_timer = QElapsedTimer()
        self._elapsed_timer.start()
        self._frame_timer.start(int(1000 / self._active_fps))

        self._pointer_timer = QTimer(self)
        self._pointer_timer.setInterval(80)
        self._pointer_timer.timeout.connect(self._update_pointer)
        self._pointer_timer.start()

        self._populate_timer = QTimer(self)
        self._populate_timer.setSingleShot(True)
        self._populate_timer.setInterval(150)
        self._populate_timer.timeout.connect(self._populate_orbs_from_parent)

        QTimer.singleShot(0, self._populate_orbs_from_parent)

    def set_background(self, in_background: bool):
        self._is_background = in_background
        self._adjust_fps()

    def _adjust_fps(self):
        fps = (
            self._background_fps if self._is_background
            else (self._active_fps if self._is_active else self._idle_fps)
        )
        self._frame_timer.setInterval(int(1000 / max(1, fps)))

    def _populate_orbs_from_parent(self):
        w = max(1, self.parent().width() if self.parent() else 800)
        h = max(1, self.parent().height() if self.parent() else 600)
        self.setFixedSize(w, h)
        self._populate(w, h)

    def _populate(self, w: float, h: float):
        self._orbs.clear()
        self._orbs_static.clear()
        count = max(8, min(20, int(w * h / 50000) // 6))
        for _ in range(count):
            colour = self._rng.choice(ORB_COLOURS)
            x = self._rng.uniform(0, w)
            y = self._rng.uniform(0, h)
            radius = self._rng.uniform(120, 280)
            speed = self._rng.uniform(0.08, 0.25)
            angle = self._rng.uniform(0, 2 * math.pi)
            self._orbs.append(_Orb(x, y, radius, colour, speed, angle, w, h))
        static_count = max(35, min(80, int(w * h / 20000)))
        for _ in range(static_count):
            colour = self._rng.choice(ORB_COLOURS)
            x = self._rng.uniform(0, w)
            y = self._rng.uniform(0, h)
            r = self._rng.uniform(30, 80)
            self._orbs_static.append(_StaticOrb(x, y, r, colour))

    def _update_pointer(self):
        parent = self.parent()
        if parent is None:
            return
        try:
            pos = parent.mapFromGlobal(QCursor.pos())
            w, h = parent.width(), parent.height()
            if 0 <= pos.x() <= w and 0 <= pos.y() <= h:
                self._is_active = True
                self._target_mouse_x = (pos.x() - w / 2) / max(1, w)
                self._target_mouse_y = (pos.y() - h / 2) / max(1, h)
            else:
                self._is_active = False
        except RuntimeError:
            self._is_active = False

    def _tick(self):
        sm = 0.12
        self._mouse_x += (self._target_mouse_x - self._mouse_x) * sm
        self._mouse_y += (self._target_mouse_y - self._mouse_y) * sm
        self._adjust_fps()
        elapsed = self._elapsed_timer.elapsed() / 1000.0
        for orb in self._orbs:
            orb.update(elapsed)
        for orb in self._orbs_static:
            orb.update(elapsed)
        self.update()

    def paintEvent(self, _event: QPaintEvent):
        if self.parent() is None or self.parent().width() <= 0:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor(WINDOW_BG))

        par_strength = 28.0
        for orb in self._orbs:
            ox = orb.x + self._mouse_x * par_strength * orb.par_factor
            oy = orb.y + self._mouse_y * par_strength * orb.par_factor
            grad = QRadialGradient(QPointF(ox, oy), max(1, orb.radius))
            col = QColor(orb.colour)
            col.setAlphaF(orb.alpha)
            grad.setColorAt(0.0, col)
            col_edge = QColor(orb.colour)
            col_edge.setAlphaF(0)
            grad.setColorAt(1.0, col_edge)
            p.setBrush(grad)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(ox, oy), orb.radius, orb.radius)

        for orb in self._orbs_static:
            ox = orb.x + self._mouse_x * 10
            oy = orb.y + self._mouse_y * 10
            grad = QRadialGradient(QPointF(ox, oy), orb.radius)
            col = QColor(orb.colour)
            col.setAlphaF(orb.alpha * 0.5)
            grad.setColorAt(0.0, col)
            c2 = QColor(orb.colour)
            c2.setAlphaF(0)
            grad.setColorAt(1.0, c2)
            p.setBrush(grad)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(ox, oy), orb.radius, orb.radius)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._populate_timer.start()
