# Análise de Negócio — Preparação para Remoção de Espaços nos Títulos de Coluna da Grade

**Documento:** BRD-011
**Autor:** Marcos (Analista de Negócios Jr)
**Data:** 16-09-2026
**Status:** Rascunho — pendente de definição do novo padrão de título pelo time responsável pela Grade
**Branch:** A definir
**Motivação:** A Grade de Ativação passará por uma reanálise na qual os títulos de coluna
deixarão de conter espaço (ex.: hoje `"TIPO MATERIAL"`, `"CATEGORIA PLANEJAMENTO"`, `"POR
SEGMENTADO"`, `"POR ORIGEM"`; formato final — `TipoMaterial`, `TIPO_MATERIAL` etc. — ainda
não definido pelo time da Grade). Este documento não altera nenhum comportamento hoje;
registra as brechas levantadas em análise de código (pesquisa só-leitura, 16-09-2026) e
propõe tarefas para fechá-las **antes** que a mudança de título aconteça.

---

## 1. Sumário Executivo

O SIC identifica colunas da Grade por **comparação de string exata** contra o título
com espaço em 3 engines, sem nenhuma camada de abstração entre "nome exibido na
planilha" e "identificador usado na lógica". Se o título perder o espaço sem que o
código mude junto, essas comparações passam a falhar **silenciosamente** — sem
exceção, sem aviso na UI — degradando ou desligando funcionalidades inteiras.

O próprio código já contém o padrão correto de correção, usado em `conversor_engine.py`
(`_norm()`, que remove todo whitespace antes de comparar). As tarefas abaixo propõem
aplicar o mesmo padrão nos pontos ainda não protegidos, de forma **agnóstica ao formato
final** do título (funciona seja o novo padrão `TipoMaterial`, `TIPO_MATERIAL` ou outro).

Nenhuma tarefa abaixo deve ser iniciada antes de o time da Grade confirmar os títulos
novos definitivos — a normalização proposta é defensiva e pode ser implementada desde já
sem esperar essa definição, mas os testes de aceite dependem dela.

> **Princípio obrigatório — acréscimo, não substituição:** toda tarefa abaixo deve ser
> implementada como uma condição/tentativa **adicional**, disparada só quando a
> comparação atual falhar (ou em paralelo a ela via `or`), sem alterar, remover ou
> reescrever nenhuma comparação/constante/função já existente. O comportamento de hoje
> (título com espaço) tem que continuar idêntico byte-a-byte depois da mudança — só passa
> a existir mais um caminho que também funciona sem espaço. A Tarefa 3 detalha um caso em
> que a forma "óbvia" de implementar violaria esse princípio (ver 4.3).

---

## 2. Tarefa 1 — `auditor_engine.py`: coluna `TIPO MATERIAL`

### 2.1 Situação Atual (AS-IS)

`src/core/auditor_engine.py:380` identifica a coluna que marca kit ZEST por igualdade
exata: `elif vu == "TIPO MATERIAL":`. Se o título perder o espaço, `tipo_col` nunca é
setado e a validação de kits cai no modo legado — degradação já documentada como
"segura" pelo BRD-007, mas **silenciosa** (`docs/analise/BRD-007_Auditor_Validacao_Kits_Unificada.md:232`
registra explicitamente "nenhum aviso na UI").

### 2.2 Situação Desejada (TO-BE)

A identificação da coluna sobrevive à mudança de título, com ou sem espaço/underscore.

### 2.3 Ação Proposta

**Acréscimo, não substituição.** Não alterar a condição `vu == "TIPO MATERIAL"`
existente. Acrescentar uma alternativa ao lado dela via `or`, comparando a versão sem
espaço/underscore de `vu` contra a versão sem espaço/underscore da constante:
`elif vu == "TIPO MATERIAL" or _sem_espaco(vu) == "TIPOMATERIAL":`. A condição original
continua sendo avaliada e continua batendo sozinha para o título de hoje; a nova condição
só passa a valer quando o título mudar.

### 2.4 Análise de Impacto

| Arquivo | Mudança | Risco |
|---|---|---|
| `src/core/auditor_engine.py:380` | Normalização na comparação de `vu` | Baixo — pontual, aditivo, não muda comportamento atual (título com espaço continua batendo) |

