# Análise de Negócio — Exportador e Auditor: Listas Vazias, Resumo de Kits e Presentes Avon

**Documento:** BRD-009
**Autor:** Marcos (Analista de Negócios Jr)
**Data:** 31-07-2026
**Status:** Aprovado para implementação
**Branch:** `fix/brd-006-007-008-criticos`
**Pré-requisitos:** BRD-008 (Exportador — Categorização de Presentes por Faixa de Preço), já implementado nesta mesma branch

---

## 1. Sumário Executivo

Em revisão do SIC entre o autor e seu gestor (QA de regras de negócio), 3 decisões
foram tomadas, cobrindo dois módulos:

1. **Exportador** — uma `LISTA_XX` esvaziada na Grade não gera nenhuma ação hoje;
   deveria remover no Salesforce tudo que estava atribuído a ela. Junto disso, abas
   ocultas da planilha devem ser ignoradas por completo.
2. **Auditor (Validação de Kits)** — o relatório exportado tem uma aba "Resumo" que
   não reflete os cards de subtipo selecionados na tela antes do export.
3. **Exportador (extensão do BRD-008)** — a categorização de presente por faixa de
   preço, hoje só para Natura, passa a valer também para Avon, com faixas e IDs de
   categoria próprios.

---

## 2. Item 1 — Lista vazia gera remoção; abas ocultas são ignoradas

### 2.1 Situação Atual (AS-IS)

`_parse_excel_files` (`src/core/sync_engine.py`) só registra uma `LISTA_XX` no dict
`excel_lists` dentro do laço que varre células em busca de SKUs — se a aba não tiver
nenhum SKU, a chave nunca é criada. O diff downstream (`_execute_rules`,
`_generate_catalog_xml`) itera só sobre `excel_lists.items()`; uma lista ausente do
dict nunca gera delta, nem de remoção. Hoje, esvaziar `LISTA_07` na Grade não remove
nada no Salesforce — o SIC simplesmente ignora a aba.

Além disso, o motor não verifica se uma aba está oculta (`sheet_state` do openpyxl:
`"visible"`/`"hidden"`/`"veryHidden"`) — processa qualquer aba cujo nome bata com o
padrão de Grade ou Lista, esteja ela visível ou não.

### 2.2 Situação Desejada (TO-BE)

- Uma `LISTA_XX` visível, mesmo com 0 SKUs, registra a chave no dict `excel_lists`
  com um conjunto vazio. O diff existente já resolve o resto: `old_set - set() =
  old_set` → todos os SKUs antes atribuídos àquela categoria são removidos no XML
  delta gerado.
- Qualquer aba oculta (`hidden` ou `veryHidden`) é ignorada por completo — tratada
  como se não existisse no arquivo. Isso vale tanto para abas `LISTA_XX` quanto para
  a própria aba `GRADE DE ATIVAÇÃO`: se a Grade estiver oculta, nenhum dado de grade
  é capturado (equivalente a Grade ausente do upload).

### 2.3 Regra de Negócio

Precedente já existente no código: `src/core/auditor_engine.py:297-300` já ignora
abas ocultas ao iterar `LISTA_XX` (`if ws.sheet_state != 'visible': continue`). O
Exportador passa a seguir o mesmo padrão, aplicado de forma única no laço de
varredura de abas (que no `sync_engine.py`, diferente do Auditor, trata Grade e
Lista no mesmo laço).

### 2.4 Análise de Impacto

| Arquivo | Mudança | Risco |
|---|---|---|
| `src/core/sync_engine.py` — `_parse_excel_files` | Checagem de `sheet_state` no topo do laço de abas; registro antecipado de `clean_id` em `excel_lists` para abas de lista | Baixo — reaproveita padrão já usado no Auditor; nenhuma mudança em `_execute_rules`/`_generate_catalog_xml` |

---

## 3. Item 2 — Resumo do Relatório de Kits reflete os cards selecionados

### 3.1 Situação Atual (AS-IS)

`_export_kit_report` (`src/ui/pages/view_auditor.py`) gera a aba "Resumo" do
relatório de kits em 2 blocos: KPIs gerais (Bloco 1) e detalhamento por subtipo
(Bloco 2). O Bloco 2 é calculado a partir de `kd.rows` sem nenhum filtro, por
design explícito ("Sempre o quadro COMPLETO, ignorando os filtros da tela"). Quando
o usuário seleciona 1+ cards de subtipo na tela antes de exportar, as abas por marca
respeitam esse filtro, mas o Bloco 2 do Resumo não — o que gera a sensação de "o
relatório não tá puxando as informações dos cards selecionados".

### 3.2 Situação Desejada (TO-BE)

- **Bloco 1 (KPIs gerais — Kits Analisados/Corretos/Divergentes) permanece sempre
  completo.** É uma contagem por kit, não por linha de divergência; não faz sentido
  fatiar por subtipo.
- **Bloco 2 (detalhamento por subtipo) passa a respeitar os cards selecionados na
  tela** (`self._kit_active_filters`), usando o mesmo recorte já calculado para as
  abas por marca (`rows_filtradas`). Sem nenhum card selecionado ("Todos"),
  comportamento idêntico ao atual.
- Quando há filtro ativo no momento do export, uma linha de aviso é adicionada ao
  final do Resumo (`⚠ Filtro ativo na exportação: <cards>`), para que quem abrir o
  Excel sem ver a tela não confunda o Bloco 2 parcial com o total geral.

### 3.3 Análise de Impacto

