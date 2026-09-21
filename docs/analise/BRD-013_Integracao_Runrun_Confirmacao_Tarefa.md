# Análise de Negócio — Integração com a API do Runrun.it: confirmação da tarefa na origem

**Documento:** BRD-013
**Autor:** Marcos (Analista de Negócios Jr)
**Data:** 21-09-2026
**Status:** Rascunho para análise — **nenhuma linha de código autorizada**
**Branch:** A definir (este documento sobe em `docs/brd-013-integracao-runrun`)
**Pré-requisito:** BRD-012 (Registry de Segmentadas), Fase 2 — o campo "Nº da tarefa Runrun.it" só passa a existir lá
**Numeração:** o BRD-012 fica reservado ao Registry de Segmentadas, que é anterior a este na ordem de implementação

---

## 1. Sumário Executivo

Hoje o operador digita o número da tarefa do Runrun.it às cegas: nada no SIC confirma que "1111" é mesmo a campanha que ele tem em mãos. O BRD-012 reduz parte do risco ao lembrar vínculos já usados, mas não cobre o **primeiro cadastro** de uma lista nem detecta um número simplesmente digitado errado.

Esta integração consulta a tarefa na origem e exibe o título antes de o XML ser gerado. O efeito prático é transformar um erro de digitação — que hoje só apareceria depois, como preço errado na loja — em uma conferência de dois segundos na tela.

**Decisões de escopo tomadas com o usuário nesta análise:**
- **Somente leitura.** O SIC não cria tarefa, não comenta e não altera status.
- **Digitar o número e conferir.** Sem lista de tarefas e sem busca enquanto digita.
- **A App-Key já existe** na conta da Natura e o usuário tem acesso a ela.

---

## 2. Situação Atual (AS-IS)

`src/ui/pages/view_exportador_segmentadas.py` recebe o `pricebook_id` como texto livre. As únicas validações, em `_run_seg_generate` (linhas 601-620), são: campo não vazio, sem caractere de espaço, e não pertencente a `RESERVED_PRICEBOOK_IDS`. Nenhuma consulta externa confirma que o número corresponde à campanha pretendida.

O `HistoryEngine` registra apenas texto livre após a geração (`:694-698`), sem o `pricebook_id`. Mesmo após o BRD-012, o campo `campaign_name` do registry seria preenchido manualmente.

---

## 3. Situação Desejada (TO-BE)

Ao sair do campo "Nº da tarefa Runrun.it" — por perda de foco ou Enter, **nunca a cada tecla digitada** — o SIC consulta a tarefa e exibe o título ao lado do ID montado:

```
1111  →  NAT-RR1111  ·  "Favoritos RR18/21"
```

- Tarefa encerrada no Runrun.it → aviso visível (gerar pricebook para tarefa encerrada é sinal de engano).
- Número inexistente → aviso claro, **sem travar o campo** (o operador pode seguir manualmente).
- Integração desligada, sem credencial, ou Runrun.it indisponível → a tela funciona exatamente como hoje.

O título retornado passa a alimentar o campo `campaign_name` do registry (BRD-012), hoje digitado à mão.

---

## 4. Regra de Negócio — a conferência cruzada

Com esta integração passam a existir **três fontes** de informação sobre a mesma lista:

| Fonte | O que afirma |
|---|---|
| Nome da aba na planilha | "esta lista se chama LISTA_48" |
| Registry (BRD-012) | "a LISTA_48 foi vinculada à tarefa 1111, campanha *Favoritos RR18/21*" |
| **Runrun.it** | "a tarefa 1111 é, de fato, *«…»*" |

Quando o registry e o Runrun.it **divergem** — o registry guarda "Favoritos RR18/21" para a tarefa 1111 mas o Runrun.it responde outro título — isso indica registro desatualizado ou aba reaproveitada apontando para o vínculo errado. Nesse caso o SIC **destaca a divergência em vermelho e exige confirmação explícita**, no mesmo padrão de segurança já definido no BRD-012 para nomes de aba reaproveitados entre ciclos.

Esta é a principal contribuição do BRD-013: ele não só confirma o número digitado, como **reforça a trava de segurança do BRD-012** com uma fonte independente.

---

## 5. Proteção da App-Key (requisito, não otimização)

A documentação do Runrun.it estabelece **100 requisições por minuto**, respondendo HTTP 429 ao estourar, e adverte que **uso abusivo leva à revogação da App-Key**. Como essa chave pertence à conta da Natura e não ao SIC, um defeito no aplicativo — laço de repetição, consulta disparada a cada tecla — poderia derrubar integrações de **outras áreas**. Por isso as regras abaixo são requisito de aceite:

