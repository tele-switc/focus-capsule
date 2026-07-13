"""Unit tests for the schedule_manager module."""

import os
import unittest
from datetime import datetime, timedelta, timezone

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QTime
from PyQt6.QtWidgets import QApplication, QDialog, QTimeEdit, QWidget

from focus_capsule.models import ScheduleRule
from focus_capsule.schedule_manager import (
    ScheduleManager,
    _rule_is_active,
    _seconds_until_next_boundary,
)
from focus_capsule.schedule_panel import SchedulePanel

_CST = timezone(timedelta(hours=8), name="CST")


def make_dt(hour: int, minute: int, second: int = 0) -> datetime:
    """Return a CST datetime on a fixed date for deterministic tests."""
    return datetime(2026, 7, 11, hour, minute, second, tzinfo=_CST)


class RuleIsActiveTests(unittest.TestCase):
    def test_same_day_range_active(self):
        rule = ScheduleRule(start_hour=6, start_minute=0, end_hour=7, end_minute=0)
        self.assertTrue(_rule_is_active(rule, make_dt(6, 30)))
        self.assertTrue(_rule_is_active(rule, make_dt(6, 0)))  # start boundary
        self.assertFalse(_rule_is_active(rule, make_dt(7, 0)))  # end boundary
        self.assertFalse(_rule_is_active(rule, make_dt(8, 0)))

    def test_overnight_range_active(self):
        # 23:00 -> 01:00 wraps past midnight
        rule = ScheduleRule(start_hour=23, start_minute=0, end_hour=1, end_minute=0)
        self.assertTrue(_rule_is_active(rule, make_dt(23, 30)))
        self.assertTrue(_rule_is_active(rule, make_dt(0, 30)))
        self.assertTrue(_rule_is_active(rule, make_dt(0, 59)))
        self.assertFalse(_rule_is_active(rule, make_dt(1, 0)))
        self.assertFalse(_rule_is_active(rule, make_dt(12, 0)))

    def test_start_equals_end_never_active(self):
        rule = ScheduleRule(start_hour=9, start_minute=0, end_hour=9, end_minute=0)
        self.assertFalse(_rule_is_active(rule, make_dt(9, 0)))

    def test_disabled_rule_not_active(self):
        rule = ScheduleRule(
            start_hour=6, start_minute=0, end_hour=7, end_minute=0, enabled=False
        )
        self.assertFalse(_rule_is_active(rule, make_dt(6, 30)))

    def test_aware_utc_input_is_converted_to_cst(self):
        rule = ScheduleRule(start_hour=6, start_minute=0, end_hour=7, end_minute=0)
        utc_time = datetime(2026, 7, 10, 22, 30, tzinfo=timezone.utc)
        self.assertTrue(_rule_is_active(rule, utc_time))


class SecondsUntilBoundaryTests(unittest.TestCase):
    def test_not_active_returns_zero(self):
        rule = ScheduleRule(start_hour=6, start_minute=0, end_hour=7, end_minute=0)
        self.assertEqual(_seconds_until_next_boundary(rule, make_dt(8, 0)), 0)

    def test_same_day_remaining(self):
        rule = ScheduleRule(start_hour=6, start_minute=0, end_hour=7, end_minute=0)
        # At 6:30:00, 30 min remain = 1800 seconds
        self.assertEqual(_seconds_until_next_boundary(rule, make_dt(6, 30, 0)), 1800)

    def test_overnight_remaining_from_before_midnight(self):
        rule = ScheduleRule(start_hour=23, start_minute=0, end_hour=1, end_minute=0)
        # At 23:30:00, 90 minutes remain = 5400 seconds
        self.assertEqual(_seconds_until_next_boundary(rule, make_dt(23, 30, 0)), 5400)

    def test_overnight_remaining_from_after_midnight(self):
        rule = ScheduleRule(start_hour=23, start_minute=0, end_hour=1, end_minute=0)
        # At 00:30:00, 30 minutes remain = 1800 seconds
        self.assertEqual(_seconds_until_next_boundary(rule, make_dt(0, 30, 0)), 1800)


class ScheduleManagerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.parent = QWidget()
        self.manager = ScheduleManager(self.parent)

    def tearDown(self):
        self.manager.stop()

    def test_set_rules_activates_matching(self):
        rule = ScheduleRule(
            start_hour=6, start_minute=0, end_hour=7, end_minute=0,
            whitelisted_apps=["chrome.exe"],
        )
        activated = []
        self.manager.rule_activated.connect(lambda r: activated.append(r))

        # Override china_now temporarily via monkey-patching _rule_is_active
        from focus_capsule import schedule_manager as sm_mod

        original = sm_mod.china_now
        sm_mod.china_now = lambda: make_dt(6, 30)
        try:
            self.manager.set_rules([rule])
        finally:
            sm_mod.china_now = original

        self.assertTrue(self.manager.is_active)
        self.assertEqual(self.manager.active_whitelist(), ["chrome.exe"])
        self.assertEqual(len(activated), 1)

    def test_set_rules_no_match_inactive(self):
        rule = ScheduleRule(
            start_hour=6, start_minute=0, end_hour=7, end_minute=0,
            whitelisted_apps=["chrome.exe"],
        )
        from focus_capsule import schedule_manager as sm_mod

        original = sm_mod.china_now
        sm_mod.china_now = lambda: make_dt(8, 0)
        try:
            self.manager.set_rules([rule])
        finally:
            sm_mod.china_now = original

        self.assertFalse(self.manager.is_active)
        self.assertEqual(self.manager.active_whitelist(), [])

    def test_add_rule_immediate_activation(self):
        from focus_capsule import schedule_manager as sm_mod

        original = sm_mod.china_now
        sm_mod.china_now = lambda: make_dt(9, 30)
        try:
            rule = ScheduleRule(
                start_hour=9, start_minute=0, end_hour=10, end_minute=0,
                whitelisted_apps=["code.exe"],
            )
            activated = []
            self.manager.rule_activated.connect(lambda r: activated.append(r))
            self.manager.add_rule(rule)
        finally:
            sm_mod.china_now = original

        self.assertTrue(self.manager.is_active)
        self.assertEqual(len(activated), 1)

    def test_remove_active_rule_releases(self):
        from focus_capsule import schedule_manager as sm_mod

        original = sm_mod.china_now
        sm_mod.china_now = lambda: make_dt(9, 30)
        try:
            rule = ScheduleRule(
                start_hour=9, start_minute=0, end_hour=10, end_minute=0,
                whitelisted_apps=["code.exe"],
            )
            self.manager.set_rules([rule])
            released = []
            self.manager.rule_released.connect(lambda r: released.append(r))
            self.manager.remove_rule(0)
        finally:
            sm_mod.china_now = original

        self.assertFalse(self.manager.is_active)
        self.assertEqual(len(released), 1)

    def test_is_process_allowed(self):
        rule = ScheduleRule(
            start_hour=9, start_minute=0, end_hour=10, end_minute=0,
            whitelisted_apps=["code.exe", "chrome.exe"],
        )
        from focus_capsule import schedule_manager as sm_mod

        original = sm_mod.china_now
        sm_mod.china_now = lambda: make_dt(9, 30)
        try:
            self.manager.set_rules([rule])
        finally:
            sm_mod.china_now = original

        casefold_normalization = "CODE.EXE"
        self.assertTrue(self.manager.is_process_allowed("code.exe"))
        self.assertTrue(self.manager.is_process_allowed(casefold_normalization))
        self.assertTrue(self.manager.is_process_allowed("chrome.exe"))
        self.assertFalse(self.manager.is_process_allowed("slack.exe"))

    def test_disabled_rule_not_enforced(self):
        rule = ScheduleRule(
            start_hour=9, start_minute=0, end_hour=10, end_minute=0,
            whitelisted_apps=["code.exe"],
            enabled=False,
        )
        self.manager.set_rules([rule])
        self.assertFalse(self.manager.is_active)
        self.assertTrue(self.manager.is_process_allowed("slack.exe"))


