import unittest
from pathlib import Path


class WindowsPackagingTests(unittest.TestCase):
    def test_shortcut_resolver_runtime_dependencies_are_bundled(self):
        project_root = Path(__file__).resolve().parents[1]
        spec = (project_root / "packaging" / "Focus Capsule.windows.spec").read_text(
            encoding="utf-8"
        )
        for module_name in (
            "pythoncom",
            "pywintypes",
            "win32timezone",
            "win32com.client",
            "win32com.shell.shell",
            "win32com.shell.shellcon",
        ):
            self.assertIn(f'"{module_name}"', spec)


if __name__ == "__main__":
    unittest.main()
