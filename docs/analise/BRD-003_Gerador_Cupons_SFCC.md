# Análise de Negócio — Gerador de Cupons SFCC

**Documento:** BRD-003  
**Autor:** Marcos (Analista de Negócios Jr)  
**Data:** 29-05-2026  
**Status:** Aprovado para implementação  
**Branch:** `feat/cupons-sfcc` *(a criar)*

---

## 1. Sumário Executivo

Este documento descreve a análise de negócio para a implementação do **módulo Cupons** no SIC. A iniciativa converte uma ferramenta HTML standalone (v1.6.1) — já validada funcionalmente pelo time de marketing — em um módulo nativo do SIC, adicionando rastreabilidade, versionamento e integração com o histórico de operações.

**Problema central:** O time de marketing monta listas de cupons manualmente e edita o XML para importação no Salesforce Commerce Cloud à mão. O processo é de alta frequência, alto volume e sem nenhuma validação automatizada — o que resulta em falhas de importação por caracteres inválidos, atraso em campanhas e retrabalho.

---

## 2. Situação Atual (AS-IS)

### 2.1 Processo hoje

O fluxo atual para importação de cupons no SFCC é inteiramente manual:

```
Receber lista de cupons (Excel de múltiplas origens)
        ↓
Consolidar planilhas manualmente
        ↓
Montar XML no formato Demandware na mão ← ponto de falha
        ↓
Tentar importar no SFCC
        ↓
Falha de import (caracteres inválidos, minúsculas, duplicatas)
        ↓
Identificar o problema, corrigir, reimportar
        ↓
Atraso ou não-lançamento da campanha no prazo
```

### 2.2 Problemas identificados

| Problema | Causa | Consequência |
|---|---|---|
| Caracteres especiais/acentos no XML | Edição manual sem validação | Import rejeitado pelo SFCC |
| Cupons com letras minúsculas | Padronização manual falha | Comportamento inesperado no SFCC |
| Duplicatas na lista final | Múltiplas fontes sem consolidação | Erros silenciosos ou conflitos |
| Sem rastreabilidade | Nenhum log do que foi importado | Impossível auditar após incidentes |

### 2.3 Perfil do usuário

**Time de marketing** — analistas e coordenadores que criam promoções e campanhas. Não são usuários técnicos; dependem de um processo confiável e sem necessidade de edição manual de XML.

---

## 3. Solução Proposta (TO-BE)

### 3.1 O que a ferramenta faz

Um módulo nativo no SIC que recebe listas de cupons (entrada manual e/ou `.xlsx` com múltiplas abas), valida e consolida os códigos, e gera dois artefatos para download:

1. **XML SFCC** pronto para importação (`coupon/2008-06-17`)
2. **Log Excel** com tudo que foi corrigido ou removido no processo

### 3.2 Regras de validação

| Situação | Ação | Registro no log |
|---|---|---|
| Código com caracteres especiais ou acentos | **Removido do XML** | Aba "Cupons Inválidos" |
| Código com letras minúsculas | **Convertido para maiúsculas** | Aba "Cupons Inválidos" |
| Código duplicado (após normalização) | **Removido silenciosamente** | Aba "Duplicatas" |
| Código válido | Incluído no XML | — |

### 3.3 Formato XML gerado

```xml
<?xml version="1.0" encoding="UTF-8"?>
<coupons xmlns="http://www.demandware.com/xml/impex/coupon/2008-06-17">
    <coupon coupon-id="promo-especial-2026">
        <enabled-flag>true</enabled-flag>
        <multiple-codes/>
    </coupon>
    <coupon-codes coupon-id="promo-especial-2026">
        <code>CUPOM001</code>
        <code>CUPOM002</code>
    </coupon-codes>
</coupons>
```

---

## 4. Quantificação do Problema

### 4.1 Volume e frequência

| Métrica | Estimativa |
|---|---|
| Operações por semana | 3–5 |
| Cupons por operação | Milhares |
| Tempo manual por operação | ~45 min |
| Retrabalho por falha (1–2x/semana) | +30 min |
| **Total de horas manuais/semana** | **~4 h** |
| **Total anual** | **~200 h** |

### 4.2 Custo indireto

O custo de labor (~200 h/ano) é relevante, mas o impacto real está no **risco de campanha**: uma importação que falha na véspera de uma ação promocional pode atrasar ou cancelar o lançamento. Em campanhas de alta temporada (Dia das Mães, Black Friday, Natal), o custo de receita perdida supera qualquer estimativa de horas.

