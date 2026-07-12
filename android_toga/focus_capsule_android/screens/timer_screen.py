"""Timer screen for Focus Capsule Android."""

from __future__ import annotations

from toga import Box, Button, Label, ProgressBar, Slider, VBox, HBox
from toga.style import Pack
from toga.style.pack import COLUMN, ROW


class TimerScreen(Box):
    """Main timer screen with start/pause/stop controls."""
    
    def __init__(self, controller, on_complete=None):
        super().__init__(style=Pack(padding=20, flex=1))
        
        self.controller = controller
        self.on_complete = on_complete
        
        self._create_header()
        self._create_timer_display()
        self._create_controls()
        self._create_progress()
        self._create_esc_indicator()
        
        # Register update callback
        self.controller.on_update(self._on_update)
        self.controller.on_complete(self._on_complete)
    
    def _create_header(self):
        """Create the screen header."""
        self.header = Label(
            "Focus Capsule",
            style=Pack(font_size=24, font_weight='bold', padding_bottom=10)
        )
        self.add(self.header)
    
    def _create_timer_display(self):
        """Create the large timer display."""
        self.timer_label = Label(
            "25:00",
            style=Pack(
                font_size=72,
                font_weight='bold',
                text_align='center',
                padding=20
            )
        )
        self.timer_box = VBox(
            self.timer_label,
            style=Pack(alignment='center')
        )
        self.add(self.timer_box)
    
    def _create_controls(self):
        """Create start/pause/stop buttons."""
        self.start_btn = Button(
            "Start Focus",
            on_press=self._on_start,
            style=Pack(flex=1, padding=10)
        )
        self.start_btn.style.update(font_size=18)
        
        self.pause_btn = Button(
            "Pause",
            on_press=self._on_pause,
            enabled=False,
            style=Pack(flex=1, padding=10)
        )
        self.pause_btn.style.update(font_size=18)
        
        self.stop_btn = Button(
            "Stop",
            on_press=self._on_stop,
            enabled=False,
            style=Pack(flex=1, padding=10)
        )
        self.stop_btn.style.update(font_size=18)
        
        controls = HBox(
            [self.start_btn, self.pause_btn, self.stop_btn],
            style=Pack(padding_top=20)
        )
        self.add(controls)
    
    def _create_progress(self):
        """Create progress bar."""
        self.progress = ProgressBar(max=100, style=Pack(padding_top=20))
        self.add(self.progress)
    
    def _create_esc_indicator(self):
        """Create escape/break indicator."""
        self.esc_label = Label(
            "Escapes remaining: 2",
            style=Pack(
                font_size=14,
                text_align='center',
                padding_top=10,
                color='#666666'
            )
        )
        self.add(self.esc_label)
    
    def _on_start(self, widget):
        """Handle start button press."""
        from focus_capsule_android.models import FocusConfig
        
        config = FocusConfig(
            duration_minutes=25,
            mode="Standard",
            max_esc=2
        )
        self.controller.start_session(config)
        self.start_btn.enabled = False
        self.pause_btn.enabled = True
        self.stop_btn.enabled = True
    
    def _on_pause(self, widget):
        """Handle pause button press."""
        self.controller.terminate()
        self._reset_buttons()
    
    def _on_stop(self, widget):
        """Handle stop button press."""
        if self._confirm_stop():
            self.controller.terminate()
            self._reset_buttons()
    
    def _confirm_stop(self):
        """Show confirmation dialog for stopping."""
        # Simple confirmation - in production, use Toga dialog
        return True
    
    def _reset_buttons(self):
        """Reset button states."""
        self.start_btn.enabled = True
        self.pause_btn.enabled = False
        self.stop_btn.enabled = False
    
    def _on_update(self, update):
        """Handle session update from controller."""
        from focus_capsule_android.models import SessionStatus
        
        # Update timer display
        remaining = max(0, update.total - update.elapsed)
        minutes = remaining // 60
        seconds = remaining % 60
        self.timer_label.text = f"{minutes:02d}:{seconds:02d}"
        
        # Update progress
        if update.total > 0:
            self.progress.value = (update.elapsed / update.total) * 100
        
        # Update escape indicator
        self.esc_label.text = f"Escapes remaining: {update.esc_remaining}"
        
        # Update button states based on status
        if update.status == SessionStatus.BREAK:
            self.timer_label.text = f"Break: {update.break_remaining}s"
            self.timer_label.style.update(color='#4CAF50')
        elif update.status == SessionStatus.LOCKED:
            self.timer_label.style.update(color='#FF9800')
        else:
            self.timer_label.style.update(color='#333333')
        
        if update.status in {SessionStatus.COMPLETED, SessionStatus.TERMINATED}:
            self._reset_buttons()
    
    def _on_complete(self, record):
        """Handle session completion."""
        if self.on_complete:
            self.on_complete(record)
