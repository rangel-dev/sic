"""
Executive Nexus Dashboard — Home View
Modern, data-driven landing page for SIC.
"""
import json
from datetime import date, datetime, timedelta
from typing import Optional
from PySide6.QtCore import Qt, QSettings, QSize, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QHBoxLayout, 
    QLabel, 
    QScrollArea, 
    QSizePolicy, 
    QVBoxLayout, 
    QWidget,
    QGridLayout,
    QSpacerItem,
    QFrame,
    QPushButton
)
from src.ui.components.base_widgets import Divider, PulseStatus, KpiWidget
from src.ui.components.charts import DonutChart, TrendAreaChart, format_delta, palette
from src.ui.components.module_detail_dialog import ModuleDetailDialog
from src.core.history_engine import HistoryEngine
from src.core.version import VERSION
from src.core import telemetry

# Ícone/cor por nome de módulo COMO GRAVADO NO HISTÓRICO (o dashboard usa
# estes nomes; _MODULE_NAV abaixo usa os nomes da navegação, que diferem).
_DASHBOARD_ICONS = {
    "Auditor":             ("✓", "#BB88FF"),
    "Exportador":          ("↕", "#FF8050"),
    "Cupons":              ("◉", "#26a69a"),
    "Cadastro/Pontuação":  ("≡", "#60a5fa"),
    "Cadastro/Gestor GCP": ("◎", "#42a5f5"),
}

# Mapa de módulo → (ícone, índice de navegação, cor do card)
_MODULE_NAV = {
    "Gerador":    ("⊕", 1, "#FF8050"),
    "Sync":       ("↕", 2, "#FF8050"),
    "Auditor":    ("✓", 3, "#BB88FF"),
    "Volumetria": ("◎", 4, "#BB88FF"),
    "Cadastro":   ("≡", 5, "#60a5fa"),
    "Menus CB":   ("≈", 8, "#42a5f5"),
    "Histórico":  ("◔", 7, "#888888"),
}

def _tinted_chip(text: str, hex_color: str, *, font_size: int = 12) -> QLabel:
    """Chip/pílula com fundo translúcido na cor dada (visual moderno)."""
    c = QColor(hex_color)
    chip = QLabel(text)
    chip.setStyleSheet(
        f"background-color: rgba({c.red()}, {c.green()}, {c.blue()}, 0.13); "
        f"color: {hex_color}; border-radius: 10px; padding: 3px 10px; "
        f"font-size: {font_size}px; font-weight: 700;"
    )
    return chip


class _ModuleCard(QFrame):
    """Card clicável do dashboard Erros × Acertos: donut + nome + chips de
    contagem. O clique chama o callback recebido (abre o drill-down)."""

    def __init__(self, module: str, icon: str, icon_color: str, data: dict,
                 theme: str, on_click, parent=None):
        super().__init__(parent)
        self.setObjectName("card_flat")
        self.setCursor(Qt.PointingHandCursor)
        self._on_click = on_click
        pal = palette(theme)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 16, 14, 16)
        layout.setSpacing(16)

        donut = DonutChart(diameter=88)
        donut.set_theme(theme)
        donut.set_values(data.get("ok"), data.get("erro", 0))
        layout.addWidget(donut)

        info = QVBoxLayout()
        info.setSpacing(8)

        name_row = QHBoxLayout()
        name_row.setSpacing(8)
        icon_chip = _tinted_chip(icon, icon_color, font_size=13)
        name_row.addWidget(icon_chip)
        name = QLabel(module)
        name.setStyleSheet("font-size: 15px; font-weight: 800; background: transparent;")
        name_row.addWidget(name)
        name_row.addStretch()
        info.addLayout(name_row)

        chips_row = QHBoxLayout()
        chips_row.setSpacing(6)
        ok = data.get("ok")
        erro = data.get("erro", 0)
        if ok is not None:
            chips_row.addWidget(
                _tinted_chip(f"✓ {ok:,}".replace(",", "."), pal["ok"]))
        chips_row.addWidget(
            _tinted_chip(f"✗ {erro:,}".replace(",", "."), pal["erro"]))
        falhas = data.get("falhas", 0)
        if falhas:
            chips_row.addWidget(_tinted_chip(f"⚠ {falhas}", pal["falha"]))
        delta = format_delta(data.get("delta"))
        if delta:
            delta_text, color_key = delta
            chips_row.addWidget(_tinted_chip(delta_text, pal[color_key], font_size=11))
        chips_row.addStretch()
        info.addLayout(chips_row)

        detail = QLabel("Ver detalhes")
        detail.setObjectName("label_hint")
        detail.setStyleSheet("font-size: 10px;")
        info.addWidget(detail)
        info.addStretch()

        layout.addLayout(info, 1)

        chevron = QLabel("›")
        chevron.setObjectName("label_muted")
        chevron.setStyleSheet("font-size: 22px; font-weight: 300;")
        layout.addWidget(chevron)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._on_click()
        super().mousePressEvent(event)


