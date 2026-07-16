"""Central QSS stylesheet for Focus Capsule v3.0.

Warm light theme inspired by Apple/Linear/Vercel.
All colours sourced from theme.py via the QSS generator below.
"""

from __future__ import annotations

from focus_capsule import theme as T


def _build_stylesheet() -> str:
    """Generate QSS from current theme tokens."""
    t = T.current()
    return f"""


/* ═════════════════════════════════════════════════════════════
   Focus Capsule v3.0 — QSS Design System
   ═════════════════════════════════════════════════════════════ */

/* ── Base ──────────────────────────────────────────────────── */
QWidget {{
    background: transparent;
    color: {t["TEXT_PRIMARY"]};
    font-size: {T.FONT_BODY}px;
    font-family: "MiSans", "HarmonyOS Sans SC", "Microsoft YaHei UI", "Inter", "Segoe UI", sans-serif;
}}
QMainWindow, QDialog, QWidget#appWindow {{
    background-color: {t["WINDOW_BG"]};
}}
QLabel {{ color: {t["TEXT_PRIMARY"]}; background: transparent; }}

/* ── Typography ────────────────────────────────────────────── */
QLabel#pageTitle {{
    color: {t["TEXT_PRIMARY"]};
    font-size: {T.FONT_PAGE_TITLE}px;
    font-weight: {T.WEIGHT_TITLE};
    letter-spacing: -0.5px;
}}
QLabel#sectionTitle {{
    color: {t["TEXT_PRIMARY"]};
    font-size: {T.FONT_SECTION_TITLE}px;
    font-weight: {T.WEIGHT_SECTION};
}}
QLabel#eyebrow {{
    color: {t["ACCENT"]};
    font-size: {T.FONT_META}px;
    font-weight: {T.WEIGHT_TITLE};
    letter-spacing: 1.2px;
    text-transform: uppercase;
}}
QLabel#heroTimer {{
    color: {t["TEXT_PRIMARY"]};
    font-size: {T.FONT_TIMER_HUGE}px;
    font-weight: {T.WEIGHT_NUMBER};
    font-family: "SF Mono", "Cascadia Mono", "Consolas", monospace;
    letter-spacing: -2px;
}}
QLabel#heroGoal {{
    color: {t["TEXT_PRIMARY"]};
    font-size: 24px;
    font-weight: {T.WEIGHT_SECTION};
    letter-spacing: -0.3px;
}}
QLabel#heroMetric {{
    color: {t["TEXT_PRIMARY"]};
    font-size: 56px;
    font-weight: {T.WEIGHT_NUMBER};
    font-family: "SF Mono", "Cascadia Mono", "Consolas", monospace;
    letter-spacing: -1px;
}}
QLabel#body, QLabel#bodyMuted {{
    color: {t["TEXT_SECONDARY"]};
    font-size: {T.FONT_BODY}px;
}}
QLabel#bodyTertiary, QLabel#hint, QLabel#tinyMuted {{
    color: {t["TEXT_TERTIARY"]};
    font-size: {T.FONT_BODY_SMALL}px;
}}
QLabel#summaryKey {{
    color: {t["TEXT_TERTIARY"]};
    font-size: {T.FONT_META}px;
    font-weight: {T.WEIGHT_BODY};
    letter-spacing: 0.3px;
}}
QLabel#summaryValue {{
    color: {t["TEXT_PRIMARY"]};
    font-size: {T.FONT_BODY}px;
    font-weight: {T.WEIGHT_SECTION};
}}
QLabel#summaryGoal {{
    color: {t["TEXT_PRIMARY"]};
    font-size: 16px;
    font-weight: {T.WEIGHT_SECTION};
}}

/* ── Surfaces / Panels ─────────────────────────────────────── */
QFrame#panel {{
    background-color: {t["SURFACE_1"]};
    border: 1px solid {t["BORDER_SUBTLE"]};
    border-radius: {T.RADIUS_LG}px;
}}
QFrame#sectionCard, QFrame#statCard {{
    background-color: {t["SURFACE_1"]};
    border: 1px solid {t["BORDER_SUBTLE"]};
    border-radius: {T.RADIUS_LG}px;
}}
QFrame#softPanel {{
    background-color: {t["SURFACE_2"]};
    border: 1px solid {t["BORDER_SUBTLE"]};
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
QFrame#navRail {{
    background-color: {t["WINDOW_BG"]};
    border-right: 1px solid {t["BORDER_SUBTLE"]};
}}
QFrame#topBar {{
    background-color: {t["WINDOW_BG"]};
    border-bottom: 1px solid {t["BORDER_SUBTLE"]};
}}
QFrame#canvas {{
    background-color: {t["WINDOW_BG"]};
}}

/* ── Navigation Rail ───────────────────────────────────────── */
QPushButton#navBtn {{
    background-color: transparent;
    border: none;
    border-radius: {T.RADIUS_MD}px;
    color: {t["TEXT_TERTIARY"]};
    font-size: {T.FONT_BODY_SMALL}px;
    font-weight: {T.WEIGHT_BODY};
    padding: 8px 4px;
    min-height: 52px;
    max-width: 56px;
}}
QPushButton#navBtn:hover {{
    background-color: {t["SURFACE_2"]};
    color: {t["TEXT_SECONDARY"]};
}}
QPushButton#navBtn:checked {{
    background-color: {t["TEXT_PRIMARY"]};
    color: {t["SURFACE_1"]};
    border-radius: {T.RADIUS_SM}px;
}}

/* ── Buttons ───────────────────────────────────────────────── */
QPushButton, QToolButton {{
    min-height: 36px;
    padding: 0 14px;
    color: {t["TEXT_PRIMARY"]};
    background-color: {t["SURFACE_1"]};
    border: 1px solid {t["BORDER_NORMAL"]};
    border-radius: {T.RADIUS_MD}px;
    font-weight: {T.WEIGHT_BUTTON};
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
    border: 2px solid {t["BORDER_FOCUS"]};
}}
QPushButton:disabled, QToolButton:disabled {{
    color: {t["TEXT_DISABLED"]};
    background-color: {t["SURFACE_2"]};
    border-color: {t["BORDER_SUBTLE"]};
}}

/* ── Primary button ────────────────────────────────────────── */
QPushButton#primaryButton {{
    min-height: 44px;
    color: #FFFFFF;
    background-color: {t["ACCENT"]};
    border: 1px solid {t["ACCENT"]};
    border-radius: {T.RADIUS_LG}px;
    font-size: 15px;
    font-weight: 600;
}}
QPushButton#primaryButton:hover {{
    background-color: {t["ACCENT_HOVER"]};
    border-color: {t["ACCENT_HOVER"]};
}}
QPushButton#primaryButton:pressed {{
    background-color: {t["ACCENT_HOVER"]};
}}
QPushButton#primaryButton:disabled {{
    color: {t["TEXT_DISABLED"]};
    background-color: {t["SURFACE_3"]};
    border-color: {t["BORDER_SUBTLE"]};
}}

/* ── Ghost / danger ────────────────────────────────────────── */
QPushButton#ghostButton {{
    color: {t["TEXT_SECONDARY"]};
    background-color: transparent;
    border-color: transparent;
}}
QPushButton#ghostButton:hover {{
    color: {t["TEXT_PRIMARY"]};
    background-color: {t["SURFACE_2"]};
}}
QPushButton#dangerButton {{
    color: {t["DANGER"]};
    background-color: transparent;
    border: 1px solid {t["DANGER_BG"]};
}}
QPushButton#dangerButton:hover {{
    background-color: {t["DANGER_BG"]};
    border-color: {t["DANGER"]};
}}

/* ── Chips / presets ──────────────────────────────────────── */
QPushButton#presetButton, QToolButton#appChip, QToolButton#intensityCard {{
    min-height: 36px;
    background-color: {t["SURFACE_1"]};
    border: 1px solid {t["BORDER_NORMAL"]};
    color: {t["TEXT_SECONDARY"]};
}}
QPushButton#presetButton:checked,
QToolButton#appChip:checked,
QToolButton#intensityCard:checked {{
    color: {t["ACCENT_TEXT"]};
    background-color: {t["ACCENT_DARK_BG"]};
    border: 2px solid {t["ACCENT"]};
}}
QToolButton#appChip {{ padding: 0 10px; }}
QToolButton#intensityCard {{
    min-height: 64px;
    padding: 10px 14px;
    text-align: left;
}}

/* ── Inputs ────────────────────────────────────────────────── */
QLineEdit, QSpinBox, QTimeEdit, QComboBox {{
    min-height: 38px;
    padding: 0 12px;
    color: {t["TEXT_PRIMARY"]};
    background-color: {t["INPUT_BG"]};
    border: 1px solid {t["INPUT_BORDER"] if "INPUT_BORDER" in t else t["BORDER_NORMAL"]};
    border-radius: {T.RADIUS_MD}px;
    selection-background-color: {t["ACCENT_MUTED"]};
}}
QLineEdit::placeholder {{ color: {t["TEXT_DISABLED"]}; }}
QSpinBox {{ padding-right: 24px; }}
QSpinBox::up-button, QSpinBox::down-button {{
    background: transparent;
    border: none;
    width: 20px;
}}

/* ── Scrollbars ────────────────────────────────────────────── */
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

/* ── Progress bar ──────────────────────────────────────────── */
QProgressBar {{
    min-height: 6px;
    max-height: 6px;
    background-color: {t["RING_TRACK"]};
    border: none;
    border-radius: 3px;
}}
QProgressBar::chunk {{
    background-color: {t["ACCENT"]};
    border-radius: 3px;
}}

/* ── Table ─────────────────────────────────────────────────── */
QTableWidget {{
    background-color: {t["SURFACE_1"]};
    alternate-background-color: {t["SURFACE_2"]};
    border: 1px solid {t["BORDER_SUBTLE"]};
    border-radius: {T.RADIUS_LG}px;
    gridline-color: transparent;
    selection-background-color: {t["ACCENT_MUTED"]};
    selection-color: {t["TEXT_PRIMARY"]};
    outline: none;
}}
QTableWidget::item {{
    padding: 8px 12px;
    border-bottom: 1px solid {t["BORDER_SUBTLE"]};
}}
QHeaderView::section {{
    color: {t["TEXT_TERTIARY"]};
    background-color: {t["SURFACE_2"]};
    border: none;
    border-bottom: 1px solid {t["BORDER_NORMAL"]};
    padding: 10px 12px;
    font-size: {T.FONT_META}px;
    font-weight: {T.WEIGHT_TITLE};
}}

/* ── Menu / tray ───────────────────────────────────────────── */
QMenu {{
    color: {t["TEXT_PRIMARY"]};
    background-color: {t["SURFACE_1"]};
    border: 1px solid {t["BORDER_NORMAL"]};
    border-radius: {T.RADIUS_MD}px;
    padding: 6px;
}}
QMenu::item {{ padding: 8px 20px; border-radius: {T.RADIUS_SM}px; }}
QMenu::item:selected {{ background-color: {t["SURFACE_3"]}; }}
QMessageBox {{ background-color: {t["SURFACE_1"]}; }}
QMessageBox QLabel {{ color: {t["TEXT_PRIMARY"]}; min-width: 280px; }}
QToolTip {{
    color: {t["TEXT_PRIMARY"]};
    background-color: {t["SURFACE_3"]};
    border: 1px solid {t["BORDER_STRONG"]};
    border-radius: {T.RADIUS_SM}px;
    padding: 6px 10px;
    font-size: {T.FONT_META}px;
}}

/* ── Calendar ──────────────────────────────────────────────── */
QFrame#calendarCell {{
    background-color: transparent;
    border: none;
    border-radius: 0;
}}
QFrame#calendarCellToday {{
    background-color: transparent;
    border: none;
}}
QFrame#calendarHeader {{
    background-color: transparent;
    border: none;
}}
QFrame#calendarWeekHeader {{
    background-color: transparent;
    border-bottom: 1px solid {t["BORDER_SUBTLE"]};
}}

/* ── Trend chart ───────────────────────────────────────────── */
QFrame#chartPanel {{
    background-color: transparent;
    border: none;
}}
QFrame#chartBar {{
    background-color: {t["ACCENT"]};
    border-radius: 3px;
}}
QFrame#chartBarWeekend {{
    background-color: {t["TEXT_TERTIARY"]};
    border-radius: 3px;
}}

/* ── Segmented control ─────────────────────────────────────── */
QFrame#segmentedControl {{
    background-color: {t["SURFACE_2"]};
    border: 1px solid {t["BORDER_SUBTLE"]};
    border-radius: {T.RADIUS_MD}px;
}}
QPushButton#segmentedBtn {{
    min-height: 34px;
    border: none;
    border-radius: {T.RADIUS_SM}px;
    background-color: transparent;
    color: {t["TEXT_TERTIARY"]};
    font-weight: {T.WEIGHT_BUTTON};
}}
QPushButton#segmentedBtn:checked {{
    background-color: {t["SURFACE_1"]};
    color: {t["TEXT_PRIMARY"]};
}}
QPushButton#segmentedBtn:hover {{
    color: {t["TEXT_SECONDARY"]};
}}

/* ── Badges ────────────────────────────────────────────────── */
QLabel#statusBadge {{
    background-color: {t["ACCENT_DARK_BG"]};
    color: {t["ACCENT_TEXT"]};
    border: 1px solid {t["ACCENT_BORDER"]};
    border-radius: 12px;
    padding: 4px 10px;
    font-size: {T.FONT_META}px;
    font-weight: {T.WEIGHT_TITLE};
}}
QLabel#breakBadge {{
    background-color: {t["WARNING_BG"]};
    color: {t["WARNING"]};
    border: 1px solid {t["WARNING"]};
    border-radius: 12px;
    padding: 4px 10px;
    font-size: {T.FONT_META}px;
    font-weight: {T.WEIGHT_TITLE};
}}

/* ── Agent step flow ──────────────────────────────────────── */
QFrame#stepRow {{
    background: transparent;
    border: none;
    padding: 2px 0;
}}
QLabel#stepIcon {{
    font-size: 16px;
    font-weight: {T.WEIGHT_TITLE};
    min-width: 20px;
}}
QLabel#stepText {{
    color: {t["TEXT_SECONDARY"]};
    font-size: {T.FONT_BODY}px;
}}
QLabel#stepTextActive {{
    color: {t["TEXT_PRIMARY"]};
    font-size: {T.FONT_BODY}px;
    font-weight: {T.WEIGHT_SECTION};
}}
QLabel#stepTextDone {{
    color: {t["TEXT_TERTIARY"]};
    font-size: {T.FONT_BODY}px;
    text-decoration: line-through;
}}

/* ── Toggle switch ─────────────────────────────────────────── */
QPushButton#toggleSwitch {{
    min-height: 24px;
    max-height: 24px;
    min-width: 44px;
    max-width: 44px;
    border-radius: 12px;
    background-color: {t["RING_TRACK"]};
    border: 1px solid {t["BORDER_NORMAL"]};
    padding: 0;
}}
QPushButton#toggleSwitch:checked {{
    background-color: {t["ACCENT"]};
    border-color: {t["ACCENT"]};
}}

/* ── Goal command input ───────────────────────────────────── */
QLineEdit#goalInput {{
    min-height: 48px;
    padding: 0 20px;
    font-size: {T.FONT_SECTION}px;
    border: 1px solid {t["BORDER_NORMAL"]};
    border-radius: {T.RADIUS_LG}px;
    background-color: {t["INPUT_BG"]};
    color: {t["TEXT_PRIMARY"]};
}}
QLineEdit#goalInput:focus {{
    border: 2px solid {t["ACCENT"]};
}}

/* ── Stat inline (no cards) ────────────────────────────────── */
QLabel#statInline {{
    color: {t["TEXT_PRIMARY"]};
    font-size: {T.FONT_SECTION_TITLE}px;
    font-weight: {T.WEIGHT_NUMBER};
}}
QLabel#statCaption {{
    color: {t["TEXT_TERTIARY"]};
    font-size: {T.FONT_META}px;
}}
QLabel#statValue {{
    color: {t["TEXT_PRIMARY"]};
    font-size: 22px;
    font-weight: {T.WEIGHT_TITLE};
}}

/* ── Insight text ─────────────────────────────────────────── */
QLabel#insightText {{
    color: {t["TEXT_SECONDARY"]};
    font-size: {T.FONT_SECTION}px;
    line-height: 1.6;
}}
QLabel#insightKey {{
    color: {t["ACCENT"]};
    font-size: {T.FONT_META}px;
    font-weight: {T.WEIGHT_TITLE};
    letter-spacing: 1px;
}}

/* ── Calendar detail panel ────────────────────────────────── */
QFrame#detailPanel {{
    background-color: {t["SURFACE_1"]};
    border: 1px solid {t["BORDER_SUBTLE"]};
    border-radius: {T.RADIUS_LG}px;
}}

/* ── Checkbox ──────────────────────────────────────────────── */
QCheckBox {{
    color: {t["TEXT_PRIMARY"]};
    font-size: {T.FONT_BODY}px;
    spacing: 8px;
}}
QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border: 1.5px solid {t["BORDER_STRONG"]};
    border-radius: 4px;
    background-color: {t["INPUT_BG"]};
}}
QCheckBox::indicator:checked {{
    background-color: {t["ACCENT"]};
    border-color: {t["ACCENT"]};
}}
QCheckBox::indicator:hover {{
    border-color: {t["ACCENT"]};
}}

/* ── Time edit ─────────────────────────────────────────────── */
QTimeEdit {{
    min-height: 38px;
    padding: 0 8px;
    font-size: {T.FONT_BODY}px;
    color: {t["TEXT_PRIMARY"]};
    background-color: {t["INPUT_BG"]};
    border: 1px solid {t["BORDER_NORMAL"]};
    border-radius: {T.RADIUS_MD}px;
}}
QTimeEdit:focus {{
    border: 2px solid {t["ACCENT"]};
}}
QTimeEdit::up-button, QTimeEdit::down-button {{
    width: 18px;
    border: none;
    background: transparent;
}}

/* ── Group box ─────────────────────────────────────────────── */
QGroupBox {{
    border: 1px solid {t["BORDER_SUBTLE"]};
    border-radius: {T.RADIUS_LG}px;
    margin-top: 12px;
    padding-top: 8px;
    font-size: {T.FONT_SECTION}px;
    font-weight: {T.WEIGHT_SECTION};
    color: {t["TEXT_PRIMARY"]};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 16px;
    padding: 0 6px;
    color: {t["TEXT_SECONDARY"]};
}}

/* ── Tab bar ──────────────────────────────────────────────── */
QTabWidget::pane {{
    border: 1px solid {t["BORDER_SUBTLE"]};
    border-radius: {T.RADIUS_LG}px;
    background-color: {t["SURFACE_1"]};
}}
QTabBar::tab {{
    background-color: transparent;
    color: {t["TEXT_TERTIARY"]};
    padding: 8px 16px;
    border: none;
    border-bottom: 2px solid transparent;
    font-weight: {T.WEIGHT_BUTTON};
}}
QTabBar::tab:selected {{
    color: {t["TEXT_PRIMARY"]};
    border-bottom: 2px solid {t["ACCENT"]};
}}
QTabBar::tab:hover {{
    color: {t["TEXT_SECONDARY"]};
}}
"""

STYLESHEET = _build_stylesheet()
