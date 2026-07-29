# Análise de Negócio — Auditor: Sincronia Simétrica de Listas de Vitrine

**Documento:** BRD-006
**Autor:** Arquiteto de Negócio
**Data:** 03-07-2026
**Status:** Implementado (motor V12) — aguardando validação com dados reais na UI
**Branch:** `feat/auditor-excesso-listas-vitrine`
**Pré-requisitos:** Check #7 existente (Visibilidade em Listas), BRD-004 (Escopo Dinâmico)

> Nota: este documento foi originalmente numerado como BRD-005, mas esse número já
> estava em uso pelo BRD "Checks Independentes da Grade" (motor V12, merged na
> `dev`). Renumerado para BRD-006 seguindo o precedente do BRD-003→004.

---

## 1. Sumário Executivo

O Módulo Auditor atualmente valida a consistência das listas de vitrine (ex: `LISTA_01`) de forma unidirecional: ele verifica se um SKU planejado no Excel está presente na categoria correspondente no XML do Salesforce. No entanto, ele não realiza a verificação inversa.

Este documento define a criação de uma nova regra de negócio, "Excesso em Listas de Vitrine", para garantir a sincronia simétrica. A nova regra identifica SKUs que foram removidos da lista no Excel, mas que permanecem na categoria do XML, representando "lixo de catálogo" e desalinhamento com a estratégia comercial.

## 2. Situação Atual (AS-IS)

A lógica atual, implementada no Check #7 de `parity_rules_v12.py`, opera da seguinte forma:

```
PARA CADA SKU na Grade Excel:
  SE SKU está na lista "LISTA_01" do Excel
  E SKU NÃO está na categoria "LISTA_01" do XML
  ENTÃO → Erro: "FALTA NO SF (LISTA_01)"
```

### 2.1 O Gap

Cenário não coberto: um SKU que está na categoria `LISTA_01` do XML, mas que não consta (ou foi removido) da aba `LISTA_01` do Excel.

Impacto do Gap: se uma importação de remoção de categoria falhar no Salesforce, um produto obsoleto pode continuar sendo promovido na vitrine do site, e o Auditor anterior não tinha visibilidade sobre essa falha.

## 3. Situação Implementada (TO-BE)

### 3.1 Nova Regra: "Excesso em Listas de Vitrine"

Implementada como **Check #7b** em `parity_rules_v12.py`, logo após o loop principal por SKU:

```
PARA CADA LISTA (ex: "LISTA_01") nos Catálogos XML:
  Obter o conjunto de SKUs do XML para esta lista (skus_no_xml)
  Obter o conjunto de SKUs do Excel para esta mesma lista (skus_no_excel)

  Calcular a diferença: skus_em_excesso = skus_no_xml - skus_no_excel

  PARA CADA SKU em skus_em_excesso:
    GERAR ERRO "list_excess"
```

- **Código do erro:** `list_excess`
- **Detalhe do erro:** `EXCESSO EM LISTA ({list_id}) — Removido da grade, mas ativo no SF`
- **Metadados de UI:** registrados em `ERROR_META["list_excess"]` (`auditor_engine.py`) — título, ícone e descrição seguem o mesmo padrão dos demais checks, então cards, filtros e exportação já funcionam sem código adicional na UI.

### 3.2 Mitigação de Risco: Escopo Dinâmico (BRD-004)

A regra respeita o escopo dinâmico: para cada `list_id`, a marca é inferida do prefixo (`LISTA_` → Natura, `lista-` → Avon) e a comparação só roda se `has_nat`/`has_avn` indicar que a grade daquela marca foi carregada nesta execução. Se o analista carregar apenas a grade da Natura, listas da Avon nunca geram `list_excess`.

### 3.3 Guarda adicional: Produtos-pai de Variação

Durante a análise do código, identificamos que `xml_lists` inclui produtos-pai de variação (`variation_bases`) sem filtro — comportamento proposital de paridade legada (ver comentário em `auditor_engine.py:609`), pois esses produtos-pai podem ser o item "vendível" da categoria mesmo quando só as variações filhas aparecem na aba do Excel.

Sem essa guarda, o Check #7b geraria falsos-positivos sistemáticos para todo produto-pai de variação presente em listas de vitrine. Por isso, SKUs marcados como `variation_bases` são **excluídos** da regra `list_excess`. Esta é uma extensão sobre o desenho original do BRD, validada com o autor antes da implementação.

### 3.4 Valor para o Negócio

A implementação transforma a auditoria de listas em um ciclo completo, garantindo paridade entre o planejamento comercial (Excel) e a execução no site (XML). O Auditor passa a detectar não apenas o que deveria estar lá, mas também o que não deveria mais estar.

## 4. Impacto Técnico (Realizado)

