"""
Pricing Master AI Agent
Rule-based expert system that interprets audit error statistics and produces
a structured HTML diagnostic report. Migrated from ai-agent.js to achieve full parity.
"""
from __future__ import annotations

from typing import Optional


# Mapeamento de Erros para Linguagem de Negócio (Base de Conhecimento V11.0 - Full Coverage)
_KB: dict[str, dict] = {
    "price": {
        "title": "Divergência de Preço (Salesforce)",
        "desc": "Os preços no Salesforce não batem com o planejado no Excel. Isso pode causar vendas com valores defasados.",
        "impact": "Alto Risco Financeiro"
    },
    "list": {
        "title": "Visibilidade em Vitrines (Listas)",
        "desc": "Produtos ativos no Excel mas fora das listas de atribuição do XML. O cliente não verá o produto nas vitrines.",
        "impact": "Baixa Conversão"
    },
    "ml": {
        "title": "Concorrência de Canais (ML vs SITE)",
        "desc": "O preço na Minha Loja (Consultor) está inferior ao Ecommerce. Isso gera conflito de canais e canibalização de vendas.",
        "impact": "Conflito Estratégico"
    },
    "margin": {
        "title": "Margem de Segurança (Conflito)",
        "desc": "SKUs promocionados em categorias onde o desconto acumulado ultrapassa a margem de saúde financeira.",
        "impact": "Prejuízo Operacional"
    },
    "logic": {
        "title": "Erro de Cadastro (POR > DE)",
        "desc": "O preço promocional está maior que o original, o que invalida a oferta no sistema.",
        "impact": "Erro de Experiência / UX"
    },
    "searchable": {
        "title": "Indexação de Busca (Searchable)",
        "desc": "O flag de busca no Salesforce diverge do planejado. O produto pode estar invisível na busca interna.",
        "impact": "Perda de Fluxo Orgânico"
    },
    "job": {
        "title": "Falha de Sincronização (JOB ML)",
        "desc": "A categoria da Minha Loja não reflete a categoria da Marca Mãe. O Job de automação falhou.",
        "impact": "Catálogo Desatualizado"
    },
    "bundle": {
        "title": "Saúde de Kits (Bundles)",
        "desc": "Componentes do kit estão offline ou sem preço, impedindo a venda do conjunto completo.",
        "impact": "Queda no Ticket Médio"
    },
    "offline": {
        "title": "Indisponibilidade (Prod. Offline)",
        "desc": "Produtos que deveriam estar à venda mas constam como Offline no Salesforce.",
        "impact": "Risco de Receita (Venda planejada não realizada)"
    },
    "missing": {
        "title": "Ausência de Preço (DE/POR)",
        "desc": "Falta um dos pilares de preço (DE ou POR) no Pricebook, o que remove o SKU do ar.",
        "impact": "Perda imediata de Venda"
    },
    "primary": {
        "title": "Categoria Primária (SEO)",
        "desc": "O produto está sem a atribuição de categoria primária, essencial para navegação e breadcrumbs.",
        "impact": "Impacto no SEO e Filtros"
    },
    "cross": {
        "title": "Invasão de Marca (Cross-Brand)",
        "desc": "Detectamos SKUs de uma marca dentro do Pricebook de outra. Grave erro de importação massiva.",
        "impact": "Erro Crítico de Governança"
    }
}


class AiAgent:
    def generate_report(
        self,
        stats: dict,
        brands_found: Optional[list[str]] = None,
        total_excel_skus: int = 0,
        theme: str = "light",
    ) -> str:
        """Return an HTML string with the full diagnostic report identical to legacy JS."""
        by_type = stats.get("by_type", {})
        
        # Filtra categorias com erros
        error_keys = [k for k, v in by_type.items() if v.get("total", 0) > 0]
        total_errors = sum(by_type[k].get("total", 0) for k in error_keys)

        # Output style vars
        h3_color = "#818cf8" if theme == "dark" else "#4f46e5"
        h4_color = "#e2e8f0" if theme == "dark" else "#1e293b"
        strong_color = "#ffffff" if theme == "dark" else "#0f172a"
        border_color = "rgba(129, 140, 248, 0.3)" if theme == "dark" else "rgba(79, 70, 229, 0.3)"
        text_color = "#e2e8f0" if theme == "dark" else "#334155"

        if total_errors == 0:
            return f"""<div style="color:{text_color};">
<h3 style="font-size: 18px; font-weight: 900; color: {h3_color}; margin-bottom: 8px;">✅ Operação Saudável</h3>
<div style="margin-bottom: 12px;"></div>
Todas as regras de negócio foram validadas. O catálogo está 100% íntegro para todos os canais.
</div>"""

        num_categories = len(error_keys)
        html_out = f"""<div style="color:{text_color}; font-size: 14px; line-height: 1.5;">
Identificamos <strong style="color:{strong_color}; font-weight:900;">{total_errors} alertas</strong> distribuídos em <strong style="color:{strong_color}; font-weight:900;">{num_categories} categorias</strong>. Confira o detalhamento completo:
<div style="margin-bottom: 16px;"></div>
"""

        # Ordem de Criticidade (Estratégico > Operacional)
        priority = ['cross', 'ml', 'margin', 'price', 'missing', 'job', 'bundle', 'offline', 'logic', 'searchable', 'primary']
        
        def sort_key(k):
            try:
                return priority.index(k)
            except ValueError:
                return 99

        sorted_keys = sorted(error_keys, key=sort_key)

        for key in sorted_keys:
            s_data = by_type[key]
            meaning = _KB.get(key, {"title": key, "desc": "Inconsistência técnica.", "impact": "Manual"})
            
            b_str = ""
            nat = s_data.get("natura", 0) > 0
            avn = s_data.get("avon", 0) > 0
            if nat and avn:
                b_str = "Natura e Avon"
            elif nat:
                b_str = "Natura"
            elif avn:
                b_str = "Avon"

            count = s_data.get("total", 0)
            
            html_out += f'<h4 style="font-size: 16px; font-weight: bold; color: {h4_color}; margin-top: 16px; margin-bottom: 4px; border-bottom: 1px solid {border_color}; padding-bottom: 4px;">🚩 {meaning["title"]} ({count} SKUs - {b_str})</h4>\n'
            html_out += f'<strong style="color:{strong_color}; font-weight:900;">Contexto:</strong> {meaning["desc"]}<br>\n'
            html_out += f'<strong style="color:{strong_color}; font-weight:900;">Risco:</strong> {meaning["impact"]}\n'
            html_out += '<div style="margin-bottom: 12px;"></div>\n'

        html_out += f"""<span style="margin-right: 4px;">⚠️</span> <strong style="color:{strong_color}; font-weight:900;">Ação Recomendada:</strong> Priorize a correção das inconsistências de 'Alto Risco' antes do próximo push de produção.
</div>"""

        return html_out

