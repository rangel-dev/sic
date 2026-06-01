# 📐 ESPECIFICAÇÃO DE MELHORIA: SINCRONIA ESTRITA DE CATÁLOGO (CHECK #13)
**De:** Edgar Santos (Arquiteto de Regras de Negócio)  
**Para:** Marcos Rangel (Desenvolvedor Core)  
**Assunto:** Homologação do Check #13 (`online_excess`) & Ajuste de Bug (Produtos Pais / Variação Base)

---

## 1. Contexto e Objetivo
Atualmente, o Check #1 (**Produto Offline**) funciona de forma unidirecional: ele garante que tudo o que a área de Pricing planejou vender (na Grade de Ativação do Excel) esteja ativo (`online-flag=true`) no Salesforce.

Porém, para garantir a governança total e a segurança jurídica/comercial, o Módulo Auditor foi expandido com o **Check #13 — Sincronia Estrita de Catálogo** (código de erro: `online_excess`). Este check opera na direção inversa: garante que o site **não** tenha produtos ativos que estejam fora da Grade de Ativação comercial atual (o chamado "lixo de catálogo" de campanhas passadas).

---

## 2. A Regra de Negócio Original (Check #13)

### 2.1 Detecção de Excesso de Oferta (Invasão de Catálogo)
* **Cenário:** O SKU possui a flag `online-flag="true"` no Salesforce XML, mas **não está presente** em nenhuma das planilhas de Grade de Ativação (Excel) carregadas.
* **Ação:** O sistema deve gerar uma divergência com o código `online_excess`.
* **Mensagem na UI:** `Divergência: Produto ativo no Salesforce, mas ausente na Grade de Ativação (Deveria estar Offline).`

### 2.2 Exceções Iniciais Cadastradas
Para evitar falsos positivos ("ruído" no relatório), o sistema deve ignorar por padrão:
* **SKUs Técnicos:** Itens de infraestrutura ou serviços que não possuem nomes amigáveis para vitrine (geralmente identificados por nomes em CAIXA ALTA).

---

## 3. O Bug Identificado em Campo (Falso Positivo em Maquiagem)
Durante os testes de homologação com dados reais de maquiagens, o Check #13 disparou uma grande quantidade de alertas indevidos (falsos positivos) para os **Produtos Pais (Mestre/Variation Base)**.

* **O Problema:** Na categoria de maquiagens, os produtos são estruturados como "Pai e Filho" (Variation Group). O Produto Pai (o contêiner do batom ou base, por exemplo) **precisa estar marcado como online no Salesforce** para que suas variações de cores (produtos filhos) fiquem ativas e visíveis no site.
* **A Dificuldade:** No entanto, o departamento de Pricing **nunca coloca os produtos pais na planilha de Grade de Ativação** (apenas os SKUs dos filhos que de fato possuem preço e estoque ativo são inseridos). 
* **O Resultado do Bug:** O Auditor, ao notar o Produto Pai ativo no XML e ausente no Excel, gerava indevidamente o erro `online_excess`.

---

## 4. O Ajuste Solicitado (A Solução)

A regra deve ser blindada para desconsiderar do check qualquer produto que possua a marcação ou estrutura de **Variation Base Product** (Produto Mestre/Pai).

> [!IMPORTANT]
> **Critério de Exclusão Corrigido:**
> Se o produto for uma variação base/mestre, o Check #13 **nunca** deve acusar erro, mesmo que ele esteja ativo no Salesforce e ausente na Grade de Ativação do Excel.

---

## 5. Especificações Técnicas para o Desenvolvedor (Rangel)

### 5.1 Onde Ajustar a Lógica (`parity_rules_v11.py`)
No arquivo de regras de paridade (`src/core/auditor/parity_rules_v11.py`), o Rangel deve garantir que o check faça a validação utilizando a tabela de rastreamento de variações base:

* **Pseudocódigo de Ajuste:**
  ```python
  # ── Check #13: PRODUTO ONLINE FORA DA GRADE ──────────────────
  if not is_offline and not is_on_grade:
      # Verificação estrita: ignora SKUs técnicos E produtos que são variação base
      if not technical_skus.get(sku) and not variation_bases.get(sku):
          errors["online_excess"].append({
              **row_base, 
              "detail": "PRODUTO ONLINE FORA DA GRADE (Deveria estar Offline)"
          })
          dump_stats("online_excess", brand)
      continue
  ```

### 5.2 Mapeamento da Variação Base no Catálogo XML (`auditor_engine.py`)
Para que o código acima funcione, a lista `variation_bases` deve ser alimentada de forma exaustiva durante o parse do XML de catálogo. O motor deve marcar o SKU como `True` se detectar qualquer uma destas marcações nativas do Salesforce:
* O atributo `variation-base-product="true"` ou `is-variation-base="true"` na tag `<product>`.
* A presença do elemento filho `<variants>` contendo nós `<variant>`.
* A propriedade `product-type` ou tipo contendo a palavra `"variation"`.

### 5.3 Mensageria do Erro
* **Código do Erro:** `online_excess`
* **Título na UI:** `Produto Online Fora da Grade`
* **Grupo de Criticidade:** `Invasão de Catálogo (Risco Operacional)`
* **Aba de Destino na Exportação:** `online_excess` (será gerada automaticamente)

---

## 6. Valor de Negócio do Ajuste
* **Zero Falso Positivo:** O analista de Pricing focará apenas nos SKUs reais de venda que foram esquecidos ativos no site, sem poluir a visão com produtos estruturais de TI.
* **Governança Limpa:** Manutenção da conformidade e alinhamento do catálogo entre comercial e TI com 100% de precisão.