---

## 3. Tarefa 2 — `sync_engine.py`: coluna `CATEGORIA PLANEJAMENTO`

### 3.1 Situação Atual (AS-IS)

`src/core/sync_engine.py:317` identifica a coluna de categorização de presentes por
igualdade exata: `if val == "CATEGORIA PLANEJAMENTO":  # BRD-008`. Sem o espaço,
`plan_col` não é encontrado, `presente_cols_ok` vira `False`, e **toda** a
categorização de "Presentes por faixa de preço" (BRD-008/BRD-009, Natura e Avon) para
de rodar — sem erro visível ao usuário.

### 3.2 Situação Desejada (TO-BE)

A identificação da coluna sobrevive à mudança de título.

### 3.3 Ação Proposta

**Acréscimo, não substituição.** Mesmo tratamento da Tarefa 1: manter
`val == "CATEGORIA PLANEJAMENTO"` como está e acrescentar `or _sem_espaco(val) ==
"CATEGORIAPLANEJAMENTO"` via `or`, sem remover a condição original.

### 3.4 Análise de Impacto

| Arquivo | Mudança | Risco |
|---|---|---|
| `src/core/sync_engine.py:317` | Normalização na comparação de `val` | Baixo — pontual, aditivo |

---

## 4. Tarefa 3 — `segmentado_engine.py`: colunas `POR SEGMENTADO` / `POR ORIGEM` (prioridade mais alta)

### 4.1 Situação Atual (AS-IS)

`src/core/segmentado_engine.py:38` define `HEADER_TARGETS = ("POR SEGMENTADO", "POR
ORIGEM")`, usada em `_find_header_row` (linhas 113-125) via `next((t for t in
HEADER_TARGETS if t in header_map), None)`. Essas duas strings **são a própria condição
de existência** da funcionalidade Exportador → Segmentadas: nenhuma delas batendo =
nenhuma aba é reconhecida como candidata = erro `"Nenhuma aba com coluna 'POR
SEGMENTADO' ou 'POR ORIGEM' encontrada"` (linha 334-335). O normalizador já existente
(`_normalize`, linhas 82-87) só colapsa espaços múltiplos em um único — **pressupõe que
o espaço existe**, não remove.

Além disso, `_normalize` (linha 171) compara `"TOTAL SKUS"` pelo mesmo padrão, para o
aviso de divergência entre total informado e total lido na aba.

O texto de ajuda da tela (`src/ui/pages/view_exportador_segmentadas.py:4,114`) cita
literalmente `"POR SEGMENTADO"`/`"POR ORIGEM"` — precisa ser atualizado junto, senão a
instrução ao usuário fica desatualizada.

### 4.2 Situação Desejada (TO-BE)

A funcionalidade continua reconhecendo a coluna correta independente do título ter ou
não espaço. O texto de ajuda da UI reflete o título vigente.

### 4.3 Ação Proposta

**⚠️ Atenção — forma ingênua quebraria o comportamento atual.** `_normalize()` é
compartilhada por 3 usos diferentes (`header_map` da linha 117, rótulo `"LP"` na linha
162, e `"TOTAL SKUS"` na linha 171), e o valor retornado por `_find_header_row` como
`matched_header` (ainda igual à constante original, com espaço) é usado depois para
buscar a coluna via `header_map.get(matched_header)` (linha 237). Se `_normalize()` for
alterada para remover todo espaço, ou se `HEADER_TARGETS`/`"TOTAL SKUS"` forem reescritos
sem espaço, o `header_map.get(matched_header)` **para de encontrar a coluna mesmo com a
planilha de hoje, sem nenhuma mudança de título** — uma regressão real, não uma
ampliação. Por isso, para esta tarefa especificamente:

- **Não alterar** `_normalize()`, `HEADER_TARGETS`, nem a comparação `"TOTAL SKUS"`.
- Acrescentar um **fallback** em `_find_header_row`: só quando
  `next((t for t in HEADER_TARGETS if t in header_map), None)` retornar `None` (nenhum
  dos dois títulos com espaço foi encontrado), tentar de novo comparando versões sem
  espaço de `HEADER_TARGETS` contra versões sem espaço das chaves de `header_map` — em
  uma função nova e separada, sem tocar na busca original.
