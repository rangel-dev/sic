"""Caminho de dados persistentes do usuário, fora da pasta de instalação.

BRD-012: não reutiliza o padrão de history_engine.py
(`Path(__file__).parent.parent.parent`) — dentro do executável empacotado
(modo onedir, sic.spec) esse caminho cai dentro da própria pasta de
instalação, sujeito a reinstalação, limpeza e falta de permissão de escrita
em instalações legadas no Program Files.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QStandardPaths

_APP_DIR_NAME = "SIC"


def user_data_dir(override: Optional[Path] = None) -> Path:
    """Pasta de dados persistentes do usuário, criando-a se necessário.

    `override` existe só para teste — nunca é usado em produção.
    """
    if override is not None:
        base = override
    else:
        location = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
        base = Path(location) if location else Path(os.environ.get("APPDATA", str(Path.home()))) / _APP_DIR_NAME
    base.mkdir(parents=True, exist_ok=True)
    return base


def data_file(name: str, override: Optional[Path] = None) -> Path:
    """Caminho de um arquivo dentro da pasta de dados do usuário."""
    return user_data_dir(override) / name
