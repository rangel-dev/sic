# 📖 Manual de Uso — SIC v0.2.3.3

Guia completo passo-a-passo de como usar cada módulo e funcionalidade do SIC.

---

## 📚 Índice

1. [Primeiros Passos](#primeiros-passos)
2. [Interface Principal](#interface-principal)
3. [Módulo Início](#1-módulo-início-home)
4. [Módulo Gerador](#2-módulo-gerador-data-generator)
5. [Módulo Sync](#3-módulo-sync-sincronização)
6. [Módulo Auditor](#4-módulo-auditor-quality-assurance)
7. [Módulo Volumetria](#5-módulo-volumetria-analytics)
8. [Módulo Cadastro](#6-módulo-cadastro-data-management)
9. [Módulo Histórico](#7-módulo-histórico-audit-log)
10. [Módulo Configurações](#8-módulo-configurações-settings)
11. [Dicas & Truques](#dicas--truques)
12. [FAQ](#faq)

---

## 🚀 Primeiros Passos

### Instalação

1. **Baixe e instale** o SIC (veja [README.md](README.md) para instruções)
2. **Clique duas vezes** no ícone para abrir
3. **Aguarde o carregamento** (~2-3 segundos)
4. O **Dashboard (Início)** abrirá automaticamente

### Primeira Execução

Na primeira vez que abrir:
- ✅ O aplicativo criará o banco de dados (`history.db`)
- ✅ As preferências padrão serão salvas
- ✅ O tema padrão é **Claro** (Light)
- ✅ O tamanho de fonte padrão é **13px**

---

## 🖥️ Interface Principal

### Anatomia da Tela

```
┌─────────────────────────────────────────────────────────────┐
│  ⬡ SIC  │ Início │ Gerador │ Sync │ Auditor │ ... │ ⚙️ │ ◑ │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│                   Conteúdo do Módulo Ativo                 │
│                    (Muda com cada aba)                      │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│ Módulo ativo: Início | v0.2.3.3                             │
└─────────────────────────────────────────────────────────────┘
```

### Componentes da Barra Superior

| Ícone | Nome | Função |
|-------|------|--------|
| ⬡ | Logo | Mostra versão do app quando clicado |
| Abas | Navegação | Mude entre os 8 módulos do sistema |
| ⚙️ | Configurações | Acesse preferências e ajustes |
| ◑ | Tema | Alterne entre claro (dia) e escuro (noite) |

### Status Bar (Inferior)

Mostra informações úteis:
- Módulo ativo atualmente
- Versão do aplicativo
- Status de operações em progresso

---

## 1️⃣ Módulo Início (Home)

### O Que É?

Painel de controle central onde você vê:
- Status geral do sistema
- Últimas operações realizadas
- Alertas importantes
- Atalhos para módulos

### Como Usar

**Passo 1:** Clique na aba "Início" (primeira aba)

**Passo 2:** Você verá cards com informações:
- **KPI Cards** — Indicadores-chave (volume, operações, etc)
- **Status Cards** — Status das últimas operações
- **Alert Cards** — Alertas que precisam atenção

**Passo 3:** Clique em qualquer card para:
- Ver detalhes completos
- Ir para o módulo relacionado
- Executar ações rápidas

### Exemplo de Fluxo

```
Abrir App
    ↓
[Início aparece automaticamente]
    ↓
Vejo 3 Alertas de Erro em Auditor
    ↓
Clico em "Ver Erros"
    ↓
Vou para Módulo Auditor automaticamente
```

---

## 2️⃣ Módulo Gerador (Data Generator)

### O Que É?

Cria, transforma e valida dados. É o ponto de entrada para processar informações no sistema.

### Como Usar — Guia Passo-a-Passo

#### **Passo 1: Acesse o Módulo**
- Clique na aba "Gerador" (2ª aba da esquerda)

#### **Passo 2: Prepare seu Arquivo**
Prepare um arquivo em um destes formatos:
- `.xml` — Arquivos XML estruturados
- `.xlsx` — Planilhas Excel
- `.csv` — Arquivos separados por vírgula
- `.json` — Dados em formato JSON

#### **Passo 3: Faça Upload**

**Opção A — Drag & Drop (Recomendado)**
```
1. Abra seu arquivo no Explorador/Finder
2. Arraste-o para a área cinzenta que diz "Solte seu arquivo aqui"
3. O arquivo será importado automaticamente
```

**Opção B — Clique para Selecionar**
```
1. Clique no botão "Selecionar Arquivo"
2. Escolha o arquivo no seu computador
3. Clique em "Abrir"
```

#### **Passo 4: Validação Automática**

Após o upload, o sistema automaticamente:
- ✅ Verifica o formato
- ✅ Valida a estrutura dos dados
- ✅ Detecta problemas comuns
- ✅ Mostra um relatório

Você verá uma barra de progresso com status:
- 🔵 **Processando...** — Analisando dados
- 🟢 **Sucesso** — Dados válidos
- 🔴 **Erro** — Problemas encontrados

#### **Passo 5: Revise os Resultados**

Se tudo OK:
```
✅ Arquivo carregado com sucesso
   📊 1,250 registros processados
   ⏱️ Tempo: 2.5 segundos
   
   [Confirmar] [Cancelar]
```

Se houver erros:
```
⚠️ Problemas encontrados (5 erros)
   
   • Linha 12: Valor inválido em "Preço"
   • Linha 45: Campo obrigatório faltando
   • Linha 67: Formato de data incorreto
   
   [Detalhes] [Corrigir] [Ignorar]
```

#### **Passo 6: Confirme o Processamento**

Clique em um dos botões:
- **Confirmar** — Processa e salva os dados
- **Cancelar** — Descarta e volta
- **Detalhes** — Vê problemas específicos
- **Corrigir** — Abre editor para corrigir

### Exemplo Real

```
Cenário: Você tem uma planilha Excel com 500 produtos

1. Abra o Gerador
2. Arraste seu Excel aqui → solta
3. Sistema processa (3 segundos)
4. "✅ 500 produtos validados com sucesso"
5. Clica Confirmar
6. Dados prontos para auditar no Auditor
```

---

## 3️⃣ Módulo Sync (Sincronização)

### O Que É?

Sincroniza dados entre múltiplas fontes, garantindo consistência entre sistemas.

### Como Usar

#### **Passo 1: Acesse Sync**
- Clique na aba "Sync" (3ª aba)

#### **Passo 2: Crie ou Selecione uma Conexão**

**Se primeira vez:**
```
Clique: [Criar Nova Conexão]
  ↓
Nome: "Banco Principal"
Tipo: "Database" ou "API"
URL: https://seu-servidor/api
Credenciais: (usuario/senha)
  ↓
[Testar Conexão]
  ↓
✅ Conexão validada
  ↓
[Salvar]
```

**Se já existe:**
```
Selecione na lista: "Banco Principal"
```

#### **Passo 3: Configure a Sincronização**

```
Origem: Dados Locais (Gerador)
Destino: Banco Principal
Modo: 
  ☑ Bidirecional (sincroniza ida e volta)
  ☐ Unidirecional (apenas enviar)
  
Agendar:
  ☑ Automático (cada 24h)
  ☐ Manual (apenas quando clico)
```

#### **Passo 4: Execute**

```
[Sincronizar Agora]
  ↓
Processando...
█████████░ 50% - Sincronizando 250/500 registros
  ↓
✅ Sincronização concluída
   • 500 registros enviados
   • 10 conflitos resolvidos
   • Tempo: 45 segundos
   
   [Ver Detalhes] [Salvar Log]
```

#### **Passo 5: Verifique o Histórico**

Clique em "Ver Histórico" para:
- Ver todas as sincronizações passadas
- Checar se houve erros
- Exportar logs

### Exemplo Prático

```
Você precisa sincronizar produtos com 2 sistemas diferentes

1. Gerador → Processa 500 produtos
2. Sync → Cria conexão com Sistema A
3. Sync → Sincroniza (automático ou manual)
4. Sync → Cria conexão com Sistema B
5. Sync → Sincroniza com Sistema B também
6. Histórico → Verifica se tudo foi sincronizado

✅ Agora os 3 sistemas têm dados idênticos
```

---

## 4️⃣ Módulo Auditor (Quality Assurance)

### O Que É?

Analisa automaticamente para encontrar problemas e inconsistências. É o "detector de erros" do sistema.

### Como Usar

#### **Passo 1: Acesse o Auditor**
- Clique na aba "Auditor" (4ª aba)

#### **Passo 2: Selecione os Dados a Auditar**

```
Fonte de Dados:
  ☑ Dados Processados (do Gerador)
  ☐ Dados Sincronizados (do Sync)
  ☐ Dados do Histórico

Escopo:
  ☑ Todos os registros
  ☐ Últimos 100
  ☐ Período: De _____ Até _____
```

#### **Passo 3: Escolha Regras de Validação**

```
Marque quais regras deseja verificar:

[x] Campos Obrigatórios
[x] Integridade de Dados
[x] Valores Fora do Intervalo
[x] Duplicatas
[x] Formatação Correta
[x] Relacionamentos Válidos
[ ] Regras Customizadas

[Selecionar Todas] [Limpar Todas]
```

#### **Passo 4: Execute a Auditoria**

```
[Auditar Agora]
  ↓
Analisando...
█████████░ 60% - Verificando 300/500 registros
  ↓
⚠️ Auditoria completa
   • 45 problemas encontrados
   • 480 registros OK
   • 20 avisos
   
   [Ver Detalhes] [Gerar Relatório]
```

#### **Passo 5: Revise os Problemas**

Uma tabela mostrará:

| # | Tipo | Registro | Problema | Sugestão |
|---|------|----------|----------|----------|
| 1 | ❌ Erro | PROD-001 | Preço inválido | Defina valor > 0 |
| 2 | ⚠️ Aviso | PROD-002 | Campo faltando | Preencha "Descrição" |
| 3 | ℹ️ Info | PROD-003 | Valor suspeito | Verifique preço alto |

#### **Passo 6: Corrija os Problemas**

Clique no ícone 🔧 ao lado de cada problema:

**Opção 1 — Corrigir Automático**
```
[Sugestão Automática]
  ↓
✅ Valor atualizado para: 150.00
```

**Opção 2 — Editar Manual**
```
[Editar]
  ↓
[Campo de edição]
  ↓
[Salvar]
```

**Opção 3 — Aceitar Como Está**
```
[Ignorar Problema]
  ↓
✅ Problema ignorado
```

#### **Passo 7: Gere Relatório**

```
[Gerar Relatório]
  ↓
Formato:
  ☑ PDF
  ☐ Excel
  ☐ CSV
  
[Exportar]
  ↓
✅ Relatório salvo: Auditoria_2026-04-16.pdf
```

### Exemplo Completo

```
Cenário: 500 produtos importados, mas com alguns erros

1. Abra Auditor
2. Selecione "Dados Processados"
3. Marque todas as regras
4. Clique "Auditar Agora"
5. Sistema encontra 45 problemas
6. Você revisa cada um:
   - 30 erros → Corrige automático
   - 10 avisos → Ignora (são ok)
   - 5 info → Lê e deixa como está
7. Gera relatório em PDF
8. Salva tudo

✅ Agora seus dados estão auditados e seguros
```

---

## 5️⃣ Módulo Volumetria (Analytics)

### O Que É?

Mostra estatísticas e análises de volume de dados. Responde perguntas como "Quantos registros?", "Como se distribuem?", "Tem crescimento?"

### Como Usar

#### **Passo 1: Acesse Volumetria**
- Clique na aba "Volumetria" (5ª aba)

#### **Passo 2: Escolha Período**

```
Período de Análise:
  
Presets:
  ☑ Últimas 24 horas
  ☐ Últimos 7 dias
  ☐ Este mês
  ☐ Últimos 3 meses
  ☐ Customizado:
     De: 01/01/2026 Até: 31/03/2026
```

#### **Passo 3: Visualize as Métricas**

Você verá cards com números:

```
┌──────────────────────────────────────┐
│  Total de Registros                  │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│           5,250                      │
│                                      │
│  📈 +12% em relação ao período anterior
└──────────────────────────────────────┘

┌──────────────────────────────────────┐
│  Registros por Dia                   │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│                                      │
│  Mar 16 ███████ 250                 │
│  Mar 15 █████████ 350               │
│  Mar 14 ██████ 200                  │
│  Mar 13 ████████ 300                │
│  Mar 12 ████ 150                    │
│                                      │
│  Média: 250 por dia                  │
└──────────────────────────────────────┘
```

#### **Passo 4: Exporte Dados**

```
[Exportar Relatório]
  ↓
Formato:
  ☑ PDF (com gráficos)
  ☐ Excel (dados brutos)
  ☐ CSV (simples)
  
[Salvar]
  ↓
✅ Arquivo salvo: Volumetria_2026-04-16.pdf
```

### Métricas Disponíveis

| Métrica | O Que Mostra |
|---------|-------------|
| **Total** | Quantidade total de registros |
| **Média** | Média de registros por período |
| **Máximo** | Maior pico de dados |
| **Mínimo** | Menor volume registrado |
| **Crescimento** | Percentual de aumento/redução |
| **Distribuição** | Como os dados se distribuem (gráfico de pizza) |
| **Tendência** | Se aumenta ou diminui ao longo do tempo |

---

## 6️⃣ Módulo Cadastro (Data Management)

### O Que É?

Gerencia os dados estruturados: criar, editar, buscar e deletar registros.

### Como Usar

#### **Passo 1: Acesse Cadastro**
- Clique na aba "Cadastro" (6ª aba)

#### **Passo 2: Visualize Registros**

Você verá uma tabela com todos os registros:

```
┌────────┬──────────┬────────┬──────────┐
│ ID     │ Nome     │ Valor  │ Status   │
├────────┼──────────┼────────┼──────────┤
│ 001    │ Produto A│ 150.00 │ Ativo    │
│ 002    │ Produto B│ 200.00 │ Ativo    │
│ 003    │ Produto C│ 175.50 │ Inativo  │
└────────┴──────────┴────────┴──────────┘
```

#### **Passo 3: Busque e Filtre**

```
Busca Rápida:
[🔍 Digite aqui...]

Filtros Avançados:
Nome: _______________
Valor mín: _____ Valor máx: _____
Status: [Todos ▼]
Data: De _____ Até _____

[Aplicar Filtros] [Limpar Filtros]
```

#### **Passo 4: Crie um Novo Registro**

```
[+ Novo Registro]
  ↓
[Formulário com campos]
  ID: ________________ (auto)
  Nome: ________________
  Valor: ________________
  Status: [Selecionar ▼]
  Descrição: ________________
  
  [Salvar] [Cancelar]
```

#### **Passo 5: Edite um Existente**

```
Clique no botão ✏️ em um registro
  ↓
[Formulário com dados já preenchidos]
  ID: 001 (não pode mudar)
  Nome: Produto A [editar]
  Valor: 150.00 [editar]
  Status: Ativo [editar]
  
  [Salvar Alterações] [Cancelar]
```

#### **Passo 6: Delete um Registro**

```
Clique no botão 🗑️ em um registro
  ↓
Confirmação:
"Tem certeza que deseja deletar PROD-001?"

[Sim, deletar] [Cancelar]
  ↓
✅ Registrodeletado e arquivado em histórico
```

#### **Passo 7: Importação em Lote**

```
[Importar Registros]
  ↓
[Selecionar arquivo...]
  ↓
Sistema processa e valida
  ↓
✅ 100 novos registros importados
```

---

## 7️⃣ Módulo Histórico (Audit Log)

### O Que É?

Rastreamento completo de todas as operações realizadas no sistema. É o "filme" de tudo o que foi feito.

### Como Usar

#### **Passo 1: Acesse Histórico**
- Clique na aba "Histórico" (7ª aba)

#### **Passo 2: Visualize o Log**

Você verá uma tabela cronológica:

```
┌─────────────┬───────────┬──────────────┬─────────────┐
│ Data/Hora   │ Módulo    │ Ação         │ Status      │
├─────────────┼───────────┼──────────────┼─────────────┤
│ 16 Apr 14:32│ Gerador   │ Upload: 500  │ ✅ Sucesso  │
│ 16 Apr 14:35│ Auditor   │ Auditoria    │ ✅ Sucesso  │
│ 16 Apr 14:40│ Sync      │ Sincronizar  │ ✅ Sucesso  │
│ 16 Apr 14:45│ Cadastro  │ Criar Reg.   │ ✅ Sucesso  │
└─────────────┴───────────┴──────────────┴─────────────┘
```

#### **Passo 3: Filtre e Busque**

```
Período:
  De: __________ Até: __________
  
Módulo:
  [Todos ▼] ou selecione: Gerador, Auditor, etc
  
Tipo de Ação:
  [Todos ▼] ou: Upload, Auditoria, Sincronizar, etc
  
Status:
  [Todos ▼] ou: ✅ Sucesso, ❌ Erro, ⚠️ Aviso
  
[Filtrar] [Limpar Filtros]
```

#### **Passo 4: Veja Detalhes**

Clique em uma linha para expandir:

```
Gerador | Upload de arquivo | 2026-04-16 14:32:45
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Status: ✅ Sucesso

Detalhes:
  • Arquivo: dados.xlsx
  • Registros processados: 500
  • Erros encontrados: 0
  • Tempo total: 2.3 segundos
  • Usuário: Sistema
  • IP: 127.0.0.1

Mais informações:
  [Ver Arquivo Original] [Ver Resultado] [Repetir]
```

#### **Passo 5: Exporte o Histórico**

```
[Exportar Log]
  ↓
Período: [Últimos 30 dias ▼]
Formato: 
  ☑ CSV (simples, para Excel)
  ☐ JSON (para integração)
  ☐ PDF (formatado)
  
[Exportar]
  ↓
✅ Arquivo salvo: historico_2026-04-16.csv
```

#### **Passo 6: Limpe Dados Antigos (Opcional)**

```
[Limpeza de Dados]
  ↓
Remover operações anteriores a:
  ☑ Mais de 90 dias
  ☐ Mais de 180 dias
  ☐ Mais de 1 ano
  
⚠️ Essa ação é irreversível
  
[Continuar] [Cancelar]
```

### Informações Rastreadas

O sistema registra automaticamente:
- ✅ Data e hora exata
- ✅ Qual módulo foi usado
- ✅ Que ação foi feita
- ✅ Se teve sucesso ou erro
- ✅ Quantos registros foram processados
- ✅ Tempo levado
- ✅ Detalhes adicionais

---

## 8️⃣ Módulo Configurações (Settings)

### O Que É?

Personaliza como o aplicativo funciona: tema, tamanho de fonte, notificações, etc.

### Como Usar

#### **Passo 1: Acesse Configurações**

**Opção A** — Clique no ícone ⚙️ no topo direito  
**Opção B** — Clique na aba "Configurações" (última aba)

#### **Passo 2: Ajuste o Tema**

```
TEMA DO APLICATIVO

Seleção Atual: [Claro ▼]

Opções:
  ☑ Claro (Light)
     - Fundo branco
     - Texto preto
     - Ideal para dia
  
  ☐ Escuro (Dark)
     - Fundo azul escuro
     - Texto branco
     - Ideal para noite

Mudança aplicada: Instantânea
Salvo em: Preferências do sistema
```

#### **Passo 3: Ajuste Tamanho de Fonte**

```
TAMANHO DE FONTE

Tamanho atual: 13px ●────────○ 18px
              [11] [12] [13] [14] [15] [16] [17] [18]

Pré-definidos:
  [Pequeno] [Normal] [Grande] [Muito Grande]

Preview:
  Este é o tamanho da fonte que você verá
  em todo o aplicativo.

Mudança aplicada: Instantânea
Salvo em: Preferências do sistema
```

#### **Passo 4: Configure Auto-Update**

```
ATUALIZAÇÕES AUTOMÁTICAS

Status: Verificar a cada 24 horas

[☑] Ativar verificação automática
    O app irá procurar por novas versões
    automaticamente e notificar você

Última verificação: 16 Apr 2026 14:30
Versão instalada: v0.2.3.3
Versão mais recente: v0.2.3.3 (você está atualizado!)

[Verificar Agora] [Histórico de Atualizações]
```

#### **Passo 5: Configure Notificações**

```
NOTIFICAÇÕES

[☑] Notificações de sucesso
    Avisar quando operações completam

[☑] Notificações de erro
    Avisar sobre problemas encontrados

[☑] Notificações de sync
    Avisar sobre sincronizações

[☐] Sons
    Emitir som ao completar operações
```

#### **Passo 6: Veja Informações do Sistema**

```
INFORMAÇÕES DO SISTEMA

Versão do SIC: v0.2.3.3
Build: 0.2.3.3
Versão Python: 3.10.2
Versão Qt/PySide6: 6.4.1
Sistema Operacional: macOS 12.4
Arquitetura: x86_64

Banco de Dados:
  Localização: ~/.config/SIC/history.db
  Tamanho: 2.5 MB
  Registros: 1,250
  Último backup: 16 Apr 2026 10:00

[Fazer Backup Agora] [Restaurar Backup]

About:
  SIC © 2026 — Sistema de Inteligência Corporativa
  Desenvolvido com Python & PySide6
  Licença: Propriedade Privada
```

#### **Passo 7: Limpe Cache (Avançado)**

```
DADOS AVANÇADOS

Cache do aplicativo:
  Tamanho: 1.2 MB
  [Limpar Cache]
  ✅ Salvo em: 16 Apr 2026 14:30
  
  Cuidado: Limpar cache pode deixar o app mais lento
  na próxima vez, mas libera espaço em disco.

Dados Locais:
  [Exportar Dados] — Salvar cópia em CSV
  [Apagar Tudo] — ⚠️ Irreversível! Deleta todos os dados
```

---

## 💡 Dicas & Truques

### 🎯 Atalhos de Teclado

| Atalho | Ação |
|--------|------|
| `Tab` | Navega entre campos |
| `Enter` | Confirma/Salva |
| `Esc` | Cancela/Fecha modal |
| `Ctrl+S` | Salva (em formulários) |
| `Ctrl+Z` | Desfaz última ação (se disponível) |

### ⌨️ Navegação Rápida

Clique nas abas no topo em qualquer momento:

```
⬡ SIC │ Início │ Gerador │ Sync │ Auditor │ Volumetria │ Cadastro │ Histórico │ ⚙️
```

Ou use números (se ativado em Configurações):
- `1` — Início
- `2` — Gerador
- `3` — Sync
- `4` — Auditor
- `5` — Volumetria
- `6` — Cadastro
- `7` — Histórico
- `8` — Configurações

### 🔄 Operações em Lote

Vários módulos suportam operações em lote:

```
Selecione múltiplos registros:
  [☑] PROD-001
  [☑] PROD-002
  [☑] PROD-003
  
[Ações em Lote ▼]
  → Editar todos
  → Deletar todos
  → Exportar seleção
  → Gerar relatório
```

### 📊 Barra de Progresso

Ao processar dados, você verá:

```
Processando...
████████░░ 80% - 4 de 5 operações concluídas
```

- 🟡 **Amarelo** = Processando
- 🟢 **Verde** = Sucesso
- 🔴 **Vermelho** = Erro
- ⚪ **Cinza** = Aguardando

### 💾 Salvamento Automático

O SIC salva automaticamente:
- ✅ Suas preferências (tema, fonte, etc)
- ✅ Dados que você processa
- ✅ Configurações de conexão
- ✅ Histórico de operações

Você NÃO precisa clicar em "Salvar" globalmente.

### 🎨 Modo Escuro (Dark Mode)

Para ativar modo escuro:

```
Opção 1: Clique no ícone ◑ (topo direito)
Opção 2: Acesse Configurações → Selecione "Escuro"
Opção 3: Pode ser automático (ao anoitecer) em breve
```

O modo escuro é perfeito para:
- Trabalhar de noite sem prejudicar os olhos
- Economizar bateria (em alguns displays)
- Ambiente com pouca luz

---

## ❓ FAQ (Perguntas Frequentes)

### Geral

**P: Como faço backup dos meus dados?**
```
R: Vá em Configurações → "Fazer Backup Agora"
   Um arquivo será salvo em: ~/Downloads/SIC_Backup_DATA.zip
   Você pode restaurar a qualquer hora em Configurações
```

**P: O que é o arquivo "history.db"?**
```
R: É o banco de dados que armazena:
   • Histórico de todas as operações
   • Dados processados
   • Configurações do usuário
   
   Não delete este arquivo! Se perder, perderá o histórico.
```

**P: Posso usar o SIC offline?**
```
R: Sim! A maioria das funcionalidades funciona offline.
   Apenas Sync (sincronização com servidores) não funciona
   sem conexão. Assim que conectar novamente, sincroniza.
```

### Performance

**P: Por que o app demora para abrir?**
```
R: Se está lento:
   1. Certifique-se de ter 500MB livres em disco
   2. Feche outras aplicações
   3. Reinicie seu computador
   4. Se persistir, limpe cache em Configurações
```

**P: Quantos registros o SIC consegue processar?**
```
R: Teoricamente: Milhões! Mas recomendação prática é:
   • Até 10,000 registros por vez = Performance ótima
   • 10,000 a 100,000 = Bom
   • Acima disso = Divida em lotes
```

### Tema & Interface

**P: O tema não muda quando clico no ícone ◑**
```
R: Tente:
   1. Feche o app
   2. Delete: ~/.config/SIC/SIC_Suite.conf
   3. Reabra o app
   4. Ajuste tema novamente
```

**P: Como mudo o tamanho de fonte?**
```
R: Configurações (⚙️) → Tamanho de Fonte → Selecione (11-18px)
   Mudança é instantânea em toda a interface
```

### Dados & Auditoria

**P: Que tipo de arquivo posso fazer upload?**
```
R: Atualmente suportados:
   • XML (.xml)
   • Excel (.xlsx)
   • CSV (.csv)
   • JSON (.json)
   
   Outros formatos: Converse com suporte
```

**P: Como desfaço uma operação?**
```
R: Ops! Não há "desfazer" global. Mas você pode:
   1. Ver em Histórico o que foi feito
   2. Editar manualmente em Cadastro
   3. Ou restaurar um backup antigo
   
   Dica: Sempre faça backup antes de operações grandes!
```

**P: Quanto tempo os dados ficam no Histórico?**
```
R: Indefinidamente, até você deletar manualmente em
   Histórico → Limpeza de Dados
   
   Recomendação: Limpe dados com mais de 1 ano anualmente
```

### Sync & Integração

**P: Como faço para sincronizar com outro sistema?**
```
R: 1. Acesse módulo Sync
   2. Clique "Criar Nova Conexão"
   3. Digite credenciais (URL, usuário, senha)
   4. Teste a conexão
   5. Configure e execute a sincronização
```

**P: Sync é bidirecional?**
```
R: Pode ser! Em Sync → Configuração → Você escolhe:
   ☑ Bidirecional (sincroniza ida e volta)
   ☐ Unidirecional (apenas enviar)
```

### Suporte & Ajuda

**P: Como reporto um bug?**
```
R: 1. Anote exatamente o que aconteceu
   2. Anote a versão (Configurações → v0.2.3.3)
   3. Abra issue em: github.com/seu-usuario/sic/issues
   4. Descreva o problema em detalhes
   5. Inclua prints se possível
```

**P: Onde fico sabendo de novidades?**
```
R: • Automaticamente = O app notifica de atualizações
   • Releases = github.com/seu-usuario/sic/releases
   • Changelog = README.md e PROJETO.md
```

---

## 🚀 Próximas Etapas

Agora que você conhece todos os módulos:

1. **Comece simples:** Abra o Gerador e importe um arquivo pequeno
2. **Pratique a auditoria:** Use o Auditor para encontrar problemas
3. **Sincronize:** Se tiver outro sistema, configure Sync
4. **Analise:** Use Volumetria para ver padrões dos seus dados
5. **Monitore:** Consulte regularmente o Histórico

---

**Versão:** 0.2.3.3  
**Última atualização:** 2026-04-16  
**Status:** ✅ Completo e pronto para uso

Para mais detalhes técnicos, veja [PROJETO.md](PROJETO.md).
