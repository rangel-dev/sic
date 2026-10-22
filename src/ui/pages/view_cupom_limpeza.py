"""
Cupons → Limpeza de Campanhas (BRD-015).

Fluxo: 3 exports (tipo pelo namespace, loja pela impressão digital) → simulação → revisão
→ confirmação explícita → XMLs de exclusão e rollback. O SIC só
gera os arquivos; quem importa no Business Manager é o operador.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import QSettings, Qt, QUrl
from PySide6.QtGui import QDesktopServices, QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFileDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.core import limpeza_engine as le
from src.core.history_engine import HistoryEngine
from src.ui.components.base_widgets import Divider, SectionHeader, StatPill
from src.workers.worker_limpeza import LimpezaExportWorker, LimpezaSimulationWorker

_KEY_TERMS = "limpeza/lista_protegida"
_KEY_GRACE = "limpeza/carencia_dias"

_STATUS_COLORS = {
    le.PROTEGIDO: "#28a745",
    le.ELEGIVEL: "#d93025",
    le.REVISAR: "#2b8fd6",
}


class _DropArea(QFrame):
    """Área de arrastar/clicar para os 3 exports. Só repassa os caminhos —
    quem decide o tipo de cada arquivo é o namespace (le.classify_files)."""

    def __init__(self, on_files, parent=None):
        super().__init__(parent)
        self._on_files = on_files
        self.setObjectName("card_flat")
        self.setAcceptDrops(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(84)
        self.setStyleSheet("QFrame#card_flat { border: 1px dashed rgba(128,128,128,0.55); }")
        lay = QVBoxLayout(self)
        lbl = QLabel("⬇  Arraste aqui os 3 exports do Business Manager, ou clique para escolher\n"
                     "(promoções e campanhas, cupons e customer groups — em qualquer ordem e com qualquer nome)")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setObjectName("label_muted")
        lbl.setStyleSheet("background: transparent;")
        lay.addWidget(lbl)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            paths, _ = QFileDialog.getOpenFileNames(self, "Escolher exports do SFCC", "", "XML (*.xml)")
            if paths:
                self._on_files(paths)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        paths = [u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()]
        if paths:
            self._on_files(paths)


class CupomLimpezaView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._settings = QSettings("SIC", "SIC_Suite")
        self._files: dict[str, str] = {}
        self._engine: Optional[le.LimpezaEngine] = None
        self._result: Optional[le.SimulationResult] = None
        self._sim_worker: Optional[LimpezaSimulationWorker] = None
        self._exp_worker: Optional[LimpezaExportWorker] = None
        self._setup_ui()
        self._refresh_files()
        self._show_store(None)

    # ── Construção da UI ──────────────────────────────────────────────────
    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(SectionHeader(
            "✦  Limpeza de Campanhas",
            "Encontre campanhas, promoções, cupons e customer groups vencidos ou sem uso e gere os "
            "arquivos de limpeza — sempre com simulação antes, carência e rollback.",
        ))
        outer.addWidget(Divider())

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        outer.addWidget(scroll)
        container = QWidget()
        scroll.setWidget(container)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(20)

        # ── 1. Loja e arquivos ─────────────────────────────────────────────
        box = QGroupBox("1. Loja e arquivos")
        bl = QVBoxLayout(box)
        bl.setContentsMargins(16, 18, 16, 14)
        bl.setSpacing(10)

        # A loja nunca é escolhida: é deduzida dos arquivos (regra 3 — incidente do Chile)
        loja_row = QHBoxLayout()
        lbl_loja = QLabel("Loja")
        lbl_loja.setObjectName("label_section")
        loja_row.addWidget(lbl_loja)
        self._lbl_store = QLabel()
        self._lbl_store.setTextFormat(Qt.RichText)
        loja_row.addWidget(self._lbl_store, 1)
        bl.addLayout(loja_row)

        bl.addWidget(_DropArea(self._add_files))

        self._file_rows: dict[str, QLabel] = {}
        for kind in (le.KIND_PROMOTIONS, le.KIND_COUPONS, le.KIND_CUSTOMER_GROUPS):
            row = QLabel()
            row.setTextFormat(Qt.RichText)
            self._file_rows[kind] = row
            bl.addWidget(row)

        self._lbl_rejected = QLabel()
        self._lbl_rejected.setWordWrap(True)
        self._lbl_rejected.setStyleSheet("color:#f2994a; font-size:12px; background:transparent;")
        self._lbl_rejected.hide()
        bl.addWidget(self._lbl_rejected)

        btn_clear_files = QPushButton("Limpar arquivos")
        btn_clear_files.setObjectName("btn_ghost")
        btn_clear_files.clicked.connect(self._clear_files)
        bl.addWidget(btn_clear_files, 0, Qt.AlignLeft)
        layout.addWidget(box)

        # ── 2. Regras ──────────────────────────────────────────────────────
        prot = QGroupBox("2. Regras")
        pl = QVBoxLayout(prot)
        pl.setContentsMargins(16, 18, 16, 14)
        pl.setSpacing(8)

        lbl_grace = QLabel("Carência de campanhas vencidas  <span style='color:#888;font-weight:400'>"
                           "(campanha vencida há menos dias que isso continua protegida, com tudo o que "
                           "está ligado a ela; itens sem campanha não têm carência)</span>")
        lbl_grace.setWordWrap(True)
        lbl_grace.setObjectName("label_section")
        pl.addWidget(lbl_grace)
        grace_row = QHBoxLayout()
        saved_grace = int(self._settings.value(_KEY_GRACE, le.GRACE_DAYS))
        saved_grace = min(max(saved_grace, le.GRACE_MIN_DAYS), le.GRACE_MAX_DAYS)
        self._sld_grace = QSlider(Qt.Horizontal)
        self._sld_grace.setRange(le.GRACE_MIN_DAYS, le.GRACE_MAX_DAYS)
        self._sld_grace.setValue(saved_grace)
        self._spn_grace = QSpinBox()
        self._spn_grace.setRange(le.GRACE_MIN_DAYS, le.GRACE_MAX_DAYS)
        self._spn_grace.setSuffix(" dias")
        self._spn_grace.setValue(saved_grace)
        self._spn_grace.setFixedWidth(110)
        self._sld_grace.valueChanged.connect(self._spn_grace.setValue)
        self._spn_grace.valueChanged.connect(self._sld_grace.setValue)
        self._spn_grace.valueChanged.connect(self._invalidate)
        grace_row.addWidget(self._sld_grace, 1)
        grace_row.addWidget(self._spn_grace)
        pl.addLayout(grace_row)

        lbl_terms = QLabel("Lista protegida  <span style='color:#888;font-weight:400'>(opcional — "
                           "itens cujo ID <b>contém</b> um destes termos nunca são apagados; "
                           "separe por vírgula)</span>")
        lbl_terms.setObjectName("label_section")
        lbl_terms.setWordWrap(True)
        pl.addWidget(lbl_terms)
        self._txt_terms = QLineEdit(str(self._settings.value(
            _KEY_TERMS, ", ".join(le.DEFAULT_PROTECTED_TERMS))))
        self._txt_terms.setPlaceholderText("Nenhum termo — além dos grupos padrão do SFCC "
                                           "(Everyone, Registered, Unregistered) e de quem tem DONT_REMOVE no nome")
        self._txt_terms.setFixedHeight(34)
        self._txt_terms.textChanged.connect(self._invalidate)
        pl.addWidget(self._txt_terms)
        layout.addWidget(prot)

        # ── Ações ─────────────────────────────────────────────────────────
        actions = QHBoxLayout()
        self._btn_simulate = QPushButton("▶  Simular")
        self._btn_simulate.setObjectName("btn_primary")
        self._btn_simulate.setFixedWidth(160)
        self._btn_simulate.clicked.connect(self._simulate)
        actions.addWidget(self._btn_simulate)
        note = QLabel("A simulação não gera nenhum XML.")
        note.setObjectName("label_muted")
        actions.addWidget(note)
        actions.addStretch()
        layout.addLayout(actions)

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.hide()
        layout.addWidget(self._progress)
        self._status = QLabel()
        self._status.setObjectName("label_muted")
        self._status.hide()
        layout.addWidget(self._status)

        # ── Resultado ──────────────────────────────────────────────────────
        self._result_box = QWidget()
        rl = QVBoxLayout(self._result_box)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(12)

        title = QLabel("3. Resultado da simulação")
        title.setObjectName("label_section")
        title.setStyleSheet("color:#0071e3; font-weight:700;")
        rl.addWidget(title)

        self._lbl_banner = QLabel()
        self._lbl_banner.setWordWrap(True)
        self._lbl_banner.setTextFormat(Qt.RichText)
        rl.addWidget(self._lbl_banner)

        pills = QHBoxLayout()
        self._pills = {s: StatPill(s, "—", c) for s, c in _STATUS_COLORS.items()}
        for p in self._pills.values():
            pills.addWidget(p)
        pills.addStretch()
        rl.addLayout(pills)

        self._tbl_summary = QTableWidget(len(le.ENTITIES), len(le.STATUSES) + 1)
        self._tbl_summary.setHorizontalHeaderLabels(["Total", *le.STATUSES])
        self._tbl_summary.setVerticalHeaderLabels([le.ENTITY_LABELS[e] for e in le.ENTITIES])
        self._tbl_summary.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._tbl_summary.setSelectionMode(QAbstractItemView.NoSelection)
        self._tbl_summary.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._tbl_summary.setFixedHeight(34 + 32 * len(le.ENTITIES))
        rl.addWidget(self._tbl_summary)

        filt = QHBoxLayout()
        lbl_f = QLabel("Itens que não ficam protegidos")
        lbl_f.setObjectName("label_section")
        filt.addWidget(lbl_f)
        filt.addStretch()
        self._cmb_filter = QComboBox()
        self._cmb_filter.addItem("Todos (exceto Protegido)", "")
        for s in le.STATUSES:
            self._cmb_filter.addItem(s, s)
        self._cmb_filter.currentIndexChanged.connect(self._fill_details)
        filt.addWidget(self._cmb_filter)
        rl.addLayout(filt)

        self._tbl_items = QTableWidget(0, 4)
        self._tbl_items.setHorizontalHeaderLabels(["Entidade", "ID", "Status", "Motivo"])
        self._tbl_items.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._tbl_items.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._tbl_items.verticalHeader().setVisible(False)
        hh = self._tbl_items.horizontalHeader()
        for col, mode in ((0, QHeaderView.ResizeToContents), (1, QHeaderView.Interactive),
                          (2, QHeaderView.ResizeToContents), (3, QHeaderView.Stretch)):
            hh.setSectionResizeMode(col, mode)
        self._tbl_items.setColumnWidth(1, 260)
        self._tbl_items.setMinimumHeight(320)
        rl.addWidget(self._tbl_items)

        out = QHBoxLayout()
        self._btn_sheet = QPushButton("📊  Salvar planilha da simulação")
        self._btn_sheet.setObjectName("btn_secondary")
        self._btn_sheet.clicked.connect(self._save_sheet)
        out.addWidget(self._btn_sheet)
        self._btn_export = QPushButton("⚠  Gerar arquivos de limpeza…")
        self._btn_export.setObjectName("btn_primary")
        self._btn_export.clicked.connect(self._export)
        out.addWidget(self._btn_export)
        out.addStretch()
        rl.addLayout(out)

        self._result_box.hide()
        layout.addWidget(self._result_box)
        layout.addStretch()

    # ── Arquivos ──────────────────────────────────────────────────────────
    def _add_files(self, paths: list[str]):
        sel = le.classify_files(paths, self._files)
        self._files = sel.paths
        if sel.rejected:
            self._lbl_rejected.setText("⚠  Recusado(s): " + "; ".join(
                f"{Path(p).name} — {why}" for p, why in sel.rejected))
            self._lbl_rejected.show()
        else:
            self._lbl_rejected.hide()
        self._invalidate()
        self._refresh_files()

    def _clear_files(self):
        self._files = {}
        self._lbl_rejected.hide()
        self._invalidate()
        self._refresh_files()

    def _refresh_files(self):
        for kind, row in self._file_rows.items():
            label = le.KIND_LABELS[kind]
            if kind in self._files:
                row.setText(f"<span style='color:#28a745'>✓</span>&nbsp; <b>{label}</b> — "
                            f"{Path(self._files[kind]).name}")
            else:
                row.setText(f"<span style='color:#888'>○&nbsp; {label} — faltando</span>")

    # ── Simulação ─────────────────────────────────────────────────────────
    def _terms(self) -> list[str]:
        return [t.strip() for t in self._txt_terms.text().split(",") if t.strip()]

    def _invalidate(self, *_):
        """Qualquer mudança de entrada invalida a simulação anterior."""
        self._result = None
        self._engine = None
        self._result_box.hide()
        self._show_store(None)

    def _show_store(self, res: Optional[le.SimulationResult]):
        if res is None:
            self._lbl_store.setText("<span style='color:#888'>identificada automaticamente pelos arquivos "
                                    "ao simular — não dá para escolher</span>")
        elif res.detection.ok:
            self._lbl_store.setText(f"<span style='color:#28a745'>✓</span>&nbsp; <b>{res.store.name}</b> "
                                    f"<span style='color:#888'>— identificada pelos arquivos</span>")
        else:
            self._lbl_store.setText("<span style='color:#d93025'><b>⛔ Loja não confirmada</b></span>")

    def _simulate(self):
        missing = [le.KIND_LABELS[k] for k in self._file_rows if k not in self._files]
        if missing:
            QMessageBox.warning(self, "Limpeza de Campanhas",
                                "Faltam os arquivos: <b>" + ", ".join(missing) + "</b>.")
            return
        self._settings.setValue(_KEY_TERMS, ", ".join(self._terms()))
        self._settings.setValue(_KEY_GRACE, self._spn_grace.value())
        self._set_busy(True)
        self._sim_worker = LimpezaSimulationWorker(
            self._files, self._terms(), self._spn_grace.value(), self)
        self._sim_worker.progress.connect(self._on_progress)
        self._sim_worker.finished.connect(self._on_simulated)
        self._sim_worker.error_msg.connect(self._on_error)
        self._sim_worker.start()

    def _set_busy(self, busy: bool):
        self._btn_simulate.setEnabled(not busy)
        self._btn_export.setEnabled(not busy and bool(self._result and self._result.can_export))
        self._btn_sheet.setEnabled(not busy and self._result is not None)
        self._progress.setVisible(busy)
        self._status.setVisible(busy)
        if busy:
            self._progress.setValue(0)

    def _on_progress(self, pct: int, msg: str):
        self._progress.setValue(pct)
        self._status.setText(msg)

    def _on_error(self, msg: str):
        self._set_busy(False)
        QMessageBox.critical(self, "Erro — Limpeza de Campanhas", msg)

    def _on_simulated(self, engine: le.LimpezaEngine, res: le.SimulationResult):
        self._engine, self._result = engine, res
        self._set_busy(False)
        self._show_result(res)
        HistoryEngine.add_entry(
            "Limpeza de Campanhas", res.store_name,
            f"Simulação — {res.affected_total} itens para limpar.",
            self._counts_text(res),
        )

    def _show_result(self, res: le.SimulationResult):
        self._show_store(res)
        if res.blocked_msg:
            banner = f"<span style='color:#d93025'><b>⛔ Bloqueado:</b> {res.blocked_msg}</span>"
        else:
            parts = []
            if res.affected_total == 0:
                parts.append("<b>Nada para limpar nesta rodada.</b>")
            if res.volume_alerts:
                parts.append("<span style='color:#f2994a'><b>Freio de volume:</b> "
                             + "; ".join(res.volume_alerts) + ". A geração vai pedir confirmação reforçada.</span>")
            parts.append(f"<span style='color:#888'>Coerência OK — {res.missing_coupons} de {res.cited_coupons} "
                         "cupons citados pelas campanhas não estão no arquivo de cupons.</span>")
            banner = "<br>".join(parts)
        self._lbl_banner.setText(banner)

        totals = {s: sum(res.counts(e)[s] for e in le.ENTITIES) for s in le.STATUSES}
        for s, pill in self._pills.items():
            pill.set_value(str(totals[s]), _STATUS_COLORS[s] if totals[s] else "#888")
        for r, e in enumerate(le.ENTITIES):
            c = res.counts(e)
            values = [len(res.items[e]), *(c[s] for s in le.STATUSES)]
            for col, v in enumerate(values):
                cell = QTableWidgetItem(str(v))
                cell.setTextAlignment(Qt.AlignCenter)
                self._tbl_summary.setItem(r, col, cell)
        self._fill_details()
        self._btn_export.setEnabled(res.can_export)
        self._btn_sheet.setEnabled(True)
        self._result_box.show()

    def _fill_details(self, *_):
        res = self._result
        self._tbl_items.setRowCount(0)
        if res is None:
            return
        wanted = self._cmb_filter.currentData()
        rows = [it for e in le.ENTITIES for it in res.items[e].values()
                if (it.status == wanted if wanted else it.status != le.PROTEGIDO)]
        rows.sort(key=lambda it: (le.STATUSES.index(it.status), le.ENTITIES.index(it.entity), it.id.lower()))
        self._tbl_items.setRowCount(len(rows))
        for r, it in enumerate(rows):
            values = (le.ENTITY_LABELS[it.entity], it.id, it.status, it.reason)
            for col, v in enumerate(values):
                self._tbl_items.setItem(r, col, QTableWidgetItem(v))

    @staticmethod
    def _counts_text(res: le.SimulationResult) -> str:
        return " | ".join(
            f"{le.ENTITY_LABELS[e]}: " + ", ".join(f"{s} {n}" for s, n in res.counts(e).items())
            for e in le.ENTITIES)

    # ── Saídas ────────────────────────────────────────────────────────────
    def _save_sheet(self):
        if self._result is None:
            return
        stamp = self._result.now.astimezone().strftime("%Y%m%d_%H%M")
        path, _ = QFileDialog.getSaveFileName(
            self, "Salvar planilha da simulação",
            f"SIMULACAO_LIMPEZA_{self._result.store.code if self._result.store else 'LOJA-NAO-IDENTIFICADA'}_{stamp}.xlsx", "Excel (*.xlsx)")
        if path:
            le.build_workbook(self._result).save(path)
            QMessageBox.information(self, "Salvo", f"Planilha salva em:\n{path}")

    def _export(self):
        res, engine = self._result, self._engine
        if res is None or engine is None or not res.can_export:
            return
        lines = []
        for e in le.ENTITIES:
            c = res.counts(e)
            if c[le.ELEGIVEL]:
                lines.append(f"• Excluir {c[le.ELEGIVEL]} {le.ENTITY_LABELS[e].lower()}")
        order = "<br>".join(f"&nbsp;&nbsp;{i}. {le.file_name(n, res.store)}"
                            for i, n in enumerate(le.IMPORT_ORDER[0][1], 1))
        box = QMessageBox(self)
        box.setWindowTitle("Confirmar geração dos arquivos")
        box.setIcon(QMessageBox.Warning)
        box.setTextFormat(Qt.RichText)
        box.setText(
            f"<span style='font-size:15px'><b>⚠ Importe SOMENTE no site {res.store.name}</b></span>"
            f"<br>Loja identificada pelos arquivos ({res.store.code})  ·  carência de {res.grace_days} dias "
            "para campanhas vencidas<br><br>"
            + "<br>".join(lines)
            + f"<br><br><b>Ordem de importação no Business Manager:</b><br>{order}"
            "<br><br>Os rollbacks são gerados junto e devolvem os itens com os códigos dos cupons. "
            "Eles <b>não</b> restauram o histórico de resgates.<br><br>"
            "Nada é importado pelo SIC: os arquivos só são gerados.")
        btn_ok = box.addButton("Gerar arquivos", QMessageBox.AcceptRole)
        btn_ok.setObjectName("btn_primary")
        btn_cancel = box.addButton("Cancelar", QMessageBox.RejectRole)
        box.setDefaultButton(btn_cancel)
        box.exec()
        if box.clickedButton() is not btn_ok:
            return

        if res.volume_alerts:
            typed, ok = QInputDialog.getText(
                self, "Confirmação reforçada",
                "Volume acima do normal:\n" + "\n".join(res.volume_alerts)
                + f"\n\nDigite o total de itens que serão excluídos ({res.affected_total}):")
            if not ok:
                return
            if typed.strip() != str(res.affected_total):
                QMessageBox.warning(self, "Limpeza de Campanhas", "O número não confere. Nada foi gerado.")
                return

        folder = QFileDialog.getExistingDirectory(self, "Escolha a pasta onde salvar os arquivos")
        if not folder:
            return
        self._set_busy(True)
        self._exp_worker = LimpezaExportWorker(engine, res, folder, self)
        self._exp_worker.progress.connect(self._on_progress)
        self._exp_worker.finished.connect(self._on_exported)
        self._exp_worker.error_msg.connect(self._on_error)
        self._exp_worker.start()

    def _on_exported(self, out: le.ExportResult):
        self._set_busy(False)
        res = self._result
        HistoryEngine.add_entry(
            "Limpeza de Campanhas", res.store_name,
            f"Arquivos de limpeza gerados — {res.affected_total} itens.",
            self._counts_text(res),
        )
        box = QMessageBox(self)
        box.setWindowTitle("Arquivos gerados")
        box.setIcon(QMessageBox.Information)
        box.setText(f"Arquivos gerados e conferidos em:\n{out.folder}\n\n"
                    f"Importe SOMENTE no site {res.store.name}, na ordem dos números (1, 2, 3). "
                    "Guarde os arquivos ROLLBACK: eles desfazem a limpeza.")
        btn_open = box.addButton("Abrir pasta", QMessageBox.ActionRole)
        box.addButton(QMessageBox.Ok)
        box.exec()
        if box.clickedButton() is btn_open:
            QDesktopServices.openUrl(QUrl.fromLocalFile(out.folder))
        if p := self.parent():
            if hasattr(p, "show_status"):
                p.show_status(f"Limpeza de Campanhas: arquivos gerados — {Path(out.folder).name}")
