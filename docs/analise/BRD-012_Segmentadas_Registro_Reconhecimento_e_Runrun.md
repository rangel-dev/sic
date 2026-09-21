# Análise de Negócio — Manutenção das Ações Segmentadas: registro de vínculos, reconhecimento na importação e confirmação da tarefa no Runrun.it

**Documento:** BRD-012
**Autor:** Marcos (Analista de Negócios Jr)
**Data:** 21-09-2026
**Status:** Rascunho para análise — **nenhuma linha de código autorizada**
**Solicitação:** "Manutenção das Ações Segmentadas" (formulário Solicitação de Evolução Integrada)
**Branch:** A definir (este documento sobe em `docs/brd-012-registry-segmentadas`)
**Pré-requisitos:** nenhum. Independente do BRD-014.
**Nota de numeração:** o conteúdo do antigo **BRD-013** (integração com a API do Runrun.it) foi incorporado a este documento como a **Etapa 4**, e o BRD-013 foi removido. Os commits `cdb79c7` e `a2e5fb5` (já publicados) citam BRD-013 e se referem à Etapa 4 deste documento.

---

## 1. Sumário Executivo

O SIC gera o XML do Pricebook Segmentado e esquece dele logo em seguida. Como os IDs seguem as tarefas do Runrun.it e são digitados à mão, o sistema não sabe quais listas já existem, de qual tarefa cada aba da planilha faz parte, nem como atualizar uma lista sem que o operador redigite tudo. O principal ponto de dor é a **manutenção**: quando o time de planejamento envia uma nova planilha com preços atualizados de várias segmentadas ativas, hoje é preciso deletar os pricebooks antigos e recriar tudo do zero, redigitando cada ID.

Este BRD propõe dar **memória compartilhada** ao SIC, em três etapas de escopo definido, uma quarta em análise e duas etapas futuras:

1. Uma **planilha Google da equipe**, acessada por uma pequena automação, guarda o vínculo entre a aba do Excel e o ID da tarefa.
2. O SIC passa a **registrar** cada lista que gera, sem mudar nada no fluxo de trabalho.
3. O SIC **reconhece** na importação as abas que já conhece e monta o ID a partir do número da tarefa, sempre pedindo confirmação.
4. *(em análise)* O SIC **confere a tarefa no Runrun.it**, exibindo o título antes de gerar, para que um número trocado deixe de virar preço errado na loja.

**Decisões tomadas com o usuário nesta análise:**

| Decisão | Escolha |
|---|---|
| Onde o registro fica | Planilha Google com automação, e cache local no computador de cada pessoa |
| Escopo de hoje | Etapas 1 a 3 (registro e reconhecimento). A Etapa 4 (Runrun.it) fica **documentada para análise**: a construção depende das pendências 4 a 6 |
| ID automático | Só **Natura** (`NAT-RR{id}`) e **Avon** (`AVN-RR{id}`). Minha Loja (CB) continua manual |
| Nome de aba reaproveitado entre ciclos | **Sim** — o vínculo nunca é aplicado sem confirmação explícita |
| Runrun.it | **Somente leitura**; o operador digita o número e confere; a App-Key já existe e o usuário tem acesso a ela |
| Painel de Gestão e botão "Encerrar" | **Etapas futuras**, fora do escopo de hoje |

---

## 2. Situação Atual (AS-IS)

`src/ui/pages/view_exportador_segmentadas.py` recebe o `pricebook_id` num campo de texto livre (`_seg_input_pbid`, linha ~140). As únicas validações, em `_run_seg_generate` (linhas 601-620), são: campo não vazio, sem espaço em branco e fora de `RESERVED_PRICEBOOK_IDS`. Não há máscara, verificação de prefixo `NAT-`/`AVN-` nem checagem de duplicidade.

Após gerar, o `HistoryEngine` grava apenas um texto livre (`:694-698`): *"Pricebook Segmentado (LISTA_48) gerado — 128 SKUs."* Não grava o `pricebook_id`, as datas, o parent nem a marca. **Nenhuma informação do pricebook gerado é persistida.**

Consequências operacionais:

- Sem vínculo salvo, a manutenção exige deletar os pricebooks antigos e recriar tudo.
- Os IDs baseados nas tarefas do Runrun.it são redigitados manualmente, com risco de erro de digitação.
- Não há como associar rapidamente a qual ID (ex.: `NAT-RR1111`) a `LISTA_48` pertence.
- Nada confirma que o número digitado corresponde à campanha pretendida: um erro só apareceria depois, como preço errado na loja.

---

## 3. Decisão de Arquitetura — por que não o Git como banco de dados

