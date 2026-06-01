# 📐 ESPECIFICAÇÃO DE MELHORIA: REESTRUTURAÇÃO DO LAYOUT DO AUDITOR E BARRA DE AÇÕES
**De:** Edgar Santos (Arquiteto de Regras de Negócio)  
**Para:** Marcos Rangel (Desenvolvedor Core)  
**Objetivo:** Adaptar a interface do Módulo Auditor para notebooks de 14 polegadas (resolução HD 1366x768), resolvendo gargalos de espaço vertical, corrigindo clipping de botões e reintegrando as ferramentas de governança de compliance que ficaram ocultas.

---

## 1. Contexto e Justificativa de Negócio
A grande maioria dos analistas de Pricing utiliza notebooks corporativos de no máximo 14 polegadas com resoluções HD (1366x768) ou Full HD com escala de zoom ativa. O cabeçalho atual do Módulo Auditor e a disposição em splitters rígidos consomem espaço vertical excessivo, gerando o fenômeno do **"Scroll Inception"** (múltiplas barras de rolagem internas espremidas na tela).

Ao rodar uma auditoria volumosa, o usuário fica incapacitado de ler a tabela de divergências e o diagnóstico estratégico da IA de forma integrada, sendo forçado a micro-ajustar as divisórias móveis a cada execução. Esta especificação propõe uma reestruturação baseada em **Rolagem Global Contínua** associada à **Liberdade de Ajuste por Splitters** e rolagens secundárias integradas.

---

## 2. Minimalismo e Ganho de Espaço Vertical

### 2.1 Cabeçalho Compacto e Minimalista
- **Redução de Ruído:** O cabeçalho de seção (`SectionHeader`) deve ser compactado de "Auditor - Motor de Auditoria - Double-Blind Price Validation" para apenas **"Auditor - Motor de Auditoria"**.
- **Remoção de Subtítulo:** Eliminar as descrições redundantes logo abaixo do título para recuperar ~30px de espaço vertical útil.
- **Fontes Proporcionais:** Ajustar o tamanho da fonte do título principal para que fique elegante e não domine o topo do viewport.

### 2.2 DropZones Otimizados (Inputs Compactos)
- **Altura Reduzida:** Diminuir a altura padrão dos três DropZones de arquivos (Pricebook XML, Catálogos XML, Excel) para que ocupem menos espaço no carregamento inicial.
- **Identificação Clara:** Manurar margens e paddings internos para que, mesmo compactos, os DropZones mostrem com clareza o status de carregamento, o ícone da marca e os nomes dos arquivos importados.

---

## 3. A Nova Proposta de Layout: Rolagem Global Mestre com Ajuste Livre

A proposta substitui o aprisionamento rígido dos componentes na altura física da janela por um **viewport de Rolagem Mestre Global**, mantendo a autonomia do analista em personalizar as alturas através de splitters móveis.

```
+---------------------------------------------------------------------------------+  |
| 1. CABEÇALHO COMPACTADO ("Auditor - Motor de Auditoria")                        |  |
+---------------------------------------------------------------------------------+  |
|                                                                                 |  |
|  2. ZONA DE ENTRADA (3 DropZones otimizados em altura)                          |  |
|                                                                                 |  |
|  3. BARRA DE AÇÕES DA CAMPANHA                                                  |  |
|     * [✓ Executar] [Limpar] | MARCA: (Todos) [Natura] [Avon]                    |  |
|                                                                                 |  |
|  4. PAINEL DE RESULTADOS (Dentro de QScrollArea Principal)                      |  |
|     |                                                                           |  v ROLAGEM
|     |-- === DIVISOR AJUSTÁVEL (Splitter Superior) ========================== --|  | GLOBAL
|     |   * O usuário pode arrastar para dar mais/menos espaço aos cards.         |  | MESTRE
|     |   [ GRID DE CARDS DE ERROS ENCONTRADOS ]                                  |  | (Scroll)
|     |                                                                           |  |
|     |-- === DIVISOR AJUSTÁVEL (Splitter do Meio) =========================== --|  |
|     |   * Ajuste fino de tamanho para a tabela.                                 |  |
|     |   [ TABELA DE DIVERGÊNCIAS DETALHADAS ]                                   |  |
|     |   * Rolagem interna ativa para navegar em mais de 20 linhas de erros.     |  |
|     |                                                                           |  |
|     |-- === DIVISOR AJUSTÁVEL (Splitter Inferior) ========================== --|  |
|     |   * Ajuste fino de tamanho para o diagnóstico de IA.                      |  |
|     |   [ DIAGNÓSTICO ESTRATÉGICO IA (HTML) ]                                   |  |
|     |   * Rolagem interna ativa para leitura de textos longos.                  |  |
|     |                                                                           |  |
|     |-- [ 4.4 NOVO PAINEL DE GOVERNANÇA E CERTIFICAÇÃO (COMPLIANCE) ]           |  |
|         * Posicionamento físico dos botões de exportação esquecidos na UI.      |  |
|                                                                           |      |
+---------------------------------------------------------------------------------+  v
```

