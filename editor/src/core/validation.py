"""
Модуль валидации XML и значений параметров.
"""

import logging
from typing import Tuple, Optional, Any, List
from lxml import etree

logger = logging.getLogger(__name__)


class ValidationUtils:
    """Утилиты валидации."""
    
    @staticmethod
    def validate_xml_wellformed(tree: etree.ElementTree) -> Tuple[bool, Optional[str]]:
        """
        Проверяет, является ли XML well-formed.
        
        Args:
            tree: XML дерево.
        
        Returns:
            Кортеж (валидно, сообщение об ошибке).
        """
        try:
            root = tree.getroot()
            etree.tostring(root, encoding='utf-8')
            return True, None
        except Exception as e:
            return False, f"XML не является well-formed: {e}"
    
    @staticmethod
    def validate_numeric_value(value: Any, field_type: str, 
                                min_val: Optional[float] = None,
                                max_val: Optional[float] = None) -> Tuple[bool, Optional[str]]:
        """
        Проверяет числовое значение.
        
        Args:
            value: Значение для проверки.
            field_type: Тип поля ('int' или 'float').
            min_val: Минимальное допустимое значение.
            max_val: Максимальное допустимое значение.
        
        Returns:
            Кортеж (валидно, сообщение об ошибке).
        """
        if value is None or value == '':
            return True, None
        
        try:
            if field_type == 'int':
                num_value = int(value)
            elif field_type == 'float':
                num_value = float(value)
            else:
                return True, None
            
            if min_val is not None and num_value < min_val:
                return False, f"Значение {num_value} меньше минимального {min_val}"
            
            if max_val is not None and num_value > max_val:
                return False, f"Значение {num_value} больше максимального {max_val}"
            
            return True, None
            
        except (ValueError, TypeError) as e:
            return False, f"Некорректный формат числа: {value}"
    
    @staticmethod
    def validate_positive(value: Any, allow_zero: bool = False) -> Tuple[bool, Optional[str]]:
        """
        Проверяет, что значение положительное.
        
        Args:
            value: Значение для проверки.
            allow_zero: Разрешить ли ноль.
        
        Returns:
            Кортеж (валидно, сообщение об ошибке).
        """
        try:
            num_value = float(value)
            
            if allow_zero:
                if num_value < 0:
                    return False, "Значение должно быть неотрицательным"
            else:
                if num_value <= 0:
                    return False, "Значение должно быть положительным"
            
            return True, None
            
        except (ValueError, TypeError):
            return False, "Значение должно быть числом"
    
    @staticmethod
    def validate_coordinate(value: Any) -> Tuple[bool, Optional[str]]:
        """
        Проверяет координатное значение (может быть отрицательным).
        
        Args:
            value: Значение для проверки.
        
        Returns:
            Кортеж (валидно, сообщение об ошибке).
        """
        try:
            float(value)
            return True, None
        except (ValueError, TypeError):
            return False, "Координата должна быть числом"
    
    @staticmethod
    def validate_required(value: Any, field_name: str) -> Tuple[bool, Optional[str]]:
        """
        Проверяет, что обязательное поле не пустое.
        
        Args:
            value: Значение для проверки.
            field_name: Имя поля.
        
        Returns:
            Кортеж (валидно, сообщение об ошибке).
        """
        if value is None or value == '':
            return False, f"Поле '{field_name}' обязательно для заполнения"
        return True, None
    
    @staticmethod
    def validate_range(value: Any, min_val: float, max_val: float, 
                       field_name: str) -> Tuple[bool, Optional[str]]:
        """
        Проверяет, что значение в диапазоне.
        
        Args:
            value: Значение для проверки.
            min_val: Минимум.
            max_val: Максимум.
            field_name: Имя поля.
        
        Returns:
            Кортеж (валидно, сообщение об ошибке).
        """
        try:
            num_value = float(value)
            
            if num_value < min_val or num_value > max_val:
                return False, f"Значение должно быть в диапазоне от {min_val} до {max_val}"
            
            return True, None
            
        except (ValueError, TypeError):
            return False, f"Значение должно быть числом"
