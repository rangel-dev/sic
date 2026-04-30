# Novas Travas de Segurança e Integridade: Módulo Auditor

## 1. Contexto
Para evitar erros de processamento e auditorias baseadas em dados incompletos ou duplicados, serão implementadas novas travas de segurança no momento do upload de arquivos no Módulo Auditor. O sistema passará a recusar lotes de importação que não atendam aos requisitos de unicidade e completude.

## 2. Requisitos de Validação

### 2.1 Upload de Pricebooks (XML)
O sistema deve garantir a presença de toda a estrutura de preços necessária para a auditoria cross-brand.
- **Regra:** É obrigatório que os arquivos contenham os preços **DE** e **POR** para as 3 operações (Natura, Avon e Minha Loja).
- **Ação:** Bloquear o início da auditoria caso falte algum pricebook ou caso algum arquivo não contenha as duas colunas de preço.

### 2.2 Upload de Catálogos (XML)
Prevenção contra arquivos repetidos ou marcas faltantes.
- **Regra de Quantidade:** É obrigatório o upload de exatamente **3 arquivos** de catálogo.
- **Regra de Unicidade:** Cada arquivo deve pertencer a uma marca distinta.
- **Validação:**
    - 1x Catálogo Natura
    - 1x Catálogo Avon
    - 1x Catálogo Minha Loja
- **Cenário de Erro:** Se o usuário subir 2x Natura e 1x Avon, o sistema deve emitir um alerta de "Marca Duplicada" e impedir o prosseguimento.

### 2.3 Upload de Grades de Ativação (Excel - Opcional)
As grades continuam sendo opcionais para o início da auditoria, porém seguem a regra de não-repetição.
- **Regra:** Caso o usuário opte por subir as grades, elas não podem ser da mesma marca.
- **Exemplo:** Se subir 2 arquivos, obrigatoriamente deve ser 1x Natura e 1x Avon.
- **Ação:** Bloquear se houver repetição de marca nas planilhas de grade.

## 3. Mensagens de Erro Sugeridas
- *"Erro de Unicidade: Foram detectados dois arquivos da mesma marca (Natura). Por favor, verifique os catálogos."*
* *"Dados Incompletos: O Pricebook da operação [Marca] não contém a coluna de Preço POR."*
* *"Quantidade Inválida: A auditoria requer exatamente 3 catálogos (Natura, Avon e ML) para garantir a integridade cross-brand."*

---
**Status:** Planejado / Aguardando Implementação.
