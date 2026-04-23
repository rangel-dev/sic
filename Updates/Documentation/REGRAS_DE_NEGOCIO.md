# Regras de Negócio - SIC (Sistema de Inteligência Corporativa)

Este documento consolida todas as regras de negócio implementadas nos motores do SIC, servindo como referência técnica para auditoria, manutenção e evolução do sistema.

---

## 1. Módulo Auditor (Quality Assurance)

O motor do Auditor (`auditor_engine.py`) realiza um cruzamento *double-blind* entre a Grade de Ativação (Excel) e os dados do Salesforce (XML).

### 1.1 Regras de Preço
- **Divergência de Preço**: Compara os preços **DE** e **POR** do Excel com o Pricebook XML do SF. Alerta se a diferença for maior que R$ 0,01.
- **Preço Ausente no SF**: Alerta se um SKU presente na Grade de Ativação não possui preço definido no Salesforce.
- **Lógica POR > DE**: Identifica erros onde o preço promocional (POR) está maior que o preço de lista (DE).
- **Falta Preço DE ou POR**: Alerta se o Salesforce possui apenas um dos preços cadastrados para um SKU ativo.

### 1.2 Regras de Margem e Categorias
- **Conflito de Margem**: Verifica se produtos em promoção (`POR < DE`) estão atribuídos a categorias onde descontos são proibidos.
    - **Natura**: `promocao-da-semana`, `LISTA_01`
    - **Avon**: `desconto-progressivo`, `lista-01`
    - **Minha Loja**: `promocao-da-semana`, `desconto-progressivo`
- **Categoria Primária**: Todo produto no catálogo (exceto SKUs técnicos) deve ter pelo menos uma categoria marcada como "Primária" (`primary-flag="true"`).

### 1.3 Regras de Visibilidade e SEO
- **Searchable vs Visible**: Compara a coluna `VISIBLE` do Excel com a flag `searchable-flag` do Salesforce.
- **Produto Offline**: Alerta se um produto está no Excel comercial mas está com `online-flag="false"` no Salesforce.

### 1.4 Regras de Estrutura e Sincronização
- **Bundle Quebrado**: Verifica se Kits/Bundles possuem componentes offline ou sem preço.
- **Cross-Brand (Invasão)**: Identifica produtos de uma marca (ex: Natura) que possuem preço no catálogo de outra marca (ex: Avon).
- **Divergência Minha Loja (ML)**: Valida se o preço no catálogo ML diverge do preço da marca principal.
- **Job de Categorias ML**: Compara se as categorias da Minha Loja estão sincronizadas com as categorias espelho da marca original.

---

## 2. Módulo Gerador (Data Generator)

O Gerador (`gerador_engine.py`) converte dados de Excel para o formato Pricebook XML do Salesforce.

- **Detecção de Marca**: Identifica a marca do arquivo contando a predominância de SKUs `NATBRA-` ou `AVNBRA-`.
- **Modo Delta**: Gera um XML contendo apenas os produtos cujos preços divergiram de um XML base fornecido.
- **Consolidação ML**: Ao gerar preços para Natura ou Avon, o sistema replica automaticamente os preços para os Pricebooks da Minha Loja (ML), garantindo paridade.
- **Normalização de Valores**: Converte formatos brasileiros de moeda (vírgulas, R$, espaços) para o padrão float XML.

---

## 3. Módulo Merchandising Sync (Sync)

O Sync (`sync_engine.py`) gerencia a ativação de vitrines e atributos de produto.

- **Regra dos 10 Minutos**: Valida se os XMLs de catálogo são recentes para evitar sobrescrever dados com versões obsoletas do ambiente.
- **Delta de Atribuição**: Gera XML de `category-assignment` contendo apenas a diferença (adições/remoções) entre o Excel e o estado atual do XML.
- **Gestão de Selos (Badges)**: Sincroniza o atributo `natg_preferencialProductSlot` com base na coluna `SELO` do Excel.

---

## 4. Módulo Menu Validator

Valida a consistência da árvore de categorias entre os sites das marcas e o canal CB (`menu_validator_engine.py`).

- **Missing**: Categoria online na origem (Natura/Avon) mas ausente no CB.
- **Inactive CB**: Categoria online na origem mas offline no CB.
- **Menu Hidden**: Categoria visível no menu da origem mas oculta no menu do CB (`showInMenu`).
