"""
Shared UI Components for Pricing Master Suite
─────────────────────────────────────────────
DropZone      – drag-and-drop / click file selector
ErrorCard     – clickable error summary card for the Auditor dashboard
SectionHeader – page title + subtitle block
StatRow       – horizontal key/value stat pill
Divider       – thin horizontal separator line
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from PySide6.QtCore import (
    Qt,
    Signal,
    QMimeData,
    QPropertyAnimation,
    QSequentialAnimationGroup,
    Property,
)
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QMouseEvent, QColor, QPainter
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


from src.core.brand_detector import BrandDetector


# ─────────────────────────────────────────────────────────────────────────────
#  DropZone
# ─────────────────────────────────────────────────────────────────────────────
class DropZone(QFrame):
    """
    A styled file-drop area.  Emits `files_selected(list[str])` whenever
    the user drops files or chooses them via the browse dialog.

    Parameters
    ----------
    label        : descriptive text shown inside the zone
    extensions   : e.g. "Excel (*.xlsx *.xls)" – passed to QFileDialog
    multiple     : whether to allow selecting multiple files
    """

    files_selected = Signal(list)  # list[str] of absolute paths

    def __init__(
        self,
        label: str = "Arraste o arquivo aqui ou clique para selecionar",
        extensions: str = "Todos os arquivos (*.*)",
        multiple: bool = False,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._extensions = extensions
        self._multiple = multiple
        self._files: list[str] = []
        self._last_dir: str = ""  # Lembra a última pasta usada

        self.setObjectName("dropzone")
        self.setAcceptDrops(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(72)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignCenter)

        self._icon_label = QLabel("⊕")
        self._icon_label.setStyleSheet("font-size:22px; background:transparent;")
        self._icon_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        layout.addWidget(self._icon_label)

        self._main_label = QLabel(label)
        self._main_label.setAlignment(Qt.AlignCenter)
        self._main_label.setWordWrap(True)
        self._main_label.setStyleSheet("font-size:12px; background:transparent;")
        self._main_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        layout.addWidget(self._main_label)

        self._file_label = QLabel("")
        self._file_label.setAlignment(Qt.AlignCenter)
        self._file_label.setWordWrap(True)
        self._file_label.setStyleSheet(
            "font-size:11px; font-weight:600; background:transparent;"
        )
        self._file_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        self._file_label.hide()
        layout.addWidget(self._file_label)

        # Botão de limpar — só visível quando há arquivos selecionados
        self._btn_clear = QPushButton("✕ Limpar seleção")
        self._btn_clear.setObjectName("btn_ghost")
        self._btn_clear.setFixedHeight(22)
        self._btn_clear.setStyleSheet("font-size:10px; padding:0 6px;")
        self._btn_clear.clicked.connect(self.clear)
        self._btn_clear.hide()
        layout.addWidget(self._btn_clear)

    # ── Public API ────────────────────────────────────────────────────────
    def clear(self) -> None:
        self._files = []
        self._file_label.hide()
        self._btn_clear.hide()
        self._icon_label.show()
        self._main_label.show()
        self.setProperty("state", "")
        self.setProperty("brand", "")
        self._refresh_style()

    @property
    def file_paths(self) -> list[str]:
        return list(self._files)

    @property
    def file_path(self) -> Optional[str]:
        return self._files[0] if self._files else None

    # ── Interaction ───────────────────────────────────────────────────────
    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self._open_dialog()

    def _open_dialog(self) -> None:
        start_dir = self._last_dir or ""
        if self._multiple:
            paths, _ = QFileDialog.getOpenFileNames(
                self, "Selecionar arquivos", start_dir, self._extensions
            )
        else:
            path, _ = QFileDialog.getOpenFileName(
                self, "Selecionar arquivo", start_dir, self._extensions
            )
            paths = [path] if path else []

        if paths:
            # Lembra a última pasta usada
            self._last_dir = str(Path(paths[0]).parent)
            if self._multiple:
                # Acumula: adiciona novos sem duplicar
                existing = set(self._files)
                new_paths = [p for p in paths if p not in existing]
                self._set_files(self._files + new_paths)
            else:
                self._set_files(paths)

    # ── Drag-and-drop ─────────────────────────────────────────────────────
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setProperty("state", "hover")
            self._refresh_style()

    def dragLeaveEvent(self, event) -> None:
        self.setProperty("state", "filled" if self._files else "")
        self._refresh_style()

    def dropEvent(self, event: QDropEvent) -> None:
        paths = [u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()]
        if paths:
            if self._multiple:
                # Acumula: adiciona novos sem duplicar
                existing = set(self._files)
                new_paths = [p for p in paths if p not in existing]
                self._set_files(self._files + new_paths)
            else:
                self._set_files(paths[:1])

    # ── State management ──────────────────────────────────────────────────
    def _set_files(self, paths: list[str]) -> None:
        self._files = paths

        # Build per-file brand information
        file_brands = []  # list of (filename, brand_set, display_str)
        for path in paths:
            filename = Path(path).name
            brands = BrandDetector.detect_single(path)
            file_brands.append((filename, brands))

        # Determine overall brand property for QSS styling
        all_brands = set()
        for _, brands in file_brands:
            all_brands.update(brands)
        brand_property = BrandDetector.get_brand_qss_state(all_brands)

        # Build display text
        if len(file_brands) == 1:
            # Single file: show with brand(s)
            filename, brands = file_brands[0]
            brand_name = BrandDetector.get_combined_display_name(brands)
            brand_emoji = self._get_brand_emoji(brands)
            if brand_name != "Desconhecida":
                display = f"[{brand_name}] {filename}"
            else:
                display = filename
            status_icon = brand_emoji
        else:
            # Multiple files: show brand names only (no filenames)
            display_lines = [f"✔ {len(file_brands)} arquivos:"]

            # Group files by brand for cleaner display
            files_by_brand = self._group_files_by_brand(file_brands)

            for brand_name, brand_emoji, filenames in files_by_brand:
                # Show only brand emoji + name (no filenames - they're just noise)
                display_lines.append(f"  {brand_emoji}  {brand_name}")

            display = "\n".join(display_lines)
            status_icon = "✔"

        self._icon_label.hide()
        self._main_label.hide()
        self._file_label.setText(f"{status_icon}  {display}")
        self._file_label.setWordWrap(True)
        self._file_label.show()
        if self._multiple:
            self._btn_clear.show()

        self.setProperty("state", "filled")
        self.setProperty("brand", brand_property)
        self._refresh_style()
        self.files_selected.emit(self._files)

    def _get_brand_emoji(self, brands: set[str]) -> str:
        """Maps brand set to emoji icon."""
        if not brands or brands == {"unknown"}:
            return "❓"

        # Single brand
        if len(brands) == 1:
            brand = list(brands)[0]
            if brand == "natura":
                return "🟧"
            elif brand == "avon":
                return "🟪"
            elif brand == "ml":
                return "🟦"

        # Multiple brands
        return "🟦🟧🟪"  # Show all three colors

    def _group_files_by_brand(
        self, file_brands: list[tuple[str, set[str]]]
    ) -> list[tuple[str, str, list[str]]]:
        """
        Groups files by their detected brand(s).

        Returns
        -------
        list of (brand_name, brand_emoji, filenames)
        """
        # Map each file to its primary brand
        natura_files = []
        avon_files = []
        ml_files = []
        mixed_files = []

        for filename, brands in file_brands:
            brands_clean = brands - {"unknown"}

            if len(brands_clean) == 0:
                mixed_files.append((filename, "❓"))
            elif len(brands_clean) == 1:
                brand = list(brands_clean)[0]
                if brand == "natura":
                    natura_files.append(filename)
                elif brand == "avon":
                    avon_files.append(filename)
                elif brand == "ml":
                    ml_files.append(filename)
            else:
                # Multiple brands in single file
                brand_name = BrandDetector.get_combined_display_name(brands_clean)
                mixed_files.append((filename, brand_name))

        result = []
        if natura_files:
            result.append(("Natura", "🟧", natura_files))
        if avon_files:
            result.append(("Avon", "🟪", avon_files))
        if ml_files:
            result.append(("Minha Loja", "🟦", ml_files))
        if mixed_files:
            for fname, label in mixed_files:
                if label == "❓":
                    result.append(("Desconhecido", "❓", [fname]))
                else:
                    result.append((label, "🟦🟧🟪", [fname]))

        return result

    def set_error(self, message: str) -> None:
        self._file_label.setText(f"⚠  {message}")
        self._file_label.setStyleSheet(
            "font-size:11px; font-weight:600; background:transparent;"
        )
        self._file_label.show()
        self._icon_label.hide()
        self._main_label.hide()
        self.setProperty("state", "error")
        self._refresh_style()

    def _refresh_style(self) -> None:
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()


# ─────────────────────────────────────────────────────────────────────────────
#  ErrorCard
# ─────────────────────────────────────────────────────────────────────────────
class ErrorCard(QFrame):
    """
    Clickable card for the Auditor dashboard.
    Shows error icon, title, total count, and Natura/Avon breakdown.
    Emits `clicked(code)` when the user clicks it.
    """

    clicked_code = Signal(str)

    def __init__(
        self,
        code: str,
        icon: str,
        title: str,
        impact: str = "",
        desc: str = "",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._code = code
        self._active = False

        self.setObjectName("error_card")
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(88)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # Tooltip rico
        tip = f"<div style='margin:4px'><b>{title}</b><br>"
        if impact:
            tip += f"<span style='color:#666'>Impacto: {impact}</span><br>"
        if desc:
            tip += f"<hr><span style='font-size:11px'>{desc}</span><br>"
        tip += f"<hr><span style='color:#0066cc;font-weight:bold'>Clique para filtrar por este erro</span>"
        tip += "</div>"
        self.setToolTip(tip)

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 10, 14, 10)
        root.setSpacing(4)

        # Top row: icon + title
        top = QHBoxLayout()
        top.setSpacing(8)

        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet("font-size:14px; background:transparent;")
        top.addWidget(icon_lbl)

        self._title_lbl = QLabel(title)
        self._title_lbl.setStyleSheet(
            "font-size:11px; font-weight:600; background:transparent;"
        )
        self._title_lbl.setWordWrap(True)
        top.addWidget(self._title_lbl, 1)
        root.addLayout(top)

        # Count
        self._count_lbl = QLabel("—")
        self._count_lbl.setStyleSheet(
            "font-size:26px; font-weight:700; background:transparent;"
        )
        root.addWidget(self._count_lbl)

        # Brand breakdown
        self._brand_lbl = QLabel("")
        self._brand_lbl.setStyleSheet("font-size:10px; background:transparent;")
        root.addWidget(self._brand_lbl)

    # ── API ───────────────────────────────────────────────────────────────
    def update_counts(self, total: int, natura: int, avon: int) -> None:
        if total == 0:
            self._count_lbl.setText("0")
            self._count_lbl.setStyleSheet(
                "font-size:26px; font-weight:700; background:transparent;"
            )
            self._brand_lbl.setText("")
        else:
            color = self._severity_color(total)
            self._count_lbl.setText(str(total))
            self._count_lbl.setStyleSheet(
                f"font-size:26px; font-weight:700; color:{color}; background:transparent;"
            )
            parts = []
            if natura > 0:
                parts.append(f'<span style="color:#ff8050">Natura:{natura}</span>')
            if avon > 0:
                parts.append(f'<span style="color:#bb88ff">Avon:{avon}</span>')
            self._brand_lbl.setText("  ".join(parts))

    def set_selected(self, selected: bool) -> None:
        self._active = selected
        self.setProperty("selected", "true" if selected else "false")
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    # ── Events ────────────────────────────────────────────────────────────
    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self.clicked_code.emit(self._code)

    # ── Helpers ───────────────────────────────────────────────────────────
    @staticmethod
    def _severity_color(n: int) -> str:
        if n == 0:
            return "#444444"
        if n <= 5:
            return "#ff9800"
        if n <= 20:
            return "#f44336"
        return "#ef5350"


# ─────────────────────────────────────────────────────────────────────────────
#  SectionHeader
# ─────────────────────────────────────────────────────────────────────────────
class SectionHeader(QWidget):
    """Page-level header: large title + muted subtitle."""

    def __init__(
        self,
        title: str,
        subtitle: str = "",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setObjectName("page_header")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 12, 28, 10)
        layout.setSpacing(3)

        title_lbl = QLabel(title)
        title_lbl.setObjectName("page_title")
        layout.addWidget(title_lbl)

        if subtitle:
            sub_lbl = QLabel(subtitle)
            sub_lbl.setObjectName("page_subtitle")
            layout.addWidget(sub_lbl)


# ─────────────────────────────────────────────────────────────────────────────
#  Divider
# ─────────────────────────────────────────────────────────────────────────────
class Divider(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("divider")
        self.setFrameShape(QFrame.HLine)
        self.setFixedHeight(1)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)


# ─────────────────────────────────────────────────────────────────────────────
#  StatPill  – small "label: value" display
# ─────────────────────────────────────────────────────────────────────────────
class StatPill(QFrame):
    def __init__(
        self, label: str, value: str = "—", color: str = "#666666", parent=None
    ):
        super().__init__(parent)
        self.setObjectName("card_flat")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(2)

        self._val_lbl = QLabel(value)
        self._val_lbl.setObjectName("label_stat_value")
        self._val_lbl.setStyleSheet(
            f"font-size:22px;font-weight:700;background:transparent;"
        )
        layout.addWidget(self._val_lbl)

        lbl = QLabel(label.upper())
        lbl.setObjectName("label_stat_label")
        layout.addWidget(lbl)

    def set_value(self, value: str, color: Optional[str] = None) -> None:
        self._val_lbl.setText(value)
        if color:
            self._val_lbl.setStyleSheet(
                f"font-size:22px;font-weight:700;color:{color};background:transparent;"
            )


# ─────────────────────────────────────────────────────────────────────────────
#  PulseStatus — A pulsing green dot for "System Online"
# ─────────────────────────────────────────────────────────────────────────────
class PulseStatus(QWidget):
    def __init__(self, color: str = "#4CAF50", parent=None):
        super().__init__(parent)
        self.setFixedSize(20, 20)
        self._color = QColor(color)
        self._opacity = 1.0

        self.anim = QPropertyAnimation(self, b"opacity")
        self.anim.setDuration(1200)
        self.anim.setStartValue(1.0)
        self.anim.setKeyValueAt(0.5, 0.3)
        self.anim.setEndValue(1.0)
        self.anim.setLoopCount(-1)
        self.anim.start()

    def get_opacity(self):
        return self._opacity

    def set_opacity(self, v):
        self._opacity = v
        self.update()

    opacity = Property(float, get_opacity, set_opacity)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        c = self._color
        c.setAlphaF(self._opacity)
        p.setBrush(c)
        p.setPen(Qt.NoPen)
        p.drawEllipse(4, 4, 12, 12)


# ─────────────────────────────────────────────────────────────────────────────
#  NexusCard — Large interactive dashboard module cards
# ─────────────────────────────────────────────────────────────────────────────
class NexusCard(QFrame):
    clicked = Signal()

    def __init__(
        self, icon: str, title: str, desc: str, color_top: str = "#FF8050", parent=None
    ):
        super().__init__(parent)
        self.setObjectName("nexus_card")
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(140)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(8)

        # Style via property
        self.setStyleSheet(f"""
            QFrame#nexus_card {{
                border-top: 3px solid {color_top};
            }}
        """)

        self._icon_lbl = QLabel(icon)
        self._icon_lbl.setStyleSheet(
            f"font-size: 28px; color: {color_top}; background: transparent;"
        )
        layout.addWidget(self._icon_lbl)

        self._title_lbl = QLabel(title)
        self._title_lbl.setStyleSheet(
            "font-size: 16px; font-weight: 700; background: transparent;"
        )
        layout.addWidget(self._title_lbl)

        self._desc_lbl = QLabel(desc)
        self._desc_lbl.setStyleSheet(
            "font-size: 12px; color: #888; background: transparent;"
        )
        self._desc_lbl.setWordWrap(True)
        layout.addWidget(self._desc_lbl)

        layout.addStretch()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()


# ─────────────────────────────────────────────────────────────────────────────
#  KpiWidget — Modern metric display
# ─────────────────────────────────────────────────────────────────────────────
class KpiWidget(QFrame):
    def __init__(self, label: str, value: str = "0", icon: str = "📈", parent=None):
        super().__init__(parent)
        self.setObjectName("kpi_card")
        self.setMinimumWidth(180)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet("font-size: 24px; background: transparent;")
        layout.addWidget(icon_lbl)

        txt_container = QVBoxLayout()
        txt_container.setSpacing(0)

        self.val_lbl = QLabel(value)
        self.val_lbl.setStyleSheet(
            "font-size: 20px; font-weight: 800; background: transparent;"
        )
        txt_container.addWidget(self.val_lbl)

        lbl = QLabel(label.upper())
        lbl.setStyleSheet(
            "font-size: 10px; font-weight: 600; color: #777; background: transparent;"
        )
        txt_container.addWidget(lbl)

        layout.addLayout(txt_container)
        layout.addStretch()

    def set_value(self, v):
        self.val_lbl.setText(str(v))
