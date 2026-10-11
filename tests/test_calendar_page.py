import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QCoreApplication, QEvent
from PyQt6.QtWidgets import QApplication, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from focus_capsule.calendar_page import CalendarPage, _format_metric_minutes


class CalendarDetailLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_compact_metric_duration_avoids_wide_spaced_headline(self):
        self.assertEqual(_format_metric_minutes(91), "1小时31分钟")
        self.assertEqual(_format_metric_minutes(120), "2小时")
        self.assertEqual(_format_metric_minutes(2), "2分钟")

    def test_clear_layout_removes_widgets_inside_nested_usage_rows(self):
        container = QWidget()
        usage_layout = QVBoxLayout(container)
        row = QHBoxLayout()
        app_name = QLabel("OpenCode")
        duration = QLabel("2 分钟")
        row.addWidget(app_name)
        row.addWidget(duration)
        usage_layout.addLayout(row)

        CalendarPage._clear_layout(usage_layout)

        self.assertEqual(usage_layout.count(), 0)
        self.assertTrue(app_name.isHidden())
        self.assertTrue(duration.isHidden())
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        container.close()


if __name__ == "__main__":
    unittest.main()
