# Análise de Negócio — Cupons: Limpeza de Campanhas (campanhas, promoções, cupons e customer groups vencidos ou órfãos)

**Documento:** BRD-015
**Autor:** Marcos (Analista de Negócios Jr)
**Data:** 20-10-2026 (atualizado no mesmo dia com o teste nos exports reais — seção 5.5 e pendências T1, T2 e T5)
**Status:** Rascunho para análise — **nenhuma linha de código autorizada**
**Branch:** `feature/cupons-limpeza-campanhas`
**Origem:** Pacote do gestor gerado por IA (`sanitizador_sfcc.py`, `analisador_sfcc.py` e guia de integração), revisado e formalizado neste BRD
**Pré-requisitos:** nenhum. Módulo novo; não altera nenhum motor existente.

---

## 1. Sumário Executivo

Com o tempo, o Salesforce Commerce Cloud (SFCC) acumula campanhas vencidas, promoções sem campanha, cupons esquecidos e customer groups criados para uma única ação. Hoje a limpeza é manual, item a item no Business Manager, e deixa resíduos: cupons ainda habilitados sem campanha, grupos de demandas antigas e o risco de apagar algo compartilhado com uma campanha ativa.

O gestor trouxe um pacote pronto que automatiza essa limpeza a partir de 3 exportações do Business Manager. A base é boa e encaixa no padrão do SIC, mas a análise encontrou **4 problemas** que poderiam apagar dados que ainda estão em uso (seção 5). Este BRD propõe um módulo novo, **Cupons → Limpeza de Campanhas**, que aproveita o pacote com as correções abaixo.

**Decisões tomadas com o usuário nesta análise:**

| Decisão | Escolha |
|---|---|
| Nome do módulo | **Limpeza de Campanhas**, dentro do menu Cupons |
| Customer groups na primeira versão | Só entram na exclusão os **grupos de demanda** (padrão `NAT-RR####` / `AVN-RR####`). Todos os outros aparecem como **"Revisar"** e nunca são apagados |
| Itens sem data (órfãos e campanhas sem data de fim desativadas) | **Carência por observação**: só ficam elegíveis depois de 30 dias nesse estado, contados a partir da primeira vez que o SIC os viu |
| Cupons | **Desativar antes de apagar**: a primeira etapa só desativa (reversível); a exclusão vem depois de 30 dias desativado |
| Execução no SFCC | O SIC **só gera arquivos**. Quem importa no Business Manager é o operador, como em todos os módulos |

---

## 2. Situação Atual (AS-IS)

### 2.1 Fluxo manual

1. O time de marketing abre o Business Manager (Merchant Tools > Online Marketing).
2. Procura as campanhas vencidas e as apaga uma a uma.
3. Raramente volta para limpar as promoções, os cupons e os customer groups ligados a elas.

### 2.2 Problemas

- **Cupons órfãos:** continuam habilitados sem nenhuma campanha, com risco de aplicação indevida.
- **Customer groups residuais:** grupos criados para uma demanda pontual ficam na base indefinidamente.
- **Deleção indevida:** uma promoção ou cupom compartilhado entre campanhas pode ser apagado junto com a campanha vencida.
- **Sem volta:** o que é apagado no Business Manager não tem backup.

---

## 3. O Pacote Recebido

### 3.1 O que ele faz

1. Lê 3 exportações do Business Manager (Merchant Tools > Operations > Import & Export):

   | Arquivo | Namespace SFCC | Conteúdo |
   |---|---|---|
   | Promoções | `.../promotion/2008-01-31` | Campanhas, promoções e os vínculos entre elas (`promotion-campaign-assignment`) |
   | Cupons | `.../coupon/2008-06-17` | Catálogo de cupons (código único e múltiplos códigos) |
   | Customer groups | `.../customergroup/2007-06-30` | Grupos dinâmicos (regra) e estáticos (membros) |

   O **nome do arquivo não é confiável**: nos exports reais recebidos, o arquivo chamado "PROMOTIONS" continha os cupons e o chamado "CUPONS" continha as promoções. Só o namespace identifica o conteúdo (seção 6).

