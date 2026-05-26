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
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QTextEdit,
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
        self._stats_layout = QVBoxLayout(self._stats_w)
        self._stats_layout.setContentsMargins(0, 0, 0, 0)
        
        r1 = QHBoxLayout()
        self._s_xml = StatPill("XML Master", "—", "#66bb6a")
        self._s_grade = StatPill("Grade (Bruta)", "—", "#42a5f5")
        self._s_match = StatPill("Match", "—", "#ab47bc")
        self._s_on = StatPill("Ativados", "—", "#ef5350")
        self._s_vis = StatPill("Vitrine", "—", "#ffa726")
        self._s_cut = StatPill("Cortes Facão", "—", "#ff7043")
        self._s_moff = StatPill("Mestres OFF", "—", "#8d6e63")
        for w in (self._s_xml, self._s_grade, self._s_match, self._s_on, self._s_vis, self._s_cut, self._s_moff): r1.addWidget(w)
        r1.addStretch()
        self._stats_layout.addLayout(r1)
        
        r2 = QHBoxLayout()
        self._s_list = StatPill("Abas Lista", "—", "#7e57c2")
        self._s_seal = StatPill("Selos Novos", "—", "#26a69a")
        self._s_delta = StatPill("Total Deltas", "—", "#888888")
        for w in (self._s_list, self._s_seal, self._s_delta): r2.addWidget(w)
        r2.addStretch()
        self._stats_layout.addLayout(r2)
        
        self._stats_w.hide()
        layout.addWidget(self._stats_w)
        
        # Lists Table
        self._lbl_table = QLabel("Comparativo de Sincronismo por Lista")
        self._lbl_table.setObjectName("label_section")
        self._lbl_table.setStyleSheet("color: #7e57c2;")
        self._lbl_table.hide()
        layout.addWidget(self._lbl_table)
        
        self._table = QTableWidget()
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels(["ID DA LISTA", "NO EXCEL (ALVO)", "NO XML (ANTIGO)", "STATUS DELTA"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.verticalHeader().hide()
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setSelectionMode(QTableWidget.NoSelection)
        self._table.setFixedHeight(250)
        self._table.hide()
        layout.addWidget(self._table)
        
        # Log Box
        self._log_box = QTextEdit()
        self._log_box.setReadOnly(True)
        self._log_box.setFixedHeight(180)
        self._log_box.setStyleSheet("background-color: #0b0c10; color: #e0e0e0; font-family: monospace; font-size: 11px;")
        self._log_box.hide()
        layout.addWidget(self._log_box)

        # Download
        dl_row = QHBoxLayout()
        self._btn_dl = QPushButton("⬇  Salvar XML Delta")
        self._btn_dl.setObjectName("btn_secondary")
        self._btn_dl.setFixedWidth(180)
        self._btn_dl.clicked.connect(self._save_xml)
        self._btn_dl.hide()
        dl_row.addWidget(self._btn_dl)

        self._btn_audit = QPushButton("📊  Baixar Auditoria XLSX")
        self._btn_audit.setObjectName("btn_secondary")
        self._btn_audit.setFixedWidth(200)
        self._btn_audit.clicked.connect(self._save_audit)
        self._btn_audit.hide()
        dl_row.addWidget(self._btn_audit)
        dl_row.addStretch()
        
        layout.addLayout(dl_row)

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
        self._btn_audit.hide()
        self._stats_w.hide()
        self._table.hide()
        self._lbl_table.hide()
        self._log_box.clear()
        self._log_box.append("<b>LOG DE ATIVIDADE</b><br>")
        self._log_box.show()
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
        if msg.startswith(">"):
            self._log_box.append(msg)
        else:
            self._status_lbl.setText(msg)
            self._progress_bar.setValue(pct)

    def _on_finished(self, result: SyncResult):
        self._result = result
        self._btn_run.setEnabled(True)

        if result.warnings:
            self._warn_lbl.setText("⚠  " + "  |  ".join(result.warnings))
            self._warn_lbl.show()

        s = result.stats
        self._s_xml.set_value(str(s.get("xml", 0)), "#66bb6a")
        self._s_grade.set_value(str(s.get("grade", 0)), "#42a5f5")
        self._s_match.set_value(str(s.get("match", 0)), "#ab47bc")
        self._s_on.set_value(str(s.get("onC", 0)), "#ef5350")
        self._s_vis.set_value(str(s.get("visC", 0)), "#ffa726")
        self._s_cut.set_value(str(s.get("cut", 0)), "#ff7043")
        self._s_moff.set_value(str(s.get("mOff", 0)), "#8d6e63")
        self._s_list.set_value(str(s.get("lists", 0)), "#7e57c2")
        self._s_seal.set_value(str(s.get("sealC", 0)), "#26a69a")
        self._s_delta.set_value(str(s.get("deltas", 0)), "#888888")

        self._stats_w.show()
        
        # Populate table
        lists = s.get("lists_details", [])
        self._table.setRowCount(len(lists))
        for r_idx, row_data in enumerate(lists):
            item_id = QTableWidgetItem(str(row_data["id"]))
            item_id.setForeground(Qt.GlobalColor.cyan)
            self._table.setItem(r_idx, 0, item_id)
            
            item_excel = QTableWidgetItem(f'{row_data["excel"]} itens')
            self._table.setItem(r_idx, 1, item_excel)
            
            item_xml = QTableWidgetItem(f'{row_data["xml"]} itens')
            self._table.setItem(r_idx, 2, item_xml)
            
            status = str(row_data["status"])
            item_st = QTableWidgetItem(status)
            if "✓" in status:
                item_st.setForeground(Qt.GlobalColor.green)
            else:
                item_st.setForeground(Qt.GlobalColor.yellow)
            self._table.setItem(r_idx, 3, item_st)
            
        self._table.show()
        self._lbl_table.show()
        
        self._btn_dl.show()
        self._btn_audit.show()

        if p := self.parent():
            if hasattr(p, "show_status"):
                p.show_status(
                    f"Sync: {s.get('deltas', 0)} Deltas gerados"
                )

        # Log to History
        brand = result.catalog_id if result.catalog_id else "Desconhecida"
        HistoryEngine.add_entry(
            "Sync",
            brand,
            f"Sync finalizado: {s.get('deltas', 0)} modificações no catálogo."
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

    def _save_audit(self):
        if not self._result or not self._result.report:
            QMessageBox.warning(self, "Auditoria", "Nenhum relatório gerado.")
            return
        
        default = "Relatorio_Sincronia_Master.xlsx"
        path, _ = QFileDialog.getSaveFileName(self, "Salvar Relatório XLSX", default, "Excel (*.xlsx)")
        if path:
            import pandas as pd
            df = pd.DataFrame(self._result.report)
            with pd.ExcelWriter(path, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="Auditoria")
            QMessageBox.information(self, "Salvo", f"Relatório salvo em:\n{path}")

    def _clear(self):
        self._dz_excel.clear()
        self._dz_xml.clear()
        self._progress_bar.hide()
        self._status_lbl.hide()
        self._warn_lbl.hide()
        self._stats_w.hide()
        self._table.hide()
        self._lbl_table.hide()
        self._log_box.hide()
        self._btn_dl.hide()
        self._btn_audit.hide()
        self._result = None
        self._btn_run.setEnabled(True)
