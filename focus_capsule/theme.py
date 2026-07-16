"""Unified design tokens for Focus Capsule.

Light theme (default, 日常模式):
  Background  #F4F3EF / Surface #FCFBF8
  Text        #17181B / Secondary #74777E
  Brand       #5B6FE8 / Brand bg #E8EBFA
  Success     #3B8D75 / Warning #C88745 / Danger #D85555

Dark theme (专注模式, when focus session active):
  Background  #0D0E11 / Surface #17181A
  Text        #F4F2ED / Secondary #B1B5C3
  Brand       #5B6FE8 (kept) / ambient #7181F5
"""

from __future__ import annotations
from typing import Dict, Any

# ═══════════════════════════════════════════════════════════════════
#  LIGHT TOKENS  (日常模式 — warm, bright, Apple-like)
# ═══════════════════════════════════════════════════════════════════

LIGHT: Dict[str, Any] = {
    # ── Backgrounds ─────────────────────────────────────────────
    "WINDOW_BG":            "#F4F3EF",
    "TOP_BAR_BG":           "#F4F3EF",
    "SURFACE_1":            "#FCFBF8",
    "SURFACE_2":            "#F7F6F4",
    "SURFACE_3":            "#F1F0EE",
    "INPUT_BG":             "#F9F8F6",
    "OVERLAY_BG":           "rgba(23, 24, 27, 0.72)",

    # ── Borders ─────────────────────────────────────────────────
    "BORDER_SUBTLE":        "rgba(23, 24, 27, 0.09)",
    "BORDER_NORMAL":        "rgba(23, 24, 27, 0.18)",
    "BORDER_STRONG":        "rgba(23, 24, 27, 0.32)",
    "BORDER_FOCUS":         "#5B6FE8",

    # ── Accent / Brand ──────────────────────────────────────────
    "ACCENT":               "#5B6FE8",
    "ACCENT_HOVER":         "#4F5ED6",
    "ACCENT_MUTED":         "rgba(91, 111, 232, 0.10)",
    "ACCENT_BORDER":        "rgba(91, 111, 232, 0.40)",
    "ACCENT_TEXT":          "#3B4BD8",
    "ACCENT_DARK_BG":       "#E8EBFA",

    # ── Status ──────────────────────────────────────────────────
    "WARNING":              "#C88745",
    "SUCCESS":              "#3B8D75",
    "DANGER":               "#D85555",
    "INFO":                 "#5B6FE8",

    "WARNING_BG":           "#FFF3E6",
    "SUCCESS_BG":           "#E8F5F2",
    "DANGER_BG":            "#FDF0F0",
    "INFO_BG":              "#E8F1FF",

    # ── Text ───────────────────────────────────────────────────
    "TEXT_PRIMARY":         "#17181B",
    "TEXT_SECONDARY":       "#74777E",
    "TEXT_TERTIARY":        "#ABAFB3",
    "TEXT_DISABLED":        "#D1D4D8",

    # ── Track / Dividers ───────────────────────────────────────
    "RING_TRACK":           "#E8E9ED",
    "DIVIDER":              "rgba(23, 24, 27, 0.09)",

    # ── Break / Amber ──────────────────────────────────────────
    "BREAK_BG":             "#FFF8E6",
    "BREAK_ACCENT":         "#C88745",
    "BREAK_LIGHT":          "#E6B346",

    # ── Misc ────────────────────────────────────────────────────
    "OLD_PANEL":            "#FCFBF8",
    "OLD_SECTION_CARD":     "#F7F6F4",
    "OLD_SOFT_PANEL":       "#F9F8F6",
    "OLD_BORDER":           "rgba(23, 24, 27, 0.12)",
}

# ═══════════════════════════════════════════════════════════════════
#  DARK TOKENS  (专注模式 — deep black, focused)
# ═══════════════════════════════════════════════════════════════════

