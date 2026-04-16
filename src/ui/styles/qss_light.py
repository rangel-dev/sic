"""
Pricing Master Suite – Light Enterprise QSS Theme (Minimal & Clean Design)
Primary accent: #3b82f6 (professional blue)
Natura brand: #f59e0b (muted orange)
Avon brand:  #a78bfa (muted purple)
"""

LIGHT_STYLESHEET = """
/* ============================================================
   GLOBAL
   ============================================================ */

QWidget {
    background-color: #f8f9fa;
    color: #1a1a1a;
    font-family: "Helvetica Neue", Arial;
    font-size: 13px;
    outline: none;
}

QMainWindow {
    background-color: #ffffff;
}

/* ============================================================
   TOP NAVIGATION BAR
   ============================================================ */
#top_nav_bar {
    background-color: #ffffff;
    border-bottom: 1px solid #e5e7eb;
}

#logo_container {
    border-right: 1px solid #e5e7eb;
}

#settings_container {
    border-left: 1px solid #e5e7eb;
}

#tabs_container {
    background-color: #ffffff;
}

#logo_label {
    color: #1a1a1a;
    font-size: 14px;
    font-weight: 700;
}

/* Navigation buttons (top tabs) */
#tab_button {
    background-color: transparent;
    color: #404040;
    border: none;
    border-bottom: 2px solid transparent;
    border-radius: 0px;
    padding: 8px 16px;
    text-align: center;
    font-size: 13px;
    font-weight: 400;
}

#tab_button:hover {
    background-color: #f5f5f5;
    color: #1a1a1a;
    border-bottom-color: #d0d0d0;
}

#tab_button:checked {
    background-color: transparent;
    color: #3b82f6;
    font-weight: 600;
    border-bottom: 2px solid #3b82f6;
}

/* Theme toggle button */
#theme_toggle_btn {
    background-color: transparent;
    color: #404040;
    border: none;
    border-radius: 6px;
    font-size: 18px;
}

#theme_toggle_btn:hover {
    background-color: #f5f5f5;
}

#theme_toggle_btn:pressed {
    background-color: #efefef;
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
    border-bottom: 1px solid #e5e7eb;
}

#page_title {
    font-size: 32px;
    font-weight: 600;
    color: #1a1a1a;
}

#page_subtitle {
    font-size: 14px;
    color: #404040;
}

/* ============================================================
   CARDS / PANELS
   ============================================================ */
#card {
    background-color: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    padding: 2px;
}

#card:hover {
    border-color: #d0d0d0;
}

#card_flat {
    background-color: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
}

#card_flat:hover {
    border-color: #d0d0d0;
}

#error_card {
    background-color: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
}

#error_card:hover {
    border-color: #d0d0d0;
    background-color: #f5f5f5;
}

#error_card[selected="true"] {
    border-color: #3b82f6;
    background-color: #eff6ff;
}

/* ============================================================
   DROP ZONE
   ============================================================ */
#dropzone {
    background-color: #fafafa;
    border: 2px dashed #d0d0d0;
    border-radius: 8px;
    color: #808080;
    font-size: 12px;
}

#dropzone:hover {
    border-color: #b0b0b0;
    background-color: #f5f5f5;
    color: #404040;
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
    border: 2px solid #f59e0b;
    background-color: #fefce8;
    color: #f59e0b;
}

#dropzone[brand="avon"] {
    border: 2px solid #a78bfa;
    background-color: #f3e8ff;
    color: #a78bfa;
}

#dropzone[brand="ml"] {
    border: 2px solid #2196F3;
    background-color: #f0f7ff;
    color: #1976D2;
}

#dropzone[brand="all"] {
    border: 2px solid #00c853;
    background-color: #e8f5e9;
    color: #1b5e20;
}

#dropzone[brand*="_"] {
    border: 2px solid #9e9e9e;
    background-color: #f5f5f5;
    color: #616161;
}

/* ============================================================
   BUTTONS
   ============================================================ */
QPushButton {
    background-color: #ffffff;
    color: #404040;
    border: 1px solid #d0d0d0;
    border-radius: 6px;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: 500;
    min-height: 32px;
    outline: none;
}

QPushButton:hover {
    background-color: #f5f5f5;
    border-color: #a0a0a0;
    color: #1a1a1a;
}

QPushButton:pressed {
    background-color: #ebebeb;
    border-color: #808080;
}

QPushButton:focus {
    border-color: #3b82f6;
}

QPushButton:disabled {
    background-color: #f5f5f5;
    color: #b0b0b0;
    border-color: #d0d0d0;
}

#btn_primary {
    background-color: #3b82f6;
    color: #ffffff;
    border: none;
    font-weight: 600;
    font-size: 13px;
    min-height: 38px;
    border-radius: 6px;
    outline: none;
}

#btn_primary:hover {
    background-color: #2563eb;
}

#btn_primary:pressed {
    background-color: #1e40af;
}

#btn_primary:focus {
    border: 2px solid #93c5fd;
    background-color: #3b82f6;
}

#btn_primary:disabled {
    background-color: #bfdbfe;
    color: #ffffff;
    border: none;
}

#btn_avon {
    background-color: #a78bfa;
    color: #ffffff;
    border: none;
    font-weight: 600;
    min-height: 38px;
    border-radius: 6px;
}

#btn_avon:hover {
    background-color: #9370f7;
}

#btn_secondary {
    background-color: #f5f5f5;
    color: #404040;
    border: 1px solid #d0d0d0;
    border-radius: 6px;
}

#btn_secondary:hover {
    background-color: #ebebeb;
    border-color: #a0a0a0;
}

#btn_secondary:focus {
    border-color: #3b82f6;
}

#btn_ghost {
    background-color: transparent;
    color: #808080;
    border: 1px solid #d0d0d0;
    border-radius: 6px;
}

#btn_ghost:hover {
    background-color: #f5f5f5;
    color: #404040;
    border-color: #a0a0a0;
}

#btn_ghost:focus {
    border-color: #3b82f6;
}

#btn_danger {
    background-color: #fef2f2;
    color: #d32f2f;
    border: 1px solid #fecaca;
    border-radius: 6px;
}

#btn_danger:hover {
    background-color: #fee2e2;
}

/* ============================================================
   PROGRESS BAR
   ============================================================ */
QProgressBar {
    background-color: #e5e7eb;
    border: none;
    border-radius: 6px;
    height: 6px;
    text-align: center;
    color: transparent;
}

QProgressBar::chunk {
    background: #3b82f6;
    border-radius: 6px;
}

/* ============================================================
   TABLE
   ============================================================ */
QTableWidget {
    background-color: #ffffff;
    alternate-background-color: #f5f5f5;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    gridline-color: #f0f0f0;
    selection-background-color: #eff6ff;
    selection-color: #3b82f6;
    show-decoration-selected: 1;
}

QTableWidget::item {
    padding: 8px 12px;
    border: none;
    color: #1a1a1a;
}

QTableWidget::item:selected {
    background-color: #eff6ff;
    color: #3b82f6;
    font-weight: 600;
}

QTableWidget::item:hover {
    background-color: #f5f5f5;
}

QHeaderView {
    background-color: #f5f5f5;
}

QHeaderView::section {
    background-color: #f5f5f5;
    color: #404040;
    font-size: 11px;
    font-weight: 600;
    padding: 9px 12px;
    border: none;
    border-bottom: 1px solid #e5e7eb;
    border-right: 1px solid #efefef;
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
    color: #1a1a1a;
    border: 1px solid #d0d0d0;
    border-radius: 6px;
    padding: 10px 12px;
    selection-background-color: #dbeafe;
    min-height: 32px;
    outline: none;
}

QLineEdit:focus {
    border: 2px solid #3b82f6;
    padding: 9px 11px;
}

QLineEdit:disabled {
    color: #b0b0b0;
    background-color: #f5f5f5;
    border-color: #d0d0d0;
}

QTextEdit, QPlainTextEdit {
    background-color: #ffffff;
    color: #1a1a1a;
    border: 1px solid #d0d0d0;
    border-radius: 6px;
    padding: 10px 12px;
    selection-background-color: #dbeafe;
    outline: none;
}

QTextEdit:focus, QPlainTextEdit:focus {
    border: 2px solid #3b82f6;
    padding: 9px 11px;
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
    background-color: #b0b0b0;
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

QScrollBar::handle:horizontal:hover {
    background-color: #b0b0b0;
}

/* ============================================================
   TAB WIDGET
   ============================================================ */
QTabWidget::pane {
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    background-color: #ffffff;
    top: -1px;
}

QTabBar::tab {
    background-color: transparent;
    color: #808080;
    padding: 8px 18px;
    border: none;
    border-bottom: 2px solid transparent;
    font-size: 13px;
    font-weight: 500;
}

QTabBar::tab:selected {
    color: #3b82f6;
    border-bottom: 2px solid #3b82f6;
}

/* ============================================================
   LABELS
   ============================================================ */
QLabel {
    color: #1a1a1a;
    background: transparent;
}

#label_muted {
    color: #808080;
    font-size: 12px;
}

#label_stat_value {
    font-size: 36px;
    font-weight: 700;
    color: #1a1a1a;
}

#label_stat_label {
    font-size: 11px;
    color: #808080;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

/* ============================================================
   STATUS BAR
   ============================================================ */
QStatusBar {
    background-color: #ffffff;
    border-top: 1px solid #e5e7eb;
    color: #808080;
    font-size: 11px;
    padding: 2px 12px;
}

/* ============================================================
   AI DIAGNOSTIC PANEL
   ============================================================ */
#ai_panel {
    background-color: #f0f4f8;
    border: 1px solid #d1dce6;
    border-radius: 8px;
}

/* ============================================================
   DASHBOARD / EXECUTIVE NEXUS
   ============================================================ */
#kpi_card {
    background-color: #ffffff;
    border: none;
    border-radius: 8px;
}

#kpi_card:hover {
}

#nexus_card {
    background-color: #ffffff;
    border: none;
    border-radius: 8px;
}

#nexus_card:hover {
    background-color: #ffffff;
}

#nexus_greeting {
    color: #1a1a1a;
}
"""
