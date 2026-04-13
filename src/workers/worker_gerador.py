"""
Worker thread for the Gerador module.
Runs Excel→XML generation off the main thread.
"""
from typing import Optional
from PySide6.QtCore import QThread, Signal

from src.core.gerador_engine import GeradorEngine


class GeradorWorker(QThread):
    progress  = Signal(int, str)
    finished  = Signal(dict)          # result dict from GeradorEngine.run()
    error_msg = Signal(str)

    def __init__(
        self,
        excel_paths: list[str],
        mode: str = "full",
        base_xml_path: Optional[str] = None,
        parent=None,
    ):
        super().__init__(parent)
        self._excel_paths  = excel_paths
        self._mode         = mode
        self._base_xml     = base_xml_path

    def run(self) -> None:
        engine = GeradorEngine(progress_callback=self._on_progress)
        result = engine.run(self._excel_paths, self._mode, self._base_xml)
        if result.get("error"):
            self.error_msg.emit(result["error"])
        else:
            self.finished.emit(result)

    def _on_progress(self, percent: int, message: str) -> None:
        self.progress.emit(percent, message)
