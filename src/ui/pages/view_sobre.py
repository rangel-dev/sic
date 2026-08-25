"""Módulo Sobre — projeto, últimas atualizações (git local) e colaboradores."""
import os
from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
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
from src.core.version import VERSION, APP_NAME, GITHUB_REPO
from src.core.changelog_data import CONTRIBUTORS
from src.ui.components.base_widgets import Divider, SectionHeader

# Quantas entradas de um card de versão ficam visíveis antes do "Ler mais".
_CHANGELOG_VISIBLE_ENTRIES = 4


# ── Ler mais / Ler menos ────────────────────────────────────────────────────
class _ReadMoreToggle(QLabel):
    """Clicável que mostra/esconde `target`, alternando o próprio texto."""

    def __init__(self, target: QWidget, parent=None):
        super().__init__("Ler mais ▾", parent)
        self._target = target
        target.setVisible(False)
        self.setCursor(Qt.PointingHandCursor)
        self.setObjectName("label_accent")
        self.setStyleSheet("font-size: 11px; font-weight: 600;")

    def mousePressEvent(self, event):
        expanded = not self._target.isVisible()
        self._target.setVisible(expanded)
        self.setText("Ler menos ▴" if expanded else "Ler mais ▾")
        super().mousePressEvent(event)


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
        role_lbl.setObjectName("label_muted")
        role_lbl.setStyleSheet("font-size: 11px;")
        name_block.addWidget(role_lbl)
        top.addLayout(name_block, 1)
        layout.addLayout(top)

        bio_lbl = QLabel(data["bio"])
        bio_lbl.setWordWrap(True)
        bio_lbl.setObjectName("label_muted")
        bio_lbl.setStyleSheet("font-size: 12px;")
        layout.addWidget(bio_lbl)

        if data.get("legacy"):
            legacy_lbl = QLabel(f"◂ {data['legacy']}")
            legacy_lbl.setObjectName("label_hint")
            legacy_lbl.setStyleSheet("font-size: 10px;")
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
        self._layout.addSpacing(28)
        self._layout.addWidget(Divider())
        self._layout.addSpacing(14)
        self._build_footer()
        self._layout.addStretch()

    # ── Rodapé ───────────────────────────────────────────────────────────
    def _build_footer(self):
        link_lbl = QLabel(
            f'Código-fonte e suporte: '
            f'<a href="https://github.com/{GITHUB_REPO}">github.com/{GITHUB_REPO}</a>'
        )
        link_lbl.setObjectName("label_muted")
        link_lbl.setStyleSheet("font-size: 11px;")
        link_lbl.setOpenExternalLinks(True)
        self._layout.addWidget(link_lbl)

    # ── Seção 1: Sobre o Projeto ──────────────────────────────────────────
    def _build_project_section(self):
        self._add_section_label(self._layout, "SOBRE O PROJETO")
        self._layout.addSpacing(14)

        # Hero: logo + (nome + badge de versão + copyright)
        hero_row = QHBoxLayout()
        hero_row.setSpacing(14)

        logo_lbl = self._build_logo_label()
        if logo_lbl is not None:
            hero_row.addWidget(logo_lbl)

        hero_text = QVBoxLayout()
        hero_text.setSpacing(4)

        name_row = QHBoxLayout()
        name_row.setSpacing(12)
        app_lbl = QLabel(APP_NAME)
        app_lbl.setStyleSheet("font-size: 20px; font-weight: 800; background: transparent;")
        name_row.addWidget(app_lbl)
        ver_badge = QLabel(f"  v{VERSION}  ")
        ver_badge.setObjectName("badge_accent")
        name_row.addWidget(ver_badge)
        name_row.addStretch()
        hero_text.addLayout(name_row)

        copyright_lbl = QLabel(f"© {date.today().year} RangelDev. Todos os direitos reservados.")
        copyright_lbl.setObjectName("label_muted")
        hero_text.addWidget(copyright_lbl)

        hero_row.addLayout(hero_text, 1)
        self._layout.addLayout(hero_row)
        self._layout.addSpacing(14)

        # Description
        desc = QLabel(
            "O SIC centraliza e automatiza as operações de precificação e catálogo "
            "para o Salesforce Commerce Cloud. Ele substitui processos manuais "
            "dispersos em planilhas por um fluxo estruturado, auditado e rastreável."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 13px;")
        self._layout.addWidget(desc)
        self._layout.addSpacing(20)

        # How it works — module cards in a horizontal strip
        modules = [
            ("⊗", "Exportador",  "Gera Pricebook XML e/ou Catálogo XML a partir de uma única grade Excel."),
            ("✓", "Auditor",     "Valida consistência de preços, categorias e regras de negócio em lote."),
            ("≡", "Cadastro",    "Valida kits e pontuação cruzando XMLs Salesforce com planilhas de controle."),
            ("✦", "Cupons",      "Consolida listas de cupons de múltiplas origens e gera o XML pronto para o SFCC."),
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
            icon_lbl.setObjectName("label_accent")
            icon_lbl.setStyleSheet("font-size: 14px;")
            top_row.addWidget(icon_lbl)
            name_lbl = QLabel(name)
            name_lbl.setStyleSheet("font-size: 12px; font-weight: 700; background: transparent;")
            top_row.addWidget(name_lbl)
            top_row.addStretch()
            card_layout.addLayout(top_row)

            tip_lbl = QLabel(tip)
            tip_lbl.setWordWrap(True)
            tip_lbl.setObjectName("label_muted")
            tip_lbl.setStyleSheet("font-size: 11px;")
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
        compat.setObjectName("label_muted")
        compat.setStyleSheet("font-size: 11px;")
        self._layout.addWidget(compat)

    def _build_logo_label(self) -> "QLabel | None":
        """QLabel de 64×64 com o ícone do app. Retorna None (não crasha) se o
        asset não existir ou o pixmap vier inválido — degradação graciosa."""
        from src.main_app import resource_path

        icon_path = resource_path("assets/icons/app_icon.png")
        if not os.path.exists(icon_path):
            return None

        pixmap = QPixmap(icon_path)
        if pixmap.isNull():
            return None

        logo_lbl = QLabel()
        logo_lbl.setFixedSize(64, 64)
        logo_lbl.setPixmap(
            pixmap.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )
        return logo_lbl

    # ── Seção 2: Últimas Atualizações ─────────────────────────────────────
    def _build_updates_section(self):
        self._add_section_label(self._layout, "ÚLTIMAS ATUALIZAÇÕES")
        self._layout.addSpacing(14)

        from src.core.changelog_data import CHANGELOG
        
        # Filtramos para mostrar apenas versões finais (sem hífen) e limitamos às últimas 4
        versions = [v for v in CHANGELOG if "-" not in v["version"]][:4]

        if not versions:
            fallback = QLabel("Nenhuma atualização registrada.")
            fallback.setObjectName("label_muted")
            fallback.setStyleSheet("font-size: 12px;")
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
            ver_lbl.setStyleSheet("font-size: 13px; font-weight: 700;")
            if i == 0:
                ver_lbl.setObjectName("label_accent")
            header.addWidget(ver_lbl)

            if i == 0:
                badge = QLabel("  última versão estável  ")
                badge.setObjectName("badge_ok")
                header.addWidget(badge)

            date_lbl = QLabel(ver.get("date", ""))
            date_lbl.setObjectName("label_muted")
            date_lbl.setStyleSheet("font-size: 11px;")
            header.addStretch()
            header.addWidget(date_lbl)
            card_layout.addLayout(header)

            card_layout.addWidget(Divider())

            # Entries — mostra só as primeiras; o resto fica atrás de "Ler mais"
            entries = [e for e in ver["entries"] if len(e) >= 2]
            visible_entries = entries[:_CHANGELOG_VISIBLE_ENTRIES]
            hidden_entries = entries[_CHANGELOG_VISIBLE_ENTRIES:]

            for entry in visible_entries:
                self._add_entry_row(card_layout, entry, dim=(i > 0), type_map=TYPE_MAP)

            if hidden_entries:
                extra = QWidget()
                extra_layout = QVBoxLayout(extra)
                extra_layout.setContentsMargins(0, 0, 0, 0)
                extra_layout.setSpacing(6)
                for entry in hidden_entries:
                    self._add_entry_row(extra_layout, entry, dim=(i > 0), type_map=TYPE_MAP)
                card_layout.addWidget(extra)

                toggle_row = QHBoxLayout()
                toggle_row.addWidget(_ReadMoreToggle(extra))
                toggle_row.addStretch()
                card_layout.addLayout(toggle_row)

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
        intro.setStyleSheet("font-size: 12px;")
        self._layout.addWidget(intro)
        self._layout.addSpacing(14)

        grid = QGridLayout()
        grid.setSpacing(20)
        for i, contributor in enumerate(CONTRIBUTORS):
            row, col = divmod(i, 2)
            grid.addWidget(_ContributorCard(contributor), row, col)
        self._layout.addLayout(grid)

    # ── Helper ────────────────────────────────────────────────────────────
    @staticmethod
    def _add_section_label(layout: QVBoxLayout, text: str):
        lbl = QLabel(text)
        lbl.setObjectName("label_muted")
        lbl.setStyleSheet("font-size: 11px; font-weight: 700; letter-spacing: 1.5px;")
        layout.addWidget(lbl)

    @staticmethod
    def _add_entry_row(layout: QVBoxLayout, entry: tuple, dim: bool, type_map: dict):
        etype, etext = entry[0], entry[1]
        icon, color, label = type_map.get(etype, ("·", "#888", "Info"))

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
        if dim:
            text_lbl.setObjectName("label_muted")
        text_lbl.setStyleSheet("font-size: 12px;")
        row.addWidget(text_lbl, 1)
        layout.addLayout(row)
