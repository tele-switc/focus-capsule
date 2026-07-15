"""Central visual system for Focus Capsule.

The palette is inspired by a quiet night observatory: deep blue surfaces keep
the interface calm, sea-glass green marks commitment, and warm amber is
reserved for a deliberate break.
"""

from focus_capsule.theme import (
    ACCENT, ACCENT_HOVER, ACCENT_BORDER, ACCENT_MUTED, ACCENT_TEXT, ACCENT_DARK_BG,
    WINDOW_BG, TOP_BAR_BG, SURFACE_1, SURFACE_2, SURFACE_3, INPUT_BG, OVERLAY_BG,
    BORDER_SUBTLE, BORDER_NORMAL, BORDER_STRONG, BORDER_FOCUS,
    WARNING, SUCCESS, DANGER, INFO,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_TERTIARY, TEXT_DISABLED,
    RING_TRACK, DIVIDER,
    BREAK_BG, BREAK_ACCENT, BREAK_LIGHT,
    RADIUS_SM, RADIUS_MD, RADIUS_LG, RADIUS_XL,
    FONT_PAGE_TITLE, FONT_WINDOW_TITLE, FONT_SECTION, FONT_BODY, FONT_AUX, FONT_META,
    WEIGHT_TITLE, WEIGHT_SECTION, WEIGHT_BUTTON, WEIGHT_BODY, WEIGHT_NUMBER,
    hex_alpha,
)

