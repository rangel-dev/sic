# SIC — System Intelligence Commerce 🚀

Módulo de Inteligência Comercial e Auditoria de Catálogo Omnichannel.

Este software realiza a auditoria avançada entre dados comerciais (planilhas de precificação e listas) e dados técnicos do Salesforce Commerce Cloud (catálogos e pricebooks de múltiplas marcas), identificando divergências de preço, visibilidade, SEO e integridade de bundles de forma automática e veloz.

## 🏗️ Estrutura do Projeto

O projeto segue uma arquitetura modularizada utilizando o Padrão de Integridade Computacional (Core Selado) para facilitar a manutenção e proteger a governança:

```text
/ (Raiz)
├── main.py                 # Ponto de entrada (Bootstrap)
├── history.db              # Banco de dados de atividades SQLite
├── assets/                 # Recursos estáticos (Ícones, Logos)
└── src/                    # Código Fonte Principal
    ├── main_app.py         # Inicialização do QApplication e Temas
    ├── core/               # Motores de Cálculo e Regras de Negócio (Engines)
    │   └── auditor/        # Módulo de Auditoria com Core Validado (Anti-Tampering)
    ├── ui/                 # Camada de Interface Nativa Desktop (PySide6)
    │   ├── main_window.py  # Container principal e Navegação
    │   ├── pages/          # Visões/Telas completas do sistema
    │   ├── components/     # Widgets e UI Elements reutilizáveis (Cards Dinâmicos)
    │   └── styles/         # Definições de StyleSheet (Temas Dark/Light)
    ├── workers/            # Processamento Assíncrono (QThreads para evitar travamento UI)
    └── utils/              # Helpers e Utilitários de sistema estático
```

## 🚀 Como Executar

1. Certifique-se de ter o Python 3.9+ instalado: `python --version`
2. Crie e ative o ambiente virtual dedicado:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # em macOS/Linux
   # ou .venv\Scripts\activate no Windows
   ```
3. Instale as dependências requisitadas para UI e Engenharia de Dados:
   ```bash
   pip install -r requirements.txt
   ```
4. Execute o aplicativo nativo:
   ```bash
   python main.py
   ```

## 🛠️ Tecnologias Utilizadas

- **Interface Desktop e Multithreading**: PySide6 (Qt for Python v6)
- **Manipulação de Séries e Estatísticas**: Pandas
- **Engenharia de Arquivos Excel**: OpenPyxl
- **Análise Profunda XML (C-Engine)**: Lxml (etree)
- **Aceleração**: Integridade em SHA-256 (Módulo Core Hashing)

## 📖 Regras de Auditoria (v11.6 Parity)

O sistema conta com um Kernel criptograficamente selado que valida instantaneamente as 12 principais regras e conflitos estruturais de catálogo de e-commerce e venda direta digital:

- **Divergência de Preço (DE/POR):** Compara preços comerciais planejados contra XMLs gerados.
- **Visibilidade em Listas de Vitrine:** Garante que o SKU mapeado estará online nas Listas Corretas.
- **Conflitos de Canal Multimarca (ex: Minha Loja):** Audita canibalização de canais de promotores independentes.
- **Margem de Segurança:** Valida se a precificação estourou políticas nas categorias proibidas para descontos agressivos.
- **Erros Lógicos:** Identifica fendas sistêmicas de formatação (Ex: POR > DE, ausência de valores).
- **Saúde de Bundles e Kits:** Invalida venda de conjuntos quando um dos componentes perdeu o preço ou estoque sistêmico.
- **Cross-Brand:** Proteção absoluta contra vazamento do catálogo de uma Marca principal para as URLs/arquivos de outra marca coligada.
- **Indexação Limpa (Searchable):** Garantia de SEO orgânico, verificando se o item oculto na verdade deveria estar respondendo organicamente no site.

---
**Desenvolvido por RangelDev**
