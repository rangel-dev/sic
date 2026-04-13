"""
Volumetria View – OCR-based product image validation.
Uses pytesseract to extract volumes from product photos and compares
against volume metadata in the Salesforce catalog XML.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from views.widgets import Divider, DropZone, SectionHeader


# ─── OCR Worker ──────────────────────────────────────────────────────────────
class VolumetriaWorker(QThread):
    progress = Signal(int, str)
    result_ready = Signal(list)   # list of result dicts
    error_msg = Signal(str)

    def __init__(self, xml_path: str, image_paths: list[str], parent=None):
        super().__init__(parent)
        self._xml_path    = xml_path
        self._image_paths = image_paths

    def run(self):
        try:
            self.progress.emit(5, "Analisando catálogo XML…")
            catalog_volumes = self._parse_catalog_volumes()

            results = []
            total = len(self._image_paths)
            for i, img_path in enumerate(self._image_paths):
                pct = 10 + int(85 * (i / max(total, 1)))
                name = Path(img_path).stem.upper()
                self.progress.emit(pct, f"Processando {Path(img_path).name}…")
                row = self._analyse_image(img_path, name, catalog_volumes)
                results.append(row)

            self.progress.emit(100, f"{total} imagens analisadas.")
            self.result_ready.emit(results)
        except Exception as exc:
            self.error_msg.emit(str(exc))

    def _parse_catalog_volumes(self) -> dict[str, str]:
        """Extract expected volumes from catalog XML display-names."""
        from lxml import etree
        CATALOG_NS = "http://www.demandware.com/xml/impex/catalog/2006-10-31"
        ns = {"c": CATALOG_NS}
        vol_re = re.compile(
            r"(\d+(?:[.,]\d+)?)\s*(ml|g|kg|l|oz|fl\.oz|unidade|un)\b", re.IGNORECASE
        )
        volumes: dict[str, str] = {}
        try:
            tree = etree.parse(self._xml_path)
            for prod in tree.findall(".//c:product", ns):
                pid = prod.get("product-id", "").upper()
                name_el = prod.find(".//c:display-name", ns)
                if name_el is not None and name_el.text:
                    m = vol_re.search(name_el.text)
                    if m:
                        volumes[pid] = f"{m.group(1)}{m.group(2).lower()}"
        except Exception:
            pass
        return volumes

    def _analyse_image(self, path: str, sku: str, catalog_vols: dict) -> dict:
        row: dict = {
            "sku":        sku,
            "file":       Path(path).name,
            "resolution": "—",
            "aspect":     "—",
            "background": "—",
            "cat_volume": catalog_vols.get(sku, "N/A"),
            "ocr_volume": "—",
            "match":      "N/A",
            "status":     "⚠️",
        }

        try:
            from PIL import Image
            img = Image.open(path)
            w, h = img.size
            row["resolution"] = f"{w}×{h}"

            # Aspect ratio
            ratio = w / h if h else 0
            row["aspect"] = f"{ratio:.2f}" + (" ✅" if 0.95 <= ratio <= 1.05 else " 🚩")

            # Background (sample corners)
            rgb = img.convert("RGB")
            corners = [
                rgb.getpixel((0, 0)), rgb.getpixel((w - 1, 0)),
                rgb.getpixel((0, h - 1)), rgb.getpixel((w - 1, h - 1)),
                rgb.getpixel((w // 2, 0)), rgb.getpixel((w // 2, h - 1)),
            ]
            white = sum(1 for r, g, b in corners if r > 230 and g > 230 and b > 230)
            row["background"] = "Branco ✅" if white >= 5 else "Colorido 🚩"

            # OCR
            try:
                import pytesseract
                small = img.resize((img.width * 2, img.height * 2))
                text = pytesseract.image_to_string(small, lang="por")
                vol_re = re.compile(
                    r"(\d+(?:[.,]\d+)?)\s*(ml|g|kg|l|oz|fl\.oz|unidade|un)\b", re.IGNORECASE
                )
                found = vol_re.findall(text)
                if found:
                    ocr_vol = found[0][0] + found[0][1].lower()
                    row["ocr_volume"] = ocr_vol
                    cat_v = row["cat_volume"]
                    if cat_v == "N/A":
                        row["match"] = "N/A"
                    elif cat_v.lower().replace(" ", "") == ocr_vol.lower().replace(" ", ""):
                        row["match"] = "✅ OK"
                        row["status"] = "✅"
                    else:
                        row["match"] = f"🚩 {cat_v} vs {ocr_vol}"
                        row["status"] = "🚩"
                else:
                    row["ocr_volume"] = "N/D"
                    row["match"] = "⚠️ Ilegível"
            except ImportError:
                row["ocr_volume"] = "pytesseract não instalado"

        except Exception as exc:
            row["status"] = f"Erro: {exc}"

        return row


# ─── View ─────────────────────────────────────────────────────────────────────
class VolumetriaView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: Optional[VolumetriaWorker] = None
        self._setup_ui()

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        outer.addWidget(SectionHeader(
            "◎  Volumetria",
            "Valida volume em imagens de produto via OCR (pytesseract) vs catálogo XML"
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
        layout.setSpacing(16)

        # Inputs
        lbl_xml = QLabel("Catálogo XML  (fonte de volumes esperados)")
        lbl_xml.setObjectName("label_section")
        layout.addWidget(lbl_xml)

        self._dz_xml = DropZone("Arraste o XML de Catálogo", "XML (*.xml)")
        layout.addWidget(self._dz_xml)

        lbl_img = QLabel("Imagens de Produto  (nomeadas como SKU.jpg)")
        lbl_img.setObjectName("label_section")
        layout.addWidget(lbl_img)

        self._dz_images = DropZone(
            "Arraste as imagens  —  NATBRA-1234.jpg, AVNBRA-5678.png…",
            "Imagens (*.jpg *.jpeg *.png *.webp)",
            multiple=True,
        )
        self._dz_images.setMinimumHeight(90)
        layout.addWidget(self._dz_images)

        # Action
        action_row = QHBoxLayout()
        self._btn_run = QPushButton("◎  Analisar Imagens")
        self._btn_run.setObjectName("btn_primary")
        self._btn_run.setFixedWidth(200)
        self._btn_run.clicked.connect(self._run)
        action_row.addWidget(self._btn_run)

        btn_clear = QPushButton("Limpar")
        btn_clear.setObjectName("btn_ghost")
        btn_clear.clicked.connect(self._clear)
        action_row.addWidget(btn_clear)
        action_row.addStretch()
        layout.addLayout(action_row)

        # Progress
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.hide()
        layout.addWidget(self._progress_bar)

        self._status_lbl = QLabel("")
        self._status_lbl.setObjectName("label_muted")
        self._status_lbl.hide()
        layout.addWidget(self._status_lbl)

        # Results table
        cols = ["SKU", "Arquivo", "Resolução", "Aspect", "Background",
                "Vol. Catálogo", "Vol. OCR", "Match", "Status"]
        self._table = QTableWidget(0, len(cols))
        self._table.setHorizontalHeaderLabels(cols)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.setAlternatingRowColors(True)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        self._table.hide()
        layout.addWidget(self._table)

        layout.addStretch()

    # ── Slots ─────────────────────────────────────────────────────────────
    def _run(self):
        xml = self._dz_xml.file_path
        imgs = self._dz_images.file_paths
        if not xml:
            QMessageBox.warning(self, "Volumetria", "Selecione o XML de Catálogo.")
            return
        if not imgs:
            QMessageBox.warning(self, "Volumetria", "Selecione ao menos uma imagem.")
            return

        self._btn_run.setEnabled(False)
        self._table.hide()
        self._progress_bar.setValue(0)
        self._progress_bar.show()
        self._status_lbl.show()

        self._worker = VolumetriaWorker(xml, imgs, self)
        self._worker.progress.connect(self._on_progress)
        self._worker.result_ready.connect(self._on_results)
        self._worker.error_msg.connect(self._on_error)
        self._worker.start()

    def _on_progress(self, pct: int, msg: str):
        self._progress_bar.setValue(pct)
        self._status_lbl.setText(msg)

    def _on_results(self, rows: list):
        self._btn_run.setEnabled(True)
        self._table.setRowCount(0)

        cols_map = ["sku", "file", "resolution", "aspect", "background",
                    "cat_volume", "ocr_volume", "match", "status"]

        for row in rows:
            r = self._table.rowCount()
            self._table.insertRow(r)
            for c, key in enumerate(cols_map):
                item = QTableWidgetItem(str(row.get(key, "")))
                item.setTextAlignment(Qt.AlignCenter)
                self._table.setItem(r, c, item)

        self._table.show()

    def _on_error(self, msg: str):
        self._btn_run.setEnabled(True)
        self._progress_bar.hide()
        self._status_lbl.hide()
        QMessageBox.critical(self, "Erro — Volumetria", msg)

    def _clear(self):
        self._dz_xml.clear()
        self._dz_images.clear()
        self._progress_bar.hide()
        self._status_lbl.hide()
        self._table.setRowCount(0)
        self._table.hide()
        self._btn_run.setEnabled(True)
