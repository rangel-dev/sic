# Análise de Negócio — Cupons: Limpeza de Campanhas (campanhas, promoções, cupons e customer groups vencidos ou órfãos)

**Documento:** BRD-015
**Autor:** Marcos (Analista de Negócios Jr)
**Data:** 20-10-2026 (atualizado no mesmo dia com o teste nos exports reais — seção 5.5 e pendências T1, T2 e T5)
**Status:** Implementado na branch, com as respostas N1–N6 (seção 13) e a revisão após o teste do Ed (seção 14 — **itens sem vínculo saem já na 1ª rodada; sem desativação de cupons; sem registro local**). **Uso em produção só depois dos testes em sandbox (T4, CA-14)**; N4 aguarda entendimento
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
| Customer groups | *(revisado em 20-10-2026, seção 13)* Seguem as mesmas regras das demais entidades, qualquer que seja o nome. Só ficam protegidos os grupos padrão do SFCC e os que têm DONT_REMOVE no nome |
| Itens sem data (órfãos e campanhas sem data de fim desativadas) | *(revisado em 22-10-2026, seção 14)* **Elegíveis já na 1ª rodada.** A carência por observação foi removida |
| Cupons | *(revisado em 22-10-2026, seção 14)* **Excluídos direto**, sem a etapa de desativação; o rollback traz a definição e os códigos |
| Carência | **Régua ajustável** de 7 a 365 dias, padrão 30 (N3) — vale só para campanhas vencidas |
| Lojas | **Todas as lojas LATAM**: o operador escolhe ou digita a loja (N6) |
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

*(Revisado em 20-10-2026 com as respostas N1 e N2 — seção 13. O padrão do ID não importa.)*

1. **Protegido:**
   - grupo padrão do SFCC (`Everyone`, `Registered`, `Unregistered`);
   - grupo cujo ID ou descrição contém `dont_remove` ou `dontremove`;
   - grupo na lista protegida, se o operador preencher algum termo;
   - grupo ligado a qualquer campanha que fica.
2. **Elegível:** ligado só a campanhas elegíveis; ou sem nenhuma campanha há pelo menos a carência (4.6).
3. **Aguardando carência:** sem nenhuma campanha, ainda dentro da carência de observação.
4. **Revisar:** ligado a uma campanha que não está no arquivo de promoções.

### 4.5 Cupons — duas etapas

> **Substituída pela seção 14 (22-10-2026):** os cupons agora são excluídos direto, sem a etapa de desativação.

1. **Desativação:** um cupom que ficaria elegível (por cascata ou por carência de órfão) primeiro entra no XML de **desativação**: a definição do cupom copiada do export, só com o `enabled-flag` trocado para `false` e sem o bloco de códigos. É reversível, e códigos e resgates continuam no SFCC (a confirmar em sandbox, pendência T3).
2. **Exclusão:** um cupom só entra no XML de exclusão depois de estar **desativado há 30 dias ou mais**, contados pela observação do SIC (4.6), e se continuar sem vínculo com campanha protegida.
3. Se um cupom desativado voltar a ser usado por uma campanha protegida, ele volta a Protegido e sai da contagem. A reativação é manual no Business Manager, e o relatório avisa.

### 4.6 Carência por observação

> **Substituída pela seção 14 (22-10-2026):** o registro de observação foi removido; itens sem vínculo são elegíveis na primeira rodada.

O SFCC não exporta a data de criação nem de modificação de promoções, cupons e customer groups. **Confirmado nos exports reais** (pendência T1): nenhum dos 3 arquivos tem esse tipo de data. Sem uma data, a carência de 30 dias não tem de onde partir. Por isso:

- A cada execução, o SIC grava localmente **a primeira data em que viu cada item** sem campanha, ou desativado (campanha sem data de fim; cupom).
- O item só fica elegível depois de **30 dias** nesse mesmo estado. Se o estado mudar (o item ganhou campanha, foi reativado), a contagem zera.
- **Na primeira execução, nada sem data fica elegível.** Essa é a falha segura: um cupom criado ontem para uma campanha que ainda vai ser montada nunca é apagado.
- O registro fica **no computador de quem roda a limpeza**, ao lado do `history.db`, e **fora do git**. Outro computador começa a contagem do zero, o que também é seguro (pendência N5).

### 4.7 Lista protegida

