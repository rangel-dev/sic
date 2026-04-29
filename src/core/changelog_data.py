"""
Dados estáticos do módulo Sobre: colaboradores e histórico de versões.
Para registrar uma nova versão, adicione uma entrada no início de CHANGELOG.
"""

CONTRIBUTORS = [
    {
        "name": "Edgar Galdino",
        "role": "Fundador & Arquiteto das Regras de Negócio",
        "icon": "◈",
        "color": "#FF8050",
        "bio": (
            "Criou o projeto original — uma aplicação web completa em HTML e JavaScript "
            "que ficou conhecida como Pricing Master V11.6. Toda a lógica de negócio do "
            "Auditor, Gerador e outros módulos nasceu do seu profundo conhecimento das "
            "regras de precificação. Hoje atua como consultor: valida regras, reporta "
            "bugs e orienta evoluções do produto."
        ),
        "legacy": "O código original está preservado em archive/legacy/",
    },
    {
        "name": "Marcos Rangel",
        "role": "Engenheiro de Software & Tech Lead",
        "icon": "⬡",
        "color": "#BB88FF",
        "bio": (
            "Identificou que o projeto poderia ganhar muito mais escala com Python e propôs "
            "a migração. Assumiu toda a arquitetura técnica: escolha de framework (PySide6), "
            "design visual, sistema de cores, versionamento semântico, CI/CD e a infraestrutura "
            "de código. Responsável por transformar as regras de negócio do Edgar em módulos "
            "Python robustos e escaláveis."
        ),
        "legacy": None,
    },
    {
        "name": "Jéssica Generoso",
        "role": "Colaboradora — Módulo Cadastro",
        "icon": "◎",
        "color": "#60a5fa",
        "bio": (
            "Desenvolveu um script em HTML/JS para apoiar o seu próprio processo de trabalho "
            "no Cadastro. Ao compartilhá-lo com Marcos, contribuiu diretamente para a criação "
            "do módulo Cadastro — uma área construída a partir da sua necessidade real de trabalho."
        ),
        "legacy": None,
    },
]

# Entradas do changelog: lista do mais recente para o mais antigo.
# type: "feat" | "fix" | "chore"
CHANGELOG = [
    {
        "version": "1.1.0",
        "date": "Abril 2026",
        "entries": [
            ("feat", "Novo Módulo de Cadastro: Agora você pode validar Kits e Pontuações cruzando suas planilhas diretamente com os dados do Salesforce."),
            ("feat", "Auditor Transparente: O motor de auditoria agora permite rastrear e exportar todos os acertos, e não apenas as divergências."),
            ("feat", "Gerador Inteligente: Identificação automática de marca e slot único para upload — o sistema faz o trabalho pesado para você."),
            ("fix",  "Segurança em Primeiro Lugar: Implementamos travas que impedem o uso de arquivos antigos ou o upload duplicado de marcas."),
        ],
    },
    {
        "version": "1.0.8",
        "date": "Março 2026",
        "entries": [
            ("feat", "Auditoria Expandida: Novas regras de validação para categorias restritas e melhorias visuais nas tabelas de resultados."),
            ("fix",  "Interface Ajustada: Corrigimos pequenos problemas visuais no DropZone para uma experiência de arrastar e soltar mais fluida."),
        ],
    },
    {
        "version": "1.0.0",
        "date": "Fevereiro 2026",
        "entries": [
            ("feat", "O SIC está de cara nova! Interface moderna com suporte a temas Claro e Escuro para melhor conforto visual."),
            ("feat", "Atualizações Automáticas: Nunca mais se preocupe em baixar novas versões; o sistema cuida de tudo para você."),
            ("perf", "Performance Turbo: Reduzimos o tempo de abertura do programa em 3 segundos através de carregamento inteligente."),
        ],
    },
    {
        "version": "0.1.0",
        "date": "Novembro 2025",
        "entries": [
            ("feat", "Lançamento Oficial: O SIC nasce como o centro de comando para precificação e catálogo no Salesforce Commerce Cloud."),
            ("feat", "Dashboard Integrado: Acompanhe sua atividade recente e acesse todos os módulos em um só lugar."),
            ("feat", "Motor de Auditoria: Validação automática de preços e consistência de dados com máxima precisão."),
        ],
    },
]
