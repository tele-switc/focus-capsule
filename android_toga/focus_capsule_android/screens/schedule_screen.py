"""Schedule screen for Focus Capsule Android."""

from __future__ import annotations

from toga import (
    Box, Button, Label, NumberField, Switch, TextField, VBox, HBox
)
from toga.style import Pack
from toga.style.pack import COLUMN, ROW


class ScheduleScreen(Box):
    """Schedule-based locking rules screen."""
    
    def __init__(self, controller):
        super().__init__(style=Pack(padding=20, flex=1))
        
        self.controller = controller
        self.rules = []
        
        self._create_header()
        self._create_rule_form()
        self._create_rules_list()
        self._create_actions()
    
    def _create_header(self):
        """Create the screen header."""
        self.header = Label(
            "Schedule Rules",
            style=Pack(font_size=24, font_weight='bold', padding_bottom=10)
        )
        self.add(self.header)
    
    def _create_rule_form(self):
        """Create form for adding new rules."""
        form = VBox(
            Label("Start Time:", style=Pack(font_size=14)),
            HBox(
                NumberField(step=1, min=0, max=23, placeholder="Hour", style=Pack(flex=1)),
                NumberField(step=1, min=0, max=59, placeholder="Minute", style=Pack(flex=1)),
                style=Pack(padding_bottom=5)
            ),
            Label("End Time:", style=Pack(font_size=14)),
            HBox(
                NumberField(step=1, min=0, max=23, placeholder="Hour", style=Pack(flex=1)),
                NumberField(step=1, min=0, max=59, placeholder="Minute", style=Pack(flex=1)),
                style=Pack(padding_bottom=10)
            ),
            Label("Mode:", style=Pack(font_size=14)),
            ComboBox(
                items=["Light", "Standard", "Deep"],
                value="Deep",
                style=Pack(padding_bottom=10)
            ),
            Label("Whitelisted Apps (comma-separated):", style=Pack(font_size=14)),
            TextField(
                placeholder="chrome, vscode",
                style=Pack(padding_bottom=15)
            ),
            VBox(
                Label("Enabled:", style=Pack(font_size=14)),
                Switch(on_toggle=self._on_enable_toggle, default=True, style=Pack(padding_bottom=15))
            ),
            style=Pack(
                border=1,
                border_color='#cccccc',
                padding=15,
                border_radius=8,
                background_color='#f9f9f9'
            )
        )
        self.form = form
        self.add(form)
    
    def _create_rules_list(self):
        """Create list of active rules."""
        self.rules_list = VBox(
            style=Pack(padding_top=10)
        )
        self.add(self.rules_list)
    
    def _create_actions(self):
        """Create action buttons."""
        self.add_btn = Button(
            "Add Rule",
            on_press=self._on_add,
            style=Pack(padding_top=10, flex=1)
        )
        self.clear_btn = Button(
            "Clear All",
            on_press=self._on_clear,
            style=Pack(padding_top=5, flex=1)
        )
        
        actions = HBox([self.add_btn, self.clear_btn])
        self.add(actions)
    
    def _on_enable_toggle(self, widget, value):
        """Handle enable/disable toggle."""
        pass
    
    def _on_add(self, widget):
        """Handle add rule button press."""
        # Simplified - in production, collect form values
        from focus_capsule_android.models import ScheduleRule
        
        rule = ScheduleRule(
            start_hour=9,
            start_minute=0,
            end_hour=17,
            end_minute=0,
            mode="Deep",
            whitelisted_apps=["chrome", "vscode"],
            enabled=True,
            label="Work Hours"
        )
        
        self.rules.append(rule)
        self._render_rules()
    
    def _on_clear(self, widget):
        """Handle clear all button press."""
        self.rules.clear()
        self._render_rules()
    
    def _render_rules(self):
        """Render the rules list."""
        # Clear existing
        while self.rules_list.children:
            self.rules_list.remove(self.rules_list.children[0])
        
        if not self.rules:
            self.rules_list.add(Label(
                "No schedule rules defined.",
                style=Pack(color='#999999', padding=10)
            ))
            return
        
        for rule in self.rules:
            rule_box = HBox([
                Label(
                    f"{rule.label or 'Rule'}: {rule.start_hour:02d}:{rule.start_minute:02d} - "
                    f"{rule.end_hour:02d}:{rule.end_minute:02d}",
                    style=Pack(flex=1)
                ),
                Label(
                    rule.mode,
                    style=Pack(color='#666666')
                ),
                Label(
                    "✓" if rule.enabled else "✗",
                    style=Pack(color='#4CAF50' if rule.enabled else '#999999')
                )
            ])
            self.rules_list.add(rule_box)
