"""
Утилиты для работы с XML.
Безопасный парсинг, работа с namespace, сохранение структуры.
"""

import logging
from typing import Optional, Dict, List, Any, Tuple
from pathlib import Path
from io import BytesIO

from lxml import etree
from defusedxml import lxml as defused_lxml

logger = logging.getLogger(__name__)


class XMLUtils:
    """Утилиты для безопасной работы с XML."""
    
    @staticmethod
    def safe_parse(file_path: Path, encoding: str) -> Tuple[Optional[etree.ElementTree], Optional[str]]:
        """
        Безопасно парсит XML файл.
        
        Args:
            file_path: Путь к файлу.
            encoding: Кодировка файла.
        
        Returns:
            Кортеж (дерево, ошибка). Если успешно, ошибка None.
        """
        try:
            with open(file_path, 'rb') as f:
                raw_data = f.read()
            
            parser = etree.XMLParser(
                encoding=encoding,
                recover=False,
                no_network=True,
                huge_tree=False,
                resolve_entities=False,
                load_dtd=False,
            )
            
            tree = etree.parse(BytesIO(raw_data), parser)
            logger.info(f"XML успешно загружен: {file_path}")
            return tree, None
            
        except etree.XMLSyntaxError as e:
            error_msg = f"Ошибка синтаксиса XML: {e}"
            logger.error(error_msg)
            return None, error_msg
        except Exception as e:
            error_msg = f"Ошибка при парсинге: {e}"
            logger.error(error_msg)
            return None, error_msg
    
    @staticmethod
    def get_namespaces(root: etree.Element) -> Dict[str, str]:
        """
        Извлекает namespace из корневого элемента.
        
        Args:
            root: Корневой элемент.
        
        Returns:
            Словарь {префикс: uri}.
        """
        namespaces = {}
        for key, value in root.nsmap.items():
            if key is not None and value is not None:
                namespaces[key] = value
        return namespaces
    
    @staticmethod
    def get_element_path(element: etree.Element, root: etree.Element) -> str:
        """
        Получает XPath элемента относительно корня.
        
        Args:
            element: Элемент.
            root: Корневой элемент.
        
        Returns:
            XPath строка.
        """
        path = element.getroottree().getpath(element)
        return path
    
    @staticmethod
    def find_elements(tree: etree.ElementTree, xpath: str, namespaces: Optional[Dict[str, str]] = None) -> List[etree.Element]:
        """
        Находит элементы по XPath.
        
        Args:
            tree: XML дерево.
            xpath: XPath выражение.
            namespaces: Словарь namespace.
        
        Returns:
            Список элементов.
        """
        try:
            root = tree.getroot()
            
            if namespaces is None:
                namespaces = XMLUtils.get_namespaces(root)
            
            elements = tree.xpath(xpath, namespaces=namespaces)
            return elements if isinstance(elements, list) else [elements] if elements is not None else []
            
        except Exception as e:
            logger.error(f"Ошибка при поиске по XPath '{xpath}': {e}")
            return []
    
    @staticmethod
    def save_tree(tree: etree.ElementTree, file_path: Path, encoding: str, 
                  xml_declaration: bool = True, pretty_print: bool = False) -> bool:
        """
        Сохраняет XML дерево в файл.
        
        Args:
            tree: XML дерево.
            file_path: Путь к файлу.
            encoding: Кодировка.
            xml_declaration: Добавить ли XML declaration.
            pretty_print: Форматировать ли вывод.
        
        Returns:
            True если успешно.
        """
        try:
            temp_path = file_path.with_suffix(file_path.suffix + '.tmp')
            
            tree.write(
                temp_path,
                encoding=encoding,
                xml_declaration=xml_declaration,
                pretty_print=pretty_print,
                method='xml',
            )
            
            temp_path.replace(file_path)
            logger.info(f"Файл сохранён: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при сохранении: {e}")
            if temp_path.exists():
                temp_path.unlink()
            return False
    
    @staticmethod
    def validate_xml(content: bytes, encoding: str) -> Tuple[bool, Optional[str]]:
        """
        Проверяет, является ли контент валидным XML.
        
        Args:
            content: Байты контента.
            encoding: Кодировка.
        
        Returns:
            Кортеж (валидно, ошибка).
        """
        try:
            parser = etree.XMLParser(
                encoding=encoding,
                recover=False,
                no_network=True,
                resolve_entities=False,
            )
            etree.fromstring(content, parser)
            return True, None
        except etree.XMLSyntaxError as e:
            return False, str(e)
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def get_element_info(element: etree.Element) -> Dict[str, Any]:
        """
        Получает информацию об элементе.
        
        Args:
            element: Элемент.
        
        Returns:
            Словарь с информацией.
        """
        info = {
            'tag': element.tag,
            'text': (element.text or '').strip(),
            'tail': (element.tail or '').strip(),
            'attrib': dict(element.attrib),
            'children_count': len(element),
        }
        return info
    
    @staticmethod
    def copy_element(element: etree.Element) -> etree.Element:
        """
        Создаёт глубокую копию элемента.
        
        Args:
            element: Элемент для копирования.
        
        Returns:
            Копия элемента.
        """
        return deepcopy(element)


from copy import deepcopy
