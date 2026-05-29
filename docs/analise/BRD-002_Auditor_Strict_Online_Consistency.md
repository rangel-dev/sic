# Análise de Negócio — Auditor: Sincronia Estrita de Catálogo (Regra Inversa)

**Documento:** BRD-002  
**Autor:** Marcos (Analista de Negócios Jr)  
**Data:** 28-05-2026  
**Status:** Aprovado para implementação  
**Branch:** `feat/auditor-strict-online-check`

---

## 1. Sumário Executivo

Este documento descreve a análise de negócio para a implementação do **Check #13 — Produto Online Fora da Grade** no módulo Auditor do SIC. A iniciativa complementa a validação existente (Check #1) com a **regra inversa**: detectar produtos que estão ativos no Salesforce (`online-flag=true`) mas que **não constam em nenhuma Grade de Ativação carregada**.

**Problema central:** Hoje o Auditor garante que "o que está na grade está online". Mas não garante que "o que está online está na grade". Essa lacuna permite que o site exponha produtos de campanhas encerradas, produtos descontinuados ou itens sem estratégia comercial vigente.

---

## 2. Situação Atual (AS-IS)

### 2.1 O Check #1 existente

O motor de auditoria hoje executa a seguinte regra:

```
SE produto está na Grade de Ativação (Excel)
E produto está offline no Salesforce (online-flag ≠ true)
ENTÃO → Erro: "PRODUTO OFFLINE (Ação Comercial Exigida)"
```

| O que é validado | O que **não** é validado |
|---|---|
| Produto planejado que está offline | Produto ativo que não foi planejado |
| Risco de perda de receita por produto "apagado" | Risco de venda de produto "esquecido ligado" |

### 2.2 Cenário de risco não coberto

```
Campanha C12 encerra em 28/05.
Time de operação gera XMLs para a campanha C13.
O Auditor valida C13 e aprova.
Porém: 47 SKUs da C12 continuam com online-flag=true no Salesforce.
Resultado: esses produtos são vendidos sem preço planejado, sem estoque estratégico,
e sem presença na grade — totalmente fora do radar do Pricing.
```

Este cenário é **silencioso**: nenhuma divergência é gerada, nenhum alerta é disparado.

---

## 3. Situação Desejada (TO-BE)

### 3.1 Nova regra de negócio

```
SE produto possui online-flag=true no Salesforce
E produto NÃO está presente em nenhuma Grade de Ativação carregada
E produto NÃO é um SKU Técnico (nome em caixa alta)
E produto NÃO é uma Variação Base (Variation Group)
ENTÃO → Erro: "PRODUTO ONLINE FORA DA GRADE (Deveria estar Offline)"
```

### 3.2 Exceções (sem ruído)

| Exceção | Motivo | Como o sistema identifica |
|---|---|---|
| **SKUs Técnicos** | Itens de infraestrutura que nunca aparecem na grade, mas precisam existir no catálogo | Nome em CAIXA ALTA (campo `name` no XML) — mapeado em `technical_skus` já presente na engine |
| **Variação Base** | Produto pai de variações (cor/tamanho) que precisa estar online para as variações funcionarem | Tipo `variation-group` no XML — mapeado em `variation_bases` já presente na engine |

Ambas as exceções já são estruturas de dados populadas pelo `AuditorEngine._parse_catalogs()`. **Nenhuma lógica nova de parsing é necessária.**

---

## 4. Análise de Impacto

### 4.1 Impacto no negócio

| Área | Impacto |
|---|---|
| **Governança de Catálogo** | Visibilidade total sobre produtos ativos fora do planejamento comercial |
| **Controle Operacional** | Prevenção de vendas sem preço estratégico ou sem estoque comprometido |
| **Limpeza de Campanha** | Identificação pós-campanha de SKUs que "esqueceram de desligar" |
| **Compliance Comercial** | Rastreabilidade: todo produto ativo no site tem justificativa na grade |

### 4.2 Impacto técnico (escopo mínimo — 4 arquivos)

| Arquivo | Tipo de mudança | Risco |
|---|---|---|
| `src/core/auditor/parity_rules_v11.py` | Adição de Check #13 (nova condição) | Baixo — lógica aditiva, não modifica checks existentes |
| `src/core/auditor/integrity.py` | Atualização do hash SHA256 | Nulo — consequência obrigatória da mudança acima |
| `src/core/auditor_engine.py` | (1) Nova entrada em `ERROR_META`; (2) Incluir `online_status.keys()` em `all_skus` | Baixo — mudança aditiva em dois pontos isolados |
| `src/ui/pages/view_auditor.py` | Adicionar novo `ErrorCard` no dashboard | Nulo — padrão já estabelecido para os 12 cards existentes |

