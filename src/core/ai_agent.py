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
                "Me responda EXCLUSIVAMENTE com um snippet HTML (sem a tag <html> ou <body>).\n"
                "NÃO utilize atributos 'style' para cores, pois o CSS será injetado pela interface.\n"
                "Utilize tags semânticas estruturadas (<h3>, <h4>, <ul>, <li>, <strong>, <p>).\n"
                "Utilize EMOJIS e ÍCONES (✅, ⚠️, 🚩, 📊, 💡, 🚨) para deixar o texto mais visual, moderno e menos seco.\n"
                "Estrutura esperada:\n"
                "1. Resumo executivo (1 parágrafo em <p> identificando erros e marcas com emojis de alerta ou sucesso).\n"
                "2. Lista de alertas detalhados (use <h4> para o título do erro e <ul>/<li> para contexto/risco).\n"
                "3. Uma recomendação final destacada.\n"
            )
        else:
            prompt += (
                "Me responda EXCLUSIVAMENTE com texto contendo tags HTML básicas (<b>, <br>).\n"
                "NÃO utilize formatação Markdown (como ** ou *), pois o Google Chat Cards não suporta.\n"
                "Utilize EMOJIS e ÍCONES (✅, ⚠️, 🚩, 📊, 💡, 🚨) para deixar o texto visual.\n"
                "Estrutura esperada:\n"
                "1. Resumo executivo curto.<br>\n"
                "2. Lista de problemas (use <b> para destacar o erro).<br>\n"
                "3. Recomendação final.<br>\n"
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

        # Fallback para heurística
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
                    return response.text.replace("```html", "").replace("```", "").strip()
            except Exception as e:
                print(f"Gemini API erro GChat: {e}")

        # Fallback
        return self._rule_based_gchat(stats)

    def _rule_based_html(self, stats: dict, theme: str) -> str:
        """Heurística nativa de fallback genérica (sem cores inline)."""
        by_type = stats.get("by_type", {})
        error_keys = [k for k, v in by_type.items() if v.get("total", 0) > 0]
        total_errors = sum(by_type[k].get("total", 0) for k in error_keys)

        if total_errors == 0:
            return '''<div>
<h3>✅ Operação Saudável</h3>
<p>Todas as regras de negócio foram validadas. O catálogo está 100% íntegro para todos os canais.</p>
</div>'''

        num_categories = len(error_keys)
        html_out = f'''<div>
<p>Identificamos <strong>{total_errors} alertas</strong> distribuídos em <strong>{num_categories} categorias</strong>. Confira o detalhamento completo:</p>
<hr>
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
            
            html_out += f'<h4>🚩 {meaning["title"]} ({count} SKUs - {b_str})</h4>\n'
            html_out += f'<ul><li><strong>Contexto:</strong> {meaning["desc"]}</li>\n'
            html_out += f'<li><strong>Risco:</strong> {meaning["impact"]}</li></ul>\n'

        html_out += '''<hr><p>⚠️ <strong>Ação Recomendada:</strong> Priorize a correção das inconsistências de 'Alto Risco' antes do próximo push de produção.</p>
</div>'''
        return html_out

    def _rule_based_gchat(self, stats: dict) -> str:
        """Heurística nativa de fallback para Google Chat (usando HTML básico)."""
        by_type = stats.get("by_type", {})
        error_keys = [k for k, v in by_type.items() if v.get("total", 0) > 0]
        total_errors = sum(by_type[k].get("total", 0) for k in error_keys)

        if total_errors == 0:
            return "✅ <b>Operação Saudável</b><br>Todas as regras de negócio foram validadas. O catálogo está 100% íntegro para todos os canais."

        num_categories = len(error_keys)
        out = f"Identificamos <b>{total_errors} alertas</b> distribuídos em <b>{num_categories} categorias</b>. Confira o detalhamento completo:<br><br>"

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
            
            out += f"🚩 <b>{meaning['title']}</b> ({count} SKUs - {b_str})<br>"
            out += f"• <b>Contexto:</b> {meaning['desc']}<br>"
            out += f"• <b>Risco:</b> {meaning['impact']}<br><br>"

        out += "⚠️ <b>Ação Recomendada:</b> Priorize a correção das inconsistências de 'Alto Risco' antes do próximo push de produção."
        return out

