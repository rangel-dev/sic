"""
Update Worker — SIC
Asynchronous update checking to keep UI smooth.
"""
from PySide6.QtCore import QThread, Signal
from src.core.update_service import UpdateService

class UpdateWorker(QThread):
    update_found = Signal(str, str) # (tag, download_url)

    def run(self):
        try:
            tag, url = UpdateService.get_latest_release()
            if tag and url and UpdateService.is_update_available(tag):
                self.update_found.emit(tag, url)
        except Exception as e:
            print(f"Background update worker failed: {e}")
