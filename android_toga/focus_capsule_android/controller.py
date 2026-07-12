"""Android-compatible session controller.

Replaces the PyQt-based SessionController with an async-compatible version
that works with Toga's event loop instead of QTimer/pyqtSignal.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Optional

from focus_capsule_android.models import (
    DistractionEntry,
    FocusConfig,
    SessionRecord,
    SessionStatus,
)


@dataclass
class SessionUpdate:
    """Snapshot of session state."""
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


class SessionController:
    """Manages the focus session lifecycle on Android.
    
    Unlike the desktop version, this doesn't monitor foreground apps.
    Instead, it relies on manual app selection or UsageStats API (opt-in).
    """
    
    def __init__(self, history_service, app=None):
        self._history = history_service
        self._app = app
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
        self._terminated = False
        self._timer_task: Optional[asyncio.Task] = None
        self._update_callbacks: list = []
        self._complete_callbacks: list = []
    
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
    def is_active(self):
        return self._status in {
            SessionStatus.RUNNING,
            SessionStatus.BREAK,
            SessionStatus.LOCKED,
        }
    
    def on_update(self, callback: Callable):
        """Register a callback for session updates."""
        self._update_callbacks.append(callback)
    
    def on_complete(self, callback: Callable):
        """Register a callback for session completion."""
        self._complete_callbacks.append(callback)
    
    def start_session(self, config: FocusConfig):
        """Start a new focus session."""
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
        
        # Start async timer
        if self._timer_task and not self._timer_task.done():
            self._timer_task.cancel()
        self._timer_task = asyncio.create_task(self._timer_loop())
        
        self._emit_update()
    
    async def _timer_loop(self):
        """Async timer loop that replaces QTimer."""
        try:
            while self._status in {SessionStatus.RUNNING, SessionStatus.LOCKED}:
                await asyncio.sleep(1)
                self._elapsed += 1
                
                if self._elapsed >= self._total_seconds:
                    await self.complete_session()
                    break
                else:
                    self._emit_update()
        except asyncio.CancelledError:
            pass
    
    def _emit_update(self):
        """Notify all update callbacks."""
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
        
        for callback in self._update_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(update))
                else:
                    callback(update)
            except Exception as e:
                print(f"Error in update callback: {e}")
    
    def handle_escape(self):
        """Handle user pressing escape (or tapping break button on Android)."""
        if self._terminated or self._status not in {
            SessionStatus.RUNNING,
            SessionStatus.LOCKED,
        } or self._esc_remaining <= 0:
            return
        
        self._esc_remaining -= 1
        self._esc_used += 1
        self._status = SessionStatus.BREAK
        self._break_remaining = (
            self._config.esc_break_minutes if self._config else 3
        ) * 60
        
        # Start break timer
        asyncio.create_task(self._break_timer_loop())
        
        self._emit_update()
    
    async def _break_timer_loop(self):
        """Async break timer loop."""
        try:
            while self._break_remaining > 0 and self._status == SessionStatus.BREAK:
                await asyncio.sleep(1)
                self._break_remaining -= 1
                self._emit_update()
            
            if self._status == SessionStatus.BREAK:
                self._status = SessionStatus.RUNNING
                self._break_remaining = 0
                self._emit_update()
        except asyncio.CancelledError:
            pass
    
    def on_distraction_detected(self, app_name: str):
        """Called when a potential distraction is detected.
        
        On Android, this is triggered manually by the user or via
        UsageStats API if permission is granted.
        """
        if self._terminated or self._status not in {
            SessionStatus.RUNNING,
            SessionStatus.LOCKED,
        }:
            return
        
        if not self._config:
            return
        
        process = (app_name or "").strip().casefold()
        if not process:
            return
        
        allowed = any(
            p.strip().casefold() == process 
            for p in self._config.whitelist
        )
        
        if allowed:
            if self._status == SessionStatus.LOCKED:
                self._status = SessionStatus.RUNNING
                self._emit_update()
            return
        
        self._distractions += 1
        self._distraction_apps[process] = self._distraction_apps.get(process, 0) + 1
        self._distraction_events.append(DistractionEntry(
            process_name=process,
            occurred_at=datetime.now().astimezone().isoformat(),
        ))
        
        mode = self._config.mode
        if mode in {"Deep", "Standard"} and self._config.whitelist:
            self._status = SessionStatus.LOCKED
            self._show_lock_dialog(app_name)
        
        self._emit_update()
    
    def _show_lock_dialog(self, blocking_app: str):
        """Show an in-app lock dialog (Android equivalent of overlay)."""
        if self._app:
            self._app.show_modal_dialog(
                title="Focus Mode Active",
                message=f"Switching to {blocking_app} is not allowed during focus time."
            )
    
    def complete_session(self):
        """Complete the current session successfully."""
        if self._terminated or self._status not in {
            SessionStatus.RUNNING,
            SessionStatus.LOCKED,
        }:
            return
        
        self._status = SessionStatus.COMPLETED
        if self._timer_task and not self._timer_task.done():
            self._timer_task.cancel()
        
        record = self._save_record()
        
        for callback in self._complete_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(record))
                else:
                    callback(record)
            except Exception as e:
                print(f"Error in complete callback: {e}")
    
    def terminate(self):
        """Terminate the current session."""
        if not self.is_active:
            return
        
        self._terminated = True
        self._status = SessionStatus.TERMINATED
        if self._timer_task and not self._timer_task.done():
            self._timer_task.cancel()
        
        record = self._save_record()
        
        for callback in self._complete_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(record))
                else:
                    callback(record)
            except Exception as e:
                print(f"Error in terminate callback: {e}")
    
    def _save_record(self) -> SessionRecord:
        """Save the session record."""
        record = self._get_record()
        self._history.save_record(record)
        return record
    
    def _get_record(self) -> SessionRecord:
        """Create a session record from current state."""
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
            distractions=[
                {"process_name": e.process_name, "occurred_at": e.occurred_at}
                for e in self._distraction_events
            ],
            goal=self._config.goal if self._config else None,
            outcome=outcome,
        )
