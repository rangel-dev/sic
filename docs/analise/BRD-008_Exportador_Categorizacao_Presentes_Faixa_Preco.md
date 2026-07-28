# Análise de Negócio — Exportador: Categorização Automática de Presentes por Faixa de Preço

**Documento:** BRD-008
**Autor:** Marcos (Analista de Negócios Jr)
**Data:** 27-07-2026
**Status:** Aprovado para implementação
**Branch:** `feat/exportador-presentes-faixa-preco`
**Origem:** Pedido do gestor (documento gerado por IA), revisado e formalizado nesta BRD
**Pré-requisitos:** Nenhum — módulo Exportador (`SyncEngine`) já em produção

---

## 1. Sumário Executivo

Produtos da categoria de planejamento "Presente" precisam ser atribuídos, no SFCC, a
uma de quatro categorias de vitrine de acordo com a faixa de preço. Hoje esse trabalho
é manual: o operador filtra a Grade de Ativação no Excel por faixa de preço e copia os
SKUs um a um para cada categoria no Business Manager. É lento e sujeito a erro
(SKU na faixa errada, SKU esquecido, categoria antiga não desmarcada quando o preço
muda).

A proposta é mover essa lógica para dentro do **Exportador** (`SyncEngine`), no mesmo
passo em que hoje ele já calcula e escreve `category-assignment` a partir das abas
`LISTA_X` da planilha. O usuário continua fazendo exatamente o mesmo upload de hoje
(Grade + XMLs); o Catálogo XML de delta passa a incluir também as
`category-assignment` de faixa de preço, com adições e remoções calculadas
automaticamente.

---

## 2. Situação Atual (AS-IS)

### 2.1 Fluxo de trabalho manual

1. Abre a Grade de Ativação e filtra "CATEGORIA PLANEJAMENTO" = "Presente".
2. Aplica filtro sequencial sobre "Preço POR" para isolar cada faixa.
3. Copia e cola a lista de SKUs de cada faixa na respectiva categoria no Business
   Manager (SFCC).
4. Repete para as 4 faixas.

### 2.2 Problemas identificados

- Alto custo operacional (tarefa manual repetida a cada ciclo).
- Risco de erro humano (SKU na faixa errada, SKU esquecido).
- Categoria antiga não é removida quando o preço do SKU muda de faixa (o processo
  manual normalmente só adiciona, raramente audita remoção).
- Atraso na atualização do catálogo/lançamento de campanhas.

### 2.3 O que o Exportador já faz hoje (relevante para esta BRD)

O mecanismo de `category-assignment` **já existe** no motor, só que alimentado pelas
abas `LISTA_X` da planilha, não por faixa de preço:

- `_parse_catalogs` lê todo `category-assignment` do XML atual em
  `state["assignments"]: {category-id: set(product-id)}` (`sync_engine.py:230-234`).
- `_execute_rules`/`_generate_catalog_xml` comparam o conjunto desejado (planilha)
  contra `state["assignments"]` e geram só o **delta** (adições e remoções),
  exatamente o padrão que esta BRD vai reaproveitar (`sync_engine.py:406-430`,
  `sync_engine.py:483-499`).

O que **não existe** hoje: leitura das colunas "CATEGORIA PLANEJAMENTO" e "Preço POR"
da Grade (`_parse_excel_files` hoje só lê SKU, VISIBLE/VITRINE e SELO —
`sync_engine.py:150-197`), e qualquer lógica de faixa de preço.

---

## 3. Situação Desejada (TO-BE)

### 3.1 Fluxo automatizado

1. Usuário faz upload da Grade de Ativação + XMLs de catálogo, como já faz hoje.
2. Ao gerar o Catálogo XML, o Exportador, além das regras já existentes:
   - Identifica SKUs com "CATEGORIA PLANEJAMENTO" = "Presente" na Grade.
   - Lê o "Preço POR" de cada um desses SKUs.
   - Determina a faixa de preço correspondente e a categoria SFCC alvo.
   - Calcula o delta de `category-assignment` (adições e remoções) contra o estado
     atual do XML, usando o mesmo mecanismo já usado para as listas de vitrine.

### 3.2 Detecção de colunas por cabeçalho (não por letra fixa)

O pedido original especifica "Coluna I" para "CATEGORIA PLANEJAMENTO". Para manter
consistência com o padrão já usado no motor (detecção de VISIBLE/VITRINE e SELO por
texto de cabeçalho, não por posição fixa — `sync_engine.py:158-161`) e evitar quebra
caso alguém insira/remova uma coluna na planilha, a detecção de
"CATEGORIA PLANEJAMENTO" e "Preço POR" será **por texto de cabeçalho**, dentro da
mesma varredura que já localiza as demais colunas da aba Grade.

---

## 4. Regras de Negócio Detalhadas

### 4.1 Fonte da informação

| Campo | Origem |
|---|---|
| SKU marcado como presente | Aba Grade de Ativação, coluna com cabeçalho "CATEGORIA PLANEJAMENTO" = "Presente" |
| Preço de referência | Mesma aba, coluna com cabeçalho "Preço POR" |

