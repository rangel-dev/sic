"""Home / Welcome view."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QScrollArea, QSizePolicy, QVBoxLayout, QWidget
)
from src.ui.components.base_widgets import Divider


class HomeView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        outer.addWidget(scroll)

        container = QWidget()
        scroll.setWidget(container)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(36, 32, 36, 32)
        layout.setSpacing(0)

        # Hero
        hero_title = QLabel("SIC")
        hero_title.setStyleSheet("font-size:32px;font-weight:800;background:transparent;")
        layout.addWidget(hero_title)

        hero_sub = QLabel("System Intelligence Commerce  ·  v0.0.8")
        hero_sub.setStyleSheet("font-size:13px;color:#555;background:transparent;margin-bottom:28px;")
        layout.addWidget(hero_sub)

        layout.addWidget(Divider())
        layout.addSpacing(24)

        # Module cards row
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(16)

        modules = [
            ("⊕", "Gerador",     "Converte planilhas Excel em XMLs de Pricebook para o Salesforce Demandware."),
            ("↕", "Sync",        "Sincroniza listas de vitrine e atributos de produto (online-flag, searchable)."),
            ("✓", "Auditor",     "Validação Double-Blind: cruza Excel vs Pricebook vs Catálogo em 12 regras."),
            ("◎", "Volumetria",  "OCR em imagens de produto para validar volume vs catálogo SF."),
        ]

        for icon, name, desc in modules:
            card = self._make_module_card(icon, name, desc)
            cards_layout.addWidget(card)

        layout.addLayout(cards_layout)
        layout.addSpacing(32)

        # Getting started
        gs_title = QLabel("Como começar")
        gs_title.setStyleSheet("font-size:15px;font-weight:700;background:transparent;margin-bottom:12px;")
        layout.addWidget(gs_title)

        steps = [
            ("1", "Gerador",    "Carregue a planilha GRADE DE ATIVAÇÃO e gere o XML de Pricebook."),
            ("2", "Sync",       "Carregue o Excel + XMLs de Catálogo para calcular o delta de listas."),
            ("3", "Auditor",    "Carregue todos os arquivos para executar a auditoria completa."),
            ("4", "Exportar",   "Exporte o resultado para Excel ou envie ao Google Chat."),
        ]

        for num, step, desc in steps:
            row = QHBoxLayout()
            row.setSpacing(12)

            num_lbl = QLabel(num)
            num_lbl.setFixedSize(28, 28)
            num_lbl.setAlignment(Qt.AlignCenter)
            num_lbl.setStyleSheet(
                "background:#2a1508;color:#ff8050;border-radius:14px;"
                "font-weight:700;font-size:12px;"
            )
            row.addWidget(num_lbl)

            step_lbl = QLabel(f"<b>{step}:</b> {desc}")
            step_lbl.setStyleSheet("font-size:12px;background:transparent;")
            step_lbl.setWordWrap(True)
            row.addWidget(step_lbl, 1)

            layout.addLayout(row)
            layout.addSpacing(8)

        layout.addStretch()

    def _make_module_card(self, icon: str, name: str, desc: str) -> QWidget:
        card = QWidget()
        card.setObjectName("card")
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(6)

        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet(
            "font-size:24px;color:#FF6B35;background:transparent;"
        )
        layout.addWidget(icon_lbl)

        name_lbl = QLabel(name)
        name_lbl.setStyleSheet("font-size:14px;font-weight:700;background:transparent;")
        layout.addWidget(name_lbl)

        desc_lbl = QLabel(desc)
        desc_lbl.setStyleSheet("font-size:11px;color:#555;background:transparent;")
        desc_lbl.setWordWrap(True)
        layout.addWidget(desc_lbl)

        return card
