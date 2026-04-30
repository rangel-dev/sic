"""Módulo Sobre — projeto, últimas atualizações (git local) e colaboradores."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from src.core.version import VERSION, APP_NAME
from src.core.changelog_data import CONTRIBUTORS
from src.ui.components.base_widgets import Divider, SectionHeader


# ── Contributor Card ─────────────────────────────────────────────────────────
class _ContributorCard(QFrame):
    def __init__(self, data: dict, parent=None):
        super().__init__(parent)
        self.setObjectName("nexus_card")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        color = data["color"]
        self.setStyleSheet(f"QFrame#nexus_card {{ border-top: 3px solid {color}; }}")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        top = QHBoxLayout()
        top.setSpacing(10)

        icon_lbl = QLabel(data["icon"])
        icon_lbl.setStyleSheet(
            f"font-size: 22px; color: {color}; background: transparent;"
        )
        top.addWidget(icon_lbl)

        name_block = QVBoxLayout()
        name_block.setSpacing(1)
        name_lbl = QLabel(data["name"])
        name_lbl.setStyleSheet("font-size: 15px; font-weight: 700; background: transparent;")
        name_block.addWidget(name_lbl)
        role_lbl = QLabel(data["role"])
        role_lbl.setStyleSheet("font-size: 11px; color: #888; background: transparent;")
        name_block.addWidget(role_lbl)
        top.addLayout(name_block, 1)
        layout.addLayout(top)

        bio_lbl = QLabel(data["bio"])
        bio_lbl.setWordWrap(True)
        bio_lbl.setStyleSheet("font-size: 12px; color: #666; background: transparent;")
        layout.addWidget(bio_lbl)

        if data.get("legacy"):
            legacy_lbl = QLabel(f"◂ {data['legacy']}")
            legacy_lbl.setStyleSheet(
                "font-size: 10px; color: #999; font-style: italic; background: transparent;"
            )
            legacy_lbl.setWordWrap(True)
            layout.addWidget(legacy_lbl)

        layout.addStretch()


# ── Main View ────────────────────────────────────────────────────────────────
class SobreView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        outer.addWidget(SectionHeader(
            "Sobre",
            "O projeto, últimas atualizações e quem faz o SIC acontecer"
        ))
        outer.addWidget(Divider())

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.NoFrame)
        outer.addWidget(scroll)

        self._container = QWidget()
        scroll.setWidget(self._container)
        self._layout = QVBoxLayout(self._container)
        self._layout.setContentsMargins(28, 28, 28, 40)
        self._layout.setSpacing(0)

        self._build_project_section()
        self._layout.addSpacing(28)
        self._layout.addWidget(Divider())
        self._layout.addSpacing(28)

        self._build_updates_section()
        self._layout.addSpacing(28)
        self._layout.addWidget(Divider())
        self._layout.addSpacing(28)

        self._build_contributors_section()
        self._layout.addStretch()

    # ── Seção 1: Sobre o Projeto ──────────────────────────────────────────
    def _build_project_section(self):
        self._add_section_label(self._layout, "SOBRE O PROJETO")
        self._layout.addSpacing(14)

        # App name + version badge
        name_row = QHBoxLayout()
        name_row.setSpacing(12)
        app_lbl = QLabel(APP_NAME)
        app_lbl.setStyleSheet("font-size: 20px; font-weight: 800; background: transparent;")
        name_row.addWidget(app_lbl)
        ver_badge = QLabel(f"  v{VERSION}  ")
        ver_badge.setStyleSheet(
            "font-size: 13px; font-weight: 600; color: #BB88FF;"
            " border: 1px solid #BB88FF; border-radius: 10px;"
            " padding: 2px 10px; background: transparent;"
        )
        name_row.addWidget(ver_badge)
        name_row.addStretch()
        self._layout.addLayout(name_row)
        self._layout.addSpacing(14)

        # Description
        desc = QLabel(
            "O SIC centraliza e automatiza as operações de precificação e catálogo "
            "para o Salesforce Commerce Cloud. Ele substitui processos manuais "
            "dispersos em planilhas por um fluxo estruturado, auditado e rastreável."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 13px; color: #555; background: transparent;")
        self._layout.addWidget(desc)
        self._layout.addSpacing(20)

        # How it works — module cards in a horizontal strip
        modules = [
            ("⊕", "Gerador",     "Processa planilhas Excel e gera XMLs de Pricebook para o Salesforce."),
            ("↕", "Sync",        "Sincroniza vitrines, atributos e catálogos entre marcas e plataformas."),
            ("✓", "Auditor",     "Valida consistência de preços, categorias e regras de negócio em lote."),
            ("≡", "Cadastro",    "Valida kits e pontuação cruzando XMLs Salesforce com planilhas de controle."),
            ("≈", "Menus CB",    "Verifica a integridade da estrutura de menus do catálogo B2C."),
        ]

        grid = QGridLayout()
        grid.setSpacing(10)
        for i, (icon, name, tip) in enumerate(modules):
            card = QFrame()
            card.setObjectName("card_flat")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(12, 12, 12, 12)
            card_layout.setSpacing(4)

            top_row = QHBoxLayout()
            top_row.setSpacing(6)
            icon_lbl = QLabel(icon)
            icon_lbl.setStyleSheet("font-size: 14px; color: #BB88FF; background: transparent;")
            top_row.addWidget(icon_lbl)
            name_lbl = QLabel(name)
            name_lbl.setStyleSheet("font-size: 12px; font-weight: 700; background: transparent;")
            top_row.addWidget(name_lbl)
            top_row.addStretch()
            card_layout.addLayout(top_row)

            tip_lbl = QLabel(tip)
            tip_lbl.setWordWrap(True)
            tip_lbl.setStyleSheet("font-size: 11px; color: #777; background: transparent;")
            card_layout.addWidget(tip_lbl)

            col = i % 3
            row = i // 3
            grid.addWidget(card, row, col)

        self._layout.addLayout(grid)
        self._layout.addSpacing(10)

        # Compat note
        compat = QLabel(
            "Compatível com Natura (NATBRA-), Avon (AVNBRA-) e Minha Loja (ML)."
        )
        compat.setStyleSheet("font-size: 11px; color: #999; background: transparent;")
        self._layout.addWidget(compat)

    # ── Seção 2: Últimas Atualizações ─────────────────────────────────────
    def _build_updates_section(self):
        self._add_section_label(self._layout, "ÚLTIMAS ATUALIZAÇÕES")
        self._layout.addSpacing(14)

        from src.core.changelog_data import CHANGELOG
        
        # Filtramos para mostrar apenas versões finais (sem hífen) e limitamos às últimas 4
        versions = [v for v in CHANGELOG if "-" not in v["version"]][:4]

        if not versions:
            fallback = QLabel("Nenhuma atualização registrada.")
            fallback.setStyleSheet("font-size: 12px; color: #888; background: transparent;")
            self._layout.addWidget(fallback)
            return

        # Mapeamento para exibição amigável
        TYPE_MAP = {
            "feat": ("⊕", "#FF8050", "Novidade"),
            "fix":  ("◈", "#60a5fa", "Correção"),
            "perf": ("⚡", "#BB88FF", "Performance"),
            "chore":("↺", "#888888", "Ajuste"),
        }

        for i, ver in enumerate(versions):
            card = QFrame()
            card.setObjectName("card_flat")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(16, 14, 16, 14)
            card_layout.setSpacing(6)

            # Header: version badge
            header = QHBoxLayout()
            header.setSpacing(10)

            ver_lbl = QLabel(f"v{ver['version']}")
            ver_lbl.setStyleSheet(
                f"font-size: 13px; font-weight: 700; "
                f"{'color: #BB88FF;' if i == 0 else ''} background: transparent;"
            )
            header.addWidget(ver_lbl)

            if i == 0:
                badge = QLabel("  última versão estável  ")
                badge.setStyleSheet(
                    "font-size: 10px; font-weight: 600; color: #BB88FF;"
                    " border: 1px solid #BB88FF; border-radius: 8px;"
                    " padding: 1px 6px; background: transparent;"
                )
                header.addWidget(badge)

            date_lbl = QLabel(ver.get("date", ""))
            date_lbl.setStyleSheet("font-size: 11px; color: #999; background: transparent;")
            header.addStretch()
            header.addWidget(date_lbl)
            card_layout.addLayout(header)

            sep = QFrame()
            sep.setFrameShape(QFrame.HLine)
            sep.setFixedHeight(1)
            sep.setStyleSheet("background: #e0e0e0; border: none;")
            card_layout.addWidget(sep)

            # Entries
            for entry in ver["entries"]:
                # Suporta tanto o formato antigo (4 itens) quanto o novo (2 itens)
                if len(entry) >= 2:
                    etype, etext = entry[0], entry[1]
                    icon, color, label = TYPE_MAP.get(etype, ("·", "#888", "Info"))
                else:
                    continue

                row = QHBoxLayout()
                row.setSpacing(8)
                row.setContentsMargins(4, 0, 0, 0)

                icon_lbl = QLabel(icon)
                icon_lbl.setFixedWidth(16)
                icon_lbl.setStyleSheet(f"font-size: 12px; color: {color}; background: transparent;")
                row.addWidget(icon_lbl)

                # Texto formatado: "Tipo: Mensagem"
                full_text = f"<b>{label}:</b> {etext}"
                text_lbl = QLabel(full_text)
                text_lbl.setWordWrap(True)
                text_lbl.setStyleSheet(
                    f"font-size: 12px; {'color: #777;' if i > 0 else ''} background: transparent;"
                )
                row.addWidget(text_lbl, 1)
                card_layout.addLayout(row)

            self._layout.addWidget(card)
            self._layout.addSpacing(8)

    # ── Seção 3: Colaboradores ────────────────────────────────────────────
    def _build_contributors_section(self):
        self._add_section_label(self._layout, "COLABORADORES")
        self._layout.addSpacing(14)

        intro = QLabel(
            "O SIC é fruto de uma colaboração entre pessoas com perspectivas complementares — "
            "quem conhece profundamente as regras de negócio e quem sabe como transformá-las "
            "em software escalável."
        )
        intro.setWordWrap(True)
        intro.setStyleSheet("font-size: 12px; color: #666; background: transparent;")
        self._layout.addWidget(intro)
        self._layout.addSpacing(14)

        grid = QGridLayout()
        grid.setSpacing(20)
        for col, contributor in enumerate(CONTRIBUTORS):
            grid.addWidget(_ContributorCard(contributor), 0, col)
        self._layout.addLayout(grid)

    # ── Helper ────────────────────────────────────────────────────────────
    @staticmethod
    def _add_section_label(layout: QVBoxLayout, text: str):
        lbl = QLabel(text)
        lbl.setStyleSheet(
            "font-size: 11px; font-weight: 700; color: #555; letter-spacing: 1.5px;"
        )
        layout.addWidget(lbl)
