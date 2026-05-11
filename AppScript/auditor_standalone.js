/**
 * SIC Standalone Auditor Pro - Business Logic & API Integration
 * Optimized for handling 100MB+ Salesforce Catalog XMLs
 */

// --- CONFIGURATION ---
const CLIENT_ID = 'SEU_CLIENT_ID_AQUI.apps.googleusercontent.com'; // User must replace this
const SCOPES = 'https://www.googleapis.com/auth/spreadsheets';
const DISCOVERY_DOCS = ["https://sheets.googleapis.com/$discovery/rest?version=v4"];

let tokenClient;
let gapiInited = false;
let gisInited = false;
let targetIds = new Set();
let finalResults = [];
let accessToken = null;

// --- INITIALIZATION ---

function gapiLoaded() {
    gapi.load('client', intializeGapiClient);
}

async function intializeGapiClient() {
    await gapi.client.init({
        discoveryDocs: DISCOVERY_DOCS,
    });
    gapiInited = true;
    checkBeforeStart();
}

function gisLoaded() {
    tokenClient = google.accounts.oauth2.initTokenClient({
        client_id: CLIENT_ID,
        scope: SCOPES,
        callback: '', // defined later
    });
    gisInited = true;
    checkBeforeStart();
}

// Auto-load SDKs if not already loading
if (typeof gapi === 'undefined') {
    const s = document.createElement('script');
    s.src = "https://apis.google.com/js/api.js";
    s.onload = gapiLoaded;
    document.body.appendChild(s);
}
if (typeof google === 'undefined') {
    const s = document.createElement('script');
    s.src = "https://accounts.google.com/gsi/client";
    s.onload = gisLoaded;
    document.body.appendChild(s);
}

function checkBeforeStart() {
    if (gapiInited && gisInited) {
        document.getElementById('loginBtn').disabled = false;
    }
}

// --- AUTHENTICATION ---

function handleAuthClick() {
    tokenClient.callback = async (resp) => {
        if (resp.error !== undefined) {
            throw (resp);
        }
        accessToken = resp.access_token;
        onAuthSuccess();
    };

    if (gapi.client.getToken() === null) {
        tokenClient.requestAccessToken({prompt: 'consent'});
    } else {
        tokenClient.requestAccessToken({prompt: ''});
    }
}

function onAuthSuccess() {
    document.getElementById('loginBtn').style.display = 'none';
    document.getElementById('userInfo').style.display = 'flex';
    document.getElementById('mainCard').style.opacity = '1';
    document.getElementById('mainCard').style.pointerEvents = 'all';
    addLog("Autenticação Google concluída com sucesso.", "success");
}

// --- UI & LOGS ---

function addLog(msg, type = "info") {
    const logWindow = document.getElementById('logWindow');
    const entry = document.createElement('div');
    entry.className = 'log-entry';
    const now = new Date().toLocaleTimeString();
    entry.innerHTML = `<span class="log-time">[${now}]</span> <span style="color: ${type === 'error' ? '#ef4444' : type === 'success' ? '#10b981' : 'inherit'}">${msg}</span>`;
    logWindow.appendChild(entry);
    logWindow.scrollTop = logWindow.scrollHeight;
}

function updateProgress(percent, text) {
    document.getElementById('statusContainer').style.display = 'block';
    document.getElementById('progressFill').style.width = percent + '%';
    document.getElementById('progressPercent').innerText = Math.round(percent) + '%';
    document.getElementById('statusText').innerText = text;
}

// --- SPREADSHEET LOGIC ---

async function fetchIdsFromSheet() {
    const spreadsheetId = document.getElementById('spreadsheetId').value.trim();
    if (!spreadsheetId) {
        alert("Por favor, insira o ID da planilha.");
        return;
    }

    addLog("Buscando IDs na planilha...");
    try {
        const response = await gapi.client.sheets.spreadsheets.values.get({
            spreadsheetId: spreadsheetId,
            range: 'A1:Z500', // Scan a reasonable area
        });

        const range = response.result;
        if (!range || !range.values || range.values.length === 0) {
            addLog("Nenhum dado encontrado na planilha.", "error");
            return;
        }

        targetIds = new Set();
        range.values.flat().forEach(val => {
            const clean = val.toString().trim();
            if (clean) targetIds.add(clean);
        });

        addLog(`Capturados ${targetIds.size} IDs únicos para validação.`, "success");
    } catch (err) {
        addLog("Erro ao acessar planilha: " + err.result.error.message, "error");
    }
}

// --- XML PROCESSING (The Heavy Lifting) ---

const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');

dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.classList.add('dragover'); });
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    handleFile(e.dataTransfer.files[0]);
});
fileInput.addEventListener('change', (e) => handleFile(e.target.files[0]));

async function handleFile(file) {
    if (!file) return;
    if (targetIds.size === 0) {
        alert("Carregue os IDs da planilha primeiro!");
        return;
    }

    addLog(`Iniciando leitura do arquivo: ${file.name} (${(file.size / 1024 / 1024).toFixed(2)} MB)`);
    updateProgress(10, "Lendo arquivo...");

    const reader = new FileReader();
    reader.onload = async (e) => {
        const xmlString = e.target.result;
        updateProgress(30, "Limpando XML e extraindo tags...");
        
        // Use a background task to not freeze the UI completely
        setTimeout(() => processXML(xmlString), 100);
    };
    reader.readAsText(file);
}

