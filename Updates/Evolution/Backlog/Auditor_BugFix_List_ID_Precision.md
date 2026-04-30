# BugFix: Preciso na Identificao de Listas (Sub-listas Decimais)

## 1. Descrio do Problema
O Mdulo Auditor apresentava um comportamento de "truncamento" ao identificar categorias de lista a partir das abas do Excel. Abas com IDs decimais ou identificadores de sub-lista (ex: `LISTA_20.1`, `LISTA_20.2`) eram reduzidas ao nmero inteiro base (`LISTA_20`).

### Impactos Identificados:
- **Mesclagem Indevida:** O Auditor somava os SKUs de diferentes abas (ex: "Lista Principal" + "Lista de Refil") como se fossem uma s.
- **Falsos Positivos:** O sistema gerava erros de "Lista Inexistente no Salesforce" ou "Falta no SF" porque tentava validar o ID truncado contra um XML que possua IDs especficos.
- **Confuso no Dashboard:** O nmero de erros reportados no condizia com a realidade da Grade de Ativao.

## 2. Causa Raiz
A Expresso Regular (Regex) no arquivo `src/core/auditor_engine.py` estava definida para capturar apenas sequncias de dgitos (`\d+`), parando no primeiro caractere no-numrico (como o ponto `.` das sub-listas).

**Regex Antiga:** `r"(?i)lista[-_\s]*0*(\d+)"`

## 3. Soluo Tcnica
A Regex foi atualizada para permitir o caractere de ponto (`.`) dentro do grupo de captura do ID, garantindo que sub-listas sejam tratadas como categorias independentes.

**Nova Regex:** `r"(?i)lista[-_\s]*0*([0-9.]+)"`

### Comparativo de Comportamento:

| Nome da Aba no Excel | ID Detectado (Antigo) | ID Detectado (Novo) | Status |
| :--- | :--- | :--- | :--- |
| `LISTA_20` | `LISTA_20` | `LISTA_20` |  Inalterado |
| `LISTA_20.1_DIA_DAS_MAES` | `LISTA_20` | `LISTA_20.1` |  Corrigido |
| `LISTA_20.2_REFIL` | `LISTA_20` | `LISTA_20.2` |  Corrigido |
| `LISTA_06_EXTRA` | `LISTA_06` | `LISTA_06` |  Inalterado |

## 4. Arquivos Afetados
- `src/core/auditor_engine.py`: Atualizao do mtodo `_parse_excels`.

## 5. Verificao Sugerida
1. Processar o arquivo Excel `CL08_2026_VIRADA_.xlsm`.
2. Validar se o Dashboard agora separa as divergncias da `LISTA_20` das divergncias da `LISTA_20.2`.
3. Confirmar que o erro "Lista Inexistente" sumiu para os casos onde o ID decimal existe no Salesforce.

Commit
