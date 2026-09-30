"""End-to-end self-check for the Focus Capsule session pipeline.

Drives one real focus session through the production wiring (foreground
events -> session controller -> overlay/break windows -> history and daily
goal persistence) against a throwaway data directory, then verifies what
actually landed on disk by re-opening the stores as if the process restarted.

Usage:
    QT_QPA_PLATFORM=offscreen .venv/Scripts/python.exe tests/e2e_session_flow.py

Prints one machine-checkable verdict line (``PASS`` / ``FAIL: ...``) and exits
with 0 / 1.  Nothing here touches the real AppData directory or QSettings:
every persisted artifact is written under a TemporaryDirectory.

Deliberate scope choices (documented so a failure is never "fixed" by relaxing
an assertion):
  * Timers are accelerated, never bypassed.  The controller's 15s/1s Qt timers
    and the break window's countdown keep firing their real slots; only the
    interval and the monotonic clock are shrunk so a 1-minute session costs
    milliseconds.  Session 2 goes through the untouched QTimer.
  * The modal ``CompletionWindow`` branch of ``_on_session_completed`` is UI
    only and would block headless, so the persistence branch
    (``_on_session_record_saved``) is what gets exercised.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
import traceback
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from PyQt6.QtWidgets import QApplication  # noqa: E402

from focus_capsule import activity_tracker as activity_tracker_module  # noqa: E402
from focus_capsule.activity_tracker import ActivityTracker  # noqa: E402
from focus_capsule.controller import SessionController  # noqa: E402
from focus_capsule.data_models import china_today  # noqa: E402
from focus_capsule.data_store import DataStore  # noqa: E402
from focus_capsule.history_db import HistoryService  # noqa: E402
from focus_capsule.main_window import MainWindow  # noqa: E402
from focus_capsule.models import FocusConfig, SessionStatus  # noqa: E402
from focus_capsule.overlay import OverlayService  # noqa: E402

TIMEOUT_SECONDS = 20.0

CODE_PATH = r"C:\Program Files\Microsoft VS Code\Code.exe"
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"


class Clock:
    """Monotonic clock stand-in so per-app usage seconds are exact."""

    def __init__(self, start: float = 1_000.0):
        self.now = start

    def monotonic(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def wait_until(predicate, what: str) -> None:
    """Poll the Qt event loop until ``predicate`` holds (pytest-qt waitUntil style)."""
    app = QApplication.instance()
    deadline = time.perf_counter() + TIMEOUT_SECONDS
    while True:
        app.processEvents()
        if predicate():
            return
        if time.perf_counter() >= deadline:
            raise AssertionError(f"timed out waiting for {what}")
        time.sleep(0.001)


def check(condition: bool, detail: str) -> None:
    if not condition:
        raise AssertionError(detail)


class FocusCapsuleE2E:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.history_path = data_dir / "history.json"
        self.store_path = data_dir
        self.clock = Clock()
        self.ui_refreshes: list[str] = []

        self.history = HistoryService(self.history_path)
        self.store = DataStore(data_path=self.store_path)
        self.overlay = OverlayService()
        self.controller = SessionController(self.history, self.overlay)

        # Production handlers are reused verbatim: they are plain methods, so
        # they are called unbound with a stand-in `self` that only exposes the
        # collaborators those two slots actually touch.  A refactor of the real
        # wiring therefore surfaces here as a failure instead of a silent copy.
        self.window = SimpleNamespace(
            _activity_tracker=None,
            _session_controller=self.controller,
            _data_store=self.store,
            _daily_goal_widget=SimpleNamespace(
                reload_goal=lambda: self.ui_refreshes.append("goal")
            ),
            _calendar_page=SimpleNamespace(refresh=lambda: self.ui_refreshes.append("calendar")),
            _trend_page=SimpleNamespace(refresh=lambda: self.ui_refreshes.append("trend")),
        )
        self.controller.session_completed.connect(
            lambda record: MainWindow._on_session_record_saved(self.window, record)
        )

    # ── harness ────────────────────────────────────────────

    def install_tracker(self) -> None:
        real_monotonic = activity_tracker_module.time.monotonic
        activity_tracker_module.time.monotonic = self.clock.monotonic
        self._restore_monotonic = real_monotonic
        tracker = ActivityTracker(self.store)
        # The 15 s housekeeping timer runs on wall clock; the fake clock owns
        # all accumulation instead, so flush points stay deterministic.
        tracker._timer.stop()
        self.window._activity_tracker = tracker
        self.tracker = tracker

    def uninstall_tracker(self) -> None:
        self.tracker.stop()
        activity_tracker_module.time.monotonic = self._restore_monotonic

    def foreground(self, process: str, executable: str, title: str) -> None:
        MainWindow._on_foreground_change(self.window, process, title, executable, 0)

    def accelerate(self, controller: SessionController) -> None:
        controller._timer.setInterval(1)
        controller._foreground_grace_timer.setInterval(1)

    def tick(self, controller: SessionController, seconds: int) -> None:
        for _ in range(seconds):
            controller._on_timer_tick()

    def config(self, **overrides) -> FocusConfig:
        values = {
            "whitelist": ["code.exe"],
            "duration_minutes": 1,
            "mode": "Standard",
            "max_esc": 2,
            "esc_break_minutes": 1,
            "goal": "端到端自检",
            "source": "timer",
        }
        values.update(overrides)
        return FocusConfig(**values)

    # ── scenario 1: full lifecycle with every state transition ──

    def run_interrupted_session(self) -> None:
        controller = self.controller
        controller.start_session(self.config())
        check(
            controller._timer.interval() == 1000,
            "start_session must arm a 1 s tick timer, got "
            f"{controller._timer.interval()} ms",
        )
        controller._timer.stop()  # ticks are driven explicitly below
        self.accelerate(controller)

        self.foreground("code.exe", CODE_PATH, "main.py — 专注神器")
        self.tick(controller, 5)
        check(controller.elapsed == 5, f"expected 5 elapsed, got {controller.elapsed}")
        check(
            controller._app_focus_seconds == {"code.exe": 5},
            f"expected 5 focused seconds on code.exe, got {controller._app_focus_seconds}",
        )

        self.clock.advance(90)
        self.foreground("chrome.exe", CHROME_PATH, "新标签页 — Google Chrome")
        wait_until(
            lambda: controller.distraction_count == 1,
            "the grace period to convert chrome.exe into a distraction",
        )
        check(
            controller.status == SessionStatus.OVERLAY,
            f"expected an overlay after the distraction, got {controller.status}",
        )
        check(
            self.overlay._overlay_window is not None,
            "OverlayService must own a live overlay window after a distraction",
        )
        self.tick(controller, 3)  # overlay time is not focus time
        check(controller.elapsed == 8, f"expected 8 elapsed, got {controller.elapsed}")

        self.clock.advance(30)
        self.foreground("code.exe", CODE_PATH, "main.py — 专注神器")
        wait_until(
            lambda: controller.status == SessionStatus.RUNNING,
            "the overlay to clear when the allowed app returns to the foreground",
        )
        check(
            self.overlay._overlay_window is None,
            "the overlay window must be released once the allowed app is back",
        )
        self.tick(controller, 4)

        controller.handle_escape()
        check(
            controller.status == SessionStatus.BREAK and controller.esc_used == 1,
            f"escape must start a break, got status={controller.status} "
            f"esc_used={controller.esc_used}",
        )
        break_window = self.overlay._break_window
        check(break_window is not None, "handle_escape must show the break window")
        check(
            break_window._remaining == 60,
            f"break must start at 60 s, got {break_window._remaining}",
        )
        break_window._timer.setInterval(1)
        wait_until(
            lambda: controller.status == SessionStatus.RUNNING,
            "the break countdown to hand the session back to RUNNING",
        )
        check(
            controller.esc_remaining == 1,
            f"one escape consumed out of two must leave 1, got {controller.esc_remaining}",
        )

        self.tick(controller, 48)  # 8 + 4 + 48 == 60 == duration
        check(
            controller.status == SessionStatus.COMPLETED,
            f"the 60th tick must complete the session, got {controller.status}",
        )
        self.clock.advance(12)

    # ── scenario 2: untouched QTimer running to its natural boundary ──

    def run_timer_driven_session(self) -> None:
        controller = self.controller
        controller.start_session(self.config())
        self.accelerate(controller)
        self.foreground("code.exe", CODE_PATH, "main.py — 专注神器")
        wait_until(
            lambda: controller.status == SessionStatus.COMPLETED,
            "the real Qt timer to finish the session on its own",
        )
        check(
            controller.elapsed == 60,
            f"a timer-driven session must stop at its 60 s boundary, got "
            f"{controller.elapsed}",
        )

    # ── scenario 3: user terminates early ──────────────────

    def run_terminated_session(self) -> None:
        controller = self.controller
        controller.start_session(self.config(duration_minutes=25, goal=None))
        controller._timer.stop()
        self.accelerate(controller)
        self.foreground("code.exe", CODE_PATH, "main.py — 专注神器")
        self.tick(controller, 15)
        controller.terminate()
        check(
            controller.status == SessionStatus.TERMINATED,
            f"terminate() must end the session, got {controller.status}",
        )
        self.clock.advance(8)

    # ── assertions on what is actually on disk ─────────────

    def verify_persistence(self) -> None:
        history_payload = json.loads(self.history_path.read_text(encoding="utf-8"))
        check(
            isinstance(history_payload, list) and len(history_payload) == 3,
            f"history.json must hold 3 appended records, got {history_payload!r}",
        )
        first, second, third = history_payload

        check(first["outcome"] == "completed", f"record 1 outcome: {first['outcome']}")
        check(first["duration_minutes"] == 1, f"record 1 duration: {first}")
        check(
            first["actual_focus_seconds"] == 60,
            f"record 1 must have run its full minute: {first['actual_focus_seconds']}",
        )
        check(
            first["distraction_count"] == 1,
            f"record 1 distraction_count: {first['distraction_count']}",
        )
        check(
            len(first["distractions"]) == 1
            and first["distractions"][0]["process_name"] == "chrome.exe"
            and first["distractions"][0]["window_title"] == "新标签页 — Google Chrome",
            f"record 1 distraction detail: {first['distractions']}",
        )
        check(first["esc_used"] == 1, f"record 1 esc_used: {first['esc_used']}")
        check(first["mode"] == "Standard", f"record 1 mode: {first['mode']}")
        check(
            first["whitelisted_apps"] == ["code.exe"],
            f"record 1 whitelist: {first['whitelisted_apps']}",
        )
        check(first["goal"] == "端到端自检", f"record 1 goal: {first['goal']}")
        check(first["source"] == "timer", f"record 1 source: {first['source']}")
        check(
            first["app_focus_seconds"] == {"code.exe": 57},
            "record 1 must credit 57 s to code.exe (5 + 4 + 48; the 3 overlay "
            f"seconds are not focus): {first['app_focus_seconds']}",
        )
        check(
            first["actual_focus_seconds"] - sum(first["app_focus_seconds"].values()) == 3,
            "record 1: the uncredited seconds must exactly match overlay time",
        )
        started = datetime.fromisoformat(first["started_at"])
        ended = datetime.fromisoformat(first["ended_at"])
        check(ended >= started, f"record 1 timestamps run backwards: {first}")

        check(
            second["outcome"] == "completed"
            and second["actual_focus_seconds"] == 60
            and second["app_focus_seconds"] == {"code.exe": 60}
            and second["distractions"] == []
            and second["distraction_count"] == 0
            and second["esc_used"] == 0,
            f"record 2 (timer-driven) mismatch: {second}",
        )
        check(
            third["outcome"] == "terminated"
            and third["actual_focus_seconds"] == 15
            and third["app_focus_seconds"] == {"code.exe": 15}
            and third["goal"] is None
            and third["duration_minutes"] == 25,
            f"record 3 (terminated) mismatch: {third}",
        )

        goals = json.loads((self.store_path / "daily_goals.json").read_text(encoding="utf-8"))
        today = china_today().isoformat()
        check(today in goals, f"daily_goals.json must key today ({today}): {goals!r}")
        entry = goals[today]
        # 60//60 + 60//60 + 15//60 == 2 achieved minutes for the day.
        check(
            entry["achieved_minutes"] == 2,
            f"today achieved_minutes must be 2, got {entry['achieved_minutes']}",
        )
        check(
            entry["sessions_completed"] == 2,
            f"today sessions_completed must be 2, got {entry['sessions_completed']}",
        )
        check(
            entry["sessions_terminated"] == 1,
            f"today sessions_terminated must be 1, got {entry['sessions_terminated']}",
        )

        activity = json.loads(
            (self.store_path / "daily_activity.json").read_text(encoding="utf-8")
        )
        usage = activity[today]["app_usage_seconds"]
        check(
            usage == {"code.exe": 110, "chrome.exe": 30},
            f"foreground usage must be 110 s code.exe / 30 s chrome.exe, got {usage}",
        )
        check(
            activity[today]["app_display_names"] == {"code.exe": "Code", "chrome.exe": "chrome"},
            f"display names not persisted: {activity[today]['app_display_names']}",
        )

        check(
            self.ui_refreshes == ["goal", "calendar", "trend"] * 3,
            f"each completed session must refresh the three views, got "
            f"{self.ui_refreshes}",
        )

        # Restart the process's view of the data: brand new services over the
        # same files must deserialize exactly what was written.
        reopened_history = HistoryService(self.history_path)
        reopened_records = reopened_history.load_history()
        check(
            len(reopened_records) == 3
            and reopened_records[0].outcome == "completed"
            and reopened_records[0].actual_focus_seconds == 60
            and reopened_records[2].outcome == "terminated"
            and reopened_records[0].distractions == first["distractions"],
            "a fresh HistoryService over the same file must read back the records",
        )
        reopened_store = DataStore(data_path=self.store_path)
        goal_entry = reopened_store.get_goal(today)
        check(
            goal_entry.achieved_minutes == 2
            and goal_entry.sessions_completed == 2
            and goal_entry.sessions_terminated == 1,
            f"a fresh DataStore must read back today's aggregates, got {goal_entry}",
        )

        leftovers = sorted(p.name for p in self.data_dir.iterdir() if p.suffix == ".tmp")
        check(not leftovers, f"atomic writes must leave no temp files behind: {leftovers}")


def run() -> None:
    app = QApplication.instance() or QApplication([])
    with tempfile.TemporaryDirectory(prefix="focus-capsule-e2e-") as tmp:
        data_dir = Path(tmp)
        scenario = FocusCapsuleE2E(data_dir)
        scenario.install_tracker()
        try:
            print("ok - isolated data directory prepared: history.json + daily_*.json")
            scenario.run_interrupted_session()
            print("ok - session 1: allowed app -> distraction overlay -> escape break -> complete")
            scenario.run_timer_driven_session()
            print("ok - session 2: production QTimer reached its own 60 s boundary")
            scenario.run_terminated_session()
            print("ok - session 3: early terminate recorded as terminated")
            scenario.uninstall_tracker()
            print("ok - activity tracker flushed to daily_activity.json")
            scenario.verify_persistence()
            print("ok - history.json / daily_goals.json / daily_activity.json verified on disk")
            print("ok - fresh HistoryService + DataStore reloaded the same persisted state")
        finally:
            app.processEvents()
            scenario.overlay.deleteLater()
            scenario.controller.deleteLater()


def main() -> int:
    try:
        run()
    except BaseException as error:  # noqa: BLE001 - a self-check must report everything
        traceback.print_exc()
        print(f"FAIL: {type(error).__name__}: {error}")
        return 1
    print("PASS: focus session end-to-end persistence self-check")
    return 0


if __name__ == "__main__":
    sys.exit(main())
