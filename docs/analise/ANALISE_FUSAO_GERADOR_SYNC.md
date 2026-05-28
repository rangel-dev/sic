# Análise de Negócio — Fusão dos Módulos Gerador e Sync

**Documento:** BRD-001  
**Autor:** Marcos (Analista de Negócios Jr)  
**Data:** 27-05-2026  
**Status:** Decisões registradas — pronto para implementação  
**Branch:** `feat/merge-sync-gerador`

---

## 1. Sumário Executivo

Este documento descreve a análise de negócio para a fusão dos módulos **Gerador** e **Sync** dentro do SIC (Sistema de Inteligência Corporativa). A iniciativa tem como objetivo eliminar redundâncias de fluxo de trabalho do usuário, consolidar a experiência de processamento de catálogos em uma única interface e reduzir o custo cognitivo de operar dois módulos separados que compartilham a mesma origem de dados.

**Motivação principal:** Hoje, o analista de dados precisa usar dois módulos distintos para processar o mesmo arquivo Excel de entrada. A fusão visa que uma única operação produza todos os artefatos necessários (XML de Pricebook + XML de Catálogo).

---

## 2. Situação Atual (AS-IS)

### 2.1 Módulo Gerador

| Atributo | Descrição |
|---|---|
| **Responsabilidade** | Converte planilha Excel em XML de **Pricebook** (preços DE e POR) |
| **Entrada** | Arquivo(s) Excel com aba "GRADE DE ATIVAÇÃO" + (opcional) XML base para modo Delta |
| **Saída** | 1 arquivo XML no formato Salesforce Demandware Pricebook |
| **Namespace XML** | `http://www.demandware.com/xml/impex/pricebook/2006-10-31` |
| **Marcas suportadas** | Natura, Avon, Minha Loja (CB — sempre incluída) |
| **Modos de operação** | `full` (todos os produtos) e `delta` (somente preços alterados) |
| **Lógica central** | Lê colunas **DE** e **POR** (preços), detecta marca pelo prefixo SKU |
| **Complexidade** | Baixa — regras simples de filtragem numérica |

**Fluxo atual do usuário:**

```
Usuário abre aba Gerador
→ Seleciona arquivo Excel
→ Escolhe modo (Full/Delta)
→ (Opcional) carrega XML base para Delta
→ Clica em "Gerar"
→ Baixa XML de Pricebook
```

---

### 2.2 Módulo Sync

| Atributo | Descrição |
|---|---|
| **Responsabilidade** | Sincroniza **atributos de catálogo** (visibilidade, flags online, selos de marketing, listas de categorias) |
| **Entrada** | Arquivo(s) Excel + XML(s) do catálogo atual (Master Data) |
| **Saída** | 1 arquivo XML delta no formato Salesforce Demandware Catalog |
| **Namespace XML** | `http://www.demandware.com/xml/impex/catalog/2006-10-31` |
| **Marcas suportadas** | Natura, Avon |
| **Modos de operação** | Único (sempre delta — compara Excel vs. XML atual) |
| **Lógica central** | Regras de governança V11.1 (online/searchable flags, selos, listas, mestres/variantes) |
| **Complexidade** | Alta — regras de negócio V11.1 com múltiplos critérios |

**Fluxo atual do usuário:**

```
Usuário abre aba Sync
→ Seleciona arquivo Excel (o mesmo de antes)
→ Seleciona XML(s) do catálogo atual
→ Clica em "Sincronizar"
→ Baixa XML de Catálogo
```

---

### 2.3 Problema Central Identificado

> O analista de dados usa **o mesmo arquivo Excel** como entrada em ambos os módulos, mas precisa alternar entre abas diferentes para gerar os dois artefatos XML necessários para uma única operação de catálogo.

Isso causa:

- **Retrabalho de seleção de arquivo** — o mesmo Excel é carregado duas vezes
- **Risco de inconsistência** — o usuário pode usar versões diferentes do Excel em cada módulo por erro
- **Fragmentação de contexto** — o fluxo de um ciclo de atualização está espalhado em dois lugares
- **Custo cognitivo** — o usuário precisa saber quando usar cada módulo e em que ordem

---

## 3. Análise de Sobreposição (GAP Analysis)

### 3.1 O que os módulos compartilham

| Elemento compartilhado | Gerador | Sync | Observação |
|---|---|---|---|
| Arquivo de entrada Excel | ✅ | ✅ | Mesma aba "GRADE DE ATIVAÇÃO" |
| Detecção de marca por SKU | ✅ | ✅ | Lógica NATBRA- / AVNBRA- duplicada |
| Parsing de SKUs válidos | ✅ | ✅ | Filtro por prefixo idêntico |
| Interface de progresso | ✅ | ✅ | Mesmo padrão `_progress(pct, msg)` |
| Plataforma alvo | ✅ | ✅ | Salesforce Demandware |
| Contexto de marca (Natura/Avon) | ✅ | ✅ | Mesma lógica de dominância por contagem |

