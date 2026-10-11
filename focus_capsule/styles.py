"""Focus Capsule QSS stylesheet.

Warm ivory canvas, white surfaces and a restrained gold accent.
All colours are sourced from theme.py.
"""

from __future__ import annotations

from focus_capsule import theme as T


def _build_stylesheet() -> str:
    t = T.current()
    return f"""

/* ═════════════════════════════════════════════════════════════
   Focus Capsule — QSS Design System
   Warm ivory · graphite · restrained gold accent
   审美红线：淡色块(5–10% 透明度)+细色条，不用饱和实色填充
   ═════════════════════════════════════════════════════════════ */

/* ── Base canvas ───────────────────────────────────────────── */
QWidget {{
    background: transparent;
    color: {t["TEXT_PRIMARY"]};
    font-size: {T.FONT_BODY}px;
    font-family: {T.FONT_FAMILY_UI};
}}
QMainWindow, QDialog, QWidget#appWindow {{
    background-color: {t["WINDOW_BG"]};
}}
QLabel {{ color: {t["TEXT_PRIMARY"]}; background: transparent; }}

/* ── Typography hierarchy ─────────────────────────────────── */
QLabel#pageTitle {{
    color: {t["TEXT_PRIMARY"]};
    font-size: 22px;
    font-weight: {T.WEIGHT_SECTION};
    letter-spacing: -0.35px;
}}
QLabel#pageSubtitle {{
    color: {t["TEXT_SECONDARY"]};
    font-size: 12px;
    font-weight: {T.WEIGHT_BODY};
}}
QLabel#sectionTitle {{
    color: {t["TEXT_PRIMARY"]};
    font-size: {T.FONT_SECTION_TITLE}px;
    font-weight: {T.WEIGHT_SECTION};
    letter-spacing: -0.2px;
}}
QLabel#eyebrow {{
    color: {t["ACCENT"]};
    font-size: 12px;
    font-weight: {T.WEIGHT_SECTION};
    letter-spacing: 1.5px;
}}
QLabel#heroTimer {{
    color: {t["TEXT_PRIMARY"]};
    font-size: {T.FONT_TIMER_HUGE}px;
    font-weight: {T.WEIGHT_NUMBER};
    font-family: {T.FONT_FAMILY_NUM};
    letter-spacing: -2px;
}}
QLabel#heroGoal {{
    color: {t["TEXT_PRIMARY"]};
    font-size: 22px;
    font-weight: {T.WEIGHT_SECTION};
    letter-spacing: -0.3px;
}}
QLabel#heroMetric {{
    color: {t["TEXT_PRIMARY"]};
    font-size: {T.FONT_HERO}px;
    font-weight: {T.WEIGHT_NUMBER};
    font-family: {T.FONT_FAMILY_NUM};
    letter-spacing: -1.5px;
}}
QLabel#calendarHeroMetric {{
    color: {t["TEXT_PRIMARY"]};
    font-size: 44px;
    font-weight: {T.WEIGHT_NUMBER};
    font-family: {T.FONT_FAMILY_NUM};
    letter-spacing: -1px;
}}
QLabel#body, QLabel#bodyMuted {{
    color: {t["TEXT_SECONDARY"]};
    font-size: {T.FONT_BODY}px;
    font-weight: {T.WEIGHT_BODY};
}}
QLabel#bodyTertiary, QLabel#hint, QLabel#tinyMuted {{
    color: {t["TEXT_TERTIARY"]};
    font-size: {T.FONT_BODY_SMALL}px;
    font-weight: {T.WEIGHT_BODY};
}}
QLabel#summaryKey {{
    color: {t["TEXT_TERTIARY"]};
    font-size: 12px;
    font-weight: {T.WEIGHT_BODY};
    letter-spacing: 0.3px;
}}
QLabel#summaryValue {{
    color: {t["TEXT_PRIMARY"]};
    font-size: {T.FONT_SECTION_TITLE}px;
    font-weight: {T.WEIGHT_SECTION};
    font-family: {T.FONT_FAMILY_NUM};
}}
QLabel#summaryGoal {{
    color: {t["TEXT_PRIMARY"]};
    font-size: 16px;
    font-weight: {T.WEIGHT_SECTION};
}}
QLabel#statInline {{
    color: {t["TEXT_PRIMARY"]};
    font-size: {T.FONT_SECTION_TITLE}px;
    font-weight: {T.WEIGHT_NUMBER};
    font-family: {T.FONT_FAMILY_NUM};
}}
QLabel#statCaption {{
    color: {t["TEXT_TERTIARY"]};
    font-size: 12px;
    font-weight: {T.WEIGHT_BODY};
    letter-spacing: 0.2px;
}}
QLabel#statValue {{
    color: {t["TEXT_PRIMARY"]};
    font-size: 24px;
    font-weight: {T.WEIGHT_NUMBER};
    font-family: {T.FONT_FAMILY_NUM};
    letter-spacing: -0.5px;
}}
QLabel#insightText {{
    color: {t["TEXT_SECONDARY"]};
    font-size: 15px;
    font-weight: {T.WEIGHT_BODY};
}}
QLabel#insightKey {{
    color: {t["ACCENT"]};
    font-size: 12px;
    font-weight: {T.WEIGHT_SECTION};
    letter-spacing: 1px;
}}

/* ── Surfaces: 3 levels only ─────────────────────────────── */
QFrame#panel, QFrame#sectionCard, QFrame#statCard {{
    background-color: {t["SURFACE_1"]};
    border: 1px solid {t["BORDER_NORMAL"]};
    border-radius: {T.RADIUS_MD}px;
}}
QFrame#inspector {{
    background-color: {t["SURFACE_2"]};
    border: 1px solid {t["BORDER_SUBTLE"]};
    border-radius: {T.RADIUS_LG}px;
}}
QFrame#softPanel {{
    background-color: {t["SURFACE_3"]};
    border: none;
    border-radius: {T.RADIUS_MD}px;
}}
QFrame#breakPanel {{
    background-color: {t["BREAK_BG"]};
    border: 1px solid {t["BREAK_ACCENT"]};
    border-radius: {T.RADIUS_MD}px;
}}
QFrame#divider {{
    background-color: {t["DIVIDER"]};
    max-height: 1px;
    border: none;
}}

/* ── Navigation sidebar ───────────────────────────────────── */
QFrame#navRail {{
    background-color: {t["NAV_BG"]};
    border: none;
}}
QFrame#navDivider {{
    background-color: {t["NAV_BORDER"]};
    max-height: 1px;
    border: none;
}}
QLabel#navBrandMark {{
    min-width: 42px;
    max-width: 42px;
    min-height: 42px;
    max-height: 42px;
    border-radius: 14px;
    background-color: {t["NAV_ACCENT"]};
    color: {t["NAV_BG"]};
    font-size: 17px;
    font-weight: 700;
}}
QLabel#navBrand {{
    color: {t["NAV_TEXT"]};
    font-size: 17px;
    font-weight: 600;
}}
QLabel#navBrandCaption {{
    color: {t["NAV_MUTED"]};
    font-size: 9px;
    font-weight: 600;
    letter-spacing: 1.1px;
}}
QLabel#navSectionLabel {{
    color: {t["NAV_MUTED"]};
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1px;
    padding: 0 10px;
}}
QFrame#navLocalCard {{
    background-color: {t["NAV_SURFACE"]};
    border: 1px solid {t["NAV_BORDER"]};
    border-radius: 12px;
}}
QLabel#navLocalTitle {{
    color: #75D7BD;
    font-size: 11px;
    font-weight: 600;
}}
QLabel#navLocalNote {{
    color: {t["NAV_MUTED"]};
    font-size: 10px;
}}
QFrame#topBar {{
    background-color: {t["TOP_BAR_BG"]};
    border-bottom: 1px solid {t["BORDER_SUBTLE"]};
}}
QFrame#canvas {{
    background-color: {t["WINDOW_BG"]};
}}
QLabel#dateChip {{
    color: {t["TEXT_SECONDARY"]};
    background-color: {t["SURFACE_3"]};
    border: 1px solid {t["BORDER_SUBTLE"]};
    border-radius: 9px;
    padding: 7px 12px;
    font-size: 11px;
}}
QPushButton#topSettingsButton {{
    color: {t["TEXT_SECONDARY"]};
    background-color: {t["SURFACE_1"]};
    border: 1px solid {t["BORDER_NORMAL"]};
    border-radius: 9px;
    padding: 0 12px;
    font-size: 12px;
}}
QPushButton#topSettingsButton:hover {{
    color: {t["ACCENT_TEXT"]};
    border-color: {t["ACCENT_BORDER"]};
    background-color: {t["ACCENT_DARK_BG"]};
}}

/* ── Navigation actions ───────────────────────────────────── */
QPushButton#navBtn {{
    background-color: transparent;
    border: none;
    border-radius: 10px;
    color: {t["NAV_MUTED"]};
    font-size: 13px;
    font-weight: 500;
    text-align: left;
    padding: 0 14px;
    min-height: 44px;
    max-height: 44px;
}}
QPushButton#navBtn:hover {{
    background-color: {t["NAV_SURFACE"]};
    color: {t["NAV_TEXT"]};
}}
QPushButton#navBtn:checked {{
    background-color: {t["NAV_ACTIVE_BG"]};
    color: {t["NAV_TEXT"]};
    border-left: 3px solid {t["NAV_ACCENT"]};
    padding-left: 11px;
}}
QPushButton#navSecondaryBtn {{
    background-color: transparent;
    border: none;
    border-radius: 9px;
    color: {t["NAV_MUTED"]};
    text-align: left;
    min-height: 38px;
    max-height: 38px;
    padding: 0 13px;
    font-size: 12px;
    font-weight: 500;
}}
QPushButton#navSecondaryBtn:hover {{
    background-color: {t["NAV_SURFACE"]};
    color: {t["NAV_TEXT"]};
}}

/* ── Default buttons — flush, minimal ────────────────────── */
QPushButton, QToolButton {{
    min-height: 36px;
    padding: 0 16px;
    color: {t["TEXT_PRIMARY"]};
    background-color: transparent;
    border: 1px solid {t["BORDER_NORMAL"]};
    border-radius: {T.RADIUS_SM}px;
    font-weight: {T.WEIGHT_BUTTON};
    font-size: 13px;
}}
QPushButton:hover, QToolButton:hover {{
    background-color: {t["SURFACE_3"]};
    border-color: {t["BORDER_STRONG"]};
}}
QPushButton:pressed, QToolButton:pressed {{
    background-color: {t["SURFACE_3"]};
}}
QPushButton:focus, QToolButton:focus,
QLineEdit:focus, QSpinBox:focus, QTimeEdit:focus {{
    border: 1px solid {t["BORDER_FOCUS"]};
}}
QPushButton:disabled, QToolButton:disabled {{
    color: {t["TEXT_DISABLED"]};
    background-color: transparent;
    border-color: {t["BORDER_SUBTLE"]};
}}

/* ── Primary button — 淡色块 + 细色条，不用饱和实色 ───────── */
QPushButton#primaryButton {{
    min-height: 44px;
    color: {t["ACCENT"]};
    background-color: {T.hex_alpha(t["ACCENT"], 0.10)};
    border: 1px solid {T.hex_alpha(t["ACCENT"], 0.32)};
    border-radius: {T.RADIUS_SM}px;
    font-size: 14px;
    font-weight: {T.WEIGHT_SECTION};
}}
QPushButton#primaryButton:hover {{
    background-color: {T.hex_alpha(t["ACCENT"], 0.16)};
    border-color: {T.hex_alpha(t["ACCENT"], 0.45)};
}}
QPushButton#primaryButton:pressed {{
    background-color: {T.hex_alpha(t["ACCENT"], 0.22)};
    border-color: {T.hex_alpha(t["ACCENT"], 0.52)};
}}
QPushButton#primaryButton:disabled {{
    color: {t["TEXT_DISABLED"]};
    background-color: {t["SURFACE_3"]};
    border-color: {t["BORDER_SUBTLE"]};
}}

/* ── Ghost / danger — 危险按钮同样用淡色块方案 ─────────────── */
QPushButton#ghostButton {{
    color: {t["TEXT_SECONDARY"]};
    background-color: transparent;
    border-color: transparent;
}}
QPushButton#ghostButton:hover {{
    color: {t["TEXT_PRIMARY"]};
    background-color: {t["SURFACE_3"]};
}}
QPushButton#dangerButton {{
    color: {t["DANGER"]};
    background-color: {T.hex_alpha(t["DANGER"], 0.08)};
    border: 1px solid {T.hex_alpha(t["DANGER"], 0.32)};
}}
QPushButton#dangerButton:hover {{
    background-color: {T.hex_alpha(t["DANGER"], 0.16)};
    border-color: {T.hex_alpha(t["DANGER"], 0.45)};
}}

/* ── Chips / presets ─────────────────────────────────────── */
QPushButton#presetButton, QToolButton#appChip, QToolButton#intensityCard {{
    min-height: 36px;
    background-color: transparent;
    border: 1px solid {t["BORDER_NORMAL"]};
    color: {t["TEXT_SECONDARY"]};
    border-radius: {T.RADIUS_SM}px;
}}
QPushButton#presetButton:checked,
QToolButton#appChip:checked,
QToolButton#intensityCard:checked {{
    color: {t["ACCENT_TEXT"]};
    background-color: {t["ACCENT_DARK_BG"]};
    border: 1px solid {t["ACCENT"]};
}}
QToolButton#appChip {{ padding: 0 10px; }}
QToolButton#intensityCard {{
    min-height: 64px;
    padding: 10px 14px;
    text-align: left;
}}

/* ── Inputs — flush, minimal ────────────────────────────── */
QLineEdit, QSpinBox, QTimeEdit, QComboBox {{
    min-height: 38px;
    padding: 0 12px;
    color: {t["TEXT_PRIMARY"]};
    background-color: {t["INPUT_BG"]};
    border: 1px solid {t["BORDER_NORMAL"]};
    border-radius: {T.RADIUS_SM}px;
    selection-background-color: {t["ACCENT_MUTED"]};
    font-size: 14px;
}}
QLineEdit::placeholder {{ color: {t["TEXT_DISABLED"]}; }}
QSpinBox {{ padding-right: 24px; }}
QSpinBox::up-button, QSpinBox::down-button {{
    background: transparent;
    border: none;
    width: 20px;
}}

/* ── Scrollbars — thin, unobtrusive ─────────────────────── */
QScrollArea {{ background: transparent; border: none; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 4px 0;
}}
QScrollBar::handle:vertical {{
    background: {t["BORDER_STRONG"]};
    border-radius: 4px;
    min-height: 32px;
}}
QScrollBar::handle:vertical:hover {{ background: {t["TEXT_TERTIARY"]}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{
    background: transparent;
    height: 8px;
    margin: 0 4px;
}}
QScrollBar::handle:horizontal {{
    background: {t["BORDER_STRONG"]};
    border-radius: 4px;
    min-width: 32px;
}}
QScrollBar::handle:horizontal:hover {{ background: {t["TEXT_TERTIARY"]}; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

/* ── Progress bar — hairline ─────────────────────────────── */
QProgressBar {{
    min-height: 4px;
    max-height: 4px;
    background-color: {t["RING_TRACK"]};
    border: none;
    border-radius: 2px;
}}
QProgressBar::chunk {{
    background-color: {t["ACCENT"]};
    border-radius: 2px;
}}

/* ── Table — editorial, minimal lines ───────────────────── */
QTableWidget {{
    background-color: {t["SURFACE_1"]};
    alternate-background-color: {t["SURFACE_1"]};
    border: 1px solid {t["BORDER_SUBTLE"]};
    border-radius: {T.RADIUS_MD}px;
    gridline-color: transparent;
    selection-background-color: {t["ACCENT_MUTED"]};
    selection-color: {t["TEXT_PRIMARY"]};
    outline: none;
}}
QTableWidget::item {{
    padding: 10px 16px;
    border-bottom: 1px solid {t["BORDER_SUBTLE"]};
}}
QHeaderView::section {{
    color: {t["TEXT_TERTIARY"]};
    background-color: transparent;
    border: none;
    border-bottom: 1px solid {t["BORDER_NORMAL"]};
    padding: 10px 16px;
    font-size: 12px;
    font-weight: {T.WEIGHT_SECTION};
}}

/* ── Menu / tray ─────────────────────────────────────────── */
QMenu {{
    color: {t["TEXT_PRIMARY"]};
    background-color: {t["SURFACE_2"]};
    border: 1px solid {t["BORDER_NORMAL"]};
    border-radius: {T.RADIUS_SM}px;
    padding: 6px;
}}
QMenu::item {{ padding: 8px 20px; border-radius: 6px; }}
QMenu::item:selected {{ background-color: {t["SURFACE_3"]}; }}
QMessageBox {{ background-color: {t["SURFACE_1"]}; }}
QMessageBox QLabel {{ color: {t["TEXT_PRIMARY"]}; min-width: 280px; }}
QToolTip {{
    color: {t["TEXT_PRIMARY"]};
    background-color: {t["SURFACE_2"]};
    border: 1px solid {t["BORDER_NORMAL"]};
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
}}

/* ── Calendar — open grid, no card borders ──────────────── */
QFrame#calendarCell {{
    background-color: transparent;
    border: none;
    border-radius: 0;
}}
QFrame#calendarCellToday {{
    background-color: {t["CAL_TODAY"]};
    border: none;
    border-radius: 0;
}}
QFrame#calendarHeader {{
    background-color: transparent;
    border: none;
}}
QFrame#calendarWeekHeader {{
    background-color: transparent;
    border-bottom: 1px solid {t["BORDER_SUBTLE"]};
}}

/* ── Trend chart ─────────────────────────────────────────── */
QFrame#chartPanel {{
    background-color: {t["SURFACE_1"]};
    border: 1px solid {t["BORDER_NORMAL"]};
    border-radius: {T.RADIUS_MD}px;
}}
QFrame#chartBar {{
    background-color: {t["ACCENT"]};
    border-radius: 2px;
}}
QFrame#chartBarWeekend {{
    background-color: {t["TEXT_TERTIARY"]};
    border-radius: 2px;
}}

/* ── Segmented control ───────────────────────────────────── */
QFrame#segmentedControl {{
    background-color: {t["SURFACE_3"]};
    border: 1px solid {t["BORDER_SUBTLE"]};
    border-radius: 8px;
    padding: 2px;
}}
QPushButton#segmentedBtn {{
    min-height: 32px;
    border: none;
    border-radius: 6px;
    background-color: transparent;
    color: {t["TEXT_TERTIARY"]};
    font-weight: {T.WEIGHT_BUTTON};
    padding: 0 12px;
}}
QPushButton#segmentedBtn:checked {{
    background-color: {t["SURFACE_1"]};
    color: {t["ACCENT_TEXT"]};
    border: 1px solid {t["ACCENT_BORDER"]};
}}
QPushButton#segmentedBtn:hover {{
    color: {t["TEXT_SECONDARY"]};
}}

/* ── Badges — restrained, small ──────────────────────────── */
QLabel#statusBadge {{
    background-color: {t["ACCENT_DARK_BG"]};
    color: {t["ACCENT_TEXT"]};
    border: none;
    border-radius: 10px;
    padding: 3px 10px;
    font-size: 11px;
    font-weight: {T.WEIGHT_SECTION};
}}
QLabel#breakBadge {{
    background-color: {t["WARNING_BG"]};
    color: {t["WARNING"]};
    border: none;
    border-radius: 10px;
    padding: 3px 10px;
    font-size: 11px;
    font-weight: {T.WEIGHT_SECTION};
}}

/* ── Toggle switch ───────────────────────────────────────── */
QPushButton#toggleSwitch {{
    min-height: 22px;
    max-height: 22px;
    min-width: 40px;
    max-width: 40px;
    border-radius: 11px;
    background-color: {t["RING_TRACK"]};
    border: 1px solid {t["BORDER_NORMAL"]};
    padding: 0;
}}
QPushButton#toggleSwitch:checked {{
    background-color: {t["ACCENT"]};
    border-color: {t["ACCENT"]};
}}

/* ── Goal command input ──────────────────────────────────── */
QLineEdit#goalInput {{
    min-height: 48px;
    padding: 0 20px;
    font-size: 16px;
    border: 1px solid {t["BORDER_NORMAL"]};
    border-radius: {T.RADIUS_SM}px;
    background-color: {t["INPUT_BG"]};
    color: {t["TEXT_PRIMARY"]};
}}
QLineEdit#goalInput:focus {{
    border: 1px solid {t["ACCENT"]};
}}

/* ── Calendar detail panel ────────────────────────────────── */
QFrame#detailPanel {{
    background-color: {t["SURFACE_1"]};
    border: 1px solid {t["BORDER_NORMAL"]};
    border-radius: {T.RADIUS_LG}px;
}}

/* ── Checkbox — minimal ───────────────────────────────────── */
QCheckBox {{
    color: {t["TEXT_PRIMARY"]};
    font-size: 14px;
    spacing: 8px;
    font-weight: {T.WEIGHT_BODY};
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1.5px solid {t["BORDER_STRONG"]};
    border-radius: 4px;
    background-color: transparent;
}}
QCheckBox::indicator:checked {{
    background-color: {t["ACCENT"]};
    border-color: {t["ACCENT"]};
}}
QCheckBox::indicator:hover {{
    border-color: {t["ACCENT"]};
}}

/* ── Time edit ────────────────────────────────────────────── */
QTimeEdit {{
    min-height: 36px;
    padding: 0 8px;
    font-size: 14px;
    color: {t["TEXT_PRIMARY"]};
    background-color: {t["INPUT_BG"]};
    border: 1px solid {t["BORDER_NORMAL"]};
    border-radius: {T.RADIUS_SM}px;
}}
QTimeEdit:focus {{
    border: 1px solid {t["ACCENT"]};
}}
QTimeEdit::up-button, QTimeEdit::down-button {{
    width: 18px;
    border: none;
    background: transparent;
}}

/* ── Group box — no card, subtle label ────────────────────── */
QGroupBox {{
    border: none;
    border-radius: 0;
    margin-top: 0;
    padding-top: 0;
    font-size: 14px;
    font-weight: {T.WEIGHT_SECTION};
    color: {t["TEXT_SECONDARY"]};
}}

/* ── Tab bar — minimal underline ─────────────────────────── */
QTabWidget::pane {{
    border: none;
    border-top: 1px solid {t["BORDER_SUBTLE"]};
    border-radius: 0;
    background-color: transparent;
}}
QTabBar::tab {{
    background-color: transparent;
    color: {t["TEXT_TERTIARY"]};
    padding: 8px 16px;
    border: none;
    border-bottom: 2px solid transparent;
    font-weight: {T.WEIGHT_BUTTON};
    font-size: 13px;
}}
QTabBar::tab:selected {{
    color: {t["TEXT_PRIMARY"]};
    border-bottom: 2px solid {t["ACCENT"]};
}}
QTabBar::tab:hover {{
    color: {t["TEXT_SECONDARY"]};
}}

/* ── Timeline row ─────────────────────────────────────────── */
QFrame#timelineRow {{
    background-color: transparent;
    border: none;
    border-radius: 0;
}}
QFrame#timelineRow:selected {{
    background-color: {t["SURFACE_3"]};
    border-radius: 8px;
}}
QFrame#timelineRow:hover {{
    background-color: {t["SURFACE_3"]};
    border-radius: 8px;
}}
"""

STYLESHEET = _build_stylesheet()
