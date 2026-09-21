# Análise de Negócio — Exportador: unificar "Grade Completa" e "Segmentadas" numa tela só

**Documento:** BRD-015
**Autor:** Marcos (Analista de Negócios Jr)
**Data:** 21-09-2026
**Status:** Rascunho para análise — **nenhuma linha de código autorizada**
**Branch:** A definir
**Pré-requisito de sequência:** BRD-012 — ver seção 7. A Etapa 1 deste documento é exceção e pode ser feita antes.

---

## 1. Sumário Executivo

O módulo Exportador tem duas telas — **Grade Completa** e **Segmentadas** — e as duas partem do mesmo arquivo de entrada: a planilha "Grade de Ativação". Hoje o operador solta a mesma planilha duas vezes, uma em cada tela, e o SIC a abre duas vezes só para descobrir a marca. Não existe nenhum estado compartilhado entre as telas: a Grade carregada numa é invisível para a outra.

Este BRD propõe **uma página só**, com a Grade carregada uma única vez no topo e os dois modos de trabalho em abas logo abaixo. A mudança é de **organização**, não de funcionalidade: mesmas entradas, mesmas saídas, mesmas validações. A única capacidade nova é consequência direta da unificação — Segmentadas passa a funcionar com **duas grades carregadas** (Natura e Avon), o que hoje exige visitar a tela duas vezes.

**Decisões tomadas com o usuário nesta análise:** o desenho fica a critério da análise técnica; o usuário pediu que a melhor forma fosse pesquisada e aplicada.

---

## 2. Situação Atual (AS-IS)

| | Grade Completa | Segmentadas |
|---|---|---|
| Arquivo | `src/ui/pages/view_exportador.py` — 890 linhas | `src/ui/pages/view_exportador_segmentadas.py` — 751 linhas |
| Zona da Grade | `_dz_excel`, `multiple=True` — **até 2 grades** (Natura + Avon), com 2 badges | `_seg_dz_grade`, `multiple=False` — **exatamente 1 grade** |
| Outras entradas | Pricebook base (só no modo Delta) e Catálogos XML (opcional) | Nenhuma |
| O que produz | Pricebook completo/delta, Catálogo delta, Inventory Natura/Avon, relatório XLSX | Um Pricebook Segmentado por lista escolhida |
| Estilo de trabalho | **Lote** sobre a grade inteira: marcar artefatos e gerar | **Seletivo**: varrer, escolher uma lista numa tabela, preencher ID/datas/loja e gerar um XML só para ela |
| Detecção de marca | `_sniff_brand` (`:54`) | `_sniff_brand` (`:57`) — **cópia**, e reimplementa a contagem em vez de chamar `dominant_brand` |

**Pontos verificados no código:**

- **Duplicação declarada.** `_sniff_brand`, `_apply_badge`, `_on_file_rejected` e o bloco de dropzone da Grade existem nos dois arquivos. O docstring da versão de Segmentadas (`:58-59`) reconhece a duplicação.
- **A Grade é lida repetidamente.** O `_sniff_brand` abre a planilha no momento em que ela é solta (300 linhas, somente leitura); depois, cada worker a reabre por inteiro: `SegmentadoScanWorker` em Segmentadas e `GeradorEngine.run`/`SyncEngine.run` na Grade Completa (`worker_exportador.py:59,72`). Quem usa as duas telas paga tudo em dobro.
- **Sem estado compartilhado.** As páginas são criadas uma única vez e mantidas vivas (`main_window.py:251-253`), mas não há objeto de estado comum nem singleton; o caminho do arquivo mora dentro do próprio `DropZone` de cada tela. O único estado global é o `QSettings("SIC","SIC_Suite")` (tema, fonte, webhook).
- **Os engines recebem caminhos de arquivo, não objetos já lidos.** Eliminar a releitura *dentro dos workers* exigiria alterar a API dos engines, o que está fora do alcance deste BRD (seção 9).
- **Não há nenhum teste de interface.** `tests/` cobre somente engines, sem `pytest-qt`.

---

## 3. Precedentes já existentes no projeto

Duas descobertas condicionam o desenho:

