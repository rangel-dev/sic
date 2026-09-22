# Análise de Negócio — Manutenção das Ações Segmentadas: registro de vínculos, reconhecimento na importação, manutenção em lote e confirmação no Runrun.it

**Documento:** BRD-012
**Autor:** Marcos (Analista de Negócios Jr)
**Data:** 21-09-2026
**Status:** Em construção — **P0, P1, P2, P3, P5 e P6 concluídos no código** (registro local + reconhecimento + compartilhamento via pasta do Google Drive + conferência da tarefa no Runrun.it, com testes). **P4 pausada**, aguardando o gestor responder V7 e a rodada de desenho da NR1 — é o único item de código que falta pra fechar tudo que não depende de terceiros. O caminho de compartilhamento via **OAuth foi abandonado por ora** (ver "Revisão da Etapa 1") em favor de uma pasta sincronizada — zero Google Cloud, zero API. **Falta, fora do código:** compartilhar a pasta de verdade no Drive da equipe (P5) e cadastrar App-Key/User-Token do Runrun.it em Configurações (P6).
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
| Autoria | **Dois campos** (D2): `created_by` (quem operou no SIC) e `task_creator` (quem abriu a tarefa no Runrun.it, vindo da Etapa 5) |
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

### P0 — Fechar o modelo de dados ✅ *concluído*

Registros gravados com o modelo errado viram migração em máquina de gente de verdade. Estas quatro decisões precisam estar fechadas **antes da primeira gravação**:

**D1 — A identidade do registro é o `pricebook_id`.** Um pricebook, um registro, atualizado no lugar. Sem isso há uma contradição: a proposta original manda o servidor recusar dois registros ativos com o mesmo `pricebook_id`, mas a atualização existe justamente para **reescrever** um pricebook existente — se cada salvamento criasse um registro novo, a regra de proteção mataria a funcionalidade principal. A decisão também espelha o Salesforce, onde reimportar o mesmo ID **substitui** (V3, respondida).

**D2 — o registro guarda dois campos de autoria, respondendo a duas perguntas diferentes** *(decidido nesta análise)*:

- **`created_by`** — quem registrou o vínculo no SIC (quem operou). Resolvido uma vez, no momento da escrita, nesta ordem: nome vindo do **Runrun.it** (quando o token estiver configurado, via `GET /users/me` — V8 confirmada) → nome digitado em Configurações → usuário do Windows. Como é gravado **no momento da escrita** e não consultado na leitura, a P2 sai com o usuário do Windows e os registros novos passam a nascer com o nome do Runrun.it quando a P6 chegar — **sem migrar nada**.
- **`task_creator`** — quem abriu a tarefa no Runrun.it (tipicamente o planejamento, que pediu a campanha). Vem **da própria tarefa consultada na Etapa 5**, não do token de quem opera o SIC. No teste da seção 14 (tarefa 2388), o campo mais provável para isso é `user_name`/`user_id` — a resposta já distingue esse par de `responsible_name`/`responsible_id` (o responsável atual pela tarefa), então "quem criou" e "quem está com a tarefa agora" já vêm separados. **Confirmar em um teste futuro** se `user_name` de fato corresponde ao criador e não a outro papel, antes de fechar a Etapa 5. Como depende da consulta da Etapa 5, `task_creator` só é preenchido quando a P6 estiver ativa — antes disso, o campo fica vazio, nunca bloqueando o registro.

**D3 — `campaign_name` precisa de alternativa.** A fonte prevista é o campo "Nome de Exibição do Pricebook", mas ele é **opcional** ("deixe em branco para omitir do XML"). Vazio, o banner da P3 mostra campanha em branco e a conferência cruzada da P6 não tem contra o que comparar. Ordem proposta: nome de exibição → rótulo LP da aba → nome da aba.

**D4 — A `loja` participa do reconhecimento.** A mesma aba pode virar pricebook na loja da marca **e** na Minha Loja (CB), que aceita SKUs de qualquer marca. São dois pricebooks distintos; sem a loja no casamento, o caso cai em "ambíguo" sem explicar o motivo real.

### P1 — Núcleo testável ✅ *concluído*

`app_paths.py` e `segmentada_registry.py`: modelo, montagem do ID, cálculo de status, regra de reconhecimento e armazenamento local, tudo com teste puro.
**Pronto quando:** testes verdes e `git diff` mostrando apenas arquivos novos. ✅ 159 testes verdes (47 novos), `git status` só com arquivos novos (`app_paths.py`, `segmentada_registry.py`, `test_app_paths.py`, `test_segmentada_registry.py`).

### P2 — Gravar de verdade, com escape ✅ *concluído*

A gravação no salvamento (ver Etapa 2) **mais um caminho de correção**: sem ele, o primeiro engano vira um registro errado sem saída — nas P2 e P3 a planilha ainda não existe, então a única alternativa seria editar um JSON na mão. O mínimo é apagar um registro e abrir a pasta do registro a partir de Configurações.
**Pronto quando:** CA-01 a CA-04 e CA-20. ✅ Verificado manualmente (sem tela automatizada — o projeto não tem `pytest-qt`): gerar e cancelar não grava nada (CA-02); salvar grava o registro completo, com `campaign_name` vindo do nome de exibição sem digitação extra (CA-01, CA-03); salvar o mesmo `pricebook_id` de novo atualiza no lugar, sem duplicar e sem resetar `created_at` (CA-04, D1). Escape hatch em Configurações → "Registry de Segmentadas (local)": lista os registros, apaga um selecionado, abre a pasta do registro.

### P3 — Reconhecimento na importação (uma lista) ✅ *concluído*

Campo do número da tarefa, montagem do ID e banner com confirmação obrigatória.
**Pronto quando:** CA-05 a CA-08. ✅ Verificado manualmente: sem vínculo salvo, o campo continua livre e o banner some (CA-05); vínculo para outra marca/loja aparece em vermelho, junto com registro expirado quando aplicável (CA-06); digitar o nº da tarefa monta `NAT-RR{id}`/`AVN-RR{id}`, editar o ID à mão trava o auto-preenchimento, e a loja CB nunca monta sozinha (CA-07); quando a contagem de SKUs cai, o banner e a confirmação de "ATUALIZAÇÃO" avisam quantos produtos vão perder o preço segmentado (CA-08). A pergunta de confirmação só aparece em modo ATUALIZAÇÃO (clique em "Usar"); "Ignorar" ou edição manual do ID mantêm o fluxo de hoje, sem pergunta extra.

