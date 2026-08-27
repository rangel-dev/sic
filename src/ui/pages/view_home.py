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
from src.ui.components.base_widgets import Divider, PulseStatus, KpiWidget
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
        self.main_layout.addSpacing(40)

        # ─── NOVIDADES DO SISTEMA ──────────────────────────────────────────────
        self._build_news_section()

        # ─── RECENT ACTIVITY TIMELINE ──────────────────────────────────────────
        self.main_layout.addWidget(Divider())
        self.main_layout.addSpacing(25)
        
        activity_header = QHBoxLayout()
        act_title = QLabel("Timeline de Operações")
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

    def _build_news_section(self):
        news_header = QHBoxLayout()
        news_title = QLabel("ÚLTIMAS NOVIDADES")
        news_title.setStyleSheet(
            "font-size: 11px; font-weight: 700; color: #555; letter-spacing: 1.5px;"
        )
        news_header.addWidget(news_title)
        
        news_header.addStretch()

        btn_sobre = QPushButton("Ver notas da versão →")
        btn_sobre.setObjectName("btn_ghost")
        btn_sobre.setCursor(Qt.PointingHandCursor)
        if hasattr(self, 'window') and self.window:
            btn_sobre.clicked.connect(lambda: self.window._switch(11))
        news_header.addWidget(btn_sobre)
        
        self.main_layout.addLayout(news_header)
        self.main_layout.addSpacing(12)

        from src.core.changelog_data import CHANGELOG
        latest = CHANGELOG[0] if CHANGELOG else None

        if latest:
            card = QFrame()
            card.setObjectName("card_flat")
            card.setStyleSheet("QFrame#card_flat { border-left: 4px solid #BB88FF; }")
            layout = QVBoxLayout(card)
            layout.setContentsMargins(20, 16, 20, 16)
            layout.setSpacing(8)

            ver_lbl = QLabel(f"Versão {latest['version']}  ·  {latest.get('date', '')}")
            ver_lbl.setStyleSheet("font-size: 12px; font-weight: 700; color: #BB88FF; background: transparent;")
            layout.addWidget(ver_lbl)

            TYPE_MAP = {
                "feat": "Novidade",
                "fix":  "Correção",
                "perf": "Performance",
                "chore":"Ajuste",
            }

            for entry in latest["entries"][:2]:
                if len(entry) >= 2:
                    etype, etext = entry[0], entry[1]
                    label = TYPE_MAP.get(etype, "Info")
                    lbl = QLabel(f"• <b>{label}:</b> {etext}")
                    lbl.setWordWrap(True)
                    lbl.setStyleSheet("font-size: 13px; color: #555; background: transparent;")
                    layout.addWidget(lbl)
            
            if len(latest["entries"]) > 2:
                more_lbl = QLabel(f"<i>E mais {len(latest['entries']) - 2} melhorias...</i>")
                more_lbl.setStyleSheet("font-size: 11px; color: #888; background: transparent;")
                layout.addWidget(more_lbl)

            self.main_layout.addWidget(card)
        else:
            lbl = QLabel("Nenhuma novidade registrada.")
            lbl.setStyleSheet("color: #888; font-size: 12px;")
            self.main_layout.addWidget(lbl)
            
        self.main_layout.addSpacing(32)

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

            # ── Atividade Recente (Timeline) ─────────────────────────
            for i in reversed(range(self.activity_container.count())):
                self.activity_container.itemAt(i).widget().setParent(None)

            if not entries:
                lbl = QLabel("Nenhuma atividade registrada no histórico.")
                lbl.setStyleSheet("color: #888; font-style: italic; font-size: 12px;")
                self.activity_container.addWidget(lbl)
                return

            for entry in entries[:6]:
                row = QFrame()
                row.setObjectName("card_flat")
                row_layout = QHBoxLayout(row)
                row_layout.setContentsMargins(15, 12, 15, 12)

                mod = entry.get('module', 'SIC')
                icon_char = _MODULE_NAV.get(mod, ("◈", 0, "#888"))[0]
                color = _MODULE_NAV.get(mod, ("◈", 0, "#888"))[2]

                icon_lbl = QLabel(icon_char)
                icon_lbl.setStyleSheet(f"font-size: 16px; color: {color}; font-weight: bold; background: transparent;")
                icon_lbl.setFixedWidth(24)
                icon_lbl.setAlignment(Qt.AlignCenter)
                row_layout.addWidget(icon_lbl)

                info_layout = QVBoxLayout()
                info_layout.setSpacing(2)
                
                act_lbl = QLabel(entry.get('action', 'Ação desconhecida'))
                act_lbl.setStyleSheet("font-size: 13px; font-weight: 600; background: transparent;")
                info_layout.addWidget(act_lbl)

                try:
                    dt = datetime.fromisoformat(entry['timestamp'])
                    date_str = dt.strftime("%d/%m/%Y às %H:%M")
                except Exception:
                    date_str = entry.get('timestamp', '')[:16]

                meta_lbl = QLabel(f"{mod}  ·  {date_str}")
                meta_lbl.setStyleSheet("font-size: 11px; color: #888; background: transparent;")
                info_layout.addWidget(meta_lbl)

                row_layout.addLayout(info_layout, 1)
                self.activity_container.addWidget(row)

        except Exception as e:
            print(f"Error refreshing dashboard: {e}")

    def refresh_theme(self):
        self.refresh_stats()