2. Classifica cada item como **para excluir** ou **protegido**, com o motivo.
3. Gera uma planilha de simulação, 3 XMLs de exclusão (`mode="delete"`) e 3 XMLs de rollback com a definição original de tudo o que seria apagado.

### 3.2 O que se aproveita

- **Leitura por streaming** (`iterparse`): arquivos de cupons de 80–300 MB não estouram a memória.
- **Proteção em cascata:** uma promoção, cupom ou grupo só sai se *todas* as campanhas a que pertence saírem.
- **Simulação antes de tudo** e **rollback** dos itens apagados.
- **Proteções fixas:** grupos nativos do SFCC (`Everyone`, `Registered`, `Unregistered`) e grupos de infraestrutura.
- Motor em Python puro, só com `openpyxl`, sem tela nem terminal acoplados, no mesmo padrão motor → worker → tela do SIC.

---

## 4. Regras de Negócio (TO-BE)

Toda regra abaixo já incorpora as correções da seção 5.

### 4.1 Status possíveis

| Status | Significado | Entra no XML de exclusão? |
|---|---|---|
| **Protegido** | Em uso, recente ou protegido por regra | Não |
| **Elegível** | Pode sair com segurança | Sim (cupons: primeiro desativação, ver 4.5) |
| **Aguardando carência** | Sem data, ainda dentro dos 30 dias de observação | Não |
| **Revisar** | O SIC não tem como garantir que é seguro | Não — aparece no relatório para decisão humana |

### 4.2 Campanhas

| Situação | Status |
|---|---|
| Na lista protegida (seção 4.7) | Protegido |
| Vigente, ou com início no futuro | Protegido |
| Vencida há **menos** de 30 dias | Protegido (carência) |
| Vencida há **30 dias ou mais** | Elegível |
| Sem data de fim e habilitada | Protegido (perene) |
| Sem data de fim e **desativada** | Aguardando carência → Elegível após 30 dias observada desativada (4.6) |
| Data de início ou de fim **ilegível** | Revisar |

### 4.3 Promoções

- Protegida se estiver ligada a pelo menos uma campanha protegida, ou se estiver na lista protegida.
- Elegível se todas as campanhas dela forem elegíveis.
- **Sem nenhuma campanha (órfã):** Aguardando carência → Elegível após 30 dias observada órfã (4.6).

### 4.4 Customer groups

1. **Protegido:**
   - grupo nativo do SFCC;
   - grupo de infraestrutura (o ID ou a descrição contém `dont_remove`, `dontremove`, `system`, `notfound`, `donation`);
   - grupo na lista protegida;
   - grupo ligado a qualquer campanha protegida.
2. **Elegível:** ID no padrão de **grupo de demanda** (`NAT-RR` ou `AVN-RR` seguido do número da tarefa) **e** ligado só a campanhas elegíveis.
3. **Aguardando carência:** grupo de demanda sem nenhuma campanha, com menos de 30 dias de observação (4.6).
4. **Revisar:** qualquer outro grupo sem vínculo com campanha protegida. Aparece no relatório com o motivo e **nunca** é apagado pelo SIC.

### 4.5 Cupons — duas etapas

1. **Desativação:** um cupom que ficaria elegível (por cascata ou por carência de órfão) primeiro entra no XML de **desativação**: a definição do cupom copiada do export, só com o `enabled-flag` trocado para `false` e sem o bloco de códigos. É reversível, e códigos e resgates continuam no SFCC (a confirmar em sandbox, pendência T3).
2. **Exclusão:** um cupom só entra no XML de exclusão depois de estar **desativado há 30 dias ou mais**, contados pela observação do SIC (4.6), e se continuar sem vínculo com campanha protegida.
3. Se um cupom desativado voltar a ser usado por uma campanha protegida, ele volta a Protegido e sai da contagem. A reativação é manual no Business Manager, e o relatório avisa.

### 4.6 Carência por observação

O SFCC não exporta a data de criação nem de modificação de promoções, cupons e customer groups. **Confirmado nos exports reais** (pendência T1): nenhum dos 3 arquivos tem esse tipo de data. Sem uma data, a carência de 30 dias não tem de onde partir. Por isso:

