# SIC - Sistema de Inteligência Corporativa

## O Que é o Projeto?

**SIC** (Sistema de Inteligência Corporativa) é uma suite empresarial de desktop moderna e profissional, desenvolvida em Python com PySide6, projetada para gerenciar, processar e auditar dados estruturados em ambientes corporativos.

### Visão Geral

O SIC é um sistema completo de inteligência de dados que integra múltiplos módulos especializados para:

- **Processamento de Dados:** Importação, validação e transformação de arquivos XML e estruturados
- **Auditoria de Qualidade:** Verificação automática de integridade e conformidade de dados
- **Sincronização de Sistemas:** Gerenciamento de processos de sincronização entre fontes de dados
- **Análise Volumétrica:** Estatísticas detalhadas e métricas de volume de dados
- **Gestão de Catálogos:** Manutenção e organização de dados estruturados
- **Histórico e Rastreamento:** Registro completo de todas as operações e mudanças
- **Configurações Centralizadas:** Gerenciamento de preferências e parâmetros do sistema

### Características Principais

#### 🏢 Arquitetura Corporativa
- Interface profissional com design Minimal & Clean (estilo Apple/Google)
- Temas claro e escuro com alternância dinâmica
- Navegação intuitiva em abas horizontais
- Responsivo e escalável para diversos tamanhos de tela

#### ⚡ Performance
- Carregamento rápido de módulos (lazy loading)
- Processamento assíncrono de operações pesadas
- Notificações em tempo real de progresso
- Cache inteligente de dados

#### 🔍 Inteligência de Dados
- **Auditor:** Análise automática de problemas e inconsistências
- **Gerador:** Criação e transformação de estruturas de dados
- **Sync:** Sincronização confiável entre sistemas
- **Volumetria:** Métricas e estatísticas de dados

#### 🛡️ Robustez
- Validação rigorosa de entrada de dados
- Tratamento completo de erros
- Logs detalhados de operações
- Recuperação automática de falhas

#### 🎨 UI/UX Moderno
- Design system consistente e profissional
- Componentes refinados (botões, cards, inputs, tabelas)
- Micro-interações suaves e feedback visual claro
- Acessibilidade (WCAG AA compliance)

#### 🔄 Manutenção Contínua
- Sistema de auto-update automático
- Verificação de novas versões em tempo real
- Interface de atualização integrada
- Versionamento semântico (v1.0.1)

---

## Tecnologias Utilizadas

### Backend
- **Python 3.8+** — Linguagem principal
- **PySide6** — Framework Qt para Python (interface gráfica)
- **SQLite** — Banco de dados local (histórico e cache)

### Frontend (UI)
- **Qt QSS** — Stylesheets para Qt (theming)
- **Helvetica Neue** — Tipografia profissional
- **Design System Moderno** — Cores neutras, acessibilidade

### Integração
- **XML Processing** — Parsing e validação de arquivos
- **Threading** — Operações assíncronas sem travamento da UI
- **GitHub API** — Verificação automática de atualizações

### Desenvolvimento
- **Git** — Versionamento de código
- **Conventional Commits** — Padrão de mensagens de commit
- **Semantic Versioning** — Versionamento (MAJOR.MINOR.PATCH.BUILD)

---

## Módulos do Sistema

### 1. **Início (Home Dashboard)**
Central de monitoramento do sistema com:
- Cards de KPI (indicadores-chave de desempenho)
- Status das operações recentes
- Alertas e notificações
- Atalhos para módulos principais

### 2. **Gerador (Data Generator)**
Criação e transformação de estruturas de dados:
- Upload de arquivos via drag-and-drop
- Validação automática de formato
- Transformação de dados em lote
- Pré-visualização de resultados
- Progresso em tempo real

### 3. **Sync (Sincronização)**
Gerenciamento de sincronização entre sistemas:
- Configuração de conexões
- Monitoramento de status
- Relatórios de sincronização
- Histórico de operações

### 4. **Auditor (Quality Assurance)**
Auditoria automática de qualidade de dados:
- Detecção de problemas e inconsistências
- Relatórios detalhados
- Sugestões de correção
- Visualização de erros em contexto