- Itens cujo ID **contém** um dos termos da lista protegida nunca são apagados, seja campanha, promoção, cupom ou grupo. A comparação é por "contém", não por início do ID, e ignora maiúsculas e minúsculas.
- **A lista começa vazia** (resposta N2: os termos herdados do pacote não precisam de proteção). Ela continua **editável na tela**, como recurso opcional para o operador.

---

## 5. Problemas Encontrados no Pacote e Solução Adotada

### 5.1 Customer groups apagados em massa

**Problema.** Na amostra recebida, **96 de 125** customer groups seriam apagados, incluindo segmentos de CRM de uso contínuo (churn, recompra, exclusividade do app, personalização de primeira compra). O pacote só enxerga o uso de um grupo *dentro de campanhas*. Se o grupo for usado em outro lugar do SFCC (frete, pagamento, testes A/B, integrações de CRM), ele é apagado do mesmo jeito.

**Solução proposta na primeira versão deste BRD:** só os grupos de demanda (`NAT-RR####` / `AVN-RR####`) poderiam ser apagados; os outros iriam para Revisar.

**Decisão do negócio (20-10-2026, N1/N2):** os grupos seguem as mesmas regras das demais entidades, qualquer que seja o nome, protegendo só os grupos padrão do SFCC (e os que têm DONT_REMOVE no nome). O que separa esta versão do pacote:
- a **carência** (a primeira execução não apaga nenhum grupo sem campanha);
- a **cascata** (grupo ligado a campanha que fica nunca sai);
- o **rollback completo** (definição, regra dinâmica e membros estáticos).

**Risco aceito pelo negócio:** se um grupo for usado fora das campanhas (frete, pagamento, teste A/B, integração de CRM), apagá-lo quebra esse uso, e o rollback recria o grupo mas **não** refaz esse vínculo.

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
| Customer groups | **95** | 0 (100 aguardando carência) | 103 elegíveis *(regras revisadas na seção 13; ver nota abaixo)* |

**Leitura:**
- O pacote apagaria 185 cupons e 95 grupos **na primeira execução**, sem carência e sem desativação, e com um rollback que perderia os códigos dos cupons (5.3).
- Pelas regras deste BRD, a primeira execução não apaga nada. Depois da carência, só sai o que ficou 30 dias sem uso, e os cupons passam primeiro pela desativação.
- Customer groups, com as regras revisadas na seção 13: na primeira execução, os 100 grupos sem campanha ficam aguardando carência e nenhum é apagado. A coluna "após 30 dias" usa uma simulação 31 dias à frente, em que as 27 campanhas vencidas recentemente também já passaram da carência; por isso aparecem mais grupos do que os 95 do pacote. Na primeira versão deste BRD, 88 desses grupos iriam para "Revisar".
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
| CA-08 | Customer group padrão do SFCC, com DONT_REMOVE no nome ou na lista protegida → Protegido *(revisado — seção 13)* |
| CA-09 | Customer group ligado só a campanhas elegíveis → Elegível, qualquer que seja o nome *(revisado)* |
| CA-10 | Customer group sem campanha → Aguardando carência; Elegível só depois da carência observada *(revisado)* |
| CA-20 | A régua de carência (7–365 dias) vale para campanha vencida, item sem campanha e cupom desativado |
| CA-21 | Qualquer loja pode ser informada; a carência é contada separadamente por loja |
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

| # | Pendência | Resposta (20-10-2026) |
|---|---|---|
| N1 | O padrão `NAT-RR####` / `AVN-RR####` cobre todos os grupos de demanda? | ✅ Podem existir padrões antigos, mas não faz diferença: valem os parâmetros (vínculo e vencimento), não o nome |
| N2 | O que a lista protegida inicial (termos herdados do pacote) protege? | ✅ Nenhum desses termos precisa de proteção; só os grupos padrão do SFCC, como `Everyone` |
| N3 | Os 30 dias servem para tudo? | ✅ Ter uma régua ajustável para configurar o prazo |
| N4 | Limites das travas: coerência (10%) e freio de volume (30%) | ⏳ Pergunta não ficou clara; os valores propostos seguem até nova orientação (explicação na seção 13) |
| N5 | Quem roda a limpeza e em qual computador? | ✅ Qualquer pessoa com acesso ao SIC, sem responsável fixo |
| N6 | Lojas atendidas | ✅ Todas as lojas LATAM, com os mesmos parâmetros |

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
- Conferir o uso de customer groups fora das campanhas (frete, pagamento, testes A/B), o que exigiria outras exportações. Candidato a fase 2 para reduzir o risco aceito na seção 5.1.
- Registro de observação compartilhado entre computadores (ver seção 13, N5).
- Os relatórios analíticos do `analisador_sfcc.py` (painel de vigência, promoções habilitadas em campanhas vencidas). O conceito de "cupom fantasma" é aproveitado só como trava de coerência (7.1).
- Agendamento automático da limpeza.

