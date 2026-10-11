"""提前结束专注时需要通过的闸门对话框（严格模式）。

三层锁：冷静期倒计时 → 随机字符 / 口令 → 放行。
冷静期内随时可以「继续专注」，取消不留任何破功记录。
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFontMetrics
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from focus_capsule.strict_lock import ExitGate
from focus_capsule.theme import (
    ACCENT,
    BORDER_NORMAL,
    DANGER,
    FONT_AUX,
    FONT_BODY,
    FONT_SECTION,
    RADIUS_MD,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_TERTIARY,
    hex_alpha,
)


class ExitGateDialog(QDialog):
    def __init__(self, gate: ExitGate, parent: QWidget | None = None):
        super().__init__(parent)
        self._gate = gate
        self.setWindowTitle("结束本次专注")
        self.setObjectName("exitGateDialog")
        self.setModal(True)
        self.setFixedWidth(430)
        self._confirmed = False

        root = QVBoxLayout(self)
        root.setContentsMargins(26, 22, 26, 22)
        root.setSpacing(12)

        self._title = QLabel("确认要提前结束？")
        self._title.setStyleSheet(
            f"color:{TEXT_PRIMARY};font-size:{FONT_SECTION + 4}px;font-weight:600;"
        )
        self._status = QLabel()
        self._status.setWordWrap(True)
        self._status.setStyleSheet(f"color:{TEXT_SECONDARY};font-size:{FONT_BODY}px;")

        # 细进度条：冷静期剩余比例
        self._bar_track = QFrame()
        self._bar_track.setFixedHeight(3)
        self._bar_track.setStyleSheet(
            f"background:{hex_alpha(ACCENT, 0.10)};border-radius:2px;"
        )
        self._bar_fill = QFrame(self._bar_track)
        self._bar_fill.setStyleSheet(
            f"background:{ACCENT};border-radius:2px;"
        )
        self._clock = QLabel()
        self._clock.setStyleSheet(
            f"color:{TEXT_TERTIARY};font-size:{FONT_AUX}px;font-variant-numeric:tabular-nums;"
        )

        root.addWidget(self._title)
        root.addWidget(self._status)
        root.addWidget(self._bar_track)
        root.addWidget(self._clock)

        # 随机字符
        self._phrase_box = QVBoxLayout()
        phrase_label = QLabel("请输入下面的字符（区分大小写不敏感）")
        phrase_label.setStyleSheet(f"color:{TEXT_SECONDARY};font-size:{FONT_BODY}px;")
        self._phrase_text = QLabel("")
        self._phrase_text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._phrase_text.setStyleSheet(
            f"color:{TEXT_PRIMARY};font-size:26px;font-weight:600;"
            f"letter-spacing:6px;padding:10px 0;"
        )
        self._phrase_input = QLineEdit()
        self._phrase_input.setStyleSheet(self._input_style())
        self._phrase_box.addWidget(phrase_label)
        self._phrase_box.addWidget(self._phrase_text)
        self._phrase_box.addWidget(self._phrase_input)
        self._phrase_host = QWidget()
        self._phrase_host.setLayout(self._phrase_box)
        root.addWidget(self._phrase_host)

        # 口令
        self._pass_input = QLineEdit()
        self._pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._pass_input.setPlaceholderText("专注口令")
        self._pass_input.setStyleSheet(self._input_style())
        self._pass_host = QWidget()
        pass_box = QVBoxLayout(self._pass_host)
        pass_box.setContentsMargins(0, 0, 0, 0)
        pass_box.addWidget(self._pass_input)
        root.addWidget(self._pass_host)

        self._hint = QLabel()
        self._hint.setStyleSheet(f"color:{DANGER};font-size:{FONT_AUX}px;")
        root.addWidget(self._hint)

        buttons = QHBoxLayout()
        buttons.addStretch()
        self._cancel_btn = QPushButton("继续专注")
        self._cancel_btn.setObjectName("ghostButton")
        self._cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._cancel_btn.setStyleSheet(
            f"QPushButton{{background:transparent;color:{TEXT_SECONDARY};"
            f"border:1px solid {BORDER_NORMAL};border-radius:{RADIUS_MD}px;padding:8px 18px;}}"
            f"QPushButton:hover{{background:{hex_alpha(ACCENT, 0.06)};color:{TEXT_PRIMARY};}}"
        )
        self._cancel_btn.clicked.connect(self._on_cancel)
        self._ok_btn = QPushButton("确认结束")
        self._ok_btn.setObjectName("dangerButton")
        self._ok_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._ok_btn.setStyleSheet(
            f"QPushButton{{background:{hex_alpha(DANGER, 0.10)};color:{DANGER};"
            f"border:1px solid {hex_alpha(DANGER, 0.32)};border-radius:{RADIUS_MD}px;"
            f"padding:8px 18px;font-weight:600;}}"
            f"QPushButton:hover{{background:{hex_alpha(DANGER, 0.16)};}}"
            f"QPushButton:disabled{{color:{TEXT_TERTIARY};"
            f"background:transparent;border:1px solid {BORDER_NORMAL};}}"
        )
        self._ok_btn.clicked.connect(self._on_confirm)
        buttons.addWidget(self._cancel_btn)
        buttons.addWidget(self._ok_btn)
        root.addLayout(buttons)

        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)
        self._timer.start()
        self._refresh()
        QTimer.singleShot(0, self._focus_input)

    # -- helpers ---------------------------------------------------------

    @staticmethod
    def _input_style() -> str:
        return (
            f"QLineEdit{{background:transparent;color:{TEXT_PRIMARY};"
            f"border:1px solid {BORDER_NORMAL};border-radius:{RADIUS_MD}px;"
            f"padding:8px 12px;font-size:{FONT_BODY}px;}}"
            f"QLineEdit:focus{{border:1px solid {ACCENT};}}"
        )

    def _focus_input(self):
        if self._gate.needs_phrase:
            self._phrase_input.setFocus()
        elif self._gate.needs_passcode:
            self._pass_input.setFocus()
        else:
            self._cancel_btn.setFocus()

    def _tick(self):
        if self._gate.waiting_for_cooldown:
            self._gate.tick()
        self._refresh()

    def _refresh(self):
        gate = self._gate
        self._status.setText(gate.status_text())

        total = gate.policy.cooldown_seconds if gate.policy.is_strict else 1
        remaining = gate.cooldown_remaining
        ratio = 0.0 if total <= 0 else max(0.0, min(1.0, remaining / total))
        width = self._bar_track.width()
        self._bar_fill.setGeometry(0, 0, int(width * ratio), self._bar_track.height())
        if gate.policy.is_strict and remaining > 0:
            minutes, seconds = divmod(remaining, 60)
            self._clock.setText(f"冷静期 {minutes:02d}:{seconds:02d} · 期间专注照常计时，可随时继续专注")
        else:
            self._clock.setText("")

        self._phrase_host.setVisible(gate.needs_phrase)
        self._pass_host.setVisible(gate.needs_passcode)
        if gate.needs_phrase and not self._phrase_text.text():
            self._phrase_text.setText(gate.arm_phrase())
            self._focus_input()
        confirmable = gate.ready_to_verify or gate.policy.level in {"off", "cooldown"}
        self._ok_btn.setEnabled(bool(confirmable))
        if gate.policy.level == "cooldown" and remaining > 0:
            self._ok_btn.setEnabled(False)

    # -- actions ---------------------------------------------------------

    def _on_cancel(self):
        self._gate.cancel()
        self._timer.stop()
        self.reject()

    def _on_confirm(self):
        gate = self._gate
        if gate.waiting_for_cooldown:
            return
        ok = gate.verify(
            phrase=self._phrase_input.text(),
            passcode=self._pass_input.text(),
        )
        if ok:
            self._confirmed = True
            self._timer.stop()
            self.accept()
            return
        self._hint.setText(
            "字符不匹配，请再看一下上方字符" if gate.policy.level == "phrase" else "口令不正确"
        )
        self._phrase_input.selectAll()
        self._phrase_input.setFocus()

    def resizeEvent(self, event):
        self._refresh()
        super().resizeEvent(event)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and self._ok_btn.isEnabled():
            self._on_confirm()
            return
        if event.key() == Qt.Key.Key_Escape:
            self._on_cancel()
            return
        super().keyPressEvent(event)

    @property
    def confirmed(self) -> bool:
        return self._confirmed