1. **`UnifiedFileDropZone`** (`src/ui/components/unified_dropzone.py:41`) — uma zona única que **classifica cada arquivo sozinha** (Pricebook, Catálogo, Grade, Kit BO) via `file_classifier.classify_file` e exibe um `IngestionChecklist` com o que já chegou. O app já resolveu uma vez o problema de "vários arquivos, uma entrada". Mas hoje **só o Auditor a usa** (`view_auditor.py:108`), e ela está acoplada ao vocabulário do Auditor. Serve como precedente do *padrão*; não como peça pronta.
2. **O estilo de abas já está escrito e nunca foi usado.** `QTabWidget`/`QTabBar` têm regras completas em `qss_light.py:555-572` e `qss_dark.py:636-658`, mas nenhuma página em `src/ui/pages/` ou `src/ui/components/` instancia um `QTabWidget`. O padrão atual do app para "modo" dentro de uma tela é `QRadioButton` com mostrar/ocultar seções.

---

## 4. Situação Desejada (TO-BE)

```
┌ Exportador ────────────────────────────────────────┐
│  [ Zona da Grade — 1 ou 2 arquivos ]     🟧  🟪     │  ← carregada uma vez
├────────────────────────────────────────────────────┤
│  ( Grade Completa )  ( Segmentadas )               │  ← QTabWidget
│                                                    │
│      conteúdo do modo selecionado                  │
└────────────────────────────────────────────────────┘
```

### 4.1 Decisões de desenho

**D1 — Só a Grade sobe.** As zonas de **Pricebook base** e **Catálogo XML** permanecem **dentro** da aba Grade Completa: só ela as usa. Içá-las para o topo poluiria a tela de quem só quer Segmentadas.

**D2 — Abas, não rádio.** Os dois modos são destinos de trabalho diferentes, feitos em momentos diferentes — não são duas configurações da mesma operação. Aba comunica "dois lugares onde posso estar"; rádio comunica "um ajuste desta operação". O `QTabWidget` introduz vocabulário novo no app, mas o estilo já está pronto nos dois temas.

**D3 — Segmentadas não vira uma terceira caixa de "Artefatos a Gerar".** Foi considerado e **rejeitado**. Gerar Pricebook ou Catálogo é lote sobre a grade inteira; Segmentadas exige varrer, escolher uma lista, preencher parâmetros e gerar um XML só para ela. É outro modo de trabalho, não mais um item marcável.

**D4 — Não adotar `UnifiedFileDropZone` agora.** Mudaria a experiência de entrada do Exportador inteiro de uma vez, sobre arquivos sem teste. Fica como possibilidade posterior (seção 9).

**D5 — A zona compartilhada aceita até 2 grades.** Reaproveita o `DropZone` já usado pela Grade Completa (`multiple=True`), com o agrupamento e os badges de marca que ele já traz. A detecção de marca ocorre **uma vez por arquivo**, e o resultado é servido às duas abas.

**D6 — O menu continua com dois atalhos.** O submenu do Exportador mantém "Grade Completa" e "Segmentadas"; cada um abre a página unificada **na aba correspondente**. Preserva a memória muscular de quem já usa e reduz a mudança em `main_window.py`. O índice de página que deixa de existir passa a redirecionar, reaproveitando o padrão já presente em `main_window.py:266-269`, onde o índice 2 redireciona para o 1.

### 4.2 Regras de comportamento

- **Segmentadas com duas grades.** A aba passa a varrer a grade da **marca selecionada**, reaproveitando o seletor de marca que já existe (`_seg_combo_marca_fallback`, `:277`), que passa a oferecer as marcas efetivamente carregadas. Com uma só grade, a escolha é automática, como hoje.
- **Trocar de aba não perde nada.** O arquivo carregado e o estado de cada aba (resultados gerados, lista selecionada) permanecem intactos ao alternar.
- **"Limpar" tem escopo explícito.** Hoje `_clear_seg_tab` (`:725`) limpa também a zona da Grade. Na página unificada, o "Limpar" de cada aba limpa **apenas os resultados daquela aba**; a Grade só é removida pela própria zona compartilhada, e removê-la reinicia as duas abas. Esta é a única mudança de comportamento não trivial e precisa ser verificada (CA-08).
- **Duas grades da mesma marca.** O aviso que a Grade Completa já emite (`view_exportador.py:441-451`) passa a valer para a zona compartilhada.

---

## 5. Etapas

### Etapa 1 — Deduplicar a detecção de marca *(sem mudança visual)*

