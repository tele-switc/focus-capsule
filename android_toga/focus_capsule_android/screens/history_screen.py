"""History screen for Focus Capsule Android."""

from __future__ import annotations

from datetime import datetime

from toga import Box, Button, Label, ScrollView, Table, VBox, HBox
from toga.style import Pack
from toga.style.pack import COLUMN, ROW


class HistoryScreen(Box):
    """Displays past focus sessions."""
    
    def __init__(self, history_service):
        super().__init__(style=Pack(padding=20, flex=1))
        
        self.history_service = history_service
        
        self._create_header()
        self._create_summary()
        self._create_table()
        self._create_actions()
        
        self._load_history()
    
    def _create_header(self):
        """Create the screen header."""
        self.header = Label(
            "Session History",
            style=Pack(font_size=24, font_weight='bold', padding_bottom=10)
        )
        self.add(self.header)
    
    def _create_summary(self):
        """Create summary statistics."""
        self.summary_label = Label(
            "Loading...",
            style=Pack(font_size=14, color='#666666', padding_bottom=10)
        )
        self.add(self.summary_label)
    
    def _create_table(self):
        """Create table for session records."""
        self.table = Table(
            headers=["Date", "Duration", "Focus", "Distractions", "Status"],
            rows=[],
            style=Pack(height=300, flex=1)
        )
        
        scroll = ScrollView(
            self.table,
            style=Pack(flex=1)
        )
        self.add(scroll)
    
    def _create_actions(self):
        """Create action buttons."""
        self.clear_btn = Button(
            "Clear History",
            on_press=self._on_clear,
            style=Pack(padding_top=10)
        )
        self.add(self.clear_btn)
    
    def _load_history(self):
        """Load and display session history."""
        records = self.history_service.load_history()
        
        if not records:
            self.summary_label.text = "No sessions recorded yet."
            return
        
        # Calculate summary
        total_sessions = len(records)
        total_focus_seconds = sum(r.actual_focus_seconds for r in records)
        total_focus_hours = total_focus_seconds / 3600
        
        # Format dates and stats
        rows = []
        for record in reversed(records[-20:]):  # Show last 20
            try:
                dt = datetime.fromisoformat(record.started_at)
                date_str = dt.strftime("%Y-%m-%d %H:%M")
            except (ValueError, TypeError):
                date_str = record.started_at
            
            duration_min = record.duration_minutes
            focus_min = record.actual_focus_seconds // 60
            distractions = record.distraction_count
            status = record.outcome.capitalize()
            
            rows.append([
                date_str,
                f"{duration_min}m",
                f"{focus_min}m",
                str(distractions),
                status
            ])
        
        self.table.rows = rows
        self.summary_label.text = (
            f"{total_sessions} sessions | {total_focus_hours:.1f} hours focused"
        )
    
    def _on_clear(self, widget):
        """Handle clear history button press."""
        if self._confirm_clear():
            self.history_service.clear_history()
            self.table.rows = []
            self.summary_label.text = "History cleared."
    
    def _confirm_clear(self):
        """Show confirmation dialog for clearing history."""
        return True  # Simplified for now
