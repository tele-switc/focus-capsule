import json
import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from focus_capsule.controller import SessionController
from focus_capsule.history_db import HistoryService
from focus_capsule.models import FocusConfig, SessionRecord, SessionStatus


class FakeHistory:
    def __init__(self):
        self.records = []

    def save_record(self, record):
        self.records.append(record)


class FakeOverlay:
    def __init__(self):
        self.break_tick = None
        self.break_end = None
        self.overlay_calls = []

    def show_overlay(self, app_name, return_seconds=3):
        self.overlay_calls.append((app_name, return_seconds))

    def hide_overlay(self):
        pass

    def show_break_window(self, max_minutes, on_tick=None, on_end=None):
        self.break_tick = on_tick
        self.break_end = on_end

    def hide_break_window(self):
        pass


class SessionControllerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.history = FakeHistory()
        self.overlay = FakeOverlay()
        self.controller = SessionController(self.history, self.overlay)
        self.config = FocusConfig(
            whitelist=["code.exe"],
            duration_minutes=25,
            mode="Standard",
            max_esc=2,
            esc_break_minutes=1,
            goal="Finish review",
        )
        self.controller.start_session(self.config)
        self.controller._timer.stop()

    def tearDown(self):
        self.controller._timer.stop()

    def test_break_updates_and_only_finishes_at_zero(self):
        self.controller.handle_escape()
        self.assertTrue(self.controller.is_active)
        self.assertEqual(self.controller.status, SessionStatus.BREAK)

        self.overlay.break_tick(30)
        self.overlay.break_end()
        self.assertEqual(self.controller.break_remaining, 30)
        self.assertEqual(self.controller.status, SessionStatus.BREAK)

        self.overlay.break_tick(0)
        self.overlay.break_end()
        self.assertEqual(self.controller.break_remaining, 0)
        self.assertEqual(self.controller.status, SessionStatus.RUNNING)

    def test_invalid_non_positive_duration_is_normalized(self):
        invalid = FocusConfig(whitelist=["code.exe"], duration_minutes=0)
        self.controller.start_session(invalid)
        self.controller._timer.stop()
        self.assertEqual(invalid.duration_minutes, 1)
        self.assertEqual(self.controller._total_seconds, 60)

    def test_record_keeps_actual_start_goal_outcome_and_distraction_details(self):
        started_at = self.controller._started_at
        self.controller.on_foreground_change("Chrome.EXE", "Research notes")
        self.assertEqual(self.controller.status, SessionStatus.OVERLAY)
        self.controller.terminate()

        self.assertEqual(len(self.history.records), 1)
        record = self.history.records[0]
        self.assertEqual(datetime.fromisoformat(record.started_at), started_at)
        self.assertEqual(record.goal, "Finish review")
        self.assertEqual(record.outcome, "terminated")
        self.assertEqual(record.distraction_count, 1)
        self.assertEqual(record.distractions[0]["process_name"], "chrome.exe")
        self.assertEqual(record.distractions[0]["window_title"], "Research notes")
        datetime.fromisoformat(record.distractions[0]["occurred_at"])


class HistoryServiceTests(unittest.TestCase):
    def make_record(self):
        return SessionRecord(
            started_at="2026-07-10T10:00:00+00:00",
            ended_at="2026-07-10T10:25:00+00:00",
            duration_minutes=25,
            actual_focus_seconds=1500,
            distraction_count=0,
            esc_used=0,
            mode="Standard",
            whitelisted_apps=["code.exe"],
            goal="写完报告",
            outcome="completed",
        )

    def test_loads_legacy_record_and_writes_utf8_atomically(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "history.json"
            legacy = {
                "started_at": "2026-07-09T10:00:00",
                "ended_at": "2026-07-09T10:25:00",
                "duration_minutes": 25,
                "actual_focus_seconds": 1500,
                "distraction_count": 0,
                "esc_used": 0,
                "mode": "Standard",
                "whitelisted_apps": ["code.exe"],
            }
            path.write_text(json.dumps([legacy]), encoding="utf-8")
            service = HistoryService(path)

            loaded = service.load_history()
            self.assertEqual(loaded[0].outcome, "completed")
            self.assertIsNone(loaded[0].goal)

            service.save_record(self.make_record())
            saved_text = path.read_text(encoding="utf-8")
            self.assertIn("写完报告", saved_text)
            self.assertFalse(list(path.parent.glob("*.tmp")))

    def test_corrupt_history_is_backed_up_before_new_save(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "history.json"
            path.write_text("{not valid json", encoding="utf-8")
            service = HistoryService(path)

            with self.assertLogs(level="ERROR"):
                self.assertEqual(service.load_history(), [])
            backups = list(path.parent.glob("history.corrupt-*.json"))
            self.assertEqual(len(backups), 1)
            self.assertFalse(path.exists())

            service.save_record(self.make_record())
            self.assertTrue(path.exists())
            self.assertTrue(backups[0].exists())


if __name__ == "__main__":
    unittest.main()