### P4 — Manutenção em lote

Várias listas numa passada só: uma tela de conferência, uma confirmação, uma pasta de destino. É a entrega que realiza o cenário descrito na solicitação original ("carregar um Excel com 5 abas de manutenções").
**Pronto quando:** CA-09 a CA-14.

> **Este é o melhor ponto de parada.** O retrabalho acabou para quem gera as listas — sem rede, sem TI, sem dado saindo da máquina. Se a publicação do Apps Script for barrada, tudo o que foi entregue até aqui continua de pé.

### P5 — Compartilhar entre a equipe ✅ *código concluído (desenho revisado — pasta do Google Drive, não planilha/API)*

Implementado: `SyncedFolderRegistryStore` (um arquivo `.json` por `pricebook_id` na pasta sincronizada), `write_xlsx_snapshot` (planilha `.xlsx` de leitura, regerada a cada gravação) e `merge_by_pricebook_id` (junta local + compartilhado para o reconhecimento, seção 8). Em Configurações: checkbox "Compartilhar com a equipe" + seletor de pasta, desligado por padrão. Verificado manualmente (sem `pytest-qt`): gerar+salvar grava no local **e** na pasta compartilhada, o `.xlsx` é gerado, e uma segunda "máquina" (registro local vazio) reconhece um vínculo que só existe na pasta compartilhada.

**Trava contra escolher a pasta errada por engano.** A pasta só é selecionável por um seletor de diretório (não dá pra digitar um caminho à mão), o que já elimina erro de digitação. Além disso, se a pasta escolhida já tiver conteúdo mas **nada que pareça registro do SIC**, o SIC pede confirmação explícita antes de salvar — evita que alguém aponte sem querer pro Desktop ou Documentos e o compartilhamento fique "ligado" apontando pro lugar errado, silenciosamente sem sincronizar com ninguém. Isso nunca gera erro visível — só não compartilha de verdade, o que é bem menos grave do que parecer que "o programa deu problema".

**Pronto quando:** CA-15 a CA-19 (revisadas abaixo, o desenho mudou de planilha/API para pasta sincronizada) — CA-29 e CA-30 **não se aplicam mais** (não há chamada de API pra regular; ler/escrever arquivo local não tem o mesmo risco de estourar cota).

| # | Critério | Situação |
|---|---|---|
| CA-15 | Compartilhamento desligado ou pasta inacessível → XML gerado normalmente | ✅ Verificado — `_seg_shared_store()` devolve `None`; falha de escrita cai em `try/except` no worker |
| CA-16 | Sem rede, o reconhecimento usa o que está disponível localmente | 🔵 Coberto **pelo Google Drive para computador** (modo "Mirror files" mantém cópia local), não por código do SIC — recomendar esse modo no guia de configuração |
| CA-17 | Duas pessoas registrando quase ao mesmo tempo → nenhum registro perdido | ✅ Verificado **para `pricebook_id` diferentes** (arquivos distintos, sem disputa). Para o mesmo `pricebook_id` editado por duas pessoas quase ao mesmo tempo, quem resolve é o próprio Google Drive (cria "cópia conflitante") — não testado, risco residual baixo com 3 pessoas |
| CA-18 | Registro gravado offline sobe sozinho depois | 🔵 Coberto pelo Google Drive (sincronização automática da pasta), não por código do SIC |
| CA-19 | Envio inicial dos registros locais pré-existentes só após confirmação | ⚠️ **Não construído.** Registros gravados antes de ligar o compartilhamento **não migram sozinhos** para a pasta — só entram registros novos, a partir de quando a P5 for ligada. Migração explícita fica como trabalho futuro, se for necessária |

**Diferença importante do desenho original:** não existe mais "fila de pendências" nem "resolução de colisão na migração" como funcionalidades de código — a sincronização em si é responsabilidade do Google Drive para computador, não do SIC.

### P6 — Conferência no Runrun.it ✅ *concluído*

Cliente somente leitura, Configurações e conferência cruzada na tela. Também é aqui que `created_by` passa a vir do Runrun.it (D2).
**Pronto quando:** CA-21 a CA-28. ✅ Verificado manualmente (sem `pytest-qt`) — ver seção 11 para o detalhe de cada critério. `RunrunClient` com 13 testes automatizados isolados (sem chamada de rede real); suíte inteira: 193 testes verdes. `segmentado_engine.py` intocado.

⚠️ **`created_by` automático via Runrun.it (D2) ainda não foi ligado.** O cliente já tem `get_current_user_name()` (`/users/me`, V8 confirmada), mas a P2 (onde `created_by` é resolvido) continua usando só `getpass.getuser()` — trocar a ordem de fontes definida em D2 (Runrun.it → Configurações → Windows) fica como ajuste pequeno e isolado, não incluído nesta rodada.

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

### NR1 — Criação de listas novas em lote ⚠️ *escalado pela V9*

A Etapa 4, como desenhada, cobre só o **lote de manutenção**: listas que o SIC já conhece. Uma planilha que traga várias abas **inéditas** exigiria uma passada por lista, porque cada uma precisa do número da tarefa digitado e do cuidado da primeira vez.

**V9 respondida: abas inéditas chegam algumas vezes ao dia.** Isso não é um caso raro — é rotina. Com a frequência confirmada, criar em lote deixa de ser "trabalho não coberto, a avaliar" e passa a ser **lacuna real no desenho da Etapa 4**: mesmo depois de pronta, quem recebe uma planilha com abas novas ainda enfrentaria o problema original, uma aba de cada vez.

