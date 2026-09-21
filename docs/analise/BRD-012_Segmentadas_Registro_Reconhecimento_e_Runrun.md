# Análise de Negócio — Manutenção das Ações Segmentadas: registro de vínculos, reconhecimento na importação, manutenção em lote e confirmação no Runrun.it

**Documento:** BRD-012
**Autor:** Marcos (Analista de Negócios Jr)
**Data:** 21-09-2026
**Status:** Rascunho para análise — **nenhuma linha de código autorizada**
**Solicitação:** "Manutenção das Ações Segmentadas" (formulário Solicitação de Evolução Integrada)
**Branch:** A definir (este documento sobe em `docs/brd-012-registry-segmentadas`)
**Pré-requisitos:** nenhum. Independente do BRD-014.
**Nota de numeração:** o conteúdo do antigo **BRD-013** (integração com a API do Runrun.it) foi incorporado a este documento como a **Etapa 5**, e o BRD-013 foi removido. Os commits `cdb79c7` e `a2e5fb5` (já publicados) citam BRD-013 e se referem a essa etapa.

---

## 1. Sumário Executivo

O SIC gera o XML do Pricebook Segmentado e esquece dele logo em seguida. Como os IDs seguem as tarefas do Runrun.it e são digitados à mão, o sistema não sabe quais listas já existem, de qual tarefa cada aba da planilha faz parte, nem como atualizar uma lista sem que o operador redigite tudo. O principal ponto de dor é a **manutenção**: quando o time de planejamento envia uma nova planilha com preços atualizados de várias segmentadas ativas, hoje é preciso deletar os pricebooks antigos e recriar tudo do zero, redigitando cada ID.

Este BRD propõe dar **memória compartilhada** ao SIC, em cinco etapas de escopo definido e duas futuras. A ordem de execução está na seção 2:

1. Uma **planilha Google da equipe**, acessada por uma pequena automação, guarda o vínculo entre a aba do Excel e o ID da tarefa.
2. O SIC passa a **registrar** cada lista que gera, sem mudar nada no fluxo de trabalho.
3. O SIC **reconhece** na importação as abas que já conhece e monta o ID a partir do número da tarefa, sempre pedindo confirmação.
4. O SIC trata **várias listas de uma vez** — o cenário real de manutenção descrito na solicitação.
5. O SIC **confere a tarefa no Runrun.it**, exibindo o título antes de gerar, para que um número trocado deixe de virar preço errado na loja.

**Decisões tomadas com o usuário nesta análise:**

| Decisão | Escolha |
|---|---|
| Onde o registro fica | Planilha Google com automação, e cache local no computador de cada pessoa |
| Escopo de hoje | Prioridades **P0 a P4** (modelo, núcleo, gravação, reconhecimento e lote) — ver seção 2 |
| ID automático | Só **Natura** (`NAT-RR{id}`) e **Avon** (`AVN-RR{id}`). Minha Loja (CB) continua manual |
| Nome de aba reaproveitado entre ciclos | **Sim** — o vínculo nunca é aplicado sem confirmação explícita |
| Runrun.it | **Somente leitura**; o operador digita o número e confere. A equipe tem acesso à API e vai implementá-la em breve |
| Reimportar o mesmo `pricebook_id` no Salesforce | **Substitui** a lista inteira (V3, respondida pelo gestor) |
| Identidade do registro | Um `pricebook_id`, um registro, atualizado no lugar (D1) |
| Quem registrou (`created_by`) | Nome do **Runrun.it** quando disponível; usuário do Windows enquanto não estiver (D2) |
| Painel de Gestão e botão "Encerrar" | **P7**, fora do escopo de hoje; o "Encerrar" segue bloqueado pela V7 |

---

## 2. Plano de Execução — o que fazer primeiro

As etapas da seção 6 estão numeradas por **dependência de conceito**. Esta seção manda na **ordem de trabalho**, que é diferente: a Etapa 1 (planilha) depende da TI, enquanto o núcleo da Etapa 2 não depende de nada.

| Prioridade | Entrega | Depende de | Libera |
|---|---|---|---|
| **P0** | Fechar o modelo de dados — 4 decisões | nada | tudo |
| **P1** | Núcleo testável (sem tela) | P0 | P2 |
| **P2** | Gravar de verdade, com escape | P1 | P3 |
| **P3** | Reconhecimento na importação (uma lista) | P2 | P4 |
| **P4** | **Manutenção em lote** — várias listas de uma vez | P3, V3 ✅ | **ponto de parada seguro** |
| **P5** | Compartilhar entre a equipe | P4, V1, V2 | P6 |
| **P6** | Conferência no Runrun.it | P5, V4-V6 | — |
| **P7** | Painel e Encerrar | P6, V7 | — |

### P0 — Fechar o modelo de dados *(bloqueia tudo; nenhuma linha de código antes)*

Registros gravados com o modelo errado viram migração em máquina de gente de verdade. Estas quatro decisões precisam estar fechadas **antes da primeira gravação**:

**D1 — A identidade do registro é o `pricebook_id`.** Um pricebook, um registro, atualizado no lugar. Sem isso há uma contradição: a proposta original manda o servidor recusar dois registros ativos com o mesmo `pricebook_id`, mas a atualização existe justamente para **reescrever** um pricebook existente — se cada salvamento criasse um registro novo, a regra de proteção mataria a funcionalidade principal. A decisão também espelha o Salesforce, onde reimportar o mesmo ID **substitui** (V3, respondida).

**D2 — `created_by` é resolvido uma vez e gravado dentro do registro.** A fonte obedece a esta ordem: nome vindo do **Runrun.it** (quando o token estiver configurado) → nome digitado em Configurações → usuário do Windows. Como o nome é gravado **no momento da escrita**, e não consultado na leitura, a P2 sai com o usuário do Windows e os registros novos passam a nascer com o nome do Runrun.it quando a P6 chegar — **sem migrar nada**. Isso evita que a primeira entrega dependa da última.

> ⚠️ **Em aberto:** *quem criou a tarefa no Runrun.it* (provavelmente o planejamento, que pediu a campanha) **não é** necessariamente *quem registrou o vínculo no SIC* (quem operou). Os dois são úteis e respondem a perguntas diferentes: "de quem foi essa campanha?" e "quem fez esse vínculo?". Decidir se o registro guarda um campo ou dois.

**D3 — `campaign_name` precisa de alternativa.** A fonte prevista é o campo "Nome de Exibição do Pricebook", mas ele é **opcional** ("deixe em branco para omitir do XML"). Vazio, o banner da P3 mostra campanha em branco e a conferência cruzada da P6 não tem contra o que comparar. Ordem proposta: nome de exibição → rótulo LP da aba → nome da aba.

**D4 — A `loja` participa do reconhecimento.** A mesma aba pode virar pricebook na loja da marca **e** na Minha Loja (CB), que aceita SKUs de qualquer marca. São dois pricebooks distintos; sem a loja no casamento, o caso cai em "ambíguo" sem explicar o motivo real.

### P1 — Núcleo testável *(nenhum arquivo existente é tocado)*

`app_paths.py` e `segmentada_registry.py`: modelo, montagem do ID, cálculo de status, regra de reconhecimento e armazenamento local, tudo com teste puro.
**Pronto quando:** testes verdes e `git diff` mostrando apenas arquivos novos.

### P2 — Gravar de verdade, com escape

A gravação no salvamento (ver Etapa 2) **mais um caminho de correção**: sem ele, o primeiro engano vira um registro errado sem saída — nas P2 e P3 a planilha ainda não existe, então a única alternativa seria editar um JSON na mão. O mínimo é apagar um registro e abrir a pasta do registro a partir de Configurações.
**Pronto quando:** CA-01 a CA-04 e CA-20.

### P3 — Reconhecimento na importação (uma lista)

Campo do número da tarefa, montagem do ID e banner com confirmação obrigatória.
**Pronto quando:** CA-05 a CA-08.

### P4 — Manutenção em lote

Várias listas numa passada só: uma tela de conferência, uma confirmação, uma pasta de destino. É a entrega que realiza o cenário descrito na solicitação original ("carregar um Excel com 5 abas de manutenções").
**Pronto quando:** CA-09 a CA-14.

> **Este é o melhor ponto de parada.** O retrabalho acabou para quem gera as listas — sem rede, sem TI, sem dado saindo da máquina. Se a publicação do Apps Script for barrada, tudo o que foi entregue até aqui continua de pé.

### P5 — Compartilhar entre a equipe

Planilha, automação, Configurações e migração explícita. Inclui **fila de pendências**: sem ela, uma falha de rede deixaria o registro só na máquina de quem gerou e a colega nunca o veria — o compartilhamento seria silenciosamente furado. Inclui também a **resolução de colisão** na migração, para o caso de duas pessoas terem registrado a mesma aba antes de a planilha existir.
**Pronto quando:** CA-15 a CA-18.

### P6 — Conferência no Runrun.it

Cliente somente leitura, Configurações e conferência cruzada na tela. Também é aqui que `created_by` passa a vir do Runrun.it (D2).
**Pronto quando:** CA-21 a CA-28.

### P7 — Painel e Encerrar

Fora do escopo de hoje. Ver seção 5, itens NR2 e NR3, para as perguntas que precisam ser respondidas antes de desenhá-los.

---

## 3. Situação Atual (AS-IS)

`src/ui/pages/view_exportador_segmentadas.py` recebe o `pricebook_id` num campo de texto livre (`_seg_input_pbid`, linha ~140). As únicas validações, em `_run_seg_generate` (linhas 601-620), são: campo não vazio, sem espaço em branco e fora de `RESERVED_PRICEBOOK_IDS`. Não há máscara, verificação de prefixo `NAT-`/`AVN-` nem checagem de duplicidade.

Após gerar, o `HistoryEngine` grava apenas um texto livre (`:694-698`): *"Pricebook Segmentado (LISTA_48) gerado — 128 SKUs."* Não grava o `pricebook_id`, as datas, o parent nem a marca. **Nenhuma informação do pricebook gerado é persistida.**