- Novo módulo `src/core/grade_brand.py`, sem Qt, com uma única função de detecção de marca a partir da planilha, apoiada em `find_grade_sheet_name` e `dominant_brand` (`excel_reader.py`). **Arquivo novo: nenhum engine existente é alterado.**
- `view_exportador.py` e `view_exportador_segmentadas.py` passam a importá-la no lugar das duas cópias de `_sniff_brand`.
- **Verificação obrigatória antes de trocar:** rodar as duas implementações atuais sobre as mesmas planilhas de teste e confirmar que devolvem o mesmo resultado, inclusive em empate e sem SKUs. A cópia de Segmentadas reimplementa a decisão em vez de chamar `dominant_brand`; presume-se equivalente, mas não está provado.
- Testes puros em `tests/`, com planilhas geradas em `tmp_path`, no padrão de `tests/test_segmentado_engine.py`.
- **Independe de todo o resto** e pode entrar a qualquer momento, inclusive antes do BRD-012.

### Etapa 2 — Painéis independentes da origem da Grade *(sem mudança visual)*

Cada tela passa a receber a Grade de fora, por uma pequena interface (`grade_paths()`, `brand_of(path)` e um sinal de mudança), em vez de possuir o `DropZone`. **O provedor padrão continua sendo o `DropZone` da própria tela — comportamento idêntico ao de hoje.** Ao fim desta etapa as duas ainda são telas separadas.

É a etapa que torna a fusão segura: separa "de onde vem a Grade" de "o que se faz com ela", e pode ser revisada isoladamente.

### Etapa 3 — Fusão

- Nova página hospedeira com a zona compartilhada no topo e um `QTabWidget` contendo os dois painéis.
- Trocar o provedor de Grade dos dois painéis pela zona compartilhada.
- Ajustar os pontos de navegação em `main_window.py`:

| Ponto | Linha | Mudança |
|---|---|---|
| Submenu do Exportador | `:178-179` | Manter os dois itens; ambos abrem a página unificada, cada um na sua aba |
| Ligação do clique | `:180` e `:353-355` (`_switch_exportador`) | Selecionar a aba além de trocar a página |
| Tamanho do stack | `:244-245` | Ajustar se o índice 10 deixar de existir |
| Carregamento preguiçoso | `:261-265` e `:293-298` | Uma instanciação só; o outro índice redireciona (padrão de `:266-269`) |
| Botão ativo | `:327` | `index in (1, 10)` continua válido ou é simplificado |
| Nomes de página | `:334`, `:344` | Nome da barra de status inclui a aba ativa |

### Depois (não entra neste BRD)

Adotar o padrão de classificação automática de arquivos (`UnifiedFileDropZone`) no Exportador inteiro — solte tudo e o SIC decide o que é o quê.

---

## 6. Análise de Impacto

| Arquivo | Etapa | Mudança | Risco |
|---|---|---|---|
| `src/core/grade_brand.py` *(novo)* | 1 | Detecção de marca única e testável | Baixo — código novo e isolado |
| `src/ui/pages/view_exportador.py` | 1, 2, 3 | Remove a cópia de `_sniff_brand`; recebe a Grade por provedor | **Médio** — 890 linhas de produção sem teste de interface |
| `src/ui/pages/view_exportador_segmentadas.py` | 1, 2, 3 | Idem; ajusta o escopo do "Limpar" | **Médio** — mesma razão |
| `src/ui/pages/view_exportador_unificado.py` *(novo)* | 3 | Página hospedeira: zona compartilhada + abas | Médio — é a peça nova visível |
| `src/ui/main_window.py` | 3 | Seis pontos de navegação (tabela acima) | Médio — tela de entrada do app |
| `qss_light.py`, `qss_dark.py` | 3 | Ajustes finos do estilo de abas, se necessários; a base já existe | Baixo |
| **Engines e `src/workers/`** | — | **Nenhuma alteração**; comprovável por `git diff` | — |

Como a mudança fica **inteiramente na camada de tela**, a garantia de que nenhuma regra de negócio foi tocada é verificável: `git diff dev -- src/core src/workers` deve mostrar apenas o arquivo novo `grade_brand.py`.

---

## 7. Sequência em relação ao BRD-012 — atenção

