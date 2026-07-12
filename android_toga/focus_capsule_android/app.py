"""Focus Capsule Android - Toga application entry point.

This module provides a native Android UI for Focus Capsule using BeeWare Toga.
It shares business logic (models, history, scheduling) with the desktop version
but replaces PyQt widgets with Toga equivalents.

Key differences from desktop:
- No foreground app monitoring (Android privacy sandbox)
- No system tray (mobile UI paradigm)
- No fullscreen overlay on other apps (Android window management)
- Uses in-app notifications and modal dialogs instead
- Manual "current app" selection or optional UsageStats API (opt-in)
"""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

from toga import App, MainWindow
from toga.style import Pack
from toga.style.pack import COLUMN, ROW

from focus_capsule_android.history_adapter import HistoryService
from focus_capsule_android.controller import SessionController
from focus_capsule_android.models import FocusConfig, SessionStatus
from focus_capsule_android.screens.timer_screen import TimerScreen
from focus_capsule_android.screens.history_screen import HistoryScreen
from focus_capsule_android.screens.settings_screen import SettingsScreen
from focus_capsule_android.screens.schedule_screen import ScheduleScreen


def _get_data_dir() -> Path:
    """Get platform-appropriate data directory for Android."""
    # Android stores data in the app's internal storage
    # Toga provides access via app.paths.app
    try:
        import toga
        app = toga.App.app
        return Path(app.paths.app) / "data"
    except Exception:
        # Fallback for testing outside Android
        home = Path.home()
        if os.name == "posix":
            return home / ".local" / "share" / "focus-capsule-android"
        return home / "focus_capsule_android"


class FocusCapsuleApp(App):
    """Main Focus Capsule Android application."""

    def __init__(self):
        super().__init__(
            formal_name="Focus Capsule",
            app_id="com.focuscapsule.android",
            version="2.1.0",
            publisher="FocusCapsule",
            description="A distraction-free focus timer for Android.",
            icon="focus_capsule_android/resources/focus-capsule",
        )

        self.history_service = HistoryService()
        self.controller = None
        self.current_screen = None
        self._setup_ui()

    def _setup_ui(self):
        """Initialize the main window and navigation."""
        self.main_window = MainWindow(title="Focus Capsule")
        
        # Main content area
        self.content = toga.Box(
            style=Pack(direction=COLUMN, padding=20)
        )
        
        # Navigation bar at bottom
        self.nav_bar = self._create_nav_bar()
        
        # Stack all widgets
        self.main_window.content = toga.Box(
            children=[
                self.content,
                self.nav_bar,
            ],
            style=Pack(direction=COLUMN, flex=1)
        )
        
        # Show timer screen by default
        self.show_timer_screen()

    def _create_nav_bar(self):
        """Create bottom navigation bar."""
        nav_box = toga.Box(
            style=Pack(
                direction=ROW,
                padding=10,
                height=60,
                align_items='flex-end'
            )
        )
        
        nav_buttons = [
            ("⏱️", "Timer", self.show_timer_screen),
            ("📊", "History", self.show_history_screen),
            ("⚙️", "Settings", self.show_settings_screen),
            ("📅", "Schedule", self.show_schedule_screen),
        ]
        
        for icon, tooltip, callback in nav_buttons:
            btn = toga.Button(
                icon,
                on_press=callback,
                style=Pack(flex=1, padding=5)
            )
            btn.tooltip = tooltip
            nav_box.add(btn)
        
        return nav_box

    def show_timer_screen(self, widget=None):
        """Switch to the timer screen."""
        if self.current_screen:
            self.content.remove(self.current_screen)
        
        if not self.controller:
            self.controller = SessionController(
                history_service=self.history_service,
                app=self
            )
        
        self.current_screen = TimerScreen(
            controller=self.controller,
            on_complete=self._on_session_complete
        )
        self.content.add(self.current_screen)
        self.main_window.refresh()

    def show_history_screen(self, widget=None):
        """Switch to the history screen."""
        if self.current_screen:
            self.content.remove(self.current_screen)
        
        self.current_screen = HistoryScreen(
            history_service=self.history_service
        )
        self.content.add(self.current_screen)
        self.main_window.refresh()

    def show_settings_screen(self, widget=None):
        """Switch to the settings screen."""
        if self.current_screen:
            self.content.remove(self.current_screen)
        
        self.current_screen = SettingsScreen(
            controller=self.controller,
            on_save=self._save_settings
        )
        self.content.add(self.current_screen)
        self.main_window.refresh()

    def show_schedule_screen(self, widget=None):
        """Switch to the schedule screen."""
        if self.current_screen:
            self.content.remove(self.current_screen)
        
        self.current_screen = ScheduleScreen(
            controller=self.controller
        )
        self.content.add(self.current_screen)
        self.main_window.refresh()

    def _save_settings(self, config: FocusConfig):
        """Save settings from the settings screen."""
        # Save config to persistent storage
        self.controller.config = config
        self._show_notification("Settings saved", "Your focus settings have been updated.")

    def _on_session_complete(self, record):
        """Handle session completion."""
        self._show_notification(
            "Session Complete!",
            f"You focused for {record.actual_focus_seconds // 60} minutes."
        )

    def _show_notification(self, title: str, message: str):
        """Show a system notification."""
        try:
            from toga_android.notification import Notification
            Notification(
                title=title,
                message=message,
                priority='high'
            ).send()
        except ImportError:
            # Fallback for non-Android platforms
            logging.info(f"Notification: {title} - {message}")

    def start_foreground_service(self):
        """Start a foreground service for ongoing focus sessions."""
        try:
            from toga_android.service import ForegroundService
            service = ForegroundService(
                name="Focus Session",
                message="Focus Capsule is running...",
                icon="focus-capsule"
            )
            service.start()
        except ImportError:
            logging.info("Foreground service not available on this platform")

    def stop_foreground_service(self):
        """Stop the foreground service."""
        try:
            from toga_android.service import ForegroundService
            ForegroundService.stop_all()
        except ImportError:
            pass


def main():
    """Entry point for the Focus Capsule Android app."""
    return FocusCapsuleApp().main()


if __name__ == "__main__":
    main()
