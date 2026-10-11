"""Extract application icons for display in the settings panel.

On Windows, icons are extracted from .exe files via the shell API (SHGetFileInfo).
Falls back to a coloured monogram when the icon can't be resolved.
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes
import os
import plistlib
import re
import struct
import sys
import xml.etree.ElementTree as ET
from collections.abc import Iterable
from pathlib import Path

from PyQt6.QtCore import QFileInfo, QSize, Qt
from PyQt6.QtGui import QColor, QFont, QIcon, QImage, QPainter, QPen, QPixmap

_ICON_CACHE: dict[str, QIcon] = {}
_DEFAULT_ICON: QIcon | None = None

DEFAULT_ICON_SIZE = 40

_MAC_APP_PATHS = {
    "safari": "/Applications/Safari.app",
    "google chrome": "/Applications/Google Chrome.app",
    "firefox": "/Applications/Firefox.app",
    "visual studio code": "/Applications/Visual Studio Code.app",
    "microsoft word": "/Applications/Microsoft Word.app",
    "microsoft excel": "/Applications/Microsoft Excel.app",
    "microsoft outlook": "/Applications/Microsoft Outlook.app",
    "slack": "/Applications/Slack.app",
    "terminal": "/System/Applications/Utilities/Terminal.app",
    "iterm2": "/Applications/iTerm.app",
    "pycharm": "/Applications/PyCharm.app",
    "microsoft edge": "/Applications/Microsoft Edge.app",
}


def _default_icon() -> QIcon:
    global _DEFAULT_ICON
    if _DEFAULT_ICON is not None:
        return _DEFAULT_ICON
    from PyQt6.QtWidgets import QApplication, QStyle

    app = QApplication.instance()
    style = app.style() if app else None
    if style:
        candidate = style.standardIcon(QStyle.StandardPixmap.SP_FileIcon)
        if not candidate.isNull():
            _DEFAULT_ICON = candidate
    if _DEFAULT_ICON is None:
        _DEFAULT_ICON = _monogram_icon("?")
    return _DEFAULT_ICON


# ---------------------------------------------------------------------------
# Windows icon extraction
# ---------------------------------------------------------------------------


class _SHFILEINFO(ctypes.Structure):
    _fields_ = [
        ("hIcon", ctypes.wintypes.HICON),
        ("iIcon", ctypes.c_int),
        ("dwAttributes", ctypes.wintypes.DWORD),
        ("szDisplayName", ctypes.c_wchar * 260),
        ("szTypeName", ctypes.c_wchar * 80),
    ]


def _extract_icon_windows(filepath: str) -> QIcon:
    """Extract a sharp executable icon, falling back to the Windows shell."""
    embedded = _extract_icon_resource_windows(filepath)
    if not embedded.isNull():
        return embedded

    # QFileIconProvider delegates to the Windows shell and returns a
    # device-pixel-ratio-aware icon. It is both sharper and more reliable than
    # manually wrapping a single small HICON when no embedded resource exists.
    try:
        from PyQt6.QtWidgets import QFileIconProvider

        native_icon = QFileIconProvider().icon(QFileInfo(filepath))
        if not native_icon.isNull():
            return native_icon
    except Exception:
        pass

    SHGFI_ICON = 0x000000100
    SHGFI_LARGEICON = 0x000000000
    flags = SHGFI_ICON | SHGFI_LARGEICON

    info = _SHFILEINFO()
    result = ctypes.windll.shell32.SHGetFileInfoW(
        filepath, 0, ctypes.byref(info), ctypes.sizeof(info), flags
    )
    if not result or not info.hIcon:
        return _monogram_icon(Path(filepath).stem)

    user32 = ctypes.windll.user32
    try:
        image = QImage.fromHICON(int(info.hIcon))
        pixmap = QPixmap.fromImage(image)
    except Exception:
        user32.DestroyIcon(info.hIcon)
        return _monogram_icon(Path(filepath).stem)
    user32.DestroyIcon(info.hIcon)

    if pixmap.isNull():
        return _monogram_icon(Path(filepath).stem)
    return QIcon(pixmap)


def _extract_icon_resource_windows(filepath: str, icon_index: int = 0) -> QIcon:
    """Extract multiple icon sizes from an EXE/DLL/ICO resource.

    ``PrivateExtractIconsW`` accepts both ordinary zero-based icon indexes and
    the negative resource identifiers commonly stored by Windows shortcuts.
    Keeping several physical sizes prevents the 48 px shell icon from being
    enlarged on 150%/200% displays.
    """
    if os.name != "nt" or not Path(filepath).is_file():
        return QIcon()

    try:
        extractor = ctypes.windll.user32.PrivateExtractIconsW
        extractor.argtypes = [
            ctypes.wintypes.LPCWSTR,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.POINTER(ctypes.wintypes.HICON),
            ctypes.POINTER(ctypes.wintypes.UINT),
            ctypes.wintypes.UINT,
            ctypes.wintypes.UINT,
        ]
        extractor.restype = ctypes.wintypes.UINT
    except (AttributeError, OSError):
        return QIcon()

    result_icon = QIcon()
    invalid_count = ctypes.wintypes.UINT(-1).value
    for physical_size in (16, 24, 32, 48, 64, 96, 128, 256):
        handle = ctypes.wintypes.HICON()
        resource_id = ctypes.wintypes.UINT()
        try:
            extracted = extractor(
                str(filepath),
                int(icon_index),
                physical_size,
                physical_size,
                ctypes.byref(handle),
                ctypes.byref(resource_id),
                1,
                0,
            )
            if extracted in (0, invalid_count) or not handle.value:
                continue
            image = QImage.fromHICON(int(handle.value))
            pixmap = QPixmap.fromImage(image)
            if not pixmap.isNull():
                result_icon.addPixmap(pixmap)
        except Exception:
            continue
        finally:
            if handle.value:
                ctypes.windll.user32.DestroyIcon(handle)
    return result_icon


def _icon_from_extracticon(filepath: str, icon_index: int = 0) -> QIcon:
    """Backward-compatible wrapper for callers of the old helper."""
    icon = _extract_icon_resource_windows(filepath, icon_index)
    return icon if not icon.isNull() else _monogram_icon(Path(filepath).stem)


def _windows_shortcut_details(lnk_path: str) -> tuple[str, str, int]:
    """Return a shortcut's target plus its independent icon locator."""
    if os.name != "nt" or not lnk_path.casefold().endswith(".lnk"):
        return lnk_path, "", 0
    initialized = False
    try:
        import pythoncom
        from win32com.shell import shell

        pythoncom.CoInitialize()
        initialized = True
        shortcut = pythoncom.CoCreateInstance(
            shell.CLSID_ShellLink,
            None,
            pythoncom.CLSCTX_INPROC_SERVER,
            shell.IID_IShellLink,
        )
        shortcut.QueryInterface(pythoncom.IID_IPersistFile).Load(str(lnk_path))
        target = str(shortcut.GetPath(0)[0] or "")
        icon_source, icon_index = shortcut.GetIconLocation()
        icon_source = os.path.expandvars(str(icon_source or "").strip().strip('"'))
        if icon_source and not os.path.isabs(icon_source):
            relative_source = Path(lnk_path).parent / icon_source
            if relative_source.is_file():
                icon_source = str(relative_source)
        if icon_source and not Path(icon_source).is_file():
            icon_source = ""
            icon_index = 0
        return target or lnk_path, icon_source, int(icon_index or 0)
    except Exception:
        return lnk_path, "", 0
    finally:
        if initialized:
            try:
                pythoncom.CoUninitialize()
            except Exception:
                pass


def resolve_windows_shortcut(lnk_path: str) -> str:
    """Resolve a Windows shortcut and return its executable target."""
    return _windows_shortcut_details(lnk_path)[0]


def windows_shortcut_details(lnk_path: str) -> tuple[str, str, int]:
    """Public shortcut resolver returning target, icon source, and icon index."""
    return _windows_shortcut_details(lnk_path)


# Backward-compatible private alias.
_resolve_lnk = resolve_windows_shortcut