### 4.3 Gap técnico identificado na análise

O loop de `_cross_validate()` constrói `all_skus` a partir de 5 fontes:

```python
all_skus.update(prices_xml.keys())      # SKUs com preço no Pricebook
all_skus.update(excel_prices.keys())    # SKUs na Grade de Ativação
all_skus.update(cat_missing_primary.keys())
all_skus.update(bundles.keys())
all_skus.update(job_errors.keys())
```

**Lacuna:** SKUs que estão `online=true` no catálogo mas que **não possuem preço no Pricebook** e **não estão na grade** nunca entram em `all_skus`. Eles são invisíveis ao loop.

**Solução:** Adicionar uma 6ª fonte restrita:
```python
all_skus.update(sku for sku, online in online_status.items() if online)
```

Isso garante que todo SKU marcado como `online=true` no Salesforce seja avaliado, sem ampliar desnecessariamente o universo de validação para SKUs offline.

---

## 5. Critérios de Aceite

| # | Critério | Como validar |
|---|---|---|
| CA-01 | SKU com `online-flag=true` ausente da grade → gera erro `online_excess` | Rodar auditoria com catálogo que contém SKUs extras; confirmar card preenchido |
| CA-02 | SKU Técnico (nome em CAIXA ALTA) com `online=true` e fora da grade → **sem erro** | Verificar que `technical_skus` filtra corretamente |
| CA-03 | Variation Group com `online=true` e fora da grade → **sem erro** | Verificar que `variation_bases` filtra corretamente |
| CA-04 | Checks #1–#12 continuam funcionando sem regressão | Rodar auditoria com conjunto de dados de referência conhecido |
| CA-05 | Integridade SHA256 passa após atualização do hash | App inicializa sem `integrity_error` |
| CA-06 | ErrorCard "Produto Online Fora da Grade" aparece no dashboard | Inspeção visual da UI |

---

## 6. Perguntas em Aberto

| # | Pergunta | Responsável | Decisão |
|---|---|---|---|
| P-01 | Após Check #13 gerar um erro `online_excess`, os demais checks devem continuar ou fazer `continue`? | Gestor / Pricing | **Fechada:** `continue`. O produto não tem dados de Excel para comparar; processar os demais checks geraria falsos positivos. |
| P-02 | O novo check deve ser exibido no histórico e no certificado PDF? | Gestor | **Fechada:** Ver análise abaixo. |
| P-03 | O painel de IA deve receber contexto extra para interpretar `online_excess`? | Marcos | **Fechada:** Sim. Baixo esforço — incluir o novo código no prompt de diagnóstico. |

### Detalhamento P-02 — Histórico e Certificado

**Histórico (`HistoryEngine`):** Automático. O registro de histórico já captura o total de divergências (`"X SKUs, Y divergências."`). Nenhuma mudança necessária — o novo check contribui para o `total` sem qualquer código adicional.

**Certificado PDF (`CertificateEngine`):** Dois comportamentos:
1. **Bloqueio automático:** O certificado só é emitido com `total == 0`. Se houver erros `online_excess`, a emissão já é bloqueada. Nenhuma mudança necessária para o gate.
2. **Tabela de conformidade:** A tabela é estática (`_COMPLIANCE_CHECKS`, 4 linhas hardcoded). Ela não menciona "Sincronia de Catálogo" — essa dimensão fica sem cobertura visual no certificado. **Decisão:** adicionar a 5ª linha à tabela.

Impacto: **+1 arquivo** ao escopo — `src/core/certificate_engine.py`.

---

## 7. Fora de Escopo

- Modificação automática do `online-flag` no Salesforce (ação manual do operador).
- Integração com sistema de workflows para abertura de tickets.
- Relatório separado de "limpeza pós-campanha" (pode ser demanda futura).

---

## 8. Entrega de Valor

```
Antes: Auditor cobre o vetor "Planned → Active"
       (garante que o planejado está ativo)

Depois: Auditor cobre os dois vetores:
        "Planned → Active"  (Check #1 — existente)
        "Active → Planned"  (Check #13 — novo)

Resultado: Sincronia estrita bidirecional entre Grade de Ativação e Catálogo Salesforce.
```