**Ainda não é uma decisão fechada — é uma decisão que falta tomar**, e que muda o desenho da Etapa 4, não só o cronograma. Um caminho possível: a tela de conferência (Etapa 4) já mostra cada lista com seu vínculo ou a falta dele; poderia aceitar, ali mesmo, o número da tarefa digitado para as linhas "novas", em vez de exigir sair do lote para cadastrá-las uma a uma. Isso precisa ser desenhado e não está neste documento — **retorna como pendência para a próxima rodada de análise antes de a Etapa 4 ser fechada para construção.**

### NR2 — O Painel: o que significa "ativa"? ✅ *respondida em 22-09-2026*

A proposta pede uma tela com "todas as ações ativas". Mas o SIC só sabe o que **ele mesmo gerou e salvou** — e salvar não é importar: o operador ainda sobe o arquivo no Business Manager. Um pricebook gerado e nunca importado apareceria como "ativo" sem estar no ar; um pricebook criado por outro caminho não apareceria.

A pergunta era: o Painel mostra **o que foi registrado pelo SIC** (honesto, mas incompleto) ou existe forma de confirmar o que está publicado no Salesforce (fora de alcance)?

**Resposta do usuário: a primeira.** Um terceiro caminho chegou a ser desenhado — usar o Runrun.it como fonte, varrendo tarefas com "Possui segmentação? Sim" — mas foi **descartado** depois de a investigação da API mostrar que enumerar tarefas é caro e sem ordenação confiável (detalhe na Etapa 6 redesenhada). O usuário descartou explicitamente o cenário "descobrir segmentadas que o SIC nunca tocou".

Fica assumido, de forma consciente: **o Painel mostra o que o SIC registrou, e isso é incompleto por construção.** A vigência vem do próprio registro (`online_from`/`online_to`), calculada por `compute_status` — não de consulta externa. Ver "Etapa 6 (redesenhada)".

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
- ~~Automação publicada como Web App, com as ações `list`, `upsert`, `upsert_batch` e `mark_ended`... acesso "Qualquer pessoa"... o token é a única proteção~~ — **superado, ver "Revisão" abaixo.** Testado com a implantação real em 22-09-2026: o Google intercepta a chamada e redireciona para login **antes** de o script rodar, porque a implantação está (e provavelmente só pode estar, por política do Workspace) como "Qualquer pessoa **na Natura**", não anônima de verdade — e um `requests`/`curl` sem sessão de navegador não tem como provar login nenhum. O desenho original de token-só não funciona contra essa implantação.
- Referência antiga do script em `tools/apps_script/registry.gs` — local (`tools/` no `.gitignore`), mantida como **Plano B documentado**, não como caminho principal.

### ⚠️ Revisão da Etapa 1 — de token anônimo para OAuth *(achado em teste real, 22-09-2026)*

**O problema não é a pessoa ter conta `natura.net` — é o processo que faz a chamada.** O SIC é um programa de desktop, sem sessão de navegador: uma chamada HTTP crua não carrega login Google nenhum, então "Qualquer pessoa na Natura" barra o SIC do mesmo jeito que barraria um estranho.

| | Continuar anônimo | **Autenticar de verdade (recomendado)** |
|---|---|---|
| Como | Pedir à TI uma exceção pra publicar como "Qualquer pessoa" (sem restrição de domínio) | O SIC abre o navegador, a pessoa loga uma vez com a conta Natura, o app guarda um token renovável |
| Depende de | Uma exceção de política que pode nem existir no Workspace da Natura — e que, se existir, expõe o endpoint à internet inteira, protegido só por um token compartilhado | Nada de exceção — é o jeito padrão do Google para apps de desktop (OAuth 2.0 "Installed App") |
| Autoria | Um segredo compartilhado pelas 3 pessoas — indistinguível quem escreveu o quê | Cada gravação carrega a identidade Google real de quem operou — resolve D2 de graça |
| Esforço | Já está pronto — só falta a permissão, que já se mostrou improvável | Código novo (fluxo OAuth), mas sem biblioteca nova |

**Recomendação: OAuth 2.0 "Installed App" (fluxo de desktop) direto contra a API do Google Sheets — abandonando o Apps Script Web App.**

Como funciona:
1. Na primeira vez (ou ao desconectar), o SIC abre o navegador padrão numa tela de login do Google pedindo consentimento pra ler/escrever a planilha.
2. A pessoa loga com a conta `natura.net` que já usa pra tudo.
3. O Google redireciona para `http://localhost:{porta}` — um servidor HTTP que o próprio SIC sobe só por esse instante, captura o código de autorização e se desliga. É o **fluxo por loopback**, o único que o Google ainda suporta para apps instalados — o método antigo de copiar e colar um código ("OOB") foi descontinuado.
4. O SIC troca o código por um **token de acesso** (curto) e um **token de renovação** (esse sim fica guardado, em `QSettings`, mesmo lugar do webhook hoje).
5. Daí em diante, cada chamada usa o token de acesso, renovado sozinho quando expira — sem pedir login de novo.

**Ganho colateral: dá pra abandonar o `LockService`/Apps Script inteiramente.** Sem um script intermediário, a escrita vira **só acréscimo** (`values.append`, operação atômica na própria API do Sheets): cada "upsert" é uma linha nova com todos os campos e um timestamp; quem lê considera **a última linha de cada `pricebook_id`** como o valor atual. Troca "impedir duas pessoas de escreverem ao mesmo tempo" por "nunca ter conflito porque ninguém sobrescreve nada" — mais simples, e D1 continua valendo do ponto de vista de quem usa (upsert por identidade); só a implementação interna vira "log com resolução na leitura" em vez de "sobrescrever a linha".

**Pré-requisito novo (organizacional, não técnico):** alguém com acesso ao Google Cloud da Natura precisa criar um **projeto vinculado à organização `natura.net`** e cadastrar um **Client ID tipo "App para computador"**. Com o projeto pertencendo à organização, a tela de consentimento pode ser marcada como **"Interna"** — nesse modo o Google **pula toda a verificação** (sem aviso de "app não verificado", sem limite de usuários, mesmo usando o escopo sensível de Planilhas), porque só quem tem conta `natura.net` consegue completar o login de qualquer jeito. Cadastro único, feito uma vez.

