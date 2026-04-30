# Correção: ID de Categoria Proibida (Avon) no Módulo Auditor

## 1. Contexto
A trava de **Margem de Segurança (Check #4)** do Módulo Auditor depende de uma lista de categorias pré-definidas que são consideradas sensíveis a empilhamento de descontos. Foi reportado que o identificador de categoria para a marca Avon mudou ou estava incorreto na implementação atual.

## 2. Diagnóstico
No arquivo `auditor_engine.py`, a marca Avon está vinculada ao ID `desconto-progressivo`. Contudo, o identificador correto utilizado no catálogo do Salesforce para esta dinâmica comercial é `promocoes-desconto-progressivo`.

## 3. Requisitos de Correção

### 3.1 Atualização de Dicionário
- **Arquivo:** `src/core/auditor_engine.py`
- **Variável:** `PROHIBITED_CATEGORIES`
- **Alteração:**
    - De: `"Avon": {"desconto-progressivo", "lista-01"}`
    - Para: `"Avon": {"promocoes-desconto-progressivo", "lista-01"}`

## 4. Impacto Esperado
- Restauração da acurácia do check de **Conflito de Margem** para a marca Avon.
- Identificação correta de SKUs que possuem preço promocional ativo enquanto estão inseridos na categoria de desconto progressivo oficial da marca.

## 5. Próximos Passos
- Após a correção no código, validar com um XML de catálogo da Avon que contenha produtos na categoria `promocoes-desconto-progressivo`.
