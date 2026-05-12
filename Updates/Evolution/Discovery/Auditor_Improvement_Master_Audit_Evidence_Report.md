# Melhoria no Módulo Auditor: Relatório de Evidências de Auditoria (Master Report)

## 1. Contexto
Para fins de governança e conformidade com auditorias internas e externas, o Módulo Auditor deve evoluir de um sistema focado apenas na detecção de erros para um sistema que fornece **evidências de conformidade**. Atualmente, o relatório de exportação foca apenas em divergências, omitindo os dados comparativos dos itens que foram validados com sucesso.

## 2. Objetivo
Implementar um "Arquivão de Auditoria" (Master Success Report) que consolide todos os dados validados, comparando lado a lado as informações extraídas da **Grade de Ativação (Excel)** e do **Salesforce (XML)**, mesmo quando os valores estão corretos.

## 3. Requisitos do Relatório

O novo relatório deve conter uma aba mestre denominada `EVIDENCIAS_AUDITORIA` com a seguinte estrutura de colunas:

| Coluna | Descrição |
| :--- | :--- |
| **SKU** | Identificador único do produto (NATBRA- / AVNBRA-) |
| **MARCA** | Natura ou Avon |
| **FONTE** | Origem do dado (Pricebook XML ou Catálogo XML) |
| **ATRIBUTO** | Nome do campo validado (Preço DE, Preço POR, Searchable, etc.) |
| **VALOR_EXCEL** | Valor extraído da Grade de Ativação |
| **VALOR_SALESFORCE** | Valor extraído do XML do Salesforce |
| **STATUS** | Indicação visual de conformidade (ex: ✅ OK) |

## 4. Escopo da Validação (Comparativo Lado a Lado)

Devem ser incluídos no relatório todos os atributos cruzados durante a auditoria:

1.  **Preços (Double-Blind):**
    *   Preço **DE**: Valor na coluna "DE" do Excel vs Valor no Pricebook "Lista" do SF.
    *   Preço **POR**: Valor na coluna "POR" do Excel vs Valor no Pricebook "Promocional" do SF.
2.  **Visibilidade:**
    *   **Searchable Flag**: Coluna "VISIBLE" (SIM/NÃO) do Excel vs atributo `searchable-flag` (true/false) do SF.
3.  **Categorização e Listas:**
    *   Presença em abas de lista (ex: LISTA_01) vs Atribuição em categorias equivalentes no XML.

## 5. Especificações Técnicas Sugeridas

### 5.1 Motor de Auditoria (`AuditorEngine`)
- Criar uma nova estrutura de dados `success_log` no objeto `AuditResult`.
- Alterar o motor para que, ao realizar um check bem-sucedido, os valores comparados sejam registrados nesta lista.

### 5.2 Interface do Usuário (UI)
- Adicionar um checkbox ou botão secundário na tela de resultados: **"Gerar Arquivo de Evidências (Full)"**.
- Devido ao volume de dados (pode gerar milhares de linhas), a exportação deste relatório completo deve ser sob demanda para não impactar a performance do uso diário.

## 6. Valor para o Negócio
- **Transparência Total:** Prova documental de que 100% da base foi conferida.
- **Rastreabilidade:** Histórico de auditoria pronto para ser apresentado a auditores, garantindo a integridade financeira das campanhas.
