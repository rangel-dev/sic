# Melhoria de UI: Padronização do Botão "Limpar Seleção" no Auditor

## 1. Contexto
Na interface atual do Módulo Auditor, os campos de upload de arquivos (**DropZones**) possuem comportamentos divergentes em relação à limpeza de dados. Enquanto os campos de "Catálogo" e "Excel" exibem um botão para limpar a seleção, o campo de **Pricebook XML** não oferece essa opção.

## 2. Diagnóstico
A análise técnica do componente `base_widgets.py` revelou que a exibição do botão de limpeza está vinculada à propriedade `multiple=True`. Como o Pricebook é configurado para aceitar apenas um arquivo por vez, o botão permanece oculto mesmo após o upload.

## 3. Requisitos de Melhoria

### 3.1 Unificação da Interface
- **Regra:** Todo componente de upload (`DropZone`) deve exibir o botão "✕ Limpar seleção" assim que houver pelo menos um arquivo carregado.
- **Independência de Modo:** O botão deve funcionar tanto para seleções únicas (Pricebook) quanto para seleções múltiplas (Catálogos e Excels).

### 3.2 Comportamento Esperado
1. O usuário seleciona ou arrasta um arquivo XML para o campo Pricebook.
2. O sistema exibe o nome do arquivo e o botão "✕ Limpar seleção" aparece logo abaixo.
3. Ao clicar em limpar, o componente volta ao estado inicial ("Arraste o arquivo aqui..."), permitindo uma nova seleção limpa.

## 4. Detalhes Técnicos (Implementação)

### 4.1 Componente Base
- **Arquivo:** `src/ui/components/base_widgets.py`
- **Componente:** `DropZone`
- **Local da alteração:** No método `_set_files`, a lógica de exibição do botão `self._btn_clear.show()` deve ser desvinculada da verificação `if self._multiple`.

### 4.2 Verificação de Estilo
- Garantir que o alinhamento central do botão de limpeza seja mantido em todos os estados para não quebrar o layout vertical da coluna de inputs.

## 5. Benefícios
- **Consistência Visual:** Todos os três inputs da linha superior terão o mesmo comportamento.
- **Usabilidade:** Redução de cliques e maior clareza para o usuário que deseja trocar um arquivo específico antes de rodar a auditoria.
