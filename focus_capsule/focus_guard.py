"""专注期间的运行环境探测：空闲、全屏、系统专注模式与排除规则。

用于避免在用户看视频、投屏演示、开会时误弹接管层。全部为纯读取，
不修改系统状态；在非 Windows 平台上安全降级为「无信号」。
"""

from __future__ import annotations

import ctypes
import re
import sys
from dataclasses import dataclass, field
from typing import Iterable, Sequence

IS_WINDOWS = sys.platform == "win32"

# Windows: 会话已锁定时 SM_REMOTELOCK 为真
_SM_REMOTELOCK = 0x2013
# 用户「无干扰/专注助手」开启时的注册表取值
_QUIET_OFF = 0
_QUIET_ALARMS = 2
_QUIET_PRIORITY = 1


@dataclass
class GuardState:
    """一次探测的汇总结果，供覆盖层与控制器共用。"""

    idle_seconds: int = 0
    foreground_fullscreen: bool = False
    dnd_enabled: bool = False
    screen_locked: bool = False
    excluded_app: str = ""

    @property
    def should_suppress(self) -> bool:
        """是否应当跳过本次拦截（不打断用户，但照常计时）。"""
        return bool(
            self.foreground_fullscreen
            or self.dnd_enabled
            or self.screen_locked
            or self.excluded_app
        )

    @property
    def reason_label(self) -> str:
        if self.excluded_app:
            return "已列入免打扰清单"
        if self.foreground_fullscreen:
            return "前台处于全屏"
        if self.dnd_enabled:
            return "系统专注模式开启"
        if self.screen_locked:
            return "屏幕已锁定"
        if self.idle_seconds >= 60:
            return "你已离开超过 1 分钟"
        return ""


# ── 默认免打扰清单 ────────────────────────────────────────────
# 进程名（不含 .exe）或窗口标题关键词，命中即不弹接管层。
DEFAULT_EXCLUSIONS: tuple[str, ...] = (
    "zoom.exe",
    "teams.exe",
    "wemeet.exe",
    "feishu.exe",
    "dingtalk.exe",
    "obs64.exe",
    "obs32.exe",
    "powerpnt.exe",
    "keynote",
    "vlc.exe",
    "mpc-hc64.exe",
    "mpc-hc.exe",
    "potplayermini64.exe",
    "potplayermini.exe",
    "wmplayer.exe",
    "tv.danmaku.bili",
    "douyu",
    "huya",
)


def compile_exclusions(patterns: Iterable[str] | None = None) -> list[re.Pattern[str]]:
    """把排除清单编译成正则（同时匹配进程名与窗口标题，忽略大小写）。"""

    items = list(patterns) if patterns else list(DEFAULT_EXCLUSIONS)
    compiled: list[re.Pattern[str]] = []
    for raw in items:
        text = str(raw).strip().casefold()
        if not text:
            continue
        # 允许用户写 "标题:直播" 这种前缀形式，也允许直接写关键词
        if text.startswith("标题:") or text.startswith("title:"):
            text = text.split(":", 1)[1].strip()
        compiled.append(re.compile(re.escape(text), re.IGNORECASE))
    return compiled


def matches_exclusion(
    process_name: str,
    window_title: str,
    patterns: Sequence[re.Pattern[str]] | None,
) -> str:
    """命中则返回命中的关键词，否则返回空串。"""

    if not patterns:
        return ""
    haystack = f"{process_name} {window_title}"
    for pattern in patterns:
        if pattern.search(haystack):
            return pattern.pattern
    return ""


# ── 平台探测 ──────────────────────────────────────────────────


