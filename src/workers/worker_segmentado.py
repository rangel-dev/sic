"""
Worker de varredura da grade para a aba "Segmentadas" do Exportador.
"""
from __future__ import annotations

import traceback

from PySide6.QtCore import QThread, Signal

from src.core.segmentado_engine import SegmentadoEngine, SegmentScanResult


class SegmentadoScanWorker(QThread):
    progress  = Signal(int, str)
    finished  = Signal(object)   # SegmentScanResult
    error_msg = Signal(str)

    def __init__(self, path: str, expected_brand: str, parent=None):
        super().__init__(parent)
        self._path = path
        self._expected_brand = expected_brand

    def run(self) -> None:
        try:
            result = SegmentadoEngine.scan_workbook(
                self._path,
                self._expected_brand,
                progress_callback=lambda pct, msg: self.progress.emit(pct, msg),
            )
            self.finished.emit(result)
        except Exception as exc:
            print(traceback.format_exc())
            self.error_msg.emit(str(exc))
