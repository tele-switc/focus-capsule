"""Android-compatible overlay/notification service.

Since Android doesn't support fullscreen overlays on other apps,
this service uses notifications and in-app modals instead.
"""

from __future__ import annotations

from typing import Callable, Optional


class OverlayService:
    """Provides overlay-like functionality on Android.
    
    Replaces the desktop overlay with:
    - Foreground notifications for active sessions
    - Modal dialogs for distraction prevention
    - In-app lock screens when schedule rules activate
    """
    
    def __init__(self, app=None):
        self._app = app
        self._active = False
        self._lock_dialog: Optional[object] = None
    
    def show_overlay(self, blocking_app: str, return_seconds: int = 3):
        """Show a lock dialog preventing app switching."""
        self._active = True
        if self._app:
            self._app.show_modal_dialog(
                title="Focus Mode Active",
                message=f"You cannot switch to {blocking_app} during focus time.",
                dismiss_after=return_seconds,
                on_dismiss=self.on_dismissed
            )
    
    def hide_overlay(self):
        """Hide the overlay/dialog."""
        self._active = False
        if self._app and self._lock_dialog:
            self._app.dismiss_modal_dialog()
            self._lock_dialog = None
    
    def show_break_window(self, minutes: int, on_tick=None, on_end=None):
        """Show a break timer dialog."""
        if self._app:
            self._app.show_modal_dialog(
                title="Break Time",
                message=f"Take a {minutes}-minute break.",
                is_break=True,
                on_tick=on_tick,
                on_end=on_end
            )
    
    def hide_break_window(self):
        """Hide the break dialog."""
        if self._app:
            self._app.dismiss_modal_dialog()
    
    def on_dismissed(self):
        """Called when the overlay is dismissed."""
        pass
    
    def show_notification(self, title: str, message: str):
        """Show a system notification."""
        if self._app:
            try:
                from toga_android.notification import Notification
                Notification(
                    title=title,
                    message=message,
                    priority='high'
                ).send()
            except ImportError:
                print(f"Notification: {title} - {message}")
