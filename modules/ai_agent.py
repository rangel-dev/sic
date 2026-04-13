"""
Pricing Master AI Agent
Rule-based expert system that interprets audit error statistics and produces
a structured HTML diagnostic report.  Migrated from ai-agent.js.
"""
from __future__ import annotations

from typing import Optional


# ── Error knowledge base ──────────────────────────────────────────────────────
_KB: dict[str, dict] = {
    "cross": {
        "title":  "Invasão de Marca (Cross-Brand)",
        "desc":   "SKUs de uma marca detectados no pricebook de outra. "
                  "Isso corromperia preços e regras de negócio em produção.",
        "impact": "CRÍTICO — Governança de Dados",
        "action": "Remova imediatamente os SKUs cruzados antes de fazer upload.",
        "priority": 1,
    },
    "margin": {
        "title":  "Conflito de Margem (Categoria Bloqueada)",
        "desc":   "Produtos com desconto em categorias onde promoções violam "
                  "a política de margem mínima.",
        "impact": "ALTO — Perda Operacional",
        "action": "Verifique a regra de margem com a equipe de Pricing antes de ativar.",
        "priority": 2,
    },
    "ml": {
        "title":  "Conflito de Canal (ML vs Site)",
        "desc":   "Preços do canal Minha Loja divergem dos preços da marca-mãe, "
                  "gerando arbitragem entre canais.",
        "impact": "ALTO — Conflito Estratégico",
        "action": "Alinhe os preços ML com os preços da marca no pricebook.",
        "priority": 3,
    },
    "price": {
        "title":  "Divergência de Preço (Salesforce vs Excel)",
        "desc":   "Preços publicados no Salesforce Demandware diferem da planilha "
                  "comercial aprovada.",
        "impact": "ALTO — Risco Financeiro",
        "action": "Gere um novo Pricebook com o Gerador e reimporte no SF.",
        "priority": 4,
    },
    "missing": {
        "title":  "Preço Ausente (DE/POR)",
        "desc":   "Produtos sem DE (preço de lista) ou POR (preço promocional) "
                  "no Salesforce. Estes produtos não podem ser vendidos.",
        "impact": "ALTO — Venda Bloqueada",
        "action": "Inclua estes SKUs no próximo Pricebook e faça upload urgente.",
        "priority": 5,
    },
    "logic": {
        "title":  "Erro Lógico (POR > DE)",
        "desc":   "Preço promocional (POR) maior que o preço de lista (DE). "
                  "Isso indica erro de cadastro na planilha.",
        "impact": "MÉDIO — Erro de Cadastro",
        "action": "Corrija os valores na planilha Excel antes de regenerar o XML.",
        "priority": 6,
    },
    "offline": {
        "title":  "Produto Indisponível (Offline)",
        "desc":   "Produtos marcados como visíveis na planilha estão offline no SF.",
        "impact": "MÉDIO — Risco de Receita",
        "action": "Ative os produtos ou corrija o online-flag via Sync.",
        "priority": 7,
    },
    "searchable": {
        "title":  "Searchable Flag Divergente",
        "desc":   "O status de busca orgânica no SF diverge da visibilidade definida "
                  "na planilha.",
        "impact": "MÉDIO — Perda de Fluxo Orgânico",
        "action": "Execute o módulo Sync para atualizar os atributos de busca.",
        "priority": 8,
    },
    "list": {
        "title":  "Visibilidade em Listas/Vitrines",
        "desc":   "Produtos fora das listas/vitrines corretas (faltando ou sobrando "
                  "em relação à planilha).",
        "impact": "MÉDIO — Conversão Reduzida",
        "action": "Execute o módulo Sync para corrigir os assignments de categoria.",
        "priority": 9,
    },
    "job": {
        "title":  "Falha de Sync (ML JOB)",
        "desc":   "Categorias do canal ML não sincronizaram com a marca-mãe.",
        "impact": "BAIXO — Catálogo Desatualizado",
        "action": "Re-execute o job de sincronização no SF Business Manager.",
        "priority": 10,
    },
    "bundle": {
        "title":  "Saúde de Bundles/Kits",
        "desc":   "Kits contendo componentes offline ou sem preço definido.",
        "impact": "BAIXO — Ticket Médio Reduzido",
        "action": "Ative os componentes ou reconfigure o bundle no SF.",
        "priority": 11,
    },
    "primary": {
        "title":  "Categoria Primária Ausente",
        "desc":   "Produtos sem categoria primária atribuída no catálogo SF. "
                  "Isso impacta SEO e filtros de navegação.",
        "impact": "BAIXO — SEO e Filtros",
        "action": "Atribua categorias primárias via SF Business Manager.",
        "priority": 12,
    },
}