| Arquivo | Mudança | Risco |
|---|---|---|
| `src/core/auditor/parity_rules_v12.py` | Novo laço "Check #7b" após o loop principal de SKUs, com guarda de escopo dinâmico (`has_nat`/`has_avn`) e exclusão de `variation_bases`. | Baixo — lógica aditiva. |
| `src/core/auditor_engine.py` | Nova entrada `list_excess` em `ERROR_META`. | Baixo — configuração. |
| `src/core/auditor/integrity.py` | `EXPECTED_V12_HASH` regenerado para refletir a mudança em `parity_rules_v12.py`. | Nulo — procedimento padrão obrigatório. |

## 5. Critérios de Aceite

Validados em duas camadas: (1) chamada sintética direta a `execute_parity_rules` com
conjuntos de dados mínimos, cobrindo todas as combinações lógicas; (2) execução do
`AuditorEngine.run()` completo (pipeline real: parsing de Excel/XML, preflight,
`_cross_validate`, `ERROR_META`) usando os fixtures reais de `test_audit/`, com um
catálogo Natura clonado e adicionado de uma category-assignment `LISTA_01` para
`NATBRA-1001` (SKU que está na grade mas não na aba Excel `LISTA_01`) e um catálogo
Avon clonado com `lista-01` para `AVNBRA-2001`.

| # | Critério | Status |
|---|---|---|
| CA-01 | SKU em `LISTA_01`/`LISTA_02` do XML, ausente da aba equivalente do Excel → gera `list_excess`. | ✅ Validado (sintético + engine real: `NATBRA-1001` → `EXCESSO EM LISTA (LISTA_01)`) |
| CA-02 | Regressão: comportamento do Check #7 (`list`) inalterado. | ✅ Validado (engine real: `NATBRA-1007` continua gerando `FALTA NO SF (LISTA_01)`) |
| CA-03 | SKU presente em ambas as fontes → nenhum erro de lista. | ✅ Validado (sintético) |
| CA-04 | Lista existe no XML sem aba correspondente no Excel → `list_excess` para todos os SKUs da lista. | ✅ Validado (sintético) |
| CA-05 | Novo erro aparece no painel com título/descrição claros. | ✅ Validado (UI real, offscreen: card "Excesso em Lista de Vitrine" 🗑️ exibido com contagem 1, filtro isola `NATBRA-1001` com impacto "Lixo de Catálogo") |
| CA-06 | Escopo dinâmico: grade só-Natura não gera `list_excess` para listas da Avon. | ✅ Validado (sintético + engine real: com só `grade_natura.xlsx` carregada, `AVNBRA-2001` em excesso na `lista-01` não gerou erro) |

Nota: o projeto não possui suíte de testes automatizados (`pytest` não está instalado
e não há diretório `tests/`); a validação de regras de negócio é feita rodando o
motor com dados reais/sintéticos, como descrito acima.

## 6. Fora de Escopo

- Alterações na lógica do Check #7 existente (não modificado).
- Alterações em qualquer outra regra de negócio do Auditor.

---

## 7. Nota de Implementação (pós-auditoria, 29-07-2026)

Uma auditoria de conformidade confirmou que os 5 pontos da especificação
(seções 3.1 a 3.3) conferem no código atual, e que o Check #7b sobreviveu
intacto às mudanças de BRD-007/008 (selo de integridade `EXPECTED_V12_HASH`
validado). Ficaram registrados os seguintes comportamentos implementados além
do texto original, e known-issues não corrigidos nesta rodada (severidade
média/baixa, sem risco de dano em produção identificado):

**Além do texto do BRD:**
- A inferência de marca por `list_id` (`LISTA_` → Natura, `lista-` → Avon) é
  **case-insensitive** no Check #7b (`.upper()`/`.lower()`), enquanto o Check
  #7 original usa comparação estrita. Um `cat_id` como `Lista_01` vindo do XML
  seria classificado pelo #7b mas nunca casaria no #7 — assimetria não
  documentada, sem caso real observado até o momento.
- O filtro `SKU_RE.match(sku)` no Check #7b não está no pseudocódigo da seção
  3.1 (baixo impacto, coerente com o resto do motor).

**Known-issues (não corrigidos nesta rodada):**
- **Marca do erro por SKU, não por lista**: a guarda de escopo dinâmico usa a
  marca da *lista*, mas o registro do erro usa a marca derivada do prefixo do
  *SKU*. Um `AVNBRA-*` presente numa `LISTA_01` (cenário cross-brand, já
  coberto pelo Check #3) geraria `list_excess` contabilizado como Avon mesmo
  com `has_avn=False` — fura o espírito do escopo dinâmico (BRD-004) embora
  respeite a letra desta regra.
- **Assimetria de normalização de chave** entre `excel_lists` (chave sempre
  canônica, com padding) e `xml_lists` (chave crua do XML). Se o SF expuser um
  `cat_id` em formato diferente do canônico (ex.: sem zero-padding), a
  categoria inteira viraria `list_excess` por descasamento de formatação, não
  por ausência real da aba. Recomenda-se validar com um dump real de
  categorias antes de considerar isso não-risco.
- `list_excess` **não está no knowledge base do `ai_agent.py`** (`_KB` e lista
  `priority`) — o relatório gerado pela IA cai no fallback genérico para esse
  tipo de erro, em vez de uma descrição dedicada.