def idle_seconds() -> int:
    """返回距离最后一次键鼠输入的秒数；无法探测时返回 0。"""

    if not IS_WINDOWS:
        return 0
    try:
        class LASTINPUTINFO(ctypes.Structure):
            _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]

        info = LASTINPUTINFO()
        info.cbSize = ctypes.sizeof(info)
        if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info)):
            return 0
        millis = ctypes.windll.kernel32.GetTickCount() - info.dwTime
        return max(0, int(millis // 1000))
    except Exception:
        return 0


def screen_locked() -> bool:
    if not IS_WINDOWS:
        return False
    try:
        return bool(ctypes.windll.user32.GetSystemMetrics(_SM_REMOTELOCK))
    except Exception:
        return False


def dnd_enabled() -> bool:
    """Windows 专注助手 / 免打扰是否开启（读注册表，只读）。"""

    if not IS_WINDOWS:
        return False
    try:
        import winreg

        key = r"Software\Microsoft\Windows\CurrentVersion\Notifications"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key) as handle:
            try:
                profile, _ = winreg.QueryValueEx(handle, "UserPreferences")
            except OSError:
                return False
        # UserPreferences 的低 3 位是 QuietHours 状态：0 关闭，1 优先通知，2 仅闹钟
        return (int(profile) & 0b111) != _QUIET_OFF
    except Exception:
        return False


def foreground_fullscreen() -> bool:
    """前台窗口是否铺满其所在显示器（视频、投屏、演示模式）。"""

    if not IS_WINDOWS:
        return False
    try:
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return False

        class RECT(ctypes.Structure):
            _fields_ = [
                ("left", ctypes.c_long),
                ("top", ctypes.c_long),
                ("right", ctypes.c_long),
                ("bottom", ctypes.c_long),
            ]

        rect = RECT()
        if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            return False

        # MONITORINFO.dwFlags == 1 表示该显示器为主显示器
        class MONITORINFO(ctypes.Structure):
            _fields_ = [
                ("cbSize", ctypes.c_uint),
                ("rcMonitor", RECT),
                ("rcWork", RECT),
                ("dwFlags", ctypes.c_uint),
            ]

        monitor = user32.MonitorFromWindow(hwnd, 2)  # MONITOR_DEFAULTTONEAREST
        if not monitor:
            return False
        info = MONITORINFO()
        info.cbSize = ctypes.sizeof(info)
        if not user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
            return False

        width = rect.right - rect.left
        height = rect.bottom - rect.top
        full = info.rcMonitor
        work = info.rcWork
        covers_monitor = (
            abs(width - (full.right - full.left)) <= 2
            and abs(height - (full.bottom - full.top)) <= 2
        )
        # 铺满工作区但没铺满整个显示器：是最大化窗口，不算全屏
        covers_work = (
            abs(width - (work.right - work.left)) <= 2
            and abs(height - (work.bottom - work.top)) <= 2
        )
        if covers_monitor:
            return True
        if covers_work and (
            full.bottom - full.top == work.bottom - work.top
            and full.right - full.left == work.right - work.left
        ):
            # 没有任务栏占位时两者相同，最大化会被误判；用样式位再确认一次
            GWL_STYLE = -16
            WS_MAXIMIZE = 0x01000000
            style = ctypes.c_long(user32.GetWindowLongW(hwnd, GWL_STYLE)).value
            return bool(style & WS_MAXIMIZE) is False and width >= (full.right - full.left) - 8
        return False
    except Exception:
        return False


def probe(exclusions: Sequence[re.Pattern[str]] | None = None) -> GuardState:
    """一次性探测全部信号。"""

    state = GuardState()
    state.idle_seconds = idle_seconds()
    state.screen_locked = screen_locked()
    state.dnd_enabled = dnd_enabled()
    state.foreground_fullscreen = foreground_fullscreen()
    if exclusions:
        process_name, window_title = _current_foreground_text()
        state.excluded_app = matches_exclusion(process_name, window_title, exclusions)
    return state


def _current_foreground_text() -> tuple[str, str]:
    if not IS_WINDOWS:
        return "", ""
    try:
        import os

        import psutil

        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return "", ""
        length = user32.GetWindowTextLengthW(hwnd)
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, length + 1)
        pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        process_name = ""
        if pid.value and pid.value != os.getpid():
            try:
                process_name = psutil.Process(pid.value).name()
            except Exception:
                process_name = ""
        return process_name, buffer.value or ""
    except Exception:
        return "", ""
