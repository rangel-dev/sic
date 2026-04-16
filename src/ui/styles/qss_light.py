"""
Pricing Master Suite – Light Enterprise QSS Theme
Natura accent: #FF6B35 (orange)
Avon  accent:  #7B2FBE (purple)
"""

LIGHT_STYLESHEET = """
/* ============================================================
   GLOBAL
   ============================================================ */

QWidget {
    background-color: #f8f9fa;
    color: #333333;
    font-family: "Helvetica Neue", Arial;
    font-size: 13px;
    outline: none;
}

QMainWindow {
    background-color: #ffffff;
}

/* ============================================================
   SIDEBAR
   ============================================================ */
#sidebar {
    background-color: #ffffff;
    border-right: 1px solid #e0e0e0;
}

#logo_label {
    color: #222222;
    font-size: 15px;
    font-weight: 700;
}

#version_label {
    color: #999999;
    font-size: 11px;
}

#label_section {
    color: #bbbbbb;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1.2px;
}

/* Navigation buttons */
#nav_button {
    background-color: transparent;
    color: #666666;
    border: none;
    border-left: 3px solid transparent;
    border-radius: 0px;
    padding: 10px 16px 10px 13px;
    text-align: left;
    font-size: 13px;
    font-weight: 400;
}

#nav_button:hover {
    background-color: #f0f0f0;
    color: #333333;
    border-left-color: #dddddd;
}

#nav_button:checked {
    background-color: #fff4f0;
    color: #FF6B35;
    font-weight: 600;
    border-left: 3px solid #FF6B35;
}

/* ============================================================
   CONTENT AREA
   ============================================================ */
#content_area {
    background-color: #f8f9fa;
}

/* ============================================================
   PAGE HEADER
   ============================================================ */
#page_header {
    background-color: #ffffff;
    border-bottom: 1px solid #e0e0e0;
}

#page_title {
    font-size: 20px;
    font-weight: 700;
    color: #222222;
}

#page_subtitle {
    font-size: 12px;
    color: #888888;
}

/* ============================================================
   CARDS / PANELS
   ============================================================ */
#card {
    background-color: #ffffff;
    border: 1px solid #e0e0e0;
    border-radius: 10px;
}

#card_flat {
    background-color: #ffffff;
    border: 1px solid #ebebeb;
    border-radius: 8px;
}

#error_card {
    background-color: #ffffff;
    border: 1px solid #e0e0e0;
    border-radius: 10px;
}

#error_card:hover {
    border-color: #cccccc;
    background-color: #fafafa;
}

#error_card[selected="true"] {
    border-color: #FF6B35;
    background-color: #fff8f5;
}

/* ============================================================
   DROP ZONE
   ============================================================ */
#dropzone {
    background-color: #f0f2f8;
    border: 2px dashed #ccd0df;
    border-radius: 10px;
    color: #777799;
    font-size: 12px;
}

#dropzone:hover {
    border-color: #aaaacc;
    background-color: #e8eaf2;
    color: #666688;
}

#dropzone[state="filled"] {
    border: 2px solid #6abf6a;
    background-color: #f0fdf0;
    color: #2d5a2d;
}

#dropzone[state="error"] {
    border: 2px solid #e06060;
    background-color: #fef0f0;
    color: #5a1a1a;
}

#dropzone[brand="natura"] {
    border: 2px solid #FF8050;
    background-color: #fff4f0;
    color: #FF6B35;
}

#dropzone[brand="avon"] {
    border: 2px solid #7B2FBE;
    background-color: #f8f0ff;
    color: #7B2FBE;
}

#dropzone[brand="ml"] {
    border: 2px solid #2196F3;
    background-color: #f0f7ff;
    color: #1976D2;
}

/* ============================================================
   BUTTONS
   ============================================================ */
QPushButton {
    background-color: #ffffff;
    color: #555555;
    border: 1px solid #d0d0d0;
    border-radius: 7px;
    padding: 7px 16px;
    font-size: 13px;
    font-weight: 500;
    min-height: 32px;
}

QPushButton:hover {
    background-color: #f5f5f5;
    border-color: #bbbbbb;
    color: #222222;
}

QPushButton:pressed {
    background-color: #eeeeee;
}

QPushButton:disabled {
    background-color: #f5f5f5;
    color: #cccccc;
    border-color: #dddddd;
}

#btn_primary {
    background-color: #FF6B35;
    color: #ffffff;
    border: none;
    font-weight: 700;
    font-size: 14px;
    min-height: 38px;
    border-radius: 8px;
}

#btn_primary:hover {
    background-color: #ff7b4d;
}

#btn_primary:pressed {
    background-color: #e65a2a;
}

#btn_primary:disabled {
    background-color: #ffd8c9;
    color: #ffffff;
    border: none;
}

#btn_avon {
    background-color: #7B2FBE;
    color: #ffffff;
    border: none;
    font-weight: 700;
    min-height: 38px;
    border-radius: 8px;
}

#btn_avon:hover {
    background-color: #8c3fce;
}

#btn_secondary {
    background-color: #f0fdf0;
    color: #2d5a2d;
    border: 1px solid #c9dfc9;
    border-radius: 7px;
}

#btn_secondary:hover {
    background-color: #e6f7e6;
    border-color: #b0d0b0;
}

#btn_ghost {
    background-color: transparent;
    color: #999999;
    border: 1px solid #e0e0e0;
}

#btn_ghost:hover {
    background-color: #f8f8f8;
    color: #666666;
    border-color: #d0d0d0;
}

#btn_danger {
    background-color: #fff0f0;
    color: #d32f2f;
    border: 1px solid #ffcdd2;
}

#btn_danger:hover {
    background-color: #ffe8e8;
}

/* ============================================================
   PROGRESS BAR
   ============================================================ */
QProgressBar {
    background-color: #e0e0e0;
    border: none;
    border-radius: 4px;
    height: 6px;
    text-align: center;
    color: transparent;
}

QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #FF8C60, stop:1 #FF6B35);
    border-radius: 4px;
}

/* ============================================================
   TABLE
   ============================================================ */
QTableWidget {
    background-color: #ffffff;
    alternate-background-color: #fafafa;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    gridline-color: #f0f0f0;
    selection-background-color: #fff4f0;
    selection-color: #FF6B35;
    show-decoration-selected: 1;
}

QTableWidget::item {
    padding: 6px 12px;
    border: none;
    color: #444444;
}

QTableWidget::item:selected {
    background-color: #fff4f0;
    color: #FF6B35;
    font-weight: 600;
}

QTableWidget::item:hover {
    background-color: #fffcfb;
}

QHeaderView {
    background-color: #f5f5f5;
}

QHeaderView::section {
    background-color: #f5f5f5;
    color: #888888;
    font-size: 11px;
    font-weight: 700;
    padding: 9px 12px;
    border: none;
    border-bottom: 1px solid #e0e0e0;
    border-right: 1px solid #eeeeee;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

QHeaderView::section:last {
    border-right: none;
}

QTableCornerButton::section {
    background-color: #f5f5f5;
    border: none;
    border-bottom: 1px solid #e0e0e0;
}

/* ============================================================
   INPUT FIELDS
   ============================================================ */
QLineEdit {
    background-color: #ffffff;
    color: #333333;
    border: 1px solid #d0d0d0;
    border-radius: 7px;
    padding: 7px 12px;
    selection-background-color: #ffecd9;
    min-height: 32px;
}

QLineEdit:focus {
    border-color: #FF6B35;
}

QLineEdit:disabled {
    color: #999999;
    background-color: #f5f5f5;
}

QTextEdit, QPlainTextEdit {
    background-color: #ffffff;
    color: #333333;
    border: 1px solid #d0d0d0;
    border-radius: 8px;
    padding: 8px 12px;
    selection-background-color: #ffecd9;
}

QTextEdit:focus, QPlainTextEdit:focus {
    border-color: #FF6B35;
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
    background-color: #d0d0d0;
    border-radius: 4px;
    min-height: 24px;
}

QScrollBar::handle:vertical:hover {
    background-color: #bbbbbb;
}

QScrollBar:horizontal {
    background-color: transparent;
    height: 8px;
    margin: 0;
}

QScrollBar::handle:horizontal {
    background-color: #d0d0d0;
    border-radius: 4px;
    min-width: 24px;
}

/* ============================================================
   TAB WIDGET
   ============================================================ */
QTabWidget::pane {
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    background-color: #ffffff;
    top: -1px;
}

QTabBar::tab {
    background-color: transparent;
    color: #999999;
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

/* ============================================================
   LABELS
   ============================================================ */
QLabel {
    color: #333333;
    background: transparent;
}

#label_muted {
    color: #888888;
    font-size: 11px;
}

#label_stat_value {
    font-size: 30px;
    font-weight: 700;
    color: #222222;
}

#label_stat_label {
    font-size: 10px;
    color: #999999;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.8px;
}

/* ============================================================
   STATUS BAR
   ============================================================ */
QStatusBar {
    background-color: #ffffff;
    border-top: 1px solid #e0e0e0;
    color: #888888;
    font-size: 11px;
    padding: 2px 12px;
}

/* ============================================================
   AI DIAGNOSTIC PANEL
   ============================================================ */
#ai_panel {
    background-color: #fcfdfe;
    border: 1px solid #e4e9f2;
    border-radius: 10px;
}

/* ============================================================
   DASHBOARD / EXECUTIVE NEXUS
   ============================================================ */
#kpi_card {
    background-color: #ffffff;
    border: 1px solid #e8e8e8;
    border-radius: 16px;
}

#nexus_card {
    background-color: #ffffff;
    border: 1px solid #e5e5e5;
    border-radius: 14px;
}

#nexus_card:hover {
    background-color: #fcfcfc;
    border-color: #d8d8d8;
}

#nexus_greeting {
    color: #222222;
}
"""