**Dependências novas:** nenhuma biblioteca nova — o fluxo inteiro dá pra fazer só com `requests` (já no projeto) mais `http.server` e `webbrowser` da biblioteca padrão do Python.

**Impacto no que já foi desenhado:**

| Peça | Antes (token anônimo) | Depois (OAuth) |
|---|---|---|
| `tools/apps_script/registry.gs` | Caminho principal | Descartado ou mantido só como Plano B |
| `GoogleSheetRegistryStore` (P1, ainda não implementado) | Chama o Web App com token | Chama `sheets.googleapis.com` com token OAuth renovável — a interface `RegistryStore` (`load`/`upsert`/`mark_ended`) **não muda** |
| `view_settings.py` (P5) | Campos de URL + token | Botão **"Conectar ao Google"**, indicação de quem está conectado, botão "Desconectar" |
| V1 (pendência de TI) | "Posso publicar como Qualquer pessoa?" | **V10** (nova): "Pode existir um projeto Google Cloud vinculado a `natura.net`, com tela de consentimento OAuth interna?" — pergunta mais fácil de aprovar, porque não expõe nada pra fora da organização |

Isso não muda nada da P0-P3, já construídas — o impacto é só na P5 (compartilhamento), que ainda não tinha código escrito.

**Verificação feita em 22-09-2026:** no Console do Google Cloud, a lista de projetos (`console.cloud.google.com/cloud-resource-manager`) mostra **"Nenhuma organização"** como pasta-mãe do único projeto visível (`gemini-natura-prd`) — ou a Natura nunca ativou o recurso de Organização no Google Cloud, ou existe uma mas a conta testada não tem visibilidade dela. Nos dois casos, a decisão é a mesma: **formalizar o pedido à TI** (opção escolhida nesta análise, em vez de prototipar agora com um projeto sem organização — que funcionaria, mas exibiria aviso de "app não verificado" a cada pessoa no primeiro login).

**Pedido pronto para encaminhar à TI (V10):**

> **Assunto:** Projeto Google Cloud vinculado à organização natura.net — automação interna do SIC
>
> O SIC (aplicativo desktop usado pelo time Comercial para gerar pricebooks) precisa de um jeito de cada pessoa da equipe autenticar com a própria conta Google (`@natura.net`) para ler e escrever numa planilha Google compartilhada do time — sem senha nem token compartilhado entre as pessoas, e sem que o SIC precise ficar acessível para fora da Natura.
>
> O caminho padrão do Google para isso é OAuth 2.0 com um **Client ID do tipo "App para computador"**, numa tela de consentimento marcada como **"Interna"** — modo em que só contas `@natura.net` conseguem logar, o Google não exige processo de verificação, e não aparece nenhum aviso de "app não verificado" para a equipe.
>
> Para isso funcionar, precisamos de uma das duas coisas:
> 1. Um **projeto no Google Cloud vinculado à organização `natura.net`** (Cloud Identity/Google Cloud Organization), com permissão para eu (ou outra pessoa indicada) criar esse Client ID e configurar a tela de consentimento como "Interna"; **ou**
> 2. Confirmação de que a Natura **não tem** esse recurso de Organização ativado no Google Cloud — nesse caso, precisaríamos saber se dá para ativá-lo, ou qual é o caminho alternativo que a TI prefere para esse tipo de automação interna.
>
> Não envolve custo (o nível gratuito do Google Cloud cobre esse uso) nem exposição de dados para fora da Natura — pelo contrário, substitui um modelo mais arriscado (token único compartilhado por chamadas anônimas) por login individual de cada pessoa, com a identidade de quem fez cada operação registrada automaticamente.

**Decisão desta análise: não esperar a resposta da V10 para começar a construir.** Avaliadas três formas de destravar sem depender de aprovação: (A) trocar a planilha por um arquivo numa pasta de rede já compartilhada — descartada, risco de escrita concorrente sem nenhum árbitro central e sem a autoria automática que é o ganho principal da D2; (B) OAuth **Externo**, usando um projeto Google Cloud que já existe e é acessível (`gemini-natura-prd`), com a tela de consentimento em modo "Teste" e as poucas pessoas da equipe cadastradas por e-mail como testadoras; (C) igual à B, mas com escopo restrito a "arquivo selecionado" (`drive.file`), mais elegante mas com mais código.

**Escolhida a opção B**, pelo ganho de autoria automática (a identidade Google de quem operou fica registrada, resolvendo D2) sem depender de ninguém aprovar nada agora. Único efeito colateral: cada pessoa vê uma tela "o Google não verificou este app" no primeiro login — inofensiva, só exige um clique em "Avançado → Acessar [app] (não seguro)".

A V10 (pedido à TI) **continua em pé, em paralelo, sem bloquear nada** — se um dia existir organização vinculada, a troca de "Externo com testadores" para "Interno" é só reconfiguração no Google Cloud, sem tocar no código do SIC.

**Pausa (22-09-2026):** ao concretizar os passos (criar o Client ID, decidir projeto, etc.), o usuário preferiu parar e reavaliar — inclusive cogitou estender o login para o SIC inteiro (10 pessoas) como base para um futuro registro de uso geral do aplicativo. Essa ideia **não é escopo deste BRD**: envolve monitorar o uso de todas as pessoas, o que precisa de proposta própria e transparente ao gestor (e possivelmente RH/compliance, dado LGPD sobre dado de funcionário), não algo decidido de lado dentro do ajuste do Segmentadas. Ficou registrado como possível BRD futuro, ainda não escrito.

### Terceira revisão da Etapa 1 — pasta do Google Drive, sem API nem OAuth *(22-09-2026, escolhida)*

No mesmo dia, ainda avaliando alternativas que não dependessem de aprovação de ninguém (nem TI, nem Google Cloud), surgiu uma terceira opção — e foi a **escolhida**: em vez de planilha + Apps Script/OAuth, o compartilhamento vira uma **pasta do Google Drive sincronizada localmente** (Google Drive para computador). Do ponto de vista do SIC, isso é só um caminho de pasta — sem API, sem OAuth, sem Google Cloud.

