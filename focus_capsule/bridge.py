"""LifeOS local intervention bridge (opt-in, additive).

Run headlessly:
    python -m focus_capsule.bridge <intent_dir>

Speaks the same file protocol as the LifeOS FocusCapsuleAdapter:
    intent_dir/intent.json     -> {"action": "ping"|"lock"|"unlock"|"query",
                                    "apps": [...], "until": iso, "rationale": str}
    intent_dir/response.json   -> {"ok": bool, "detail": str, "level": str?,
                                    "now": iso}

Uses the REAL Focus Capsule enforcement chain: ScheduleManager +
WindowMonitorThread + OverlayService. When a non-whitelisted process is
foreground, the real overlay window is shown (the actual restriction).

Safety:
- Local only, no network.
- No arbitrary command execution from request files (only enum actions).
- Request files are consumed atomically (rename/delelete after read).
- The overlay dies with this process (crash-safe; no stale restrictions).
- Normal Focus Capsule operation is untouched: this module only runs when
  invoked explicitly as `-m focus_capsule.bridge`.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication

from focus_capsule.monitor import WindowMonitorThread
from focus_capsule.overlay import OverlayService
from focus_capsule.schedule_manager import ScheduleManager, china_now

ALLOWED_ACTIONS = {"ping", "lock", "unlock", "query"}
DEFAULT_DURATION_MINUTES = 30


class Bridge:
    def __init__(self, intent_dir: str | Path, ttl_seconds: int = 60):
        self.intent_dir = Path(intent_dir)
        self.intent_dir.mkdir(parents=True, exist_ok=True)
        self.overlay = OverlayService()
        self.manager = ScheduleManager()
        self.monitor = WindowMonitorThread()
        self.monitor.foreground_changed.connect(self._on_foreground)
        self.manager.start()
        self.monitor.start()
        self.ttl_seconds = ttl_seconds
        self._lease_timer = None

    def _on_foreground(
        self,
        process_name: str,
        _window_title: str,
        executable_path: str = "",
        process_id: int = 0,
    ) -> None:
        if process_name == "__focus_capsule__":
            return
        if not self.manager.is_active:
            return
        if not self.manager.is_process_allowed(process_name, executable_path, process_id):
            if process_name in {"explorer.exe", "shell.exe", "windows.ui.shell.lightswitch.exe"}:
                return
            rule = self.manager.active_rule
            first_app = rule.whitelisted_apps[0] if rule and rule.whitelisted_apps else process_name
            if not self.overlay._alive(self.overlay._overlay_window):
                self.overlay.show_overlay(
                    first_app,
                    return_seconds=5,
                    allowed_apps=rule.whitelisted_apps if rule else None,
                    allowed_app_paths=dict(getattr(rule, "allowed_app_paths", {})) if rule else None,
                )
        else:
            self.overlay.hide_overlay()

    def _apply_lock(self, intent: dict) -> dict:
        apps = [str(a).strip() for a in intent.get("apps", []) if str(a).strip()]
        until = intent.get("until")
        if until:
            try:
                end_ts = time.mktime(time.strptime(until[:19], "%Y-%m-%dT%H:%M:%S"))
            except ValueError:
                return {"ok": False, "detail": "bad until timestamp"}
        else:
            end_ts = time.time() + DEFAULT_DURATION_MINUTES * 60
        now_cst = china_now()
        start_min = now_cst.hour * 60 + now_cst.minute - 1  # 1 min back so it activates now
        end_min = min(24 * 60 - 1, end_ts_to_minutes(end_ts))
        from focus_capsule.models import ScheduleRule

        rule = ScheduleRule(
            start_hour=start_min // 60,
            start_minute=start_min % 60,
            end_hour=end_min // 60,
            end_minute=end_min % 60,
            whitelisted_apps=apps,
            mode="Deep",
            enabled=True,
            label="LifeOS Bridge",
            max_esc=0,
        )
        self.manager.set_rules([rule])
        self.manager.start()
        # Lease/TTL: auto-release after ttl_seconds so restrictions can never
        # outlive the bridge (crash-safe + stale-cleanup).
        from PyQt6.QtCore import QTimer as _QTimer

        if self._lease_timer is not None:
            self._lease_timer.stop()
        timer = _QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(self._apply_unlock)
        timer.start(self.ttl_seconds * 1000)
        self._lease_timer = timer
        return {
            "ok": True,
            "detail": f"locked {len(apps)} whitelisted apps (ttl={self.ttl_seconds}s)",
            "level": "L4",
            "now": china_now().isoformat(),
        }

    def _apply_unlock(self) -> dict:
        if self._lease_timer is not None:
            self._lease_timer.stop()
            self._lease_timer = None
        self.manager.stop()
        self.overlay.hide_overlay()
        return {"ok": True, "detail": "unlocked", "now": china_now().isoformat()}

    def _query(self) -> dict:
        overlay_active = bool(
            self.overlay._alive(self.overlay._overlay_window)
        )
        return {
            "ok": True,
            "detail": "active" if self.manager.is_active else "idle",
            "overlay_active": overlay_active,
            "level": "L4" if self.manager.is_active else None,
            "now": china_now().isoformat(),
        }

    def handle(self, intent: dict) -> dict:
        action = intent.get("action")
        if action not in ALLOWED_ACTIONS:
            return {"ok": False, "detail": f"unsupported action: {action}"}
        if action == "ping":
            return {"ok": True, "detail": "bridge v1 alive", "now": china_now().isoformat()}
        if action == "lock":
            return self._apply_lock(intent)
        if action == "unlock":
            return self._apply_unlock()
        return self._query()

    def poll(self) -> None:
        intent_file = self.intent_dir / "intent.json"
        if not intent_file.exists():
            return
        try:
            payload = json.loads(intent_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return
        try:
            intent_file.unlink(missing_ok=True)  # atomic-ish consume
        except OSError:
            pass
        response = self.handle(payload)
        resp_file = self.intent_dir / "response.json"
        resp_file.write_text(json.dumps(response, ensure_ascii=False), encoding="utf-8")

    def shutdown(self) -> None:
        self.manager.stop()
        self.overlay.hide_overlay()
        self.monitor.stop()


def end_ts_to_minutes(end_ts: float) -> int:
    """Convert a UTC epoch to CST minutes-of-day (0..1439)."""
    now_cst = china_now()
    delta_minutes = int((end_ts - time.time()) // 60)
    current_minutes = now_cst.hour * 60 + now_cst.minute
    return max(current_minutes + 1, min(24 * 60 - 1, current_minutes + max(1, delta_minutes)))


def main() -> int:
    parser = argparse.ArgumentParser(description="LifeOS local intervention bridge")
    parser.add_argument("intent_dir", help="directory for intent.json / response.json")
    parser.add_argument("--poll-ms", type=int, default=250)
    args = parser.parse_args()

    app = QApplication(sys.argv)
    app.setApplicationName("focus-capsule-bridge")
    bridge = Bridge(args.intent_dir)
    timer = QTimer()
    timer.timeout.connect(bridge.poll)
    timer.start(args.poll_ms)
    try:
        code = app.exec()
    finally:
        bridge.shutdown()
    return code


if __name__ == "__main__":
    raise SystemExit(main())
