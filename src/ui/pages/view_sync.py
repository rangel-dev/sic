"""
Sync View – Merchandising Sync (store lists + product attributes).
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.ui.components.base_widgets import Divider, DropZone, SectionHeader, StatPill
from src.workers.worker_sync import SyncWorker
from src.core.sync_engine import SyncResult
from src.core.history_engine import HistoryEngine


class SyncView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: SyncWorker | None = None
        self._result: SyncResult | None = None
        self._setup_ui()

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        outer.addWidget(SectionHeader(
            "↕  Sync de Merchandising",
            "Sincroniza listas de vitrine, online-flag e searchable-flag via delta XML"
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

        # Inputs
        lbl_excel = QLabel("Planilha(s) Excel  (GRADE DE ATIVAÇÃO + LISTA_XX)")
        lbl_excel.setObjectName("label_section")
        layout.addWidget(lbl_excel)

        self._dz_excel = DropZone(
            "Arraste o(s) Excel aqui — abas GRADE + LISTA_XX",
            "Excel (*.xlsx *.xlsm *.xls)",
            multiple=True,
        )
        self._dz_excel.setToolTip(
            "A planilha deve conter a aba GRADE DE ATIVAÇÃO (visibilidade) "
            "e abas LISTA_XX (vitrine)."
        )
        layout.addWidget(self._dz_excel)

        lbl_xml = QLabel("Catálogo(s) XML  —  Natura, Avon, Minha Loja")
        lbl_xml.setObjectName("label_section")
        layout.addWidget(lbl_xml)

        self._dz_xml = DropZone(
            "Arraste os XMLs de Catálogo (exportados do SF há >10 min)",
            "XML (*.xml)",
            multiple=True,
        )
        self._dz_xml.setToolTip(
            "Regra de Ouro: os XMLs devem ter sido exportados há mais de 10 minutos "
            "para garantir que a exportação do Salesforce está completa."
        )
        layout.addWidget(self._dz_xml)

        # Action
        action_row = QHBoxLayout()
        self._btn_run = QPushButton("↕  Executar Sync")
        self._btn_run.setObjectName("btn_primary")
        self._btn_run.setFixedWidth(200)
        self._btn_run.clicked.connect(self._run)
        action_row.addWidget(self._btn_run)

        btn_clear = QPushButton("Limpar")
        btn_clear.setObjectName("btn_ghost")
        btn_clear.clicked.connect(self._clear)
        action_row.addWidget(btn_clear)
        action_row.addStretch()
        layout.addLayout(action_row)

        # Progress
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.hide()
        layout.addWidget(self._progress_bar)

        self._status_lbl = QLabel("")
        self._status_lbl.setObjectName("label_muted")
        self._status_lbl.hide()
        layout.addWidget(self._status_lbl)

        # Warnings
        self._warn_lbl = QLabel("")
        self._warn_lbl.setWordWrap(True)
        self._warn_lbl.setStyleSheet("color:#ffcc80;font-size:11px;background:transparent;")
        self._warn_lbl.hide()
        layout.addWidget(self._warn_lbl)

        # Stats
        self._stats_w = QWidget()
        sr = QHBoxLayout(self._stats_w)
        sr.setContentsMargins(0, 0, 0, 0)
        sr.setSpacing(12)
        self._s_add    = StatPill("Adições",         "—", "#66bb6a")
        self._s_rm     = StatPill("Remoções",         "—", "#ef5350")
        self._s_attr   = StatPill("Atrib. Atualizados", "—", "#42a5f5")
        self._s_lists  = StatPill("Listas Processadas",  "—", "#888888")
        for w in (self._s_add, self._s_rm, self._s_attr, self._s_lists):
            sr.addWidget(w)
        sr.addStretch()
        self._stats_w.hide()
        layout.addWidget(self._stats_w)

        # Download
        self._btn_dl = QPushButton("⬇  Salvar XML Delta")
        self._btn_dl.setObjectName("btn_secondary")
        self._btn_dl.setFixedWidth(180)
        self._btn_dl.clicked.connect(self._save_xml)
        self._btn_dl.hide()
        layout.addWidget(self._btn_dl)

        layout.addStretch()

    # ── Slots ─────────────────────────────────────────────────────────────
    def _run(self):
        excel = self._dz_excel.file_paths
        xmls  = self._dz_xml.file_paths
        if not excel:
            QMessageBox.warning(self, "Sync", "Selecione ao menos uma planilha Excel.")
            return
        if not xmls:
            QMessageBox.warning(self, "Sync", "Selecione ao menos um XML de Catálogo.")
            return

        self._btn_run.setEnabled(False)
        self._btn_dl.hide()
        self._stats_w.hide()
        self._warn_lbl.hide()
        self._progress_bar.setValue(0)
        self._progress_bar.show()
        self._status_lbl.show()

        self._worker = SyncWorker(excel, xmls, self)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.error_msg.connect(self._on_error)
        self._worker.start()

    def _on_progress(self, pct: int, msg: str):
        self._progress_bar.setValue(pct)
        self._status_lbl.setText(msg)

    def _on_finished(self, result: SyncResult):
        self._result = result
        self._btn_run.setEnabled(True)

        if result.warnings:
            self._warn_lbl.setText("⚠  " + "  |  ".join(result.warnings))
            self._warn_lbl.show()

        s = result.stats
        self._s_add.set_value(str(s.get("additions",      0)), "#66bb6a")
        self._s_rm.set_value( str(s.get("removals",       0)), "#ef5350")
        self._s_attr.set_value(str(s.get("attr_updates",  0)), "#42a5f5")
        self._s_lists.set_value(str(s.get("lists_processed", 0)), "#888")
        self._stats_w.show()
        self._btn_dl.show()

        if p := self.parent():
            if hasattr(p, "show_status"):
                p.show_status(
                    f"Sync: +{s.get('additions',0)} / -{s.get('removals',0)} assignamentos"
                )

        # Log to History
        brand = result.catalog_id if result.catalog_id else "Desconhecida"
        HistoryEngine.add_entry(
            "Sync",
            brand,
            f"Sync finalizado: +{s.get('additions', 0)} / -{s.get('removals', 0)} modificações."
        )

    def _on_error(self, msg: str):
        self._btn_run.setEnabled(True)
        self._progress_bar.hide()
        self._status_lbl.hide()
        QMessageBox.critical(self, "Erro — Sync", msg)

    def _save_xml(self):
        if not self._result or not self._result.xml_content:
            return
        cat_id = self._result.catalog_id or "catalog"
        default = f"CATALOG_DELTA_{cat_id}.xml"
        path, _ = QFileDialog.getSaveFileName(self, "Salvar Catálogo Delta", default, "XML (*.xml)")
        if path:
            with open(path, "wb") as f:
                f.write(self._result.xml_content)
            QMessageBox.information(self, "Salvo", f"XML salvo em:\n{path}")

    def _clear(self):
        self._dz_excel.clear()
        self._dz_xml.clear()
        self._progress_bar.hide()
        self._status_lbl.hide()
        self._warn_lbl.hide()
        self._stats_w.hide()
        self._btn_dl.hide()
        self._result = None
        self._btn_run.setEnabled(True)