---

## 12. Nota de Implementação (20-10-2026)

Código em `src/core/limpeza_engine.py`, `src/workers/worker_limpeza.py` e `src/ui/pages/view_cupom_limpeza.py`, com o menu **Cupons → Gerador / Limpeza de Campanhas** em `src/ui/main_window.py`. Testes em `tests/test_limpeza_engine.py`: 29 testes, todos com XMLs inventados. Nenhum motor existente foi alterado.

**Parâmetros**, todos em constantes no topo do motor: carência padrão de 30 dias (régua na tela, de 7 a 365); coerência 10%; freio de volume 30%; grupos protegidos (padrão do SFCC e DONT_REMOVE). Os valores provisórios da primeira versão foram substituídos pelas respostas da seção 13.

**Decisões tomadas na implementação, além do texto acima:**
- **Loja obrigatória.** O registro de observação é separado por loja. Assim, um mesmo ID em duas lojas não compartilha a contagem.
- **Trava de coerência também para customer groups**, e só bloqueia quando falta **mais de 1** item além dos 10%. Isso evita bloquear bases pequenas por um único item.
- **Campanha "Aguardando carência" também segura a cascata.** As promoções, cupons e grupos dela ficam Protegidos até ela sair.
- **Vínculo com campanha que não está no arquivo → Revisar.** O pacote tratava esse caso como se a campanha fosse excluída.
- **Registro de observação não é gravado** quando a trava de coerência bloqueia, para que arquivos errados não contem carência.
- **Saída:** pasta `LIMPEZA_<LOJA>_<data>_<hora>`, com os arquivos numerados na ordem de importação (`1`, `2a`, `2b`, `3`; rollbacks `ROLLBACK_1` a `ROLLBACK_3`). Os arquivos são montados numa pasta temporária, conferidos e só então liberados; se a conferência falhar, nada aparece na pasta escolhida.
- **Rollback de desativação:** o arquivo de rollback de cupons também traz a definição original dos cupons desativados (com `enabled-flag` original), para reativá-los se preciso.

**Teste com os exports reais (só leitura, saídas fora do repositório):** na 1ª execução, nada é apagado (184 cupons aguardando carência; com as regras da seção 13, 100 grupos aguardando carência). Pico de memória de **79 MB** na simulação (CA-17 atendido; o pacote chegou a 783 MB), entre 12 e 20 segundos. Numa execução simulada 31 dias depois, a geração de 103 grupos, 208 cupons, 28 campanhas e 31 promoções passou na conferência, incluindo o rollback com os códigos de um cupom de múltiplos códigos e as definições dos grupos (pico de 167 MB, cerca de 26 segundos).

---

## 13. Respostas do Negócio e Ajustes (20-10-2026)

As respostas do Ed às pendências N1–N6 (seção 10.1) foram aplicadas no código:

| # | Ajuste |
|---|---|
| N1 + N2 | Customer groups seguem as mesmas regras das demais entidades (cascata + carência), **qualquer que seja o nome**. Ficam protegidos só os grupos padrão do SFCC (`Everyone`, `Registered`, `Unregistered`) e os que têm `DONT_REMOVE`/`DONTREMOVE` no ID ou na descrição. Os termos `system`, `notfound` e `donation` deixaram de proteger. O status **Revisar** ficou só para data ilegível e vínculo com campanha que não está no arquivo. Risco aceito: seção 5.1 |
| N2 | A **lista protegida começa vazia**. Continua editável na tela, como recurso opcional |
| N3 | **Régua de carência** na tela (controle deslizante + campo numérico), de **7 a 365 dias**, padrão 30. Vale para as três carências: campanha vencida, item sem campanha e cupom desativado. O mínimo de 7 dias evita que uma campanha encerrada ontem já entre na exclusão |
| N5 | Qualquer pessoa pode rodar. **O registro de observação continua local** (decisão do usuário). Consequência: a carência dos itens sem data é contada por computador. Se a próxima limpeza for feita em outro computador, esses itens recomeçam a contagem, o que é seguro mas atrasa a limpeza deles. A tela avisa isso ao lado da loja. Registro compartilhado fica fora de escopo (seção 11) |
| N6 | **Todas as lojas LATAM**: a loja é uma lista editável (sugestões Natura Brasil, Avon Brasil e Minha Loja (CB), mais as lojas já usadas), onde dá para digitar qualquer outra, como "Natura Chile". A loja só separa a contagem de carência; acentos, maiúsculas e espaços são ignorados ("Avon Colômbia" = "avon colombia") |

