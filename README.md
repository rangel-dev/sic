# 🏢 SIC — Sistema de Inteligência Corporativa

[![Version](https://img.shields.io/badge/version-1.1.4--beta-brightgreen.svg)](#)
[![Python](https://img.shields.io/badge/python-3.8+-green.svg)](#)
[![PySide6](https://img.shields.io/badge/pyside6-6.x-blue.svg)](#)
[![License](https://img.shields.io/badge/license-Proprietary-red.svg)](#)
[![Status](https://img.shields.io/badge/status-Active-brightgreen.svg)](#)

> Ferramenta desktop **interna** para as equipes de dados dos catálogos Natura, Avon e Minha Loja. Processa, audita e sincroniza arquivos de produtos estruturados (XML, Excel) — tudo **localmente**, sem enviar dados para servidores externos.

---

## 📋 Sumário Rápido

| Aspecto | Descrição |
|---------|-----------|
| **Tipo** | Aplicação Desktop (PySide6 / Python) |
| **Plataformas** | macOS 10.13+ / Windows 10+ / Linux moderno |
| **Banco de Dados** | SQLite local — sem servidor, sem nuvem |
| **Conexão externa** | Somente `api.github.com` para verificar atualizações (opcional) |
| **Startup** | ~2-3 segundos |
| **Módulos** | 8 (Início, Gerador, Sync, Auditor, Volumetria, Cadastro, Histórico, Configurações) |
| **Dados enviados para fora** | **Nenhum** |

---

## 🎯 O Que é o SIC?

O SIC é uma ferramenta de desktop desenvolvida internamente para apoiar as equipes de dados dos catálogos **Natura**, **Avon** e **Minha Loja**. Ela reúne em uma interface única as tarefas que antes eram feitas em planilhas ou scripts avulsos:

- ✅ **Processamento** de arquivos XML/Excel de catálogos com validação automática
- ✅ **Auditoria** de qualidade com detecção de inconsistências
- ✅ **Sincronização** entre múltiplas fontes de dados de produtos
- ✅ **Análise volumétrica** com estatísticas detalhadas
- ✅ **Rastreamento** completo com histórico de auditoria local
- ✅ **Interface** profissional com tema claro/escuro

Todo o processamento acontece na própria máquina do usuário. Os arquivos de catálogo não saem do computador.

---

## 🔒 Segurança & Transparência

> Esta seção existe especificamente para esclarecer o comportamento técnico do SIC a analistas de segurança, TI ou auditores que precisem avaliar o software.

### O que o SIC FAZ

| Ação | Detalhe |
|------|---------|
| Lê arquivos XML e Excel | Somente arquivos selecionados pelo usuário via diálogo de abertura |
| Grava `history.db` | SQLite na pasta da aplicação — registra quais operações foram feitas e quando |
| Consulta `api.github.com` | Uma requisição GET para verificar se há nova versão (sem enviar dados do usuário) |
| Baixa instalador (update) | Somente após **confirmação explícita do usuário**, do repositório `github.com/rangel-dev/sic` |
| Executa PowerShell (Windows) | Somente durante instalação de update confirmado pelo usuário (detalhado abaixo) |

### O que o SIC NÃO FAZ

- ❌ Não envia arquivos, dados de produtos ou informações do usuário para nenhum servidor
- ❌ Não coleta telemetria, analytics ou métricas de uso
- ❌ Não acessa arquivos fora do diretório selecionado pelo usuário
- ❌ Não se conecta a servidores internos da empresa
- ❌ Não criptografa dados do usuário (não há risco de ransomware)
- ❌ Não captura tela, não acessa câmera, não grava áudio
- ❌ Não modifica o registro do Windows (exceto durante instalação do update, pelo Inno Setup)
- ❌ Não persiste dados na nuvem

### Explicação das funcionalidades que podem parecer suspeitas

**Requisições de rede (`requests` + GitHub API)**
A única URL externa acessada é:
```
GET https://api.github.com/repos/rangel-dev/sic/releases/latest
```
O corpo da requisição não contém dados do usuário — é apenas uma consulta pública para comparar o número de versão. Pode ser desabilitado em Configurações → Auto-update.

**PowerShell com `-ExecutionPolicy Bypass`**
Executado exclusivamente durante uma atualização de versão, **iniciada e confirmada pelo usuário**. O script aguarda o processo principal fechar, exibe uma janela de progresso e então executa o instalador `.exe` baixado do GitHub. Este é o método recomendado pela Microsoft para instaladores sem elevação UAC (`PrivilegesRequired=lowest` no Inno Setup). O código-fonte do script está em `src/core/update_service.py`, linha ~470.

**Remoção do `Zone.Identifier` (Mark of the Web)**
O Windows marca arquivos baixados da internet com um Alternate Data Stream (`Zone.Identifier`). Sem removê-lo, o SmartScreen e o AppLocker bloqueiam a execução do instalador em ambientes corporativos. O VS Code, Slack, Zoom e qualquer outro software com auto-update legítimo fazem o mesmo. O código está em `src/core/update_service.py`, função `_unblock_file()`.

**`src/core/_secret.py` (OBFUSCATED_KEY)**
Este arquivo contém um token de acesso ao repositório privado do GitHub, gerado automaticamente pelo script de build. O comentário na primeira linha diz explicitamente `# Auto-generated file by build script. DO NOT COMMIT.` — ele foi adicionado ao repositório por engano e o `.gitignore` deve ser atualizado para excluí-lo. O token é usado exclusivamente para autenticação na API do GitHub ao verificar releases de repositórios privados.

**OCR (`pytesseract` + `Pillow`)**
Processa imagens de catálogos de produtos fornecidas pelo usuário para extrair texto de campos como descrição e código de item. Não captura tela, não acessa câmera e não processa imagens fora dos arquivos selecionados pelo usuário.

**Banco de dados SQLite (`history.db`)**
Armazena o histórico de operações: qual arquivo foi processado, em que momento, qual foi o resultado. Fica na pasta da aplicação e não é transmitido para nenhum lugar. Pode ser inspecionado com qualquer cliente SQLite (ex: DB Browser for SQLite).

---

## 🖥️ Para o Departamento de TI

### Regras de firewall necessárias

O SIC só precisa de acesso externo se o **auto-update estiver habilitado** (padrão: habilitado, mas configurável). Se preferir bloquear completamente o acesso à rede, desabilite o auto-update nas Configurações — o software continua funcionando normalmente.

Se quiser manter o auto-update ativo, libere apenas:

| Destino | Porta | Protocolo | Finalidade |
|---------|-------|-----------|-----------|
| `api.github.com` | 443 | HTTPS | Verificar versão disponível |
| `github.com` | 443 | HTTPS | Baixar instalador (somente ao atualizar) |
| `objects.githubusercontent.com` | 443 | HTTPS | CDN de assets do GitHub (download do `.exe`) |

Nenhuma outra conexão de rede é feita.

### Como desabilitar o auto-update

1. Abra o SIC
2. Clique na aba **Configurações** ⚙️
3. Desmarque **"Verificar atualizações automaticamente"**

Com isso desabilitado, o SIC não faz nenhuma conexão de rede.

### Permissões necessárias

O SIC **não requer** privilégios de administrador para rodar. A instalação padrão (via Inno Setup com `PrivilegesRequired=lowest`) é feita na pasta do usuário (`%LOCALAPPDATA%\SIC`), sem tocar em `Program Files` nem em chaves de registro protegidas.

Se o SIC estiver instalado em `Program Files` por uma instalação legada com admin, o auto-update exibirá uma mensagem pedindo ao usuário que solicite ao TI a desinstalação da versão antiga.

### Arquivos gravados pelo app

| Arquivo | Local | Conteúdo |
|---------|-------|---------|
| `history.db` | Pasta da aplicação | Log de operações (SQLite) |
| `SIC_Suite.conf` | `%APPDATA%\SIC\` (Windows) ou `~/.config/SIC/` (macOS) | Preferências do usuário (tema, fonte, auto-update on/off) |
| `sic_update_python.log` | `%TEMP%` | Log de update (gravado somente durante atualização) |

### Auditoria do código-fonte

O código-fonte completo está disponível no repositório interno. Qualquer linha de código que faz requisição de rede está em `src/core/update_service.py`. O restante do código processa apenas arquivos locais.

---

## ✨ Módulos

| # | Módulo | Funcionalidade |
|---|--------|----------------|
| 1 | 🏠 **Início** | Dashboard com KPIs e status do sistema |
| 2 | 🔧 **Gerador** | Upload, validação e transformação de arquivos de catálogo |
| 3 | 🔄 **Sync** | Sincronização entre múltiplas fontes de dados de produtos |
| 4 | 📊 **Auditor** | Detecção automática de inconsistências e problemas de qualidade |
| 5 | 📈 **Volumetria** | Estatísticas, métricas e análises de volume |
| 6 | 📝 **Cadastro** | Gestão e manutenção de dados estruturados |
| 7 | 📅 **Histórico** | Auditoria completa de todas as operações (local) |
| 8 | ⚙️ **Configurações** | Tema, fonte, auto-update e preferências |

---

## 🚀 Instalação & Execução

### Opção 1: Executável (Recomendado para usuários finais)

Baixe o instalador na página de [Releases](https://github.com/rangel-dev/sic/releases) e execute. Não requer Python instalado, não requer privilégios de administrador.

### Opção 2: Código-Fonte (Para desenvolvedores)

```bash
# Clone o repositório
git clone https://github.com/rangel-dev/sic.git
cd sic

# Crie e ative um ambiente virtual
python -m venv venv
source venv/bin/activate          # macOS/Linux
# venv\Scripts\activate           # Windows

# Instale dependências
pip install -r requirements.txt

# Execute
python -m src.main_app
```

---

## 🏗️ Arquitetura & Fluxo de Dados

```
┌──────────────────────────────────────────────────────┐
│                   Máquina do Usuário                  │
│                                                       │
│  [Arquivos XML/Excel] ──► [SIC Desktop App]          │
│         (catálogos)              │                    │
│                                  ▼                    │
│                          [history.db]                 │
│                         (SQLite local)                │
│                                                       │
└──────────────────────────────────────────────────────┘
                              │
                              │ HTTPS GET (somente versão)
                              │ Nenhum dado do usuário enviado
                              ▼
                    api.github.com/repos/
                    rangel-dev/sic/releases/latest
```

```
┌─────────────────────────────────────┐
│     SIC — Camadas da Aplicação      │
├─────────────────────────────────────┤
│  UI Layer (PySide6)                 │
│  ├─ Janela principal                │
│  ├─ 8 módulos (views)               │
│  └─ Temas claro/escuro (QSS)        │
├─────────────────────────────────────┤
│  Business Logic (Python)            │
│  ├─ Auditor Engine                  │
│  ├─ Generator Engine                │
│  ├─ Sync Engine                     │
│  └─ Volumetry Engine                │
├─────────────────────────────────────┤
│  Data Layer                         │
│  ├─ SQLite (history.db — local)     │
│  └─ File System (arquivos do usuário│
└─────────────────────────────────────┘
```

---

## 🛠️ Stack Técnico

| Camada | Tecnologia | Finalidade |
|--------|-----------|-----------|
| UI | PySide6 (Qt para Python) | Interface gráfica desktop |
| Estilo | QSS (Qt Stylesheets) | Temas claro e escuro |
| Processamento | Python + Pandas | Manipulação de dados estruturados |
| Planilhas | openpyxl | Leitura/escrita de arquivos Excel |
| XML | lxml | Parsing e validação de XMLs de catálogo |
| OCR | pytesseract + Pillow | Extração de texto de imagens de produtos |
| Banco local | SQLite3 (stdlib) | Histórico de operações |
| Updates | requests + GitHub API | Verificação de nova versão (opcional) |
| Empacotamento | PyInstaller + Inno Setup | Geração do instalador `.exe` |

---

## ⚙️ Configuração Rápida

Após iniciar a aplicação:

1. **Tema:** Clique no ícone ◑ (canto superior direito) para alternar claro/escuro
2. **Fonte:** Configurações ⚙️ → ajuste tamanho (11-18px)
3. **Auto-update:** Configurações → ativar/desativar (desabilitar remove toda conexão de rede)
4. **Módulos:** Clique nas abas no topo para navegar

As preferências são salvas automaticamente.

---

## 🐛 Troubleshooting

**App não abre**
```bash
python -m src.main_app
```

**Erro `ModuleNotFoundError`**
```bash
pip install --upgrade PySide6
```

**Tema não muda**
Apague o arquivo de configuração:
- macOS/Linux: `~/.config/SIC/SIC_Suite.conf`
- Windows: `%AppData%\SIC\SIC_Suite.conf`

**Update falhou em rede corporativa**
O SIC exibe uma mensagem de erro com o diagnóstico. Se o proxy/firewall corporativo bloquear `api.github.com`, desabilite o auto-update nas Configurações — o app continua funcionando normalmente sem acesso à internet.

---

## 📖 Documentação

| Documento | Descrição |
|-----------|-----------|
| **README.md** (este) | Visão geral, segurança e instalação |
| **PROJETO.md** | Arquitetura e motivação do projeto |
| **MANUAL.md** | Como usar cada módulo (passo a passo) |
| **JORNADA.md** | Histórico de desenvolvimento |
| **FLUXO_TRABALHO.md** | Git Flow e processo de release |

---

## 📈 Estatísticas

| Métrica | Valor |
|---------|-------|
| Linhas de Código | ~8.500+ |
| Módulos | 8 |
| Temas | 2 (claro/escuro, WCAG AA) |
| Plataformas | macOS, Windows, Linux |
| Conexões externas | 1 (GitHub API, opcional) |

---

## 📝 Changelog

**v1.1.4-beta** — atual
- Correções de bugs e melhorias de estabilidade

**v1.0.x**
- Lançamento inicial com os 8 módulos funcionais
- Auto-update via GitHub Releases
- Suporte a temas claro e escuro (WCAG AA)

---

**Versão:** 1.1.4-beta
**Status:** ✅ Ativo e em manutenção
**Repositório:** [github.com/rangel-dev/sic](https://github.com/rangel-dev/sic)

Para dúvidas de uso, consulte [MANUAL.md](MANUAL.md). Para arquitetura, consulte [PROJETO.md](PROJETO.md).
