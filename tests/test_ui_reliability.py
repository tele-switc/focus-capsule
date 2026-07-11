import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from focus_capsule.controller import SessionUpdate
from focus_capsule.models import FocusConfig, SessionStatus
from focus_capsule.overlay import BreakWindow
from focus_capsule.session_view import SessionViewWindow
from focus_capsule.styles import STYLESHEET


class UiReliabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setStyleSheet(STYLESHEET)

    def test_break_window_reports_zero_before_ending_once(self):
        calls = []
        window = BreakWindow(
            1,
            on_tick=lambda remaining: calls.append(("tick", remaining)),
            on_end=lambda: calls.append(("end", None)),
        )
        window._remaining = 1
        window._tick()
        self.app.processEvents()
        self.assertEqual(calls, [("tick", 0), ("end", None)])
        window.cancel()
        window.close()

    def test_session_view_switches_between_focus_and_break_states(self):
        config = FocusConfig(
            whitelist=["code.exe"],
            duration_minutes=25,
            mode="Standard",
            max_esc=2,
            esc_break_minutes=3,
            goal="完成第一稿",
        )
        window = SessionViewWindow(config)
        window.show()
        window.update_from_session(
            SessionUpdate(
                SessionStatus.BREAK,
                60,
                1500,
                1,
                1,
                0,
                "Standard",
                "code.exe",
                179,
            )
        )
        self.app.processEvents()
        self.assertTrue(window._break_panel.isVisible())
        self.assertFalse(window._break_button.isEnabled())
        self.assertEqual(window._ring._state, "break")

        window.update_from_session(
            SessionUpdate(
                SessionStatus.RUNNING,
                61,
                1500,
                1,
                1,
                0,
                "Standard",
                "code.exe",
                0,
            )
        )
        self.app.processEvents()
        self.assertFalse(window._break_panel.isVisible())
        self.assertTrue(window._break_button.isEnabled())
        self.assertEqual(window._ring._state, "running")
        window.finish_and_close()


if __name__ == "__main__":
    unittest.main()
