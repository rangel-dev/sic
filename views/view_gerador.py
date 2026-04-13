"""
Gerador View – Excel → Pricebook XML generator.
"""
from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from views.widgets import Divider, DropZone, SectionHeader, StatPill
from workers.worker_gerador import GeradorWorker


class GeradorView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: GeradorWorker | None = None
        self._result: dict | None = None
        self._setup_ui()

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        outer.addWidget(SectionHeader(
            "⊕  Gerador de Pricebook",
            "Converte planilhas Excel em XMLs de Pricebook para o Salesforce Demandware"
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

        # Mode selector
        mode_box = QGroupBox("Modo de Geração")
        mode_layout = QHBoxLayout(mode_box)
        mode_layout.setContentsMargins(16, 18, 16, 14)
        mode_layout.setSpacing(24)

        self._bg = QButtonGroup(self)
        self._radio_full  = QRadioButton("Full Grade  (todos os produtos)")
        self._radio_delta = QRadioButton("Delta Ajustes  (somente alterados)")
        self._radio_full.setChecked(True)
        self._bg.addButton(self._radio_full,  0)
        self._bg.addButton(self._radio_delta, 1)
        self._bg.buttonClicked.connect(self._on_mode_changed)

        mode_layout.addWidget(self._radio_full)
        mode_layout.addWidget(self._radio_delta)
        mode_layout.addStretch()
        layout.addWidget(mode_box)

        # File inputs
        files_box = QGroupBox("Arquivos de Entrada")
        files_layout = QVBoxLayout(files_box)
        files_layout.setContentsMargins(16, 18, 16, 14)
        files_layout.setSpacing(12)

        lbl_excel = QLabel("Planilha(s) Excel")
        lbl_excel.setObjectName("label_section")
        files_layout.addWidget(lbl_excel)

        self._dz_excel = DropZone(
            "Arraste o(s) Excel aqui  —  GRADE DE ATIVAÇÃO",
            "Excel (*.xlsx *.xlsm *.xls)",
            multiple=True,
        )
        self._dz_excel.setToolTip(
            "A planilha deve conter a aba 'GRADE DE ATIVAÇÃO' com colunas: SKU, DE, POR"
        )
        files_layout.addWidget(self._dz_excel)

        # Delta base XML (hidden until delta mode selected)
        self._delta_widget = QWidget()
        delta_inner = QVBoxLayout(self._delta_widget)
        delta_inner.setContentsMargins(0, 0, 0, 0)
        delta_inner.setSpacing(6)
        lbl_base = QLabel("Pricebook XML Base (referência para o Delta)")
        lbl_base.setObjectName("label_section")
        delta_inner.addWidget(lbl_base)
        self._dz_base = DropZone(
            "Arraste o Pricebook XML atual (base de comparação)",
            "XML (*.xml)",
        )
        delta_inner.addWidget(self._dz_base)
        self._delta_widget.hide()
        files_layout.addWidget(self._delta_widget)

        layout.addWidget(files_box)

        # Action bar
        action_row = QHBoxLayout()
        action_row.setSpacing(12)

        self._btn_run = QPushButton("⊕  Gerar Pricebook XML")
        self._btn_run.setObjectName("btn_primary")
        self._btn_run.setFixedWidth(220)
        self._btn_run.clicked.connect(self._run)
        action_row.addWidget(self._btn_run)

        self._btn_clear = QPushButton("Limpar")
        self._btn_clear.setObjectName("btn_ghost")
        self._btn_clear.clicked.connect(self._clear)
        action_row.addWidget(self._btn_clear)

        action_row.addStretch()
        layout.addLayout(action_row)

        # Progress
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.hide()
        layout.addWidget(self._progress_bar)

        self._status_lbl = QLabel("")
        self._status_lbl.setObjectName("label_muted")
        self._status_lbl.hide()
        layout.addWidget(self._status_lbl)

        # Stats row (shown after generation)
        self._stats_widget = QWidget()
        stats_row = QHBoxLayout(self._stats_widget)
        stats_row.setContentsMargins(0, 0, 0, 0)
        stats_row.setSpacing(12)
        self._stat_total  = StatPill("Total SKUs",  "—", "#f0f0f0")
        self._stat_natura = StatPill("Natura",       "—", "#FF8050")
        self._stat_avon   = StatPill("Avon",         "—", "#bb88ff")
        self._stat_mode   = StatPill("Modo",         "—", "#888888")
        for w in (self._stat_total, self._stat_natura, self._stat_avon, self._stat_mode):
            stats_row.addWidget(w)
        stats_row.addStretch()
        self._stats_widget.hide()
        layout.addWidget(self._stats_widget)

        # Download button
        self._btn_download = QPushButton("⬇  Salvar XML")
        self._btn_download.setObjectName("btn_secondary")
        self._btn_download.setFixedWidth(160)
        self._btn_download.clicked.connect(self._save_xml)
        self._btn_download.hide()
        layout.addWidget(self._btn_download)

        layout.addStretch()

    # ── Slots ─────────────────────────────────────────────────────────────
    def _on_mode_changed(self):
        is_delta = self._radio_delta.isChecked()
        self._delta_widget.setVisible(is_delta)

    def _run(self):
        excel_paths = self._dz_excel.file_paths
        if not excel_paths:
            QMessageBox.warning(self, "Gerador", "Selecione ao menos uma planilha Excel.")
            return

        mode = "delta" if self._radio_delta.isChecked() else "full"
        base_xml = self._dz_base.file_path if mode == "delta" else None

        self._btn_run.setEnabled(False)
        self._btn_download.hide()
        self._stats_widget.hide()
        self._progress_bar.setValue(0)
        self._progress_bar.show()
        self._status_lbl.show()

        self._worker = GeradorWorker(excel_paths, mode, base_xml, self)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.error_msg.connect(self._on_error)
        self._worker.start()

    def _on_progress(self, pct: int, msg: str):
        self._progress_bar.setValue(pct)
        self._status_lbl.setText(msg)

    def _on_finished(self, result: dict):
        self._result = result
        self._btn_run.setEnabled(True)

        s = result.get("stats", {})
        self._stat_total.set_value(str(s.get("total", 0)))
        self._stat_natura.set_value(str(s.get("natura", 0)), "#FF8050")
        self._stat_avon.set_value(str(s.get("avon", 0)),    "#bb88ff")
        self._stat_mode.set_value(s.get("mode", "—").upper(), "#888")
        self._stats_widget.show()
        self._btn_download.show()

        if parent := self.parent():
            if hasattr(parent, "show_status"):
                parent.show_status(
                    f"Gerador: {s.get('total', 0)} SKUs processados ({s.get('mode', '')})"
                )

    def _on_error(self, msg: str):
        self._btn_run.setEnabled(True)
        self._progress_bar.hide()
        self._status_lbl.hide()
        QMessageBox.critical(self, "Erro — Gerador", msg)

    def _save_xml(self):
        if not self._result or not self._result.get("xml_content"):
            return
        brand = self._result.get("brand", "brand").upper()
        mode  = self._result.get("stats", {}).get("mode", "full").upper()
        default_name = f"PRICEBOOK_{brand}_{mode}_SYNC.xml"

        path, _ = QFileDialog.getSaveFileName(
            self, "Salvar Pricebook XML", default_name, "XML (*.xml)"
        )
        if path:
            with open(path, "wb") as f:
                f.write(self._result["xml_content"])
            QMessageBox.information(self, "Salvo", f"XML salvo em:\n{path}")

    def _clear(self):
        self._dz_excel.clear()
        self._dz_base.clear()
        self._progress_bar.setValue(0)
        self._progress_bar.hide()
        self._status_lbl.hide()
        self._stats_widget.hide()
        self._btn_download.hide()
        self._result = None
        self._radio_full.setChecked(True)
        self._delta_widget.hide()
        self._btn_run.setEnabled(True)
