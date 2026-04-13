// ==========================================
// js/utils.js - CAIXA DE FERRAMENTAS GLOBAIS
// ==========================================

// Função para pausar a tela (criar a sensação de loading fluido)
const sleep = ms => new Promise(r => setTimeout(r, ms));

// Leitura segura de XML (Ignora a sujeira de Namespaces do Salesforce, ex: ns0:)
const getTagText = (node, tag) => {
    let els = node.getElementsByTagNameNS("*", tag);
    if (!els.length) els = node.getElementsByTagName(tag);
    return els.length ? els[0].textContent.trim() : null;
};

// Scanner Dinâmico de Colunas (Para a Grade de Ativação)
// Procura as colunas "DE", "POR" e descobre onde estão os SKUs da Natura ou Avon
const findDynamicColumns = (ws) => {
    let skuCol = -1, deCol = -1, porCol = -1, visibleCol = -1, seloCol = -1;
    if(!ws || !ws['!ref']) return { skuCol: 2, deCol: 26, porCol: 27, visibleCol: -1, seloCol: -1 }; // Fallback
    
    const range = XLSX.utils.decode_range(ws['!ref']);
    for(let r = range.s.r; r <= Math.min(range.e.r, 50); r++) { // Lê as 50 primeiras linhas
        for(let c = range.s.c; c <= range.e.c; c++) {
            const cell = ws[XLSX.utils.encode_cell({r, c})];
            if (!cell || !cell.v) continue;
            const val = String(cell.v).trim().toUpperCase();
            
            if (val === 'DE') deCol = c;
            if (val === 'POR') porCol = c;
            if (val === 'VISIBLE IMPLANTAÇÃO' || val === 'VISIBLE' || val === 'VISIBILIDADE') visibleCol = c;
            if (val === 'SELO' || val === 'FLAG' || val === 'MARKETING') seloCol = c;

            // Se achar um SKU legítimo, crava a coluna como a coluna de SKU
            if (skuCol === -1 && (val.startsWith('NATBRA-') || val.startsWith('AVNBRA-'))) {
                skuCol = c;
            }
        }
    }
    return { 
        skuCol: skuCol !== -1 ? skuCol : 2, 
        deCol: deCol !== -1 ? deCol : 26, 
        porCol: porCol !== -1 ? porCol : 27,
        visibleCol: visibleCol,
        seloCol: seloCol
    };
};

// Scanner Dinâmico Simples (Para as abas de LISTA_XX)
// Nas listas só nos interessa a coluna do SKU, ignoramos preço
const findSkuColumnOnly = (ws) => {
     let skuCol = -1;
     if(!ws || !ws['!ref']) return 2; // Fallback
     const range = XLSX.utils.decode_range(ws['!ref']);
     for(let r = range.s.r; r <= Math.min(range.e.r, 50); r++) {
         for(let c = range.s.c; c <= range.e.c; c++) {
             const cell = ws[XLSX.utils.encode_cell({r, c})];
             if (!cell || !cell.v) continue;
             const val = String(cell.v).trim().toUpperCase();
             if (val.startsWith('NATBRA-') || val.startsWith('AVNBRA-')) { 
                 skuCol = c; 
                 break; 
             }
         }
         if(skuCol !== -1) break;
     }
     return skuCol !== -1 ? skuCol : 2;
};