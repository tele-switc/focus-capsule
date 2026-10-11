import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from focus_capsule.process_matching import (
    ProcessIdentity,
    ProcessMatcher,
    same_application_family,
)


class ProcessMatchingTests(unittest.TestCase):
    def test_related_wrapper_and_foreground_process_share_app_family(self):
        with tempfile.TemporaryDirectory() as temporary:
            app_root = Path(temporary) / "Vendor" / "DesktopEditors"
            launcher = app_root / "DesktopEditors.exe"
            foreground = app_root / "editors.exe"

            self.assertTrue(same_application_family(str(launcher), str(foreground)))

    def test_unrelated_suite_apps_are_not_treated_as_same_app(self):
        with tempfile.TemporaryDirectory() as temporary:
            suite_root = Path(temporary) / "Vendor" / "OfficeSuite"
            word = suite_root / "word.exe"
            sheet = suite_root / "spreadsheet.exe"

            self.assertFalse(same_application_family(str(word), str(sheet)))

    def test_broad_install_root_never_grants_access(self):
        program_files = os.environ.get("ProgramFiles")
        if not program_files:
            self.skipTest("ProgramFiles is unavailable")
        selected = Path(program_files) / "ProductA" / "product.exe"
        foreground = Path(program_files) / "ProductB" / "product.exe"

        self.assertFalse(same_application_family(str(selected), str(foreground)))

    def test_matcher_learns_verified_runtime_alias_for_session(self):
        with tempfile.TemporaryDirectory() as temporary:
            app_root = Path(temporary) / "Vendor" / "DesktopEditors"
            launcher = app_root / "DesktopEditors.exe"
            foreground = app_root / "editors.exe"
            matcher = ProcessMatcher(
                ["desktopeditors.exe"],
                {"desktopeditors.exe": str(launcher)},
            )

            self.assertTrue(matcher.is_allowed("editors.exe", str(foreground)))
            self.assertTrue(matcher.is_allowed("editors.exe"))
            self.assertIn("editors.exe", matcher.learned_aliases["desktopeditors.exe"])

    def test_main_executable_allows_a_sibling_generic_launcher(self):
        with tempfile.TemporaryDirectory() as temporary:
            app_root = Path(temporary) / "Vendor" / "Anki"
            selected = app_root / "anki.exe"
            launcher = app_root / "launcher.exe"

            self.assertTrue(same_application_family(str(selected), str(launcher)))

    def test_generic_runtime_is_allowed_only_through_selected_live_ancestor(self):
        selected = r"C:\Users\Example\AppData\Local\Programs\Anki\anki.exe"
        runtime = (
            r"C:\Users\Example\AppData\Local\AnkiProgramFiles\python"
            r"\cpython-3.13.5-windows-x86_64-none\pythonw.exe"
        )
        unrelated_runtime = r"C:\Tools\OtherApp\pythonw.exe"
        matcher = ProcessMatcher(
            ["anki.exe"],
            {"anki.exe": selected},
        )
        lineage = (
            ProcessIdentity("pythonw.exe", runtime, 300),
            ProcessIdentity("pythonw.exe", r"C:\AnkiProgramFiles\.venv\pythonw.exe", 200),
            ProcessIdentity("anki.exe", selected, 100),
        )

        with patch(
            "focus_capsule.process_matching._process_lineage",
            return_value=lineage,
        ):
            self.assertTrue(matcher.is_allowed("pythonw.exe", runtime, 300))

        self.assertEqual(matcher.matched_app, "anki.exe")
        self.assertIn(
            os.path.normcase(os.path.abspath(runtime)),
            matcher.learned_runtime_paths["anki.exe"],
        )
        self.assertTrue(matcher.is_allowed("pythonw.exe", runtime))
        self.assertFalse(matcher.is_allowed("pythonw.exe", unrelated_runtime))

    def test_generic_runtime_without_selected_ancestor_remains_blocked(self):
        selected = r"C:\Users\Example\AppData\Local\Programs\Anki\anki.exe"
        runtime = r"C:\Tools\OtherApp\pythonw.exe"
        matcher = ProcessMatcher(
            ["anki.exe"],
            {"anki.exe": selected},
        )
        lineage = (
            ProcessIdentity("pythonw.exe", runtime, 300),
            ProcessIdentity("other-launcher.exe", r"C:\Tools\OtherApp\launcher.exe", 200),
        )

        with patch(
            "focus_capsule.process_matching._process_lineage",
            return_value=lineage,
        ):
            self.assertFalse(matcher.is_allowed("pythonw.exe", runtime, 300))

    def test_same_process_name_at_unrelated_path_does_not_bypass_saved_path(self):
        matcher = ProcessMatcher(
            ["anki.exe"],
            {"anki.exe": r"C:\Apps\Anki\anki.exe"},
        )

        self.assertFalse(
            matcher.is_allowed("anki.exe", r"C:\Unrelated\anki.exe")
        )


if __name__ == "__main__":
    unittest.main()