def _find_exe_path(process_name: str) -> str | None:
    """Find the full path of a .exe by scanning common install locations."""
    base = process_name.lower()
    if not base.endswith(".exe"):
        base += ".exe"

    candidates: list[str] = []

    program_dirs = [
        os.environ.get("ProgramFiles", r"C:\Program Files"),
        os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
        os.environ.get("LOCALAPPDATA", ""),
        os.environ.get("APPDATA", ""),
    ]

    sub_dirs = [
        "",
        "Microsoft",
        "Microsoft Office",
        "Microsoft Office/root",
        "Microsoft Office/root/Office16",
        "Google/Chrome/Application",
        "Microsoft/Edge/Application",
        "Mozilla Firefox",
        "Slack",
        "JetBrains",
        " JetBrains/Toolbox/apps",
        "WindowsApps",
        "Windows Terminal",
        "Git",
    ]

    for root in program_dirs:
        if not root:
            continue
        for sub in sub_dirs:
            p = Path(root) / sub / base
            if p.is_file():
                candidates.append(str(p))

    from shutil import which

    found = which(base)
    if found:
        candidates.append(found)

    # Special cases for well-known apps
    special: dict[str, list[str]] = {
        "code.exe": [
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe"),
            r"C:\Program Files\Microsoft VS Code\Code.exe",
        ],
        "chrome.exe": [
            os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        ],
        "msedge.exe": [
            os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
        ],
        "firefox.exe": [
            os.path.expandvars(r"%ProgramFiles%\Mozilla Firefox\firefox.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Mozilla Firefox\firefox.exe"),
        ],
        "winword.exe": [
            r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE",
            r"C:\Program Files (x86)\Microsoft Office\root\Office16\WINWORD.EXE",
            r"C:\Program Files\Microsoft Office\Office16\WINWORD.EXE",
            r"C:\Program Files (x86)\Microsoft Office\Office16\WINWORD.EXE",
        ],
        "excel.exe": [
            r"C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE",
            r"C:\Program Files (x86)\Microsoft Office\root\Office16\EXCEL.EXE",
            r"C:\Program Files\Microsoft Office\Office16\EXCEL.EXE",
            r"C:\Program Files (x86)\Microsoft Office\Office16\EXCEL.EXE",
        ],
        "outlook.exe": [
            r"C:\Program Files\Microsoft Office\root\Office16\OUTLOOK.EXE",
            r"C:\Program Files (x86)\Microsoft Office\root\Office16\OUTLOOK.EXE",
            r"C:\Program Files\Microsoft Office\Office16\OUTLOOK.EXE",
            r"C:\Program Files (x86)\Microsoft Office\Office16\OUTLOOK.EXE",
        ],
        "slack.exe": [
            os.path.expandvars(r"%LOCALAPPDATA%\slack\slack.exe"),
            os.path.expandvars(r"%ProgramFiles%\Slack\slack.exe"),
        ],
        "wt.exe": [
            os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WindowsApps\wt.exe"),
            r"C:\Program Files\WindowsApps\wt.exe",
        ],
        "notepad.exe": [
            r"C:\Windows\System32\notepad.exe",
            r"C:\Windows\notepad.exe",
        ],
        "pycharm64.exe": [
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\PyCharm\bin\pycharm64.exe"),
            r"C:\Program Files\JetBrains\PyCharm\bin\pycharm64.exe",
        ],
        "idea64.exe": [
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\IntelliJ IDEA\bin\idea64.exe"),
            r"C:\Program Files\JetBrains\IntelliJ IDEA\bin\idea64.exe",
        ],
        "anki.exe": [
            os.path.expandvars(r"%LOCALAPPDATA%\Anki\anki.exe"),
            r"C:\Program Files\Anki\anki.exe",
            r"C:\Program Files (x86)\Anki\anki.exe",
        ],
    }

    for path in special.get(base, []):
        if Path(path).is_file():
            candidates.append(path)

    for c in candidates:
        if Path(c).is_file():
            return c
    return None


# ---------------------------------------------------------------------------
# Monogram fallback (coloured circle with first letter)
# ---------------------------------------------------------------------------

_MONOGRAM_COLORS: dict[str, tuple[int, int, int]] = {
    "code": (0, 122, 204),
    "chrome": (66, 133, 244),
    "msedge": (0, 120, 215),
    "firefox": (255, 139, 24),
    "winword": (43, 87, 158),
    "excel": (33, 115, 70),
    "outlook": (13, 95, 175),
    "slack": (74, 21, 75),
    "wt": (16, 124, 16),
    "notepad": (220, 220, 220),
    "pycharm64": (38, 182, 150),
    "idea64": (255, 149, 0),
}


def _monogram_icon(name: str) -> QIcon:
    """Create a fallback icon: a coloured circle with the first letter."""
    name_lower = name.lower().replace(".exe", "")
    color = _MONOGRAM_COLORS.get(name_lower, (100, 120, 140))
    icon = QIcon()
    letter = name[0].upper() if name else "?"
    for dpr in (1, 2, 3):
        logical_size = DEFAULT_ICON_SIZE
        pixel_size = logical_size * dpr
        pixmap = QPixmap(pixel_size, pixel_size)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(*color))
        painter.setPen(QPen(Qt.GlobalColor.transparent))
        inset = 2 * dpr
        painter.drawEllipse(inset, inset, pixel_size - 2 * inset, pixel_size - 2 * inset)

        font = QFont()
        font.setPixelSize(int(pixel_size * 0.5))
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, letter)
        painter.end()
        pixmap.setDevicePixelRatio(float(dpr))
        icon.addPixmap(pixmap)

    return icon


# ---------------------------------------------------------------------------
# macOS icon extraction
# ---------------------------------------------------------------------------


def _icon_for_macos(app_path: str) -> QIcon:
    key = app_path
    if key in _ICON_CACHE:
        return _ICON_CACHE[key]

    if not app_path.endswith(".app"):
        icon = _monogram_icon(Path(app_path).stem)
        _ICON_CACHE[key] = icon
        return icon

    try:
        from PyQt6.QtWidgets import QFileIconProvider

        native_icon = QFileIconProvider().icon(QFileInfo(app_path))
        if not native_icon.isNull():
            _ICON_CACHE[key] = native_icon
            return native_icon
    except Exception:
        pass

    icon_dir = Path(app_path) / "Contents" / "Resources"
    icon_file = None
    if icon_dir.is_dir():
        for ext in ("icns", "png", "tiff"):
            for f in icon_dir.glob(f"*.{ext}"):
                icon_file = f
                break
            if icon_file:
                break

    icon = (
        QIcon(str(icon_file))
        if icon_file and icon_file.is_file()
        else _monogram_icon(Path(app_path).stem)
    )
    _ICON_CACHE[key] = icon
    return icon


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def _icon_cache_key(
    process_name: str,
    custom_path: str,
    icon_source: str,
    icon_index: int,
) -> str:
    def normalize(value: str) -> str:
        if not value:
            return ""
        expanded = os.path.expandvars(value)
        return os.path.normcase(os.path.abspath(expanded))

    return "|".join(
        (
            process_name.casefold(),
            normalize(custom_path),
            normalize(icon_source),
            str(int(icon_index)),
        )
    )


def _icon_from_source(icon_source: str, icon_index: int = 0) -> QIcon:
    source = os.path.expandvars(str(icon_source).strip().strip('"'))
    if not source or not Path(source).is_file():
        return QIcon()
    if os.name == "nt" and Path(source).suffix.casefold() in {
        ".cpl",
        ".dll",
        ".exe",
        ".icl",
        ".ico",
    }:
        extracted = _extract_icon_resource_windows(source, icon_index)
        if not extracted.isNull():
            return extracted
    direct = QIcon(source)
    return direct if not direct.isNull() else QIcon()


