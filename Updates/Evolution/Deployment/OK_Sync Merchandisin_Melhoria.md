# Plano de Execução - Módulo 2: Merchandising Sync

## Contexto
Aplicação: Pricing Master Suite V11.0 (Dev).
Objetivo: criar módulo robusto que recebe Excel e XML para gerar Delta XML de "category-assignment" plus flags (online/searchable/custom attributes) para SFCC.

## Entradas obrigatórias
- Excel (Planilha Comercial) -> `syncExcelInput`
- XML Catálogo Site   -> `syncXmlInput`
- Botão processar     -> `syncProcessBtn`

## 7 Regras de Negócio
1. Dual upload obrigatório
2. Pre-flight brand check
3. Online lifecycle (`online-flag true/false`)
4. Searchable flag (via `VISIBLE IMPLANTAÇÃO` ou `VISIBLE`)
5. Promo category assignment (`POR < DE`)
6. Selos -> custom-attributes (limpar se vazio)
7. Sync listas `LISTA_XX` (set delta add/delete)

## Estruturas de dados chave
- `excelLists: { [listaId]: Set<sku> }`
- `excelGrade: { [sku]: {DE, POR, VISIBLE, SELOS}}`
- `xmlLists: { [listaId]: Set<sku> }`
- `xmlCatalog: { [sku]: {online, searchable, primary, ...}}`
- `deltaXmlResult: string`

## Perguntas Técnicas pendentes
- Categoria promocional exata (Natura, Avon)
  - Natura: categoria ID `promocao-exclusiva`
  - Avon: pendente (deferido para definição futura)
- Nome/ID do custom attribute selo
  - trocas nos 4 campos:
    - `natg_preferencialProductSlot`
    - `natg_productSlotsRules`
    - `natg_preferencialProductSlotCbSite`
    - `natg_productSlotsRulesCbSite`
  - valor do selo dinâmico em `SELO` do Excel (substituir texto do tag e do values / `Name` conforme entrada)
  - hex ou estilo de cores: pendente, avaliar padrão por catálogo ou mapeamento de estilo global
- Forma do delta SFCC (product update? category-assignment?)
  - revisar com time; foco inicial: `category-assignment` + custom attributes em delta XML
- Estrutura `online-flag` (PUT/merge ou categoria)
  - usar `<online-flag>false</online-flag>` como atributo de produto no delta
- Separador de selo (pipe/virgula)
  - questão de parsing de múltiplos selos no Excel; avaliar implementação mais tarde (pendente)
- Suporte para lista case-insensitive e novos codes
  - pendente; interpretar IDs listáveis sem case sensitivity e criar fallback para novos códigos
- Validação de data: 10 minutos para arquivos (consistente com Auditor)
  - aplicar trava de máxima diferença de 10 minutos na timestamp de upload XML/Excel
- Flag global de catálogo
  - garantir `searchable-if-unavailable-flag` em todo catálogo; se aparecer `false`, converter para `true`

## Fluxo de execução
1. validar upload + disponibilidade
2. detectar marca Excel + XML
3. abortar se conflitante
4. ler todas abas LISTA_XX + grade
5. ler XML e compilar estado atual
6. calcular delta for lists + promo + online + searchable + selos
7. gerar output XML
8. atualizar UI stats + download + webhook (sync)

## Ação imediata 1
- manter este arquivo no repo e usar como referência de codificação.

## Ação imediata 2
- amanhã retomar por: implementar `Sync.processData` + testes com amostras.