- A cada execução, o SIC grava localmente **a primeira data em que viu cada item** sem campanha, ou desativado (campanha sem data de fim; cupom).
- O item só fica elegível depois de **30 dias** nesse mesmo estado. Se o estado mudar (o item ganhou campanha, foi reativado), a contagem zera.
- **Na primeira execução, nada sem data fica elegível.** Essa é a falha segura: um cupom criado ontem para uma campanha que ainda vai ser montada nunca é apagado.
- O registro fica **no computador de quem roda a limpeza**, ao lado do `history.db`, e **fora do git**. Outro computador começa a contagem do zero, o que também é seguro (pendência N5).

### 4.7 Lista protegida

- Itens cujo ID **contém** um dos termos da lista protegida nunca são apagados, seja campanha, promoção, cupom ou grupo. A comparação é por "contém", não por início do ID, e ignora maiúsculas e minúsculas.
- Lista inicial, herdada do pacote: `origem`, `institucional`, `scprdig`, `crm` (pendência N2).
- A lista fica **editável na tela** do módulo, sem precisar de nova versão do SIC.

---

## 5. Problemas Encontrados no Pacote e Solução Adotada

### 5.1 Customer groups apagados em massa

**Problema.** Na amostra recebida, **96 de 125** customer groups seriam apagados, incluindo segmentos de CRM de uso contínuo (churn, recompra, exclusividade do app, personalização de primeira compra). O pacote só enxerga o uso de um grupo *dentro de campanhas*. Se o grupo for usado em outro lugar do SFCC (frete, pagamento, testes A/B, integrações de CRM), ele é apagado do mesmo jeito.

**Solução adotada.** Classificação em quatro status (seção 4.4):
- só os **grupos de demanda** (`NAT-RR####` / `AVN-RR####`), criados para uma ação pontual, podem entrar na exclusão;
- todo o resto que não está protegido vira **Revisar**.

O problema que motivou o pacote, grupos de tarefas antigas esquecidos, continua resolvido, sem o risco de apagar segmentos de CRM.

### 5.2 Itens sem data apagados na hora

**Problema.** Promoções e cupons sem campanha, e campanhas sem data de fim desativadas, eram apagados **imediatamente**, sem os 30 dias de carência que valem para campanhas vencidas. Um cupom criado para uma campanha que ainda vai ser montada, ou uma campanha pausada ontem, seriam apagados.

**Solução adotada.** Carência por observação (seção 4.6): esses itens só ficam elegíveis depois de 30 dias observados no mesmo estado, e a primeira execução nunca apaga nada sem data.

### 5.3 Rollback que pode não restaurar tudo

**Problema.** Reimportar um cupom apagado recria a definição, mas não há garantia de que traga de volta os códigos já distribuídos nem o histórico de resgates. Um cupom de uso único poderia voltar "zerado".

**Confirmado nos exports reais:**
- O export de cupons traz os códigos num bloco separado (`coupon-codes`): **89 cupons de múltiplos códigos, com cerca de 2,57 milhões de códigos**. O rollback do pacote copia só a definição (`coupon`) e **deixa esse bloco de fora**. Reimportar recriaria esses cupons **sem nenhum código**.
- O export de customer groups traz os membros estáticos num bloco separado (`group-assignment`, 5 vínculos de cliente). O rollback do pacote também **deixa esse bloco de fora**.
- O histórico de resgates **não vem no export** (só o limite de resgates, `redemption-limits`). Nenhum rollback consegue restaurar o uso já feito de um cupom.

**Solução adotada.**
1. **Cupons em duas etapas** (seção 4.5): primeiro desativar, que é reversível e preserva códigos e resgates; apagar só depois de 30 dias desativado.
2. **Rollback completo:** o rollback de cupons inclui o bloco `coupon-codes` de cada cupom apagado, e o de customer groups inclui os `group-assignment` de cada grupo apagado.
3. **Conferência automática:** antes de liberar os arquivos, o SIC verifica que cada rollback contém **exatamente** os IDs do XML de exclusão correspondente, nem um a mais nem um a menos, e a mesma quantidade de códigos e de membros que o export original. Se não bater, nada é gerado.
4. **Teste em sandbox:** restaurar pelo rollback num ambiente de teste é critério de aceite antes do primeiro uso em produção (CA-14).
5. A tela informa o que o rollback **não** restaura: o histórico de resgates.

