"""
Executive Nexus Dashboard — Home View
Modern, data-driven landing page for SIC.
"""
from datetime import datetime
from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtWidgets import (
    QHBoxLayout, 
    QLabel, 
    QScrollArea, 
    QSizePolicy, 
    QVBoxLayout, 
    QWidget,
    QGridLayout,
    QSpacerItem,
    QFrame,
    QPushButton
)
from src.ui.components.base_widgets import Divider, PulseStatus, KpiWidget, NexusCard
from src.core.history_engine import HistoryEngine
from src.core.version import VERSION

# Mapa de módulo → (ícone, índice de navegação, cor do card)
_MODULE_NAV = {
    "Gerador":    ("⊕", 1, "#FF8050"),
    "Sync":       ("↕", 2, "#FF8050"),
    "Auditor":    ("✓", 3, "#BB88FF"),
    "Volumetria": ("◎", 4, "#BB88FF"),
    "Cadastro":   ("≡", 5, "#60a5fa"),
    "Menus CB":   ("≈", 8, "#42a5f5"),
    "Histórico":  ("◔", 7, "#888888"),
}

class HomeView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.window = parent # MainWindow
        self._setup_ui()
        # Adiar a query ao banco para depois da janela ser pintada (evita bloqueio pré-render)
        QTimer.singleShot(50, self.refresh_stats)

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        root.addWidget(scroll)

        container = QWidget()
        scroll.setWidget(container)
        
        self.main_layout = QVBoxLayout(container)
        self.main_layout.setContentsMargins(40, 40, 40, 40)
        self.main_layout.setSpacing(0)

        # ─── HEADER AREA ──────────────────────────────────────────────────────
        header = QHBoxLayout()
        header.setSpacing(12)
        
        greeting = self._get_greeting()
        self.title_lbl = QLabel(greeting)
        self.title_lbl.setObjectName("nexus_greeting")
        self.title_lbl.setStyleSheet("font-size: 28px; font-weight: 800;")
        header.addWidget(self.title_lbl)

        header.addWidget(PulseStatus())
        
        status_lbl = QLabel("Sistemas Prontos")
        status_lbl.setStyleSheet("font-size: 12px; color: #4CAF50; font-weight: 600; text-transform: uppercase;")
        header.addWidget(status_lbl)
        
        header.addStretch()
        self.main_layout.addLayout(header)

        sub_header = QLabel(f"Bem-vindo ao centro de comando SIC  ·  Versão {VERSION}")
        sub_header.setStyleSheet("font-size: 13px; color: #777; margin-bottom: 30px;")
        self.main_layout.addWidget(sub_header)

        # ─── KPI ROW ──────────────────────────────────────────────────────────
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(20)

        self.kpi_total = KpiWidget("Operações Realizadas", "0", "📊")
        self.kpi_brands = KpiWidget("Marcas Ativas", "2", "🏢")
        self.kpi_status = KpiWidget("Saúde do Motor", "100%", "⚡")

        kpi_row.addWidget(self.kpi_total)
        kpi_row.addWidget(self.kpi_brands)
        kpi_row.addWidget(self.kpi_status)
        kpi_row.addStretch()
        
        self.main_layout.addLayout(kpi_row)
        self.main_layout.addSpacing(32)

        # ─── ACESSOS RECENTES ──────────────────────────────────────────────────────
        recent_header = QHBoxLayout()
        recent_title = QLabel("ACESSOS RECENTES")
        recent_title.setStyleSheet(
            "font-size: 11px; font-weight: 700; color: #555; letter-spacing: 1.5px;"
        )
        recent_header.addWidget(recent_title)
        recent_header.addStretch()
        self.main_layout.addLayout(recent_header)
        self.main_layout.addSpacing(12)

        # Container widget para recentes (QGridLayout igual ao nexus_grid)
        self.recent_container = QWidget()
        self.recent_grid = QGridLayout(self.recent_container)
        self.recent_grid.setSpacing(20)
        self.recent_grid.setContentsMargins(0, 0, 0, 0)

        self.recent_placeholder = QLabel("Nenhum módulo utilizado ainda. Execute uma operação para ver seus atalhos aqui.")
        self.recent_placeholder.setStyleSheet("color: #888; font-size: 12px;")
        self.recent_grid.addWidget(self.recent_placeholder, 0, 0)

        self.main_layout.addWidget(self.recent_container)
        self.main_layout.addSpacing(32)

        # ─── NEXUS CENTER (Action Cards) ──────────────────────────────────────
        nexus_label = QLabel("NEXUS DE OPERAÇÕES")
        nexus_label.setStyleSheet("font-size: 11px; font-weight: 700; color: #555; letter-spacing: 1.5px; margin-bottom: 15px;")
        self.main_layout.addWidget(nexus_label)

        nexus_grid = QGridLayout()
        nexus_grid.setSpacing(20)

        # Module Cards
        modules = [
            ("⊕", "Gerador Pro",  "Processamento de planilhas e geração de XML Pricebook.", "#FF8050", 1),
            ("↕", "Sync Hub",     "Sincronização de vitrines e atributos Salesforce.",    "#FF8050", 2),
            ("✓", "Audit Nexus",  "Motor de auditoria integrada com 12 regras.",          "#BB88FF", 3),
            ("◎", "Volumetria",   "Validação de volumes via processamento de catálogo.",  "#BB88FF", 4),
        ]

        for i, (icon, name, desc, color, idx) in enumerate(modules):
            card = NexusCard(icon, name, desc, color)
            card.clicked.connect(lambda i=idx: self.window._switch(i)) # Access main window
            nexus_grid.addWidget(card, 0, i)

        self.main_layout.addLayout(nexus_grid)
        self.main_layout.addSpacing(40)

        # ─── RECENT ACTIVITY ──────────────────────────────────────────────────
        self.main_layout.addWidget(Divider())
        self.main_layout.addSpacing(25)
        
        activity_header = QHBoxLayout()
        act_title = QLabel("Atividade Recente")
        act_title.setStyleSheet("font-size: 16px; font-weight: 700;")
        activity_header.addWidget(act_title)
        activity_header.addStretch()
        
        view_all = QPushButton("Ver Histórico Completo →")
        view_all.setObjectName("btn_ghost")
        view_all.setCursor(Qt.PointingHandCursor)
        view_all.clicked.connect(lambda: self.window._switch(7))
        activity_header.addWidget(view_all)
        
        self.main_layout.addLayout(activity_header)
        self.main_layout.addSpacing(15)

        self.activity_container = QVBoxLayout()
        self.activity_container.setSpacing(10)
        self.main_layout.addLayout(self.activity_container)

        self.main_layout.addStretch()

    def _get_greeting(self) -> str:
        hour = datetime.now().hour
        if hour < 12: return "Bom dia"
        if hour < 18: return "Boa tarde"
        return "Boa noite"

    def refresh_stats(self):
        """Pulls real data from engines."""
        try:
            entries = HistoryEngine.get_entries()
            self.kpi_total.set_value(len(entries))

            # ── Acessos Recentes: últimos 3 módulos distintos ──────────────────
            # Clear grid preservando o placeholder
            while self.recent_grid.count():
                item = self.recent_grid.takeAt(0)
                if item and item.widget() and item.widget() is not self.recent_placeholder:
                    item.widget().deleteLater()

            seen: set[str] = set()
            recent_modules: list[dict] = []
            for entry in entries:
                mod = entry["module"]
                if mod not in seen and mod in _MODULE_NAV:
                    seen.add(mod)
                    recent_modules.append(entry)
                if len(recent_modules) == 3:
                    break

            if recent_modules:
                for col, entry in enumerate(recent_modules):
                    mod = entry["module"]
                    icon, nav_idx, color = _MODULE_NAV.get(mod, ("◈", 0, "#888888"))
                    try:
                        dt = datetime.fromisoformat(entry["timestamp"])
                        when = dt.strftime("%d/%m  %H:%M")
                    except Exception:
                        when = entry["timestamp"][:16]
                    card = NexusCard(icon, mod, f"Última vez: {when}", color)
                    card.clicked.connect(lambda i=nav_idx: self.window._switch(i))
                    self.recent_grid.addWidget(card, 0, col)
            else:
                self.recent_grid.addWidget(self.recent_placeholder, 0, 0)

            # ── Atividade Recente (últimas 3 entradas) ─────────────────────────
            for i in reversed(range(self.activity_container.count())):
                self.activity_container.itemAt(i).widget().setParent(None)

            for entry in entries[:3]:
                row = QFrame()
                row.setObjectName("card_flat")
                row_layout = QHBoxLayout(row)
                row_layout.setContentsMargins(15, 10, 15, 10)

                mod_lbl = QLabel(f"<b>{entry['module']}</b>")
                mod_lbl.setFixedWidth(80)
                row_layout.addWidget(mod_lbl)

                act_lbl = QLabel(entry['action'])
                row_layout.addWidget(act_lbl, 1)

                try:
                    dt = datetime.fromisoformat(entry['timestamp'])
                    date_str = dt.strftime("%d/%m/%Y")
                except Exception:
                    date_str = entry['timestamp'].split('T')[0]

                date_lbl = QLabel(date_str)
                date_lbl.setStyleSheet("color: #666; font-size: 11px;")
                row_layout.addWidget(date_lbl)

                self.activity_container.addWidget(row)

        except Exception as e:
            print(f"Error refreshing dashboard: {e}")

    def refresh_theme(self):
        self.refresh_stats()