def app_icon(
    process_name: str,
    custom_path: str = "",
    icon_source: str = "",
    icon_index: int = 0,
) -> QIcon:
    """Return a QIcon for the given process/app.

    Args:
        process_name: e.g. "chrome.exe" (Windows) or "safari" (macOS).
        custom_path: Optional full path to the executable/app bundle.
        icon_source: Optional independent image or EXE/DLL/ICO resource.
        icon_index: Resource index (including negative resource IDs).
    """
    key = _icon_cache_key(process_name, custom_path, icon_source, icon_index)
    if key in _ICON_CACHE:
        return _ICON_CACHE[key]

    explicit = _icon_from_source(icon_source, icon_index)
    if not explicit.isNull():
        _ICON_CACHE[key] = explicit
        return explicit

    # macOS
    if sys.platform == "darwin":
        path = custom_path or _MAC_APP_PATHS.get(
            process_name.casefold(),
            f"/Applications/{process_name}.app",
        )
        if Path(path).is_dir():
            icon = _icon_for_macos(path)
            _ICON_CACHE[key] = icon
            return icon
        icon = _monogram_icon(process_name)
        _ICON_CACHE[key] = icon
        return icon

    # Windows
    if os.name == "nt":
        filepath = custom_path if custom_path else _find_exe_path(process_name)
        if filepath and os.path.isfile(filepath):
            if filepath.lower().endswith(".lnk"):
                filepath, shortcut_icon, shortcut_index = _windows_shortcut_details(filepath)
                shortcut_qicon = _icon_from_source(shortcut_icon, shortcut_index)
                if not shortcut_qicon.isNull():
                    _ICON_CACHE[key] = shortcut_qicon
                    return shortcut_qicon
            icon = _extract_icon_windows(filepath)
            _ICON_CACHE[key] = icon
            return icon
        icon = _monogram_icon(process_name)
        _ICON_CACHE[key] = icon
        return icon

    return _monogram_icon(process_name)


def app_pixmap(
    process_name: str,
    custom_path: str = "",
    size: int = DEFAULT_ICON_SIZE,
    icon_source: str = "",
    icon_index: int = 0,
    device_pixel_ratio: float | None = None,
) -> QPixmap:
    """Return a pixmap for the given app, scaled to *size*."""
    icon = app_icon(process_name, custom_path, icon_source, icon_index)
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance()
    screen = app.primaryScreen() if app else None
    dpr = max(
        1.0,
        float(device_pixel_ratio)
        if device_pixel_ratio is not None
        else (float(screen.devicePixelRatio()) if screen else 1.0),
    )
    try:
        pm = icon.pixmap(
            QSize(size, size),
            dpr,
            QIcon.Mode.Normal,
            QIcon.State.Off,
        )
    except TypeError:
        pm = icon.pixmap(QSize(round(size * dpr), round(size * dpr)))
        if not pm.isNull():
            pm.setDevicePixelRatio(dpr)
    if pm.isNull():
        fallback = _default_icon()
        pm = fallback.pixmap(QSize(size, size))
    if pm.isNull():
        pm = _monogram_icon(process_name).pixmap(QSize(size, size))
    return pm


def clear_icon_cache() -> None:
    """Clear the icon cache (e.g. when new apps are added)."""
    _ICON_CACHE.clear()


# Backward-compatible alias
clear_cache = clear_icon_cache


# ---------------------------------------------------------------------------
# Installed-application discovery
# ---------------------------------------------------------------------------

_DISCOVERED_APPS: list[dict] | None = None

_BLOCKED_CATALOG_TOKENS = {
    "compatibility",
    "bootstrap",
    "bootstrapper",
    "crash",
    "crashpad",
    "diagnostic",
    "driver",
    "helper",
    "installer",
    "language",
    "lime",
    "maintenance",
    "notification",
    "notify",
    "redist",
    "redistributable",
    "repair",
    "runtime",
    "sdk",
    "service",
    "setup",
    "telemetry",
    "toolchain",
    "uninstall",
    "uninstaller",
    "update",
    "updater",
    "webview",
    "verifier",
    "proxy",
    "edgecore",
    "edgeupdate",
    "integrated",
    "mingw",
    "usr",
    "nicdrv",
    "frameview",
    "offline",
    "pdf",
    "bss",
    "ocr",
    "capture",
    "peruna",
    "tooldeployment",
    "scanner",
    "feedback",
    "reporter",
    "sandbox",
    "enterprise",
    "snipping",
    "folder",
    "doctor",
    "support",
    "cleaner",
    "check",
    "alibaba",
    "protect",
    "assist",
    "config",
    "sync",
    "patcher",
    "filecoauth",
    "cookie",
    "copilot",
    "uc",
    "connector",
    "broker",
    "ondemand",
    "comregistershell",
    "core",
    "copilotapp",
    "msedgewebview",
    "enableloopback",
    "cssdk",
    "installxl",
    "thundercmd",
    "thunderev",
    "thunderfw",
    "xlacc",
    "xlbug",
    "xlliveud",
    "xlservice",
    "mintty",
    "pinentry",
    "rtinstaller",
    "8169",
    "dialup",
    "sas",
    "extexport",
    "ieinstal",
    "ielowutil",
    "presentmon",
    "nvrla",
    "nvfvsdk",
    "dlp",
    "mipdlp",
    "mpcopy",
    "mpext",
    "msmpeng",
    "wmlaunch",
    "wmpconfig",
    "wmpnscfg",
    "wmprph",
    "wmpshare",
    "imaging",
    "devices",
}
_BLOCKED_EXECUTABLE_PREFIXES = ("unins", "uninst", "wsl")
_BLOCKED_EXECUTABLE_AFFIXES = (
    "bootstrap",
    "crash",
    "helper",
    "installer",
    "launcher",
    "repair",
    "runtime",
    "service",
    "setup",
    "start",
    "uninstall",
    "update",
    "updater",
)
_BLOCKED_CATALOG_PHRASES = ("卸载", "安装程序", "更新程序")
_BLOCKED_DISPLAY_PHRASES = (
    "administrative tools",
    "amd compatibility",
    "application verifier",
    "disk cleanup",
    "frameview service",
    "microsoft defender command line",
    "office language",
    "office lime",
    "office telemetry",
    "windows software development kit",
)
_BLOCKED_PROCESS_NAMES = {
    "__nvcc_device_query.exe",
    "amdinstalluep.exe",
    "amdsoftwarecompatibilitytool.exe",
    "appverif.exe",
    "appvlp.exe",
    "chrome_proxy.exe",
    "cleanmgr.exe",
    "cmd.exe",
    "conhost.exe",
    "control.exe",
    "createdump.exe",
    "cscript.exe",
    "dfrgui.exe",
    "dotnet.exe",
    "explorer.exe",
    "focus capsule.exe",
    "iexplore.exe",
    "installmanagerapp.exe",
    "java.exe",
    "javaw.exe",
    "mmc.exe",
    "mpcmdrun.exe",
    "msiexec.exe",
    "msoev.exe",
    "msoadfsb.exe",
    "msoasb.exe",
    "msoxmled.exe",
    "nahimicnotifsys.exe",
    "node.exe",
    "officeclicktorun.exe",
    "officec2rclient.exe",
    "penotify.exe",
    "powershell.exe",
    "pwsh.exe",
    "python.exe",
    "pythonw.exe",
    "regedit.exe",
    "rundll32.exe",
    "sdxhelper.exe",
    "setlang.exe",
    "skypeserver.exe",
    "wab.exe",
    "wabmig.exe",
    "windowspackagemanagerserver.exe",
    "wscript.exe",
    "wslg.exe",
    "wslhost.exe",
    "wslrelay.exe",
    "wt.exe",
}
_BLOCKED_EXECUTABLE_FRAGMENTS = (
    "cleanup",
    "compatibilitytool",
    "installer",
    "notif",
    "sdksvc",
    "splashscreen",
)
_BLOCKED_PATH_SEGMENTS = {
    ".cache",
    "cache",
    "common files",
    "node_modules",
    "package cache",
    "system32",
    "syswow64",
    "temp",
    "tmp",
    "windows kits",
    "winsxs",
}
_BLOCKED_PATH_ROLE_SEGMENTS = {
    "bootstrap",
    "helper",
    "installer",
    "repair",
    "runtime",
    "service",
    "setup",
    "uninstaller",
    "update",
    "updater",
}
_PROGRAM_SEARCH_FOLDERS = (
    "app",
    "application",
    "bin",
    "current",
    "host",
    "main",
    "program",
    "office",
    "root",
    "office16",
    "office15",
)
_PROGRAM_SEARCH_CHAINS = (
    ("app", "current"),
    ("application", "current"),
    ("main", "current"),
)
_LAUNCHER_EXECUTABLE_AFFIXES = (
    "bootstrap",
    "desktop",
    "launcher",
    "start",
    "starter",
)
_BLOCKED_PROGRAM_DIRECTORY_NAMES = {
    "amd",
    "common files",
    "dotnet",
    "nodejs",
    "windows kits",
    "wsl",
    "windows defender",
    "windows media player",
    "windows photo viewer",
    "windows sidebar",
    "windows mail",
    "nt",
    "oem",
    "powershell",
    "internet explorer",
    "windows apps",
    "windowsapps",
}


