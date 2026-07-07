# Análise de Negócio — Auditor: Checks Independentes da Grade (Motor V12)

**Documento:** BRD-005
**Autor:** Marcos (Analista de Negócios Jr)
**Data:** 24-06-2026
**Status:** Aprovado para implementação
**Branch:** `fix/auditor-checks-grade-independentes`
**Pré-requisitos:** BRD-002 (Check #13 — Produto Online Fora da Grade), BRD-004 (Escopo Dinâmico)

---

## 1. Sumário Executivo

O motor de paridade (v11.6) condicionava indevidamente vários checks à presença da
**grade (planilha Excel)** anexada para a marca. Reportado pelo time de implantação
(Edgar): produtos sem preço apareciam no site sem serem flagrados, e a auditoria de
problemas puramente sistêmicos (XML de catálogo vs XML de pricebook) ficava
inviabilizada quando não se anexava grade.

O princípio correto, conforme alinhado: **nem todos os checks dependem da grade.**
Os checks que comparam o XML de catálogo/pricebook entre si (ex.: Minha Loja vs Ecom,
marca cruzada, POR > DE, preço ausente) devem olhar o XML **como um todo**, sem
intervenção da grade. A grade só é pré-requisito para os checks que de fato comparam
a planilha contra o Salesforce.

Este documento define o motor **V12**, que corrige esse acoplamento preservando a
paridade V11.6 para todos os cenários com grade.

---

## 2. Situação Atual (AS-IS) — Motor V11.6

Em `parity_rules_v11.py`, dois mecanismos prendiam checks à grade:

1. **`continue` no Check #13** (produto online fora da grade): ao encontrar um SKU
   online que não estava em nenhuma grade, o loop encerrava ali (`continue`),
   **pulando todos os checks seguintes** (#2 Bundle, #3 Cross-brand, #8–#12 e o
   Check JOB) — justamente os que comparam XML vs XML.

2. **Gate `if pE:` no Check #4** (preço ausente no SF): só verificava preço ausente
   se o produto existisse na planilha. Produto puramente online com preço zerado
   **nunca era flagrado**.

> Observação técnica: o `continue` do Check #13 foi *adicionado* pelo BRD-002. Na
> v11.6 original, SKUs online fora da grade já passavam pelos checks sistêmicos —
> ou seja, a correção V12 **restaura** o comportamento de paridade original,
> mantendo por cima apenas o flag `online_excess`.

### 2.1 Cenários de falso negativo (reportados)

```
Problema 01 — Produto online sem preço:
  Produto online no XML, fora da grade, com DE e POR zerados.
  V11.6: silêncio (Check #4 exige planilha).

Problema 02 — Auditoria "XML-only" (sem grade):
  Analista sobe só os XMLs para checar problemas internos do SF.
  V11.6: todo produto online cai no Check #13 e o `continue` bloqueia
  #9 (POR>DE), #10 (Margem), #11 (ML) etc. Auditoria inviável.
```

---

## 3. Situação Desejada (TO-BE) — Motor V12

### 3.1 Checks sistêmicos rodam independentemente da grade

Remoção do `continue` do Check #13. SKUs online fora da grade passam a percorrer os
checks que comparam XML vs XML: **#2 Bundle, #3 Cross-brand, #8 Falta preço DE/POR,
#9 POR>DE, #10 Conflito de margem, #11 Divergência ML, #12 Categoria primária** e o
Check JOB.

Permanecem condicionados à grade (exigem a planilha) apenas: **#1 Offline, #4 clássico
(grade), #5 Divergência de preço grade×SF, #6 Searchable, #7 Listas de vitrine.**

### 3.2 Check #4 (Preço Ausente) independente de grade

Adicionado um ramo do Check #4 que dispara `FALTA NO SF (PREÇO)` para produto **online**
com DE e POR ausentes/zerados, esteja ou não na grade. O ramo clássico (dentro de
`if pE:`) é preservado para os SKUs da grade; o novo ramo (`not is_on_grade`) cobre os
puramente online — sem disparo duplo. Mantém a paridade V11.6 de contabilizar
`FALTA NO SF (PREÇO)` como **Preço E Lista** no dashboard.

> **Exclusão obrigatória (descoberta em teste com dados reais):** o ramo novo isenta
> **SKU Técnico** e **Variação Base** (produto-pai), pela mesma regra do Check #13.
> Produto-pai não tem preço próprio — quem precifica é a variação —, então flagrá-lo
> como "sem preço" é falso positivo. Na base de maio/2026, sem essa exclusão, o check
> gerava 97 falsos positivos (majoritariamente SKUs `*-PAI*`); com a exclusão, cai para
> os casos reais.

### 3.3 `online_excess` (Check #13) preservado e ainda gated por marca

O flag `PRODUTO ONLINE FORA DA GRADE` continua disparando **apenas quando a marca tem
grade carregada** nesta execução (`has_nat`/`has_avn`) — preservando a proteção do
BRD-004 contra o flood de falsos positivos ao auditar uma marca por vez. A diferença é
que os SKUs fora da grade agora **também** recebem os checks sistêmicos, em vez de
serem ignorados.

### 3.4 Aposentadoria do aviso de escopo do BRD-004

O aviso informativo "marca fora do escopo desta execução" (contador `scope_skipped` +
banner na UI), introduzido pelo BRD-004, **deixa de fazer sentido**: a marca sem grade
não é mais "ignorada", apenas não recebe os checks que exigem planilha — todos os demais
rodam normalmente. Portanto, `scope_skipped` e o banner são **removidos** por completo.

> **Implicação operacional:** em auditoria de uma marca só (ex.: apenas grade Natura),
> os produtos da outra marca (Avon) online passam a aparecer com erros **sistêmicos**
> no relatório, em vez de ficarem ocultos sob o aviso de escopo. É a consequência
> esperada de "olhar o XML como um todo". A supressão do `online_excess` para a marca
> sem grade **continua** (não reabre o flood do BRD-004).

---

## 4. Análise de Impacto

### 4.1 Impacto técnico

| Arquivo | Mudança | Risco |
|---|---|---|
| `src/core/auditor/parity_rules_v12.py` | **Novo arquivo** — clone da V11.6 + correções 3.1/3.2. Substitui o v11 como motor ativo. | Médio — coberto por testes de paridade |
| `src/core/auditor/parity_rules_v11.py` | **Mantido intocado** como legado/rollback (hash original preservado) | Nulo |
| `src/core/auditor/integrity.py` | Aponta para `parity_rules_v12.py`; `EXPECTED_V12_HASH` recalculado | Nulo — consequência obrigatória |
| `src/core/auditor_engine.py` | Import → v12; remoção do `scope_skipped` (campo, wiring, retorno) | Baixo |
| `src/ui/pages/view_auditor.py` | Remoção do banner `scope_skip` e do método `_refresh_scope_skip_banner` | Baixo |

### 4.2 O que **não** muda (paridade preservada)

- Todos os SKUs **na grade** produzem resultado idêntico ao V11.6 (validado por diff
  v11×v12 em dataset misto: SKUs offline-na-grade, online-ok, online-divergente e
  técnico → 100% iguais).
- SKUs técnicos / variação base seguem isentos de `online_excess`.
- `has_nat`/`has_avn` mantêm o mesmo cálculo.

---

## 5. Critérios de Aceite

| # | Critério | Status |
|---|---|---|
| CA-01 | SKU online sem preço (DE e POR zerados), fora da grade → erro `FALTA NO SF (PREÇO)` | ✅ validado |
| CA-02 | Modo sem-grade: #9 (POR>DE), #11 (ML) etc. rodam normalmente; #13 suprimido | ✅ validado |
| CA-03 | SKU online fora da grade **com** grade da marca carregada → `online_excess` preservado (regressão BRD-002) | ✅ validado |
| CA-04 | Check #4 não duplica para SKUs já cobertos pelo ramo clássico (grade) | ✅ validado |
| CA-05 | SKUs na grade: resultado idêntico V11.6 (diff v11×v12) | ✅ validado |
| CA-06 | Integridade SHA256 (`EXPECTED_V12_HASH`) passa após mudanças | ✅ validado |
| CA-07 | Banner/contador `scope_skipped` removido sem quebrar a UI | ✅ validado (imports OK) |
| CA-08 | Dados reais (maio + junho/2026): com grade, v12 reproduz o motor certificado v11 byte-a-byte (0 regressão, 0 erro removido) | ✅ validado |
| CA-09 | Dados reais (junho): em modo XML-only, v11 antigo detectava `{}` e o v12 surfa `ml` + `margin` (checks sistêmicos liberados) | ✅ validado |

---

## 6. Fora de Escopo

- Alteração da semântica dos checks #5/#6/#7 (continuam exigindo grade — comparam
  planilha × SF, não XML × XML).
- Persistência de qualquer aviso de escopo (removido em definitivo).
- Conceito de "grade híbrida" — não existe.
