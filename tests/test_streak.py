"""连续打卡 + 破功留痕的单元测试：TrendService.get_streak_summary。

覆盖：达标日判定（每日目标开启/关闭两种）、破功日收集且不打断连续、
跨窗口长度（40 天数据证明超过 get_trend 的 30 天上限）、
current/longest 计算、today_achieved、get_broke_counts_by_date 计数。
数据目录全部用 tempfile 隔离。
"""

import os
import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from focus_capsule.data_models import AppConfig, DailyGoalEntry
from focus_capsule.data_store import DataStore
from focus_capsule.history_db import HistoryService
from focus_capsule.models import SessionRecord
from focus_capsule.trend_service import StreakSummary, TrendService


def _make_record(
    started: datetime,
    seconds: int = 1800,
    outcome: str = "completed",
    broke: bool = False,
) -> SessionRecord:
    return SessionRecord(
        started_at=started.isoformat(timespec="seconds"),
        ended_at=(started + timedelta(seconds=seconds)).isoformat(timespec="seconds"),
        duration_minutes=max(1, seconds // 60),
        actual_focus_seconds=seconds,
        distraction_count=0,
        esc_used=0,
        mode="Standard",
        whitelisted_apps=["code.exe"],
        distractions=[],
        outcome=outcome,
        broke=broke,
    )


class StreakSummaryTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        base = Path(self._tmp.name)
        self.history = HistoryService(history_path=base / "history.json")
        self.store = DataStore(data_path=base / "data")
        self.config = AppConfig()
        self.service = TrendService(self.history, self.config, self.store)
        # 统一用本地正午时间造数据，日期归属稳定
        self.today = datetime.now().astimezone().date()

    def tearDown(self):
        self._tmp.cleanup()

    def _day(self, offset: int) -> date:
        return self.today - timedelta(days=offset)

    def _at_noon(self, offset: int) -> datetime:
        return datetime.combine(self._day(offset), datetime.min.time()).replace(
            hour=12
        )

    # ── 目标关闭：有 completed 会话即达标 ──────────────────

    def test_goal_disabled_streak_from_completed_sessions(self):
        # 前天、昨天各有 completed，今天还没有记录
        self.history.save_record(_make_record(self._at_noon(2)))
        self.history.save_record(_make_record(self._at_noon(1)))
        summary = self.service.get_streak_summary()
        self.assertIsInstance(summary, StreakSummary)
        # 今天未达标时，连续天数从昨天往回数（今天还没过完，不应清零）
        self.assertEqual(summary.current_streak, 2)
        self.assertEqual(summary.longest_streak, 2)
        self.assertFalse(summary.today_achieved)

    def test_goal_disabled_terminated_only_day_breaks_streak(self):
        # 大前天、前天 completed；昨天只有 terminated → 当前连续应为 0
        self.history.save_record(_make_record(self._at_noon(3)))
        self.history.save_record(_make_record(self._at_noon(2)))
        self.history.save_record(
            _make_record(self._at_noon(1), outcome="terminated")
        )
        summary = self.service.get_streak_summary()
        self.assertEqual(summary.current_streak, 0)
        self.assertEqual(summary.longest_streak, 2)

    def test_goal_disabled_today_achieved_flag(self):
        self.history.save_record(_make_record(self._at_noon(0)))
        summary = self.service.get_streak_summary()
        self.assertTrue(summary.today_achieved)
        self.assertEqual(summary.current_streak, 1)

    # ── 目标开启：按 achieved_minutes >= target_minutes 判定 ──

    def test_goal_enabled_uses_achieved_minutes(self):
        self.config.daily_goal_enabled = True
        # 前天：目标达成（无 completed 会话也算达标）
        self.history.save_record(
            _make_record(self._at_noon(2), outcome="terminated")
        )
        self.store.save_goal(
            DailyGoalEntry(date_str=self._day(2).isoformat(),
                           target_minutes=30, achieved_minutes=30)
        )
        # 昨天：completed 会话不少但 achieved < target → 不达标
        self.history.save_record(_make_record(self._at_noon(1), 3600))
        self.store.save_goal(
            DailyGoalEntry(date_str=self._day(1).isoformat(),
                           target_minutes=60, achieved_minutes=10)
        )
        summary = self.service.get_streak_summary()
        self.assertFalse(summary.today_achieved)
        # 昨天不达标，当前连续为 0（前天达标但已与昨天断开）
        self.assertEqual(summary.current_streak, 0)
        self.assertEqual(summary.longest_streak, 1)

    def test_goal_enabled_zero_target_falls_back_to_completed(self):
        self.config.daily_goal_enabled = True
        # 昨天：target 为 0 → 退回「有 completed 会话」判定
        self.history.save_record(_make_record(self._at_noon(1)))
        self.store.save_goal(
            DailyGoalEntry(date_str=self._day(1).isoformat(),
                           target_minutes=0, achieved_minutes=0)
        )
        summary = self.service.get_streak_summary()
        self.assertEqual(summary.current_streak, 1)
        self.assertEqual(summary.longest_streak, 1)

    # ── 破功日收集，且不打断连续 ──────────────────────────

    def test_broken_days_collected_but_do_not_break_streak(self):
        # 昨天达标且破功、前天达标、大前天破功 → 连续仍为 2
        self.history.save_record(_make_record(self._at_noon(2)))
        self.history.save_record(_make_record(self._at_noon(1)))
        self.history.save_record(
            _make_record(self._at_noon(1), outcome="terminated", broke=True)
        )
        self.history.save_record(
            _make_record(self._at_noon(3), outcome="terminated", broke=True)
        )
        summary = self.service.get_streak_summary()
        self.assertEqual(summary.current_streak, 2)
        self.assertEqual(summary.longest_streak, 2)
        self.assertEqual(summary.broken_days, [self._day(3), self._day(1)])

    def test_get_broke_counts_by_date(self):
        self.history.save_record(
            _make_record(self._at_noon(1), broke=True)
        )
        self.history.save_record(
            _make_record(self._at_noon(1, ), seconds=600, broke=True)
        )
        self.history.save_record(_make_record(self._at_noon(2)))
        counts = self.service.get_broke_counts_by_date()
        self.assertEqual(counts, {self._day(1): 2})

    # ── 跨窗口长度：40 天数据应超过 get_trend(30) 的上限 ────

    def test_streak_exceeds_30_day_window(self):
        # 造 40 个连续达标日（含今天）
        for offset in range(40):
            self.history.save_record(_make_record(self._at_noon(offset)))
        summary = self.service.get_streak_summary()
        self.assertEqual(summary.current_streak, 40)
        self.assertEqual(summary.longest_streak, 40)
        self.assertTrue(summary.today_achieved)
        # 对照组：get_trend 的 30 天窗口最多只能给出 30
        legacy = self.service.get_trend(days=30)
        self.assertLessEqual(legacy.current_streak, 30)

    def test_empty_history_returns_zeros(self):
        summary = self.service.get_streak_summary()
        self.assertEqual(summary.current_streak, 0)
        self.assertEqual(summary.longest_streak, 0)
        self.assertEqual(summary.broken_days, [])
        self.assertFalse(summary.today_achieved)

    def test_longest_streak_beats_current_streak(self):
        # 早段 5 连击，近段只有 2 天 → longest 5，current 2
        for offset in range(4, 9):  # 第 4~8 天前，连续 5 天
            self.history.save_record(_make_record(self._at_noon(offset)))
        self.history.save_record(_make_record(self._at_noon(1)))
        self.history.save_record(_make_record(self._at_noon(2)))
        # 第 3 天前故意断掉
        summary = self.service.get_streak_summary()
        self.assertEqual(summary.current_streak, 2)
        self.assertEqual(summary.longest_streak, 5)


if __name__ == "__main__":
    unittest.main()
