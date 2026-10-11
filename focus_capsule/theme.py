"""Focus Capsule design tokens.

The desktop shell uses a warm ivory canvas with white surfaces and a soft
gold accent.  Status colours stay semantically distinct.
"""

from __future__ import annotations

from typing import Any, Dict

# ═══════════════════════════════════════════════════════════════════
#  LIGHT TOKENS  — Warm ivory & white surfaces, soft gold accent
# ═══════════════════════════════════════════════════════════════════

LIGHT: Dict[str, Any] = {
    # ── Backgrounds ─────────────────────────────────────────────
    "WINDOW_BG":            "#F4F1EA",
    "TOP_BAR_BG":           "#F8F5EF",
    "SURFACE_1":            "#FFFFFF",
    "SURFACE_2":            "#FFFFFF",
    "SURFACE_3":            "#EDE8DC",
    "INPUT_BG":             "#FFFFFF",
    "OVERLAY_BG":           "rgba(244, 241, 234, 0.90)",

    # ── Navigation shell ────────────────────────────────────────
    "NAV_BG":               "#FFFFFF",
    "NAV_SURFACE":          "#F8F5EF",
    "NAV_ACTIVE_BG":        "#EDE8DC",
    "NAV_TEXT":             "#1E1C18",
    "NAV_MUTED":            "#8C8578",
    "NAV_ACCENT":           "#A08458",
    "NAV_BORDER":           "rgba(160, 132, 88, 0.18)",

    # ── Borders ─────────────────────────────────────────────────
    "BORDER_SUBTLE":        "rgba(30, 28, 24, 0.06)",
    "BORDER_NORMAL":        "rgba(30, 28, 24, 0.10)",
    "BORDER_STRONG":        "rgba(30, 28, 24, 0.18)",
    "BORDER_FOCUS":         "#A08458",

    # ── Accent / Brand (warm gold) ──────────────────────────────
    "ACCENT":               "#A08458",
    "ACCENT_HOVER":         "#8C6F45",
    "ACCENT_MUTED":         "rgba(160, 132, 88, 0.10)",
    "ACCENT_BORDER":        "rgba(160, 132, 88, 0.28)",
    "ACCENT_TEXT":          "#8C6F45",
    "ACCENT_DARK_BG":       "#EDE4D0",

    # ── Status ──────────────────────────────────────────────────
    "WARNING":              "#B47A42",
    "SUCCESS":              "#7A9968",
    "DANGER":                "#B65C4E",
    "INFO":                 "#A08458",

    "WARNING_BG":           "rgba(180, 122, 66, 0.10)",
    "SUCCESS_BG":           "rgba(122, 153, 104, 0.10)",
    "DANGER_BG":            "rgba(182, 92, 78, 0.08)",
    "INFO_BG":              "rgba(160, 132, 88, 0.10)",

    # ── Text ───────────────────────────────────────────────────
    "TEXT_PRIMARY":         "#1E1C18",
    "TEXT_SECONDARY":       "#5C5648",
    "TEXT_TERTIARY":        "#9A9285",
    "TEXT_DISABLED":        "#C4BDB0",

    # ── Track / Dividers ───────────────────────────────────────
    "RING_TRACK":           "#E3DED1",
    "DIVIDER":              "rgba(30, 28, 24, 0.07)",

    # ── Break / Amber ──────────────────────────────────────────
    "BREAK_BG":             "rgba(180, 122, 66, 0.08)",
    "BREAK_ACCENT":         "#B47A42",
    "BREAK_LIGHT":          "#D4A06A",

    # ── Focus ring state colours ───────────────────────────────
    "RING_READY":           "#9A9285",
    "RING_RUNNING":         "#A08458",
    "RING_BREAK":           "#B47A42",
    "RING_COMPLETE":         "#7A9968",
    "RING_STOPPED":         "#B65C4E",

    # ── Calendar intensity tint ────────────────────────────────
    "CAL_LOW":              "#F4EFE2",
    "CAL_MED":              "#E8DEC4",
    "CAL_HIGH":             "#D4BE8C",
    "CAL_PEAK":             "#A08458",
    "CAL_TODAY":            "rgba(160, 132, 88, 0.10)",
    "CAL_BORDER":           "rgba(30, 28, 24, 0.06)",

    # ── Chart series ───────────────────────────────────────────
    "CHART_PRIMARY":        "#A08458",
    "CHART_SECONDARY":      "#B47A42",
    "CHART_TERTIARY":       "#7A9968",
    "CHART_GRID":           "#E3DED1",
    "CHART_FILL":           "#D4BE8C",
    "CHART_TEXT":           "#9A9285",
    "CHART_CROSSHAIR":      "#1E1C18",

    # ── Misc ────────────────────────────────────────────────────
    "OLD_PANEL":            "#FFFFFF",
    "OLD_SECTION_CARD":     "#FFFFFF",
    "OLD_SOFT_PANEL":       "#EDE8DC",
    "OLD_BORDER":           "rgba(30, 28, 24, 0.07)",
}