O fluxo é **uma lista por vez**: a tela varre a planilha, lista as abas candidatas numa tabela de seleção única (`_seg_table`, `:313`), e o operador escolhe uma, preenche os parâmetros, gera e salva por uma caixa de diálogo individual (`_save_seg_pricebook`, `:705`).

Consequências operacionais:

- Sem vínculo salvo, a manutenção exige deletar os pricebooks antigos e recriar tudo.
- Os IDs baseados nas tarefas do Runrun.it são redigitados manualmente, com risco de erro de digitação.
- Não há como associar rapidamente a qual ID (ex.: `NAT-RR1111`) a `LISTA_48` pertence.
- Nada confirma que o número digitado corresponde à campanha pretendida: um erro só apareceria depois, como preço errado na loja.
- **Manutenção de cinco listas custa cinco ciclos completos**, com cinco caixas de salvar.

---

## 4. Confronto com a proposta original — onde nos afastamos e por quê

A solicitação veio acompanhada de uma proposta de arquitetura ("Lousa Branca V3"). Esta seção registra, de forma explícita, **em que este BRD diverge dela**, para que a diferença seja discutida em vez de descoberta durante a construção.

### A1 — Confirmação obrigatória no lugar do preenchimento automático *(divergência principal)*

**A proposta dizia:** *"Ele vai preencher o ID automaticamente (NAT-RR1111) e já marcará que esta ação é uma Atualização"*, com o benefício *"os IDs serão resgatados na mesma hora. **É só clicar em Exportar**"*.

**Este BRD faz o oposto:** o SIC **nunca** preenche o ID sozinho. Ele mostra o vínculo encontrado e espera um clique explícito.

**Motivo:** os nomes de aba **se repetem entre ciclos** — confirmado com a operação. A `LISTA_48` de hoje pode ser outra campanha. Preenchendo sozinho, uma "atualização" sobrescreveria o preço de uma promoção ativa não relacionada, em produção. Como a reimportação **substitui** a lista inteira (V3), o estrago seria imediato e silencioso.

**O que isso custa:** um clique de confirmação por lista, o que contraria o "é só clicar em Exportar".

**Como devolvemos o benefício:** a Etapa 4 (manutenção em lote) reduz isso a **uma confirmação para o conjunto inteiro**. Cinco listas voltam a ser uma revisão e um clique — com a diferença de que a revisão existe. Sem a Etapa 4, esta divergência piora a experiência que a proposta prometia; com ela, a promessa é cumprida sem abrir mão da trava.

### A2 — Planilha Google no lugar do Git *(mudança por segurança)*

A proposta previa um `segmentadas_registry.json` versionado no repositório e sincronizado por `git pull`/`git push`. Foi substituído por uma planilha Google da equipe. **Motivo detalhado na seção 5.** Em resumo: o repositório é público, as demais pessoas não têm o repositório clonado, e o projeto já ignora dado de operação de propósito.

### A3 — Painel e "Encerrar" adiados *(redução de escopo)*

**A proposta incluía** o Painel de Gestão e o botão "Encerrar" como parte da entrega (seção C e passo 3 dos "Próximos Passos").

**Este BRD os adia** para a P7, fora do escopo de hoje.

**Motivo:** o "Encerrar" depende de uma validação no Salesforce que ainda não foi feita (V7) e que agora tem **duas hipóteses possíveis de mecanismo** — ver NR3. O Painel depende de uma definição de negócio ainda em aberto sobre o que significa "ativa" — ver NR2. Construir qualquer um dos dois antes dessas respostas seria adivinhar.

**Consequência:** a solicitação original **não é atendida por inteiro** por este BRD. As duas peças continuam registradas, com as perguntas que as destravam.

### A4 — Integração com a API do Runrun.it *(acréscimo do usuário)*

**A proposta não previa** integração com a API do Runrun.it — ela cita o Runrun.it apenas como origem dos números das tarefas.

**Este BRD acrescenta** a conferência da tarefa (Etapa 5), por decisão do usuário, que considerou o uso necessário e confirmou que a equipe tem acesso à API e vai implementá-la em breve.

**O que isso agrega:** a proposta original só reduz o risco de número trocado **quando já existe vínculo salvo**. Ela não cobre o **primeiro cadastro** de uma lista nem detecta um número simplesmente digitado errado. A conferência na origem fecha essa lacuna e ainda dá uma terceira fonte independente para a trava do item A1.

---

## 5. O que este BRD não responde

Registrado aqui para não se perder. Nenhum destes itens tem solução fechada.

### NR1 — Criação de listas novas em lote

A Etapa 4 cobre o **lote de manutenção**: listas que o SIC já conhece. Uma planilha que traga várias abas **inéditas** continua exigindo uma passada por lista, porque cada uma precisa do número da tarefa digitado e do cuidado da primeira vez.

Isso é aceitável para o cenário descrito na solicitação, que é explicitamente de manutenção. Mas se a criação em lote também for comum na prática, é trabalho não coberto. **A operação precisa dizer com que frequência isso acontece.**

### NR2 — O Painel: o que significa "ativa"?

A proposta pede uma tela com "todas as ações ativas". Mas o SIC só sabe o que **ele mesmo gerou e salvou** — e salvar não é importar: o operador ainda sobe o arquivo no Business Manager. Um pricebook gerado e nunca importado apareceria como "ativo" sem estar no ar; um pricebook criado por outro caminho não apareceria.

