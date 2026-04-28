# 🛠️ Fluxo de Trabalho (Git Workflow) — SIC

Este documento descreve o processo profissional de desenvolvimento, versionamento e lançamento do SIC, garantindo estabilidade para o usuário final e agilidade para o desenvolvimento.

---

## 🌳 Estrutura de Branches

O projeto utiliza um modelo simplificado de **Git Flow**, focado em dois canais principais:

### 1. `main` (Canal Estável / Produção)
- **Propósito:** Código pronto para o usuário final.
- **Conteúdo:** Apenas versões testadas, polidas e aprovadas.
- **Automação:** Qualquer push ou tag nesta branch gera uma **Release Oficial (Latest)** no GitHub.
- **Atualizações:** Os usuários do SIC receberão notificações automáticas de atualização apenas quando esta branch for atualizada.

### 2. `dev` (Canal Beta / Desenvolvimento)
- **Propósito:** Integração de novas funcionalidades e correções.
- **Conteúdo:** Versões em teste ("In-progress").
- **Automação:** Qualquer push nesta branch gera uma **Pre-release (Beta)** no GitHub.
- **Atualizações:** Usuários da versão estável **não** recebem notificações destas versões. Ideal para testes internos.

---

## 🏷️ Versionamento Semântico

Seguimos o padrão `MAJOR.MINOR.PATCH`:

- **MAJOR (1.0.0):** Mudanças grandes, quebras de compatibilidade ou marcos históricos.
- **MINOR (1.1.0):** Novas funcionalidades que não quebram o uso anterior.
- **PATCH (1.0.1):** Correções de bugs e melhorias internas.

### Versões de Desenvolvimento
Enquanto estiver na branch `dev`, adicionamos o sufixo `-beta`:
- Exemplo: `1.1.0-beta`

---

## 🚀 Ciclo de Lançamento (Release Cycle)

O ciclo de vida de uma demanda no SIC segue o fluxo abaixo:

### Passo 1: Backlog e Planejamento
1. Selecione a demanda prioritária no **Backlog**.
2. Identifique o tipo de alteração:
   - ✨ `feature/`: Nova funcionalidade.
   - 🐛 `fix/`: Correção de bug.
   - 🆙 `update/`: Melhoria em recurso existente ou atualização de dependência.

### Passo 2: Desenvolvimento Local
1. A partir da branch `dev`, crie sua branch de trabalho:
   `git checkout dev`
   `git checkout -b feature/nome-da-demanda`
2. Implemente as alterações e realize testes locais.

### Passo 3: Integração e Versão Beta
1. Quando terminar o desenvolvimento, faça o merge na branch `dev`:
   `git checkout dev`
   `git merge feature/nome-da-demanda`
2. Atualize a versão em `src/core/version.py` adicionando o sufixo `-beta` (ex: `1.1.0-beta`).
3. Envie para o GitHub:
   `git push origin dev`
4. **GitHub Actions:** O sistema criará automaticamente uma **Pre-release (Beta)**.

### Passo 4: Validação por QA
1. Notifique a equipe de **QA** que uma nova versão Beta está disponível.
2. Aguarde os testes e o "OK" do QA.
3. Se houver bugs, corrija na branch da demanda e repita o processo.

### Passo 5: Lançamento Oficial (Latest)
1. Após o "OK" do QA, mescle a `dev` na `main`:
   `git checkout main`
   `git merge dev`
2. No arquivo `src/core/version.py`, remova o sufixo `-beta` (ex: `1.1.0`).
3. Crie a tag da versão oficial:
   `git tag v1.1.0`
4. Suba as alterações e a tag:
   `git push origin main --tags`
5. **GitHub Actions:** O sistema gerará a versão **Latest** e os usuários receberão o aviso de atualização.

---

## 💡 Regras de Ouro
1. **Nomenclatura:** Use sempre os prefixos `feature/`, `fix/` ou `update/`.
2. **Qualidade:** Nunca mescle para a `main` sem o selo de aprovação do QA na versão Beta.
3. **Sincronia:** Mantenha o `version.py` sempre alinhado com a Tag criada.

---
*Última atualização: 2026-04-28 (Padronização do Ciclo QA/Backlog)*
