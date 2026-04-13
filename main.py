"""
Pricing Master Suite v11.6 – Entry Point
Run: python main.py
"""
import sys

from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from styles.qss_dark import DARK_STYLESHEET
from styles.qss_light import LIGHT_STYLESHEET
from ui_main import MainWindow


def main():
    # ── HiDPI + anti-aliasing ─────────────────────────────────────────────
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Pricing Master Suite")
    app.setOrganizationName("PricingMaster")
    app.setApplicationVersion("11.6")

    # ── Settings & Theme ──────────────────────────────────────────────────
    settings = QSettings("PricingMaster", "PricingMasterSuite")
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
