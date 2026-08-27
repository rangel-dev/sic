"""
Diálogo de drill-down do dashboard "Erros × Acertos por Módulo" (Tarefa 8).

Aberto ao clicar num card de módulo na Home: mostra o donut de conformidade,
a linha do tempo diária de erros (30 dias), o breakdown por tipo de erro e a
lista das execuções do período — tudo dado passivo já gravado no histórico/
telemetria, nenhuma consulta nova a engines.
"""
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QVBoxLayout, QWidget,
)

from src.ui.components.charts import DailyBarsChart, DonutChart, format_delta, palette

_MAX_BREAKDOWN_ROWS = 8
_MAX_RUN_ROWS = 30


class ModuleDetailDialog(QDialog):
    """data esperado (montado por HomeView._compute_module_dashboard):
    {"ok": int|None, "erro": int, "falhas": int, "period_days": int,
     "days": [{"label", "erro", "falha"}, ...]  (cronológico),
     "breakdown": {rótulo: contagem},
     "delta": {"kind","value","better"}|None (Tarefa 9, comparação com o
               período anterior de mesmo tamanho),
     "runs": [{"ts", "status", "ok", "erro", "action"}, ...] (desc)}
    """

    def __init__(self, module: str, icon: str, data: dict, theme: str,
                 parent=None):
        super().__init__(parent)
        period_days = data.get("period_days", 30)
        self.setWindowTitle(f"{module} — Erros × Acertos ({period_days} dias)")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setMinimumWidth(680)
        self.setMaximumHeight(760)
        self._pal = palette(theme)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(16)

        # ── Cabeçalho: donut + números ────────────────────────────────────
        head = QHBoxLayout()
        head.setSpacing(20)

        donut = DonutChart(diameter=110)
        donut.set_theme(theme)
        donut.set_values(data.get("ok"), data.get("erro", 0))
        head.addWidget(donut)

        head_info = QVBoxLayout()
        head_info.setSpacing(4)

        title = QLabel(f"{icon}  {module}")
        title.setStyleSheet("font-size: 20px; font-weight: 800;")
        head_info.addWidget(title)

        ok = data.get("ok")
        erro = data.get("erro", 0)
        falhas = data.get("falhas", 0)
        if ok is None:
            ok_html = (f'<span style="color:{self._pal["muted"]};">'
                       f'sem contagem de acertos</span>')
        else:
            ok_html = (f'<span style="color:{self._pal["ok"]}; font-weight:700;">'
                       f'✓ {format(ok, ",").replace(",", ".")} acertos</span>')
        nums = QLabel(
            f'{ok_html}'
            f'&nbsp;&nbsp;·&nbsp;&nbsp;'
            f'<span style="color:{self._pal["erro"]}; font-weight:700;">✗ '
            f'{format(erro, ",").replace(",", ".")} erros</span>'
            f'&nbsp;&nbsp;·&nbsp;&nbsp;'
            f'<span style="color:{self._pal["falha"]}; font-weight:700;">⚠ '
            f'{falhas} falha(s) de execução</span>'
        )
        nums.setStyleSheet("font-size: 13px;")
        head_info.addWidget(nums)

        delta = format_delta(data.get("delta"))
        if delta:
            delta_text, color_key = delta
            delta_lbl = QLabel(f"{delta_text} vs. os {period_days} dias anteriores")
            delta_lbl.setStyleSheet(
                f"font-size: 12px; font-weight: 700; color: {self._pal[color_key]};"
            )
            head_info.addWidget(delta_lbl)

        hint = QLabel(f"Fonte: histórico de operações dos últimos {period_days} dias.")
        hint.setObjectName("label_hint")
        hint.setStyleSheet("font-size: 11px;")
        head_info.addWidget(hint)
        head_info.addStretch()

        head.addLayout(head_info, 1)
        root.addLayout(head)

        # ── Corpo rolável ─────────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        body_widget = QWidget()
        body = QVBoxLayout(body_widget)
        body.setContentsMargins(0, 0, 8, 0)
        body.setSpacing(16)
        scroll.setWidget(body_widget)
        root.addWidget(scroll, 1)

        # Timeline diária
        body.addWidget(self._section_label("ERROS POR DIA"))
        days_card = self._card()
        days_layout = QVBoxLayout(days_card)
        days_layout.setContentsMargins(16, 12, 16, 12)
        daily = DailyBarsChart()
        daily.set_theme(theme)
        daily.set_data(data.get("days", []))
        days_layout.addWidget(daily)
        legend = QLabel("Barra vermelha = erros no dia  ·  ● âmbar = dia com falha de execução")
        legend.setObjectName("label_hint")
        legend.setStyleSheet("font-size: 10px;")
        days_layout.addWidget(legend)
        body.addWidget(days_card)

        # Breakdown por tipo
        breakdown = data.get("breakdown") or {}
        body.addWidget(self._section_label("QUAIS FORAM OS ERROS"))
        bd_card = self._card()
        bd_layout = QVBoxLayout(bd_card)
        bd_layout.setContentsMargins(16, 12, 16, 12)
        bd_layout.setSpacing(8)
        if breakdown:
            items = sorted(breakdown.items(), key=lambda kv: kv[1], reverse=True)
            max_val = max(v for _, v in items)
            for label, value in items[:_MAX_BREAKDOWN_ROWS]:
                bd_layout.addLayout(self._breakdown_row(label, value, max_val))
            if len(items) > _MAX_BREAKDOWN_ROWS:
                more = QLabel(f"… e mais {len(items) - _MAX_BREAKDOWN_ROWS} tipo(s).")
                more.setObjectName("label_muted")
                more.setStyleSheet("font-size: 11px;")
                bd_layout.addWidget(more)
        else:
            msg = ("Este módulo não classifica erros por tipo "
                   "(ou não houve erros com classificação no período).")
            empty = QLabel(msg)
            empty.setObjectName("label_hint")
            empty.setWordWrap(True)
            empty.setStyleSheet("font-size: 12px;")
            bd_layout.addWidget(empty)
        body.addWidget(bd_card)

        # Execuções
        runs = data.get("runs", [])
        body.addWidget(self._section_label(f"EXECUÇÕES NO PERÍODO ({len(runs)})"))
        for run in runs[:_MAX_RUN_ROWS]:
            body.addWidget(self._run_row(run))
        if len(runs) > _MAX_RUN_ROWS:
            more = QLabel(f"… e mais {len(runs) - _MAX_RUN_ROWS} execução(ões) — "
                          "veja a tela Histórico para a lista completa.")
            more.setObjectName("label_muted")
            more.setStyleSheet("font-size: 11px;")
            body.addWidget(more)
        if not runs:
            empty = QLabel("Nenhuma execução registrada no período.")
            empty.setObjectName("label_hint")
            empty.setStyleSheet("font-size: 12px;")
            body.addWidget(empty)
        body.addStretch()

        # ── Rodapé ────────────────────────────────────────────────────────
        footer = QHBoxLayout()
        footer.addStretch()
        btn_close = QPushButton("Fechar")
        btn_close.setObjectName("btn_primary")
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.clicked.connect(self.accept)
        footer.addWidget(btn_close)
        root.addLayout(footer)

    # ── Helpers ───────────────────────────────────────────────────────────
    @staticmethod
    def _card() -> QFrame:
        card = QFrame()
        card.setObjectName("card_flat")
        return card

    @staticmethod
    def _section_label(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("label_muted")
        lbl.setStyleSheet(
            "font-size: 11px; font-weight: 700; letter-spacing: 1.2px;"
        )
        return lbl

    def _breakdown_row(self, label: str, value: int, max_val: int) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(10)

        text = QLabel(label)
        text.setStyleSheet("font-size: 12px;")
        text.setFixedWidth(260)
        row.addWidget(text)

        # Barra proporcional ao maior tipo (mín. 3px pra não sumir)
        bar_track = QFrame()
        bar_track.setFixedHeight(8)
        bar_track.setStyleSheet(
            f"background-color: {self._pal['track']}; border-radius: 4px;"
        )
        bar_layout = QHBoxLayout(bar_track)
        bar_layout.setContentsMargins(0, 0, 0, 0)
        bar = QFrame()
        bar.setFixedHeight(8)
        bar.setStyleSheet(
            f"background-color: {self._pal['erro']}; border-radius: 4px;"
        )
        bar_layout.addWidget(bar, max(int(1000 * value / max_val), 8))
        bar_layout.addStretch(max(1000 - max(int(1000 * value / max_val), 8), 0))
        row.addWidget(bar_track, 1)

        count = QLabel(f"{value:,}".replace(",", "."))
        count.setStyleSheet(
            f"font-size: 12px; font-weight: 700; color: {self._pal['erro']};"
        )
        count.setFixedWidth(56)
        count.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        row.addWidget(count)
        return row

    def _run_row(self, run: dict) -> QFrame:
        row = self._card()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(12)

        is_falha = run.get("status") == "falha"
        badge = QLabel("⚠ FALHA" if is_falha else "✓ OK")
        badge.setStyleSheet(
            "font-size: 10px; font-weight: 800; background: transparent; "
            f"color: {self._pal['falha'] if is_falha else self._pal['ok']};"
        )
        badge.setFixedWidth(58)
        layout.addWidget(badge)

        info = QVBoxLayout()
        info.setSpacing(2)
        action = QLabel(run.get("action", ""))
        action.setWordWrap(True)
        action.setStyleSheet("font-size: 12px; font-weight: 600; background: transparent;")
        info.addWidget(action)

        try:
            when = datetime.fromisoformat(run.get("ts", ""))
            when_str = when.strftime("%d/%m/%Y às %H:%M")
        except (TypeError, ValueError):
            when_str = str(run.get("ts", ""))[:16]

        parts = [when_str]
        if run.get("ok") is not None:
            parts.append(f"✓ {run['ok']:,}".replace(",", "."))
        if run.get("erro") is not None:
            parts.append(f"✗ {run['erro']:,}".replace(",", "."))
        meta = QLabel("  ·  ".join(parts))
        meta.setObjectName("label_muted")
        meta.setStyleSheet("font-size: 11px;")
        info.addWidget(meta)
        layout.addLayout(info, 1)
        return row
