# Mdulo Auditor: Certificado de Conformidade e Evidncias (Master Audit)

## 1. Objetivo
Transformar o processo de auditoria em um sistema de certificao. O objetivo  garantir que a Grade de Ativao esteja 100% ntegra antes de qualquer gerao de arquivos. Os documentos de evidncia (PDF e Excel) s sero emitidos se **no houver nenhuma divergncia** nos pontos crticos.

## 2. Fluxo de Operao e Trava de Segurana
- **Condio de Emisso:** O sistema s habilitar a gerao do PDF e do Excel de Evidncias se o resultado da auditoria for **ZERO ERROS** nos pilares de Preo, Visibilidade e Existncia.
- **Mensageria de Erro:** Caso existam divergncias, o sistema **bloqueia** a emisso dos documentos e exibe um alerta crtico: 
  >  **Bloqueio de Conformidade:** Foram encontradas divergncias na auditoria. Ajuste os itens apontados para liberar o Certificado de Evidncias.

## 3. Relatrios de Sada (Status: 100% OK)

### 3.1 Sumrio Executivo (Documento PDF)
Um documento formal em PDF contendo o resumo consolidado da auditoria para fins de arquivamento e governana:
1.  **Total de Registros:** Quantidade total de produtos identificados na aba `GRADE DE ATIVAO`.
2.  **Validao de Preos:** Confirmao de que 100% dos preos (DE/POR) esto em conformidade, informando a quantidade total de SKUs validados.
3.  **Validao de Visibilidade:** Confirmao de que 100% dos itens marcados como `VISIBLE` no Excel esto como `searchable` no Salesforce, com a contagem total.
4.  **Integridade de Ativao:** Confirmao de que todos os produtos da Grade esto presentes e corretos no Salesforce, com a contagem final.

### 3.2 Relatrio de Evidncias (Arquivo Excel)
Arquivo detalhado com o "lado a lado" de cada validao realizada.
- **Aba nica:** `EVIDENCIAS_MASTER`
- **Colunas:** SKU, MARCA, ATRIBUTO (Preo DE, Preo POR, Searchable, Online), VALOR_EXCEL, VALOR_SALESFORCE, STATUS ( OK).

## 4. Especificaes Tcnicas

### 4.1 Lgica de Validao (`CertificationEngine`)
- O motor deve realizar o cruzamento "Double-Blind" usual.
- Se a lista de erros (`AuditResult.errors`) estiver vazia para os mdulos crticos, o sistema dispara a gerao dos arquivos de evidncia.

### 4.2 Requisitos de Dados (PDF)
O PDF deve ser gerado contendo:
- Data e Hora da Auditoria.
- Nome dos arquivos comparados (Excel e XMLs).
- Selo visual de **"CONFORMIDADE GARANTIDA"**.

## 5. Valor para o Negcio
- **Segurana Operacional:** Garante que nenhum erro de preo ou visibilidade passe para a produo.
- **Arquivamento de Provas:** O PDF serve como comprovante de que a auditoria foi realizada e aprovada em 100% da base.
- **Eficincia:** Elimina a necessidade de conferncia manual de relatrios de erro "vazios".
