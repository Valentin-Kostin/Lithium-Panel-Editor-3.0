"""
Команды для системы Undo/Redo.
"""

import logging
from typing import Optional, Any, Protocol
from lxml import etree

logger = logging.getLogger(__name__)


class UndoCommand(Protocol):
    """Протокол команды undo/redo."""
    
    def undo(self) -> None:
        """Отменяет команду."""
        ...
    
    def redo(self) -> None:
        """Повторяет команду."""
        ...


class SetAttributeCommand:
    """Команда установки атрибута."""
    
    def __init__(self, element: etree.Element, attr_name: str, 
                 old_value: Optional[str], new_value: Optional[str]):
        self.element = element
        self.attr_name = attr_name
        self.old_value = old_value
        self.new_value = new_value
        self._was_removed = old_value is None and attr_name in (element.attrib if hasattr(element, 'attrib') else {})
    
    def undo(self) -> None:
        """Отменяет установку атрибута."""
        if self.old_value is None:
            if self.attr_name in self.element.attrib:
                del self.element.attrib[self.attr_name]
        else:
            self.element.set(self.attr_name, self.old_value)
        logger.debug(f"Undo: {self.element.tag}/@{self.attr_name} = {self.old_value}")
    
    def redo(self) -> None:
        """Повторяет установку атрибута."""
        if self.new_value is None:
            if self.attr_name in self.element.attrib:
                del self.element.attrib[self.attr_name]
        else:
            self.element.set(self.attr_name, self.new_value)
        logger.debug(f"Redo: {self.element.tag}/@{self.attr_name} = {self.new_value}")


class SetTextCommand:
    """Команда установки текста."""
    
    def __init__(self, element: etree.Element, old_text: Optional[str], 
                 new_text: Optional[str]):
        self.element = element
        self.old_text = old_text
        self.new_text = new_text
    
    def undo(self) -> None:
        """Отменяет установку текста."""
        self.element.text = self.old_text
        logger.debug(f"Undo: {self.element.tag}.text = {self.old_text}")
    
    def redo(self) -> None:
        """Повторяет установку текста."""
        self.element.text = self.new_text
        logger.debug(f"Redo: {self.element.tag}.text = {self.new_text}")


class UndoStack:
    """Стек отмены/повтора команд."""
    
    def __init__(self, max_size: int = 100):
        self._undo_stack: list[UndoCommand] = []
        self._redo_stack: list[UndoCommand] = []
        self.max_size = max_size
    
    def push(self, command: UndoCommand):
        """
        Добавляет команду в стек.
        
        Args:
            command: Команда для выполнения.
        """
        self._undo_stack.append(command)
        self._redo_stack.clear()
        
        if len(self._undo_stack) > self.max_size:
            self._undo_stack.pop(0)
    
    def undo(self) -> bool:
        """
        Отменяет последнюю команду.
        
        Returns:
            True если команда была отменена.
        """
        if not self._undo_stack:
            return False
        
        command = self._undo_stack.pop()
        command.undo()
        self._redo_stack.append(command)
        return True
    
    def redo(self) -> bool:
        """
        Повторяет отменённую команду.
        
        Returns:
            True если команда была повторена.
        """
        if not self._redo_stack:
            return False
        
        command = self._redo_stack.pop()
        command.redo()
        self._undo_stack.append(command)
        return True
    
    def clear(self):
        """Очищает стеки."""
        self._undo_stack.clear()
        self._redo_stack.clear()
    
    def can_undo(self) -> bool:
        """Проверяет, можно ли отменить."""
        return len(self._undo_stack) > 0
    
    def can_redo(self) -> bool:
        """Проверяет, можно ли повторить."""
        return len(self._redo_stack) > 0
    
    def undo_count(self) -> int:
        """Получает количество доступных undo."""
        return len(self._undo_stack)
    
    def redo_count(self) -> int:
        """Получает количество доступных redo."""
        return len(self._redo_stack)