**Desenho:**
- `SyncedFolderRegistryStore`: um arquivo `<pricebook_id>.json` por registro dentro da pasta — duas pessoas mexendo em campanhas diferentes nunca disputam o mesmo arquivo, evitando a maior parte das "cópias conflitantes" que o Drive cria quando o mesmo arquivo é editado por duas máquinas quase ao mesmo tempo.
- `write_xlsx_snapshot`: gera, na mesma pasta, um `.xlsx` só de leitura a cada gravação — abre direto pelo Google Drive como planilha (Drive edita `.xlsx` nativamente no navegador), sem o SIC falar com a API do Sheets. Resolve o pedido de "ter uma sheet lá" sem reabrir a questão do OAuth.
- `merge_by_pricebook_id`: junta os registros locais com os da pasta compartilhada para o reconhecimento (seção 8) enxergar o que a equipe inteira já sabe, não só o que a própria máquina gravou.
- Em Configurações: checkbox "Compartilhar com a equipe" + seletor de pasta — desligado por padrão, mesmo espírito do resto do BRD.

**Por que essa e não as opções A/B/C anteriores:** a opção A (pasta de rede genérica) foi descartada por risco de concorrência sem nenhuma defesa; as opções B/C (OAuth) foram pausadas pelo próprio usuário por causa do peso de configurar Google Cloud. A pasta do Drive tem o ganho de concorrência da SyncedFolderRegistryStore (arquivo por registro) **sem precisar de nenhuma das duas coisas que geraram hesitação** — nem organização no Google Cloud, nem tela de login.

**Construído e testado manualmente** (sem `pytest-qt`, mesmo padrão das etapas anteriores): geração+salvamento grava no registro local **e** na pasta compartilhada; o `.xlsx` é regerado; uma segunda "máquina" (sem nada no registro local) reconhece um vínculo que só existe na pasta compartilhada. Ver seção 7 (Etapa 1 e P5) para o estado exato de cada critério de aceite.

**O que ainda falta, fora de código:** criar/compartilhar a pasta de verdade no Drive da equipe, instalar o Google Drive para computador nas 3 máquinas (recomendado modo "Mirror files", para funcionar offline — ver CA-16/CA-18), e configurar o caminho da pasta em Configurações. A V10 (pedido à TI sobre Google Cloud) **deixa de bloquear qualquer coisa** — continua em pé só como caminho alternativo de "polimento" (login individual, autoria automática do D2 via Google) para o futuro, não mais necessário para o compartilhamento funcionar.

**Proteção contra excesso de chamadas (requisito, não otimização — decidido nesta análise; ajustado após a revisão para OAuth acima).** A API do Google Sheets tem cota por projeto e por usuário (padrão de mercado, não específica da Natura), e multiplicar chamadas por engano continua sendo o jeito mais fácil de estourar isso silenciosamente. Por isso:

1. **A leitura é cacheada localmente** (`CachedRegistry`) e só é reconsultada sob ação explícita — abrir a tela de Segmentadas, um botão "Sincronizar" em Configurações, ou expiração do cache por tempo. **Nunca a cada seleção de lista na tabela.**
2. **A P4 (lote) usa uma única chamada `values.append` com todas as linhas do lote**, não uma chamada por lista. Processar 10 ou 20 listas não pode virar 10 ou 20 requisições HTTP sequenciais.
3. Falha de rede em qualquer chamada cai na **fila de pendências** (P5) e no cache local — nunca trava a geração ou o salvamento do XML, mesma regra da seção 8.

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
| `created_by` | nome de quem registrou o vínculo no SIC | Runrun.it (`/users/me`) → Configurações → usuário do Windows (D2) |
| `task_creator` | nome de quem abriu a tarefa no Runrun.it | resposta de `GET /tasks/{numero}` na Etapa 5 — vazio até a P6 estar ativa (D2) |
| `ended_at`, `source_file` | reservados à P7 | — |

O envelope carrega `schema_version` para permitir migração. **Só metadados saem do computador — nenhum preço e nenhuma lista de SKUs.**

⚠️ **A migração dos registros locais é explícita.** As etapas anteriores rodam antes de a planilha existir, então, quando esta entrar, haverá registros criados sob o combinado de que ficariam na máquina. Subi-los automaticamente mudaria a regra depois do fato. O envio inicial precisa **mostrar o que será enviado e pedir confirmação**; nunca ocorre sozinho.

### Etapa 2 — Registro passivo

O SIC passa a gravar um registro a cada segmentada salva, **sem alterar o fluxo de trabalho**.

- Novo `src/core/app_paths.py` — caminho de dados válido dentro do executável (`QStandardPaths.AppDataLocation`, com fallback em `%APPDATA%\SIC`). **Não** reutilizar o padrão de `history_engine.py:6,12` (`Path(__file__).parent.parent.parent`): dentro do executável (modo *onedir*, `sic.spec`) ele grava dentro da própria pasta de instalação, e dado do usuário guardado ali fica sujeito a reinstalação, limpeza da pasta e à falta de permissão de escrita em instalações legadas em `Program Files`.
- Novo `src/core/segmentada_registry.py` — `SegmentadaRecord`; `RegistryStore` **orientado a registro** (`load`, `upsert`, `mark_ended`); `GoogleSheetRegistryStore(url, token, timeout=5)` via `requests` (já em `pyproject.toml:15`); `JsonFileRegistryStore` como armazenamento local com escrita atômica; `CachedRegistry`.
- `view_settings.py` (já usa `QSettings` e `QFormLayout`, linhas 13 e 40-48): bloco "Registry de Segmentadas". ✅ Construído na P2 **só com o que fazia sentido sem compartilhamento**: lista os registros locais, apaga um selecionado, abre a pasta do registro. **URL, token, botão Testar (modelo `_test_webhook`, `:129`) e a chave liga/desliga do compartilhamento entram só na P5**, quando a planilha (Etapa 1) estiver publicada — antes disso não há o que testar nem o que ligar/desligar.

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
7. **Um registro por lista**, gravado sob a mesma regra da Etapa 2: só depois de o arquivo correspondente ter sido escrito. Localmente (P2-P4) isso é uma escrita em JSON por lista, sem rede. Quando a P5 existir, essas N gravações somam-se num **único** `values.append` ao final do lote, não N chamadas HTTP — ver "Proteção contra excesso de chamadas" na Etapa 1.