class ScheduleRuleModelTests(unittest.TestCase):
    def test_to_dict_round_trip(self):
        rule = ScheduleRule(
            start_hour=6, start_minute=30,
            end_hour=7, end_minute=15,
            whitelisted_apps=["chrome.exe", "code.exe"],
            mode="Deep",
            enabled=True,
            label="晨间浏览",
        )
        data = rule.to_dict()
        restored = ScheduleRule.from_dict(data)
        self.assertEqual(restored.start_hour, 6)
        self.assertEqual(restored.start_minute, 30)
        self.assertEqual(restored.end_hour, 7)
        self.assertEqual(restored.end_minute, 15)
        self.assertEqual(restored.whitelisted_apps, ["chrome.exe", "code.exe"])
        self.assertEqual(restored.mode, "Deep")
        self.assertTrue(restored.enabled)
        self.assertEqual(restored.label, "晨间浏览")

    def test_from_dict_defaults(self):
        rule = ScheduleRule.from_dict({})
        self.assertEqual(rule.start_hour, 0)
        self.assertEqual(rule.mode, "Deep")
        self.assertTrue(rule.enabled)

    def test_from_dict_rejects_invalid_time_and_whitelist_shape(self):
        with self.assertRaises(ValueError):
            ScheduleRule.from_dict({"start_hour": 24})
        with self.assertRaises(ValueError):
            ScheduleRule.from_dict({"whitelisted_apps": "code.exe"})

    def test_from_dict_parses_false_string_and_normalizes_apps(self):
        rule = ScheduleRule.from_dict(
            {
                "enabled": "false",
                "whitelisted_apps": [" CODE.EXE ", "code.exe", ""],
            }
        )
        self.assertFalse(rule.enabled)
        self.assertEqual(rule.whitelisted_apps, ["code.exe"])


class SchedulePanelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.manager = ScheduleManager()
        original_load_rules = SchedulePanel.load_rules
        SchedulePanel.load_rules = lambda panel: panel._manager.set_rules([])
        try:
            self.panel = SchedulePanel(self.manager)
        finally:
            SchedulePanel.load_rules = original_load_rules
        self.panel.save_rules = lambda: None

    def tearDown(self):
        self.manager.stop()
        self.panel.deleteLater()

    def test_multiple_rule_editors_update_the_correct_rule_without_rebuild(self):
        self.manager.set_rules(
            [
                ScheduleRule(9, 0, 10, 0, ["code.exe"]),
                ScheduleRule(14, 0, 15, 0, ["chrome.exe"]),
            ]
        )
        self.panel._refresh_rules_list()
        editors = self.panel._rules_container.findChildren(QTimeEdit)
        first_start = next(editor for editor in editors if editor.time() == QTime(9, 0))

        first_start.setTime(QTime(8, 15))

        rules = self.manager.rules
        self.assertEqual((rules[0].start_hour, rules[0].start_minute), (8, 15))
        self.assertEqual((rules[1].start_hour, rules[1].start_minute), (14, 0))
        self.assertIn(first_start, self.panel._rules_container.findChildren(QTimeEdit))

    def test_new_empty_rule_starts_disabled(self):
        self.manager.set_rules([])
        self.panel._add_rule()
        self.assertEqual(len(self.manager.rules), 1)
        self.assertFalse(self.manager.rules[0].enabled)
        self.assertEqual(self.manager.rules[0].whitelisted_apps, [])

    def test_app_picker_keeps_existing_selection_and_deduplicates_catalog(self):
        import focus_capsule.schedule_panel as panel_module

        self.manager.set_rules(
            [ScheduleRule(9, 0, 10, 0, ["code.exe"], enabled=False)]
        )
        self.panel._installed_by_process = {
            "code.exe": {
                "display_name": "Visual Studio Code",
                "process_name": "code.exe",
                "custom_path": r"C:\Apps\Code.exe",
            }
        }
        captured = {}

        class FakePicker:
            def __init__(self, apps, selected, _parent):
                captured["apps"] = apps
                captured["selected"] = list(selected)

            def exec(self):
                return QDialog.DialogCode.Accepted

            def selected_apps(self):
                return [captured["apps"][0]]

        original_picker = panel_module.InstalledAppPickerDialog
        panel_module.InstalledAppPickerDialog = FakePicker
        try:
            self.panel._edit_rule_apps(0)
        finally:
            panel_module.InstalledAppPickerDialog = original_picker

        processes = [item["process_name"] for item in captured["apps"]]
        self.assertEqual(processes.count("code.exe"), 1)
        self.assertEqual(captured["selected"], ["code.exe"])
        self.assertEqual(self.manager.rules[0].whitelisted_apps, ["code.exe"])


if __name__ == "__main__":
    unittest.main()
