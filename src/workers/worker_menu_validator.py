"""
Worker thread for the Menu Validator module.
Runs the full validation off the main thread so the UI stays responsive.
"""
from PySide6.QtCore import QThread, Signal

from src.core.menu_validator_engine import MenuValidatorEngine, MenuValidationResult


class MenuValidatorWorker(QThread):
    progress  = Signal(int, str)   # (percent, message)
    finished  = Signal(object)     # MenuValidationResult
    error_msg = Signal(str)

    def __init__(
        self,
        natura_path: str,
        avon_path: str,
        cb_path: str,
        parent=None,
    ):
        super().__init__(parent)
        self._natura_path = natura_path
        self._avon_path   = avon_path
        self._cb_path     = cb_path

    def run(self) -> None:
        engine = MenuValidatorEngine(progress_callback=self._on_progress)
        result: MenuValidationResult = engine.run(
            self._natura_path,
            self._avon_path,
            self._cb_path,
        )
        if result.error:
            self.error_msg.emit(result.error)
        else:
            self.finished.emit(result)

    def _on_progress(self, percent: int, message: str) -> None:
        self.progress.emit(percent, message)
