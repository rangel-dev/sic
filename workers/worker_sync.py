"""
Worker thread for the Sync module.
Runs the catalog delta calculation off the main thread.
"""
from PySide6.QtCore import QThread, Signal

from modules.sync_engine import SyncEngine, SyncResult


class SyncWorker(QThread):
    progress  = Signal(int, str)
    finished  = Signal(object)        # SyncResult
    error_msg = Signal(str)

    def __init__(
        self,
        excel_paths: list[str],
        catalog_xml_paths: list[str],
        parent=None,
    ):
        super().__init__(parent)
        self._excel_paths = excel_paths
        self._cat_paths   = catalog_xml_paths

    def run(self) -> None:
        engine = SyncEngine(progress_callback=self._on_progress)
        result: SyncResult = engine.run(self._excel_paths, self._cat_paths)
        if result.error:
            self.error_msg.emit(result.error)
        else:
            self.finished.emit(result)

    def _on_progress(self, percent: int, message: str) -> None:
        self.progress.emit(percent, message)
