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
class TrendReport:
    days: list[DaySummary] = field(default_factory=list)
    total_focus_seconds: int = 0
    total_sessions: int = 0
    avg_daily_minutes: float = 0.0
    best_day: Optional[DaySummary] = None
    current_streak: int = 0
    longest_streak: int = 0
    category_breakdown: list[CategorySummary] = field(default_factory=list)


class TrendService:
    """Computes trend analytics from session history."""

    def __init__(self, history: HistoryService, app_config=None):
        self._history = history
        self._app_config = app_config

    def set_app_config(self, app_config) -> None:
        self._app_config = app_config

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
