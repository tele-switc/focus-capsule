"""Persistent store for app categories, daily goals, daily reports.

Uses QSettings for small config and a JSON file in the app data location
for daily reports / goals history.  All data remains on the local machine.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QSettings, QStandardPaths

from focus_capsule.data_models import (
    AppConfig, AppCategory, DailyGoalEntry, DailyReport, CST, china_today,
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
            return {k: builder(v) for k, v in data.items()}
        except (OSError, json.JSONDecodeError, UnicodeError, TypeError, ValueError):
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
