import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QLabel

from focus_capsule.daily_goal_page import DailyGoalPage
from focus_capsule.data_models import DailyGoal
from focus_capsule.data_store import DataStore


class FakeGoalStore:
    def __init__(self, goal=None, report=None):
        self.goal = goal
        self.report = report

    def get_goal_for_date(self, _date):
        return self.goal

    def save_daily_goal(self, goal):
        self.goal = goal

    def get_report(self, _date):
        return self.report


class FakeTrendService:
    def __init__(self, **values):
        defaults = {
            "total_focus_seconds": 0,
            "session_count": 0,
            "completed_count": 0,
        }
        defaults.update(values)
        self.summary = SimpleNamespace(**defaults)

    def get_today_summary(self):
        return self.summary


class DailyOverviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_empty_day_is_an_editable_guided_state(self):
        page = DailyGoalPage(FakeGoalStore(), FakeTrendService())

        self.assertEqual(page.goal_heading.text(), "今天想完成什么？")
        self.assertEqual(page.submit_button.text(), "创建今日任务")
        self.assertTrue(page.goal_input.isEnabled())
        self.assertFalse(page.submit_button.isEnabled())
        self.assertEqual(page.completion_value.text(), "0/0")
        self.assertTrue(page.report_card.isHidden())

        visible_copy = {label.text() for label in page.findChildren(QLabel)}
        self.assertNotIn("Precision Agent OS", visible_copy)
        self.assertNotIn("质量评分", visible_copy)
        self.assertNotIn("效率", visible_copy)
        self.assertNotIn("自主复盘报告", visible_copy)
        page.close()

    def test_blank_daily_goal_is_treated_as_no_user_goal(self):
        blank = DailyGoal(date="2026-07-22", title="", tasks=[])
        page = DailyGoalPage(FakeGoalStore(blank), FakeTrendService())

        self.assertEqual(page.goal_heading.text(), "今天想完成什么？")
        self.assertEqual(page.task_count_label.text(), "0 项")
        page.close()

    def test_user_can_create_and_add_tasks_from_the_overview(self):
        store = FakeGoalStore()
        page = DailyGoalPage(store, FakeTrendService())

        page.goal_input.setText("完成报告第一稿")
        page.submit_button.click()

        self.assertIsNotNone(store.goal)
        self.assertEqual(store.goal.title, "完成报告第一稿")
        self.assertEqual([task.title for task in store.goal.tasks], ["完成报告第一稿"])
        self.assertEqual(page.submit_button.text(), "添加任务")

        page.goal_input.setText("检查引用格式")
        page.submit_button.click()
        self.assertEqual(
            [task.title for task in store.goal.tasks],
            ["完成报告第一稿", "检查引用格式"],
        )
        self.assertEqual(page.task_count_label.text(), "2 项")
        page.close()

    def test_progress_uses_real_focus_history_and_shows_review_only_after_activity(self):
        goal = DailyGoal(date="2026-07-22", title="Write", tasks=[])
        trend = FakeTrendService(
            total_focus_seconds=3900,
            session_count=2,
            completed_count=1,
        )
        page = DailyGoalPage(FakeGoalStore(goal), trend)

        self.assertEqual(page.focus_value.text(), "1 小时 5 分钟")
        self.assertEqual(page.session_value.text(), "2")
        self.assertFalse(page.report_card.isHidden())
        self.assertIn("实际", page.progress_note.text())
        self.assertIn("2 轮专注", page.report_text.text())
        page.close()

    def test_data_store_returns_none_until_a_goal_is_really_created(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = DataStore(Path(tmp))
            self.assertIsNone(store.get_goal_for_date("2026-07-22"))


if __name__ == "__main__":
    unittest.main()
