"""Daily metrics and multi-target progress derived from real local records."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone

from focus_capsule.app_categories import (
    category_for_process,
    display_name_for_process,
)
from focus_capsule.data_models import AppConfig, DailyGoalEntry, china_today
from focus_capsule.data_store import DataStore
from focus_capsule.history_db import HistoryService
from focus_capsule.models import SessionRecord

CST = timezone(timedelta(hours=8), name="CST")


def _record_date(record: SessionRecord) -> date | None:
    try:
        started = datetime.fromisoformat(record.started_at)
        if started.tzinfo is None:
            started = started.replace(tzinfo=CST)
        return started.astimezone(CST).date()
    except (TypeError, ValueError):
        return None


@dataclass
class ScheduledLockSummary:
    started_at: str
    ended_at: str
    label: str
    actual_minutes: int
    outcome: str


@dataclass
class DailyMetrics:
    date: date
    total_focus_seconds: int = 0
    session_count: int = 0
    completed_sessions: int = 0
    terminated_sessions: int = 0
    distraction_count: int = 0
    temporary_unlocks: int = 0
    app_focus_seconds: dict[str, int] = field(default_factory=dict)
    category_focus_seconds: dict[str, int] = field(default_factory=dict)
    app_usage_seconds: dict[str, int] = field(default_factory=dict)
    category_usage_seconds: dict[str, int] = field(default_factory=dict)
    scheduled_locks: list[ScheduledLockSummary] = field(default_factory=list)

    @property
    def focus_minutes(self) -> int:
        return self.total_focus_seconds // 60


@dataclass
class GoalProgress:
    key: str
    label: str
    current: int
    target: int
    unit: str
    direction: str
    percent: int
    status: str

    @property
    def value_text(self) -> str:
        if self.direction == "maximum":
            return f"{self.current}/{self.target} {self.unit}"
        return f"{self.current}/{self.target} {self.unit}"


@dataclass
class DailyGoalProgress:
    items: list[GoalProgress] = field(default_factory=list)
    percent: int | None = None
    state: str = "none"


class DailyProgressService:
    """Join focus history, app usage, categories and target definitions."""

    def __init__(
        self,
        history: HistoryService,
        data_store: DataStore,
        app_config: AppConfig,
    ):
        self._history = history
        self._store = data_store
        self._config = app_config

    def set_app_config(self, config: AppConfig) -> None:
        self._config = config

    def metrics_for_date(self, target_date: date) -> DailyMetrics:
        return self.metrics_for_dates([target_date])[target_date]

    def metrics_for_dates(self, dates: list[date]) -> dict[date, DailyMetrics]:
        requested = set(dates)
        by_date = {target: DailyMetrics(date=target) for target in requested}
        for record in self._history.load_history():
            record_day = _record_date(record)
            if record_day not in by_date:
                continue
            metrics = by_date[record_day]
            focus_seconds = max(0, int(record.actual_focus_seconds))
            metrics.total_focus_seconds += focus_seconds
            metrics.session_count += 1
            if record.outcome == "completed":
                metrics.completed_sessions += 1
            elif record.outcome == "terminated":
                metrics.terminated_sessions += 1
            metrics.distraction_count += max(0, int(record.distraction_count))
            metrics.temporary_unlocks += max(0, int(record.esc_used))

            per_app = {
                str(process).strip().casefold(): max(0, int(seconds))
                for process, seconds in getattr(record, "app_focus_seconds", {}).items()
                if str(process).strip()
            }
            if not per_app:
                whitelisted = [
                    str(process).strip().casefold()
                    for process in record.whitelisted_apps
                    if str(process).strip()
                ]
                if len(whitelisted) == 1:
                    per_app[whitelisted[0]] = focus_seconds
            for process, seconds in per_app.items():
                metrics.app_focus_seconds[process] = (
                    metrics.app_focus_seconds.get(process, 0) + seconds
                )

            source = str(getattr(record, "source", "timer") or "timer")
            legacy_schedule = str(record.goal or "") == "通过日程锁定进行专注"
            if source == "schedule" or legacy_schedule:
                metrics.scheduled_locks.append(
                    ScheduledLockSummary(
                        started_at=record.started_at,
                        ended_at=record.ended_at,
                        label=(
                            str(getattr(record, "schedule_label", "")).strip()
                            or "日程锁定"
                        ),
                        actual_minutes=focus_seconds // 60,
                        outcome=record.outcome,
                    )
                )

        activities = self._store.load_all_activity()
        for target_date, metrics in by_date.items():
            for process, seconds in metrics.app_focus_seconds.items():
                category = category_for_process(self._config, process)
                metrics.category_focus_seconds[category] = (
                    metrics.category_focus_seconds.get(category, 0) + seconds
                )

            activity = activities.get(target_date.isoformat())
            if activity is not None:
                metrics.app_usage_seconds = dict(activity.app_usage_seconds)
            for process, seconds in metrics.app_usage_seconds.items():
                category = category_for_process(self._config, process)
                metrics.category_usage_seconds[category] = (
                    metrics.category_usage_seconds.get(category, 0) + seconds
                )
        return by_date

    @staticmethod
    def _minimum_progress(
        key: str,
        label: str,
        current: int,
        target: int,
        unit: str,
    ) -> GoalProgress:
        target = max(1, int(target))
        current = max(0, int(current))
        percent = min(100, round(current / target * 100))
        return GoalProgress(
            key=key,
            label=label,
            current=current,
            target=target,
            unit=unit,
            direction="minimum",
            percent=percent,
            status="complete" if current >= target else "in_progress",
        )

    @staticmethod
    def _maximum_progress(
        key: str,
        label: str,
        current: int,
        target: int,
        unit: str,
    ) -> GoalProgress:
        target = max(0, int(target))
        current = max(0, int(current))
        percent = 100 if target == 0 and current else (
            min(100, round(current / max(1, target) * 100))
        )
        return GoalProgress(
            key=key,
            label=label,
            current=current,
            target=target,
            unit=unit,
            direction="maximum",
            percent=percent,
            status="exceeded" if current > target else "safe",
        )

    def progress_for_date(
        self,
        target_date: date,
        metrics: DailyMetrics | None = None,
    ) -> DailyGoalProgress:
        entry = self._store.get_goal(target_date.isoformat())
        metrics = metrics or self.metrics_for_date(target_date)
        targets = entry.targets
        items: list[GoalProgress] = []

        if targets.max_distractions is not None:
            items.append(
                self._maximum_progress(
                    "distractions",
                    "分心次数",
                    metrics.distraction_count,
                    targets.max_distractions,
                    "次",
                )
            )
        if targets.total_focus_minutes is not None:
            items.append(
                self._minimum_progress(
                    "focus_minutes",
                    "总专注时长",
                    metrics.focus_minutes,
                    targets.total_focus_minutes,
                    "分钟",
                )
            )
        for category, minutes in targets.category_focus_minutes.items():
            items.append(
                self._minimum_progress(
                    f"category_focus:{category}",
                    f"{category}专注",
                    metrics.category_focus_seconds.get(category, 0) // 60,
                    minutes,
                    "分钟",
                )
            )
        if targets.focus_sessions is not None:
            items.append(
                self._minimum_progress(
                    "sessions",
                    "完成专注",
                    metrics.completed_sessions,
                    targets.focus_sessions,
                    "次",
                )
            )
        for process, minutes in targets.app_usage_minutes.items():
            items.append(
                self._maximum_progress(
                    f"app_usage:{process}",
                    f"{display_name_for_process(self._config, process)}使用",
                    metrics.app_usage_seconds.get(process.casefold(), 0) // 60,
                    minutes,
                    "分钟",
                )
            )
        for category, minutes in targets.category_usage_minutes.items():
            items.append(
                self._maximum_progress(
                    f"category_usage:{category}",
                    f"{category}类应用使用",
                    metrics.category_usage_seconds.get(category, 0) // 60,
                    minutes,
                    "分钟",
                )
            )
        if targets.max_temporary_unlocks is not None:
            items.append(
                self._maximum_progress(
                    "temporary_unlocks",
                    "临时解锁",
                    metrics.temporary_unlocks,
                    targets.max_temporary_unlocks,
                    "次",
                )
            )

        if not items:
            return DailyGoalProgress()

        if any(item.status == "exceeded" for item in items):
            state = "failed"
        elif all(item.status in {"complete", "safe"} for item in items):
            state = "complete"
        else:
            state = "in_progress"

        minimum_items = [item for item in items if item.direction == "minimum"]
        if minimum_items:
            percent = round(sum(item.percent for item in minimum_items) / len(minimum_items))
        else:
            percent = 0 if state == "failed" else 100
        return DailyGoalProgress(items=items, percent=percent, state=state)

    def remaining_unlocks_today(self) -> int | None:
        entry = self._store.get_today_goal()
        limit = entry.targets.max_temporary_unlocks
        if limit is None:
            return None
        used = self.metrics_for_date(china_today()).temporary_unlocks
        return max(0, limit - used)

    def exceeded_usage_limit(
        self,
        process_name: str,
        target_date: date | None = None,
    ) -> tuple[str, int, int] | None:
        process = str(process_name).strip().casefold()
        if not process:
            return None
        target_date = target_date or china_today()
        entry: DailyGoalEntry = self._store.get_goal(target_date.isoformat())
        metrics = self.metrics_for_date(target_date)

        app_limit = entry.targets.app_usage_minutes.get(process)
        if app_limit is not None:
            used = metrics.app_usage_seconds.get(process, 0) // 60
            if used >= app_limit:
                return display_name_for_process(self._config, process), used, app_limit

        category = category_for_process(self._config, process)
        category_limit = entry.targets.category_usage_minutes.get(category)
        if category_limit is not None:
            used = metrics.category_usage_seconds.get(category, 0) // 60
            if used >= category_limit:
                return f"{category}类应用", used, category_limit
        return None
