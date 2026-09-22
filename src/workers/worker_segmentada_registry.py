"""Worker de gravação em segundo plano do registry das segmentadas (BRD-012, P2)."""
from __future__ import annotations

import traceback

from PySide6.QtCore import QThread, Signal

from src.core.segmentada_registry import RegistryStore, SegmentadaRecord


class SegmentadaRegistryWriteWorker(QThread):
    """Grava um registro fora da UI thread. Erro nunca é reportado à tela —
    o registro jamais pode impedir o trabalho (BRD-012, seção 8)."""

    finished = Signal()

    def __init__(self, store: RegistryStore, record: SegmentadaRecord, parent=None):
        super().__init__(parent)
        self._store = store
        self._record = record

    def run(self) -> None:
        try:
            self._store.upsert(self._record)
        except Exception:
            print(traceback.format_exc())
        finally:
            self.finished.emit()
