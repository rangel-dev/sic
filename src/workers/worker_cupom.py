"""
Worker thread para o módulo Cupons.
Executa CupomEngine fora da thread principal para não bloquear a UI.
"""
from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from src.core.cupom_engine import CupomEngine, CupomResult


class CupomWorker(QThread):
    progress  = Signal(int, str)
    finished  = Signal(object)   # CupomResult
    error_msg = Signal(str)

    def __init__(
        self,
        coupon_id:   str,
        manual_text: str,
        xlsx_paths:  list[str],
        parent=None,
    ):
        super().__init__(parent)
        self._coupon_id   = coupon_id
        self._manual_text = manual_text
        self._xlsx_paths  = xlsx_paths

    def run(self) -> None:
        try:
            engine = CupomEngine(progress_callback=self.progress.emit)
            result = engine.run(self._coupon_id, self._manual_text, self._xlsx_paths)
            self.finished.emit(result)
        except Exception as exc:
            import traceback
            traceback.print_exc()
            self.error_msg.emit(str(exc))
