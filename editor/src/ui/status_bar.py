"""
Виджет статусной строки.
"""

import logging

from PySide6.QtWidgets import QStatusBar, QLabel
from PySide6.QtCore import Qt

logger = logging.getLogger(__name__)


class StatusBar(QStatusBar):
    """Статусная строка приложения."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._file_path_label = QLabel("")
        self.addWidget(self._file_path_label, 1)
        
        self._encoding_label = QLabel("")
        self.addPermanentWidget(self._encoding_label)
        
        self._root_tag_label = QLabel("")
        self.addPermanentWidget(self._root_tag_label)
        
        self._changes_label = QLabel("Изменений: 0")
        self.addPermanentWidget(self._changes_label)
        
        self._status_label = QLabel("Готов")
        self.addPermanentWidget(self._status_label)
    
    def set_file_path(self, path: str):
        """Устанавливает путь к файлу."""
        self._file_path_label.setText(f"Файл: {path}" if path else "Файл не открыт")
    
    def set_encoding(self, encoding: str):
        """Устанавливает кодировку."""
        self._encoding_label.setText(f"Кодировка: {encoding}")
    
    def set_root_tag(self, tag: str):
        """Устанавливает корневой тег."""
        self._root_tag_label.setText(f"Корень: {tag}")
    
    def set_changes_count(self, count: int):
        """Устанавливает количество изменений."""
        self._changes_label.setText(f"Изменений: {count}")
    
    def set_status(self, message: str):
        """Устанавливает сообщение статуса."""
        self._status_label.setText(message)
        self.showMessage(message, 5000)
    
    def clear_file_info(self):
        """Очищает информацию о файле."""
        self._file_path_label.setText("")
        self._encoding_label.setText("")
        self._root_tag_label.setText("")
        self._changes_label.setText("Изменений: 0")
