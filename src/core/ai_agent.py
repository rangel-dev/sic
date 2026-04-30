"""
Pricing Master AI Agent
Rule-based expert system that interprets audit error statistics and produces
a structured HTML diagnostic report. Migrated from ai-agent.js to achieve full parity.
"""
from __future__ import annotations

import base64
import json
from typing import Optional

try:
    from google import genai
    from src.core._secret import OBFUSCATED_KEY
    _GENAI_AVAILABLE = True
except ImportError:
    _GENAI_AVAILABLE = False
    OBFUSCATED_KEY = ""

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
    def __init__(self):
        self._client = None
        if _GENAI_AVAILABLE and OBFUSCATED_KEY:
            try:
                encoded_bytes = OBFUSCATED_KEY.encode('utf-8')
                reversed_key_bytes = base64.b64decode(encoded_bytes)
                api_key = reversed_key_bytes.decode('utf-8')[::-1]
                self._client = genai.Client(api_key=api_key)
            except Exception as e:
                print(f"Falha ao inicializar o Gemini: {e}")

    def _build_prompt(
        self, stats: dict, brands: Optional[list[str]], skus: int, fmt: str, theme: str
    ) -> str:
        prompt = (
            "Você é um especialista em e-commerce e catálogo Salesforce B2C.\n"
            "Eu executei uma auditoria de catálogo e encontrei os seguintes erros técnicos:\n"
            f"{json.dumps(stats.get('by_type', {}), indent=2)}\n\n"
            f"O total de SKUs lidos no Excel foi de {skus}.\n"
            f"As marcas envolvidas são: {brands or 'Desconhecidas'}.\n\n"
        )
        if fmt == "html":
            prompt += (
                f"Me responda EXCLUSIVAMENTE com um snippet HTML (sem a tag <html> ou <body>, apenas as <div> e afins).\n"
                f"O tema escolhido é '{theme}'. Utilize cores e fontes modernas e minimalistas para esse tema (Ex: #e2e8f0 para texto no dark theme).\n"
                "Estrutura esperada:\n"
                "1. Resumo executivo (1 parágrafo identificando a quantidade de erros e marcas afetadas).\n"
                "2. Lista de alertas detalhados agrupados por erro.\n"
                "3. Uma recomendação final com um alerta em destaque.\n"
            )
        else:
            prompt += (
                "Me responda EXCLUSIVAMENTE com um texto formatado em Markdown compatível com o Google Chat.\n"
                "Estrutura esperada:\n"
                "1. Resumo executivo curto (1 parágrafo).\n"
                "2. Lista de problemas.\n"
                "3. Recomendação final.\n"
            )
        return prompt

    def generate_report(
        self,
        stats: dict,
        brands_found: Optional[list[str]] = None,
        total_excel_skus: int = 0,
        theme: str = "light",
    ) -> str:
        if self._client:
            prompt = self._build_prompt(stats, brands_found, total_excel_skus, "html", theme)
            try:
                response = self._client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt,
                )
                if response.text:
                    return response.text.replace("```html", "").replace("```", "").strip()
            except Exception as e:
                print(f"Gemini API erro HTML: {e}")

        # Fallback para heurística caso não haja cliente ou falhe a requisição
        return self._rule_based_html(stats, theme)

    def generate_gchat_report(
        self, stats: dict, brands_found: Optional[list[str]] = None, total_excel_skus: int = 0
    ) -> str:
        if self._client:
            prompt = self._build_prompt(stats, brands_found, total_excel_skus, "gchat", "light")
            try:
                response = self._client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt,
                )
                if response.text:
                    return response.text.replace("```markdown", "").replace("```", "").strip()
            except Exception as e:
                print(f"Gemini API erro GChat: {e}")

        # Fallback
        return self._rule_based_gchat(stats)

    def _rule_based_html(self, stats: dict, theme: str) -> str:
        """Heurística nativa de fallback para HTML."""
        by_type = stats.get("by_type", {})
        error_keys = [k for k, v in by_type.items() if v.get("total", 0) > 0]
        total_errors = sum(by_type[k].get("total", 0) for k in error_keys)

        h3_color = "#818cf8" if theme == "dark" else "#4f46e5"
        h4_color = "#e2e8f0" if theme == "dark" else "#1e293b"
        strong_color = "#ffffff" if theme == "dark" else "#0f172a"
        border_color = "rgba(129, 140, 248, 0.3)" if theme == "dark" else "rgba(79, 70, 229, 0.3)"
        text_color = "#e2e8f0" if theme == "dark" else "#334155"

        if total_errors == 0:
            return f'''<div style="color:{text_color};">
<h3 style="font-size: 18px; font-weight: 900; color: {h3_color}; margin-bottom: 8px;">✅ Operação Saudável</h3>
<div style="margin-bottom: 12px;"></div>
Todas as regras de negócio foram validadas. O catálogo está 100% íntegro para todos os canais.
</div>'''

        num_categories = len(error_keys)
        html_out = f'''<div style="color:{text_color}; font-size: 14px; line-height: 1.5;">
Identificamos <strong style="color:{strong_color}; font-weight:900;">{total_errors} alertas</strong> distribuídos em <strong style="color:{strong_color}; font-weight:900;">{num_categories} categorias</strong>. Confira o detalhamento completo:
<div style="margin-bottom: 16px;"></div>
'''
        priority = ['cross', 'ml', 'margin', 'price', 'missing', 'job', 'bundle', 'offline', 'logic', 'searchable', 'primary']
        def sort_key(k): return priority.index(k) if k in priority else 99
        sorted_keys = sorted(error_keys, key=sort_key)

        for key in sorted_keys:
            s_data = by_type[key]
            meaning = _KB.get(key, {"title": key, "desc": "Inconsistência técnica.", "impact": "Manual"})
            
            b_str = ""
            nat = s_data.get("natura", 0) > 0
            avn = s_data.get("avon", 0) > 0
            if nat and avn: b_str = "Natura e Avon"
            elif nat: b_str = "Natura"
            elif avn: b_str = "Avon"

            count = s_data.get("total", 0)
            
            html_out += f'<h4 style="font-size: 16px; font-weight: bold; color: {h4_color}; margin-top: 16px; margin-bottom: 4px; border-bottom: 1px solid {border_color}; padding-bottom: 4px;">🚩 {meaning["title"]} ({count} SKUs - {b_str})</h4>\n'
            html_out += f'<strong style="color:{strong_color}; font-weight:900;">Contexto:</strong> {meaning["desc"]}<br>\n'
            html_out += f'<strong style="color:{strong_color}; font-weight:900;">Risco:</strong> {meaning["impact"]}\n'
            html_out += '<div style="margin-bottom: 12px;"></div>\n'

        html_out += f'''<span style="margin-right: 4px;">⚠️</span> <strong style="color:{strong_color}; font-weight:900;">Ação Recomendada:</strong> Priorize a correção das inconsistências de 'Alto Risco' antes do próximo push de produção.
</div>'''
        return html_out

    def _rule_based_gchat(self, stats: dict) -> str:
        """Heurística nativa de fallback para Google Chat."""
        by_type = stats.get("by_type", {})
        error_keys = [k for k, v in by_type.items() if v.get("total", 0) > 0]
        total_errors = sum(by_type[k].get("total", 0) for k in error_keys)

        if total_errors == 0:
            return "✅ *Operação Saudável*\nTodas as regras de negócio foram validadas. O catálogo está 100% íntegro para todos os canais."

        num_categories = len(error_keys)
        out = f"Identificamos *{total_errors} alertas* distribuídos em *{num_categories} categorias*. Confira o detalhamento completo:\n\n"

        priority = ['cross', 'ml', 'margin', 'price', 'missing', 'job', 'bundle', 'offline', 'logic', 'searchable', 'primary']
        def sort_key(k): return priority.index(k) if k in priority else 99
        sorted_keys = sorted(error_keys, key=sort_key)

        for key in sorted_keys:
            s_data = by_type[key]
            meaning = _KB.get(key, {"title": key, "desc": "Inconsistência técnica.", "impact": "Manual"})
            
            b_str = ""
            nat = s_data.get("natura", 0) > 0
            avn = s_data.get("avon", 0) > 0
            if nat and avn: b_str = "Natura e Avon"
            elif nat: b_str = "Natura"
            elif avn: b_str = "Avon"

            count = s_data.get("total", 0)
            
            out += f"🚩 *{meaning['title']}* ({count} SKUs - {b_str})\n"
            out += f"• *Contexto:* {meaning['desc']}\n"
            out += f"• *Risco:* {meaning['impact']}\n\n"

        out += "⚠️ *Ação Recomendada:* Priorize a correção das inconsistências de 'Alto Risco' antes do próximo push de produção."
        return out