STYLESHEET = r"""
/* ═══════════════════════════════════════════════════════════
   Focus Capsule — Unified QSS  (v2.1 design system)
   ═══════════════════════════════════════════════════════════ */

/* ── Base ──────────────────────────────────────────────────── */
QWidget {
    background: transparent;
    color: #F4F7FB;
    font-size: """ + str(FONT_BODY) + r"""px;
}

QMainWindow, QDialog, QWidget#appWindow {
    background-color: """ + WINDOW_BG + r""";
}

QLabel { color: """ + TEXT_PRIMARY + r"""; }

/* ── Brand ─────────────────────────────────────────────────── */
QLabel#brandTitle {
    font-size: """ + str(FONT_WINDOW_TITLE) + r"""px;
    font-weight: """ + str(WEIGHT_TITLE) + r""";
}
QLabel#brandSubtitle, QLabel#subtitle {
    color: """ + TEXT_TERTIARY + r""";
    font-size: """ + str(FONT_AUX) + r"""px;
}
QLabel#eyebrow {
    color: """ + ACCENT + r""";
    font-size: """ + str(FONT_META) + r"""px;
    font-weight: """ + str(WEIGHT_TITLE) + r""";
    letter-spacing: 1px;
}

/* ── Page / Section headings ────────────────────────────────── */
QLabel#pageTitle {
    color: """ + TEXT_PRIMARY + r""";
    font-size: """ + str(FONT_PAGE_TITLE) + r"""px;
    font-weight: """ + str(WEIGHT_TITLE) + r""";
    letter-spacing: -0.3px;
}
QLabel#sectionTitle {
    color: """ + TEXT_PRIMARY + r""";
    font-size: """ + str(FONT_SECTION) + r"""px;
    font-weight: """ + str(WEIGHT_SECTION) + r""";
}
QLabel#bodyMuted, QLabel#hint {
    color: """ + TEXT_TERTIARY + r""";
    font-size: """ + str(FONT_AUX) + r""";
}
QLabel#tinyMuted {
    color: """ + TEXT_DISABLED + r""";
    font-size: """ + str(FONT_META) + r""";
}

/* ── Summary / stat ────────────────────────────────────────── */
QLabel#summaryGoal {
    color: """ + TEXT_PRIMARY + r""";
    font-size: 17px;
    font-weight: """ + str(WEIGHT_SECTION) + r""";
}
QLabel#summaryValue {
    color: """ + TEXT_PRIMARY + r""";
    font-size: 13px;
    font-weight: """ + str(WEIGHT_SECTION) + r""";
}
QLabel#summaryKey {
    color: """ + TEXT_TERTIARY + r""";
    font-size: """ + str(FONT_AUX) + r""";
}
QLabel#statValue {
    color: """ + TEXT_PRIMARY + r""";
    font-size: 25px;
    font-weight: """ + str(WEIGHT_TITLE) + r""";
}
QLabel#statCaption {
    color: """ + TEXT_TERTIARY + r""";
    font-size: """ + str(FONT_META) + r""";
}

/* ── Badges ────────────────────────────────────────────────── */
QLabel#statusBadge {
    background-color: """ + ACCENT_DARK_BG + r""";
    color: """ + ACCENT_TEXT + r""";
    border: 1px solid """ + ACCENT_BORDER + r""";
    border-radius: 12px;
    padding: 4px 10px;
    font-size: """ + str(FONT_META) + r""";
    font-weight: """ + str(WEIGHT_TITLE) + r""";
}
QLabel#breakBadge {
    background-color: #382C1D;
    color: """ + BREAK_ACCENT + r""";
    border: 1px solid #5A4529;
    border-radius: 12px;
    padding: 4px 10px;
    font-size: """ + str(FONT_META) + r""";
    font-weight: """ + str(WEIGHT_TITLE) + r""";
}

/* ── Panels / surfaces ─────────────────────────────────────── */
QFrame#panel {
    background-color: """ + SURFACE_1 + r""";
    border: 1px solid """ + BORDER_SUBTLE + r""";
    border-radius: """ + str(RADIUS_XL) + r"""px;
}
QFrame#sectionCard, QFrame#statCard {
    background-color: """ + SURFACE_2 + r""";
    border: 1px solid """ + BORDER_SUBTLE + r""";
    border-radius: """ + str(RADIUS_LG) + r"""px;
}
QFrame#softPanel {
    background-color: """ + INPUT_BG + r""";
    border: 1px solid """ + BORDER_SUBTLE + r""";
    border-radius: """ + str(RADIUS_MD) + r"""px;
}
QFrame#breakPanel {
    background-color: """ + BREAK_BG + r""";
    border: 1px solid #594329;
    border-radius: """ + str(RADIUS_MD) + r"""px;
}
QFrame#divider {
    background-color: """ + DIVIDER + r""";
    max-height: 1px;
}

/* ── Buttons ───────────────────────────────────────────────── */
QPushButton, QToolButton {
    min-height: 38px;
    padding: 0 16px;
    color: """ + TEXT_SECONDARY + r""";
    background-color: """ + SURFACE_3 + r""";
    border: 1px solid """ + BORDER_NORMAL + r""";
    border-radius: """ + str(RADIUS_MD) + r"""px;
    font-weight: """ + str(WEIGHT_BUTTON) + r""";
}
QPushButton:hover, QToolButton:hover {
    color: """ + TEXT_PRIMARY + r""";
    background-color: #1D2D45;
    border-color: """ + BORDER_STRONG + r""";
}
QPushButton:pressed, QToolButton:pressed {
    background-color: #22344E;
}
QPushButton:focus, QToolButton:focus,
QLineEdit:focus, QSpinBox:focus, QTimeEdit:focus {
    border: 2px solid """ + BORDER_FOCUS + r""";
}
QPushButton:disabled, QToolButton:disabled {
    color: """ + TEXT_DISABLED + r""";
    background-color: """ + INPUT_BG + r""";
    border-color: """ + BORDER_SUBTLE + r""";
}

/* ── Primary button ────────────────────────────────────────── */
QPushButton#primaryButton {
    min-height: 44px;
    color: #071510;
    background-color: """ + ACCENT + r""";
    border: 1px solid """ + ACCENT + r""";
    border-radius: """ + str(RADIUS_LG) + r"""px;
    font-size: 15px;
    font-weight: 750;
}
QPushButton#primaryButton:hover {
    background-color: """ + ACCENT_HOVER + r""";
    border-color: """ + ACCENT_HOVER + r""";
}
QPushButton#primaryButton:pressed {
    background-color: #58BAA8;
}
QPushButton#primaryButton:disabled {
    color: #6F7B87;
    background-color: #1A2635;
    border-color: #28364A;
}

/* ── Ghost / danger ────────────────────────────────────────── */
QPushButton#ghostButton, QToolButton#ghostButton {
    color: """ + TEXT_SECONDARY + r""";
    background-color: transparent;
    border-color: transparent;
}
QPushButton#ghostButton:hover, QToolButton#ghostButton:hover {
    color: """ + TEXT_PRIMARY + r""";
    background-color: """ + SURFACE_3 + r""";
    border-color: """ + BORDER_NORMAL + r""";
}
QPushButton#dangerButton {
    color: #F2A2A2;
    background-color: transparent;
    border-color: #5B343B;
}
QPushButton#dangerButton:hover {
    background-color: #2E1B22;
    border-color: #8B4C56;
}

/* ── Chip / preset / intensity ─────────────────────────────── */
QPushButton#presetButton, QToolButton#appChip, QToolButton#intensityCard {
    min-height: 38px;
    background-color: """ + SURFACE_1 + r""";
    border: 1px solid """ + BORDER_NORMAL + r""";
    color: """ + TEXT_SECONDARY + r""";
}
QPushButton#presetButton:checked,
QToolButton#appChip:checked,
QToolButton#intensityCard:checked {
    color: """ + ACCENT_TEXT + r""";
    background-color: """ + ACCENT_DARK_BG + r""";
    border: 2px solid """ + ACCENT + r""";
}
QToolButton#appChip { padding: 0 12px; }
QToolButton#intensityCard {
    min-height: 68px;
    padding: 10px 14px;
    text-align: left;
}

/* ── Inputs ────────────────────────────────────────────────── */
QLineEdit, QSpinBox {
    min-height: 40px;
    padding: 0 12px;
    color: """ + TEXT_PRIMARY + r""";
    background-color: """ + INPUT_BG + r""";
    border: 1px solid """ + BORDER_NORMAL + r""";
    border-radius: """ + str(RADIUS_MD) + r"""px;
    selection-background-color: #35786D;
}
QLineEdit::placeholder { color: #65748A; }
QSpinBox { padding-right: 24px; }
QSpinBox::up-button, QSpinBox::down-button {
    background: transparent;
    border: none;
    width: 20px;
}

/* ── Scrollbars ────────────────────────────────────────────── */
QScrollArea { background: transparent; border: none; }
QScrollArea > QWidget > QWidget { background: transparent; }
QScrollBar:vertical {
    background: transparent;
    width: 8px;
    margin: 4px 0;
}
QScrollBar::handle:vertical {
    background: #33445F;
    border-radius: 4px;
    min-height: 32px;
}
QScrollBar::handle:vertical:hover { background: #465B7A; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

QScrollBar:horizontal {
    background: transparent;
    height: 8px;
    margin: 0 4px;
}
QScrollBar::handle:horizontal {
    background: #33445F;
    border-radius: 4px;
    min-width: 32px;
}
QScrollBar::handle:horizontal:hover { background: #465B7A; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

/* ── Progress bar ──────────────────────────────────────────── */
QProgressBar {
    min-height: 6px;
    max-height: 6px;
    background-color: """ + SURFACE_3 + r""";
    border: none;
    border-radius: 3px;
}
QProgressBar::chunk { background-color: """ + ACCENT + r"""; border-radius: 3px; }

/* ── Table ─────────────────────────────────────────────────── */
QTableWidget {
    background-color: """ + INPUT_BG + r""";
    alternate-background-color: """ + SURFACE_2 + r""";
    border: 1px solid """ + BORDER_SUBTLE + r""";
    border-radius: """ + str(RADIUS_LG) + r"""px;
    gridline-color: transparent;
    selection-background-color: #1D3B3A;
    selection-color: #FFFFFF;
    outline: none;
}
QTableWidget::item {
    padding: 8px 10px;
    border-bottom: 1px solid """ + BORDER_SUBTLE + r""";
}
QHeaderView::section {
    color: """ + TEXT_TERTIARY + r""";
    background-color: """ + SURFACE_3 + r""";
    border: none;
    border-bottom: 1px solid """ + BORDER_NORMAL + r""";
    padding: 10px;
    font-size: """ + str(FONT_META) + r""";
    font-weight: """ + str(WEIGHT_TITLE) + r""";
}

/* ── Menu / tray ───────────────────────────────────────────── */
QMenu {
    color: """ + TEXT_PRIMARY + r""";
    background-color: """ + SURFACE_2 + r""";
    border: 1px solid """ + BORDER_NORMAL + r""";
    border-radius: 8px;
    padding: 6px;
}
QMenu::item { padding: 8px 20px; border-radius: 6px; }
QMenu::item:selected { background-color: """ + SURFACE_3 + r"""; }

QMessageBox { background-color: """ + SURFACE_2 + r"""; }
QMessageBox QLabel { color: """ + TEXT_PRIMARY + r"""; min-width: 280px; }

QToolTip {
    color: """ + TEXT_PRIMARY + r""";
    background-color: """ + SURFACE_3 + r""";
    border: 1px solid """ + BORDER_STRONG + r""";
    padding: 6px;
}

/* ── Calendar (new) ────────────────────────────────────────── */
QFrame#calendarCell {
    background-color: """ + SURFACE_2 + r""";
    border: 1px solid """ + BORDER_SUBTLE + r""";
    border-radius: 8px;
}
QFrame#calendarCellToday {
    background-color: """ + ACCENT_MUTED + r""";
    border: 2px solid """ + ACCENT + r""";
    border-radius: 8px;
}
QFrame#calendarCellHasData {
    background-color: """ + ACCENT_DARK_BG + r""";
    border: 1px solid """ + ACCENT_BORDER + r""";
    border-radius: 8px;
}
QFrame#calendarHeader {
    background-color: """ + SURFACE_3 + r""";
    border-radius: 8px;
}

/* ── Trend chart area (new) ────────────────────────────────── */
QFrame#chartPanel {
    background-color: """ + SURFACE_2 + r""";
    border: 1px solid """ + BORDER_SUBTLE + r""";
    border-radius: """ + str(RADIUS_LG) + r"""px;
}
QFrame#chartBar {
    background-color: """ + ACCENT + r""";
    border-radius: 3px;
}
QFrame#chartBarWeekend {
    background-color: """ + WARNING + r""";
    border-radius: 3px;
}

/* ── Toggle switch (new) ───────────────────────────────────── */
QPushButton#toggleSwitch {
    min-height: 24px;
    max-height: 24px;
    min-width: 44px;
    max-width: 44px;
    border-radius: 12px;
    background-color: """ + SURFACE_3 + r""";
    border: 1px solid """ + BORDER_NORMAL + r""";
    padding: 0;
}
QPushButton#toggleSwitch:checked {
    background-color: """ + ACCENT + r""";
    border-color: """ + ACCENT + r""";
}

/* ── Segmented control (new) ───────────────────────────────── */
QFrame#segmentedControl {
    background-color: """ + INPUT_BG + r""";
    border: 1px solid """ + BORDER_SUBTLE + r""";
    border-radius: 10px;
}
QPushButton#segmentedBtn {
    min-height: 34px;
    border: none;
    border-radius: 8px;
    background-color: transparent;
    color: """ + TEXT_TERTIARY + r""";
    font-weight: """ + str(WEIGHT_BUTTON) + r""";
}
QPushButton#segmentedBtn:checked {
    background-color: """ + SURFACE_3 + r""";
    color: """ + TEXT_PRIMARY + r""";
}
QPushButton#segmentedBtn:hover {
    color: """ + TEXT_SECONDARY + r""";
}
"""
