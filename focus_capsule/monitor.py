import logging
import os
import sys

import psutil
from PyQt6.QtCore import QThread, pyqtSignal

HAS_WIN32 = False
HAS_APPKIT = False

if sys.platform == "win32":
    try:
        import win32gui
        import win32process

        HAS_WIN32 = True
    except ImportError:
        logging.warning("pywin32 is unavailable; foreground monitoring is disabled.")
elif sys.platform == "darwin":
    try:
        from AppKit import NSWorkspace

        HAS_APPKIT = True
    except ImportError:
        logging.warning("PyObjC AppKit is unavailable; foreground monitoring is disabled.")


ForegroundInfo = tuple[str, str, int, str]


class WindowMonitorThread(QThread):
    """Monitors the frontmost application on Windows and macOS."""

    foreground_changed = pyqtSignal(str, str, str, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = False
        self._last_process = ""
        self._last_title = ""
        self._last_executable_path = ""
        self._last_pid = 0
        self._last_seen: tuple[str, str, str, int] | None = None

    @property
    def last_process(self) -> str:
        return self._last_process

    @property
    def last_title(self) -> str:
        return self._last_title

    @property
    def last_executable_path(self) -> str:
        return self._last_executable_path

    @property
    def last_pid(self) -> int:
        return self._last_pid

    @property
    def is_focus_capsule_foreground(self) -> bool:
        return bool(self._last_seen and self._last_seen[0] == "__focus_capsule__")

    def start(self, priority=QThread.Priority.InheritPriority):
        """Start or restart monitoring without reusing stale thread state."""
        if self.isRunning():
            return
        self._running = True
        self._last_process = ""
        self._last_title = ""
        self._last_executable_path = ""
        self._last_pid = 0
        self._last_seen = None
        super().start(priority)

    def run(self):
        while self._running:
            try:
                foreground = self._read_foreground()
                if foreground is not None:
                    process_name, window_title, pid, executable_path = foreground
                    process_name = (process_name or "").strip().casefold()
                    window_title = (window_title or "").strip()
                    executable_path = (executable_path or "").strip()

                    if pid == os.getpid():
                        # Emit an explicit local-app transition so foreground
                        # usage tracking stops attributing time to the previous
                        # application. Controllers treat this marker as a
                        # system-safe process.
                        current = ("__focus_capsule__", window_title, executable_path, int(pid))
                        if current != self._last_seen:
                            self._last_seen = current
                            self._last_process = current[0]
                            self._last_title = current[1]
                            self._last_executable_path = current[2]
                            self._last_pid = current[3]
                            self.foreground_changed.emit(*current)
                    elif process_name:
                        current = (process_name, window_title, executable_path, int(pid))
                        if current != self._last_seen:
                            self._last_seen = current
                            self._last_process = process_name
                            self._last_title = window_title
                            self._last_executable_path = executable_path
                            self._last_pid = int(pid)
                            self.foreground_changed.emit(
                                process_name,
                                window_title,
                                executable_path,
                                int(pid),
                            )

                self.msleep(400)
            except Exception:
                logging.debug("Foreground monitoring failed", exc_info=True)
                self.msleep(500)

    def _read_foreground(self) -> ForegroundInfo | None:
        if HAS_WIN32:
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                return None
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            if not pid:
                return None
            process = psutil.Process(pid)
            process_name = process.name()
            try:
                executable_path = process.exe()
            except (psutil.AccessDenied, psutil.NoSuchProcess, OSError):
                executable_path = ""
            title = win32gui.GetWindowText(hwnd) or ""
            return process_name, title, int(pid), executable_path

        if HAS_APPKIT:
            application = NSWorkspace.sharedWorkspace().frontmostApplication()
            if application is None:
                return None

            pid = int(application.processIdentifier())
            display_name = application.localizedName() or ""
            executable_name = ""
            executable_url = application.executableURL()
            if executable_url is not None:
                executable_path = executable_url.path()
                if executable_path:
                    executable_name = os.path.basename(str(executable_path))

            # NSWorkspace's localized name matches what people select in the
            # UI (for example "Visual Studio Code"), while many .app bundles
            # expose a generic executable name such as "Electron".
            return display_name or executable_name, display_name, pid, str(executable_path or "")

        return None

    def stop(self):
        self._running = False
        if self.isRunning():
            return self.wait(2000)
        return True
