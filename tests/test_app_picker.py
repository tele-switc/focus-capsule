import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QApplication, QDialog

from focus_capsule.models import FocusConfig
from focus_capsule.settings_panel import (
    MAX_FOCUS_MINUTES,
    MIN_FOCUS_MINUTES,
    InstalledAppPickerDialog,
    SettingsPanel,
)


class InstalledAppPickerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    @staticmethod
    def _catalog(root: Path) -> list[dict]:
        apps = []
        for index in range(14):
            process = "chrome.exe" if index == 0 else f"app{index:02}.exe"
            path = root / process
            path.write_bytes(b"")
            apps.append(
                {
                    "display_name": "Google Chrome" if index == 0 else f"App {index:02}",
                    "process_name": process,
                    "custom_path": str(path),
                }
            )
        apps.append(
            {
                "display_name": "Missing Word",
                "process_name": "winword.exe",
                "custom_path": str(root / "missing" / "winword.exe"),
            }
        )
        return apps

    def _new_panel(self, catalog: list[dict]) -> SettingsPanel:
        with (
            patch("focus_capsule.settings_panel.discover_installed_apps", return_value=catalog),
            patch.object(SettingsPanel, "load_config", return_value=FocusConfig()),
        ):
            return SettingsPanel()

    def test_main_grid_contains_only_installed_common_apps(self):
        with tempfile.TemporaryDirectory() as temporary:
            catalog = self._catalog(Path(temporary))
            panel = self._new_panel(catalog)

            self.assertEqual(len(panel._chip_widgets), 1)
            self.assertIn("chrome.exe", panel._chip_widgets)
            self.assertNotIn("winword.exe", panel._chip_widgets)
            self.assertEqual(len(panel._remaining_installed_apps()), 13)
            self.assertIn("（13）", panel._other_apps_button.text())
            panel.close()

    def test_custom_duration_accepts_arbitrary_positive_minutes(self):
        panel = self._new_panel([])
        panel._custom_min_spin.setValue(37)
        self.assertEqual(panel.get_config().duration_minutes, 37)

        panel._apply_config(FocusConfig(duration_minutes=10_080), emit=False)
        self.assertEqual(panel._custom_min_spin.value(), 10_080)

        panel._apply_config(FocusConfig(duration_minutes=0), emit=False)
        self.assertEqual(panel._custom_min_spin.value(), MIN_FOCUS_MINUTES)

        panel._apply_config(
            FocusConfig(duration_minutes=MAX_FOCUS_MINUTES + 1), emit=False
        )
        self.assertEqual(panel._custom_min_spin.value(), MAX_FOCUS_MINUTES)
        panel.close()

    def test_picker_filters_icons_and_keeps_selection_staged(self):
        apps = [
            {
                "display_name": "Alpha Writer",
                "process_name": "alpha.exe",
                "custom_path": r"C:\Apps\Alpha\alpha.exe",
            },
            {
                "display_name": "Beta Browser",
                "process_name": "beta.exe",
                "custom_path": r"C:\Apps\Beta\beta.exe",
            },
        ]
        dialog = InstalledAppPickerDialog(apps, ())

        dialog._search.setText("browser")
        self.app.processEvents()
        self.assertTrue(dialog._tiles[0].isHidden())
        self.assertFalse(dialog._tiles[1].isHidden())

        dialog._tiles[1].click()
        chosen = dialog.selected_apps()
        self.assertEqual([item["process_name"] for item in chosen], ["beta.exe"])
        self.assertEqual(dialog.result(), 0)
        dialog.reject()
        dialog.close()

    def test_picker_preserves_independent_icon_resource_metadata(self):
        apps = [
            {
                "display_name": "OneDrive",
                "process_name": "onedrive.exe",
                "custom_path": r"C:\Apps\OneDrive.exe",
                "icon_source": r"C:\Icons\OneDrive.exe",
                "icon_index": 1,
                "app_user_model_id": "Microsoft.SkyDrive.Desktop!App",
            }
        ]
        pixmap = QPixmap(44, 44)
        with patch("focus_capsule.settings_panel.app_pixmap", return_value=pixmap) as rendered:
            dialog = InstalledAppPickerDialog(apps, ())

        self.assertEqual(dialog._tiles[0]._icon_source, r"C:\Icons\OneDrive.exe")
        self.assertEqual(dialog._tiles[0]._icon_index, 1)
        self.assertEqual(rendered.call_args.kwargs["icon_source"], r"C:\Icons\OneDrive.exe")
        self.assertEqual(rendered.call_args.kwargs["icon_index"], 1)

        dialog._tiles[0].click()
        self.assertEqual(dialog.selected_apps(), apps)
        dialog.close()

    def test_picker_can_manually_add_a_real_executable_without_duplicates(self):
        with tempfile.TemporaryDirectory() as temporary:
            executable = Path(temporary) / "Custom Tool.exe"
            executable.write_bytes(b"")
            dialog = InstalledAppPickerDialog([], ())

            with patch(
                "focus_capsule.settings_panel.QFileDialog.getOpenFileNames",
                return_value=([str(executable), str(executable)], ""),
            ):
                dialog._browse_apps()

            self.assertEqual(len(dialog._tiles), 1)
            self.assertEqual(dialog._tiles[0].process_name, "custom tool.exe")
            self.assertTrue(dialog._tiles[0].isChecked())
            self.assertEqual(
                dialog.selected_apps(),
                [
                    {
                        "display_name": "Custom Tool",
                        "process_name": "custom tool.exe",
                        "custom_path": str(executable),
                    }
                ],
            )
            self.assertTrue(dialog._add_button.isEnabled())
            dialog.close()

    def test_picker_reports_a_stale_manual_path(self):
        dialog = InstalledAppPickerDialog([], ())
        missing = r"Z:\missing\stale.exe"
        with (
            patch(
                "focus_capsule.settings_panel.QFileDialog.getOpenFileNames",
                return_value=([missing], ""),
            ),
            patch("focus_capsule.settings_panel.QMessageBox.warning") as warning,
        ):
            dialog._browse_apps()

        self.assertEqual(dialog.selected_apps(), [])
        warning.assert_called_once()
        dialog.close()

    def test_confirmed_other_app_is_pinned_selected_and_restored(self):
        with tempfile.TemporaryDirectory() as temporary:
            catalog = self._catalog(Path(temporary))
            panel = self._new_panel(catalog)
            extra = panel._remaining_installed_apps()[0]

            class AcceptedPicker:
                def __init__(self, *_args, **_kwargs):
                    pass

                def exec(self):
                    return QDialog.DialogCode.Accepted

                def selected_apps(self):
                    return [extra]

            with (
                patch("focus_capsule.settings_panel.InstalledAppPickerDialog", AcceptedPicker),
                patch.object(panel, "_emit_config_changed") as emitted,
            ):
                panel._open_app_picker()

            process = str(extra["process_name"])
            self.assertIn(process, panel._chip_widgets)
            self.assertTrue(panel._chip_widgets[process].isChecked())
            self.assertIn(process, panel._whitelist)
            self.assertIn(str(extra["custom_path"]), panel._custom_apps)
            emitted.assert_called_once()

            saved = panel.get_config()
            restored = self._new_panel(catalog)
            restored._apply_config(saved, emit=False)
            self.assertIn(process, restored._chip_widgets)
            self.assertTrue(restored._chip_widgets[process].isChecked())
            self.assertEqual(restored._display_name_for(process), extra["display_name"])

            restored.close()
            panel.close()


if __name__ == "__main__":
    unittest.main()