### 5.4 Defeitos no código do pacote

| Defeito | Efeito | Correção |
|---|---|---|
| O rollback de customer groups só é gravado quando há grupo a apagar | Falta um dos 3 arquivos; o operador não sabe se é erro ou ausência | Sempre gerar os 3 rollbacks, mesmo vazios |
| Data sem fuso horário derruba a execução (comparação entre data com e sem fuso) | Erro em vez de resultado | Data sem fuso é tratada como UTC, padrão do SFCC |
| Data ilegível vira "sem data de fim" | Uma campanha **desativada** com data ilegível seria **apagada** como perene | Data ilegível → **Revisar**, nunca exclusão |
| O rollback de cupons não inclui o bloco `coupon-codes` | Cupons de múltiplos códigos voltariam sem nenhum código (ver 5.3) | Incluir o bloco de cada cupom apagado e conferir a quantidade de códigos |
| O rollback de customer groups não inclui os `group-assignment` | Grupos estáticos voltariam sem membros | Incluir os vínculos de cada grupo apagado |
| Na leitura e no rollback de cupons, os códigos lidos nunca são liberados da memória | No export real (88 MB, 2,57 milhões de códigos) o pacote chegou a **783 MB** de memória; num arquivo de 300 MB passaria de 2 GB | Liberar cada elemento assim que for lido; os códigos só são relidos do arquivo na hora de montar o rollback |
| A lista "de prefixos" na verdade compara por "contém" | Comportamento diferente do nome | Documentar e manter "contém", que é o lado mais seguro (protege mais) |

### 5.5 Teste com os exports reais (20-10-2026)

O motor do pacote foi rodado sobre os 3 exports reais da loja Natura, **só em simulação**, sem gerar nenhum arquivo. As mesmas bases foram classificadas pelas regras deste BRD. Os exports ficaram fora do repositório, e só as contagens abaixo foram registradas.

**Base:** 110 campanhas, 132 promoções, 301 cupons e 126 customer groups. Nenhuma campanha estava vencida havia 30 dias ou mais; 27 estavam vencidas havia menos de 30 dias, 25 eram perenes habilitadas e 1 era perene desativada.

| Entidade | Pacote original apagaria | BRD-015, 1ª execução | BRD-015, após 30 dias sem mudança |
|---|---|---|---|
| Campanhas | 1 | 0 (1 aguardando carência) | 1 elegível |
| Promoções | 2 | 0 (1 aguardando carência) | 1 elegível |
| Cupons | **185** | 0 (184 aguardando carência) | 184 entram na **desativação**; exclusão só 30 dias depois |
| Customer groups | **95** | 0 (7 aguardando carência, **88 Revisar**) | 7 elegíveis; 88 continuam em Revisar |

**Leitura:**
- O pacote apagaria 185 cupons e 95 grupos **na primeira execução**, sem carência e sem desativação, e com um rollback que perderia os códigos dos cupons (5.3).
- Pelas regras deste BRD, a primeira execução não apaga nada. Depois da carência, só sai o que ficou 30 dias sem uso, e os cupons passam primeiro pela desativação.
- Dos 126 grupos, só 18 seguem o padrão de demanda. Os 88 em "Revisar" são exatamente os que o pacote apagaria sem conseguir confirmar se estão em uso.
- Desempenho do pacote no arquivo de cupons (88 MB): 10 segundos, com pico de 783 MB de memória (defeito em 5.4).

---

## 6. Fluxo na Tela

1. **Entrada:** o operador escolhe ou arrasta os 3 arquivos. O SIC reconhece cada um pelo **namespace do XML**, não pelo nome do arquivo (nos exports reais, os nomes vieram trocados; ver 3.1), e mostra um checklist do que falta. **Nunca** lê arquivos de Downloads ou de outra pasta por conta própria.
2. **Simulação:** roda sempre primeiro e mostra, por entidade, os totais de Protegido, Elegível, Aguardando carência e Revisar, com o motivo de cada item e a planilha para baixar.
3. **Confirmação:** os XMLs só são gerados depois de uma confirmação explícita, que mostra os totais e a ordem de importação.
4. **Saída:** XMLs de desativação de cupons, de exclusão e de rollback, mais a planilha. Tudo numa pasta escolhida pelo operador.
5. **Ordem de importação**, exibida na tela (a validar em sandbox, pendência T4):
   - **Exclusão:** 1) campanhas e promoções → 2) cupons (desativação/exclusão) → 3) customer groups.
   - **Rollback:** a ordem inversa.
