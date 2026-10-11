import os
import struct
import tempfile
import unittest
from pathlib import Path

from focus_capsule.icon_utils import (
    _appx_manifest_entry,
    _choose_primary_executable,
    _finalize_catalog,
    _is_blocked_catalog_path,
    _is_catalog_component,
    _parse_display_icon_path,
    _parse_icon_location,
    _windows_catalog_candidate,
    _windows_pe_subsystem,
    resolve_windows_app_target,
)


def _write_fake_pe(path: Path, subsystem: int = 2) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = bytearray(256)
    payload[:2] = b"MZ"
    struct.pack_into("<I", payload, 0x3C, 0x80)
    payload[0x80:0x84] = b"PE\x00\x00"
    struct.pack_into("<H", payload, 0x80 + 24 + 68, subsystem)
    path.write_bytes(payload)


class IconCatalogHelperTests(unittest.TestCase):
    def test_component_filter_checks_display_process_and_path(self):
        self.assertFalse(
            _is_catalog_component(
                "Visual Studio Code",
                "code.exe",
                r"C:\Program Files\Microsoft VS Code\Code.exe",
            )
        )
        self.assertFalse(
            _is_catalog_component(
                "Inno Setup Compiler",
                "Compil32.exe",
                r"C:\Program Files (x86)\Inno Setup 6\Compil32.exe",
            )
        )
        self.assertTrue(
            _is_catalog_component(
                "Microsoft OneDrive",
                "OneDriveSetup.exe",
                r"C:\Program Files\Microsoft OneDrive\OneDriveSetup.exe",
            )
        )
        self.assertTrue(
            _is_catalog_component(
                "FormatFactory",
                "uninstall.exe",
                r"C:\Program Files\FormatFactory\uninstall.exe",
            )
        )
        self.assertTrue(
            _is_catalog_component(
                "Example App",
                "example.exe",
                r"C:\Program Files\Example\Updater\example.exe",
            )
        )
        self.assertTrue(
            _is_catalog_component(
                "GitHub",
                "chrome_proxy.exe",
                r"C:\Program Files\Google\Chrome\Application\chrome_proxy.exe",
            )
        )
        self.assertTrue(
            _is_catalog_component(
                "Nahimic Companion",
                "nahimicNotifSys.exe",
                r"C:\Apps\Nahimic\nahimicNotifSys.exe",
            )
        )
        self.assertTrue(
            _is_catalog_component(
                "AMD Software",
                "AMDSoftwareCompatibilityTool.exe",
                r"C:\Program Files\AMD\AMDSoftwareCompatibilityTool.exe",
            )
        )
        self.assertTrue(
            _is_catalog_component(
                "AMD Software",
                "AMDCleanupUtility.exe",
                r"C:\Program Files\AMD\AMDCleanupUtility.exe",
            )
        )
        self.assertTrue(
            _is_catalog_component(
                "WSL",
                "wslhost.exe",
                r"C:\Program Files\WSL\wslhost.exe",
            )
        )
        self.assertTrue(
            _is_catalog_component(
                "AMD Software",
                "AMDInstallUEP.exe",
                r"C:\Program Files\AMD\CIM\BIN64\AMDInstallUEP.exe",
            )
        )
        self.assertTrue(
            _is_catalog_component(
                "AMD Software",
                "AMDSplashScreen.exe",
                r"C:\Program Files\AMD\CIM\BIN64\AMDSplashScreen.exe",
            )
        )
        self.assertTrue(
            _is_catalog_component(
                "AMD Software",
                "InstallManagerApp.exe",
                r"C:\Program Files\AMD\CIM\BIN64\InstallManagerApp.exe",
            )
        )
        self.assertTrue(
            _is_catalog_component(
                "WSL",
                "wslrelay.exe",
                r"C:\Program Files\WSL\wslrelay.exe",
            )
        )
        self.assertTrue(
            _is_catalog_component(
                "Windows Package Manager Server",
                "WindowsPackageManagerServer.exe",
                r"C:\Program Files\WindowsApps\WindowsPackageManagerServer.exe",
            )
        )
        self.assertTrue(
            _is_catalog_component(
                "Office component",
                "msoasb.exe",
                r"C:\Program Files\Microsoft Office\Root\Office16\msoasb.exe",
            )
        )
        self.assertTrue(
            _is_catalog_component(
                "Windows Terminal alias",
                "wt.exe",
                r"C:\Program Files\WindowsApps\Microsoft.WindowsTerminal\wt.exe",
            )
        )

    def test_blocked_path_rejects_dependency_and_cache_trees(self):
        self.assertTrue(
            _is_blocked_catalog_path(
                os.path.join("project", "node_modules", "electron", "electron.exe")
            )
        )
        self.assertTrue(
            _is_blocked_catalog_path(os.path.join("ProgramData", "Package Cache", "installer.exe"))
        )

    def test_pe_subsystem_distinguishes_gui_from_console(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            gui_path = Path(temporary_directory) / "gui.exe"
            console_path = Path(temporary_directory) / "console.exe"

            for path, subsystem in ((gui_path, 2), (console_path, 3)):
                _write_fake_pe(path, subsystem)

            self.assertEqual(_windows_pe_subsystem(str(gui_path)), 2)
            self.assertEqual(_windows_pe_subsystem(str(console_path)), 3)

    def test_launcher_maps_to_monitor_visible_gui_process(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temporary_directory:
            install_root = Path(temporary_directory) / "DingDing"
            launcher = install_root / "DingtalkLauncher.exe"
            foreground_app = install_root / "main" / "current" / "DingTalk.exe"
            updater = install_root / "main" / "current" / "DingTalkUpdater.exe"
            _write_fake_pe(launcher)
            _write_fake_pe(foreground_app)
            _write_fake_pe(updater)

            candidate = _windows_catalog_candidate(
                "钉钉",
                str(launcher),
                0,
                "DingTalk.exe",
            )

            self.assertIsNotNone(candidate)
            self.assertEqual(candidate["display_name"], "钉钉")
            self.assertEqual(candidate["process_name"], "dingtalk.exe")
            self.assertEqual(
                os.path.normcase(candidate["custom_path"]),
                os.path.normcase(str(foreground_app.resolve())),
            )
            self.assertEqual(
                os.path.normcase(resolve_windows_app_target(str(launcher), "钉钉")),
                os.path.normcase(str(foreground_app.resolve())),
            )

    def test_onlyoffice_launcher_maps_to_foreground_editor(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temporary_directory:
            install_root = Path(temporary_directory) / "ONLYOFFICE" / "DesktopEditors"
            launcher = install_root / "DesktopEditors.exe"
            foreground_app = install_root / "editors.exe"
            _write_fake_pe(launcher)
            _write_fake_pe(foreground_app)

            self.assertEqual(
                os.path.normcase(resolve_windows_app_target(str(launcher), "ONLYOFFICE")),
                os.path.normcase(str(foreground_app.resolve())),
            )

    def test_trusted_launcher_admits_windowed_console_but_not_updater(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temporary_directory:
            install_root = Path(temporary_directory) / "DingDing"
            launcher = install_root / "DingtalkLauncher.exe"
            foreground_app = install_root / "main" / "current" / "DingTalk.exe"
            updater = install_root / "main" / "current" / "DingTalkUpdater.exe"
            _write_fake_pe(launcher)
            _write_fake_pe(foreground_app, subsystem=3)
            _write_fake_pe(updater)

            candidate = _windows_catalog_candidate("钉钉", str(launcher), 0)
            self.assertIsNotNone(candidate)
            self.assertEqual(candidate["process_name"], "dingtalk.exe")
            self.assertNotEqual(candidate["custom_path"], str(updater))

            # A blind Program Files crawl is not a trusted indication that a
            # console-subsystem binary is a user-facing desktop application.
            self.assertIsNone(_windows_catalog_candidate("钉钉", str(launcher), 3))

    def test_known_install_layout_uses_launcher_identity_for_main_app(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temporary_directory:
            install_root = Path(temporary_directory) / "DingDing"
            launcher = install_root / "DingtalkLauncher.exe"
            foreground_app = install_root / "main" / "current" / "DingTalk.exe"
            _write_fake_pe(launcher)
            _write_fake_pe(foreground_app)

            selected = _choose_primary_executable(
                str(install_root),
                "DingDing",
                require_name_match=True,
            )

            self.assertIsNotNone(selected)
            self.assertEqual(
                os.path.normcase(str(selected.resolve())),
                os.path.normcase(str(foreground_app.resolve())),
            )

    def test_finalize_prefers_priority_then_sorts_and_deduplicates(self):
        candidates = [
            {
                "display_name": "Registry Chrome",
                "process_name": "chrome.exe",
                "custom_path": r"C:\Registry\chrome.exe",
                "_priority": 2,
            },
            {
                "display_name": "Google Chrome",
                "process_name": "CHROME.EXE",
                "custom_path": r"C:\StartMenu\chrome.exe",
                "icon_source": r"C:\StartMenu\chrome.ico",
                "icon_index": 2,
                "_priority": 0,
            },
            {
                "display_name": "Alpha Editor",
                "process_name": "alpha.exe",
                "custom_path": r"C:\Apps\alpha.exe",
                "_priority": 1,
            },
            {
                "display_name": "Updater",
                "process_name": "update.exe",
                "custom_path": r"C:\Apps\update.exe",
                "_priority": 0,
            },
        ]

        result = _finalize_catalog(candidates)

        self.assertEqual(
            [item["display_name"] for item in result],
            ["Google Chrome", "Alpha Editor"],
        )
        self.assertEqual(result[0]["process_name"], "CHROME.EXE")
        self.assertEqual(result[0]["icon_source"], r"C:\StartMenu\chrome.ico")
        self.assertEqual(result[0]["icon_index"], 2)
        self.assertNotIn("_priority", result[0])

    def test_display_icon_parser_preserves_quoted_paths_and_removes_index(self):
        self.assertEqual(
            _parse_display_icon_path(r'"C:\Program Files\App\App.exe",-2'),
            r"C:\Program Files\App\App.exe",
        )
        self.assertEqual(
            _parse_display_icon_path(r"C:\Apps\App.exe,0"),
            r"C:\Apps\App.exe",
        )
        self.assertEqual(
            _parse_icon_location(r'"C:\Program Files\App\icons.dll",-27'),
            (r"C:\Program Files\App\icons.dll", -27),
        )

    def test_appx_manifest_maps_aumid_to_executable_and_best_logo(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temporary_directory:
            package = Path(temporary_directory) / "Example.Package_1.0_x64__publisher"
            executable = package / "app" / "Example.exe"
            assets = package / "Assets"
            _write_fake_pe(executable)
            assets.mkdir(parents=True)
            (assets / "Square44x44Logo.targetsize-48_altform-unplated.png").write_bytes(b"48")
            preferred_logo = assets / "Square44x44Logo.targetsize-64_altform-unplated.png"
            preferred_logo.write_bytes(b"64")
            (assets / "Square44x44Logo.scale-400.png").write_bytes(b"176")
            (package / "AppxManifest.xml").write_text(
                """<?xml version="1.0" encoding="utf-8"?>
                <Package xmlns="http://schemas.microsoft.com/appx/manifest/foundation/windows10"
                         xmlns:uap="http://schemas.microsoft.com/appx/manifest/uap/windows10">
                  <Applications>
                    <Application Id="Main" Executable="app/Example.exe" EntryPoint="Example.App">
                      <uap:VisualElements DisplayName="Example"
                          Square44x44Logo="Assets/Square44x44Logo.png" />
                    </Application>
                  </Applications>
                </Package>
                """,
                encoding="utf-8",
            )

            resolved = _appx_manifest_entry(
                str(package),
                "Example.Package_publisher!Main",
            )

            self.assertIsNotNone(resolved)
            resolved_executable, resolved_logo = resolved
            self.assertEqual(resolved_executable, executable.resolve())
            self.assertEqual(Path(resolved_logo), preferred_logo)


if __name__ == "__main__":
    unittest.main()
