"""
Cadastro — Conversor Biosphera (Pontuação) sub-view.
Converte Carga Biosphera (Auditoria) vs Revista CF.
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
from src.core.conversor_engine import ConversorResult
from src.core.utils import get_unique_path
from src.ui.components.base_widgets import DropZone
from src.workers.worker_conversor import ConversorWorker


class CadastroConversorView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: Optional[ConversorWorker] = None
        self._result: Optional[ConversorResult] = None
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

        # Row 1: ciclo base + file inputs
        inputs_row = QHBoxLayout()
        inputs_row.setSpacing(16)

        # Ciclo Base
        ciclo_col = QVBoxLayout()
        ciclo_lbl = QLabel("Ciclo Base (Ex: 202609)")
        ciclo_lbl.setObjectName("label_section")
        ciclo_col.addWidget(ciclo_lbl)
        self._ciclo_input = QLineEdit()
        self._ciclo_input.setPlaceholderText("ex: 202609")
        self._ciclo_input.setMaximumWidth(140)
        self._ciclo_input.setToolTip("Ciclo base para cálculo (o GCP usa Ciclo - 2)")
        ciclo_col.addWidget(self._ciclo_input)
        ciclo_col.addStretch()
        inputs_row.addLayout(ciclo_col, 0)

        # Carga Biosphera (Auditoria)
        aud_col = QVBoxLayout()
        aud_lbl = QLabel("1. Carga Biosphera (Auditoria)")
        aud_lbl.setObjectName("label_section")
        aud_col.addWidget(aud_lbl)
        self._dz_auditoria = DropZone("Carga Auditoria\n(.xlsx / .csv)", "Excel (*.xlsx *.csv)")
        aud_col.addWidget(self._dz_auditoria)
        inputs_row.addLayout(aud_col, 1)

        # Relatório Revista
        rev_col = QVBoxLayout()
        rev_lbl = QLabel("2. Relatório Revista CF")
        rev_lbl.setObjectName("label_section")
        rev_col.addWidget(rev_lbl)
        self._dz_revista = DropZone("Revista CF\n(.xlsx / .csv)", "Excel (*.xlsx *.csv)")
        rev_col.addWidget(self._dz_revista)
        inputs_row.addLayout(rev_col, 1)

        # Grade Backup
        grade_col = QVBoxLayout()
        grade_lbl = QLabel("3. Grade de Backup")
        grade_lbl.setObjectName("label_section")
        grade_col.addWidget(grade_lbl)
        self._dz_grade = DropZone("Grade (Opcional)\n(.xlsx / .xlsm)", "Excel (*.xlsm *.xlsx)")
        grade_col.addWidget(self._dz_grade)
        inputs_row.addLayout(grade_col, 1)

        top_layout.addLayout(inputs_row)

        # Row 2: action buttons
        action_row = QHBoxLayout()
        action_row.setSpacing(12)

        self._btn_run = QPushButton("▶  Executar Processamento")
        self._btn_run.setObjectName("btn_primary")
        self._btn_run.setFixedWidth(220)
        self._btn_run.clicked.connect(self._run)
        action_row.addWidget(self._btn_run)

        self._btn_clear = QPushButton("Limpar")
        self._btn_clear.setObjectName("btn_ghost")
        self._btn_clear.clicked.connect(self._clear)
        action_row.addWidget(self._btn_clear)

        action_row.addStretch()

        self._btn_export_excecoes = QPushButton("⬇  Exceções (Não Encontrados)")
        self._btn_export_excecoes.setObjectName("btn_secondary")
        self._btn_export_excecoes.setEnabled(False)
        self._btn_export_excecoes.clicked.connect(self._export_excecoes)
        action_row.addWidget(self._btn_export_excecoes)

        self._btn_export_carga = QPushButton("⬇  Carga para GCP")
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
        self._stat_total  = self._make_stat_card("0", "Total Auditoria", "#475569")
        self._stat_match  = self._make_stat_card("0", "Encontrados",     "#10b981")
        self._stat_linhas = self._make_stat_card("0", "Linhas Geradas",  "#3b82f6")
        self._stat_erro   = self._make_stat_card("0", "Não Encontrados", "#ef4444")
        for card in (self._stat_total, self._stat_match, self._stat_linhas, self._stat_erro):
            stats_row.addWidget(card)
        bottom_layout.addLayout(stats_row)

        # Results table
        log_header = QLabel("Exceções Encontradas")
        log_header.setStyleSheet(
            "font-size:11px;font-weight:700;color:#888;text-transform:uppercase;"
        )
        bottom_layout.addWidget(log_header)

        self._log_table = QTableWidget(0, 3)
        self._log_table.setHorizontalHeaderLabels(
            ["Código Auditoria", "Status", "Ação"]
        )
        hh = self._log_table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(2, QHeaderView.Stretch)
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
        aud_path   = self._dz_auditoria.file_path
        rev_path   = self._dz_revista.file_path
        grade_path = self._dz_grade.file_path

        missing = []
        if not ciclo_text or not ciclo_text.isdigit() or len(ciclo_text) != 6:
            missing.append("Ciclo Base (formato YYYYCC, ex: 202609)")
        if not aud_path:
            missing.append("Carga Biosphera (Auditoria)")
        if not rev_path:
            missing.append("Relatório Revista CF")

        if missing:
            QMessageBox.warning(
                self, "Pontuação",
                "Preencha os seguintes campos antes de executar:\n• "
                + "\n• ".join(missing),
            )
            return

        ciclo_base = int(ciclo_text)

        self._btn_run.setEnabled(False)
        self._btn_export_excecoes.setEnabled(False)
        self._btn_export_carga.setEnabled(False)
        self._log_table.setRowCount(0)
        self._progress_bar.setValue(0)
        self._progress_bar.show()
        self._status_lbl.show()
        self._result = None

        self._worker = ConversorWorker(ciclo_base, aud_path, rev_path, grade_path, self)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.error_msg.connect(self._on_error)
        self._worker.start()

    # ── Slots ─────────────────────────────────────────────────────────────

    def _on_progress(self, pct: int, msg: str):
        self._progress_bar.setValue(pct)
        self._status_lbl.setText(msg)

    def _on_finished(self, result: ConversorResult):
        self._result = result
        self._progress_bar.hide()
        self._status_lbl.hide()
        self._btn_run.setEnabled(True)

        stats = result.stats
        self._set_stat(self._stat_total,  stats.get("total", 0))
        self._set_stat(self._stat_match,  stats.get("match", 0))
        self._set_stat(self._stat_linhas, stats.get("linhas", 0))
        self._set_stat(self._stat_erro,   stats.get("erro", 0))

        # Populate results table
        rows = result.excecoes
        self._log_table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            items = [
                QTableWidgetItem(str(row.get("CODIGO_AUDITORIA", ""))),
                QTableWidgetItem(str(row.get("STATUS", ""))),
                QTableWidgetItem(str(row.get("ACCAO", ""))),
            ]
            
            items[1].setForeground(QColor("#ff7b72")) # Status column (Error)

            for col, item in enumerate(items):
                self._log_table.setItem(i, col, item)

        has_excecoes = len(rows) > 0
        has_carga    = len(result.carga) > 0
        self._btn_export_excecoes.setEnabled(has_excecoes)
        self._btn_export_carga.setEnabled(has_carga)

        total = stats.get("total", 0)
        HistoryEngine.add_entry(
            "Cadastro/Pontuação",
            "NATBRA",
            (
                f"Processamento concluído: {total} itens lidos · "
                f"{stats.get('match', 0)} encontrados · "
                f"{stats.get('linhas', 0)} linhas geradas · "
                f"{stats.get('erro', 0)} erros (exceções)."
            ),
        )

        if p := self.parent():
            if hasattr(p, "show_status"):
                p.show_status(
                    f"Pontuação: {total} Lidos · "
                    f"{stats.get('match', 0)} Encontrados · "
                    f"{stats.get('erro', 0)} Exceções"
                )

    def _on_error(self, msg: str):
        self._btn_run.setEnabled(True)
        self._progress_bar.hide()
        self._status_lbl.hide()
        QMessageBox.critical(self, "Erro — Pontuação", msg)

    # ── Export ────────────────────────────────────────────────────────────

    def _export_excecoes(self):
        if not self._result or not self._result.excecoes:
            return
        
        ciclo = self._ciclo_input.text().strip()
        path, _ = QFileDialog.getSaveFileName(
            self, "Salvar Exceções", f"EXCECOES_NAO_ENCONTRADOS_C{ciclo}.xlsx", "Excel (*.xlsx)"
        )
        if not path:
            return
        path = get_unique_path(path)
        try:
            df = pd.DataFrame(self._result.excecoes)
            with pd.ExcelWriter(path, engine="openpyxl") as writer:
                df.to_excel(writer, sheet_name="Itens_Nao_Processados", index=False)
            QMessageBox.information(self, "Exportado", f"Relatório salvo em:\n{path}")
        except Exception as exc:
            QMessageBox.critical(self, "Erro ao Exportar", str(exc))

    def _export_carga(self):
        if not self._result or not self._result.carga:
            QMessageBox.information(self, "Carga", "Nenhuma linha de carga gerada.")
            return
        
        ciclo = self._ciclo_input.text().strip()
        path, _ = QFileDialog.getSaveFileName(
            self, "Salvar Carga GCP", f"CARGA_PARA_GCP_C{ciclo}.xlsx", "Excel (*.xlsx)"
        )
        if not path:
            return
        path = get_unique_path(path)
        try:
            df = pd.DataFrame(self._result.carga)
            with pd.ExcelWriter(path, engine="openpyxl") as writer:
                df.to_excel(writer, sheet_name="Preço", index=False)
            QMessageBox.information(self, "Exportado", f"Carga salva em:\n{path}")
        except Exception as exc:
            QMessageBox.critical(self, "Erro ao Exportar", str(exc))

    # ── Clear ─────────────────────────────────────────────────────────────

    def _clear(self):
        self._dz_auditoria.clear()
        self._dz_revista.clear()
        self._dz_grade.clear()
        self._log_table.setRowCount(0)
        self._progress_bar.setValue(0)
        self._progress_bar.hide()
        self._status_lbl.hide()
        self._btn_export_excecoes.setEnabled(False)
        self._btn_export_carga.setEnabled(False)
        self._btn_run.setEnabled(True)
        self._result = None
        for card in (self._stat_total, self._stat_match, self._stat_linhas, self._stat_erro):
            self._set_stat(card, 0)