A primeira proposta previa um arquivo `segmentadas_registry.json` versionado no repositório e sincronizado entre a equipe por `git pull`/`git push`. Ela foi **descartada** por três motivos verificados:

1. **O repositório é público.** `rangel-dev/sic` retorna `"visibility": "public"` na API do GitHub. O registro guardaria nome de campanha, datas de vigência e volume de SKUs — o calendário promocional da Natura e da Avon ficaria exposto, inclusive campanhas ainda não lançadas.
2. **Os usuários não têm o repositório.** O SIC é distribuído como executável (PyInstaller + Inno Setup, instalado em `%LOCALAPPDATA%\SIC`, com atualização automática via GitHub Releases). As demais pessoas da equipe não têm o repositório clonado, nem Git, nem Python; e dentro do executável não existe uma "pasta do projeto" gravável.
3. **Precedente do projeto.** O `history.db` está no `.gitignore` de propósito: dado de operação nunca foi versionado neste projeto.

**Solução adotada:** uma **planilha Google da equipe** como fonte da verdade, acessada por uma automação (Apps Script publicado como Web App), com uma **cópia local em cache** no computador de cada pessoa. A concorrência entre as 3 pessoas é resolvida no servidor do Google, não no SIC, o que evita a escrita perdida e a "cópia em conflito" de uma pasta sincronizada.

A separação do repositório em código privado e instaladores públicos, necessária para o aspecto de privacidade, é **tratada em solicitação própria** e está fora deste BRD.

---

## 4. Etapas

### Etapa 1 — Planilha e automação (fora do código Python)

- Planilha no Drive de uma **conta de equipe** (não pessoal), aba `registry`, acesso restrito ao time.
- Automação publicada como Web App, com as ações `list`, `upsert` e `mark_ended`. O `upsert` age **por `id`** — nunca reescreve a lista inteira.
- Toda escrita sob `LockService.getScriptLock()`. O token é lido de `PropertiesService.getScriptProperties()`: **nunca fica no código do script**. O servidor recusa dois registros ativos com o mesmo `pricebook_id`.
- ⚠️ Um aplicativo de desktop sem login Google só chama o Web App se ele for publicado com acesso **"Qualquer pessoa"**. Nesse modelo a URL é alcançável sem autenticação e **o token é a única proteção** — deve ser tratado como senha (longo, aleatório, rotacionável).
- Referência do script versionada em `tools/apps_script/registry.gs`, **sem token**.

**Formato do registro:**

| Campo | Exemplo |
|---|---|
| `id` | identificador interno único |
| `sheet_name` | `LISTA_48` |
| `lp_label` | rótulo LP da aba |
| `runrun_id` | `1111` |
| `pricebook_id` | `NAT-RR1111` |
| `brand`, `loja` | `natura`, `natura` |
| `campaign_name` | "Favoritos RR18/21" |
| `online_from`, `online_to` | datas de vigência (UTC, no formato do XML) |
| `sku_count` | quantidade de SKUs |
| `created_at`, `updated_at`, `created_by` | autoria e datas |
| `ended_at`, `source_file` | reservados às etapas futuras |

O envelope carrega `schema_version` para permitir migração. **Só metadados saem do computador — nenhum preço e nenhuma lista de SKUs.**

### Etapa 2 — Registro passivo

O SIC passa a gravar um registro a cada segmentada gerada, **sem alterar o fluxo de trabalho**. Entrega valor sozinha: o registro começa a ser alimentado.

- Novo `src/core/app_paths.py` — caminho de dados válido dentro do executável (`QStandardPaths.AppDataLocation`, com fallback em `%APPDATA%\SIC`). **Não** reutilizar o padrão de `history_engine.py:6,12` (`Path(__file__).parent.parent.parent`), que dentro do executável aponta para uma pasta temporária.
- Novo `src/core/segmentada_registry.py` — `SegmentadaRecord`; `RegistryStore` **orientado a registro** (`load`, `upsert`, `mark_ended`; uma API de "salvar a lista inteira" reintroduziria a perda de escrita de um colega); `GoogleSheetRegistryStore(url, token, timeout=5)` via `requests` (já em `pyproject.toml:15`); `JsonFileRegistryStore` como cache local com escrita atômica; `CachedRegistry` (Sheets disponível → atualiza o cache; indisponível → devolve o cache marcado como desatualizado, com o horário).
- `view_settings.py` (já usa `QSettings` e `QFormLayout`, linhas 13 e 40-48): bloco "Registry de Segmentadas" com URL, token, botão **Testar** (modelo `_test_webhook`, `:129`) e chave liga/desliga.
- `view_exportador_segmentadas.py`: após o `HistoryEngine.add_entry` (`~:699`), gravar em segundo plano (padrão de `worker_segmentado.py:13-17`), dentro de `try/except`.
- **Desligado por padrão:** sem URL configurada, o SIC não faz nenhuma chamada nova.

