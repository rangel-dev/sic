"""
Exportador View – unified Excel → Pricebook XML and/or Catalog XML.
Replaces the separate Gerador and Sync tabs.
"""
from __future__ import annotations

import openpyxl
from datetime import date
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
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
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.ui.components.base_widgets import Divider, DropZone, SectionHeader, StatPill
from src.core.excel_reader import find_grade_sheet_name, dominant_brand
from src.core.history_engine import HistoryEngine
from src.core.sync_engine import SyncResult
from src.workers.worker_exportador import ExportadorWorker, ExportResult


BRAND_COLORS: dict[str, str] = {
    "natura": "#f59e0b",
    "avon":   "#c4b5fd",
    "ml":     "#60a5fa",
}
BRAND_LABELS: dict[str, str] = {
    "natura": "Natura",
    "avon":   "Avon",
    "ml":     "CB (Minha Loja)",
}


def _sniff_brand(path: str) -> str | None:
    """Quick brand detection for UI badge display — reads first 300 rows only."""
    try:
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        sheet_name = find_grade_sheet_name(wb)
        if sheet_name is None:
            wb.close()
            return None
        ws = wb[sheet_name]
        nat = avn = 0
        for row in ws.iter_rows(max_row=300, values_only=True):
            for cell in row:
                if cell and isinstance(cell, str):
                    v = cell.strip().upper()
                    if v.startswith("NATBRA-"):
                        nat += 1
                    elif v.startswith("AVNBRA-"):
                        avn += 1
            if nat + avn >= 5:
                break
        wb.close()
        if nat == 0 and avn == 0:
            return None
        return dominant_brand(nat, avn)
    except Exception:
        return None


