"""
Checklist da Ativação — painel lateral (orelha) com o passo a passo de uma
ativação de Grade. Fica ao lado das telas para a pessoa acompanhar enquanto
trabalha no Exportador, no Auditor ou no Salesforce.

Só interface: as marcações ficam salvas no QSettings deste computador.
"""
from PySide6.QtCore import Qt, QSettings, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

# Passo a passo da ativação de uma Grade, na ordem em que é executado.
ATIVACAO_STEPS = [
    "Baixar o XML de catálogo da loja que vai ser processada.",
    "Baixar o anexo da Grade no Runrun.it.",
    "Carregar os 2 arquivos no módulo Exportador (uma marca por vez).",
    "Salvar os 3 arquivos gerados: Pricebook, Catalog e Inventory.",
    "Carregar os 3 arquivos no Salesforce.",
    "Importar os 3 arquivos.",
    "Rodar o Job de Categorization: Natura ou Avon + CBBRAZIL/Minha Loja.",
    "Rodar o Auditor.",
    "Replicar catálogo Natura/Avon + CBBRAZIL/Minha Loja + Pricebook.",
    "Executar o rebuild.",
    "Rodar o Auditor em PRD.",
]
_KEY_DONE = "checklist_ativacao/concluidos"
_KEY_OPEN = "checklist_ativacao/aberto"
PANEL_WIDTH = 320


def _settings() -> QSettings:
    return QSettings("SIC", "SIC_Suite")


def is_panel_open() -> bool:
    return str(_settings().value(_KEY_OPEN, "false")).lower() == "true"


def set_panel_open(is_open: bool):
    _settings().setValue(_KEY_OPEN, "true" if is_open else "false")


