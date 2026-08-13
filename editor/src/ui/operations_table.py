"""
Таблица операций обработки.
"""

import logging

from PySide6.QtWidgets import QTableView, QMenu
from PySide6.QtGui import QAction
from PySide6.QtCore import Signal, Slot, QModelIndex, Qt

from ..models.operations_model import OperationsModel

logger = logging.getLogger(__name__)


class OperationsTable(QTableView):
    """Виджет таблицы операций."""
    
    operation_selected = Signal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        
        self.setSelectionBehavior(QTableView.SelectRows)
        self.setSelectionMode(QTableView.SingleSelection)
        self.setAlternatingRowColors(True)
        self.horizontalHeader().setStretchLastSection(True)
        self.verticalHeader().setVisible(False)
    
    def set_model(self, model: OperationsModel):
        """Устанавливает модель."""
        self.setModel(model)
        self.resizeColumnsToContents()
    
    @Slot(QModelIndex)
    def _on_selection_changed(self, index: QModelIndex):
        """Обрабатывает изменение выделения."""
        if index.isValid():
            row = index.row()
            self.operation_selected.emit(row)
    
    def _show_context_menu(self, pos: QModelIndex):
        """Показывает контекстное меню."""
        index = self.indexAt(pos)
        if not index.isValid():
            return
        
        menu = QMenu(self)
        
        edit_action = QAction("Редактировать операцию", self)
        edit_action.triggered.connect(lambda: self._edit_operation(index))
        menu.addAction(edit_action)
        
        goto_xml_action = QAction("Перейти к XML узлу", self)
        goto_xml_action.triggered.connect(lambda: self._goto_xml(index))
        menu.addAction(goto_xml_action)
        
        menu.exec_(self.viewport().mapToGlobal(pos))
    
    def _edit_operation(self, index: QModelIndex):
        """Редактирует операцию."""
        row = index.row()
        logger.info(f"Редактирование операции {row}")
    
    def _goto_xml(self, index: QModelIndex):
        """Переходит к XML узлу."""
        row = index.row()
        self.operation_selected.emit(row)
        logger.info(f"Переход к XML узлу операции {row}")
