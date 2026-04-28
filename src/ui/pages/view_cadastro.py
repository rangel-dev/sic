"""
Cadastro View — container with two sub-modules:
  • Validação de Kits   (CadastroKitsView)
  • Auditor de Pontuação (CadastroPontuacaoView)
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from src.ui.components.base_widgets import Divider, SectionHeader
from src.ui.pages.view_cadastro_kits import CadastroKitsView
from src.ui.pages.view_cadastro_pontuacao import CadastroPontuacaoView


class CadastroView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(SectionHeader(
            "≡  Cadastro",
            "Validação de Kits e Auditoria de Pontuação BR/BIO"
        ))
        root.addWidget(Divider())

        # ── Sub-tab bar ───────────────────────────────────────────────────
        sub_bar_container = QWidget()
        sub_bar_container.setObjectName("sub_tab_bar")
        sub_bar_layout = QHBoxLayout(sub_bar_container)
        sub_bar_layout.setContentsMargins(28, 0, 28, 0)
        sub_bar_layout.setSpacing(0)

        self._btn_kits = QPushButton("  Validação de Kits")
        self._btn_kits.setObjectName("tab_button")
        self._btn_kits.setCheckable(True)
        self._btn_kits.setChecked(True)
        self._btn_kits.setFixedHeight(40)
        self._btn_kits.setCursor(Qt.PointingHandCursor)
        self._btn_kits.clicked.connect(lambda: self._switch(0))
        sub_bar_layout.addWidget(self._btn_kits)

        self._btn_pontuacao = QPushButton("  Auditor de Pontuação")
        self._btn_pontuacao.setObjectName("tab_button")
        self._btn_pontuacao.setCheckable(True)
        self._btn_pontuacao.setFixedHeight(40)
        self._btn_pontuacao.setCursor(Qt.PointingHandCursor)
        self._btn_pontuacao.clicked.connect(lambda: self._switch(1))
        sub_bar_layout.addWidget(self._btn_pontuacao)

        sub_bar_layout.addStretch()
        root.addWidget(sub_bar_container)
        root.addWidget(Divider())

        # ── Sub-views ─────────────────────────────────────────────────────
        self._stack = QStackedWidget()
        self._kits_view      = CadastroKitsView(self)
        self._pontuacao_view = CadastroPontuacaoView(self)
        self._stack.addWidget(self._kits_view)
        self._stack.addWidget(self._pontuacao_view)
        root.addWidget(self._stack)

        self._switch(0)

    def _switch(self, index: int):
        self._stack.setCurrentIndex(index)
        self._btn_kits.setChecked(index == 0)
        self._btn_pontuacao.setChecked(index == 1)

    # Forward show_status calls from sub-views to the main window
    def show_status(self, message: str):
        if p := self.parent():
            if hasattr(p, "show_status"):
                p.show_status(message)