### Etapa 3 — Reconhecimento na importação

Em `view_exportador_segmentadas.py`:

- Novo campo **"Nº da tarefa Runrun.it"** acima de `_seg_input_pbid`. Ao digitar, o SIC monta o ID (`NAT-RR{id}` / `AVN-RR{id}`) **apenas se o campo de ID não tiver sido editado à mão** (flag `_pbid_touched`, ligada ao `textEdited`). Para a loja CB o campo segue manual.
- Ao selecionar uma lista (`_on_seg_lista_selected`, `~:570`), o SIC consulta o registro e exibe um **banner de confirmação**:

  `LISTA_48 → NAT-RR1111 · "Favoritos RR18/21" · 01/09–14/09 · registrada em 28/08 · antes 128 SKUs / agora 118`

  com os botões **"Usar (ATUALIZAÇÃO)"** e **"Ignorar — é campanha nova"**. Sem clique, o campo de ID permanece vazio e livre.
- A comparação de `sku_count` reaproveita o campo já gravado e denuncia queda inesperada de produtos.
- Em `_run_seg_generate`, acrescentar **somente** uma pergunta de confirmação quando o modo for ATUALIZAÇÃO, com o `pricebook_id` em destaque. As validações 601-620 permanecem intactas.

### Etapa 4 — Confirmação da tarefa no Runrun.it *(antigo BRD-013 — em análise)*

**Problema.** O BRD só reduz o risco de número trocado quando já existe um vínculo salvo; não cobre o **primeiro cadastro** de uma lista nem detecta um número simplesmente digitado errado. Hoje nada confirma que "1111" é mesmo a campanha em mãos.

**Situação desejada.** Ao sair do campo "Nº da tarefa Runrun.it" (perda de foco ou Enter — **nunca a cada tecla**), o SIC consulta a tarefa e exibe o título ao lado do ID montado:

```
1111  →  NAT-RR1111  ·  "Favoritos RR18/21"
```

- Tarefa encerrada no Runrun.it → aviso visível.
- Número inexistente → aviso claro, **sem travar o campo**.
- Integração desligada, sem credencial ou Runrun.it indisponível → a tela funciona exatamente como hoje.

O título retornado passa a preencher o campo `campaign_name` do registro, hoje digitado à mão.

**Conferência cruzada.** Passam a existir três fontes sobre a mesma lista:

| Fonte | O que afirma |
|---|---|
| Nome da aba na planilha | "esta lista se chama LISTA_48" |
| Registro (Etapas 1 a 3) | "a LISTA_48 foi vinculada à tarefa 1111, campanha *Favoritos RR18/21*" |
| **Runrun.it** | "a tarefa 1111 é, de fato, *«…»*" |

Quando o registro e o Runrun.it **divergem** — o registro guarda "Favoritos RR18/21" mas o Runrun.it responde outro título para a 1111 —, isso indica registro desatualizado ou aba reaproveitada apontando para o vínculo errado. O SIC destaca a divergência em vermelho e **exige confirmação explícita**, no mesmo padrão de segurança da Etapa 3. Esta etapa não só confirma o número digitado: ela **reforça a trava da Etapa 3** com uma fonte independente.

**Proteção da App-Key (requisito, não otimização).** A documentação do Runrun.it estabelece **100 requisições por minuto**, com resposta HTTP 429 ao estourar, e adverte que **o uso abusivo leva à revogação da App-Key**. Como essa chave pertence à conta da Natura e não ao SIC, um defeito no aplicativo — laço de repetição, consulta a cada tecla — poderia derrubar integrações de **outras áreas**. Por isso:

1. Consulta apenas por ação explícita (saída de foco, Enter ou botão). **Nunca por tecla digitada.**
2. Cache em memória por sessão: a mesma tarefa não é consultada duas vezes.
3. O `campaign_name` já gravado no registro é exibido de imediato, servindo de cache entre sessões.
4. **Sem repetição automática** em caso de 429: o SIC informa e para.
5. Intervalo mínimo entre consultas consecutivas.
6. Chave de liga/desliga em Configurações, independente do registro.

Volume esperado: **unidades de chamadas por sessão**, contra um teto de 100 por minuto.

