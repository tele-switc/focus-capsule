"""严格模式、延后与破功判定的回归测试。"""

from __future__ import annotations

import json
import sys
import tempfile
import time
import unittest
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PyQt6.QtWidgets import QApplication

from focus_capsule.controller import BROKE_DISTRACTION_THRESHOLD, SessionController
from focus_capsule.models import FocusConfig, ScheduleRule, SessionStatus
from focus_capsule.strict_lock import (
    ClockGuard,
    ExitGate,
    StrictPolicy,
    hash_passcode,
    verify_passcode,
)


class FakeOverlay:
    """记录调用的最小覆盖层替身。"""

    def __init__(self):
        self.calls: list[dict] = []
        self.break_shown = False
        self.hidden = 0

    def show_overlay(self, app_name, **kwargs):
        self.calls.append({"app": app_name, **kwargs})
        return True

    def show_usage_limit(self, app_name, **kwargs):
        self.calls.append({"app": app_name, "limit": True, **kwargs})
        return True

    def hide_overlay(self):
        self.hidden += 1

    def show_break_window(self, minutes, on_tick=None, on_end=None):
        self.break_shown = True

    def hide_break_window(self):
        self.break_shown = False

    def snooze_remaining(self):
        return 0


class FakeHistory:
    def __init__(self):
        self.records = []

    def save_record(self, record):
        self.records.append(record)


class StrictModeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.overlay = FakeOverlay()
        self.history = FakeHistory()
        self.controller = SessionController(self.history, self.overlay)

    def _config(self, **kwargs) -> FocusConfig:
        base = dict(whitelist=["code.exe"], duration_minutes=25, mode="Standard", max_esc=2)
        base.update(kwargs)
        return FocusConfig(**base)

    # -- 冷静期 ---------------------------------------------------------

    def test_cooldown_blocks_immediate_exit(self):
        self.controller.start_session(self._config(strict_level="cooldown", strict_cooldown_minutes=5))
        gate = self.controller.request_early_exit()
        self.assertTrue(gate.waiting_for_cooldown)
        self.assertFalse(self.controller.can_exit())

        self.controller.terminate()  # 未解锁：不应结束
        self.assertTrue(self.controller.is_active)

        for _ in range(5 * 60):
            gate.tick()
        self.assertTrue(gate.ready_to_verify)
        self.assertTrue(gate.verify())
        self.controller.terminate()
        self.assertFalse(self.controller.is_active)
        self.assertEqual(self.history.records[-1].outcome, "terminated")

    def test_cancel_during_cooldown_keeps_session_clean(self):
        self.controller.start_session(self._config(strict_level="cooldown", strict_cooldown_minutes=2))
        gate = self.controller.request_early_exit()
        gate.cancel()
        self.assertFalse(gate.released)
        self.assertTrue(self.controller.is_active)

    # -- 随机字符 / 口令 ------------------------------------------------

    def test_phrase_gate(self):
        gate = ExitGate(StrictPolicy(level="phrase", phrase_length=6))
        gate.begin()
        self.assertTrue(gate.needs_phrase)
        phrase = gate.arm_phrase()
        self.assertEqual(len(phrase), 6)
        self.assertFalse(gate.verify(phrase="XXXXXX"))
        self.assertEqual(gate.failed_attempts, 1)
        self.assertTrue(gate.verify(phrase=phrase.lower()))
        self.assertTrue(gate.released)

    def test_passcode_hash_and_gate(self):
        stored = hash_passcode("mima1234")
        self.assertTrue(verify_passcode("mima1234", stored))
        self.assertFalse(verify_passcode("wrong", stored))
        self.assertNotIn("mima1234", stored)

        gate = ExitGate(StrictPolicy(level="passcode", passcode_hash=stored))
        gate.begin()
        self.assertTrue(gate.needs_passcode)
        self.assertFalse(gate.verify(passcode="nope"))
        self.assertTrue(gate.verify(passcode="mima1234"))

    # -- 破功判定 -------------------------------------------------------

    def test_terminate_marks_broke(self):
        self.controller.start_session(self._config())
        self.controller.request_early_exit()
        self.controller.terminate(force=True)
        self.assertTrue(self.history.records[-1].broke)

    def test_escape_exhaustion_marks_broke(self):
        self.controller.start_session(self._config(max_esc=1))
        self.controller.handle_escape()
        self.assertEqual(self.controller.esc_remaining, 0)
        self.controller.handle_escape()  # 配额耗尽后再离开
        self.assertTrue(self.controller._broke)
        self.assertEqual(self.history.records, [])

    def test_overlay_receives_strict_and_snooze_flags(self):
        self.controller.start_session(
            self._config(strict_level="cooldown", snooze_quota=1)
        )
        self.controller.on_foreground_change("chrome.exe", "news", "", 12)
        self.controller._foreground_grace_timer.timeout.emit()
        self.assertTrue(self.overlay.calls, "分心时应弹出覆盖层")
        call = self.overlay.calls[-1]
        self.assertTrue(call["strict"])
        self.assertEqual(call["snooze_quota"], 1)

    def test_many_distractions_mark_broke(self):
        self.controller.start_session(self._config(mode="Light"))
        for _ in range(BROKE_DISTRACTION_THRESHOLD):
            self.controller._pending_distraction = ("wechat.exe", "", "", 1)
            self.controller._enforce_pending_distraction()
        self.assertTrue(self.controller._broke)

    # -- 单调钟计时 -----------------------------------------------------

    def test_elapsed_survives_wall_clock_change(self):
        self.controller.start_session(self._config(duration_minutes=25))
        self.controller._mono_anchor = time.monotonic() - 60
        self.controller._on_timer_tick()
        self.assertGreaterEqual(self.controller.elapsed, 60)

    def test_break_time_is_not_counted_as_focus(self):
        self.controller.start_session(self._config(duration_minutes=25, max_esc=2))
        self.controller._mono_anchor = time.monotonic() - 30
        self.controller._on_timer_tick()
        before = self.controller.elapsed
        self.controller.handle_escape()
        self.controller._on_timer_tick()
        self.controller._status = SessionStatus.RUNNING
        self.controller._on_timer_tick()
        self.assertGreaterEqual(self.controller.elapsed, before)

    # -- 记录字段 -------------------------------------------------------

    def test_record_carries_strict_metadata(self):
        self.controller.start_session(
            self._config(strict_level="phrase", max_esc=2, snooze_quota=3)
        )
        self.controller.complete_session()
        record = self.history.records[-1]
        self.assertEqual(record.strict_level, "phrase")
        self.assertEqual(record.esc_allowed, 2)
        self.assertFalse(record.broke)
        self.assertEqual(record.snooze_used, 0)

    def test_session_update_exposes_new_fields(self):
        self.controller.start_session(self._config())
        captured = {}
        self.controller.update_requested.connect(lambda update: captured.setdefault("u", update))
        self.controller._emit_update()
        payload = captured["u"].to_dict()
        for key in ("snooze_remaining", "suppressed_reason", "broke"):
            self.assertIn(key, payload)


