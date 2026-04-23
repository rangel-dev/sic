// ==========================================
// js/sync.js - MÓDULO 2: MERCHANDISING SYNC
// ==========================================

const Sync = {
    catalogId: '',
    finalDeltaXml: '',
    stats: { lists: 0, add: 0, rem: 0 },

    updateUI: async (pct, txt, det) => { 
        document.getElementById('syncProgressBar').style.width = pct + "%"; 
        document.getElementById('syncStatusText').innerText = txt; 
        document.getElementById('syncStepDetails').innerText = det; 
        await sleep(50); 
    },

    checkReady: (e) => { 
        if (e && e.target && e.target.files[0]) {
            const file = e.target.files[0];
            const zone = e.target.parentElement;
            const icon = zone.querySelector('i');
            const title = zone.querySelector('h3');
            const desc = zone.querySelector('p');
            
            zone.classList.remove('border-slate-200', 'dark:border-slate-700');
            zone.classList.add('!border-emerald-500', 'dark:!border-emerald-400', 'bg-emerald-50', 'dark:bg-emerald-900/20');
            if (icon) {
                icon.setAttribute('data-lucide', 'check-circle');
                icon.className = 'text-emerald-500 dark:text-emerald-400 w-5 h-5';
            }
            if (title) title.innerText = "Lido com Sucesso";
            if (desc) desc.innerText = file.name;
            if (window.lucide) lucide.createIcons();
        }

        if(document.getElementById('syncExcelInput').files[0] && document.getElementById('syncXmlInput').files[0]) {
            document.getElementById('syncProcessBtn').classList.remove('hidden-el'); 
        }
    },

    processData: async () => {
        document.getElementById('syncStepUploads').classList.add('hidden-el'); 
        document.getElementById('syncProcessBtn').classList.add('hidden-el'); 
        document.getElementById('syncStatusArea').classList.remove('hidden-el'); 
        document.getElementById('syncResultArea').classList.add('hidden-el'); 
        
        try { 
            const excelFile = document.getElementById('syncExcelInput').files[0]; 
            const xmlFile = document.getElementById('syncXmlInput').files[0]; 

            // --- TRAVA DE SEGURANÇA: 10 MINUTOS (V11.5) --- - DESATIVADO
            // const now = Date.now();
            // const xmlModified = xmlFile.lastModified;
            // if ((now - xmlModified) < 600000) { // Menor que 10 min
            //     throw new Error(`O XML do Salesforce é muito recente (${Math.round((now - xmlModified)/1000/60)} min). \nPor segurança, aguarde o período de estabilidade de 10 minutos após o download do Salesforce para processar.`);
            // }
            
            await Sync.updateUI(15, "Lendo Excel", "Mapeando SKUs para descobrir a Marca...");
            const excelData = await excelFile.arrayBuffer(); 
            await new Promise(r => setTimeout(r, 10)); // Yield UI
            const wb = XLSX.read(new Uint8Array(excelData), { 
                type: 'array', cellStyles: false, cellFormula: false, cellHTML: false, sheetStubs: false 
            }); 
            
            // Auto-Brand Discovery
            let natCount = 0, avnCount = 0;
            wb.SheetNames.forEach((sheetName, idx) => {
                if (wb.Workbook && wb.Workbook.Sheets && wb.Workbook.Sheets[idx] && wb.Workbook.Sheets[idx].Hidden) return;
                const match = sheetName.match(/^LISTA[-_\s]*0*(\d+)/i);
                if (match || sheetName === "GRADE DE ATIVAÇÃO") {
                    const ws = wb.Sheets[sheetName]; 
                    if(!ws['!ref']) return;
                    const skuColList = findSkuColumnOnly(ws); 
                    const range = XLSX.utils.decode_range(ws['!ref']);
                    let emptyStreak = 0;
                    for (let r = range.s.r; r <= range.e.r; r++) {
                        const cell = ws[XLSX.utils.encode_cell({ r: r, c: skuColList })]; 
                        const sku = cell ? String(cell.v).trim().toUpperCase() : "";
                        if (!sku) { emptyStreak++; if (emptyStreak >= 50) break; } 
                        else { 
                            emptyStreak = 0;
                            if(sku.startsWith('NATBRA-')) natCount++;
                            if(sku.startsWith('AVNBRA-')) avnCount++;
                        }
                    }
                }
            });

            if(natCount === 0 && avnCount === 0) throw new Error("Nenhum SKU válido encontrado no Excel.");
            const detectedBrand = natCount >= avnCount ? 'natura' : 'avon';
            Sync.catalogId = detectedBrand === 'natura' ? 'natura-br-storefront-catalog' : 'avon-br-storefront-catalog';
            const isAvon = detectedBrand === 'avon'; 
            const prefix = isAvon ? 'lista-' : 'LISTA_'; 
            const brandName = isAvon ? 'Avon' : 'Natura';

            // UI Brand Feedback
            document.getElementById('syncDetectedBrand').innerText = brandName;
            const box = document.getElementById('syncResultBox');
            box.className = `border p-6 rounded-xl mb-6 text-center smooth-transition dark:border-slate-700 dark:bg-slate-800 ${!isAvon ? 'bg-orange-50 border-orange-200' : 'bg-purple-50 border-purple-200'}`;
            
            await Sync.updateUI(30, "Lendo Grade", "Extraindo Vitrines, Visibilidade e Selos...");
            
            // Mapeando a Verdade do Excel
            const excelLists = {}; 
            const excelGrade = {}; // SKU -> { de, por, visible, selo }
            
            for(let idx = 0; idx < wb.SheetNames.length; idx++) {
                const sheetName = wb.SheetNames[idx];
                if (wb.Workbook && wb.Workbook.Sheets && wb.Workbook.Sheets[idx] && wb.Workbook.Sheets[idx].Hidden) continue;
                
                const ws = wb.Sheets[sheetName]; 
                if(!ws['!ref']) continue;

                // Caso 1: Aba de Vitrine (LISTA_XX)
                const match = sheetName.match(/^LISTA[-_\s]*0*(\d+)/i);
                if (match) {
                    const cleanId = prefix + match[1].padStart(2, '0');
                    if(!excelLists[cleanId]) excelLists[cleanId] = new Set();
                    const skuColList = findSkuColumnOnly(ws); 
                    const range = XLSX.utils.decode_range(ws['!ref']);
                    let emptyS = 0;
                    for (let r = range.s.r; r <= range.e.r; r++) {
                        const cell = ws[XLSX.utils.encode_cell({ r: r, c: skuColList })]; 
                        const sku = cell ? String(cell.v).trim().toUpperCase() : "";
                        if (!sku) { emptyS++; if (emptyS >= 50) break; } 
                        else { 
                            emptyS = 0;
                            if (sku.startsWith(isAvon ? 'AVNBRA-' : 'NATBRA-')) excelLists[cleanId].add(sku);
                        }
                    }
                }

                // Caso 2: Grade de Ativação (Atributos)
                if (sheetName === "GRADE DE ATIVAÇÃO") {
                    const { skuCol, deCol, porCol, visibleCol, seloCol } = findDynamicColumns(ws);
                    const range = XLSX.utils.decode_range(ws['!ref']);
                    let emptyG = 0;
                    for (let r = range.s.r; r <= range.e.r; r++) {
                        const cell = ws[XLSX.utils.encode_cell({ r: r, c: skuCol })]; 
                        const sku = cell ? String(cell.v).trim().toUpperCase() : "";
                        if (!sku) { emptyG++; if (emptyG >= 50) break; } 
                        else { 
                            emptyG = 0;
                            if (sku.startsWith(isAvon ? 'AVNBRA-' : 'NATBRA-')) {
                                const cDE = ws[XLSX.utils.encode_cell({ r: r, c: deCol })];
                                const cPOR = ws[XLSX.utils.encode_cell({ r: r, c: porCol })];
                                const cVIS = visibleCol !== -1 ? ws[XLSX.utils.encode_cell({ r: r, c: visibleCol })] : null;
                                const cSELO = seloCol !== -1 ? ws[XLSX.utils.encode_cell({ r: r, c: seloCol })] : null;

                                const de = cDE && !isNaN(parseFloat(cDE.v)) ? parseFloat(cDE.v) : 0;
                                const por = cPOR && !isNaN(parseFloat(cPOR.v)) ? parseFloat(cPOR.v) : 0;

                                excelGrade[sku] = {
                                    de, por,
                                    visible: cVIS ? String(cVIS.v).trim().toUpperCase() : "SIM",
                                    selo: cSELO ? String(cSELO.v).trim() : ""
                                };

                                // Promoção Automática
                                if (por > 0 && por < de && detectedBrand === 'natura') {
                                    const promoId = 'promocao-exclusiva';
                                    if (!excelLists[promoId]) excelLists[promoId] = new Set();
                                    excelLists[promoId].add(sku);
                                }
                            }
                        }
                    }
                }
            }

            await Sync.updateUI(60, "Lendo Base XML", "Analisando visibilidade e status atual no Salesforce...");
            
            const xmlText = await xmlFile.text(); 
            const xmlDoc = new DOMParser().parseFromString(xmlText, "text/xml"); 
            const currentXmlLists = {}; 
            const unfinishedSkus = new Set(); // CAIXA ALTA LOCK
            const skusInXml = new Set();

            // Sinc de Categorias (Assignments)
            const assignments = xmlDoc.getElementsByTagName("category-assignment"); 
            for(let a of assignments) { 
                const catId = a.getAttribute("category-id"); 
                const sku = a.getAttribute("product-id").toUpperCase();
                if(catId.startsWith(prefix) || catId === 'promocao-exclusiva') { 
                    if(!currentXmlLists[catId]) currentXmlLists[catId] = new Set(); 
                    currentXmlLists[catId].add(sku); 
                } 
            } 

            // Sinc de Produtos (Atributos e Segurança)
            const products = xmlDoc.getElementsByTagName("product");
            for (let p of products) {
                const sku = p.getAttribute("product-id").toUpperCase();
                skusInXml.add(sku);

                // TRAVA CAIXA ALTA (Cadastro Incompleto)
                const nameEls = Array.from(p.getElementsByTagName("display-name")).concat(Array.from(p.getElementsByTagName("name")));
                const namesToTest = nameEls.map(el => (el.textContent || "").trim()).filter(t => t.length > 0);
                const pageUrl = (getTagText(p, "page-url") || "").trim();
                if (pageUrl) namesToTest.push(pageUrl);

                if (namesToTest.length > 0 && namesToTest.every(n => n === n.toUpperCase() && /[A-Z]/.test(n))) {
                    unfinishedSkus.add(sku);
                }
            }

            await Sync.updateUI(85, "Calculando Delta", "Gerando XML de alta precisão...");
            
            let deltaNodes = ""; 
            Sync.stats = { lists: 0, add: 0, rem: 0 }; 

            // 1. Delta de Categorias
            const allLists = new Set([...Object.keys(excelLists), ...Object.keys(currentXmlLists)]);
            Sync.stats.lists = allLists.size;
            for (const listId of allLists) {
                const eSkus = excelLists[listId] || new Set();
                const xSkus = currentXmlLists[listId] || new Set();
                eSkus.forEach(sku => { if(!xSkus.has(sku)) { deltaNodes += `\n    <category-assignment category-id="${listId}" product-id="${sku}"/>`; Sync.stats.add++; } });
                xSkus.forEach(sku => { if(!eSkus.has(sku)) { deltaNodes += `\n    <category-assignment category-id="${listId}" product-id="${sku}" mode="delete"/>`; Sync.stats.rem++; } });
            }

            // 2. Delta de Produtos (Vibrancy & Security)
            const allSkus = new Set([...skusInXml, ...Object.keys(excelGrade)]);
            for (const sku of allSkus) {
                if (!sku.startsWith(isAvon ? 'AVNBRA-' : 'NATBRA-')) continue;

                const grade = excelGrade[sku];
                const nodeStr = [];

                if (grade) {
                    // SKU na Grade -> ONLINE
                    nodeStr.push(`        <online-flag>true</online-flag>`);
                    
                    // Lógica Searchable (Visible + Trava Caixa Alta)
                    const isVisibleInExcel = grade.visible === "SIM" || grade.visible === "S" || grade.visible === "YES";
                    const isUnfinished = unfinishedSkus.has(sku);
                    const searchable = (isVisibleInExcel && !isUnfinished) ? "true" : "false";
                    nodeStr.push(`        <searchable-flag>${searchable}</searchable-flag>`);

                    // Selos (4 Campos JSON)
                    if (grade.selo) {
                        const sTxt = grade.selo.replace(/"/g, '&quot;');
                        const sJson = `{"Name":"${sTxt}","Color":"#edf0ff","Border":"radius"}`;
                        const rJson = `[{"tag":"${sTxt}","type":"product","color":"#edf0ff","border":"radius","date_start":"","date_end":"","priority":"1","values":"${sTxt}"}]`;
                        
                        nodeStr.push(`        <custom-attributes>`);
                        nodeStr.push(`            <custom-attribute attribute-id="natg_preferencialProductSlot">${sJson}</custom-attribute>`);
                        nodeStr.push(`            <custom-attribute attribute-id="natg_productSlotsRules">${rJson}</custom-attribute>`);
                        nodeStr.push(`            <custom-attribute attribute-id="natg_preferencialProductSlotCbSite">${sJson}</custom-attribute>`);
                        nodeStr.push(`            <custom-attribute attribute-id="natg_productSlotsRulesCbSite">${rJson}</custom-attribute>`);
                        nodeStr.push(`        </custom-attributes>`);
                    }
                } else if (skusInXml.has(sku)) {
                    // SKU no XML mas fora da Grade -> OFFLINE
                    nodeStr.push(`        <online-flag>false</online-flag>`);
                }

                if (nodeStr.length > 0) {
                    deltaNodes += `\n    <product product-id="${sku}">\n${nodeStr.join('\n')}\n    </product>`;
                }
            }

            Sync.finalDeltaXml = `<?xml version="1.0" encoding="UTF-8"?>\n<catalog xmlns="http://www.demandware.com/xml/impex/catalog/2006-10-31" catalog-id="${Sync.catalogId}">\n${deltaNodes}\n</catalog>`; 
            
            await Sync.updateUI(100, "Finalizado!", "Download disponível abaixo.");
            document.getElementById('syncListCount').innerText = Sync.stats.lists; 
            document.getElementById('syncAddCount').innerText = Sync.stats.add; 
            document.getElementById('syncRemCount').innerText = Sync.stats.rem; 
            
            Sync.lastResults = { brand: brandName, lists: Sync.stats.lists, add: Sync.stats.add, rem: Sync.stats.rem };
            setTimeout(() => { 
                document.getElementById('syncStatusArea').classList.add('hidden-el'); 
                document.getElementById('syncResultArea').classList.remove('hidden-el'); 
            }, 800); 

        } catch (err) { 
            App.showToast("Processamento Abortado: " + err.message, "error"); 
            console.error(err);
            document.getElementById('syncStatusArea').classList.add('hidden-el'); 
            document.getElementById('syncStepUploads').classList.remove('hidden-el'); 
            document.getElementById('syncProcessBtn').classList.remove('hidden-el'); 
        } 
    },

    downloadXML: () => {
        const a = document.createElement('a'); 
        a.href = window.URL.createObjectURL(new Blob([Sync.finalDeltaXml], { type: 'text/xml' })); 
        a.download = `CATALOG_DELTA_${Sync.catalogId}.xml`; 
        a.click();
    }
};

// Escutadores de Eventos
document.getElementById('syncExcelInput').addEventListener('change', Sync.checkReady); 
document.getElementById('syncXmlInput').addEventListener('change', Sync.checkReady);
document.getElementById('syncProcessBtn').addEventListener('click', Sync.processData);
document.getElementById('syncDownloadBtn').addEventListener('click', Sync.downloadXML);
document.getElementById('syncChatBtn').addEventListener('click', () => {
    if (Sync.lastResults) App.sendToGoogleChat(Sync.lastResults, 'sync');
});