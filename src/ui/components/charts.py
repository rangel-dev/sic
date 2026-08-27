"""
Gráficos leves desenhados com QPainter (Tarefas 7/8/9).

Sem QtCharts de propósito: QtCharts não segue QSS (a troca de tema global via
app.setStyleSheet não recolore o gráfico) e exigiria garantir o bundle do
módulo no PyInstaller. Aqui as cores vêm de uma paleta própria por tema,
espelhando os tokens #badge_ok/#badge_error/#label_muted dos QSS, e a Home
chama set_theme() no refresh_theme() que já existe.
"""
from typing import Optional

from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

# Paleta por tema — mesmos tons de qss_light.py/qss_dark.py
# (#label_success, #badge_error, #label_muted, #card_flat).
_PALETTES = {
    "light": {
        "ok": "#059669",
        "erro": "#dc2626",
        "falha": "#d97706",
        "track": "#e5e7eb",
        "label": "#374151",
        "muted": "#808080",
    },
    "dark": {
        "ok": "#34d399",
        "erro": "#f87171",
        "falha": "#fbbf24",
        "track": "#334155",
        "label": "#c0cce0",
        "muted": "#94a3b8",
    },
}


def palette(theme: str) -> dict:
    """Paleta de cores dos gráficos para o tema dado (fallback: light)."""
    return _PALETTES.get(theme, _PALETTES["light"])


def format_delta(delta: Optional[dict]) -> Optional[tuple]:
    """Formata um delta de comparação de período (ver
    HomeView._compute_delta) em (texto, chave_de_cor). None se não há delta.

    kind="pp": pontos percentuais de conformidade (↑ = melhorou = "ok").
    kind="pct": variação percentual de erros brutos (↑ = piorou = "erro")."""
    if not delta:
        return None
    arrow = "▲" if delta["value"] > 0 else "▼"
    color_key = "ok" if delta["better"] else "erro"
    value_txt = f"{abs(delta['value']):.1f}".replace(".", ",")
    if delta["kind"] == "pp":
        return f"{arrow} {value_txt} p.p.", color_key
    return f"{arrow} {value_txt}% erros", color_key


