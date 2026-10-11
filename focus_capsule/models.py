from dataclasses import dataclass, field
from enum import Enum


class IntensityMode(Enum):
    LIGHT = "Light"
    STANDARD = "Standard"
    DEEP = "Deep"


@dataclass
class ScheduleRule:
    """A time-based app-locking rule following the China timezone (UTC+8).

    The rule activates every day at *start_hour:start_minute* and releases at
    *end_hour:end_minute*. While active, only *whitelisted_apps* are permitted
    and the overlay protection behaves as if a Deep-mode session is running.
    """
    start_hour: int = 0
    start_minute: int = 0
    end_hour: int = 0
    end_minute: int = 0
    whitelisted_apps: list[str] = field(default_factory=list)
    mode: str = "Deep"
    enabled: bool = True
    label: str = ""
    max_esc: int = 2
    esc_break_minutes: int = 3
    allowed_app_paths: dict[str, str] = field(default_factory=dict)

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
                raise ValueError(f"Schedule value out of range: {name}")
            setattr(self, name, value)

        if not isinstance(self.whitelisted_apps, (list, tuple, set)):
            raise ValueError("whitelisted_apps must be a sequence")
        self.whitelisted_apps = list(
            dict.fromkeys(
                str(app).strip().casefold()
                for app in self.whitelisted_apps
                if str(app).strip()
            )
        )
        self.mode = self.mode if self.mode in {"Light", "Standard", "Deep"} else "Deep"
        self.label = str(self.label or "").strip()
        if not isinstance(self.allowed_app_paths, dict):
            self.allowed_app_paths = {}
        self.allowed_app_paths = {
            str(process).strip().casefold(): str(path).strip()
            for process, path in self.allowed_app_paths.items()
            if str(process).strip() and str(path).strip()
        }
        try:
            self.max_esc = max(0, min(10, int(self.max_esc or 2)))
        except (TypeError, ValueError):
            self.max_esc = 2
        try:
            self.esc_break_minutes = max(1, min(15, int(self.esc_break_minutes or 3)))
        except (TypeError, ValueError):
            self.esc_break_minutes = 3

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
            "max_esc": self.max_esc,
            "esc_break_minutes": self.esc_break_minutes,
            "allowed_app_paths": dict(self.allowed_app_paths),
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
            max_esc=data.get("max_esc", 2),
            esc_break_minutes=data.get("esc_break_minutes", 3),
            allowed_app_paths=data.get("allowed_app_paths", {}),
        )



class SessionStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
    BREAK = "break"
    OVERLAY = "overlay"
    COMPLETED = "completed"
    TERMINATED = "terminated"


@dataclass
class FocusConfig:
    whitelist: list[str] = field(default_factory=list)
    duration_minutes: int = 25
    mode: str = "Standard"
    max_esc: int = 2
    esc_break_minutes: int = 3
    goal: str | None = None
    custom_apps: list[str] = field(default_factory=list)
    allowed_app_paths: dict[str, str] = field(default_factory=dict)
    source: str = "timer"
    schedule_label: str = ""
    schedule_start: str = ""
    schedule_end: str = ""


@dataclass
class DistractionEntry:
    process_name: str
    window_title: str | None
    occurred_at: str


@dataclass
class SessionRecord:
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
    source: str = "timer"
    schedule_label: str = ""
    schedule_start: str = ""
    schedule_end: str = ""
    app_focus_seconds: dict[str, int] = field(default_factory=dict)