class ScheduleStrictTests(unittest.TestCase):
    def test_rule_strict_roundtrip(self):
        rule = ScheduleRule(
            start_hour=9,
            end_hour=12,
            strict_level="cooldown",
            strict_cooldown_minutes=10,
            snooze_quota=0,
        )
        restored = ScheduleRule.from_dict(json.loads(json.dumps(rule.to_dict())))
        self.assertEqual(restored.strict_level, "cooldown")
        self.assertEqual(restored.strict_cooldown_minutes, 10)
        self.assertEqual(restored.snooze_quota, 0)

    def test_invalid_strict_level_falls_back_to_off(self):
        rule = ScheduleRule(start_hour=1, end_hour=2, strict_level="nonsense")
        self.assertEqual(rule.strict_level, "off")

    def test_old_rule_dict_without_strict_still_loads(self):
        legacy = {
            "start_hour": 8,
            "start_minute": 30,
            "end_hour": 11,
            "end_minute": 0,
            "whitelisted_apps": ["code.exe"],
            "mode": "Standard",
            "enabled": True,
        }
        rule = ScheduleRule.from_dict(legacy)
        self.assertEqual(rule.mode, "Standard")
        self.assertEqual(rule.strict_level, "off")
        self.assertEqual(rule.snooze_quota, 2)


class ClockGuardTests(unittest.TestCase):
    def test_detects_wall_clock_going_backwards(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "clock.json"
            guard = ClockGuard(path)
            tampered, _ = guard.check()
            self.assertFalse(tampered)

            # 模拟重启后系统时间被调回一小时
            state = json.loads(path.read_text("utf-8"))
            state["wall"] = state["wall"] + 3600
            path.write_text(json.dumps(state), "utf-8")
            restarted = ClockGuard(path)
            tampered, reason = restarted.check()
            self.assertTrue(tampered)
            self.assertIn("调回", reason)

    def test_now_never_goes_backwards(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "clock.json"
            guard = ClockGuard(path)
            guard.check()
            future = datetime.now().astimezone() + timedelta(hours=2)
            state = json.loads(path.read_text("utf-8"))
            state["wall"] = future.timestamp()
            path.write_text(json.dumps(state), "utf-8")
            self.assertGreaterEqual(ClockGuard(path).now().timestamp(), future.timestamp() - 5)


if __name__ == "__main__":
    unittest.main()
