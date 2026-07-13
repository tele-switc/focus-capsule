from dataclasses import dataclass
from datetime import datetime

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from focus_capsule.models import DistractionEntry, FocusConfig, SessionRecord, SessionStatus
from focus_capsule.monitor import WindowMonitorThread


@dataclass
class SessionUpdate:
    status: SessionStatus
    elapsed: int
    total: int
    esc_remaining: int
    esc_used: int
    distraction_count: int
    mode: str
    current_app: str
    break_remaining: int

    def to_dict(self):
        return {
            'status': self.status.value,
            'elapsed': self.elapsed,
            'total': self.total,
            'esc_remaining': self.esc_remaining,
            'esc_used': self.esc_used,
            'distraction_count': self.distraction_count,
            'mode': self.mode,
            'current_app': self.current_app,
            'break_remaining': self.break_remaining
        }


class SessionController(QObject):
    """Manages the focus session lifecycle."""

    update_requested = pyqtSignal(object)  # SessionUpdate
    session_completed = pyqtSignal(object)  # SessionRecord
    tray_update = pyqtSignal(bool)

    def __init__(self, history_service, overlay_service, parent=None):
        super().__init__(parent)
        self._history = history_service
        self._overlay = overlay_service
        self._config: FocusConfig | None = None
        self._total_seconds = 0
        self._elapsed = 0
        self._esc_remaining = 0
        self._esc_used = 0
        self._distractions = 0
        self._distraction_apps: dict[str, int] = {}
        self._distraction_events: list[DistractionEntry] = []
        self._status = SessionStatus.IDLE
        self._break_remaining = 0
        self._started_at: datetime | None = None
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._on_timer_tick)
        self._terminated = False

    @property
    def status(self):
        return self._status

    @property
    def elapsed(self):
        return self._elapsed

    @property
    def total(self):
        return self._total_seconds

    @property
    def esc_remaining(self):
        return self._esc_remaining

    @property
    def esc_used(self):
        return self._esc_used

    @property
    def distraction_count(self):
        return self._distractions

    @property
    def break_remaining(self):
        return self._break_remaining

    @property
    def is_running(self):
        """Compatibility alias used by the existing main window."""
        return self.is_active

    @property
    def is_active(self):
        return self._status in {
            SessionStatus.RUNNING,
            SessionStatus.BREAK,
            SessionStatus.OVERLAY,
        }

    def start_session(self, config: FocusConfig):
        try:
            duration_minutes = int(config.duration_minutes)
        except (TypeError, ValueError):
            duration_minutes = 25
        config.duration_minutes = max(1, duration_minutes)
        self._config = config
        self._total_seconds = config.duration_minutes * 60
        self._elapsed = 0
        self._esc_remaining = config.max_esc
        self._esc_used = 0
        self._distractions = 0
        self._distraction_apps.clear()
        self._distraction_events.clear()
        self._status = SessionStatus.RUNNING
        self._break_remaining = 0
        self._started_at = datetime.now().astimezone()
        self._terminated = False
        self._timer.start()
        self.tray_update.emit(True)
        self._emit_update()

    def _on_timer_tick(self):
        if self._status in {SessionStatus.RUNNING, SessionStatus.OVERLAY}:
            self._elapsed += 1
            if self._elapsed >= self._total_seconds:
                self.complete_session()
            else:
                self._emit_update()

    def _emit_update(self):
        update = SessionUpdate(
            status=self._status,
            elapsed=self._elapsed,
            total=self._total_seconds,
            esc_remaining=self._esc_remaining,
            esc_used=self._esc_used,
            distraction_count=self._distractions,
            mode=self._config.mode if self._config else "Standard",
            current_app=(
                self._config.whitelist[0]
                if self._config and self._config.whitelist
                else ""
            ),
            break_remaining=self._break_remaining
        )
        self.update_requested.emit(update)

    def handle_escape(self):
        if (
            self._terminated
            or self._status not in {SessionStatus.RUNNING, SessionStatus.OVERLAY}
            or self._esc_remaining <= 0
        ):
            return

        self._esc_remaining -= 1
        self._esc_used += 1
        self._status = SessionStatus.BREAK
        self._break_remaining = (self._config.esc_break_minutes if self._config else 3) * 60
        self._overlay.hide_overlay()

        self._overlay.show_break_window(
            self._config.esc_break_minutes if self._config else 3,
            on_tick=self._on_break_tick,
            on_end=self._on_break_end
        )
        self._emit_update()

    def _on_break_tick(self, seconds_remaining: int):
        if self._terminated or self._status != SessionStatus.BREAK:
            return
        try:
            remaining = max(0, int(seconds_remaining))
        except (TypeError, ValueError):
            return
        self._break_remaining = remaining
        self._emit_update()

    def _on_break_end(self):
        if (
            self._terminated
            or self._status != SessionStatus.BREAK
            or self._break_remaining > 0
        ):
            return
        self._status = SessionStatus.RUNNING
        self._break_remaining = 0
        self._overlay.hide_break_window()
        self._emit_update()

    def on_overlay_dismissed(self, window_monitor: WindowMonitorThread):
        if self._terminated or not self.is_active or self._status == SessionStatus.BREAK:
            return
        current = (window_monitor._last_process or "").strip().casefold()
        if self._config and current:
            allowed = any(p.strip().casefold() == current for p in self._config.whitelist)
            if not allowed:
                self._status = SessionStatus.OVERLAY
                self._overlay.show_overlay(
                    self._config.whitelist[0],
                    return_seconds=5 if self._config.mode == "Deep" else 3
                )
            else:
                self._status = SessionStatus.RUNNING
                self._overlay.hide_overlay()
            self._emit_update()

    def on_foreground_change(self, process_name: str, window_title: str):
        if self._terminated or self._status not in {
            SessionStatus.RUNNING,
            SessionStatus.OVERLAY,
        }:
            return
        if not self._config:
            return

        process = (process_name or "").strip().casefold()
        if not process:
            return

        allowed = any(p.strip().casefold() == process for p in self._config.whitelist)
        if allowed:
            if self._status == SessionStatus.OVERLAY:
                self._status = SessionStatus.RUNNING
                self._overlay.hide_overlay()
                self._emit_update()
            return

        self._distractions += 1
        self._distraction_apps[process] = self._distraction_apps.get(process, 0) + 1
        self._distraction_events.append(
            DistractionEntry(
                process_name=process,
                window_title=(window_title or "").strip() or None,
                occurred_at=datetime.now().astimezone().isoformat(),
            )
        )

        mode = self._config.mode
        if mode in {"Deep", "Standard"} and self._config.whitelist:
            self._status = SessionStatus.OVERLAY
            self._overlay.show_overlay(
                self._config.whitelist[0],
                return_seconds=5 if mode == "Deep" else 3
            )
        self._emit_update()

    def complete_session(self):
        if self._terminated or self._status not in {
            SessionStatus.RUNNING,
            SessionStatus.OVERLAY,
        }:
            return
        self._status = SessionStatus.COMPLETED
        self._timer.stop()
        self._overlay.hide_overlay()
        record = self._save_record()
        self.session_completed.emit(record)
        self.tray_update.emit(False)

    def terminate(self):
        if not self.is_active:
            return
        self._terminated = True
        self._status = SessionStatus.TERMINATED
        self._timer.stop()
        self._overlay.hide_overlay()
        self._overlay.hide_break_window()
        record = self._save_record()
        self.session_completed.emit(record)
        self.tray_update.emit(False)

    def _save_record(self):
        record = self._get_record()
        self._history.save_record(record)
        return record

    def _get_record(self) -> SessionRecord:
        now = datetime.now().astimezone()
        started = self._started_at or now
        outcome = (
            "terminated"
            if self._status == SessionStatus.TERMINATED
            else "completed"
            if self._status == SessionStatus.COMPLETED
            else self._status.value
        )
        return SessionRecord(
            started_at=started.isoformat(),
            ended_at=now.isoformat(),
            duration_minutes=self._config.duration_minutes if self._config else 0,
            actual_focus_seconds=self._elapsed,
            distraction_count=self._distractions,
            esc_used=self._esc_used,
            mode=self._config.mode if self._config else "Standard",
            whitelisted_apps=list(self._config.whitelist) if self._config else [],
            distractions=[event.__dict__.copy() for event in self._distraction_events],
            goal=self._config.goal if self._config else None,
            outcome=outcome,
        )
