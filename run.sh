#!/bin/zsh
# Script de execução do SIC para macOS
# Define o QT_QPA_PLATFORM_PLUGIN_PATH automaticamente a partir do venv ativo.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON="$SCRIPT_DIR/.venv/bin/python"

if [ ! -f "$PYTHON" ]; then
    echo "❌  .venv não encontrado. Execute: python3 -m venv .venv && pip install -r requirements.txt"
    exit 1
fi

# Resolve o caminho do PySide6 dinamicamente para não depender de versão ou usuário
PYSIDE6_DIR=$("$PYTHON" -c "import PySide6, os; print(os.path.dirname(PySide6.__file__))")
export QT_QPA_PLATFORM_PLUGIN_PATH="$PYSIDE6_DIR/Qt/plugins/platforms"
export DYLD_FRAMEWORK_PATH="$PYSIDE6_DIR/Qt/lib"

exec "$PYTHON" "$SCRIPT_DIR/main.py" "$@"
