"""
Pricing Master Suite – Dark Enterprise QSS Theme
Natura accent: #FF6B35 (orange)
Avon  accent:  #7B2FBE (purple)
"""

DARK_STYLESHEET = """
/* ============================================================
   GLOBAL
   ============================================================ */

QWidget {
    background-color: #1a1a1a;
    color: #e0e0e0;
    font-family: "Helvetica Neue", Arial;
    font-size: 13px;
    outline: none;
}

QMainWindow {
    background-color: #141414;
}

/* ============================================================
   SIDEBAR
   ============================================================ */
#sidebar {
    background-color: #111111;
    border-right: 1px solid #232323;
}

#logo_label {
    color: #ffffff;
    font-size: 15px;
    font-weight: 700;
}

#version_label {
    color: #555555;
    font-size: 11px;
}

#label_section {
    color: #454545;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1.2px;
}

/* Navigation buttons */
#nav_button {
    background-color: transparent;
    color: #888888;
    border: none;
    border-left: 3px solid transparent;
    border-radius: 0px;
    padding: 10px 16px 10px 13px;
    text-align: left;
    font-size: 13px;
    font-weight: 400;
}

#nav_button:hover {
    background-color: #1d1d1d;
    color: #cccccc;
    border-left-color: #333333;
}

#nav_button:checked {
    background-color: #1e1e2e;
    color: #ffffff;
    font-weight: 600;
    border-left: 3px solid #FF6B35;
}

/* ============================================================
   CONTENT AREA
   ============================================================ */
#content_area {
    background-color: #1a1a1a;
}

/* ============================================================
   PAGE HEADER
   ============================================================ */
#page_header {
    background-color: #1a1a1a;
    border-bottom: 1px solid #242424;
}

#page_title {
    font-size: 20px;
    font-weight: 700;
    color: #f0f0f0;
}

#page_subtitle {
    font-size: 12px;
    color: #555555;
}

/* ============================================================
   CARDS / PANELS
   ============================================================ */
#card {
    background-color: #202020;
    border: 1px solid #2a2a2a;
    border-radius: 10px;
}

#card_flat {
    background-color: #1d1d1d;
    border: 1px solid #262626;
    border-radius: 8px;
}

#error_card {
    background-color: #1e1e1e;
    border: 1px solid #2a2a2a;
    border-radius: 10px;
}

#error_card:hover {
    border-color: #3a3a3a;
    background-color: #222222;
}

#error_card[selected="true"] {
    border-color: #FF6B35;
    background-color: #211510;
}

/* ============================================================
   DROP ZONE
   ============================================================ */
#dropzone {
    background-color: #181828;
    border: 2px dashed #2a2a44;
    border-radius: 10px;
    color: #555577;
    font-size: 12px;
}

#dropzone:hover {
    border-color: #44446a;
    background-color: #1c1c30;
    color: #8888aa;
}

#dropzone[state="filled"] {
    border: 2px solid #2d5a2d;
    background-color: #0e1e0e;
    color: #6abf6a;
}

#dropzone[state="error"] {
    border: 2px solid #5a1a1a;
    background-color: #1e0e0e;
    color: #e06060;
}

/* ============================================================
   BUTTONS
   ============================================================ */
QPushButton {
    background-color: #252525;
    color: #cccccc;
    border: 1px solid #333333;
    border-radius: 7px;
    padding: 7px 16px;
    font-size: 13px;
    font-weight: 500;
    min-height: 32px;
}

QPushButton:hover {
    background-color: #2e2e2e;
    border-color: #484848;
    color: #eeeeee;
}

QPushButton:pressed {
    background-color: #1a1a1a;
}

QPushButton:disabled {
    background-color: #1a1a1a;
    color: #3a3a3a;
    border-color: #222222;
}

#btn_primary {
    background-color: #d4521a;
    color: #ffffff;
    border: none;
    font-weight: 700;
    font-size: 14px;
    min-height: 38px;
    border-radius: 8px;
}

#btn_primary:hover {
    background-color: #e05e22;
}

#btn_primary:pressed {
    background-color: #b84515;
}

#btn_primary:disabled {
    background-color: #3a2010;
    color: #664422;
    border: none;
}

#btn_avon {
    background-color: #6a28a8;
    color: #ffffff;
    border: none;
    font-weight: 700;
    min-height: 38px;
    border-radius: 8px;
}

#btn_avon:hover {
    background-color: #7b33bb;
}

#btn_secondary {
    background-color: #1e2a1e;
    color: #6abf6a;
    border: 1px solid #2a4a2a;
    border-radius: 7px;
}

#btn_secondary:hover {
    background-color: #243024;
    border-color: #3a6a3a;
}

#btn_ghost {
    background-color: transparent;
    color: #666666;
    border: 1px solid #2a2a2a;
}

#btn_ghost:hover {
    background-color: #222222;
    color: #999999;
}

#btn_danger {
    background-color: #2a1010;
    color: #ef9a9a;
    border: 1px solid #5a2020;
}

#btn_danger:hover {
    background-color: #381515;
}

/* ============================================================
   PROGRESS BAR
   ============================================================ */
QProgressBar {
    background-color: #181818;
    border: 1px solid #252525;
    border-radius: 4px;
    height: 6px;
    text-align: center;
    color: transparent;
}

QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #c04010, stop:1 #FF6B35);
    border-radius: 4px;
}

#progress_avon::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #5a1f90, stop:1 #9B4FDE);
}

/* ============================================================
   TABLE
   ============================================================ */
QTableWidget {
    background-color: #181818;
    alternate-background-color: #1c1c1c;
    border: 1px solid #252525;
    border-radius: 8px;
    gridline-color: #222222;
    selection-background-color: #2a2a3e;
    selection-color: #ffffff;
    show-decoration-selected: 1;
}

QTableWidget::item {
    padding: 6px 12px;
    border: none;
    color: #cccccc;
}

QTableWidget::item:selected {
    background-color: #252538;
    color: #ffffff;
}

QTableWidget::item:hover {
    background-color: #202030;
}

QHeaderView {
    background-color: #141414;
}

QHeaderView::section {
    background-color: #141414;
    color: #666666;
    font-size: 11px;
    font-weight: 700;
    padding: 9px 12px;
    border: none;
    border-bottom: 1px solid #252525;
    border-right: 1px solid #1e1e1e;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

QHeaderView::section:last {
    border-right: none;
}

QTableCornerButton::section {
    background-color: #141414;
    border: none;
    border-bottom: 1px solid #252525;
}

/* ============================================================
   INPUT FIELDS
   ============================================================ */
QLineEdit {
    background-color: #161616;
    color: #e0e0e0;
    border: 1px solid #2a2a2a;
    border-radius: 7px;
    padding: 7px 12px;
    selection-background-color: #333355;
    min-height: 32px;
}

QLineEdit:focus {
    border-color: #FF6B35;
}

QLineEdit:disabled {
    color: #444444;
    background-color: #141414;
}

QTextEdit, QPlainTextEdit {
    background-color: #161616;
    color: #d0d0d0;
    border: 1px solid #2a2a2a;
    border-radius: 8px;
    padding: 8px 12px;
    selection-background-color: #333355;
}

QTextEdit:focus, QPlainTextEdit:focus {
    border-color: #FF6B35;
}

/* ============================================================
   COMBO BOX
   ============================================================ */
QComboBox {
    background-color: #161616;
    color: #e0e0e0;
    border: 1px solid #2a2a2a;
    border-radius: 7px;
    padding: 7px 12px;
    min-height: 32px;
    min-width: 120px;
}

QComboBox:hover {
    border-color: #3a3a3a;
}

QComboBox:focus {
    border-color: #FF6B35;
}

QComboBox::drop-down {
    border: none;
    width: 28px;
    padding-right: 8px;
}

QComboBox::down-arrow {
    width: 10px;
    height: 10px;
}

QComboBox QAbstractItemView {
    background-color: #1e1e1e;
    border: 1px solid #333333;
    border-radius: 6px;
    selection-background-color: #2a2a3e;
    selection-color: #ffffff;
    outline: none;
    padding: 4px;
}

QComboBox QAbstractItemView::item {
    padding: 6px 10px;
    border-radius: 4px;
    min-height: 28px;
}

/* ============================================================
   SCROLL BARS
   ============================================================ */
QScrollBar:vertical {
    background-color: transparent;
    width: 8px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background-color: #2e2e2e;
    border-radius: 4px;
    min-height: 24px;
}

QScrollBar::handle:vertical:hover {
    background-color: #3e3e3e;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0;
    background: none;
}

QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {
    background: none;
}

QScrollBar:horizontal {
    background-color: transparent;
    height: 8px;
    margin: 0;
}

QScrollBar::handle:horizontal {
    background-color: #2e2e2e;
    border-radius: 4px;
    min-width: 24px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #3e3e3e;
}

QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {
    width: 0;
    background: none;
}

/* ============================================================
   SCROLL AREA
   ============================================================ */
QScrollArea {
    border: none;
    background-color: transparent;
}

QScrollArea > QWidget > QWidget {
    background-color: transparent;
}

/* ============================================================
   TAB WIDGET
   ============================================================ */
QTabWidget::pane {
    border: 1px solid #252525;
    border-radius: 8px;
    background-color: #1a1a1a;
    top: -1px;
}

QTabBar::tab {
    background-color: transparent;
    color: #555555;
    padding: 8px 18px;
    border: none;
    border-bottom: 2px solid transparent;
    font-size: 12px;
    font-weight: 500;
}

QTabBar::tab:selected {
    color: #FF6B35;
    border-bottom: 2px solid #FF6B35;
}

QTabBar::tab:hover:!selected {
    color: #999999;
}

/* ============================================================
   GROUP BOX
   ============================================================ */
QGroupBox {
    border: 1px solid #252525;
    border-radius: 8px;
    margin-top: 18px;
    padding: 12px 8px 8px 8px;
    font-size: 11px;
    color: #555555;
    font-weight: 600;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 6px;
    color: #555555;
    text-transform: uppercase;
    letter-spacing: 0.8px;
}

/* ============================================================
   CHECKBOXES & RADIO BUTTONS
   ============================================================ */
QCheckBox {
    color: #999999;
    spacing: 8px;
    font-size: 12px;
}

QCheckBox::indicator {
    width: 15px;
    height: 15px;
    border: 1px solid #3a3a3a;
    border-radius: 4px;
    background-color: #1a1a1a;
}

QCheckBox::indicator:checked {
    background-color: #FF6B35;
    border-color: #FF6B35;
}

QCheckBox::indicator:hover {
    border-color: #555555;
}

QRadioButton {
    color: #999999;
    spacing: 8px;
    font-size: 12px;
}

QRadioButton::indicator {
    width: 15px;
    height: 15px;
    border: 1px solid #3a3a3a;
    border-radius: 8px;
    background-color: #1a1a1a;
}

QRadioButton::indicator:checked {
    background-color: #FF6B35;
    border-color: #FF6B35;
}

/* ============================================================
   LABELS
   ============================================================ */
QLabel {
    color: #cccccc;
    background: transparent;
}

#label_muted {
    color: #555555;
    font-size: 11px;
}

#label_hint {
    color: #444466;
    font-size: 11px;
    font-style: italic;
}

#label_stat_value {
    font-size: 30px;
    font-weight: 700;
    color: #f0f0f0;
}

#label_stat_label {
    font-size: 10px;
    color: #555555;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.8px;
}

#label_natura {
    color: #FF8050;
    font-size: 11px;
    font-weight: 600;
}

#label_avon {
    color: #aa77ee;
    font-size: 11px;
    font-weight: 600;
}

/* ============================================================
   STATUS BAR
   ============================================================ */
QStatusBar {
    background-color: #0e0e0e;
    border-top: 1px solid #1e1e1e;
    color: #555555;
    font-size: 11px;
    padding: 2px 12px;
}

/* ============================================================
   MESSAGE BOX / DIALOGS
   ============================================================ */
QMessageBox {
    background-color: #1e1e1e;
}

QMessageBox QLabel {
    color: #dddddd;
    min-width: 320px;
}

QMessageBox QPushButton {
    min-width: 80px;
}

/* ============================================================
   TOOLTIP
   ============================================================ */
QToolTip {
    background-color: #252525;
    color: #dddddd;
    border: 1px solid #3a3a3a;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
    opacity: 230;
}

/* ============================================================
   SPLITTER
   ============================================================ */
QSplitter::handle {
    background-color: #252525;
}

QSplitter::handle:horizontal {
    width: 1px;
}

QSplitter::handle:vertical {
    height: 1px;
}

/* ============================================================
   FRAMES / DIVIDERS
   ============================================================ */
#divider {
    background-color: #252525;
    max-height: 1px;
    min-height: 1px;
    border: none;
}

#divider_v {
    background-color: #252525;
    max-width: 1px;
    min-width: 1px;
    border: none;
}

/* ============================================================
   BADGES
   ============================================================ */
#badge_error {
    background-color: #3a1010;
    color: #ef9a9a;
    border: 1px solid #602020;
    border-radius: 10px;
    padding: 1px 8px;
    font-size: 10px;
    font-weight: 700;
}

#badge_warning {
    background-color: #2e2008;
    color: #ffcc80;
    border: 1px solid #4a3808;
    border-radius: 10px;
    padding: 1px 8px;
    font-size: 10px;
    font-weight: 700;
}

#badge_ok {
    background-color: #0a2010;
    color: #88cc88;
    border: 1px solid #1a4020;
    border-radius: 10px;
    padding: 1px 8px;
    font-size: 10px;
    font-weight: 700;
}

#badge_natura {
    background-color: #2a1508;
    color: #ff9060;
    border-radius: 4px;
    padding: 1px 7px;
    font-size: 10px;
    font-weight: 700;
}

#badge_avon {
    background-color: #180828;
    color: #cc88ff;
    border-radius: 4px;
    padding: 1px 7px;
    font-size: 10px;
    font-weight: 700;
}

/* ============================================================
   AI DIAGNOSTIC PANEL
   ============================================================ */
#ai_panel {
    background-color: #0e1118;
    border: 1px solid #1e2535;
    border-radius: 10px;
}

#ai_text {
    background-color: transparent;
    color: #c0cce0;
    font-family: "JetBrains Mono", "Fira Code", "Cascadia Code", "Courier New", monospace;
    font-size: 12px;
    border: none;
    padding: 0;
    line-height: 1.6;
}

/* ============================================================
   DASHBOARD / EXECUTIVE NEXUS
   ============================================================ */
#kpi_card {
    background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, stop:0 #222222, stop:1 #1a1a1a);
    border: 1px solid #2d2d2d;
    border-radius: 16px;
}

#nexus_card {
    background-color: #1a1a1a;
    border: 1px solid #282828;
    border-radius: 14px;
}

#nexus_card:hover {
    background-color: #222222;
    border-color: #444444;
}

#nexus_greeting {
    color: #ffffff;
}
"""
