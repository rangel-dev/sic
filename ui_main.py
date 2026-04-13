"""
MainWindow – Pricing Master Suite
Sidebar navigation (QVBoxLayout of NavButtons) + QStackedWidget for views.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, QSize, QSettings
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QSizePolicy,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from styles.qss_dark  import DARK_STYLESHEET
from styles.qss_light import LIGHT_STYLESHEET

from views.view_home       import HomeView
from views.view_gerador    import GeradorView
from views.view_sync       import SyncView
from views.view_auditor    import AuditorView
from views.view_volumetria import VolumetriaView
from views.view_cadastro   import CadastroView
from views.view_settings   import SettingsView
from views.view_history    import HistoryView


# ─── Navigation button ────────────────────────────────────────────────────────
class NavButton(QPushButton):
    """Left-sidebar navigation button — checkable, auto-exclusive."""

    def __init__(self, icon: str, label: str, parent=None):
        super().__init__(parent)
        self.setText(f"  {icon}   {label}")
        self.setObjectName("nav_button")
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(40)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        font = self.font()
        font.setPointSize(12)
        self.setFont(font)


# ─── Main Window ──────────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SIC — System Intelligence Commerce  v0.0.8")
        self.setMinimumSize(1280, 800)
        self.resize(1460, 900)

        self._nav_buttons: list[NavButton] = []
        self._pages: list[QWidget] = []

        self._build_ui()

        # Start on home
        self._switch(0)

    # ── Build ─────────────────────────────────────────────────────────────
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self._build_sidebar())

        self._stack = QStackedWidget()
        self._stack.setObjectName("content_area")
        self._build_pages()
        layout.addWidget(self._stack)

        # Status bar
        sb = self.statusBar()
        sb.showMessage("Pronto  —  SIC System Intelligence Commerce v0.0.8")

    def _build_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(226)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Logo block ────────────────────────────────────────────────────
        logo_widget = QWidget()
        logo_layout = QVBoxLayout(logo_widget)
        logo_layout.setContentsMargins(18, 22, 16, 16)
        logo_layout.setSpacing(3)

        title_lbl = QLabel("⬡  SIC")
        title_lbl.setObjectName("logo_label")
        font = QFont()
        font.setPointSize(16)
        font.setWeight(QFont.Bold)
        title_lbl.setFont(font)
        logo_layout.addWidget(title_lbl)

        ver_lbl = QLabel("System Intelligence Commerce  v0.0.8")
        ver_lbl.setObjectName("version_label")
        logo_layout.addWidget(ver_lbl)

        layout.addWidget(logo_widget)

        # Divider
        div = QFrame()
        div.setObjectName("divider")
        div.setFrameShape(QFrame.HLine)
        div.setFixedHeight(1)
        layout.addWidget(div)

        layout.addSpacing(8)

        # ── Nav section label ─────────────────────────────────────────────
        nav_lbl = QLabel("  MÓDULOS")
        nav_lbl.setObjectName("label_section")
        nav_lbl.setContentsMargins(18, 6, 0, 4)
        layout.addWidget(nav_lbl)

        # ── Nav items ─────────────────────────────────────────────────────
        NAV_ITEMS = [
            ("⌂",  "Início",      0),
            ("⊕",  "Gerador",     1),
            ("↕",  "Sync",        2),
            ("✓",  "Auditor",     3),
            ("◎",  "Volumetria",  4),
            ("≡",  "Cadastro",    5),
            ("◔",  "Histórico",   7),
        ]

        for icon, label, idx in NAV_ITEMS:
            btn = NavButton(icon, label)
            btn.clicked.connect(lambda _checked, i=idx: self._switch(i))
            self._nav_buttons.append(btn)
            layout.addWidget(btn)

        layout.addStretch()

        # ── Settings section ──────────────────────────────────────────────
        cfg_lbl = QLabel("  SISTEMA")
        cfg_lbl.setObjectName("label_section")
        cfg_lbl.setContentsMargins(18, 6, 0, 4)
        layout.addWidget(cfg_lbl)

        btn_cfg = NavButton("⚙", "Configurações")
        btn_cfg.clicked.connect(lambda: self._switch(6))
        self._nav_buttons.append(btn_cfg)
        layout.addWidget(btn_cfg)

        # ── Theme Toggle ──────────────────────────────────────────────────
        layout.addSpacing(12)
        self._btn_theme = QPushButton("  ◑   Mudar Tema")
        self._btn_theme.setObjectName("nav_button") # Reuse style but not NavButton logic
        self._btn_theme.setFixedHeight(40)
        self._btn_theme.setCursor(Qt.PointingHandCursor)
        self._btn_theme.clicked.connect(self._toggle_theme)
        layout.addWidget(self._btn_theme)

        layout.addSpacing(16)

        return sidebar

    def _build_pages(self):
        self._pages = [
            HomeView(self),        # 0
            GeradorView(self),     # 1
            SyncView(self),        # 2
            AuditorView(self),     # 3
            VolumetriaView(self),  # 4
            CadastroView(self),    # 5
            SettingsView(self),    # 6
            HistoryView(self),     # 7
        ]
        for page in self._pages:
            self._stack.addWidget(page)

    # ── Navigation ────────────────────────────────────────────────────────
    def _switch(self, index: int):
        self._stack.setCurrentIndex(index)

        # Update button states (manual exclusive group — sidebar has no auto-exclusive)
        for i, btn in enumerate(self._nav_buttons):
            btn.setChecked(i == index)

        NAMES = ["Início", "Gerador", "Sync", "Auditor",
                 "Volumetria", "Cadastro", "Configurações", "Histórico"]
        if 0 <= index < len(NAMES):
            self.statusBar().showMessage(f"Módulo ativo: {NAMES[index]}")

    # ── Theme ─────────────────────────────────────────────────────────────
    def _toggle_theme(self):
        settings = QSettings("SIC", "SIC_Suite")
        current  = settings.value("theme", "light")
        new_theme = "dark" if current == "light" else "light"
        settings.setValue("theme", new_theme)
        settings.sync()

        app = QApplication.instance()
        if new_theme == "dark":
            app.setStyleSheet(DARK_STYLESHEET)
            self.statusBar().showMessage("Tema alterado p/ Escuro")
        else:
            app.setStyleSheet(LIGHT_STYLESHEET)
            self.statusBar().showMessage("Tema alterado p/ Claro")

        # Refresh all pages that support it
        for i in range(self._stack.count()):
            page = self._stack.widget(i)
            if hasattr(page, "refresh_theme"):
                page.refresh_theme()

    # ── Public API for child widgets ──────────────────────────────────────
    def show_status(self, message: str):
        self.statusBar().showMessage(message)