Antes de desenhar o Painel é preciso decidir: ele mostra **o que foi registrado pelo SIC** (honesto, mas incompleto) ou existe alguma forma de confirmar o que está de fato publicado no Salesforce? A segunda opção implicaria ler o Salesforce, o que está fora de tudo que foi discutido até aqui.

### NR3 — O "Encerrar": qual mecanismo, e qual comportamento se deseja?

A proposta especifica *"XML de online-to = ontem"*. Com a V3 respondida, passaram a existir **duas hipóteses**, com efeitos diferentes:

| Hipótese | Como | Efeito esperado |
|---|---|---|
| A | XML com `online-to` no passado | Derruba o pricebook inteiro |
| B | Mesmo pricebook, **lista de preços vazia** | Esvazia os preços; o pricebook continua existindo |

A hipótese B só se tornou plausível porque a reimportação substitui a lista inteira, e o motor já gera esse XML sem erro (`build_xml` aceita lista vazia, `tests/test_segmentado_engine.py:435-444`).

Nenhuma das duas foi validada. E antes de testar **qual funciona**, é preciso definir **qual comportamento se quer** — derrubar ou esvaziar. São decisões de negócio diferentes.

---

## 6. Decisão de Arquitetura — por que não o Git como banco de dados

A primeira proposta previa um arquivo `segmentadas_registry.json` versionado no repositório e sincronizado entre a equipe por `git pull`/`git push`. Ela foi **descartada** por três motivos verificados:

1. **O repositório é público.** `rangel-dev/sic` retorna `"visibility": "public"` na API do GitHub. O registro guardaria nome de campanha, datas de vigência e volume de SKUs — o calendário promocional da Natura e da Avon ficaria exposto, inclusive campanhas ainda não lançadas.
2. **Os usuários não têm o repositório.** O SIC é distribuído como executável (PyInstaller + Inno Setup, instalado em `%LOCALAPPDATA%\SIC`, com atualização automática via GitHub Releases). As demais pessoas da equipe não têm o repositório clonado, nem Git, nem Python — sem repositório local, não há `git pull` possível.
3. **Precedente do projeto.** O `history.db` está no `.gitignore` de propósito: dado de operação nunca foi versionado neste projeto.

**Solução adotada:** uma **planilha Google da equipe** como fonte da verdade, acessada por uma automação (Apps Script publicado como Web App), com uma **cópia local em cache** no computador de cada pessoa. A concorrência entre as 3 pessoas é resolvida no servidor do Google, não no SIC, o que evita a escrita perdida e a "cópia em conflito" de uma pasta sincronizada.

A separação do repositório em código privado e instaladores públicos, necessária para o aspecto de privacidade, é **tratada em solicitação própria** e está fora deste BRD.

---

## 7. Etapas

### Etapa 1 — Planilha e automação (fora do código Python)

- Planilha no Drive de uma **conta de equipe** (não pessoal), aba `registry`, acesso restrito ao time.
- Automação publicada como Web App, com as ações `list`, `upsert` e `mark_ended`. O `upsert` age **por `pricebook_id`** (D1) — nunca reescreve a lista inteira.
- Toda escrita sob `LockService.getScriptLock()`. O token é lido de `PropertiesService.getScriptProperties()`: **nunca fica no código do script**.
- ⚠️ Um aplicativo de desktop sem login Google só chama o Web App se ele for publicado com acesso **"Qualquer pessoa"**. Nesse modelo a URL é alcançável sem autenticação e **o token é a única proteção** — deve ser tratado como senha (longo, aleatório, rotacionável).
- Referência do script versionada em `tools/apps_script/registry.gs`, **sem token**.

**Formato do registro:**

| Campo | Exemplo | Origem |
|---|---|---|
| `pricebook_id` | `NAT-RR1111` | **identidade do registro (D1)** |
| `sheet_name` | `LISTA_48` | aba da planilha |
| `lp_label` | rótulo LP da aba | aba da planilha |
| `runrun_id` | `1111` | digitado pelo operador |
| `brand`, `loja` | `natura`, `natura` | detecção de marca e seletor de loja |
| `campaign_name` | "Favoritos RR18/21" | nome de exibição → LP → nome da aba (D3) |
| `online_from`, `online_to` | datas de vigência (UTC) | parâmetros da geração |
| `sku_count` | quantidade de SKUs | contagem da aba |
| `created_at`, `updated_at` | datas | automático |
| `created_by` | nome da pessoa | Runrun.it → Configurações → usuário do Windows (D2) |
| `ended_at`, `source_file` | reservados à P7 | — |

O envelope carrega `schema_version` para permitir migração. **Só metadados saem do computador — nenhum preço e nenhuma lista de SKUs.**

⚠️ **A migração dos registros locais é explícita.** As etapas anteriores rodam antes de a planilha existir, então, quando esta entrar, haverá registros criados sob o combinado de que ficariam na máquina. Subi-los automaticamente mudaria a regra depois do fato. O envio inicial precisa **mostrar o que será enviado e pedir confirmação**; nunca ocorre sozinho.