**N4 — explicação para o Ed, ainda sem resposta.** São duas travas de segurança, e os valores atuais continuam até nova orientação:
- **Coerência (10%):** confere se os 3 arquivos são da mesma loja e do mesmo momento. As campanhas citam cupons e grupos; se mais de 10% deles não existir nos outros arquivos, é sinal de que alguém misturou arquivos (por exemplo, os cupons de outra loja), e o SIC **bloqueia** a simulação. Sem essa trava, os cupons da loja certa pareceriam todos "sem campanha". Nos exports reais, só 1 de 118 cupons citados faltava (0,8%).
- **Freio de volume (30%):** se uma rodada for desativar ou excluir mais de 30% de uma base (ex.: 120 de 300 cupons), o SIC pede que o operador **digite a quantidade** antes de gerar os arquivos, para ninguém confirmar uma limpeza grande sem perceber. Não impede nada, só exige atenção. Na primeira limpeza real ele vai disparar, porque é a limpeza do acúmulo antigo.

---

## 14. Revisão Após o Teste do Ed (22-10-2026)

**O que aconteceu.** No teste da versão 1.7.0-alpha, a primeira simulação não trouxe nenhum cupom para excluir: os cupons sem campanha apareceram como "Sem campanha — observado há 0 de 14 dias". Era o comportamento previsto (carência por observação, seção 4.6), mas o Ed entendeu como erro e definiu a regra de negócio: **"se um cupom não tem vínculo com uma campanha, ele deve ser excluído"**.

**Decisões (usuário, 22-10-2026):**

| Tema | Antes | Agora |
|---|---|---|
| Cupom sem campanha | Aguardava a carência observada | **Elegível já na 1ª rodada** |
| Cupom de campanha que sai | Desativado primeiro; excluído depois da carência | **Excluído direto** — arquivo `2_EXCLUIR_CUPONS.xml`; a etapa e o arquivo de desativação deixaram de existir |
| Promoção / customer group sem campanha | Aguardavam a carência observada | **Elegíveis já na 1ª rodada** |
| Campanha sem data de fim desativada | Aguardava a carência observada | **Elegível já na 1ª rodada** |
| Registro de observação local | Arquivo `limpeza_observacoes.db` no computador | **Removido** — o resultado depende só dos 3 arquivos, da data e da régua, e é igual em qualquer computador (resolve a limitação da N5) |
| Régua de carência | Valia para as três carências | Vale **só para campanhas vencidas** |

**Por que excluir direto é aceitável.** Um cupom sem campanha não tem efeito na loja; e o rollback traz a definição completa e os códigos (bloco `coupon-codes`, conferido antes de liberar os arquivos). O que não volta é o histórico de resgates (seção 5.3).

**Risco aceito pelo negócio.** Um cupom, promoção ou grupo criado para uma campanha que ainda vai ser montada é excluído se a limpeza rodar antes de a campanha existir no export. Mitigação: a simulação lista cada item com o motivo "Sem campanha", e o freio de volume pede confirmação reforçada em limpezas grandes.

**Pendência T3 encerrada:** como não há mais XML de desativação, o teste de desativação em sandbox deixou de ser necessário. Continuam T4 (ordem de importação) e CA-14 (restauração pelo rollback).

**Resultado com os exports reais (só leitura):** com carência de 30 dias, a 1ª rodada traz 1 campanha, 2 promoções, **185 cupons** (184 sem campanha + 1 de campanha que sai) e **100 customer groups** para excluir; o freio de volume dispara para cupons (61%) e grupos (79%). A geração passou na conferência, com pico de 167 MB e cerca de 22 segundos. Testes automatizados: 30 no módulo, todos com XMLs inventados.
