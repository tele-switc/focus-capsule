import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from focus_capsule.activity_tracker import ActivityTracker
from focus_capsule.app_categories import merge_catalog_categories
from focus_capsule.daily_progress import CST, DailyProgressService
from focus_capsule.daily_targets_dialog import DailyTargetsDialog
from focus_capsule.data_models import (
    AppCategory,
    AppConfig,
    DailyGoal,
    DailyGoalEntry,
    DailyGoalTargets,
    TaskItem,
    china_today,
)
from focus_capsule.data_store import DataStore
from focus_capsule.history_db import HistoryService
from focus_capsule.models import SessionRecord


class DailyTargetPersistenceTests(unittest.TestCase):
    def test_targets_round_trip_without_enabling_unselected_types(self):
        targets = DailyGoalTargets(
            max_distractions=3,
            total_focus_minutes=90,
            category_focus_minutes={"学习": 45},
            focus_sessions=4,
            app_usage_minutes={"chrome.exe": 30},
            category_usage_minutes={"影音娱乐": 60},
            max_temporary_unlocks=2,
        )
        restored = DailyGoalTargets.from_dict(targets.to_dict())

        self.assertEqual(restored, targets)
        self.assertFalse(restored.is_empty)
        self.assertTrue(DailyGoalTargets().is_empty)

    def test_tasks_and_targets_really_persist_to_disk(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = DataStore(Path(temporary))
            day = china_today().isoformat()
            store.save_daily_goal(
                DailyGoal(
                    date=day,
                    title="完成报告",
                    tasks=[TaskItem(title="写第一稿")],
                )
            )
            store.save_daily_targets(
                day,
                DailyGoalTargets(total_focus_minutes=60, focus_sessions=2),
            )

            reopened = DataStore(Path(temporary))
            goal = reopened.get_goal_for_date(day)
            entry = reopened.get_goal(day)
            self.assertIsNotNone(goal)
            self.assertEqual(goal.title, "完成报告")
            self.assertEqual([task.title for task in goal.tasks], ["写第一稿"])
            self.assertEqual(entry.targets.total_focus_minutes, 60)
            self.assertEqual(entry.targets.focus_sessions, 2)

    def test_old_entries_without_targets_do_not_gain_an_automatic_score(self):
        entry = DailyGoalEntry.from_dict(
            {
                "date_str": "2026-07-23",
                "target_minutes": 120,
                "achieved_minutes": 20,
            }
        )
        self.assertTrue(entry.targets.is_empty)


class DailyTargetsDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_multiple_checked_goal_types_are_returned_together(self):
        config = AppConfig(
            app_categories=[
                AppCategory("code.exe", "VS Code", "编程"),
            ]
        )
        dialog = DailyTargetsDialog(DailyGoalTargets(), config)
        captured = []
        dialog.targets_saved.connect(captured.append)

        dialog._distractions_enabled.setChecked(True)
        dialog._distractions_value.setValue(3)
        dialog._focus_enabled.setChecked(True)
        dialog._focus_value.setValue(90)
        dialog._sessions_enabled.setChecked(True)
        dialog._sessions_value.setValue(4)
        dialog._app_usage_enabled.setChecked(True)
        dialog._app_usage_editor._add_value("code.exe", 45)
        dialog._unlocks_enabled.setChecked(True)
        dialog._unlocks_value.setValue(2)
        dialog._save()

        self.assertEqual(len(captured), 1)
        targets = captured[0]
        self.assertEqual(targets.max_distractions, 3)
        self.assertEqual(targets.total_focus_minutes, 90)
        self.assertEqual(targets.focus_sessions, 4)
        self.assertEqual(targets.app_usage_minutes, {"code.exe": 45})
        self.assertEqual(targets.max_temporary_unlocks, 2)

    def test_dropdown_and_value_controls_enable_their_goal_automatically(self):
        config = AppConfig(
            app_categories=[
                AppCategory("code.exe", "VS Code", "编程"),
            ]
        )
        dialog = DailyTargetsDialog(DailyGoalTargets(), config)

        self.assertTrue(dialog._app_usage_editor.isEnabled())
        self.assertFalse(dialog._app_usage_enabled.isChecked())
        dialog._app_usage_editor._choice.setCurrentIndex(0)
        dialog._app_usage_editor._minutes.setValue(50)
        dialog._app_usage_editor._add.click()
        self.assertTrue(dialog._app_usage_enabled.isChecked())
        self.assertEqual(dialog._app_usage_editor.values(), {"code.exe": 50})

        self.assertFalse(dialog._sessions_enabled.isChecked())
        dialog._sessions_value.setValue(6)
        self.assertTrue(dialog._sessions_enabled.isChecked())


class ActivityTrackerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_usage_is_flushed_per_app_and_focus_capsule_is_not_counted(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = DataStore(Path(temporary))
            tracker = ActivityTracker(store)
            tracker._timer.stop()
            tracker._process = "code.exe"
            tracker._display_name = "Code"
            tracker._date_str = china_today().isoformat()
            tracker._started = 100
            emitted = []
            tracker.usage_updated.connect(emitted.append)

            with patch(
                "focus_capsule.activity_tracker.time.monotonic",
                side_effect=[161, 170, 170],
            ):
                tracker.flush()
                tracker.on_foreground_change("__focus_capsule__", "专注舱")

            activity = store.get_activity(china_today().isoformat())
            self.assertEqual(activity.app_usage_seconds, {"code.exe": 70})
            self.assertEqual(activity.app_display_names, {"code.exe": "Code"})
            self.assertEqual(emitted, ["code.exe", "code.exe"])
            self.assertEqual(tracker._process, "")


class DailyProgressTests(unittest.TestCase):
    def test_progress_joins_sessions_categories_usage_and_limits(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            store = DataStore(root / "data")
            history = HistoryService(root / "history.json")
            config = AppConfig(
                app_categories=[
                    AppCategory("code.exe", "VS Code", "编程"),
                    AppCategory("chrome.exe", "Chrome", "浏览器"),
                ]
            )
            day = china_today()
            history.save_record(
                SessionRecord(
                    started_at=datetime.now(CST).isoformat(),
                    ended_at=datetime.now(CST).isoformat(),
                    duration_minutes=30,
                    actual_focus_seconds=1800,
                    distraction_count=3,
                    esc_used=1,
                    mode="Standard",
                    whitelisted_apps=["code.exe"],
                    outcome="completed",
                    app_focus_seconds={"code.exe": 1800},
                )
            )
            store.add_app_usage(day.isoformat(), "code.exe", 25 * 60, "VS Code")
            store.save_daily_targets(
                day.isoformat(),
                DailyGoalTargets(
                    max_distractions=2,
                    total_focus_minutes=30,
                    category_focus_minutes={"编程": 30},
                    focus_sessions=1,
                    app_usage_minutes={"code.exe": 20},
                    category_usage_minutes={"编程": 30},
                    max_temporary_unlocks=1,
                ),
            )

            service = DailyProgressService(history, store, config)
            metrics = service.metrics_for_date(day)
            progress = service.progress_for_date(day, metrics)
            by_key = {item.key: item for item in progress.items}

            self.assertEqual(metrics.focus_minutes, 30)
            self.assertEqual(metrics.category_focus_seconds["编程"], 1800)
            self.assertEqual(metrics.category_usage_seconds["编程"], 25 * 60)
            self.assertEqual(by_key["focus_minutes"].status, "complete")
            self.assertEqual(by_key["category_focus:编程"].status, "complete")
            self.assertEqual(by_key["distractions"].status, "exceeded")
            self.assertEqual(by_key["app_usage:code.exe"].status, "exceeded")
            self.assertEqual(by_key["category_usage:编程"].status, "safe")
            self.assertEqual(progress.state, "failed")
            self.assertEqual(service.remaining_unlocks_today(), 0)
            self.assertEqual(
                service.exceeded_usage_limit("code.exe"),
                ("VS Code", 25, 20),
            )


class AutomaticCategoryTests(unittest.TestCase):
    def test_new_apps_are_classified_and_user_overrides_are_preserved(self):
        config = AppConfig(
            app_categories=[
                AppCategory("chrome.exe", "Chrome", "学习"),
            ]
        )
        catalog = [
            {
                "process_name": "chrome.exe",
                "display_name": "Chrome",
                "custom_path": r"C:\Apps\Chrome.exe",
            },
            {
                "process_name": "code.exe",
                "display_name": "Visual Studio Code",
                "custom_path": r"C:\Apps\Code.exe",
            },
            {
                "process_name": "editors.exe",
                "display_name": "ONLYOFFICE",
                "custom_path": r"C:\Apps\editors.exe",
            },
        ]

        merged, changed = merge_catalog_categories(config, catalog)
        by_process = {item.process_name: item.category for item in merged.app_categories}
        self.assertTrue(changed)
        self.assertEqual(by_process["chrome.exe"], "学习")
        self.assertEqual(by_process["code.exe"], "编程")
        self.assertEqual(by_process["editors.exe"], "办公软件")


if __name__ == "__main__":
    unittest.main()