### Etapa 2 — Registro passivo

O SIC passa a gravar um registro a cada segmentada salva, **sem alterar o fluxo de trabalho**.

- Novo `src/core/app_paths.py` — caminho de dados válido dentro do executável (`QStandardPaths.AppDataLocation`, com fallback em `%APPDATA%\SIC`). **Não** reutilizar o padrão de `history_engine.py:6,12` (`Path(__file__).parent.parent.parent`): dentro do executável (modo *onedir*, `sic.spec`) ele grava dentro da própria pasta de instalação, e dado do usuário guardado ali fica sujeito a reinstalação, limpeza da pasta e à falta de permissão de escrita em instalações legadas em `Program Files`.
- Novo `src/core/segmentada_registry.py` — `SegmentadaRecord`; `RegistryStore` **orientado a registro** (`load`, `upsert`, `mark_ended`); `GoogleSheetRegistryStore(url, token, timeout=5)` via `requests` (já em `pyproject.toml:15`); `JsonFileRegistryStore` como armazenamento local com escrita atômica; `CachedRegistry`.
- `view_settings.py` (já usa `QSettings` e `QFormLayout`, linhas 13 e 40-48): bloco "Registry de Segmentadas" com URL, token, botão **Testar** (modelo `_test_webhook`, `:129`), chave liga/desliga do compartilhamento e **acesso à pasta do registro**.

**Quando gravar — o registro é confirmado no salvamento, não na geração.**

`_run_seg_generate` apenas monta o XML em memória (`self._seg_xml`); o arquivo só vai para o disco em `_save_seg_pricebook`, na linha 721, **dentro do `if path:`**. Gravar o registro logo após o `HistoryEngine.add_entry` (`:694`) criaria um vínculo para um pricebook que o operador pode ter cancelado na caixa de salvar — e, na importação seguinte daquela aba, o SIC ofereceria "ATUALIZAÇÃO" de algo que nunca existiu.

Portanto:

1. Em `_run_seg_generate`, montar um **registro pendente** com o que entrou no XML. É o padrão que o próprio arquivo já adota nas linhas 678-680.
2. Em `_save_seg_pricebook`, **depois** de `f.write(self._seg_xml)` concluir, gravar o registro pendente em segundo plano (padrão de `worker_segmentado.py:13-17`), dentro de `try/except`.

**Limite conhecido:** salvar não é importar. O registro afirma "este XML foi gerado e salvo", nunca "este pricebook está no ar" — ver NR2.

**O que fica ligado e o que é opt-in:**

| | O que é | Rede | Padrão |
|---|---|---|---|
| Registro local | Arquivo em `%APPDATA%\SIC` | Não | **Ligado**, com opção de desligar |
| Compartilhamento | Planilha da equipe (Etapa 1) | Sim | **Desligado** até configurar URL e token |

O registro local é da mesma natureza do `history.db`, que o SIC já grava hoje sem perguntar. Mantê-lo ligado é necessário para o recurso funcionar — memória desligada por padrão nasce vazia, e a pessoa só descobre que precisava dela na manutenção seguinte. O que exige decisão consciente é o dado **sair** da máquina.

### Etapa 3 — Reconhecimento na importação (uma lista)

- Novo campo **"Nº da tarefa Runrun.it"** acima de `_seg_input_pbid`. Ao digitar, o SIC monta o ID **apenas se o campo de ID não tiver sido editado à mão** (flag `_pbid_touched`). Para a loja CB o campo segue manual.
- Ao selecionar uma lista (`_on_seg_lista_selected`, `~:570`), o SIC consulta o registro e exibe um **banner de confirmação**:

  `LISTA_48 → NAT-RR1111 · "Favoritos RR18/21" · 01/09–14/09 · registrada em 28/08 por fulano · antes 128 SKUs / agora 118`

  com os botões **"Usar (ATUALIZAÇÃO)"** e **"Ignorar — é campanha nova"**. Sem clique, o campo de ID permanece vazio e livre.
- **A comparação de `sku_count` é a principal defesa, não um detalhe informativo.** A V3 confirmou que reimportar o mesmo `pricebook_id` **substitui a lista inteira**. Isso elimina o risco de preço fantasma, mas cria o oposto: **os SKUs ausentes perdem o preço segmentado imediatamente**. Por isso, quando a quantidade **cair**, a confirmação não deve apenas mostrar números, e sim dizer o que vai acontecer: *"10 produtos vão perder o preço segmentado ao importar."*
- Em `_run_seg_generate`, acrescentar **somente** uma pergunta de confirmação quando o modo for ATUALIZAÇÃO. As validações 601-620 permanecem intactas.

### Etapa 4 — Manutenção em lote

**Problema.** O cenário descrito na solicitação é *"carregar um Excel com 5 abas de manutenções"*. O fluxo atual, e também o da Etapa 3, é **uma lista por vez**: selecionar, preencher, gerar, salvar, repetir. Cinco listas custam cinco ciclos e cinco caixas de salvar — e, com a trava do item A1, cinco confirmações.

**Situação desejada.**