### 🌟 Diferenciais da Usabilidade Proposta (O Melhor dos Dois Mundos):
* **Rolagem Mestre (Global):** Garante a mobilidade de toda a página de resultados. Se o conjunto de blocos expandido for maior do que o monitor de 14", o usuário simplesmente gira a roda do mouse para navegar verticalmente de forma fluida. As DropZones saem da tela dando **100% de tela útil** para a análise dos resultados.
* **Ajuste Livre (Splitters):** O analista preserva a liberdade absoluta de redimensionar o tamanho de cada bloco (Cards, Tabela, IA) individualmente, conforme sua necessidade de foco.
* **Rolagem nos Blocos (Concorrente):** Se a tabela contiver 500 linhas ou se o diagnóstico da IA for muito longo, a **rolagem interna desses componentes continua existindo**, servindo como uma navegação de suporte dentro do tamanho que o usuário arbitrou no splitter.

---

## 4. Correção e Padronização da Barra de Ações (Action Bar)

A barra de ações intermediária (`_action_bar`) sofre hoje com clipping de botões em janelas menores e alinhamentos irregulares. Além disso, as opções de exportação avançada de compliance foram esquecidas fora do layout.

### 4.1 Reintegração dos Botões de Compliance Ocultos
O Rangel implementou toda a inteligência e controle de estado para duas rotinas fundamentais, mas esqueceu de colocá-las fisicamente na interface:
1. **`self._btn_master_cert` ("Emitir Certificado PDF"):** Gera o Certificado de Conformidade oficial, que deve ficar visível e só habilitar quando o total de erros na auditoria for estritamente zero (`total == 0`).
2. **`self._btn_export_full` ("Exportar Evidências Master"):** Gera a planilha Excel estilizada com a trilha completa de conformidade (sucessos + divergências) da aba `EVIDENCIAS_MASTER`.

* **Melhoria:** Estes dois botões devem ser criados na interface gráfica. A sugestão é colocá-los em uma nova seção na base da página de resultados chamada **"Conformidade e Certificação (Compliance)"** ou de forma elegante na barra de ferramentas.

### 4.2 Ajuste de Layout da Barra de Ações (Anti-Clipping)
- **QHBoxLayout Responsivo:** A linha de ações deve usar um `QHBoxLayout` com espaçamento rigoroso de `8px`.
- **Botão do Google Chat:** O botão "Enviar ao Google Chat" (`self._btn_webhook`) deve possuir uma largura mínima garantida ou recolher-se para um ícone minimalista em telas HD para evitar empurrar os demais botões para fora do visor.

---

## 5. Instruções Técnicas para o Desenvolvedor (Rangel)

1. **SectionHeader:** Modificar o construtor de `SectionHeader` em `view_auditor.py` para exibir apenas o título limpo "Auditor - Motor de Auditoria" e retirar descrições secundárias que tomem espaço útil.
2. **QScrollArea no Widget Principal:**
   * Envelopar o layout principal da página de resultados (toda a região abaixo da barra de ações) em um `QScrollArea`.
   * Configurar `scroll_area.setWidgetResizable(True)` para garantir a fluidez de redimensionamento e evitar o travamento físico do tamanho da janela.
3. **Preservar os Splitters com Alturas Dinâmicas:**
   * **Não eliminar os QSplitter.** O Rangel deve manter `self._splitter` e `self._bottom_splitter`, mas garantir que eles não fiquem atrelados a tamanhos fixos limitados pelo tamanho do monitor físico.
   * Quando o analista redimensionar um bloco via splitter de modo que a soma total de alturas estoure o viewport, a barra de rolagem global do `QScrollArea` entra em ação automaticamente.
4. **Instanciar Botões Esquecidos:**
   * Inserir no construtor de UI a instanciação física e posicionamento de:
     ```python
     self._btn_export_full = QPushButton("📊 Exportar Evidências Master")
     self._btn_master_cert = QPushButton("⚙️ Emitir Certificado PDF")
     self._cert_status_lbl = QLabel("")
     ```
   * Adicionar estes elementos de forma organizada e estilizada na base do módulo, garantindo que as chamadas de conexões que o Rangel já implementou em `_clear` e `_on_finished` funcionem visualmente na tela.

---

## 6. Impacto Esperado
* **Visual Premium e Organizado:** Interface com cara de suite empresarial topo de linha, alinhada com as melhores práticas de usabilidade moderna.
* **Liberdade de Foco:** O analista consegue equilibrar a visualização da tela rodando o scroll mestre para ocultar as DropZones, enquanto usa as divisórias livres para focar no dado de seu interesse.
* **Compliance Transparente:** O analista ganha visibilidade instantânea de que o sistema emite certificados PDF e gera relatórios de governança completos de sucesso.