**Por que isso não enfraquece a trava.** A conferência mostra as cinco listas **lado a lado**, o que é melhor para revisão do que cinco caixas de diálogo isoladas: dá para comparar, notar a que destoa e desmarcá-la. A confirmação continua existindo — passa a ser uma, sobre o conjunto, em vez de uma por lista. É assim que o item A1 devolve o "é só clicar em Exportar" sem abrir mão da segurança.

**Fronteira.** O lote é de **manutenção**: listas que o SIC já reconhece. Criação de lista nova segue individual, porque exige o número da tarefa digitado e o cuidado da primeira vez — ver NR1.

**Dados que já existem e serão reaproveitados:** cada candidata já traz `sheet_name`, `lp_label`, `periodo_sugerido`, contagem de SKUs e avisos próprios (`ListaCandidate`, `segmentado_engine.py`). O período de cada lista vem do sugerido pela aba, editável na tela de conferência. A **loja** continua sendo uma escolha única para o lote, já que a grade é de uma marca.

### Etapa 5 — Confirmação da tarefa no Runrun.it *(antigo BRD-013)* ✅ *concluída*

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

### Etapa 6 — Painel de Gestão *(desenho original — substituído pela versão redesenhada abaixo)*

Tela com o status de cada lista (ativa, agendada, expirada), no padrão de `view_history.py`. Exige acrescentar uma página em `main_window.py` (`:179`, `:244-246`, `:305-309`, `:327`, `:332-345`) e estilos de aviso em `qss_light.py`/`qss_dark.py`.

### Etapa 6 (redesenhada) — Painel das Segmentadas do SIC *(desenho fechado em 22-09-2026; nenhuma linha de código ainda)*

**Ideia, do usuário:** uma aba dentro de Exportador → Segmentadas mostrando as segmentadas e seu status de vigência ("dentro da data").

**Caminho descartado (e por quê).** A primeira versão deste desenho propunha usar o **Runrun.it como fonte da lista** — varrer as tarefas com `custom_38 = "Possui segmentação? Sim"` e filtrar pela janela de datas da própria tarefa. Investigação em 22-09-2026 mostrou que isso é caro e mal resolvido pela API: `GET /tasks` não filtra por campo customizado nem por texto, e com `limit=100` devolve uma amostra que cobre IDs de 42 a 2737 (quatro meses) — ou seja, **não é uma lista "as N mais recentes"**, e montar o universo exigiria paginar a base inteira sem garantia de ordenação. Além disso, essa varredura contraria a proteção contra excesso de chamadas da própria Etapa 5.

**Decisão do usuário:** descartar o cenário "descobrir segmentadas que o SIC nunca tocou". O Painel mostra **o que o SIC registrou** — o que, na prática, **responde a NR2**: entre as duas saídas que ela colocava (o que o SIC registrou × o que está publicado no Salesforce), ficou a primeira, assumindo conscientemente que é honesta porém incompleta.

**Além disso, a data nunca precisou vir da API.** Ela já existe em dois lugares locais: o período da aba na grade (`periodo_sugerido`, extraído pelo `segmentado_engine`) e o `online_from`/`online_to` do próprio registro. O cálculo de vigência **já está construído e testado**: `compute_status` (P1) devolve `ativa` / `agendada` / `expirada` / `encerrada`.

**Desenho resultante — quase tudo já existe:**

| Peça | Situação |
|---|---|
| Fonte dos dados | `merge_by_pricebook_id(local, compartilhado)` — **pronto** (P5) |
| Cálculo de vigência | `compute_status(record, now)` — **pronto e testado** (P1) |
| Tela | **Único trabalho novo de verdade** — tabela no padrão de `view_history.py` |
| Enriquecimento com o Runrun.it | `RunrunClient.get_task` — **pronto** (P6), mas é consulta por tarefa: entra só sob ação explícita, nunca em varredura |

Colunas propostas: aba, `pricebook_id`, campanha, período, **status**, SKUs, quem registrou, última atualização. Ordenação sugerida: o que vence primeiro no topo.

**Decisões que faltam (pequenas, de produto):**

1. **Expiradas aparecem por padrão?** Proposta: não — mostrar ativas e agendadas, com uma opção para incluir o histórico.
2. **Conferir no Runrun.it entra na v1?** Um botão por linha ("conferir tarefa") reaproveitando a P6, sempre sob clique — nunca automático para a lista inteira, pela proteção da App-Key.
3. **Onde a aba vive.** Dentro da tela de Segmentadas (`QTabWidget`) ou como página própria no menu? ⚠️ Se for dentro da tela, **disputa o mesmo arquivo que o BRD-015** (unificação Grade Completa × Segmentadas) e que a Etapa 4 — mesma advertência da seção 9.

**Ainda sem prioridade (P) atribuída** — mas, diferente do desenho anterior, não depende de nenhuma investigação externa: as três decisões acima são de produto, e o resto já está construído.

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
| `tools/apps_script/registry.gs` *(local, não versionado)* | 1 *(abandonada)* | Automação da planilha — Plano B, não é mais o caminho principal | — |
| `src/core/app_paths.py` *(novo)* | 2 | Caminho de dados no executável | Baixo |
| `src/core/segmentada_registry.py` *(novo)* | 2, 3, 4, 5 | Registro, resolução de vínculo, `SyncedFolderRegistryStore`, `merge_by_pricebook_id`, `write_xlsx_snapshot` | Baixo — código novo e isolado |
| `src/workers/worker_segmentada_registry.py` *(novo)* | 2, 5 | Grava o registro (local e/ou pasta compartilhada) e regera o `.xlsx`, em segundo plano | Baixo |
| `src/core/runrun_client.py` *(novo)* | 5 | Cliente somente leitura (`get_task`, `get_current_user_name`) | Baixo — 13 testes isolados, sem Qt |
| `src/workers/worker_runrun_task.py` *(novo)* | 5 | Consulta a tarefa em segundo plano | Baixo |
| `src/ui/pages/view_settings.py` | 2, 5 | Bloco "Registry de Segmentadas" (local + compartilhamento) e bloco "Runrun.it — Conferência de Tarefa" (App-Key/User-Token mascarados, liga/desliga, testar) | Baixo |
| `src/ui/pages/view_exportador_segmentadas.py` | 2, 3, 5 | Gravação, campo do Runrun.it com consulta ao sair do campo, banner, conferência cruzada. Validações 601-620 **intactas**. Etapa 4 (lote) ainda não construída | Baixo-médio — aditivo, sem tela nova de lote ainda |
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