_COLORS = {
    1: "#ef5350", 2: "#f44336", 3: "#ab47bc",
    4: "#ff7043", 5: "#e53935", 6: "#ff8a65",
    7: "#757575", 8: "#26a69a", 9: "#ff7043",
    10: "#7e57c2", 11: "#8d6e63", 12: "#5c6bc0",
}


class AiAgent:
    def generate_report(
        self,
        stats: dict,
        brands_found: Optional[list[str]] = None,
        total_excel_skus: int = 0,
        theme: str = "light",
    ) -> str:
        """Return an HTML string with the full diagnostic report."""
        by_type: dict = stats.get("by_type", {})
        total   = stats.get("total", 0)

        # Filter to errors that actually occurred
        active = [
            (code, by_type[code])
            for code in by_type
            if by_type[code].get("total", 0) > 0
        ]
        # Sort by business priority
        active.sort(key=lambda x: _KB.get(x[0], {}).get("priority", 99))

        if not active:
            return self._no_errors_html(total_excel_skus, theme)

        return self._build_html(active, total, brands_found or [], total_excel_skus, theme)

    # ── HTML builders ─────────────────────────────────────────────────────
    def _no_errors_html(self, total_skus: int, theme: str) -> str:
        color_ok = "#66bb6a" if theme == "dark" else "#2d7a2d"
        color_muted = "#888" if theme == "dark" else "#666"
        return f"""
<div style="padding:4px 0">
  <p style="color:{color_ok};font-size:15px;font-weight:700;margin:0 0 8px">
    ✅ Auditoria sem divergências detectadas
  </p>
  <p style="color:{color_muted};font-size:12px;margin:0">
    {total_skus} SKUs auditados — todos os preços e atributos estão consistentes
    entre a planilha e o Salesforce Demandware.
  </p>
</div>"""

    def _build_html(
        self,
        active: list,
        total: int,
        brands: list[str],
        total_skus: int,
        theme: str,
    ) -> str:
        brands_str = " + ".join(b.capitalize() for b in brands) if brands else "Desconhecido"
        
        # Theme-aware base colors
        bg_card  = "#181818" if theme == "dark" else "#ffffff"
        border_c = "1px solid #252525" if theme == "dark" else "1px solid #e0e0e0"
        fg_main  = "#dddddd" if theme == "dark" else "#222222"
        fg_muted = "#888888" if theme == "dark" else "#666666"
        fg_meta  = "#f0f0f0" if theme == "dark" else "#111111"
        bg_impact = "#1e1e1e" if theme == "dark" else "#f0f0f0"

        sections = []
        for code, counts in active:
            kb = _KB.get(code, {})
            priority = kb.get("priority", 99)
            color = _COLORS.get(priority, "#888")
            nat = counts.get("natura", 0)
            avn = counts.get("avon", 0)
            tot = counts.get("total", 0)

            brand_breakdown = ""
            if nat > 0 and avn > 0:
                brand_breakdown = (
                    f'<span style="color:#ff8050">Natura: {nat}</span> &nbsp; '
                    f'<span style="color:#7B2FBE">Avon: {avn}</span>'
                )
            elif nat > 0:
                brand_breakdown = f'<span style="color:#ff8050">Natura: {nat}</span>'
            elif avn > 0:
                brand_breakdown = f'<span style="color:#7B2FBE">Avon: {avn}</span>'

            sections.append(f"""
<div style="margin-bottom:14px;padding:12px;background:{bg_card};border:{border_c};border-left:3px solid {color};border-radius:6px">
  <div style="display:flex;align-items:baseline;gap:10px;margin-bottom:4px">
    <span style="color:{color};font-size:18px;font-weight:700">{tot}</span>
    <span style="color:{fg_main};font-size:13px;font-weight:600">{kb.get("title","")}</span>
    <span style="color:{fg_muted};font-size:10px;font-weight:600;text-transform:uppercase;
                 background:{bg_impact};padding:1px 6px;border-radius:3px">
      {kb.get("impact","")}
    </span>
  </div>
  <p style="color:{fg_muted};font-size:12px;margin:0 0 4px">{kb.get("desc","")}</p>
  <p style="color:{fg_main};font-size:11px;margin:0">
    <span style="color:{fg_muted}">→ Ação: </span>{kb.get("action","")}
  </p>
  {f'<p style="margin:6px 0 0;font-size:11px">{brand_breakdown}</p>' if brand_breakdown else ""}
</div>""")

        header = f"""
<div style="margin-bottom:16px">
  <p style="color:{fg_meta};font-size:14px;font-weight:700;margin:0 0 4px">
    Diagnóstico Estratégico — {brands_str}
  </p>
  <p style="color:{fg_muted};font-size:11px;margin:0">
    {total_skus} SKUs auditados &nbsp;·&nbsp;
    <span style="color:#ef5350;font-weight:600">{total} divergências detectadas</span>
    &nbsp;·&nbsp; {len(active)} tipo(s) de erro
  </p>
</div>"""

        return header + "".join(sections)
