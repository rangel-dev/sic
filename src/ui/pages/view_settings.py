"""Settings view – webhook URL, theme preferences via QSettings."""
from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import (
    QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)
from src.ui.components.base_widgets import Divider, SectionHeader


class SettingsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._settings = QSettings("SIC", "SIC_Suite")
        self._setup_ui()
        self._load_settings()

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        outer.addWidget(SectionHeader(
            "Configurações",
            "Webhooks, integrações e preferências da aplicação"
        ))
        outer.addWidget(Divider())

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        outer.addWidget(scroll)

        container = QWidget()
        scroll.setWidget(container)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(24)

        # Google Chat
        gchat_box = QGroupBox("Google Chat – Webhook")
        form = QFormLayout(gchat_box)
        form.setSpacing(12)
        form.setContentsMargins(16, 20, 16, 16)

        self._webhook_input = QLineEdit()
        self._webhook_input.setPlaceholderText("https://chat.googleapis.com/v1/spaces/.../messages?key=...")
        self._webhook_input.setMinimumWidth(520)
        form.addRow("URL do Webhook:", self._webhook_input)

        btn_row = QHBoxLayout()
        btn_save = QPushButton("Salvar")
        btn_save.setObjectName("btn_primary")
        btn_save.clicked.connect(self._save_settings)

        btn_test = QPushButton("Testar Conexão")
        btn_test.setObjectName("btn_secondary")
        btn_test.clicked.connect(self._test_webhook)

        btn_row.addWidget(btn_save)
        btn_row.addWidget(btn_test)
        btn_row.addStretch()
        form.addRow("", btn_row)

        hint = QLabel(
            "O webhook é usado para enviar relatórios de Auditoria e Sync "
            "diretamente ao seu espaço no Google Chat."
        )
        hint.setObjectName("label_hint")
        hint.setWordWrap(True)
        form.addRow("", hint)
        layout.addWidget(gchat_box)

        # Accessibility
        acc_box = QGroupBox("Acessibilidade — Visual")
        acc_layout = QHBoxLayout(acc_box)
        acc_layout.setContentsMargins(16, 20, 16, 16)
        acc_layout.setSpacing(12)

        acc_layout.addWidget(QLabel("Tamanho da Fonte:"))
        
        btn_font_small = QPushButton("A-")
        btn_font_small.setFixedWidth(60)
        btn_font_small.clicked.connect(lambda: self._change_font(-1))
        
        btn_font_reset = QPushButton("Normal")
        btn_font_reset.setFixedWidth(80)
        btn_font_reset.clicked.connect(lambda: self._reset_font())
        
        btn_font_large = QPushButton("A+")
        btn_font_large.setFixedWidth(60)
        btn_font_large.clicked.connect(lambda: self._change_font(1))

        acc_layout.addWidget(btn_font_small)
        acc_layout.addWidget(btn_font_reset)
        acc_layout.addWidget(btn_font_large)
        acc_layout.addStretch()

        layout.addWidget(acc_box)

        # About
        about_box = QGroupBox("Sobre")
        about_layout = QVBoxLayout(about_box)
        about_layout.setContentsMargins(16, 20, 16, 16)
        about_layout.setSpacing(6)

        for line in [
            "SIC — System Intelligence Commerce  v0.0.8",
            "Enterprise Pricing & Catalog Management para Salesforce Demandware",
            "Compatível com: Natura (NATBRA-), Avon (AVNBRA-), Minha Loja (ML)",
            "Dependências: PySide6, Pandas, lxml, openpyxl, pytesseract",
        ]:
            lbl = QLabel(line)
            lbl.setObjectName("label_muted")
            about_layout.addWidget(lbl)

        layout.addWidget(about_box)
        layout.addStretch()

    # ── Persistence ───────────────────────────────────────────────────────
    def _load_settings(self):
        self._webhook_input.setText(
            self._settings.value("gchat_webhook", "")
        )

    def _save_settings(self):
        self._settings.setValue("gchat_webhook", self._webhook_input.text().strip())
        QMessageBox.information(self, "Configurações", "Configurações salvas com sucesso.")

    def _change_font(self, delta: int):
        val = int(self._settings.value("font_size", 13))
        new_val = max(10, min(24, val + delta))
        self._settings.setValue("font_size", new_val)
        
        # Notify MainWindow
        main_win = self.window()
        if hasattr(main_win, "apply_theme_and_font"):
            main_win.apply_theme_and_font()

    def _reset_font(self):
        self._settings.setValue("font_size", 13)
        main_win = self.window()
        if hasattr(main_win, "apply_theme_and_font"):
            main_win.apply_theme_and_font()

    # ── Webhook test ──────────────────────────────────────────────────────
    def _test_webhook(self):
        url = self._webhook_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Webhook", "Insira a URL do webhook antes de testar.")
            return
        try:
            import requests
            resp = requests.post(
                url,
                json={"text": "✅ SIC System Intelligence Commerce — conexão de teste bem-sucedida!"},
                timeout=8,
            )
            if resp.status_code == 200:
                QMessageBox.information(self, "Webhook", "Mensagem enviada com sucesso ao Google Chat!")
            else:
                QMessageBox.warning(
                    self, "Webhook",
                    f"Servidor retornou status {resp.status_code}.\n{resp.text[:200]}"
                )
        except requests.exceptions.RequestException as exc:
            QMessageBox.critical(self, "Erro de Conexão", str(exc))

    def get_webhook_url(self) -> str:
        return self._settings.value("gchat_webhook", "")
