"""Worker thread for the Conversor Biosphera module."""
from PySide6.QtCore import QThread, Signal

from src.core.conversor_engine import ConversorEngine, ConversorResult


class ConversorWorker(QThread):
    progress  = Signal(int, str)
    finished  = Signal(object)   # ConversorResult
    error_msg = Signal(str)

    def __init__(self, ciclo_base: int, aud_path: str, rev_path: str, grade_path: str, parent=None):
        super().__init__(parent)
        self._ciclo_base = ciclo_base
        self._aud_path   = aud_path
        self._rev_path   = rev_path
        self._grade_path = grade_path

    def run(self) -> None:
        engine = ConversorEngine(progress_callback=self._on_progress)
        result: ConversorResult = engine.run(self._ciclo_base, self._aud_path, self._rev_path, self._grade_path)
        if result.error:
            self.error_msg.emit(result.error)
        else:
            self.finished.emit(result)

    def _on_progress(self, percent: int, message: str) -> None:
        self.progress.emit(percent, message)
