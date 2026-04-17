"""
MenuValidatorView — SIC v1.1.0
Validates category menus between Natura/Avon (origin) and CB (destination).

Layout:
  Top panel  — 3 DropZones (Natura, Avon, CB) + action bar + progress
  Bottom panel — summary cards + filterable QTableWidget + export
"""
from __future__ import annotations

from typing import Optional

import pandas as pd
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
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
    QHeaderView,
    QFrame,
)

from src.core.menu_validator_engine import (
    MenuValidationResult,
    ALERT_META,
    ALERT_MISSING,
    ALERT_INACTIVE_CB,
    ALERT_MENU_HIDDEN,
)
from src.ui.components.base_widgets import Divider, DropZone, SectionHeader
from src.workers.worker_menu_validator import MenuValidatorWorker
from src.core.history_engine import HistoryEngine


MAX_TABLE_ROWS = 1000


class MenuValidatorView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: Optional[MenuValidatorWorker] = None
        self._result: Optional[MenuValidationResult] = None
        self._active_filter: str = "all"   # "all" | alert title string
        self._brand_filter: str = "all"    # "all" | "Natura" | "Avon"
        self._setup_ui()

    # ── Layout ────────────────────────────────────────────────────────────────
    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(SectionHeader(
            "≈  Menus CB  — Validador de Sincronização de Categorias",
            "Compara categorias ativas de Natura e Avon contra o catálogo Minha Loja (CB/cbbrazil)"
        ))
        root.addWidget(Divider())

        splitter = QSplitter(Qt.Vertical)
        splitter.setHandleWidth(4)
        splitter.setChildrenCollapsible(False)
        root.addWidget(splitter)

        # ── Top Panel ─────────────────────────────────────────────────────────
        top_scroll = QScrollArea()
        top_scroll.setWidgetResizable(True)
        top_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        top_scroll.setMinimumHeight(230)
        splitter.addWidget(top_scroll)

        top_widget = QWidget()
        top_scroll.setWidget(top_widget)
        top_layout = QVBoxLayout(top_widget)
        top_layout.setContentsMargins(28, 16, 28, 12)
        top_layout.setSpacing(12)

        # DropZones row
        dz_row = QHBoxLayout()
        dz_row.setSpacing(16)

        def _dz_col(label: str, hint: str) -> tuple[DropZone, QVBoxLayout]:
            col = QVBoxLayout()
            lbl = QLabel(label)
            lbl.setObjectName("label_section")
            col.addWidget(lbl)
            dz = DropZone(hint, "XML (*.xml)")
            col.addWidget(dz)
            dz_row.addLayout(col, 1)
            return dz, col

        self._dz_natura, _ = _dz_col(
            "Catálogo Natura XML",
            "Natura Commerce\n(natura-br-catalog.xml)"
        )
        self._dz_avon, _ = _dz_col(
            "Catálogo Avon XML",
            "Avon Commerce\n(avon-br-catalog.xml)"
        )
        self._dz_cb, _ = _dz_col(
            "Catálogo CB XML  (Minha Loja)",
            "Catálogo CB\n(cbbrazil-catalog.xml)"
        )

        top_layout.addLayout(dz_row)

        # Action bar
        action_row = QHBoxLayout()
        action_row.setSpacing(12)

        self._btn_run = QPushButton("▷  Executar Validação")
        self._btn_run.setObjectName("btn_primary")
        self._btn_run.setFixedWidth(220)
        self._btn_run.clicked.connect(self._run)
        action_row.addWidget(self._btn_run)

        self._btn_clear = QPushButton("Limpar")
        self._btn_clear.setObjectName("btn_ghost")
        self._btn_clear.clicked.connect(self._clear)
        action_row.addWidget(self._btn_clear)

        action_row.addSpacing(24)

        # Filter pills
        self._filter_btns: dict[str, QPushButton] = {}
        pill_defs = [
            ("all",                         "Todos"),
            (ALERT_META[ALERT_MISSING]["title"],     ALERT_META[ALERT_MISSING]["icon"] + "  Faltantes"),
            (ALERT_META[ALERT_INACTIVE_CB]["title"], ALERT_META[ALERT_INACTIVE_CB]["icon"] + "  Inativos"),
            (ALERT_META[ALERT_MENU_HIDDEN]["title"], ALERT_META[ALERT_MENU_HIDDEN]["icon"] + "  Ocultos no Menu"),
        ]
        for key, label in pill_defs:
            btn = QPushButton(label)
            btn.setObjectName("btn_ghost")
            btn.setCheckable(True)
            btn.setChecked(key == "all")
            btn.setFixedHeight(28)
            btn.clicked.connect(lambda _checked, k=key: self._set_filter(k))
            self._filter_btns[key] = btn
            action_row.addWidget(btn)

        action_row.addStretch()

        # ── Brand filter pills ─────────────────────────────────────────────────
        brand_row = QHBoxLayout()
        brand_row.setSpacing(8)

        brand_lbl = QLabel("Marca:")
        brand_lbl.setStyleSheet("font-size:11px;font-weight:600;color:#888;background:transparent;")
        brand_row.addWidget(brand_lbl)

        self._brand_btns: dict[str, QPushButton] = {}
        brand_defs = [
            ("all",    "Todas"),
            ("Natura", "🟧  Natura"),
            ("Avon",   "🟪  Avon"),
        ]
        for key, label in brand_defs:
            btn = QPushButton(label)
            btn.setObjectName("btn_ghost")
            btn.setCheckable(True)
            btn.setChecked(key == "all")
            btn.setFixedHeight(28)
            btn.clicked.connect(lambda _checked, k=key: self._set_brand_filter(k))
            self._brand_btns[key] = btn
            brand_row.addWidget(btn)

        brand_row.addStretch()

        self._btn_export = QPushButton("⬇  Exportar Excel")
        self._btn_export.setObjectName("btn_secondary")
        self._btn_export.clicked.connect(self._export_excel)
        self._btn_export.setEnabled(False)
        brand_row.addWidget(self._btn_export)

        top_layout.addLayout(action_row)
        top_layout.addLayout(brand_row)

        # Progress bar + status
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.hide()
        top_layout.addWidget(self._progress_bar)

        self._status_lbl = QLabel("")
        self._status_lbl.setObjectName("label_muted")
        self._status_lbl.hide()
        top_layout.addWidget(self._status_lbl)

        top_layout.addStretch()

        # ── Bottom Panel ──────────────────────────────────────────────────────
        bottom_widget = QWidget()
        splitter.addWidget(bottom_widget)
        bottom_layout = QVBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(28, 12, 28, 16)
        bottom_layout.setSpacing(12)

        # Summary cards row
        self._cards_row = QHBoxLayout()
        self._cards_row.setSpacing(12)
        self._stat_cards: dict[str, dict] = {}

        for code, meta in ALERT_META.items():
            card = self._make_stat_card(meta["icon"], meta["title"], "0")
            self._stat_cards[meta["title"]] = card
            self._cards_row.addWidget(card["widget"])

        self._cards_row.addStretch()
        self._cards_container = QWidget()
        self._cards_container.setLayout(self._cards_row)
        self._cards_container.hide()
        bottom_layout.addWidget(self._cards_container)

        # Table header
        tbl_hdr = QHBoxLayout()
        self._table_title_lbl = QLabel("Selecione os três catálogos e execute a validação")
        self._table_title_lbl.setStyleSheet(
            "color:#888;font-size:11px;font-weight:700;text-transform:uppercase;"
        )
        tbl_hdr.addWidget(self._table_title_lbl)
        tbl_hdr.addStretch()
        self._table_count_lbl = QLabel("")
        self._table_count_lbl.setObjectName("label_muted")
        tbl_hdr.addWidget(self._table_count_lbl)
        bottom_layout.addLayout(tbl_hdr)

        # Table
        self._table = QTableWidget(0, 7)
        self._table.setHorizontalHeaderLabels([
            "ID", "Nome", "Marca", "Status Origem", "Status CB", "Menu CB", "Alerta"
        ])
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self._table.setAlternatingRowColors(True)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.verticalHeader().setVisible(False)
        bottom_layout.addWidget(self._table)

        splitter.setSizes([230, 670])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

    def _make_stat_card(self, icon: str, title: str, count: str) -> dict:
        """Creates a compact summary card widget and returns references."""
        frame = QFrame()
        frame.setObjectName("card_flat")
        frame.setFixedHeight(72)
        frame.setMinimumWidth(160)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(2)

        top_row = QHBoxLayout()
        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet("font-size:13px;background:transparent;")
        top_row.addWidget(icon_lbl)
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("font-size:10px;font-weight:600;color:#888;background:transparent;")
        top_row.addWidget(title_lbl, 1)
        layout.addLayout(top_row)

        count_lbl = QLabel(count)
        count_lbl.setStyleSheet("font-size:22px;font-weight:700;background:transparent;")
        layout.addWidget(count_lbl)

        return {"widget": frame, "count_lbl": count_lbl}

    # ── Filter ────────────────────────────────────────────────────────────────
    def _set_filter(self, key: str):
        self._active_filter = key
        for k, btn in self._filter_btns.items():
            btn.setChecked(k == key)
        self._refresh_table()

    def _set_brand_filter(self, key: str):
        self._brand_filter = key
        for k, btn in self._brand_btns.items():
            btn.setChecked(k == key)
        self._update_stat_cards()
        self._refresh_table()

    # ── Run ───────────────────────────────────────────────────────────────────
    def _run(self):
        natura = self._dz_natura.file_path
        avon   = self._dz_avon.file_path
        cb     = self._dz_cb.file_path

        missing = []
        if not natura: missing.append("Catálogo Natura XML")
        if not avon:   missing.append("Catálogo Avon XML")
        if not cb:     missing.append("Catálogo CB XML")

        if missing:
            QMessageBox.warning(
                self, "Menus CB",
                "Selecione os seguintes arquivos antes de executar:\n• " + "\n• ".join(missing)
            )
            return

        self._btn_run.setEnabled(False)
        self._btn_export.setEnabled(False)
        self._table.setRowCount(0)
        self._cards_container.hide()
        self._progress_bar.setValue(0)
        self._progress_bar.show()
        self._status_lbl.show()
        self._active_filter = "all"
        self._brand_filter = "all"
        for btn in self._filter_btns.values():
            btn.setChecked(False)
        self._filter_btns["all"].setChecked(True)
        for btn in self._brand_btns.values():
            btn.setChecked(False)
        self._brand_btns["all"].setChecked(True)

        self._worker = MenuValidatorWorker(natura, avon, cb, self)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.error_msg.connect(self._on_error)
        self._worker.start()

    # ── Signals ───────────────────────────────────────────────────────────────
    def _on_progress(self, pct: int, msg: str):
        self._progress_bar.setValue(pct)
        self._status_lbl.setText(msg)

    def _on_finished(self, result: MenuValidationResult):
        self._result = result
        self._progress_bar.hide()
        self._status_lbl.hide()
        self._btn_run.setEnabled(True)
        self._btn_export.setEnabled(not result.df_report.empty)

        # Update stat cards
        self._update_stat_cards()
        self._cards_container.show()

        self._refresh_table()

        # Status bar
        total = result.stats.get("total", 0)
        if p := self.parent():
            if hasattr(p, "show_status"):
                p.show_status(f"Menus CB: {total} divergências encontradas")

        # History
        HistoryEngine.add_entry(
            "Menus CB",
            "Natura / Avon / CB",
            f"Validação concluída: {total} divergências detectadas."
        )

    def _on_error(self, msg: str):
        self._btn_run.setEnabled(True)
        self._progress_bar.hide()
        self._status_lbl.hide()
        QMessageBox.critical(self, "Erro — Menus CB", msg)

    def _update_stat_cards(self):
        """Refreshes stat cards based on current brand filter."""
        if self._result is None:
            return
        df = self._result.df_report
        if self._brand_filter != "all":
            df = df[df["Marca_Origem"] == self._brand_filter]
        for title, card in self._stat_cards.items():
            count = int((df["Alerta"] == title).sum()) if not df.empty else 0
            color = "#ef5350" if count > 0 else "#888888"
            card["count_lbl"].setText(str(count))
            card["count_lbl"].setStyleSheet(
                f"font-size:22px;font-weight:700;color:{color};background:transparent;"
            )

    # ── Table refresh ─────────────────────────────────────────────────────────
    def _refresh_table(self):
        if self._result is None or self._result.df_report.empty:
            self._table_title_lbl.setText("Nenhuma divergência encontrada ✓")
            self._table_count_lbl.setText("")
            return

        df = self._result.df_report

        # Apply brand filter
        if self._brand_filter != "all":
            df = df[df["Marca_Origem"] == self._brand_filter]

        # Apply alert type filter
        if self._active_filter != "all":
            df = df[df["Alerta"] == self._active_filter]

        truncated = len(df) > MAX_TABLE_ROWS
        df = df.iloc[:MAX_TABLE_ROWS]

        self._table.setRowCount(0)
        self._table.setRowCount(len(df))

        # Alert → color mapping
        ALERT_COLORS = {
            ALERT_META[ALERT_MISSING]["title"]:     "#ef5350",
            ALERT_META[ALERT_INACTIVE_CB]["title"]: "#ff9800",
            ALERT_META[ALERT_MENU_HIDDEN]["title"]: "#42a5f5",
        }

        for r_idx, (_, row) in enumerate(df.iterrows()):
            alert_color = ALERT_COLORS.get(row["Alerta"], "#888888")
            cols = [
                row["ID"],
                row["Nome"],
                row["Marca_Origem"],
                row["Status_Origem"],
                row["Status_CB"],
                row["Menu_CB"],
                row["Alerta"],
            ]
            for c_idx, val in enumerate(cols):
                item = QTableWidgetItem(str(val))
                item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
                if c_idx == 6:   # Alerta column — colorize
                    item.setForeground(__import__("PySide6.QtGui", fromlist=["QColor"]).QColor(alert_color))
                self._table.setItem(r_idx, c_idx, item)

        total_filtered = len(self._result.df_report[
            self._result.df_report["Marca_Origem"] == self._brand_filter
        ]) if self._brand_filter != "all" else self._result.stats.get("total", 0)
        shown = len(df)
        alert_label = "Todos" if self._active_filter == "all" else self._active_filter
        brand_label = "" if self._brand_filter == "all" else f"  ·  {self._brand_filter}"
        self._table_title_lbl.setText(f"Divergências  ·  {alert_label}{brand_label}")
        count_txt = f"{shown} de {total_filtered}" if (self._active_filter != "all" or self._brand_filter != "all") else f"{total_filtered} divergências"
        if truncated:
            count_txt += f" (limitado a {MAX_TABLE_ROWS})"
        self._table_count_lbl.setText(count_txt)

    # ── Export ────────────────────────────────────────────────────────────────
    def _export_excel(self):
        if self._result is None or self._result.df_report.empty:
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar Relatório", "MENUS_CB_REPORT.xlsx", "Excel (*.xlsx)"
        )
        if not path:
            return

        try:
            with pd.ExcelWriter(path, engine="openpyxl") as writer:
                self._result.df_report.to_excel(writer, sheet_name="Divergências", index=False)

                # One sheet per alert type
                for title in self._stat_cards:
                    df_filt = self._result.df_report[self._result.df_report["Alerta"] == title]
                    if not df_filt.empty:
                        sheet = title[:31]
                        df_filt.to_excel(writer, sheet_name=sheet, index=False)

            QMessageBox.information(self, "Exportado", f"Relatório salvo em:\n{path}")
        except Exception as exc:
            QMessageBox.critical(self, "Erro ao Exportar", str(exc))

    # ── Clear ─────────────────────────────────────────────────────────────────
    def _clear(self):
        self._dz_natura.clear()
        self._dz_avon.clear()
        self._dz_cb.clear()
        self._table.setRowCount(0)
        self._progress_bar.setValue(0)
        self._progress_bar.hide()
        self._status_lbl.hide()
        self._btn_export.setEnabled(False)
        self._cards_container.hide()
        self._result = None
        self._active_filter = "all"
        self._brand_filter = "all"
        for k, btn in self._filter_btns.items():
            btn.setChecked(k == "all")
        for k, btn in self._brand_btns.items():
            btn.setChecked(k == "all")
        self._btn_run.setEnabled(True)
        self._table_title_lbl.setText("Selecione os três catálogos e execute a validação")
        self._table_count_lbl.setText("")

    def refresh_theme(self):
        """Called by MainWindow when theme changes — nothing to refresh here."""
        pass
