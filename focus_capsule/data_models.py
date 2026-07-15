"""App category, daily goal, AI daily report and trend models.

All new data structures introduced in v2.1 live here to preserve backward
compatibility with the original :mod:`focus_capsule.models`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone, timedelta
from typing import Optional

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

@dataclass
class DailyGoalEntry:
    """Tracks the daily focus goal for a specific CST date."""
    date_str: str            # ISO date "2026-07-14"
    target_minutes: int = 120
    achieved_minutes: int = 0
    sessions_completed: int = 0
    sessions_terminated: int = 0

    def to_dict(self) -> dict:
        return {
            "date_str": self.date_str,
            "target_minutes": self.target_minutes,
            "achieved_minutes": self.achieved_minutes,
            "sessions_completed": self.sessions_completed,
            "sessions_terminated": self.sessions_terminated,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DailyGoalEntry":
        return cls(
            date_str=str(data.get("date_str", "")),
            target_minutes=int(data.get("target_minutes", 120)),
            achieved_minutes=int(data.get("achieved_minutes", 0)),
            sessions_completed=int(data.get("sessions_completed", 0)),
            sessions_terminated=int(data.get("sessions_terminated", 0)),
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
