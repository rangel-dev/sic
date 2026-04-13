"""
Worker thread for the Auditor module.
Runs the full double-blind audit off the main thread so the UI stays responsive.
"""
from PySide6.QtCore import QThread, Signal

from modules.auditor_engine import AuditorEngine, AuditResult


class AuditorWorker(QThread):
    progress  = Signal(int, str)      # (percent, message)
    finished  = Signal(object)        # AuditResult
    error_msg = Signal(str)

    def __init__(
        self,
        excel_paths: list[str],
        pb_path: str,
        cat_paths: list[str],
        parent=None,
    ):
        super().__init__(parent)
        self._excel_paths = excel_paths
        self._pb_path     = pb_path
        self._cat_paths   = cat_paths

    def run(self) -> None:
        engine = AuditorEngine(progress_callback=self._on_progress)
        result: AuditResult = engine.run(
            self._excel_paths, self._pb_path, self._cat_paths
        )
        if result.preflight_error:
            self.error_msg.emit(result.preflight_error)
        elif result.error:
            self.error_msg.emit(result.error)
        else:
            self.finished.emit(result)

    def _on_progress(self, percent: int, message: str) -> None:
        self.progress.emit(percent, message)
