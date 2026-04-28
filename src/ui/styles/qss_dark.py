"""
Pricing Master Suite – Dark Enterprise QSS Theme (Minimal & Clean Design)
Primary accent: #60a5fa (professional blue)
Natura brand: #f59e0b (muted orange)
Avon brand:  #c4b5fd (muted purple)
"""

DARK_STYLESHEET = """
/* ============================================================
   GLOBAL
   ============================================================ */

QWidget {
    background-color: #0f172a;
    color: #f1f5f9;
    font-family: "Helvetica Neue", Arial;
    font-size: 13px;
    outline: none;
}

QMainWindow {
    background-color: #0f172a;
}

/* ============================================================
   TOP NAVIGATION BAR
   ============================================================ */
#top_nav_bar {
    background-color: #1e293b;
    border-bottom: 1px solid #334155;
}

#logo_container {
    border-right: 1px solid #334155;
}

#settings_container {
    border-left: 1px solid #334155;
}

#tabs_container {
    background-color: #1e293b;
}

#logo_label {
    color: #f1f5f9;
    font-size: 14px;
    font-weight: 700;
}

/* Navigation buttons (top tabs) */
#tab_button {
    background-color: transparent;
    color: #94a3b8;
    border: none;
    border-bottom: 2px solid transparent;
    border-radius: 0px;
    padding: 8px 16px;
    text-align: center;
    font-size: 13px;
    font-weight: 400;
}

#tab_button:hover {
    background-color: #334155;
    color: #e2e8f0;
    border-bottom-color: #475569;
}

#tab_button:checked {
    background-color: transparent;
    color: #60a5fa;
    font-weight: 600;
    border-bottom: 2px solid #60a5fa;
}

/* Theme toggle button */
#theme_toggle_btn {
    background-color: transparent;
    color: #94a3b8;
    border: none;
    border-radius: 20px;
    font-size: 20px;
    padding: 0px;
    margin: 0px;
}

#theme_toggle_btn:hover {
    background-color: #334155;
}

#theme_toggle_btn:pressed {
    background-color: #475569;
}

/* ============================================================
   CADASTRO DROPDOWN PANEL
   ============================================================ */
#dropdown_panel {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 2px;
}

#dropdown_item {
    background-color: transparent;
    color: #94a3b8;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    text-align: left;
    font-size: 13px;
    font-weight: 400;
    min-height: 36px;
}

#dropdown_item:hover {
    background-color: #0c2540;
    color: #60a5fa;
    font-weight: 500;
}

#dropdown_item:pressed {
    background-color: #1e3a6e;
    color: #93c5fd;
}

/* ============================================================
   CONTENT AREA
   ============================================================ */
#content_area {
    background-color: #0f172a;
}

/* ============================================================
   PAGE HEADER
   ============================================================ */
#page_header {
    background-color: #0f172a;
    border-bottom: 1px solid #334155;
}

#page_title {
    font-size: 32px;
    font-weight: 600;
    color: #f1f5f9;
}

#page_subtitle {
    font-size: 14px;
    color: #cbd5e1;
}

/* ============================================================
   CARDS / PANELS
   ============================================================ */
#card {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 2px;
}

#card:hover {
    border-color: #475569;
}

#card_flat {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 8px;
}

#card_flat:hover {
    border-color: #475569;
}

#error_card {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 8px;
}

#error_card:hover {
    border-color: #475569;
    background-color: #334155;
}

#error_card[selected="true"] {
    border-color: #60a5fa;
    background-color: #0c2540;
}

/* ============================================================
   DROP ZONE
   ============================================================ */
#dropzone {
    background-color: #1e293b;
    border: 2px dashed #475569;
    border-radius: 8px;
    color: #94a3b8;
    font-size: 12px;
}

#dropzone:hover {
    border-color: #64748b;
    background-color: #334155;
    color: #cbd5e1;
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

#dropzone[brand="natura"] {
    border: 2px solid #f59e0b;
    background-color: #332b1a;
    color: #fcd34d;
}

#dropzone[brand="avon"] {
    border: 2px solid #c4b5fd;
    background-color: #2d1b4e;
    color: #e9d5ff;
}

#dropzone[brand="ml"] {
    border: 2px solid #2196F3;
    background-color: #0d1b2a;
    color: #5cabff;
}

#dropzone[brand="all"] {
    border: 2px solid #00e676;
    background-color: #0a1e14;
    color: #b2ffda;
}

#dropzone[brand*="_"] {
    border: 2px solid #9e9e9e;
    background-color: #1e1e1e;
    color: #e0e0e0;
}

/* ============================================================
   BUTTONS
   ============================================================ */
QPushButton {
    background-color: #334155;
    color: #e2e8f0;
    border: 1px solid #475569;
    border-radius: 6px;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: 500;
    min-height: 32px;
    outline: none;
}

QPushButton:hover {
    background-color: #475569;
    border-color: #64748b;
    color: #f1f5f9;
}

QPushButton:pressed {
    background-color: #1e293b;
    border-color: #64748b;
}

QPushButton:focus {
    border-color: #60a5fa;
}

QPushButton:disabled {
    background-color: #1e293b;
    color: #64748b;
    border-color: #334155;
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
    border: 2px solid #60a5fa;
    background-color: #3b82f6;
}

#btn_primary:disabled {
    background-color: #1e3a8a;
    color: #60a5fa;
    border: none;
}

#btn_avon {
    background-color: #8b5cf6;
    color: #ffffff;
    border: none;
    font-weight: 600;
    min-height: 38px;
    border-radius: 6px;
}

#btn_avon:hover {
    background-color: #a78bfa;
}

#btn_secondary {
    background-color: #334155;
    color: #f1f5f9;
    border: 1px solid #475569;
    border-radius: 6px;
}

#btn_secondary:hover {
    background-color: #475569;
    border-color: #64748b;
}

#btn_secondary:focus {
    border-color: #60a5fa;
}

#btn_ghost {
    background-color: transparent;
    color: #94a3b8;
    border: 1px solid #475569;
    border-radius: 6px;
}

#btn_ghost:hover {
    background-color: #1e293b;
    color: #cbd5e1;
    border-color: #64748b;
}

#btn_ghost:focus {
    border-color: #60a5fa;
}

#btn_danger {
    background-color: #7f1d1d;
    color: #fca5a5;
    border: 1px solid #991b1b;
    border-radius: 6px;
}

#btn_danger:hover {
    background-color: #b91c1c;
}

/* ============================================================
   PROGRESS BAR
   ============================================================ */
QProgressBar {
    background-color: #334155;
    border: none;
    border-radius: 6px;
    height: 6px;
    text-align: center;
    color: transparent;
}

QProgressBar::chunk {
    background: #60a5fa;
    border-radius: 6px;
}

#progress_avon::chunk {
    background: #a78bfa;
}

/* ============================================================
   TABLE
   ============================================================ */
QTableWidget {
    background-color: #1e293b;
    alternate-background-color: #334155;
    border: 1px solid #334155;
    border-radius: 8px;
    gridline-color: #475569;
    selection-background-color: #0c2540;
    selection-color: #60a5fa;
    show-decoration-selected: 1;
}

QTableWidget::item {
    padding: 8px 12px;
    border: none;
    color: #e2e8f0;
}

QTableWidget::item:selected {
    background-color: #0c2540;
    color: #60a5fa;
    font-weight: 600;
}

QTableWidget::item:hover {
    background-color: #334155;
}

QHeaderView {
    background-color: #334155;
}

QHeaderView::section {
    background-color: #334155;
    color: #94a3b8;
    font-size: 11px;
    font-weight: 600;
    padding: 9px 12px;
    border: none;
    border-bottom: 1px solid #475569;
    border-right: 1px solid #1e293b;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

QHeaderView::section:last {
    border-right: none;
}

QTableCornerButton::section {
    background-color: #334155;
    border: none;
    border-bottom: 1px solid #475569;
}

/* ============================================================
   INPUT FIELDS
   ============================================================ */
QLineEdit {
    background-color: #334155;
    color: #f1f5f9;
    border: 1px solid #475569;
    border-radius: 6px;
    padding: 10px 12px;
    selection-background-color: #1e40af;
    min-height: 32px;
    outline: none;
}

QLineEdit:focus {
    border: 2px solid #60a5fa;
    padding: 9px 11px;
}

QLineEdit:disabled {
    color: #64748b;
    background-color: #1e293b;
    border-color: #475569;
}

QTextEdit, QPlainTextEdit {
    background-color: #334155;
    color: #f1f5f9;
    border: 1px solid #475569;
    border-radius: 6px;
    padding: 10px 12px;
    selection-background-color: #1e40af;
    outline: none;
}

QTextEdit:focus, QPlainTextEdit:focus {
    border: 2px solid #60a5fa;
    padding: 9px 11px;
}

/* ============================================================
   COMBO BOX
   ============================================================ */
QComboBox {
    background-color: #334155;
    color: #f1f5f9;
    border: 1px solid #475569;
    border-radius: 6px;
    padding: 8px 12px;
    min-height: 32px;
    min-width: 120px;
}

QComboBox:hover {
    border-color: #64748b;
}

QComboBox:focus {
    border-color: #60a5fa;
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
    background-color: #1e293b;
    border: 1px solid #475569;
    border-radius: 6px;
    selection-background-color: #0c2540;
    selection-color: #60a5fa;
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
    background-color: #475569;
    border-radius: 4px;
    min-height: 24px;
}

QScrollBar::handle:vertical:hover {
    background-color: #64748b;
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
    background-color: #475569;
    border-radius: 4px;
    min-width: 24px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #64748b;
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
    border: 1px solid #334155;
    border-radius: 8px;
    background-color: #1e293b;
    top: -1px;
}

QTabBar::tab {
    background-color: transparent;
    color: #94a3b8;
    padding: 8px 18px;
    border: none;
    border-bottom: 2px solid transparent;
    font-size: 13px;
    font-weight: 500;
}

QTabBar::tab:selected {
    color: #60a5fa;
    border-bottom: 2px solid #60a5fa;
}

QTabBar::tab:hover:!selected {
    color: #cbd5e1;
}

/* ============================================================
   GROUP BOX
   ============================================================ */
QGroupBox {
    border: 1px solid #475569;
    border-radius: 8px;
    margin-top: 18px;
    padding: 12px 8px 8px 8px;
    font-size: 11px;
    color: #94a3b8;
    font-weight: 600;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 6px;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

/* ============================================================
   CHECKBOXES & RADIO BUTTONS
   ============================================================ */
QCheckBox {
    color: #cbd5e1;
    spacing: 8px;
    font-size: 12px;
}

QCheckBox::indicator {
    width: 15px;
    height: 15px;
    border: 1px solid #475569;
    border-radius: 4px;
    background-color: #334155;
}

QCheckBox::indicator:checked {
    background-color: #60a5fa;
    border-color: #60a5fa;
}

QCheckBox::indicator:hover {
    border-color: #64748b;
}

QRadioButton {
    color: #cbd5e1;
    spacing: 8px;
    font-size: 12px;
}

QRadioButton::indicator {
    width: 15px;
    height: 15px;
    border: 1px solid #475569;
    border-radius: 8px;
    background-color: #334155;
}

QRadioButton::indicator:checked {
    background-color: #60a5fa;
    border-color: #60a5fa;
}

/* ============================================================
   LABELS
   ============================================================ */
QLabel {
    color: #e2e8f0;
    background: transparent;
}

#label_muted {
    color: #94a3b8;
    font-size: 12px;
}

#label_hint {
    color: #64748b;
    font-size: 12px;
    font-style: italic;
}

#label_stat_value {
    font-size: 36px;
    font-weight: 700;
    color: #f1f5f9;
}

#label_stat_label {
    font-size: 11px;
    color: #94a3b8;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

#label_natura {
    color: #fcd34d;
    font-size: 11px;
    font-weight: 600;
}

#label_avon {
    color: #e9d5ff;
    font-size: 11px;
    font-weight: 600;
}

/* ============================================================
   STATUS BAR
   ============================================================ */
QStatusBar {
    background-color: #0f172a;
    border-top: 1px solid #334155;
    color: #94a3b8;
    font-size: 11px;
    padding: 2px 12px;
}

/* ============================================================
   MESSAGE BOX / DIALOGS
   ============================================================ */
QMessageBox {
    background-color: #1e293b;
}

QMessageBox QLabel {
    color: #e2e8f0;
    min-width: 320px;
}

QMessageBox QPushButton {
    min-width: 80px;
}

/* ============================================================
   TOOLTIP
   ============================================================ */
QToolTip {
    background-color: #334155;
    color: #f1f5f9;
    border: 1px solid #475569;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
    opacity: 230;
}

/* ============================================================
   SPLITTER
   ============================================================ */
QSplitter::handle {
    background-color: #334155;
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
    background-color: #334155;
    max-height: 1px;
    min-height: 1px;
    border: none;
}

#divider_v {
    background-color: #334155;
    max-width: 1px;
    min-width: 1px;
    border: none;
}

/* ============================================================
   BADGES
   ============================================================ */
#badge_error {
    background-color: #7f1d1d;
    color: #fca5a5;
    border: 1px solid #991b1b;
    border-radius: 6px;
    padding: 2px 8px;
    font-size: 10px;
    font-weight: 700;
}

#badge_warning {
    background-color: #78350f;
    color: #fde047;
    border: 1px solid #92400e;
    border-radius: 6px;
    padding: 2px 8px;
    font-size: 10px;
    font-weight: 700;
}

#badge_ok {
    background-color: #064e3b;
    color: #6ee7b7;
    border: 1px solid #059669;
    border-radius: 6px;
    padding: 2px 8px;
    font-size: 10px;
    font-weight: 700;
}

#badge_natura {
    background-color: #332b1a;
    color: #fcd34d;
    border-radius: 4px;
    padding: 2px 7px;
    font-size: 10px;
    font-weight: 700;
}

#badge_avon {
    background-color: #2d1b4e;
    color: #e9d5ff;
    border-radius: 4px;
    padding: 2px 7px;
    font-size: 10px;
    font-weight: 700;
}

/* ============================================================
   AI DIAGNOSTIC PANEL
   ============================================================ */
#ai_panel {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 8px;
}

#ai_text {
    background-color: transparent;
    color: #cbd5e1;
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
    background-color: #1e293b;
    border: none;
    border-radius: 8px;
}

#kpi_card:hover {
}

#nexus_card {
    background-color: #1e293b;
    border: none;
    border-radius: 8px;
}

#nexus_card:hover {
    background-color: #1e293b;
}

#nexus_greeting {
    color: #f1f5f9;
}
"""