# ═══════════════════════════════════════════════════════════════════
#  DARK TOKENS  — Warm dark amber for deep focus mode
# ═══════════════════════════════════════════════════════════════════

DARK: Dict[str, Any] = {
    # ── Backgrounds ─────────────────────────────────────────────
    "WINDOW_BG":            "#1E1C18",
    "TOP_BAR_BG":           "#28251F",
    "SURFACE_1":            "#2E2B24",
    "SURFACE_2":            "#36322A",
    "SURFACE_3":            "#403B31",
    "INPUT_BG":             "#2E2B24",
    "OVERLAY_BG":           "rgba(30, 28, 24, 0.94)",

    "NAV_BG":               "#1E1C18",
    "NAV_SURFACE":          "#2E2B24",
    "NAV_ACTIVE_BG":        "#403B31",
    "NAV_TEXT":             "#F4F1EA",
    "NAV_MUTED":            "#8C8578",
    "NAV_ACCENT":           "#D4A06A",
    "NAV_BORDER":           "rgba(255, 255, 255, 0.08)",

    # ── Borders ─────────────────────────────────────────────────
    "BORDER_SUBTLE":        "rgba(205, 195, 175, 0.08)",
    "BORDER_NORMAL":        "rgba(205, 195, 175, 0.14)",
    "BORDER_STRONG":        "rgba(205, 195, 175, 0.22)",
    "BORDER_FOCUS":         "#D4A06A",

    # ── Accent / Brand (warm gold) ──────────────────────────────
    "ACCENT":               "#D4A06A",
    "ACCENT_HOVER":         "#E8B380",
    "ACCENT_MUTED":         "rgba(212, 160, 106, 0.10)",
    "ACCENT_BORDER":        "rgba(212, 160, 106, 0.30)",
    "ACCENT_TEXT":          "#E8B380",
    "ACCENT_DARK_BG":       "#403B31",

    # ── Status ──────────────────────────────────────────────────
    "WARNING":              "#D4A06A",
    "SUCCESS":              "#A8C28E",
    "DANGER":               "#D68A7A",
    "INFO":                 "#D4A06A",

    "WARNING_BG":           "rgba(212, 160, 106, 0.08)",
    "SUCCESS_BG":           "rgba(168, 194, 142, 0.08)",
    "DANGER_BG":            "rgba(214, 138, 122, 0.06)",
    "INFO_BG":              "rgba(212, 160, 106, 0.08)",

    # ── Text ───────────────────────────────────────────────────
    "TEXT_PRIMARY":         "#F4F1EA",
    "TEXT_SECONDARY":       "#C4BBA8",
    "TEXT_TERTIARY":        "#8C8578",
    "TEXT_DISABLED":        "#5C5648",

    # ── Track / Dividers ───────────────────────────────────────
    "RING_TRACK":           "#403B31",
    "DIVIDER":              "rgba(205, 195, 175, 0.07)",

    # ── Break / Amber ──────────────────────────────────────────
    "BREAK_BG":             "rgba(212, 160, 106, 0.10)",
    "BREAK_ACCENT":         "#D4A06A",
    "BREAK_LIGHT":          "#E8B380",

    # ── Focus ring state colours ───────────────────────────────
    "RING_READY":           "#8C8578",
    "RING_RUNNING":         "#D4A06A",
    "RING_BREAK":           "#D4A06A",
    "RING_COMPLETE":        "#A8C28E",
    "RING_STOPPED":         "#D68A7A",

    # ── Calendar intensity tint ────────────────────────────────
    "CAL_LOW":              "#403B31",
    "CAL_MED":              "#594F3D",
    "CAL_HIGH":             "#8C6F45",
    "CAL_PEAK":             "#D4A06A",
    "CAL_TODAY":            "rgba(212, 160, 106, 0.10)",
    "CAL_BORDER":           "rgba(205, 195, 175, 0.06)",

    # ── Chart series ───────────────────────────────────────────
    "CHART_PRIMARY":        "#D4A06A",
    "CHART_SECONDARY":      "#E8B380",
    "CHART_TERTIARY":       "#A8C28E",
    "CHART_GRID":           "#403B31",
    "CHART_FILL":           "#594F3D",
    "CHART_TEXT":           "#8C8578",
    "CHART_CROSSHAIR":      "#F4F1EA",

    # ── Misc ────────────────────────────────────────────────────
    "OLD_PANEL":            "#2E2B24",
    "OLD_SECTION_CARD":     "#36322A",
    "OLD_SOFT_PANEL":       "#403B31",
    "OLD_BORDER":           "rgba(205, 195, 175, 0.08)",
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
#  PRECISION AGENT OS — DESIGN TOKENS
# ═══════════════════════════════════════════════════════════════════

# ── 8px spacing grid ─────────────────────────────────────────
SPACE_2   = 2
SPACE_4   = 4
SPACE_8   = 8
SPACE_12  = 12
SPACE_16  = 16
SPACE_20  = 20
SPACE_24  = 24
SPACE_32  = 32
SPACE_40  = 40
SPACE_48  = 48
SPACE_64  = 64

# Legacy aliases
SPACE_NONE    = 0
SPACE_XS      = SPACE_4
SPACE_SM      = SPACE_8
SPACE_MD      = SPACE_12
SPACE_LG      = SPACE_20
SPACE_XL      = 28
SPACE_2XL     = SPACE_40

MARGIN_WINDOW_H    = 24
MARGIN_WINDOW_TOP   = 20
MARGIN_WINDOW_BOT   = 20
MARGIN_SECTION_H    = 20
MARGIN_SECTION_V    = 16

# ── Radius ────────────────────────────────────────────────────
RADIUS_SM   = 8
RADIUS_MD   = 14
RADIUS_LG   = 18
RADIUS_XL   = 20
RADIUS_2XL  = 24

# ── Sizing ────────────────────────────────────────────────────
NAV_WIDTH         = 224
TOP_BAR_HEIGHT    = 76
BTN_ICON    = 32
BTN_COMPACT = 36
BTN_DEFAULT = 38
BTN_PRIMARY = 44
TOGGLE_SIZE = 28

# ── Typography (px) ──────────────────────────────────────────
FONT_PAGE_TITLE    = 30
FONT_WINDOW_TITLE  = 20
FONT_SECTION       = 15
FONT_SECTION_TITLE = 17
FONT_BODY          = 14
FONT_AUX           = 13
FONT_BODY_SMALL    = 12
FONT_META          = 11
FONT_NUMBER        = 18
FONT_HERO          = 64
FONT_HERO_SM       = 56
FONT_TIMER         = 56
FONT_TIMER_LARGE   = 72
FONT_TIMER_HUGE    = 72

# ── Weights ───────────────────────────────────────────────────
WEIGHT_TITLE     = 600
WEIGHT_SECTION   = 600
WEIGHT_BUTTON    = 500
WEIGHT_BODY      = 400
WEIGHT_NUMBER    = 500
WEIGHT_MEDIUM    = 500

# ── Motion (ms) ───────────────────────────────────────────────
DUR_HOVER      = 140
DUR_CHECKED    = 180
DUR_PAGE_SW    = 260
DUR_POPUP      = 220
DUR_STATE      = 260
DUR_ERROR      = 160
DUR_INSPECTOR  = 300
DUR_FOCUS_MODE = 600

# ── Fonts ─────────────────────────────────────────────────────
FONT_FAMILY_CN    = '"MiSans", "HarmonyOS Sans SC", "Microsoft YaHei UI", sans-serif'
FONT_FAMILY_NUM   = '"Geist", "SF Mono", "Cascadia Mono", "Consolas", monospace'
FONT_FAMILY_UI    = '"Inter", "Geist", "MiSans", "Microsoft YaHei UI", sans-serif'


def hex_alpha(hex_colour: str, alpha: float) -> str:
    """Return an rgba() string from a #RRGGBB hex and 0..1 alpha."""
    h = hex_colour.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha:.2f})"


