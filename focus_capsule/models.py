from dataclasses import dataclass, field
from enum import Enum

from focus_capsule.strict_lock import StrictPolicy

VALID_STRICT_LEVELS = {"off", "cooldown", "phrase", "passcode"}


def _normalise_strict_fields(container) -> None:
    """把严格模式字段收敛到合法范围（就地修改 dataclass 实例）。"""

    level = str(getattr(container, "strict_level", "off") or "off")
    if level not in VALID_STRICT_LEVELS:
        level = "off"
    container.strict_level = level
    try:
        minutes = int(getattr(container, "strict_cooldown_minutes", 5) or 5)
    except (TypeError, ValueError):
        minutes = 5
    container.strict_cooldown_minutes = max(1, min(240, minutes))
    try:
        quota = int(getattr(container, "snooze_quota", 2) or 0)
    except (TypeError, ValueError):
        quota = 2
    container.snooze_quota = max(0, min(5, quota))
    container.strict_passcode_hash = str(getattr(container, "strict_passcode_hash", "") or "")


@dataclass
class IntensityMode(Enum):
    LIGHT = "Light"
    STANDARD = "Standard"
    DEEP = "Deep"


@dataclass
class ScheduleRule:
    """A time-based app-locking rule following the local timezone.

    The rule activates every day at *start_hour:start_minute* and releases at
    *end_hour:end_minute*. While active, only *whitelisted_apps* are permitted
    and the overlay protection follows *mode* (Light / Standard / Deep).
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
    strict_level: str = "off"
    strict_cooldown_minutes: int = 5
    strict_passcode_hash: str = ""
    snooze_quota: int = 2

    def strict_policy(self) -> StrictPolicy:
        return StrictPolicy(
            level=self.strict_level,
            cooldown_minutes=self.strict_cooldown_minutes,
            passcode_hash=self.strict_passcode_hash,
        )

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
        _normalise_strict_fields(self)

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
            "strict_level": self.strict_level,
            "strict_cooldown_minutes": self.strict_cooldown_minutes,
            "strict_passcode_hash": self.strict_passcode_hash,
            "snooze_quota": self.snooze_quota,
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
            strict_level=str(data.get("strict_level", "off") or "off"),
            strict_cooldown_minutes=data.get("strict_cooldown_minutes", 5),
            strict_passcode_hash=str(data.get("strict_passcode_hash", "") or ""),
            snooze_quota=data.get("snooze_quota", 2),
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
    strict_level: str = "off"
    strict_cooldown_minutes: int = 5
    strict_passcode_hash: str = ""
    phrase_length: int = 8
    snooze_quota: int = 2

    def __post_init__(self) -> None:
        _normalise_strict_fields(self)

    def strict_policy(self) -> StrictPolicy:
        return StrictPolicy(
            level=self.strict_level,
            cooldown_minutes=self.strict_cooldown_minutes,
            phrase_length=self.phrase_length,
            passcode_hash=self.strict_passcode_hash,
        )


@dataclass
class DistractionEntry:
    process_name: str
    window_title: str | None
    occurred_at: str
    note: str | None = None


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
    esc_allowed: int = 0
    snooze_used: int = 0
    suppressed_count: int = 0
    broke: bool = False
    strict_level: str = "off"