**Compartilhamento (P5)** — desenho revisado em 22-09-2026 (pasta do Google Drive, não planilha/API); detalhe e situação de cada critério na seção 7, "P5 — Compartilhar entre a equipe". CA-29 e CA-30 (proteção contra excesso de chamadas de API) **não se aplicam mais** nesse desenho.

| # | Critério | Situação |
|---|---|---|
| CA-15 | Compartilhamento desligado ou pasta inacessível → XML gerado e salvo normalmente | ✅ |
| CA-16 | Sem rede, o reconhecimento usa o que está disponível localmente | 🔵 Coberto pelo Google Drive para computador |
| CA-17 | Duas pessoas registrando quase ao mesmo tempo → nenhum registro perdido | ✅ para `pricebook_id` diferentes; mesmo `pricebook_id` fica a cargo do Drive |
| CA-18 | Registro gravado offline **sobe sozinho** depois | 🔵 Coberto pelo Google Drive para computador |
| CA-19 | Migração dos registros locais pré-existentes só após confirmação | ⚠️ Não construído — registros antigos não migram sozinhos |

**Transversal**

| # | Critério |
|---|---|
| CA-20 | O fluxo atual (ID digitado à mão, uma lista por vez) funciona idêntico, com e sem registro configurado |

**Runrun.it (P6)** — todos ✅ verificados manualmente (roteiro de smoke test dedicado) e/ou cobertos pelos 13 testes automatizados de `RunrunClient`.

| # | Critério | Situação |
|---|---|---|
| CA-21 | Número válido → título da tarefa exibido antes de gerar o XML | ✅ |
| CA-22 | Número inexistente → aviso claro, campo continua utilizável | ✅ (`RunrunClient.get_task` levanta `RunrunUnavailable` em 404; a tela mostra aviso discreto, campo segue editável) |
| CA-23 | Integração desligada, sem credencial ou indisponível → a tela se comporta exatamente como hoje | ✅ (`_seg_runrun_client()` devolve `None`, nenhuma consulta é feita) |
| CA-24 | Título divergente do registro → alerta vermelho com confirmação obrigatória | ✅ |
| CA-25 | Tarefa encerrada no Runrun.it → aviso exibido | ✅ |
| CA-26 | Nenhuma consulta é disparada por tecla digitada | ✅ (consulta só em `editingFinished`, nunca em `textEdited`) |
| CA-27 | HTTP 429 → mensagem ao usuário e parada, sem repetição automática | ✅ (`RunrunRateLimited`, testado — nenhuma tentativa automática de novo) |
| CA-28 | Nenhuma requisição de escrita é emitida contra a API em nenhum fluxo | ✅ (`RunrunClient` só tem métodos `GET`) |

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
| V1 | ~~**TI:** confirmar que a automação da planilha pode ser publicada com acesso "Qualquer pessoa"~~ e liberar `script.google.com` e `script.googleusercontent.com` no firewall | P5 | 🟡 **Parcial** — o firewall segue liberado; o teste real de 22-09-2026 mostrou que "Qualquer pessoa" (anônimo) provavelmente não é possível no Workspace da Natura. **Substituída pela V10.** |
| V10 | **TI/Google Cloud:** pode existir um projeto Google Cloud vinculado à organização `natura.net`, com um Client ID OAuth tipo "App para computador" e tela de consentimento marcada como "Interna"? | Nenhuma — P5 não depende mais disso | 🟡 Enviada ao TI, sem resposta ainda — mas **não bloqueia nada**: a P5 foi construída via pasta do Google Drive (terceira revisão da Etapa 1), sem precisar de OAuth. V10 vira só um "polimento" futuro opcional |
| V2 | **Conta de equipe** (não pessoal) dona da planilha e da automação | P5 | ✅ **Confirmada** — conta do gestor, com acesso de equipe à planilha |
| V3 | **Salesforce:** reimportar o mesmo `pricebook-id` substitui ou mescla? | P3, P4 | ✅ **Respondida: substitui** |
| V4 | **Runrun.it:** `/tasks/:id` aceita o número visível da tarefa ou um identificador interno? | P6 | ✅ **Respondida: aceita o número visível** — ver seção 14 |
| V5 | **Runrun.it:** nomes exatos dos campos de **título** e **situação** na resposta | P6 | ✅ **Respondida** — ver seção 14 |
| V6 | **Runrun.it:** confirmar que o consumo do SIC não conflita com outras integrações da mesma App-Key, e que o plano cobre acesso à API | P6 | ✅ **Respondida** — ver seção 14 |
| V7 | **Salesforce:** qual mecanismo derruba a promoção, e qual comportamento se **deseja**? | P7 | 🟡 Enviada ao gestor — aguardando resposta |
| V8 | **Runrun.it:** como obter o nome da pessoa dona do token | Melhor fonte de `created_by` — **não bloqueia a P2** | ✅ **Respondida: `GET /users/me`** — ver seção 14 |
| V9 | **Operação:** com que frequência chegam planilhas com várias abas **inéditas**? | Define se NR1 vira trabalho | ✅ **Respondida: algumas vezes ao dia** — ver NR1, escalado |