1. **A tabela de candidatas ganha duas coisas:** uma coluna **"Vínculo"** — mostrando, por linha, o ID reconhecido e a campanha, ou "nova" — e **caixas de seleção múltipla**.
2. O operador marca as listas que quer processar e aciona **"Gerar selecionadas"**.
3. **Uma tela de conferência** lista tudo o que vai acontecer, uma linha por lista: aba, ID, campanha, período, e a variação de SKUs com o alerta em texto claro quando houver queda. Linhas com vínculo fraco, ambíguo ou vencido aparecem **em vermelho e desmarcadas por padrão** — para entrarem no lote, precisam ser marcadas deliberadamente.
4. **Uma confirmação** para o conjunto.
5. **Uma pasta de destino**, escolhida uma vez. O SIC grava os N arquivos usando a mesma convenção de nome que já existe em `_save_seg_pricebook` (`:714-717`).
6. **Um resumo ao final:** quantos foram gerados, quantos falharam e por quê.
7. **Um registro por lista**, gravado sob a mesma regra da Etapa 2: só depois de o arquivo correspondente ter sido escrito.

**Por que isso não enfraquece a trava.** A conferência mostra as cinco listas **lado a lado**, o que é melhor para revisão do que cinco caixas de diálogo isoladas: dá para comparar, notar a que destoa e desmarcá-la. A confirmação continua existindo — passa a ser uma, sobre o conjunto, em vez de uma por lista. É assim que o item A1 devolve o "é só clicar em Exportar" sem abrir mão da segurança.

**Fronteira.** O lote é de **manutenção**: listas que o SIC já reconhece. Criação de lista nova segue individual, porque exige o número da tarefa digitado e o cuidado da primeira vez — ver NR1.

**Dados que já existem e serão reaproveitados:** cada candidata já traz `sheet_name`, `lp_label`, `periodo_sugerido`, contagem de SKUs e avisos próprios (`ListaCandidate`, `segmentado_engine.py`). O período de cada lista vem do sugerido pela aba, editável na tela de conferência. A **loja** continua sendo uma escolha única para o lote, já que a grade é de uma marca.

### Etapa 5 — Confirmação da tarefa no Runrun.it *(antigo BRD-013)*

**Situação desejada.** Ao sair do campo "Nº da tarefa Runrun.it" (perda de foco ou Enter — **nunca a cada tecla**), o SIC consulta a tarefa e exibe o título ao lado do ID montado:

```
1111  →  NAT-RR1111  ·  "Favoritos RR18/21"
```

- Tarefa encerrada no Runrun.it → aviso visível.
- Número inexistente → aviso claro, **sem travar o campo**.
- Integração desligada, sem credencial ou Runrun.it indisponível → a tela funciona exatamente como hoje.

O título retornado **confirma** o `campaign_name` do registro, que desde a Etapa 2 já vem do campo de nome de exibição. A diferença é a fonte: lá é o que o operador digitou; aqui é o que o Runrun.it afirma.

**Conferência cruzada.** Passam a existir três fontes sobre a mesma lista:

| Fonte | O que afirma |
|---|---|
| Nome da aba na planilha | "esta lista se chama LISTA_48" |
| Registro (Etapas 1 a 4) | "a LISTA_48 foi vinculada à tarefa 1111, campanha *Favoritos RR18/21*" |
| **Runrun.it** | "a tarefa 1111 é, de fato, *«…»*" |

Quando o registro e o Runrun.it **divergem**, isso indica registro desatualizado ou aba reaproveitada apontando para o vínculo errado. O SIC destaca a divergência em vermelho e **exige confirmação explícita**.

**Proteção da App-Key (requisito, não otimização).** A documentação estabelece **100 requisições por minuto**, com HTTP 429 ao estourar, e adverte que **o uso abusivo leva à revogação da App-Key**. Como essa chave pertence à conta da Natura, um defeito no aplicativo poderia derrubar integrações de **outras áreas**. Por isso:

1. Consulta apenas por ação explícita. **Nunca por tecla digitada.**
2. Cache em memória por sessão.
3. O `campaign_name` já gravado é exibido de imediato, servindo de cache entre sessões.
4. **Sem repetição automática** em caso de 429.
5. Intervalo mínimo entre consultas consecutivas.
6. Chave de liga/desliga em Configurações, independente do registro.

Volume esperado: unidades de chamadas por sessão, contra um teto de 100 por minuto.

**Credenciais.** Cabeçalhos `App-Key`, `User-Token` e `Content-Type: application/json`, sobre `https://runrun.it/api/v1.0`. A **App-Key** é da conta da empresa; o **User-Token é pessoal**. ⚠️ O User-Token dá acesso à conta inteira daquela pessoa, não apenas à leitura de uma tarefa: campo mascarado, armazenamento em `QSettings("SIC","SIC_Suite")`, e instrução de como revogar pelo próprio perfil.

Novo `src/core/runrun_client.py` — `RunrunClient(app_key, user_token, timeout=5)` e `get_task(numero)`; falhas viram `RunrunUnavailable`. Sem Qt, apenas `requests`.

### Etapa 6 — Painel de Gestão *(P7 — depende de NR2)*

