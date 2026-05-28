"""
Worker thread for the Exportador module.
Orchestrates GeradorEngine and/or SyncEngine sequentially off the main thread.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from PySide6.QtCore import QThread, Signal

from src.core.gerador_engine import GeradorEngine
from src.core.sync_engine import SyncEngine, SyncResult


@dataclass
class ExportResult:
    pricebook: Optional[dict] = None      # GeradorEngine.run() dict; None if not requested
    catalog: Optional[SyncResult] = None  # SyncEngine.run() result; None if not requested


class ExportadorWorker(QThread):
    progress  = Signal(int, str)
    finished  = Signal(object)   # ExportResult
    error_msg = Signal(str)

    def __init__(
        self,
        excel_paths: list[str],
        generate_pricebook: bool,
        pb_mode: str,
        pb_base_xml: Optional[str],
        generate_catalog: bool,
        catalog_xml_paths: list[str],
        parent=None,
    ):
        super().__init__(parent)
        self._excel_paths = excel_paths
        self._gen_pb      = generate_pricebook
        self._pb_mode     = pb_mode
        self._pb_base_xml = pb_base_xml
        self._gen_cat     = generate_catalog
        self._cat_paths   = catalog_xml_paths

    def run(self) -> None:
        result = ExportResult()
        both = self._gen_pb and self._gen_cat

        try:
            if self._gen_pb:
                pb_scale = 0.48 if both else 1.0

                def pb_progress(p: int, m: str) -> None:
                    self.progress.emit(int(p * pb_scale), m)

                engine = GeradorEngine(progress_callback=pb_progress)
                result.pricebook = engine.run(self._excel_paths, self._pb_mode, self._pb_base_xml)

                if both:
                    self.progress.emit(50, "Pricebook concluído. Iniciando geração de Catálogo…")

            if self._gen_cat:
                cat_offset = 50 if both else 0
                cat_scale  = 0.50 if both else 1.0

                def cat_progress(p: int, m: str) -> None:
                    self.progress.emit(int(cat_offset + p * cat_scale), m)

                engine = SyncEngine(progress_callback=cat_progress)
                result.catalog = engine.run(self._excel_paths, self._cat_paths)

            self.finished.emit(result)

        except Exception as exc:
            import traceback
            traceback.print_exc()
            self.error_msg.emit(str(exc))