### 3.2 O que os módulos NÃO compartilham

| Elemento | Gerador | Sync | Impacto |
|---|---|---|---|
| **Dado extraído do Excel** | Preços (DE/POR — numérico) | Visibilidade, selos, listas (flags + texto) | Alto — leituras distintas, colunas distintas |
| **XML de entrada obrigatório** | Não (só no modo Delta) | Sim (catálogo atual é obrigatório) | Alto — fluxo de entrada diferente |
| **Namespace XML de saída** | Pricebook | Catalog | Alto — arquivos XML incompatíveis |
| **Regras de negócio** | Simples (filtro numérico) | Complexas (V11.1 com Facão, Mestres, Selos) | Alto — lógica não intercambiável |
| **Estrutura do resultado** | `dict` simples | `SyncResult` (dataclass com warnings, report) | Médio — contratos de API distintos |
| **Minha Loja (CB)** | Sempre incluída | Não se aplica | Baixo |

---

## 4. Situação Desejada (TO-BE)

### 4.1 Visão do Produto

Criar um **módulo unificado** chamado **"Exportador"** que, a partir de uma única seleção de arquivo Excel, permita ao usuário gerar um ou ambos os artefatos XML (Pricebook e/ou Catálogo) em uma operação integrada.

### 4.2 Fluxo Proposto

```
Usuário abre módulo Exportador
→ Passo 1: Seleciona o(s) arquivo(s) Excel
→ Passo 2: Escolhe o(s) artefato(s) a gerar:
     ├── [✅ Pricebook]  → habilita: Modo [Full] ou [Delta + arquivo base XML]
     └── [  Catálogo]   → habilita: campo de seleção do(s) XML(s) do catálogo atual (obrigatório)
→ Passo 3: Clica em "Exportar"
→ Barra de progresso unificada exibe etapas de cada engine ativa
→ Resultados (independentes, exibidos conforme o que foi gerado):
     ├── [Baixar Pricebook XML]   (se Pricebook foi gerado)
     ├── [Baixar Catálogo XML]    (se Catálogo foi gerado)
     └── [Baixar Relatório]       (relatório do Sync — exibido separadamente, apenas se Catálogo foi gerado)
```

### 4.3 O Que Muda vs. O Que Permanece

| Aspecto | Decisão | Justificativa |
|---|---|---|
| `GeradorEngine` (classe) | **Permanece inalterada** | Lógica correta e testada; não há benefício em alterar |
| `SyncEngine` (classe) | **Permanece inalterada** | Regras V11.1 complexas; risco alto de regressão ao refatorar |
| Leitura de Excel | **Extrair para módulo utilitário** | Eliminar duplicação de código e garantir consistência |
| Detecção de marca | **Extrair para módulo utilitário** | Duplicação identificada — mesma lógica nos dois engines |
| Aba Gerador (UI) | **Removida — sem legado** | Substituída integralmente pelo módulo Exportador |
| Aba Sync (UI) | **Removida — sem legado** | Substituída integralmente pelo módulo Exportador |
| Histórico de operações | **Manter separado por tipo** | O banco `history.db` registra por tipo de operação |

---

## 5. Regras de Negócio — Restrições e Preservação

As seguintes regras de negócio existentes devem ser **preservadas integralmente** na fusão:

| ID | Regra | Módulo de Origem | Criticidade |
|---|---|---|---|
| RN-01 | Detecção automática de marca por prefixo SKU (NATBRA-/AVNBRA-) | Ambos | Alta |
| RN-02 | Minha Loja (CB) deve SEMPRE aparecer no Pricebook | Gerador | Alta |
| RN-03 | Modo Delta de Pricebook — só produtos com preço alterado (tolerância 0,01) | Gerador | Alta |
| RN-04 | Regra Facão — corta visibilidade de produtos com nome em CAIXA ALTA | Sync | Alta |
| RN-05 | Mestres ativos apenas se houver pelo menos 1 variante ativa na Grade | Sync | Alta |
| RN-06 | Regra de Antiguidade — XMLs com menos de 10 minutos geram aviso | Sync | Média |
| RN-07 | Sanitização de Selos — limpa atributo `natg_preferencialProductSlot` se sem selo na Grade | Sync | Alta |
| RN-08 | Formato JSON de Selo deve ser compatível com V14.0 JS (separators=(',',':')) | Sync | Alta |
| RN-09 | Filtro de contaminação — arquivo Natura não deve incluir SKUs AVNBRA- e vice-versa | Gerador | Alta |
| RN-10 | Arquivo Excel com aba oculta "GRADE DE ATIVAÇÃO" deve retornar erro explícito | Gerador | Média |

---