As Etapas 2, 3 e 4 do **BRD-012** modificam `view_exportador_segmentadas.py` (campo do Runrun.it, banner de confirmação, gravação do registro). A Etapa 3 deste BRD **reestrutura o mesmo arquivo**. Executar as duas em paralelo gera conflito e obriga a testar tudo duas vezes, sem teste de interface para amparar.

**Ordem recomendada:** BRD-012 primeiro, BRD-015 depois. O registro é o valor de negócio solicitado; a unificação é ergonomia interna. Como a Etapa 3 move o código em bloco para dentro da página unificada, o que o BRD-012 escrever viaja junto — o retrabalho é mecânico, não conceitual.

**Exceção:** a **Etapa 1** não conflita com nada e pode entrar quando convier.

---

## 8. Critérios de Aceite

| # | Critério |
|---|---|
| CA-01 | A função de marca compartilhada devolve o mesmo resultado que as duas cópias antigas sobre as mesmas planilhas, incluindo empate Natura×Avon e planilha sem SKUs |
| CA-02 | Soltar a Grade **uma vez** a disponibiliza às duas abas |
| CA-03 | A detecção de marca abre cada planilha **uma única vez**, não uma por aba |
| CA-04 | Trocar de aba com arquivo carregado não perde o arquivo nem o estado de nenhuma aba |
| CA-05 | Com **uma** grade carregada, Segmentadas escolhe a marca automaticamente, como hoje |
| CA-06 | Com **duas** grades carregadas, Segmentadas varre a grade da marca selecionada |
| CA-07 | Duas grades da mesma marca geram o mesmo aviso que a Grade Completa emite hoje |
| CA-08 | O "Limpar" de cada aba limpa só os resultados dela; remover a Grade pela zona compartilhada reinicia as duas abas |
| CA-09 | Os menus "Grade Completa" e "Segmentadas" abrem a página unificada na aba correspondente |
| CA-10 | **Saídas idênticas:** Pricebook completo, Pricebook delta, Catálogo, Inventory Natura, Inventory Avon, relatório XLSX e Pricebook Segmentado gerados pela página unificada são **iguais, byte a byte, aos gerados pelas telas separadas**, a partir dos mesmos arquivos de entrada |
| CA-11 | Nenhuma validação existente é removida ou enfraquecida em nenhuma das duas abas |
| CA-12 | `git diff dev -- src/core src/workers` mostra apenas `grade_brand.py` (arquivo novo) |
| CA-13 | Os 112 testes existentes continuam passando |

---

## 9. Fora de Escopo

- **Alterar a API dos engines para receberem a grade já lida.** A releitura dentro dos workers permanece. Eliminá-la é um ganho real de desempenho, mas toca terreno protegido e merece BRD próprio.
- **Adotar `UnifiedFileDropZone` no Exportador** (classificação automática de arquivos).
- Mover para o topo as zonas de Pricebook base e Catálogo XML.
- Qualquer redesenho visual além do necessário para as abas.
- Unificar outras telas do aplicativo.

---

## 10. Pendências e Riscos

**Decisões abertas**
1. **Menu.** Manter o dropdown com dois atalhos (recomendado, pela memória muscular e por mexer menos) ou reduzir a um único botão "Exportador". Depende da preferência de quem opera.
2. **Duas grades da mesma marca em Segmentadas.** Além do aviso, definir se a aba bloqueia a varredura ou usa a última carregada.
3. **Atalhos na Home.** `view_home.py` navega por índice (`:114`, `:140`). Confirmar se algum aponta para o índice de Segmentadas antes de a Etapa 3 mexer nos índices. **Não foi verificado.**

**Riscos**
- **Não há teste de interface.** As duas telas somam 1.641 linhas em produção, sobre preço real. As Etapas 2 e 3 exigem **roteiro manual com arquivos reais**, cobrindo cada uma das sete saídas listadas no CA-10, antes e depois, comparando os arquivos gerados. A Etapa 1 é a única com cobertura automatizada completa.
- **Fusão ingênua daria ~1.600 linhas numa classe.** É o motivo de a Etapa 2 existir: sem separar os painéis antes, a fusão vira um arquivo impossível de revisar.
- **Vocabulário novo.** É a primeira vez que o app usa abas. O estilo está pronto, mas o comportamento de teclado e foco entre abas não foi exercitado em nenhuma tela.