DARK: Dict[str, Any] = {
    # ── Backgrounds ─────────────────────────────────────────────
    "WINDOW_BG":            "#0D0E11",
    "TOP_BAR_BG":           "#0D0E11",
    "SURFACE_1":            "#17181A",
    "SURFACE_2":            "#1E1F21",
    "SURFACE_3":            "#23262D",
    "INPUT_BG":             "#121315",
    "OVERLAY_BG":           "rgba(13, 14, 17, 0.88)",

    # ── Borders ─────────────────────────────────────────────────
    "BORDER_SUBTLE":        "rgba(113, 129, 245, 0.08)",
    "BORDER_NORMAL":        "rgba(113, 129, 245, 0.16)",
    "BORDER_STRONG":        "rgba(113, 129, 245, 0.28)",
    "BORDER_FOCUS":         "#5B6FE8",

    # ── Accent / Brand ──────────────────────────────────────────
    "ACCENT":               "#5B6FE8",
    "ACCENT_HOVER":         "#6C7BF0",
    "ACCENT_MUTED":         "rgba(91, 111, 232, 0.12)",
    "ACCENT_BORDER":        "rgba(91, 111, 232, 0.40)",
    "ACCENT_TEXT":          "#C7CDF8",
    "ACCENT_DARK_BG":       "#1A1F36",

    # ── Status ──────────────────────────────────────────────────
    "WARNING":              "#C88745",
    "SUCCESS":              "#3B8D75",
    "DANGER":               "#D85555",
    "INFO":                 "#5B6FE8",

    "WARNING_BG":           "#2D1D13",
    "SUCCESS_BG":           "#162824",
    "DANGER_BG":            "#2E1414",
    "INFO_BG":              "#1A2738",

    # ── Text ───────────────────────────────────────────────────
    "TEXT_PRIMARY":         "#F4F2ED",
    "TEXT_SECONDARY":       "#B1B5C3",
    "TEXT_TERTIARY":        "#818594",
    "TEXT_DISABLED":        "#545760",

    # ── Track / Dividers ───────────────────────────────────────
    "RING_TRACK":           "#23262D",
    "DIVIDER":              "rgba(113, 129, 245, 0.08)",

    # ── Break / Amber ──────────────────────────────────────────
    "BREAK_BG":             "#2F2612",
    "BREAK_ACCENT":         "#E6B346",
    "BREAK_LIGHT":          "#E6D08F",

    # ── Misc ────────────────────────────────────────────────────
    "OLD_PANEL":            "#17181A",
    "OLD_SECTION_CARD":     "#1E1F21",
    "OLD_SOFT_PANEL":       "#121315",
    "OLD_BORDER":           "rgba(113, 129, 245, 0.12)",
}

# ═══════════════════════════════════════════════════════════════════
#  THEME STATE MANAGEMENT
# ═══════════════════════════════════════════════════════════════════

_theme_mode: str = "light"
_focused: bool = False
_listeners: list = []


def set_theme(mode: str):
    global _theme_mode
    _theme_mode = mode if mode in ("light", "dark") else "light"


def set_focused(focused: bool):
    global _focused
    _focused = focused


def is_focused() -> bool:
    return _focused


def is_dark() -> bool:
    return _theme_mode == "dark" or _focused


def _tokens() -> Dict[str, Any]:
    return DARK if is_dark() else LIGHT


def get(key: str, default: Any = None) -> Any:
    return _tokens().get(key, default)


def current() -> Dict[str, Any]:
    return _tokens()


def add_listener(fn):
    _listeners.append(fn)


def notify_listeners():
    for fn in _listeners:
        fn()


# ═══════════════════════════════════════════════════════════════════
#  BACKWARD-COMPATIBILITY MODULE-LEVEL CONSTANTS
#  All old imports (ACCENT, WINDOW_BG, etc.) resolve dynamically to
#  the current theme via __getattr__ so existing files keep working.
# ═══════════════════════════════════════════════════════════════════

import sys as _sys

# Colour keys that should resolve from the active theme dict
_COLOUR_KEYS = frozenset(LIGHT.keys())

# Numeric / string constants that are theme-independent
SPACE_NONE    = 0
SPACE_XS      = 4
SPACE_SM      = 8
SPACE_MD      = 12
SPACE_LG      = 20
SPACE_XL      = 28
SPACE_2XL     = 36

MARGIN_WINDOW_H    = 24
MARGIN_WINDOW_TOP   = 20
MARGIN_WINDOW_BOT   = 20
MARGIN_SECTION_H    = 20
MARGIN_SECTION_V    = 16

RADIUS_SM   = 8
RADIUS_MD   = 12
RADIUS_LG   = 16
RADIUS_XL   = 20
RADIUS_2XL  = 24

BTN_ICON    = 32
BTN_COMPACT = 36
BTN_DEFAULT = 38
BTN_PRIMARY = 44