# ── FocusRing colours by state ──────────────────────────────
def _ring_colours():
    t = _tokens()
    return {
        "ready":    t["RING_READY"],
        "running":  t["RING_RUNNING"],
        "break":    t["RING_BREAK"],
        "complete": t["RING_COMPLETE"],
        "stopped":  t["RING_STOPPED"],
    }


class _RingColoursProxy:
    def __getitem__(self, key): return _ring_colours()[key]
    def __contains__(self, key): return key in _ring_colours()
    def get(self, key, default=None): return _ring_colours().get(key, default)
    def keys(self): return _ring_colours().keys()
    def items(self): return _ring_colours().items()
    def values(self): return _ring_colours().values()
    def __repr__(self): return repr(_ring_colours())


RING_COLOURS = _RingColoursProxy()

# ── Mode labels ───────────────────────────────────────────────
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

# ── Default categories ────────────────────────────────────────
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

# ── Agent workflow stages ────────────────────────────────────
AGENT_STAGES = ["goal", "plan", "execute", "verify", "review"]
AGENT_STAGE_LABELS = {
    "goal":    "目标",
    "plan":    "计划",
    "execute": "执行",
    "verify":  "验证",
    "review":  "复盘",
}
AGENT_STAGE_ICONS = {
    "goal":    "◆",
    "plan":    "◇",
    "execute": "●",
    "verify":  "◐",
    "review":  "○",
}

# ═══════════════════════════════════════════════════════════════════
#  __getattr__ — resolve old-style token names from active theme
# ═══════════════════════════════════════════════════════════════════


_COLOUR_KEYS = frozenset(LIGHT.keys())


def __getattr__(name: str):
    if name in _COLOUR_KEYS:
        return _tokens()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
