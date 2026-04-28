"""
Dropdown navigation button with a custom floating popup panel.

Replaces the native QMenu approach (which caused layout bugs in the navbar
and looked ugly/misaligned) with a borderless QFrame popup that is fully
styled by the app's QSS themes.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal, QPoint, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class _DropdownPanel(QFrame):
    """Floating borderless popup panel that contains the submenu items."""

    item_clicked = Signal(int)  # Emits the page index

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setObjectName("dropdown_panel")
        self.setAutoFillBackground(True)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(6, 6, 6, 6)
        self._layout.setSpacing(2)

    def _apply_theme(self):
        """Sync panel colors from the application's active stylesheet."""
        app = QApplication.instance()
        if app is None:
            return
        qss = app.styleSheet()
        # Detect theme by a known dark-only token
        if "#1e293b" in qss:  # dark theme bg token
            self.setStyleSheet("""
                _DropdownPanel, QFrame#dropdown_panel {
                    background-color: #1e293b;
                    border: 1px solid #334155;
                    border-radius: 8px;
                }
                QPushButton#dropdown_item {
                    background-color: transparent;
                    color: #94a3b8;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 16px;
                    text-align: left;
                    font-size: 13px;
                    font-weight: 400;
                    min-height: 36px;
                }
                QPushButton#dropdown_item:hover {
                    background-color: #0c2540;
                    color: #60a5fa;
                    font-weight: 500;
                }
                QPushButton#dropdown_item:pressed {
                    background-color: #1e3a6e;
                    color: #93c5fd;
                }
            """)
        else:  # light theme
            self.setStyleSheet("""
                QFrame#dropdown_panel {
                    background-color: #ffffff;
                    border: 1px solid #e5e7eb;
                    border-radius: 8px;
                }
                QPushButton#dropdown_item {
                    background-color: transparent;
                    color: #404040;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 16px;
                    text-align: left;
                    font-size: 13px;
                    font-weight: 400;
                    min-height: 36px;
                }
                QPushButton#dropdown_item:hover {
                    background-color: #eff6ff;
                    color: #3b82f6;
                    font-weight: 500;
                }
                QPushButton#dropdown_item:pressed {
                    background-color: #dbeafe;
                    color: #2563eb;
                }
            """)

    def add_item(self, label: str, page_index: int, icon: str = ""):
        text = f"  {icon}  {label}" if icon else f"  {label}"
        btn = QPushButton(text.strip())
        btn.setObjectName("dropdown_item")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFixedHeight(36)
        btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        btn.clicked.connect(lambda: self._on_item_clicked(page_index))

        font = btn.font()
        font.setPointSize(12)
        btn.setFont(font)

        self._layout.addWidget(btn)

    def _on_item_clicked(self, page_index: int):
        self.hide()
        self.item_clicked.emit(page_index)

    def show_below(self, anchor: QWidget):
        """Position the panel directly below the anchor widget and show it."""
        self._apply_theme()  # Sync colors with current theme before showing
        global_pos: QPoint = anchor.mapToGlobal(QPoint(0, anchor.height()))
        self.adjustSize()
        self.move(global_pos)
        self.show()
        self.raise_()


class DropdownNavButton(QPushButton):
    """
    Navigation button that shows a custom floating submenu panel on click.

    Unlike QPushButton.setMenu(), this approach does NOT add a native arrow
    indicator or split-button visual, keeping the navbar layout clean and
    consistent with the other tab buttons.
    """

    submenu_clicked = Signal(int)  # Emits the page index when a submenu item is clicked

    def __init__(self, icon: str, label: str, parent=None):
        super().__init__(parent)
        self.setText(f"  {icon}   {label}  ▾")
        self.setObjectName("tab_button")
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(56)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

        font = self.font()
        font.setPointSize(12)
        self.setFont(font)

        # Build the custom floating popup (parented to None so it floats freely)
        self._panel = _DropdownPanel(None)
        self._panel.item_clicked.connect(self._on_submenu_item_clicked)

        self.clicked.connect(self._toggle_panel)

    # ── Public API ────────────────────────────────────────────────────────────

    def add_submenu_item(self, label: str, page_index: int, icon: str = ""):
        """Add an item to the dropdown panel."""
        self._panel.add_item(label, page_index, icon)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _toggle_panel(self):
        if self._panel.isVisible():
            self._panel.hide()
        else:
            self._panel.show_below(self)

    def _on_submenu_item_clicked(self, page_index: int):
        self.submenu_clicked.emit(page_index)
