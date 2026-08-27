"""
Pricing Master Suite v11.6 – Entry Point
Run: python main.py
"""
import os
import sys
import platform

from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QFont, QIcon, QPixmap
from PySide6.QtWidgets import QApplication, QSplashScreen, QProgressBar, QLabel, QFrame

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


# Tamanho lógico fixo do splash (não muda em nenhum monitor)
_SPLASH_W = 600
_SPLASH_H = 600


class PremiumSplash(QSplashScreen):
    """Modern splash screen with progress bar and status updates.
    
    Usa um tamanho lógico FIXO (600×600) para garantir que a janela
    nunca mude de tamanho durante a inicialização, independentemente
    do DPR ou resolução do monitor.
    """
    def __init__(self, pixmap, app_name, version):
        w, h = _SPLASH_W, _SPLASH_H

        # 1. Escalar a imagem para o tamanho lógico desejado em pixels físicos,
        #    levando em conta o DPR do monitor para imagens nítidas em HiDPI.
        dpr = QApplication.instance().devicePixelRatio()
        phys_w = int(w * dpr)
        phys_h = int(h * dpr)

        scaled = pixmap.scaled(
            phys_w, phys_h,
            Qt.KeepAspectRatioByExpanding,
            Qt.SmoothTransformation,
        )
        # Recortar ao centro para garantir exatamente phys_w × phys_h
        x_off = (scaled.width()  - phys_w) // 2
        y_off = (scaled.height() - phys_h) // 2
        scaled = scaled.copy(x_off, y_off, phys_w, phys_h)

        # 2. Agora sim definimos o DPR — o Qt vai tratar como w×h lógicos
        scaled.setDevicePixelRatio(dpr)

        super().__init__(scaled, Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)

        # 3. Travamos em tamanho lógico fixo — nunca vai pular
        self.setFixedSize(w, h)

        # Bottom Overlay (efeito gradiente na parte inferior)
        self.overlay = QFrame(self)
        self.overlay.setGeometry(0, h - 80, w, 80)
        self.overlay.setStyleSheet("""
            QFrame {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                                  stop:0 rgba(0,0,0,0),
                                                  stop:1 rgba(0,0,0,160));
                border-bottom-left-radius: 12px;
                border-bottom-right-radius: 12px;
            }
        """)

        # Barra de progresso — faixa fina no rodapé
        self.progress = QProgressBar(self)
        self.progress.setGeometry(40, h - 35, w - 80, 4)
        self.progress.setStyleSheet("""
            QProgressBar {
                background-color: rgba(255, 255, 255, 25);
                border: none;
                border-radius: 2px;
                color: transparent;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                            stop:0 #FF6B35, stop:1 #7B2FBE);
                border-radius: 2px;
            }
        """)
        self.progress.setRange(0, 100)
        self.progress.setValue(0)

        # Label de status
        self.status_lbl = QLabel("Iniciando SIC...", self)
        self.status_lbl.setGeometry(44, h - 60, w - 88, 20)
        self.status_lbl.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 230);
                font-size: 12px;
                font-weight: 500;
                letter-spacing: 0.4px;
            }
        """)

        # Label de versão
        self.ver_lbl = QLabel(f"v{version}", self)
        self.ver_lbl.setGeometry(w - 100, 20, 80, 20)
        self.ver_lbl.setStyleSheet(
            "color: rgba(255,255,255,100); font-size: 11px; font-weight: 600;"
        )
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
    if os.path.exists(splash_bg_path):
        splash_pixmap = QPixmap(splash_bg_path)
    else:
        splash_pixmap = QPixmap(icon_path)

    splash = PremiumSplash(splash_pixmap, APP_NAME, VERSION)
    splash.show()
    
    app.processEvents()

    # ── Launch ────────────────────────────────────────────────────────────
    splash.update_progress(10, "Carregando módulos de segurança...")
    app.processEvents()
    
    def on_progress(val, msg):
        # Mapeia 0-100 da MainWindow para 15-95 no Splash
        mapped_val = 15 + int(val * 0.8)
        splash.update_progress(mapped_val, msg)

    window = MainWindow(progress_callback=on_progress)
    window.setWindowIcon(QIcon(icon_path))
    
    splash.update_progress(100, "Inicialização Concluída")
    app.processEvents()
    
    window.show()
    splash.finish(window)

    # Permitir que o Ctrl+C (SIGINT) feche o programa imediatamente e sem erros
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    try:
        sys.exit(app.exec())
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
