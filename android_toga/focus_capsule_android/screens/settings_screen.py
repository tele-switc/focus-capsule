"""Settings screen for Focus Capsule Android."""

from __future__ import annotations

from toga import (
    Box, Button, Label, NumberField, Slider, TextField, VBox, HBox, Switch
)
from toga.style import Pack
from toga.style.pack import COLUMN, ROW


class SettingsScreen(Box):
    """Configuration screen for focus settings."""
    
    def __init__(self, controller, on_save=None):
        super().__init__(style=Pack(padding=20, flex=1))
        
        self.controller = controller
        self.on_save = on_save
        
        self._create_header()
        self._create_duration_setting()
        self._create_mode_setting()
        self._create_esc_setting()
        self._create_goal_setting()
        self._create_save_button()
    
    def _create_header(self):
        """Create the screen header."""
        self.header = Label(
            "Settings",
            style=Pack(font_size=24, font_weight='bold', padding_bottom=10)
        )
        self.add(self.header)
    
    def _create_duration_setting(self):
        """Create duration slider."""
        self.duration_label = Label(
            "Focus Duration: 25 minutes",
            style=Pack(font_size=14, padding_bottom=5)
        )
        
        self.duration_slider = Slider(
            min=5, max=120, step=5, value=25,
            on_change=self._on_duration_change,
            style=Pack(padding_bottom=10)
        )
        
        duration_box = VBox(
            self.duration_label,
            self.duration_slider,
            style=Pack(padding_bottom=15)
        )
        self.add(duration_box)
    
    def _create_mode_setting(self):
        """Create intensity mode selector."""
        mode_label = Label(
            "Intensity Mode:",
            style=Pack(font_size=14, padding_bottom=5)
        )
        
        self.mode_selector = ComboBox(
            items=["Light", "Standard", "Deep"],
            on_select=self._on_mode_change,
            style=Pack(padding_bottom=15)
        )
        self.mode_selector.value = "Standard"
        
        mode_box = VBox(mode_label, self.mode_selector)
        self.add(mode_box)
    
    def _create_esc_setting(self):
        """Create escape limit setting."""
        self.esc_label = Label(
            "Escape Limit: 2",
            style=Pack(font_size=14, padding_bottom=5)
        )
        
        self.esc_slider = Slider(
            min=0, max=5, step=1, value=2,
            on_change=self._on_esc_change,
            style=Pack(padding_bottom=15)
        )
        
        esc_box = VBox(self.esc_label, self.esc_slider)
        self.add(esc_box)
    
    def _create_goal_setting(self):
        """Create goal text field."""
        goal_label = Label(
            "Goal (optional):",
            style=Pack(font_size=14, padding_bottom=5)
        )
        
        self.goal_field = TextField(
            placeholder="What are you focusing on?",
            style=Pack(padding_bottom=15)
        )
        
        goal_box = VBox(goal_label, self.goal_field)
        self.add(goal_box)
    
    def _create_save_button(self):
        """Create save button."""
        self.save_btn = Button(
            "Save Settings",
            on_press=self._on_save,
            style=Pack(padding_top=10)
        )
        self.add(self.save_btn)
    
    def _on_duration_change(self, widget, value):
        """Handle duration slider change."""
        self.duration_label.text = f"Focus Duration: {int(value)} minutes"
    
    def _on_mode_change(self, widget, selected_value, index):
        """Handle mode selection change."""
        pass
    
    def _on_esc_change(self, widget, value):
        """Handle escape limit slider change."""
        self.esc_label.text = f"Escape Limit: {int(value)}"
    
    def _on_save(self, widget):
        """Handle save button press."""
        from focus_capsule_android.models import FocusConfig
        
        config = FocusConfig(
            duration_minutes=int(self.duration_slider.value),
            mode=self.mode_selector.value if self.mode_selector.value else "Standard",
            max_esc=int(self.esc_slider.value),
            goal=self.goal_field.value
        )
        
        if self.on_save:
            self.on_save(config)
