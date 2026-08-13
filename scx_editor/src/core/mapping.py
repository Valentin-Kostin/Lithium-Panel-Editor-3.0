"""
Модуль работы с маппингом параметров SCX.
Загрузка, применение XPath, поиск параметров.
"""

import json
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

from lxml import etree

logger = logging.getLogger(__name__)


class MappingField:
    """Описание одного поля маппинга."""
    
    def __init__(self, data: Dict[str, Any]):
        self.id = data.get('id', '')
        self.label_ru = data.get('label_ru', '')
        self.label_en = data.get('label_en', '')
        self.field_type = data.get('type', 'string')
        self.unit = data.get('unit', '')
        self.min_value = data.get('min')
        self.max_value = data.get('max')
        self.step = data.get('step')
        self.xpath = data.get('xpath', '')
    
    def get_label(self, language: str = 'ru') -> str:
        """Получает метку на нужном языке."""
        if language == 'en':
            return self.label_en or self.label_ru
        return self.label_ru or self.label_en
    
    def validate_value(self, value: Any) -> tuple[bool, Optional[str]]:
        """
        Проверяет значение на корректность.
        
        Returns:
            Кортеж (валидно, сообщение об ошибке).
        """
        if value is None or value == '':
            return True, None
        
        try:
            if self.field_type == 'int':
                num_value = int(value)
            elif self.field_type == 'float':
                num_value = float(value)
            else:
                return True, None
            
            if self.min_value is not None and num_value < self.min_value:
                return False, f"Значение {num_value} меньше минимального {self.min_value}"
            
            if self.max_value is not None and num_value > self.max_value:
                return False, f"Значение {num_value} больше максимального {self.max_value}"
            
            return True, None
            
        except (ValueError, TypeError):
            return False, f"Некорректный формат числа: {value}"


class MappingConfig:
    """Конфигурация маппинга параметров."""
    
    def __init__(self, config_path: Optional[Path] = None):
        self.version = 1
        self.description = ''
        self.namespaces: Dict[str, str] = {}
        self.fields: List[MappingField] = []
        
        if config_path:
            self.load(config_path)
    
    def load(self, config_path: Path) -> bool:
        """
        Загружает конфигурацию из JSON файла.
        
        Args:
            config_path: Путь к файлу конфигурации.
        
        Returns:
            True если успешно.
        """
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.version = data.get('version', 1)
            self.description = data.get('description', '')
            self.namespaces = data.get('namespaces', {})
            
            fields_data = data.get('fields', [])
            self.fields = [MappingField(fd) for fd in fields_data]
            
            logger.info(f"Маппинг загружен: {len(self.fields)} полей")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка загрузки маппинга: {e}")
            return False
    
    def save(self, config_path: Path) -> bool:
        """
        Сохраняет конфигурацию в JSON файл.
        
        Args:
            config_path: Путь к файлу.
        
        Returns:
            True если успешно.
        """
        try:
            data = {
                'version': self.version,
                'description': self.description,
                'namespaces': self.namespaces,
                'fields': [
                    {
                        'id': f.id,
                        'label_ru': f.label_ru,
                        'label_en': f.label_en,
                        'type': f.field_type,
                        'unit': f.unit,
                        'min': f.min_value,
                        'max': f.max_value,
                        'step': f.step,
                        'xpath': f.xpath,
                    }
                    for f in self.fields
                ]
            }
            
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Маппинг сохранён: {config_path}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка сохранения маппинга: {e}")
            return False
    
    def find_values(self, tree: etree.ElementTree, field: MappingField) -> List[tuple]:
        """
        Находит значения поля в XML дереве.
        
        Args:
            tree: XML дерево.
            field: Поле маппинга.
        
        Returns:
            Список кортежей (элемент, атрибут_или_текст, текущее_значение).
        """
        results = []
        
        if not field.xpath:
            return results
        
        namespaces = self.namespaces.copy()
        root = tree.getroot()
        for prefix, uri in root.nsmap.items():
            if prefix is not None and uri is not None:
                namespaces[prefix] = uri
        
        try:
            elements = tree.xpath(field.xpath, namespaces=namespaces)
            
            for elem in elements:
                if isinstance(elem, etree._Element):
                    if '@' in field.xpath.split('/')[-1]:
                        attr_name = field.xpath.split('@')[-1].split('|')[0].split(']')[0]
                        if attr_name in elem.attrib:
                            results.append((elem, attr_name, elem.attrib[attr_name]))
                    else:
                        text_val = (elem.text or '').strip()
                        results.append((elem, 'text', text_val))
                        
        except Exception as e:
            logger.warning(f"Ошибка поиска по XPath '{field.xpath}': {e}")
        
        return results
    
    def get_field_by_id(self, field_id: str) -> Optional[MappingField]:
        """Получает поле по ID."""
        for field in self.fields:
            if field.id == field_id:
                return field
        return None
    
    def add_field(self, field_data: Dict[str, Any]) -> MappingField:
        """Добавляет новое поле."""
        field = MappingField(field_data)
        self.fields.append(field)
        return field
    
    def remove_field(self, field_id: str) -> bool:
        """Удаляет поле по ID."""
        for i, field in enumerate(self.fields):
            if field.id == field_id:
                self.fields.pop(i)
                return True
        return False
