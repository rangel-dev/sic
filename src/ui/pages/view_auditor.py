"""
Auditor View – Double-Blind Price & Catalog Validation Engine.
The most feature-rich view of the suite:
  • 3 DropZone inputs  (Pricebook XML, Catalog XMLs, Excel files)
  • Run button + QProgressBar
  • 12 clickable ErrorCard tiles
  • Filtered QTableWidget (max 500 rows)
  • AI Diagnostic panel (HTML rendered in QTextBrowser)
  • Export to Excel + Send to Google Chat
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import pandas as pd
from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFileDialog,
    QGridLayout,
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
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from src.core.auditor_engine import AuditResult, ERROR_META
from src.core.ai_agent import AiAgent
from src.core.brand_detector import BrandDetector
from src.ui.components.base_widgets import Divider, DropZone, ErrorCard, SectionHeader
from src.workers.worker_auditor import AuditorWorker
from src.core.history_engine import HistoryEngine
from src.core.utils import get_unique_path


MAX_TABLE_ROWS = 500


class AuditorView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: Optional[AuditorWorker] = None
        self._result: Optional[AuditResult]   = None
        self._active_filters: set[str]        = set()  # error codes
        self._brand_filter:  str = "all"       # "all", "natura", "avon"
        self._error_cards: dict[str, ErrorCard] = {}
        self._settings = QSettings("SIC", "SIC_Suite")
        self._setup_ui()

    # ── Layout ────────────────────────────────────────────────────────────
    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(SectionHeader(
            "✓  Auditor  — Motor de Auditoria de Catálogo",
            "Cruza Excel × Pricebook XML × Catálogo XML em 12 regras de negócio"
        ))
        root.addWidget(Divider())

        # Main splitter: controls top, results bottom
        self._splitter = QSplitter(Qt.Vertical)
        self._splitter.setHandleWidth(4)
        self._splitter.setChildrenCollapsible(False)
        root.addWidget(self._splitter)

        # Container for the top half (so progress bar is outside scroll)
        top_half_widget = QWidget()
        top_half_layout = QVBoxLayout(top_half_widget)
        top_half_layout.setContentsMargins(0, 0, 0, 0)
        top_half_layout.setSpacing(0)

        # ── Top panel: file inputs + action bar (Scrollable) ──────────────
        top_scroll = QScrollArea()
        top_scroll.setWidgetResizable(True)
        top_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        top_scroll.setMinimumHeight(240) # Slightly reduced from 280
        top_half_layout.addWidget(top_scroll)

        top_widget = QWidget()
        top_scroll.setWidget(top_widget)
        top_layout = QVBoxLayout(top_widget)
        top_layout.setContentsMargins(28, 16, 28, 12)
        top_layout.setSpacing(12)

        # File inputs row
        inputs_row = QHBoxLayout()
        inputs_row.setSpacing(16)

        # 1 – Pricebook XML
        pb_col = QVBoxLayout()
        pb_lbl = QLabel("Pricebook XML")
        pb_lbl.setObjectName("label_section")
        pb_col.addWidget(pb_lbl)
        self._dz_pb = DropZone(
            "Pricebook XML\n(br-natura / brl-avon)",
            "XML (*.xml)",
        )
        self._dz_pb.setToolTip(
            "XML de Pricebook exportado do Salesforce Business Manager.\n"
            "Contém os pricebooks de Lista (DE) e Promocional (POR)."
        )
        pb_col.addWidget(self._dz_pb)
        inputs_row.addLayout(pb_col, 1)

        # 2 – Catalog XMLs
        cat_col = QVBoxLayout()
        cat_lbl = QLabel("Catálogo(s) XML  (Natura + Avon + ML)")
        cat_lbl.setObjectName("label_section")
        cat_col.addWidget(cat_lbl)
        self._dz_cat = DropZone(
            "XMLs de Catálogo\n(múltiplos permitidos)",
            "XML (*.xml)",
            multiple=True,
        )
        self._dz_cat.setToolTip(
            "XMLs de Catálogo do Salesforce: natura-br, avon-br, cbbrazil.\n"
            "Contêm category-assignments, online-flag e searchable-flag."
        )
        cat_col.addWidget(self._dz_cat)
        inputs_row.addLayout(cat_col, 1)

        # 3 – Excel files
        excel_col = QVBoxLayout()
        excel_lbl = QLabel("Planilha(s) Excel  (GRADE DE ATIVAÇÃO)")
        excel_lbl.setObjectName("label_section")
        excel_col.addWidget(excel_lbl)
        self._dz_excel = DropZone(
            "Excel(s) comerciais\n(múltiplos permitidos)",
            "Excel (*.xlsx *.xlsm *.xls)",
            multiple=True,
        )
        self._dz_excel.setToolTip(
            "Planilha comercial com aba 'GRADE DE ATIVAÇÃO'.\n"
            "Colunas: SKU, DE (preço lista), POR (preço promo), VISIBLE, SELO."
        )
        excel_col.addWidget(self._dz_excel)
        inputs_row.addLayout(excel_col, 1)

        top_layout.addLayout(inputs_row)

        # Action bar
        action_row = QHBoxLayout()
        action_row.setSpacing(12)

        self._btn_run = QPushButton("✓  Executar Auditoria")
        self._btn_run.setObjectName("btn_primary")
        self._btn_run.setFixedWidth(220)
        self._btn_run.clicked.connect(self._run)
        action_row.addWidget(self._btn_run)

        self._btn_clear = QPushButton("Limpar")
        self._btn_clear.setObjectName("btn_ghost")
        self._btn_clear.clicked.connect(self._clear)
        action_row.addWidget(self._btn_clear)

        action_row.addSpacing(20)

        # Brand filter pills
        self._btn_all    = self._make_filter_pill("Todos",   "all",    True)
        self._btn_natura = self._make_filter_pill("Natura",  "natura", False)
        self._btn_avon   = self._make_filter_pill("Avon",    "avon",   False)
        self._btn_all.setToolTip("Mostrar erros de todas as marcas")
        self._btn_natura.setToolTip("Filtrar apenas erros da marca Natura")
        self._btn_avon.setToolTip("Filtrar apenas erros da marca Avon")
        for b in (self._btn_all, self._btn_natura, self._btn_avon):
            action_row.addWidget(b)

        action_row.addStretch()

        self._btn_export = QPushButton("⬇  Relatório")
        self._btn_export.setObjectName("btn_secondary")
        self._btn_export.clicked.connect(self._export_excel)
        self._btn_export.setEnabled(False)
        self._btn_export.setToolTip("Exportar apenas divergências detectadas")
        action_row.addWidget(self._btn_export)

        self._btn_export_full = QPushButton("📊  Evidências (Full)")
        self._btn_export_full.setObjectName("btn_secondary")
        self._btn_export_full.clicked.connect(self._export_evidence)
        self._btn_export_full.setEnabled(False)
        self._btn_export_full.setToolTip("Exportar relatório completo de evidências (OK + ERRO)")
        action_row.addWidget(self._btn_export_full)

        self._btn_webhook = QPushButton("⊕  Enviar ao Google Chat")
        self._btn_webhook.setObjectName("btn_ghost")
        self._btn_webhook.clicked.connect(self._send_webhook)
        self._btn_webhook.setEnabled(False)
        action_row.addWidget(self._btn_webhook)

        top_layout.addLayout(action_row)

        # Progress bar moved OUT of top_scroll
        top_layout.addStretch()

        # Fixed progress bar container at the bottom of the top half
        progress_container = QWidget()
        progress_layout = QVBoxLayout(progress_container)
        progress_layout.setContentsMargins(28, 8, 28, 8)
        progress_layout.setSpacing(4)
        
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.hide()
        self._progress_bar.setFixedHeight(6) # Thinner, more modern
        progress_layout.addWidget(self._progress_bar)

        self._status_lbl = QLabel("")
        self._status_lbl.setObjectName("label_muted")
        self._status_lbl.hide()
        progress_layout.addWidget(self._status_lbl)

        top_half_layout.addWidget(progress_container)
        self._splitter.addWidget(top_half_widget)

        # ── Bottom panel: dashboard + table + AI ─────────────────────────
        # Use a horizontal splitter for bottom results part
        self._bottom_splitter = QSplitter(Qt.Horizontal)
        self._bottom_splitter.setHandleWidth(4)
        self._bottom_splitter.setChildrenCollapsible(False)
        self._splitter.addWidget(self._bottom_splitter)

        # ── LEFT PART: Dashboard + AI (Inside QScrollArea) ──────────────
        diag_scroll = QScrollArea()
        diag_scroll.setWidgetResizable(True)
        diag_scroll.setObjectName("diag_scroll")
        diag_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._bottom_splitter.addWidget(diag_scroll)

        diag_widget = QWidget()
        diag_scroll.setWidget(diag_widget)
        diag_layout = QVBoxLayout(diag_widget)
        diag_layout.setContentsMargins(18, 12, 10, 12)
        diag_layout.setSpacing(16)

        # Error card dashboard (Flow-like grid)
        self._cards_container = QWidget()
        self._cards_grid = QGridLayout(self._cards_container)
        self._cards_grid.setContentsMargins(0, 0, 0, 0)
        self._cards_grid.setSpacing(10)

        # Pre-instantiate cards...
        for code, meta in ERROR_META.items():
            card = ErrorCard(
                code,
                icon=meta.get("icon", "·"),
                title=meta.get("title", code),
                impact=meta.get("impact", ""),
                desc=meta.get("desc", ""),
            )
            card.clicked_code.connect(self._on_card_clicked)
            self._error_cards[code] = card
            card.hide()

        diag_layout.addWidget(self._cards_container)

        # Empty-state (no divergences) — celebratory message shown when the
        # audit completes with zero errors. Hidden by default; toggled in
        # `_refresh_cards` based on the result stats.
        self._empty_state = QLabel()
        self._empty_state.setObjectName("auditor_empty_state")
        self._empty_state.setAlignment(Qt.AlignCenter)
        self._empty_state.setWordWrap(True)
        self._empty_state.setTextFormat(Qt.RichText)
        self._empty_state.setText(
            "<div style='padding:28px 20px;'>"
            "<div style='font-size:42px;line-height:1;'>✅</div>"
            "<div style='font-size:16px;font-weight:700;margin-top:12px;color:#22A06B;'>"
            "Catálogo 100% íntegro"
            "</div>"
            "<div style='font-size:12px;margin-top:6px;color:#888;'>"
            "Nenhuma divergência encontrada nas 12 regras de negócio.<br>"
            "Pricebook, catálogos e planilhas estão alinhados."
            "</div>"
            "</div>"
        )
        self._empty_state.hide()
        diag_layout.addWidget(self._empty_state)
        diag_layout.addStretch()

        # ── RIGHT PART: Vertical Splitter (Table top, AI bottom) ────────
        right_splitter = QSplitter(Qt.Vertical)
        right_splitter.setHandleWidth(4)
        right_splitter.setChildrenCollapsible(False)
        self._bottom_splitter.addWidget(right_splitter)

        table_widget = QWidget()
        right_splitter.addWidget(table_widget)
        table_layout = QVBoxLayout(table_widget)
        table_layout.setContentsMargins(10, 12, 18, 12)
        table_layout.setSpacing(12)

        table_header = QHBoxLayout()
        self._table_title = QLabel("Divergências Detalhadas")
        self._table_title.setStyleSheet("color:#888;font-size:11px;font-weight:700;text-transform:uppercase;")
        table_header.addWidget(self._table_title)
        table_header.addStretch()
        self._table_count_lbl = QLabel("")
        self._table_count_lbl.setObjectName("label_muted")
        table_header.addWidget(self._table_count_lbl)
        table_layout.addLayout(table_header)

        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(["SKU", "Marca", "Tipo", "Detalhe", "Impt."])
        # Configure resize modes: all interactive, last column stretches
        for col in range(4):
            self._table.horizontalHeader().setSectionResizeMode(col, QHeaderView.Interactive)
        self._table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self._table.setAlternatingRowColors(True)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.verticalHeader().setVisible(False)
        table_layout.addWidget(self._table)

        # AI Panel (Bottom Right)
        ai_widget = QWidget()
        ai_layout = QVBoxLayout(ai_widget)
        ai_layout.setContentsMargins(10, 0, 18, 12)
        ai_layout.setSpacing(8)

        ai_header = QLabel("Diagnóstico Estratégico — IA")
        ai_header.setStyleSheet("font-size:11px;font-weight:700;color:#888;text-transform:uppercase;")
        ai_layout.addWidget(ai_header)

        self._ai_browser = QTextBrowser()
        self._ai_browser.setObjectName("ai_panel")
        self._ai_browser.setOpenExternalLinks(False)
        self._ai_browser.setPlaceholderText("Diagnóstico estratégico aparecerá aqui…")
        ai_layout.addWidget(self._ai_browser)

        right_splitter.addWidget(ai_widget)
        right_splitter.setSizes([450, 250])
        right_splitter.setStretchFactor(0, 1)
        right_splitter.setStretchFactor(1, 0)

        # Splitter distributions
        self._splitter.setSizes([260, 640])
        self._splitter.setStretchFactor(0, 0)
        self._splitter.setStretchFactor(1, 1)

        self._bottom_splitter.setSizes([350, 850])
        self._bottom_splitter.setStretchFactor(0, 0)
        self._bottom_splitter.setStretchFactor(1, 1)

        # Conecta validadores de bloqueio imediato nos DropZones
        self._setup_dropzone_validators()

    # ── DropZone validators (bloqueio imediato no drag-and-drop) ──────────
    def _setup_dropzone_validators(self) -> None:
        """Registra funções validadoras e conecta o sinal de rejeição em cada DropZone."""
        self._dz_cat.set_validator(self._validate_cat_paths)
        self._dz_excel.set_validator(self._validate_excel_paths)
        self._dz_cat.file_rejected.connect(self._on_file_rejected)
        self._dz_excel.file_rejected.connect(self._on_file_rejected)

    def _validate_cat_paths(self, paths: list[str]) -> "Optional[str]":
        """
        Valida a lista proposta de catálogos antes de qualquer commit no DropZone.
        Retorna mensagem de erro se houver duplicidade de marca; None se ok.
        (A checagem de quantidade exata de 3 fica reservada para o _run().)
        """
        brand_map: dict[str, str] = {}
        for path in paths:
            brands = BrandDetector.detect_single(path)
            brand_key = next(iter(brands)) if brands else "desconhecida"
            if brand_key in brand_map:
                brand_display = BrandDetector.get_combined_display_name({brand_key})
                return (
                    f"Erro de Unicidade: Foram detectados dois arquivos da mesma marca "
                    f"({brand_display}).\n\n"
                    f"• {Path(brand_map[brand_key]).name}\n"
                    f"• {Path(path).name}\n\n"
                    f"Por favor, verifique os catálogos."
                )
            brand_map[brand_key] = path
        return None

    def _validate_excel_paths(self, paths: list[str]) -> "Optional[str]":
        """
        Valida a lista proposta de grades Excel antes de qualquer commit no DropZone.
        Retorna mensagem de erro se houver duplicidade de marca; None se ok.
        """
        brand_map: dict[str, str] = {}
        for path in paths:
            brands = BrandDetector.detect_single(path)
            brand_key = next(iter(brands)) if brands else "desconhecida"
            if brand_key in brand_map:
                brand_display = BrandDetector.get_combined_display_name({brand_key})
                return (
                    f"Erro de Unicidade: Foram detectados dois arquivos de Grade "
                    f"da mesma marca ({brand_display}).\n\n"
                    f"• {Path(brand_map[brand_key]).name}\n"
                    f"• {Path(path).name}\n\n"
                    f"Por favor, verifique as planilhas de Grade."
                )
            brand_map[brand_key] = path
        return None

    def _on_file_rejected(self, message: str) -> None:
        """Exibe um aviso quando o DropZone rejeita um arquivo por violação de unicidade."""
        QMessageBox.warning(self, "Arquivo Recusado", message)

    # ── Filter pills ──────────────────────────────────────────────────────
    def _make_filter_pill(self, text: str, key: str, checked: bool) -> QPushButton:
        btn = QPushButton(text)
        btn.setCheckable(True)
        btn.setChecked(checked)
        btn.setObjectName("btn_ghost")
        btn.setFixedHeight(28)
        btn.setProperty("filter_key", key)
        btn.clicked.connect(lambda: self._set_brand_filter(key))
        return btn

    def _set_brand_filter(self, key: str):
        self._brand_filter = key
        for btn in (self._btn_all, self._btn_natura, self._btn_avon):
            btn.setChecked(btn.property("filter_key") == key)
        self._refresh_cards()
        self._refresh_table()

    # ── Run ───────────────────────────────────────────────────────────────
    def _run(self):
        excel_paths = self._dz_excel.file_paths
        pb_path     = self._dz_pb.file_path
        cat_paths   = self._dz_cat.file_paths

        missing = []
        if not pb_path:
            missing.append("Pricebook XML")
        if not cat_paths:
            missing.append("Catálogo(s) XML")

        if missing:
            QMessageBox.warning(
                self, "Auditor",
                "Selecione os seguintes arquivos antes de executar:\n• " + "\n• ".join(missing)
            )
            return

        # Trava 1: Quantidade exata de catálogos
        if len(cat_paths) != 3:
            QMessageBox.warning(
                self, "Quantidade Inválida",
                f"Quantidade Inválida: A auditoria requer exatamente 3 catálogos "
                f"(Natura, Avon e ML) para garantir a integridade cross-brand.\n\n"
                f"Foram selecionados {len(cat_paths)} arquivo(s)."
            )
            return

        # Trava 2: Unicidade de marca nos catálogos
        cat_brand_map: dict[str, str] = {}
        for path in cat_paths:
            brands = BrandDetector.detect_single(path)
            brand_key = next(iter(brands)) if brands else "desconhecida"
            if brand_key in cat_brand_map:
                brand_display = BrandDetector.get_combined_display_name({brand_key})
                QMessageBox.warning(
                    self, "Erro de Unicidade",
                    f"Erro de Unicidade: Foram detectados dois arquivos da mesma marca "
                    f"({brand_display}).\n\n"
                    f"• {Path(cat_brand_map[brand_key]).name}\n"
                    f"• {Path(path).name}\n\n"
                    f"Por favor, verifique os catálogos."
                )
                return
            cat_brand_map[brand_key] = path

        # Trava 3: Unicidade de marca nas grades Excel (se enviadas)
        if excel_paths:
            excel_brand_map: dict[str, str] = {}
            for path in excel_paths:
                brands = BrandDetector.detect_single(path)
                brand_key = next(iter(brands)) if brands else "desconhecida"
                if brand_key in excel_brand_map:
                    brand_display = BrandDetector.get_combined_display_name({brand_key})
                    QMessageBox.warning(
                        self, "Erro de Unicidade",
                        f"Erro de Unicidade: Foram detectados dois arquivos de Grade "
                        f"da mesma marca ({brand_display}).\n\n"
                        f"• {Path(excel_brand_map[brand_key]).name}\n"
                        f"• {Path(path).name}\n\n"
                        f"Por favor, verifique as planilhas de Grade."
                    )
                    return
                excel_brand_map[brand_key] = path

        self._btn_run.setEnabled(False)
        self._btn_export.setEnabled(False)
        self._btn_webhook.setEnabled(False)
        self._table.setRowCount(0)
        self._ai_browser.clear()
        self._empty_state.hide()
        self._progress_bar.setValue(0)
        self._progress_bar.show()
        self._status_lbl.show()
        self._active_filters.clear()

        # Reset cards
        for card in self._error_cards.values():
            card.update_counts(0, 0, 0)
            card.set_selected(False)

        self._worker = AuditorWorker(excel_paths, pb_path, cat_paths, self)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.error_msg.connect(self._on_error)
        self._worker.start()

    # ── Progress ──────────────────────────────────────────────────────────
    def _on_progress(self, pct: int, msg: str):
        self._progress_bar.setValue(pct)
        self._status_lbl.setText(msg)

    # ── Finished ──────────────────────────────────────────────────────────
    def _on_finished(self, result: AuditResult):
        self._result = result
        self._progress_bar.hide()
        self._status_lbl.hide()
        self._btn_run.setEnabled(True)
        self._btn_export.setEnabled(True)
        self._btn_export_full.setEnabled(True)
        self._btn_webhook.setEnabled(True)

        self._refresh_cards()

        # Default: show all errors (clear selection)
        self._active_filters.clear()
        self._refresh_table()

        # AI diagnostic
        agent = AiAgent()
        self._settings.sync()
        theme = str(self._settings.value("theme", "light"))
        html  = agent.generate_report(
            result.stats,
            brands_found=result.brands_found,
            total_excel_skus=result.total_excel_skus,
            theme=theme,
        )
        bg_html = "#fcfdfe" if theme == "light" else "#0e1118"
        fg_html = "#333333" if theme == "light" else "#c0cce0"

        self._ai_browser.setHtml(f"""
        <html><body style="background:{bg_html};color:{fg_html};
                   font-family:'Helvetica Neue', Arial, Helvetica;font-size:12px;
                   padding:8px;line-height:1.6">
        {html}
        </body></html>""")

        total = result.stats.get("total", 0)
        color = "#ef5350" if total > 0 else "#66bb6a"
        if p := self.parent():
            if hasattr(p, "show_status"):
                p.show_status(
                    f"Auditoria: {result.total_excel_skus} SKUs · "
                    f"{total} divergências detectadas"
                )

        # Log to History
        brands = " / ".join(result.brands_found) if result.brands_found else "Desconhecida"
        HistoryEngine.add_entry(
            "Auditor",
            brands,
            f"Auditoria concluída: {result.total_excel_skus} SKUs, {total} divergências."
        )

    # ── Error ─────────────────────────────────────────────────────────────
    def _on_error(self, msg: str):
        self._btn_run.setEnabled(True)
        self._progress_bar.hide()
        self._status_lbl.hide()
        QMessageBox.critical(self, "Erro — Auditor", msg)

    # ── Card click ────────────────────────────────────────────────────────
    def _on_card_clicked(self, code: str):
        # Toggle filter
        if code in self._active_filters:
            self._active_filters.remove(code)
        else:
            self._active_filters.add(code)

        # Update visuals
        for c_code, card in self._error_cards.items():
            card.set_selected(c_code in self._active_filters)

        self._refresh_table()

    # ── Table refresh ─────────────────────────────────────────────────────
    def _refresh_cards(self):
        if not self._result:
            return

        for i in reversed(range(self._cards_grid.count())):
            self._cards_grid.itemAt(i).widget().setParent(None)

        visible_cards = []
        for code, card in self._error_cards.items():
            bt = self._result.stats.get("by_type", {}).get(code, {})
            
            if self._brand_filter == "natura":
                nat = bt.get("natura", 0)
                card.update_counts(nat, nat, 0)
                if nat > 0: visible_cards.append(card)
            elif self._brand_filter == "avon":
                avn = bt.get("avon", 0)
                card.update_counts(avn, 0, avn)
                if avn > 0: visible_cards.append(card)
            else:
                total = bt.get("total", 0)
                card.update_counts(total, bt.get("natura", 0), bt.get("avon", 0))
                if total > 0: visible_cards.append(card)
                
            if card in visible_cards:
                card.show()
            else:
                card.hide()

        for idx, card in enumerate(visible_cards):
            row, col = divmod(idx, 2)
            self._cards_grid.addWidget(card, row, col)

        self._cards_container.setVisible(len(visible_cards) > 0)

        # Optimistic empty-state: only when the audit result has zero total
        # divergences (not when filters merely hide everything).
        total_errors = self._result.stats.get("total", 0)
        self._empty_state.setVisible(total_errors == 0)

    def _refresh_table(self):
        if not self._result:
            return

        rows_to_show: list[dict] = []
        errors = self._result.errors

        # Which error types to include (empty set means show all)
        codes = list(self._active_filters) if self._active_filters else list(errors.keys())

        for code in codes:
            df = errors.get(code)
            if df is None or df.empty:
                continue
            meta = ERROR_META.get(code, {})
            for _, row in df.iterrows():
                brand = str(row.get("brand", "")).lower()
                if self._brand_filter != "all" and brand != self._brand_filter:
                    continue
                rows_to_show.append(
                    {
                        "sku":    str(row.get("sku", "")),
                        "brand":  brand,
                        "code":   code,
                        "title":  meta.get("title", code),
                        "detail": str(row.get("detail", "")),
                        "impact": meta.get("impact", ""),
                    }
                )

        # Truncate
        truncated = len(rows_to_show) > MAX_TABLE_ROWS
        visible   = rows_to_show[:MAX_TABLE_ROWS]

        self._table.setRowCount(0)
        self._table.setRowCount(len(visible))

        for r_idx, row in enumerate(visible):
            sku_item = QTableWidgetItem(row["sku"])
            sku_item.setFont(self._table.font())

            brand_item  = QTableWidgetItem(row["brand"].capitalize())
            error_item  = QTableWidgetItem(row["title"])
            detail_item = QTableWidgetItem(row["detail"])
            impact_item = QTableWidgetItem(row["impact"])

            # Brand color hint
            if row["brand"] == "natura":
                brand_item.setForeground(QColor("#FF8050"))
            elif row["brand"] == "avon":
                brand_item.setForeground(QColor("#bb88ff"))

            for c_idx, item in enumerate(
                [sku_item, brand_item, error_item, detail_item, impact_item]
            ):
                item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
                self._table.setItem(r_idx, c_idx, item)

        # Update title
        has_filters = bool(self._active_filters) or self._brand_filter != "all"
        filter_indicator = "🔽 " if has_filters else ""

        if not self._active_filters:
            title_text = "Todos os Erros"
        else:
            names = [ERROR_META.get(c, {}).get("title", c) for c in self._active_filters]
            if len(names) > 2:
                title_text = f"{len(names)} filtros ativos"
            else:
                title_text = " + ".join(names)

        brand_suffix = "" if self._brand_filter == "all" else f"  ·  {self._brand_filter.capitalize()}"
        self._table_title.setText(f"{filter_indicator}{title_text}{brand_suffix}")

        # Calculate total errors from selected cards (respecting brand filter)
        cards_total = 0
        for code in (self._active_filters if self._active_filters else errors.keys()):
            by_type = self._result.stats.get("by_type", {}).get(code, {})
            if self._brand_filter == "natura":
                cards_total += by_type.get("natura", 0)
            elif self._brand_filter == "avon":
                cards_total += by_type.get("avon", 0)
            else:
                cards_total += by_type.get("total", 0)

        # Display count from selected cards, with note if table is truncated
        count_text = f"{cards_total} erros encontrados"
        if truncated:
            count_text += f"  •  Exibindo {MAX_TABLE_ROWS} primeiros"

        # Set tooltip to explain that this is the sum of selected cards
        if has_filters:
            tooltip_text = (
                f"Total de {cards_total} erros dos cards selecionados.\n"
                f"Filtros: {title_text}{brand_suffix}\n"
                f"Tabela exibe os primeiros {len(visible)} para melhor visualização."
                if not truncated
                else
                f"Total de {cards_total} erros dos cards selecionados.\n"
                f"Filtros: {title_text}{brand_suffix}\n"
                f"Tabela mostra apenas os {MAX_TABLE_ROWS} primeiros para performance."
            )
        else:
            tooltip_text = (
                f"Total de {cards_total} erros encontrados.\n"
                f"Clique em um card de erro para filtrar por tipo ou use os botões de marca para filtrar."
            )

        self._table_count_lbl.setText(count_text)
        self._table_count_lbl.setToolTip(tooltip_text)

    # ── Export ────────────────────────────────────────────────────────────
    def _export_excel(self):
        if not self._result:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar Relatório", "AUDIT_REPORT.xlsx", "Excel (*.xlsx)"
        )
        if not path:
            return
        path = get_unique_path(path)
        try:
            with pd.ExcelWriter(path, engine="openpyxl") as writer:
                # Filter codes to export: active selections OR all non-empty ones
                codes = list(self._active_filters) if self._active_filters else list(self._result.errors.keys())

                for code in codes:
                    df = self._result.errors.get(code)
                    if df is None or df.empty:
                        continue

                    # Apply brand filter if active
                    if self._brand_filter != "all":
                        df = df[df["brand"].str.lower() == self._brand_filter.lower()]
                    
                    if df.empty:
                        continue

                    title = ERROR_META.get(code, {}).get("title", code)
                    # Sanitize sheet name: remove invalid chars / \ ? * : [ ]
                    for char in r"/\?*:[]":
                        title = title.replace(char, "_")
                    sheet = title[:31]
                    df.to_excel(writer, sheet_name=sheet, index=False)

                # Aba de Acertos
                acertos_df = getattr(self._result, "acertos", None)
                if acertos_df is not None and not acertos_df.empty:
                    df_ac = acertos_df.copy()
                    if self._brand_filter != "all":
                        df_ac = df_ac[df_ac["brand"].str.lower() == self._brand_filter.lower()]
                    if not df_ac.empty:
                        df_ac.to_excel(writer, sheet_name="Acertos", index=False)

            QMessageBox.information(self, "Exportado", f"Relatório salvo em:\n{path}")
        except Exception as exc:
            QMessageBox.critical(self, "Erro ao Exportar", str(exc))

    # ── Webhook ───────────────────────────────────────────────────────────
    def _compute_filtered_stats(self) -> dict:
        """Rebuild the stats dict respecting active card filters and brand filter.

        Mirrors the filter logic in `_refresh_table` so the webhook payload
        matches exactly what the user sees on screen. Returns the same shape
        as `AuditResult.stats` so `AiAgent.generate_gchat_report` works unchanged.
        """
        by_type: dict[str, dict] = {}
        by_brand = {"natura": 0, "avon": 0}
        total = 0

        if not self._result:
            return {"total": 0, "by_type": {}, "by_brand": by_brand}

        errors = self._result.errors
        codes = list(self._active_filters) if self._active_filters else list(errors.keys())

        for code in codes:
            df = errors.get(code)
            if df is None or df.empty:
                continue

            if self._brand_filter != "all":
                df = df[df["brand"].str.lower() == self._brand_filter.lower()]

            if df.empty:
                continue

            df_unique = df.drop_duplicates(subset=["sku"])
            brand_series = df_unique["brand"].astype(str).str.lower()
            nat = int((brand_series == "natura").sum())
            avn = int((brand_series == "avon").sum())
            tot = int(len(df_unique))

            by_type[code] = {"total": tot, "natura": nat, "avon": avn}
            by_brand["natura"] += nat
            by_brand["avon"]   += avn
            total += tot

        return {"total": total, "by_type": by_type, "by_brand": by_brand}

    def _send_webhook(self):
        if not self._result:
            return
        url = self._settings.value("gchat_webhook", "")
        if not url:
            QMessageBox.warning(
                self, "Google Chat",
                "Configure a URL do webhook em Configurações antes de enviar."
            )
            return

        import requests
        stats   = self._compute_filtered_stats()
        total   = stats.get("total", 0)
        nat_err = stats.get("by_brand", {}).get("natura", 0)
        avn_err = stats.get("by_brand", {}).get("avon",   0)

        if total == 0:
            QMessageBox.information(
                self, "Google Chat",
                "Nenhum erro no recorte atual. Ajuste os filtros antes de enviar."
            )
            return

        has_filter = bool(self._active_filters) or self._brand_filter != "all"
        if has_filter:
            subtitle = f"Recorte filtrado · {total} divergências"
        else:
            subtitle = f"{self._result.total_excel_skus} SKUs auditados"

        agent = AiAgent()
        plain_ai = agent.generate_gchat_report(
            stats,
            brands_found=self._result.brands_found,
            total_excel_skus=self._result.total_excel_skus,
        )

        payload = {
            "cards": [
                {
                    "header": {
                        "title": "SIC — Relatório Estratégico",
                        "subtitle": subtitle,
                    },
                    "sections": [
                        {
                            "widgets": [
                                {"keyValue": {"topLabel": "Total de Divergências",  "content": str(total)}},
                                {"keyValue": {"topLabel": "Erros Natura",           "content": str(nat_err)}},
                                {"keyValue": {"topLabel": "Erros Avon",             "content": str(avn_err)}},
                            ]
                        },
                        {"widgets": [{"textParagraph": {"text": plain_ai[:3000]}}]},
                    ],
                }
            ]
        }

        try:
            resp = requests.post(url, json=payload, timeout=10)
            if resp.status_code == 200:
                QMessageBox.information(self, "Google Chat", "Relatório enviado com sucesso!")
            else:
                QMessageBox.warning(self, "Google Chat", f"Status {resp.status_code}: {resp.text[:200]}")
        except Exception as exc:
            QMessageBox.critical(self, "Erro", str(exc))

    # ── Clear ─────────────────────────────────────────────────────────────
    def _clear(self):
        self._dz_pb.clear()
        self._dz_cat.clear()
        self._dz_excel.clear()
        self._table.setRowCount(0)
        self._ai_browser.clear()
        self._progress_bar.setValue(0)
        self._progress_bar.hide()
        self._status_lbl.hide()
        self._btn_export.setEnabled(False)
        self._btn_export_full.setEnabled(False)
        self._btn_webhook.setEnabled(False)
        self._result = None
        self._active_filters.clear()
        self._brand_filter  = "all"
        self._btn_all.setChecked(True)
        self._btn_natura.setChecked(False)
        self._btn_avon.setChecked(False)
        self._cards_container.hide()
        self._empty_state.hide()
        for card in self._error_cards.values():
            card.hide()
            card.update_counts(0, 0, 0)
            card.set_selected(False)
        self._table_title.setText("Selecione um ou mais tipos de erro")
        self._table_count_lbl.setText("")
        self._btn_run.setEnabled(True)

    def _export_evidence(self):
        if not self._result or self._result.evidence.empty:
            QMessageBox.information(self, "Evidências", "Nenhuma evidência disponível.")
            return
        
        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar Evidências (Master Report)", "MASTER_AUDIT_REPORT.xlsx", "Excel (*.xlsx)"
        )
        if not path:
            return
        
        path = get_unique_path(path)
        try:
            with pd.ExcelWriter(path, engine="openpyxl") as writer:
                self._result.evidence.to_excel(writer, sheet_name="EVIDENCIAS_AUDITORIA", index=False)
            QMessageBox.information(self, "Exportado", f"Relatório de Evidências salvo em:\n{path}")
        except Exception as exc:
            QMessageBox.critical(self, "Erro ao Exportar", str(exc))

    def refresh_theme(self):
        """Update UI components that have hardcoded theme colors (like HTML panels)."""
        if self._result:
            self._on_finished(self._result)
