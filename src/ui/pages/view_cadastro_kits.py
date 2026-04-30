"""
Cadastro — Kit Validation sub-view.
Crosses Salesforce XML against BO Excel to detect and export kit divergences.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.core.cadastro_engine import KitValidationResult
from src.core.history_engine import HistoryEngine
from src.core.utils import get_unique_path
from src.ui.components.base_widgets import Divider, DropZone, SectionHeader
from src.workers.worker_cadastro import CadastroWorker


class CadastroKitsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: Optional[CadastroWorker] = None
        self._result: Optional[KitValidationResult] = None
        self._setup_ui()

    # ── Layout ────────────────────────────────────────────────────────────

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        splitter = QSplitter(Qt.Vertical)
        splitter.setHandleWidth(4)
        splitter.setChildrenCollapsible(False)
        root.addWidget(splitter)

        # ── Top: file inputs + actions ────────────────────────────────────
        top_scroll = QScrollArea()
        top_scroll.setWidgetResizable(True)
        top_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        top_scroll.setMinimumHeight(220)
        splitter.addWidget(top_scroll)

        top_widget = QWidget()
        top_scroll.setWidget(top_widget)
        top_layout = QVBoxLayout(top_widget)
        top_layout.setContentsMargins(28, 16, 28, 12)
        top_layout.setSpacing(12)

        # File inputs row
        inputs_row = QHBoxLayout()
        inputs_row.setSpacing(16)

        xml_col = QVBoxLayout()
        xml_lbl = QLabel("XML Salesforce (Brasil ou Peru)")
        xml_lbl.setObjectName("label_section")
        xml_col.addWidget(xml_lbl)
        self._dz_xml = DropZone("XML Salesforce\n(br-natura / natper)", "XML (*.xml)")
        self._dz_xml.setToolTip(
            "XML de Catálogo exportado do Salesforce.\n"
            "Deve conter produtos com a tag <bundled-products>."
        )
        xml_col.addWidget(self._dz_xml)
        inputs_row.addLayout(xml_col, 1)

        excel_col = QVBoxLayout()
        excel_lbl = QLabel("Planilha Excel BO (.xlsx)")
        excel_lbl.setObjectName("label_section")
        excel_col.addWidget(excel_lbl)
        self._dz_excel = DropZone(
            "Excel do BO\n(COD_VENDA_PAI / FILHO / QUANTIDADE)",
            "Excel (*.xlsx *.xlsm *.xls)",
        )
        self._dz_excel.setToolTip(
            "Planilha do BO com colunas COD_VENDA_PAI, COD_VENDA_FILHO e QUANTIDADE.\n"
            "Usada como fonte de verdade para a correção dos kits."
        )
        excel_col.addWidget(self._dz_excel)
        inputs_row.addLayout(excel_col, 1)

        top_layout.addLayout(inputs_row)

        # Action row
        action_row = QHBoxLayout()
        action_row.setSpacing(12)

        self._btn_run = QPushButton("▶  Analisar Kits")
        self._btn_run.setObjectName("btn_primary")
        self._btn_run.setFixedWidth(200)
        self._btn_run.clicked.connect(self._run)
        action_row.addWidget(self._btn_run)

        self._btn_clear = QPushButton("Limpar")
        self._btn_clear.setObjectName("btn_ghost")
        self._btn_clear.clicked.connect(self._clear)
        action_row.addWidget(self._btn_clear)

        action_row.addStretch()

        self._btn_export_xlsx = QPushButton("⬇  Baixar Relatório .xlsx")
        self._btn_export_xlsx.setObjectName("btn_secondary")
        self._btn_export_xlsx.setEnabled(False)
        self._btn_export_xlsx.clicked.connect(self._export_xlsx)
        action_row.addWidget(self._btn_export_xlsx)

        self._btn_export_xml = QPushButton("⬇  Baixar XML de Correção")
        self._btn_export_xml.setObjectName("btn_secondary")
        self._btn_export_xml.setEnabled(False)
        self._btn_export_xml.clicked.connect(self._export_xml)
        action_row.addWidget(self._btn_export_xml)

        top_layout.addLayout(action_row)

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.hide()
        top_layout.addWidget(self._progress_bar)

        self._status_lbl = QLabel("")
        self._status_lbl.setObjectName("label_muted")
        self._status_lbl.hide()
        top_layout.addWidget(self._status_lbl)

        top_layout.addStretch()

        # ── Bottom: stats + log ───────────────────────────────────────────
        bottom_scroll = QScrollArea()
        bottom_scroll.setWidgetResizable(True)
        bottom_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        splitter.addWidget(bottom_scroll)

        bottom_widget = QWidget()
        bottom_scroll.setWidget(bottom_widget)
        bottom_layout = QVBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(28, 12, 28, 16)
        bottom_layout.setSpacing(14)

        # Stats cards
        stats_row = QHBoxLayout()
        stats_row.setSpacing(14)
        self._stat_total = self._make_stat_card("0", "Kits Analisados", "#00a1e0")
        self._stat_ok    = self._make_stat_card("0", "Kits Corretos",   "#2ecc71")
        self._stat_erro  = self._make_stat_card("0", "Divergências",    "#e74c3c")
        for card in (self._stat_total, self._stat_ok, self._stat_erro):
            stats_row.addWidget(card)
        bottom_layout.addLayout(stats_row)

        # Log area
        log_header = QLabel("Log de Análise")
        log_header.setStyleSheet(
            "font-size:11px;font-weight:700;color:#888;text-transform:uppercase;"
        )
        bottom_layout.addWidget(log_header)

        self._log_table = QTableWidget(0, 3)
        self._log_table.setHorizontalHeaderLabels(["SKU Pai", "Status", "Detalhe"])
        self._log_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self._log_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self._log_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self._log_table.setAlternatingRowColors(True)
        self._log_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._log_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._log_table.verticalHeader().setVisible(False)
        self._log_table.setMinimumHeight(200)
        bottom_layout.addWidget(self._log_table)

        splitter.setSizes([240, 560])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

    @staticmethod
    def _make_stat_card(value: str, label: str, color: str) -> QWidget:
        card = QWidget()
        card.setStyleSheet(
            f"background:{color};border-radius:8px;padding:10px;"
        )
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(2)

        val_lbl = QLabel(value)
        val_lbl.setAlignment(Qt.AlignCenter)
        val_lbl.setStyleSheet(
            "font-size:28px;font-weight:700;color:white;background:transparent;"
        )
        val_lbl.setObjectName("_val")
        layout.addWidget(val_lbl)

        name_lbl = QLabel(label)
        name_lbl.setAlignment(Qt.AlignCenter)
        name_lbl.setStyleSheet("font-size:11px;color:white;background:transparent;")
        layout.addWidget(name_lbl)

        return card

    @staticmethod
    def _set_stat(card: QWidget, value: int):
        lbl = card.findChild(QLabel, "_val")
        if lbl:
            lbl.setText(str(value))

    # ── Run ───────────────────────────────────────────────────────────────

    def _run(self):
        xml_path   = self._dz_xml.file_path
        excel_path = self._dz_excel.file_path

        missing = []
        if not xml_path:
            missing.append("XML Salesforce")
        if not excel_path:
            missing.append("Excel BO")
        if missing:
            QMessageBox.warning(
                self, "Cadastro",
                "Selecione os seguintes arquivos antes de executar:\n• "
                + "\n• ".join(missing),
            )
            return

        self._btn_run.setEnabled(False)
        self._btn_export_xlsx.setEnabled(False)
        self._btn_export_xml.setEnabled(False)
        self._log_table.setRowCount(0)
        self._progress_bar.setValue(0)
        self._progress_bar.show()
        self._status_lbl.show()
        self._result = None

        self._worker = CadastroWorker(xml_path, excel_path, self)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.error_msg.connect(self._on_error)
        self._worker.start()

    # ── Slots ─────────────────────────────────────────────────────────────

    def _on_progress(self, pct: int, msg: str):
        self._progress_bar.setValue(pct)
        self._status_lbl.setText(msg)

    def _on_finished(self, result: KitValidationResult):
        self._result = result
        self._progress_bar.hide()
        self._status_lbl.hide()
        self._btn_run.setEnabled(True)

        stats = result.stats
        self._set_stat(self._stat_total, stats.get("total", 0))
        self._set_stat(self._stat_ok,    stats.get("ok",    0))
        self._set_stat(self._stat_erro,  stats.get("erro",  0))

        has_errors = stats.get("erro", 0) > 0

        if result.errors:
            self._log_table.setRowCount(len(result.errors))
            for i, e in enumerate(result.errors):
                pai_item = QTableWidgetItem(str(e.get("Pai", "")))
                status_item = QTableWidgetItem(str(e.get("Status", "")))
                detalhe_item = QTableWidgetItem(str(e.get("Detalhe", "")))

                status_val = e.get("Status", "")
                if "Ausente" in status_val:
                    status_item.setForeground(QColor("#ff7b72"))
                elif "Divergente" in status_val:
                    status_item.setForeground(QColor("#e2b93d"))

                self._log_table.setItem(i, 0, pai_item)
                self._log_table.setItem(i, 1, status_item)
                self._log_table.setItem(i, 2, detalhe_item)
        else:
            self._log_table.setRowCount(1)
            self._log_table.setItem(0, 0, QTableWidgetItem(""))
            sucesso_item = QTableWidgetItem("✅ Sucesso")
            sucesso_item.setForeground(QColor("#2ecc71"))
            self._log_table.setItem(0, 1, sucesso_item)
            self._log_table.setItem(0, 2, QTableWidgetItem("Todos os kits conferem!"))

        self._btn_export_xlsx.setEnabled(has_errors)
        self._btn_export_xml.setEnabled(has_errors)

        total = stats.get("total", 0)
        HistoryEngine.add_entry(
            "Cadastro",
            "NATBRA",
            f"Validação concluída: {total} kits, {stats.get('erro', 0)} divergências.",
        )

        if p := self.parent():
            if hasattr(p, "show_status"):
                p.show_status(
                    f"Cadastro: {total} kits analisados · "
                    f"{stats.get('erro', 0)} divergências"
                )

    def _on_error(self, msg: str):
        self._btn_run.setEnabled(True)
        self._progress_bar.hide()
        self._status_lbl.hide()
        QMessageBox.critical(self, "Erro — Cadastro", msg)

    # ── Export ────────────────────────────────────────────────────────────

    def _export_xlsx(self):
        if not self._result or not self._result.errors:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Salvar Relatório", "Relatorio_Erros_Kits_NATBRA.xlsx", "Excel (*.xlsx)"
        )
        if not path:
            return
        path = get_unique_path(path)
        try:
            df = pd.DataFrame(self._result.errors)
            with pd.ExcelWriter(path, engine="openpyxl") as writer:
                df.to_excel(writer, sheet_name="Divergencias", index=False)
            QMessageBox.information(self, "Exportado", f"Relatório salvo em:\n{path}")
        except Exception as exc:
            QMessageBox.critical(self, "Erro ao Exportar", str(exc))

    def _export_xml(self):
        if not self._result or not self._result.correction_xml:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Salvar XML de Correção", "CORRECAO_KITS_BRASIL.xml", "XML (*.xml)"
        )
        if not path:
            return
        path = get_unique_path(path)
        try:
            Path(path).write_text(self._result.correction_xml, encoding="utf-8")
            QMessageBox.information(self, "Exportado", f"XML salvo em:\n{path}")
        except Exception as exc:
            QMessageBox.critical(self, "Erro ao Exportar", str(exc))

    # ── Clear ─────────────────────────────────────────────────────────────

    def _clear(self):
        self._dz_xml.clear()
        self._dz_excel.clear()
        self._log_table.setRowCount(0)
        self._progress_bar.setValue(0)
        self._progress_bar.hide()
        self._status_lbl.hide()
        self._btn_export_xlsx.setEnabled(False)
        self._btn_export_xml.setEnabled(False)
        self._btn_run.setEnabled(True)
        self._result = None
        self._set_stat(self._stat_total, 0)
        self._set_stat(self._stat_ok,    0)
        self._set_stat(self._stat_erro,  0)
