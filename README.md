# 🏢 SIC — Sistema de Inteligência Corporativa

[![Version](https://img.shields.io/badge/version-1.0.1-brightgreen.svg)](#)
[![Python](https://img.shields.io/badge/python-3.8+-green.svg)](#)
[![PySide6](https://img.shields.io/badge/pyside6-6.x-blue.svg)](#)
[![License](https://img.shields.io/badge/license-Proprietary-red.svg)](#)
[![Status](https://img.shields.io/badge/status-Active-brightgreen.svg)](#)

> Suite corporativa profissional de desktop para inteligência de dados, auditoria e processamento de informações estruturadas em ambientes empresariais.

## 📋 Sumário Rápido

| Aspecto | Descrição |
|---------|-----------|
| **Tipo** | Aplicação Desktop (PySide6) |
| **Plataformas** | macOS 10.13+ / Windows 10+ / Linux moderno |
| **Linguagem** | Python 3.8+ |
| **Interface** | Profissional, Minimal & Clean |
| **Banco de Dados** | SQLite (local, sem servidor) |
| **Startup** | ~2-3 segundos |
| **Módulos** | 8 (Início, Gerador, Sync, Auditor, Volumetria, Cadastro, Histórico, Configurações) |
| **Temas** | Claro e Escuro com alternância dinâmica |
| **Acessibilidade** | WCAG AA Compliant |

---

## 🎯 O Que é o SIC?

SIC é uma plataforma integrada de inteligência corporativa que combina:

- ✅ **Processamento** de dados estruturados com validação automática
- ✅ **Auditoria** de qualidade com detecção inteligente de problemas
- ✅ **Sincronização** confiável entre múltiplas fontes de dados
- ✅ **Análise** volumétrica e estatísticas detalhadas
- ✅ **Rastreamento** completo com histórico de auditoria
- ✅ **Interface** profissional e intuitiva

---

## ✨ Características Principais

### 🏢 Interface Profissional
- Design moderno Minimal & Clean (Apple/Google style)
- Navegação intuitiva em abas horizontais (top tab bar)
- Temas claro e escuro com troca instantânea
- Responsivo para múltiplos tamanhos de tela
- Acessibilidade WCAG AA em ambos os temas

### ⚡ Performance Otimizada
- Startup rápido (~2-3 segundos)
- Lazy loading de módulos para economia de memória
- Processamento assíncrono em background threads
- Notificações em tempo real de progresso
- Interface responsiva sem travamentos

### 🔍 8 Módulos Especializados

| # | Módulo | Funcionalidade |
|---|--------|---|
| 1 | 🏠 **Início** | Dashboard central com KPIs e status do sistema |
| 2 | 🔧 **Gerador** | Upload, validação e transformação de dados |
| 3 | 🔄 **Sync** | Sincronização entre múltiplas fontes de dados |
| 4 | 📊 **Auditor** | Detecção automática de problemas e inconsistências |
| 5 | 📈 **Volumetria** | Estatísticas, métricas e análises de volume |
| 6 | 📝 **Cadastro** | Gestão e manutenção de dados estruturados |
| 7 | 📅 **Histórico** | Auditoria completa de todas as operações |
| 8 | ⚙️ **Configurações** | Personalização de tema, fonte e preferências |

### 🛡️ Robusto & Confiável
- Validação rigorosa de entrada de dados
- Tratamento completo de erros e exceções
- Logs detalhados com rastreamento de auditoria
- Recuperação automática de falhas
- SQLite para persistência local sem dependência de servidor

### 🔄 Manutenção Contínua
- Auto-update automático via GitHub
- Notificação visual de novas versões
- Interface integrada para atualização
- Versionamento semântico (MAJOR.MINOR.PATCH.BUILD)

---

## 🚀 Instalação & Execução

### Pré-requisitos

- Python 3.8 ou superior
- pip (gerenciador de pacotes)
- ~500MB de espaço em disco

### Opção 1: Executável (Recomendado)

Baixe a versão compilada em [Releases](https://github.com/seu-usuario/sic/releases) e execute.

### Opção 2: Código-Fonte (Desenvolvimento)

```bash
# Clone o repositório
git clone https://github.com/seu-usuario/sic.git
cd sic

# Crie ambiente virtual
python -m venv venv

# Ative-o
source venv/bin/activate          # macOS/Linux
# ou: venv\Scripts\activate       # Windows

# Instale dependências
pip install -r requirements.txt

# Execute a aplicação
python -m src.main_app
```

---

## 🏗️ Estrutura do Projeto

```
Versão Estável/
├── src/
│   ├── main_app.py                 # Ponto de entrada
│   ├── core/                       # Motores de negócio
│   │   ├── version.py
│   │   ├── update_service.py
│   │   └── config.py
│   ├── engines/                    # Lógica de processamento
│   │   ├── auditor.py
│   │   ├── generator.py
│   │   ├── sync.py
│   │   └── volumetry.py
│   ├── ui/                         # Interface
│   │   ├── main_window.py
│   │   ├── pages/                  # Vistas dos módulos
│   │   ├── components/             # Widgets reutilizáveis
│   │   ├── styles/
│   │   │   ├── qss_light.py        # Tema claro
│   │   │   └── qss_dark.py         # Tema escuro
│   │   └── ...
│   ├── workers/                    # Threads de background
│   ├── utils/                      # Utilitários
│   └── resources/                  # Assets
├── history.db                      # Banco de dados SQLite
├── README.md                       # Este arquivo
├── PROJETO.md                      # Visão geral do projeto
├── MANUAL.md                       # Manual de uso
├── JORNADA.md                      # Histórico de desenvolvimento
└── requirements.txt                # Dependências Python
```

---

## 🛠️ Stack Técnico

### Frontend
- **PySide6** — Framework Qt para Python (GUI desktop)
- **QSS** — Stylesheets (temas e componentes)
- **Helvetica Neue** — Tipografia profissional

### Backend
- **Python 3.8+** — Linguagem principal
- **Threading** — Processamento assíncrono (sem travamentos)
- **SQLite3** — Persistência de dados local

### DevOps
- **Git** — Versionamento
- **GitHub API** — Auto-update
- **Semantic Versioning** — Versionamento (v1.0.1)

---

## 📖 Documentação

| Documento | Descrição |
|-----------|-----------|
| **README.md** (este) | Quick start e visão técnica |
| **PROJETO.md** | Explicação completa do projeto |
| **MANUAL.md** | Como usar cada módulo (passo-a-passo) |
| **JORNADA.md** | Histórico de desenvolvimento (fases) |
| **FLUXO_TRABALHO.md** | Como desenvolver e lançar versões (Git Flow) |

👉 **Leia [PROJETO.md](PROJETO.md) para entender melhor o sistema.**  
👉 **Leia [FLUXO_TRABALHO.md](FLUXO_TRABALHO.md) para saber como contribuir e lançar versões.**  
👉 **Leia [MANUAL.md](MANUAL.md) para saber como usar cada funcionalidade.**

---

## ⚙️ Configuração Rápida

Após iniciar a aplicação:

1. **Tema:** Clique no ícone ◑ (canto superior direito) para alternar claro/escuro
2. **Fonte:** Acesse Configurações ⚙️ → ajuste tamanho (11-18px)
3. **Auto-update:** Configure em Configurações → ativar/desativar
4. **Módulos:** Clique nas abas no topo para navegar

As preferências são salvas automaticamente.

---

## 🧪 Desenvolvimento

### Setup para Desenvolvedores

```bash
# Clone + ambiente
git clone https://github.com/seu-usuario/sic.git
cd sic
python -m venv venv
source venv/bin/activate

# Dependências incluindo dev
pip install -r requirements-dev.txt

# Testes (se disponíveis)
pytest tests/

# Debug mode
python -m src.main_app --debug
```

### Padrões

- **Commits:** Conventional Commits format
- **Branches:** feature/, fix/, docs/
- **Type Hints:** Obrigatório em funções públicas
- **Naming:** snake_case (funções), PascalCase (classes)

---

## 📊 Arquitetura

```
┌─────────────────────────────────────┐
│     SIC Desktop Application         │
├─────────────────────────────────────┤
│  UI Layer                           │
│  ├─ Main Window (56px Top Bar)      │
│  ├─ 8 Page Views (Módulos)          │
│  ├─ Components (Buttons, Cards)     │
│  └─ Themes (Light/Dark QSS)         │
├─────────────────────────────────────┤
│  Business Logic                     │
│  ├─ Auditor Engine                  │
│  ├─ Generator Engine                │
│  ├─ Sync Engine                     │
│  └─ Volumetry Engine                │
├─────────────────────────────────────┤
│  Data Layer                         │
│  ├─ SQLite Database                 │
│  ├─ File System                     │
│  └─ Cache                           │
└─────────────────────────────────────┘
```

---

## 🎨 Design System

### Cores Tema Claro
- Primária: `#3b82f6` (Azul profissional)
- Fundo: `#ffffff` (Branco)
- Cards: `#f5f5f5` (Cinza leve)
- Texto: `#1a1a1a` (Preto suave)
- Bordas: `#e5e7eb` (Cinza suave)

### Cores Tema Escuro
- Primária: `#60a5fa` (Azul claro)
- Fundo: `#0f172a` (Azul muito escuro)
- Cards: `#1e293b` (Azul escuro)
- Texto: `#f1f5f9` (Branco suave)
- Bordas: `#334155` (Cinza-azul)

### Componentes
- **Botões:** Primário (azul), Secundário (cinza), Ghost (transparente)
- **Cards:** Bordas 1px com hover, raio 8px
- **Inputs:** Foco 2px com cor primária
- **Tabelas:** Header destacado, seleção clara

---

## 🐛 Troubleshooting

### App não abre

```bash
# Teste do terminal
python -m src.main_app
```

### Erro "ModuleNotFoundError"

```bash
pip install --upgrade PySide6
```

### Tema não muda

Apague config: `~/.config/SIC/SIC_Suite.conf` (macOS/Linux)  
Ou: `%AppData%\SIC\SIC_Suite.conf` (Windows)

### Performance lenta

- Feche outras aplicações
- Verifique RAM disponível
- Reinicie a aplicação

---

## 📈 Estatísticas

| Métrica | Valor |
|---------|-------|
| Linhas de Código | ~8,500+ |
| Módulos | 8 |
| Componentes UI | 50+ |
| QSS Lines | 1,450+ |
| Startup Time | ~2-3s |
| Temas | 2 (claro/escuro) |
| Acessibilidade | WCAG AA ✅ |

---

## 📝 Changelog

**v0.2.3.3** — Phase 4 Polish (atual)
- Enhanced card styling com bordas
- Button focus states melhorados
- Input field polish (2px focus borders)
- Dark mode consistency

**v0.2.3.0-v0.2.3.2** — Phases 1-3
- Design system & colors
- Components refinement
- Navigation redesign (top tab bar)

---

## 📞 Suporte

- 📖 Leia [MANUAL.md](MANUAL.md) para dúvidas de uso
- 📖 Leia [PROJETO.md](PROJETO.md) para arquitetura
- 🐛 [Abra uma issue](https://github.com/seu-usuario/sic/issues)

---

## ✅ Checklist Rápido

- [x] Interface profissional (Minimal & Clean)
- [x] 8 módulos funcionais
- [x] Performance otimizada (~2-3s startup)
- [x] Temas claro e escuro
- [x] Acessibilidade WCAG AA
- [x] Auto-update integrado
- [x] Histórico e auditoria
- [x] Validação de dados robusta

---

**Versão:** 0.2.3.3  
**Status:** ✅ Ativo e em manutenção  
**Última atualização:** 2026-04-16

Para mais detalhes, consulte [PROJETO.md](PROJETO.md) e [MANUAL.md](MANUAL.md).