**Credenciais.** Autenticação por cabeçalhos `App-Key`, `User-Token` e `Content-Type: application/json`, sobre a base `https://runrun.it/api/v1.0`. A **App-Key** é da conta da empresa (Configurações → Integrações → App); o **User-Token é pessoal**, obtido no perfil de cada pessoa. ⚠️ O User-Token dá acesso à conta inteira daquela pessoa no Runrun.it, não apenas à leitura de uma tarefa. Consequências: campo mascarado na tela; armazenamento em `QSettings("SIC","SIC_Suite")`, como o `gchat_webhook` já faz (`view_settings.py:104-109`), **nunca no repositório**; instrução na interface de como revogar o token pelo próprio perfil.

Novo `src/core/runrun_client.py` — `RunrunClient(app_key, user_token, timeout=5)` e `get_task(numero) -> RunrunTask | None`; falhas viram `RunrunUnavailable`. Sem Qt, apenas `requests`.

### Etapa 5 — Painel de Gestão *(futura — fora do escopo de hoje)*

Nova tela com o status colorido de cada lista (ativa, agendada, expirada), no padrão de `view_history.py`. Exige acrescentar uma página em `main_window.py` (`:179`, `:244-246`, `:305-309`, `:327`, `:332-345`) e estilos de aviso em `qss_light.py`/`qss_dark.py`.

### Etapa 6 — Encerrar promoção *(futura — bloqueada)*

Geração de um XML com `online-to` no passado, usando o `pricebook_id` do registro, para derrubar a promoção sem abrir planilha. O motor já suporta — `build_xml` aceita lista de SKUs vazia (`tests/test_segmentado_engine.py:435-444`) —, mas **o comportamento no Salesforce não foi validado** (ver Pendências).

---

## 5. Regras de Negócio Transversais

- **A confirmação nunca é dispensada.** O nome da aba é reaproveitado entre ciclos: a `LISTA_48` de hoje pode ser outra campanha. Um vínculo resgatado jamais é aplicado sem o clique do operador.
- **Confiança do vínculo:** `exact` (aba + `lp_label` + marca batem), `sheet_only` (só a aba bate — chave fraca), `ambiguous` (2 ou mais registros para a mesma aba) e `none`. Em `sheet_only`, `ambiguous`, registro expirado, `lp_label` divergente ou registro com mais de 90 dias, o banner fica **vermelho** e explica que o nome da aba é reaproveitado entre ciclos.
- **O registro nunca bloqueia o trabalho.** Toda leitura e gravação ocorre fora da tela principal, com tempo limite de 5 segundos; falha do registro **jamais impede gerar ou salvar o XML**.
- **Aditivo.** O fluxo atual — digitar o ID à mão — permanece idêntico. Nenhuma linha de `segmentado_engine.py` muda.

---

## 6. Análise de Impacto

| Arquivo | Etapa | Mudança | Risco |
|---|---|---|---|
| `tools/apps_script/registry.gs` *(novo)* | 1 | Automação da planilha | Baixo — fora do executável |
| `src/core/app_paths.py` *(novo)* | 2 | Caminho de dados no executável | Baixo |
| `src/core/segmentada_registry.py` *(novo)* | 2, 3 | Registro, cache, resolução de vínculo | Baixo — código novo e isolado |
| `src/core/runrun_client.py` *(novo)* | 4 | Cliente somente leitura | Baixo |
| `src/ui/pages/view_settings.py` | 2, 4 | Blocos de configuração do registro e do Runrun.it | Baixo |
| `src/ui/pages/view_exportador_segmentadas.py` | 2, 3, 4 | Gravação passiva, campo do Runrun.it, banner, confirmação. Validações 601-620 **intactas** | **Médio** — tela do fluxo crítico; precisa ser estritamente aditivo |
| `README.md` e `docs/seguranca/` | 2, 4 | Ver seção 7 | Nulo em runtime |
| `segmentado_engine.py` e demais engines | — | **Nenhuma alteração** | — |

---

## 7. Privacidade, Segurança e Comunicação com a TI

- **O que sai do computador:** nome da aba, ID da tarefa, nome da campanha, datas, marca e quantidade de produtos. **Nenhum preço e nenhuma lista de SKUs.**
- **Segredos** (URL e token do registro; App-Key e User-Token do Runrun.it) ficam em `QSettings("SIC","SIC_Suite")`, nunca no repositório.
- ⚠️ O `README.md` (`:46-65`, `:69-74`, `:93-115`) afirma hoje "Não persiste dados na nuvem", "Não se conecta a servidores internos", "A única URL externa é `api.github.com`" e "Nenhuma outra conexão de rede é feita". **Essas afirmações deixam de valer** e devem ser reescritas. A tabela de firewall precisa acrescentar `script.google.com` e `script.googleusercontent.com` (registro) e `runrun.it` (Etapa 4). Aproveitar para corrigir o que **já está defasado**: o webhook do Google Chat (`chat.googleapis.com`) nunca entrou na lista.
- Como o registro e o Runrun.it são **opt-in e desligados por padrão**, a promessa de que "sem auto-update o SIC não faz conexão de rede" passa a ter chaves independentes, todas documentadas.

