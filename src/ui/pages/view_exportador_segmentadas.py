"""
Exportador — Segmentadas: gera um Pricebook XML enxuto (override de preço)
para uma única lista/campanha segmentada, identificada na grade pela coluna
de preço final (hoje "POR SEGMENTADO"/"POR ORIGEM" — ver
core.segmentado_engine.HEADER_TARGETS; a busca tolera título sem
espaço/underscore, BRD-014). Totalmente separado do Pricebook DE/POR
completo gerado pela tela Exportador → Grade Completa.
"""
from __future__ import annotations

import getpass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QDate, QSettings
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QFileDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.core.app_paths import data_file
from src.core.excel_reader import find_grade_sheet_name
from src.core.history_engine import HistoryEngine
from src.core.runrun_client import RunrunClient, RunrunTask
from src.core.segmentado_engine import (
    LOJA_PARENT_IDS,
    RESERVED_PRICEBOOK_IDS,
    ListaCandidate,
    SegmentadoEngine,
    SegmentScanResult,
)
from src.core.segmentada_registry import (
    JsonFileRegistryStore,
    MatchConfidence,
    ResolveResult,
    SegmentadaRecord,
    SyncedFolderRegistryStore,
    build_pricebook_id,
    merge_by_pricebook_id,
    resolve as resolve_seg_registry,
    write_xlsx_snapshot,
)
from src.ui.components.base_widgets import Divider, DropZone, SectionHeader, StatPill, show_rejection_dialog
from src.ui.pages.view_settings import (
    RUNRUN_APP_KEY_KEY,
    RUNRUN_ENABLED_KEY,
    RUNRUN_USER_TOKEN_KEY,
    SEG_SHARED_ENABLED_KEY,
    SEG_SHARED_FOLDER_KEY,
)
from src.workers.worker_runrun_task import RunrunTaskFetchWorker
from src.workers.worker_segmentado import SegmentadoScanWorker
from src.workers.worker_segmentada_registry import SegmentadaRegistryWriteWorker

import openpyxl


BRAND_LABELS: dict[str, str] = {
    "natura": "Natura",
    "avon":   "Avon",
    "ml":     "CB (Minha Loja)",
}


def _sniff_brand(path: str) -> Optional[str]:
    """Mesma heurística rápida de detecção de marca usada no Exportador
    (Grade Completa) — lê só as primeiras linhas para o badge da UI."""
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
        return "natura" if nat >= avn else "avon"
    except Exception:
        return None


def _populate_numeric_combo(combo: QComboBox, count: int) -> None:
    """Preenche um QComboBox com "00".."{count-1}" — dropdown de verdade
    (igual ao calendário da data), usado para Hora (0-23) e Minuto (0-59)
    separadamente, permitindo qualquer combinação HH:MM."""
    for i in range(count):
        combo.addItem(f"{i:02d}")


