# Documento de Especificação Técnica
## Ajuste Fino de Escopo Dinâmico — Motor de Auditoria (`AuditorEngine`)

### 1. Objetivo do Documento
Este documento serve como instrução detalhada de desenvolvimento para o programador (e ferramentas de IA/Cloud) aplicar uma alteração cirúrgica no componente de validação de catálogo. O objetivo é eliminar falsos positivos de "Excesso Online" (Invasão de Vitrine) quando a grade de uma das marcas não for incluída intencionalmente na execução (Excel).

---

### 2. Diretriz de Impacto Mínimo (Premissa Crucial)
* **NÃO ALTERAR** nenhuma outra regra de negócio existente.
* As validações de Preço (DE/POR), Margem Proibida, Travas de Pré-execução, Erros Lógicos e Cross-Brand na leitura da grade devem permanecer exatamente como estão hoje.
* O foco é **exclusivamente** na regra de **Excesso Online** (Validação Fluxo: XML ➡️ Grade Excel).
* **Importante:** Não existe o conceito de "grade híbrida". A operação utiliza arquivos de grade separados e independentes para Natura e Avon.

---

### 3. O Problema Atual (Falso Positivo)
A regra de "Excesso Online" varre o XML do Salesforce procurando produtos ativos que *não* constam nas Grades Excel enviadas. 
* Quando o analista opta por auditar apenas a marca **Natura** (subindo apenas a grade da Natura), o sistema lê o XML da **Avon**, identifica que os produtos ativos da Avon não estão na Grade e gera milhares de alertas de erro incorretos. 
* O sistema deve entender que a ausência do arquivo de grade de uma marca específica é uma escolha operacional de escopo para aquela execução, e não um erro de vitrine.

---

### 4. Solução Proposta: Identificação Dinâmica de Escopo

Antes de iniciar a varredura do "Excesso Online", o sistema passará a inferir quais marcas estão ativas na auditoria do dia olhando para as chaves (SKUs) carregadas a partir dos arquivos Excel.

#### Passo 4.1: Mapeamento de Presença (Filtro de Atividade)
Após o carregamento dos Excels (quando o dicionário `excel_prices` ou similar já estiver populado), crie duas variáveis booleanas de controle:
* `has_natura_in_grid` (Padrão: `False`)
* `has_avon_in_grid` (Padrão: `False`)

**Lógica de Ativação:**
* Se houver ao menos um SKU carregado contendo o prefixo da Natura (`NATBRA-`), mude `has_natura_in_grid = True`.
* Se houver ao menos um SKU carregado contendo o prefixo da Avon (`AVNBRA-`), mude `has_avon_in_grid = True`.

#### Passo 4.2: Intervenção na Regra de "Excesso Online"
No loop onde o `AuditorEngine` processa os produtos vindos dos XMLs (Salesforce) para verificar se estão ausentes, adicione uma **condição de escape (skip)** baseada no prefixo do SKU do XML:

```python
# Pseudo-código de orientação para o Desenvolvedor / IA

para cada produto no xml_salesforce:
    se produto.status == "online/ativo":
        sku_xml = produto.sku
        
        # --- INÍCIO DO AJUSTE FINO DE ESCOPO ---
        
        # Se o produto do XML é AVON, mas o arquivo de grade da AVON não foi carregado, IGNORE o check de excesso
        se sku_xml.comeca_com("AVNBRA-") e nao has_avon_in_grid:
            continuar  # Dá um skip silencioso para o próximo produto
            
        # Se o produto do XML é NATURA, mas o arquivo de grade da NATURA não foi carregado, IGNORE o check de excesso
        se sku_xml.comeca_com("NATBRA-") e nao has_natura_in_grid:
            continuar  # Dá um skip silencioso para o próximo produto
            
        # --- FIM DO AJUSTE FINO DE ESCOPO ---
        
        # Mantém a lógica original intocada abaixo
        se sku_xml nao esta em nenhuma grade_excel:
            registrar_erro("Excesso Online: Produto está online no SF, mas não consta na Grade")