---

## 8. Critérios de Aceite

| # | Critério |
|---|---|
| CA-01 | Cada segmentada gerada resulta em um registro na planilha com os campos do formato da Etapa 1 |
| CA-02 | Registro desligado, sem URL, token inválido ou rede indisponível → o XML é gerado e salvo normalmente, com aviso discreto |
| CA-03 | Sem rede, o painel de configuração e o reconhecimento usam o cache local, indicando o horário da última sincronização |
| CA-04 | Reimportar uma aba conhecida exibe o banner com o vínculo correto; "Ignorar" mantém o campo de ID livre; **nada é preenchido sem clique** |
| CA-05 | Vínculo `sheet_only`, `ambiguous`, expirado ou antigo → banner vermelho |
| CA-06 | Digitar só o número da tarefa monta `NAT-RR{id}` ou `AVN-RR{id}` conforme a marca; loja CB permanece manual |
| CA-07 | Duas máquinas registrando quase ao mesmo tempo → nenhum registro perdido |
| CA-08 | O fluxo atual (ID digitado à mão) funciona idêntico, com e sem registro configurado |
| CA-09 | Número válido → título da tarefa exibido antes de gerar o XML |
| CA-10 | Número inexistente → aviso claro, campo continua utilizável |
| CA-11 | Integração Runrun.it desligada, sem credencial ou indisponível → a tela se comporta exatamente como hoje |
| CA-12 | Título do Runrun.it divergente do registro → alerta vermelho com confirmação obrigatória |
| CA-13 | Tarefa encerrada no Runrun.it → aviso exibido |
| CA-14 | Nenhuma consulta ao Runrun.it é disparada por tecla digitada |
| CA-15 | HTTP 429 → mensagem ao usuário e parada, sem repetição automática |
| CA-16 | Nenhuma requisição de escrita é emitida contra a API do Runrun.it em nenhum fluxo |

---

## 9. Fora de Escopo (Nesta Fase)

- **Painel de Gestão e botão "Encerrar"** (Etapas 5 e 6) — futuras.
- **Escrever no Runrun.it** (criar tarefa, comentar, alterar status) e listar, pesquisar ou sugerir tarefas enquanto se digita.
- Sincronizar datas da campanha a partir da tarefa; usar o Runrun.it como fonte do registro (a planilha continua sendo).
- ID automático para a loja Minha Loja (CB).
- **Tornar o repositório privado sem quebrar a atualização automática** — solicitação própria.
- Corrigir o caminho do `history.db` (`history_engine.py:6,12`), que dentro do executável aponta para uma pasta temporária — o histórico provavelmente se perde hoje no aplicativo instalado. Merece BRD próprio.
- Migrar de um token compartilhado para autenticação por usuário — só se a política de segurança da Natura exigir.

---

## 10. Pendências e Validações Bloqueantes

**Antes da Etapa 1**
1. **TI:** confirmar que a automação da planilha pode ser publicada com acesso "Qualquer pessoa" (política do Workspace) e liberar `script.google.com` e `script.googleusercontent.com` no firewall.
2. **Conta de equipe** (não pessoal) definida como dona da planilha e da automação.

**Antes da Etapa 3**
3. **Salesforce (ambiente de teste):** reimportar o mesmo `pricebook-id` **substitui** a lista inteira ou apenas **mescla**? Se mesclar, um SKU que saiu da planilha continua com o preço segmentado antigo no site. O aviso de queda de `sku_count` mitiga, mas não elimina.

**Antes da Etapa 4**
4. **Confirmar se `/tasks/:id` aceita o número visível da tarefa** ou um identificador interno distinto. A documentação oficial não pôde ser verificada por leitura automatizada. Se for identificador interno, a integração passa a exigir um endpoint de busca, alterando a conta de chamadas e o desenho da tela. É um teste de dez minutos com um token real.
5. Confirmar os nomes exatos dos campos de **título** e **situação** na resposta da API.
6. Confirmar com quem administra a conta do Runrun.it que o consumo do SIC **não conflita** com outras integrações que usam a mesma App-Key.

**Antes da Etapa 6**
7. **Salesforce:** importar um pricebook com `online-to` no passado realmente derruba o preço no site? O XML precisa levar os SKUs junto?
