"""Extract application icons for display in the settings panel.

On Windows, icons are extracted from .exe files via the shell API (SHGetFileInfo).
Falls back to a coloured monogram when the icon can't be resolved.
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes
import os
import sys
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap, QPen

_ICON_CACHE: dict[str, QIcon] = {}
_DEFAULT_ICON: QIcon | None = None

DEFAULT_ICON_SIZE = 40


def _default_icon() -> QIcon:
    global _DEFAULT_ICON
    if _DEFAULT_ICON is not None:
        return _DEFAULT_ICON
    from PyQt6.QtWidgets import QStyle, QApplication

    app = QApplication.instance()
    style = app.style() if app else None
    if style:
        _DEFAULT_ICON = style.standardIcon(QStyle.StandardPixmap.SP_FileIcon)
    else:
        _DEFAULT_ICON = QIcon()
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
    """Extract an icon from an executable using SHGetFileInfo."""
    SHGFI_ICON = 0x000000100
    SHGFI_LARGEICON = 0x000000000
    SHGFI_SHELLICONSIZE = 0x000000004
    flags = SHGFI_ICON | SHGFI_LARGEICON

    info = _SHFILEINFO()
    result = ctypes.windll.shell32.SHGetFileInfoW(
        filepath, 0, ctypes.byref(info), ctypes.sizeof(info), flags
    )
    if not result or not info.hIcon:
        return _monogram_icon(Path(filepath).stem)

    user32 = ctypes.windll.user32
    try:
        from PyQt6.QtGui import QGuiApplication
        pixmap = QPixmap.fromHICON(int(info.hIcon))
    except Exception:
        user32.DestroyIcon(info.hIcon)
        return _monogram_icon(Path(filepath).stem)
    user32.DestroyIcon(info.hIcon)

    if pixmap.isNull():
        return _monogram_icon(Path(filepath).stem)
    return QIcon(pixmap)


def _icon_from_extracticon(filepath: str) -> QIcon:
    """Alternative extraction via ExtractIconEx (used for .exe without shell icon)."""
    ExtractIconEx = ctypes.windll.shell32.ExtractIconExW
    ExtractIconEx.restype = ctypes.wintypes.UINT
    hicon = ctypes.wintypes.HICON()
    count = ExtractIconEx(filepath, 0, ctypes.byref(hicon), None, 1)
    if count == 0 or not hicon.value:
        return _monogram_icon(Path(filepath).stem)
    try:
        pixmap = QPixmap.fromHICON(int(hicon.value))
    except Exception:
        ctypes.windll.user32.DestroyIcon(hicon)
        return _monogram_icon(Path(filepath).stem)
    ctypes.windll.user32.DestroyIcon(hicon)
    if pixmap.isNull():
        return _monogram_icon(Path(filepath).stem)
    return QIcon(pixmap)


def _resolve_lnk(lnk_path: str) -> str:
    """Resolve a Windows .lnk shortcut to its target path."""
    try:
        import pythoncom
        from win32com.shell import shell

        shortcut = pythoncom.CoCreateInstance(
            shell.CLSID_ShellLink,
            None,
            pythoncom.CLSCTX_INPROC_SERVER,
            shell.IID_IShellLink,
        )
        shortcut.QueryInterface(shell.IID_IPersistFile).Load(lnk_path)
        target = shortcut.GetPath(0)[0]
        return target if target else lnk_path
    except Exception:
        return lnk_path


def _find_exe_path(process_name: str) -> Optional[str]:
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
        "", "Microsoft", "Microsoft Office", "Microsoft Office/root",
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
    size = DEFAULT_ICON_SIZE
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor(*color))
    painter.setPen(QPen(Qt.GlobalColor.transparent))
    painter.drawEllipse(2, 2, size - 4, size - 4)

    letter = name[0].upper() if name else "?"
    font = QFont()
    font.setPixelSize(int(size * 0.5))
    font.setBold(True)
    painter.setFont(font)
    painter.setPen(QColor(255, 255, 255))
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, letter)
    painter.end()

    return QIcon(pixmap)


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

    icon_dir = Path(app_path) / "Contents" / "Resources"
    icon_file = None
    if icon_dir.is_dir():
        for ext in ("icns", "png", "tiff"):
            for f in icon_dir.glob(f"*.{ext}"):
                icon_file = f
                break
            if icon_file:
                break

    icon = QIcon(str(icon_file)) if icon_file and icon_file.is_file() else _monogram_icon(Path(app_path).stem)
    _ICON_CACHE[key] = icon
    return icon


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def app_icon(process_name: str, custom_path: str = "") -> QIcon:
    """Return a QIcon for the given process/app.

    Args:
        process_name: e.g. "chrome.exe" (Windows) or "safari" (macOS).
        custom_path: Optional full path to an executable/app bundle.
    """
    key = custom_path or process_name
    if key in _ICON_CACHE:
        return _ICON_CACHE[key]

    # macOS
    if sys.platform == "darwin":
        path = custom_path or f"/Applications/{process_name}.app"
        if Path(path).is_dir():
            return _icon_for_macos(path)
        return _monogram_icon(process_name)

    # Windows
    if os.name == "nt":
        filepath = custom_path if custom_path else _find_exe_path(process_name)
        if filepath and os.path.isfile(filepath):
            if filepath.lower().endswith(".lnk"):
                filepath = _resolve_lnk(filepath)
            icon = _extract_icon_windows(filepath)
            _ICON_CACHE[key] = icon
            return icon
        icon = _monogram_icon(process_name)
        _ICON_CACHE[key] = icon
        return icon

    return _monogram_icon(process_name)


def app_pixmap(process_name: str, custom_path: str = "", size: int = DEFAULT_ICON_SIZE) -> QPixmap:
    """Return a pixmap for the given app, scaled to *size*."""
    icon = app_icon(process_name, custom_path)
    pm = icon.pixmap(QSize(size, size))
    if pm.isNull():
        icon = _default_icon()
        pm = icon.pixmap(QSize(size, size))
    return pm


def clear_icon_cache() -> None:
    """Clear the icon cache (e.g. when new apps are added)."""
    _ICON_CACHE.clear()


# Backward-compatible alias
clear_cache = clear_icon_cache


# ---------------------------------------------------------------------------
# Windows installed-app discovery
# ---------------------------------------------------------------------------

_DISCOVERED_APPS: list[dict] | None = None


def discover_installed_apps() -> list[dict]:
    """Return a cached list of discovered installed Windows applications.

    Each dict has keys: ``display_name``, ``process_name``, ``custom_path``.
    """
    global _DISCOVERED_APPS
    if _DISCOVERED_APPS is not None:
        return _DISCOVERED_APPS

    _DISCOVERED_APPS = _discover_installed_apps_windows()
    return _DISCOVERED_APPS


def _discover_installed_apps_windows() -> list[dict]:
    """Scan common locations for installed Windows applications."""
    seen: set[str] = set()
    apps: list[dict] = []

    def _add(display_name: str, process_name: str, path: str = "") -> None:
        key = process_name.lower()
        if key not in seen and display_name.strip():
            seen.add(key)
            apps.append({
                "display_name": display_name,
                "process_name": process_name,
                "custom_path": path,
            })

    # --- Start Menu folders ---
    start_menu_dirs = [
        os.path.join(os.environ.get("ProgramData", ""), "Microsoft", "Windows", "Start Menu", "Programs"),
        os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Windows", "Start Menu", "Programs"),
    ]
    for folder in start_menu_dirs:
        _scan_start_menu_folder(folder, _add)

    # --- Desktop shortcuts ---
    desktop_path = os.path.join(os.environ.get("USERPROFILE", ""), "Desktop")
    if os.path.isdir(desktop_path):
        for f in os.listdir(desktop_path):
            full = os.path.join(desktop_path, f)
            if f.lower().endswith(".lnk"):
                _resolve_and_add_lnk(full, _add)
            elif f.lower().endswith((".exe",)):
                _add(Path(f).stem, f.lower(), full)

    # --- Registry uninstall keys ---
    _scan_registry_apps(_add)

    # --- Common install directories ---
    common_dirs = [
        os.environ.get("PROGRAMFILES", r"C:\Program Files"),
        os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs"),
    ]
    for d in common_dirs:
        if os.path.isdir(d):
            _scan_program_dir(d, _add)

    return apps


def _scan_start_menu_folder(folder_path: str, add_fn) -> None:
    if not os.path.isdir(folder_path):
        return
    for root, _dirs, files in os.walk(folder_path):
        for f in files:
            full = os.path.join(root, f)
            if f.lower().endswith(".lnk"):
                _resolve_and_add_lnk(full, add_fn)
            elif f.lower().endswith((".exe", ".bat", ".cmd")):
                exe_path = os.path.join(root, f)
                if os.path.isfile(exe_path):
                    display = Path(f).stem.replace("-", " ").replace("_", " ").title()
                    add_fn(display, f.lower(), exe_path)


def _resolve_and_add_lnk(lnk_path: str, add_fn) -> None:
    try:
        import pythoncom
        from win32com.shell import shell

        shortcut = pythoncom.CoCreateInstance(
            shell.CLSID_ShellLink, None, pythoncom.CLSCTX_INPROC_SERVER, shell.IID_IShellLink
        )
        shortcut.QueryInterface(shell.IID_IPersistFile).Load(lnk_path)
        target, _, _ = shortcut.GetPath(0)
        if target and os.path.isfile(target):
            name = Path(target).stem
            display = name.replace("-", " ").replace("_", " ").title()
            add_fn(display, name.lower(), target)
    except Exception:
        pass


def _scan_registry_apps(add_fn) -> None:
    try:
        import winreg
    except ImportError:
        return

    keys = [
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
    ]

    for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        for key_path in keys:
            try:
                reg_key = winreg.OpenKey(hive, key_path, 0, winreg.KEY_READ | winreg.KEY_WOW64_32KEY)
                i = 0
                while True:
                    try:
                        sub_key_name = winreg.EnumKey(reg_key, i)
                        try:
                            sub = winreg.OpenKey(reg_key, sub_key_name, 0, winreg.KEY_READ)
                            display_name, _ = winreg.QueryValueEx(sub, "DisplayName")
                            if isinstance(display_name, str) and display_name.strip():
                                install_loc, _ = winreg.QueryValueEx(sub, "InstallLocation")
                                process_name, _ = winreg.QueryValueEx(sub, "DisplayIcon")
                                if not isinstance(process_name, str) or not process_name.strip():
                                    process_name = _safe_process_name(display_name)
                                exe_path = process_name.split(",")[0].strip().strip('"')
                                if not os.path.isfile(exe_path):
                                    exe_path = ""
                                add_fn(display_name.strip(), process_name.strip(), exe_path)
                            winreg.CloseKey(sub)
                        except Exception:
                            pass
                        i += 1
                    except OSError:
                        break
                winreg.CloseKey(reg_key)
            except OSError:
                pass


def _safe_process_name(name: str) -> str:
    import re
    base = re.sub(r"[^\w]", "", name.lower())
    if not base:
        base = "app"
    return base[:30] + ".exe" if not base.endswith(".exe") else base


def _scan_program_dir(dir_path: str, add_fn) -> None:
    try:
        for entry in os.listdir(dir_path):
            full = os.path.join(dir_path, entry)
            if os.path.isfile(full) and full.lower().endswith(".exe"):
                name = Path(entry).stem
                display = name.replace("-", " ").replace("_", " ").title()
                add_fn(display, entry.lower(), full)
            elif os.path.isdir(full):
                # Look for .exe in subfolder (skip .vs, .nuget etc.)
                skip_prefixes = (".", "vs", "nuget", "packages", "node_modules")
                if entry.lower().startswith(skip_prefixes):
                    continue
                for sub in os.listdir(full):
                    subpath = os.path.join(full, sub)
                    if os.path.isfile(subpath) and subpath.lower().endswith(".exe"):
                        name = Path(sub).stem
                        display = name.replace("-", " ").replace("_", " ").title()
                        add_fn(display, sub.lower(), subpath)
                        break
    except Exception:
        pass
