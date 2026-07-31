# Análise de Negócio — Auditor: Listas Ausentes/Ocultas e Exportador: searchable-if-unavailable-flag

**Documento:** BRD-010
**Autor:** Marcos (Analista de Negócios Jr)
**Data:** 31-07-2026
**Status:** Aprovado para implementação
**Branch:** `fix/brd-006-007-008-criticos`
**Pré-requisitos:** BRD-006 (Auditor — Excesso em Listas de Vitrine), BRD-009 (padrão de `setdefault` para aba visível vazia)

---

## 1. Sumário Executivo

Em nova revisão do SIC entre o autor e seu gestor (QA de regras de negócio), 2 decisões
foram tomadas, cobrindo os dois módulos principais do sistema:

1. **Auditor** — o Check "Excesso em Lista de Vitrine" (BRD-006) trata uma `LISTA_XX`
   ausente ou oculta na Grade exatamente como uma lista genuinamente esvaziada, gerando
   falso-positivo sistemático. Uma lista ausente/oculta não deve ser validada.
2. **Exportador** — nova regra de negócio: todo produto do catálogo (Natura e Avon,
   ativo ou não, mestre ou não) deve ter `searchable-if-unavailable-flag = true`.

---

## 2. Item 1 — Auditor: Lista ausente/oculta da Grade não é validada

### 2.1 Situação Atual (AS-IS)

`AuditorEngine._parse_excels` (`src/core/auditor_engine.py`) já ignora abas ocultas ao
varrer `LISTA_XX` (`if ws.sheet_state != 'visible': continue`, precedente do próprio
BRD-006/BRD-009). Porém `_parse_lista` só registra a chave em `excel_lists` dentro do
laço que casa um SKU válido — uma aba visível com 0 SKUs nunca ganha chave. Resultado:
"aba ausente", "aba oculta" e "aba visível vazia" são hoje **indistinguíveis** depois do
parsing — as três resultam em `list_id not in excel_lists`.

O Check `list_excess` (`src/core/auditor/parity_rules_v12.py`, BRD-005/BRD-006) usa
`excel_lists.get(list_id, set())` para calcular o excesso (`xml_skus - ex_skus`). Como
não distingue os três cenários, uma `LISTA_XX` presente no catálogo XML mas ausente ou
oculta na Grade (por não se aplicar a este ciclo, por exemplo) faz **todos** os SKUs
daquela categoria serem reportados como falso-positivo de excesso.

