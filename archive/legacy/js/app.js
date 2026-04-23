// ==========================================
// js/app.js - MAESTRO DA INTERFACE E NAVEGAÇÃO
// ==========================================

document.addEventListener("DOMContentLoaded", () => {
    App.loadTheme();
    App.setupDragDrop();
    lucide.createIcons();
});

const App = {
    toggleTheme: () => {
        const isDark = document.documentElement.classList.toggle('dark');
        localStorage.setItem('theme', isDark ? 'dark' : 'light');
    },

    saveSettings: () => {
        const url = document.getElementById('gchat-url').value;
        if (url && !url.startsWith('https://chat.googleapis.com/')) {
            return App.showToast("URL do Webhook inválida. Deve começar com chat.googleapis.com", "error");
        }
        localStorage.setItem('gchat_webhook', url);
        App.showToast("Configurações salvas com sucesso!", "info");
    },

    getSettings: () => {
        return {
            webhook: localStorage.getItem('gchat_webhook') || ""
        };
    },

    testWebhook: async () => {
        const url = document.getElementById('gchat-url').value;
        if (!url) return App.showToast("Insira uma URL para testar.", "warning");

        App.showToast("Enviando mensagem de teste...", "info");
        try {
            const res = await fetch(url, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ text: "🚀 *Pricing Master Suite V11.0*\nConexão com Webhook testada com sucesso!" })
            });
            if (res.ok) App.showToast("Teste enviado! Verifique seu Google Chat.", "info");
            else throw new Error("Status: " + res.status);
        } catch (e) {
            App.showToast("Erro ao testar Webhook. Verifique a URL ou permissões de CORS.", "error");
        }
    },

    sendToGoogleChat: async (data, type) => {
        const config = App.getSettings();
        if (!config.webhook) return App.showToast("Webhook não configurado. Vá em Configurações.", "warning");

        const errorLabels = {
            price: "Divergência Excel vs SF",
            list: "Catálogos e Listas SF",
            ml: "Divergência Minha Loja (ML)",
            margin: "Conflitos de Margem",
            logic: "Erros Lógicos (POR > DE)",
            missing: "Preços Faltantes",
            primary: "Categorias Primárias",
            bundle: "Integridade de Bundles",
            cross: "Marcas Cruzadas",
            offline: "Produtos Offline",
            job: "Jobs de Sincronização",
            searchable: "Divergência Searchable"
        };

        let payload = {};
        if (type === 'auditor') {
            const marginErrors = data.criticalList.filter(s => s.error.includes("CONFLITO PROG"));
            const sections = [];

            // Seção 1: 🏮 ALERTA CRÍTICO: CONFLITO DE MARGEM (Se houver)
            if (marginErrors.length > 0) {
                sections.push({
                    header: "🏮 ALERTA CRÍTICO: CONFLITO DE MARGEM",
                    widgets: [
                        { textParagraph: { text: `<b>${marginErrors.length} SKUs</b> com conflito de programação de desconto.` } },
                        { textParagraph: { text: `<b>SKUs Críticos:</b>\n` + marginErrors.slice(0, 15).map(s => `• ${s.sku}`).join('\n') } }
                    ]
                });
            }

            // Seção 2: 🚩 RESUMO DE FALHAS
            const failWidgets = [];
            for (let [key, count] of Object.entries(data.errors)) {
                if (count > 0) {
                    failWidgets.push({
                        decoratedText: {
                            topLabel: errorLabels[key] || key,
                            text: `🚩 ${count} divergências encontradas`,
                            startIcon: { knownIcon: "CONFIRMATION_NUMBER_ICON" }
                        }
                    });
                }
            }
            if (failWidgets.length > 0) {
                sections.push({ header: "🚩 RELATÓRIO DE FALHAS", widgets: failWidgets });
            }

            // Seção 3: ✅ AUDITORIA DE SUCESSO
            const successWidgets = [];
            for (let [key, count] of Object.entries(data.errors)) {
                if (count === 0) {
                    successWidgets.push({
                        decoratedText: {
                            text: `✅ ${errorLabels[key] || key} OK`,
                            startIcon: { knownIcon: "TICKET" }
                        }
                    });
                }
            }
            if (successWidgets.length > 0) {
                sections.push({ header: "✅ VERIFICAÇÕES DE SUCESSO", widgets: successWidgets });
            }

            // Seção Nova: 🤖 ANÁLISE DO PRICING AI
            if (data.aiInsight) {
                // Conversão robusta de Markdown para o formato do Google Chat (que usa * para Bold)
                let aiText = data.aiInsight
                    .replace(/### (.*?)\n/g, '<b>$1</b><br>') // Título Principal
                    .replace(/#### (.*?)\n/g, '<br><b>$1</b><br>') // Categorias de Erro
                    .replace(/\*\*(.*?)\*\*/g, '<b>$1</b>') // Negritos internos
                    .replace(/\n\n/g, '<br>')
                    .replace(/\n/g, '<br>');

                sections.push({
                    header: "🤖 ANÁLISE DO PRICING AI",
                    collapsible: false,
                    widgets: [{
                        textParagraph: { text: aiText }
                    }]
                });
            }

            payload = {
                cardsV2: [{
                    cardId: "auditorReport",
                    card: {
                        header: {
                            title: `Auditoria: ${data.brand}`,
                            subtitle: `V11.6 - Total de ${data.total} SKUs`,
                            imageUrl: "https://fonts.gstatic.com/s/i/short-term/release/googlestandardsymbols/security/default/24px.svg"
                        },
                        sections: sections
                    }
                }]
            };
        } else if (type === 'sync') {
            payload = {
                cardsV2: [{
                    cardId: "syncReport",
                    card: {
                        header: {
                            title: `Sync Concluído: ${data.brand}`,
                            subtitle: "Merchandising Automation",
                            imageUrl: "https://fonts.gstatic.com/s/i/short-term/release/googlestandardsymbols/sync/default/24px.svg"
                        },
                        sections: [{
                            widgets: [
                                { decoratedText: { text: `✅ Listas Processadas: ${data.lists}`, startIcon: { knownIcon: "DESCRIPTION" } } },
                                { decoratedText: { text: `➕ Adicionados: ${data.add}`, startIcon: { knownIcon: "STAR" } } },
                                { decoratedText: { text: `➖ Removidos: ${data.rem}`, startIcon: { knownIcon: "TRASH" } } }
                            ]
                        }]
                    }
                }]
            };
        }

        App.showToast("Enviando para o Google Chat...", "info");
        try {
            const res = await fetch(config.webhook, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
            if (res.ok) App.showToast("Relatório de alta transparência enviado!", "info");
            else throw new Error("Status: " + res.status);
        } catch (e) {
            App.showToast("Falha no envio. Verifique o Webhook.", "error");
        }
    },

    loadTheme: () => {
        if (localStorage.theme === 'dark' || (!('theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
            document.documentElement.classList.add('dark');
        } else {
            document.documentElement.classList.remove('dark');
        }
    },

    showToast: (msg, type = 'info') => {
        const container = document.getElementById('toast-container');
        if (!container) return alert(msg);

        const icons = {
            error: '<i data-lucide="alert-octagon" class="w-5 h-5 text-red-500"></i>',
            warning: '<i data-lucide="alert-triangle" class="w-5 h-5 text-orange-500"></i>',
            info: '<i data-lucide="info" class="w-5 h-5 text-indigo-500"></i>'
        };

        const bg = {
            error: 'bg-red-50 dark:bg-red-900/90 border-red-200 dark:border-red-800 text-red-800 dark:text-red-100',
            warning: 'bg-orange-50 dark:bg-orange-900/90 border-orange-200 dark:border-orange-800 text-orange-800 dark:text-orange-100',
            info: 'bg-indigo-50 dark:bg-indigo-900/90 border-indigo-200 dark:border-indigo-800 text-indigo-800 dark:text-indigo-100'
        };

        const toast = document.createElement('div');
        toast.className = `flex items-center gap-3 px-5 py-4 min-w-[300px] max-w-sm rounded-xl shadow-xl border transform transition-all duration-300 translate-y-10 opacity-0 backdrop-blur-md ${bg[type]}`;
        toast.innerHTML = `${icons[type]} <span class="text-sm font-medium flex-1">${msg}</span>`;

        container.appendChild(toast);
        lucide.createIcons({ root: toast });

        requestAnimationFrame(() => {
            requestAnimationFrame(() => toast.classList.remove('translate-y-10', 'opacity-0'));
        });

        setTimeout(() => {
            toast.classList.add('translate-y-10', 'opacity-0');
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    },

    setupDragDrop: () => {
        const inputs = document.querySelectorAll('input[type="file"]');
        inputs.forEach(input => {
            const zone = input.parentElement;
            input.addEventListener('dragover', (e) => {
                zone.classList.add('border-indigo-500', 'dark:border-indigo-400', 'bg-indigo-50', 'dark:bg-indigo-900/40', 'scale-[1.02]');
                zone.classList.remove('border-slate-200');
            });
            input.addEventListener('dragleave', (e) => {
                zone.classList.remove('border-indigo-500', 'dark:border-indigo-400', 'bg-indigo-50', 'dark:bg-indigo-900/40', 'scale-[1.02]');
                zone.classList.add('border-slate-200');
            });
            input.addEventListener('drop', (e) => {
                zone.classList.remove('border-indigo-500', 'dark:border-indigo-400', 'bg-indigo-50', 'dark:bg-indigo-900/40', 'scale-[1.02]');
                zone.classList.add('border-slate-200');
            });
        });
    },

    switchView: (viewId) => {
        ['view-menu', 'view-gen', 'view-sync', 'view-aud', 'view-vol', 'view-cad', 'view-pt', 'view-settings'].forEach(id => {
            const el = document.getElementById(id);
            if(el) el.classList.add('hidden-el');
        });

        ['nav-menu', 'nav-gen', 'nav-sync', 'nav-aud', 'nav-vol', 'nav-cad', 'nav-pt', 'nav-settings'].forEach(id => {
            let el = document.getElementById(id);
            if(el) {
                el.classList.remove('bg-white', 'dark:bg-slate-700', 'text-indigo-600', 'text-slate-800', 'dark:text-slate-100', 'shadow-sm');
                el.classList.add('text-slate-500', 'dark:text-slate-400');
            }
        });
        
        const targetView = document.getElementById('view-' + viewId);
        if(targetView) {
            targetView.classList.remove('hidden-el');
            // Carrega configurações se for a tela de settings
            if (viewId === 'settings') {
                document.getElementById('gchat-url').value = App.getSettings().webhook;
            }
        }
        
        let activeBtn = document.getElementById('nav-' + viewId);
        if(activeBtn) {
            activeBtn.classList.remove('text-slate-500', 'dark:text-slate-400');
            if(viewId === 'menu') {
                activeBtn.classList.add('bg-white', 'dark:bg-slate-700', 'text-slate-800', 'dark:text-slate-100', 'shadow-sm');
            } else {
                activeBtn.classList.add('bg-white', 'dark:bg-slate-700', 'text-indigo-600', 'dark:text-indigo-400', 'shadow-sm');
            }
        }
    }
};