def discover_installed_apps(force_refresh: bool = False) -> list[dict]:
    """Return cached, real launchable applications for the current platform.

    Each result contains ``display_name``, ``process_name`` and ``custom_path``;
    Windows entries may also include ``icon_source`` and ``icon_index``.
    Process names are normalized to the identifiers emitted by the foreground
    monitor: executable basenames on Windows and localized app names on macOS.
    """
    global _DISCOVERED_APPS
    if force_refresh:
        _DISCOVERED_APPS = None
    if _DISCOVERED_APPS is None:
        if os.name == "nt":
            _DISCOVERED_APPS = _discover_installed_apps_windows()
        elif sys.platform == "darwin":
            _DISCOVERED_APPS = _discover_installed_apps_macos()
        else:
            _DISCOVERED_APPS = []
    return [dict(item) for item in _DISCOVERED_APPS]


def _catalog_tokens(*values: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", " ".join(values).casefold()))


def _is_catalog_component(
    display_name: str,
    process_name: str,
    path: str,
    *,
    allow_system_path: bool = False,
) -> bool:
    """Return whether an entry is infrastructure rather than a user app."""
    normalized_process = Path(process_name).name.casefold()
    executable_stem = Path(normalized_process).stem
    if normalized_process in _BLOCKED_PROCESS_NAMES:
        return True
    if executable_stem.startswith("_"):
        return True
    if any(fragment in executable_stem for fragment in _BLOCKED_EXECUTABLE_FRAGMENTS):
        return True
    if executable_stem.startswith(_BLOCKED_EXECUTABLE_PREFIXES):
        return True
    if executable_stem.startswith(_BLOCKED_EXECUTABLE_AFFIXES) or executable_stem.endswith(
        _BLOCKED_EXECUTABLE_AFFIXES
    ):
        return True
    display_folded = display_name.casefold()
    if any(phrase in display_folded for phrase in _BLOCKED_CATALOG_PHRASES):
        return True
    if any(phrase in display_folded for phrase in _BLOCKED_DISPLAY_PHRASES):
        return True
    if not allow_system_path and _is_blocked_catalog_path(path):
        return True
    # Installation folders frequently contain words such as "setup" or
    # "runtime" even when the executable itself is a real user application
    # (Inno Setup Compiler is one example).  Filter executable identities here;
    # path roles are handled separately by _is_blocked_catalog_path().
    tokens = _catalog_tokens(process_name)
    return bool(tokens & _BLOCKED_CATALOG_TOKENS)


def _is_blocked_catalog_path(path: str) -> bool:
    if not path:
        return False
    expanded = os.path.abspath(os.path.expandvars(path))
    path_parts = {part.casefold() for part in Path(expanded).parts}
    if path_parts & (_BLOCKED_PATH_SEGMENTS | _BLOCKED_PATH_ROLE_SEGMENTS):
        return True

    roots = [os.environ.get("WINDIR", "")]
    roots.extend(os.environ.get(name, "") for name in ("TEMP", "TMP"))
    for root in roots:
        if root and _path_is_within(expanded, root):
            return True
    return False


def _path_is_within(path: str, root: str) -> bool:
    try:
        normalized_path = os.path.normcase(os.path.abspath(path))
        normalized_root = os.path.normcase(os.path.abspath(root))
        return os.path.commonpath((normalized_path, normalized_root)) == normalized_root
    except (OSError, ValueError):
        return False


def _windows_pe_subsystem(path: str) -> int | None:
    """Read the PE optional-header subsystem without loading the executable."""
    try:
        with open(path, "rb") as handle:
            if handle.read(2) != b"MZ":
                return None
            handle.seek(0x3C)
            pe_offset_data = handle.read(4)
            if len(pe_offset_data) != 4:
                return None
            pe_offset = struct.unpack("<I", pe_offset_data)[0]
            handle.seek(pe_offset)
            if handle.read(4) != b"PE\x00\x00":
                return None
            optional_header = pe_offset + 24
            handle.seek(optional_header + 68)
            subsystem_data = handle.read(2)
            if len(subsystem_data) != 2:
                return None
            return struct.unpack("<H", subsystem_data)[0]
    except OSError:
        return None


def _finalize_catalog(candidates: Iterable[dict]) -> list[dict]:
    """Sort deterministically and keep the best entry for each process."""
    ordered = sorted(
        candidates,
        key=lambda item: (
            int(item.get("_priority", 99)),
            str(item.get("display_name", "")).casefold(),
            str(item.get("process_name", "")).casefold(),
            os.path.normcase(str(item.get("custom_path", ""))),
        ),
    )
    seen: set[str] = set()
    result: list[dict] = []
    for item in ordered:
        display_name = str(item.get("display_name", "")).strip()
        process_name = str(item.get("process_name", "")).strip()
        custom_path = str(item.get("custom_path", "")).strip()
        allow_system_path = bool(item.get("_allow_system_path"))
        key = process_name.casefold()
        if not display_name or not key or key in seen:
            continue
        # Skip catalog component check for verified launcher executables
        # (e.g. blender-launcher.exe from Start Menu shortcuts).
        is_verified_launcher = item.get("_verified") and _is_launcher_executable(Path(custom_path))
        if not is_verified_launcher and _is_catalog_component(
            display_name,
            process_name,
            custom_path,
            allow_system_path=allow_system_path,
        ):
            continue
        seen.add(key)
        normalized = {
            "display_name": display_name,
            "process_name": process_name,
            "custom_path": custom_path,
        }
        icon_source = str(item.get("icon_source", "")).strip()
        if icon_source:
            normalized["icon_source"] = icon_source
            normalized["icon_index"] = int(item.get("icon_index", 0) or 0)
        app_user_model_id = str(item.get("app_user_model_id", "")).strip()
        if app_user_model_id:
            normalized["app_user_model_id"] = app_user_model_id
        result.append(normalized)
    return result


def _normalized_executable_identity(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", Path(value).stem.casefold())


def _launcher_identity(value: str) -> str:
    """Return the app identity embedded in a launcher executable name."""
    identity = _normalized_executable_identity(value)
    for affix in _LAUNCHER_EXECUTABLE_AFFIXES:
        if identity.startswith(affix) and len(identity) > len(affix):
            identity = identity[len(affix) :]
        if identity.endswith(affix) and len(identity) > len(affix):
            identity = identity[: -len(affix)]
    return identity


def _is_launcher_executable(path: Path) -> bool:
    identity = _normalized_executable_identity(path.name)
    return any(
        identity.startswith(affix) or identity.endswith(affix)
        for affix in _LAUNCHER_EXECUTABLE_AFFIXES
    )


def _windows_program_search_dirs(root: Path) -> list[Path]:
    """Return bounded install-layout directories that can contain a GUI app."""
    search_dirs = [root]
    for folder_name in _PROGRAM_SEARCH_FOLDERS:
        candidate_dir = root / folder_name
        if candidate_dir.is_dir():
            search_dirs.append(candidate_dir)
    for chain in _PROGRAM_SEARCH_CHAINS:
        candidate_dir = root.joinpath(*chain)
        if candidate_dir.is_dir():
            search_dirs.append(candidate_dir)

    try:
        for child in sorted(root.iterdir(), key=lambda item: item.name.casefold()):
            if child.is_dir() and (
                child.name[:1].isdigit()
                or child.name.casefold().startswith("app-")
                or child.name.casefold() in _PROGRAM_SEARCH_FOLDERS
            ):
                search_dirs.append(child)
    except OSError:
        pass
    return _unique_paths(search_dirs)


def _resolve_launcher_foreground_executable(
    launcher: Path,
    display_hint: str = "",
    process_hint: str = "",
    *,
    allow_console: bool = False,
    allow_system_path: bool = False,
) -> Path | None:
    """Map a short-lived launcher to the GUI process seen by the monitor.

    Resolution is deliberately strict: the replacement must live in a known,
    bounded directory below the launcher's install root and its normalized
    executable name must exactly match an identity supplied by the launcher,
    shortcut, or App Paths key.
    """
    try:
        if (
            not launcher.is_file()
            or launcher.suffix.casefold() != ".exe"
            or not _is_launcher_executable(launcher)
        ):
            return None
    except OSError:
        return None

    identities = {
        _launcher_identity(launcher.name),
        _launcher_identity(process_hint),
        _normalized_executable_identity(display_hint),
    }
    identities.discard("")
    identities.difference_update(_LAUNCHER_EXECUTABLE_AFFIXES)
    if not identities:
        return None

    launcher_path = os.path.normcase(os.path.abspath(launcher))
    candidates: list[Path] = []
    for directory in _windows_program_search_dirs(launcher.parent):
        try:
            executables = sorted(directory.glob("*.exe"), key=lambda item: item.name.casefold())
        except OSError:
            continue
        for executable in executables:
            if os.path.normcase(os.path.abspath(executable)) == launcher_path:
                continue
            if _normalized_executable_identity(executable.name) not in identities:
                continue
            if _is_catalog_component(
                display_hint,
                executable.name,
                str(executable),
                allow_system_path=allow_system_path,
            ):
                continue
            subsystem = _windows_pe_subsystem(str(executable))
            if subsystem != 2 and not (allow_console and subsystem == 3):
                continue
            candidates.append(Path(os.path.abspath(executable)))

    if not candidates:
        return None
    return min(
        candidates,
        key=lambda path: (
            "current" not in {part.casefold() for part in path.parts},
            len(path.parts),
            str(path).casefold(),
        ),
    )


def _resolve_windows_catalog_executable(
    executable: Path,
    display_hint: str = "",
    process_hint: str = "",
    *,
    trusted_source: bool = False,
    allow_system_path: bool = False,
) -> Path | None:
    """Return a real GUI executable with foreground-monitor-compatible identity."""
    foreground = _resolve_launcher_foreground_executable(
        executable,
        display_hint,
        process_hint,
        allow_console=trusted_source,
        allow_system_path=allow_system_path,
    )
    if foreground is not None:
        executable = foreground
    process_name = executable.name.casefold()
    if not _is_catalog_component(
        display_hint,
        process_name,
        str(executable),
        allow_system_path=allow_system_path,
    ):
        # IMAGE_SUBSYSTEM_WINDOWS_GUI. Console tools remain available through
        # trusted Start/AppsFolder sources because programs such as Blender
        # deliberately ship a console-subsystem executable with a real window.
        subsystem = _windows_pe_subsystem(str(executable))
        if subsystem == 2 or (trusted_source and subsystem == 3):
            return executable
        return None
    resolved = _resolve_launcher_foreground_executable(
        executable,
        display_hint,
        process_hint,
        allow_console=trusted_source,
        allow_system_path=allow_system_path,
    )
    return resolved


def resolve_windows_app_target(
    file_path: str,
    display_hint: str = "",
    process_hint: str = "",
) -> str:
    """Resolve a user-picked Windows app to the process visible to the monitor.

    Start Menu shortcuts sometimes point at a short-lived launcher (DingTalk is
    one example).  Preserve explicitly selected regular executables, including
    console tools, while translating a known launcher to its foreground GUI
    executable when a safe match exists below the same install directory.
    """
    raw_path = os.path.expandvars(str(file_path).strip().strip('"'))
    if not raw_path:
        return ""
    source = Path(raw_path).expanduser()
    if source.suffix.casefold() == ".lnk":
        resolved = resolve_windows_shortcut(str(source))
        if resolved == str(source):
            return ""
        raw_path = resolved

    executable = Path(raw_path).expanduser()
    try:
        if not executable.is_file() or executable.suffix.casefold() != ".exe":
            return ""
    except OSError:
        return ""

    executable = Path(os.path.abspath(executable))
    foreground = _resolve_launcher_foreground_executable(
        executable,
        display_hint or source.stem,
        process_hint or executable.name,
        allow_console=True,
    )
    return str(foreground or executable)


def _windows_catalog_candidate(
    display_name: str,
    path: str,
    priority: int,
    process_hint: str = "",
    *,
    icon_source: str = "",
    icon_index: int = 0,
    trusted_source: bool = False,
    allow_system_path: bool = False,
    app_user_model_id: str = "",
) -> dict | None:
    raw_path = os.path.expandvars(str(path).strip().strip('"'))
    if not raw_path:
        return None
    from_lnk = raw_path.casefold().endswith(".lnk")
    if from_lnk:
        resolved, shortcut_icon, shortcut_index = _windows_shortcut_details(raw_path)
        if resolved != raw_path:
            raw_path = resolved
        if not icon_source and shortcut_icon:
            icon_source = shortcut_icon
            icon_index = shortcut_index
    executable = Path(raw_path).expanduser()
    try:
        if not executable.is_file() or executable.suffix.casefold() != ".exe":
            return None
    except OSError:
        return None

    display = str(display_name).strip() or executable.stem
    executable = _resolve_windows_catalog_executable(
        Path(os.path.abspath(executable)),
        display,
        process_hint,
        trusted_source=trusted_source or from_lnk or priority <= 1,
        allow_system_path=allow_system_path,
    )
    if executable is None:
        return None
    process_name = executable.name.casefold()
    candidate = {
        "display_name": display,
        "process_name": process_name,
        "custom_path": str(executable),
        "_priority": priority,
        "_verified": from_lnk or trusted_source,
        "_allow_system_path": allow_system_path,
    }
    if icon_source and Path(os.path.expandvars(icon_source)).is_file():
        candidate["icon_source"] = os.path.abspath(os.path.expandvars(icon_source))
        candidate["icon_index"] = int(icon_index)
    if app_user_model_id:
        candidate["app_user_model_id"] = app_user_model_id
    return candidate


def _xml_local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _resolve_appx_logo(package_root: Path, logo_reference: str) -> str:
    """Resolve an AppX logo reference to the best transparent raster asset."""
    reference = str(logo_reference).strip().replace("\\", os.sep).replace("/", os.sep)
    if not reference:
        return ""
    requested = package_root / reference
    if not _path_is_within(str(requested), str(package_root)):
        return ""
    if requested.is_file():
        return str(requested)

    parent = requested.parent
    if not parent.is_dir():
        return ""
    suffix = requested.suffix or ".png"
    try:
        variants = [
            path
            for path in parent.glob(f"{requested.stem}*{suffix}")
            if path.is_file() and _path_is_within(str(path), str(package_root))
        ]
    except OSError:
        return ""
    if not variants:
        return ""

    nominal_match = re.search(r"(?:square)?(\d+)x\d+", requested.stem.casefold())
    nominal_size = int(nominal_match.group(1)) if nominal_match else 44

    def effective_size(path: Path) -> int:
        folded = path.stem.casefold()
        target_match = re.search(r"targetsize-(\d+)", folded)
        if target_match:
            return int(target_match.group(1))
        scale_match = re.search(r"scale-(\d+)", folded)
        if scale_match:
            return max(1, round(nominal_size * int(scale_match.group(1)) / 100))
        return nominal_size

    def score(path: Path):
        pixels = effective_size(path)
        folded = path.stem.casefold()
        return (
            pixels < 64,
            abs(pixels - 64),
            "altform-unplated" not in folded,
            -pixels,
            path.name.casefold(),
        )

    return str(min(variants, key=score))


def _appx_manifest_entry(
    package_install_path: str,
    app_user_model_id: str,
) -> tuple[Path, str] | None:
    """Map an AppsFolder AUMID to its real foreground EXE and logo."""
    package_root = Path(package_install_path)
    manifest = package_root / "AppxManifest.xml"
    if not package_root.is_dir() or not manifest.is_file():
        return None
    try:
        document = ET.parse(manifest)
    except (ET.ParseError, OSError):
        return None

    app_id = app_user_model_id.rsplit("!", 1)[-1].casefold()
    applications = [
        element
        for element in document.getroot().iter()
        if _xml_local_name(str(element.tag)) == "Application"
    ]
    selected = next(
        (
            element
            for element in applications
            if str(element.attrib.get("Id", "")).casefold() == app_id
        ),
        applications[0] if len(applications) == 1 else None,
    )
    if selected is None:
        return None

    executable_reference = str(selected.attrib.get("Executable", "")).strip()
    if not executable_reference or "$" in executable_reference:
        return None
    executable_reference = executable_reference.replace("\\", os.sep).replace("/", os.sep)
    executable = Path(executable_reference)
    if not executable.is_absolute():
        executable = package_root / executable
    if (
        not _path_is_within(str(executable), str(package_root))
        or not executable.is_file()
        or executable.suffix.casefold() != ".exe"
    ):
        return None

    visual = next(
        (
            child
            for child in selected.iter()
            if _xml_local_name(str(child.tag)) == "VisualElements"
        ),
        None,
    )
    logo_source = ""
    if visual is not None:
        for attribute in ("Square44x44Logo", "SmallLogo", "Square150x150Logo", "Logo"):
            logo_source = _resolve_appx_logo(
                package_root,
                str(visual.attrib.get(attribute, "")),
            )
            if logo_source:
                break
    return Path(os.path.abspath(executable)), logo_source


def _scan_windows_apps_folder(add_fn) -> None:
    """Discover packaged Start apps with localized names via AppsFolder."""
    initialized = False
    try:
        import pythoncom
        import win32com.client

        pythoncom.CoInitialize()
        initialized = True
        shell_application = win32com.client.Dispatch("Shell.Application")
        folder = shell_application.NameSpace("shell:AppsFolder")
        if folder is None:
            return
        items = folder.Items()
        for item in items:
            try:
                display_name = str(item.Name or "").strip()
                app_user_model_id = str(
                    item.ExtendedProperty("System.AppUserModel.ID") or item.Path or ""
                ).strip()
                package_install_path = str(
                    item.ExtendedProperty("System.AppUserModel.PackageInstallPath") or ""
                ).strip()
            except Exception:
                continue
            if not display_name or not app_user_model_id or not package_install_path:
                continue
            manifest_entry = _appx_manifest_entry(package_install_path, app_user_model_id)
            if manifest_entry is None:
                continue
            executable, logo_source = manifest_entry
            add_fn(
                display_name,
                executable.name.casefold(),
                str(executable),
                icon_source=logo_source,
                icon_index=0,
                trusted_source=True,
                allow_system_path=True,
                app_user_model_id=app_user_model_id,
            )
    except Exception:
        return
    finally:
        if initialized:
            try:
                pythoncom.CoUninitialize()
            except Exception:
                pass


def _discover_installed_apps_windows() -> list[dict]:
    """Discover user-facing Windows applications from preferred sources."""
    candidates: list[dict] = []

    def add_with_priority(priority: int):
        def add(
            display_name: str,
            process_name: str,
            path: str = "",
            *,
            icon_source: str = "",
            icon_index: int = 0,
            trusted_source: bool = False,
            allow_system_path: bool = False,
            app_user_model_id: str = "",
        ) -> None:
            candidate = _windows_catalog_candidate(
                display_name,
                path,
                priority,
                process_name,
                icon_source=icon_source,
                icon_index=icon_index,
                trusted_source=trusted_source,
                allow_system_path=allow_system_path,
                app_user_model_id=app_user_model_id,
            )
            if candidate is not None:
                candidates.append(candidate)

        return add

    # AppsFolder is the authoritative source for packaged Store/MSIX apps and
    # exposes localized labels plus package install locations without spawning
    # PowerShell or requiring administrator privileges.
    _scan_windows_apps_folder(add_with_priority(-1))

    # Start Menu names are curated for people and therefore have highest rank.
    start_menu_dirs: list[Path] = []
    for env_name in ("ProgramData", "APPDATA"):
        root = os.environ.get(env_name)
        if root:
            start_menu_dirs.append(Path(root) / "Microsoft" / "Windows" / "Start Menu" / "Programs")
    for folder in _unique_paths(start_menu_dirs):
        _scan_start_menu_folder(str(folder), add_with_priority(0))

    desktop_dirs = [Path.home() / "Desktop"]
    one_drive = os.environ.get("OneDrive")
    if one_drive:
        desktop_dirs.append(Path(one_drive) / "Desktop")
    for folder in _unique_paths(desktop_dirs):
        _scan_shortcut_folder(str(folder), add_with_priority(1))

    _scan_registry_apps(add_with_priority(2))
    _scan_registry_app_paths(add_with_priority(2))

    common_dirs: list[Path] = []
    for env_name in ("PROGRAMFILES", "PROGRAMFILES(X86)"):
        value = os.environ.get(env_name)
        if value:
            common_dirs.append(Path(value))
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        common_dirs.append(Path(local_app_data) / "Programs")
    for directory in _unique_paths(common_dirs):
        _scan_program_dir(str(directory), add_with_priority(3))

    return _finalize_catalog(candidates)


def _unique_paths(paths: Iterable[Path]) -> list[Path]:
    seen: set[str] = set()
    result: list[Path] = []
    for path in paths:
        key = os.path.normcase(os.path.abspath(path))
        if key not in seen:
            seen.add(key)
            result.append(path)
    return result


def _scan_start_menu_folder(folder_path: str, add_fn) -> None:
    if not os.path.isdir(folder_path):
        return
    for root, dirs, files in os.walk(folder_path):
        dirs.sort(key=str.casefold)
        for filename in sorted(files, key=str.casefold):
            full_path = os.path.join(root, filename)
            if filename.casefold().endswith(".lnk"):
                _resolve_and_add_lnk(full_path, add_fn)
            elif filename.casefold().endswith(".exe"):
                add_fn(Path(filename).stem, filename.casefold(), full_path)


def _scan_shortcut_folder(folder_path: str, add_fn) -> None:
    if not os.path.isdir(folder_path):
        return
    try:
        filenames = sorted(os.listdir(folder_path), key=str.casefold)
    except OSError:
        return
    for filename in filenames:
        full_path = os.path.join(folder_path, filename)
        if filename.casefold().endswith(".lnk"):
            _resolve_and_add_lnk(full_path, add_fn)
        elif filename.casefold().endswith(".exe"):
            add_fn(Path(filename).stem, filename.casefold(), full_path)


def _resolve_and_add_lnk(lnk_path: str, add_fn) -> None:
    target, icon_source, icon_index = _windows_shortcut_details(lnk_path)
    if target == lnk_path:
        return
    target_path = Path(target)
    if not target_path.is_file() or target_path.suffix.casefold() != ".exe":
        return
    display = Path(lnk_path).stem.replace("-", " ").replace("_", " ").strip()
    add_fn(
        display or target_path.stem,
        target_path.name.casefold(),
        target,
        icon_source=icon_source,
        icon_index=icon_index,
        trusted_source=True,
    )


def _registry_string(key, value_name: str) -> str:
    try:
        value, _ = __import__("winreg").QueryValueEx(key, value_name)
    except OSError:
        return ""
    return value.strip() if isinstance(value, str) else ""


def _parse_icon_location(value: str) -> tuple[str, int]:
    text = os.path.expandvars(value.strip())
    if not text:
        return "", 0
    icon_index = 0
    if text.startswith('"'):
        closing_quote = text.find('"', 1)
        candidate = text[1:closing_quote] if closing_quote > 1 else text.strip('"')
        remainder = text[closing_quote + 1 :] if closing_quote > 1 else ""
        index_match = re.search(r",\s*(-?\d+)\s*$", remainder)
    else:
        index_match = re.search(r",\s*(-?\d+)\s*$", text)
        candidate = text[: index_match.start()].strip() if index_match else text.strip()
    if index_match:
        try:
            icon_index = int(index_match.group(1))
        except (TypeError, ValueError):
            icon_index = 0
    return candidate, icon_index


def _parse_display_icon_path(value: str) -> str:
    """Backward-compatible path-only view of a DisplayIcon locator."""
    return _parse_icon_location(value)[0]


def _scan_registry_apps(add_fn) -> None:
    try:
        import winreg
    except ImportError:
        return

    key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"
    registry_views = {
        getattr(winreg, "KEY_WOW64_64KEY", 0),
        getattr(winreg, "KEY_WOW64_32KEY", 0),
    }
    for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        for view in sorted(registry_views):
            try:
                registry_key = winreg.OpenKey(
                    hive,
                    key_path,
                    0,
                    winreg.KEY_READ | view,
                )
            except OSError:
                continue
            try:
                index = 0
                while True:
                    try:
                        sub_key_name = winreg.EnumKey(registry_key, index)
                    except OSError:
                        break
                    index += 1
                    try:
                        sub_key = winreg.OpenKey(registry_key, sub_key_name)
                    except OSError:
                        continue
                    try:
                        display_name = _registry_string(sub_key, "DisplayName")
                        if not display_name:
                            continue
                        try:
                            system_component, _ = winreg.QueryValueEx(sub_key, "SystemComponent")
                        except OSError:
                            system_component = 0
                        if system_component == 1:
                            continue

                        icon_source, icon_index = _parse_icon_location(
                            _registry_string(sub_key, "DisplayIcon")
                        )
                        executable_path = (
                            icon_source
                            if icon_source
                            and Path(icon_source).is_file()
                            and Path(icon_source).suffix.casefold() == ".exe"
                            else ""
                        )
                        if not (
                            executable_path
                            and Path(executable_path).is_file()
                            and Path(executable_path).suffix.casefold() == ".exe"
                        ):
                            install_location = _registry_string(sub_key, "InstallLocation")
                            executable = _choose_primary_executable(install_location, display_name)
                            executable_path = str(executable) if executable else ""
                        if executable_path:
                            add_fn(
                                display_name,
                                Path(executable_path).name.casefold(),
                                executable_path,
                                icon_source=(
                                    icon_source
                                    if icon_source and Path(icon_source).is_file()
                                    else ""
                                ),
                                icon_index=icon_index,
                            )
                    finally:
                        winreg.CloseKey(sub_key)
            finally:
                winreg.CloseKey(registry_key)


def _scan_registry_app_paths(add_fn) -> None:
    """Discover executable aliases registered for ShellExecute/CreateProcess."""
    try:
        import winreg
    except ImportError:
        return

    key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"
    registry_views = {
        getattr(winreg, "KEY_WOW64_64KEY", 0),
        getattr(winreg, "KEY_WOW64_32KEY", 0),
    }
    for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        for view in sorted(registry_views):
            try:
                registry_key = winreg.OpenKey(
                    hive,
                    key_path,
                    0,
                    winreg.KEY_READ | view,
                )
            except OSError:
                continue
            try:
                index = 0
                while True:
                    try:
                        sub_key_name = winreg.EnumKey(registry_key, index)
                    except OSError:
                        break
                    index += 1
                    try:
                        sub_key = winreg.OpenKey(registry_key, sub_key_name)
                    except OSError:
                        continue
                    try:
                        executable_path = _parse_display_icon_path(_registry_string(sub_key, ""))
                        if executable_path:
                            add_fn(
                                Path(sub_key_name).stem,
                                Path(sub_key_name).name.casefold(),
                                executable_path,
                            )
                    finally:
                        winreg.CloseKey(sub_key)
            finally:
                winreg.CloseKey(registry_key)


def _choose_primary_executable(
    directory: str,
    display_hint: str = "",
    require_name_match: bool = False,
) -> Path | None:
    root = Path(os.path.expandvars(directory)).expanduser() if directory else None
    if root is None or not root.is_dir():
        return None

    search_dirs = _windows_program_search_dirs(root)

    executables: list[Path] = []
    launcher_identities: set[str] = set()
    for search_dir in search_dirs:
        try:
            directory_executables = list(search_dir.glob("*.exe"))
        except OSError:
            continue
        for path in directory_executables:
            if _is_launcher_executable(path):
                launcher_identity = _launcher_identity(path.name)
                if launcher_identity:
                    launcher_identities.add(launcher_identity)
            if (
                path.is_file()
                and not _is_catalog_component(display_hint, path.name, str(path))
                and _windows_pe_subsystem(str(path)) == 2
            ):
                executables.append(path)
    if not executables:
        return None

    normalized_hint = re.sub(r"[^a-z0-9]", "", display_hint.casefold())
    normalized_hints = launcher_identities | ({normalized_hint} if normalized_hint else set())

    def score(path: Path):
        stem = re.sub(r"[^a-z0-9]", "", path.stem.casefold())
        if stem and stem in normalized_hints:
            match_score = 0
        elif stem and any(stem in hint or hint in stem for hint in normalized_hints):
            match_score = 1
        else:
            match_score = 3
        return match_score, len(path.parts), path.name.casefold(), str(path).casefold()

    selected = min(executables, key=score)
    if require_name_match and score(selected)[0] > 1:
        return None
    return selected


def _scan_program_dir(dir_path: str, add_fn) -> None:
    root = Path(dir_path)
    if not root.is_dir():
        return
    try:
        entries = sorted(root.iterdir(), key=lambda item: item.name.casefold())
    except OSError:
        return
    for entry in entries:
        if not entry.is_dir() or entry.name.startswith("."):
            continue
        if entry.name.casefold() in _BLOCKED_PROGRAM_DIRECTORY_NAMES:
            continue
        if _is_catalog_component(entry.name, "", str(entry)):
            continue
        # Try the strict name-match approach first
        executable = _choose_primary_executable(
            str(entry),
            entry.name,
            require_name_match=True,
        )
        if executable is not None:
            display = entry.name.replace("-", " ").replace("_", " ").strip()
            add_fn(display or executable.stem, executable.name.casefold(), str(executable))
            continue

        # If name matching failed, scan subdirectories for the main executable
        _scan_program_subtree_relaxed(str(entry), entry.name, add_fn)


def _scan_program_subtree_relaxed(root_path: str, display_hint: str, add_fn) -> None:
    """Relaxed scan: look for main executable in subdirs of a program folder.

    This is used when the top-level directory name doesn't match any executable
    (e.g., 'Tencent' folder contains 'Weixin.exe'). It searches subdirectories
    for the primary executable by preferring common main app names.
    """
    root = Path(root_path)
    if not root.is_dir():
        return

    # Collect all candidate executables from bounded subdirectories
    candidates: list[tuple[Path, int]] = []  # (path, score)

    # Search bounded program directories
    search_dirs = _windows_program_search_dirs(root)

    # Also add immediate subdirectories that look like app containers
    try:
        for child in sorted(root.iterdir(), key=lambda item: item.name.casefold()):
            if child.is_dir() and child.name not in {str(sd) for sd in search_dirs}:
                # Include subdirs that look like app containers (versioned dirs starting with digit,
                # or dirs that contain bounded subdirs themselves)
                if child.name.casefold() in _PROGRAM_SEARCH_FOLDERS or child.name[:1].isdigit():
                    search_dirs.append(child)
                elif _has_bounded_subdir(child):
                    search_dirs.append(child)
    except OSError:
        pass

    for search_dir in search_dirs:
        try:
            executables = sorted(search_dir.glob("*.exe"), key=lambda p: p.name.casefold())
        except OSError:
            continue
        for exe in executables:
            # Skip launcher executables
            if _is_launcher_executable(exe):
                continue
            # Skip uninstallers
            if exe.stem.lower().startswith(("unins", "uninst")):
                continue

            # Check PE subsystem
            if _windows_pe_subsystem(str(exe)) != 2:
                continue

            # Calculate priority score
            exe_stem = exe.stem.lower()

            # Main executable names get lowest score (best)
            if exe_stem in _MAIN_APP_EXECUTABLES:
                score = 0
            # Contains common main name
            elif any(name in exe_stem for name in ("app", "main", "client")):
                score = 1
            # Default
            else:
                score = 2

            # Prefer executables in bounded subdirs (bin, current, main, etc.)
            if "current" in {p.casefold() for p in exe.parts}:
                score -= 1
            if "bin" in {p.casefold() for p in exe.parts}:
                score -= 1

            candidates.append((exe, score))

    # Also scan immediate subdirectories that contain bounded subdirs
    # This catches versioned directories like "Nsight Compute 2025.3.0"
    try:
        for child in sorted(root.iterdir(), key=lambda item: item.name.casefold()):
            if not child.is_dir() or child.name.startswith("."):
                continue
            # Skip common non-app directories
            blocked = {"common files", "windows kits", "dotnet", "nodejs", "amd", "wsl"}
            if child.name.casefold() in blocked:
                continue

            # Check if this child has bounded subdirs
            if not _has_bounded_subdir(child):
                continue

            # Scan bounded subdirs within this child
            for folder_name in _PROGRAM_SEARCH_FOLDERS:
                sub = child / folder_name
                if sub.is_dir():
                    try:
                        for exe in sub.glob("*.exe"):
                            if _is_launcher_executable(exe):
                                continue
                            if exe.stem.lower().startswith(("unins", "uninst")):
                                continue
                            if _windows_pe_subsystem(str(exe)) != 2:
                                continue

                            exe_stem = exe.stem.lower()
                            if exe_stem in _MAIN_APP_EXECUTABLES:
                                score = 0
                            elif any(name in exe_stem for name in ("app", "main", "client")):
                                score = 1
                            else:
                                score = 2

                            if "current" in {p.casefold() for p in exe.parts}:
                                score -= 1
                            if "bin" in {p.casefold() for p in exe.parts}:
                                score -= 1

                            candidates.append((exe, score))
                    except OSError:
                        pass

                    # Also scan immediate subdirs of bounded subdirs
                    # This catches "Nsight Compute 2025.3.0/host/windows-desktop-win7-x64/"
                    try:
                        for grandchild in sub.iterdir():
                            if grandchild.is_dir():
                                for exe in grandchild.glob("*.exe"):
                                    if _is_launcher_executable(exe):
                                        continue
                                    if exe.stem.lower().startswith(("unins", "uninst")):
                                        continue
                                    if _windows_pe_subsystem(str(exe)) != 2:
                                        continue

                                    exe_stem = exe.stem.lower()
                                    if exe_stem in _MAIN_APP_EXECUTABLES:
                                        score = 0
                                    elif any(n in exe_stem for n in ("app", "main", "client")):
                                        score = 1
                                    else:
                                        score = 2

                                    if "current" in {p.casefold() for p in exe.parts}:
                                        score -= 1
                                    if "bin" in {p.casefold() for p in exe.parts}:
                                        score -= 1

                                    candidates.append((exe, score))
                    except OSError:
                        pass
    except OSError:
        pass

    if not candidates:
        return

    # Sort by score and pick the best one
    candidates.sort(key=lambda x: (x[1], str(x[0]).casefold()))
    best_exe = candidates[0][0]

    display = display_hint.replace("-", " ").replace("_", " ").strip()
    if _is_catalog_component(display, best_exe.name, str(best_exe)):
        return
    add_fn(display or best_exe.stem, best_exe.name.casefold(), str(best_exe))


def _has_bounded_subdir(path: Path) -> bool:
    """Check if a directory has any bounded subdirectories."""
    try:
        for folder_name in _PROGRAM_SEARCH_FOLDERS:
            if (path / folder_name).is_dir():
                return True
    except OSError:
        pass
    return False


# Known main executable names for common app patterns
_MAIN_APP_EXECUTABLES = frozenset({
    "excel", "winword", "outlook", "powerpnt", "onedrive", "chrome",
    "firefox", "edge", "code", "slack", "teams", "zoom", "meet",
    "wechat", "weixin", "qq", "tb", "taobao", "ali",
    "baidu", "netdisk", "yun", "pan",
    "xmind", "note", "doc",
    "calibre", "anki", "obsidian", "logseq",
    "rustdesk", "toDesk", "sunlogin", "teamviewer",
    "discord", "telegram", "whatsapp", "signal",
    "spotify", "netease", "cloud",
    "vscode", "pycharm", "idea", "webstorm",
    "notepad", "calc", "camera", "mail", "photos",
    "wmplayer", "vlc", "potplayer",
    "winrar", "7z", "bandizip", "peazip",
    "pdf", "reader", "editor", "creator",
    "premiere", "after", "effects", "audition",
    "lightroom", "photoshop", "indesign",
    "dev", "studio", "builder", "maker",
    "tool", "utils", "utility",
    "server", "host", "client", "peer",
    "node", "worker", "task", "scheduler",
    "monitor", "tracker", "logger",
    "backup", "restore", "migrate", "convert",
    "sync", "upload", "download", "transfer",
    "share", "collab", "comm", "chat",
    "social", "network", "connect", "link",
    "web", "http", "https", "ftp", "ssh",
    "git", "svn", "hg", "mercurial",
    "docker", "kube", "container", "vm",
    "virtual", "machine", "emu", "simulator",
    "ncu", "nsys", "nsight", "ncu-ui",
    "thunder", "dingtalk", "formatfactory", "ting_es", "jianpian",
    "jianyingpro", "clash", "nyanpasu", "comet", "daymark",
    "vidbee", "proxygpt", "antigravity",
    "anythingllm", "activitywatch", "ueli",
    "weektodo", "notion", "lobsterai",
    "resdownloader", "diskgenius", "furmark",
    "ebook", "lrfviewer", "hina", "spanish", "dictionary",
    "windirstat", "winstat", "gethelp", "itunes", "mspaint",
    "olk", "snippingtool", "devenv",
    "wondershare", "pdfelement", "adobe",
    "microsoft", "google", "chromium",
    "media", "player", "windows",
    "app", "main", "client", "launch", "start", "center", "manager",
    "browser", "editor", "viewer", "player", "reader", "writer",
    "game", "play", "store", "shop", "market",
    "call", "music", "video", "photo", "camera", "media",
    "preferences", "settings", "options",
    "service", "daemon", "agent", "proxy",
    "test", "spec", "bench", "profile",
    "analyze", "inspect", "checker", "validator",
})


def _read_macos_bundle_info(bundle_path: Path) -> dict:
    info_path = bundle_path / "Contents" / "Info.plist"
    try:
        with info_path.open("rb") as handle:
            payload = plistlib.load(handle)
        return payload if isinstance(payload, dict) else {}
    except (OSError, plistlib.InvalidFileException):
        return {}


def _macos_bundle_details(bundle_path: Path) -> tuple[str, str] | None:
    if not bundle_path.is_dir() or bundle_path.suffix.casefold() != ".app":
        return None
    info = _read_macos_bundle_info(bundle_path)
    executable_name = str(info.get("CFBundleExecutable", "")).strip()
    executable_path = bundle_path / "Contents" / "MacOS" / executable_name
    if not executable_name or not executable_path.is_file():
        return None
    if not os.access(executable_path, os.X_OK):
        return None

    display_name = ""
    if sys.platform == "darwin":
        try:
            from Foundation import NSBundle

            bundle = NSBundle.bundleWithPath_(str(bundle_path))
            localized = bundle.localizedInfoDictionary() if bundle else None
            if localized:
                display_name = str(
                    localized.get("CFBundleDisplayName") or localized.get("CFBundleName") or ""
                )
        except Exception:
            pass
    display_name = (
        display_name.strip()
        or str(info.get("CFBundleDisplayName", "")).strip()
        or str(info.get("CFBundleName", "")).strip()
        or bundle_path.stem
    )
    return display_name, display_name.casefold()


def _iter_macos_app_bundles(root: Path):
    if not root.is_dir():
        return
    for current_root, directories, _files in os.walk(root):
        directories.sort(key=str.casefold)
        app_directories = [name for name in directories if name.casefold().endswith(".app")]
        for name in app_directories:
            yield Path(current_root) / name
        directories[:] = [name for name in directories if name not in app_directories]


def _discover_installed_apps_macos() -> list[dict]:
    """Discover launchable macOS bundles using monitor-compatible names."""
    roots = [
        (Path.home() / "Applications", 0),
        (Path("/Applications"), 0),
        (Path("/System/Applications"), 1),
        (Path("/System/Applications/Utilities"), 1),
    ]
    candidates: list[dict] = []
    seen_paths: set[str] = set()
    for root, priority in roots:
        for bundle_path in _iter_macos_app_bundles(root):
            path_key = str(bundle_path).casefold()
            if path_key in seen_paths:
                continue
            seen_paths.add(path_key)
            details = _macos_bundle_details(bundle_path)
            if details is None:
                continue
            display_name, process_name = details
            if _is_catalog_component(display_name, process_name, str(bundle_path)):
                continue
            candidates.append(
                {
                    "display_name": display_name,
                    "process_name": process_name,
                    "custom_path": str(bundle_path),
                    "_priority": priority,
                }
            )
    return _finalize_catalog(candidates)


def _safe_process_name(name: str) -> str:
    """Legacy helper retained for callers outside the discovery pipeline."""
    base = re.sub(r"[^\w]", "", name.casefold())
    if not base:
        base = "app"
    return base[:30] + ".exe" if not base.endswith(".exe") else base
