# -*- mode: python ; coding: utf-8 -*-
import os
from pathlib import Path
import sys


if sys.platform != "darwin":
    raise SystemExit("Focus Capsule.macos.spec must be built on macOS")

ROOT = Path(SPECPATH).resolve().parent
ENTRY = ROOT / "focus_capsule" / "app.py"
ICON = ROOT / "assets" / "FocusCapsule.icns"
VERSION = (ROOT / "packaging" / "version.txt").read_text(encoding="utf-8").strip()
ENTITLEMENTS = ROOT / "packaging" / "macos.entitlements"

for required in (ENTRY, ICON, ENTITLEMENTS):
    if not required.exists():
        raise SystemExit(f"Missing build input: {required}")

codesign_identity = os.environ.get("MACOS_CODESIGN_IDENTITY") or None
target_arch = os.environ.get("PYINSTALLER_ARCH") or None

a = Analysis(
    [str(ENTRY)],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pystray", "win32gui", "win32process"],
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
    argv_emulation=False,
    target_arch=target_arch,
    codesign_identity=codesign_identity,
    entitlements_file=str(ENTITLEMENTS),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="Focus Capsule",
)

app = BUNDLE(
    coll,
    name="Focus Capsule.app",
    icon=str(ICON),
    bundle_identifier="com.focuscapsule.desktop",
    version=VERSION,
    info_plist={
        "CFBundleDisplayName": "Focus Capsule",
        "CFBundleName": "Focus Capsule",
        "CFBundleShortVersionString": VERSION,
        "CFBundleVersion": VERSION,
        "LSApplicationCategoryType": "public.app-category.productivity",
        "LSMinimumSystemVersion": "11.0",
        "NSHighResolutionCapable": True,
        "NSPrincipalClass": "NSApplication",
    },
)
