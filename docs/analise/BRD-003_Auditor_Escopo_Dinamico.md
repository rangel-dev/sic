# Análise de Negócio — Auditor: Ajuste Fino de Escopo Dinâmico (Excesso Online)

**Documento:** BRD-003
**Autor:** Marcos (Analista de Negócios Jr)
**Data:** 22-06-2026
**Status:** Aprovado para implementação
**Branch:** `feat/escopo-dinamico-excesso-online`
**Pré-requisito:** BRD-002 (Check #13 — Produto Online Fora da Grade)

---

## 1. Sumário Executivo

O Check #13, introduzido pelo BRD-002, criou a regra inversa "Active → Planned": todo SKU `online=true` no Salesforce que não conste em nenhuma Grade de Ativação carregada gera erro `online_excess`. Essa regra assume implicitamente que **todas** as marcas relevantes tiveram sua grade carregada na execução.

Na prática, o analista frequentemente audita **uma marca por vez** (ex.: sobe apenas a grade Natura). Como o XML do catálogo Salesforce traz as duas marcas independente da grade selecionada, o Check #13 interpreta a ausência da grade Avon como "47 SKUs Avon esquecidos ligados" — quando na verdade Avon simplesmente não fazia parte do escopo daquela execução. Resultado: milhares de falsos positivos.

Este documento define como diferenciar **"marca fora de escopo"** de **"marca esquecida online"**, sem reabrir a lacuna de silêncio que o BRD-002 foi criado para fechar.

---

## 2. Situação Atual (AS-IS)

```
SE produto.online == true
E produto NÃO está em nenhuma Grade carregada
E produto NÃO é SKU Técnico
E produto NÃO é Variação Base
ENTÃO → Erro: "PRODUTO ONLINE FORA DA GRADE"
```

A regra não considera **se a grade da marca do produto foi carregada na execução**. `has_nat`/`has_avn` já são calculados em `_parse_excels()` (`auditor_engine.py:206-214`) e já chegam como parâmetro em `execute_parity_rules()` (`parity_rules_v11.py:17`) — mas hoje só são consumidos pelo Check #3 (cross-brand de preço, linha 89), não pelo Check #13.

### 2.1 Cenário de falso positivo

```
Analista sobe apenas a Grade Natura (arquivo único da marca).
Pasta de catálogos contém XML Natura + XML Avon (padrão de execução).
Check #13 varre os dois XMLs.
Todo SKU Avon online vira "erro" — Avon nunca esteve em escopo.
```

---

## 3. Situação Desejada (TO-BE)

### 3.1 Nova condição no Check #13

```
SE produto possui online-flag=true
E produto NÃO está em nenhuma Grade carregada
E a marca do produto TEM grade carregada nesta execução (has_nat / has_avn)
E produto NÃO é SKU Técnico
E produto NÃO é Variação Base
ENTÃO → Erro: "PRODUTO ONLINE FORA DA GRADE"
```

Se a marca do SKU não teve grade carregada, o produto é ignorado pelo Check #13 — mas **continua contado** para fins de rastreabilidade (Seção 3.3).

### 3.2 Regra para grade vazia (decisão fechada)

**Grade vazia ≠ marca fora de escopo.** Se o analista carregou um arquivo da marca mas a aba "GRADE DE ATIVAÇÃO" não retornou nenhum SKU (`excel_prices` sem nenhuma entrada daquela marca), isso é tratado como **erro operacional**, não como exclusão de escopo. `has_nat`/`has_avn` já refletem isso corretamente hoje: são setados a partir da detecção de marca do workbook (`_detect_brand_workbook`), que conta ocorrências de `NATBRA-`/`AVNBRA-` na planilha — não da presença de linhas na Grade de Ativação especificamente. Ou seja, **um arquivo carregado da marca, mesmo com a Grade de Ativação vazia, ainda assim mantém `has_nat`/`has_avn = True`** (porque a marca foi detectada em outras abas, como Listas) — então o alerta `online_excess` permanece ativo nesse caso, como desejado. Nenhuma lógica adicional é necessária para este ponto; é uma consequência natural de como `has_nat`/`has_avn` já são calculados, e deve ser coberta por teste (CA-04).

### 3.3 Rastreabilidade (decisão fechada)

A exclusão de uma marca do escopo **não deve ser silenciosa**. Cada SKU ignorado pelo novo filtro é contado num stat dedicado (`scope_skipped`, fora de `ERROR_META`/`errors`, não é uma divergência) e exibido como aviso informativo no dashboard — formato sugerido: *"Avon fora do escopo desta execução (grade não carregada) — N SKUs online ignorados"*. Não bloqueia o Certificado Mestre (não é erro), apenas comunica a decisão de escopo.

---

## 4. Análise de Impacto

### 4.1 Impacto no negócio

| Área | Impacto |
|---|---|
| **Precisão Operacional** | Elimina falsos positivos quando o analista escolhe auditar uma marca por vez |
| **Compliance Comercial** | Mantém a rastreabilidade (BRD-002, item 4.1) via aviso explícito de marca fora de escopo |
| **Risco de regressão** | Não reabre a lacuna do BRD-002 quando ambas as grades estão presentes — o filtro só ativa na ausência real de uma marca |

### 4.2 Impacto técnico (escopo mínimo — 3 arquivos)

| Arquivo | Tipo de mudança | Risco |
|---|---|---|
| `src/core/auditor/parity_rules_v11.py` | Nova condição dentro do bloco do Check #13 (linhas 33-37), usando `has_nat`/`has_avn` já recebidos como parâmetro | Baixo — aditivo, não altera os demais 12 checks |
| `src/core/auditor/integrity.py` | Atualização do hash SHA256 (`EXPECTED_V11_HASH`) | Nulo — consequência obrigatória da mudança acima |
| `src/core/auditor_engine.py` | Novo contador `scope_skipped` em `stats`/`_cross_validate()` | Baixo — aditivo, isolado |
| `src/ui/pages/view_auditor.py` | Aviso informativo (não-erro) próximo ao header de "Painel de Divergências" quando `scope_skipped > 0` | Baixo — novo elemento de UI, não reaproveita `ErrorCard` (não é divergência) |

### 4.3 O que **não** muda

- Checks #1–#12 permanecem intocados.
- Filtro de marca cruzada na leitura da grade (`_parse_grade`, linhas 326-329) permanece — confirmado que não há conceito de "grade híbrida".
- `has_nat`/`has_avn` não mudam de cálculo — apenas ganham um novo consumidor.

---

## 5. Critérios de Aceite

| # | Critério | Como validar |
|---|---|---|
| CA-01 | SKU online + fora da grade + marca COM grade carregada → erro `online_excess` (comportamento atual preservado) | Rodar com ambas as grades carregadas, confirmar que SKUs órfãos ainda geram erro |
| CA-02 | SKU online + fora da grade + marca SEM grade carregada → **sem erro**, mas contabilizado em `scope_skipped` | Rodar auditoria só-Natura com catálogo contendo SKUs Avon online; confirmar ausência de erro e presença do aviso |
| CA-03 | SKU Técnico / Variação Base continuam isentos independente do escopo de marca | Regressão dos casos do BRD-002 (CA-02/CA-03) |
| CA-04 | Grade carregada mas com aba "GRADE DE ATIVAÇÃO" vazia → alerta `online_excess` **mantido** (não tratado como fora de escopo) | Rodar com arquivo Natura cuja Grade de Ativação está zerada; confirmar que erro continua disparando |
| CA-05 | Aviso de "marca fora de escopo" aparece no dashboard quando `scope_skipped > 0`, e não aparece quando todas as marcas presentes no catálogo têm grade carregada | Inspeção visual da UI nos dois cenários |
| CA-06 | Integridade SHA256 passa após atualização do hash | App inicializa sem `integrity_error` |
| CA-07 | Checks #1–#12 sem regressão | Rodar com dataset de referência conhecido (mesmo do BRD-002) |

---

## 6. Perguntas em Aberto

Todas fechadas nesta rodada de análise:

| # | Pergunta | Decisão |
|---|---|---|
| P-01 | Formalizar como BRD antes de implementar? | **Sim** — este documento |
| P-02 | Grade vazia suprime o alerta? | **Não** — mantém alerta (erro operacional ≠ fora de escopo) |
| P-03 | Marca fora de escopo deve ser visível no dashboard? | **Sim** — aviso/contador informativo, sem bloquear certificado |

---

## 7. Fora de Escopo

- Conceito de "grade híbrida" — não existe e não será criado.
- Alteração de qualquer um dos Checks #1–#12.
- Persistência do aviso de "marca fora de escopo" no histórico ou certificado PDF (pode ser demanda futura, análoga ao item P-02 do BRD-002).
