"""Persistent store for app categories, daily goals, daily reports.

Uses QSettings for small config and a JSON file in the app data location
for daily reports / goals history.  All data remains on the local machine.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from datetime import timedelta, timezone
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QSettings, QStandardPaths

from focus_capsule.data_models import (
    AppConfig,
    DailyActivityEntry,
    DailyGoal,
    DailyGoalEntry,
    DailyGoalTargets,
    DailyReport,
    GoalStatus,
    TaskItem,
    china_today,
)

CST_TZ = timezone(timedelta(hours=8), name="CST")


class DataStore:
    """Reads and writes app-level data for v2.1 features."""

    SETTINGS_ORG = "FocusCapsule"
    SETTINGS_APP = "FocusCapsule"

    def __init__(self, data_path: Optional[Path] = None):
        if data_path is None:
            location = QStandardPaths.writableLocation(
                QStandardPaths.StandardLocation.AppDataLocation
            )
            if not location:
                location = QStandardPaths.writableLocation(
                    QStandardPaths.StandardLocation.GenericDataLocation
                )
                if location:
                    location = str(Path(location) / "FocusCapsule")
            if not location:
                location = str(Path.home() / ".focus-capsule")
            self._base = Path(location)
        else:
            self._base = Path(data_path)
        self._base.mkdir(parents=True, exist_ok=True)
        self._reports_path = self._base / "daily_reports.json"
        self._goals_path = self._base / "daily_goals.json"
        self._activity_path = self._base / "daily_activity.json"

    # ── AppConfig (QSettings) ────────────────────────────────

    def load_app_config(self) -> AppConfig:
        settings = QSettings(self.SETTINGS_ORG, self.SETTINGS_APP)
        settings.beginGroup("app_config_v2")
        raw = settings.value("config", "")
        settings.endGroup()
        if not raw:
            return AppConfig()
        try:
            data = json.loads(raw) if isinstance(raw, str) else dict(raw)
            return AppConfig.from_dict(data)
        except (json.JSONDecodeError, TypeError, ValueError):
            logging.warning("app_config_v2 corrupt, resetting")
            return AppConfig()

    def save_app_config(self, config: AppConfig) -> None:
        settings = QSettings(self.SETTINGS_ORG, self.SETTINGS_APP)
        settings.beginGroup("app_config_v2")
        settings.setValue("config", json.dumps(config.to_dict(), ensure_ascii=False))
        settings.endGroup()
        settings.sync()

    # ── Daily goals ──────────────────────────────────────────

    def load_all_goals(self) -> dict[str, DailyGoalEntry]:
        return self._load_dict(self._goals_path, DailyGoalEntry.from_dict)

    def get_goal(self, date_str: str) -> DailyGoalEntry:
        goals = self.load_all_goals()
        return goals.get(date_str, DailyGoalEntry(date_str=date_str))

    def get_today_goal(self) -> DailyGoalEntry:
        return self.get_goal(china_today().isoformat())

    def save_goal(self, entry: DailyGoalEntry) -> None:
        goals = self.load_all_goals()
        goals[entry.date_str] = entry
        # Prune old entries (keep 365 days)
        cutoff = (china_today() - timedelta(days=365)).isoformat()
        goals = {k: v for k, v in goals.items() if k >= cutoff}
        self._atomic_write(self._goals_path, {k: v.to_dict() for k, v in goals.items()})

    def save_daily_goal(self, goal: DailyGoal) -> None:
        """Backward-compatible wrapper for daily_goal_page's new Goal model.

        Stored under :attr:`goal.date` with ``target_minutes=0``/``achieved_minutes=0``
        so existing history queries keep working; task list is kept alongside.
        """
        existing = self.get_goal(goal.date)
        existing.daily_goal_title = goal.title
        existing.daily_goal_status = (
            goal.status.value if isinstance(goal.status, GoalStatus) else str(goal.status)
        )
        existing.daily_goal_tasks = [
            {
                "title": t.title,
                "priority": t.priority,
                "status": t.status.value if isinstance(t.status, GoalStatus) else t.status,
                "estimated_minutes": t.estimated_minutes,
                "actual_minutes": t.actual_minutes,
            }
            for t in goal.tasks
        ]
        self.save_goal(existing)

    def save_daily_targets(self, date_str: str, targets: DailyGoalTargets) -> None:
        entry = self.get_goal(date_str)
        entry.targets = targets
        if targets.total_focus_minutes is not None:
            entry.target_minutes = targets.total_focus_minutes
        self.save_goal(entry)

    def get_goal_for_date(self, date_str: str) -> Optional[DailyGoal]:
        """Load a :class:`DailyGoal` from the store for a given date string.

        Returns ``None`` when no user-created goal exists. Session-only daily
        statistics must not make the overview look as if a task was created.
        """
        entry = self.get_goal(date_str)
        payload = entry.to_dict()
        title = str(payload.get("daily_goal_title", "")).strip()
        tasks_raw = payload.get("daily_goal_tasks", [])
        if not title and not any(str(task.get("title", "")).strip() for task in tasks_raw):
            return None
        tasks = []
        for task in tasks_raw:
            status_raw = task.get("status", "todo")
            try:
                task_status = GoalStatus(status_raw)
            except (TypeError, ValueError):
                task_status = GoalStatus.TODO
            try:
                estimated_minutes = max(0, int(task.get("estimated_minutes", 0)))
            except (TypeError, ValueError):
                estimated_minutes = 0
            try:
                actual_minutes = max(0, int(task.get("actual_minutes", 0)))
            except (TypeError, ValueError):
                actual_minutes = 0
            tasks.append(
                TaskItem(
                    title=str(task.get("title", "")),
                    priority=str(task.get("priority", "medium")),
                    status=task_status,
                    estimated_minutes=estimated_minutes,
                    actual_minutes=actual_minutes,
                )
            )
        status_raw = entry.to_dict().get("daily_goal_status", "todo")
        try:
            status = GoalStatus(status_raw)
        except (ValueError, TypeError):
            status = GoalStatus.TODO
        return DailyGoal(
            date=date_str,
            title=title,
            tasks=tasks,
            status=status,
        )

    def update_today_goal_from_session(
        self, achieved_minutes: int, completed: bool, terminated: bool
    ) -> DailyGoalEntry:
        entry = self.get_today_goal()
        entry.achieved_minutes += achieved_minutes
        if completed:
            entry.sessions_completed += 1
        if terminated:
            entry.sessions_terminated += 1
        self.save_goal(entry)
        return entry

    # ── Daily foreground activity ───────────────────────────

    def load_all_activity(self) -> dict[str, DailyActivityEntry]:
        return self._load_dict(self._activity_path, DailyActivityEntry.from_dict)

    def get_activity(self, date_str: str) -> DailyActivityEntry:
        entries = self.load_all_activity()
        return entries.get(date_str, DailyActivityEntry(date_str=date_str))

    def save_activity(self, entry: DailyActivityEntry) -> None:
        entries = self.load_all_activity()
        entries[entry.date_str] = entry
        cutoff = (china_today() - timedelta(days=365)).isoformat()
        entries = {key: value for key, value in entries.items() if key >= cutoff}
        self._atomic_write(
            self._activity_path,
            {key: value.to_dict() for key, value in entries.items()},
        )

    def add_app_usage(
        self,
        date_str: str,
        process_name: str,
        seconds: int,
        display_name: str = "",
    ) -> DailyActivityEntry:
        process = str(process_name).strip().casefold()
        seconds = max(0, int(seconds))
        entry = self.get_activity(date_str)
        if process and seconds:
            entry.app_usage_seconds[process] = (
                entry.app_usage_seconds.get(process, 0) + seconds
            )
        if process and display_name.strip():
            entry.app_display_names[process] = display_name.strip()
        self.save_activity(entry)
        return entry

    # ── Daily reports ────────────────────────────────────────

    def load_all_reports(self) -> dict[str, DailyReport]:
        return self._load_dict(self._reports_path, DailyReport.from_dict)

    def get_report(self, date_str: str) -> Optional[DailyReport]:
        reports = self.load_all_reports()
        return reports.get(date_str)

    def save_report(self, report: DailyReport) -> None:
        reports = self.load_all_reports()
        reports[report.date_str] = report
        # Prune old entries (keep 365 days)
        cutoff = (china_today() - timedelta(days=365)).isoformat()
        reports = {k: v for k, v in reports.items() if k >= cutoff}
        self._atomic_write(self._reports_path, {k: v.to_dict() for k, v in reports.items()})

    # ── Internal helpers ──────────────────────────────────────

    @staticmethod
    def _load_dict(path: Path, builder):
        if not path.exists():
            return {}
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                return {}
            result = {}
            for key, value in data.items():
                try:
                    result[str(key)] = builder(value)
                except (TypeError, ValueError):
                    logging.warning("Skipping invalid entry %s in %s", key, path)
            return result
        except (OSError, json.JSONDecodeError, UnicodeError):
            logging.exception("Failed to load data from %s", path)
            return {}

    def _atomic_write(self, path: Path, payload: dict) -> None:
        fd, tmp_name = tempfile.mkstemp(
            prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
        )
        tmp_path = Path(tmp_name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2, default=str)
                f.write("\n")
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, path)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()
