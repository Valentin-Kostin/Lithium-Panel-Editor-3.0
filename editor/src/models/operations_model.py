"""
Модель операций обработки для таблицы.
Извлекает операции из XML и предоставляет для редактирования.
Поддерживает как SCX (через XML элементы), так и PGMX (через OperationData).
"""

import logging
from typing import Optional, Any, List, Dict, Union
from lxml import etree

from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex

from ..core.base_handler import OperationData as BaseOperationData

logger = logging.getLogger(__name__)


class SCXOperationData:
    """Данные одной SCX операции."""
    
    def __init__(self, element: etree.Element, index: int):
        self.element = element
        self.index = index
        self.data = self._parse_element()
    
    def _parse_element(self) -> Dict[str, Any]:
        """Парсит элемент операции."""
        return {
            'id': self.element.get('ID', str(self.index)),
            'type': self.element.get('Type', 'Unknown'),
            'name': self.element.get('Name', ''),
            'x': self.element.get('X', ''),
            'y': self.element.get('Y', ''),
            'z': self.element.get('Z', ''),
            'depth': self.element.get('Depth', ''),
            'diameter': self.element.get('Diameter', ''),
            'tool_id': self.element.get('ToolID', ''),
            'feed_rate': self.element.get('FeedRate', ''),
            'spindle_speed': self.element.get('SpindleSpeed', ''),
        }
    
    def get_type_display(self) -> str:
        """Получает отображаемое имя типа операции."""
        type_map = {
            'Drill': 'Сверление',
            'Mill': 'Фрезеровка',
            'Cut': 'Раскрой',
            'Pocket': 'Карман',
            'Contour': 'Контур',
            'Engrave': 'Гравировка',
        }
        op_type = self.data.get('type', 'Unknown')
        return type_map.get(op_type, op_type)


class OperationsModel(QAbstractTableModel):
    """Модель операций для QTableView. Поддерживает SCX и PGMX."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._operations: List[Union[SCXOperationData, BaseOperationData]] = []
        self._is_pgmx_mode = False
        self._headers = [
            '№', 'Тип', 'Имя', 'X', 'Y', 'Z', 
            'Глубина', 'Ø', 'Инструмент', 'Подача', 'Обороты'
        ]
    
    def set_root_element(self, root: Optional[etree.Element]):
        """
        Устанавливает корневой элемент и извлекает SCX операции.
        
        Args:
            root: Корневой элемент XML.
        """
        self.beginResetModel()
        self._operations = []
        self._is_pgmx_mode = False
        
        if root is not None:
            self._extract_operations(root)
        
        self.endResetModel()
    
    def set_operations(self, operations: List[BaseOperationData]):
        """
        Устанавливает PGMX операции из handler.
        
        Args:
            operations: Список OperationData из PGMX handler.
        """
        self.beginResetModel()
        self._operations = operations
        self._is_pgmx_mode = True
        self.endResetModel()
    
    def _extract_operations(self, root: etree.Element):
        """Извлекает SCX операции из XML."""
        op_index = 0
        
        for elem in root.iter():
            tag = elem.tag
            if '}' in tag:
                tag = tag.split('}')[1]
            
            if tag.lower() == 'operation':
                op_data = SCXOperationData(elem, op_index)
                self._operations.append(op_data)
                op_index += 1
    
    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Получает количество строк."""
        if parent.isValid():
            return 0
        return len(self._operations)
    
    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Получает количество столбцов."""
        return len(self._headers)
    
    def headerData(self, section: int, orientation: Qt.Orientation,
                   role: int = Qt.DisplayRole) -> Any:
        """Получает заголовок."""
        if role != Qt.DisplayRole:
            return None
        
        if orientation == Qt.Horizontal:
            if 0 <= section < len(self._headers):
                return self._headers[section]
        
        return None
    
    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        """Получает данные ячейки."""
        if not index.isValid():
            return None
        
        if role not in (Qt.DisplayRole, Qt.EditRole):
            return None
        
        operation = self._operations[index.row()]
        col = index.column()
        
        if self._is_pgmx_mode:
            # Режим PGMX - используется BaseOperationData
            if isinstance(operation, BaseOperationData):
                if col == 0:
                    return operation.id
                elif col == 1:
                    return operation.name  # PGMX не имеет типа, использовать имя
                elif col == 2:
                    return operation.name
                elif col == 3:
                    return operation.parameters.get('X', '')
                elif col == 4:
                    return operation.parameters.get('Y', '')
                elif col == 5:
                    return operation.parameters.get('Z', '')
                elif col == 6:
                    return str(operation.depth) if operation.depth else ''
                elif col == 7:
                    return operation.parameters.get('Diameter', '')
                elif col == 8:
                    return operation.tool_id or operation.tool_name
                elif col == 9:
                    return str(operation.feed_rate) if operation.feed_rate else ''
                elif col == 10:
                    return str(operation.speed) if operation.speed else ''
        else:
            # Режим SCX - используется SCXOperationData
            if isinstance(operation, SCXOperationData):
                if col == 0:
                    return operation.data['id']
                elif col == 1:
                    return operation.get_type_display()
                elif col == 2:
                    return operation.data['name']
                elif col == 3:
                    return operation.data['x']
                elif col == 4:
                    return operation.data['y']
                elif col == 5:
                    return operation.data['z']
                elif col == 6:
                    return operation.data['depth']
                elif col == 7:
                    return operation.data['diameter']
                elif col == 8:
                    return operation.data['tool_id']
                elif col == 9:
                    return operation.data['feed_rate']
                elif col == 10:
                    return operation.data['spindle_speed']
        
        return None
    
    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        """Получает флаги ячейки."""
        if not index.isValid():
            return Qt.NoItemFlags
        
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable
    
    def get_operation(self, row: int) -> Optional[Union[SCXOperationData, BaseOperationData]]:
        """
        Получает операцию по строке.
        
        Args:
            row: Номер строки.
        
        Returns:
            OperationData или None.
        """
        if 0 <= row < len(self._operations):
            return self._operations[row]
        return None
    
    def get_element(self, row: int) -> Optional[Any]:
        """
        Получает XML элемент операции (для SCX) или xml_node_ref (для PGMX).
        
        Args:
            row: Номер строки.
        
        Returns:
            XML элемент или None.
        """
        op = self.get_operation(row)
        if op is None:
            return None
        
        if self._is_pgmx_mode and isinstance(op, BaseOperationData):
            return op.xml_node_ref
        elif isinstance(op, SCXOperationData):
            return op.element
        return None
    
    def operation_count(self) -> int:
        """Получает количество операций."""
        return len(self._operations)
    
    def clear(self):
        """Очищает модель."""
        self.beginResetModel()
        self._operations = []
        self._is_pgmx_mode = False
        self.endResetModel()
