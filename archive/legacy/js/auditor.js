// ==========================================
// js/auditor.js - MÓDULO 3: AUDITORIA DOUBLE-BLIND (V8.4 - Scanner Bruto à prova de falhas)
// ==========================================

const Auditor = {
    data: [],
    activeBrands: new Set(['Natura', 'Avon']),
    activeFilters: new Set(),

    pbFile: null,
    catFiles: [],
    excelFiles: [],

    updateUI: async (pct, txt, det) => {
        document.getElementById('audProgressBar').style.width = pct + "%";
        document.getElementById('audStatusText').innerText = txt;
        document.getElementById('audStepDetails').innerText = det;
        await sleep(50);
    },

    // Novo Scanner "Força Bruta": Ignora colunas e lê o arquivo como texto puro.
    detectBrandQuickly: async (file) => {
        try {
            const exData = await file.arrayBuffer();
            await new Promise(r => setTimeout(r, 10)); // Yield UI
            const wb = XLSX.read(new Uint8Array(exData), {
                type: 'array', cellStyles: false, cellFormula: false, cellHTML: false, sheetStubs: false
            });

            // Pega a aba GRADE ou a primeira aba se a GRADE não existir
            let targetSheetName = wb.SheetNames.includes("GRADE DE ATIVAÇÃO") ? "GRADE DE ATIVAÇÃO" : wb.SheetNames[0];
            const ws = wb.Sheets[targetSheetName];
            if (!ws) return 'Desconhecida';

            // Transforma a aba inteira num bloco gigante de texto CSV
            const csv = XLSX.utils.sheet_to_csv(ws).toUpperCase();

            // Conta quantas vezes a palavra aparece no arquivo inteiro
            let natCount = (csv.match(/NATBRA-/g) || []).length;
            let avnCount = (csv.match(/AVNBRA-/g) || []).length;

            if (natCount === 0 && avnCount === 0) return 'Desconhecida';
            return natCount >= avnCount ? 'Natura' : 'Avon';
        } catch (e) {
            console.error("Erro no scanner bruto: ", e);
            return 'Desconhecida';
        }
    },

    handleUpload: async (e, type) => {
        const newFiles = Array.from(e.target.files);
        if (newFiles.length === 0) return;

        const setLoadedState = (zone, titleText, descText) => {
            if(!zone) return;
            zone.classList.remove('border-slate-200', 'dark:border-slate-700');
            zone.classList.add('!border-emerald-500', 'dark:!border-emerald-400', 'bg-emerald-50', 'dark:bg-emerald-900/30');
            let icon = zone.querySelector('i');
            if (icon) { icon.setAttribute('data-lucide', 'check-check'); icon.className = 'text-emerald-500 dark:text-emerald-400 w-5 h-5'; }
            if (zone.querySelector('h3')) {
                zone.querySelector('h3').classList.add('text-emerald-700', 'dark:text-emerald-300');
                zone.querySelector('h3').innerText = titleText;
            }
            if (zone.querySelector('p')) {
                zone.querySelector('p').classList.add('text-emerald-600', 'dark:text-emerald-400');
                zone.querySelector('p').innerText = descText;
            }
            if (window.lucide) lucide.createIcons();
        }

        if (type === 'pb') {
            Auditor.pbFile = newFiles[0];
            setLoadedState(document.getElementById('audPbInput').parentElement, "PB Lido", Auditor.pbFile.name);
        }
        else if (type === 'cat') {
            newFiles.forEach(f => {
                if (!Auditor.catFiles.some(existing => existing.name === f.name)) {
                    Auditor.catFiles.push(f);
                }
            });
            setLoadedState(document.getElementById('audCatInput').parentElement, Auditor.catFiles.length + " XMLs Anexados", "Catálogos na Fila");
        }
        else if (type === 'excel') {
            let zone = document.getElementById('audExcelInput').parentElement;
            let titleEl = document.getElementById('excelUploadTitle');
            let descEl = document.getElementById('excelUploadDesc');
            
            if (titleEl) { titleEl.innerText = "Scanner Auto-Discovery..."; titleEl.classList.add('text-indigo-600', 'dark:text-indigo-400', 'animate-pulse'); }
            if (descEl) descEl.innerText = "Lendo matriz pesada e detectando...";
            
            zone.classList.add('!border-indigo-500', 'dark:!border-indigo-500', 'bg-indigo-50', 'dark:bg-indigo-900/30');

            await sleep(400); // Feedback visual fluido para o usuário ler a pulsação do motor

            for (let f of newFiles) {
                if (!Auditor.excelFiles.some(existing => existing.file.name === f.name)) {
                    let brand = await Auditor.detectBrandQuickly(f);
                    Auditor.excelFiles.push({ file: f, brand: brand });
                }
            }

            if (titleEl) titleEl.classList.remove('text-indigo-600', 'dark:text-indigo-400', 'animate-pulse');
            zone.classList.remove('!border-indigo-500', 'dark:!border-indigo-500', 'bg-indigo-50', 'dark:bg-indigo-900/30');
            
            let brands = [...new Set(Auditor.excelFiles.map(e => e.brand))];
            setLoadedState(zone, "Excel Concl.", "Marcas lidas: " + brands.join(" / "));
        }

        e.target.value = '';
        Auditor.updateFileInfo();
    },

    updateFileInfo: () => {
        const pb = Auditor.pbFile;
        const cats = Auditor.catFiles;
        const excels = Auditor.excelFiles;

        const list = document.getElementById('audFileList');
        const container = document.getElementById('audFileInfoBox');

        if (!pb && cats.length === 0 && excels.length === 0) {
            container.classList.add('hidden-el');
            return;
        }

        container.classList.remove('hidden-el');
        list.innerHTML = '';

        const fD = (ts) => new Date(ts).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });

        if (pb) list.innerHTML += `<li><span class="text-indigo-400 font-bold">XML PB:</span> ${pb.name} (${fD(pb.lastModified)})</li>`;
        cats.forEach(c => list.innerHTML += `<li><span class="text-slate-400 font-bold">XML CT:</span> ${c.name} (${fD(c.lastModified)})</li>`);

        excels.forEach(eObj => {
            let colorClass = 'text-amber-400';
            let label = 'EXCEL';
            if (eObj.brand === 'Natura') { colorClass = 'text-orange-400'; label = 'Excel Natura'; }
            else if (eObj.brand === 'Avon') { colorClass = 'text-purple-400'; label = 'Excel Avon'; }
            else { colorClass = 'text-slate-400'; label = 'Excel S/ Marca'; }
            list.innerHTML += `<li><span class="${colorClass} font-bold">${label}:</span> ${eObj.file.name} (${fD(eObj.file.lastModified)})</li>`;
        });
    },

    toggleFilter: (filterType) => {
        if (Auditor.activeFilters.has(filterType)) {
            Auditor.activeFilters.delete(filterType);
        } else {
            Auditor.activeFilters.add(filterType);
        }
        Auditor.renderDashboard();
    },

    toggleBrand: (brand) => {
        if (Auditor.activeBrands.has(brand)) {
            Auditor.activeBrands.delete(brand);
        } else {
            Auditor.activeBrands.add(brand);
        }
        Auditor.renderDashboard();
    },

    checkFilterMatch: (row, activeBrands, activeFilters) => {
        // Se marcas estão vazias ou filtros estão vazios -> Nenhum resultado
        if (activeBrands.size === 0 || activeFilters.size === 0) return false;
        
        // 1. Checa Marca
        if (!activeBrands.has(row.Marca)) return false;

        // 2. Checa Erro (OR Logic entre os ativos)
        const errString = row.E;
        let matched = false;
        if (activeFilters.has('price') && (errString.includes('DIVERGE SF (DE') || errString.includes('DIVERGE SF (POR') || errString.includes('FALTA NO SF (PREÇO)'))) matched = true;
        if (activeFilters.has('list') && (errString.includes('FALTA NO SF') || errString.includes('LISTA INEXISTENTE'))) matched = true;
        if (activeFilters.has('ml') && errString.includes('DIVERGE ML')) matched = true;
        if (activeFilters.has('margin') && errString.includes('CONFLITO PROG')) matched = true;
        if (activeFilters.has('logic') && errString.includes('POR > DE')) matched = true;
        if (activeFilters.has('missing') && errString.includes('FALTA PREÇO')) matched = true;
        if (activeFilters.has('primary') && errString.includes('FALTA CAT PRIMÁRIA')) matched = true;
        if (activeFilters.has('bundle') && errString.includes('BUNDLE QUEBRADO')) matched = true;
        if (activeFilters.has('cross') && errString.includes('MARCA CRUZADA')) matched = true;
        if (activeFilters.has('offline') && errString.includes('PRODUTO OFFLINE (Ação Comercial Exigida)')) matched = true;
        if (activeFilters.has('job') && errString.includes('JOB NÃO RODOU')) matched = true;
        if (activeFilters.has('searchable') && errString.includes('DIVERGE SEARCHABLE')) matched = true;
        
        return matched;
    },

    renderDashboard: () => {
        const categories = ['price', 'list', 'ml', 'margin', 'logic', 'missing', 'primary', 'bundle', 'cross', 'offline', 'job', 'searchable'];
        const activeFilters = Auditor.activeFilters;
        const activeBrands = Auditor.activeBrands;

        // 1. Recalcula Estatísticas Dinâmicas por Marca (V11.6)
        const dynamicStats = {};
        categories.forEach(c => dynamicStats[c] = { total: 0, nat: 0, avn: 0 });

        const errorKeywords = {
            price: ['DIVERGE SF (DE', 'DIVERGE SF (POR', 'FALTA NO SF (PREÇO)'],
            list: ['FALTA NO SF', 'LISTA INEXISTENTE'],
            ml: ['DIVERGE ML'],
            margin: ['CONFLITO PROG'],
            logic: ['POR > DE'],
            missing: ['FALTA PREÇO'],
            primary: ['FALTA CAT PRIMÁRIA'],
            bundle: ['BUNDLE QUEBRADO'],
            cross: ['MARCA CRUZADA'],
            offline: ['PRODUTO OFFLINE'],
            job: ['JOB NÃO RODOU'],
            searchable: ['DIVERGE SEARCHABLE']
        };

        Auditor.data.forEach(r => {
            if (!activeBrands.has(r.Marca)) return;
            const isNat = r.Marca === 'Natura';
            for (let cat of categories) {
                if (errorKeywords[cat].some(k => r.E.includes(k))) {
                    dynamicStats[cat].total++;
                    isNat ? dynamicStats[cat].nat++ : dynamicStats[cat].avn++;
                }
            }
        });

        // Atualiza os números nos Cards
        categories.forEach(c => {
            const s = dynamicStats[c];
            const cap = c.charAt(0).toUpperCase() + c.slice(1);
            const el = document.getElementById('count' + cap);
            const elN = document.getElementById('count' + cap + 'Nat');
            const elA = document.getElementById('count' + cap + 'Avn');
            if (el) el.innerText = s.total;
            if (elN) elN.innerText = s.nat;
            if (elA) elA.innerText = s.avn;
            
            // Oculta cards vazios (opcional, mas mantém o comportamento anterior de limpeza)
            const card = document.getElementById('card-' + c);
            if (card) {
                if (s.total === 0 && !activeFilters.has(c)) card.classList.add('hidden-el');
                else card.classList.remove('hidden-el');
            }
        });

        // 2. Atualiza Cores dos Botões de Marca
        const btnNat = document.getElementById('btn-natura');
        const btnAvn = document.getElementById('btn-avon');
        if (btnNat) {
            if (activeBrands.has('Natura')) btnNat.className = "px-6 py-2 rounded-xl text-sm font-black bg-orange-500 text-white shadow-md hover-lift smooth-transition flex items-center gap-2";
            else btnNat.className = "px-6 py-2 rounded-xl text-sm font-black bg-slate-200 dark:bg-slate-700 text-slate-400 dark:text-slate-500 filter-dimmed smooth-transition flex items-center gap-2";
            btnNat.innerHTML = `<i data-lucide="${activeBrands.has('Natura') ? 'check-circle' : 'circle'}"></i> NATURA`;
        }
        if (btnAvn) {
            if (activeBrands.has('Avon')) btnAvn.className = "px-6 py-2 rounded-xl text-sm font-black bg-purple-600 text-white shadow-md hover-lift smooth-transition flex items-center gap-2";
            else btnAvn.className = "px-6 py-2 rounded-xl text-sm font-black bg-slate-200 dark:bg-slate-700 text-slate-400 dark:text-slate-500 filter-dimmed smooth-transition flex items-center gap-2";
            btnAvn.innerHTML = `<i data-lucide="${activeBrands.has('Avon') ? 'check-circle' : 'circle'}"></i> AVON`;
        }
        if (window.lucide) lucide.createIcons();

        // 3. Atualiza Estilo dos Cards de Erro
        categories.forEach(c => {
            let el = document.getElementById('card-' + c);
            if (!el || el.classList.contains('hidden-el')) return;

            if (activeFilters.has(c)) {
                el.classList.add('filter-active');
                el.classList.remove('filter-dimmed');
            } else {
                el.classList.remove('filter-active');
                el.classList.add('filter-dimmed');
            }
        });

        // 4. Filtragem Real da Tabela
        const lbl = document.getElementById('filterLabel');
        const isNotFullState = activeBrands.size < 2 || activeFilters.size < categories.filter(k => !document.getElementById('card-'+k).classList.contains('hidden-el')).length;
        isNotFullState ? lbl.classList.remove('hidden-el') : lbl.classList.add('hidden-el');

        let filteredData = Auditor.data.filter(r => Auditor.checkFilterMatch(r, activeBrands, activeFilters));
        document.getElementById('tableRowsCount').innerText = `${filteredData.length} SKUs encontrados`;

        if (filteredData.length === 0) {
            document.getElementById('audTableBody').innerHTML = `<tr><td colspan="5" class="p-8 text-center text-slate-400 font-medium">Nenhum resultado encontrado para os filtros selecionados.</td></tr>`;
            return;
        }

        const rowsHTML = [];
        for (let i = 0; i < Math.min(filteredData.length, 500); i++) {
            let r = filteredData[i];
            let isCritical = r.C === 'row-error';
            rowsHTML.push(`<tr class="border-b border-slate-100 dark:border-slate-700/50 table-row-hover smooth-transition">
                <td class="px-6 py-4 font-bold text-xs font-mono text-slate-700 dark:text-slate-300">${r.SKU}</td>
                <td class="px-6 py-4 text-xs font-medium text-slate-500 dark:text-slate-400">${r.Marca}</td>
                <td class="px-6 py-4 text-xs font-medium text-slate-600 dark:text-slate-300">R$ ${r.O.toFixed(2)}</td>
                <td class="px-6 py-4 text-xs font-medium text-slate-600 dark:text-slate-300">R$ ${r.ML.toFixed(2)}</td>
                <td class="px-6 py-4 text-[10px] font-black ${isCritical ? 'text-red-500' : 'text-orange-500'}">${r.E}</td>
            </tr>`);
        }

        if (filteredData.length > 500) {
            rowsHTML.push(`<tr><td colspan="5" class="px-6 py-4 text-center text-xs font-bold text-indigo-400 bg-indigo-50/50 dark:bg-indigo-900/20">Mostrando os primeiros 500 resultados. Exporte para ver todos.</td></tr>`);
        }

        document.getElementById('audTableBody').innerHTML = rowsHTML.join('');
    },

    processData: async () => {
        const pb = Auditor.pbFile;
        const cats = Auditor.catFiles;
        const exFiles = Auditor.excelFiles.map(e => e.file);

        if (!pb || cats.length === 0) return App.showToast("Insira o Pricebook e ao menos um Catálogo XML.", "warning");

        document.getElementById('audAllGoodMsg').classList.add('hidden-el');
        document.getElementById('audDashboard').classList.add('hidden-el');
        const errBox = document.getElementById('audPreflightError');
        if (errBox) errBox.classList.add('hidden-el');

        const showError = (title, msg) => {
            if (errBox) {
                document.getElementById('audPreflightErrorTitle').innerText = title;
                document.getElementById('audPreflightErrorMsg').innerText = msg;
                errBox.classList.remove('hidden-el');
                document.getElementById('audProcessBtn').classList.add('hidden-el');
                if (window.lucide) lucide.createIcons();
            } else {
                App.showToast(title + ": " + msg, "error");
            }
        };

        // --- PRE-FLIGHT CHECKS (Rápidos e sem flash na Tela) ---
        // const now = Date.now();
        // const tenMins = 10 * 60 * 1000;
        // let expiredFiles = [];

        // const checkAge = (f) => {
        //     if ((now - f.lastModified) > tenMins) expiredFiles.push(f.name);
        // };

        // if (pb) checkAge(pb);
        // cats.forEach(checkAge);
        // // Regra de negócios nova: Excels da área de preços (comerciais) não são cobrados de estarem em defasagem máxima de 10 minutos. Somente XMLs.

        // if (expiredFiles.length > 0) {
        //     return showError("Arquivos SF Defasados", `Os arquivos Pricebook/Catálogo abaixo foram baixados há mais de 10 minutos:\n\n${expiredFiles.join("\n")}\n\nA auditoria exige arquivos SF incrivelmente recentes. Exporte-os novamente.`);
        // }

        let catBrands = new Set();
        for (let f of cats) {
            let slice = f.slice(0, 4096);
            let text = await slice.text();
            let match = text.match(/<catalog[^>]*catalog-id="([^"]+)"/i);
            let catIdStr = match ? match[1].toLowerCase() : f.name.toLowerCase();
            let brandCat = (catIdStr.includes("cb-br") || catIdStr.includes("cbbrazil") || catIdStr.includes("cbcom")) ? "ML" : catIdStr.includes("natura") ? "Natura" : catIdStr.includes("avon") ? "Avon" : "Desconhecido";
            catBrands.add(brandCat);
        }

        // --- REGRA DE OURO V11.6 (SINGLE BRAND AUDIT) ---
        // Só cobramos o XML da marca se o usuário subiu o Excel correspondente.
        const excelBrands = new Set(Auditor.excelFiles.map(e => e.brand));
        const missingXmls = [];
        if (excelBrands.has("Natura") && !catBrands.has("Natura")) missingXmls.push("XML Natura");
        if (excelBrands.has("Avon") && !catBrands.has("Avon")) missingXmls.push("XML Avon");
        if (!catBrands.has("ML")) missingXmls.push("XML Minha Loja (cbbrazil)");

        if (missingXmls.length > 0) {
            return showError("Estrutura de Catálogos Incompleta", `Para os Excels carregados, faltam os seguintes XMLs:\n\n• ${missingXmls.join("\n• ")}\n\nAnexe-os para garantir a precisão do cruzamento Double-Blind.`);
        }
        // --- FIM REGRA DE OURO ---
        // --- FIM PRE-FLIGHT ---

        // Iniciar Processamento Pesado Real
        document.getElementById('audProcessBtn').classList.add('hidden-el');
        document.getElementById('audStatusArea').classList.remove('hidden-el');

        try {
            await Auditor.updateUI(10, "Lendo Planilhas", "Escaneando layout e varrendo matrizes...");
            let excelPrices = {}, excelLists = {};
            let excelHasNatura = false, excelHasAvon = false;

            const processExcel = async (file) => {
                const exData = await file.arrayBuffer();
                await new Promise(r => setTimeout(r, 10)); // Yield UI
                const wb = XLSX.read(new Uint8Array(exData), {
                    type: 'array', cellStyles: false, cellFormula: false, cellHTML: false, sheetStubs: false
                });

                let fileBrand = Auditor.excelFiles.find(e => e.file.name === file.name)?.brand || 'Desconhecida';
                if (fileBrand === 'Natura') excelHasNatura = true;
                if (fileBrand === 'Avon') excelHasAvon = true;

                const gradeIdx = wb.SheetNames.indexOf("GRADE DE ATIVAÇÃO");
                if (gradeIdx !== -1 && !(wb.Workbook && wb.Workbook.Sheets && wb.Workbook.Sheets[gradeIdx] && wb.Workbook.Sheets[gradeIdx].Hidden)) {
                    const wsGrade = wb.Sheets["GRADE DE ATIVAÇÃO"];
                    // A extração de preços ainda precisa da função findDynamicColumns, certifique-se que ela existe no seu utils.js
                    const { skuCol, deCol, porCol, visibleCol } = findDynamicColumns(wsGrade);
                    const rG = XLSX.utils.decode_range(wsGrade['!ref']);

                    let emptyStreak = 0;
                    for (let r = rG.s.r; r <= rG.e.r; r++) {
                        if (r % 1000 === 0) await new Promise(res => setTimeout(res, 0)); // Evita freeze
                        const cSKU = wsGrade[XLSX.utils.encode_cell({ r: r, c: skuCol })];
                        const sku = cSKU ? String(cSKU.v).trim().toUpperCase() : "";

                        if (!sku) {
                            emptyStreak++;
                            if (emptyStreak >= 50) break; // Trava de performance
                        } else {
                            emptyStreak = 0;
                            if (sku && (sku.startsWith('NATBRA-') || sku.startsWith('AVNBRA-'))) {
                                if (fileBrand === 'Natura' && sku.startsWith('AVNBRA-')) continue;
                                if (fileBrand === 'Avon' && sku.startsWith('NATBRA-')) continue;

                                const cDE = wsGrade[XLSX.utils.encode_cell({ r: r, c: deCol })];
                                const cPOR = wsGrade[XLSX.utils.encode_cell({ r: r, c: porCol })];
                                const cVIS = visibleCol !== -1 ? wsGrade[XLSX.utils.encode_cell({ r: r, c: visibleCol })] : null;

                                excelPrices[sku] = {
                                    DE: cDE && !isNaN(parseFloat(cDE.v)) ? parseFloat(cDE.v) : 0,
                                    POR: cPOR && !isNaN(parseFloat(cPOR.v)) ? parseFloat(cPOR.v) : 0,
                                    VISIBLE: cVIS ? String(cVIS.v).trim().toUpperCase() : ""
                                };
                            }
                        }
                    }
                }

                for (let idx = 0; idx < wb.SheetNames.length; idx++) {
                    const sheetName = wb.SheetNames[idx];
                    if (wb.Workbook && wb.Workbook.Sheets && wb.Workbook.Sheets[idx] && wb.Workbook.Sheets[idx].Hidden) continue;
                    const match = sheetName.match(/^LISTA[-_\s]*0*(\d+)/i);
                    if (match) {
                        const num = match[1].padStart(2, '0');
                        const ws = wb.Sheets[sheetName];
                        if (!ws['!ref']) continue;

                        const skuColList = findSkuColumnOnly(ws);
                        const rG = XLSX.utils.decode_range(ws['!ref']);

                        let emptyStreakL = 0;
                        for (let r = rG.s.r; r <= rG.e.r; r++) {
                            if (r % 1000 === 0) await new Promise(res => setTimeout(res, 0)); // Evita freeze
                            const c = ws[XLSX.utils.encode_cell({ r: r, c: skuColList })];
                            const sku = c ? String(c.v).trim().toUpperCase() : "";
                            if (!sku) {
                                emptyStreakL++;
                                if (emptyStreakL >= 50) break; // Trava de performance
                            } else {
                                emptyStreakL = 0;
                                if (sku && (sku.startsWith('NATBRA-') || sku.startsWith('AVNBRA-'))) {
                                    if (fileBrand === 'Natura' && sku.startsWith('AVNBRA-')) continue;
                                    if (fileBrand === 'Avon' && sku.startsWith('NATBRA-')) continue;

                                    let cleanId = sku.startsWith('NATBRA-') ? "LISTA_" + num : "lista-" + num;
                                    if (!excelLists[cleanId]) excelLists[cleanId] = new Set();
                                    excelLists[cleanId].add(sku);
                                }
                            }
                        }
                    }
                }
            };

            for (let file of exFiles) { await processExcel(file); }

            for (let listKey in excelLists) {
                if (excelLists[listKey].size === 0) delete excelLists[listKey];
            }

            await Auditor.updateUI(40, "Descompactando Pricebook", "Extraindo matriz XML base...");

            const pbText = await pb.text();
            const xmlDoc = new DOMParser().parseFromString(pbText, "text/xml");
            let pricesXML = {};

            // Leitura Flexível (que resolve aquele problema de IDs diferentes do Salesforce)
            for (let p of xmlDoc.getElementsByTagName("pricebook")) {
                let idStr = (p.getElementsByTagName("header")[0]?.getAttribute("pricebook-id") || "").toLowerCase();
                let pbBrand = null;

                if (idStr.includes("cb-br") || idStr.includes("cbbrazil") || idStr.includes("cbcom")) pbBrand = "ML";
                else if (idStr.includes("natura") && (idStr.includes("brazil") || idStr.includes("-br"))) pbBrand = "Natura";
                else if (idStr.includes("avon") && (idStr.includes("brazil") || idStr.includes("-br"))) pbBrand = "Avon";

                if (!pbBrand) continue;

                let type = idStr.includes("sale") ? "POR" : "DE";
                for (let t of p.getElementsByTagName("price-table")) {
                    let sku = t.getAttribute("product-id").toUpperCase();
                    if (!pricesXML[sku]) pricesXML[sku] = { Natura: {}, Avon: {}, ML: {} };

                    let amt = parseFloat(t.getElementsByTagName("amount")[0]?.textContent);
                    if (!isNaN(amt)) pricesXML[sku][pbBrand][type] = amt;
                }
            }

            await Auditor.updateUI(60, "Varrendo Catálogos", "Lendo Namespaces, Primary Flags e Bundles...");

            let prohibitedState = { Natura: new Set(), Avon: new Set(), ML: new Set() };
            let catMissingPrimary = {}, xmlLists = {};
            let onlineStatus = {};
            let bundles = {};
            let variationBaseProducts = {};
            let searchableStatus = {};
            let isTechnicalSku = {}; // Novo: Detecta nomes em CAIXA ALTA
            
            // Novos dicionários para o Check #11
            let categoryAssignmentsMap = { Natura: {}, Avon: {}, ML: {} };
            let mlJobRulesCount = [];

            for (let f of cats) {
                const cText = await f.text();
                const cDoc = new DOMParser().parseFromString(cText, "text/xml");
                const catNode = cDoc.getElementsByTagName("catalog")[0];
                let catIdStr = (catNode ? catNode.getAttribute("catalog-id") || "" : "").toLowerCase();
                let brandCat = (catIdStr.includes("cb-br") || catIdStr.includes("cbbrazil") || catIdStr.includes("cbcom")) ? "ML" : catIdStr.includes("natura") ? "Natura" : catIdStr.includes("avon") ? "Avon" : "Desconhecido";

                let assignedSkus = new Set(), primarySkus = new Set();

                if (brandCat === "ML") {
                    for (let cat of cDoc.getElementsByTagName("category")) {
                        let catId = cat.getAttribute("category-id");
                        if (!catId) continue;
                        let rules = cat.getElementsByTagName("category-assignment-rule");
                        for (let rule of rules) {
                            let conds = rule.getElementsByTagName("category-condition");
                            for (let cond of conds) {
                                let motherCatId = cond.getAttribute("category-id");
                                if (motherCatId) {
                                    mlJobRulesCount.push({ mlCatId: catId, motherCatId: motherCatId });
                                    break;
                                }
                            }
                        }
                    }
                }

                let products = cDoc.getElementsByTagName("product");
                for (let p of products) {
                    let sku = p.getAttribute("product-id");
                    if (!sku) continue;
                    sku = sku.toUpperCase();

                    let oFlag = getTagText(p, "online-flag");
                    if (oFlag !== null) {
                        if (oFlag === "true") onlineStatus[sku] = true;
                        else if (onlineStatus[sku] !== true) onlineStatus[sku] = false;
                    }

                    let sFlag = getTagText(p, "searchable-flag");
                    if (sFlag !== null) {
                        if (sFlag === "true") searchableStatus[sku] = true;
                        else if (searchableStatus[sku] !== true) searchableStatus[sku] = false;
                    }

                    // Regra V10.4: Detectar se o nome está todo em CAIXA ALTA (Ignorar no Searchable)
                    const nameEls = Array.from(p.getElementsByTagName("display-name")).concat(Array.from(p.getElementsByTagName("name")));
                    const namesToTest = nameEls.map(el => (el.textContent || "").trim()).filter(t => t.length > 0);
                    const fName = (getTagText(p, "friendly-name") || "").trim();
                    if (fName) namesToTest.push(fName);
                    
                    if (namesToTest.some(n => n === n.toUpperCase() && /[A-Z]/.test(n))) {
                        isTechnicalSku[sku] = true;
                    }

                    // Detecção de Variation Base Product (não deve ser checado nos bundles)
                    const variationMarker = (p.getAttribute("variation-base-product") || p.getAttribute("is-variation-base") || "").toString().toLowerCase();
                    const productType = (p.getAttribute("type") || getTagText(p, "product-type") || "").toString().toLowerCase();
                    const hasVariants = p.getElementsByTagName("variant").length > 0;
                    const isVariationBase = variationMarker === "true" || productType.includes("variation") || getTagText(p, "variation-base-product") === "true" || getTagText(p, "is-variation-base") === "true" || hasVariants;
                    if (isVariationBase) {
                        variationBaseProducts[sku] = true;
                    }

                    let bundledNodes = p.getElementsByTagName("bundled-products");
                    if (bundledNodes.length > 0) {
                        let comps = bundledNodes[0].getElementsByTagName("bundled-product");
                        if (comps.length > 0) {
                            if (!bundles[sku]) bundles[sku] = [];
                            for (let comp of comps) {
                                let compSku = comp.getAttribute("product-id");
                                if (compSku) bundles[sku].push(compSku.toUpperCase());
                            }
                        }
                    }
                }

                for (let a of cDoc.getElementsByTagName("category-assignment")) {
                    let sku = a.getAttribute("product-id").toUpperCase();
                    let catId = a.getAttribute("category-id");
                    assignedSkus.add(sku);

                    if (!categoryAssignmentsMap[brandCat][catId]) categoryAssignmentsMap[brandCat][catId] = new Set();
                    categoryAssignmentsMap[brandCat][catId].add(sku);

                    // Check #4 Strict Mapping
                    if (brandCat === "Natura" && (catId === "promocao-da-semana" || catId === "LISTA_01")) prohibitedState.Natura.add(sku);
                    if (brandCat === "Avon" && (catId === "desconto-progressivo" || catId === "lista-01")) prohibitedState.Avon.add(sku);
                    if (brandCat === "ML" && (catId === "promocao-da-semana" || catId === "desconto-progressivo")) prohibitedState.ML.add(sku);

                    if (brandCat !== "ML") {
                        if (catId.startsWith("LISTA_") || catId.startsWith("lista-")) {
                            if (!xmlLists[catId]) xmlLists[catId] = new Set();
                            xmlLists[catId].add(sku);
                        }
                    }

                    if (getTagText(a, "primary-flag") === "true") primarySkus.add(sku);
                }

                for (let sku of assignedSkus) {
                    if (!primarySkus.has(sku)) {
                        if (!catMissingPrimary[sku]) catMissingPrimary[sku] = [];
                        catMissingPrimary[sku].push(brandCat);
                    }
                }
            }

            await Auditor.updateUI(85, "Cruzamento Analítico", "Aplicando regras de Herança do Salesforce (Apenas Ativos)...");

            Auditor.data = [];
            Auditor.activeFilters = new Set();
            
            // Estrutura de Contagem V10.0 (Total, Natura, Avon)
            const stats = {};
            ['price', 'list', 'ml', 'margin', 'logic', 'missing', 'primary', 'bundle', 'cross', 'offline', 'job', 'searchable'].forEach(k => {
                stats[k] = { total: 0, natura: 0, avon: 0 };
            });

            let jobErrorBySku = {};
            mlJobRulesCount.forEach(rule => {
                let mCat = rule.motherCatId;
                let mlCat = rule.mlCatId;
                let setM = categoryAssignmentsMap.Natura[mCat] || categoryAssignmentsMap.Avon[mCat] || new Set();
                let setML = categoryAssignmentsMap.ML[mlCat] || new Set();
                
                let diffSkus = new Set();
                setM.forEach(s => { if (!setML.has(s)) diffSkus.add(s); });
                setML.forEach(s => { if (!setM.has(s)) diffSkus.add(s); });
                
                diffSkus.forEach(s => {
                    if (!jobErrorBySku[s]) jobErrorBySku[s] = [];
                    jobErrorBySku[s].push(`JOB NÃO RODOU (A Categoria ML ${mlCat} divergiu do espelho da Marca Mãe)`);
                });
            });

            let allSkus = new Set([...Object.keys(pricesXML), ...Object.keys(excelPrices), ...Object.keys(catMissingPrimary), ...Object.keys(bundles), ...Object.keys(jobErrorBySku)]);
            for (let l in xmlLists) xmlLists[l].forEach(s => allSkus.add(s));

            allSkus.forEach(sku => {
                if (!sku.startsWith("NATBRA-") && !sku.startsWith("AVNBRA-")) return;

                let pE = excelPrices[sku];
                let isOffline = (onlineStatus[sku] !== true);
                let isOnActiveGrade = !!pE;

                if (isOffline && !isOnActiveGrade) return;

                let e = [], c = "";
                let brand = sku.startsWith("NATBRA-") ? "Natura" : "Avon";

                let pX = pricesXML[sku] && pricesXML[sku][brand] ? pricesXML[sku][brand] : {};
                let pML = pricesXML[sku] && pricesXML[sku].ML ? pricesXML[sku].ML : {};

                let pxDE = pX.DE || 0;
                let pxPOR = pX.POR || 0;

                // HERANÇA (INHERITANCE) 
                let sfMlDE = pML.DE !== undefined ? pML.DE : pxDE;
                let sfMlPOR = pML.POR !== undefined ? pML.POR : pxPOR;

                if (isOffline && isOnActiveGrade) {
                    e.push("PRODUTO OFFLINE (Ação Comercial Exigida)");
                    c = "row-error";
                    stats.offline.total++;
                    if (brand === "Natura") stats.offline.natura++; else stats.offline.avon++;
                }

                if (!isOffline) {
                    if (bundles[sku]) {
                        let offlineComps = [];
                        let missingPriceComps = [];

                        bundles[sku].forEach(compSku => {
                            // Ignore variation base products no check de bundle (offline + preço)
                            if (variationBaseProducts[compSku]) return;

                            if (onlineStatus[compSku] !== true) { offlineComps.push(compSku); }

                            const compPriceBrand = pricesXML[compSku] && pricesXML[compSku][brand];
                            const compDE = compPriceBrand?.DE || 0;
                            const compPOR = compPriceBrand?.POR || 0;

                            if (compDE <= 0 || compPOR <= 0) {
                                missingPriceComps.push(compSku);
                            }
                        });

                        if (offlineComps.length > 0 || missingPriceComps.length > 0) {
                            let details = [];
                            if (offlineComps.length > 0) details.push(`Comp. Offline: ${offlineComps.join(', ')}`);
                            if (missingPriceComps.length > 0) details.push(`Comp. sem preço (DE/POR): ${missingPriceComps.join(', ')}`);

                            e.push(`BUNDLE QUEBRADO (${details.join(' ; ')})`);
                            c = "row-error";
                            stats.bundle.total++;
                            if (brand === "Natura") stats.bundle.natura++; else stats.bundle.avon++;
                        }
                    }

                    let hasNaturaPrice = pricesXML[sku] && pricesXML[sku]['Natura'] && (pricesXML[sku]['Natura'].DE || pricesXML[sku]['Natura'].POR);
                    let hasAvonPrice = pricesXML[sku] && pricesXML[sku]['Avon'] && (pricesXML[sku]['Avon'].DE || pricesXML[sku]['Avon'].POR);

                    if (brand === "Natura" && hasAvonPrice) { e.push("MARCA CRUZADA (NAT no Pricebook AVN)"); c = "row-error"; stats.cross.total++; stats.cross.natura++; }
                    if (brand === "Avon" && hasNaturaPrice) { e.push("MARCA CRUZADA (AVN no Pricebook NAT)"); c = "row-error"; stats.cross.total++; stats.cross.avon++; }

                    let shouldCompareExcel = (brand === "Natura" && excelHasNatura) || (brand === "Avon" && excelHasAvon);
                    if (shouldCompareExcel) {
                        if (pE) {
                            if (!pxDE && !pxPOR) { e.push("FALTA NO SF (PREÇO)"); c = "row-error"; stats.price.total++; if (brand === "Natura") stats.price.natura++; else stats.price.avon++; }
                            else {
                                if (Math.abs(pE.DE - pxDE) > 0.01 && pE.DE > 0) { e.push(`DIVERGE SF (DE: R$${pE.DE.toFixed(2)})`); c = "row-error"; stats.price.total++; if (brand === "Natura") stats.price.natura++; else stats.price.avon++; }
                                if (Math.abs(pE.POR - pxPOR) > 0.01 && pE.POR > 0) { e.push(`DIVERGE SF (POR: R$${pE.POR.toFixed(2)})`); c = "row-error"; stats.price.total++; if (brand === "Natura") stats.price.natura++; else stats.price.avon++; }
                            }
                        }

                        // Check #12: Searchable vs Visible Implantação (Ignora se for SKU Técnico/Caixa Alta)
                        if (pE && pE.VISIBLE && !isTechnicalSku[sku]) {
                            let visLabel = pE.VISIBLE;
                            let isVisibleInExcel = (visLabel === "SIM");
                            let isHiddenInExcel = (visLabel === "NÃO" || visLabel === "NAO");
                            let isSearchableInXml = searchableStatus[sku] === true;

                            if (isVisibleInExcel && !isSearchableInXml) {
                                e.push(`DIVERGE SEARCHABLE (Excel SIM vs SF false)`);
                                c = "row-error";
                                stats.searchable.total++;
                                if (brand === "Natura") stats.searchable.natura++; else stats.searchable.avon++;
                            } else if (isHiddenInExcel && isSearchableInXml) {
                                e.push(`DIVERGE SEARCHABLE (Excel NÃO vs SF true)`);
                                c = "row-error";
                                stats.searchable.total++;
                                if (brand === "Natura") stats.searchable.natura++; else stats.searchable.avon++;
                            }
                        }

                        Object.keys(excelLists).forEach(listId => {
                            let listBelongsToSku = (brand === "Natura" && listId.startsWith("LISTA_")) || (brand === "Avon" && listId.startsWith("lista-"));
                            if (listBelongsToSku) {
                                let inExcel = excelLists[listId].has(sku);
                                if (inExcel) {
                                    let listExistsInXml = !!xmlLists[listId];
                                    if (!listExistsInXml) { e.push(`LISTA INEXISTENTE NO SF (${listId})`); c = "row-error"; stats.list.total++; if (brand === "Natura") stats.list.natura++; else stats.list.avon++; }
                                    else {
                                        let inXml = xmlLists[listId].has(sku);
                                        if (!inXml) { e.push(`FALTA NO SF (${listId})`); c = "row-error"; stats.list.total++; if (brand === "Natura") stats.list.natura++; else stats.list.avon++; }
                                    }
                                }
                            }
                        });
                    }

                    if (pxDE || pxPOR || sfMlDE || sfMlPOR || catMissingPrimary[sku]) {
                        if (pxPOR === 0 && pxDE !== 0) { e.push("FALTA PREÇO POR"); c = c || "row-error"; stats.missing.total++; if (brand === "Natura") stats.missing.natura++; else stats.missing.avon++; }
                        if (pxDE === 0 && pxPOR !== 0) { e.push("FALTA PREÇO DE"); c = c || "row-error"; stats.missing.total++; if (brand === "Natura") stats.missing.natura++; else stats.missing.avon++; }
                        if (pxPOR > pxDE && pxDE > 0) { e.push("POR > DE"); c = c || "row-error"; stats.logic.total++; if (brand === "Natura") stats.logic.natura++; else stats.logic.avon++; }

                        let isPromoSkuBrand = (pxPOR < pxDE && pxPOR > 0);
                        let isPromoSkuML = (sfMlPOR < sfMlDE && sfMlPOR > 0);

                        if (isPromoSkuBrand && brand === 'Natura' && prohibitedState.Natura.has(sku)) {
                            e.push("CONFLITO PROG (Natura)"); c = c || "row-alert"; stats.margin.total++; stats.margin.natura++;
                        }
                        if (isPromoSkuBrand && brand === 'Avon' && prohibitedState.Avon.has(sku)) {
                            e.push("CONFLITO PROG (Avon)"); c = c || "row-alert"; stats.margin.total++; stats.margin.avon++;
                        }
                        if (isPromoSkuML && prohibitedState.ML.has(sku)) {
                            e.push("CONFLITO PROG (Minha Loja)"); c = c || "row-alert"; stats.margin.total++; if (brand === "Natura") stats.margin.natura++; else stats.margin.avon++;
                        }

                        if ((pxPOR > 0 || sfMlPOR > 0) && Math.abs(pxPOR - sfMlPOR) > 0.01) {
                            e.push(`DIVERGE ML (POR: Marca R$${pxPOR.toFixed(2)} vs ML R$${sfMlPOR.toFixed(2)})`);
                            c = c || "row-error";
                            stats.ml.total++; if (brand === "Natura") stats.ml.natura++; else stats.ml.avon++;
                        }
                        if ((pxDE > 0 || sfMlDE > 0) && Math.abs(pxDE - sfMlDE) > 0.01) {
                            e.push(`DIVERGE ML (DE: Marca R$${pxDE.toFixed(2)} vs ML R$${sfMlDE.toFixed(2)})`);
                            c = c || "row-error";
                            stats.ml.total++; if (brand === "Natura") stats.ml.natura++; else stats.ml.avon++;
                        }

                        let missingCats = catMissingPrimary[sku] || [];
                        missingCats.forEach(catBrand => { e.push(`FALTA CAT PRIMÁRIA (${catBrand})`); c = c || "row-error"; stats.primary.total++; if (brand === "Natura") stats.primary.natura++; else stats.primary.avon++; });
                    }
                    
                    if (jobErrorBySku[sku]) {
                        jobErrorBySku[sku].forEach(err => {
                            e.push(err);
                            c = "row-error";
                            stats.job.total++; if (brand === "Natura") stats.job.natura++; else stats.job.avon++;
                        });
                    }
                } // Fim if (!isOffline)

                if (e.length) Auditor.data.push({ SKU: sku, Marca: brand, O: pxPOR || pxDE || 0, ML: sfMlPOR || sfMlDE || 0, E: e.join(" | "), C: c });
            });

            await Auditor.updateUI(100, "Concluído!", "Renderizando Dashboard...");

            if (Auditor.data.length === 0) {
                document.getElementById('audAllGoodMsg').classList.remove('hidden-el');
            } else {
                document.getElementById('audDashboard').classList.remove('hidden-el');

                const upCard = (key, data) => {
                    const card = document.getElementById('card-' + key);
                    const labelMap = { 
                        price: 'countPrice', list: 'countList', ml: 'countMl', margin: 'countMargin',
                        logic: 'countLogic', missing: 'countMissing', primary: 'countPrimary',
                        bundle: 'countBundle', cross: 'countCross', offline: 'countOffline', 
                        job: 'countJob', searchable: 'countSearchable'
                    };
                    const mainId = labelMap[key];
                    
                    if (data.total === 0) {
                        card.classList.add('hidden-el');
                    } else {
                        card.classList.remove('hidden-el');
                        document.getElementById(mainId).innerText = data.total;
                        document.getElementById(mainId + 'Nat').innerText = data.natura;
                        document.getElementById(mainId + 'Avn').innerText = data.avon;
                    }
                };

                Object.keys(stats).forEach(k => upCard(k, stats[k]));
                // Salva estatísticas para o Agente de IA
                Auditor.lastStats = stats;
                PricingAI.run(stats);

                // Inicializa filtros com tudo selecionado (Regra V11.6)
                Auditor.activeBrands = new Set(['Natura', 'Avon']);
                Auditor.activeFilters = new Set(Object.keys(stats).filter(k => stats[k].total > 0));

                Auditor.renderDashboard();

                // Salva resultados para o Google Chat
                Auditor.lastResults = {
                    total: Auditor.data.length,
                    brand: document.getElementById('syncDetectedBrand') ? document.getElementById('syncDetectedBrand').innerText : "Multimarca",
                    aiInsight: PricingAI.lastInsight, // NOVO: Insight do Agente AI
                    errors: {
                        price: stats.price.total, list: stats.list.total, ml: stats.ml.total, margin: stats.margin.total,
                        logic: stats.logic.total, missing: stats.missing.total, primary: stats.primary.total,
                        bundle: stats.bundle.total, cross: stats.cross.total, offline: stats.offline.total, job: stats.job.total, searchable: stats.searchable.total
                    },
                    criticalList: Auditor.data.map(r => ({ sku: r.SKU, error: r.E }))
                };

                Auditor.renderDashboard();

                Auditor.pbFile = null;
                Auditor.catFiles = [];
                Auditor.excelFiles = [];
            }

            setTimeout(() => {
                document.getElementById('audStatusArea').classList.add('hidden-el');
                document.getElementById('audProcessBtn').classList.remove('hidden-el');
            }, 1000);

        } catch (e) {
            App.showToast("Erro crítico do motor principal: " + e.message, "error");
            console.error(e);
            document.getElementById('audStatusArea').classList.add('hidden-el');
            document.getElementById('audProcessBtn').classList.remove('hidden-el');
        }
    },

    exportReport: () => {
        const activeBrands = Auditor.activeBrands;
        const activeFilters = Auditor.activeFilters;
        let filteredData = Auditor.data.filter(r => Auditor.checkFilterMatch(r, activeBrands, activeFilters));
        
        if (filteredData.length === 0) return App.showToast("Nada para exportar com os filtros atuais.", "warning");

        const ws = XLSX.utils.json_to_sheet(filteredData.map(r => ({
            SKU: r.SKU,
            Marca: r.Marca,
            Preco_Base: r.O,
            Preco_ML: r.ML,
            Erros: r.E
        })));

        const wb = XLSX.utils.book_new();
        XLSX.utils.book_append_sheet(wb, ws, "Auditoria_V11_6");

        let filename = `Auditoria_${[...activeBrands].join('_')}_${activeFilters.size}Tipos.xlsx`;
        XLSX.writeFile(wb, filename);
    }
};

