# Análise de Negócio — Auditor: Validação de Kits Unificada

**Documento:** BRD-007
**Autor:** Marcos (Analista de Negócios Jr)
**Data:** 17-07-2026
**Status:** Aprovado para implementação
**Branch:** `feat/auditor-validacao-kits-unificada` (criada a partir de `main`, não de `dev`)
**Pré-requisitos:** nenhum — feature independente do motor de paridade (V11/V12)

---

## 1. Sumário Executivo

Hoje a validação de composição de Kits (Pai/Filho/Quantidade do XML Salesforce contra
a planilha do BO) vive isolada em **Cadastro → Validação de Kits**, rodando manualmente
e, na prática, só "na virada" do ciclo. Como a grade sofre alterações ao longo do
ciclo, kits podem ficar divergentes por dias sem que ninguém perceba — risco de subir
composição errada pro cliente.

Pedido da Fernanda (time de implantação): trazer essa validação para dentro do
**Auditor**, para que ela rode automaticamente toda vez que uma nova versão de grade
for auditada, em vez de depender de uma checagem manual esporádica.

## 2. Situação Atual (AS-IS)

- `src/core/cadastro_engine.py` (`CadastroEngine`) cruza XML Salesforce
  (`bundled-products`) contra Excel do BO (`COD_VENDA_PAI/FILHO/QUANTIDADE`) e reporta
  divergências (filho ausente, quantidade errada, kit ausente no BO).
- Rodado a partir da tela isolada `src/ui/pages/view_cadastro_kits.py`, via
  `src/workers/worker_cadastro.py`. Sem relação com o fluxo do Auditor.
- O Auditor (`auditor_engine.py._parse_catalogs`) já lê `bundled-products` do mesmo
  XML, mas descarta a quantidade — usa só a lista de componentes para o Check #2
  (Saúde de Bundles/Kits: componente offline/sem preço).

## 3. Situação Desejada (TO-BE)

### 3.1 Planilha do BO como input opcional do Auditor

A tela do Auditor ganha um novo campo de upload **opcional** para a planilha do BO.
**Obrigatório não é opção**: outras operações do Auditor rodam rotineiramente sem essa
planilha em mãos, então torná-la obrigatória bloquearia esses fluxos.

- Planilha **ausente** → Auditor roda exatamente como hoje, sem o check de kit.
- Planilha **presente + Pricebook** → auditoria completa, com o check de kit
  adicionado no mesmo relatório e no mesmo passe.

### 3.1.1 Modo só-kit (BO sem Pricebook)

Para validar **apenas** a composição de kits, exigir Pricebook + 3 catálogos seria
excessivo. Então, quando a planilha **BO é anexada SEM Pricebook**, o Auditor entra
em **modo só-kit**, detectado automaticamente pelos arquivos presentes:

- Exige somente **catálogo(s) (1+)** e a **planilha BO**. Dispensa Pricebook e a regra
  dos 3 catálogos (kit não depende de cross-brand).
- Pula toda a auditoria de preço; popula apenas o card `kit` no dashboard.
- **Não interfere** na auditoria completa: com Pricebook presente, o fluxo de sempre
  roda intacto. O modo só-kit é um caminho aditivo (`AuditorEngine._run_kit_only`).
- O **Certificado Mestre** fica desabilitado no modo só-kit — ele atesta conformidade
  do catálogo inteiro e seria enganoso a partir de uma checagem só de kits.

### 3.2 Reaproveitamento da regra existente (sem redesenho)

A lógica de validação (`CadastroEngine._read_excel`, `._validate`) é reaproveitada
tal como está — é mudança estrutural (onde roda), não uma regra nova. Passos:

1. `auditor_engine._parse_catalogs` passa a capturar também a **quantidade** de cada
   componente do bundle (hoje descartada), equivalente ao que
   `CadastroEngine._read_xml` já faz.
2. Quando a planilha do BO for anexada, `AuditorEngine.run` lê o Excel do BO (mesmo
   parser de `CadastroEngine._read_excel`) e roda a comparação Pai/Filho/Quantidade
   contra os bundles já extraídos do XML.
3. Divergências entram no `AuditResult` como uma nova categoria de erro (não se
   confunde com o Check #2 "bundle", que é sobre online/preço, não composição), com
   entrada correspondente em `CHECK_META` para exibição no dashboard.

### 3.3 Remoção da tela avulsa

Como o Auditor passa a cobrir o caso (de forma opcional), a tela separada
**Cadastro → Validação de Kits** é removida:

- Deletar `src/ui/pages/view_cadastro_kits.py`, `src/core/cadastro_engine.py`,
  `src/workers/worker_cadastro.py` (sem outros consumidores — confirmado).
- Remover o item de submenu "Validação de Kits" e o roteamento de página em
  `src/ui/main_window.py`.

## 4. Análise de Impacto

| Arquivo | Mudança |
|---|---|
| `src/core/auditor_engine.py` | Captura quantidade nos bundles; novo parâmetro opcional (planilha BO) em `run`; nova função de validação Pai/Filho/Quantidade; nova entrada em `CHECK_META` |
| `src/ui/pages/view_auditor.py` | Novo campo de upload opcional (planilha BO) |
| `src/ui/pages/view_cadastro_kits.py` | **Removido** |
| `src/core/cadastro_engine.py` | **Removido** (lógica migrada para `auditor_engine.py`) |
| `src/workers/worker_cadastro.py` | **Removido** |
| `src/ui/main_window.py` | Remove submenu/roteamento de "Validação de Kits" |

**Nota de branch:** criada a partir de `main` (não `dev`) porque a `dev` está com
mudanças ainda não validadas (motor V12 — BRD-005/BRD-006). Essa feature não depende
do motor de paridade, então parte de uma base estável. Fila de QA do Edgar está
temporariamente sem resposta; entrega segue sem aguardar liberação formal.

## 5. Critérios de Aceite

| # | Critério |
|---|---|
| CA-01 | Auditor sem planilha BO anexada → comportamento idêntico ao atual, nenhum check novo dispara |
| CA-02 | Auditor com planilha BO anexada → divergências de kit (ausente/quantidade errada) aparecem no relatório |
| CA-03 | Resultado do novo check é idêntico ao que `CadastroEngine` produzia para o mesmo par XML+Excel (paridade) |
| CA-04 | Tela Cadastro → Validação de Kits não existe mais; nenhuma referência quebrada em `main_window.py` |
| CA-05 | Modo só-kit: BO + catálogo(s) sem Pricebook roda o check de kit e popula só o card `kit` |
| CA-06 | Modo só-kit aceita 1+ catálogos (regra dos 3 não se aplica sem Pricebook) |
| CA-07 | Com Pricebook presente, a auditoria completa roda intacta (modo só-kit não é acionado) |
| CA-08 | Certificado Mestre fica desabilitado no modo só-kit |

## 6. Fora de Escopo

- Alteração da regra de comparação Pai/Filho/Quantidade em si.
- Unificação de Gestor GCP ou Pontuação ao Auditor (permanecem como estão).
- Qualquer mudança no motor de paridade V11/V12.
