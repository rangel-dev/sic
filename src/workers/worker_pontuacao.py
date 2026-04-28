"""Worker thread for the Pontuação auditor module."""
from PySide6.QtCore import QThread, Signal

from src.core.pontuacao_engine import PontuacaoEngine, PontuacaoResult


class PontuacaoWorker(QThread):
    progress  = Signal(int, str)
    finished  = Signal(object)   # PontuacaoResult
    error_msg = Signal(str)

    def __init__(self, ciclo_ref: int, grade_path: str, gcp_path: str, parent=None):
        super().__init__(parent)
        self._ciclo_ref  = ciclo_ref
        self._grade_path = grade_path
        self._gcp_path   = gcp_path

    def run(self) -> None:
        engine = PontuacaoEngine(progress_callback=self._on_progress)
        result: PontuacaoResult = engine.run(self._ciclo_ref, self._grade_path, self._gcp_path)
        if result.error:
            self.error_msg.emit(result.error)
        else:
            self.finished.emit(result)

    def _on_progress(self, percent: int, message: str) -> None:
        self.progress.emit(percent, message)