let pbEl = document.getElementById('audPbInput');
if (pbEl) pbEl.addEventListener('change', (e) => Auditor.handleUpload(e, 'pb'));

let catEl = document.getElementById('audCatInput');
if (catEl) catEl.addEventListener('change', (e) => Auditor.handleUpload(e, 'cat'));

let exEl = document.getElementById('audExcelInput');
if (exEl) exEl.addEventListener('change', (e) => Auditor.handleUpload(e, 'excel'));

let btnProcess = document.getElementById('audProcessBtn');
if (btnProcess) btnProcess.addEventListener('click', Auditor.processData);

let btnExport = document.getElementById('audExportBtn');
if (btnExport) btnExport.addEventListener('click', Auditor.exportReport);

document.getElementById('syncDownloadBtn').addEventListener('click', Sync.downloadXML);
document.getElementById('syncChatBtn').addEventListener('click', () => {
    if (Sync.lastResults) App.sendToGoogleChat(Sync.lastResults, 'sync');
});

// Listener para Chat da Auditoria (V11.6 - Alta Transparência)
document.getElementById('audChatBtn').addEventListener('click', () => {
    const activeBrands = Auditor.activeBrands;
    const activeFilters = Auditor.activeFilters;
    const filteredData = Auditor.data.filter(r => Auditor.checkFilterMatch(r, activeBrands, activeFilters));

    if (activeBrands.size === 0) return App.showToast("Selecione ao menos uma marca para reportar.", "warning");

    // Mapeamento de categorias para palavras-chave
    const labelMap = { 
        price: ['DIVERGE SF (DE', 'DIVERGE SF (POR', 'FALTA NO SF (PREÇO)'],
        list: ['FALTA NO SF', 'LISTA INEXISTENTE'],
        ml: ['DIVERGE ML'],
        margin: ['CONFLITO PROG'],
        logic: ['POR > DE'],
        missing: ['FALTA PREÇO'],
        primary: ['FALTA CAT PRIMÁRIA'],
        bundle: ['BUNDLE QUEBRADO'],
        cross: ['MARCA CRUZADA'],
        offline: ['PRODUTO OFFLINE'],
        job: ['JOB NÃO RODOU'],
        searchable: ['DIVERGE SEARCHABLE']
    };

    const allCategories = Object.keys(labelMap);
    const filteredErrors = {};
    const filteredStatsForAI = {}; // Formato que o PricingAI espera
    const fullBrandData = Auditor.data.filter(r => activeBrands.has(r.Marca));

    allCategories.forEach(f => {
        const keywords = labelMap[f];
        const natCount = fullBrandData.filter(r => r.Marca === 'Natura' && keywords.some(k => r.E.includes(k))).length;
        const avnCount = fullBrandData.filter(r => r.Marca === 'Avon' && keywords.some(k => r.E.includes(k))).length;
        const totalCount = natCount + avnCount;

        // Regra de Reporte V11.6 (Foco total em Erros):
        // Só incluímos no report se tiver erro (> 0) E se o filtro estiver ativo.
        if (totalCount > 0 && activeFilters.has(f)) {
            filteredErrors[f] = totalCount;
            filteredStatsForAI[f] = { total: totalCount, natura: natCount, avon: avnCount };
        } else {
            // Se não tem erro ou está silenciado, garantimos que a IA também não foque nisso
            filteredStatsForAI[f] = { total: 0, natura: 0, avon: 0 };
        }
    });

    // GERA INSIGHT DINÂMICO PARA A IA (Baseado apenas no que realmente vai no report)
    const dynamicAiInsight = PricingAI.generateInsight(filteredStatsForAI);

    const reportData = {
        total: fullBrandData.length,
        brand: [...activeBrands].join(' & '),
        errors: filteredErrors,
        criticalList: filteredData.map(r => ({ sku: r.SKU, error: r.E })),
        aiInsight: dynamicAiInsight
    };

    App.sendToGoogleChat(reportData, 'auditor');
});