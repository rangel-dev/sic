"""Worker de consulta de tarefa no Runrun.it, fora da UI thread (BRD-012, Etapa 5/P6)."""
from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from src.core.runrun_client import RunrunClient, RunrunUnavailable


class RunrunTaskFetchWorker(QThread):
    """Consulta uma tarefa e emite o resultado. Nunca levanta exceção pra
    fora — falha vira `error` com uma mensagem, tratada como discreta pela
    tela (CA-22/CA-23): o campo continua utilizável de qualquer jeito."""

    finished = Signal(object)  # RunrunTask
    error = Signal(str)

    def __init__(self, client: RunrunClient, number: str, parent=None):
        super().__init__(parent)
        self._client = client
        self._number = number

    def run(self) -> None:
        try:
            task = self._client.get_task(self._number)
        except RunrunUnavailable as exc:
            self.error.emit(str(exc))
            return
        self.finished.emit(task)
