"""
Утилиты для безопасного парсинга и сериализации XML.
Сохраняет namespaces, префиксы, порядок элементов и XML declaration.
"""

from typing import Optional, Dict, Any, Tuple
from pathlib import Path
from lxml import etree
import logging

logger = logging.getLogger(__name__)


def safe_parse_xml(
    file_path: Path,
    encoding: Optional[str] = None,
    remove_blank_text: bool = False
) -> Tuple[etree._ElementTree, Dict[str, str]]:
    """
    Безопасный парсинг XML файла с сохранением namespaces.

    Args:
        file_path: Путь к XML файлу.
        encoding: Кодировка файла (если None, определяется автоматически).
        remove_blank_text: Удалять ли пустые текстовые узлы.

    Returns:
        Кортеж (xml_tree, namespaces_dict).

    Raises:
        ValueError: Если файл не является корректным XML.
        FileNotFoundError: Если файл не найден.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Файл не найден: {file_path}")

    # Чтение файла
    if encoding:
        with open(file_path, 'r', encoding=encoding) as f:
            xml_content = f.read()
    else:
        # Попытка определить кодировку
        with open(file_path, 'rb') as f:
            raw_data = f.read()

        # Проверка XML declaration
        try:
            xml_decl = raw_data[:200].decode('utf-8', errors='ignore')
            if '<?xml' in xml_decl:
                import re
                match = re.search(r'encoding=["\']([^"\']+)["\']', xml_decl)
                if match:
                    encoding = match.group(1)
        except Exception:
            pass

        # Чтение с определённой или дефолтной кодировкой
        try:
            xml_content = raw_data.decode(encoding or 'utf-8')
        except UnicodeDecodeError:
            # Попытка с другими кодировками
            for fallback_encoding in ['utf-8-sig', 'gb18030', 'windows-1251']:
                try:
                    xml_content = raw_data.decode(fallback_encoding)
                    encoding = fallback_encoding
                    logger.warning(f"Использована резервная кодировка: {fallback_encoding}")
                    break
                except UnicodeDecodeError:
                    continue
            else:
                raise ValueError(f"Не удалось определить кодировку файла: {file_path}")

    # Парсинг XML
    try:
        parser = etree.XMLParser(
            remove_blank_text=remove_blank_text,
            recover=False,
            resolve_entities=False
        )
        tree = etree.XML(xml_content.encode(encoding or 'utf-8'), parser)
        
        # Извлечение namespaces
        namespaces = tree.nsmap
        if namespaces is None:
            namespaces = {}
        
        # Создание ElementTree из элемента
        element_tree = etree.ElementTree(tree)
        
        logger.debug(f"XML успешно распарсен: {file_path}, кодировка: {encoding}")
        return element_tree, namespaces
        
    except etree.XMLSyntaxError as e:
        logger.error(f"Ошибка синтаксиса XML в файле {file_path}: {e}")
        raise ValueError(f"Некорректный XML файл: {file_path}. Ошибка: {e}")


def serialize_xml(
    tree: etree._ElementTree,
    encoding: str = 'utf-8',
    xml_declaration: bool = True,
    pretty_print: bool = False,
    namespaces: Optional[Dict[str, str]] = None
) -> bytes:
    """
    Сериализация XML дерева в байты с сохранением структуры.

    Args:
        tree: XML дерево (ElementTree).
        encoding: Кодировка выходных данных.
        xml_declaration: Добавить ли XML declaration.
        pretty_print: Форматировать ли вывод.
        namespaces: Словарь namespaces для сохранения.

    Returns:
        Байтовое представление XML.
    """
    root = tree.getroot()
    
    # Восстановление namespaces если переданы
    if namespaces:
        for prefix, uri in namespaces.items():
            if prefix is None:
                root.set('xmlns', uri)
            else:
                root.set(f'xmlns:{prefix}', uri)
    
    # Сериализация
    xml_bytes = etree.tostring(
        root,
        encoding=encoding,
        xml_declaration=xml_declaration,
        pretty_print=pretty_print
    )
    
    logger.debug(f"XML сериализован: {len(xml_bytes)} байт, кодировка: {encoding}")
    return xml_bytes


def get_element_by_xpath(
    root: etree._Element,
    xpath: str,
    namespaces: Optional[Dict[str, str]] = None
) -> Optional[etree._Element]:
    """
    Поиск элемента по XPath.
    Автоматически обрабатывает default namespace (None ключ) заменяя на 'ns'.

    Args:
        root: Корневой элемент.
        xpath: XPath выражение.
        namespaces: Словарь namespaces.

    Returns:
        Найденный элемент или None.
    """
    # Обработка namespaces: замена None ключа на 'ns'
    processed_ns = {}
    if namespaces:
        for prefix, uri in namespaces.items():
            if prefix is None:
                processed_ns['ns'] = uri
            else:
                processed_ns[prefix] = uri
    
    try:
        elements = root.xpath(xpath, namespaces=processed_ns)
        if elements:
            return elements[0]
        return None
    except etree.XPathError as e:
        logger.error(f"Ошибка XPath '{xpath}': {e}")
        return None


def get_elements_by_xpath(
    root: etree._Element,
    xpath: str,
    namespaces: Optional[Dict[str, str]] = None
) -> list:
    """
    Поиск всех элементов по XPath.
    Автоматически обрабатывает default namespace (None ключ) заменяя на 'ns'.

    Args:
        root: Корневой элемент.
        xpath: XPath выражение.
        namespaces: Словарь namespaces.

    Returns:
        Список найденных элементов.
    """
    # Обработка namespaces: замена None ключа на 'ns'
    processed_ns = {}
    if namespaces:
        for prefix, uri in namespaces.items():
            if prefix is None:
                processed_ns['ns'] = uri
            else:
                processed_ns[prefix] = uri
    
    try:
        return root.xpath(xpath, namespaces=processed_ns) or []
    except etree.XPathError as e:
        logger.error(f"Ошибка XPath '{xpath}': {e}")
        return []


def set_element_value(
    element: etree._Element,
    value: Any,
    attribute_name: Optional[str] = None
) -> None:
    """
    Установка значения элемента или атрибута.

    Args:
        element: XML элемент.
        value: Значение для установки.
        attribute_name: Имя атрибута (если None, устанавливается текст элемента).
    """
    if value is None:
        return
    
    if attribute_name:
        element.set(attribute_name, str(value))
    else:
        element.text = str(value)


def create_element(
    tag: str,
    text: Optional[str] = None,
    attrib: Optional[Dict[str, str]] = None,
    nsmap: Optional[Dict[str, str]] = None
) -> etree._Element:
    """
    Создание нового XML элемента.

    Args:
        tag: Тег элемента.
        text: Текстовое содержимое.
        attrib: Атрибуты элемента.
        nsmap: Namespaces элемента.

    Returns:
        Новый XML элемент.
    """
    element = etree.Element(tag, attrib=attrib or {}, nsmap=nsmap)
    if text:
        element.text = text
    return element
