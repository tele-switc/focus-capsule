from dataclasses import dataclass
from datetime import datetime
import time

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from focus_capsule.models import (
    DistractionEntry,
    FocusConfig,
    SessionRecord,
    SessionStatus,
)
from focus_capsule.monitor import WindowMonitorThread
from focus_capsule.process_matching import ProcessMatcher
from focus_capsule.strict_lock import ExitGate, StrictPolicy

DISALLOWED_FOREGROUND_GRACE_MS = 1200
# 连续分心达到该次数即视为本次专注「破功」（Forest 式枯枝判定）
BROKE_DISTRACTION_THRESHOLD = 8


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
    snooze_remaining: int = 0
    suppressed_reason: str = ""
    broke: bool = False

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
            'break_remaining': self.break_remaining,
            'snooze_remaining': self.snooze_remaining,
            'suppressed_reason': self.suppressed_reason,
            'broke': self.broke,
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
        self._app_focus_seconds: dict[str, int] = {}
        self._current_focus_process = ""
        self._status = SessionStatus.IDLE
        self._break_remaining = 0
        self._started_at: datetime | None = None
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._on_timer_tick)
        self._foreground_grace_timer = QTimer(self)
        self._foreground_grace_timer.setSingleShot(True)
        self._foreground_grace_timer.setInterval(DISALLOWED_FOREGROUND_GRACE_MS)
        self._foreground_grace_timer.timeout.connect(self._enforce_pending_distraction)
        self._pending_distraction: tuple[str, str, str, int] | None = None
        self._terminated = False
        self._process_matcher = ProcessMatcher()
        self._monitor: WindowMonitorThread | None = None
        # 新增：单调钟计时、延后配额、免打扰抑制计数、破功判定、严格模式闸门
        self._mono_anchor = 0.0
        self._paused_seconds = 0.0
        self._pause_started: float | None = None
        self._snooze_used = 0
        self._suppressed_count = 0
        self._last_suppressed_reason = ""
        self._broke = False
        self.exit_gate: ExitGate | None = None
        closed_signal = getattr(self._overlay, "closed", None)
        if closed_signal is not None and hasattr(closed_signal, "connect"):
            closed_signal.connect(self._on_overlay_closed)
        snooze_signal = getattr(self._overlay, "snoozed", None)
        if snooze_signal is not None and hasattr(snooze_signal, "connect"):
            snooze_signal.connect(self._on_snoozed)
        suppress_signal = getattr(self._overlay, "suppressed", None)
        if suppress_signal is not None and hasattr(suppress_signal, "connect"):
            suppress_signal.connect(self._on_suppressed)

    def attach_monitor(self, monitor: WindowMonitorThread) -> None:
        """让控制器在覆盖层被关闭后能复查前台应用（否则关掉就没人再管了）。"""

        self._monitor = monitor

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
        self._cancel_pending_distraction()
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
        self._app_focus_seconds.clear()
        self._current_focus_process = ""
        self._status = SessionStatus.RUNNING
        self._break_remaining = 0
        self._started_at = datetime.now().astimezone()
        self._terminated = False
        self._snooze_used = 0
        self._suppressed_count = 0
        self._last_suppressed_reason = ""
        self._broke = False
        self.exit_gate = None
        self._mono_anchor = time.monotonic()
        self._paused_seconds = 0.0
        self._pause_started = None
        self._process_matcher = ProcessMatcher(
            config.whitelist,
            getattr(config, "allowed_app_paths", {}),
        )
        self._timer.start()
        self.tray_update.emit(True)
        self._emit_update()

    def _on_timer_tick(self):
        # 用单调钟推进，改系统时间或电脑睡眠都不会让会话计时造假或停住
        now_mono = time.monotonic()
        if self._status == SessionStatus.BREAK:
            if self._pause_started is None:
                self._pause_started = now_mono
        else:
            if self._pause_started is not None:
                self._paused_seconds += now_mono - self._pause_started
                self._pause_started = None
        if self._status in {SessionStatus.RUNNING, SessionStatus.OVERLAY}:
            self._elapsed = max(
                self._elapsed,
                min(
                    self._total_seconds,
                    int(now_mono - self._mono_anchor - self._paused_seconds),
                ),
            )
            if self._status == SessionStatus.RUNNING and self._current_focus_process:
                process = self._current_focus_process
                self._app_focus_seconds[process] = (
                    self._app_focus_seconds.get(process, 0) + 1
                )
            if self._elapsed >= self._total_seconds:
                self.complete_session()
            else:
                self._emit_update()

    def _on_overlay_closed(self):
        """Called when overlay window is destroyed (auto-close or user dismiss)."""
        if self._status == SessionStatus.OVERLAY:
            if self._monitor is not None:
                # 关掉弹层不等于回到正轨：立刻复查前台，仍分心就重新弹
                self.on_overlay_dismissed(self._monitor)
                return
            self._status = SessionStatus.RUNNING
            self._overlay.hide_overlay()
            self._emit_update()

    def _on_snoozed(self, minutes: int) -> None:
        self._snooze_used += 1
        self._emit_update()

    def _on_suppressed(self, reason: str) -> None:
        self._suppressed_count += 1
        self._last_suppressed_reason = reason

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
            break_remaining=self._break_remaining,
            snooze_remaining=(
                self._overlay.snooze_remaining()
                if hasattr(self._overlay, "snooze_remaining")
                else 0
            ),
            suppressed_reason=self._last_suppressed_reason,
            broke=self._broke,
        )
        self.update_requested.emit(update)

    def handle_escape(self):
        if self._terminated or self._status not in {
            SessionStatus.RUNNING,
            SessionStatus.OVERLAY,
        }:
            return
        if self._esc_remaining <= 0:
            # 配额用尽后再按「临时离开」＝主动破功：本次专注记为枯枝，且不再给休息
            self._broke = True
            self._esc_used += 1
            self._distraction_events.append(
                DistractionEntry(
                    process_name="__escape_exhausted__",
                    window_title=None,
                    occurred_at=datetime.now().astimezone().isoformat(),
                    note="逃逸配额用尽后仍选择离开",
                )
            )
            self._emit_update()
            return

        self._esc_remaining -= 1
        self._esc_used += 1
        if self._esc_remaining == 0 and self._config and self._config.max_esc:
            self._broke = True
        self._status = SessionStatus.BREAK
        self._cancel_pending_distraction()
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
            allowed = self._process_matcher.is_allowed(
                current,
                window_monitor.last_executable_path,
                window_monitor.last_pid,
            )
            if not allowed:
                self._status = SessionStatus.OVERLAY
                self._overlay.show_overlay(
                    self._config.whitelist[0],
                    return_seconds=5 if self._config.mode == "Deep" else 3,
                    allowed_apps=list(self._config.whitelist),
                    allowed_app_paths=dict(getattr(self._config, "allowed_app_paths", {})),
                )
            else:
                self._status = SessionStatus.RUNNING
                self._overlay.hide_overlay()
            self._emit_update()

    def on_foreground_change(
        self,
        process_name: str,
        window_title: str,
        executable_path: str = "",
        process_id: int = 0,
    ):
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

        allowed_system = {
            "explorer.exe",
            "explorer",
            "finder",
            "shell.exe",
            "windows.ui.shell.lightswitch.exe",
            "dock",
            "launchpad",
            "launcher",
            "startmenuexperiencehost",
            "searchhost.exe",
            "taskhostw.exe",
            "ctfmon.exe",
            "services.exe",
            "csrss.exe",
            "winlogon.exe",
            "smss.exe",
            "wininit.exe",
            "svchost.exe",
            "lsass.exe",
            "runtimebroker.exe",
            "dllhost.exe",
            "taskmgr.exe",
            "taskmgr",
            "__focus_capsule__",
        }
        if process in allowed_system:
            self._current_focus_process = ""
            self._cancel_pending_distraction()
            return

        allowed = self._process_matcher.is_allowed(
            process,
            executable_path,
            process_id,
        )
        if allowed:
            self._cancel_pending_distraction()
            self._current_focus_process = self._process_matcher.matched_app or process
            if self._status == SessionStatus.OVERLAY:
                self._status = SessionStatus.RUNNING
                self._overlay.hide_overlay()
                self._emit_update()
            return

        self._current_focus_process = ""
        self._pending_distraction = (
            process,
            (window_title or "").strip(),
            (executable_path or "").strip(),
            int(process_id or 0),
        )
        self._foreground_grace_timer.start()

    def _cancel_pending_distraction(self) -> None:
        self._foreground_grace_timer.stop()
        self._pending_distraction = None

    def _enforce_pending_distraction(self) -> None:
        pending = self._pending_distraction
        self._pending_distraction = None
        if (
            pending is None
            or self._terminated
            or self._status not in {SessionStatus.RUNNING, SessionStatus.OVERLAY}
            or not self._config
        ):
            return

        process, window_title, executable_path, process_id = pending
        # Re-check at the enforcement boundary because a verified
        # launcher/runtime alias may have been learned during the grace period.
        if self._process_matcher.is_allowed(process, executable_path, process_id):
            self._current_focus_process = self._process_matcher.matched_app or process
            return

        self._distractions += 1
        if self._distractions >= BROKE_DISTRACTION_THRESHOLD:
            self._broke = True
        self._distraction_apps[process] = self._distraction_apps.get(process, 0) + 1
        self._distraction_events.append(
            DistractionEntry(
                process_name=process,
                window_title=window_title or None,
                occurred_at=datetime.now().astimezone().isoformat(),
            )
        )

        mode = self._config.mode
        if mode in {"Deep", "Standard"} and self._config.whitelist:
            self._status = SessionStatus.OVERLAY
            strict = getattr(self._config, "strict_level", "off") != "off"
            kwargs = dict(
                return_seconds=5 if mode == "Deep" else 3,
                allowed_apps=list(self._config.whitelist),
                allowed_app_paths=dict(getattr(self._config, "allowed_app_paths", {})),
                strict=strict,
                snooze_used=self._snooze_used,
                snooze_quota=getattr(self._config, "snooze_quota", 2),
            )
            try:
                shown = self._overlay.show_overlay(
                    self._config.whitelist[0],
                    **kwargs,
                )
            except TypeError as exc:
                # Preserve compatibility with small overlay adapters that
                # implement the pre-v3 two-argument interface.
                if "allowed_apps" not in str(exc):
                    raise
                shown = self._overlay.show_overlay(
                    self._config.whitelist[0],
                    return_seconds=5 if mode == "Deep" else 3,
                )
            if shown is False:
                # 被免打扰环境抑制（全屏演示/系统专注模式）：记一笔但不打断
                if self._distraction_events:
                    self._distraction_events[-1].note = (
                        self._last_suppressed_reason or "免打扰环境，已跳过拦截"
                    )
        self._emit_update()

    def request_early_exit(self) -> ExitGate:
        """用户点「提前结束」时调用；严格模式下返回需要满足的闸门。"""

        policy = (
            self._config.strict_policy()
            if self._config is not None
            else StrictPolicy()
        )
        gate = ExitGate(policy)
        gate.begin()
        if policy.level == "phrase":
            gate.arm_phrase()
        self.exit_gate = gate
        return gate

    def can_exit(self) -> bool:
        """非严格模式恒为 True；严格模式要求冷静期走完且校验通过。"""

        if self.exit_gate is None:
            return True
        return bool(self.exit_gate.released)

    def complete_session(self):
        if self._terminated or self._status not in {
            SessionStatus.RUNNING,
            SessionStatus.OVERLAY,
        }:
            return
        self._status = SessionStatus.COMPLETED
        self._cancel_pending_distraction()
        self._timer.stop()
        self._overlay.hide_overlay()
        record = self._save_record()
        self.session_completed.emit(record)
        self.tray_update.emit(False)

    def terminate(self, force: bool = False):
        if not self.is_active:
            return
        if not force and not self.can_exit():
            # 严格模式：冷静期未结束或校验未通过，不允许结束
            return
        self._terminated = True
        self._broke = True  # 提前结束＝破功，与 Forest 的枯树一致
        self._status = SessionStatus.TERMINATED
        self._cancel_pending_distraction()
        self._timer.stop()
        self._overlay.hide_overlay()
        self._overlay.hide_break_window()
        record = self._save_record()
        self.session_completed.emit(record)
        self.tray_update.emit(False)

    def finish_scheduled_session(self):
        """Finish a schedule at its natural boundary as a completed record."""
        if not self.is_active:
            return
        self._status = SessionStatus.COMPLETED
        self._cancel_pending_distraction()
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
            source=getattr(self._config, "source", "timer") if self._config else "timer",
            schedule_label=(
                getattr(self._config, "schedule_label", "") if self._config else ""
            ),
            schedule_start=(
                getattr(self._config, "schedule_start", "") if self._config else ""
            ),
            schedule_end=(
                getattr(self._config, "schedule_end", "") if self._config else ""
            ),
            app_focus_seconds=dict(self._app_focus_seconds),
            esc_allowed=(self._config.max_esc if self._config else 0),
            snooze_used=self._snooze_used,
            suppressed_count=self._suppressed_count,
            broke=bool(self._broke),
            strict_level=(
                getattr(self._config, "strict_level", "off") if self._config else "off"
            ),
        )