class DonutChart(QWidget):
    """Anel acertos × erros com o % de conformidade no centro.

    set_values(ok, erro): `ok=None` indica módulo sem contagem de acertos
    (ex. Menus CB) — o anel fica neutro e o centro mostra o nº de erros,
    distinguindo "não medido" de "100% ok".
    """

    def __init__(self, diameter: int = 96, parent=None):
        super().__init__(parent)
        self._ok: Optional[int] = None
        self._erro: int = 0
        self._theme = "light"
        self._diameter = diameter
        self.setFixedSize(diameter, diameter)

    def set_values(self, ok: Optional[int], erro: int) -> None:
        self._ok = ok
        self._erro = erro or 0
        self.update()

    def set_theme(self, theme: str) -> None:
        self._theme = theme
        self.update()

    def paintEvent(self, event) -> None:
        pal = palette(self._theme)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        ring_w = max(self._diameter // 12, 6)
        rect = QRectF(ring_w / 2 + 1, ring_w / 2 + 1,
                      self._diameter - ring_w - 2, self._diameter - ring_w - 2)

        # Trilho de fundo
        pen = QPen(QColor(pal["track"]), ring_w)
        pen.setCapStyle(Qt.FlatCap)
        painter.setPen(pen)
        painter.drawEllipse(rect)

        measured = self._ok is not None
        total = (self._ok or 0) + self._erro

        if measured and total > 0:
            pct = (self._ok or 0) / total
            # Arco verde (acertos) a partir do topo, sentido horário; o
            # restante do anel fica vermelho (erros). Pontas arredondadas e
            # um pequeno respiro entre os segmentos (visual mais moderno).
            circle = 360 * 16
            ok_angle = int(circle * pct)
            start = 90 * 16
            gap = 7 * 16
            has_gap = (ok_angle - 2 * gap) > 0 and (circle - ok_angle - 2 * gap) > 0
            pen.setCapStyle(Qt.RoundCap)

            pen.setColor(QColor(pal["ok"]))
            painter.setPen(pen)
            if has_gap:
                painter.drawArc(rect, start - gap, -(ok_angle - 2 * gap))
            else:
                painter.drawArc(rect, start, -ok_angle)

            if pct < 1.0:
                pen.setColor(QColor(pal["erro"]))
                painter.setPen(pen)
                if has_gap:
                    painter.drawArc(rect, start - ok_angle - gap,
                                    -(circle - ok_angle - 2 * gap))
                else:
                    painter.drawArc(rect, start - ok_angle, -(circle - ok_angle))
            center_text = f"{pct * 100:.1f}%".replace(".", ",")
            center_color = pal["ok"] if pct >= 0.95 else (
                pal["falha"] if pct >= 0.80 else pal["erro"])
            sub_text = "conforme"
        elif not measured and self._erro > 0:
            pen.setColor(QColor(pal["erro"]))
            painter.setPen(pen)
            painter.drawArc(rect, 90 * 16, -360 * 16)
            center_text = f"{self._erro:,}".replace(",", ".")
            center_color = pal["erro"]
            sub_text = "erros"
        else:
            center_text = "—"
            center_color = pal["muted"]
            sub_text = ""

        font = QFont(self.font())
        font.setBold(True)
        size = self._diameter / 5.4
        if len(center_text) > 5:
            size *= 0.76
        font.setPointSizeF(size)
        painter.setFont(font)
        painter.setPen(QColor(center_color))
        text_rect = QRectF(0, 0, self._diameter, self._diameter)
        if sub_text:
            text_rect.translate(0, -self._diameter / 14)
        painter.drawText(text_rect, Qt.AlignCenter, center_text)

        if sub_text:
            sub_font = QFont(self.font())
            sub_font.setPointSizeF(max(self._diameter / 13.0, 6.5))
            painter.setFont(sub_font)
            painter.setPen(QColor(pal["muted"]))
            sub_rect = QRectF(0, self._diameter / 2, self._diameter,
                              self._diameter / 3)
            painter.drawText(sub_rect, Qt.AlignHCenter | Qt.AlignTop, sub_text)
        painter.end()


class DailyBarsChart(QWidget):
    """Barras verticais de erros por dia (janela de N dias), com marcador
    âmbar nos dias que tiveram falha de execução e rótulos de data esparsos.

    set_data(days): lista cronológica de dicts
    {"label": "dd/mm", "erro": int, "falha": int}.
    """

    _CHART_H = 120
    _AXIS_H = 22

    def __init__(self, parent=None):
        super().__init__(parent)
        self._days: list[dict] = []
        self._theme = "light"
        self.setMinimumHeight(self._CHART_H + self._AXIS_H)
        self.setMaximumHeight(self._CHART_H + self._AXIS_H)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def set_data(self, days: list[dict]) -> None:
        self._days = days or []
        self.update()

    def set_theme(self, theme: str) -> None:
        self._theme = theme
        self.update()

    def paintEvent(self, event) -> None:
        if not self._days:
            return
        pal = palette(self._theme)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        n = len(self._days)
        max_err = max((d.get("erro", 0) for d in self._days), default=0)
        max_err = max(max_err, 1)

        slot_w = self.width() / n
        bar_w = max(min(slot_w * 0.62, 18.0), 2.0)

        label_font = QFont(self.font())
        label_font.setPointSizeF(max(label_font.pointSizeF() - 2.5, 6.5))

        # Linha de base
        base_y = self._CHART_H
        painter.setPen(QPen(QColor(pal["track"]), 1))
        painter.drawLine(0, base_y, self.width(), base_y)

        label_every = max(n // 6, 1)
        for i, day in enumerate(self._days):
            cx = slot_w * i + slot_w / 2
            erro = day.get("erro", 0)
            falha = day.get("falha", 0)

            if erro > 0:
                h = max((erro / max_err) * (self._CHART_H - 18), 3.0)
                painter.setPen(Qt.NoPen)
                painter.setBrush(QColor(pal["erro"]))
                painter.drawRoundedRect(
                    QRectF(cx - bar_w / 2, base_y - h, bar_w, h), 2, 2)
                # Valor no topo da barra (só quando há espaço razoável)
                if slot_w >= 14:
                    painter.setFont(label_font)
                    painter.setPen(QColor(pal["erro"]))
                    painter.drawText(
                        QRectF(cx - slot_w, base_y - h - 14, slot_w * 2, 12),
                        Qt.AlignCenter, str(erro))

            if falha > 0:
                painter.setPen(Qt.NoPen)
                painter.setBrush(QColor(pal["falha"]))
                painter.drawEllipse(QRectF(cx - 2.5, base_y + 3, 5, 5))

            if i % label_every == 0 or i == n - 1:
                painter.setFont(label_font)
                painter.setPen(QColor(pal["muted"]))
                painter.drawText(
                    QRectF(cx - slot_w, base_y + 8, slot_w * 2, 12),
                    Qt.AlignCenter, day.get("label", ""))
        painter.end()


class TrendAreaChart(QWidget):
    """Linha suave + área com gradiente somando os erros de TODOS os módulos
    por dia (Tarefa 9) — visão executiva da "forma do período" antes de
    entrar módulo a módulo, mesmo espírito de um gráfico de tendência de BI.

    set_data(days): lista cronológica de dicts {"label": "dd/mm", "erro": int}.
    """

    _CHART_H = 150
    _AXIS_H = 22

    def __init__(self, parent=None):
        super().__init__(parent)
        self._days: list[dict] = []
        self._theme = "light"
        self.setMinimumHeight(self._CHART_H + self._AXIS_H)
        self.setMaximumHeight(self._CHART_H + self._AXIS_H)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def set_data(self, days: list[dict]) -> None:
        self._days = days or []
        self.update()

    def set_theme(self, theme: str) -> None:
        self._theme = theme
        self.update()

    def paintEvent(self, event) -> None:
        if not self._days:
            return
        pal = palette(self._theme)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        n = len(self._days)
        values = [d.get("erro", 0) for d in self._days]
        max_v = max(max(values, default=0), 1)

        base_y = float(self._CHART_H)
        top_pad = 30.0  # espaço pro rótulo do pico não ser cortado no topo
        usable_h = self._CHART_H - top_pad

        w = max(self.width(), 1)
        xs = [w / 2.0] if n == 1 else [w * i / (n - 1) for i in range(n)]
        ys = [base_y - (v / max_v) * usable_h for v in values]

        painter.setPen(QPen(QColor(pal["track"]), 1))
        painter.drawLine(0, int(base_y), self.width(), int(base_y))

        # Curva suave via Bezier cúbica entre pontos consecutivos (control
        # points no ponto médio horizontal — evita overshoot, fica orgânica).
        line_path = QPainterPath()
        line_path.moveTo(xs[0], ys[0])
        for i in range(1, n):
            cx = (xs[i - 1] + xs[i]) / 2.0
            line_path.cubicTo(cx, ys[i - 1], cx, ys[i], xs[i], ys[i])

        area_path = QPainterPath(line_path)
        area_path.lineTo(xs[-1], base_y)
        area_path.lineTo(xs[0], base_y)
        area_path.closeSubpath()

        gradient = QLinearGradient(0, top_pad, 0, base_y)
        c_top = QColor(pal["erro"])
        c_top.setAlphaF(0.30)
        c_bottom = QColor(pal["erro"])
        c_bottom.setAlphaF(0.02)
        gradient.setColorAt(0.0, c_top)
        gradient.setColorAt(1.0, c_bottom)
        painter.setPen(Qt.NoPen)
        painter.setBrush(gradient)
        painter.drawPath(area_path)

        painter.setPen(QPen(QColor(pal["erro"]), 2.4))
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(line_path)

        peak_idx = values.index(max(values)) if any(values) else None
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(pal["erro"]))
        for i in range(n):
            if values[i] <= 0:
                continue
            r = 4.2 if i == peak_idx else 2.6
            painter.drawEllipse(QPointF(xs[i], ys[i]), r, r)

        peak_font = QFont(self.font())
        peak_font.setBold(True)
        peak_font.setPointSizeF(max(peak_font.pointSizeF() - 1.0, 7.5))
        if peak_idx is not None and values[peak_idx] > 0:
            painter.setFont(peak_font)
            painter.setPen(QColor(pal["erro"]))
            painter.drawText(
                QRectF(xs[peak_idx] - 40, ys[peak_idx] - 22, 80, 16),
                Qt.AlignCenter, str(values[peak_idx]))

        label_font = QFont(self.font())
        label_font.setPointSizeF(max(label_font.pointSizeF() - 2.5, 6.5))
        painter.setFont(label_font)
        painter.setPen(QColor(pal["muted"]))
        label_every = max(n // 6, 1)
        for i, day in enumerate(self._days):
            if i % label_every == 0 or i == n - 1:
                painter.drawText(
                    QRectF(xs[i] - 30, base_y + 6, 60, 14),
                    Qt.AlignCenter, day.get("label", ""))
        painter.end()
