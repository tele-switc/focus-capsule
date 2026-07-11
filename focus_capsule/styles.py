"""Central visual system for Focus Capsule.

The palette is inspired by a quiet night observatory: deep blue surfaces keep
the interface calm, sea-glass green marks commitment, and warm amber is
reserved for a deliberate break.
"""

STYLESHEET = r"""
QWidget {
    background: transparent;
    color: #F5F7FA;
    font-size: 14px;
}

QMainWindow, QDialog, QWidget#appWindow {
    background-color: #0B121D;
}

QLabel { color: #F5F7FA; }
QLabel#brandTitle { font-size: 20px; font-weight: 700; }
QLabel#brandSubtitle, QLabel#subtitle { color: #93A1AF; font-size: 12px; }
QLabel#eyebrow {
    color: #67CFBB;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1px;
}
QLabel#pageTitle { color: #F5F7FA; font-size: 26px; font-weight: 700; }
QLabel#sectionTitle { color: #F5F7FA; font-size: 15px; font-weight: 650; }
QLabel#bodyMuted, QLabel#hint { color: #93A1AF; font-size: 12px; }
QLabel#tinyMuted { color: #718097; font-size: 11px; }
QLabel#summaryGoal { color: #F5F7FA; font-size: 17px; font-weight: 600; }
QLabel#summaryValue { color: #F5F7FA; font-size: 13px; font-weight: 600; }
QLabel#summaryKey { color: #7F8DA3; font-size: 12px; }
QLabel#statValue { color: #F5F7FA; font-size: 25px; font-weight: 700; }
QLabel#statCaption { color: #8492A8; font-size: 11px; }
QLabel#statusBadge {
    background-color: #17342F;
    color: #86DECE;
    border: 1px solid #275148;
    border-radius: 12px;
    padding: 4px 10px;
    font-size: 11px;
    font-weight: 700;
}
QLabel#breakBadge {
    background-color: #382C1D;
    color: #F0C98F;
    border: 1px solid #5A4529;
    border-radius: 12px;
    padding: 4px 10px;
    font-size: 11px;
    font-weight: 700;
}

QFrame#panel {
    background-color: #111C2B;
    border: 1px solid #213149;
    border-radius: 18px;
}
QFrame#sectionCard, QFrame#statCard {
    background-color: #131F30;
    border: 1px solid #22334D;
    border-radius: 14px;
}
QFrame#softPanel {
    background-color: #0E1826;
    border: 1px solid #1E2D43;
    border-radius: 12px;
}
QFrame#breakPanel {
    background-color: #2B2318;
    border: 1px solid #594329;
    border-radius: 12px;
}
QFrame#divider { background-color: #203047; max-height: 1px; }

QPushButton, QToolButton {
    min-height: 38px;
    padding: 0 16px;
    color: #DFE6EF;
    background-color: #17253A;
    border: 1px solid #2B3C57;
    border-radius: 10px;
    font-weight: 600;
}
QPushButton:hover, QToolButton:hover {
    color: #FFFFFF;
    background-color: #1D2D45;
    border-color: #405575;
}
QPushButton:pressed, QToolButton:pressed { background-color: #22344E; }
QPushButton:focus, QToolButton:focus, QLineEdit:focus, QSpinBox:focus {
    border: 2px solid #67CFBB;
}
QPushButton:disabled, QToolButton:disabled {
    color: #5F6D80;
    background-color: #111A28;
    border-color: #1E2A3C;
}
QPushButton#primaryButton {
    min-height: 48px;
    color: #071510;
    background-color: #67CFBB;
    border: 1px solid #67CFBB;
    border-radius: 12px;
    font-size: 15px;
    font-weight: 750;
}
QPushButton#primaryButton:hover { background-color: #7ADCCA; border-color: #7ADCCA; }
QPushButton#primaryButton:pressed { background-color: #58BAA8; }
QPushButton#primaryButton:disabled {
    color: #6F7B87;
    background-color: #1A2635;
    border-color: #28364A;
}
QPushButton#ghostButton, QToolButton#ghostButton {
    color: #AAB5C5;
    background-color: transparent;
    border-color: transparent;
}
QPushButton#ghostButton:hover, QToolButton#ghostButton:hover {
    color: #FFFFFF;
    background-color: #162235;
    border-color: #263750;
}
QPushButton#dangerButton {
    color: #F2A2A2;
    background-color: transparent;
    border-color: #5B343B;
}
QPushButton#dangerButton:hover { background-color: #2E1B22; border-color: #8B4C56; }
QPushButton#presetButton, QToolButton#appChip, QToolButton#intensityCard {
    min-height: 38px;
    background-color: #111B2A;
    border: 1px solid #2A3A54;
    color: #AEB9C8;
}
QPushButton#presetButton:checked, QToolButton#appChip:checked, QToolButton#intensityCard:checked {
    color: #EFFFFB;
    background-color: #17342F;
    border: 2px solid #67CFBB;
}
QToolButton#appChip { padding: 0 12px; }
QToolButton#intensityCard {
    min-height: 68px;
    padding: 10px 14px;
    text-align: left;
}

QLineEdit, QSpinBox {
    min-height: 40px;
    padding: 0 12px;
    color: #F5F7FA;
    background-color: #0E1826;
    border: 1px solid #2A3A54;
    border-radius: 10px;
    selection-background-color: #35786D;
}
QLineEdit::placeholder { color: #65748A; }
QSpinBox { padding-right: 24px; }
QSpinBox::up-button, QSpinBox::down-button {
    background: transparent;
    border: none;
    width: 20px;
}

QScrollArea { background: transparent; border: none; }
QScrollArea > QWidget > QWidget { background: transparent; }
QScrollBar:vertical { background: transparent; width: 8px; margin: 4px 0; }
QScrollBar::handle:vertical { background: #33445F; border-radius: 4px; min-height: 32px; }
QScrollBar::handle:vertical:hover { background: #465B7A; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

QProgressBar {
    min-height: 6px;
    max-height: 6px;
    background-color: #223149;
    border: none;
    border-radius: 3px;
}
QProgressBar::chunk { background-color: #67CFBB; border-radius: 3px; }

QTableWidget {
    background-color: #0F1927;
    alternate-background-color: #121E2E;
    border: 1px solid #22334D;
    border-radius: 12px;
    gridline-color: transparent;
    selection-background-color: #1D3B3A;
    selection-color: #FFFFFF;
    outline: none;
}
QTableWidget::item { padding: 8px 10px; border-bottom: 1px solid #1B2A40; }
QHeaderView::section {
    color: #8F9DB1;
    background-color: #142136;
    border: none;
    border-bottom: 1px solid #2B3B56;
    padding: 10px;
    font-size: 11px;
    font-weight: 700;
}

QMenu {
    color: #F5F7FA;
    background-color: #111C2B;
    border: 1px solid #2B3C57;
    border-radius: 8px;
    padding: 6px;
}
QMenu::item { padding: 8px 20px; border-radius: 6px; }
QMenu::item:selected { background-color: #1E3049; }

QMessageBox { background-color: #111C2B; }
QMessageBox QLabel { color: #F5F7FA; min-width: 280px; }
QToolTip {
    color: #F5F7FA;
    background-color: #1B2A40;
    border: 1px solid #3A4C68;
    padding: 6px;
}
"""
