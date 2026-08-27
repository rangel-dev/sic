"""
Cupom View – Gerador de Cupons SFCC
Entrada manual e/ou .xlsx → XML Demandware coupon/2008-06-17 + log de inconsistências.
"""
from __future__ import annotations

import io
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.ui.components.base_widgets import Divider, SectionHeader, StatPill
from src.core.history_engine import HistoryEngine
from src.core.cupom_engine import CupomResult
from src.workers.worker_cupom import CupomWorker


class CupomView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: CupomWorker | None = None
        self._result: CupomResult | None = None
        self._setup_ui()

    # ── Construção da UI ──────────────────────────────────────────────────
    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        outer.addWidget(SectionHeader(
            "✦  Cupons SFCC",
            "Consolide listas de cupons de múltiplas origens e gere o XML pronto para "
            "importação no Salesforce Commerce Cloud."
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

        # ── Coupon ID ──────────────────────────────────────────────────────
        cfg_box = QGroupBox("Configuração")
        cfg_layout = QVBoxLayout(cfg_box)
        cfg_layout.setContentsMargins(16, 18, 16, 14)
        cfg_layout.setSpacing(10)

        lbl_id = QLabel("Coupon ID  <span style='color:#888;font-weight:400'>"
                        "(identificador no Salesforce)</span>")
        lbl_id.setObjectName("label_section")
        cfg_layout.addWidget(lbl_id)

        self._coupon_id = QLineEdit()
        self._coupon_id.setPlaceholderText("Ex: promo-especial-2026")
        self._coupon_id.setFixedHeight(36)
        cfg_layout.addWidget(self._coupon_id)

        layout.addWidget(cfg_box)

        # ── Entrada de dados ───────────────────────────────────────────────
        input_box = QGroupBox("Entrada de Dados")
        input_layout = QVBoxLayout(input_box)
        input_layout.setContentsMargins(16, 18, 16, 14)
        input_layout.setSpacing(14)

        lbl_manual = QLabel("Códigos manuais  <span style='color:#888;font-weight:400'>"
                            "(um por linha)</span>")
        lbl_manual.setObjectName("label_section")
        input_layout.addWidget(lbl_manual)

        self._manual_input = QPlainTextEdit()
        self._manual_input.setPlaceholderText("Cole aqui seus códigos, um por linha…")
        self._manual_input.setFixedHeight(130)
        self._manual_input.setStyleSheet("font-family: monospace; font-size: 12px;")
        input_layout.addWidget(self._manual_input)

        sep = QWidget()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background-color: rgba(128,128,128,0.15);")
        input_layout.addWidget(sep)

        lbl_xlsx = QLabel("Planilha(s) .xlsx  <span style='color:#888;font-weight:400'>"
                          "(todas as abas são processadas automaticamente)</span>")
        lbl_xlsx.setObjectName("label_section")
        input_layout.addWidget(lbl_xlsx)

        xlsx_row = QHBoxLayout()
        xlsx_row.setSpacing(10)

        self._btn_browse = QPushButton("⊕  Selecionar arquivo(s)")
        self._btn_browse.setObjectName("btn_secondary")
        self._btn_browse.setFixedHeight(36)
        self._btn_browse.clicked.connect(self._browse_xlsx)
        xlsx_row.addWidget(self._btn_browse)

        self._lbl_xlsx_files = QLabel("Nenhum arquivo selecionado")
        self._lbl_xlsx_files.setObjectName("label_muted")
        self._lbl_xlsx_files.setWordWrap(True)
        xlsx_row.addWidget(self._lbl_xlsx_files, 1)

        self._btn_clear_xlsx = QPushButton("✕")
        self._btn_clear_xlsx.setObjectName("btn_ghost")
        self._btn_clear_xlsx.setFixedSize(28, 28)
        self._btn_clear_xlsx.setToolTip("Remover arquivo(s) selecionado(s)")
        self._btn_clear_xlsx.clicked.connect(self._clear_xlsx)
        self._btn_clear_xlsx.hide()
        xlsx_row.addWidget(self._btn_clear_xlsx)

        input_layout.addLayout(xlsx_row)
        layout.addWidget(input_box)

        # ── Barra de ações ─────────────────────────────────────────────────
        action_row = QHBoxLayout()
        action_row.setSpacing(12)

        self._btn_run = QPushButton("✦  Processar")
        self._btn_run.setObjectName("btn_primary")
        self._btn_run.setFixedWidth(160)
        self._btn_run.clicked.connect(self._run)
        action_row.addWidget(self._btn_run)

        self._btn_clear = QPushButton("Limpar")
        self._btn_clear.setObjectName("btn_ghost")
        self._btn_clear.clicked.connect(self._clear)
        action_row.addWidget(self._btn_clear)
        action_row.addStretch()
        layout.addLayout(action_row)

        # ── Progresso ──────────────────────────────────────────────────────
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.hide()
        layout.addWidget(self._progress_bar)

        self._status_lbl = QLabel("")
        self._status_lbl.setObjectName("label_muted")
        self._status_lbl.hide()
        layout.addWidget(self._status_lbl)

        # ── Resultado ──────────────────────────────────────────────────────
        self._result_widget = QWidget()
        res_layout = QVBoxLayout(self._result_widget)
        res_layout.setContentsMargins(0, 0, 0, 0)
        res_layout.setSpacing(12)

        lbl_res = QLabel("Resultado")
        lbl_res.setObjectName("label_section")
        lbl_res.setStyleSheet("color:#0071e3; font-weight:700;")
        res_layout.addWidget(lbl_res)

        stats_row = QHBoxLayout()
        self._stat_total     = StatPill("Códigos válidos", "—", "#28a745")
        self._stat_deleted   = StatPill("Deletados",       "—", "#d93025")
        self._stat_corrected = StatPill("Corrigidos",      "—", "#f2994a")
        self._stat_dupes     = StatPill("Duplicatas",      "—", "#888888")
        for w in (self._stat_total, self._stat_deleted, self._stat_corrected, self._stat_dupes):
            stats_row.addWidget(w)
        stats_row.addStretch()
        res_layout.addLayout(stats_row)

        self._lbl_alert = QLabel("")
        self._lbl_alert.setWordWrap(True)
        self._lbl_alert.setStyleSheet(
            "color:#f2994a; font-size:12px; background:transparent;"
        )
        self._lbl_alert.hide()
        res_layout.addWidget(self._lbl_alert)

        dl_row = QHBoxLayout()
        dl_row.setSpacing(10)

        self._btn_dl_xml = QPushButton("⬇  Salvar XML SFCC")
        self._btn_dl_xml.setObjectName("btn_secondary")
        self._btn_dl_xml.setFixedWidth(200)
        self._btn_dl_xml.clicked.connect(self._save_xml)
        dl_row.addWidget(self._btn_dl_xml)

        self._btn_dl_log = QPushButton("📊  Baixar Log Excel")
        self._btn_dl_log.setObjectName("btn_secondary")
        self._btn_dl_log.setFixedWidth(200)
        self._btn_dl_log.clicked.connect(self._save_log)
        self._btn_dl_log.hide()
        dl_row.addWidget(self._btn_dl_log)

        dl_row.addStretch()
        res_layout.addLayout(dl_row)

        self._result_widget.hide()
        layout.addWidget(self._result_widget)

        layout.addStretch()

        self._xlsx_paths: list[str] = []

    # ── Seleção de arquivos ───────────────────────────────────────────────
    def _browse_xlsx(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Selecionar planilha(s)", "", "Excel (*.xlsx *.xls)"
        )
        if not paths:
            return
        existing = set(self._xlsx_paths)
        for p in paths:
            if p not in existing:
                self._xlsx_paths.append(p)
                existing.add(p)
        self._refresh_xlsx_label()

    def _clear_xlsx(self) -> None:
        self._xlsx_paths.clear()
        self._refresh_xlsx_label()

    def _refresh_xlsx_label(self) -> None:
        if not self._xlsx_paths:
            self._lbl_xlsx_files.setText("Nenhum arquivo selecionado")
            self._btn_clear_xlsx.hide()
        elif len(self._xlsx_paths) == 1:
            self._lbl_xlsx_files.setText(Path(self._xlsx_paths[0]).name)
            self._btn_clear_xlsx.show()
        else:
            names = ", ".join(Path(p).name for p in self._xlsx_paths)
            self._lbl_xlsx_files.setText(f"{len(self._xlsx_paths)} arquivos: {names}")
            self._btn_clear_xlsx.show()

    # ── Execução ──────────────────────────────────────────────────────────
    def _run(self) -> None:
        coupon_id   = self._coupon_id.text().strip()
        manual_text = self._manual_input.toPlainText().strip()

        if not coupon_id:
            QMessageBox.warning(self, "Cupons SFCC", "Informe o <b>Coupon ID</b>.")
            return

        if not manual_text and not self._xlsx_paths:
            QMessageBox.warning(
                self, "Cupons SFCC",
                "Insira códigos manualmente ou selecione ao menos uma planilha .xlsx."
            )
            return

        self._btn_run.setEnabled(False)
        self._result_widget.hide()
        self._lbl_alert.hide()
        self._progress_bar.setValue(0)
        self._progress_bar.show()
        self._status_lbl.show()

        self._worker = CupomWorker(coupon_id, manual_text, list(self._xlsx_paths), self)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.error_msg.connect(self._on_error)
        self._worker.start()

    # ── Callbacks de progresso / resultado ────────────────────────────────
    def _on_progress(self, pct: int, msg: str) -> None:
        self._progress_bar.setValue(pct)
        self._status_lbl.setText(msg)

    def _on_finished(self, result: CupomResult) -> None:
        self._result = result
        self._btn_run.setEnabled(True)
        self._progress_bar.setValue(100)

        if result.error:
            HistoryEngine.add_entry(
                "Cupons",
                self._coupon_id.text().strip() or "N/A",
                f"Falha na execução: {result.error[:200]}",
                status="falha",
            )
            QMessageBox.critical(self, "Erro — Cupons SFCC", result.error)
            self._progress_bar.hide()
            self._status_lbl.hide()
            return

        s = result.stats
        self._stat_total.set_value(str(s.get("total", 0)),     "#28a745")
        self._stat_deleted.set_value(str(s.get("deleted", 0)),
                                     "#d93025" if s.get("deleted") else "#888")
        self._stat_corrected.set_value(str(s.get("corrected", 0)),
                                       "#f2994a" if s.get("corrected") else "#888")
        self._stat_dupes.set_value(str(s.get("duplicates", 0)),
                                   "#888888")

        if result.log_workbook:
            self._btn_dl_log.show()
            parts = []
            if s.get("deleted"):
                parts.append(f"{s['deleted']} cupom(ns) com caracteres especiais deletado(s)")
            if s.get("corrected"):
                parts.append(f"{s['corrected']} cupom(ns) minúsculo(s) corrigido(s) para maiúsculas")
            if parts:
                self._lbl_alert.setText("⚠  " + ".  ".join(parts) + ".  Consulte o Log Excel.")
                self._lbl_alert.show()
        else:
            self._btn_dl_log.hide()

        self._result_widget.show()
        self._status_lbl.hide()

        # Contagens (Tarefa 7): acerto = códigos válidos no XML; erro = códigos
        # deletados por caractere inválido. Corrigidos/duplicatas são warning/
        # neutro (seguem só no texto de details), e não há "total lido" bruto
        # no stats do engine — total fica NULL.
        coupon_id = self._coupon_id.text().strip()
        HistoryEngine.add_entry(
            "Cupons",
            coupon_id,
            f"XML gerado — {s.get('total', 0)} códigos válidos.",
            f"Deletados: {s.get('deleted', 0)} | "
            f"Corrigidos: {s.get('corrected', 0)} | "
            f"Duplicatas: {s.get('duplicates', 0)}",
            ok_count=s.get("total", 0),
            error_count=s.get("deleted", 0),
            breakdown={
                k: v for k, v in (
                    ("🗑️ Deletados (caractere inválido)", s.get("deleted", 0)),
                    ("🔤 Corrigidos p/ maiúsculas", s.get("corrected", 0)),
                    ("👥 Duplicatas ignoradas", s.get("duplicates", 0)),
                ) if v > 0
            } or None,
        )

        if p := self.parent():
            if hasattr(p, "show_status"):
                p.show_status(
                    f"Cupons: {s.get('total', 0)} códigos prontos — {coupon_id}"
                )

    def _on_error(self, msg: str) -> None:
        self._btn_run.setEnabled(True)
        self._progress_bar.hide()
        self._status_lbl.hide()
        HistoryEngine.add_entry(
            "Cupons", "N/A", f"Falha na execução: {msg[:200]}", status="falha"
        )
        QMessageBox.critical(self, "Erro — Cupons SFCC", msg)

    # ── Salvar arquivos ───────────────────────────────────────────────────
    def _save_xml(self) -> None:
        if not self._result or not self._result.xml_content:
            return
        coupon_id = self._coupon_id.text().strip() or "cupons"
        default   = f"{coupon_id}.xml"
        path, _   = QFileDialog.getSaveFileName(
            self, "Salvar XML SFCC", default, "XML (*.xml)"
        )
        if path:
            with open(path, "wb") as f:
                f.write(self._result.xml_content)
            QMessageBox.information(self, "Salvo", f"XML salvo em:\n{path}")

    def _save_log(self) -> None:
        if not self._result or not self._result.log_workbook:
            return
        coupon_id = self._coupon_id.text().strip() or "cupons"
        default   = f"LOG_INCONSISTENCIAS_{coupon_id}.xlsx"
        path, _   = QFileDialog.getSaveFileName(
            self, "Salvar Log Excel", default, "Excel (*.xlsx)"
        )
        if path:
            self._result.log_workbook.save(path)
            QMessageBox.information(self, "Salvo", f"Log salvo em:\n{path}")

    # ── Limpar ────────────────────────────────────────────────────────────
    def _clear(self) -> None:
        self._coupon_id.clear()
        self._manual_input.clear()
        self._xlsx_paths.clear()
        self._refresh_xlsx_label()
        self._progress_bar.setValue(0)
        self._progress_bar.hide()
        self._status_lbl.hide()
        self._lbl_alert.hide()
        self._result_widget.hide()
        self._btn_dl_log.hide()
        self._btn_run.setEnabled(True)
        self._result = None
