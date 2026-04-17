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

### Fase 1: Desenvolvimento e Testes Internos
1. Certifique-se de que está na branch `dev`:  
   `git checkout dev`
2. Implemente as melhorias.
3. Atualize a versão em `src/core/version.py` (ex: `1.0.2-beta`).
4. Envie para o GitHub:  
   `git add .`  
   `git commit -m "feat: descrição da melhoria"`  
   `git push origin dev`
5. O GitHub criará uma **Versão Beta** automaticamente para testes.

### Fase 2: Lançamento Oficial
Quando a versão estiver estável e pronta para todos os usuários:
1. Mude para a `main`:  
   `git checkout main`
2. Mescle as novidades da `dev`:  
   `git merge dev`
3. Atualize a versão para a forma final (ex: `1.0.2` sem o "-beta").
4. Crie uma Tag oficial:  
   `git tag v1.0.2`
5. Envie para o mundo:  
   `git push origin main`  
   `git push origin v1.0.2`
6. **BUM!** O GitHub marcará como **"Latest"** e todos os usuários receberão o aviso de atualização no SIC.

---

## 💡 Regras de Ouro
1. **Nunca** faça commits diretos na `main` sem testar antes na `dev`.
2. **Sempre** atualize o `version.py` antes de criar uma tag ou fazer um merge de lançamento.
3. **Tags** devem sempre seguir o formato `vX.Y.Z` (v minúsculo).

---
*Última atualização: 2026-04-17 (Início da Era v1.x)*
