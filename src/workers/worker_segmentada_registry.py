"""Worker de gravação em segundo plano do registry das segmentadas (BRD-012, P2/P5)."""
from __future__ import annotations

import traceback
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QThread, Signal

from src.core.segmentada_registry import RegistryStore, SegmentadaRecord, write_xlsx_snapshot


class SegmentadaRegistryWriteWorker(QThread):
    """Grava um registro fora da UI thread, em uma ou mais fontes (local e,
    se configurada, a pasta compartilhada — P5). Erro em qualquer uma nunca
    é reportado à tela nem impede as demais — o registro jamais pode
    impedir o trabalho (BRD-012, seção 8).

    `xlsx_source`/`xlsx_path`, quando informados, regeram o `.xlsx` de
    leitura na pasta compartilhada a partir do estado atual dessa fonte
    (depois do upsert), para refletir o registro recém-gravado.
    """

    finished = Signal()

    def __init__(
        self,
        stores: list[RegistryStore],
        record: SegmentadaRecord,
        parent=None,
        xlsx_source: Optional[RegistryStore] = None,
        xlsx_path: Optional[Path] = None,
    ):
        super().__init__(parent)
        self._stores = stores
        self._record = record
        self._xlsx_source = xlsx_source
        self._xlsx_path = xlsx_path

    def run(self) -> None:
        for store in self._stores:
            try:
                store.upsert(self._record)
            except Exception:
                print(traceback.format_exc())

        if self._xlsx_source is not None and self._xlsx_path is not None:
            try:
                write_xlsx_snapshot(self._xlsx_source.load(), self._xlsx_path)
            except Exception:
                print(traceback.format_exc())

        self.finished.emit()
