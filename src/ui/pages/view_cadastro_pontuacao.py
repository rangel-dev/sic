"""
Cadastro — Pontuação Auditor sub-view.
Validates SKUs from a Grade de Ativação against a GCP report within a ±2-cycle window.
"""
from __future__ import annotations

from typing import Optional

import pandas as pd
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
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

from src.core.history_engine import HistoryEngine
from src.core.pontuacao_engine import PontuacaoResult
from src.ui.components.base_widgets import DropZone
from src.workers.worker_pontuacao import PontuacaoWorker


class CadastroPontuacaoView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: Optional[PontuacaoWorker] = None
        self._result: Optional[PontuacaoResult] = None
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

        # ── Top: inputs + actions ─────────────────────────────────────────
        top_scroll = QScrollArea()
        top_scroll.setWidgetResizable(True)
        top_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        top_scroll.setMinimumHeight(240)
        splitter.addWidget(top_scroll)

        top_widget = QWidget()
        top_scroll.setWidget(top_widget)
        top_layout = QVBoxLayout(top_widget)
        top_layout.setContentsMargins(28, 16, 28, 12)
        top_layout.setSpacing(12)

        # Row 1: ciclo ref + file inputs
        inputs_row = QHBoxLayout()
        inputs_row.setSpacing(16)

        # Ciclo Ref
        ciclo_col = QVBoxLayout()
        ciclo_lbl = QLabel("Ciclo Referência (YYYYCC)")
        ciclo_lbl.setObjectName("label_section")
        ciclo_col.addWidget(ciclo_lbl)
        self._ciclo_input = QLineEdit("202608")
        self._ciclo_input.setPlaceholderText("ex: 202608")
        self._ciclo_input.setMaximumWidth(140)
        self._ciclo_input.setToolTip(
            "Ciclo de referência no formato YYYYCC.\n"
            "A janela de validade será ±2 ciclos em torno deste valor."
        )
        ciclo_col.addWidget(self._ciclo_input)
        ciclo_col.addStretch()
        inputs_row.addLayout(ciclo_col, 0)

        # Grade de Ativação
        grade_col = QVBoxLayout()
        grade_lbl = QLabel("Grade de Ativação (.xlsm)")
        grade_lbl.setObjectName("label_section")
        grade_col.addWidget(grade_lbl)
        self._dz_grade = DropZone(
            "Grade de Ativação\n(.xlsm / .xlsx)",
            "Excel (*.xlsm *.xlsx)",
        )
        self._dz_grade.setToolTip(
            "Planilha da Grade de Ativação.\n"
            "Deve conter uma aba 'GRADE DE ATIVAÇÃO' com coluna 'SKU'."
        )
        grade_col.addWidget(self._dz_grade)
        inputs_row.addLayout(grade_col, 1)

        # GCP Report
        gcp_col = QVBoxLayout()
        gcp_lbl = QLabel("Relatório GCP (.xlsx / .csv)")
        gcp_lbl.setObjectName("label_section")
        gcp_col.addWidget(gcp_lbl)
        self._dz_gcp = DropZone(
            "Relatório GCP\n(.xlsx ou .csv)",
            "Planilha/CSV (*.xlsx *.xls *.csv)",
        )
        self._dz_gcp.setToolTip(
            "Relatório de preços exportado do GCP.\n"
            "Deve conter colunas de SKU, Abrangência e Ciclo Início/Final."
        )
        gcp_col.addWidget(self._dz_gcp)
        inputs_row.addLayout(gcp_col, 1)

        top_layout.addLayout(inputs_row)

        # Row 2: action buttons
        action_row = QHBoxLayout()
        action_row.setSpacing(12)

        self._btn_run = QPushButton("▶  Executar Auditoria")
        self._btn_run.setObjectName("btn_primary")
        self._btn_run.setFixedWidth(220)
        self._btn_run.clicked.connect(self._run)
        action_row.addWidget(self._btn_run)

        self._btn_clear = QPushButton("Limpar")
        self._btn_clear.setObjectName("btn_ghost")
        self._btn_clear.clicked.connect(self._clear)
        action_row.addWidget(self._btn_clear)

        action_row.addStretch()

        self._btn_export_relatorio = QPushButton("⬇  Relatório de Conferência")
        self._btn_export_relatorio.setObjectName("btn_secondary")
        self._btn_export_relatorio.setEnabled(False)
        self._btn_export_relatorio.clicked.connect(self._export_relatorio)
        action_row.addWidget(self._btn_export_relatorio)

        self._btn_export_carga = QPushButton("⬇  Carga RE Biosphera")
        self._btn_export_carga.setObjectName("btn_secondary")
        self._btn_export_carga.setEnabled(False)
        self._btn_export_carga.clicked.connect(self._export_carga)
        action_row.addWidget(self._btn_export_carga)

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

        # ── Bottom: dashboard cards + results table ───────────────────────
        bottom_scroll = QScrollArea()
        bottom_scroll.setWidgetResizable(True)
        bottom_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        splitter.addWidget(bottom_scroll)

        bottom_widget = QWidget()
        bottom_scroll.setWidget(bottom_widget)
        bottom_layout = QVBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(28, 12, 28, 16)
        bottom_layout.setSpacing(14)

        # Dashboard cards (4 — mirrors the HTML/JS version)
        stats_row = QHBoxLayout()
        stats_row.setSpacing(14)
        self._stat_total = self._make_stat_card("0", "Lidos",           "#475569")
        self._stat_ok    = self._make_stat_card("0", "Conformes",       "#10b981")
        self._stat_fora  = self._make_stat_card("0", "Fora da Janela",  "#f59e0b")
        self._stat_erro  = self._make_stat_card("0", "Não Encontrados", "#ef4444")
        for card in (self._stat_total, self._stat_ok, self._stat_fora, self._stat_erro):
            stats_row.addWidget(card)
        bottom_layout.addLayout(stats_row)

        # Results table
        log_header = QLabel("Resultado da Auditoria")
        log_header.setStyleSheet(
            "font-size:11px;font-weight:700;color:#888;text-transform:uppercase;"
        )
        bottom_layout.addWidget(log_header)

        self._log_table = QTableWidget(0, 5)
        self._log_table.setHorizontalHeaderLabels(
            ["SKU Original", "SKU Limpo", "Abrangência GCP", "Status", "Motivo"]
        )
        hh = self._log_table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(4, QHeaderView.Stretch)
        self._log_table.setAlternatingRowColors(True)
        self._log_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._log_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._log_table.verticalHeader().setVisible(False)
        self._log_table.setMinimumHeight(200)
        bottom_layout.addWidget(self._log_table)

        splitter.setSizes([260, 540])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

    @staticmethod
    def _make_stat_card(value: str, label: str, color: str) -> QWidget:
        card = QWidget()
        card.setStyleSheet(f"background:{color};border-radius:8px;padding:10px;")
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
        ciclo_text = self._ciclo_input.text().strip()
        grade_path = self._dz_grade.file_path
        gcp_path   = self._dz_gcp.file_path

        missing = []
        if not ciclo_text or not ciclo_text.isdigit() or len(ciclo_text) != 6:
            missing.append("Ciclo Referência (formato YYYYCC, ex: 202608)")
        if not grade_path:
            missing.append("Grade de Ativação (.xlsm)")
        if not gcp_path:
            missing.append("Relatório GCP (.xlsx ou .csv)")

        if missing:
            QMessageBox.warning(
                self, "Pontuação",
                "Preencha os seguintes campos antes de executar:\n• "
                + "\n• ".join(missing),
            )
            return

        ciclo_ref = int(ciclo_text)

        self._btn_run.setEnabled(False)
        self._btn_export_relatorio.setEnabled(False)
        self._btn_export_carga.setEnabled(False)
        self._log_table.setRowCount(0)
        self._progress_bar.setValue(0)
        self._progress_bar.show()
        self._status_lbl.show()
        self._result = None

        self._worker = PontuacaoWorker(ciclo_ref, grade_path, gcp_path, self)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.error_msg.connect(self._on_error)
        self._worker.start()

    # ── Slots ─────────────────────────────────────────────────────────────

    def _on_progress(self, pct: int, msg: str):
        self._progress_bar.setValue(pct)
        self._status_lbl.setText(msg)

    def _on_finished(self, result: PontuacaoResult):
        self._result = result
        self._progress_bar.hide()
        self._status_lbl.hide()
        self._btn_run.setEnabled(True)

        stats = result.stats
        self._set_stat(self._stat_total, stats.get("total", 0))
        self._set_stat(self._stat_ok,    stats.get("ok",    0))
        self._set_stat(self._stat_fora,  stats.get("fora",  0))
        self._set_stat(self._stat_erro,  stats.get("erro",  0))

        # Populate results table
        rows = result.relatorio
        self._log_table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            status_val = row.get("Status", "")
            items = [
                QTableWidgetItem(str(row.get("SKU Original", ""))),
                QTableWidgetItem(str(row.get("SKU Limpo", ""))),
                QTableWidgetItem(str(row.get("Abrangência GCP", ""))),
                QTableWidgetItem(status_val),
                QTableWidgetItem(str(row.get("Motivo", ""))),
            ]
            if status_val == "OK":
                items[3].setForeground(QColor("#2ecc71"))
            elif status_val == "FORA DA REGRA":
                items[3].setForeground(QColor("#e2b93d"))
            else:
                items[3].setForeground(QColor("#ff7b72"))

            for col, item in enumerate(items):
                self._log_table.setItem(i, col, item)

        has_relatorio = len(rows) > 0
        has_carga     = len(result.carga) > 0
        self._btn_export_relatorio.setEnabled(has_relatorio)
        self._btn_export_carga.setEnabled(has_carga)

        total = stats.get("total", 0)
        HistoryEngine.add_entry(
            "Cadastro/Pontuação",
            "NATBRA",
            (
                f"Auditoria concluída: {total} SKUs · "
                f"{stats.get('ok', 0)} conformes · "
                f"{stats.get('fora', 0)} fora da janela · "
                f"{stats.get('erro', 0)} não encontrados."
            ),
        )

        if p := self.parent():
            if hasattr(p, "show_status"):
                p.show_status(
                    f"Pontuação: {total} SKUs · "
                    f"{stats.get('ok', 0)} conformes · "
                    f"{stats.get('fora', 0) + stats.get('erro', 0)} pendentes"
                )

    def _on_error(self, msg: str):
        self._btn_run.setEnabled(True)
        self._progress_bar.hide()
        self._status_lbl.hide()
        QMessageBox.critical(self, "Erro — Pontuação", msg)

    # ── Export ────────────────────────────────────────────────────────────

    def _export_relatorio(self):
        if not self._result or not self._result.relatorio:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Salvar Relatório", "Relatorio_Auditoria_BR_BIO.xlsx", "Excel (*.xlsx)"
        )
        if not path:
            return
        try:
            df = pd.DataFrame(self._result.relatorio)
            with pd.ExcelWriter(path, engine="openpyxl") as writer:
                df.to_excel(writer, sheet_name="Resultado Auditoria", index=False)
            QMessageBox.information(self, "Exportado", f"Relatório salvo em:\n{path}")
        except Exception as exc:
            QMessageBox.critical(self, "Erro ao Exportar", str(exc))

    def _export_carga(self):
        if not self._result or not self._result.carga:
            QMessageBox.information(self, "Carga", "Nenhum item pendente de carga.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Salvar Carga Biosphera", "CARGA_RE_BIOSPHERA.xlsx", "Excel (*.xlsx)"
        )
        if not path:
            return
        try:
            df = pd.DataFrame(self._result.carga)
            with pd.ExcelWriter(path, engine="openpyxl") as writer:
                df.to_excel(writer, sheet_name="Carga Biosphera", index=False)
            QMessageBox.information(self, "Exportado", f"Carga salva em:\n{path}")
        except Exception as exc:
            QMessageBox.critical(self, "Erro ao Exportar", str(exc))

    # ── Clear ─────────────────────────────────────────────────────────────

    def _clear(self):
        self._dz_grade.clear()
        self._dz_gcp.clear()
        self._log_table.setRowCount(0)
        self._progress_bar.setValue(0)
        self._progress_bar.hide()
        self._status_lbl.hide()
        self._btn_export_relatorio.setEnabled(False)
        self._btn_export_carga.setEnabled(False)
        self._btn_run.setEnabled(True)
        self._result = None
        for card in (self._stat_total, self._stat_ok, self._stat_fora, self._stat_erro):
            self._set_stat(card, 0)
