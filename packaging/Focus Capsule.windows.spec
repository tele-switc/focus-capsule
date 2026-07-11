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
    hiddenimports=[],
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
