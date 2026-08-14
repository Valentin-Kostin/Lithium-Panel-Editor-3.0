"""
Модель списка файлов для отображения в левой панели.
"""

from typing import List, Optional
from pathlib import Path
from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt, Slot

from ..core.base_handler import FileInfo


class FileListModel(QAbstractListModel):
    """
    Модель списка файлов для QListView.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._files: List[FileInfo] = []
        self._selected_index: Optional[int] = None

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._files)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> any:
        if not index.isValid() or index.row() >= len(self._files):
            return None

        file_info = self._files[index.row()]

        if role == Qt.DisplayRole:
            return file_info.name
        elif role == Qt.ToolTipRole:
            tooltip = f"Файл: {file_info.name}\n"
            tooltip += f"Путь: {file_info.path}\n"
            tooltip += f"Размер: {file_info.size} байт\n"
            tooltip += f"Кодировка: {file_info.encoding or 'N/A'}\n"
            if file_info.error_message:
                tooltip += f"Ошибка: {file_info.error_message}"
            return tooltip
        elif role == Qt.ForegroundRole:
            if not file_info.is_valid:
                from PySide6.QtGui import QColor
                return QColor('red')
        elif role == Qt.UserRole:
            return file_info

        return None

    def set_files(self, files: List[FileInfo]) -> None:
        """Установка списка файлов."""
        self.beginResetModel()
        self._files = files
        self.endResetModel()

    def add_file(self, file_info: FileInfo) -> None:
        """Добавление одного файла."""
        row = len(self._files)
        self.beginInsertRows(QModelIndex(), row, row)
        self._files.append(file_info)
        self.endInsertRows()

    def clear(self) -> None:
        """Очистка списка файлов."""
        self.beginResetModel()
        self._files = []
        self._selected_index = None
        self.endResetModel()

    def get_file_at(self, row: int) -> Optional[FileInfo]:
        """Получение FileInfo по индексу строки."""
        if 0 <= row < len(self._files):
            return self._files[row]
        return None

    def get_selected_file(self) -> Optional[FileInfo]:
        """Получение выбранного файла."""
        if self._selected_index is not None:
            return self.get_file_at(self._selected_index)
        return None

    @Slot(int)
    def set_selected_index(self, index: int) -> None:
        """Установка выбранного индекса."""
        self._selected_index = index

    def get_all_paths(self) -> List[Path]:
        """Получение путей всех файлов."""
        return [f.path for f in self._files if f.is_valid]

    def get_valid_files_count(self) -> int:
        """Получение количества валидных файлов."""
        return sum(1 for f in self._files if f.is_valid)

    def get_invalid_files_count(self) -> int:
        """Получение количества невалидных файлов."""
        return sum(1 for f in self._files if not f.is_valid)
