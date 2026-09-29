"""
Relatório Menu View – match dos menus Natura/Avon contra o CB (Minha Loja).
Resumo em tela + PDF detalhado para download.
"""
from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.core.history_engine import HistoryEngine
from src.core.relatorio_menu_engine import BRANDS, RelatorioMenuResult
from src.ui.components.base_widgets import Divider, DropZone, SectionHeader, StatPill
from src.workers.worker_relatorio_menu import RelatorioMenuWorker

_GREEN, _RED, _ORANGE, _GRAY = "#28a745", "#d93025", "#f2994a", "#888888"


class RelatorioMenuView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: RelatorioMenuWorker | None = None
        self._result: RelatorioMenuResult | None = None
        self._setup_ui()

    # ── Layout ────────────────────────────────────────────────────────────
    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        outer.addWidget(SectionHeader(
            "📄  Relatório Menu",
            "Verifica se os menus e submenus de Natura e Avon estão presentes e online "
            "no catálogo CB (Minha Loja)."
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
        layout.setSpacing(18)

        # ── Catálogos ──────────────────────────────────────────────────────
        dz_row = QHBoxLayout()
        dz_row.setSpacing(16)

        def _dz_col(title: str, hint: str) -> DropZone:
            col = QVBoxLayout()
            lbl = QLabel(title)
            lbl.setObjectName("label_section")
            col.addWidget(lbl)
            dz = DropZone(hint, "XML (*.xml)")
            col.addWidget(dz)
            dz_row.addLayout(col, 1)
            return dz

        self._dz_natura = _dz_col("Catálogo Natura XML", "Natura Commerce\n(natura-br-catalog.xml)")
        self._dz_avon   = _dz_col("Catálogo Avon XML", "Avon Commerce\n(avon-br-catalog.xml)")
        self._dz_cb     = _dz_col("Catálogo CB XML  (Minha Loja)", "Catálogo CB\n(cbbrazil-catalog.xml)")
        layout.addLayout(dz_row)

        # ── Ações ──────────────────────────────────────────────────────────
        action_row = QHBoxLayout()
        action_row.setSpacing(12)

        self._btn_run = QPushButton("▷  Gerar Relatório")
        self._btn_run.setObjectName("btn_primary")
        self._btn_run.setFixedWidth(200)
        self._btn_run.clicked.connect(self._run)
        action_row.addWidget(self._btn_run)

        self._btn_clear = QPushButton("Limpar")
        self._btn_clear.setObjectName("btn_ghost")
        self._btn_clear.clicked.connect(self._clear)
        action_row.addWidget(self._btn_clear)
        action_row.addStretch()
        layout.addLayout(action_row)

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
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

        lbl_res = QLabel("Resumo")
        lbl_res.setObjectName("label_section")
        res_layout.addWidget(lbl_res)

        stats_row = QHBoxLayout()
        self._stat_total   = StatPill("Menus na origem", "—")
        self._stat_ok      = StatPill("OK", "—", _GREEN)
        self._stat_ausente = StatPill("Ausentes no CB", "—", _RED)
        self._stat_offline = StatPill("Offline no CB", "—", _ORANGE)
        for w in (self._stat_total, self._stat_ok, self._stat_ausente, self._stat_offline):
            stats_row.addWidget(w)
        stats_row.addStretch()
        res_layout.addLayout(stats_row)

        self._brand_table = QTableWidget(len(BRANDS), 6)
        self._brand_table.setHorizontalHeaderLabels(
            ["Marca", "Menus", "OK", "Ausentes no CB", "Offline no CB", "% OK"]
        )
        self._brand_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._brand_table.verticalHeader().setVisible(False)
        self._brand_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._brand_table.setSelectionMode(QTableWidget.NoSelection)
        self._brand_table.setFixedHeight(
            self._brand_table.horizontalHeader().height() + 36 * len(BRANDS) + 4
        )
        for i in range(len(BRANDS)):
            self._brand_table.setRowHeight(i, 36)
        res_layout.addWidget(self._brand_table)

        self._btn_pdf = QPushButton("⬇  Baixar PDF detalhado")
        self._btn_pdf.setObjectName("btn_secondary")
        self._btn_pdf.setFixedWidth(240)
        self._btn_pdf.clicked.connect(self._save_pdf)
        res_layout.addWidget(self._btn_pdf)

        self._result_widget.hide()
        layout.addWidget(self._result_widget)
        layout.addStretch()

    # ── Execução ──────────────────────────────────────────────────────────
    def _run(self) -> None:
        paths = (self._dz_natura.file_path, self._dz_avon.file_path, self._dz_cb.file_path)
        if not all(paths):
            QMessageBox.warning(
                self, "Relatório Menu",
                "Selecione os três catálogos XML: Natura, Avon e CB."
            )
            return

        self._btn_run.setEnabled(False)
        self._result_widget.hide()
        self._progress_bar.setValue(0)
        self._progress_bar.show()
        self._status_lbl.show()

        self._worker = RelatorioMenuWorker(*paths, parent=self)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.error_msg.connect(self._on_error)
        self._worker.start()

    def _on_progress(self, pct: int, msg: str) -> None:
        self._progress_bar.setValue(pct)
        self._status_lbl.setText(msg)

    def _on_finished(self, result: RelatorioMenuResult) -> None:
        self._result = result
        self._btn_run.setEnabled(True)
        self._progress_bar.hide()
        self._status_lbl.hide()

        s = result.stats
        self._stat_total.set_value(str(s["total"]))
        self._stat_ok.set_value(str(s["ok"]), _GREEN)
        self._stat_ausente.set_value(str(s["ausente"]), _RED if s["ausente"] else _GRAY)
        self._stat_offline.set_value(str(s["offline"]), _ORANGE if s["offline"] else _GRAY)

        for row, brand in enumerate(BRANDS):
            b = s["by_brand"][brand]
            pct = f"{b['ok'] / b['total'] * 100:.1f}%" if b["total"] else "—"
            values = [brand, b["total"], b["ok"], b["ausente"], b["offline"], pct]
            for col, val in enumerate(values):
                item = QTableWidgetItem(str(val))
                item.setTextAlignment(Qt.AlignCenter)
                self._brand_table.setItem(row, col, item)

        self._result_widget.show()

        HistoryEngine.add_entry(
            "Relatório Menu",
            "Natura/Avon × CB",
            f"Match gerado — {s['ok']}/{s['total']} menus OK.",
            f"Ausentes no CB: {s['ausente']} | Offline no CB: {s['offline']}",
        )
        if (p := self.parent()) and hasattr(p, "show_status"):
            p.show_status(f"Relatório Menu: {s['ok']}/{s['total']} menus OK no CB")

    def _on_error(self, msg: str) -> None:
        self._btn_run.setEnabled(True)
        self._progress_bar.hide()
        self._status_lbl.hide()
        QMessageBox.critical(self, "Erro — Relatório Menu", msg)

    # ── PDF ───────────────────────────────────────────────────────────────
    def _save_pdf(self) -> None:
        if not self._result:
            return
        ts = datetime.now()
        default = f"Relatorio_Menu_{ts:%Y%m%d_%H%M}.pdf"
        path, _ = QFileDialog.getSaveFileName(self, "Salvar PDF", default, "PDF (*.pdf)")
        if not path:
            return
        try:
            from src.core.relatorio_menu_pdf import generate_pdf
            generate_pdf(self._result, path, ts)
        except Exception as exc:
            QMessageBox.critical(self, "Erro — Relatório Menu", f"Falha ao gerar o PDF:\n{exc}")
            return
        QMessageBox.information(self, "Salvo", f"PDF salvo em:\n{path}")

    # ── Limpar ────────────────────────────────────────────────────────────
    def _clear(self) -> None:
        for dz in (self._dz_natura, self._dz_avon, self._dz_cb):
            dz.clear()
        self._progress_bar.hide()
        self._status_lbl.hide()
        self._result_widget.hide()
        self._btn_run.setEnabled(True)
        self._result = None
