"""
Модель дерева XML для отображения в QTreeView.
"""

import logging
from typing import Optional, Any, List
from lxml import etree

from PySide6.QtCore import Qt, QAbstractItemModel, QModelIndex

logger = logging.getLogger(__name__)


class SCXTreeItem:
    """Элемент дерева XML."""
    
    def __init__(self, element: Optional[etree.Element] = None, 
                 parent: Optional['SCXTreeItem'] = None):
        self.element = element
        self.parent_item = parent
        self.child_items: List['SCXTreeItem'] = []
        
        if element is not None:
            self._build_children()
    
    def _build_children(self):
        """Строит дочерние элементы."""
        if self.element is None:
            return
        
        for child in self.element:
            child_item = SCXTreeItem(child, self)
            self.child_items.append(child_item)
    
    def child(self, row: int) -> Optional['SCXTreeItem']:
        """Получает дочерний элемент по индексу."""
        if 0 <= row < len(self.child_items):
            return self.child_items[row]
        return None
    
    def child_count(self) -> int:
        """Получает количество дочерних элементов."""
        return len(self.child_items)
    
    def row(self) -> int:
        """Получает индекс элемента у родителя."""
        if self.parent_item:
            return self.parent_item.child_items.index(self)
        return 0
    
    def get_element(self) -> Optional[etree.Element]:
        """Получает XML элемент."""
        return self.element
    
    def get_display_data(self) -> dict:
        """Получает данные для отображения."""
        if self.element is None:
            return {'tag': 'Root', 'attribs': '', 'text': ''}
        
        tag = self.element.tag
        if '}' in tag:
            tag = tag.split('}')[1]
        
        attribs = ', '.join(f"{k}={v}" for k, v in self.element.attrib.items())
        text = (self.element.text or '').strip()[:50]
        
        return {
            'tag': tag,
            'attribs': attribs,
            'text': text,
        }


class SCXTreeModel(QAbstractItemModel):
    """Модель дерева XML для QTreeView."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.root_item = SCXTreeItem()
        self._headers = ['Тег', 'Атрибуты', 'Текст']
    
    def set_tree(self, tree: Optional[etree.ElementTree]):
        """
        Устанавливает XML дерево.
        
        Args:
            tree: XML дерево или None.
        """
        self.beginResetModel()
        
        if tree is None:
            self.root_item = SCXTreeItem()
        else:
            root_element = tree.getroot()
            self.root_item = SCXTreeItem(root_element)
        
        self.endResetModel()
    
    def headerData(self, section: int, orientation: Qt.Orientation, 
                   role: int = Qt.DisplayRole) -> Any:
        """Получает заголовок столбца."""
        if role != Qt.DisplayRole:
            return None
        
        if orientation == Qt.Horizontal:
            if 0 <= section < len(self._headers):
                return self._headers[section]
        
        return None
    
    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Получает количество столбцов."""
        return len(self._headers)
    
    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Получает количество строк."""
        if parent.isValid():
            parent_item = parent.internalPointer()
        else:
            parent_item = self.root_item
        
        return parent_item.child_count()
    
    def index(self, row: int, column: int, 
              parent: QModelIndex = QModelIndex()) -> QModelIndex:
        """Создаёт индекс элемента."""
        if not self.hasIndex(row, column, parent):
            return QModelIndex()
        
        if parent.isValid():
            parent_item = parent.internalPointer()
        else:
            parent_item = self.root_item
        
        child_item = parent_item.child(row)
        
        if child_item:
            return self.createIndex(row, column, child_item)
        else:
            return QModelIndex()
    
    def parent(self, index: QModelIndex) -> QModelIndex:
        """Получает индекс родителя."""
        if not index.isValid():
            return QModelIndex()
        
        child_item = index.internalPointer()
        parent_item = child_item.parent_item
        
        if parent_item is None or parent_item == self.root_item:
            return QModelIndex()
        
        return self.createIndex(parent_item.row(), 0, parent_item)
    
    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        """Получает данные элемента."""
        if not index.isValid():
            return None
        
        if role != Qt.DisplayRole:
            return None
        
        item = index.internalPointer()
        data = item.get_display_data()
        
        column = index.column()
        if column == 0:
            return data['tag']
        elif column == 1:
            return data['attribs']
        elif column == 2:
            return data['text']
        
        return None
    
    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        """Получает флаги элемента."""
        if not index.isValid():
            return Qt.NoItemFlags
        
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable
    
    def get_element(self, index: QModelIndex) -> Optional[etree.Element]:
        """
        Получает XML элемент по индексу.
        
        Args:
            index: Индекс элемента.
        
        Returns:
            XML элемент или None.
        """
        if not index.isValid():
            return None
        
        item = index.internalPointer()
        return item.get_element()
    
    def get_item(self, index: QModelIndex) -> Optional[SCXTreeItem]:
        """
        Получает элемент дерева по индексу.
        
        Args:
            index: Индекс элемента.
        
        Returns:
            Элемент дерева или None.
        """
        if not index.isValid():
            return None
        
        return index.internalPointer()
