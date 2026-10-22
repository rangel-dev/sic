"""
Workers da Limpeza de Campanhas (BRD-015).
Simulação e geração dos arquivos rodam fora da thread principal: o export de
cupons pode ter centenas de MB.
"""
from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from src.core.limpeza_engine import LimpezaEngine, SimulationResult


class LimpezaSimulationWorker(QThread):
    progress = Signal(int, str)
    finished = Signal(object, object)   # (LimpezaEngine, SimulationResult)
    error_msg = Signal(str)

    def __init__(self, files: dict[str, str], loja: str, protected_terms: list[str],
                 grace_days: int, parent=None):
        super().__init__(parent)
        self._files = dict(files)
        self._loja = loja
        self._terms = list(protected_terms)
        self._grace_days = grace_days

    def run(self) -> None:
        try:
            engine = LimpezaEngine(self._files, self._loja, protected_terms=self._terms,
                                   grace_days=self._grace_days, progress_callback=self.progress.emit)
            self.finished.emit(engine, engine.simulate())
        except Exception as exc:
            import traceback
            traceback.print_exc()
            self.error_msg.emit(str(exc))


class LimpezaExportWorker(QThread):
    progress = Signal(int, str)
    finished = Signal(object)            # ExportResult
    error_msg = Signal(str)

    def __init__(self, engine: LimpezaEngine, result: SimulationResult, output_dir: str, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._result = result
        self._output_dir = output_dir

    def run(self) -> None:
        try:
            self._engine.set_progress_callback(self.progress.emit)
            self.finished.emit(self._engine.export(self._result, self._output_dir))
        except Exception as exc:
            import traceback
            traceback.print_exc()
            self.error_msg.emit(str(exc))