| Arquivo | Mudança | Risco |
|---|---|---|
| `src/ui/pages/view_auditor.py` — `_export_kit_report` | Bloco 2 passa a iterar `rows_filtradas` (já calculado para as abas por marca) em vez de `kd.rows` cru; linha de aviso quando há filtro ativo | Baixo — reaproveita filtro já existente; Bloco 1 e abas por marca inalterados |

---

## 4. Item 3 — Presente por Faixa de Preço estendido para Avon

### 4.1 Situação Atual (AS-IS)

O BRD-008 implementou a categorização de presente só para Natura —
`_compute_presente_targets` retorna `None` sempre que `brand != "natura"`, e a Avon
nunca recebe nenhuma das 4 categorias de faixa (`presentes-faixa-de-preco-*`).

### 4.2 Situação Desejada (TO-BE)

A mesma lógica de negócio do BRD-008 (fonte de dados, detecção de colunas por
cabeçalho, escopo por SKU de variação, delta add/remove) passa a valer também para
Avon, com faixas e IDs de categoria próprios:

| ID da Categoria no SFCC (Avon) | Faixa de Preço (`Preço POR`) |
|---|---|
| `presentes-faixa-de-preco-ate-19` | Até R$ 19,99 |
| `presentes-faixa-de-preco-de-20-ate-49` | De R$ 20,00 até R$ 49,99 |
| `presentes-faixa-de-preco-de-50-ate-99` | De R$ 50,00 até R$ 99,99 |
| `presentes-faixa-de-preco-acima-de-150` | Acima de R$ 150,00 |

*(Faixas Natura do BRD-008 permanecem inalteradas — ver aquele documento.)*

### 4.3 Regra de Negócio Detalhada — Lacuna Proposital 100,00–150,00

*(Decisão confirmada em 31-07-2026)* Diferente das faixas Natura (contíguas, sem
gaps), as faixas Avon **não cobrem o intervalo entre R$ 100,00 e R$ 150,00**
(ambos inclusive). Um SKU Avon "Presente"/"PRESENTES" com preço nessa faixa **não
recebe nenhuma** das 4 categorias — comportamento idêntico ao de "preço inválido"
do BRD-008 (CA-04): se estava categorizado antes e o preço migrou para essa lacuna,
é removido de qualquer faixa em que estivesse.

R$ 150,00 exato cai na lacuna — "acima de 150" é estritamente `> 150,00`.

### 4.4 Reaproveitamento de Infraestrutura

`run()`, `_execute_rules` e `_generate_catalog_xml` **não precisam de nenhuma
mudança** — já tratam `presente_targets` de forma genérica por `cat_id` cru, sem
qualquer lógica específica de marca (confirmado lendo o código: o diff add/remove
funciona para qualquer conjunto de IDs de categoria). Só `_compute_presente_targets`
muda, escolhendo a tabela de faixas/IDs certa por marca via um dict de regras
(`_PRESENTE_RULES_BY_BRAND`).

### 4.5 Análise de Impacto

| Arquivo | Mudança | Risco |
|---|---|---|
| `src/core/sync_engine.py` | Nova constante `PRESENTE_CATEGORY_IDS_AVON`, nova função `_price_bucket_avon` (com lacuna proposital), `_compute_presente_targets` reescrito para escolher a tabela por marca | Baixo/Médio — nova regra de negócio, mesma estrutura já validada para Natura |

---

## 5. Critérios de Aceite

| # | Critério |
|---|---|
| CA-09 | `LISTA_XX` esvaziada no Excel (visível, 0 SKUs) → todos os SKUs antes atribuídos a essa categoria são removidos no XML delta |
| CA-10 | Aba `LISTA_XX` oculta (hidden ou veryHidden) → tratada como inexistente; nenhum delta gerado para essa lista, mesmo que tenha SKUs |
| CA-11 | Aba `GRADE DE ATIVAÇÃO` oculta → nenhum dado de grade é capturado (equivalente a Grade ausente) |
| CA-12 | Relatório de Validação de Kits: com cards de subtipo selecionados na tela, o Bloco 2 da aba Resumo mostra apenas as contagens do recorte filtrado, com aviso textual do filtro ativo |
| CA-13 | Sem nenhum card selecionado, o Bloco 2 do Resumo mantém o comportamento atual (todos os subtipos com achado) |
| CA-14 | Bloco 1 (KPIs gerais) do Resumo permanece sempre completo, independente de filtro |
| CA-15 | SKU Avon, variação, "CATEGORIA PLANEJAMENTO" = "Presente"/"PRESENTES", preço até R$ 19,99 → `presentes-faixa-de-preco-ate-19` |
| CA-16 | Mesma lógica válida para as outras 3 faixas Avon (20-49, 50-99, acima de 150) |
| CA-17 | SKU Avon "Presente" com preço entre R$ 100,00 e R$ 150,00 (ambos inclusive) → nenhuma das 4 categorias Avon; se estava categorizado, é removido |
| CA-18 | R$ 150,00 exato cai na lacuna (não entra em "acima de 150", que é estritamente > R$ 150,00) |

---

## 6. Fora de Escopo (Nesta Fase)

- Alteração das faixas de preço Natura definidas no BRD-008.
- Interface para o usuário configurar as faixas Avon (fixas no código, mesmo padrão
  do BRD-008).
- Preencher a lacuna 100–150 da Avon com uma faixa adicional — decisão explícita de
  deixá-la sem categoria nesta fase.
- Mudanças no Bloco 1 do Resumo de kits (KPIs gerais) para respeitar filtro de
  subtipo.
