"""
Виджет дерева XML.
"""

import logging
from typing import Optional

from PySide6.QtWidgets import QTreeView, QMenu, QApplication
from PySide6.QtCore import Signal, Slot, QModelIndex, Qt
from PySide6.QtGui import QClipboard, QAction

from ..models.tree_model import SCXTreeModel

logger = logging.getLogger(__name__)


class SCXTreeView(QTreeView):
    """Виджет дерева XML с контекстным меню."""
    
    element_selected = Signal(object)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        
        self.setSelectionBehavior(QTreeView.SelectRows)
        self.setAlternatingRowColors(True)
        self.header().setStretchLastSection(True)
    
    def set_model(self, model: SCXTreeModel):
        """Устанавливает модель."""
        self.setModel(model)
        self.expandAll()
    
    @Slot(QModelIndex)
    def _on_selection_changed(self, index: QModelIndex):
        """Обрабатывает изменение выделения."""
        if isinstance(self.model(), SCXTreeModel):
            element = self.model().get_element(index)
            if element is not None:
                self.element_selected.emit(element)
    
    def _show_context_menu(self, pos: QModelIndex):
        """Показывает контекстное меню."""
        index = self.indexAt(pos)
        if not index.isValid():
            return
        
        menu = QMenu(self)
        
        copy_value_action = QAction("Копировать значение", self)
        copy_value_action.triggered.connect(lambda: self._copy_value(index))
        menu.addAction(copy_value_action)
        
        copy_xpath_action = QAction("Копировать XPath", self)
        copy_xpath_action.triggered.connect(lambda: self._copy_xpath(index))
        menu.addAction(copy_xpath_action)
        
        find_same_tag_action = QAction("Найти узлы с этим тегом", self)
        find_same_tag_action.triggered.connect(lambda: self._find_same_tag(index))
        menu.addAction(find_same_tag_action)
        
        menu.exec_(self.viewport().mapToGlobal(pos))
    
    def _copy_value(self, index: QModelIndex):
        """Копирует значение в буфер."""
        if isinstance(self.model(), SCXTreeModel):
            data = self.model().data(index)
            if data:
                clipboard = QApplication.clipboard()
                clipboard.setText(str(data))
    
    def _copy_xpath(self, index: QModelIndex):
        """Копирует XPath в буфер."""
        if isinstance(self.model(), SCXTreeModel):
            element = self.model().get_element(index)
            if element is not None:
                tree = element.getroottree()
                xpath = tree.getpath(element)
                clipboard = QApplication.clipboard()
                clipboard.setText(xpath)
    
    def _find_same_tag(self, index: QModelIndex):
        """Ищет узлы с таким же тегом."""
        if isinstance(self.model(), SCXTreeModel):
            element = self.model().get_element(index)
            if element is not None:
                tag = element.tag
                logger.info(f"Поиск узлов с тегом: {tag}")
