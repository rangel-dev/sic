from PySide6.QtCore import QThread, Signal

from src.core.relatorio_menu_engine import RelatorioMenuEngine


class RelatorioMenuWorker(QThread):
    progress  = Signal(int, str)
    finished  = Signal(object)     # RelatorioMenuResult
    error_msg = Signal(str)

    def __init__(self, natura_path: str, avon_path: str, cb_path: str, parent=None):
        super().__init__(parent)
        self._paths = (natura_path, avon_path, cb_path)

    def run(self) -> None:
        engine = RelatorioMenuEngine(progress_callback=self.progress.emit)
        result = engine.run(*self._paths)
        if result.error:
            self.error_msg.emit(result.error)
        else:
            self.finished.emit(result)
