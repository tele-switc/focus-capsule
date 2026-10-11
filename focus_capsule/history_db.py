import json
import logging
import os
import tempfile
from dataclasses import asdict, fields
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Union

from PyQt6.QtCore import QStandardPaths

from focus_capsule.models import SessionRecord

PathLike = Union[str, os.PathLike]
_RECORD_FIELDS = {item.name for item in fields(SessionRecord)}


class HistoryService:
    def __init__(self, history_path: Optional[PathLike] = None):
        if history_path is None:
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
                raise RuntimeError("No writable application data location is available")
            self._path = Path(location) / "history.json"
        else:
            self._path = Path(history_path)

        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._load_blocked = False

    def load_history(self) -> List[SessionRecord]:
        self._load_blocked = False
        if not self._path.exists():
            return []

        try:
            with self._path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
            return self._deserialize_records(payload)
        except OSError:
            logging.exception("Unable to read focus history from %s", self._path)
            return []
        except (json.JSONDecodeError, UnicodeError, TypeError, ValueError, KeyError):
            logging.exception("Focus history is corrupt or incompatible: %s", self._path)
            try:
                backup_path = self._backup_corrupt_file()
                logging.warning("Corrupt focus history moved to %s", backup_path)
            except OSError:
                # Never overwrite unreadable data when a safety backup could not
                # be created.
                self._load_blocked = True
                logging.exception("Unable to back up corrupt focus history")
            return []

    def _deserialize_records(self, payload) -> List[SessionRecord]:
        if isinstance(payload, dict) and "records" in payload:
            payload = payload["records"]
        if not isinstance(payload, list):
            raise ValueError("History root must be a list of session records")

        records: List[SessionRecord] = []
        for item in payload:
            if not isinstance(item, dict):
                raise ValueError("History entries must be objects")

            migrated = dict(item)
            if "outcome" not in migrated:
                migrated["outcome"] = migrated.pop("status", "completed")
            else:
                migrated.pop("status", None)
            migrated.setdefault("outcome", "completed")
            migrated.setdefault("goal", None)
            migrated.setdefault("distractions", [])

            known_values = {
                key: value for key, value in migrated.items() if key in _RECORD_FIELDS
            }
            records.append(SessionRecord(**known_values))
        return records

    def _backup_corrupt_file(self) -> Path:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        backup = self._path.with_name(
            f"{self._path.stem}.corrupt-{timestamp}{self._path.suffix}"
        )
        os.replace(self._path, backup)
        return backup

    def save_record(self, record: SessionRecord):
        history = self.load_history()
        if self._load_blocked:
            raise OSError("Refusing to overwrite history without a corrupt-data backup")

        history.append(record)
        # Keep enough detail for long-term calendar review. Ten thousand
        # sessions covers several years for typical daily use while keeping the
        # local JSON file bounded.
        if len(history) > 10_000:
            history = history[-10_000:]
        self._atomic_write([asdict(item) for item in history])

    def _atomic_write(self, payload):
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{self._path.name}.",
            suffix=".tmp",
            dir=self._path.parent,
        )
        temporary_path = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
                json.dump(
                    payload,
                    handle,
                    ensure_ascii=False,
                    indent=2,
                    default=str,
                )
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_path, self._path)
        finally:
            if temporary_path.exists():
                temporary_path.unlink()

    def clear_history(self):
        self._load_blocked = False
        if self._path.exists():
            self._path.unlink()
