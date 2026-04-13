// ==========================================
// js/gerador.js - MÓDULO 1: GESTÃO DE PREÇOS
// ==========================================

const Gerador = {
    brand: '',
    data: [],
    mode: 'full', // 'full' ou 'delta'
    basePrices: {},
    IDS: { 
        natura: { de: "br-natura-brazil-list-prices", por: "br-natura-brazil-sale-prices" }, 
        avon: { de: "brl-avon-brazil-list-prices", por: "brl-avon-brazil-sale-prices" }, 
        ml: { de: "br-cb-brazil-list-prices", por: "br-cb-brazil-sale-prices" } 
    },

    selectMode: (m) => {
        Gerador.mode = m;
        document.getElementById('genModeSelector').classList.add('hidden-el');
        document.getElementById('genStepUpload').classList.remove('hidden-el');
        
        const title = document.getElementById('genUploadTitle');
        const xmlZone = document.getElementById('genXmlUploadZone');
        const processBtn = document.getElementById('genProcessBtn');
        
        if (m === 'full') {
            title.innerText = "Modo: Grade Full";
            xmlZone.classList.add('hidden-el');
        } else {
            title.innerText = "Modo: Ajustes (Delta)";
            xmlZone.classList.remove('hidden-el');
        }
        
        document.getElementById('genExcelInput').value = '';
        document.getElementById('genXmlInput').value = '';
        processBtn.classList.add('hidden-el');
        
        const resetZone = (id) => {
            let el = document.getElementById(id);
            if(!el) return;
            el.classList.remove('!border-emerald-500', 'bg-emerald-50', 'dark:!border-emerald-400', 'dark:bg-emerald-900/30');
            el.classList.add('border-slate-200', 'dark:border-slate-700');
            let icon = el.children[1].querySelector('i');
            if(icon && icon.getAttribute('data-lucide') === 'check-check') {
                icon.setAttribute('data-lucide', id.includes('Xml') ? 'file-code-2' : 'file-spreadsheet');
                icon.className = id.includes('Xml') ? 'text-emerald-500 dark:text-emerald-400 w-5 h-5' : 'text-indigo-500 dark:text-indigo-400 w-5 h-5';
            }
        };
        resetZone('genXmlUploadZone');
        resetZone('genExcelUploadZone');
        if (window.lucide) lucide.createIcons();
    },

    resetMode: () => {
        document.getElementById('genStepUpload').classList.add('hidden-el');
        document.getElementById('genModeSelector').classList.remove('hidden-el');
    },

    updateUI: async (pct, txt, det) => { 
        document.getElementById('genProgressBar').style.width = pct + "%"; 
        document.getElementById('genStatusText').innerText = txt; 
        document.getElementById('genStepDetails').innerText = det; 
        await sleep(50); 
    },

    checkReady: (e, type) => {
        const file = e.target.files[0];
        if (!file) return;

        const zoneId = type === 'xml' ? 'genXmlUploadZone' : 'genExcelUploadZone';
        const zone = document.getElementById(zoneId);
        
        zone.classList.remove('border-slate-200', 'dark:border-slate-700');
        zone.classList.add('!border-emerald-500', 'dark:!border-emerald-400', 'bg-emerald-50', 'dark:bg-emerald-900/30');
        
        const icon = zone.children[1].querySelector('i');
        if (icon) {
            icon.setAttribute('data-lucide', 'check-check');
            icon.className = 'text-emerald-500 dark:text-emerald-400 w-5 h-5';
            if (window.lucide) lucide.createIcons();
        }

        const excelHasFile = document.getElementById('genExcelInput').files.length > 0;
        const xmlHasFile = document.getElementById('genXmlInput').files.length > 0;
        const processBtn = document.getElementById('genProcessBtn');

        if (Gerador.mode === 'full' && excelHasFile) {
            processBtn.classList.remove('hidden-el');
        } else if (Gerador.mode === 'delta' && excelHasFile && xmlHasFile) {
            processBtn.classList.remove('hidden-el');
        } else {
            processBtn.classList.add('hidden-el');
        }
    },

    processData: async () => {
        const excelFile = document.getElementById('genExcelInput').files[0];
        const xmlFile = document.getElementById('genXmlInput').files[0];
        
        document.getElementById('genStepUpload').classList.add('hidden-el');
        document.getElementById('genStatusArea').classList.remove('hidden-el'); 
        document.getElementById('genStepResult').classList.add('hidden-el'); 
        
        try {
            Gerador.data = [];
            Gerador.basePrices = {};

            // 1. DELTA MODE: Parse XML Base
            if (Gerador.mode === 'delta') {
                await Gerador.updateUI(15, "Lendo XML Atual", "Construindo Base de Preços (Delta)...");
                const xmlText = await xmlFile.text();
                await new Promise(r => setTimeout(r, 10)); // Yield UI
                
                const xmlDoc = new DOMParser().parseFromString(xmlText, "text/xml");
                const priceTables = xmlDoc.getElementsByTagName("price-table");
                
                for (let pt of priceTables) {
                    const sku = pt.getAttribute("product-id").toUpperCase();
                    const pbId = pt.parentElement.parentElement.getElementsByTagName("header")[0].getAttribute("pricebook-id");
                    const amtText = pt.getElementsByTagName("amount")[0]?.textContent;
                    if (amtText) {
                        const amt = parseFloat(amtText);
                        if (!Gerador.basePrices[sku]) Gerador.basePrices[sku] = { de: 0, por: 0 };
                        
                        if (pbId.includes("list-prices")) Gerador.basePrices[sku].de = amt;
                        if (pbId.includes("sale-prices")) Gerador.basePrices[sku].por = amt;
                    }
                }
            }

            // 2. EXCEL PARSE
            await Gerador.updateUI(40, "Lendo Planilhas Excel", "Extraindo Grade(s) de Novos Preços...");
            
            const excelFiles = Array.from(document.getElementById('genExcelInput').files);
            Gerador.brands = new Set();
            let skippedCount = 0;

            for (let i = 0; i < excelFiles.length; i++) {
                const currentExcelFile = excelFiles[i];
                const pctBase = 40 + (i * (40 / excelFiles.length));
                await Gerador.updateUI(pctBase, `Processando Arquivo ${i+1}/${excelFiles.length}`, `Lendo: ${currentExcelFile.name}...`);
                
                await new Promise((resolve, reject) => {
                    const reader = new FileReader(); 
                    reader.onload = async (ev) => { 
                        try {
                            await new Promise(r => setTimeout(r, 10)); // Yield UI
                            const wb = XLSX.read(new Uint8Array(ev.target.result), { 
                                type: 'array', cellStyles: false, cellFormula: false, cellHTML: false, sheetStubs: false 
                            }); 
                            
                            const sheetIdx = wb.SheetNames.indexOf("GRADE DE ATIVAÇÃO");
                            if (sheetIdx === -1) throw new Error("Aba 'GRADE DE ATIVAÇÃO' não foi encontrada no arquivo " + currentExcelFile.name);
                            if (wb.Workbook && wb.Workbook.Sheets && wb.Workbook.Sheets[sheetIdx] && wb.Workbook.Sheets[sheetIdx].Hidden) {
                                throw new Error("A aba 'GRADE DE ATIVAÇÃO' está OCULTA no arquivo " + currentExcelFile.name);
                            }

                            const ws = wb.Sheets["GRADE DE ATIVAÇÃO"]; 
                            await Gerador.updateUI(pctBase + 10, "Calculando Diferenças", "Mapeando SKUs...");
                            
                            const { skuCol, deCol, porCol } = findDynamicColumns(ws); 
                            const range = XLSX.utils.decode_range(ws['!ref']); 
                            
                            let natCount = 0, avnCount = 0;
                            let emptyStreak = 0;
                            for (let row = range.s.r; row <= range.e.r; row++) { 
                                const cSKU = ws[XLSX.utils.encode_cell({ r: row, c: skuCol })]; 
                                const sku = cSKU ? String(cSKU.v).trim().toUpperCase() : ""; 
                                if (!sku) {
                                    emptyStreak++; if (emptyStreak >= 50) break;
                                } else {
                                    emptyStreak = 0;
                                    if(sku.startsWith('NATBRA-')) natCount++;
                                    if(sku.startsWith('AVNBRA-')) avnCount++;
                                }
                            }

                            if(natCount === 0 && avnCount === 0) throw new Error("Nenhum SKU Natura/Avon válido no arquivo " + currentExcelFile.name);
                            const fileBrand = natCount >= avnCount ? 'natura' : 'avon';
                            Gerador.brands.add(fileBrand);
                            
                            let emptyStreakExt = 0;
                            for (let row = range.s.r; row <= range.e.r; row++) { 
                                if (row % 1000 === 0) await new Promise(r => setTimeout(r, 0));
                                
                                const cSKU = ws[XLSX.utils.encode_cell({ r: row, c: skuCol })]; 
                                const cDE = ws[XLSX.utils.encode_cell({ r: row, c: deCol })]; 
                                const cPOR = ws[XLSX.utils.encode_cell({ r: row, c: porCol })]; 
                                const sku = cSKU ? String(cSKU.v).trim().toUpperCase() : ""; 
                                
                                if (!sku) {
                                    emptyStreakExt++; if (emptyStreakExt >= 50) break;
                                } else {
                                    emptyStreakExt = 0;
                                    if (sku && (sku.startsWith('NATBRA-') || sku.startsWith('AVNBRA-'))) { 
                                        // O auto-discovery local do arquivo nos protege contra contaminação
                                        if (fileBrand === 'natura' && sku.startsWith('AVNBRA-')) continue; 
                                        if (fileBrand === 'avon' && sku.startsWith('NATBRA-')) continue; 
                                        
                                        const de = cDE && !isNaN(parseFloat(cDE.v)) ? parseFloat(cDE.v) : 0; 
                                        const por = cPOR && !isNaN(parseFloat(cPOR.v)) ? parseFloat(cPOR.v) : 0; 
                                        
                                        if (de > 0 || por > 0) {
                                            if (Gerador.mode === 'delta') {
                                                const bp = Gerador.basePrices[sku];
                                                if (bp && bp.de === de && bp.por === por) {
                                                    skippedCount++; // Exatamente o mesmo preço
                                                } else {
                                                    Gerador.data.push({ sku, de, por }); // Diferente ou Novo
                                                }
                                            } else {
                                                Gerador.data.push({ sku, de, por });
                                            }
                                        }
                                    }
                                }
                            } 
                            resolve();
                        } catch(err) {
                            reject(err);
                        }
                    };
                    reader.readAsArrayBuffer(currentExcelFile);
                });
            }

            // Geração Concluída
            await Gerador.updateUI(100, "Concluído!", "Mapeamento Multi-Marca Concluído.");
            
            const brandArr = Array.from(Gerador.brands);
            const brandStr = brandArr.length === 2 ? "Multi (Natura + Avon)" : (brandArr[0] === 'natura' ? 'Natura' : 'Avon');
            document.getElementById('genDetectedBrand').innerText = brandStr;
            
            const countTxt = Gerador.data.length + (Gerador.mode === 'delta' ? ` (Ignorados pelo Delta: ${skippedCount})` : '');
            document.getElementById('genSkuCount').innerText = countTxt;
            
            const box = document.getElementById('genResultBox');
            const icon = document.getElementById('genResultIcon');
            const title = document.getElementById('genResultTitle');
            const sub = document.getElementById('genResultSubtitle');
            
            // UI Dinâmica para Multi-Marca
            const isMulti = brandArr.length > 1;
            box.className = `border p-8 rounded-xl mb-6 text-center smooth-transition dark:bg-slate-800 dark:border-slate-700 ${isMulti ? 'bg-indigo-50 border-indigo-200' : (brandArr[0] === 'natura' ? 'bg-orange-50 border-orange-200' : 'bg-purple-50 border-purple-200')}`;
            icon.className = `w-8 h-8 dark:text-emerald-400 ${isMulti ? 'text-indigo-500' : (brandArr[0] === 'natura' ? 'text-orange-500' : 'text-purple-500')}`;
            title.className = `text-3xl font-black tracking-tight dark:text-slate-100 ${isMulti ? 'text-indigo-700' : (brandArr[0] === 'natura' ? 'text-orange-700' : 'text-purple-700')}`;
            sub.className = `font-bold text-sm mb-1 uppercase tracking-widest dark:text-slate-400 ${isMulti ? 'text-indigo-900' : (brandArr[0] === 'natura' ? 'text-orange-900' : 'text-purple-900')}`;
            
            title.innerText = Gerador.mode === 'delta' ? "Delta Consolidado" : "Grade Unificada";
            sub.innerText = "Pricebooks XML Prontos para SFCC";

            setTimeout(() => { 
                document.getElementById('genStatusArea').classList.add('hidden-el'); 
                document.getElementById('genStepResult').classList.remove('hidden-el'); 
            }, 800); 

        } catch(err) {
            App.showToast("Erro durante processamento: " + err.message, "error"); 
            document.getElementById('genStatusArea').classList.add('hidden-el'); 
            document.getElementById('genStepUpload').classList.remove('hidden-el');
        }
    },

    downloadXML: () => {
        const ml = Gerador.IDS.ml; 
        const block = (id, t, activeSkus) => {
            const tableData = Gerador.data.filter(r => r[t] > 0 && activeSkus(r.sku)).map(r => `<price-table product-id="${r.sku}"><amount quantity="1">${r[t].toFixed(2)}</amount></price-table>`).join('');
            if (!tableData) return ''; // Se não houver produtos pra esta tabela, não gera o XML inútil
            return `\n<pricebook><header pricebook-id="${id}"><currency>BRL</currency><online-flag>true</online-flag></header><price-tables>${tableData}</price-tables></pricebook>`;
        }
        
        let xmlParts = [];

        // Monta os blocos de Natura de/por se a Natura existir
        if (Gerador.brands.has('natura')) {
            const n = Gerador.IDS.natura;
            const filterNat = (sku) => sku.startsWith('NATBRA-');
            xmlParts.push(block(n.de, 'de', filterNat));
            xmlParts.push(block(n.por, 'por', filterNat));
        }

        // Monta os blocos de Avon de/por se a Avon existir
        if (Gerador.brands.has('avon')) {
            const a = Gerador.IDS.avon;
            const filterAvn = (sku) => sku.startsWith('AVNBRA-');
            xmlParts.push(block(a.de, 'de', filterAvn));
            xmlParts.push(block(a.por, 'por', filterAvn));
        }

        // Pela regra de negócio, Minha Loja (ML) deve englobar TUDO o que for exportado
        const filterAll = (sku) => true; 
        xmlParts.push(block(ml.de, 'de', filterAll));
        xmlParts.push(block(ml.por, 'por', filterAll));

        const xmlFileStr = `<?xml version="1.0" encoding="UTF-8"?>\n<pricebooks xmlns="http://www.demandware.com/xml/impex/pricebook/2006-10-31">${xmlParts.join('')}\n</pricebooks>`; 
        
        // Nome dinâmico para o XML
        const brandArr = Array.from(Gerador.brands);
        const nameType = brandArr.length === 2 ? 'MULTIBRAND' : brandArr[0].toUpperCase();
        
        const a = document.createElement('a'); 
        a.href = window.URL.createObjectURL(new Blob([xmlFileStr], { type: 'text/xml' })); 
        a.download = `PRICEBOOK_${nameType}_${Gerador.mode === 'delta' ? 'DELTA' : 'FULL'}_SYNC.xml`; 
        a.click();
    }
};

document.getElementById('genBtn').addEventListener('click', Gerador.downloadXML);