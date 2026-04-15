"""
Pricing Master Suite v11.6 – Entry Point
Run: python main.py
"""
import os
import sys
import platform

from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QFont, QIcon, QPixmap
from PySide6.QtWidgets import QApplication, QSplashScreen, QProgressBar, QLabel

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


class PremiumSplash(QSplashScreen):
    """Modern splash screen with progress bar and status updates."""
    def __init__(self, pixmap, app_name, version):
        super().__init__(pixmap, Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setFixedSize(pixmap.size())
        
        # Progress bar - positioned at the bottom
        self.progress = QProgressBar(self)
        self.progress.setGeometry(40, pixmap.height() - 50, pixmap.width() - 80, 6)
        self.progress.setStyleSheet("""
            QProgressBar {
                background-color: rgba(255, 255, 255, 20);
                border: none;
                border-radius: 3px;
                text-align: center;
                color: transparent;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                                          stop:0 #FF6B35, stop:1 #7B2FBE);
                border-radius: 3px;
            }
        """)
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        
        # Status Label
        self.status_lbl = QLabel(self)
        self.status_lbl.setGeometry(40, pixmap.height() - 80, pixmap.width() - 80, 20)
        self.status_lbl.setStyleSheet("""
            color: rgba(255, 255, 255, 0.8);
            font-size: 11px;
            font-weight: 500;
            letter-spacing: 0.5px;
        """)
        self.status_lbl.setText(f"Iniciando {app_name}...")

        # Version Label
        self.ver_lbl = QLabel(f"v{version}", self)
        self.ver_lbl.setGeometry(pixmap.width() - 100, 20, 80, 20)
        self.ver_lbl.setStyleSheet("color: rgba(255, 255, 255, 0.4); font-size: 10px; font-weight: 600;")
        self.ver_lbl.setAlignment(Qt.AlignRight)

    def update_progress(self, value, message):
        self.progress.setValue(value)
        self.status_lbl.setText(message)
        QApplication.instance().processEvents()


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

    # ── Splash Screen ─────────────────────────────────────────────────────
    splash_bg_path = resource_path("assets/splash_bg.png")
    if not os.path.exists(splash_bg_path):
        # Fallback to icon if background is missing
        splash_pixmap = QPixmap(icon_path).scaled(
            256, 256, Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
    else:
        splash_pixmap = QPixmap(splash_bg_path)

    splash = PremiumSplash(splash_pixmap, APP_NAME, VERSION)
    splash.show()
    app.processEvents()

    # ── Launch ────────────────────────────────────────────────────────────
    splash.update_progress(10, "Carregando módulos principais...")
    
    def on_progress(val, msg):
        # Map 0-100 from MainWindow to 10-100 on Splash
        mapped_val = 10 + int(val * 0.9)
        splash.update_progress(mapped_val, msg)

    window = MainWindow(progress_callback=on_progress)
    window.setWindowIcon(QIcon(icon_path))
    
    splash.update_progress(100, "Concluído")
    window.show()
    splash.finish(window)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