6. **Registro:** cada execução é registrada no Histórico do SIC (data, totais), de forma passiva.

---

## 7. Travas de Segurança

1. **Coerência entre os 3 arquivos.** Se uma parte relevante dos cupons citados pelas campanhas não existir no arquivo de cupons (sinal de arquivos de lojas ou datas diferentes), a execução é **bloqueada**. Sem essa trava, um arquivo de cupons da loja errada faria todos os cupons parecerem órfãos. Limite proposto: 10% (pendência N4). Referência real: nos exports de 20-10-2026, só 1 dos 118 cupons citados (0,8%) não existia no arquivo de cupons.
2. **Freio de volume.** Se a exclusão ou desativação passar de uma porcentagem da base de qualquer entidade, a confirmação exige que o operador digite a quantidade. Limite proposto: 30% (pendência N4). Referência real: a primeira limpeza de cupons depois da carência vai envolver 184 de 301 (61%), então o freio **vai disparar** nessa rodada. Isso é esperado: é a limpeza do acúmulo antigo.
3. **Arquivo do tipo errado ou repetido** (ex.: dois arquivos de cupons) → recusado no checklist de entrada.
4. **Dados reais fora do repositório.** O repositório `rangel-dev/sic` é **público** (BRD-012, seção 3). Exportações reais, planilhas de simulação e o registro de observação nunca entram no git. Os testes automatizados usam XMLs inventados, e este documento não cita IDs reais.

---

## 8. Análise de Impacto

| Arquivo | Mudança | Risco |
|---|---|---|
| `src/core/limpeza_engine.py` *(novo)* | Motor adaptado do `sanitizador_sfcc.py`, com as regras da seção 4 e as correções da seção 5 | Médio — regra nova que gera exclusões; coberto por testes |
| Registro de observação *(novo, local)* | Arquivo ao lado do `history.db`, com o mesmo mecanismo; incluído no `.gitignore` | Baixo |
| `src/workers/worker_limpeza.py` *(novo)* | Executa o motor em segundo plano com barra de progresso, no padrão dos demais workers | Baixo |
| `src/ui/pages/view_cupom_limpeza.py` *(novo)* | Tela da seção 6. Reconhecimento por namespace no mesmo padrão do `src/core/auditor/file_classifier.py` (o classificador atual é específico do Auditor e não é alterado) | Baixo |
| `src/ui/main_window.py` | "Cupons" vira menu com submenu (**Gerador** e **Limpeza de Campanhas**), como o Exportador; nova página no stack | Baixo |
| `tests/test_limpeza_engine.py` *(novo)* | Um teste por regra e por critério de aceite, com XMLs inventados | — |
| `src/core/cupom_engine.py`, `sync_engine.py`, `auditor_engine.py` | **Nenhuma mudança** | Nulo |

---

## 9. Critérios de Aceite