1. Consulta apenas por ação explícita (saída de foco, Enter ou botão). **Nunca por tecla digitada.**
2. Cache em memória por sessão: a mesma tarefa não é consultada duas vezes.
3. O `campaign_name` já gravado no registry é exibido de imediato, servindo de cache entre sessões.
4. **Sem repetição automática** em caso de 429: o SIC informa e para.
5. Intervalo mínimo entre consultas consecutivas.
6. Chave de liga/desliga em Configurações, independente das demais integrações.

Volume esperado: **unidades de chamadas por sessão**, contra um teto de 100 por minuto. A folga é grande — desde que não haja defeito.

---

## 6. Credenciais

Autenticação por cabeçalhos `App-Key`, `User-Token` e `Content-Type: application/json`, sobre a base `https://runrun.it/api/v1.0`.

- A **App-Key** é da conta da empresa (Configurações → Integrações → App).
- O **User-Token é pessoal**, obtido no perfil de cada pessoa. Cada uma das 3 pessoas cadastra o seu.

⚠️ **Registro de risco:** o User-Token dá acesso à conta inteira daquela pessoa no Runrun.it, não apenas à leitura de uma tarefa. Consequências para o desenho: campo mascarado na tela; armazenamento em `QSettings("SIC","SIC_Suite")` como o `gchat_webhook` já faz (`view_settings.py:104-109`), **nunca no repositório**; e instrução na interface de como revogar o token pelo próprio perfil.

---

## 7. Análise de Impacto

| Arquivo | Mudança | Risco |
|---|---|---|
| `src/core/runrun_client.py` *(novo)* | `RunrunClient(app_key, user_token, timeout=5)` e `get_task(numero) -> RunrunTask \| None`; falhas viram `RunrunUnavailable`. Sem Qt, apenas `requests` (já em `pyproject.toml:15`) | Baixo — código novo e isolado |
| `src/ui/pages/view_exportador_segmentadas.py` | Consulta em worker (padrão de `worker_segmentado.py:13-17`) ao sair do campo; rótulo exibindo o título. Validações 601-620 **intactas** | Médio — mexe na tela do fluxo crítico; precisa ser estritamente aditivo |
| `src/ui/pages/view_settings.py` | Bloco "Runrun.it": App-Key, User-Token, liga/desliga e botão Testar (modelo `_test_webhook`, `:129`) | Baixo |
| `README.md` e `docs/seguranca/` | Acrescentar `runrun.it` à tabela de firewall; revisar as afirmações sobre conexões de rede | Nulo em runtime |
| `segmentado_engine.py` e demais engines | **Nenhuma alteração** | — |

---

## 8. Critérios de Aceite

| # | Critério |
|---|---|
| CA-01 | Número válido → título da tarefa exibido antes de gerar o XML |
| CA-02 | Número inexistente → aviso claro, campo continua utilizável |
| CA-03 | Integração desligada, sem credencial ou Runrun.it fora do ar → a tela se comporta exatamente como hoje |
| CA-04 | Título divergente do registrado no registry → alerta vermelho com confirmação obrigatória |
| CA-05 | Tarefa encerrada no Runrun.it → aviso exibido |
| CA-06 | Nenhuma consulta disparada por tecla digitada |
| CA-07 | HTTP 429 → mensagem ao usuário e parada, sem repetição automática |
| CA-08 | Nenhuma requisição de escrita é emitida contra a API em nenhum fluxo |

---

## 9. Fora de Escopo

- Criar tarefa, comentar, alterar status ou **qualquer escrita** no Runrun.it.
- Listar ou pesquisar tarefas; sugestão enquanto o usuário digita.
- Sincronizar datas da campanha a partir da tarefa.
- Usar o Runrun.it como fonte do registry — a planilha (BRD-012) continua sendo a fonte.

---

## 10. Pendências Bloqueantes (resolver antes de qualquer código)

1. **Confirmar se `/tasks/:id` aceita o número visível da tarefa** ou um identificador interno distinto. A documentação oficial não pôde ser verificada por leitura automatizada. Se for identificador interno, a integração passa a exigir um endpoint de busca, alterando a conta de chamadas e o desenho da tela. Teste de dez minutos com um token real.
2. Confirmar os nomes exatos dos campos de **título** e **situação** na resposta da API.
3. Confirmar com quem administra a conta que o consumo do SIC **não conflita** com outras integrações que usam a mesma App-Key.
