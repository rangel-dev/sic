# BugFix: Normalizao Inteligente de IDs de Listas (Smart Padding)

## 1. Contexto da Melhoria
Identificamos que apenas permitir nmeros decimais na Regex no era suficiente, pois havia divergncias na conveno de zeros esquerd entre o Excel (`LISTA_6.1`) e o Salesforce (`LISTA_06.1`).

## 2. Nova Lgica de Inteligncia
O Auditor agora aplica uma **Normalizao Segmentada**. Em vez de tratar o ID como um texto nico, ele processa a parte principal e a sub-lista separadamente para garantir a paridade com o Salesforce.

### O Algoritmo:
1.  **Captura:** Extrai o ncleo numrico da aba (ex: `1.5`, `06.1`).
2.  **Segmentao:** Divide o ID no caractere de ponto (`.`).
3.  **Padding:** Aplica `zfill(2)` **apenas na primeira parte** (ID Principal).
4.  **Reconstituio:** Une as partes novamente para formar o ID Final.

## 3. Exemplos de Sucesso (Casos de Match)

| Nome da Aba (Excel) | ID Bruto | Processamento | ID Final (Auditor) | ID Salesforce |
| :--- | :--- | :--- | :--- | :--- |
| `LISTA_1.5_PROMO` | `1.5` | `1`  `01` | **`LISTA_01.5`** | `LISTA_01.5` |
| `LISTA_01.5_V1` | `01.5` | `01`  `01` | **`LISTA_01.5`** | `LISTA_01.5` |
| `LISTA_6.1_CAMPANHA` | `6.1` | `6`  `06` | **`LISTA_06.1`** | `LISTA_06.1` |
| `LISTA_20.2_REFIL` | `20.2` | `20`  `20` | **`LISTA_20.2`** | `LISTA_20.2` |

## 4. Implementao Tcnica
A mudana foi aplicada no mtodo `_parse_excels` do arquivo `src/core/auditor_engine.py`.

```python
# Trecho da nova lgica
raw_id = m.group(1)
parts = raw_id.split('.')
parts[0] = parts[0].zfill(2) # Normaliza a parte principal
num = ".".join(parts)
```

## 5. Benefcios
- **Resilincia:** O analista pode digitar com ou sem o zero inicial no Excel sem quebrar a auditoria.
- **Preciso:** Garante que sub-listas no sejam mescladas com a lista principal.
