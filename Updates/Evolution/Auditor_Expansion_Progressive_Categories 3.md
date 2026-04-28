# Expansão de Categorias Proibidas (Conflito de Margem)

Este documento detalha as categorias monitoradas pelo módulo Auditor para evitar o "Conflito de Margem" (também conhecido como Regra do Progressivo), onde produtos em promoção são indevidamente atribuídos a categorias que já possuem descontos automáticos ou regras de margem estritas.

## Contexto Atual no Código

Atualmente, o motor de auditoria (`auditor_engine.py`) utiliza a constante `PROHIBITED_CATEGORIES` para identificar SKUs que não podem estar em promoção (`POR < DE`).

### Categorias Monitoradas (v1.1.0):

| Marca | ID da Categoria (Salesforce) | Nome Amigável |
| :--- | :--- | :--- |
| **Natura** | `promocao-da-semana` | Promoção da Semana |
| **Natura** | `LISTA_01` | Lista 01 (Vitrines) |
| **Avon** | `desconto-progressivo` | Desconto Progressivo |
| **Avon** | `lista-01` | Lista 01 (Vitrines) |
| **Minha Loja** | `promocao-da-semana` | Promoção da Semana (ML) |
| **Minha Loja** | `desconto-progressivo` | Desconto Progressivo (ML) |

## Identificação de Catálogos e Pricebooks

O sistema identifica as marcas e catálogos através de substrings nos IDs dos arquivos XML. Abaixo estão os padrões reconhecidos pelo motor de auditoria e geração:

| Loja / Marca | ID do Catálogo (Salesforce) | Pricebook DE (Lista) | Pricebook POR (Sale) |
| :--- | :--- | :--- | :--- |
| **Natura** | `natura-br` | `br-natura-brazil-list-prices` | `br-natura-brazil-sale-prices` |
| **Avon** | `avon-br` | `brl-avon-brazil-list-prices` | `brl-avon-brazil-sale-prices` |
| **Minha Loja** | `cbbrazil` (ou `cb-br`) | `br-cb-brazil-list-prices` | `br-cb-brazil-sale-prices` |

> **Nota Técnica:** O motor utiliza busca por substring. Por exemplo, qualquer ID de catálogo que contenha `natura` será processado com as regras da Natura. O catálogo Minha Loja é identificado pelas strings `cb-br`, `cbbrazil` ou `cbcom`.

## Lógica de Validação

A regra é aplicada no arquivo `parity_rules_v11.py` sob o Check #10:
1. O sistema identifica se o produto possui preço promocional ativo (`POR < DE`).
2. O sistema verifica se o produto está associado a qualquer uma das categorias acima no XML de Catálogo.
3. Se ambas as condições forem verdadeiras, é gerado o erro **"CONFLITO PROG"** no dashboard.

## Expansão Planejada (Novas Categorias)

As seguintes categorias foram aprovadas para inclusão na regra de bloqueio de promoção no próximo ciclo de desenvolvimento:

| Marca | ID da Categoria | Status |
| :--- | :--- | :--- |
| **Natura** | `monte-seu-kit` | 🚀 Planejado |
| **Natura** | `LISTA_02` | 🚀 Planejado |
| **Minha Loja** | `monte-seu-kit` | 🚀 Planejado |

## Lógica de Validação

---
*Documento gerado para auxiliar o time de Governança na definição de novas travas de segurança.*
