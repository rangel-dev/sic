"""Cadastro view – placeholder for future feature."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class CadastroView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        icon = QLabel("≡")
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet("font-size:48px;color:#2a2a2a;background:transparent;")
        layout.addWidget(icon)

        title = QLabel("Cadastro")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size:18px;font-weight:700;color:#444;background:transparent;")
        layout.addWidget(title)

        sub = QLabel("Módulo em desenvolvimento — disponível em breve.")
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet("font-size:12px;color:#444;background:transparent;")
        layout.addWidget(sub)