class _StepLabel(QLabel):
    """Texto do passo — clicar nele marca/desmarca o checkbox ao lado."""

    def __init__(self, text: str, checkbox: QCheckBox):
        super().__init__(text)
        self._checkbox = checkbox
        self.setWordWrap(True)
        self.setCursor(Qt.PointingHandCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._checkbox.toggle()
        super().mousePressEvent(event)


class ChecklistAtivacaoPanel(QFrame):
    """Painel lateral com os passos da ativação.

    Emite `progress_changed(concluidos, total)` a cada marcação e
    `close_requested` quando o × do cabeçalho é clicado."""

    progress_changed = Signal(int, int)
    close_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("checklist_panel")
        self.setFixedWidth(PANEL_WIDTH)
        self._checks: list[QCheckBox] = []
        self._labels: list[_StepLabel] = []
        self._setup_ui()
        self.refresh_theme()

    # ── Build ─────────────────────────────────────────────────────────────
    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 14, 18)
        root.setSpacing(6)

        header = QHBoxLayout()
        title = QLabel("PASSO A PASSO DA ATIVAÇÃO")
        title.setObjectName("checklist_title")
        header.addWidget(title)
        header.addStretch()

        btn_close = QPushButton("×")
        btn_close.setObjectName("checklist_close")
        btn_close.setFixedSize(28, 28)
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.setToolTip("Fechar checklist")
        btn_close.clicked.connect(self.close_requested.emit)
        header.addWidget(btn_close)
        root.addLayout(header)

        self._progress_lbl = QLabel()
        self._progress_lbl.setObjectName("checklist_progress")
        root.addWidget(self._progress_lbl)
        root.addSpacing(8)

        scroll = QScrollArea()
        scroll.setObjectName("checklist_scroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        body = QWidget()
        body.setObjectName("checklist_body")
        grid = QGridLayout(body)
        grid.setContentsMargins(0, 0, 6, 0)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(12)
        grid.setColumnStretch(2, 1)

        done = self._load_done()
        for i, text in enumerate(ATIVACAO_STEPS):
            num_lbl = QLabel(str(i + 1))
            num_lbl.setObjectName("checklist_num")
            num_lbl.setFixedWidth(20)
            num_lbl.setAlignment(Qt.AlignRight | Qt.AlignTop)
            grid.addWidget(num_lbl, i, 0, Qt.AlignTop)

            chk = QCheckBox()
            chk.setCursor(Qt.PointingHandCursor)
            chk.setChecked(i in done)
            chk.toggled.connect(self._on_toggled)
            grid.addWidget(chk, i, 1, Qt.AlignTop)

            lbl = _StepLabel(text, chk)
            grid.addWidget(lbl, i, 2)

            self._checks.append(chk)
            self._labels.append(lbl)

        grid.setRowStretch(len(ATIVACAO_STEPS), 1)
        scroll.setWidget(body)
        root.addWidget(scroll, 1)

        btn_reset = QPushButton("Reiniciar checklist ↺")
        btn_reset.setObjectName("btn_ghost")
        btn_reset.setCursor(Qt.PointingHandCursor)
        btn_reset.clicked.connect(self.reset)
        root.addWidget(btn_reset)

    # ── Estado ────────────────────────────────────────────────────────────
    def _load_done(self) -> set:
        raw = _settings().value(_KEY_DONE, "")
        return {int(x) for x in str(raw).split(",") if x.strip().isdigit()}

    def _save_done(self):
        done = [str(i) for i, chk in enumerate(self._checks) if chk.isChecked()]
        _settings().setValue(_KEY_DONE, ",".join(done))

    def _on_toggled(self, _checked: bool):
        self._save_done()
        self._refresh_steps()

    def reset(self):
        for chk in self._checks:
            chk.blockSignals(True)
            chk.setChecked(False)
            chk.blockSignals(False)
        self._save_done()
        self._refresh_steps()

    def progress(self) -> tuple[int, int]:
        return sum(chk.isChecked() for chk in self._checks), len(self._checks)

    def _refresh_steps(self):
        """Risca os passos concluídos e destaca o próximo passo pendente."""
        done_count, total = self.progress()
        self._progress_lbl.setText(f"{done_count} de {total} concluídas")

        next_marked = False
        for chk, lbl in zip(self._checks, self._labels):
            font = lbl.font()
            font.setStrikeOut(chk.isChecked())
            lbl.setFont(font)
            if chk.isChecked():
                style = "color: #888;"
            elif not next_marked:
                style = "font-weight: 700; color: #BB88FF;"
                next_marked = True
            else:
                style = ""
            lbl.setStyleSheet(f"font-size: 13px; background: transparent; {style}")

        self.progress_changed.emit(done_count, total)

    # ── Tema ──────────────────────────────────────────────────────────────
    def refresh_theme(self):
        # O indicador do checkbox é estilizado aqui porque o tema claro não
        # define QCheckBox, e qualquer QSS que alcance o widget faria o
        # quadradinho sumir.
        dark = _settings().value("theme", "light") == "dark"
        if dark:
            bg, border, box_bg, box_border, muted = "#1e293b", "#334155", "#334155", "#475569", "#94a3b8"
        else:
            bg, border, box_bg, box_border, muted = "#ffffff", "#e5e7eb", "#ffffff", "#c4c9d1", "#555"

        self.setStyleSheet(f"""
            #checklist_panel {{ background-color: {bg}; border: none; border-left: 1px solid {border}; }}
            #checklist_panel QLabel, #checklist_panel QCheckBox,
            #checklist_scroll, #checklist_body {{ background: transparent; }}
            #checklist_title {{ font-size: 11px; font-weight: 700; color: {muted}; letter-spacing: 1.5px; }}
            #checklist_progress {{ font-size: 12px; font-weight: 700; color: #4CAF50; }}
            #checklist_num {{ font-size: 13px; color: #888; }}
            #checklist_close {{ background: transparent; border: none; color: {muted}; font-size: 20px; padding: 0px; }}
            #checklist_close:hover {{ color: #BB88FF; }}
            #checklist_panel QCheckBox::indicator {{
                width: 15px; height: 15px; border-radius: 4px;
                border: 1px solid {box_border}; background-color: {box_bg};
            }}
            #checklist_panel QCheckBox::indicator:checked {{
                background-color: #4CAF50; border-color: #4CAF50;
            }}
        """)
        self._refresh_steps()
