"""
Gera o PDF detalhado do Relatório Menu (match Natura/Avon × CB).
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fpdf import FPDF
from fpdf.fonts import FontFace

from src.core.relatorio_menu_engine import (
    BRANDS,
    STATUS_OK,
    RelatorioMenuResult,
)

_NAVY     = (13, 31, 61)
_GRAPHITE = (55, 65, 81)
_RED      = (217, 48, 37)
_GREEN    = (5, 150, 105)
_HEAD_BG  = (226, 232, 240)

_WIN_FONT_DIR = Path("C:/Windows/Fonts")


class _PDF(FPDF):
    font_name = "Helvetica"

    def footer(self):
        self.set_y(-12)
        self.set_font(self.font_name, size=7.5)
        self.set_text_color(*_GRAPHITE)
        self.cell(0, 6, f"SIC · Relatório Menu · página {self.page_no()}/{{nb}}", align="C")


def generate_pdf(result: RelatorioMenuResult, output_path: str, ts: datetime | None = None) -> str:
    ts = ts or datetime.now()
    pdf = _PDF(orientation="P", unit="mm", format="A4")
    _setup_font(pdf)
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.set_margins(14, 14, 14)
    pdf.add_page()

    s = _sanitizer(pdf)
    font = pdf.font_name

    pdf.set_text_color(*_NAVY)
    pdf.set_font(font, "B", 16)
    pdf.cell(0, 9, s("Relatório Menu — Natura/Avon × CB (Minha Loja)"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(font, size=9)
    pdf.set_text_color(*_GRAPHITE)
    pdf.cell(0, 5, s(f"Gerado em {ts:%d/%m/%Y %H:%M}"), new_x="LMARGIN", new_y="NEXT")
    for brand, path in result.source_files.items():
        pdf.cell(0, 5, s(f"Catálogo {brand}: {Path(path).name}"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.multi_cell(0, 5, s(
        "Critério: menus da origem (online e visíveis no menu) são considerados OK "
        "quando existem no CB com o mesmo ID e estão online."
    ), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    _section_title(pdf, s("Resumo"))
    _summary_table(pdf, result.stats, s)
    pdf.ln(6)

    df = result.df_report
    not_ok = df[df["Resultado"] != STATUS_OK]
    ok = df[df["Resultado"] == STATUS_OK]

    for brand in BRANDS:
        part = not_ok[not_ok["Marca"] == brand].sort_values(["Resultado", "Pai", "Nome"])
        _section_title(pdf, s(f"{brand} — Não OK ({len(part)})"), _RED)
        _detail_table(pdf, part, s)
        pdf.ln(6)

    for brand in BRANDS:
        part = ok[ok["Marca"] == brand].sort_values(["Pai", "Nome"])
        _section_title(pdf, s(f"{brand} — OK ({len(part)})"), _GREEN)
        _detail_table(pdf, part, s)
        pdf.ln(6)

    pdf.output(output_path)
    return output_path


def _setup_font(pdf: _PDF) -> None:
    regular, bold = _WIN_FONT_DIR / "arial.ttf", _WIN_FONT_DIR / "arialbd.ttf"
    if regular.exists() and bold.exists():
        try:
            pdf.add_font("ArialW", fname=str(regular))
            pdf.add_font("ArialW", style="B", fname=str(bold))
            pdf.font_name = "ArialW"
        except Exception:
            pdf.font_name = "Helvetica"


def _sanitizer(pdf: _PDF):
    if pdf.font_name != "Helvetica":
        return lambda text: str(text)

    def s(text) -> str:
        return (
            str(text)
            .replace("—", "-").replace("–", "-").replace("×", "x").replace("·", "|")
            .encode("latin-1", errors="replace").decode("latin-1")
        )
    return s


def _section_title(pdf: _PDF, text: str, color=_NAVY) -> None:
    pdf.set_font(pdf.font_name, "B", 12)
    pdf.set_text_color(*color)
    pdf.cell(0, 7, text, new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(*_GRAPHITE)


def _summary_table(pdf: _PDF, stats: dict, s) -> None:
    pdf.set_font(pdf.font_name, size=9)
    heading = FontFace(emphasis="BOLD", fill_color=_HEAD_BG)
    with pdf.table(
        col_widths=(30, 22, 22, 26, 26, 22),
        text_align=("LEFT", "RIGHT", "RIGHT", "RIGHT", "RIGHT", "RIGHT"),
        headings_style=heading,
        line_height=6,
    ) as table:
        table.row(["Marca", "Menus", "OK", "Ausentes no CB", "Offline no CB", "% OK"])
        rows = [(b, stats["by_brand"][b]) for b in BRANDS] + [("Total", stats)]
        for label, st in rows:
            pct = f"{st['ok'] / st['total'] * 100:.1f}%" if st["total"] else "—"
            table.row([s(label), str(st["total"]), str(st["ok"]),
                       str(st["ausente"]), str(st["offline"]), s(pct)])


def _detail_table(pdf: _PDF, df, s) -> None:
    pdf.set_font(pdf.font_name, size=8)
    if df.empty:
        pdf.cell(0, 6, s("Nenhum item."), new_x="LMARGIN", new_y="NEXT")
        return
    heading = FontFace(emphasis="BOLD", fill_color=_HEAD_BG)
    with pdf.table(
        col_widths=(38, 48, 18, 40, 38),
        headings_style=heading,
        line_height=5,
        repeat_headings=1,
    ) as table:
        table.row(["ID", "Nome", "Nível", "Menu pai", "Resultado"])
        for _, r in df.iterrows():
            table.row([s(r["ID"]), s(r["Nome"]), s(r["Nivel"]), s(r["Pai"]), s(r["Resultado"])])
