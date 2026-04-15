"""
MainWindow – Pricing Master Suite
Sidebar navigation (QVBoxLayout of NavButtons) + QStackedWidget for views.
"""
from __future__ import annotations
import re
from typing import Optional

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

from src.ui.styles.qss_dark  import DARK_STYLESHEET
from src.ui.styles.qss_light import LIGHT_STYLESHEET

# View modules will be imported lazily in _load_page to drastically improve application startup time.

from src.core.version import VERSION, APP_NAME
# UpdateService e UpdateWorker são importados lazily dentro dos métodos que os usam,
# para evitar que o módulo `requests` seja carregado no startup (custo: 1–3 s).


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
    def __init__(self, progress_callback=None):
        super().__init__()
        self._progress = progress_callback
        def report(val, msg):
            if self._progress: self._progress(val, msg)

        report(0, "Inicializando interface...")
        self.setWindowTitle(f"{APP_NAME}  v{VERSION}")
        self.setMinimumSize(1280, 800)
        self.resize(1460, 900)
        
        self._nav_buttons: list[NavButton] = []
        self._pages: list[QWidget] = []
        self._update_url: Optional[str] = None

        report(20, "Construindo layout base...")
        self._build_ui()
        
        report(60, "Aplicando identidade visual...")
        self.apply_theme_and_font()

        # Start on home
        report(80, "Carregando Dashboard...")
        self._switch(0)

        # Check for updates in background
        self._check_for_updates()
        report(100, "Pronto")

    # ── Build ─────────────────────────────────────────────────────────────
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self._build_sidebar())
        
        if self._progress: self._progress(40, "Preparando módulos...")

        self._stack = QStackedWidget()
        self._stack.setObjectName("content_area")
        self._build_pages()
        layout.addWidget(self._stack)

        # Status bar
        sb = self.statusBar()
        sb.showMessage(f"Pronto  —  {APP_NAME} v{VERSION}")

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

        ver_lbl = QLabel(f"{APP_NAME}  v{VERSION}")
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

        # ── Update Notification Footer (Hidden by default) ────────────────
        layout.addStretch()
        self._btn_update = QPushButton("⚡  Atualização Disponível")
        self._btn_update.setObjectName("btn_primary") # Use primary color to grab attention
        self._btn_update.setFixedHeight(34)
        self._btn_update.setContentsMargins(10, 0, 10, 0)
        self._btn_update.setCursor(Qt.PointingHandCursor)
        self._btn_update.clicked.connect(self._on_update_clicked)
        self._btn_update.hide()
        
        # Wrapped for padding
        self._update_container = QWidget()
        up_layout = QVBoxLayout(self._update_container)
        up_layout.setContentsMargins(15, 10, 15, 15)
        up_layout.addWidget(self._btn_update)
        self._update_container.hide()
        layout.addWidget(self._update_container)

        return sidebar

    def _build_pages(self):
        self._pages = [None] * 8
        for i in range(8):
            self._stack.addWidget(QWidget())  # Dummy placeholder
            
        # Pre-load only the Home view for immediate startup
        self._load_page(0)

    def _load_page(self, index: int):
        if self._pages[index] is not None:
            return

        from PySide6.QtWidgets import QApplication

        # Lazy Imports
        if index == 0:
            from src.ui.pages.view_home import HomeView
            page = HomeView(self)
        elif index == 1:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            from src.ui.pages.view_gerador import GeradorView
            page = GeradorView(self)
            QApplication.restoreOverrideCursor()
        elif index == 2:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            from src.ui.pages.view_sync import SyncView
            page = SyncView(self)
            QApplication.restoreOverrideCursor()
        elif index == 3:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            from src.ui.pages.view_auditor import AuditorView
            page = AuditorView(self)
            QApplication.restoreOverrideCursor()
        elif index == 4:
            from src.ui.pages.view_volumetria import VolumetriaView
            page = VolumetriaView(self)
        elif index == 5:
            from src.ui.pages.view_cadastro import CadastroView
            page = CadastroView(self)
        elif index == 6:
            from src.ui.pages.view_settings import SettingsView
            page = SettingsView(self)
        elif index == 7:
            from src.ui.pages.view_history import HistoryView
            page = HistoryView(self)
        else:
            return

        self._pages[index] = page
        old_widget = self._stack.widget(index)
        self._stack.insertWidget(index, page)
        self._stack.removeWidget(old_widget)
        old_widget.deleteLater()

    # ── Navigation ────────────────────────────────────────────────────────
    def _switch(self, index: int):
        self._load_page(index)
        self._stack.setCurrentIndex(index)

        # Update button states (manual exclusive group — sidebar has no auto-exclusive)
        for i, btn in enumerate(self._nav_buttons):
            btn.setChecked(i == index)

        NAMES = ["Início", "Gerador", "Sync", "Auditor",
                 "Volumetria", "Cadastro", "Configurações", "Histórico"]
        if 0 <= index < len(NAMES):
            self.statusBar().showMessage(f"Módulo ativo: {NAMES[index]}  |  v{VERSION}")

    # ── Updates ───────────────────────────────────────────────────────────
    def _check_for_updates(self):
        from src.workers.worker_update import UpdateWorker  # lazy — evita import do requests no startup
        self._update_worker = UpdateWorker()
        self._update_worker.update_found.connect(self._on_update_found)
        self._update_worker.start()

    def _on_update_found(self, tag: str, url: str):
        self._update_url = url
        self._btn_update.setText(f"⚡ Baixar {tag}")
        self._update_container.show()
        self._btn_update.show()
        self.statusBar().showMessage(f"Uma nova versão está disponível: {tag}!")

    def _on_update_clicked(self):
        if not self._update_url:
            return
            
        from PySide6.QtWidgets import QMessageBox
        res = QMessageBox.question(
            self, "Auto-Update", 
            "Deseja baixar a nova versão agora?\n\nO programa será reiniciado automaticamente após o download.",
            QMessageBox.Yes | QMessageBox.No
        )
        if res == QMessageBox.Yes:
            self._btn_update.setText("⏳ Baixando...")
            self._btn_update.setEnabled(False)
            self.statusBar().showMessage("Iniciando download da atualização...")
            
            # Run updater in background thread to prevent UI freezing
            import threading
            def run_update():
                try:
                    from src.core.update_service import UpdateService  # lazy
                    UpdateService.download_and_install(self._update_url)
                except Exception as e:
                    # Thread errors are hard to show directly in QMessageBox without signals,
                    # but the main process exits on success anyway.
                    print(f"Update background thread failed: {e}")
            
            threading.Thread(target=run_update, daemon=True).start()

    # ── Theme & Font Scaling ──────────────────────────────────────────────
    def _toggle_theme(self):
        settings = QSettings("SIC", "SIC_Suite")
        current  = settings.value("theme", "light")
        new_theme = "dark" if current == "light" else "light"
        settings.setValue("theme", new_theme)
        settings.sync()
        self.apply_theme_and_font()

    def apply_theme_and_font(self):
        """Applies both theme QSS and font scaling globally."""
        settings = QSettings("SIC", "SIC_Suite")
        theme = settings.value("theme", "light")
        base_size = int(settings.value("font_size", 13))
        
        # 1. Update Application Global Font
        app = QApplication.instance()
        font = app.font()
        font.setPointSize(base_size)
        app.setFont(font)

        # 2. Select Base Stylesheet
        raw_qss = DARK_STYLESHEET if theme == "dark" else LIGHT_STYLESHEET
        
        # 3. Scale QSS (Regex replacement of all 'px' values)
        # We scale based on ratio to 13px (original base)
        ratio = base_size / 13.0

        if ratio == 1.0:
            # Sem escalonamento necessário — aplica direto, evita ~500 ms de regex
            # (caso padrão: todos os usuários que não alteraram o tamanho de fonte)
            app.setStyleSheet(raw_qss)
        else:
            def scale_px(match):
                val = int(match.group(1))
                if val <= 1: return f"{val}px"  # Don't scale 1px borders
                return f"{int(val * ratio)}px"

            scaled_qss = re.sub(r'(\d+)px', scale_px, raw_qss)
            app.setStyleSheet(scaled_qss)
        
        # 4. Update Status Bar
        mode = "Escuro" if theme == "dark" else "Claro"
        self.statusBar().showMessage(f"Tema: {mode} | Fonte: {base_size}px")

        # 5. Refresh all pages that support it
        if hasattr(self, "_stack"):
            for i in range(self._stack.count()):
                page = self._stack.widget(i)
                if hasattr(page, "refresh_theme"):
                    page.refresh_theme()

    # ── Public API for child widgets ──────────────────────────────────────
    def show_status(self, message: str):
        self.statusBar().showMessage(message)
