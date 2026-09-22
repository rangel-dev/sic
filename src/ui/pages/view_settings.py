"""Settings view – webhook URL, theme preferences via QSettings."""
from pathlib import Path

from PySide6.QtCore import QSettings, Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFileDialog, QFormLayout, QGroupBox, QHBoxLayout,
    QLabel, QLineEdit, QMessageBox, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)
from src.core.app_paths import data_file, user_data_dir
from src.core.segmentada_registry import JsonFileRegistryStore, SyncedFolderRegistryStore
from src.ui.components.base_widgets import Divider, SectionHeader

# Chaves do QSettings para o compartilhamento (P5) — importadas também por
# view_exportador_segmentadas.py, para não duplicar o nome da chave.
SEG_SHARED_ENABLED_KEY = "seg_registry_shared_enabled"
SEG_SHARED_FOLDER_KEY = "seg_registry_shared_folder"


class SettingsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._settings = QSettings("SIC", "SIC_Suite")
        self._seg_registry_store = JsonFileRegistryStore(data_file("segmentadas_registry.json"))
        self._setup_ui()
        self._load_settings()
        self._reload_seg_registry_combo()

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

        # Registry de Segmentadas (BRD-012, P2 — armazenamento local; P5 —
        # compartilhamento via pasta do Google Drive sincronizada, revisado
        # em 22-09-2026: sem Google Cloud, sem OAuth, sem API)
        seg_box = QGroupBox("Registry de Segmentadas")
        seg_form = QFormLayout(seg_box)
        seg_form.setSpacing(12)
        seg_form.setContentsMargins(16, 20, 16, 16)

        self._seg_registry_combo = QComboBox()
        self._seg_registry_combo.setMinimumWidth(420)
        seg_form.addRow("Registros salvos:", self._seg_registry_combo)

        seg_btn_row = QHBoxLayout()
        btn_seg_delete = QPushButton("Apagar registro selecionado")
        btn_seg_delete.setObjectName("btn_secondary")
        btn_seg_delete.clicked.connect(self._delete_seg_registry_entry)
        seg_btn_row.addWidget(btn_seg_delete)

        btn_seg_open_folder = QPushButton("Abrir pasta do registro")
        btn_seg_open_folder.setObjectName("btn_ghost")
        btn_seg_open_folder.clicked.connect(self._open_seg_registry_folder)
        seg_btn_row.addWidget(btn_seg_open_folder)
        seg_btn_row.addStretch()
        seg_form.addRow("", seg_btn_row)

        seg_hint = QLabel(
            "Cada pricebook segmentado salvo pelo Exportador → Segmentadas grava um "
            "vínculo aqui (aba da planilha ↔ ID do pricebook). Use \"Apagar\" só "
            "para corrigir um vínculo salvo por engano — apagar não desfaz o "
            "arquivo XML já gerado."
        )
        seg_hint.setObjectName("label_hint")
        seg_hint.setWordWrap(True)
        seg_form.addRow("", seg_hint)

        seg_form.addRow("", Divider())

        self._seg_shared_check = QCheckBox("Compartilhar com a equipe")
        seg_form.addRow("", self._seg_shared_check)

        seg_folder_row = QHBoxLayout()
        self._seg_shared_folder_input = QLineEdit()
        self._seg_shared_folder_input.setReadOnly(True)
        self._seg_shared_folder_input.setPlaceholderText(
            "Pasta do Google Drive sincronizada (Google Drive para computador)"
        )
        self._seg_shared_folder_input.setMinimumWidth(360)
        seg_folder_row.addWidget(self._seg_shared_folder_input)
        btn_seg_choose_folder = QPushButton("Escolher pasta...")
        btn_seg_choose_folder.setObjectName("btn_secondary")
        btn_seg_choose_folder.clicked.connect(self._choose_seg_shared_folder)
        seg_folder_row.addWidget(btn_seg_choose_folder)
        seg_form.addRow("Pasta compartilhada:", seg_folder_row)

        btn_seg_save_sharing = QPushButton("Salvar compartilhamento")
        btn_seg_save_sharing.setObjectName("btn_primary")
        btn_seg_save_sharing.clicked.connect(self._save_seg_sharing_settings)
        seg_form.addRow("", btn_seg_save_sharing)

        seg_shared_hint = QLabel(
            "A pasta precisa estar sincronizada pelo Google Drive para computador "
            "(instalado e logado com a conta da equipe) em todas as máquinas. O SIC só "
            "lê e escreve arquivos nela — não fala com nenhuma API do Google. Cada "
            "pricebook salvo grava um arquivo próprio na pasta, e uma planilha .xlsx "
            "de leitura é atualizada junto, para conferir sem abrir o SIC."
        )
        seg_shared_hint.setObjectName("label_hint")
        seg_shared_hint.setWordWrap(True)
        seg_form.addRow("", seg_shared_hint)

        layout.addWidget(seg_box)

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

        layout.addStretch()

    # ── Persistence ───────────────────────────────────────────────────────
    def _load_settings(self):
        self._webhook_input.setText(
            self._settings.value("gchat_webhook", "")
        )
        shared_enabled = self._settings.value(SEG_SHARED_ENABLED_KEY, False, type=bool)
        self._seg_shared_check.setChecked(shared_enabled)
        self._seg_shared_folder_input.setText(self._settings.value(SEG_SHARED_FOLDER_KEY, ""))

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

    # ── Registry de Segmentadas — escape hatch da P2 ────────────────────────
    def _reload_seg_registry_combo(self) -> None:
        self._seg_registry_combo.clear()
        records = sorted(self._seg_registry_store.load(), key=lambda r: r.updated_at or "")
        if not records:
            self._seg_registry_combo.addItem("Nenhum registro salvo", None)
            self._seg_registry_combo.setEnabled(False)
            return
        self._seg_registry_combo.setEnabled(True)
        for r in records:
            label = f"{r.pricebook_id} — {r.sheet_name} ({r.campaign_name or 'sem campanha'})"
            self._seg_registry_combo.addItem(label, r.pricebook_id)

    def _delete_seg_registry_entry(self) -> None:
        pricebook_id = self._seg_registry_combo.currentData()
        if not pricebook_id:
            return
        resp = QMessageBox.question(
            self, "Apagar registro",
            f"Apagar o vínculo salvo de <b>{pricebook_id}</b>?\n\n"
            "Isso não afeta nenhum arquivo XML já gerado — só o vínculo "
            "lembrado pelo SIC para o reconhecimento na próxima importação.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if resp == QMessageBox.Yes:
            self._seg_registry_store.delete(pricebook_id)
            self._reload_seg_registry_combo()

    def _open_seg_registry_folder(self) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(user_data_dir())))

    # ── Compartilhamento (P5) — pasta do Google Drive sincronizada ─────────
    def _choose_seg_shared_folder(self) -> None:
        start_dir = self._seg_shared_folder_input.text().strip() or str(Path.home())
        folder = QFileDialog.getExistingDirectory(self, "Escolher pasta compartilhada", start_dir)
        if folder:
            self._seg_shared_folder_input.setText(folder)

    def _save_seg_sharing_settings(self) -> None:
        enabled = self._seg_shared_check.isChecked()
        folder_text = self._seg_shared_folder_input.text().strip()
        if enabled and not folder_text:
            QMessageBox.warning(
                self, "Registry de Segmentadas",
                "Escolha a pasta compartilhada antes de ligar o compartilhamento."
            )
            return

        if enabled and not self._confirm_seg_shared_folder_looks_right(Path(folder_text)):
            return

        self._settings.setValue(SEG_SHARED_ENABLED_KEY, enabled)
        self._settings.setValue(SEG_SHARED_FOLDER_KEY, folder_text)
        QMessageBox.information(self, "Registry de Segmentadas", "Compartilhamento salvo com sucesso.")

    def _confirm_seg_shared_folder_looks_right(self, folder: Path) -> bool:
        """Trava de segurança: se a pasta escolhida já tiver algo dentro mas
        nada que pareça registro do SIC, é bem provável que seja a pasta
        errada (Desktop, Documentos etc.) escolhida por engano — pede
        confirmação explícita antes de ligar o compartilhamento nela."""
        if not folder.exists():
            return True
        has_any_content = any(folder.iterdir())
        has_sic_records = bool(SyncedFolderRegistryStore(folder).load())
        if has_any_content and not has_sic_records:
            resp = QMessageBox.question(
                self, "Confirmar pasta compartilhada",
                f"A pasta escolhida já tem arquivos, mas nenhum deles parece ser "
                f"registro do SIC:\n\n{folder}\n\n"
                "Isso pode ser a pasta certa na primeira vez que alguém liga o "
                "compartilhamento, ou pode ser a pasta errada escolhida por engano.\n\n"
                "Confirma que é a pasta compartilhada certa?",
                QMessageBox.Yes | QMessageBox.No,
            )
            return resp == QMessageBox.Yes
        return True