NAV_WIDTH         = 72
NAV_WIDTH_HOVER   = 224
NAV_HEIGHT        = 44
TOGGLE_SIZE       = 28

FONT_PAGE_TITLE   = 28
FONT_WINDOW_TITLE = 20
FONT_SECTION      = 15
FONT_SECTION_TITLE = 18
FONT_BODY         = 14
FONT_AUX          = 13
FONT_BODY_SMALL   = 12
FONT_META         = 11
FONT_NUMBER       = 18
FONT_TIMER        = 56
FONT_TIMER_LARGE  = 72
FONT_HERO         = 64
FONT_TIMER_HUGE   = 80

WEIGHT_TITLE     = 700
WEIGHT_SECTION   = 600
WEIGHT_BUTTON    = 500
WEIGHT_BODY      = 400
WEIGHT_NUMBER    = 650

DUR_HOVER   = 150
DUR_CHECKED = 180
DUR_PAGE_SW = 240
DUR_POPUP   = 200
DUR_STATE   = 220
DUR_ERROR   = 160


def hex_alpha(hex_colour: str, alpha: float) -> str:
    """Return an rgba() string from a #RRGGBB hex and 0..1 alpha."""
    h = hex_colour.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha:.2f})"


# ── FocusRing colours by state ──────────────────────────────
def _ring_colours():
    t = _tokens()
    return {
        "ready":    t["ACCENT"],
        "running":  t["ACCENT"],
        "break":    t["WARNING"],
        "complete": t["SUCCESS"],
        "stopped":  t["DANGER"],
    }


# Module-level property for RING_COLOURS (dict that reflects current theme)
class _RingColoursProxy:
    def __getitem__(self, key):
        return _ring_colours()[key]

    def __contains__(self, key):
        return key in _ring_colours()

    def get(self, key, default=None):
        return _ring_colours().get(key, default)

    def keys(self):
        return _ring_colours().keys()

    def items(self):
        return _ring_colours().items()

    def values(self):
        return _ring_colours().values()

    def __repr__(self):
        return repr(_ring_colours())


RING_COLOURS = _RingColoursProxy()

# ── Mode labels (theme-independent) ─────────────────────────
MODE_LABELS = {
    "Light":     "轻柔记录",
    "Standard":  "标准提醒",
    "Deep":      "深度拦截",
}

MODE_SHORT = {
    "Light":     "轻度",
    "Standard":  "标准",
    "Deep":      "深度",
}

MODE_DESCRIPTIONS = {
    "Light":     "仅记录分心，不中断操作",
    "Standard":  "离开允许应用时提醒返回",
    "Deep":      "保持遮罩直到切回允许应用",
}

MODE_ICONS = {
    "Light":     "○",
    "Standard":  "◐",
    "Deep":      "●",
}

# ── Default categories ───────────────────────────────────────
DEFAULT_CATEGORIES = [
    "学习", "工作", "编程", "办公", "浏览器",
    "通讯", "阅读", "影音娱乐", "游戏", "系统工具", "其他",
]

# ── Agent execution step states ─────────────────────────────
STEP_COMPLETED  = "completed"
STEP_ACTIVE     = "active"
STEP_PENDING    = "pending"
STEP_BLOCKED    = "blocked"
STEP_CONFIRM    = "confirm"
STEP_DEVIADED   = "deviated"

STEP_ICONS = {
    STEP_COMPLETED:  "✓",
    STEP_ACTIVE:     "●",
    STEP_PENDING:    "○",
    STEP_BLOCKED:     "⊘",
    STEP_CONFIRM:     "!",
    STEP_DEVIADED:    "×",
}

STEP_LABELS = {
    STEP_COMPLETED:  "已完成",
    STEP_ACTIVE:     "执行中",
    STEP_PENDING:    "待执行",
    STEP_BLOCKED:    "已阻塞",
    STEP_CONFIRM:    "待确认",
    STEP_DEVIADED:   "已偏离",
}


# ═══════════════════════════════════════════════════════════════════
#  __getattr__ — resolve old-style token names from active theme
#  This lets `from focus_capsule.theme import ACCENT` work while
#  returning the value from the currently-active theme dict.
# ═══════════════════════════════════════════════════════════════════

def __getattr__(name: str):
    if name in _COLOUR_KEYS:
        return _tokens()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
