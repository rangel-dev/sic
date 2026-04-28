"""Worker thread for the Cadastro kit-validation module."""
from PySide6.QtCore import QThread, Signal

from src.core.cadastro_engine import CadastroEngine, KitValidationResult


class CadastroWorker(QThread):
    progress  = Signal(int, str)
    finished  = Signal(object)   # KitValidationResult
    error_msg = Signal(str)

    def __init__(self, xml_path: str, excel_path: str, parent=None):
        super().__init__(parent)
        self._xml_path   = xml_path
        self._excel_path = excel_path

    def run(self) -> None:
        engine = CadastroEngine(progress_callback=self._on_progress)
        result: KitValidationResult = engine.run(self._xml_path, self._excel_path)
        if result.error:
            self.error_msg.emit(result.error)
        else:
            self.finished.emit(result)

    def _on_progress(self, percent: int, message: str) -> None:
        self.progress.emit(percent, message)
