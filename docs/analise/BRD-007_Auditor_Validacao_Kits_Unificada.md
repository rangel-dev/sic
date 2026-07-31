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

---

## 7. Adendo de Implementação (v2) — 29-07-2026

A implementação real, entregue em 6 commits ao longo do ciclo
(`ed2458a`, `f1a53a1`, `a996941`, `21a9526`, `bbef0b9`, `7ff4f3c`), evoluiu
além do desenho original deste documento. A seção §3.2 ("reaproveitamento
sem redesenho") e o CA-03 ("paridade com `CadastroEngine`") descrevem o
plano inicial, **não** o estado atual — este adendo é a referência
vigente; o corpo do documento acima fica como registro histórico da decisão
original.

### 7.1 O motor virou dirigido pela Grade (redesenho, não previsto)

A regra Pai/Filho/Quantidade original do `CadastroEngine` foi reescrita.
Universo de auditoria, chaveamento e identidade de versão mudaram por
completo — ver `src/core/auditor/kit_validation.py`:

- **Universo auditado = Grade, não catálogo.** A Grade de Ativação passou a
  listar quais SKUs são kits do ciclo (coluna "TIPO MATERIAL" = `ZEST`,
  `GradeIndex.kits`) e qual o Código de Material (CM) vigente de cada um
  (`GradeIndex.cm`). Isso viabiliza um check impossível no desenho original:
  "kit ativo na Grade sem composição no catálogo" (`KIND_KIT_SEM_BUNDLE`).
- **Identidade de versão SKU+CM.** O BO é tratado como histórico acumulado —
  o mesmo SKU reaparece com vários CMs ao longo dos ciclos. A versão vigente
  de um kit é resolvida por `MATERIAL_PAI == CM da grade` (`BoIndex.versoes`),
  não pela união ingênua de todas as linhas do BO.
- **Suporte a marcas.** Catálogos e a Grade são chaveados por `(marca, SKU)`
  (`_brand_from_pid`, `_prefixo`) — corrige o `"NATBRA-"` hardcoded do
  `CadastroEngine` legado, que quebrava kits Avon.
- **8 kinds de divergência** (`KIND_KIT_SEM_BUNDLE`, `KIND_AUSENTE_NO_BO`,
  `KIND_MATERIAL_PAI_DIV`, `KIND_MATERIAL_FILHO_DIV`, `KIND_FILHO_AUSENTE_BO`,
  `KIND_QTD_ERRADA`, `KIND_FILHO_FALTANDO_SF`, `KIND_FILHO_FORA_DA_GRADE`) —
  o BRD original previa só 2 ("ausente"/"quantidade errada").
- **Degradação segura sem "TIPO MATERIAL".** Se a Grade não tiver essa
  coluna, `GradeIndex.kits` fica vazio e o motor cai no modo antigo,
  dirigido pelo catálogo (filtrando por `GradeIndex.cm` quando existir, ou
  auditando tudo se nem isso existir). Não documentado no texto original,
  mas intencional (ver docstring de `GradeIndex` no código).
- **Grade tornou-se obrigatória junto com o BO** na UI (`view_auditor.py`),
  inclusive na auditoria completa — requisito não previsto no §3.1 original
  (que só descrevia o BO como opcional).

### 7.2 UI muito além do "novo campo de upload opcional" (§4 original)

`src/ui/pages/view_auditor.py` ganhou um capítulo dedicado "VALIDAÇÃO DE
KITS (BO)": stat cards, grade de 8 cards clicáveis por subtipo com filtro
próprio, pills de filtro de marca **independentes** do filtro da auditoria
tradicional, tabela dedicada, botões próprios de exportação (Relatório de
Kits, XML de Correção), empty-state anti-falso-verde e supressão do
diagnóstico de IA no modo só-kit. CA-05 ("popula só o card `kit`") deve ser
lido hoje como "popula só o capítulo de Kits" — o card `kit` do dashboard
tradicional foi removido (`a996941`), kits não entram mais em
`ERROR_META`/`result.errors`/`result.stats["total"]`.

### 7.3 Relatório Excel de kits (não previsto)

Aba "Resumo" em formato matriz (Indicador × Natura × Avon × Total), com
estilo condicional, e uma aba de detalhe por marca — além do relatório
principal do Auditor.

### 7.4 CA-03 (paridade com `CadastroEngine`) — status: substituído

Paridade estrita com o `CadastroEngine` legado **não vale mais** por
desenho (ver §7.1). Diferenças relevantes: universo auditado, chave de
kit (`(marca, SKU)` vs. SKU puro), resolução de composição por versão
(SKU+CM) vs. união de todas as linhas do BO, e `_so_numeros` corrigido
para tratar o artefato `.0` de célula numérica (`73667.0` → `73667`, não
`736670` como no legado — correção de bug que quebra paridade byte-a-byte
de propósito).

### 7.5 Correções críticas aplicadas (29-07-2026)

Uma auditoria de conformidade pós-implementação encontrou e corrigiu os
seguintes riscos de falso-verde/dado incorreto, todos ativos até este
adendo:

- **Webhook de "Operação Saudável" falso no modo só-kit.** `result.errors`
  vem vazio nesse modo (kits não entram em `ERROR_META`), então o botão de
  webhook enviava ao Google Chat "0 Divergências" mesmo com kits
  divergentes reais. Corrigido: botão desabilitado no modo só-kit + guard
  no handler (`_send_webhook`).
- **Exportações tradicionais quebravam no modo só-kit.** Os botões
  "Relatório"/"Evidências (Full)" ficavam habilitados, mas `_export_excel`
  não tem nenhuma aba pra escrever nesse modo → erro cru do openpyxl.
  Corrigido: desabilitados no modo só-kit (o capítulo de Kits já tem
  botões próprios).
- **Gate do Certificado Mestre era só visual (CA-08).** `_export_master_audit`
  validava apenas `stats["total"] != 0`, condição trivialmente satisfeita
  (`0`) no modo só-kit. Corrigido: guard explícito de `_last_kit_only` no
  início do handler (defesa em profundidade — o botão já fica desabilitado).
- **`catalog-id` fixo em Natura no XML de Correção.** `_build_correction_xml`
  sempre escrevia `catalog-id="natura-br-storefront-catalog"`, mesmo para
  kits Avon — o arquivo de correção de um kit Avon apontava pro catálogo
  errado. Corrigido: `_read_kits_from_xml` agora captura o `catalog-id`
  real de origem por marca; `KitAuditData.correction_xmls` é
  `dict[marca, xml]` (um envelope `<catalog>` por marca, já que cada uma
  tem um `catalog-id` diferente — não dá pra combinar num XML só). A UI
  salva um arquivo por marca quando há mais de uma. Coberto por
  `tests/test_kit_validation_correction_xml.py`.

### 7.6 Limitações conhecidas (não corrigidas nesta rodada)

Achados de severidade média/baixa da mesma auditoria, sem fix aplicado —
registrados para uma futura rodada:

- **Histórico enganoso no modo só-kit**: a entrada de histórico registra
  "0 SKUs, 0 divergências" mesmo quando `kit_data.stats["erro"] > 0`.
- **Falha silenciosa na leitura do BO** (modo completo, com Pricebook): uma
  exceção ao ler o BO só vai para `print()`; o capítulo de Kits some da
  tela sem nenhum aviso, indistinguível de "BO não anexado".
- **Degradação sem "TIPO MATERIAL" é silenciosa**: nenhum aviso na UI
  quando a Grade não tem a coluna e o motor cai no modo antigo — o usuário
  não sabe que o check de kit "sem composição" não pode rodar.
- **Bundle fora da Grade (ZEST) nunca é auditado**: com `GradeIndex.kits`
  populado, `_alvos` só audita os kits marcados na Grade — um
  `bundled-products` publicado no SF sem essa marcação é ignorado em
  silêncio (não existe o equivalente de `KIND_FILHO_FORA_DA_GRADE` para o
  pai).
- **Composição não-determinística** quando o mesmo SKU aparece em mais de
  um catálogo de entrada (marca + Minha Loja) com composições diferentes:
  o primeiro catálogo processado vence, e a ordem depende da seleção do
  usuário no `QFileDialog`.
- **BO sem nenhum catálogo** (chamada direta ao motor, fora da UI): gera
  uma enxurrada de `KIND_KIT_SEM_BUNDLE` — só a UI bloqueia esse caso hoje.
- **`KIND_FILHO_FORA_DA_GRADE` assume a marca do pai** ao consultar
  `GradeIndex.cm` — componente legitimamente cross-brand geraria falso
  positivo.
- **`BoIndex.cms_por_sku` é global**, não por par pai-filho — um CM visto
  como filho em um kit "absolve" o mesmo SKU como filho de outro kit.
- **Zero cobertura de testes automatizados** para `kit_validation.py`
  além do que este adendo adicionou (`tests/test_kit_validation_correction_xml.py`,
  cobre só o Fix do catalog-id). CA-01/02/05/06/07 e os 8 `kind`s de
  divergência seguem sem regressão automatizada.
