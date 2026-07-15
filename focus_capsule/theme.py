"""Unified theme variables for Focus Capsule.

All colour, spacing, font, and size tokens used across the application.
Import from here instead of hardcoding hex values in inline stylesheets.
"""

from __future__ import annotations

# ── Backgrounds ──────────────────────────────────────────────
WINDOW_BG       = "#0A1019"
TOP_BAR_BG      = "#0C1420"
SURFACE_1       = "#101A28"
SURFACE_2       = "#131F2F"
SURFACE_3       = "#172436"
INPUT_BG        = "#0D1723"
OVERLAY_BG      = "rgba(5, 9, 15, 0.91)"

# ── Borders ──────────────────────────────────────────────────
BORDER_SUBTLE   = "rgba(132, 157, 188, 0.12)"
BORDER_NORMAL   = "rgba(132, 157, 188, 0.20)"
BORDER_STRONG   = "rgba(132, 157, 188, 0.32)"
BORDER_FOCUS    = "#67CFBB"

# ── Accent (sea-glass green) ──────────────────────────────────
ACCENT          = "#67CFBB"
ACCENT_HOVER    = "#78DAC8"
ACCENT_MUTED    = "rgba(103, 207, 187, 0.12)"
ACCENT_BORDER   = "rgba(103, 207, 187, 0.55)"
ACCENT_TEXT     = "#B8F1E6"
ACCENT_DARK_BG  = "#17342F"

# ── Status colours ───────────────────────────────────────────
WARNING         = "#E6B46B"
SUCCESS         = "#8BD6A8"
DANGER          = "#ED979D"
INFO            = "#8EADD4"

# ── Text ─────────────────────────────────────────────────────
TEXT_PRIMARY    = "#F4F7FB"
TEXT_SECONDARY  = "#B4BECC"
TEXT_TERTIARY   = "#7F8DA1"
TEXT_DISABLED   = "#566276"

# ── Track / dividers ─────────────────────────────────────────
RING_TRACK      = "#26364F"
DIVIDER         = "#203047"

# ── Break / amber ────────────────────────────────────────────
BREAK_BG        = "#2B2318"
BREAK_ACCENT    = "#F0C98F"
BREAK_LIGHT     = "#F5D9AF"

# ── Old colour tokens (kept for backward compat) ─────────────
OLD_PANEL          = "#111C2B"
OLD_SECTION_CARD   = "#131F30"
OLD_SOFT_PANEL     = "#0E1826"
OLD_BORDER         = "#22334D"

# ── Spacing (px) ─────────────────────────────────────────────
SPACE_NONE    = 0
SPACE_XS      = 4
SPACE_SM      = 8
SPACE_MD      = 14
SPACE_LG      = 18
SPACE_XL      = 24
SPACE_2XL     = 30

# ── Margins ──────────────────────────────────────────────────
MARGIN_WINDOW_H   = 24
MARGIN_WINDOW_TOP = 18
MARGIN_WINDOW_BOT = 20

# ── Radius (px) ──────────────────────────────────────────────
RADIUS_SM   = 6
RADIUS_MD   = 9
RADIUS_LG   = 12
RADIUS_XL   = 16
RADIUS_2XL  = 18

# ── Button heights (px) ──────────────────────────────────────
BTN_ICON    = 32
BTN_COMPACT = 36
BTN_DEFAULT = 38
BTN_PRIMARY = 44

# ── Font sizes (px) ─────────────────────────────────────────
FONT_PAGE_TITLE   = 22
FONT_WINDOW_TITLE = 18
FONT_SECTION      = 14
FONT_BODY         = 12
FONT_AUX          = 11
FONT_META         = 10
FONT_TIMER        = 40   # up to 64 in session
FONT_TIMER_LARGE  = 56

# ── Font weights ─────────────────────────────────────────────
WEIGHT_TITLE   = 700
WEIGHT_SECTION = 600
WEIGHT_BUTTON  = 600
WEIGHT_BODY    = 400
WEIGHT_NUMBER  = 650

# ── Durations (ms) ──────────────────────────────────────────
DUR_HOVER     = 120
DUR_CHECKED   = 180
DUR_PAGE_SW    = 200
DUR_POPUP      = 180
DUR_STATE      = 220
DUR_ERROR      = 160


def hex_alpha(hex_colour: str, alpha: float) -> str:
    """Return an rgba() string from a #RRGGBB hex and 0..1 alpha."""
    h = hex_colour.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha:.2f})"


# ── FocusRing colours by state ──────────────────────────────
RING_COLOURS = {
    "ready":    ACCENT,
    "running":  ACCENT,
    "break":    WARNING,
    "complete": SUCCESS,
    "stopped":  DANGER,
}

# ── Mode labels ─────────────────────────────────────────────
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