### 5. **Volumetria (Analytics)**
Análise de volume e estatísticas:
- Métricas de quantidade de dados
- Gráficos de distribuição
- Comparações temporais
- Exportação de relatórios

### 6. **Cadastro (Data Management)**
Gestão de dados estruturados:
- Criação e edição de registros
- Busca e filtros avançados
- Importação em lote
- Validação de campos

### 7. **Histórico (Audit Log)**
Rastreamento completo de operações:
- Registro de todas as ações do sistema
- Filtros por data, tipo, módulo
- Visualização de detalhes de operações
- Exportação de logs

### 8. **Configurações (Settings)**
Personalização e preferências:
- Ajustes de tema (claro/escuro)
- Tamanho de fonte escalável
- Preferenciais de operação
- Informações de sistema

---

## Fluxo de Dados

```
┌─────────────────────────────────────────────────────────────────┐
│                      SIC - Sistema Integrado                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐ │
│  │   Entrada    │      │  Processamento│     │    Saída     │ │
│  │   (Dados)    │  →   │  (Inteligência) →   │  (Relatórios)│ │
│  └──────────────┘      └──────────────┘      └──────────────┘ │
│         ↓                     ↓                      ↓          │
│    • XML Files         • Validação             • Relatórios   │
│    • Upload            • Transformação        • Logs          │
│    • Drag-Drop         • Auditoria            • Estatísticas  │
│                        • Sincronização                         │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │             Histórico & Rastreamento (SQLite)            │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Arquitetura Técnica

### Estrutura de Diretórios

```
Versão Estável/
├── src/
│   ├── main_app.py                 # Ponto de entrada da aplicação
│   ├── core/
│   │   ├── version.py              # Informações de versão
│   │   ├── update_service.py       # Gerenciamento de atualizações
│   │   └── config.py               # Configurações centralizadas
│   ├── engines/
│   │   ├── auditor.py              # Motor de auditoria
│   │   ├── generator.py            # Motor de geração de dados
│   │   ├── sync.py                 # Motor de sincronização
│   │   └── volumetry.py            # Motor de análise volumétrica
│   ├── ui/
│   │   ├── main_window.py          # Janela principal
│   │   ├── components/             # Componentes reutilizáveis
│   │   ├── pages/                  # Páginas dos módulos
│   │   │   ├── view_home.py
│   │   │   ├── view_gerador.py
│   │   │   ├── view_sync.py
│   │   │   ├── view_auditor.py
│   │   │   ├── view_volumetria.py
│   │   │   ├── view_cadastro.py
│   │   │   ├── view_history.py
│   │   │   └── view_settings.py
│   │   └── styles/
│   │       ├── qss_light.py        # Stylesheet tema claro
│   │       └── qss_dark.py         # Stylesheet tema escuro
│   ├── workers/                    # Threads de background
│   │   ├── worker_update.py
│   │   └── worker_processing.py
│   └── utils/                      # Utilitários
│       ├── file_handler.py
│       ├── validators.py
│       └── helpers.py
├── resources/                      # Arquivos de recurso
├── history.db                      # Banco de dados SQLite
├── README.md                       # Documentação
└── PROJETO.md                      # Este arquivo
```

### Padrões de Arquitetura

1. **MVC-like Pattern**
   - Views: `src/ui/pages/view_*.py`
   - Models: `src/engines/*.py`
   - Controllers: `src/ui/main_window.py`

2. **Signal-Slot (Qt)**
   - Comunicação entre componentes via sinais
   - Desacoplamento entre módulos
   - Threading seguro

3. **Lazy Loading**
   - Módulos carregados sob demanda
   - Startup rápido (~2-3 segundos)
   - Economia de memória

4. **Theme System**
   - Dois temas completos (claro/escuro)
   - QSS para styling (sem caixa de sombra em Qt)
   - Alternância dinâmica em tempo real

---

## Design System

### Paleta de Cores

**Tema Claro:**
- Primária: `#3b82f6` (Azul profissional)
- Fundo: `#ffffff` (Branco)
- Superfícies: `#f5f5f5` (Cinza claro)
- Texto: `#1a1a1a` (Preto suave)
- Bordas: `#e5e7eb` (Cinza suave)

**Tema Escuro:**
- Primária: `#60a5fa` (Azul claro)
- Fundo: `#0f172a` (Azul muito escuro)
- Superfícies: `#1e293b` (Azul escuro)
- Texto: `#f1f5f9` (Branco suave)
- Bordas: `#334155` (Cinza-azul)

### Componentes

- **Botões:** Primário (azul), Secundário (cinza), Ghost (transparente), Perigo (vermelho)
- **Cards:** Bordas suaves, hover efeitos, raio de canto 8px
- **Inputs:** Bordas 1px, foco 2px com cor primária
- **Tabelas:** Header destacado, hover suave, seleção clara
- **DropZones:** Bordas tracejadas, estados (vazio, preenchido, erro)

### Tipografia

- **Família:** Helvetica Neue, Arial (fallback)
- **Título:** 32px, peso 600
- **Seções:** 18px, peso 600
- **Corpo:** 13px, peso 400
- **Pequeno:** 11px, peso 400
- **Label:** 12px, peso 500

---

## Evolução do Projeto

### Fase 1: Fundação (Colors & Typography)
- Criação do design system
- Paleta de cores profissional
- Tipografia hierárquica
- Spacing e padding otimizados

### Fase 2: Componentes (implícita na Fase 1)
- Refinamento de botões
- Styling de cards e panels
- Input fields polidos
- Tabelas e dropzones

### Fase 3: Navegação (Tab Bar)
- Transição: sidebar → top tab bar
- Layout responsivo
- 8 módulos acessíveis
- Logo e configurações no topo

### Fase 4: Polish & Refinement
- Cards com bordas e hover efeitos
- Focus states em todos os botões
- Input fields com foco 2px
- Dark mode consistency
- Acessibilidade WCAG AA

---

## Performance & Otimizações

### Startup
- Tempo inicial: ~2-3 segundos
- Lazy loading de módulos
- Pre-load apenas Home (Início)
- Cache de stylesheets

### Runtime
- Threading para operações pesadas
- Progresso em tempo real com workers
- UI responsiva sem travamentos
- Memória otimizada com lazy loading

### Tema
- Alternância instantânea (light ↔ dark)
- QSS compilado em cache
- Nenhuma recarga desnecessária
- Persistência em QSettings

---

## Segurança & Conformidade

### Validação
- Input validation em todos os campos
- XML parsing seguro
- Prevenção de injection
- Sanitização de dados

### Acessibilidade
- WCAG AA compliance (mínimo 4.5:1 contrast)
- Focus states visíveis
- Navegação por teclado completa
- Alto contraste em ambos os temas

### Auditoria
- Histórico completo de operações
- Logs detalhados (SQLite)
- Rastreamento de mudanças
- Exportação de relatórios

---

## Atualizações & Manutenção

### Auto-Update
- Verificação automática em background
- GitHub API para releases
- Download e instalação automáticos
- Notificação visual no top bar

### Versionamento
- Semântico: MAJOR.MINOR.PATCH.BUILD
- Atual: v1.0.1
- Histórico em git tags
- Release notes automáticos

---

## Requisitos do Sistema

### Mínimos
- Python 3.8+
- PySide6 6.x
- SQLite3
- macOS 10.13+ / Windows 10+ / Linux (moderno)

### Recomendados
- Python 3.10+
- 8GB RAM
- SSD para performance
- Resolução 1280x800+ (mas responsivo em menor)

---

## Licença & Créditos

Desenvolvido como aplicação corporativa moderna com:
- Interface: PySide6 (Qt para Python)
- Design: Minimal & Clean corporate aesthetic
- Versão: 1.0.1
- Status: Ativo e em manutenção

---

## Próximas Melhorias Planejadas

- [ ] Modo offline com sincronização quando online
- [ ] Integração com APIs externas
- [ ] Exportação de dados (CSV, JSON, PDF)
- [ ] Gráficos avançados (matplotlib/plotly)
- [ ] Dark mode automático baseado em preferências do SO
- [ ] Multi-idioma
- [ ] Temas customizáveis pelo usuário

---

*Última atualização: 2026-04-16*
*Versão: 1.0.1*
