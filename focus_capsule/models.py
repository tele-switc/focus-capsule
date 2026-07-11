from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional, Dict


class IntensityMode(Enum):
    LIGHT = "Light"
    STANDARD = "Standard"
    DEEP = "Deep"


class SessionStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
    BREAK = "break"
    OVERLAY = "overlay"
    COMPLETED = "completed"
    TERMINATED = "terminated"


@dataclass
class FocusConfig:
    whitelist: List[str] = field(default_factory=list)
    duration_minutes: int = 25
    mode: str = "Standard"
    max_esc: int = 2
    esc_break_minutes: int = 3
    goal: Optional[str] = None
    custom_apps: List[str] = field(default_factory=list)


@dataclass
class DistractionEntry:
    process_name: str
    window_title: Optional[str]
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
    whitelisted_apps: List[str]
    distractions: List[Dict] = field(default_factory=list)
    goal: Optional[str] = None
    outcome: str = "completed"
