/**
 * js/volumetria.js - MÓDULO 4: VOLUMETRIA C/ IA (V11.6 - FULL)
 * Responsável pelo cruzamento de dados entre Imagens (OCR) e XML do Catálogo.
 */

const Volumetria = {
    results: [],
    catalogData: {}, // Mapa SKU -> { name, friendly, desc, longDesc, volDetected: [] }
    isProcessing: false,

    init: () => {
        console.log("[Volumetria] Inicializando módulo...");
        const imgInput = document.getElementById('volImageInput');
        const xmlInput = document.getElementById('volXmlInput');
        
        if (imgInput) imgInput.addEventListener('change', (e) => Volumetria.handleImageUpload(e));
        if (xmlInput) xmlInput.addEventListener('change', (e) => Volumetria.handleXmlUpload(e));
        
        console.log("[Volumetria] Eventos registrados.");
    },

    // 1. PROCESSAMENTO DE XML
    handleXmlUpload: async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        const status = document.getElementById('volXmlStatus');
        status.innerText = "Lendo catálogo...";
        status.classList.replace('text-slate-400', 'text-indigo-500');

        const reader = new FileReader();
        reader.onload = async (event) => {
            const parser = new DOMParser();
            const xmlDoc = parser.parseFromString(event.target.result, "text/xml");
            const products = xmlDoc.getElementsByTagName("product");

            Volumetria.catalogData = {};
            let count = 0;

            for (let i = 0; i < products.length; i++) {
                const p = products[i];
                const sku = p.getAttribute("product-id");
                if (!sku) continue;

                const displayName = p.getElementsByTagName("display-name")[0]?.textContent || "";
                const friendlyName = p.getElementsByTagName("friendly-name")[0]?.textContent || "";
                const description = p.getElementsByTagName("description")[0]?.textContent || "";
                const longDescription = p.getElementsByTagName("long-description")[0]?.textContent || "";

                const allText = `${displayName} ${friendlyName} ${description} ${longDescription}`;
                const volDetected = Volumetria.extractVolume(allText);

                Volumetria.catalogData[sku] = {
                    name: displayName,
                    friendly: friendlyName,
                    desc: description,
                    long: longDescription,
                    expectedVol: volDetected
                };
                count++;
            }

            status.innerText = `Catálogo OK: ${count} produtos mapeados.`;
            App.showToast(`Catálogo processado com ${count} produtos.`, "info");
        };
        reader.readAsText(file);
    },

    // 2. EXTRAÇÃO DE VOLUMETRIA (REGEX)
    extractVolume: (text) => {
        // Busca padrões como 100ml, 50g, 200 ml, 1.5l, etc.
        const regex = /(\d+(?:[\.,]\d+)?)\s*(ml|g|kg|l|oz|fl\.oz|unidade|un)\b/gi;
        const matches = [];
        let match;
        while ((match = regex.exec(text)) !== null) {
            matches.push(`${match[1].replace(',', '.')}${match[2].toLowerCase()}`);
        }
        return [...new Set(matches)]; // Unique values
    },

    // 3. PROCESSAMENTO DE IMAGENS
    handleImageUpload: async (e) => {
        const files = Array.from(e.target.files);
        if (files.length === 0) return;
        if (Object.keys(Volumetria.catalogData).length === 0) {
            App.showToast("Por favor, carregue o XML do Catálogo primeiro!", "warning");
            e.target.value = '';
            return;
        }

        Volumetria.isProcessing = true;
        document.getElementById('volStatusArea').classList.remove('hidden-el');
        document.getElementById('volResultArea').classList.add('hidden-el');
        
        Volumetria.results = [];
        let completed = 0;

        for (const file of files) {
            const result = await Volumetria.analyzeImage(file);
            Volumetria.results.push(result);
            completed++;
            Volumetria.updateUI((completed / files.length) * 100, `Analisando ${completed} de ${files.length} (IA Vision)...`);
        }

        Volumetria.renderResults();
        Volumetria.isProcessing = false;
        e.target.value = '';
    },

    analyzeImage: (file) => {
        return new Promise((resolve) => {
            const reader = new FileReader();
            reader.onload = (event) => {
                const img = new Image();
                img.onload = async () => {
                    const canvas = document.createElement('canvas');
                    const ctx = canvas.getContext('2d');
                    canvas.width = img.width;
                    canvas.height = img.height;
                    ctx.drawImage(img, 0, 0);

                    // Validação de Resolução (600x600 solicitado)
                    const resOk = img.width >= 600 && img.height >= 600;
                    const resolution = `${img.width}x${img.height}`;

                    // Proporção 1:1
                    const ratio = img.width / img.height;
                    const ratioOk = Math.abs(ratio - 1) <= 0.05;

                    // Heurística de Fundo
                    const bgOk = Volumetria.checkBackground(ctx, canvas.width, canvas.height);

                    // SKU Extraction (ignora sufixos como _1, _v2, etc.)
                    // Ex: NATBRA-1234_1.jpg -> NATBRA-1234
                    const sku = file.name.split('_')[0].split('.')[0].toUpperCase();
                    const catalogInfo = Volumetria.catalogData[sku];

                    // Pre-processamento para melhorar OCR em 600x600
                    const processedCanvas = document.createElement('canvas');
                    const pCtx = processedCanvas.getContext('2d');
                    // Upscale 2x para ajudar o Tesseract com fontes pequenas
                    processedCanvas.width = img.width * 2;
                    processedCanvas.height = img.height * 2;
                    pCtx.filter = 'grayscale(100%) contrast(150%)';
                    pCtx.drawImage(img, 0, 0, processedCanvas.width, processedCanvas.height);

                    // OCR IA (Tesseract)
                    let ocrResult = [];
                    try {
                        const { data: { text } } = await Tesseract.recognize(processedCanvas, 'eng');
                        ocrResult = Volumetria.extractVolume(text);
                    } catch (e) {
                        console.error("[OCR Error]", e);
                    }

                    // Comparação
                    let compliant = resOk && ratioOk && bgOk && !!catalogInfo;
                    let volMatch = "N/A";
                    let volStatus = "info";

                    if (catalogInfo) {
                        const expected = catalogInfo.expectedVol;
                        if (expected.length > 0 && ocrResult.length > 0) {
                            const intersect = expected.filter(v => ocrResult.includes(v));
                            if (intersect.length > 0) {
                                volMatch = "✅ Match (" + intersect.join(', ') + ")";
                                volStatus = "success";
                            } else {
                                volMatch = `🚩 Conflito: XML(${expected[0]}) vs Foto(${ocrResult[0]})`;
                                volStatus = "error";
                                compliant = false;
                            }
                        } else if (expected.length > 0) {
                            volMatch = `⚠️ XML pende(${expected[0]}), Foto não legível`;
                            volStatus = "warning";
                            compliant = false; // Se o XML exige e a foto não mostra, não está em compliance
                        }
                    }

                    resolve({
                        name: file.name,
                        sku: sku,
                        preview: event.target.result,
                        resolution: resolution,
                        resOk: resOk,
                        ratio: ratio.toFixed(2),
                        ratioOk: ratioOk,
                        bgOk: bgOk,
                        volCompare: volMatch,
                        volStatus: volStatus,
                        catalogFound: !!catalogInfo,
                        compliant: compliant
                    });
                };
                img.src = event.target.result;
            };
            reader.readAsDataURL(file);
        });
    },

    checkBackground: (ctx, w, h) => {
        const points = [[5, 5], [w - 5, 5], [5, h - 5], [w - 5, h - 5], [w / 2, 5], [w / 2, h - 5], [5, h / 2], [w - 5, h / 2]];
        let whiteCount = 0;
        points.forEach(([x, y]) => {
            const pixel = ctx.getImageData(x, y, 1, 1).data;
            if ((pixel[0] > 245 && pixel[1] > 245 && pixel[2] > 245) || pixel[3] < 10) whiteCount++;
        });
        return whiteCount >= 5;
    },

    updateUI: (pct, txt) => {
        const bar = document.getElementById('volProgressBar');
        const status = document.getElementById('volStatusText');
        if (bar) bar.style.width = pct + "%";
        if (status) status.innerText = txt;
    },

    renderResults: () => {
        const tbody = document.getElementById('volTableBody');
        tbody.innerHTML = '';

        let okCount = 0;
        let errCount = 0;

        Volumetria.results.forEach(res => {
            if (res.compliant) okCount++; else errCount++;

            const volColors = {
                success: 'text-emerald-500 bg-emerald-50 dark:bg-emerald-900/20',
                warning: 'text-amber-500 bg-amber-50 dark:bg-amber-900/20',
                error: 'text-rose-500 bg-rose-50 dark:bg-rose-900/20',
                info: 'text-slate-400 bg-slate-50 dark:bg-slate-900/20'
            };

            const row = document.createElement('tr');
            row.className = "hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors";
            row.innerHTML = `
                <td class="px-8 py-4"><img src="${res.preview}" class="w-16 h-16 rounded-xl object-cover border dark:border-slate-700 shadow-sm"></td>
                <td class="px-8 py-4">
                    <div class="font-black text-slate-800 dark:text-white">${res.sku}</div>
                    <div class="text-[10px] uppercase font-bold ${res.catalogFound ? 'text-indigo-400' : 'text-rose-400'}">
                        ${res.catalogFound ? 'Encontrado no XML' : 'SKU Faltante no XML'}
                    </div>
                </td>
                <td class="px-8 py-4">
                    <span class="font-mono text-xs ${res.resOk ? 'text-emerald-500' : 'text-rose-500'} font-bold">${res.resolution}</span>
                </td>
                <td class="px-8 py-4">
                    <span class="font-mono text-xs ${res.ratioOk ? 'text-emerald-500' : 'text-rose-500'} font-bold">${res.ratio}</span>
                </td>
                <td class="px-8 py-4">
                    <span class="px-2 py-1 rounded-lg text-[10px] font-black ${res.bgOk ? 'text-emerald-500 bg-emerald-50' : 'text-rose-500 bg-rose-50'} dark:bg-slate-900/50 uppercase tracking-widest">
                        ${res.bgOk ? 'Fundo Branco' : 'Fundo Colorido'}
                    </span>
                </td>
                <td class="px-8 py-4 text-right">
                    <div class="inline-block px-3 py-1.5 rounded-xl text-[10px] font-black uppercase tracking-tight shadow-sm ${volColors[res.volStatus]}">
                        ${res.volCompare}
                    </div>
                </td>
            `;
            tbody.appendChild(row);
        });

        document.getElementById('volOkCount').innerText = okCount;
        document.getElementById('volErrCount').innerText = errCount;

        setTimeout(() => {
            document.getElementById('volStatusArea').classList.add('hidden-el');
            document.getElementById('volResultArea').classList.remove('hidden-el');
            App.showToast("Análise de volumetria concluída!", "info");
        }, 500);
    },

    reset: () => {
        Volumetria.results = [];
        Volumetria.catalogData = {};
        document.getElementById('volResultArea').classList.add('hidden-el');
        document.getElementById('volTableBody').innerHTML = '';
        document.getElementById('volImageInput').value = '';
        document.getElementById('volXmlInput').value = '';
        const status = document.getElementById('volXmlStatus');
        status.innerText = "Nenhum arquivo carregado";
        status.classList.replace('text-indigo-500', 'text-slate-400');
    }
};

Volumetria.init();
