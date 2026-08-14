"""
Модуль управления SCX документом.
Загрузка, сохранение, редактирование параметров.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from copy import deepcopy

from lxml import etree

from .xml_utils import XMLUtils
from .encoding_detector import detect_and_validate, extract_xml_declaration_encoding
from .mapping import MappingConfig, MappingField
from .diff import DiffUtils, Change
from .backup import BackupUtils

logger = logging.getLogger(__name__)


class SCXDocument:
    """Класс для работы с SCX документом."""
    
    def __init__(self):
        self.file_path: Optional[Path] = None
        self.tree: Optional[etree.ElementTree] = None
        self.encoding: str = 'utf-8'
        self.original_content: Optional[bytes] = None
        self.mapping: Optional[MappingConfig] = None
        self.is_modified: bool = False
        self.is_read_only: bool = False
        self.error_message: Optional[str] = None
        
        self._original_states: Dict[str, Dict[str, Any]] = {}
    
    def load(self, file_path: Path, mapping_config: Optional[MappingConfig] = None) -> Tuple[bool, Optional[str]]:
        """
        Загружает SCX файл.
        
        Args:
            file_path: Путь к файлу.
            mapping_config: Конфигурация маппинга.
        
        Returns:
            Кортеж (успешно, сообщение об ошибке).
        """
        self.file_path = file_path
        self.mapping = mapping_config
        
        xml_encoding_hint = extract_xml_declaration_encoding(file_path)
        self.encoding, message, is_valid = detect_and_validate(file_path)
        
        if not is_valid:
            self.is_read_only = True
            self.error_message = message
            logger.warning(f"Файл открыт в режиме только для чтения: {message}")
        
        with open(file_path, 'rb') as f:
            self.original_content = f.read()
        
        tree, error = XMLUtils.safe_parse(file_path, self.encoding)
        
        if error:
            self.is_read_only = True
            self.error_message = error
            logger.error(f"Ошибка парсинга: {error}")
            return False, error
        
        self.tree = tree
        self.is_modified = False
        self.is_read_only = False
        self.error_message = None
        
        self._save_original_state()
        
        logger.info(f"SCX файл загружен: {file_path}")
        return True, None
    
    def _save_original_state(self):
        """Сохраняет оригинальное состояние для diff."""
        if self.tree is None:
            return
        
        root = self.tree.getroot()
        self._original_states = {
            'root_tag': root.tag,
            'attrib': deepcopy(dict(root.attrib)),
        }
    
    def get_root_element(self) -> Optional[etree.Element]:
        """Получает корневой элемент."""
        if self.tree is None:
            return None
        return self.tree.getroot()
    
    def get_tree(self) -> Optional[etree.ElementTree]:
        """Получает XML дерево."""
        return self.tree
    
    def get_xml_tree(self) -> Optional[etree.ElementTree]:
        """Получает XML дерево (алиас для совместимости)."""
        return self.get_tree()
    
    def get_operations(self) -> List[Dict[str, Any]]:
        """
        Извлекает список операций из SCX документа.
        
        Returns:
            Список словарей с параметрами операций.
        """
        if self.tree is None:
            return []
        
        operations = []
        root = self.tree.getroot()
        
        # Ищем секцию Operations
        ops_element = root.find('Operations')
        if ops_element is None:
            logger.warning("Секция Operations не найдена")
            return []
        
        # Извлекаем каждую операцию
        for op in ops_element.findall('Operation'):
            op_data = {
                'id': op.get('ID', ''),
                'type': op.get('Type', ''),
                'tool_id': op.get('ToolID', ''),
                'x': op.get('X', '0'),
                'y': op.get('Y', '0'),
                'z': op.get('Z', '0'),
                'depth': op.get('Depth', '0'),
                'feed_rate': op.get('FeedRate', ''),
                'element': op  # Сохраняем ссылку на элемент для редактирования
            }
            operations.append(op_data)
        
        logger.info(f"Найдено операций: {len(operations)}")
        return operations
    
    def find_by_xpath(self, xpath: str) -> List[etree.Element]:
        """
        Находит элементы по XPath.
        
        Args:
            xpath: XPath выражение.
        
        Returns:
            Список элементов.
        """
        if self.tree is None:
            return []
        
        namespaces = None
        if self.mapping and self.mapping.namespaces:
            namespaces = self.mapping.namespaces
        
        return XMLUtils.find_elements(self.tree, xpath, namespaces)
    
    def get_mapped_values(self, field: MappingField) -> List[Tuple[etree.Element, str, str]]:
        """
        Получает значения поля из маппинга.
        
        Args:
            field: Поле маппинга.
        
        Returns:
            Список кортежей (элемент, атрибут, значение).
        """
        if self.tree is None or self.mapping is None:
            return []
        
        return self.mapping.find_values(self.tree, field)
    
    def set_attribute(self, element: etree.Element, attr_name: str, value: str) -> bool:
        """
        Устанавливает атрибут элемента.
        
        Args:
            element: Элемент.
            attr_name: Имя атрибута.
            value: Значение.
        
        Returns:
            True если успешно.
        """
        if self.is_read_only:
            logger.warning("Документ в режиме только для чтения")
            return False
        
        old_value = element.get(attr_name)
        element.set(attr_name, value)
        self.is_modified = True
        
        logger.info(f"Атрибут изменён: {element.tag}/@{attr_name} = {old_value} -> {value}")
        return True
    
    def set_text(self, element: etree.Element, text: str) -> bool:
        """
        Устанавливает текстовое содержимое элемента.
        
        Args:
            element: Элемент.
            text: Текст.
        
        Returns:
            True если успешно.
        """
        if self.is_read_only:
            logger.warning("Документ в режиме только для чтения")
            return False
        
        old_text = (element.text or '').strip()
        element.text = text
        self.is_modified = True
        
        logger.info(f"Текст изменён: {element.tag} = {old_text} -> {text}")
        return True
    
    def get_changes(self) -> List[Change]:
        """
        Получает список изменений с момента загрузки.
        
        Returns:
            Список изменений.
        """
        if self.tree is None:
            return []
        
        changes = []
        root = self.tree.getroot()
        path = self.tree.getpath(root)
        
        current_attrib = dict(root.attrib)
        original_attrib = self._original_states.get('attrib', {})
        
        attr_changes = DiffUtils.compare_attributes(
            original_attrib, current_attrib, path, root.tag
        )
        changes.extend(attr_changes)
        
        return changes
    
    def save(self, create_backup: bool = True, backup_format: str = 'timestamp',
             pretty_print: bool = False) -> Tuple[bool, Optional[str]]:
        """
        Сохраняет файл.
        
        Args:
            create_backup: Создать ли резервную копию.
            backup_format: Формат имени копии.
            pretty_print: Форматировать ли вывод.
        
        Returns:
            Кортеж (успешно, сообщение об ошибке).
        """
        if self.tree is None or self.file_path is None:
            return False, "Документ не загружен"
        
        if self.is_read_only:
            return False, "Документ в режиме только для чтения"
        
        if not self.is_modified:
            logger.info("Изменений нет, файл не будет перезаписан")
            return True, "Изменений нет"
        
        if create_backup:
            backup_path = BackupUtils.create_backup(self.file_path, backup_format)
            if backup_path is None:
                return False, "Не удалось создать резервную копию"
            logger.info(f"Резервная копия: {backup_path}")
        
        is_valid, error = DiffUtils.validate_xml_wellformed(self.tree) if hasattr(DiffUtils, 'validate_xml_wellformed') else (True, None)
        if not is_valid:
            return False, f"XML невалиден: {error}"
        
        success = XMLUtils.save_tree(
            self.tree, 
            self.file_path, 
            self.encoding,
            xml_declaration=True,
            pretty_print=pretty_print,
        )
        
        if success:
            self.is_modified = False
            self._save_original_state()
            logger.info(f"Файл сохранён: {self.file_path}")
            return True, None
        else:
            return False, "Ошибка сохранения файла"
    
    def save_as(self, new_path: Path, create_backup: bool = False,
                pretty_print: bool = False) -> Tuple[bool, Optional[str]]:
        """
        Сохраняет файл под новым именем.
        
        Args:
            new_path: Новый путь.
            create_backup: Создать ли резервную копию.
            pretty_print: Форматировать ли вывод.
        
        Returns:
            Кортеж (успешно, сообщение об ошибке).
        """
        if self.tree is None:
            return False, "Документ не загружен"
        
        if create_backup and new_path.exists():
            backup_path = BackupUtils.create_backup(new_path, 'timestamp')
            if backup_path is None:
                logger.warning("Не удалось создать резервную копию")
        
        success = XMLUtils.save_tree(
            self.tree,
            new_path,
            self.encoding,
            xml_declaration=True,
            pretty_print=pretty_print,
        )
        
        if success:
            self.file_path = new_path
            self.is_modified = False
            logger.info(f"Файл сохранён как: {new_path}")
            return True, None
        else:
            return False, "Ошибка сохранения файла"
    
    def close(self):
        """Закрывает документ."""
        self.file_path = None
        self.tree = None
        self.encoding = 'utf-8'
        self.original_content = None
        self.is_modified = False
        self.is_read_only = False
        self.error_message = None
        self._original_states = {}
        logger.info("Документ закрыт")
