"""Android-compatible history service adapter.

Wraps the desktop HistoryService to work without PyQt dependencies.
Uses the same JSON format for cross-platform compatibility.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from dataclasses import asdict, fields
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Union

from focus_capsule_android.models import SessionRecord


PathLike = Union[str, os.PathLike]
_RECORD_FIELDS = {item.name for item in fields(SessionRecord)}


class HistoryService:
    """Android-compatible history service."""
    
    def __init__(self, history_path: Optional[PathLike] = None):
        if history_path is None:
            # Use app-specific storage on Android
            data_dir = Path(os.environ.get("ANDROID_DATA_DIR", Path.home()))
            self._path = data_dir / "focus-capsule" / "history.json"
        else:
            self._path = Path(history_path)
        
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._load_blocked = False
    
    def load_history(self) -> List[SessionRecord]:
        """Load session history from disk."""
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
            logging.exception("Focus history is corrupt: %s", self._path)
            try:
                backup_path = self._backup_corrupt_file()
                logging.warning("Corrupt history moved to %s", backup_path)
            except OSError:
                self._load_blocked = True
                logging.exception("Unable to back up corrupt history")
            return []
    
    def _deserialize_records(self, payload) -> List[SessionRecord]:
        """Deserialize JSON payload into SessionRecord objects."""
        if isinstance(payload, dict) and "records" in payload:
            payload = payload["records"]
        if not isinstance(payload, list):
            raise ValueError("History root must be a list")
        
        records: List[SessionRecord] = []
        for item in payload:
            if not isinstance(item, dict):
                raise ValueError("History entries must be objects")
            
            migrated = dict(item)
            migrated.setdefault("outcome", "completed")
            migrated.setdefault("goal", None)
            migrated.setdefault("distractions", [])
            
            known_values = {
                key: value for key, value in migrated.items() 
                if key in _RECORD_FIELDS
            }
            records.append(SessionRecord(**known_values))
        return records
    
    def _backup_corrupt_file(self) -> Path:
        """Create a backup of corrupt history file."""
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        backup = self._path.with_name(
            f"{self._path.stem}.corrupt-{timestamp}{self._path.suffix}"
        )
        os.replace(self._path, backup)
        return backup
    
    def save_record(self, record: SessionRecord):
        """Save a session record to disk."""
        history = self.load_history()
        if self._load_blocked:
            raise OSError("Refusing to overwrite history without backup")
        
        history.append(record)
        if len(history) > 100:
            history = history[-100:]
        self._atomic_write([asdict(item) for item in history])
    
    def _atomic_write(self, payload):
        """Write payload atomically to prevent corruption."""
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
        """Clear all history."""
        self._load_blocked = False
        if self._path.exists():
            self._path.unlink()
