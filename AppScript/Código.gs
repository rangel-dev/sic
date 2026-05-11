/**
 * Categorization Rules Auditor - V2.0.0 | GOLD EDITION
 * A primeira versão estável de produção com Dual-Sync e Brand Isolation.
 */

function doGet() {
  return HtmlService.createHtmlOutputFromFile('Upload')
      .setTitle('Categorization Rules Auditor')
      .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
}

function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('📦 SIC Auditor')
    .addItem('🚀 Abrir Auditor Multi-Brand', 'showUploadDialog')
    .addToUi();
}

/**
 * Exibe o diálogo de upload com a interface premium
 */
function showUploadDialog() {
  const html = HtmlService.createHtmlOutputFromFile('Upload')
    .setWidth(1000)
    .setHeight(700)
    .setTitle('Categorization Rules Auditor | V2.0.0 GOLD');
  SpreadsheetApp.getUi().showModalDialog(html, ' ');
}

/**
 * Retorna os IDs das categorias que estão na planilha para o navegador
 */
function getIdsFromSheet() {
  try {
    const naturaIds = [];
    const avonIds = [];
    
    // 1. Carrega Planilha Natura (Atual)
    const ssNatura = SpreadsheetApp.getActiveSpreadsheet();
    const sheetNatura = ssNatura.getSheetByName("Categorias") || ssNatura.getSheets()[0];
    const valsNatura = sheetNatura.getDataRange().getValues();
    
    for (let i = 0; i < valsNatura.length; i++) {
      for (let j = 0; j < valsNatura[i].length; j++) {
        let val = valsNatura[i][j];
        if (val) {
          val = val.toString().trim();
          if (val !== "" && val !== "undefined") naturaIds.push(val);
        }
      }
    }

    // 2. Carrega Planilha Avon (Externa)
    try {
      const avonId = '1zaPTjg-VO8X86QSmAg81dM1_x2lhGk7MHtKBnD1lrqA';
      const ssAvon = SpreadsheetApp.openById(avonId);
      const sheetAvon = ssAvon.getSheetByName("Categorias") || ssAvon.getSheets()[0];
      const valsAvon = sheetAvon.getDataRange().getValues();
      
      for (let i = 0; i < valsAvon.length; i++) {
        for (let j = 0; j < valsAvon[i].length; j++) {
          let val = valsAvon[i][j];
          if (val) {
            val = val.toString().trim();
            if (val !== "" && val !== "undefined") avonIds.push(val);
          }
        }
      }
    } catch (errAvon) {
      console.log("Erro ao carregar Avon: " + errAvon);
    }

    return {
      natura: [...new Set(naturaIds)],
      avon: [...new Set(avonIds)],
      name: "Dual-Sync (Natura & Avon Separados)"
    };
  } catch (e) {
    throw new Error("Erro ao acessar planilhas: " + e.message);
  }
}

/**
 * Grava os resultados finais enviados pelo navegador
 */
function saveAuditResults(results) {
  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    let resSheet = ss.getSheetByName("Relatorio_Sincronia");
    
    if (!resSheet) {
      resSheet = ss.insertSheet("Relatorio_Sincronia");
    }
    
    resSheet.clear();
    
    const header = [["Catálogo", "ID Categoria", "Categorias Origem", "Status Sincronia", "Qtd Atual", "Qtd Esperada", "Total Divergência", "AÇÃO: ADICIONAR", "AÇÃO: REMOVER"]];
    const numCols = header[0].length;
    
    resSheet.getRange(1, 1, 1, numCols)
      .setValues(header)
      .setBackground("#FF8050")
      .setFontColor("white")
      .setFontWeight("bold");
    
    if (results.length > 0) {
      resSheet.getRange(2, 1, results.length, numCols).setValues(results);
      resSheet.autoResizeColumns(1, numCols);
    }
    
    return "Sucesso! Planilha atualizada.";
  } catch (e) {
    throw new Error("Erro ao gravar resultados: " + e.message);
  }
}