Tela com o status de cada lista (ativa, agendada, expirada), no padrão de `view_history.py`. Exige acrescentar uma página em `main_window.py` (`:179`, `:244-246`, `:305-309`, `:327`, `:332-345`) e estilos de aviso em `qss_light.py`/`qss_dark.py`.

### Etapa 7 — Encerrar promoção *(P7 — bloqueada por NR3 e V7)*

Ver NR3 para as duas hipóteses de mecanismo e a decisão de negócio pendente.

---

## 8. Regras de Negócio Transversais

- **A confirmação nunca é dispensada.** O nome da aba é reaproveitado entre ciclos. Um vínculo resgatado jamais é aplicado sem o clique do operador — individualmente na Etapa 3, ou para o conjunto na Etapa 4.
- **Confiança do vínculo:** `exact` (aba + `lp_label` + marca + loja batem), `sheet_only`, `ambiguous` (2 ou mais registros para a mesma aba) e `none`. Em `sheet_only`, `ambiguous`, registro expirado, `lp_label` divergente ou registro com mais de 90 dias, o aviso fica **vermelho**.
- **O registro nunca bloqueia o trabalho.** Toda leitura e gravação ocorre fora da tela principal, com tempo limite de 5 segundos; falha do registro **jamais impede gerar ou salvar o XML**.
- **Aditivo.** O fluxo atual — digitar o ID à mão, uma lista por vez — permanece disponível e idêntico. Nenhuma linha de `segmentado_engine.py` muda.
- **Só o que foi salvo é registrado.** Um XML gerado e não salvo não gera vínculo.
- **Identidade do registro:** um `pricebook_id`, um registro, atualizado no lugar (D1).

---

## 9. Análise de Impacto

| Arquivo | Etapa | Mudança | Risco |
|---|---|---|---|
| `tools/apps_script/registry.gs` *(novo)* | 1 | Automação da planilha | Baixo — fora do executável |
| `src/core/app_paths.py` *(novo)* | 2 | Caminho de dados no executável | Baixo |
| `src/core/segmentada_registry.py` *(novo)* | 2, 3, 4 | Registro, cache, resolução de vínculo | Baixo — código novo e isolado |
| `src/core/runrun_client.py` *(novo)* | 5 | Cliente somente leitura | Baixo |
| `src/ui/pages/view_settings.py` | 2, 5 | Blocos de configuração do registro e do Runrun.it | Baixo |
| `src/ui/pages/view_exportador_segmentadas.py` | 2, 3, 4, 5 | Gravação, campo do Runrun.it, banner, seleção múltipla, tela de conferência. Validações 601-620 **intactas** | **Médio-alto** — a Etapa 4 é a maior mudança estrutural da tela |
| `README.md` e `docs/seguranca/` | 2, 5 | Ver seção 11 | Nulo em runtime |
| `segmentado_engine.py` e demais engines | — | **Nenhuma alteração** | — |

⚠️ **A Etapa 4 e o BRD-015 disputam o mesmo arquivo.** O BRD-015 (unificar Grade Completa e Segmentadas) reestrutura `view_exportador_segmentadas.py`. A Etapa 4 muda a tabela e acrescenta uma tela de conferência no mesmo arquivo. Os dois **não devem correr em paralelo**; a recomendação registrada no BRD-015 é concluir este BRD primeiro.

---

## 10. Privacidade, Segurança e Comunicação com a TI

- **O que sai do computador:** nome da aba, ID da tarefa, nome da campanha, datas, marca e quantidade de produtos. **Nenhum preço e nenhuma lista de SKUs.**
- **Segredos** (URL e token do registro; App-Key e User-Token do Runrun.it) ficam em `QSettings("SIC","SIC_Suite")`, nunca no repositório.
- ⚠️ O `README.md` (`:46-65`, `:69-74`, `:93-115`) afirma hoje "Não persiste dados na nuvem", "Não se conecta a servidores internos", "A única URL externa é `api.github.com`" e "Nenhuma outra conexão de rede é feita". **Essas afirmações deixam de valer** e devem ser reescritas. A tabela de firewall precisa acrescentar `script.google.com` e `script.googleusercontent.com` (registro) e `runrun.it` (Etapa 5). Aproveitar para corrigir o que **já está defasado**: o webhook do Google Chat (`chat.googleapis.com`) nunca entrou na lista.
- O que sai da máquina é **opt-in e desligado por padrão**, com chaves independentes para o compartilhamento e para o Runrun.it. O registro local não é opt-in e também não é destino de rede.

---

## 11. Critérios de Aceite

**Registro (P2)**

| # | Critério |
|---|---|
| CA-01 | Cada segmentada **salva em disco** resulta em um registro com os campos da Etapa 1 |
| CA-02 | Gerar e **cancelar** a caixa de salvar **não** cria registro |
| CA-03 | O `campaign_name` é preenchido sem digitação extra, seguindo a ordem da D3 |
| CA-04 | Salvar o mesmo pricebook duas vezes **não** duplica registro (D1) |

**Reconhecimento (P3)**

