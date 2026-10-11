"""时间线相关功能的单元测试：区间存储、周/月聚合、分类占比、AFK 分段。"""

import os
import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from focus_capsule.activity_events import (
    AFK_PROCESS,
    ActivityEventLog,
    compute_afk_segments,
    merge_adjacent,
)
from focus_capsule.data_models import AppConfig, AppCategory
from focus_capsule.data_store import DataStore
from focus_capsule.history_db import HistoryService
from focus_capsule.models import SessionRecord
from focus_capsule.trend_service import TrendService


def _make_record(started: datetime, seconds: int, outcome: str) -> SessionRecord:
    return SessionRecord(
        started_at=started.isoformat(timespec="seconds"),
        ended_at=(started + timedelta(seconds=seconds)).isoformat(timespec="seconds"),
        duration_minutes=max(1, seconds // 60),
        actual_focus_seconds=seconds,
        distraction_count=0,
        esc_used=0,
        mode="Standard",
        whitelisted_apps=["chrome.exe"],
        distractions=[],
        outcome=outcome,
    )


class EventLogStorageTests(unittest.TestCase):
    """区间事件 JSONL 存储：按天分文件、30 天保留、坏行/坏输入静默降级。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)
        self.log = ActivityEventLog(self.base)

    def tearDown(self):
        self._tmp.cleanup()

    def test_append_creates_daily_jsonl_and_reads_back(self):
        day = date(2026, 10, 11)
        start = datetime.combine(day, datetime.min.time()).replace(hour=9)
        end = start + timedelta(minutes=30)
        self.assertTrue(self.log.append_event("Code.exe", "a.py", start, end))
        path = self.base / "activity_events_2026-10-11.jsonl"
        self.assertTrue(path.exists())
        events = self.log.read_events(day)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["process"], "code.exe")
        self.assertEqual(events[0]["title"], "a.py")

    def test_cross_midnight_event_visible_on_both_days(self):
        start = datetime(2026, 10, 11, 23, 50).astimezone()
        end = datetime(2026, 10, 12, 0, 10).astimezone()
        self.log.append_event("chrome.exe", "mail", start, end)
        # 事件落在开始日文件；次日读取也应能拿到（跨午夜区间）
        self.assertEqual(len(self.log.read_events(date(2026, 10, 12))), 1)

    def test_prune_removes_files_older_than_retention(self):
        old = self.base / "activity_events_2000-01-01.jsonl"
        keep = self.base / f"activity_events_{date.today().isoformat()}.jsonl"
        old.write_text("{}", encoding="utf-8")
        keep.write_text("", encoding="utf-8")
        self.log.prune()
        self.assertFalse(old.exists())
        self.assertTrue(keep.exists())

    def test_bad_input_silently_degrades(self):
        now = datetime.now().astimezone()
        self.assertFalse(self.log.append_event("", "x", now, now))
        # 坏行不崩、被跳过
        path = self.base / f"activity_events_{date.today().isoformat()}.jsonl"
        path.write_text("不是JSON\n{}\n", encoding="utf-8")
        self.assertEqual(self.log.read_events(date.today()), [])


class TrackerIntervalTests(unittest.TestCase):
    """ActivityTracker：前台切换写区间事件，且旧 app_usage_seconds 逻辑不变。"""

    @classmethod
    def setUpClass(cls):
        from PyQt6.QtWidgets import QApplication

        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.store = DataStore(data_path=Path(self._tmp.name) / "data")

    def tearDown(self):
        self._tmp.cleanup()

    def test_foreground_change_writes_interval_event(self):
        from focus_capsule.activity_tracker import ActivityTracker

        # 机器真实空闲时长会影响 AFK 判定，这里固定为「刚有输入」保证确定性
        import focus_capsule.focus_guard as focus_guard

        original_idle = focus_guard.idle_seconds
        focus_guard.idle_seconds = lambda: 0
        try:
            tracker = ActivityTracker(self.store)
            tracker.on_foreground_change("chrome.exe", "Gmail", "C:/x/chrome.exe")
            # 把当前区间的开始时间回拨 5 秒，模拟真实停留
            tracker._ev_start -= timedelta(seconds=5)
            tracker.on_foreground_change("code.exe", "a.py", "C:/x/Code.exe")
            events = tracker._events.read_events(date.today())
            chrome = [e for e in events if e["process"] == "chrome.exe"]
            self.assertEqual(len(chrome), 1)
            self.assertEqual(chrome[0]["title"], "Gmail")
            self.assertLessEqual(chrome[0]["start"], chrome[0]["end"])
        finally:
            focus_guard.idle_seconds = original_idle
            tracker.stop()

    def test_flush_still_accumulates_app_usage_seconds(self):
        from focus_capsule.activity_tracker import ActivityTracker

        tracker = ActivityTracker(self.store)
        try:
            tracker.on_foreground_change("code.exe", "a.py", "C:/x/Code.exe")
            tracker._started -= 40  # 伪造已过 40 秒
            tracker.flush()
            entry = self.store.get_activity(tracker._date_str)
            self.assertEqual(entry.app_usage_seconds.get("code.exe"), 40)
            self.assertEqual(entry.app_display_names.get("code.exe"), "Code")
        finally:
            tracker.stop()


class WeekMonthAggregationTests(unittest.TestCase):
    """get_range_summary：总时长、日均、完成率、分类 Top5。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        base = Path(self._tmp.name)
        self.history = HistoryService(history_path=base / "history.json")
        self.store = DataStore(data_path=base / "data")
        self.service = TrendService(self.history, AppConfig(), self.store)

    def tearDown(self):
        self._tmp.cleanup()

    def test_range_summary_aggregates_totals_avg_completion(self):
        today = datetime.now().astimezone()
        self.history.save_record(_make_record(today - timedelta(hours=2), 1800, "completed"))
        self.history.save_record(_make_record(today - timedelta(days=1, hours=3), 3600, "terminated"))
        self.history.save_record(_make_record(today - timedelta(days=2, hours=1), 600, "completed"))
        start = (today - timedelta(days=6)).date()
        summary = self.service.get_range_summary(start, today.date())
        self.assertEqual(summary.day_count, 7)
        self.assertEqual(summary.total_focus_seconds, 1800 + 3600 + 600)
        self.assertAlmostEqual(summary.avg_daily_minutes, (6000 / 7) / 60.0)
        self.assertAlmostEqual(summary.completion_rate, 2 / 3)
        self.assertIsInstance(summary.category_top5, list)

    def test_reversed_range_is_normalised(self):
        today = date.today()
        summary = self.service.get_range_summary(today, today - timedelta(days=3))
        self.assertEqual(summary.day_count, 4)


class CategoryShareTests(unittest.TestCase):
    """分类占比与应用排行：查询时现算分类，不落库。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        base = Path(self._tmp.name)
        self.history = HistoryService(history_path=base / "history.json")
        self.store = DataStore(data_path=base / "data")
        config = AppConfig()
        config.app_categories = [
            AppCategory(process_name="qq.exe", display_name="QQ", category="通讯"),
        ]
        self.service = TrendService(self.history, config, self.store)

    def tearDown(self):
        self._tmp.cleanup()

    def test_category_share_ratios_and_override(self):
        today = date.today().isoformat()
        self.store.add_app_usage(today, "chrome.exe", 600, "Chrome")
        self.store.add_app_usage(today, "code.exe", 300, "Code")
        self.store.add_app_usage(today, "qq.exe", 100, "QQ")
        share = self.service.get_category_share(date.today(), date.today())
        by_cat = {item["category"]: item["seconds"] for item in share}
        self.assertEqual(by_cat["浏览器"], 600)
        self.assertEqual(by_cat["编程"], 300)
        self.assertEqual(by_cat["通讯"], 100)  # 用户覆盖优先于关键词推断
        self.assertAlmostEqual(sum(item["ratio"] for item in share), 1.0)

    def test_app_usage_ranking_sorted_with_names(self):
        today = date.today().isoformat()
        self.store.add_app_usage(today, "chrome.exe", 600, "Chrome")
        self.store.add_app_usage(today, "code.exe", 300, "VS Code")
        ranking = self.service.get_app_usage_ranking(date.today(), date.today())
        self.assertEqual(ranking[0]["process"], "chrome.exe")
        self.assertEqual(ranking[0]["display_name"], "Chrome")
        self.assertEqual(ranking[1]["category"], "编程")

    def test_get_day_events_reads_jsonl_with_category(self):
        log = ActivityEventLog(self.store.base_dir)
        now = datetime.now().astimezone()
        log.append_event("chrome.exe", "MDN", now - timedelta(minutes=30), now)
        events = self.service.get_day_events(now.date())
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["category"], "浏览器")

    def test_daily_activity_seconds_series(self):
        self.store.add_app_usage(date.today().isoformat(), "code.exe", 120, "Code")
        series = self.service.get_daily_activity_seconds(
            date.today() - timedelta(days=2), date.today()
        )
        self.assertEqual(len(series), 3)
        self.assertEqual(series[-1][1], 120)


class AfkSegmentTests(unittest.TestCase):
    """AFK 分段：显式 __afk__ 事件 + 超过 180 秒的空隙，合并重叠。"""

    def test_gap_between_events_becomes_afk(self):
        day = datetime.now().astimezone().replace(hour=0, minute=0, second=0, microsecond=0)
        events = [
            {"process": "code.exe", "title": "", "start": day, "end": day + timedelta(hours=1)},
            {"process": "chrome.exe", "title": "", "start": day + timedelta(hours=3), "end": day + timedelta(hours=4)},
        ]
        segments = compute_afk_segments(
            events, day, day + timedelta(hours=6), threshold_seconds=180
        )
        self.assertIn((day + timedelta(hours=1), day + timedelta(hours=3)), segments)

    def test_short_gap_not_afk(self):
        day = datetime.now().astimezone().replace(hour=8, minute=0, second=0, microsecond=0)
        events = [
            {"process": "a", "title": "", "start": day, "end": day + timedelta(minutes=10)},
            {"process": "b", "title": "", "start": day + timedelta(minutes=11), "end": day + timedelta(minutes=20)},
        ]
        segments = compute_afk_segments(
            events, day, day + timedelta(minutes=20), threshold_seconds=180
        )
        self.assertEqual(segments, [])

    def test_explicit_afk_merged_with_gap_segments(self):
        day = datetime.now().astimezone().replace(hour=8, minute=0, second=0, microsecond=0)
        events = [
            {"process": AFK_PROCESS, "title": "", "start": day + timedelta(hours=1), "end": day + timedelta(hours=2)},
            {"process": "a", "title": "", "start": day, "end": day + timedelta(minutes=30)},
            {"process": "b", "title": "", "start": day + timedelta(hours=1, minutes=30), "end": day + timedelta(hours=3)},
        ]
        segments = compute_afk_segments(
            events, day, day + timedelta(hours=3), threshold_seconds=180
        )
        # (30min→90min) 空隙 1 小时 ≥180s，与显式 60–120min 重叠 → 合并为一段
        self.assertEqual(len(segments), 1)
        self.assertEqual(segments[0], (day + timedelta(minutes=30), day + timedelta(hours=2)))

    def test_merge_adjacent_same_process(self):
        day = datetime.now().astimezone()
        events = [
            {"process": "a", "title": "t", "start": day, "end": day + timedelta(seconds=60)},
            {"process": "a", "title": "t", "start": day + timedelta(seconds=61), "end": day + timedelta(seconds=90)},
            {"process": "b", "title": "", "start": day, "end": day + timedelta(seconds=10)},
        ]
        merged = merge_adjacent(events)
        self.assertEqual(len(merged), 2)
        a = [e for e in merged if e["process"] == "a"][0]
        self.assertEqual((a["end"] - a["start"]).total_seconds(), 90)


class TimelineViewSmokeTests(unittest.TestCase):
    """时间线组件冒烟：set_day / 渲染 / 点击回调不崩。"""

    @classmethod
    def setUpClass(cls):
        from PyQt6.QtWidgets import QApplication

        cls.app = QApplication.instance() or QApplication([])

    def test_render_and_click_callback(self):
        from PyQt6.QtCore import QPointF, Qt
        from PyQt6.QtGui import QMouseEvent
        from PyQt6.QtWidgets import QVBoxLayout, QWidget

        from focus_capsule.activity_events import ActivityEventLog
        from focus_capsule.timeline_view import TimelineView

        with tempfile.TemporaryDirectory() as tmp:
            log = ActivityEventLog(Path(tmp))
            now = datetime.now().astimezone().replace(microsecond=0)
            start = now.replace(hour=9, minute=0)
            log.append_event("code.exe", "a.py", start, start + timedelta(minutes=40))

            host = QWidget()
            layout = QVBoxLayout(host)
            view = TimelineView()
            layout.addWidget(view)
            host.resize(900, 300)

            received = []
            view.event_clicked.connect(received.append)
            view.set_day(start.date(), [
                {"process": "code.exe", "title": "a.py", "start": start,
                 "end": start + timedelta(minutes=40),
                 "display_name": "Code", "category": "编程"},
            ])
            host.grab()  # 走一遍 paintEvent，渲染不崩

            # 模拟在色条位置点击（9:20 在 0–24 轴上的 x）
            rect = view._chart_rect()
            x = view._x_of(start + timedelta(minutes=20))
            y = rect.top() + 13
            event = QMouseEvent(
                QMouseEvent.Type.MouseButtonPress,
                QPointF(x, y),
                QPointF(x, y),
                Qt.MouseButton.LeftButton,
                Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier,
            )
            view.mousePressEvent(event)
            self.assertEqual(len(received), 1)
            self.assertEqual(received[0]["process"], "code.exe")


if __name__ == "__main__":
    unittest.main()
