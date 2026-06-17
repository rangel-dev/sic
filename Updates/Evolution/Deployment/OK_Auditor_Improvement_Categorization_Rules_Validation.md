# Melhoria no Módulo Auditor: Validação Universal de Categorization Rules

## 1. Contexto e Comparativo
Atualmente, o Módulo Auditor possui uma validação de sincronia restrita. Abaixo o comparativo de evolução:

| Recurso | Situação Atual (V11.6) | Situação Futura (Proposta) |
| :--- | :--- | :--- |
| **Escopo de Catálogo** | Apenas catálogo "Minha Loja" (cbbrazil) | **Todos** (Natura, Avon e Minha Loja) |
| **Identificação de Regra** | Hardcoded para regras específicas de espelhamento ML | **Dinâmica**: Detecta qualquer `<category-assignment-rule>` |
| **Tipo de Validação** | Valida se SKUs da Marca Mãe estão na ML | Valida qualquer Categoria A que espelha uma Categoria B |

## 2. Requisitos de Negócio (Regras de Auditoria)
O novo motor de auditoria deve seguir o fluxo lógico abaixo para cada categoria encontrada nos arquivos XML de catálogo:

### 2.1 Identificação de Regras
- **Regra:** O sistema deve varrer todas as categorias (`<category>`) e identificar a presença do nó `<category-assignment-rule>`.
- **Condição:** Se uma categoria **não possuir** regras cadastradas, ela deve ser ignorada por este check (considerada uma categoria de atribuição manual).

### 2.2 Filtragem por Tipo de Vínculo
- **Regra:** Dentro das regras encontradas, o sistema deve filtrar apenas aquelas que utilizam um vínculo direto com outra categoria ID (`category-id`).
- **Condição:** Se a regra for baseada em atributos de produto (ex: marca, preço, cor), ela deve ser ignorada. O foco desta melhoria é a **integridade do espelhamento (Mirroring)**.

### 2.3 Validação de Integridade (Match de SKUs)
- **Regra:** Ao identificar um vínculo entre uma **Categoria A (Filha/Espelho)** e uma **Categoria B (Mãe/Origem)**, o sistema deve extrair a lista de SKUs de ambas.
- **Validação:** O conjunto de produtos da Categoria A deve ser **exatamente igual** ao conjunto de produtos da Categoria B.
- **Falha:** Qualquer divergência (SKU sobrando ou faltando em um dos lados) deve gerar um alerta de erro de sincronia.

## 3. Especificações Técnicas
### 3.1 Mapeamento XML (Salesforce Schema)
- **Tag Pai:** `category` (atributo `category-id`)
- **Tag de Regra:** `category-assignment-rule`
- **Tag de Condição:** `category-condition` (atributo `category-id` para identificar a categoria de origem).

### 3.2 Mensageria de Erro
- **Código Sugerido:** `sync_rule`
- **Título na UI:** Falha de Categorização Dinâmica
- **Mensagem Detalhada:** `Divergência detectada: A categoria [ID_FILHA] não reflete fielmente a origem [ID_MAE].`


## 4. Impacto Esperado
- Eliminação de "Gaps" de vitrine onde produtos entram na categoria principal mas não aparecem nas categorias espelhadas (ex: Categorias de Promoção ou Vitrines Temáticas).
- Identificação rápida de falhas nos Jobs de atualização do Salesforce Business Manager.