| # | Critério |
|---|---|
| CA-05 | Reimportar uma aba conhecida exibe o vínculo correto; **nada é preenchido sem clique** |
| CA-06 | Vínculo `sheet_only`, `ambiguous`, expirado ou antigo → aviso vermelho |
| CA-07 | Digitar só o número da tarefa monta `NAT-RR{id}` ou `AVN-RR{id}`; loja CB permanece manual |
| CA-08 | Queda de SKUs na atualização → a confirmação diz **quantos produtos perderão o preço segmentado** |

**Lote (P4)**

| # | Critério |
|---|---|
| CA-09 | Cinco listas reconhecidas são geradas com **uma** conferência, **uma** confirmação e **uma** escolha de pasta |
| CA-10 | A tela de conferência mostra, por lista, o vínculo, o período e a variação de SKUs |
| CA-11 | Linhas com vínculo fraco, ambíguo ou vencido vêm **desmarcadas** e em vermelho |
| CA-12 | Os arquivos gerados em lote são **idênticos** aos que o fluxo individual geraria para as mesmas listas |
| CA-13 | Falha em uma lista não impede as demais; o resumo final diz o que falhou e por quê |
| CA-14 | Um registro é gravado por lista, apenas para as que tiveram arquivo escrito |

**Compartilhamento (P5)**

| # | Critério |
|---|---|
| CA-15 | Compartilhamento desligado, sem URL, token inválido ou rede indisponível → o XML é gerado e salvo normalmente, com aviso discreto |
| CA-16 | Sem rede, o reconhecimento usa o armazenamento local, indicando o horário da última sincronização |
| CA-17 | Duas máquinas registrando quase ao mesmo tempo → nenhum registro perdido |
| CA-18 | Registro gravado offline **sobe sozinho** na primeira oportunidade seguinte |
| CA-19 | O envio inicial para a planilha só ocorre após confirmação explícita do que será enviado |

**Transversal**

| # | Critério |
|---|---|
| CA-20 | O fluxo atual (ID digitado à mão, uma lista por vez) funciona idêntico, com e sem registro configurado |

**Runrun.it (P6)**

| # | Critério |
|---|---|
| CA-21 | Número válido → título da tarefa exibido antes de gerar o XML |
| CA-22 | Número inexistente → aviso claro, campo continua utilizável |
| CA-23 | Integração desligada, sem credencial ou indisponível → a tela se comporta exatamente como hoje |
| CA-24 | Título divergente do registro → alerta vermelho com confirmação obrigatória |
| CA-25 | Tarefa encerrada no Runrun.it → aviso exibido |
| CA-26 | Nenhuma consulta é disparada por tecla digitada |
| CA-27 | HTTP 429 → mensagem ao usuário e parada, sem repetição automática |
| CA-28 | Nenhuma requisição de escrita é emitida contra a API em nenhum fluxo |

---

## 12. Fora de Escopo (Nesta Fase)

- **Painel de Gestão e "Encerrar"** (P7) — ver NR2 e NR3.
- **Criação de listas novas em lote** — ver NR1.
- **Escrever no Runrun.it** (criar tarefa, comentar, alterar status) e listar, pesquisar ou sugerir tarefas enquanto se digita.
- Sincronizar datas da campanha a partir da tarefa; usar o Runrun.it como fonte do registro.
- ID automático para a loja Minha Loja (CB).
- **Tornar o repositório privado sem quebrar a atualização automática** — solicitação própria.
- Mover o `history.db` para fora da pasta de instalação — merece verificação e BRD próprio.
- Migrar de token compartilhado para autenticação por usuário — só se a política de segurança da Natura exigir.

---

## 13. Pendências e Validações

| # | O quê | Bloqueia | Situação |
|---|---|---|---|
| V1 | **TI:** confirmar que a automação da planilha pode ser publicada com acesso "Qualquer pessoa" e liberar `script.google.com` e `script.googleusercontent.com` no firewall | P5 | Aberta |
| V2 | **Conta de equipe** (não pessoal) dona da planilha e da automação | P5 | Aberta |
| V3 | **Salesforce:** reimportar o mesmo `pricebook-id` substitui ou mescla? | P3, P4 | ✅ **Respondida: substitui** |
| V4 | **Runrun.it:** `/tasks/:id` aceita o número visível da tarefa ou um identificador interno? | P6 | Aberta — teste de 10 min com token real |
| V5 | **Runrun.it:** nomes exatos dos campos de **título** e **situação** na resposta | P6 | Aberta — mesmo teste da V4 |
| V6 | **Runrun.it:** confirmar que o consumo do SIC não conflita com outras integrações da mesma App-Key, e que o plano cobre acesso à API | P6 | Aberta |
| V7 | **Salesforce:** qual mecanismo derruba a promoção, e qual comportamento se **deseja**? | P7 | Aberta — ver NR3 |
| V8 | **Runrun.it:** como obter o nome da pessoa dona do token | Melhor fonte de `created_by` — **não bloqueia a P2** | Aberta — mesmo teste da V4 |
| V9 | **Operação:** com que frequência chegam planilhas com várias abas **inéditas**? | Define se NR1 vira trabalho | Aberta |

**V1 e V2 podem entrar na fila agora**, porque a P5 depende delas e costumam demorar. As prioridades **P0 a P4 não dependem de nenhuma validação em aberto** — a única que as afetava, a V3, já foi respondida.
