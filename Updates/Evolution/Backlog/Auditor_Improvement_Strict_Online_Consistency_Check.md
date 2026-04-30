# Melhoria no Módulo Auditor: Auditoria Estrita de Disponibilidade (Online vs Grade)

## 1. Contexto
Atualmente, o Check #1 (**Produto Offline**) valida apenas se os produtos que o Pricing planejou vender (via Grade de Ativação) estão devidamente "Online" no Salesforce. No entanto, o sistema não identifica o cenário inverso: produtos que estão "Online" no site, mas que não constam no planejamento da planilha atual.

## 2. Objetivo
Implementar uma validação de **Sincronia Estrita de Catálogo**, garantindo que o site reflita exatamente e apenas o que consta na Grade de Ativação.

## 3. Requisitos de Negócio (Regra Inversa)

O motor do Auditor deve passar a validar o "Deveria estar Offline":

### 3.1 Detecção de Excesso de Oferta (Invasão de Catálogo)
- **Cenário:** O SKU possui a flag `online-flag="true"` no Salesforce XML, mas **não está presente** em nenhuma das planilhas de Grade de Ativação carregadas.
- **Ação:** O sistema deve gerar uma divergência indicando que o produto está ativo indevidamente.
- **Objetivo:** Limpeza de catálogo e prevenção de vendas de itens de campanhas passadas ou fora de linha.

### 3.2 Exceções Necessárias
Para evitar "ruído" no relatório, o sistema deve ignorar nesta regra:
- **SKUs Técnicos:** Itens que não possuem nomes amigáveis (geralmente identificados por nomes em caixa alta).
- **Variações Base:** Produtos do tipo "Variation Group" que precisam estar online para as variações funcionarem, mas não aparecem na grade.

## 4. Especificações Técnicas

### 4.1 Lógica de Comparação
A lógica interna deve ser expandida no arquivo de regras:
- **Antes:** `if is_offline and is_on_grade: ERROR`
- **Depois (Adicional):** `if not is_offline and not is_on_grade: ERROR`

### 4.2 Mensageria
- **Novo Erro:** `online_excess`
- **Título na UI:** Produto Online Fora da Grade
- **Mensagem Detalhada:** `Divergência: Produto ativo no Salesforce, mas ausente na Grade de Ativação (Deveria estar Offline).`

## 5. Valor para o Negócio
- **Governança de Catálogo:** Garante que o site não tenha "lixo" de campanhas anteriores.
- **Controle de Estoque/Operação:** Evita que produtos sem preço planejado ou sem estratégia comercial continuem disponíveis para compra.
