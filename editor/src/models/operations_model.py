"""
Модель таблицы операций для отображения и редактирования данных.
"""

from typing import List, Optional, Any
from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt, Signal
from PySide6.QtGui import QColor

from ..core.base_handler import OperationRow


class OperationsTableModel(QAbstractTableModel):
    """
    Модель таблицы операций для QTableView.
    Отображает: Название операции, Тип, Z, Диаметр, Глубина
    """

    # Сигналы
    data_changed_signal = Signal(int, str, object)  # row, field, value
    operation_selected = Signal(int)  # row

    # Заголовки столбцов - только нужные колонки
    HEADERS = ['№', 'Файл', 'Имя операции', 'Тип', 'Z', 'Диаметр', 'Глубина']
    
    # Индексы столбцов
    COL_ID = 0
    COL_FILE = 1
    COL_NAME = 2
    COL_TYPE = 3
    COL_Z = 4
    COL_DIAMETER = 5
    COL_DEPTH = 6

    def __init__(self, parent=None):
        super().__init__(parent)
        self._operations: List[OperationRow] = []
        self._editable_columns = {
            self.COL_Z,
            self.COL_DIAMETER, self.COL_DEPTH
        }

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._operations)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self.HEADERS)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole) -> any:
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.HEADERS[section]
        elif role == Qt.TextAlignmentRole:
            return Qt.AlignCenter
        return None

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> any:
        if not index.isValid() or index.row() >= len(self._operations):
            return None

        operation = self._operations[index.row()]
        column = index.column()

        if role == Qt.DisplayRole or role == Qt.EditRole:
            if column == self.COL_ID:
                return operation.id
            elif column == self.COL_FILE:
                # Показываем имя файла из атрибута _source_file если есть
                source_file = getattr(operation, '_source_file', None)
                if source_file:
                    return source_file.name if hasattr(source_file, 'name') else str(source_file)
                return operation.file_name
            elif column == self.COL_NAME:
                return operation.operation_name
            elif column == self.COL_TYPE:
                return operation.operation_type
            elif column == self.COL_Z:
                return f"{operation.z:.3f}" if operation.z is not None else ""
            elif column == self.COL_DIAMETER:
                return f"{operation.diameter:.3f}" if operation.diameter is not None else ""
            elif column == self.COL_DEPTH:
                return f"{operation.depth:.3f}" if operation.depth is not None else ""

        elif role == Qt.TextAlignmentRole:
            if column in {self.COL_Z, self.COL_DIAMETER, self.COL_DEPTH}:
                return Qt.AlignRight | Qt.AlignVCenter
            return Qt.AlignLeft | Qt.AlignVCenter

        elif role == Qt.BackgroundRole:
            if operation.is_modified:
                return QColor(255, 255, 200)  # Светло-жёлтый для изменённых
            return None

        elif role == Qt.ToolTipRole:
            tooltip = f"Операция #{operation.id}\n"
            tooltip += f"Имя: {operation.operation_name}\n"
            tooltip += f"Тип: {operation.operation_type}\n"
            source_file = getattr(operation, '_source_file', None)
            if source_file:
                tooltip += f"Файл: {source_file.name if hasattr(source_file, 'name') else str(source_file)}\n"
            if operation.z is not None:
                tooltip += f"Z: {operation.z:.3f}\n"
            if operation.diameter is not None:
                tooltip += f"Диаметр: {operation.diameter:.3f}\n"
            if operation.depth is not None:
                tooltip += f"Глубина: {operation.depth:.3f}"
            return tooltip

        return None

    def setData(self, index: QModelIndex, value: Any, role: int = Qt.EditRole) -> bool:
        if not index.isValid() or index.row() >= len(self._operations):
            return False

        if role != Qt.EditRole:
            return False

        operation = self._operations[index.row()]
        column = index.column()

        # Проверка возможности редактирования
        if column not in self._editable_columns:
            return False

        # Парсинг значения
        try:
            if value == "" or value is None:
                new_value = None
            else:
                new_value = float(value)
        except (ValueError, TypeError):
            return False

        # Обновление значения
        old_value = None
        if column == self.COL_Z:
            old_value = operation.z
            operation.z = new_value
        elif column == self.COL_DIAMETER:
            old_value = operation.diameter
            operation.diameter = new_value
        elif column == self.COL_DEPTH:
            old_value = operation.depth
            operation.depth = new_value

        # Пометка как изменённое если значение действительно изменилось
        if old_value != new_value:
            operation.is_modified = True
            self.data_changed_signal.emit(operation.id, self.HEADERS[column], new_value)

        # Уведомление об изменении данных
        self.dataChanged.emit(index, index, [Qt.DisplayRole, Qt.BackgroundRole])
        return True

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        if not index.isValid():
            return Qt.NoItemFlags

        base_flags = Qt.ItemIsEnabled | Qt.ItemIsSelectable

        if index.column() in self._editable_columns:
            base_flags |= Qt.ItemIsEditable

        return base_flags

    def set_operations(self, operations: List[OperationRow]) -> None:
        """Установка списка операций."""
        self.beginResetModel()
        self._operations = operations
        self.endResetModel()

    def add_operation(self, operation: OperationRow) -> None:
        """Добавление одной операции."""
        row = len(self._operations)
        self.beginInsertRows(QModelIndex(), row, row)
        self._operations.append(operation)
        self.endInsertRows()

    def clear(self) -> None:
        """Очистка списка операций."""
        self.beginResetModel()
        self._operations = []
        self.endResetModel()

    def get_operation_at(self, row: int) -> Optional[OperationRow]:
        """Получение операции по индексу строки."""
        if 0 <= row < len(self._operations):
            return self._operations[row]
        return None

    def get_all_operations(self) -> List[OperationRow]:
        """Получение всех операций."""
        return self._operations.copy()

    def get_modified_operations(self) -> List[OperationRow]:
        """Получение только изменённых операций."""
        return [op for op in self._operations if op.is_modified]

    def has_modifications(self) -> bool:
        """Проверка наличия изменённых операций."""
        return any(op.is_modified for op in self._operations)

    def reset_modifications(self) -> None:
        """Сброс флага модификации у всех операций."""
        for op in self._operations:
            op.is_modified = False
        
        # Обновление фона всей таблицы
        top_left = self.index(0, 0)
        bottom_right = self.index(len(self._operations) - 1, self.columnCount() - 1)
        self.dataChanged.emit(top_left, bottom_right, [Qt.BackgroundRole])

    def filter_by_type(self, operation_type: str) -> None:
        """
        Фильтрация операций по типу.
        TODO: Реализовать полноценную фильтрацию с proxy model.
        """
        pass

    def search_by_name(self, search_text: str) -> List[int]:
        """
        Поиск операций по имени.
        
        Returns:
            Список индексов строк соответствующих поиску.
        """
        if not search_text:
            return list(range(len(self._operations)))
        
        results = []
        search_lower = search_text.lower()
        for i, op in enumerate(self._operations):
            if search_lower in op.operation_name.lower():
                results.append(i)
        return results