class HomeView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.window = parent # MainWindow
        stored_days = int(QSettings("SIC", "SIC_Suite").value("dashboard_period_days", 30))
        self._period_days = stored_days if stored_days in (7, 30, 90) else 30
        self._setup_ui()
        self._update_period_buttons()
        # Adiar a query ao banco para depois da janela ser pintada (evita bloqueio pré-render)
        QTimer.singleShot(50, self.refresh_stats)

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        root.addWidget(scroll)

        container = QWidget()
        scroll.setWidget(container)
        
        self.main_layout = QVBoxLayout(container)
        self.main_layout.setContentsMargins(40, 40, 40, 40)
        self.main_layout.setSpacing(0)

        # ─── HEADER AREA ──────────────────────────────────────────────────────
        header = QHBoxLayout()
        header.setSpacing(12)
        
        greeting = self._get_greeting()
        self.title_lbl = QLabel(greeting)
        self.title_lbl.setObjectName("nexus_greeting")
        self.title_lbl.setStyleSheet("font-size: 28px; font-weight: 800;")
        header.addWidget(self.title_lbl)

        header.addWidget(PulseStatus())
        
        status_lbl = QLabel("Sistemas Prontos")
        status_lbl.setObjectName("label_success")
        status_lbl.setStyleSheet("font-size: 12px; font-weight: 600; text-transform: uppercase;")
        header.addWidget(status_lbl)
        
        header.addStretch()
        self.main_layout.addLayout(header)

        sub_header = QLabel(f"Bem-vindo ao centro de comando SIC  ·  Versão {VERSION}")
        sub_header.setObjectName("label_muted")
        sub_header.setStyleSheet("font-size: 13px; margin-bottom: 30px;")
        self.main_layout.addWidget(sub_header)

        # ─── KPI ROW ──────────────────────────────────────────────────────────
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(20)

        self.kpi_total = KpiWidget("Operações Realizadas", "0", "📊")
        self.kpi_brands = KpiWidget("Marcas Ativas", "0", "🏢")
        self.kpi_status = KpiWidget("Módulos Ativos (7 dias)", "0", "🧩")

        kpi_row.addWidget(self.kpi_total)
        kpi_row.addWidget(self.kpi_brands)
        kpi_row.addWidget(self.kpi_status)
        kpi_row.addStretch()
        
        self.main_layout.addLayout(kpi_row)
        self.main_layout.addSpacing(40)

        # ─── ERROS × ACERTOS POR MÓDULO (Tarefa 7) ────────────────────────────
        self._build_chart_section()

        # ─── NOVIDADES DO SISTEMA ──────────────────────────────────────────────
        self._build_news_section()

        # ─── RECENT ACTIVITY TIMELINE ──────────────────────────────────────────
        self.main_layout.addWidget(Divider())
        self.main_layout.addSpacing(25)
        
        activity_header = QHBoxLayout()
        act_title = QLabel("Timeline de Operações")
        act_title.setStyleSheet("font-size: 16px; font-weight: 700;")
        activity_header.addWidget(act_title)
        activity_header.addStretch()
        
        view_all = QPushButton("Ver Histórico Completo →")
        view_all.setObjectName("btn_ghost")
        view_all.setCursor(Qt.PointingHandCursor)
        view_all.clicked.connect(lambda: self.window._switch(7))
        activity_header.addWidget(view_all)
        
        self.main_layout.addLayout(activity_header)
        self.main_layout.addSpacing(15)

        self.activity_container = QVBoxLayout()
        self.activity_container.setSpacing(10)
        self.main_layout.addLayout(self.activity_container)

        self.main_layout.addStretch()

    def _build_chart_section(self):
        header = QHBoxLayout()
        title = QLabel("VISÃO EXECUTIVA · ERROS × ACERTOS POR MÓDULO")
        title.setObjectName("label_muted")
        title.setStyleSheet(
            "font-size: 11px; font-weight: 700; letter-spacing: 1.5px;"
        )
        header.addWidget(title)
        header.addStretch()

        self._period_buttons: dict[int, QPushButton] = {}
        for days in (7, 30, 90):
            btn = QPushButton(f"{days} dias")
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _c=False, d=days: self._on_period_selected(d))
            header.addWidget(btn)
            self._period_buttons[days] = btn

        self.main_layout.addLayout(header)
        self.main_layout.addSpacing(14)

        self._build_hero_card()
        self.main_layout.addSpacing(16)

        self._trend_card = QFrame()
        self._trend_card.setObjectName("card_flat")
        trend_layout = QVBoxLayout(self._trend_card)
        trend_layout.setContentsMargins(20, 16, 20, 12)
        trend_layout.setSpacing(6)

        trend_title = QLabel("TENDÊNCIA GERAL · ERROS POR DIA (TODOS OS MÓDULOS)")
        trend_title.setObjectName("label_muted")
        trend_title.setStyleSheet(
            "font-size: 10px; font-weight: 700; letter-spacing: 1px;"
        )
        trend_layout.addWidget(trend_title)

        self._trend_chart = TrendAreaChart()
        trend_layout.addWidget(self._trend_chart)

        self.main_layout.addWidget(self._trend_card)
        self.main_layout.addSpacing(16)

        self._cards_container = QWidget()
        self._cards_grid = QGridLayout(self._cards_container)
        self._cards_grid.setContentsMargins(0, 0, 0, 0)
        self._cards_grid.setSpacing(16)
        self.main_layout.addWidget(self._cards_container)

        self._chart_empty_lbl = QLabel(
            "Sem dados de erros/acertos no período — execute operações nos "
            "módulos para alimentar o dashboard."
        )
        self._chart_empty_lbl.setObjectName("label_hint")
        self._chart_empty_lbl.setStyleSheet("font-size: 12px;")
        self._chart_empty_lbl.setWordWrap(True)
        self.main_layout.addWidget(self._chart_empty_lbl)

        self.main_layout.addSpacing(40)

    def _build_hero_card(self):
        self._hero_card = QFrame()
        self._hero_card.setObjectName("card_flat")
        self._hero_card.setProperty("accentLeft", "true")
        layout = QHBoxLayout(self._hero_card)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(24)

        self._hero_donut = DonutChart(diameter=100)
        layout.addWidget(self._hero_donut)

        info = QVBoxLayout()
        info.setSpacing(6)

        eyebrow = QLabel("CONFORMIDADE GERAL DA OPERAÇÃO")
        eyebrow.setObjectName("label_muted")
        eyebrow.setStyleSheet(
            "font-size: 10px; font-weight: 700; letter-spacing: 1px;"
        )
        info.addWidget(eyebrow)

        self._hero_pct_lbl = QLabel("—")
        self._hero_pct_lbl.setStyleSheet("font-size: 30px; font-weight: 800; background: transparent;")
        info.addWidget(self._hero_pct_lbl)

        self._hero_highlights_lbl = QLabel("")
        self._hero_highlights_lbl.setWordWrap(True)
        self._hero_highlights_lbl.setStyleSheet("font-size: 13px; background: transparent;")
        info.addWidget(self._hero_highlights_lbl)

        self._hero_empty_lbl = QLabel(
            "Ainda sem dados suficientes no período selecionado."
        )
        self._hero_empty_lbl.setObjectName("label_hint")
        self._hero_empty_lbl.setStyleSheet("font-size: 12px;")
        self._hero_empty_lbl.hide()
        info.addWidget(self._hero_empty_lbl)

        info.addStretch()
        layout.addLayout(info, 1)

        self.main_layout.addWidget(self._hero_card)

    def _on_period_selected(self, days: int):
        self._period_days = days
        QSettings("SIC", "SIC_Suite").setValue("dashboard_period_days", days)
        self._update_period_buttons()
        self.refresh_stats()

    def _update_period_buttons(self):
        for days, btn in self._period_buttons.items():
            active = days == self._period_days
            btn.setObjectName("btn_primary" if active else "btn_ghost")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _build_news_section(self):
        news_header = QHBoxLayout()
        news_title = QLabel("ÚLTIMAS NOVIDADES")
        news_title.setObjectName("label_muted")
        news_title.setStyleSheet(
            "font-size: 11px; font-weight: 700; letter-spacing: 1.5px;"
        )
        news_header.addWidget(news_title)
        
        news_header.addStretch()

        btn_sobre = QPushButton("Ver notas da versão →")
        btn_sobre.setObjectName("btn_ghost")
        btn_sobre.setCursor(Qt.PointingHandCursor)
        if hasattr(self, 'window') and self.window:
            btn_sobre.clicked.connect(lambda: self.window._switch(11))
        news_header.addWidget(btn_sobre)
        
        self.main_layout.addLayout(news_header)
        self.main_layout.addSpacing(12)

        from src.core.changelog_data import CHANGELOG
        latest = CHANGELOG[0] if CHANGELOG else None

        if latest:
            card = QFrame()
            card.setObjectName("card_flat")
            card.setProperty("accentLeft", "true")
            layout = QVBoxLayout(card)
            layout.setContentsMargins(20, 16, 20, 16)
            layout.setSpacing(8)

            ver_lbl = QLabel(f"Versão {latest['version']}  ·  {latest.get('date', '')}")
            ver_lbl.setObjectName("label_accent")
            ver_lbl.setStyleSheet("font-size: 12px; font-weight: 700;")
            layout.addWidget(ver_lbl)

            TYPE_MAP = {
                "feat": "Novidade",
                "fix":  "Correção",
                "perf": "Performance",
                "chore":"Ajuste",
            }

            for entry in latest["entries"][:2]:
                if len(entry) >= 2:
                    etype, etext = entry[0], entry[1]
                    label = TYPE_MAP.get(etype, "Info")
                    lbl = QLabel(f"• <b>{label}:</b> {etext}")
                    lbl.setWordWrap(True)
                    lbl.setObjectName("label_muted")
                    lbl.setStyleSheet("font-size: 13px;")
                    layout.addWidget(lbl)

            if len(latest["entries"]) > 2:
                more_lbl = QLabel(f"<i>E mais {len(latest['entries']) - 2} melhorias...</i>")
                more_lbl.setObjectName("label_muted")
                more_lbl.setStyleSheet("font-size: 11px;")
                layout.addWidget(more_lbl)

            self.main_layout.addWidget(card)
        else:
            lbl = QLabel("Nenhuma novidade registrada.")
            lbl.setObjectName("label_muted")
            lbl.setStyleSheet("font-size: 12px;")
            self.main_layout.addWidget(lbl)
            
        self.main_layout.addSpacing(32)

    def _get_greeting(self) -> str:
        hour = datetime.now().hour
        if hour < 12: return "Bom dia"
        if hour < 18: return "Boa tarde"
        return "Boa noite"

    def _compute_kpis(self, local_entries: list[dict]) -> tuple[int, int, int]:
        """(operações, marcas ativas, módulos ativos em 7 dias). Usa
        telemetria de equipe (Tarefa 3) se a pasta compartilhada do Drive
        estiver configurada; senão cai no history.db local desta instalação."""
        if telemetry.get_shared_folder_path():
            kpis = telemetry.compute_team_kpis(telemetry.read_team_events())
            return kpis["operations"], kpis["brands_active"], kpis["modules_active_7d"]

        total = len(local_entries)
        brands: set = set()
        for e in local_entries:
            brands |= telemetry.normalize_brands(e.get("brand"))
        brands_active = len(brands)

        cutoff = datetime.now() - timedelta(days=7)
        modules_7d = set()
        for e in local_entries:
            ts, module = e.get("timestamp"), e.get("module")
            if not ts or not module:
                continue
            try:
                when = datetime.fromisoformat(ts)
            except ValueError:
                continue
            if when >= cutoff:
                modules_7d.add(module)

        return total, brands_active, len(modules_7d)

    @staticmethod
    def _parse_breakdown(raw) -> dict:
        """Aceita dict (telemetria JSONL) ou string JSON (history.db)."""
        if isinstance(raw, dict):
            return raw
        if isinstance(raw, str) and raw:
            try:
                parsed = json.loads(raw)
                return parsed if isinstance(parsed, dict) else {}
            except (json.JSONDecodeError, ValueError):
                return {}
        return {}

    @staticmethod
    def _compute_delta(slot: dict) -> Optional[dict]:
        """Compara a janela atual com a janela anterior de mesmo tamanho.
        Retorna None se não há dado suficiente no período anterior (evita
        um delta enganoso, ex. "0 → 5" aparentando +∞%).

        kind="pp": módulo com contagem de acertos — delta de conformidade em
        pontos percentuais (subiu = melhorou = "ok"; desceu = "erro").
        kind="pct": módulo sem contagem de acertos — variação % de erros
        brutos (subiu = piorou = "erro"; desceu = melhorou = "ok")."""
        ok, erro = slot.get("ok"), slot.get("erro") or 0
        prev_ok, prev_erro = slot.get("prev_ok"), slot.get("prev_erro")

        if ok is not None and prev_ok is not None:
            cur_total = ok + erro
            prev_total = prev_ok + (prev_erro or 0)
            if cur_total == 0 or prev_total == 0:
                return None
            diff = (ok / cur_total * 100) - (prev_ok / prev_total * 100)
            if abs(diff) < 0.05:
                return None
            return {"kind": "pp", "value": diff, "better": diff > 0}

        if prev_erro:
            diff_pct = (erro - prev_erro) / prev_erro * 100
            if abs(diff_pct) < 1:
                return None
            return {"kind": "pct", "value": diff_pct, "better": diff_pct < 0}

        return None

    def _compute_overall(self, rows: list[dict]) -> dict:
        """Resumo executivo: conformidade geral ponderada pelo volume de
        cada módulo (não média simples — um módulo com 50 mil SKUs pesa mais
        que um com 200), melhor/pior módulo e total de falhas de execução."""
        measured = [r for r in rows if r.get("ok") is not None]
        total_ok = sum(r["ok"] for r in measured)
        total_all = sum(r["ok"] + r["erro"] for r in measured)
        overall_pct = (total_ok / total_all * 100) if total_all else None

        prev_measured = [r for r in rows if r.get("prev_ok") is not None]
        prev_ok_sum = sum(r["prev_ok"] for r in prev_measured)
        prev_all_sum = sum(
            r["prev_ok"] + (r.get("prev_erro") or 0) for r in prev_measured
        )
        prev_pct = (prev_ok_sum / prev_all_sum * 100) if prev_all_sum else None

        delta = None
        if overall_pct is not None and prev_pct is not None:
            diff = overall_pct - prev_pct
            if abs(diff) >= 0.05:
                delta = {"kind": "pp", "value": diff, "better": diff > 0}

        best = max(
            measured, key=lambda r: r["ok"] / (r["ok"] + r["erro"]), default=None
        ) if measured else None
        with_errors = [r for r in rows if r["erro"] > 0]
        worst = max(with_errors, key=lambda r: r["erro"], default=None)

        return {
            "pct": overall_pct,
            "total_ok": total_ok,
            "total_all": total_all,
            "delta": delta,
            "best_module": best["module"] if best else None,
            "best_pct": (best["ok"] / (best["ok"] + best["erro"]) * 100) if best else None,
            "worst_module": worst["module"] if worst else None,
            "worst_erro": worst["erro"] if worst else None,
            "total_falhas": sum(r["falhas"] for r in rows),
        }

    def _compute_module_dashboard(self, local_entries: list[dict], days: int) -> dict:
        """Agrega, por módulo, os últimos `days` dias do histórico: soma de
        ok_count/error_count, nº de execuções com status="falha", série
        diária de erros/falhas, breakdown por tipo e a lista das execuções
        (para o diálogo de drill-down) — além da janela ANTERIOR de mesmo
        tamanho (só ok/erro agregados, para o delta de comparação — Tarefa
        9) e uma série diária somando erros de TODOS os módulos (gráfico de
        tendência geral). Mesma fonte dos KPIs (Tarefa 3): telemetria de
        equipe se configurada, senão history.db local. Entradas sem nenhuma
        contagem/falha e os módulos Volumetria/Menus CB (ocultados) ficam
        de fora.

        Retorna {"rows": [...], "trend_days": [...], "overall": {...}}."""
        if telemetry.get_shared_folder_path():
            # months_back precisa cobrir janela atual + anterior; o padrão
            # de 2 meses só bastava pros 30 dias fixos de antes da Tarefa 9.
            months_back = max(2, (days * 2 + 29) // 30 + 1)
            source = [
                (e.get("ts"), e.get("module"), e.get("status"),
                 e.get("ok_count"), e.get("error_count"),
                 e.get("breakdown"), e.get("action", ""))
                for e in telemetry.read_team_events(months_back=months_back)
            ]
        else:
            source = [
                (e.get("timestamp"), e.get("module"), e.get("status"),
                 e.get("ok_count"), e.get("error_count"),
                 e.get("breakdown"), e.get("action", ""))
                for e in local_entries
            ]

        today = date.today()
        now = datetime.now()
        cur_cutoff = now - timedelta(days=days)
        prev_cutoff = now - timedelta(days=days * 2)
        day_keys = [today - timedelta(days=i) for i in range(days - 1, -1, -1)]

        # Módulos fora do dashboard: Volumetria (ocultado no app) e
        # Menus CB (descontinuado pela equipe).
        hidden_modules = {"Volumetria", "Menus CB"}

        agg: dict[str, dict] = {}
        global_day_erro: dict = {}
        for ts, module, status, ok, erro, breakdown_raw, action in source:
            if not ts or not module or module in hidden_modules:
                continue
            try:
                when = datetime.fromisoformat(ts)
            except (TypeError, ValueError):
                continue
            if when < prev_cutoff:
                continue

            slot = agg.setdefault(module, {
                "module": module, "ok": None, "erro": None, "falhas": 0,
                "day_erro": {}, "day_falha": {}, "breakdown": {}, "runs": [],
                "prev_ok": None, "prev_erro": None,
            })
            is_falha = status == "falha"

            if when >= cur_cutoff:
                day = when.date()
                if is_falha:
                    slot["falhas"] += 1
                    slot["day_falha"][day] = slot["day_falha"].get(day, 0) + 1
                else:
                    if ok is not None:
                        slot["ok"] = (slot["ok"] or 0) + ok
                    if erro is not None:
                        slot["erro"] = (slot["erro"] or 0) + erro
                        slot["day_erro"][day] = slot["day_erro"].get(day, 0) + erro
                        global_day_erro[day] = global_day_erro.get(day, 0) + erro
                    for label, count in self._parse_breakdown(breakdown_raw).items():
                        if isinstance(count, (int, float)) and count > 0:
                            slot["breakdown"][label] = (
                                slot["breakdown"].get(label, 0) + int(count)
                            )
                slot["runs"].append({
                    "ts": ts, "status": "falha" if is_falha else "ok",
                    "ok": ok, "erro": erro, "action": action,
                })
            elif not is_falha:
                # Janela anterior: só agregados de ok/erro, para o delta —
                # não precisa de série diária nem lista de execuções.
                if ok is not None:
                    slot["prev_ok"] = (slot["prev_ok"] or 0) + ok
                if erro is not None:
                    slot["prev_erro"] = (slot["prev_erro"] or 0) + erro

        rows = []
        for slot in agg.values():
            if slot["ok"] is None and slot["erro"] is None and not slot["falhas"]:
                continue
            slot["erro"] = slot["erro"] or 0
            slot["period_days"] = days
            slot["days"] = [
                {"label": d.strftime("%d/%m"),
                 "erro": slot["day_erro"].get(d, 0),
                 "falha": slot["day_falha"].get(d, 0)}
                for d in day_keys
            ]
            slot["runs"].sort(key=lambda r: r["ts"], reverse=True)
            slot["delta"] = self._compute_delta(slot)
            rows.append(slot)

        rows.sort(key=lambda r: (r["erro"], r["falhas"]), reverse=True)

        trend_days = [
            {"label": d.strftime("%d/%m"), "erro": global_day_erro.get(d, 0)}
            for d in day_keys
        ]

        return {
            "rows": rows,
            "trend_days": trend_days,
            "overall": self._compute_overall(rows),
        }

    def _update_hero(self, overall: dict, theme: str):
        self._hero_donut.set_theme(theme)
        pal = palette(theme)
        pct = overall.get("pct")

        if pct is None:
            self._hero_donut.set_values(None, 0)
            self._hero_pct_lbl.setText("—")
            self._hero_highlights_lbl.setText("")
            self._hero_empty_lbl.show()
            return

        self._hero_empty_lbl.hide()
        total_ok = overall.get("total_ok", 0)
        total_all = overall.get("total_all", 0)
        self._hero_donut.set_values(total_ok, total_all - total_ok)
        pct_txt = f"{pct:.1f}%".replace(".", ",")

        delta = format_delta(overall.get("delta"))
        if delta:
            delta_text, color_key = delta
            pct_txt += (f'  <span style="font-size:14px; font-weight:700; '
                       f'color:{pal[color_key]};">{delta_text}</span>')
        self._hero_pct_lbl.setText(pct_txt)

        lines = []
        if overall.get("best_module"):
            best_pct_txt = f'{overall["best_pct"]:.1f}'.replace(".", ",")
            lines.append(
                f'🏆 Melhor desempenho: <b>{overall["best_module"]}</b> '
                f'({best_pct_txt}%)'
            )
        if overall.get("worst_module"):
            lines.append(
                f'⚠ Requer atenção: <b>{overall["worst_module"]}</b> '
                f'({overall["worst_erro"]:,} erros)'.replace(",", ".")
            )
        if overall.get("total_falhas"):
            n = overall["total_falhas"]
            lines.append(
                f'<span style="color:{pal["falha"]};">'
                f'{n} falha(s) de execução no período</span>'
            )
        self._hero_highlights_lbl.setText("<br>".join(lines))

    def _open_module_detail(self, data: dict, theme: str):
        module = data["module"]
        icon = _DASHBOARD_ICONS.get(module, ("◈", "#888"))[0]
        dialog = ModuleDetailDialog(module, icon, data, theme, self)
        dialog.exec()

    def _rebuild_module_cards(self, rows: list[dict], theme: str):
        while self._cards_grid.count():
            item = self._cards_grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        for idx, data in enumerate(rows):
            module = data["module"]
            icon, color = _DASHBOARD_ICONS.get(module, ("◈", "#888"))
            card = _ModuleCard(
                module, icon, color, data, theme,
                on_click=lambda d=data, t=theme: self._open_module_detail(d, t),
            )
            self._cards_grid.addWidget(card, idx // 2, idx % 2)

    def refresh_stats(self):
        """Pulls real data from engines."""
        try:
            entries = HistoryEngine.get_entries()

            total, brands_active, modules_7d = self._compute_kpis(entries)
            self.kpi_total.set_value(total)
            self.kpi_brands.set_value(brands_active)
            self.kpi_status.set_value(modules_7d)

            # ── Dashboard executivo: hero + tendência + módulos (Tarefas 7-9) ─
            self._update_period_buttons()
            dashboard = self._compute_module_dashboard(entries, self._period_days)
            chart_rows = dashboard["rows"]
            theme = str(QSettings("SIC", "SIC_Suite").value("theme", "light"))

            self._update_hero(dashboard["overall"], theme)

            self._trend_chart.set_theme(theme)
            self._trend_chart.set_data(dashboard["trend_days"])
            self._trend_card.setVisible(bool(chart_rows))

            self._rebuild_module_cards(chart_rows, theme)
            self._cards_container.setVisible(bool(chart_rows))
            self._chart_empty_lbl.setVisible(not chart_rows)

            # ── Atividade Recente (Timeline) ─────────────────────────
            for i in reversed(range(self.activity_container.count())):
                self.activity_container.itemAt(i).widget().setParent(None)

            if not entries:
                lbl = QLabel("Nenhuma atividade registrada no histórico.")
                lbl.setObjectName("label_hint")
                lbl.setStyleSheet("font-size: 12px;")
                self.activity_container.addWidget(lbl)
                return

            for entry in entries[:6]:
                row = QFrame()
                row.setObjectName("card_flat")
                row_layout = QHBoxLayout(row)
                row_layout.setContentsMargins(15, 12, 15, 12)

                mod = entry.get('module', 'SIC')
                icon_char = _MODULE_NAV.get(mod, ("◈", 0, "#888"))[0]
                color = _MODULE_NAV.get(mod, ("◈", 0, "#888"))[2]

                icon_lbl = QLabel(icon_char)
                icon_lbl.setStyleSheet(f"font-size: 16px; color: {color}; font-weight: bold; background: transparent;")
                icon_lbl.setFixedWidth(24)
                icon_lbl.setAlignment(Qt.AlignCenter)
                row_layout.addWidget(icon_lbl)

                info_layout = QVBoxLayout()
                info_layout.setSpacing(2)
                
                act_lbl = QLabel(entry.get('action', 'Ação desconhecida'))
                act_lbl.setStyleSheet("font-size: 13px; font-weight: 600; background: transparent;")
                info_layout.addWidget(act_lbl)

                try:
                    dt = datetime.fromisoformat(entry['timestamp'])
                    date_str = dt.strftime("%d/%m/%Y às %H:%M")
                except Exception:
                    date_str = entry.get('timestamp', '')[:16]

                meta_lbl = QLabel(f"{mod}  ·  {date_str}")
                meta_lbl.setObjectName("label_muted")
                meta_lbl.setStyleSheet("font-size: 11px;")
                info_layout.addWidget(meta_lbl)

                row_layout.addLayout(info_layout, 1)
                self.activity_container.addWidget(row)

        except Exception as e:
            print(f"Error refreshing dashboard: {e}")

    def refresh_theme(self):
        self.refresh_stats()
