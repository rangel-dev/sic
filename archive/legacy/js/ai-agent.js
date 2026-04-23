/**
 * js/ai-agent.js - PRICING MASTER AI AGENT (V11.0)
 * Responsável por gerar resumos executivos e contextualizar erros.
 */

const PricingAI = {
    isThinking: false,
    lastInsight: "", // Armazena o texto puro (Markdown) para exportação
    
    // Mapeamento de Erros para Linguagem de Negócio (Base de Conhecimento V11.0 - Full Coverage)
    errorMeanings: {
        price: {
            title: "Divergência de Preço (Salesforce)",
            desc: "Os preços no Salesforce não batem com o planejado no Excel. Isso pode causar vendas com valores defasados.",
            impact: "Alto Risco Financeiro"
        },
        list: {
            title: "Visibilidade em Vitrines (Listas)",
            desc: "Produtos ativos no Excel mas fora das listas de atribuição do XML. O cliente não verá o produto nas vitrines.",
            impact: "Baixa Conversão"
        },
        ml: {
            title: "Concorrência de Canais (ML vs SITE)",
            desc: "O preço na Minha Loja (Consultor) está inferior ao Ecommerce. Isso gera conflito de canais e canibalização de vendas.",
            impact: "Conflito Estratégico"
        },
        margin: {
            title: "Margem de Segurança (Conflito)",
            desc: "SKUs promocionados em categorias onde o desconto acumulado ultrapassa a margem de saúde financeira.",
            impact: "Prejuízo Operacional"
        },
        logic: {
            title: "Erro de Cadastro (POR > DE)",
            desc: "O preço promocional está maior que o original, o que invalida a oferta no sistema.",
            impact: "Erro de Experiência / UX"
        },
        searchable: {
            title: "Indexação de Busca (Searchable)",
            desc: "O flag de busca no Salesforce diverge do planejado. O produto pode estar invisível na busca interna.",
            impact: "Perda de Fluxo Orgânico"
        },
        job: {
            title: "Falha de Sincronização (JOB ML)",
            desc: "A categoria da Minha Loja não reflete a categoria da Marca Mãe. O Job de automação falhou.",
            impact: "Catálogo Desatualizado"
        },
        bundle: {
            title: "Saúde de Kits (Bundles)",
            desc: "Componentes do kit estão offline ou sem preço, impedindo a venda do conjunto completo.",
            impact: "Queda no Ticket Médio"
        },
        offline: {
            title: "Indisponibilidade (Prod. Offline)",
            desc: "Produtos que deveriam estar à venda mas constam como Offline no Salesforce.",
            impact: "Risco de Receita (Venda planejada não realizada)"
        },
        missing: {
            title: "Ausência de Preço (DE/POR)",
            desc: "Falta um dos pilares de preço (DE ou POR) no Pricebook, o que remove o SKU do ar.",
            impact: "Perda imediata de Venda"
        },
        primary: {
            title: "Categoria Primária (SEO)",
            desc: "O produto está sem a atribuição de categoria primária, essencial para navegação e breadcrumbs.",
            impact: "Impacto no SEO e Filtros"
        },
        cross: {
            title: "Invasão de Marca (Cross-Brand)",
            desc: "Detectamos SKUs de uma marca dentro do Pricebook de outra. Grave erro de importação massiva.",
            impact: "Erro Crítico de Governança"
        }
    },

    typeWriter: (text, elementId, speed = 15) => {
        const el = document.getElementById(elementId);
        if (!el) return;
        el.innerHTML = "";
        let i = 0;
        
        function type() {
            if (i < text.length) {
                if (text.charAt(i) === '<') {
                    const tagEnd = text.indexOf('>', i);
                    if (tagEnd !== -1) {
                        el.innerHTML += text.substring(i, tagEnd + 1);
                        i = tagEnd + 1;
                    } else {
                        el.innerHTML += text.charAt(i);
                        i++;
                    }
                } else {
                    el.innerHTML += text.charAt(i);
                    i++;
                }
                setTimeout(type, speed);
            }
        }
        type();
    },

    generateInsight: (stats) => {
        if (!stats) return "Nenhum dado processado para análise.";

        // Coleta todas as categorias com erros
        const errorKeys = Object.keys(stats).filter(k => stats[k] && stats[k].total > 0);
        const totalErrors = errorKeys.reduce((acc, k) => acc + stats[k].total, 0);

        if (totalErrors === 0) return "### ✅ Operação Saudável\n\nTodas as regras de negócio foram validadas. O catálogo está 100% íntegro para todos os canais.";

        let summary = `Identificamos **${totalErrors} alertas** distribuídos em **${errorKeys.length} categorias**. Confira o detalhamento completo:\n\n`;

        // Ordem de Criticidade (Estratégico > Operacional)
        const priority = ['cross', 'ml', 'margin', 'price', 'missing', 'job', 'bundle', 'offline', 'logic', 'searchable', 'primary'];
        const sortedKeys = errorKeys.sort((a, b) => {
            const idxA = priority.indexOf(a) !== -1 ? priority.indexOf(a) : 99;
            const idxB = priority.indexOf(b) !== -1 ? priority.indexOf(b) : 99;
            return idxA - idxB;
        });

        sortedKeys.forEach(key => {
            const s = stats[key];
            const meaning = PricingAI.errorMeanings[key] || { title: key, desc: "Inconsistência técnica.", impact: "Manual" };
            const brands = (s.natura > 0 ? "Natura" : "") + 
                           (s.natura > 0 && s.avon > 0 ? " e " : "") +
                           (s.avon > 0 ? "Avon" : "");

            summary += `#### 🚩 ${meaning.title} (${s.total} SKUs - ${brands})\n`;
            summary += `**Contexto:** ${meaning.desc}\n`;
            summary += `**Risco:** ${meaning.impact}\n\n`;
        });

        summary += `⚠️ **Ação Recomendada:** Priorize a correção das inconsistências de 'Alto Risco' antes do próximo push de produção.`;

        return summary;
    },

    run: (stats) => {
        const panel = document.getElementById('aiInsightPanel');
        const content = document.getElementById('aiInsightContent');

        if (!panel || !content) return;

        // Mostrar painel
        panel.classList.remove('hidden-el');
        
        // Simular pensamento
        content.innerHTML = "<div class='flex gap-2 items-center text-indigo-500 font-bold'><i class='animate-spin' data-lucide='loader-2'></i> Analisando dados e gerando contexto...</div>";
        if(window.lucide) lucide.createIcons();

        // GERA IMEDIATAMENTE PARA O WEBHOOK
        const rawText = PricingAI.generateInsight(stats);
        PricingAI.lastInsight = rawText;

        setTimeout(() => {
            // CONVERSÃO DE MARKDOWN PARA HTML (Ordem correta para evitar conflitos)
            let html = rawText
                .replace(/### (.*?)\n/g, '<h3 class="text-lg font-black text-indigo-600 dark:text-indigo-400 mb-2">$1</h3>')
                .replace(/#### (.*?)\n/g, '<h4 class="text-md font-bold text-slate-800 dark:text-slate-200 mt-4 mb-1 border-b border-indigo-500/30 pb-1">$1</h4>')
                .replace(/\*\*(.*?)\*\*/g, '<strong class="text-slate-900 dark:text-white font-black">$1</strong>')
                .replace(/\n\n/g, '<div class="mb-3"></div>')
                .replace(/\n/g, '<br>')
                .replace(/⚠️/g, '<span class="mr-1">⚠️</span>');

            PricingAI.typeWriter(html, 'aiInsightContent', 10);
        }, 1500);
    },

    toggle: () => {
        const panel = document.getElementById('aiContentArea');
        const icon = document.getElementById('aiToggleIcon');
        if (panel.classList.contains('hidden-el')) {
            panel.classList.remove('hidden-el');
            icon.style.transform = 'rotate(180deg)';
        } else {
            panel.classList.add('hidden-el');
            icon.style.transform = 'rotate(0deg)';
        }
    }
};
