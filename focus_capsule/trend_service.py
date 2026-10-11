"""Trend analysis service — derives insights from session history.

Reads :class:`~focus_capsule.models.SessionRecord` entries from
:class:`~focus_capsule.history_db.HistoryService` and produces
category-level statistics, 7-day / 30-day summaries, and streaks.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from focus_capsule.activity_events import AFK_PROCESS, ActivityEventLog
from focus_capsule.app_categories import category_for_process
from focus_capsule.data_models import china_today
from focus_capsule.history_db import HistoryService
from focus_capsule.models import SessionRecord

CST_TZ = timezone(timedelta(hours=8), name="CST")


def _record_cst_date(record: SessionRecord) -> Optional[date]:
    try:
        started = datetime.fromisoformat(record.started_at)
        if started.tzinfo is None:
            started = started.replace(tzinfo=CST_TZ)
        return started.astimezone(CST_TZ).date()
    except (TypeError, ValueError):
        return None


@dataclass
class DaySummary:
    date: date
    total_focus_seconds: int = 0
    session_count: int = 0
    completed_count: int = 0
    terminated_count: int = 0
    distraction_count: int = 0
    esc_used: int = 0

    @property
    def focus_minutes(self) -> int:
        return self.total_focus_seconds // 60

    @property
    def completion_rate(self) -> float:
        if self.session_count == 0:
            return 0.0
        return self.completed_count / self.session_count


@dataclass
class CategorySummary:
    category: str
    total_focus_seconds: int = 0
    session_count: int = 0
    app_count: int = 0


@dataclass
class RangeSummary:
    """任意日期区间的聚合结果（周/月视图使用）。"""

    start_date: date
    end_date: date
    days: list[DaySummary] = field(default_factory=list)
    total_focus_seconds: int = 0
    day_count: int = 0
    avg_daily_minutes: float = 0.0
    completion_rate: float = 0.0
    category_top5: list[CategorySummary] = field(default_factory=list)


@dataclass
class TrendReport:
    days: list[DaySummary] = field(default_factory=list)
    total_focus_seconds: int = 0
    total_sessions: int = 0
    avg_daily_minutes: float = 0.0
    best_day: Optional[DaySummary] = None
    current_streak: int = 0
    longest_streak: int = 0
    category_breakdown: list[CategorySummary] = field(default_factory=list)


@dataclass
class StreakSummary:
    """全量历史的连续达标与破功留痕（不受 7/30 天窗口限制）。"""

    current_streak: int = 0
    longest_streak: int = 0
    broken_days: list[date] = field(default_factory=list)
    today_achieved: bool = False


class TrendService:
    """Computes trend analytics from session history."""

    def __init__(self, history: HistoryService, app_config=None, data_store=None):
        self._history = history
        self._app_config = app_config
        self._data_store = data_store

    def set_app_config(self, app_config) -> None:
        self._app_config = app_config

    def _store(self):
        """惰性获取 DataStore（老调用方未注入时走默认数据目录）。"""
        if self._data_store is None:
            from focus_capsule.data_store import DataStore

            self._data_store = DataStore()
        return self._data_store

    def _event_log(self) -> ActivityEventLog:
        return ActivityEventLog(self._store().base_dir)

    def _categorize(self, process_name: str) -> str:
        if self._app_config and self._app_config.app_categories:
            cf = process_name.strip().casefold()
            for cat in self._app_config.app_categories:
                if cat.process_name.strip().casefold() == cf:
                    return cat.category
        return "其他"

    def get_day_summaries(self, days: int = 7) -> list[DaySummary]:
        return self._summarize_days(self._history.load_history(), days)

    @staticmethod
    def _summarize_days(records: list[SessionRecord], days: int) -> list[DaySummary]:
        today = china_today()
        start = today - timedelta(days=days - 1)

        by_date: dict[date, DaySummary] = {}
        for i in range(days):
            d = start + timedelta(days=i)
            by_date[d] = DaySummary(date=d)

        for r in records:
            d = _record_cst_date(r)
            if d and d in by_date:
                s = by_date[d]
                s.total_focus_seconds += max(0, r.actual_focus_seconds)
                s.session_count += 1
                if r.outcome == "completed":
                    s.completed_count += 1
                elif r.outcome == "terminated":
                    s.terminated_count += 1
                s.distraction_count += r.distraction_count
                s.esc_used += r.esc_used

        return [by_date[start + timedelta(days=i)] for i in range(days)]

    def get_trend(self, days: int = 7) -> TrendReport:
        records = self._history.load_history()
        summaries = self._summarize_days(records, days)
        total_seconds = sum(s.total_focus_seconds for s in summaries)
        total_sessions = sum(s.session_count for s in summaries)
        avg = total_seconds / max(1, days) / 60.0

        best = max(summaries, key=lambda s: s.total_focus_seconds, default=None)
        if best and best.total_focus_seconds == 0:
            best = None

        # Streaks (consecutive days with ≥1 completed session)
        current_streak = 0
        longest_streak = 0
        streak = 0
        for s in reversed(summaries):
            if s.completed_count > 0:
                streak += 1
            else:
                if streak > longest_streak:
                    longest_streak = streak
                streak = 0
        if streak > 0:
            current_streak = streak
            longest_streak = max(longest_streak, streak)

        # Category breakdown
        cat_seconds: dict[str, int] = defaultdict(int)
        cat_sessions: dict[str, int] = defaultdict(int)
        cat_apps: dict[str, set] = defaultdict(set)
        cutoff = china_today() - timedelta(days=days)
        for r in records:
            d = _record_cst_date(r)
            if not d or d < cutoff:
                continue
            for app in r.whitelisted_apps:
                cat = self._categorize(app)
                cat_seconds[cat] += max(0, r.actual_focus_seconds)
                cat_sessions[cat] += 1
                cat_apps[cat].add(app)

        categories = [
            CategorySummary(
                category=cat,
                total_focus_seconds=secs,
                session_count=cat_sessions[cat],
                app_count=len(cat_apps[cat]),
            )
            for cat, secs in sorted(cat_seconds.items(), key=lambda x: -x[1])
        ]

        return TrendReport(
            days=summaries,
            total_focus_seconds=total_seconds,
            total_sessions=total_sessions,
            avg_daily_minutes=round(avg, 1),
            best_day=best,
            current_streak=current_streak,
            longest_streak=longest_streak,
            category_breakdown=categories,
        )

    def get_today_summary(self) -> DaySummary:
        today = china_today()
        records = self._history.load_history()
        s = DaySummary(date=today)
        for r in records:
            d = _record_cst_date(r)
            if d == today:
                s.total_focus_seconds += max(0, r.actual_focus_seconds)
                s.session_count += 1
                if r.outcome == "completed":
                    s.completed_count += 1
                elif r.outcome == "terminated":
                    s.terminated_count += 1
                s.distraction_count += r.distraction_count
                s.esc_used += r.esc_used
        return s

    # ── 区间聚合（新代码统一本地时区，不改老函数行为）──────────

    @staticmethod
    def _record_local_date(record: SessionRecord) -> Optional[date]:
        """把会话开始时间映射到本地日期；naive 时间按本地时区解释。"""
        try:
            started = datetime.fromisoformat(record.started_at)
            if started.tzinfo is None:
                started = started.astimezone()
            return started.astimezone().date()
        except (TypeError, ValueError):
            return None

    def _records_in_range(
        self, start_date: date, end_date: date
    ) -> list[SessionRecord]:
        result = []
        for r in self._history.load_history():
            d = self._record_local_date(r)
            if d and start_date <= d <= end_date:
                result.append(r)
        return result

    def get_range_summary(self, start_date: date, end_date: date) -> RangeSummary:
        """聚合 [start_date, end_date] 闭区间的会话统计。"""
        if end_date < start_date:
            start_date, end_date = end_date, start_date
        records = self._records_in_range(start_date, end_date)

        by_date: dict[date, DaySummary] = {}
        day = start_date
        while day <= end_date:
            by_date[day] = DaySummary(date=day)
            day += timedelta(days=1)

        for r in records:
            d = self._record_local_date(r)
            if not d or d not in by_date:
                continue
            s = by_date[d]
            s.total_focus_seconds += max(0, r.actual_focus_seconds)
            s.session_count += 1
            if r.outcome == "completed":
                s.completed_count += 1
            elif r.outcome == "terminated":
                s.terminated_count += 1
            s.distraction_count += r.distraction_count
            s.esc_used += r.esc_used

        days = list(by_date.values())
        total = sum(s.total_focus_seconds for s in days)
        sessions = sum(s.session_count for s in days)
        completed = sum(s.completed_count for s in days)
        day_count = len(days)
        share = self.get_category_share(start_date, end_date)
        top5 = [
            CategorySummary(
                category=item["category"],
                total_focus_seconds=item["seconds"],
                app_count=item["app_count"],
            )
            for item in share[:5]
        ]
        return RangeSummary(
            start_date=start_date,
            end_date=end_date,
            days=days,
            total_focus_seconds=total,
            day_count=day_count,
            avg_daily_minutes=total / max(1, day_count) / 60.0,
            completion_rate=completed / sessions if sessions else 0.0,
            category_top5=top5,
        )

    def _activity_seconds_by_app(
        self, start_date: date, end_date: date
    ) -> tuple[dict[str, int], dict[str, str]]:
        """从 daily_activity.json 汇总区间内每个进程的秒数与显示名。"""
        seconds: dict[str, int] = {}
        names: dict[str, str] = {}
        try:
            entries = self._store().load_all_activity()
        except OSError:
            return seconds, names
        day = start_date
        while day <= end_date:
            entry = entries.get(day.isoformat())
            if entry is not None:
                for process, value in entry.app_usage_seconds.items():
                    seconds[process] = seconds.get(process, 0) + max(0, int(value))
                names.update(entry.app_display_names)
            day += timedelta(days=1)
        return seconds, names

    def get_daily_activity_seconds(
        self, start_date: date, end_date: date
    ) -> list[tuple[date, int]]:
        """区间内每天的前台总秒数（来自 daily_activity.json），供柱状图。"""
        if end_date < start_date:
            start_date, end_date = end_date, start_date
        try:
            entries = self._store().load_all_activity()
        except OSError:
            entries = {}
        result: list[tuple[date, int]] = []
        day = start_date
        while day <= end_date:
            entry = entries.get(day.isoformat())
            total = sum(max(0, int(v)) for v in entry.app_usage_seconds.values()) if entry else 0
            result.append((day, total))
            day += timedelta(days=1)
        return result

    def get_app_usage_ranking(
        self, start_date: date, end_date: date
    ) -> list[dict]:
        """区间内按应用累计前台秒数排行（含分类与占比）。"""
        if end_date < start_date:
            start_date, end_date = end_date, start_date
        seconds, names = self._activity_seconds_by_app(start_date, end_date)
        total = sum(seconds.values())
        ranking = []
        for process, value in sorted(seconds.items(), key=lambda x: -x[1]):
            ranking.append(
                {
                    "process": process,
                    "display_name": names.get(process) or process,
                    "category": self._category_for(process),
                    "seconds": value,
                    "ratio": value / total if total else 0.0,
                }
            )
        return ranking

    def _category_for(self, process: str) -> str:
        if self._app_config is not None:
            return category_for_process(self._app_config, process)
        from focus_capsule.app_categories import infer_app_category

        return infer_app_category(process)

    def get_category_share(
        self, start_date: date, end_date: date
    ) -> list[dict]:
        """区间内按分类聚合前台时间占比（分类在查询时现算，不落库）。"""
        if end_date < start_date:
            start_date, end_date = end_date, start_date
        seconds, _names = self._activity_seconds_by_app(start_date, end_date)
        by_cat: dict[str, int] = defaultdict(int)
        apps_per_cat: dict[str, set] = defaultdict(set)
        for process, value in seconds.items():
            cat = self._category_for(process)
            by_cat[cat] += value
            apps_per_cat[cat].add(process)
        total = sum(by_cat.values())
        result = []
        for cat, value in sorted(by_cat.items(), key=lambda x: -x[1]):
            result.append(
                {
                    "category": cat,
                    "seconds": value,
                    "ratio": value / total if total else 0.0,
                    "app_count": len(apps_per_cat[cat]),
                }
            )
        return result

    def get_day_events(self, day: date) -> list[dict]:
        """读取某天的前台切换区间事件（含 AFK 段），裁剪并合并。"""
        try:
            events = self._event_log().read_events(day)
        except OSError:
            events = []
        window_start = datetime.combine(day, datetime.min.time()).astimezone()
        window_end = (window_start + timedelta(days=1)).replace(microsecond=0)
        from focus_capsule.activity_events import merge_adjacent

        clamped = ActivityEventLog.clamp_events(events, window_start, window_end)
        foreground = merge_adjacent(
            [ev for ev in clamped if ev["process"] != "__afk__"]
        )
        afk = [ev for ev in clamped if ev["process"] == "__afk__"]

        # 查询时现算分类与显示名，供时间线取色/标注（不落库）
        display_names: dict[str, str] = {}
        try:
            entry = self._store().get_activity(day.isoformat())
            display_names = dict(entry.app_display_names)
        except OSError:
            pass
        result: list[dict] = []
        for ev in foreground:
            item = dict(ev)
            item["display_name"] = display_names.get(ev["process"], "")
            item["category"] = self._category_for(ev["process"])
            result.append(item)
        for ev in afk:
            item = dict(ev)
            item["display_name"] = "离开"
            item["category"] = AFK_PROCESS
            result.append(item)
        return result

    # ── 连续达标 + 破功留痕（新代码统一本地时区，读目标仍兼容 CST 键）──

    def get_broke_counts_by_date(self) -> dict[date, int]:
        """按本地日期统计破功会话数（当天每条 broke=True 记录各计 1 次）。"""
        counts: dict[date, int] = {}
        for r in self._history.load_history():
            if not getattr(r, "broke", False):
                continue
            d = self._record_local_date(r)
            if d is not None:
                counts[d] = counts.get(d, 0) + 1
        return counts

    def get_streak_summary(self) -> StreakSummary:
        """扫描全量历史计算连续达标与破功日，不受 7/30 天窗口限制。

        达标日规则：
        - AppConfig.daily_goal_enabled 为真时，取当天 daily goal 条目
          （daily_goals.json 按 CST 日期键存储，读取方式保持兼容），
          achieved_minutes >= target_minutes 即达标；target 为 0 或缺条目
          时退回「当天有 completed 会话」。
        - 目标未开启时，当天有 completed 会话即达标。

        破功日（当天至少一条 broke=True）不打断连续，只在结果里单独列出。
        current_streak 从今天往回数；今天还没过完，若今日未达标则从昨天起算，
        是否达标由 today_achieved 单独给出。
        """
        broke_counts = self.get_broke_counts_by_date()

        completed_by_day: dict[date, int] = {}
        for r in self._history.load_history():
            if r.outcome != "completed":
                continue
            d = self._record_local_date(r)
            if d is not None:
                completed_by_day[d] = completed_by_day.get(d, 0) + 1

        goal_enabled = bool(self._app_config and self._app_config.daily_goal_enabled)
        goals: dict = {}
        if goal_enabled:
            try:
                goals = self._store().load_all_goals()
            except OSError:
                goals = {}

        def achieved(d: date) -> bool:
            if goal_enabled:
                entry = goals.get(d.isoformat())
                if entry is not None and entry.target_minutes > 0:
                    return entry.achieved_minutes >= entry.target_minutes
            return completed_by_day.get(d, 0) > 0

        def _goal_day_keys() -> set[date]:
            # 目标按 CST 日期键存储；无 completed 会话的日子也要参与达标判定
            keys: set[date] = set()
            for raw in goals:
                try:
                    keys.add(date.fromisoformat(str(raw)))
                except (TypeError, ValueError):
                    continue
            return keys

        all_days = sorted(
            set(completed_by_day) | set(broke_counts) | _goal_day_keys()
        )
        achieved_days = {d for d in all_days if achieved(d)}

        # 全量最长连续：按日排序扫描达标日
        longest = 0
        run = 0
        prev: Optional[date] = None
        for d in sorted(achieved_days):
            run = run + 1 if prev is not None and (d - prev).days == 1 else 1
            prev = d
            longest = max(longest, run)

        today = datetime.now().astimezone().date()
        cursor = today if today in achieved_days else today - timedelta(days=1)
        current = 0
        while cursor in achieved_days:
            current += 1
            cursor -= timedelta(days=1)

        return StreakSummary(
            current_streak=current,
            longest_streak=longest,
            broken_days=sorted(broke_counts),
            today_achieved=today in achieved_days,
        )