- Mesmo padrão de fallback (função separada, sem tocar em `_normalize`) para
  `"TOTAL SKUS"`, se decidido incluir esse item.
- Atualizar o texto de `view_exportador_segmentadas.py` para citar o título vigente
  assim que o novo padrão for confirmado (isso é só texto de UI, não tem o mesmo risco).

### 4.4 Análise de Impacto

| Arquivo | Mudança | Risco |
|---|---|---|
| `src/core/segmentado_engine.py:113-125` | Fallback novo em `_find_header_row`, disparado só quando a busca atual falhar; `_normalize`, `HEADER_TARGETS` e `"TOTAL SKUS"` permanecem intocados | Baixo para o comportamento atual (é aditivo puro) / Médio para o comportamento novo — é o coração da funcionalidade, então o caminho de fallback precisa de teste manual com planilha real antes de aprovar, mesmo não arriscando o caminho de hoje |
| `src/ui/pages/view_exportador_segmentadas.py:4,114` | Texto de ajuda | Nulo — só UI |
| `tests/test_sync_engine_parse_excel.py:65`, `tests/test_sync_engine_presente.py:107` | Ajustar fixtures que hoje usam o título com espaço | Baixo — só garante que o teste continue representativo |

---

## 5. Critérios de Aceite

| # | Critério |
|---|---|
| CA-01 | Com o título `TIPO MATERIAL` renomeado (espaço removido, formato a definir), o Auditor continua identificando corretamente kits ZEST (não cai no modo legado) |
| CA-02 | Com o título `CATEGORIA PLANEJAMENTO` renomeado, a categorização de presentes por faixa de preço (Natura e Avon) continua rodando normalmente |
| CA-03 | Com os títulos `POR SEGMENTADO`/`POR ORIGEM` renomeados, o Exportador → Segmentadas continua reconhecendo as abas candidatas sem exigir espaço |
| CA-04 | Com o título `TOTAL SKUS` renomeado, o aviso de divergência de total continua funcionando |
| CA-05 | Textos de ajuda em `view_exportador_segmentadas.py` citam o título vigente após a mudança |
| CA-06 | Nenhum dos itens acima quebra o comportamento atual: com a planilha de hoje (título ainda com espaço), Auditor, Exportador e categorização de presentes se comportam byte-a-byte igual ao que se comportam antes de qualquer uma destas tarefas ser implementada |

---

## 6. Fora de Escopo (Nesta Fase)

- **`pontuacao_engine.py` (`_find_col`, needles de `"CD VENDA PRODUTO"`, `"CICLO
  INICIO"` etc.)** — foi identificado no levantamento inicial com o mesmo padrão de
  risco (matching por substring sem tolerância a espaço), mas essas needles procuram
  colunas no relatório **GCP**, um arquivo de fonte **externa** ao SIC — não a Grade que
  está sendo reanalisada. Renomear os títulos da Grade não afeta este arquivo. Fica fora
  desta rodada; só entraria em pauta se o GCP também mudasse de layout.
- Qualquer mudança em `conversor_engine.py` — já protegido por `_norm()`.
- O template de saída "Carga GCP" gerado por `conversor_engine._build_row()`
  (`"COD. VENDA PRODUTO"`, `"PREÇO  ($)"`, `"PONTOS "` etc.) — é formato de sistema
  **externo** (aparenta ser SAP/GCP), não a Grade de entrada; não deve mudar junto a
  menos que esse sistema externo também mude seu layout.
- Detecção da aba "GRADE DE ATIVAÇÃO" — já resiliente via fallback por substring
  (`"GRADE" in nome and "ATIVA" in nome`), não precisa de ação.
- Colunas de uma palavra só (`DE`, `POR`, `CM`, `SELO`, `VISIBLE`) — não têm espaço hoje,
  não afetadas por esta mudança.
- Definir o formato final do novo título (`TipoMaterial` vs `TIPO_MATERIAL` vs outro) —
  decisão de fora do SIC, a ser confirmada pelo time responsável pela Grade antes de
  fechar os testes de aceite.
