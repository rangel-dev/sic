Além disso, a barra de ações superior sofre com problemas de "clipping", e o cabeçalho atual consome espaço vertical excessivo que poderia ser utilizado para a visualização dos dados.

## 2. Minimalismo e Ganho de Espaço Vertical

### 2.1 Cabeçalho Compacto
- **Alteração de Texto:** Substituir o título longo por "Auditor - Motor de Auditoria".
- **Redução de Fonte:** Aplicar um tamanho de fonte menor para o título.
- **Remoção de Subtítulo:** Eliminar a descrição secundária que aparece abaixo do título principal para ganhar aproximadamente 20-30px de altura.

### 2.2 DropZones Otimizados
- **Altura Reduzida:** Diminuir a altura mínima dos campos de upload (DropZones).
- **Visibilidade:** Garantir que, mesmo menores, o nome do arquivo selecionado e o ícone de status permaneçam claros para o usuário.

## 3. Nova Estrutura de Layout (Tri-Linear)
A proposta é transformar o layout "Dashboard + Detalhes" em um fluxo **linear vertical**, onde cada seção ocupa a largura total disponível, garantindo foco e clareza.

### 2.1 Bloco 1: Dashboard de Erros (Topo)
- **Posicionamento:** Primeira seção após os inputs de arquivos.
- **Formato:** Grid horizontal de `ErrorCard` tiles.
- **Comportamento:** Ocupará a largura total, permitindo uma visão panorâmica imediata de todos os 12 checks de auditoria.

### 2.2 Bloco 2: Lista de Divergências (Meio)
- **Posicionamento:** Logo abaixo dos cards de erro.
- **Formato:** `QTableWidget` de largura total.
- **Benefício:** Aumento significativo no espaço para as colunas "Detalhe" e "Impacto", reduzindo a necessidade de scroll horizontal na tabela.

### 2.3 Bloco 3: Diagnóstico Estratégico IA (Base)
- **Posicionamento:** Seção final do relatório.
- **Formato:** Painel de texto formatado (HTML) ocupando a base do módulo.
- **Benefício:** Leitura mais confortável do contexto gerado pela IA, assemelhando-se a um relatório técnico impresso.

## 3. Refinamento da Barra de Ações e Responsividade
Para resolver o problema de botões cortados e o alinhamento "torto", serão aplicadas as seguintes melhorias:

### 3.1 Layout Flexível
- **Regra:** A `action_row` deve permitir o ajuste dos botões conforme a largura da janela.
- **Implementação:** Uso de `QHBoxLayout` com espaçamentos padronizados (`setSpacing(8)`) e, se necessário, agrupamento de funções secundárias (Exportar/Webhook) em um submenu ou layout que quebre linhas (Wrapping).

### 3.2 Padronização de Botões
- **Estética:** Todos os botões na linha de ação devem seguir a mesma altura e estilo de borda/padding para eliminar a percepção de desalinhamento.
- **Botão Google Chat:** Garantir que o botão "Enviar ao Google Chat" possua uma largura mínima garantida ou um ícone representativo que economize espaço sem perder a funcionalidade.

## 5. Requisitos Técnicos
1. **SectionHeader:** Modificar o construtor do `SectionHeader` na `AuditorView` para passar apenas o novo título curto e omitir a descrição.
2. **DropZone Styling:** Ajustar o `fixedHeight` ou as margens internas do componente `DropZone` para reduzir seu "footprint" vertical.
3. **QSplitter:** Alterar a orientação dos splitters principais para `Qt.Vertical` em toda a hierarquia de resultados.
4. **Scroll Management:** Garantir que o `QScrollArea` principal envolva toda a estrutura para que o usuário possa navegar pelo relatório completo de forma fluida.
5. **Alignment:** Revisar os `margins` e `spacings` de todos os `QHBoxLayout` para garantir simetria visual.

## 6. Impacto Esperado
- Interface mais profissional e organizada (Look & Feel premium).
- Foco total nos resultados: o usuário vê mais erros na tela sem precisar dar scroll.
- Compatibilidade com notebooks de resolução 1366x768 e telas ultra-wide.
- Fluxo de trabalho mais intuitivo: Identificação (Card) -> Análise (Tabela) -> Conclusão (IA).