class ExportadorSegmentadasView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._seg_scan_worker: SegmentadoScanWorker | None = None
        self._seg_scan_result: SegmentScanResult | None = None
        self._seg_selected_lista: ListaCandidate | None = None
        self._seg_xml: bytes | None = None
        self._seg_detected_brand: Optional[str] = None
        self._seg_generated_campaign_start: Optional[date] = None
        self._seg_generated_label: Optional[str] = None
        # BRD-012, P2: registro pendente, montado na geração e só persistido
        # depois que o XML realmente for escrito em disco (_save_seg_pricebook)
        # — nunca na geração, para não criar um vínculo "fantasma" se o
        # usuário cancelar a caixa de salvar.
        self._seg_pending_record: Optional[SegmentadaRecord] = None
        self._seg_registry_store = JsonFileRegistryStore(data_file("segmentadas_registry.json"))
        self._seg_registry_worker: Optional[SegmentadaRegistryWriteWorker] = None
        # BRD-012, P5 (revisado): compartilhamento via pasta do Google Drive
        # sincronizada — configurado em Configurações, opcional e desligado
        # por padrão. `_seg_settings` é lido de novo a cada gravação/consulta
        # para refletir uma mudança feita em Configurações sem reiniciar o app.
        self._seg_settings = QSettings("SIC", "SIC_Suite")
        # BRD-012, P3: reconhecimento na importação — a flag impede que o
        # ID montado automaticamente sobrescreva o que o operador já digitou
        # à mão (nem na direção contrária: digitar o nº da tarefa não some
        # o que a pessoa já tiver escrito manualmente no ID).
        self._seg_pbid_touched: bool = False
        self._seg_resolve_result: Optional[ResolveResult] = None
        self._seg_is_update_mode: bool = False
        # BRD-012, Etapa 5/P6: conferência da tarefa no Runrun.it — cache em
        # memória por sessão (CA-26/proteção da App-Key) e intervalo mínimo
        # entre consultas, além de nunca disparar por tecla (editingFinished).
        self._seg_runrun_cache: dict[str, RunrunTask] = {}
        self._seg_runrun_worker: Optional[RunrunTaskFetchWorker] = None
        self._seg_runrun_task: Optional[RunrunTask] = None
        self._seg_runrun_last_query_at: Optional[datetime] = None
        self._setup_ui()

    # ── UI Construction ───────────────────────────────────────────────────
    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        outer.addWidget(SectionHeader(
            "⊗  Exportador — Segmentadas",
            "Gera um Pricebook XML enxuto (override de preço) para uma lista/campanha "
            "segmentada, identificada na grade por colunas de preço final "
            "(ex.: POR SEGMENTADO, POR ORIGEM — com ou sem espaço no título)."
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

        # ── Parâmetros ───────────────────────────────────────────────────
        params_box = QGroupBox("Parâmetros do Pricebook Segmentado")
        params_layout = QVBoxLayout(params_box)
        params_layout.setContentsMargins(16, 18, 16, 14)
        params_layout.setSpacing(12)

        lbl_runrun_id = QLabel("Nº da tarefa Runrun.it (opcional)")
        lbl_runrun_id.setObjectName("label_section")
        params_layout.addWidget(lbl_runrun_id)
        self._seg_input_runrun_id = QLineEdit()
        self._seg_input_runrun_id.setPlaceholderText("Ex: 1111 — monta o ID abaixo automaticamente")
        self._seg_input_runrun_id.textEdited.connect(self._on_seg_runrun_id_edited)
        self._seg_input_runrun_id.editingFinished.connect(self._on_seg_runrun_id_editing_finished)
        params_layout.addWidget(self._seg_input_runrun_id)

        # BRD-012, Etapa 5/P6: título da tarefa, consultado só ao sair do
        # campo (editingFinished) ou Enter — nunca a cada tecla (CA-26).
        self._seg_runrun_status_lbl = QLabel("")
        self._seg_runrun_status_lbl.setWordWrap(True)
        self._seg_runrun_status_lbl.setStyleSheet("font-size:11px; background:transparent; color:#9e9e9e;")
        self._seg_runrun_status_lbl.hide()
        params_layout.addWidget(self._seg_runrun_status_lbl)

        lbl_pbid = QLabel("ID do Pricebook (Salesforce)")
        lbl_pbid.setObjectName("label_section")
        params_layout.addWidget(lbl_pbid)
        self._seg_input_pbid = QLineEdit()
        self._seg_input_pbid.setPlaceholderText("Ex: NAT-RR1881")
        self._seg_input_pbid.textEdited.connect(self._on_seg_pbid_edited)
        params_layout.addWidget(self._seg_input_pbid)

        lbl_display_name = QLabel("Nome de Exibição do Pricebook (opcional)")
        lbl_display_name.setObjectName("label_section")
        params_layout.addWidget(lbl_display_name)
        self._seg_input_display_name = QLineEdit()
        self._seg_input_display_name.setPlaceholderText(
            "Ex: Campanha Favoritos RR18/21 — deixe em branco para omitir do XML"
        )
        params_layout.addWidget(self._seg_input_display_name)

        loja_col = QVBoxLayout()
        loja_col.setSpacing(6)
        lbl_loja = QLabel("Loja")
        lbl_loja.setObjectName("label_section")
        loja_col.addWidget(lbl_loja)
        self._seg_combo_loja = QComboBox()
        self._seg_combo_loja.setFixedWidth(220)
        self._seg_combo_loja.addItem("Natura", "natura")
        self._seg_combo_loja.addItem("Avon", "avon")
        self._seg_combo_loja.addItem("Minha Loja (CB)", "ml")
        self._seg_combo_loja.currentIndexChanged.connect(self._on_seg_loja_changed)
        loja_col.addWidget(self._seg_combo_loja)

        combo_row = QHBoxLayout()
        combo_row.addLayout(loja_col)
        combo_row.addStretch()
        params_layout.addLayout(combo_row)

        date_start_col = QVBoxLayout()
        date_start_col.setSpacing(6)
        lbl_date_start = QLabel("Data/Hora Início")
        lbl_date_start.setObjectName("label_section")
        date_start_col.addWidget(lbl_date_start)
        start_row = QHBoxLayout()
        start_row.setSpacing(6)
        self._seg_date_start = QDateEdit()
        self._seg_date_start.setCalendarPopup(True)
        self._seg_date_start.setDisplayFormat("dd/MM/yyyy")
        self._seg_date_start.setDate(QDate.currentDate())
        self._seg_date_start.setFixedWidth(120)
        start_row.addWidget(self._seg_date_start)
        lbl_start_at = QLabel("às")
        lbl_start_at.setObjectName("label_muted")
        start_row.addWidget(lbl_start_at)
        self._seg_hour_start = QComboBox()
        self._seg_hour_start.setFixedWidth(56)
        _populate_numeric_combo(self._seg_hour_start, 24)
        self._seg_hour_start.setCurrentIndex(0)
        start_row.addWidget(self._seg_hour_start)
        lbl_colon_start = QLabel(":")
        start_row.addWidget(lbl_colon_start)
        self._seg_min_start = QComboBox()
        self._seg_min_start.setFixedWidth(56)
        _populate_numeric_combo(self._seg_min_start, 60)
        self._seg_min_start.setCurrentIndex(0)
        start_row.addWidget(self._seg_min_start)
        date_start_col.addLayout(start_row)

        date_end_col = QVBoxLayout()
        date_end_col.setSpacing(6)
        lbl_date_end = QLabel("Data/Hora Fim")
        lbl_date_end.setObjectName("label_section")
        date_end_col.addWidget(lbl_date_end)
        end_row = QHBoxLayout()
        end_row.setSpacing(6)
        self._seg_date_end = QDateEdit()
        self._seg_date_end.setCalendarPopup(True)
        self._seg_date_end.setDisplayFormat("dd/MM/yyyy")
        self._seg_date_end.setDate(QDate.currentDate())
        self._seg_date_end.setFixedWidth(120)
        end_row.addWidget(self._seg_date_end)
        lbl_end_at = QLabel("às")
        lbl_end_at.setObjectName("label_muted")
        end_row.addWidget(lbl_end_at)
        self._seg_hour_end = QComboBox()
        self._seg_hour_end.setFixedWidth(56)
        _populate_numeric_combo(self._seg_hour_end, 24)
        self._seg_hour_end.setCurrentIndex(23)
        end_row.addWidget(self._seg_hour_end)
        lbl_colon_end = QLabel(":")
        end_row.addWidget(lbl_colon_end)
        self._seg_min_end = QComboBox()
        self._seg_min_end.setFixedWidth(56)
        _populate_numeric_combo(self._seg_min_end, 60)
        self._seg_min_end.setCurrentIndex(59)
        end_row.addWidget(self._seg_min_end)
        date_end_col.addLayout(end_row)

        date_sep = QLabel("→")
        date_sep.setObjectName("label_muted")
        date_sep.setAlignment(Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter)
        date_sep.setFixedHeight(self._seg_date_start.sizeHint().height())

        date_row = QHBoxLayout()
        date_row.setSpacing(10)
        date_row.addLayout(date_start_col)
        date_row.addWidget(date_sep)
        date_row.addLayout(date_end_col)
        date_row.addStretch()

        params_layout.addLayout(date_row)
        layout.addWidget(params_box)

        # ── Import de grade ─────────────────────────────────────────────
        grade_box = QGroupBox("Grade Segmentada")
        grade_layout = QVBoxLayout(grade_box)
        grade_layout.setContentsMargins(16, 18, 16, 14)
        grade_layout.setSpacing(12)

        self._seg_dz_grade = DropZone(
            "Arraste a grade aqui  —  GRADE DE ATIVAÇÃO (com abas LISTA_XX)",
            "Excel (*.xlsx *.xlsm)",
            multiple=False,
        )
        self._seg_dz_grade.set_validator(self._seg_validate_file)
        self._seg_dz_grade.file_rejected.connect(self._on_file_rejected)
        self._seg_dz_grade.files_selected.connect(self._on_seg_file_selected)
        grade_layout.addWidget(self._seg_dz_grade)

        self._seg_badge = QLabel("")
        self._seg_badge.setFixedHeight(28)
        self._seg_badge.hide()
        grade_layout.addWidget(self._seg_badge)

        # Seletor manual de Marca — some por padrão. Só aparece quando a
        # detecção automática (pelo prefixo dos SKUs) falha, como fallback.
        self._seg_marca_fallback_row = QWidget()
        marca_fb_layout = QHBoxLayout(self._seg_marca_fallback_row)
        marca_fb_layout.setContentsMargins(0, 0, 0, 0)
        marca_fb_layout.setSpacing(8)
        lbl_marca_fb = QLabel("Selecione a marca manualmente:")
        lbl_marca_fb.setObjectName("label_muted")
        marca_fb_layout.addWidget(lbl_marca_fb)
        self._seg_combo_marca_fallback = QComboBox()
        self._seg_combo_marca_fallback.addItem("Natura", "natura")
        self._seg_combo_marca_fallback.addItem("Avon", "avon")
        self._seg_combo_marca_fallback.currentIndexChanged.connect(self._on_seg_marca_fallback_changed)
        marca_fb_layout.addWidget(self._seg_combo_marca_fallback)
        marca_fb_layout.addStretch()
        self._seg_marca_fallback_row.hide()
        grade_layout.addWidget(self._seg_marca_fallback_row)

        scan_row = QHBoxLayout()
        scan_row.setSpacing(12)
        self._seg_btn_scan = QPushButton("🔍  Buscar Listas Segmentadas")
        self._seg_btn_scan.setObjectName("btn_secondary")
        self._seg_btn_scan.setFixedWidth(230)
        self._seg_btn_scan.clicked.connect(self._run_seg_scan)
        scan_row.addWidget(self._seg_btn_scan)
        scan_row.addStretch()
        grade_layout.addLayout(scan_row)

        self._seg_progress_bar = QProgressBar()
        self._seg_progress_bar.setRange(0, 100)
        self._seg_progress_bar.setValue(0)
        self._seg_progress_bar.hide()
        grade_layout.addWidget(self._seg_progress_bar)

        self._seg_status_lbl = QLabel("")
        self._seg_status_lbl.setObjectName("label_muted")
        self._seg_status_lbl.hide()
        grade_layout.addWidget(self._seg_status_lbl)

        layout.addWidget(grade_box)

        # ── Listas identificadas ────────────────────────────────────────
        self._seg_lista_box = QGroupBox("Listas Segmentadas Identificadas")
        lista_layout = QVBoxLayout(self._seg_lista_box)
        lista_layout.setContentsMargins(16, 18, 16, 14)
        lista_layout.setSpacing(10)

        self._seg_table = QTableWidget()
        self._seg_table.setColumnCount(6)
        self._seg_table.setHorizontalHeaderLabels([
            "LISTA (ABA)", "LP", "PERÍODO SUGERIDO", "COLUNA DETECTADA",
            "SKUs c/ preço válido", "TOTAL INFORMADO"
        ])
        self._seg_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._seg_table.verticalHeader().hide()
        self._seg_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._seg_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._seg_table.setSelectionMode(QTableWidget.SingleSelection)
        self._seg_table.setFixedHeight(180)
        self._seg_table.itemSelectionChanged.connect(self._on_seg_lista_selected)
        lista_layout.addWidget(self._seg_table)

        self._seg_warn_lbl = QLabel("")
        self._seg_warn_lbl.setWordWrap(True)
        self._seg_warn_lbl.setStyleSheet("color:#ffcc80; font-size:11px; background:transparent;")
        self._seg_warn_lbl.hide()
        lista_layout.addWidget(self._seg_warn_lbl)

        # BRD-012, P3: banner de reconhecimento — nunca preenche o ID
        # sozinho (o nome da aba é reaproveitado entre ciclos); só mostra o
        # vínculo lembrado e espera um clique explícito.
        self._seg_banner = QFrame()
        self._seg_banner.setFrameShape(QFrame.NoFrame)
        banner_layout = QHBoxLayout(self._seg_banner)
        banner_layout.setContentsMargins(12, 10, 12, 10)
        banner_layout.setSpacing(10)
        self._seg_banner_lbl = QLabel("")
        self._seg_banner_lbl.setWordWrap(True)
        self._seg_banner_lbl.setStyleSheet("background:transparent; font-size:11px;")
        banner_layout.addWidget(self._seg_banner_lbl, 1)
        self._seg_banner_btn_use = QPushButton("Usar (ATUALIZAÇÃO)")
        self._seg_banner_btn_use.setObjectName("btn_primary")
        self._seg_banner_btn_use.clicked.connect(self._on_seg_banner_use)
        banner_layout.addWidget(self._seg_banner_btn_use)
        self._seg_banner_btn_ignore = QPushButton("Ignorar — é campanha nova")
        self._seg_banner_btn_ignore.setObjectName("btn_ghost")
        self._seg_banner_btn_ignore.clicked.connect(self._on_seg_banner_ignore)
        banner_layout.addWidget(self._seg_banner_btn_ignore)
        self._seg_banner.hide()
        lista_layout.addWidget(self._seg_banner)

        seg_action_row = QHBoxLayout()
        seg_action_row.setSpacing(12)
        self._seg_btn_generate = QPushButton("⊗  Gerar Pricebook Segmentado")
        self._seg_btn_generate.setObjectName("btn_primary")
        self._seg_btn_generate.setFixedWidth(230)
        self._seg_btn_generate.setEnabled(False)
        self._seg_btn_generate.clicked.connect(self._run_seg_generate)
        seg_action_row.addWidget(self._seg_btn_generate)

        self._seg_btn_clear = QPushButton("Limpar")
        self._seg_btn_clear.setObjectName("btn_ghost")
        self._seg_btn_clear.clicked.connect(self._clear_seg_tab)
        seg_action_row.addWidget(self._seg_btn_clear)
        seg_action_row.addStretch()
        lista_layout.addLayout(seg_action_row)

        self._seg_lista_box.hide()
        layout.addWidget(self._seg_lista_box)

        # ── Resultado ────────────────────────────────────────────────────
        self._seg_result_widget = QWidget()
        seg_res_layout = QVBoxLayout(self._seg_result_widget)
        seg_res_layout.setContentsMargins(0, 0, 0, 0)
        seg_res_layout.setSpacing(8)

        lbl_seg_res = QLabel("Pricebook Segmentado")
        lbl_seg_res.setObjectName("label_section")
        lbl_seg_res.setStyleSheet("color:#60a5fa; font-weight:700;")
        seg_res_layout.addWidget(lbl_seg_res)

        seg_stats_row = QHBoxLayout()
        self._seg_stat_skus    = StatPill("SKUs Incluídos", "—", "#f0f0f0")
        self._seg_stat_lista   = StatPill("Lista",          "—", "#7e57c2")
        self._seg_stat_lp      = StatPill("LP",             "—", "#26a69a")
        self._seg_stat_loja    = StatPill("Loja",           "—", "#60a5fa")
        self._seg_stat_periodo = StatPill("Período",        "—", "#888888")
        for w in (self._seg_stat_skus, self._seg_stat_lista, self._seg_stat_lp,
                  self._seg_stat_loja, self._seg_stat_periodo):
            seg_stats_row.addWidget(w)
        seg_stats_row.addStretch()
        seg_res_layout.addLayout(seg_stats_row)

        self._seg_btn_dl = QPushButton("⬇  Salvar Pricebook Segmentado XML")
        self._seg_btn_dl.setObjectName("btn_secondary")
        self._seg_btn_dl.setFixedWidth(260)
        self._seg_btn_dl.clicked.connect(self._save_seg_pricebook)
        seg_res_layout.addWidget(self._seg_btn_dl)

        self._seg_result_widget.hide()
        layout.addWidget(self._seg_result_widget)

        layout.addStretch()

    # ── Handlers ─────────────────────────────────────────────────────────
    @staticmethod
    def _seg_validate_file(paths: list[str]) -> Optional[str]:
        for path in paths:
            suffix = Path(path).suffix.lower()
            if suffix == ".xls":
                return (f"<b>Arquivo:</b> {Path(path).name}\n\n"
                        "O formato .xls (Excel 97-2003) não é suportado. "
                        "Salve a grade como .xlsx ou .xlsm e tente novamente.")
            if suffix not in (".xlsx", ".xlsm"):
                return (f"<b>Arquivo:</b> {Path(path).name}\n\n"
                        "Selecione uma planilha Excel (.xlsx ou .xlsm).")
        return None

    @staticmethod
    def _format_seg_brand_rejection(detected: Optional[str], expected: Optional[str]) -> str:
        detected_name = BRAND_LABELS.get(detected, detected or "Desconhecida") if detected else "Desconhecida"
        expected_name = BRAND_LABELS.get(expected, expected or "Desconhecida") if expected else "Desconhecida"
        return (
            "A marca detectada nos SKUs das listas segmentadas não corresponde à marca "
            "selecionada.\n\n"
            f"<b>Marca selecionada:</b> {expected_name}\n"
            f"<b>Marca detectada na grade:</b> {detected_name}\n\n"
            "Selecione a marca correta antes de buscar as listas novamente."
        )

    def _on_file_rejected(self, message: str) -> None:
        show_rejection_dialog(self, message, header="Este arquivo foi recusado")

    def _reset_seg_scan_state(self) -> None:
        self._seg_lista_box.hide()
        self._seg_result_widget.hide()
        self._seg_warn_lbl.hide()
        self._seg_banner.hide()
        self._seg_table.setRowCount(0)
        self._seg_scan_result = None
        self._seg_selected_lista = None
        self._seg_xml = None
        self._seg_generated_campaign_start = None
        self._seg_generated_label = None
        self._seg_pending_record = None
        self._seg_resolve_result = None
        self._seg_is_update_mode = False
        self._seg_btn_generate.setEnabled(False)

    def _on_seg_file_selected(self, paths: list[str]) -> None:
        self._reset_seg_scan_state()
        if not paths:
            self._seg_badge.hide()
            self._seg_marca_fallback_row.hide()
            self._set_detected_brand(None)
            return

        # A marca é detectada automaticamente pelo prefixo dos SKUs
        # (NATBRA-/AVNBRA-) assim que a grade é solta — sem seletor manual.
        # O seletor de fallback só aparece se a detecção falhar.
        brand = _sniff_brand(paths[0])
        if brand in ("natura", "avon"):
            self._seg_marca_fallback_row.hide()
            self._apply_badge(brand)
            self._seg_badge.show()
            self._set_detected_brand(brand)
        else:
            self._seg_badge.setText("❓  Marca não identificada")
            self._seg_badge.setStyleSheet(
                "font-size:12px; font-weight:700; color:#888888; "
                "border-radius:5px; padding:0 12px; background:transparent;"
            )
            self._seg_badge.show()
            self._seg_marca_fallback_row.show()
            self._set_detected_brand(self._seg_combo_marca_fallback.currentData())

    def _apply_badge(self, brand: str) -> None:
        color = "#f59e0b" if brand == "natura" else "#c4b5fd"
        text = "🟧  Natura detectada ✓" if brand == "natura" else "🟪  Avon detectada ✓"
        self._seg_badge.setText(text)
        self._seg_badge.setStyleSheet(
            f"font-size:12px; font-weight:700; color:{color}; "
            "border-radius:5px; padding:0 12px; background:transparent;"
        )

    def _on_seg_marca_fallback_changed(self, _index: int) -> None:
        self._set_detected_brand(self._seg_combo_marca_fallback.currentData())

    def _set_detected_brand(self, brand: Optional[str]) -> None:
        self._seg_detected_brand = brand
        # Loja acompanha a marca, exceto quando o alvo é Minha Loja (CB),
        # que aceita SKUs de qualquer marca.
        if brand and self._seg_combo_loja.currentData() != "ml":
            idx = self._seg_combo_loja.findData(brand)
            if idx >= 0:
                self._seg_combo_loja.setCurrentIndex(idx)

    def _run_seg_scan(self) -> None:
        path = self._seg_dz_grade.file_path
        if not path:
            QMessageBox.warning(
                self, "Segmentadas",
                "Selecione uma grade Excel antes de buscar as listas segmentadas."
            )
            return

        expected_brand = self._seg_detected_brand
        if not expected_brand:
            QMessageBox.warning(
                self, "Segmentadas",
                "Não foi possível identificar a marca da grade. "
                "Selecione manualmente no campo que apareceu abaixo do arquivo."
            )
            return

        self._reset_seg_scan_state()
        self._seg_btn_scan.setEnabled(False)
        self._seg_progress_bar.setValue(0)
        self._seg_progress_bar.show()
        self._seg_status_lbl.setText("Iniciando varredura…")
        self._seg_status_lbl.show()

        self._seg_scan_worker = SegmentadoScanWorker(path, expected_brand, self)
        self._seg_scan_worker.progress.connect(self._on_seg_scan_progress)
        self._seg_scan_worker.finished.connect(self._on_seg_scan_finished)
        self._seg_scan_worker.error_msg.connect(self._on_seg_scan_error)
        self._seg_scan_worker.start()

    def _on_seg_scan_progress(self, pct: int, msg: str) -> None:
        self._seg_progress_bar.setValue(pct)
        self._seg_status_lbl.setText(msg)

    def _on_seg_scan_finished(self, result: SegmentScanResult) -> None:
        self._seg_btn_scan.setEnabled(True)
        self._seg_progress_bar.hide()
        self._seg_status_lbl.hide()

        if result.error:
            QMessageBox.warning(self, "Segmentadas", result.error)
            return

        expected_brand = self._seg_detected_brand
        if result.brand_mismatch:
            show_rejection_dialog(
                self,
                self._format_seg_brand_rejection(result.detected_brand, expected_brand),
                header="Marca da grade não corresponde",
            )
            return

        self._seg_scan_result = result
        self._populate_seg_table(result.candidates)
        self._seg_lista_box.show()

    def _on_seg_scan_error(self, msg: str) -> None:
        self._seg_btn_scan.setEnabled(True)
        self._seg_progress_bar.hide()
        self._seg_status_lbl.hide()
        QMessageBox.critical(self, "Erro — Segmentadas", msg)

    def _populate_seg_table(self, candidates: list[ListaCandidate]) -> None:
        self._seg_table.setRowCount(len(candidates))
        for row, c in enumerate(candidates):
            self._seg_table.setItem(row, 0, QTableWidgetItem(c.sheet_name))
            self._seg_table.setItem(row, 1, QTableWidgetItem(c.lp_label or "—"))

            if c.periodo_sugerido:
                start, end = c.periodo_sugerido
                periodo_str = f"{start.strftime('%d/%m/%Y')} – {end.strftime('%d/%m/%Y')}"
            else:
                periodo_str = "—"
            self._seg_table.setItem(row, 2, QTableWidgetItem(periodo_str))
            self._seg_table.setItem(row, 3, QTableWidgetItem(c.matched_header))

            item_skus = QTableWidgetItem(str(len(c.rows)))
            if c.warnings:
                item_skus.setForeground(Qt.GlobalColor.yellow)
            elif c.rows:
                item_skus.setForeground(Qt.GlobalColor.green)
            self._seg_table.setItem(row, 4, item_skus)

            total_str = str(c.total_skus_informado) if c.total_skus_informado is not None else "—"
            self._seg_table.setItem(row, 5, QTableWidgetItem(total_str))

            if c.warnings:
                tip = "\n".join(f"• {w}" for w in c.warnings)
                for col in range(self._seg_table.columnCount()):
                    item = self._seg_table.item(row, col)
                    if item is not None:
                        item.setToolTip(tip)

    def _on_seg_lista_selected(self) -> None:
        sel_model = self._seg_table.selectionModel()
        rows = sel_model.selectedRows() if sel_model else []
        if not rows or not self._seg_scan_result:
            self._seg_selected_lista = None
            self._seg_btn_generate.setEnabled(False)
            self._seg_warn_lbl.hide()
            self._seg_banner.hide()
            self._seg_resolve_result = None
            self._seg_is_update_mode = False
            return

        idx = rows[0].row()
        candidate = self._seg_scan_result.candidates[idx]
        self._seg_selected_lista = candidate

        if candidate.periodo_sugerido:
            start, end = candidate.periodo_sugerido
            self._seg_date_start.setDate(QDate(start.year, start.month, start.day))
            self._seg_hour_start.setCurrentIndex(0)
            self._seg_min_start.setCurrentIndex(0)
            self._seg_date_end.setDate(QDate(end.year, end.month, end.day))
            self._seg_hour_end.setCurrentIndex(23)
            self._seg_min_end.setCurrentIndex(59)

        if candidate.warnings:
            self._seg_warn_lbl.setText("⚠  " + "  |  ".join(candidate.warnings))
            self._seg_warn_lbl.show()
        else:
            self._seg_warn_lbl.hide()

        self._seg_btn_generate.setEnabled(bool(candidate.rows))
        self._seg_is_update_mode = False
        self._update_seg_banner(candidate)
        # Reexibe a conferência contra o título já consultado, se houver —
        # o vínculo pode ter mudado com a nova lista selecionada.
        if self._seg_runrun_task:
            self._on_seg_runrun_task_fetched(self._seg_runrun_task)

    # ── BRD-012, P3: reconhecimento na importação ───────────────────────────
    @staticmethod
    def _fmt_iso_date(value: Optional[str]) -> str:
        """Converte um `online_from`/`online_to`/`created_at` (UTC, formato
        de `SegmentadoEngine.compute_online_window`) de volta para BRT antes
        de exibir — sem isso, um horário perto da meia-noite mostraria o
        dia seguinte ao real."""
        if not value:
            return "—"
        try:
            dt = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.000Z") - timedelta(hours=3)
            return dt.strftime("%d/%m")
        except ValueError:
            return "—"

    def _current_loja_and_brand(self) -> tuple[Optional[str], Optional[str]]:
        loja_key = self._seg_combo_loja.currentData()
        return loja_key, self._seg_detected_brand

    def _seg_shared_store(self) -> Optional[SyncedFolderRegistryStore]:
        """BRD-012, P5 (revisado): pasta do Google Drive sincronizada,
        configurada em Configurações. `None` se desligado ou sem pasta —
        nesse caso o SIC segue só com o registro local, como hoje."""
        if not self._seg_settings.value(SEG_SHARED_ENABLED_KEY, False, type=bool):
            return None
        folder = self._seg_settings.value(SEG_SHARED_FOLDER_KEY, "")
        if not folder:
            return None
        return SyncedFolderRegistryStore(Path(folder))

    def _seg_all_records(self) -> list[SegmentadaRecord]:
        """Registros locais + compartilhados (quando ligado), para o
        reconhecimento (Etapa 3) enxergar o que a equipe inteira já sabe,
        não só o que esta máquina gravou. Falha ao ler a pasta compartilhada
        (Drive fora do ar, ainda sincronizando) nunca impede nada — cai só
        no que já existe localmente, mesma regra da seção 8."""
        local = self._seg_registry_store.load()
        shared_store = self._seg_shared_store()
        if not shared_store:
            return local
        try:
            shared = shared_store.load()
        except OSError:
            return local
        return merge_by_pricebook_id(local, shared)

    def _update_seg_banner(self, candidate: ListaCandidate) -> None:
        loja_key, marca_key = self._current_loja_and_brand()
        if not marca_key:
            self._seg_banner.hide()
            self._seg_resolve_result = None
            return

        result = resolve_seg_registry(
            candidate.sheet_name, candidate.lp_label, marca_key, loja_key or "",
            self._seg_all_records(),
        )
        self._seg_resolve_result = result

        if result.confidence == MatchConfidence.NONE:
            self._seg_banner.hide()
            return

        text = self._format_seg_banner(candidate, result)
        self._seg_banner_lbl.setText(text)
        if result.is_risky:
            self._seg_banner.setStyleSheet(
                "background:#3a1e1e; border:1px solid #c62828; border-radius:6px;"
            )
            self._seg_banner_lbl.setStyleSheet("color:#ffcdd2; background:transparent; font-size:11px;")
        else:
            self._seg_banner.setStyleSheet(
                "background:#1e3a2f; border:1px solid #2e7d32; border-radius:6px;"
            )
            self._seg_banner_lbl.setStyleSheet("color:#c8e6c9; background:transparent; font-size:11px;")
        self._seg_banner_btn_use.setEnabled(result.record is not None)
        self._seg_banner.show()

    def _format_seg_banner(self, candidate: ListaCandidate, result: ResolveResult) -> str:
        record = result.record
        if record is None:
            return f"⚠  {candidate.sheet_name}: " + "; ".join(result.reasons or ["vínculo ambíguo"])

        parts = [f"{candidate.sheet_name} → {record.pricebook_id}"]
        if record.campaign_name:
            parts.append(f'"{record.campaign_name}"')
        if record.online_from and record.online_to:
            parts.append(f"{self._fmt_iso_date(record.online_from)}–{self._fmt_iso_date(record.online_to)}")
        if record.created_at:
            who = f" por {record.created_by}" if record.created_by else ""
            parts.append(f"registrada em {self._fmt_iso_date(record.created_at)}{who}")

        text = "  ·  ".join(parts)

        if record.sku_count is not None:
            after = len(candidate.rows)
            if after < record.sku_count:
                diff = record.sku_count - after
                text += (
                    f"\n⚠  antes {record.sku_count} SKUs / agora {after} — "
                    f"{diff} produto(s) vão perder o preço segmentado ao importar."
                )
            else:
                text += f"\n antes {record.sku_count} SKUs / agora {after}"

        if result.reasons:
            text += "\n⚠  " + "; ".join(result.reasons)
        return text

    def _on_seg_banner_use(self) -> None:
        result = self._seg_resolve_result
        if not result or not result.record:
            return
        self._seg_input_pbid.setText(result.record.pricebook_id)
        self._seg_pbid_touched = True
        self._seg_is_update_mode = True
        self._seg_banner.hide()

    def _on_seg_banner_ignore(self) -> None:
        self._seg_is_update_mode = False
        self._seg_banner.hide()

    def _apply_pbid_from_runrun_id(self) -> None:
        if self._seg_pbid_touched:
            return
        loja_key, _ = self._current_loja_and_brand()
        runrun_id = self._seg_input_runrun_id.text().strip()
        pbid = build_pricebook_id(loja_key or "", runrun_id) if loja_key else None
        if pbid:
            self._seg_input_pbid.setText(pbid)

    def _on_seg_runrun_id_edited(self, _text: str) -> None:
        self._apply_pbid_from_runrun_id()
        # O número mudou — o título mostrado (se algum) não vale mais pro
        # texto atual do campo.
        self._seg_runrun_task = None
        self._seg_runrun_status_lbl.hide()

    def _on_seg_pbid_edited(self, _text: str) -> None:
        self._seg_pbid_touched = True
        self._seg_is_update_mode = False

    def _on_seg_loja_changed(self, _index: int) -> None:
        self._apply_pbid_from_runrun_id()
        if self._seg_selected_lista:
            self._update_seg_banner(self._seg_selected_lista)

    # ── BRD-012, Etapa 5/P6: conferência da tarefa no Runrun.it ────────────
    def _seg_runrun_client(self) -> Optional[RunrunClient]:
        if not self._seg_settings.value(RUNRUN_ENABLED_KEY, False, type=bool):
            return None
        app_key = self._seg_settings.value(RUNRUN_APP_KEY_KEY, "")
        user_token = self._seg_settings.value(RUNRUN_USER_TOKEN_KEY, "")
        if not (app_key and user_token):
            return None
        return RunrunClient(app_key, user_token, timeout=5)

    def _on_seg_runrun_id_editing_finished(self) -> None:
        """Perda de foco ou Enter — nunca a cada tecla (CA-26)."""
        number = self._seg_input_runrun_id.text().strip()
        if not number:
            self._seg_runrun_status_lbl.hide()
            return

        cached = self._seg_runrun_cache.get(number)
        if cached:
            self._on_seg_runrun_task_fetched(cached)
            return

        client = self._seg_runrun_client()
        if not client:
            return  # integração desligada/sem credencial — tela segue como hoje (CA-23)

        # Intervalo mínimo entre consultas — defesa extra além de nunca
        # disparar por tecla (proteção da App-Key, Etapa 5).
        now = datetime.now(timezone.utc)
        if self._seg_runrun_last_query_at and (now - self._seg_runrun_last_query_at).total_seconds() < 1.5:
            return
        self._seg_runrun_last_query_at = now

        self._seg_runrun_status_lbl.setText("Consultando tarefa no Runrun.it…")
        self._seg_runrun_status_lbl.setStyleSheet("font-size:11px; background:transparent; color:#9e9e9e;")
        self._seg_runrun_status_lbl.show()

        self._seg_runrun_worker = RunrunTaskFetchWorker(client, number, self)
        self._seg_runrun_worker.finished.connect(self._on_seg_runrun_task_fetched)
        self._seg_runrun_worker.error.connect(self._on_seg_runrun_task_error)
        self._seg_runrun_worker.start()

    def _on_seg_runrun_task_fetched(self, task: RunrunTask) -> None:
        self._seg_runrun_cache[task.number] = task
        self._seg_runrun_task = task

        parts = [f'"{task.title}"' if task.title else "(sem título)"]
        is_risky = False
        if task.is_closed:
            parts.append("⚠ tarefa encerrada no Runrun.it")
            is_risky = True

        record = self._seg_resolve_result.record if self._seg_resolve_result else None
        if record and record.campaign_name and task.title:
            if record.campaign_name.strip().upper() != task.title.strip().upper():
                parts.append(f'⚠ diverge do registro ("{record.campaign_name}")')
                is_risky = True

        self._seg_runrun_status_lbl.setText("  ·  ".join(parts))
        color = "#ff8a80" if is_risky else "#9e9e9e"
        self._seg_runrun_status_lbl.setStyleSheet(f"font-size:11px; background:transparent; color:{color};")
        self._seg_runrun_status_lbl.show()

    def _on_seg_runrun_task_error(self, message: str) -> None:
        # CA-22/CA-23: discreto — nunca trava o campo nem bloqueia nada.
        self._seg_runrun_task = None
        self._seg_runrun_status_lbl.setText("Não foi possível confirmar a tarefa no Runrun.it.")
        self._seg_runrun_status_lbl.setStyleSheet("font-size:11px; background:transparent; color:#9e9e9e;")
        self._seg_runrun_status_lbl.show()

    def _run_seg_generate(self) -> None:
        pricebook_id = self._seg_input_pbid.text().strip()
        if not pricebook_id:
            QMessageBox.warning(self, "Segmentadas", "Informe o <b>ID do Pricebook</b>.")
            return
        if any(ch.isspace() for ch in pricebook_id):
            QMessageBox.warning(
                self, "Segmentadas",
                "O <b>ID do Pricebook</b> não pode conter espaços."
            )
            return
        if pricebook_id.lower() in RESERVED_PRICEBOOK_IDS:
            show_rejection_dialog(
                self,
                f'<b>ID informado:</b> "{pricebook_id}"\n\n'
                "Este é o ID de uma pricebook <b>default</b> (DE/POR) de produção. "
                "Importar um XML segmentado com esse ID sobrescreveria a pricebook principal.\n\n"
                "Use um ID exclusivo para a campanha (ex.: NAT-RR1881).",
                header="ID de pricebook reservado",
            )
            return

        marca_key = self._seg_detected_brand
        if not marca_key:
            QMessageBox.warning(
                self, "Segmentadas",
                "Não foi possível identificar a marca da grade. "
                "Selecione manualmente no campo que apareceu abaixo do arquivo."
            )
            return

        loja_key = self._seg_combo_loja.currentData()
        if loja_key not in (marca_key, "ml"):
            marca_label = BRAND_LABELS.get(marca_key, marca_key)
            show_rejection_dialog(
                self,
                f"<b>Marca da grade:</b> {marca_label}\n"
                f"<b>Loja selecionada:</b> {self._seg_combo_loja.currentText()}\n\n"
                "SKUs de uma marca não podem ser publicados na pricebook de outra marca. "
                "Escolha a Loja da mesma marca ou <b>Minha Loja (CB)</b>, que aceita todas.",
                header="Loja incompatível com a marca",
            )
            return

        candidate = self._seg_selected_lista
        if not candidate or not candidate.rows:
            QMessageBox.warning(
                self, "Segmentadas",
                "Selecione uma lista com pelo menos um SKU com preço segmentado válido."
            )
            return

        d_start = self._seg_date_start.date()
        d_end = self._seg_date_end.date()
        dt_start = datetime(
            d_start.year(), d_start.month(), d_start.day(),
            self._seg_hour_start.currentIndex(), self._seg_min_start.currentIndex(),
        )
        dt_end = datetime(
            d_end.year(), d_end.month(), d_end.day(),
            self._seg_hour_end.currentIndex(), self._seg_min_end.currentIndex(),
        )
        if dt_end <= dt_start:
            QMessageBox.warning(
                self, "Segmentadas",
                "A <b>Data/Hora Fim</b> deve ser posterior à Data/Hora Início."
            )
            return

        # BRD-012, P3 (CA-08): único acréscimo às validações — só pergunta
        # quando o operador clicou em "Usar (ATUALIZAÇÃO)" no banner.
        if self._seg_is_update_mode and self._seg_resolve_result and self._seg_resolve_result.record:
            record = self._seg_resolve_result.record
            confirm_msg = (
                f"Isso vai <b>ATUALIZAR</b> o pricebook <b>{pricebook_id}</b>, "
                "substituindo a lista de preços existente no Salesforce."
            )
            if record.sku_count is not None and len(candidate.rows) < record.sku_count:
                diff = record.sku_count - len(candidate.rows)
                confirm_msg += (
                    f"\n\n⚠ {diff} produto(s) que estavam na lista anterior "
                    "não estão nesta e vão <b>perder o preço segmentado</b> ao importar."
                )
            resp = QMessageBox.question(
                self, "Confirmar atualização", confirm_msg,
                QMessageBox.Yes | QMessageBox.No,
            )
            if resp != QMessageBox.Yes:
                return

        # BRD-012, Etapa 5 (CA-24): título do Runrun.it divergente do
        # registro exige confirmação explícita — independe do modo
        # ATUALIZAÇÃO, porque pode ser o primeiro cadastro com o número
        # errado digitado.
        runrun_record = self._seg_resolve_result.record if self._seg_resolve_result else None
        if (
            self._seg_runrun_task and self._seg_runrun_task.title
            and runrun_record and runrun_record.campaign_name
            and runrun_record.campaign_name.strip().upper() != self._seg_runrun_task.title.strip().upper()
        ):
            resp = QMessageBox.question(
                self, "Conferir tarefa do Runrun.it",
                f"O título da tarefa no Runrun.it é <b>\"{self._seg_runrun_task.title}\"</b>, "
                f"diferente da campanha registrada (<b>\"{runrun_record.campaign_name}\"</b>).\n\n"
                "Isso pode indicar número de tarefa errado ou registro desatualizado. "
                "Confirma que é a campanha certa mesmo assim?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if resp != QMessageBox.Yes:
                return

        parent_id = LOJA_PARENT_IDS[loja_key]

        online_from, online_to = SegmentadoEngine.compute_online_window(dt_start, dt_end)
        display_name = self._seg_input_display_name.text().strip() or None
        xml_bytes = SegmentadoEngine.build_xml(
            pricebook_id, parent_id, online_from, online_to, candidate.rows,
            display_name=display_name,
        )
        self._seg_xml = xml_bytes
        # Capturados no momento da geração (não relidos ao salvar) — o nome
        # do arquivo sugerido precisa refletir o que está dentro do XML, não
        # o que os campos mostram se o usuário mexer neles depois de gerar.
        self._seg_generated_campaign_start = dt_start.date()
        self._seg_generated_label = candidate.lp_label or candidate.sheet_name

        # BRD-012, P2: registro pendente — só grava de verdade em
        # _save_seg_pricebook, depois que o arquivo for escrito.
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        existing = next(
            (r for r in self._seg_all_records() if r.pricebook_id == pricebook_id),
            None,
        )
        self._seg_pending_record = SegmentadaRecord(
            pricebook_id=pricebook_id,
            sheet_name=candidate.sheet_name,
            brand=marca_key,
            loja=loja_key,
            lp_label=candidate.lp_label,
            campaign_name=display_name or candidate.lp_label or candidate.sheet_name,
            online_from=online_from,
            online_to=online_to,
            sku_count=len(candidate.rows),
            created_at=existing.created_at if existing else now_iso,
            updated_at=now_iso,
            created_by=getpass.getuser(),
        )

        self._seg_stat_skus.set_value(str(len(candidate.rows)))
        self._seg_stat_lista.set_value(candidate.sheet_name, "#7e57c2")
        self._seg_stat_lp.set_value(candidate.lp_label or "—", "#26a69a")
        self._seg_stat_loja.set_value(self._seg_combo_loja.currentText(), "#60a5fa")
        self._seg_stat_periodo.set_value(
            f"{dt_start.strftime('%d/%m %H:%M')} – {dt_end.strftime('%d/%m %H:%M')}", "#888888"
        )
        self._seg_result_widget.show()

        brand_label = BRAND_LABELS.get(marca_key, marca_key)
        HistoryEngine.add_entry(
            "Exportador",
            brand_label,
            f"Pricebook Segmentado ({candidate.lp_label or candidate.sheet_name}) gerado — "
            f"{len(candidate.rows)} SKUs.",
        )

        if p := self.parent():
            if hasattr(p, "show_status"):
                p.show_status(f"Pricebook Segmentado: {len(candidate.rows)} SKUs")

    def _save_seg_pricebook(self) -> None:
        if not self._seg_xml:
            return
        campaign_start = self._seg_generated_campaign_start or date.today()
        detected = self._seg_detected_brand
        brand = (BRAND_LABELS.get(detected, detected) if detected else "").upper()
        pb_id = "".join(ch if (ch.isalnum() or ch in "-_") else "_" for ch in self._seg_input_pbid.text().strip())
        label_raw = (self._seg_generated_label or "").strip().upper()
        label_token = "".join(ch if (ch.isalnum() or ch in "-_") else "_" for ch in label_raw) or "LISTA"
        default = (
            f"---{campaign_start.strftime('%d')}.{campaign_start.strftime('%m')}"
            f"-{brand}-PRICEBOOK-SEGMENTADA-{label_token}-{pb_id or 'ID'}.xml"
        )

        path, _ = QFileDialog.getSaveFileName(self, "Salvar Pricebook Segmentado XML", default, "XML (*.xml)")
        if path:
            with open(path, "wb") as f:
                f.write(self._seg_xml)
            QMessageBox.information(self, "Salvo", f"Pricebook Segmentado salvo em:\n{path}")

            # BRD-012, P2/P5: só agora o registro é persistido — o XML foi
            # de fato escrito em disco. Em segundo plano; falha em qualquer
            # fonte nunca impede o salvamento, que já aconteceu.
            if self._seg_pending_record:
                stores: list = [self._seg_registry_store]
                xlsx_source = None
                xlsx_path = None
                shared_store = self._seg_shared_store()
                if shared_store is not None:
                    stores.append(shared_store)
                    xlsx_source = shared_store
                    folder = self._seg_settings.value(SEG_SHARED_FOLDER_KEY, "")
                    if folder:
                        xlsx_path = Path(folder) / "segmentadas_registry.xlsx"

                self._seg_registry_worker = SegmentadaRegistryWriteWorker(
                    stores, self._seg_pending_record, self,
                    xlsx_source=xlsx_source, xlsx_path=xlsx_path,
                )
                self._seg_registry_worker.start()

    def _clear_seg_tab(self) -> None:
        self._seg_dz_grade.clear()
        self._seg_badge.hide()
        self._seg_marca_fallback_row.hide()
        self._seg_combo_marca_fallback.setCurrentIndex(0)
        self._seg_detected_brand = None
        self._seg_warn_lbl.hide()
        self._seg_banner.hide()
        self._seg_input_runrun_id.clear()
        self._seg_runrun_task = None
        self._seg_runrun_status_lbl.hide()
        self._seg_input_pbid.clear()
        self._seg_pbid_touched = False
        self._seg_resolve_result = None
        self._seg_is_update_mode = False
        self._seg_input_display_name.clear()
        self._seg_combo_loja.setCurrentIndex(0)
        self._seg_date_start.setDate(QDate.currentDate())
        self._seg_hour_start.setCurrentIndex(0)
        self._seg_min_start.setCurrentIndex(0)
        self._seg_date_end.setDate(QDate.currentDate())
        self._seg_hour_end.setCurrentIndex(23)
        self._seg_min_end.setCurrentIndex(59)
        self._seg_table.setRowCount(0)
        self._seg_lista_box.hide()
        self._seg_result_widget.hide()
        self._seg_progress_bar.hide()
        self._seg_status_lbl.hide()
        self._seg_btn_generate.setEnabled(False)
        self._seg_scan_result = None
        self._seg_selected_lista = None
        self._seg_xml = None
        self._seg_generated_campaign_start = None
        self._seg_generated_label = None
        self._seg_pending_record = None
