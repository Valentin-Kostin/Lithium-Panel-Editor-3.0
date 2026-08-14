"""
Модуль вычисления различий (diff) между состояниями XML.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ChangeType(Enum):
    """Тип изменения."""
    ATTRIBUTE_CHANGED = "attribute_changed"
    TEXT_CHANGED = "text_changed"
    ELEMENT_ADDED = "element_added"
    ELEMENT_REMOVED = "element_removed"
    ATTRIBUTE_ADDED = "attribute_added"
    ATTRIBUTE_REMOVED = "attribute_removed"


@dataclass
class Change:
    """Описание одного изменения."""
    change_type: ChangeType
    element_path: str
    element_tag: str
    attribute_name: Optional[str] = None
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразует в словарь."""
        return {
            'type': self.change_type.value,
            'path': self.element_path,
            'tag': self.element_tag,
            'attribute': self.attribute_name,
            'old_value': self.old_value,
            'new_value': self.new_value,
        }


class DiffUtils:
    """Утилиты для вычисления различий."""
    
    @staticmethod
    def compare_attributes(old_attrib: Dict[str, str], new_attrib: Dict[str, str],
                           element_path: str, element_tag: str) -> List[Change]:
        """
        Сравнивает атрибуты двух элементов.
        
        Args:
            old_attrib: Старые атрибуты.
            new_attrib: Новые атрибуты.
            element_path: XPath элемента.
            element_tag: Тег элемента.
        
        Returns:
            Список изменений.
        """
        changes = []
        
        all_keys = set(old_attrib.keys()) | set(new_attrib.keys())
        
        for key in all_keys:
            old_val = old_attrib.get(key)
            new_val = new_attrib.get(key)
            
            if old_val != new_val:
                if key in old_attrib and key in new_attrib:
                    changes.append(Change(
                        change_type=ChangeType.ATTRIBUTE_CHANGED,
                        element_path=element_path,
                        element_tag=element_tag,
                        attribute_name=key,
                        old_value=old_val,
                        new_value=new_val,
                    ))
                elif key not in old_attrib:
                    changes.append(Change(
                        change_type=ChangeType.ATTRIBUTE_ADDED,
                        element_path=element_path,
                        element_tag=element_tag,
                        attribute_name=key,
                        old_value=None,
                        new_value=new_val,
                    ))
                else:
                    changes.append(Change(
                        change_type=ChangeType.ATTRIBUTE_REMOVED,
                        element_path=element_path,
                        element_tag=element_tag,
                        attribute_name=key,
                        old_value=old_val,
                        new_value=None,
                    ))
        
        return changes
    
    @staticmethod
    def compare_text(old_text: Optional[str], new_text: Optional[str],
                     element_path: str, element_tag: str) -> List[Change]:
        """
        Сравнивает текстовое содержимое.
        
        Args:
            old_text: Старый текст.
            new_text: Новый текст.
            element_path: XPath элемента.
            element_tag: Тег элемента.
        
        Returns:
            Список изменений.
        """
        old_stripped = (old_text or '').strip()
        new_stripped = (new_text or '').strip()
        
        if old_stripped != new_stripped:
            return [Change(
                change_type=ChangeType.TEXT_CHANGED,
                element_path=element_path,
                element_tag=element_tag,
                old_value=old_stripped or None,
                new_value=new_stripped or None,
            )]
        
        return []
    
    @staticmethod
    def create_change_summary(changes: List[Change]) -> str:
        """
        Создаёт краткое описание изменений на русском языке.
        
        Args:
            changes: Список изменений.
        
        Returns:
            Строка с описанием.
        """
        if not changes:
            return "Изменений нет"
        
        summary_parts = []
        
        attr_changes = [c for c in changes if c.change_type == ChangeType.ATTRIBUTE_CHANGED]
        text_changes = [c for c in changes if c.change_type == ChangeType.TEXT_CHANGED]
        added_attrs = [c for c in changes if c.change_type == ChangeType.ATTRIBUTE_ADDED]
        removed_attrs = [c for c in changes if c.change_type == ChangeType.ATTRIBUTE_REMOVED]
        
        if attr_changes:
            summary_parts.append(f"Изменено атрибутов: {len(attr_changes)}")
        if text_changes:
            summary_parts.append(f"Изменено текста: {len(text_changes)}")
        if added_attrs:
            summary_parts.append(f"Добавлено атрибутов: {len(added_attrs)}")
        if removed_attrs:
            summary_parts.append(f"Удалено атрибутов: {len(removed_attrs)}")
        
        return "; ".join(summary_parts)
    
    @staticmethod
    def format_change_for_display(change: Change, language: str = 'ru') -> str:
        """
        Форматирует изменение для отображения пользователю.
        
        Args:
            change: Изменение.
            language: Язык ('ru' или 'en').
        
        Returns:
            Отформатированная строка.
        """
        if language == 'en':
            type_descriptions = {
                ChangeType.ATTRIBUTE_CHANGED: "Attribute changed",
                ChangeType.TEXT_CHANGED: "Text changed",
                ChangeType.ELEMENT_ADDED: "Element added",
                ChangeType.ELEMENT_REMOVED: "Element removed",
                ChangeType.ATTRIBUTE_ADDED: "Attribute added",
                ChangeType.ATTRIBUTE_REMOVED: "Attribute removed",
            }
        else:
            type_descriptions = {
                ChangeType.ATTRIBUTE_CHANGED: "Изменён атрибут",
                ChangeType.TEXT_CHANGED: "Изменён текст",
                ChangeType.ELEMENT_ADDED: "Добавлен элемент",
                ChangeType.ELEMENT_REMOVED: "Удалён элемент",
                ChangeType.ATTRIBUTE_ADDED: "Добавлен атрибут",
                ChangeType.ATTRIBUTE_REMOVED: "Удалён атрибут",
            }
        
        change_type_desc = type_descriptions.get(change.change_type, str(change.change_type))
        
        if change.attribute_name:
            detail = f"{change.element_tag}/@{change.attribute_name}"
        else:
            detail = change.element_tag
        
        return (f"{change_type_desc}: {detail}\n"
                f"  Путь: {change.element_path}\n"
                f"  Было: {change.old_value}\n"
                f"  Стало: {change.new_value}")
