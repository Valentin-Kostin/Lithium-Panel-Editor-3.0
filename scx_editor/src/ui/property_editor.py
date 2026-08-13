"""
Редактор свойств XML элементов.
"""

import logging
from typing import Optional, Dict, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLabel, 
    QLineEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QGroupBox
)
from PySide6.QtCore import Qt, Signal
from lxml import etree

logger = logging.getLogger(__name__)


class PropertyEditor(QWidget):
    """Виджет редактирования свойств элемента."""
    
    value_changed = Signal(str, str, str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_element: Optional[etree.Element] = None
        self._attribute_inputs: Dict[str, QLineEdit] = {}
        
        self._init_ui()
    
    def _init_ui(self):
        """Инициализирует UI."""
        layout = QVBoxLayout(self)
        
        element_group = QGroupBox("Элемент")
        element_layout = QFormLayout()
        
        self._tag_label = QLabel("")
        element_layout.addRow("Тег:", self._tag_label)
        
        self._path_label = QLabel("")
        element_layout.addRow("Путь:", self._path_label)
        
        element_group.setLayout(element_layout)
        layout.addWidget(element_group)
        
        attributes_group = QGroupBox("Атрибуты")
        self._attributes_layout = QFormLayout()
        attributes_group.setLayout(self._attributes_layout)
        layout.addWidget(attributes_group)
        
        text_group = QGroupBox("Текст")
        text_layout = QVBoxLayout()
        
        self._text_edit = QLineEdit()
        self._text_edit.textChanged.connect(self._on_text_changed)
        text_layout.addWidget(self._text_edit)
        
        text_group.setLayout(text_layout)
        layout.addWidget(text_group)
        
        layout.addStretch()
    
    def set_element(self, element: Optional[etree.Element]):
        """
        Устанавливает элемент для редактирования.
        
        Args:
            element: XML элемент.
        """
        self._current_element = element
        self._clear_form()
        
        if element is None:
            self._tag_label.setText("")
            self._path_label.setText("")
            return
        
        tag = element.tag
        if '}' in tag:
            tag = tag.split('}')[1]
        
        self._tag_label.setText(tag)
        
        tree = element.getroottree()
        path = tree.getpath(element)
        self._path_label.setText(path)
        
        self._populate_attributes(element)
        
        text = (element.text or '').strip()
        self._text_edit.blockSignals(True)
        self._text_edit.setText(text)
        self._text_edit.blockSignals(False)
    
    def _clear_form(self):
        """Очищает форму."""
        self._attribute_inputs.clear()
        
        while self._attributes_layout.count():
            item = self._attributes_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
    
    def _populate_attributes(self, element: etree.Element):
        """Заполняет атрибуты."""
        for attr_name, attr_value in sorted(element.attrib.items()):
            label = QLabel(f"{attr_name}:")
            edit = QLineEdit(attr_value)
            edit.textChanged.connect(
                lambda val, name=attr_name: self._on_attribute_changed(name, val)
            )
            
            self._attributes_layout.addRow(label, edit)
            self._attribute_inputs[attr_name] = edit
    
    def _on_attribute_changed(self, attr_name: str, new_value: str):
        """Обрабатывает изменение атрибута."""
        if self._current_element is not None:
            old_value = self._current_element.get(attr_name, '')
            self.value_changed.emit(attr_name, old_value, new_value)
    
    def _on_text_changed(self, new_text: str):
        """Обрабатывает изменение текста."""
        if self._current_element is not None:
            old_text = (self._current_element.text or '').strip()
            self.value_changed.emit('text', old_text, new_text)
    
    def get_current_element(self) -> Optional[etree.Element]:
        """Получает текущий элемент."""
        return self._current_element
