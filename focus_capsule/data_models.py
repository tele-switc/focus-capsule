"""App category, daily goal, AI daily report and trend models.

All new data structures introduced in v2.1 live here to preserve backward
compatibility with the original :mod:`focus_capsule.models`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from enum import Enum

CST = timezone(timedelta(hours=8), name="CST")


def china_today() -> date:
    """Return today's date in China Standard Time."""
    return datetime.now(CST).date()


# ── App categories ───────────────────────────────────────────

DEFAULT_CATEGORIES = [
    "学习", "工作", "编程", "办公软件", "浏览器",
    "通讯", "阅读", "影音娱乐", "游戏", "系统工具", "其他",
]


@dataclass
class AppCategory:
    """An app classification: process_name -> category mapping."""
    process_name: str
    display_name: str
    category: str = "其他"
    icon_source: str = ""
    custom_path: str = ""


@dataclass
class AppConfig:
    """Persistent app-level configuration for v2.1 features."""
    app_categories: list[AppCategory] = field(default_factory=list)
    daily_goal_minutes: int = 120
    daily_goal_enabled: bool = False
    ai_daily_report_enabled: bool = False
    ai_daily_report_time: str = "21:00"
    ai_api_key: str = ""
    ai_api_url: str = "https://api.deepseek.com/v1/chat/completions"
    ai_model: str = "deepseek-chat"

    def to_dict(self) -> dict:
        return {
            "app_categories": [
                {
                    "process_name": c.process_name,
                    "display_name": c.display_name,
                    "category": c.category,
                    "icon_source": c.icon_source,
                    "custom_path": c.custom_path,
                }
                for c in self.app_categories
            ],
            "daily_goal_minutes": self.daily_goal_minutes,
            "daily_goal_enabled": self.daily_goal_enabled,
            "ai_daily_report_enabled": self.ai_daily_report_enabled,
            "ai_daily_report_time": self.ai_daily_report_time,
            "ai_api_key": self.ai_api_key,
            "ai_api_url": self.ai_api_url,
            "ai_model": self.ai_model,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AppConfig":
        if not isinstance(data, dict):
            return cls()
        cats = []
        for item in data.get("app_categories", []):
            if isinstance(item, dict):
                cats.append(AppCategory(
                    process_name=str(item.get("process_name", "")),
                    display_name=str(item.get("display_name", "")),
                    category=str(item.get("category", "其他")),
                    icon_source=str(item.get("icon_source", "")),
                    custom_path=str(item.get("custom_path", "")),
                ))
        return cls(
            app_categories=cats,
            daily_goal_minutes=int(data.get("daily_goal_minutes", 120)),
            daily_goal_enabled=bool(data.get("daily_goal_enabled", False)),
            ai_daily_report_enabled=bool(data.get("ai_daily_report_enabled", False)),
            ai_daily_report_time=str(data.get("ai_daily_report_time", "21:00")),
            ai_api_key=str(data.get("ai_api_key", "")),
            ai_api_url=str(data.get("ai_api_url", "https://api.deepseek.com/v1/chat/completions")),
            ai_model=str(data.get("ai_model", "deepseek-chat")),
        )


# ── Daily goal entry ─────────────────────────────────────────


def _optional_non_negative_int(value) -> int | None:
    if value is None or value == "":
        return None
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return None


def _non_negative_int(value, default: int = 0) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return max(0, int(default))


def _positive_int_map(value) -> dict[str, int]:
    if not isinstance(value, dict):
        return {}
    result: dict[str, int] = {}
    for raw_key, raw_value in value.items():
        key = str(raw_key).strip()
        try:
            number = int(raw_value)
        except (TypeError, ValueError):
            continue
        if key and number > 0:
            result[key] = number
    return result


@dataclass
class DailyGoalTargets:
    """Optional, independently selectable targets for one day."""

    max_distractions: int | None = None
    total_focus_minutes: int | None = None
    category_focus_minutes: dict[str, int] = field(default_factory=dict)
    focus_sessions: int | None = None
    app_usage_minutes: dict[str, int] = field(default_factory=dict)
    category_usage_minutes: dict[str, int] = field(default_factory=dict)
    max_temporary_unlocks: int | None = None

    @property
    def is_empty(self) -> bool:
        return not any(
            (
                self.max_distractions is not None,
                self.total_focus_minutes is not None,
                bool(self.category_focus_minutes),
                self.focus_sessions is not None,
                bool(self.app_usage_minutes),
                bool(self.category_usage_minutes),
                self.max_temporary_unlocks is not None,
            )
        )

    def to_dict(self) -> dict:
        return {
            "max_distractions": self.max_distractions,
            "total_focus_minutes": self.total_focus_minutes,
            "category_focus_minutes": dict(self.category_focus_minutes),
            "focus_sessions": self.focus_sessions,
            "app_usage_minutes": dict(self.app_usage_minutes),
            "category_usage_minutes": dict(self.category_usage_minutes),
            "max_temporary_unlocks": self.max_temporary_unlocks,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DailyGoalTargets":
        if not isinstance(data, dict):
            return cls()
        return cls(
            max_distractions=_optional_non_negative_int(data.get("max_distractions")),
            total_focus_minutes=_optional_non_negative_int(
                data.get("total_focus_minutes")
            ),
            category_focus_minutes=_positive_int_map(
                data.get("category_focus_minutes")
            ),
            focus_sessions=_optional_non_negative_int(data.get("focus_sessions")),
            app_usage_minutes=_positive_int_map(data.get("app_usage_minutes")),
            category_usage_minutes=_positive_int_map(
                data.get("category_usage_minutes")
            ),
            max_temporary_unlocks=_optional_non_negative_int(
                data.get("max_temporary_unlocks")
            ),
        )


@dataclass
class DailyGoalEntry:
    """Persistent task, target and aggregate state for one CST date."""

    date_str: str            # ISO date "2026-07-14"
    target_minutes: int = 0  # Legacy total-focus target.
    achieved_minutes: int = 0
    sessions_completed: int = 0
    sessions_terminated: int = 0
    daily_goal_title: str = ""
    daily_goal_status: str = "todo"
    daily_goal_tasks: list[dict] = field(default_factory=list)
    targets: DailyGoalTargets = field(default_factory=DailyGoalTargets)

    def to_dict(self) -> dict:
        return {
            "date_str": self.date_str,
            "target_minutes": self.target_minutes,
            "achieved_minutes": self.achieved_minutes,
            "sessions_completed": self.sessions_completed,
            "sessions_terminated": self.sessions_terminated,
            "daily_goal_title": self.daily_goal_title,
            "daily_goal_status": self.daily_goal_status,
            "daily_goal_tasks": [dict(task) for task in self.daily_goal_tasks],
            "targets": self.targets.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DailyGoalEntry":
        if not isinstance(data, dict):
            data = {}
        targets = DailyGoalTargets.from_dict(data.get("targets", {}))
        # Migrate the old opt-in single duration goal only when the persisted
        # record explicitly marked it as enabled.
        if (
            targets.total_focus_minutes is None
            and bool(data.get("daily_goal_enabled", False))
        ):
            targets.total_focus_minutes = _optional_non_negative_int(
                data.get("target_minutes")
            )
        tasks = data.get("daily_goal_tasks", [])
        if not isinstance(tasks, list):
            tasks = []
        return cls(
            date_str=str(data.get("date_str", "")),
            target_minutes=_non_negative_int(data.get("target_minutes")),
            achieved_minutes=_non_negative_int(data.get("achieved_minutes")),
            sessions_completed=_non_negative_int(data.get("sessions_completed")),
            sessions_terminated=_non_negative_int(data.get("sessions_terminated")),
            daily_goal_title=str(data.get("daily_goal_title", "")),
            daily_goal_status=str(data.get("daily_goal_status", "todo")),
            daily_goal_tasks=[
                dict(task) for task in tasks if isinstance(task, dict)
            ],
            targets=targets,
        )


@dataclass
class DailyActivityEntry:
    """Foreground application usage accumulated while Focus Capsule runs."""

    date_str: str
    app_usage_seconds: dict[str, int] = field(default_factory=dict)
    app_display_names: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "date_str": self.date_str,
            "app_usage_seconds": {
                str(key).strip().casefold(): max(0, int(value))
                for key, value in self.app_usage_seconds.items()
                if str(key).strip()
            },
            "app_display_names": {
                str(key).strip().casefold(): str(value).strip()
                for key, value in self.app_display_names.items()
                if str(key).strip() and str(value).strip()
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DailyActivityEntry":
        if not isinstance(data, dict):
            data = {}
        raw_usage = data.get("app_usage_seconds", {})
        usage: dict[str, int] = {}
        if isinstance(raw_usage, dict):
            for process, seconds in raw_usage.items():
                key = str(process).strip().casefold()
                try:
                    value = max(0, int(seconds))
                except (TypeError, ValueError):
                    continue
                if key:
                    usage[key] = value
        raw_names = data.get("app_display_names", {})
        names = (
            {
                str(process).strip().casefold(): str(name).strip()
                for process, name in raw_names.items()
                if str(process).strip() and str(name).strip()
            }
            if isinstance(raw_names, dict)
            else {}
        )
        return cls(
            date_str=str(data.get("date_str", "")),
            app_usage_seconds=usage,
            app_display_names=names,
        )


# ── AI daily report ──────────────────────────────────────────

@dataclass
class DailyReport:
    """AI-generated daily summary stored per CST date."""
    date_str: str
    summary: str = ""
    highlights: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    total_focus_minutes: int = 0
    total_sessions: int = 0
    completion_rate: float = 0.0
    top_distractions: list[str] = field(default_factory=list)
    generated_at: str = ""
    source: str = "local"   # "ai" or "local"

    def to_dict(self) -> dict:
        return {
            "date_str": self.date_str,
            "summary": self.summary,
            "highlights": self.highlights,
            "suggestions": self.suggestions,
            "total_focus_minutes": self.total_focus_minutes,
            "total_sessions": self.total_sessions,
            "completion_rate": self.completion_rate,
            "top_distractions": self.top_distractions,
            "generated_at": self.generated_at,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DailyReport":
        return cls(
            date_str=str(data.get("date_str", "")),
            summary=str(data.get("summary", "")),
            highlights=list(data.get("highlights", [])),
            suggestions=list(data.get("suggestions", [])),
            total_focus_minutes=int(data.get("total_focus_minutes", 0)),
            total_sessions=int(data.get("total_sessions", 0)),
            completion_rate=float(data.get("completion_rate", 0.0)),
            top_distractions=list(data.get("top_distractions", [])),
            generated_at=str(data.get("generated_at", "")),
            source=str(data.get("source", "local")),
        )


# ── Precision Agent OS (daily-goal-page) models ────────────────


class GoalStatus(str, Enum):
    """Lifecycle of a daily goal."""

    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    FAILED = "failed"


@dataclass
class TaskItem:
    """A single task within a daily goal."""

    title: str
    priority: str = "medium"  # low | medium | high
    status: GoalStatus = GoalStatus.TODO
    estimated_minutes: int = 0
    actual_minutes: int = 0


@dataclass
class DailyGoal:
    """A daily goal with title, tasks, and execution metadata."""

    date: str
    title: str
    tasks: list[TaskItem] = field(default_factory=list)
    status: GoalStatus = GoalStatus.TODO
    created_at: str = ""
    completed_at: str = ""

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.tasks:
            self.tasks = []

    def to_dict(self) -> dict:
        return {
            "date": self.date,
            "title": self.title,
            "tasks": [
                {
                    "title": t.title,
                    "priority": t.priority,
                    "status": t.status.value if isinstance(t.status, GoalStatus) else t.status,
                    "estimated_minutes": t.estimated_minutes,
                    "actual_minutes": t.actual_minutes,
                }
                for t in self.tasks
            ],
            "status": self.status.value if isinstance(self.status, GoalStatus) else self.status,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DailyGoal":
        tasks_data = data.get("tasks", [])
        tasks = [
            TaskItem(
                title=str(t.get("title", "")),
                priority=str(t.get("priority", "medium")),
                status=GoalStatus(t.get("status", "todo"))
                if isinstance(t.get("status"), str)
                else GoalStatus.TODO,
                estimated_minutes=int(t.get("estimated_minutes", 0)),
                actual_minutes=int(t.get("actual_minutes", 0)),
            )
            for t in tasks_data
        ]
        status_raw = data.get("status", "todo")
        try:
            status = GoalStatus(status_raw)
        except ValueError:
            status = GoalStatus.TODO
        return cls(
            date=str(data.get("date", "")),
            title=str(data.get("title", "")),
            tasks=tasks,
            status=status,
            created_at=str(data.get("created_at", "")),
            completed_at=str(data.get("completed_at", "")),
        )
