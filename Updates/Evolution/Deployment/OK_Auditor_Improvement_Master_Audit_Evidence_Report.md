# Mdulo Auditor: Certificado de Conformidade e Evidncias (Master Audit)

## 1. Objetivo
Transformar o processo de auditoria em um sistema de certificao de alta governana. O objetivo  assegurar que 100% da Grade de Ativao esteja ntegra antes da execuo de cargas, fornecendo uma trilha de auditoria (audit trail) profissional e irrefutvel.

## 2. Fluxo de Operao e Segurana (Safety Gate)
- **Trava de Emisso:** Os documentos de conformidade (PDF e Excel) so bloqueados por padro. Sua emisso  habilitada **exclusivamente** quando o motor de auditoria retorna um status de **ZERO DIVERGNCIAS** nos pilares crticos.
- **Protocolo de Falha:** Caso existam erros, o sistema exibe uma interface de alerta impeditiva, orientando o analista a realizar os ajustes necessrios antes de tentar uma nova certificao.

## 3. Design e Identidade Visual (Padro Executivo)

O Certificado em PDF deve seguir rigorosos padres de design corporativo:
- **Tipografia:** Uso de fontes *Sans-Serif* modernas (Inter, Roboto ou Montserrat) para mxima legibilidade.
- **Paleta de Cores:** Azul Marinho (Autoridade), Cinza Grafite (Sobriedade) e Verde Esmeralda (Sucesso/Aprovao).
- **Elementos de Segurana:** Incluso de carimbo digital de "CONFORMIDADE GARANTIDA" e Protocolo nico de Auditoria (Hash ID).

## 4. Estrutura do Sumrio Executivo (PDF)

O documento deve ser organizado nas seguintes sees:

### 4.1 Cabealho de Governança
- Identificao da Marca (Natura/Avon).
- Data e Hora da Extrao (Timestamp).
- Verso do Motor de Auditoria.
- Arquivos Fontes (Nomes dos arquivos Excel e XML processados).

### 4.2 Indicadores de Conformidade
| Indicador | Descrio Tcnica | Status |
| :--- | :--- | :---: |
| **Volumetria Total** | Total de SKUs processados na Grade de Ativao. | [QTD] |
| **Audit de Preos** | 100% de paridade entre Excel (DE/POR) e Salesforce. |  OK |
| **Audit de Visibilidade** | 100% de paridade na flag `searchable` (Searchable/Visible). |  OK |
| **Integridade de Catlogo** | Validao de presena e categorizao primria. |  OK |

## 5. Relatrio de Evidncias Detalhado (Excel)

Complementando o PDF, o sistema gera um arquivo Excel tcnico para conferncia linha a linha:
- **Aba:** `EVIDENCIAS_MASTER`
- **Contedo:** Tabela completa contendo `SKU`, `ATRIBUTO`, `VALOR_EXCEL`, `VALOR_SF` e o timestamp da validao.

## 6. Valor para Auditoria (Compliance)
Este novo formato foi desenhado para atender aos requisitos de auditorias externas, garantindo:
1.  **Imutabilidade:** O PDF serve como um "Snapshot" do momento da validao.
2.  **Transparncia:** Exposio clara de todos os critrios de sucesso.
3.  **Rastreabilidade:** Registro histrico de quem e quando validou cada lote de ativao.