## 6. Análise de Riscos

| Risco | Probabilidade | Impacto | Mitigação |
|---|---|---|---|
| Regressão nas regras V11.1 do Sync | Médio | Alto | Não alterar `SyncEngine`; apenas envolvê-la em nova UI |
| Usuário confundir entrada obrigatória de XML do Sync | Alto | Médio | UI com validação clara: campo de XML bloqueado se "Catálogo" desmarcado |
| Histórico de operações registrado de forma inconsistente | Médio | Médio | Definir novo `operation_type` no `history.db` para operações combinadas |
| Arquivo Excel com dados de Pricebook e Sync conflitantes | Baixo | Médio | Engines independentes — cada uma lê apenas as colunas que lhe competem |
| Performance degradada ao rodar as duas engines sequencialmente | Baixo | Baixo | Engines são CPU-bound, não bloqueiam UI se rodadas em thread separada |

---

## 7. Plano de Implementação (Alto Nível)

> ⚠️ Este é um plano de análise. A ordem e os detalhes técnicos devem ser revisados pelo desenvolvedor antes da execução.

### Fase 1 — Preparação (Sem alterar comportamento)

- [ ] Criar `src/core/excel_reader.py` com função utilitária de leitura de Excel e detecção de marca (extrair lógica duplicada)
- [ ] Atualizar `GeradorEngine` e `SyncEngine` para usar o utilitário (sem alterar resultados)
- [ ] Validar que todos os testes existentes continuam passando

### Fase 2 — Nova UI Unificada

- [ ] Criar `src/ui/views/exportador_view.py` (nova aba unificada — módulo Exportador)
- [ ] Implementar seleção de Excel (aceitar múltiplos arquivos)
- [ ] Implementar seleção de XML de catálogo (obrigatório apenas se "Catálogo" estiver marcado)
- [ ] Implementar checkboxes de artefatos: Pricebook e/ou Catálogo
- [ ] Implementar configuração de modo (Full/Delta) para o Pricebook
- [ ] Implementar barra de progresso unificada que exibe etapas de cada engine
- [ ] Implementar dois botões de download independentes no resultado

### Fase 3 — Integração e Depreciação

- [x] Registrar operação unificada no `history.db` com novo tipo (`"Exportador"`)
- [x] Remover abas "Gerador" e "Sync" da navegação principal (arquivos excluídos)
- [x] Atualizar documentação (`MANUAL.md` atualizado com seção Exportador)
- [ ] Teste de regressão com arquivos reais de Natura e Avon *(a executar manualmente)*

---

## 8. Decisões Registradas

Questões levantadas durante a análise e respondidas pelo negócio em 2026-05-27:

| # | Questão | Decisão | Impacto |
|---|---|---|---|
| 1 | O usuário sempre gera Pricebook **e** Catálogo juntos? | **Não** — há cenários onde somente o Pricebook é necessário | Checkboxes independentes confirmados; fluxo deve permitir selecionar apenas um artefato |
| 2 | As abas "Gerador" e "Sync" são removidas ou mantidas como legado? | **Removidas — sem legado** | Fase 3 deve excluir completamente ambas as abas da navegação |
| 3 | Qual o nome do novo módulo? | **Exportador** | UI, histórico (`history.db`) e código-fonte devem usar "exportador" como identificador |
| 4 | O relatório de auditoria será unificado ou separado por engine? | **Separado** — cada engine mantém seu próprio relatório | O relatório do Sync é exibido individualmente no resultado; o Gerador não gera relatório |

---

## 9. Glossário

| Termo | Significado |
|---|---|
| **Pricebook** | Arquivo XML com tabela de preços DE (lista) e POR (promocional) para importação no Demandware |
| **Catalog XML** | Arquivo XML com atributos de produto (online, searchable, selos, listas) para importação no Demandware |
| **Delta** | Arquivo contendo apenas as diferenças em relação ao estado atual — reduz tamanho e risco de importação |
| **GRADE DE ATIVAÇÃO** | Aba padrão do Excel de catálogo que contém a lista de produtos ativos no ciclo |
| **Facão** | Regra V11.1 que remove da vitrine produtos cujo nome está inteiramente em caixa alta |
| **Mestre / Variante** | Estrutura do Demandware: produto mestre agrupa variações; mestre ativo = pelo menos 1 variante ativa |
| **SKU** | Código único de produto. Prefixo NATBRA- (Natura) ou AVNBRA- (Avon) |
| **CB / Minha Loja** | Marca Canal Beleza, sempre presente no Pricebook gerado |
| **Selo** | Atributo de marketing do produto (ex: "Novo", "Oferta") armazenado como JSON no campo `natg_preferencialProductSlot` |

---

*Fim do documento. Todas as decisões da Seção 8 foram registradas em 27-05-2026. Documento pronto para handoff ao desenvolvimento.*