| # | Critério |
|---|---|
| CA-01 | Campanha vencida há 30 dias ou mais → Elegível; vencida há menos de 30 → Protegida |
| CA-02 | Campanha sem data de fim e habilitada → Protegida |
| CA-03 | Campanha sem data de fim e desativada → Aguardando carência na 1ª execução; Elegível só após 30 dias observada desativada |
| CA-04 | Campanha com data ilegível → Revisar, nunca Elegível |
| CA-05 | Promoção, cupom ou grupo ligado a qualquer campanha protegida → Protegido |
| CA-06 | Promoção ou cupom sem campanha → Aguardando carência na 1ª execução; Elegível só após 30 dias observado órfão |
| CA-07 | Item que ganha campanha ou é reativado durante a carência → contagem zera |
| CA-08 | Customer group nativo, de infraestrutura ou da lista protegida → Protegido |
| CA-09 | Customer group de demanda (`NAT-RR####`/`AVN-RR####`) ligado só a campanhas elegíveis → Elegível |
| CA-10 | Customer group que não é de demanda e não está protegido → Revisar; **nunca** aparece no XML de exclusão |
| CA-11 | Cupom elegível pela primeira vez → só entra no XML de **desativação**, nunca direto na exclusão |
| CA-12 | Cupom desativado há 30 dias ou mais e sem vínculo protegido → entra no XML de exclusão |
| CA-13 | Os 3 rollbacks são sempre gerados e contêm exatamente os IDs dos XMLs de exclusão, com o bloco `coupon-codes` de cada cupom e os `group-assignment` de cada grupo; divergência de IDs, de códigos ou de membros → nada é gerado |
| CA-14 | Restauração pelo rollback testada em sandbox antes do primeiro uso em produção |
| CA-15 | Arquivos incoerentes entre si (limite da trava 7.1) → execução bloqueada com mensagem clara |
| CA-16 | Exclusão acima do freio de volume → confirmação reforçada |
| CA-17 | Export de cupons de 88 MB (2,57 milhões de códigos) processado com pico de memória abaixo de 200 MB (o pacote chegou a 783 MB) |
| CA-18 | Nenhum XML é gerado sem a confirmação explícita do operador |
| CA-19 | Arquivos com o nome trocado (ex.: cupons num arquivo chamado "PROMOTIONS") são reconhecidos corretamente pelo namespace |

---

## 10. Pendências

### 10.1 Para validar com o Ed (negócio)

| # | Pendência |
|---|---|
| N1 | O padrão `NAT-RR####` / `AVN-RR####` cobre todos os grupos de demanda? Existe outro padrão de grupo pontual? |
| N2 | O que cada termo da lista protegida inicial (`origem`, `institucional`, `scprdig`, `crm`) protege, e se falta algum |
| N3 | Os 30 dias servem para tudo (campanha vencida, observação, cupom desativado) ou algum prazo deve ser diferente? |
| N4 | Limites das travas: coerência (proposta 10%) e freio de volume (proposta 30%) |
| N5 | Quem roda a limpeza, em qual computador e com que frequência. O registro de observação é local, então o ideal é uma pessoa responsável |
| N6 | Lojas atendidas: Natura e Avon (uma execução por loja)? Minha Loja (CB) também? |

### 10.2 Técnicas

| # | Pendência | Situação |
|---|---|---|
| T1 | O export traz data de criação de promoções, cupons ou grupos? | ✅ **Respondida (20-10-2026):** não. Nenhum dos 3 arquivos tem data de criação ou modificação; a carência por observação (4.6) é necessária |
| T2 | Formato real das datas | ✅ **Respondida (20-10-2026):** todas as datas de início e fim das campanhas vêm em ISO 8601 com milissegundos e fuso UTC explícito (`AAAA-MM-DDTHH:MM:SS.sssZ`). A regra para data sem fuso fica só como proteção |
| T3 | O SFCC aceita o XML de desativação (definição do cupom com `enabled-flag=false`, sem o bloco de códigos) e mantém os códigos existentes? | Aberta — testar em sandbox |
| T4 | Ordem de importação aceita pelo SFCC na exclusão e no rollback (seção 6) | Aberta — testar em sandbox |
| T5 | O export de cupons traz os códigos? | ✅ **Respondida (20-10-2026):** sim, num bloco `coupon-codes` separado (89 cupons, ~2,57 milhões de códigos). O rollback precisa incluir esse bloco (5.3). O histórico de resgates não vem no export |

---

## 11. Fora de Escopo (Nesta Fase)

- Importar ou apagar direto no SFCC por API: o SIC só gera arquivos.
- Apagar customer groups com status **Revisar**, nem mesmo com seleção manual.
- Conferir o uso de customer groups fora das campanhas (frete, pagamento, testes A/B), o que exigiria outras exportações. Candidato a fase 2, junto com a liberação dos grupos "Revisar".
- Os relatórios analíticos do `analisador_sfcc.py` (painel de vigência, promoções habilitadas em campanhas vencidas). O conceito de "cupom fantasma" é aproveitado só como trava de coerência (7.1).
- Agendamento automático da limpeza.
