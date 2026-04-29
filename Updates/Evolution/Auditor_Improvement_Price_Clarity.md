# Melhoria de UX: Clareza em Mensagens de Divergência de Preço

## 1. Contexto
No módulo **Auditor**, quando o sistema identifica uma divergência entre os preços da Grade de Ativação (Excel) e os preços cadastrados no Salesforce (XML), ele gera um alerta. Atualmente, a mensagem de erro é ambígua quanto à origem de cada valor, o que dificulta a correção rápida pelo analista.

## 2. Problema Atual
A mensagem atual não especifica qual valor pertence a qual fonte de dados.
- **Exemplo Atual:** `DIVERGE SF (POR: R$113.22 vs R$132.09)`
- **Dificuldade:** O usuário não sabe se o erro está na planilha (Grade) ou se o Salesforce é que precisa de atualização, exigindo uma conferência manual extra.

## 3. Solução Proposta
Alterar a string de retorno do motor de auditoria para incluir prefixos explícitos da fonte de dados (**GRADE** e **SF**).

### 3.1 Formatação Sugerida
- **De:** `DIVERGE SF (POR: R$113.22 vs R$132.09)`
- **Para:** `DIVERGE SF (POR GRADE: R$113.22 vs POR SF: R$132.09)`

### 3.2 Extensão para Preço "DE"
A mesma lógica deve ser aplicada para divergências no preço de lista:
- **Exemplo:** `DIVERGE SF (DE GRADE: R$150.00 vs DE SF: R$165.00)`

## 4. Benefícios
1. **Redução de MTTR (Mean Time To Repair):** O analista identifica instantaneamente onde está o dado incorreto.
2. **Autonomia:** Evita dúvidas e chamados para o time de tecnologia para entender "quem é quem" na mensagem de erro.
3. **Precisão:** Elimina o risco de o analista corrigir o Salesforce quando, na verdade, a planilha estava errada (ou vice-versa).

---
**Status:** Aguardando Implementação no `auditor_engine.py`.