### 4.2 Faixas de preço → categoria SFCC

| ID da Categoria no SFCC | Faixa de Preço (`Preço POR`) |
|---|---|
| `presentes-faixa-de-preco-agradecer` | Até R$ 50,00 |
| `presentes-faixa-de-preco-encantar` | De R$ 50,01 a R$ 100,00 |
| `presentes-faixa-de-preco-surpreender` | De R$ 100,01 a R$ 150,00 |
| `presentes-faixa-de-preco-impressionar` | A partir de R$ 150,01 |

As 4 categorias são **mutuamente exclusivas**: um SKU pertence a no máximo uma delas
por vez. Se o preço mudar de faixa entre uma execução e outra, o delta remove o SKU
da faixa antiga e adiciona na nova na mesma geração de XML.

### 4.3 Marca

Aplica-se somente a produtos **Natura**, reaproveitando a detecção de marca já
existente na execução (`brand`). Não roda para execuções Avon.

### 4.4 Escopo por SKU — só variações, não o produto-pai

*(Decisão confirmada em 27-07-2026)* A regra considera apenas SKUs de variação
(vendáveis), que têm "Preço POR" próprio na Grade. O produto-pai/SKU mestre é
isento, seguindo o mesmo critério já usado no Auditor para o Check #4/#13
([BRD-005](BRD-005_Auditor_Checks_Independentes_Grade.md)): quem precifica é a
variação, não o master.

### 4.5 Preço ausente, zerado ou inválido

*(Decisão confirmada em 27-07-2026)* Se "Preço POR" estiver vazio, zerado ou não for
numérico para um SKU marcado como "Presente", o SKU **não é categorizado** em
nenhuma das 4 faixas nesta execução. Se ele estava atribuído a alguma faixa em uma
execução anterior, é **removido** dela (o delta trata "sem preço válido" como "não
pertence a nenhuma faixa").

### 4.6 Coexistência com outras categorias

*(Decisão confirmada em 27-07-2026)* O Exportador **só adiciona/remove as 4
categorias de faixa de preço**. Nenhuma outra atribuição de categoria do produto
(categoria primária, outras vitrines, listas) é tocada por esta regra.

### 4.7 Geração do delta XML

Catálogo XML de saída continua sendo sempre um delta: inclui apenas as
`category-assignment` que precisam ser adicionadas ou removidas para que o estado
final no SFCC reflita a categorização correta — mesmo mecanismo de diff já usado
para as listas `LISTA_X`.

---

## 5. Análise de Impacto

| Arquivo | Mudança | Risco |
|---|---|---|
| `src/core/sync_engine.py` — `_parse_excel_files` | Detectar colunas "CATEGORIA PLANEJAMENTO" e "Preço POR" por cabeçalho na aba Grade; gravar em `grade_map[pid]` (ex.: `planning_cat`, `price`) | Baixo — mesmo padrão já usado para VISIBLE/SELO |
| `src/core/sync_engine.py` — `_execute_rules` | Nova etapa: para cada SKU variação com `planning_cat == "Presente"` e marca Natura, calcular faixa a partir de `price` e montar conjunto desejado por categoria (`presentes-faixa-de-preco-*`) | Médio — nova regra de negócio, precisa de teste com dados reais |
| `src/core/sync_engine.py` — `_generate_catalog_xml` | Reaproveitar o diff add/remove de `category-assignment` já existente para as 4 categorias fixas | Baixo — infraestrutura já existe |
| Relatório XLSX do Exportador | Sem mudança nesta fase (ver Fora de Escopo) | Nulo |

---

## 6. Critérios de Aceite

| # | Critério |
|---|---|
| CA-01 | SKU Natura, variação, "CATEGORIA PLANEJAMENTO" = "Presente", preço até R$ 50,00 → `category-assignment` para `presentes-faixa-de-preco-agradecer` |
| CA-02 | Mesma lógica válida para as outras 3 faixas (encantar, surpreender, impressionar) |
| CA-03 | SKU que muda de faixa entre execuções → removido da faixa antiga e adicionado à nova na mesma geração |
| CA-04 | SKU sem preço válido (vazio/zero/não numérico) → não recebe nenhuma das 4 categorias; se estava em uma, é removido |
| CA-05 | SKU Avon → nunca recebe categoria de faixa de presente, mesmo com "CATEGORIA PLANEJAMENTO" = "Presente" |
| CA-06 | Produto-pai/SKU mestre → nunca recebe categoria de faixa de presente |
| CA-07 | Nenhuma outra `category-assignment` do produto (categoria primária, listas, etc.) é alterada por esta regra |
| CA-08 | SKU que deixa de ser "Presente" na Grade → removido de qualquer uma das 4 categorias em que estivesse |

---

## 7. Fora de Escopo (Nesta Fase)

- Interface para o usuário configurar as faixas de preço (fixas no código nesta
  fase).
- Aplicação da regra para outras marcas além da Natura.
- Coluna no relatório XLSX do Exportador indicando a faixa/categoria atribuída
  (melhoria futura).