**V2, V4, V5, V6 e V8 confirmadas; V1 rebaixada a parcial.** A V10 nasceu do teste real da implantação anônima (22-09-2026), mas **deixou de bloquear a P5** depois da terceira revisão da Etapa 1 (pasta do Google Drive, sem API/OAuth) — fica só como caminho de polimento futuro, opcional. **Nenhuma prioridade de código (P0 a P3, P5) depende de validação em aberto.** Só a P4 segue pausada (V7 com o gestor, e a rodada de desenho da NR1, escalada pela V9).

---

## 14. Teste da API do Runrun.it (V4, V5, V6, V8) — resultado

Teste manual, fora do código do SIC, com um `App-Key` e `User-Token` reais. Cobriu as pendências que só um teste com credencial real resolve.

**Como o teste foi feito — por segurança, não pela via mais direta.**

O `User-Token` age em nome da pessoa dona dele na conta inteira do Runrun.it, não só na leitura de uma tarefa — é mais parecido com uma senha do que com uma chave de leitura. Colar o token diretamente numa mensagem de chat o deixaria registrado no histórico da conversa de forma permanente, o que foi evitado.

Caminho adotado: o token ficou apenas num arquivo `.env` local, **na raiz do repositório mas coberto pelo `.gitignore`** (`.env` e `.env.*`, adicionados antes de o arquivo existir, como rede de segurança — confirmado com `git check-ignore` que ele nunca aparece em `git status` nem seria commitado). Cada chamada à API rodou só depois de autorização explícita, uma por vez — nenhuma foi encadeada, e nenhuma escrita foi feita, só leitura. O valor do token nunca apareceu na saída de nenhum comando. O arquivo `.env` foi mantido localmente por decisão do usuário, para servir de base a testes futuros importantes.

**Roteiro e resultado:**

1. `GET /api/v1.0/tasks/2388` (tarefa real, enviada pelo gestor) → **HTTP 200**, com os dados da tarefa certa (`title: "Segmentada - Ofertas Semanais Exclusivo Ecom - sem 3"`, `id: 2388`). **V4 resolvida: o número visível da tarefa é aceito diretamente — não existe identificador interno separado.**
2. Nomes de campo confirmados na mesma resposta — **V5 resolvida:**
   - Título: `title`.
   - Situação: não há um único campo "status"; a resposta traz várias fontes coerentes entre si — `task_status_name`, `task_status_id`, `state`, `is_closed`, `board_stage_name`, `board_stage_id`. Para o alerta de "tarefa encerrada" (Etapa 5), o candidato mais direto é `is_closed`, com `task_status_name` como texto de apoio no aviso.
3. `GET /api/v1.0/users` (rodado numa etapa anterior) devolveu a lista completa de 24 pessoas da conta, sem marcação de "esta é você". Um teste seguinte a `GET /api/v1.0/users/me` respondeu **HTTP 200** (enquanto `/me`, `/whoami` e `/user` responderam 404). Inspecionando o corpo: **a rota devolve um único registro** — o da pessoa dona do token, não a lista inteira — com `id`, `name`, `email` entre outros campos. **V8 resolvida: `GET /api/v1.0/users/me` é a fonte automática de `created_by` (D2).** *(Nomes e e-mails reais que apareceram no teste não são citados aqui por serem dado pessoal, desnecessário num repositório público — o que importa para o desenho é o formato da resposta, já confirmado.)*

**V6 — resolvida por resposta da operação, sem chamada de API:**

- **Sem conflito de leitura entre integrações.** Cada consulta é feita pelo número da tarefa (`/tasks/{numero}`), e cada tarefa é um recurso isolado — não existe cenário em que a leitura de uma tarefa por uma integração interfira na leitura da mesma ou de outra tarefa por outra integração. O risco documentado na Etapa 5 (estourar os 100 req/min e arriscar a revogação da App-Key) continua válido como cuidado de engenharia, mas não é um risco de **conflito** com outro sistema.
- **Esta é a primeira integração do usuário dono deste token.** Não há hoje nenhum outro sistema consumindo a API do Runrun.it com essas credenciais — logo, não há nada em produção que o SIC possa atrapalhar ao começar a usá-las.

### Achado adicional (22-09-2026): campo "Possui segmentação?" no formulário do Runrun.it

Fora do escopo original do teste, mas relevante para qualquer trabalho futuro de busca/filtro de tarefas de Segmentadas. O formulário "Solicitação de Promoção (Cupons e Mecânicas)" (`form_id: 133302`) tem, na aba lateral da tarefa, uma pergunta estruturada **"Possui segmentação? Sim/Não"** — documentada no arquivo local `Formulário Runrun x Salesforce.pdf` (fora do repositório), que mapeia os campos do formulário do Runrun.it para o Salesforce (ex.: *Possui segmentação = Customer Groups (Campaign)*).

Comparando os `custom_fields` de duas tarefas reais via API — **#2388** ("Segmentada - Ofertas Semanais...") e **#2626** ("cupom dia da cb ML", não-segmentada) — o campo **`custom_38` é "Possui segmentação?"** (`Sim` na #2388, `Não` na #2626), com evidência cruzada de dois outros campos-texto que só apareciam preenchidos quando a pergunta correspondente do formulário era "Sim" (`custom_78`/`custom_75`, ligados a "possui mensagem de erro"/"possui limite por CPF").

**Tratado como fixo por decisão do usuário (22-09-2026), até segunda ordem:** o número do campo (`custom_38`) pode mudar se o formulário for editado por quem administra o Runrun.it — o formulário já está ganhando campos novos (ver PDF, itens marcados "*Novo campo"). Não é o SIC nem quem mantém este documento que administra esse formulário; **se mudar, a pessoa responsável pelo formulário no Runrun.it precisa avisar**, e este documento é atualizado a partir daí. Até lá, `custom_38 = "Possui segmentação?"` é tratado como verdade conhecida.

Não implica código novo agora — é só um achado registrado para o dia em que uma busca/filtro por "tarefas de Segmentadas" via API for construída (ver conversa sobre busca de cards, fora do escopo formal do BRD).
