"""Android-compatible models for Focus Capsule.

These are simplified versions of the desktop models that don't depend
on PyQt or platform-specific features.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class IntensityMode(Enum):
    LIGHT = "Light"
    STANDARD = "Standard"
    DEEP = "Deep"


@dataclass
class ScheduleRule:
    """Time-based app-locking rule for Android."""
    start_hour: int = 0
    start_minute: int = 0
    end_hour: int = 0
    end_minute: int = 0
    whitelisted_apps: list[str] = field(default_factory=list)
    mode: str = "Deep"
    enabled: bool = True
    label: str = ""
    
    def __post_init__(self) -> None:
        for name, minimum, maximum in (
            ("start_hour", 0, 23),
            ("start_minute", 0, 59),
            ("end_hour", 0, 23),
            ("end_minute", 0, 59),
        ):
            try:
                value = int(getattr(self, name))
            except (TypeError, ValueError) as error:
                raise ValueError(f"Invalid schedule value: {name}") from error
            if not minimum <= value <= maximum:
                setattr(self, name, value)
        
        self.whitelisted_apps = list(dict.fromkeys(
            str(app).strip().casefold()
            for app in self.whitelisted_apps
            if str(app).strip()
        ))
        self.mode = self.mode if self.mode in {"Light", "Standard", "Deep"} else "Deep"
        self.label = str(self.label or "").strip()
    
    def to_dict(self) -> dict:
        return {
            "start_hour": self.start_hour,
            "start_minute": self.start_minute,
            "end_hour": self.end_hour,
            "end_minute": self.end_minute,
            "whitelisted_apps": list(self.whitelisted_apps),
            "mode": self.mode,
            "enabled": self.enabled,
            "label": self.label,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ScheduleRule":
        if not isinstance(data, dict):
            raise TypeError("Schedule rule must be an object")
        
        enabled_value = data.get("enabled", True)
        if isinstance(enabled_value, str):
            normalized = enabled_value.strip().casefold()
            if normalized in {"true", "1", "yes", "on"}:
                enabled = True
            elif normalized in {"false", "0", "no", "off", ""}:
                enabled = False
            else:
                raise ValueError("Invalid enabled value")
        else:
            enabled = bool(enabled_value)
        
        return cls(
            start_hour=int(data.get("start_hour", 0)),
            start_minute=int(data.get("start_minute", 0)),
            end_hour=int(data.get("end_hour", 0)),
            end_minute=int(data.get("end_minute", 0)),
            whitelisted_apps=data.get("whitelisted_apps", []),
            mode=str(data.get("mode", "Deep")),
            enabled=enabled,
            label=str(data.get("label", "") or ""),
        )


class SessionStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
    BREAK = "break"
    LOCKED = "locked"  # Android equivalent of OVERLAY
    COMPLETED = "completed"
    TERMINATED = "terminated"


@dataclass
class FocusConfig:
    """Focus session configuration."""
    whitelist: list[str] = field(default_factory=list)
    duration_minutes: int = 25
    mode: str = "Standard"
    max_esc: int = 2
    esc_break_minutes: int = 3
    goal: str | None = None
    custom_apps: list[str] = field(default_factory=list)


@dataclass
class DistractionEntry:
    """Record of a distraction event."""
    process_name: str
    window_title: str | None = None
    occurred_at: str = ""


@dataclass
class SessionRecord:
    """Completed or terminated session record."""
    started_at: str
    ended_at: str
    duration_minutes: int
    actual_focus_seconds: int
    distraction_count: int
    esc_used: int
    mode: str
    whitelisted_apps: list[str]
    distractions: list[dict] = field(default_factory=list)
    goal: str | None = None
    outcome: str = "completed"