---

## 5. Proposta de Valor

### 5.1 Ganhos diretos

- **Eliminação de erros de importação** por validação automática antes do XML ser gerado
- **Redução de ~4 h/semana** de trabalho manual do time de marketing
- **Autonomia operacional**: o usuário gera o XML sem depender de ajuste técnico

### 5.2 Ganhos pela integração ao SIC (vs. HTML standalone)

| Critério | HTML Standalone | Integrado ao SIC |
|---|---|---|
| Controle de versão | Arquivo avulso, sem controle | Dentro do Git Flow do projeto |
| Quem tem a versão certa? | Quem lembrar de salvar | Toda equipe, sempre atualizada |
| Histórico de operações | Nenhum | Registrado no `history.db` |
| Auditoria pós-incidente | Impossível | Quem rodou, quando, quantos cupons |
| Manutenção futura | Isolada do projeto | Dentro do ciclo de desenvolvimento |
| Validações futuras | Isolada | Pode cruzar com `auditor_engine` |

O argumento mais forte para a integração é a **rastreabilidade**: hoje, se um XML importado causar problema semanas depois, não existe nenhum registro de qual lista foi usada, quem processou ou quais correções foram feitas. No SIC, cada operação fica logada no `history.db`.

---

## 6. Escopo

### 6.1 Dentro do escopo

- Entrada: Coupon ID + texto manual (um código por linha) + `.xlsx` (todas as abas)
- Validação: caracteres especiais (remove) + minúsculas (corrige) + duplicatas (remove)
- Saída: XML SFCC (`coupon/2008-06-17`) + Log Excel de inconsistências
- Registro no histórico do SIC (`history.db`)
- Interface nativa PySide6, aba própria "Cupons" na `MainWindow`

### 6.2 Fora do escopo (por enquanto)

- Validação cruzada com catálogo SFCC (ex.: verificar se coupon ID já existe)
- Envio direto para o SFCC via API
- Fluxo de aprovação ou workflow multi-etapa
- Suporte a formatos além de `.xlsx`/`.xls`

---

## 7. Decisão de Arquitetura

### 7.1 Posicionamento no SIC

O módulo será implementado como uma **aba independente "Cupons"** na `MainWindow`, seguindo o padrão Engine → Worker → View já estabelecido no projeto.

**Arquivos novos:**

```
src/core/cupom_engine.py        ← lógica pura de validação, XML e log Excel
src/workers/worker_cupom.py     ← thread para não bloquear a UI
src/ui/pages/view_cupom.py      ← interface PySide6
```

A decisão de **não integrar ao Exportador** é intencional: o módulo Exportador foi recém consolidado (`feat/merge-sync-gerador` / v1.2.5-beta) e está estabilizando. Adicionar cupons nele agora seria escopo no momento errado.

### 7.2 Dependências

Nenhuma dependência nova. Todas já constam no `requirements.txt`:

| Funcionalidade | Biblioteca já presente |
|---|---|
| Leitura de `.xlsx` | `openpyxl` |
| Geração de XML com escape | `lxml` |
| Geração de log Excel | `openpyxl` |
| Interface gráfica | `PySide6` |
| Histórico de operações | `sqlite3` (stdlib) via `HistoryEngine` |

---

## 8. Riscos

| Risco | Probabilidade | Mitigação |
|---|---|---|
| Scope creep no Exportador | Baixa | Aba independente, sem tocar no Exportador |
| Diferenças de namespace SFCC por ambiente | Baixa | Namespace fixo `2008-06-17`, igual ao HTML validado |
| Usuário esperar envio direto via API | Média | Documentar claramente que o módulo gera o arquivo; import manual no SFCC permanece |

---

## 9. Referências

- Ferramenta HTML de referência: `SFCC Universal Coupon Generator v1.6.1` (validada pelo time de marketing)
- Namespace SFCC: `http://www.demandware.com/xml/impex/coupon/2008-06-17`
- Padrão de XML existente no projeto: `src/core/gerador_engine.py`
- Histórico de operações: `src/core/history_engine.py`
- Análise relacionada: [BRD-002 — Auditor Sincronia Estrita](BRD-002_Auditor_Strict_Online_Consistency.md)
