"""
Certificate Engine — Gerador do Certificado de Conformidade (Master Audit)
Produz um PDF executivo apenas quando result.stats["total"] == 0 (zero divergências).
"""
from __future__ import annotations

import hashlib
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.auditor_engine import AuditResult

# ── Paleta corporativa ────────────────────────────────────────────────────────
_NAVY        = (13,  31,  61)
_GRAPHITE    = (55,  65,  81)
_EMERALD     = (5,  150, 105)
_EMERALD_LT  = (209, 250, 229)
_LIGHT_GRAY  = (245, 247, 250)
_WHITE       = (255, 255, 255)
_BORDER_CLR  = (203, 213, 225)

# ── Dimensões A4 em mm ────────────────────────────────────────────────────────
_PAGE_W = 210
_MARGIN = 14

# ── Indicadores de conformidade ───────────────────────────────────────────────
_COMPLIANCE_CHECKS = [
    ("Volumetria Total",        "SKUs processados na Grade de Ativação"),
    ("Audit de Preços",         "Pricebook XML × Planilha Excel (DE/POR)"),
    ("Audit de Visibilidade",   "Flag searchable/online vs. coluna VISIBLE"),
    ("Integridade de Catálogo", "Categoria primária, Bundles, Cross-Brand"),
    ("Sincronia de Catálogo",   "online-flag SF × Grade de Ativação (bidirecional)"),
]


