# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
import sys


if sys.platform != "win32":
    raise SystemExit("Focus Capsule.windows.spec must be built on Windows")

ROOT = Path(SPECPATH).resolve().parent
ENTRY = ROOT / "focus_capsule" / "app.py"
ICON = ROOT / "assets" / "focus-capsule.ico"
VERSION_INFO = ROOT / "packaging" / "windows-version-info.txt"

for required in (ENTRY, ICON, VERSION_INFO):
    if not required.exists():
        raise SystemExit(f"Missing build input: {required}")

a = Analysis(
    [str(ENTRY)],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[],
    hiddenimports=[
        "pythoncom",
        "pywintypes",
        "win32timezone",
        "win32com.client",
        "win32com.shell",
        "win32com.shell.shell",
        "win32com.shell.shellcon",
        "urllib.request",
        "urllib.parse",
        "urllib.error",
        "http.client",
        "focus_capsule.ui",
        "focus_capsule.ui.components",
        "focus_capsule.ui.components.precision_stage_bar",
        # Explicitly include all focus_capsule submodules
        "focus_capsule.data_models",
        "focus_capsule.data_store",
        "focus_capsule.settings_panel",
        "focus_capsule.main_window",
        "focus_capsule.styles",
        "focus_capsule.trend_page",
        "focus_capsule.calendar_page",
        "focus_capsule.history_window",
        "focus_capsule.session_view",
        "focus_capsule.schedule_panel",
        "focus_capsule.overlay",
        "focus_capsule.controller",
        "focus_capsule.monitor",
        "focus_capsule.dialogs",
        "focus_capsule.schedule_manager",
        "focus_capsule.ambient_background",
        "focus_capsule.trend_service",
        "focus_capsule.ai_report_service",
        "focus_capsule.widgets",
        "focus_capsule.daily_goal_page",
        "focus_capsule.icon_utils",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pystray"],
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Focus Capsule",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    icon=str(ICON),
    version=str(VERSION_INFO),
    uac_admin=False,
    uac_uiaccess=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="Focus Capsule",
)