class ExportadorView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: ExportadorWorker | None = None
        self._result: ExportResult | None = None
        self._file_brands: dict[str, str | None] = {}
        self._setup_ui()

    # ── UI Construction ───────────────────────────────────────────────────
    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        outer.addWidget(SectionHeader(
            "⊗  Exportador de Catálogo",
            "Gere Pricebook XML e/ou Catálogo XML a partir de uma única grade Excel. "
            "Selecione os artefatos desejados — a marca é detectada automaticamente."
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

        # ── Grade de Ativação ──────────────────────────────────────────────
        excel_box = QGroupBox("Grade de Ativação")
        excel_layout = QVBoxLayout(excel_box)
        excel_layout.setContentsMargins(16, 18, 16, 14)
        excel_layout.setSpacing(12)

        lbl_excel = QLabel(
            "Insira até <b>duas grades</b> — uma "
            "<b style='color:#f59e0b'>Natura</b> e uma "
            "<b style='color:#c4b5fd'>Avon</b>. "
            "A marca é detectada automaticamente."
        )
        lbl_excel.setObjectName("label_section")
        lbl_excel.setWordWrap(True)
        excel_layout.addWidget(lbl_excel)

        self._dz_excel = DropZone(
            "Arraste a(s) grade(s) aqui  —  GRADE DE ATIVAÇÃO\n"
            "(até 2 arquivos: Natura e/ou Avon)",
            "Excel (*.xlsx *.xlsm *.xls)",
            multiple=True,
        )
        self._dz_excel.files_selected.connect(self._on_excel_selected)
        excel_layout.addWidget(self._dz_excel)

        self._badges_row = QHBoxLayout()
        self._badges_row.setSpacing(10)
        self._badge_a = QLabel("")
        self._badge_b = QLabel("")
        for badge in (self._badge_a, self._badge_b):
            badge.setFixedHeight(28)
            badge.hide()
            self._badges_row.addWidget(badge)
        self._badges_row.addStretch()
        excel_layout.addLayout(self._badges_row)

        layout.addWidget(excel_box)

        # ── Artefatos a Gerar ──────────────────────────────────────────────
        art_box = QGroupBox("Artefatos a Gerar")
        art_layout = QVBoxLayout(art_box)
        art_layout.setContentsMargins(16, 18, 16, 14)
        art_layout.setSpacing(14)

        # Pricebook
        self._chk_pb = QCheckBox("Pricebook XML  (preços DE e POR)")
        self._chk_pb.setChecked(True)
        self._chk_pb.toggled.connect(self._on_pb_toggled)
        art_layout.addWidget(self._chk_pb)

        self._pb_options = QWidget()
        pb_opt_layout = QVBoxLayout(self._pb_options)
        pb_opt_layout.setContentsMargins(24, 0, 0, 0)
        pb_opt_layout.setSpacing(8)

        mode_row = QHBoxLayout()
        self._bg = QButtonGroup(self)
        self._radio_full  = QRadioButton("Full Grade  (todos os produtos)")
        self._radio_delta = QRadioButton("Delta Ajustes  (somente alterados)")
        self._radio_full.setChecked(True)
        self._bg.addButton(self._radio_full,  0)
        self._bg.addButton(self._radio_delta, 1)
        self._bg.buttonClicked.connect(self._on_mode_changed)
        mode_row.addWidget(self._radio_full)
        mode_row.addWidget(self._radio_delta)
        mode_row.addStretch()
        pb_opt_layout.addLayout(mode_row)

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
        pb_opt_layout.addWidget(self._delta_widget)

        art_layout.addWidget(self._pb_options)

        # Separator line
        sep = QWidget()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background-color: rgba(128,128,128,0.2);")
        art_layout.addWidget(sep)

        # Catálogo
        self._chk_cat = QCheckBox("Catálogo XML  (visibilidade, selos e listas de vitrine)")
        self._chk_cat.setChecked(False)
        self._chk_cat.toggled.connect(self._on_cat_toggled)
        art_layout.addWidget(self._chk_cat)

        self._cat_options = QWidget()
        cat_opt_layout = QVBoxLayout(self._cat_options)
        cat_opt_layout.setContentsMargins(24, 0, 0, 0)
        cat_opt_layout.setSpacing(8)

        lbl_xml = QLabel("Catálogo(s) XML  —  Master Data do Salesforce (exportados há >10 min)")
        lbl_xml.setObjectName("label_section")
        cat_opt_layout.addWidget(lbl_xml)

        self._dz_catalog = DropZone(
            "Arraste os XMLs de Catálogo (Natura, Avon, Minha Loja)",
            "XML (*.xml)",
            multiple=True,
        )
        self._dz_catalog.setToolTip(
            "Regra de Ouro: os XMLs devem ter sido exportados há mais de 10 minutos."
        )
        cat_opt_layout.addWidget(self._dz_catalog)
        self._cat_options.hide()
        art_layout.addWidget(self._cat_options)

        layout.addWidget(art_box)

        # ── Action bar ────────────────────────────────────────────────────
        action_row = QHBoxLayout()
        action_row.setSpacing(12)

        self._btn_run = QPushButton("⊗  Exportar")
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

        # ── Progress ──────────────────────────────────────────────────────
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.hide()
        layout.addWidget(self._progress_bar)

        self._status_lbl = QLabel("")
        self._status_lbl.setObjectName("label_muted")
        self._status_lbl.hide()
        layout.addWidget(self._status_lbl)

        self._log_box = QTextEdit()
        self._log_box.setReadOnly(True)
        self._log_box.setFixedHeight(160)
        self._log_box.setStyleSheet(
            "background-color:#0b0c10; color:#e0e0e0; "
            "font-family:monospace; font-size:11px;"
        )
        self._log_box.hide()
        layout.addWidget(self._log_box)

        # Warnings (Sync file-age alerts)
        self._warn_lbl = QLabel("")
        self._warn_lbl.setWordWrap(True)
        self._warn_lbl.setStyleSheet("color:#ffcc80; font-size:11px; background:transparent;")
        self._warn_lbl.hide()
        layout.addWidget(self._warn_lbl)

        # ── Resultados — Pricebook ─────────────────────────────────────────
        self._pb_result_widget = QWidget()
        pb_res_layout = QVBoxLayout(self._pb_result_widget)
        pb_res_layout.setContentsMargins(0, 0, 0, 0)
        pb_res_layout.setSpacing(8)

        lbl_pb_res = QLabel("Pricebook")
        lbl_pb_res.setObjectName("label_section")
        lbl_pb_res.setStyleSheet("color:#f59e0b; font-weight:700;")
        pb_res_layout.addWidget(lbl_pb_res)

        pb_stats_row = QHBoxLayout()
        self._stat_pb_total  = StatPill("Total SKUs",          "—", "#f0f0f0")
        self._stat_pb_nat    = StatPill("Pricebook Natura",    "—", BRAND_COLORS["natura"])
        self._stat_pb_avn    = StatPill("Pricebook Avon",      "—", BRAND_COLORS["avon"])
        self._stat_pb_ml     = StatPill("Pricebook Minha Loja","—", BRAND_COLORS["ml"])
        self._stat_pb_mode   = StatPill("Modo",                "—", "#888888")
        for w in (self._stat_pb_total, self._stat_pb_nat, self._stat_pb_avn,
                  self._stat_pb_ml, self._stat_pb_mode):
            pb_stats_row.addWidget(w)
        pb_stats_row.addStretch()
        pb_res_layout.addLayout(pb_stats_row)

        self._btn_dl_pb = QPushButton("⬇  Salvar Pricebook XML")
        self._btn_dl_pb.setObjectName("btn_secondary")
        self._btn_dl_pb.setFixedWidth(210)
        self._btn_dl_pb.clicked.connect(self._save_pricebook)
        pb_res_layout.addWidget(self._btn_dl_pb)

        self._pb_result_widget.hide()
        layout.addWidget(self._pb_result_widget)

        # ── Resultados — Catálogo ──────────────────────────────────────────
        self._cat_result_widget = QWidget()
        cat_res_layout = QVBoxLayout(self._cat_result_widget)
        cat_res_layout.setContentsMargins(0, 0, 0, 0)
        cat_res_layout.setSpacing(8)

        lbl_cat_res = QLabel("Catálogo")
        lbl_cat_res.setObjectName("label_section")
        lbl_cat_res.setStyleSheet("color:#7e57c2; font-weight:700;")
        cat_res_layout.addWidget(lbl_cat_res)

        cat_stats_r1 = QHBoxLayout()
        self._s_xml   = StatPill("XML Master",    "—", "#66bb6a")
        self._s_grade = StatPill("Grade (Bruta)", "—", "#42a5f5")
        self._s_match = StatPill("Match",         "—", "#ab47bc")
        self._s_on    = StatPill("Ativados",      "—", "#ef5350")
        self._s_vis   = StatPill("Vitrine",       "—", "#ffa726")
        self._s_cut   = StatPill("Cortes Facão",  "—", "#ff7043")
        self._s_moff  = StatPill("Mestres OFF",   "—", "#8d6e63")
        for w in (self._s_xml, self._s_grade, self._s_match, self._s_on,
                  self._s_vis, self._s_cut, self._s_moff):
            cat_stats_r1.addWidget(w)
        cat_stats_r1.addStretch()
        cat_res_layout.addLayout(cat_stats_r1)

        cat_stats_r2 = QHBoxLayout()
        self._s_list  = StatPill("Abas Lista",   "—", "#7e57c2")
        self._s_seal  = StatPill("Selos Novos",  "—", "#26a69a")
        self._s_delta = StatPill("Total Deltas", "—", "#888888")
        for w in (self._s_list, self._s_seal, self._s_delta):
            cat_stats_r2.addWidget(w)
        cat_stats_r2.addStretch()
        cat_res_layout.addLayout(cat_stats_r2)

        self._lbl_lists = QLabel("Comparativo de Sincronismo por Lista")
        self._lbl_lists.setObjectName("label_section")
        self._lbl_lists.setStyleSheet("color:#7e57c2;")
        cat_res_layout.addWidget(self._lbl_lists)

        self._table = QTableWidget()
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels([
            "ID DA LISTA", "NO EXCEL (ALVO)", "NO XML (ANTIGO)", "STATUS DELTA"
        ])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.verticalHeader().hide()
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setSelectionMode(QTableWidget.NoSelection)
        self._table.setFixedHeight(220)
        cat_res_layout.addWidget(self._table)

        dl_cat_row = QHBoxLayout()
        self._btn_dl_cat = QPushButton("⬇  Salvar Catálogo XML")
        self._btn_dl_cat.setObjectName("btn_secondary")
        self._btn_dl_cat.setFixedWidth(210)
        self._btn_dl_cat.clicked.connect(self._save_catalog)
        dl_cat_row.addWidget(self._btn_dl_cat)

        self._btn_dl_report = QPushButton("📊  Baixar Relatório XLSX")
        self._btn_dl_report.setObjectName("btn_secondary")
        self._btn_dl_report.setFixedWidth(210)
        self._btn_dl_report.clicked.connect(self._save_report)
        dl_cat_row.addWidget(self._btn_dl_report)

        dl_cat_row.addStretch()
        cat_res_layout.addLayout(dl_cat_row)

        self._cat_result_widget.hide()
        layout.addWidget(self._cat_result_widget)

        # ── Resultados — Inventory (BRD-011, independente de Pricebook/Catálogo) ──
        self._inv_result_widget = QWidget()
        inv_res_layout = QVBoxLayout(self._inv_result_widget)
        inv_res_layout.setContentsMargins(0, 0, 0, 0)
        inv_res_layout.setSpacing(8)

        lbl_inv_res = QLabel("Inventory")
        lbl_inv_res.setObjectName("label_section")
        lbl_inv_res.setStyleSheet("color:#60a5fa; font-weight:700;")
        inv_res_layout.addWidget(lbl_inv_res)

        dl_inv_row = QHBoxLayout()
        self._btn_dl_inv_nat = QPushButton("⬇  Salvar Inventory Natura XML")
        self._btn_dl_inv_nat.setObjectName("btn_inv_natura")
        self._btn_dl_inv_nat.setFixedWidth(230)
        self._btn_dl_inv_nat.clicked.connect(self._save_inventory_natura)
        self._btn_dl_inv_nat.hide()
        dl_inv_row.addWidget(self._btn_dl_inv_nat)

        self._btn_dl_inv_avn = QPushButton("⬇  Salvar Inventory Avon XML")
        self._btn_dl_inv_avn.setObjectName("btn_inv_avon")
        self._btn_dl_inv_avn.setFixedWidth(230)
        self._btn_dl_inv_avn.clicked.connect(self._save_inventory_avon)
        self._btn_dl_inv_avn.hide()
        dl_inv_row.addWidget(self._btn_dl_inv_avn)

        dl_inv_row.addStretch()
        inv_res_layout.addLayout(dl_inv_row)

        self._inv_result_widget.hide()
        layout.addWidget(self._inv_result_widget)

        layout.addStretch()

    # ── Excel file handling ───────────────────────────────────────────────
    def _on_excel_selected(self, paths: list[str]) -> None:
        if len(paths) > 2:
            QMessageBox.warning(
                self, "Exportador",
                "Insira no máximo <b>duas grades</b>: uma Natura e uma Avon."
            )
            self._dz_excel.clear()
            self._reset_badges()
            return

        for p in paths:
            if p not in self._file_brands:
                self._file_brands[p] = _sniff_brand(p)

        for old in list(self._file_brands):
            if old not in set(paths):
                del self._file_brands[old]

        brands = [b for b in self._file_brands.values() if b]
        if len(brands) == 2 and brands[0] == brands[1]:
            brand_name = BRAND_LABELS.get(brands[0], brands[0].capitalize())
            QMessageBox.warning(
                self, "Grades incompatíveis",
                f"Ambas as grades pertencem à marca <b>{brand_name}</b>.<br><br>"
                "Insira uma grade <b>Natura</b> e uma grade <b>Avon</b>.",
            )
            self._dz_excel.clear()
            self._file_brands.clear()
            self._reset_badges()
            return

        self._update_badges(paths)

    def _update_badges(self, paths: list[str]) -> None:
        for i, badge in enumerate([self._badge_a, self._badge_b]):
            if i < len(paths):
                brand = self._file_brands.get(paths[i])
                self._apply_badge(badge, brand)
                badge.show()
            else:
                badge.hide()

    def _apply_badge(self, badge: QLabel, brand: str | None) -> None:
        if brand == "natura":
            color, text = BRAND_COLORS["natura"], "🟧  Natura detectada ✓"
        elif brand == "avon":
            color, text = BRAND_COLORS["avon"], "🟪  Avon detectada ✓"
        else:
            color, text = "#888888", "❓  Marca não identificada"
        badge.setText(text)
        badge.setStyleSheet(
            f"font-size:12px; font-weight:700; color:{color}; "
            "border-radius:5px; padding:0 12px; background:transparent;"
        )

    def _reset_badges(self) -> None:
        self._badge_a.hide()
        self._badge_b.hide()

    # ── Checkbox / mode toggles ───────────────────────────────────────────
    def _on_pb_toggled(self, checked: bool) -> None:
        self._pb_options.setVisible(checked)

    def _on_cat_toggled(self, checked: bool) -> None:
        self._cat_options.setVisible(checked)
        if checked:
            self._log_box.clear()
            self._log_box.append("<b>LOG DE ATIVIDADE</b><br>")

    def _on_mode_changed(self) -> None:
        self._delta_widget.setVisible(self._radio_delta.isChecked())

    # ── Run ───────────────────────────────────────────────────────────────
    def _run(self) -> None:
        gen_pb  = self._chk_pb.isChecked()
        gen_cat = self._chk_cat.isChecked()

        if not gen_pb and not gen_cat:
            QMessageBox.warning(
                self, "Exportador",
                "Selecione ao menos um artefato: <b>Pricebook</b> ou <b>Catálogo</b>."
            )
            return

        excel_paths = [
            p for p, b in self._file_brands.items() if b in ("natura", "avon")
        ]
        if not excel_paths:
            QMessageBox.warning(
                self, "Exportador",
                "Selecione ao menos uma grade Excel válida com SKUs "
                "NATBRA- (Natura) ou AVNBRA- (Avon)."
            )
            return

        if gen_cat and not self._dz_catalog.file_paths:
            QMessageBox.warning(
                self, "Exportador",
                "O Catálogo XML requer os arquivos de <b>Master Data</b>.<br>"
                "Arraste os XMLs exportados do Salesforce no campo Catálogo."
            )
            return

        mode     = "delta" if self._radio_delta.isChecked() else "full"
        base_xml = self._dz_base.file_path if mode == "delta" else None
        cat_xmls = self._dz_catalog.file_paths if gen_cat else []

        self._btn_run.setEnabled(False)
        self._pb_result_widget.hide()
        self._cat_result_widget.hide()
        self._inv_result_widget.hide()
        self._warn_lbl.hide()
        self._progress_bar.setValue(0)
        self._progress_bar.show()
        self._status_lbl.show()

        if gen_cat:
            self._log_box.clear()
            self._log_box.append("<b>LOG DE ATIVIDADE</b><br>")
            self._log_box.show()

        self._worker = ExportadorWorker(
            excel_paths, gen_pb, mode, base_xml, gen_cat, cat_xmls, self
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.error_msg.connect(self._on_error)
        self._worker.start()

    # ── Progress / result callbacks ───────────────────────────────────────
    def _on_progress(self, pct: int, msg: str) -> None:
        if msg.startswith(">"):
            self._log_box.append(msg)
        else:
            self._progress_bar.setValue(pct)
            self._status_lbl.setText(msg)

    def _on_finished(self, result: ExportResult) -> None:
        self._result = result
        self._btn_run.setEnabled(True)
        self._progress_bar.setValue(100)

        # ── Pricebook result ───────────────────────────────────────────────
        if result.pricebook is not None:
            pb = result.pricebook
            if pb.get("error"):
                QMessageBox.critical(
                    self, "Erro — Pricebook",
                    f"Falha ao gerar Pricebook:\n\n{pb['error']}"
                )
            else:
                s      = pb.get("stats", {})
                brands = s.get("brands", [])

                self._stat_pb_total.set_value(str(s.get("total", 0)))
                self._stat_pb_nat.set_value("✓" if "natura" in brands else "—",
                                             BRAND_COLORS["natura"] if "natura" in brands else "#444")
                self._stat_pb_avn.set_value("✓" if "avon" in brands else "—",
                                             BRAND_COLORS["avon"] if "avon" in brands else "#444")
                self._stat_pb_ml.set_value("✓", BRAND_COLORS["ml"])
                self._stat_pb_mode.set_value(s.get("mode", "—").upper(), "#888")

                self._pb_result_widget.show()

                HistoryEngine.add_entry(
                    "Exportador",
                    pb.get("brand", "Desconhecida"),
                    f"Pricebook gerado ({s.get('mode', 'full').upper()}) — "
                    f"{s.get('total', 0)} SKUs.",
                )

        # ── Catalog result ─────────────────────────────────────────────────
        if result.catalog is not None:
            cat: SyncResult = result.catalog
            if cat.error:
                QMessageBox.critical(
                    self, "Erro — Catálogo",
                    f"Falha ao gerar Catálogo:\n\n{cat.error}"
                )
            else:
                if cat.warnings:
                    self._warn_lbl.setText("⚠  " + "  |  ".join(cat.warnings))
                    self._warn_lbl.show()

                s = cat.stats
                self._s_xml.set_value(str(s.get("xml", 0)),   "#66bb6a")
                self._s_grade.set_value(str(s.get("grade", 0)), "#42a5f5")
                self._s_match.set_value(str(s.get("match", 0)), "#ab47bc")
                self._s_on.set_value(str(s.get("onC", 0)),    "#ef5350")
                self._s_vis.set_value(str(s.get("visC", 0)),  "#ffa726")
                self._s_cut.set_value(str(s.get("cut", 0)),   "#ff7043")
                self._s_moff.set_value(str(s.get("mOff", 0)), "#8d6e63")
                self._s_list.set_value(str(s.get("lists", 0)),  "#7e57c2")
                self._s_seal.set_value(str(s.get("sealC", 0)), "#26a69a")
                self._s_delta.set_value(str(s.get("deltas", 0)), "#888888")

                lists = s.get("lists_details", [])
                self._table.setRowCount(len(lists))
                for r_idx, row_data in enumerate(lists):
                    item_id = QTableWidgetItem(str(row_data["id"]))
                    item_id.setForeground(Qt.GlobalColor.cyan)
                    self._table.setItem(r_idx, 0, item_id)
                    self._table.setItem(r_idx, 1, QTableWidgetItem(f'{row_data["excel"]} itens'))
                    self._table.setItem(r_idx, 2, QTableWidgetItem(f'{row_data["xml"]} itens'))
                    status = str(row_data["status"])
                    item_st = QTableWidgetItem(status)
                    item_st.setForeground(
                        Qt.GlobalColor.green if "✓" in status else Qt.GlobalColor.yellow
                    )
                    self._table.setItem(r_idx, 3, item_st)

                self._cat_result_widget.show()

                HistoryEngine.add_entry(
                    "Exportador",
                    cat.catalog_id or "Desconhecida",
                    f"Catálogo gerado: {s.get('deltas', 0)} modificações.",
                )

        # ── Inventory result (BRD-011) — independente de Pricebook/Catálogo ─
        has_nat_inv = bool(result.inventory_natura_xml)
        has_avn_inv = bool(result.inventory_avon_xml)
        self._btn_dl_inv_nat.setVisible(has_nat_inv)
        self._btn_dl_inv_avn.setVisible(has_avn_inv)
        self._inv_result_widget.setVisible(has_nat_inv or has_avn_inv)

        if p := self.parent():
            if hasattr(p, "show_status"):
                parts = []
                if result.pricebook and not result.pricebook.get("error"):
                    parts.append(f"Pricebook {result.pricebook.get('stats', {}).get('total', 0)} SKUs")
                if result.catalog and not result.catalog.error:
                    parts.append(f"Catálogo {result.catalog.stats.get('deltas', 0)} deltas")
                p.show_status("Exportador: " + "  |  ".join(parts) if parts else "Exportação concluída")

    def _on_error(self, msg: str) -> None:
        self._btn_run.setEnabled(True)
        self._progress_bar.hide()
        self._status_lbl.hide()
        QMessageBox.critical(self, "Erro — Exportador", msg)

    # ── Save handlers ─────────────────────────────────────────────────────
    def _save_pricebook(self) -> None:
        if not self._result or not self._result.pricebook:
            return
        xml = self._result.pricebook.get("xml_content")
        if not xml:
            return

        s      = self._result.pricebook.get("stats", {})
        brands = s.get("brands", [])
        today  = date.today()
        brands_str = "_".join(b.upper() for b in brands) + "+CB" if brands else "CB"
        default = f"---{today.strftime('%d')}.{today.strftime('%m')}-{brands_str}-PRICEBOOK-AJUSTE.xml"

        path, _ = QFileDialog.getSaveFileName(self, "Salvar Pricebook XML", default, "XML (*.xml)")
        if path:
            with open(path, "wb") as f:
                f.write(xml)
            QMessageBox.information(self, "Salvo", f"Pricebook salvo em:\n{path}")

    def _save_catalog(self) -> None:
        if not self._result or not self._result.catalog:
            return
        xml = self._result.catalog.xml_content
        if not xml:
            return

        cat_id  = self._result.catalog.catalog_id or "catalog"
        default = f"CATALOG_DELTA_{cat_id}.xml"
        path, _ = QFileDialog.getSaveFileName(self, "Salvar Catálogo XML", default, "XML (*.xml)")
        if path:
            with open(path, "wb") as f:
                f.write(xml)
            QMessageBox.information(self, "Salvo", f"Catálogo salvo em:\n{path}")

    def _save_inventory_natura(self) -> None:
        if not self._result:
            return
        xml = self._result.inventory_natura_xml
        if not xml:
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Salvar Inventory Natura XML", "INVENTORY_NATURA.xml", "XML (*.xml)"
        )
        if path:
            with open(path, "wb") as f:
                f.write(xml)
            QMessageBox.information(self, "Salvo", f"Inventory Natura salvo em:\n{path}")

    def _save_inventory_avon(self) -> None:
        if not self._result:
            return
        xml = self._result.inventory_avon_xml
        if not xml:
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Salvar Inventory Avon XML", "INVENTORY_AVON.xml", "XML (*.xml)"
        )
        if path:
            with open(path, "wb") as f:
                f.write(xml)
            QMessageBox.information(self, "Salvo", f"Inventory Avon salvo em:\n{path}")

    def _save_report(self) -> None:
        if not self._result or not self._result.catalog or not self._result.catalog.report:
            QMessageBox.warning(self, "Relatório", "Nenhum relatório disponível.")
            return

        default = "Relatorio_Sincronia_Master.xlsx"
        path, _ = QFileDialog.getSaveFileName(self, "Salvar Relatório XLSX", default, "Excel (*.xlsx)")
        if path:
            import pandas as pd
            df = pd.DataFrame(self._result.catalog.report)
            with pd.ExcelWriter(path, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="Auditoria")
            QMessageBox.information(self, "Salvo", f"Relatório salvo em:\n{path}")

    # ── Clear ─────────────────────────────────────────────────────────────
    def _clear(self) -> None:
        self._dz_excel.clear()
        self._dz_base.clear()
        self._dz_catalog.clear()
        self._file_brands.clear()
        self._reset_badges()
        self._progress_bar.setValue(0)
        self._progress_bar.hide()
        self._status_lbl.hide()
        self._log_box.hide()
        self._warn_lbl.hide()
        self._pb_result_widget.hide()
        self._cat_result_widget.hide()
        self._inv_result_widget.hide()
        self._btn_dl_inv_nat.hide()
        self._btn_dl_inv_avn.hide()
        self._btn_run.setEnabled(True)
        self._chk_pb.setChecked(True)
        self._chk_cat.setChecked(False)
        self._radio_full.setChecked(True)
        self._delta_widget.hide()
        self._result = None
