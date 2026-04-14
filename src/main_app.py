"""
Pricing Master Suite v11.6 – Entry Point
Run: python main.py
"""
import os
import sys
import platform

from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import QApplication

from src.core.version import VERSION, APP_NAME
from src.ui.styles.qss_dark  import DARK_STYLESHEET
from src.ui.styles.qss_light import LIGHT_STYLESHEET
from src.ui.main_window import MainWindow


def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def main():
    # ── Windows Taskbar Icon Fix ──────────────────────────────────────────
    if platform.system().lower() == "windows":
        try:
            import ctypes
            myappid = f"rangeldev.sic.suite.{VERSION}"
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception:
            pass

    # ── HiDPI + anti-aliasing ─────────────────────────────────────────────
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("RangelDev")
    app.setApplicationVersion(VERSION)
    
    icon_path = resource_path("assets/icons/app_icon.png")
    app.setWindowIcon(QIcon(icon_path))

    # ── Settings & Theme ──────────────────────────────────────────────────
    settings = QSettings("SIC", "SIC_Suite")
    theme = settings.value("theme", "light")  # Defaulting to light as requested

    # ── Font ──────────────────────────────────────────────────────────────
    font = QFont("Helvetica Neue", 10)
    font.setStyleStrategy(QFont.PreferAntialias)
    app.setFont(font)

    # ── Apply Stylesheet ──────────────────────────────────────────────────
    if theme == "dark":
        app.setStyleSheet(DARK_STYLESHEET)
    else:
        app.setStyleSheet(LIGHT_STYLESHEET)

    # ── Launch ────────────────────────────────────────────────────────────
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
