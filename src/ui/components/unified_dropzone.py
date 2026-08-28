"""
Entrada unificada de arquivos do Auditor (Tarefa 1).

`UnifiedFileDropZone` — uma única área de arrastar-e-soltar/clique que
aceita Pricebook, Catálogo(s), Grade(s) e Kit BO de uma vez ou aos poucos,
classificando cada arquivo automaticamente (`file_classifier.classify_file`)
e aplicando as mesmas regras de negócio que já existiam nos 4 `DropZone`
separados (marca única por catálogo/grade, país Brasil — BRD, incidente
Chile). Não substitui a validação de `AuditorView._run()`, que continua
intacta como defesa em profundidade.

`IngestionChecklist` — painel somente-leitura ao lado/abaixo da caixa,
mostrando ✅/⏳ por categoria a partir de `file_classifier.compute_readiness`.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QMouseEvent
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.core.auditor.file_classifier import ClassifiedFile, classify_file, compute_readiness

_BRAND_DISPLAY = {"natura": "Natura", "avon": "Avon", "ml": "Minha Loja"}


# ─────────────────────────────────────────────────────────────────────────────
#  UnifiedFileDropZone
# ─────────────────────────────────────────────────────────────────────────────
class UnifiedFileDropZone(QFrame):
    """Uma única zona de drop que roteia cada arquivo pra sua categoria
    (Pricebook/Catálogo/Grade/Kit BO), classificando automaticamente."""

    state_changed = Signal()
    file_rejected = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._pricebook: Optional[ClassifiedFile] = None
        self._kit_bo: Optional[ClassifiedFile] = None
        self._catalogs: dict[str, ClassifiedFile] = {}
        self._grades: dict[str, ClassifiedFile] = {}
        self._last_dir: str = ""

        self.setObjectName("dropzone")
        self.setAcceptDrops(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(120)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.MinimumExpanding)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignCenter)

        self._icon_label = QLabel("⊕")
        self._icon_label.setStyleSheet("font-size:26px; background:transparent;")
        self._icon_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        layout.addWidget(self._icon_label)

        self._main_label = QLabel(
            "Arraste aqui Pricebook, Catálogo(s), Grade(s) e/ou Kit BO — de uma "
            "vez ou aos poucos\n(ou clique para escolher os arquivos)"
        )
        self._main_label.setAlignment(Qt.AlignCenter)
        self._main_label.setWordWrap(True)
        self._main_label.setStyleSheet("font-size:12px; background:transparent;")
        self._main_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        layout.addWidget(self._main_label)

        self._file_label = QLabel("")
        self._file_label.setAlignment(Qt.AlignCenter)
        self._file_label.setWordWrap(True)
        self._file_label.setStyleSheet("font-size:11px; font-weight:600; background:transparent;")
        self._file_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        self._file_label.hide()
        layout.addWidget(self._file_label)

        self._btn_clear = QPushButton("✕ Limpar tudo")
        self._btn_clear.setObjectName("btn_ghost")
        self._btn_clear.setFixedHeight(22)
        self._btn_clear.setStyleSheet("font-size:10px; padding:0 6px;")
        self._btn_clear.clicked.connect(self.clear)
        self._btn_clear.hide()
        layout.addWidget(self._btn_clear, 0, Qt.AlignmentFlag.AlignHCenter)

    # ── Acessores públicos (mesma forma dos antigos DropZone.file_path(s)) ──
    @property
    def pricebook_path(self) -> Optional[str]:
        return self._pricebook.path if self._pricebook else None

    @property
    def catalog_paths(self) -> list[str]:
        return [cf.path for cf in self._catalogs.values()]

    @property
    def grade_paths(self) -> list[str]:
        return [cf.path for cf in self._grades.values()]

    @property
    def bo_path(self) -> Optional[str]:
        return self._kit_bo.path if self._kit_bo else None

    def catalog_by_brand(self) -> dict[str, str]:
        return {b: cf.path for b, cf in self._catalogs.items()}

    def grade_by_brand(self) -> dict[str, str]:
        return {b: cf.path for b, cf in self._grades.items()}

    def clear(self) -> None:
        self._pricebook = None
        self._kit_bo = None
        self._catalogs.clear()
        self._grades.clear()
        self._refresh_visual()
        self.state_changed.emit()

    def remove_file(self, path: str) -> None:
        changed = False
        if self._pricebook and self._pricebook.path == path:
            self._pricebook = None
            changed = True
        if self._kit_bo and self._kit_bo.path == path:
            self._kit_bo = None
            changed = True
        for container in (self._catalogs, self._grades):
            for brand, cf in list(container.items()):
                if cf.path == path:
                    del container[brand]
                    changed = True
        if changed:
            self._refresh_visual()
            self.state_changed.emit()

    # ── Interação (clique + arrastar-e-soltar, mesmo padrão do DropZone) ───
    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self._open_dialog()

    def _open_dialog(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Selecionar arquivos", self._last_dir or "",
            "Arquivos suportados (*.xml *.xlsx *.xlsm *.xls)"
        )
        if paths:
            self._last_dir = str(Path(paths[0]).parent)
            self._handle_new_paths(paths)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setProperty("state", "hover")
            self._refresh_style()

    def dragLeaveEvent(self, event) -> None:
        self.setProperty("state", "filled" if self._total_count() else "")
        self._refresh_style()

    def dropEvent(self, event: QDropEvent) -> None:
        paths = [u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()]
        if paths:
            self._last_dir = str(Path(paths[0]).parent)
            self._handle_new_paths(paths)

    # ── Classificação e roteamento ──────────────────────────────────────────
    def _handle_new_paths(self, paths: list[str]) -> None:
        rejected: list[str] = []
        for path in paths:
            cf = classify_file(path)
            msg = self._try_accept(cf)
            if msg:
                rejected.append(msg)

        if rejected:
            body = rejected[0] if len(rejected) == 1 else "\n".join(f"• {m}" for m in rejected)
            self.file_rejected.emit(body)

        self._refresh_visual()
        self.state_changed.emit()

    def _try_accept(self, cf: ClassifiedFile) -> Optional[str]:
        name = Path(cf.path).name

        if cf.category == "unknown":
            return f"{name}: {cf.reason}"

        if cf.category == "pricebook":
            self._pricebook = cf
            return None

        if cf.category == "kit_bo":
            self._kit_bo = cf
            return None

        # catalog / grade — múltiplos, um por marca
        container = self._catalogs if cf.category == "catalog" else self._grades
        label = "catálogo" if cf.category == "catalog" else "grade"
        brand_key = next(iter(cf.brands)) if cf.brands else "desconhecida"

        existing = container.get(brand_key)
        if existing is not None and existing.path != cf.path:
            brand_display = _BRAND_DISPLAY.get(brand_key, "Desconhecida")
            return (
                f"{name}: já existe um {label} da marca {brand_display} "
                f"carregado ({Path(existing.path).name})."
            )

        container[brand_key] = cf
        return None

    # ── Estado visual ────────────────────────────────────────────────────────
    def _total_count(self) -> int:
        return (
            (1 if self._pricebook else 0)
            + (1 if self._kit_bo else 0)
            + len(self._catalogs)
            + len(self._grades)
        )

    def _refresh_visual(self) -> None:
        total = self._total_count()
        if total == 0:
            self._icon_label.show()
            self._main_label.show()
            self._file_label.hide()
            self._btn_clear.hide()
            self.setProperty("state", "")
        else:
            self._icon_label.hide()
            self._main_label.hide()
            plural = "s" if total != 1 else ""
            self._file_label.setText(f"✔  {total} arquivo{plural} inserido{plural}")
            self._file_label.show()
            self._btn_clear.show()
            self.setProperty("state", "filled")
        self._refresh_style()

    def _refresh_style(self) -> None:
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()


# ─────────────────────────────────────────────────────────────────────────────
#  _ChecklistRow — uma linha do checklist (categoria ou marca)
# ─────────────────────────────────────────────────────────────────────────────
class _ChecklistRow(QFrame):
    remove_requested = Signal(str)  # path

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("card_flat")
        self._path: Optional[str] = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(8)

        self._icon = QLabel("⏳")
        self._icon.setFixedWidth(18)
        self._icon.setStyleSheet("font-size:13px; background:transparent;")
        layout.addWidget(self._icon)

        self._text = QLabel("")
        self._text.setWordWrap(True)
        self._text.setStyleSheet("font-size:12px; background:transparent;")
        layout.addWidget(self._text, 1)

        self._btn_remove = QPushButton("✕")
        self._btn_remove.setObjectName("btn_ghost")
        self._btn_remove.setFixedSize(22, 22)
        self._btn_remove.setStyleSheet("font-size:10px; padding:0;")
        self._btn_remove.hide()
        self._btn_remove.clicked.connect(self._on_remove_clicked)
        layout.addWidget(self._btn_remove)

    def _on_remove_clicked(self) -> None:
        if self._path:
            self.remove_requested.emit(self._path)

    def set_state(
        self,
        filled: bool,
        label: str,
        path: Optional[str] = None,
        *,
        optional_empty: bool = False,
    ) -> None:
        self._path = path
        if filled:
            self._icon.setText("✅")
        elif optional_empty:
            self._icon.setText("—")
        else:
            self._icon.setText("⏳")

        name = Path(path).name if path else ""
        self._text.setText(f"{label} — {name}" if name else label)
        self._btn_remove.setVisible(bool(path))


# ─────────────────────────────────────────────────────────────────────────────
#  IngestionChecklist
# ─────────────────────────────────────────────────────────────────────────────
class IngestionChecklist(QWidget):
    """Painel somente-leitura: reflete ao vivo o estado de um
    `UnifiedFileDropZone` via `compute_readiness`."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._dz: Optional[UnifiedFileDropZone] = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(6)

        self._mode_lbl = QLabel("")
        self._mode_lbl.setObjectName("label_muted")
        self._mode_lbl.setStyleSheet("font-weight:700;")
        layout.addWidget(self._mode_lbl)

        self._row_pb = _ChecklistRow()
        layout.addWidget(self._row_pb)

        self._cat_header = QLabel("Catálogos (0/3)")
        self._cat_header.setObjectName("label_muted")
        layout.addWidget(self._cat_header)
        self._row_cat_natura = _ChecklistRow()
        self._row_cat_avon = _ChecklistRow()
        self._row_cat_ml = _ChecklistRow()
        for row in (self._row_cat_natura, self._row_cat_avon, self._row_cat_ml):
            layout.addWidget(row)

        self._grade_header = QLabel("Grade de Ativação")
        self._grade_header.setObjectName("label_muted")
        layout.addWidget(self._grade_header)
        self._row_grade_natura = _ChecklistRow()
        self._row_grade_avon = _ChecklistRow()
        for row in (self._row_grade_natura, self._row_grade_avon):
            layout.addWidget(row)

        self._row_bo = _ChecklistRow()
        layout.addWidget(self._row_bo)

        self._all_rows = (
            self._row_pb, self._row_cat_natura, self._row_cat_avon, self._row_cat_ml,
            self._row_grade_natura, self._row_grade_avon, self._row_bo,
        )

    def bind(self, dz: UnifiedFileDropZone) -> None:
        """Conecta ao widget de entrada: escuta `state_changed` e liga os
        botões '✕' de cada linha a `dz.remove_file`."""
        self._dz = dz
        dz.state_changed.connect(self.refresh)
        for row in self._all_rows:
            row.remove_requested.connect(dz.remove_file)
        self.refresh()

    def refresh(self) -> None:
        if self._dz is None:
            return

        state = compute_readiness(
            self._dz.pricebook_path, self._dz.catalog_paths,
            self._dz.grade_paths, self._dz.bo_path,
        )

        self._mode_lbl.setText(
            "Modo: Só-Kit (sem Pricebook)" if state.kit_only else "Modo: Auditoria completa"
        )

        self._row_pb.set_state(bool(self._dz.pricebook_path), "Pricebook XML", self._dz.pricebook_path)

        cat_brands = self._dz.catalog_by_brand()
        self._cat_header.setText(f"Catálogos ({state.cat_count}/3)")
        self._row_cat_natura.set_state("natura" in cat_brands, "Natura", cat_brands.get("natura"))
        self._row_cat_avon.set_state("avon" in cat_brands, "Avon", cat_brands.get("avon"))
        self._row_cat_ml.set_state("ml" in cat_brands, "Minha Loja", cat_brands.get("ml"))

        grade_brands = self._dz.grade_by_brand()
        suffix = " — obrigatória (Kit BO anexado)" if state.grade_required else " — opcional"
        self._grade_header.setText(f"Grade de Ativação{suffix}")
        self._row_grade_natura.set_state("natura" in grade_brands, "Natura", grade_brands.get("natura"))
        self._row_grade_avon.set_state("avon" in grade_brands, "Avon", grade_brands.get("avon"))

        self._row_bo.set_state(
            bool(self._dz.bo_path), "Kit BO (opcional)", self._dz.bo_path,
            optional_empty=not self._dz.bo_path,
        )
