import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from focus_capsule.app import EXCEPTION_DIALOG_COOLDOWN_SECONDS, ExceptionHandler
from focus_capsule.controller import SessionController
from focus_capsule.history_db import HistoryService
from focus_capsule.models import FocusConfig, SessionRecord, SessionStatus
from focus_capsule.process_matching import ProcessIdentity


class AppStartupTests(unittest.TestCase):
    def test_exception_handler_logs_all_repeats_but_throttles_duplicate_dialogs(self):
        clock = [100.0]
        dialogs = []
        handler = ExceptionHandler(
            Path("diagnostic.log"),
            show_dialog=lambda *args: dialogs.append(args),
            clock=lambda: clock[0],
        )

        try:
            raise AttributeError("layout callback failed")
        except AttributeError as error:
            exc_info = (type(error), error, error.__traceback__)

        with self.assertLogs("focus_capsule", level="ERROR") as captured:
            handler(*exc_info)
            handler(*exc_info)
            clock[0] += EXCEPTION_DIALOG_COOLDOWN_SECONDS
            handler(*exc_info)

        self.assertEqual(len(captured.output), 3)
        self.assertEqual(len(dialogs), 2)

    @unittest.skipIf(sys.platform == "darwin", "macOS CI 下子进程启动自检会挂死，改由 Windows/Linux 覆盖")
    def test_main_starts_when_windowed_bundle_has_no_standard_streams(self):
        script = r"""
import os
import sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PyQt6.QtCore import QTimer

import focus_capsule.app as app_module

original_show = app_module.MainWindow.show

def show_and_quit(window):
    original_show(window)
    QTimer.singleShot(100, app_module.QApplication.instance().quit)

app_module.MainWindow.show = show_and_quit
sys.stdout = None
sys.stderr = None
raise SystemExit(app_module.main())
"""
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=Path(__file__).resolve().parents[1],
            env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
            capture_output=True,
            timeout=30,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr.decode(errors="replace"))


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
        self.controller._enforce_pending_distraction()
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

    def test_whitelist_accepts_path_identity_but_not_fuzzy_process_names(self):
        self.controller._config.whitelist = [r"C:\Apps\Code.exe"]

        self.controller.on_foreground_change("CODE.EXE", "Editor")
        self.assertEqual(self.controller.status, SessionStatus.RUNNING)
        self.assertEqual(self.controller.distraction_count, 0)

        self.controller.on_foreground_change("code-helper.exe", "Unrelated helper")
        self.controller._enforce_pending_distraction()
        self.assertEqual(self.controller.status, SessionStatus.OVERLAY)
        self.assertEqual(self.controller.distraction_count, 1)

    def test_launcher_path_family_allows_foreground_editor(self):
        with tempfile.TemporaryDirectory() as temporary:
            app_root = Path(temporary) / "Vendor" / "DesktopEditors"
            launcher = app_root / "DesktopEditors.exe"
            foreground = app_root / "editors.exe"
            config = FocusConfig(
                whitelist=["desktopeditors.exe"],
                allowed_app_paths={"desktopeditors.exe": str(launcher)},
            )
            self.controller.start_session(config)
            self.controller._timer.stop()
            self.controller.on_foreground_change(
                "editors.exe",
                "Document editor",
                str(foreground),
            )

        self.assertEqual(self.controller.status, SessionStatus.RUNNING)
        self.assertEqual(self.controller.distraction_count, 0)

    def test_transient_disallowed_foreground_does_not_block_allowed_app_launch(self):
        self.controller.start_session(
            FocusConfig(whitelist=["anki.exe"], duration_minutes=25)
        )
        self.controller._timer.stop()
        self.controller.on_foreground_change("launcher.exe", "Starting application")
        self.controller.on_foreground_change("ANKI.EXE", "Anki")

        self.assertEqual(self.controller.status, SessionStatus.RUNNING)
        self.assertEqual(self.controller.distraction_count, 0)
        self.assertFalse(self.controller._foreground_grace_timer.isActive())
        self.assertEqual(self.overlay.overlay_calls, [])

    def test_generic_runtime_descendant_is_counted_as_selected_app(self):
        selected = r"C:\Users\Example\AppData\Local\Programs\Anki\anki.exe"
        runtime = r"C:\Users\Example\AppData\Local\AnkiProgramFiles\python\pythonw.exe"
        self.controller.start_session(
            FocusConfig(
                whitelist=["anki.exe"],
                allowed_app_paths={"anki.exe": selected},
                duration_minutes=25,
            )
        )
        self.controller._timer.stop()
        lineage = (
            ProcessIdentity("pythonw.exe", runtime, 300),
            ProcessIdentity("anki.exe", selected, 100),
        )

        with patch(
            "focus_capsule.process_matching._process_lineage",
            return_value=lineage,
        ):
            self.controller.on_foreground_change(
                "pythonw.exe",
                "Anki",
                runtime,
                300,
            )

        self.assertEqual(self.controller.status, SessionStatus.RUNNING)
        self.assertEqual(self.controller.distraction_count, 0)
        self.assertEqual(self.controller._current_focus_process, "anki.exe")
        self.assertFalse(self.controller._foreground_grace_timer.isActive())

    def test_record_keeps_schedule_metadata_and_exact_allowed_app_time(self):
        scheduled = FocusConfig(
            whitelist=["code.exe"],
            duration_minutes=25,
            mode="Deep",
            source="schedule",
            schedule_label="上午写作",
            schedule_start="09:00",
            schedule_end="11:00",
        )
        self.controller.start_session(scheduled)
        self.controller._timer.stop()
        self.controller.on_foreground_change("CODE.EXE", "Editor")
        self.controller._on_timer_tick()
        self.controller.finish_scheduled_session()

        record = self.history.records[-1]
        self.assertEqual(record.source, "schedule")
        self.assertEqual(record.schedule_label, "上午写作")
        self.assertEqual(record.schedule_start, "09:00")
        self.assertEqual(record.schedule_end, "11:00")
        self.assertEqual(record.app_focus_seconds, {"code.exe": 1})
        self.assertEqual(record.outcome, "completed")


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
