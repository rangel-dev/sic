# SIC — System Intelligence Commerce 🚀

Módulo de Inteligência Comercial e Auditoria de Catálogo para o ecossistema Natura & Avon.

Este software realiza a validação "Double-Blind" entre dados comerciais (Excel) e dados técnicos do Salesforce Commerce Cloud (XML), identificando divergências de preço, visibilidade, SEO e integridade de bundles.

## 🏗️ Estrutura do Projeto

O projeto segue uma arquitetura modularizada para facilitar a manutenção e escalabilidade:

```text
/ (Raiz)
├── main.py                 # Ponto de entrada (Bootstrap)
├── history.db              # Banco de dados de atividades
├── assets/                 # Recursos estáticos (Ícones, Logos)
└── src/                    # Código Fonte Principal
    ├── main_app.py         # Inicialização do QApplication e Temas
    ├── core/               # Motores de Cálculo e Regras de Negócio (Engines)
    ├── ui/                 # Camada de Interface (PySide6)
    │   ├── main_window.py  # Container principal e Navegação
    │   ├── pages/          # Visões/Telas completas do sistema
    │   ├── components/     # Widgets e UI Elements reutilizáveis
    │   └── styles/         # Definições de QSS (Temas Dark/Light)
    ├── workers/            # Processamento Assíncrono (QThreads)
    └── utils/              # Helpers e Utilitários de sistema
```

## 🚀 Como Executar

1. Certifique-se de ter o Python 3.9+ instalado.
2. Crie e ative um ambiente virtual:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   ```
3. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
4. Execute o aplicativo:
   ```bash
   python main.py
   ```

## 🛠️ Tecnologias Utilizadas

- **Interface**: PySide6 (Qt for Python)
- **Processamento de Dados**: Pandas, OpenPyxl
- **Processamento XML**: Lxml (etree)
- **Persistência**: SQLite3
- **Estilização**: QSS (Qt Style Sheets)

## 📖 Regras de Auditoria (v0.0.8)

O sistema valida atualmente 12 regras críticas:
- Divergência de Preço (DE/POR)
- Visibilidade em Listas de Vitrine
- Conflitos de Canal Minha Loja (ML)
- Margem de Segurança em categorias proibidas
- Erros Lógicos (POR > DE)
- Saúde de Bundles e Kits
- Cross-Brand (Natura vs Avon)
- Status Online/Offline
- Entre outros...

---
**Desenvolvido por RangelDev**
