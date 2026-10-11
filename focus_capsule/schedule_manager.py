"""Schedule-based app-locking engine.

The scheduler operates in China Standard Time (CST, UTC+8) regardless of the
host machine's local timezone. Every second it checks whether any active
:class:`~focus_capsule.models.ScheduleRule` applies to the current moment and,
when it does, enforces the whitelist using the same overlay mechanism as a
Deep-mode focus session. The scheduler runs in the background — there is no
visible session window — but the overlay and tray notifications keep the user
informed.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from focus_capsule.models import ScheduleRule
from focus_capsule.process_matching import ProcessMatcher

CST = timezone(timedelta(hours=8), name="CST")


def china_now() -> datetime:
    """Return the current time in China Standard Time (UTC+8)."""
    return datetime.now(CST)


def _as_cst(value: datetime) -> datetime:
    """Normalize aware datetimes to CST and interpret naive values as CST."""
    if value.tzinfo is None:
        return value.replace(tzinfo=CST)
    return value.astimezone(CST)


def _now_minutes(utc_now: datetime | None = None) -> int:
    """Return the current time-of-day in minutes (0..1439) in CST."""
    now = _as_cst(utc_now) if utc_now is not None else china_now()
    return now.hour * 60 + now.minute


def _rule_span_minutes(rule: ScheduleRule) -> tuple[int, int]:
    start = rule.start_hour * 60 + rule.start_minute
    end = rule.end_hour * 60 + rule.end_minute
    return start, end


def _rule_is_active(rule: ScheduleRule, now: datetime | None = None) -> bool:
    """Return True when *rule* covers the current CST time-of-day.

    Supports both same-day ranges (start < end) and overnight ranges that wrap
    past midnight (start >= end, e.g. 23:00→07:00).
    """
    if not rule.enabled:
        return False
    current = _now_minutes(now)
    start, end = _rule_span_minutes(rule)
    if start == end:
        return False
    if start < end:
        return start <= current < end
    return current >= start or current < end


def _seconds_until_next_boundary(rule: ScheduleRule, now: datetime | None = None) -> int:
    """Seconds remaining until the active rule's end boundary (or its start
    if not yet active). A return of 0 means the rule is not active.
    """
    now_cst = _as_cst(now) if now is not None else china_now()
    current = _now_minutes(now_cst)
    start, end = _rule_span_minutes(rule)
    if not _rule_is_active(rule, now_cst):
        return 0
    if start < end:
        delta_minutes = end - current
    else:
        if current >= start:
            delta_minutes = (24 * 60 - current) + end
        else:
            delta_minutes = end - current
    remaining_seconds = delta_minutes * 60 - now_cst.second
    return max(0, remaining_seconds)


class ScheduleManager(QObject):
    """Background timer that activates / releases schedule rules in CST.

    Emits
    -----
    rule_activated(rule: ScheduleRule)
        Fired the moment a rule becomes active (at start time). The controller
        should begin enforcing the whitelist.
    rule_released(rule: ScheduleRule)
        Fired the moment a rule's time window ends. The controller should
        release the whitelist enforcement.
    tick(active_rule: Optional[ScheduleRule], seconds_left: int)
        Once per second while a rule is active, carrying the remaining seconds
        until the window closes. ``seconds_left`` is 0 when no rule is active.
    """

    rule_activated = pyqtSignal(object)   # ScheduleRule
    rule_released = pyqtSignal(object)     # ScheduleRule
    tick = pyqtSignal(object, int)         # (ScheduleRule | None, seconds_left)
    rules_changed = pyqtSignal()           # list contents changed

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._rules: list[ScheduleRule] = []
        self._active_rule: ScheduleRule | None = None
        self._process_matcher: ProcessMatcher | None = None
        self._process_matcher_key: tuple[tuple[str, ...], tuple[tuple[str, str], ...]] | None = None
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._on_timer_tick)
        # Rules whose enforcement the user manually overroade; their hash
        # identifies the (start, end) window so we don't re-trigger after the
        # user explicitly ended a schedule session.
        self._suppressed_keys: set[tuple[int, int, int, int]] = set()

    @property
    def rules(self) -> list[ScheduleRule]:
        return list(self._rules)

    @property
    def active_rule(self) -> ScheduleRule | None:
        return self._active_rule

    @property
    def is_active(self) -> bool:
        return self._active_rule is not None

    def set_rules(self, rules: list[ScheduleRule]) -> None:
        """Replace all rules. If a new rule covers the current time it is
        activated immediately, otherwise the previous active rule is released.
        """
        old_active = self._active_rule
        self._rules = list(rules)
        self._suppressed_keys.clear()
        new_active = None
        for rule in self._rules:
            if _rule_is_active(rule):
                new_active = rule
                break
        self._active_rule = new_active
        if old_active != new_active:
            if old_active is not None:
                self.rule_released.emit(old_active)
            if new_active is not None:
                self.rule_activated.emit(new_active)
        self.rules_changed.emit()

    def add_rule(self, rule: ScheduleRule) -> None:
        self._rules.append(rule)
        if _rule_is_active(rule) and self._active_rule is None:
            self._active_rule = rule
            self.rule_activated.emit(rule)
        self.rules_changed.emit()

    def update_rule(self, index: int, rule: ScheduleRule) -> None:
        if 0 <= index < len(self._rules):
            old_active = self._active_rule
            self._rules[index] = rule
            self._recalculate_active(old_active)
        self.rules_changed.emit()

    def remove_rule(self, index: int) -> None:
        if 0 <= index < len(self._rules):
            removed = self._rules.pop(index)
            if removed is self._active_rule:
                old_active = self._active_rule
                self._active_rule = None
                self.rule_released.emit(old_active)
                for rule in self._rules:
                    if _rule_is_active(rule):
                        self._active_rule = rule
                        self.rule_activated.emit(rule)
                        break
            self.rules_changed.emit()

    def _recalculate_active(self, old_active: ScheduleRule | None) -> None:
        new_active: ScheduleRule | None = None
        for rule in self._rules:
            if _rule_is_active(rule):
                new_active = rule
                break
        if new_active != old_active:
            if old_active is not None:
                self.rule_released.emit(old_active)
            self._active_rule = new_active
            if new_active is not None:
                self.rule_activated.emit(new_active)
        else:
            # Keep the active object tied to the current rules list even when a
            # semantically identical replacement was supplied.
            self._active_rule = new_active

    def start(self) -> None:
        """Start the background ticker."""
        if not self._timer.isActive():
            self._on_timer_tick()
            self._timer.start()

    def stop(self) -> None:
        self._timer.stop()
        if self._active_rule:
            old = self._active_rule
            self._active_rule = None
            self.rule_released.emit(old)

    def _on_timer_tick(self) -> None:
        now = china_now()
        if self._active_rule:
            if _rule_is_active(self._active_rule, now):
                seconds_left = _seconds_until_next_boundary(self._active_rule, now)
                self.tick.emit(self._active_rule, seconds_left)
                return
            old = self._active_rule
            self._active_rule = None
            # When the rule's window ends, also clear its suppression.
            self._suppressed_keys.discard(
                (old.start_hour, old.start_minute, old.end_hour, old.end_minute)
            )
            self.rule_released.emit(old)
        for rule in self._rules:
            if _rule_is_active(rule, now):
                key = (rule.start_hour, rule.start_minute, rule.end_hour, rule.end_minute)
                if key in self._suppressed_keys:
                    # User manually ended this rule's session; don't re-enforce.
                    self.tick.emit(None, 0)
                    return
                self._active_rule = rule
                self.rule_activated.emit(rule)
                seconds_left = _seconds_until_next_boundary(rule, now)
                self.tick.emit(rule, seconds_left)
                return
        self.tick.emit(None, 0)

    def suppress_active_rule(self) -> None:
        """Mark the current active rule as user-terminated so it won't
        re-enforce until the time window expires and re-enters."""
        if self._active_rule:
            r = self._active_rule
            self._suppressed_keys.add(
                (r.start_hour, r.start_minute, r.end_hour, r.end_minute)
            )
            old = self._active_rule
            self._active_rule = None
            self.rule_released.emit(old)

    def active_whitelist(self) -> list[str]:
        if self._active_rule:
            return list(self._active_rule.whitelisted_apps)
        return []

    def is_process_allowed(
        self,
        process_name: str,
        executable_path: str = "",
        process_id: int = 0,
    ) -> bool:
        if not self._active_rule:
            return True
        process = (process_name or "").strip().casefold()
        if not process:
            return True
        matcher_key = (
            tuple(
                str(item).strip().casefold()
                for item in self._active_rule.whitelisted_apps
                if str(item).strip()
            ),
            tuple(
                sorted(
                    (
                        str(name).strip().casefold(),
                        str(path).strip(),
                    )
                    for name, path in self._active_rule.allowed_app_paths.items()
                    if str(name).strip() and str(path).strip()
                )
            ),
        )
        if self._process_matcher is None or matcher_key != self._process_matcher_key:
            self._process_matcher = ProcessMatcher(matcher_key[0], dict(matcher_key[1]))
            self._process_matcher_key = matcher_key
        return self._process_matcher.is_allowed(process, executable_path, process_id)

    def rule_for_time(self, now: datetime | None = None) -> ScheduleRule | None:
        """Return the rule that would be active at the given time (or now)."""
        for rule in self._rules:
            if _rule_is_active(rule, now):
                return rule
        return None