function processXML(xmlString) {
    try {
        const parser = new DOMParser();
        updateProgress(40, "Fazendo parse DOM (isso pode demorar em arquivos de 100MB+)...");
        const xmlDoc = parser.parseFromString(xmlString, "text/xml");
        
        const catMap = new Map();
        updateProgress(60, "Mapeando associações de produtos...");
        
        // Fast mapping using querySelectorAll
        const assignments = xmlDoc.querySelectorAll('category-assignment');
        addLog(`Encontrados ${assignments.length} assignments.`);
        
        assignments.forEach(asgn => {
            const sku = asgn.getAttribute('product-id');
            const catId = asgn.getAttribute('category-id');
            if (sku && catId) {
                if (!catMap.has(catId)) catMap.set(catId, new Set());
                catMap.get(catId).add(sku.toUpperCase());
            }
        });

        updateProgress(80, "Validando regras de categorização...");
        const categories = xmlDoc.querySelectorAll('category');
        finalResults = [];
        let ruleCount = 0;

        categories.forEach(cat => {
            const childId = cat.getAttribute('category-id');
            if (!targetIds.has(childId)) return;

            const ruleElements = cat.querySelectorAll('categorization-rule');
            const motherIds = new Set();

            ruleElements.forEach(rule => {
                const conditions = rule.querySelectorAll('categorization-condition');
                conditions.forEach(cond => {
                    if (cond.getAttribute('attribute-id') === 'CategoryId') {
                        const valEl = cond.querySelector('attribute-value');
                        if (valEl) {
                            const val = valEl.textContent.trim();
                            const mId = val.includes(',') ? val.split(',')[1].trim() : val;
                            if (mId !== childId) motherIds.add(mId);
                        }
                    }
                });
            });

            if (motherIds.size > 0) {
                ruleCount++;
                const childSkus = catMap.get(childId) || new Set();
                const unionMotherSkus = new Set();
                motherIds.forEach(mId => {
                    const mSkus = catMap.get(mId) || new Set();
                    mSkus.forEach(s => unionMotherSkus.add(s));
                });

                const onlyInChild = [...childSkus].filter(x => !unionMotherSkus.has(x));
                const onlyInMother = [...unionMotherSkus].filter(x => !childSkus.has(x));
                const diffTotal = onlyInChild.length + onlyInMother.length;
                
                finalResults.push({
                    childId,
                    motherIds: [...motherIds].join(', '),
                    status: diffTotal === 0 ? 'OK' : 'DIVERGENTE',
                    diffTotal,
                    childCount: childSkus.size,
                    motherCount: unionMotherSkus.size,
                    onlyInMother: onlyInMother.slice(0, 50),
                    onlyInChild: onlyInChild.slice(0, 50)
                });
            }
        });

        updateProgress(100, "Concluído!");
        addLog(`Auditoria finalizada. ${ruleCount} categorias com regras processadas.`, "success");
        renderResults();
    } catch (err) {
        addLog("Erro no processamento: " + err.message, "error");
        console.error(err);
    }
}

function renderResults() {
    const tbody = document.getElementById('resultsTableBody');
    tbody.innerHTML = '';
    document.getElementById('resultsSection').style.display = 'block';

    finalResults.forEach(res => {
        const tr = document.createElement('tr');
        const isOk = res.status === 'OK';
        tr.innerHTML = `
            <td><strong style="color: var(--primary)">${res.childId}</strong><br><small>${res.childCount} SKUs</small></td>
            <td><small>${res.motherIds}</small><br><small>Esperado: ${res.motherCount} SKUs</small></td>
            <td><span class="status-pill ${isOk ? 'pill-ok' : 'pill-error'}">${res.status}</span></td>
            <td>
                ${isOk ? '-' : `<strong style="color: var(--danger)">${res.diffTotal} divergências</strong>`}
                ${!isOk ? `<div style="font-size: 10px; color: var(--text-muted); margin-top: 5px;">
                    ${res.onlyInMother.length ? `Faltam: ${res.onlyInMother.slice(0,3).join(', ')}...` : ''}
                    ${res.onlyInChild.length ? `<br>Sobram: ${res.onlyInChild.slice(0,3).join(', ')}...` : ''}
                </div>` : ''}
            </td>
        `;
        tbody.appendChild(tr);
    });
}

// --- WRITE BACK TO SHEET ---

async function writeResultsToSheet() {
    const spreadsheetId = document.getElementById('spreadsheetId').value.trim();
    if (!spreadsheetId) return;

    addLog("Gravando resultados na planilha...");
    const values = [
        ["Categoria Filha", "Origem (Mães)", "Status", "Qtd XML", "Qtd Esperada", "Divergência", "Faltam (Sample)", "Sobram (Sample)"]
    ];

    finalResults.forEach(r => {
        values.push([
            r.childId, r.motherIds, r.status, r.childCount, r.motherCount, r.diffTotal, 
            r.onlyInMother.join(', '), r.onlyInChild.join(', ')
        ]);
    });

    try {
        // 1. Create the sheet if it doesn't exist (optional, but here we just try to update a sheet named 'Relatorio_Standalone')
        // For simplicity in this POC, we write to a specific range.
        const body = { values: values };
        
        // We'll try to update 'Relatorio_Standalone!A1'
        // If the sheet doesn't exist, this might fail, so in production we'd create it first.
        await gapi.client.sheets.spreadsheets.values.update({
            spreadsheetId: spreadsheetId,
            range: 'Relatorio_Standalone!A1',
            valueInputOption: 'RAW',
            resource: body,
        });

        addLog("Planilha atualizada com sucesso!", "success");
        alert("Resultados gravados na aba 'Relatorio_Standalone'!");
    } catch (err) {
        addLog("Erro ao gravar na planilha. Verifique se a aba 'Relatorio_Standalone' existe.", "error");
        console.error(err);
    }
}
