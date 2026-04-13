from __future__ import annotations

import os
from datetime import datetime, date
from typing import Optional

import pandas as pd
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from modules.history_engine import HistoryEngine
from views.widgets import Divider, SectionHeader


class HistoryView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._load_data()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header
        root.addWidget(SectionHeader(
            "◔  Histórico de Atividades",
            "Registro centralizado de todas as operações realizadas na suíte"
        ))
        root.addWidget(Divider())

        # Main Layout
        content = QVBoxLayout()
        content.setContentsMargins(28, 20, 28, 20)
        content.setSpacing(16)
        root.addLayout(content)

        # Filters Bar
        filters_row = QHBoxLayout()
        filters_row.setSpacing(12)

        # From Date
        filters_row.addWidget(QLabel("De:"))
        self._date_from = QDateEdit()
        self._date_from.setCalendarPopup(True)
        self._date_from.setDate(QDate.currentDate().addMonths(-1))
        self._date_from.dateChanged.connect(self._load_data)
        filters_row.addWidget(self._date_from)

        # To Date
        filters_row.addWidget(QLabel("Até:"))
        self._date_to = QDateEdit()
        self._date_to.setCalendarPopup(True)
        self._date_to.setDate(QDate.currentDate())
        self._date_to.dateChanged.connect(self._load_data)
        filters_row.addWidget(self._date_to)

        filters_row.addSpacing(16)

        # Brand Filter
        filters_row.addWidget(QLabel("Marca:"))
        self._combo_brand = QComboBox()
        self._combo_brand.addItems(["Todos", "Natura", "Avon", "Ambas"])
        self._combo_brand.currentTextChanged.connect(self._load_data)
        filters_row.addWidget(self._combo_brand)

        # Module Filter
        filters_row.addWidget(QLabel("Módulo:"))
        self._combo_module = QComboBox()
        self._combo_module.addItems(["Todos", "Auditor", "Sync", "Gerador", "Volumetria"])
        self._combo_module.currentTextChanged.connect(self._load_data)
        filters_row.addWidget(self._combo_module)

        filters_row.addStretch()

        # Action Buttons
        self._btn_refresh = QPushButton("↻ Atualizar")
        self._btn_refresh.setObjectName("btn_ghost")
        self._btn_refresh.clicked.connect(self._load_data)
        filters_row.addWidget(self._btn_refresh)

        content.addLayout(filters_row)

        # Table
        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(["ID", "Data/Hora", "Módulo", "Marca", "Ação"])
        self._table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self._table.setAlternatingRowColors(True)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.verticalHeader().setVisible(False)
        self._table.setColumnHidden(0, True) # Hide ID
        content.addWidget(self._table)

        # Bottom Action Bar
        bottom_row = QHBoxLayout()
        
        self._btn_export = QPushButton("⬇  Exportar Excel")
        self._btn_export.setObjectName("btn_secondary")
        self._btn_export.clicked.connect(self._export_excel)
        bottom_row.addWidget(self._btn_export)

        bottom_row.addStretch()

        self._btn_delete = QPushButton("Excluir Selecionado")
        self._btn_delete.setObjectName("btn_ghost")
        self._btn_delete.clicked.connect(self._delete_selected)
        bottom_row.addWidget(self._btn_delete)

        self._btn_clear = QPushButton("Limpar Tudo")
        self._btn_clear.setObjectName("btn_ghost")
        self._btn_clear.setStyleSheet("color: #ef5350;")
        self._btn_clear.clicked.connect(self._clear_all)
        bottom_row.addWidget(self._btn_clear)

        content.addLayout(bottom_row)

    def _load_data(self):
        start = self._date_from.date().toString("yyyy-MM-dd")
        end = self._date_to.date().toString("yyyy-MM-dd")
        brand = self._combo_brand.currentText()
        module = self._combo_module.currentText()

        # "Todos" mapped to "all" for engine
        brand_val = "all" if brand == "Todos" else brand
        module_val = "all" if module == "Todos" else module

        entries = HistoryEngine.get_entries(start, end, brand_val, module_val)

        self._table.setRowCount(0)
        self._table.setRowCount(len(entries))

        for i, entry in enumerate(entries):
            # ID
            self._table.setItem(i, 0, QTableWidgetItem(str(entry['id'])))
            
            # Format Date: DD-MM-YYYY HH:MM
            try:
                dt = datetime.fromisoformat(entry['timestamp'])
                dt_str = dt.strftime("%d-%m-%Y %H:%M")
            except:
                dt_str = entry['timestamp']
            
            self._table.setItem(i, 1, QTableWidgetItem(dt_str))
            
            # Module
            self._table.setItem(i, 2, QTableWidgetItem(entry['module']))
            
            # Brand
            brand_item = QTableWidgetItem(entry['brand'])
            if entry['brand'].lower() == 'natura':
                brand_item.setForeground(QColor("#FF8050"))
            elif entry['brand'].lower() == 'avon':
                brand_item.setForeground(QColor("#bb88ff"))
            self._table.setItem(i, 3, brand_item)
            
            # Action
            self._table.setItem(i, 4, QTableWidgetItem(entry['action']))

    def _delete_selected(self):
        row = self._table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Histórico", "Selecione um registro para excluir.")
            return
        
        entry_id = int(self._table.item(row, 0).text())
        confirm = QMessageBox.question(
            self, "Excluir", 
            f"Tem certeza que deseja excluir o registro ID {entry_id}?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if confirm == QMessageBox.Yes:
            HistoryEngine.delete_entry(entry_id)
            self._load_data()

    def _clear_all(self):
        confirm = QMessageBox.question(
            self, "Limpar Tudo", 
            "Tem certeza que deseja limpar TODO o histórico?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if confirm == QMessageBox.Yes:
            HistoryEngine.clear_history()
            self._load_data()

    def _export_excel(self):
        if self._table.rowCount() == 0:
            QMessageBox.warning(self, "Exportar", "Não há dados para exportar.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar Histórico", "HISTORICO_ATIVIDADES.xlsx", "Excel (*.xlsx)"
        )
        if not path:
            return

        # Collect data from table
        data = []
        for r in range(self._table.rowCount()):
            row_data = []
            for c in range(1, self._table.columnCount()): # Skip ID
                row_data.append(self._table.item(r, c).text())
            data.append(row_data)

        df = pd.DataFrame(data, columns=["Data/Hora", "Módulo", "Marca", "Ação"])
        try:
            df.to_excel(path, index=False)
            QMessageBox.information(self, "Sucesso", f"Histórico exportado com sucesso para:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao exportar: {str(e)}")

    def refresh_view(self):
        self._load_data()

    def refresh_theme(self):
        self._load_data()