> **Nota de mudança de critério**: o BRD-006 (CA-04) documentou esse comportamento como
> validado ("Lista existe no XML sem aba correspondente no Excel → `list_excess` para
> todos os SKUs da lista"). Este documento **revoga esse critério** — a partir daqui,
> esse cenário deixa de gerar `list_excess`. Não se trata de um bug do BRD-006, e sim de
> uma regra de negócio nova que restringe o escopo original.

### 2.2 Situação Desejada (TO-BE)

- `LISTA_XX` **ausente** do arquivo, ou **oculta** (`hidden`/`veryHidden`) → não é
  validada pelo Check `list_excess`. Nenhum erro é gerado para os SKUs dessa categoria,
  independente do que exista no catálogo XML.
- `LISTA_XX` **visível, mesmo com 0 SKUs** → continua validada normalmente: todo SKU
  daquela categoria presente no XML é reportado como excesso genuíno (sinal real de
  "deveria ter sido removido do Salesforce, ainda não foi").

### 2.3 Regra de Negócio

`_parse_lista` passa a registrar a chave de uma lista assim que a aba é identificada
como visível (`excel_lists.setdefault(...)`), independente de conter SKU — mesmo padrão
já usado no Exportador para o cenário simétrico (BRD-009, `sync_engine.py`). O Check
`list_excess` passa a pular (`continue`) qualquer `list_id` que não exista como chave em
`excel_lists`, antes de calcular o excesso.

### 2.4 Análise de Impacto

| Arquivo | Mudança | Risco |
|---|---|---|
| `src/core/auditor_engine.py` — `_parse_lista` | `setdefault` antecipado da chave da lista (aba já garantidamente visível) | Baixo — reaproveita padrão já usado no Exportador (BRD-009); Check `list` (não-excesso) não é afetado, confirmado lendo o código |
| `src/core/auditor/parity_rules_v12.py` — Check `list_excess` | Guarda `if list_id not in excel_lists: continue` antes do cálculo de excesso | Baixo — lógica aditiva; regride pontualmente o CA-04 do BRD-006, com essa reversão documentada aqui |
| `src/core/auditor/integrity.py` | `EXPECTED_V12_HASH` regenerado (arquivo `parity_rules_v12.py` é integrity-locked) | Nulo — procedimento padrão já usado desde o BRD-006 |

---

## 3. Item 2 — Exportador: searchable-if-unavailable-flag sempre true

### 3.1 Situação Atual (AS-IS)

O parsing do catálogo XML de entrada (`_parse_catalogs`, `src/core/sync_engine.py`) já
lê `<searchable-if-unavailable-flag>` de todo produto (`seoFlag`), e a geração do XML
delta (`_generate_catalog_xml`) já emite essa tag se ela estiver presente no dicionário
de mudanças (`up`). Porém nenhuma regra de negócio em `_execute_rules` decide o valor —
a flag nunca é incluída em `up`, então nunca é escrita no XML de saída.

### 3.2 Situação Desejada (TO-BE)

Todo produto do catálogo (Natura e Avon, ativo ou não, mestre ou não, sem exceção) deve
ter `<searchable-if-unavailable-flag>true</searchable-if-unavailable-flag>`.

### 3.3 Regra de Negócio — Modo Idempotente

*(Decisão confirmada em 31-07-2026)* A cada execução, o motor inclui a flag no delta
apenas para produtos cujo estado atual **não** é `true` (o que inclui a ausência da tag
no XML de entrada, parseada como `seoFlag = False`). Produtos que já estão corretos não
reaparecem no delta só por causa dessa flag — mesmo padrão de convergência já usado para
`online-flag`/`searchable-flag`. A regra não depende de marca (`is_avon`) nem do estado
online/searchable do produto, e vale igualmente para produtos mestre.

Ao longo de sucessivas execuções, o catálogo inteiro converge para `true` em todos os
produtos, sem exigir que o motor gere um XML com o catálogo completo a cada rodada.

### 3.4 Reaproveitamento de Infraestrutura

`_parse_catalogs` e `_generate_catalog_xml` **não precisam de nenhuma mudança** — o
parsing e a emissão da flag já existiam prontos (gancho morto), só faltava a regra de
negócio em `_execute_rules` decidindo o valor.

### 3.5 Análise de Impacto

| Arquivo | Mudança | Risco |
|---|---|---|
| `src/core/sync_engine.py` — `_execute_rules` | Uma linha em cada um dos 2 loops (produtos normais e mestres): `if not prod["seoFlag"]: up["searchable-if-unavailable-flag"] = "true"` | Baixo — aditivo, idempotente, reaproveita infraestrutura de parsing/emissão já existente |

---

## 4. Critérios de Aceite

| # | Critério |
|---|---|
| CA-19 | `LISTA_XX` ausente do arquivo Excel → nenhum `list_excess` gerado para os SKUs dessa categoria no XML |
| CA-20 | `LISTA_XX` oculta (`hidden` ou `veryHidden`), mesmo que exista no arquivo → nenhum `list_excess` gerado |
| CA-21 | `LISTA_XX` visível com 0 SKUs → `list_excess` gerado normalmente para os SKUs dessa categoria no XML (regressão controlada do CA-04 do BRD-006, agora restrita a este cenário) |
| CA-22 | Produto (Natura ou Avon) com `searchable-if-unavailable-flag` ausente ou `false` no XML de entrada → delta inclui a flag como `true` |
| CA-23 | Produto já com a flag `true` e nenhuma outra mudança → não aparece no delta (idempotência) |
| CA-24 | A regra do CA-22/CA-23 vale igualmente para produtos mestre |

---

## 5. Fora de Escopo (Nesta Fase)

- Adicionar coluna de relatório dedicada à flag `searchable-if-unavailable-flag` no
  Exportador.
- Qualquer mudança no Check #7 original (`list` — "Falta no SF"/"Lista Inexistente no
  SF"), que já não gerava falso-positivo com listas ausentes/ocultas.
- Qualquer mudança em regras de marca (`is_avon`) além do já descrito no Item 2.
- Forçar reemissão da flag em produtos já corretos a cada execução (decisão explícita
  pelo modo idempotente).