class CertificateEngine:
    """Gera o PDF Certificado de Conformidade a partir de um AuditResult limpo."""

    ENGINE_VERSION = "V11.6"

    # ── API pública ───────────────────────────────────────────────────────────

    def generate(
        self,
        result: "AuditResult",
        output_path: str,
        source_files: list[str],
        timestamp: datetime | None = None,
    ) -> str:
        """
        Constrói e grava o PDF em output_path.

        Levanta ValueError se result.stats["total"] != 0.
        Retorna o caminho gravado.
        """
        if result.stats.get("total", -1) != 0:
            raise ValueError(
                "O Certificado só pode ser emitido com ZERO divergências."
            )

        ts          = timestamp or datetime.now()
        protocol_id = self._build_protocol_id(ts, result.total_excel_skus, result.brands_found)

        try:
            from fpdf import FPDF
        except ImportError as exc:
            raise RuntimeError(
                "A biblioteca fpdf2 não está instalada.\n"
                "Execute: pip install fpdf2>=2.7.0"
            ) from exc

        pdf = FPDF(orientation="P", unit="mm", format="A4")
        pdf.set_auto_page_break(auto=False)
        pdf.add_page()

        # Arial Unicode MS (macOS) suporta o conjunto completo de caracteres necessário.
        # Fallback: Helvetica com sanitização automática de caracteres fora do Latin-1.
        from pathlib import Path as _Path
        _ARIAL_UNICODE = "/Library/Fonts/Arial Unicode.ttf"
        self._unicode_font = "Helvetica"
        if _Path(_ARIAL_UNICODE).exists():
            try:
                pdf.add_font("ArialU", fname=_ARIAL_UNICODE)
                pdf.add_font("ArialU", style="B", fname=_ARIAL_UNICODE)
                self._unicode_font = "ArialU"
            except Exception:
                pass

        self._draw_header(pdf, result.brands_found, ts)
        self._draw_provenance_block(pdf, ts, source_files, protocol_id)
        self._draw_summary_stats(pdf, result)
        self._draw_compliance_table(pdf)
        self._draw_security_stamp(pdf, protocol_id)
        self._draw_footer(pdf, ts)

        pdf.output(output_path)
        return output_path

    # ── Helpers privados ──────────────────────────────────────────────────────

    def _build_protocol_id(
        self,
        ts: datetime,
        total_skus: int,
        brands: list[str],
    ) -> str:
        raw    = f"{ts.isoformat()}|{total_skus}|{'_'.join(sorted(brands))}"
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        return digest[:16].upper()

    def _set_font(self, pdf, style: str = "", size: int = 10) -> None:
        pdf.set_font(self._unicode_font, style=style, size=size)

    def _s(self, text: str) -> str:
        """Sanitiza texto para Helvetica: substitui caracteres fora do Latin-1."""
        if self._unicode_font != "Helvetica":
            return text
        return (
            text
            .replace("—", " - ")   # em dash —
            .replace("–", " - ")   # en dash –
            .replace("•", "*")     # bullet •
            .replace("✓", "OK")    # check mark ✓
            .replace("·", "|")     # middle dot ·
            .encode("latin-1", errors="replace").decode("latin-1")
        )

    # ── Seção 1: Cabeçalho ────────────────────────────────────────────────────
    def _draw_header(self, pdf, brands: list[str], ts: datetime) -> None:
        pdf.set_fill_color(*_NAVY)
        pdf.rect(0, 0, _PAGE_W, 32, style="F")

        # Título principal
        pdf.set_text_color(*_WHITE)
        self._set_font(pdf, style="B", size=16)
        pdf.set_xy(_MARGIN, 6)
        pdf.cell(0, 8, self._s("CERTIFICADO DE CONFORMIDADE"), ln=True)

        self._set_font(pdf, size=9)
        pdf.set_x(_MARGIN)
        pdf.cell(0, 5, self._s("Catálogo de Produtos — Salesforce Commerce Cloud"), ln=True)

        # Marcas (canto direito)
        brand_str = " / ".join(b.upper() for b in brands) if brands else "NATURA"
        self._set_font(pdf, style="B", size=13)
        pdf.set_xy(0, 10)
        pdf.cell(_PAGE_W - _MARGIN, 10, brand_str, align="R")

        # Linha separadora embaixo do header
        pdf.set_draw_color(*_EMERALD)
        pdf.set_line_width(0.8)
        pdf.line(0, 32, _PAGE_W, 32)
        pdf.set_line_width(0.2)
        pdf.set_text_color(*_GRAPHITE)

    # ── Seção 2: Proveniência ─────────────────────────────────────────────────
    def _draw_provenance_block(
        self, pdf, ts: datetime, source_files: list[str], protocol_id: str
    ) -> None:
        y_start = 36
        col_w   = (_PAGE_W - _MARGIN * 2) / 2

        # Fundo cinza claro
        pdf.set_fill_color(*_LIGHT_GRAY)
        pdf.rect(_MARGIN, y_start, _PAGE_W - _MARGIN * 2, 26, style="F")
        pdf.set_draw_color(*_BORDER_CLR)
        pdf.rect(_MARGIN, y_start, _PAGE_W - _MARGIN * 2, 26, style="D")

        # Coluna esquerda
        self._set_font(pdf, style="B", size=8)
        pdf.set_xy(_MARGIN + 3, y_start + 3)
        pdf.set_text_color(*_NAVY)
        pdf.cell(col_w, 4, "INFORMAÇÕES DE EMISSÃO", ln=True)

        self._set_font(pdf, size=8)
        pdf.set_text_color(*_GRAPHITE)
        items_left = [
            ("Gerado em",  ts.strftime("%d/%m/%Y às %H:%M:%S")),
            ("Protocolo",  protocol_id),
            ("Motor",      f"Auditor Engine {self.ENGINE_VERSION}"),
        ]
        for label, val in items_left:
            pdf.set_x(_MARGIN + 3)
            pdf.set_font(self._unicode_font, style="B", size=8)
            pdf.cell(22, 4, f"{label}:", ln=False)
            pdf.set_font(self._unicode_font, style="", size=8)
            pdf.cell(col_w - 22, 4, val, ln=True)

        # Coluna direita
        self._set_font(pdf, style="B", size=8)
        pdf.set_xy(_MARGIN + col_w + 3, y_start + 3)
        pdf.set_text_color(*_NAVY)
        pdf.cell(col_w, 4, "ARQUIVOS-FONTE", ln=True)

        self._set_font(pdf, size=7.5)
        pdf.set_text_color(*_GRAPHITE)
        for fname in source_files[:5]:
            pdf.set_xy(_MARGIN + col_w + 3, pdf.get_y())
            pdf.cell(col_w - 3, 3.8, self._s(f"• {fname}"), ln=True)
        if len(source_files) > 5:
            pdf.set_xy(_MARGIN + col_w + 3, pdf.get_y())
            pdf.cell(col_w - 3, 3.8, self._s(f"  ... +{len(source_files) - 5} arquivo(s)"), ln=True)

    # ── Seção 3: Indicadores de resumo ───────────────────────────────────────
    def _draw_summary_stats(self, pdf, result: "AuditResult") -> None:
        y_start = 66
        height  = 18
        pdf.set_fill_color(*_EMERALD)
        pdf.rect(0, y_start, _PAGE_W, height, style="F")

        brands_str = " / ".join(b.capitalize() for b in result.brands_found) if result.brands_found else "-"
        stats_items = [
            ("Total de SKUs",    str(result.total_excel_skus)),
            ("Marcas auditadas", brands_str),
            ("Divergencias",     self._s("0  ✓")),
        ]
        col_w = _PAGE_W / len(stats_items)
        pdf.set_text_color(*_WHITE)
        for i, (label, val) in enumerate(stats_items):
            x = i * col_w
            self._set_font(pdf, size=7.5)
            pdf.set_xy(x, y_start + 2)
            pdf.cell(col_w, 4, label, align="C", ln=False)
            self._set_font(pdf, style="B", size=13)
            pdf.set_xy(x, y_start + 7)
            pdf.cell(col_w, 6, val, align="C", ln=False)

        pdf.set_text_color(*_GRAPHITE)

    # ── Seção 4: Tabela de conformidade ───────────────────────────────────────
    def _draw_compliance_table(self, pdf) -> None:
        y_start  = 88
        row_h    = 11
        col_widths = [52, 108, 22]
        headers    = ["DIMENSÃO DE AUDITORIA", "ESCOPO TÉCNICO", "STATUS"]

        # Cabeçalho da tabela
        pdf.set_fill_color(*_NAVY)
        pdf.set_text_color(*_WHITE)
        self._set_font(pdf, style="B", size=8)
        pdf.set_xy(_MARGIN, y_start)
        for w, h in zip(col_widths, headers):
            pdf.cell(w, row_h, h, border=0, align="C", fill=True)
        pdf.ln(row_h)

        # Linhas de dados
        self._set_font(pdf, size=8)
        for i, (dimensao, escopo) in enumerate(_COMPLIANCE_CHECKS):
            fill_color = _LIGHT_GRAY if i % 2 == 0 else _WHITE
            pdf.set_fill_color(*fill_color)
            pdf.set_text_color(*_GRAPHITE)
            row_y = pdf.get_y()

            pdf.set_x(_MARGIN)
            self._set_font(pdf, style="B", size=8)
            pdf.set_text_color(*_NAVY)
            pdf.cell(col_widths[0], row_h, dimensao, border=0, fill=True)

            self._set_font(pdf, size=8)
            pdf.set_text_color(*_GRAPHITE)
            pdf.cell(col_widths[1], row_h, escopo, border=0, fill=True)

            # Coluna STATUS em verde
            pdf.set_fill_color(*_EMERALD_LT)
            pdf.set_text_color(*_EMERALD)
            self._set_font(pdf, style="B", size=8)
            pdf.cell(col_widths[2], row_h, "APROVADO", border=0, align="C", fill=True)
            pdf.ln(row_h)

            # Linha separadora horizontal
            pdf.set_draw_color(*_BORDER_CLR)
            pdf.line(_MARGIN, pdf.get_y(), _PAGE_W - _MARGIN, pdf.get_y())

        # Borda externa da tabela
        table_h = row_h + row_h * len(_COMPLIANCE_CHECKS)
        pdf.set_draw_color(*_BORDER_CLR)
        pdf.rect(_MARGIN, y_start, sum(col_widths), table_h, style="D")
        pdf.set_text_color(*_GRAPHITE)

    # ── Seção 5: Carimbo de segurança ─────────────────────────────────────────
    def _draw_security_stamp(self, pdf, protocol_id: str) -> None:
        y_start = 142
        height  = 62
        inner_x = _MARGIN + 6
        inner_w = _PAGE_W - _MARGIN * 2 - 12

        # Fundo
        pdf.set_fill_color(*_LIGHT_GRAY)
        pdf.set_draw_color(*_NAVY)
        pdf.set_line_width(0.6)
        pdf.rect(_MARGIN, y_start, _PAGE_W - _MARGIN * 2, height, style="FD")
        pdf.set_line_width(0.2)

        # Linha decorativa superior interna
        pdf.set_draw_color(*_EMERALD)
        pdf.set_line_width(2)
        pdf.line(_MARGIN, y_start + 6, _PAGE_W - _MARGIN, y_start + 6)
        pdf.set_line_width(0.2)

        # Título do carimbo
        pdf.set_text_color(*_NAVY)
        self._set_font(pdf, style="B", size=17)
        pdf.set_xy(inner_x, y_start + 10)
        pdf.cell(inner_w, 9, "CONFORMIDADE GARANTIDA", align="C", ln=True)

        # Protocolo
        pdf.set_text_color(*_GRAPHITE)
        self._set_font(pdf, size=9)
        pdf.set_x(inner_x)
        pdf.cell(inner_w, 5, f"PROTOCOLO:  {protocol_id}", align="C", ln=True)

        # Divisor interno
        pdf.set_draw_color(*_BORDER_CLR)
        pdf.line(_MARGIN + 30, pdf.get_y() + 2, _PAGE_W - _MARGIN - 30, pdf.get_y() + 2)
        pdf.ln(5)

        # Texto de certificação
        self._set_font(pdf, size=8)
        pdf.set_text_color(*_GRAPHITE)
        pdf.set_x(inner_x)
        pdf.multi_cell(
            inner_w,
            5.5,
            (
                f"Este documento certifica que 100% dos SKUs processados na Grade de "
                f"Ativação foram validados pelo Motor de Auditoria SIC {self.ENGINE_VERSION}\n"
                f"A emissão deste certificado é automática e condicionada à conformidade total."
            ),
            align="C",
        )

        # Linha decorativa inferior interna
        pdf.set_draw_color(*_EMERALD)
        pdf.set_line_width(2)
        y_bottom = y_start + height - 6
        pdf.line(_MARGIN, y_bottom, _PAGE_W - _MARGIN, y_bottom)
        pdf.set_line_width(0.2)
        pdf.set_text_color(*_GRAPHITE)

    # ── Seção 6: Rodapé ───────────────────────────────────────────────────────
    def _draw_footer(self, pdf, ts: datetime) -> None:
        y_footer = 280
        pdf.set_draw_color(*_BORDER_CLR)
        pdf.line(_MARGIN, y_footer, _PAGE_W - _MARGIN, y_footer)

        self._set_font(pdf, size=7.5)
        pdf.set_text_color(*_GRAPHITE)
        pdf.set_xy(_MARGIN, y_footer + 2)
        pdf.cell(0, 4, self._s("SIC — Sistema de Inteligência Corporativa  ·  Natura & Co."), ln=False)

        pdf.set_xy(0, y_footer + 2)
        pdf.cell(
            _PAGE_W - _MARGIN,
            4,
            self._s(f"Página 1 de 1  ·  Gerado em {ts.strftime('%d/%m/%Y')}"),
            align="R",
        )
