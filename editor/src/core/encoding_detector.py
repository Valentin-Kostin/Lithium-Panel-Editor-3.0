"""
Модуль определения кодировки XML-файлов.
Поддерживает UTF-8, GB18030, GBK, Windows-1251 и другие.
"""

import logging
from typing import Optional, Tuple
from pathlib import Path

import charset_normalizer
from charset_normalizer import CharsetMatch

logger = logging.getLogger(__name__)


COMMON_ENCODINGS = [
    'utf-8',
    'utf-8-sig',
    'gb18030',
    'gbk',
    'gb2312',
    'windows-1251',
    'cp1252',
    'iso-8859-1',
]


def detect_encoding(file_path: Path, xml_declaration_hint: Optional[str] = None) -> Tuple[str, bool]:
    """
    Определяет кодировку файла.
    
    Args:
        file_path: Путь к файлу.
        xml_declaration_hint: Кодировка из XML declaration (если известна).
    
    Returns:
        Кортеж (кодировка, успешность_определения).
    """
    if xml_declaration_hint:
        hint_lower = xml_declaration_hint.lower().strip('"\'')
        if hint_lower in ['utf-8', 'utf8']:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    f.read(1024)
                logger.info(f"Кодировка определена из XML declaration: {hint_lower}")
                return hint_lower, True
            except UnicodeDecodeError:
                pass
        
        if hint_lower in ['gb18030', 'gbk', 'gb2312']:
            try:
                with open(file_path, 'r', encoding=hint_lower) as f:
                    f.read(1024)
                logger.info(f"Кодировка определена из XML declaration: {hint_lower}")
                return hint_lower, True
            except UnicodeDecodeError:
                pass
    
    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read(8192)
        
        result = charset_normalizer.from_bytes(raw_data).best()
        if result:
            encoding = result.encoding.lower()
            # Обработка разных версий charset-normalizer
            confidence = getattr(result, 'confidence', None)
            if confidence is None:
                # Для новых версий или когда уверенность недоступна, предполагать высокую уверенность
                confidence = 1.0
            
            if confidence > 0.7:
                logger.info(f"Кодировка определена через charset-normalizer: {encoding} (confidence={confidence:.2f})")
                return encoding, True
            else:
                logger.warning(f"Низкая уверенность в кодировке: {encoding} (confidence={confidence:.2f})")
                return encoding, False
    except Exception as e:
        logger.error(f"Ошибка при определении кодировки: {e}")
    
    for encoding in COMMON_ENCODINGS:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                f.read(1024)
            logger.info(f"Кодировка подобрана перебором: {encoding}")
            return encoding, True
        except UnicodeDecodeError:
            continue
    
    logger.error("Не удалось определить кодировку файла")
    return 'utf-8', False


def extract_xml_declaration_encoding(file_path: Path) -> Optional[str]:
    """
    Извлекает кодировку из XML declaration.
    
    Args:
        file_path: Путь к файлу.
    
    Returns:
        Кодировка или None.
    """
    try:
        with open(file_path, 'rb') as f:
            first_bytes = f.read(512)
        
        first_line = first_bytes.split(b'\n')[0].decode('ascii', errors='ignore')
        
        if '<?xml' in first_line:
            import re
            match = re.search(r'encoding=["\']([^"\']+)["\']', first_line)
            if match:
                return match.group(1)
    except Exception as e:
        logger.debug(f"Не удалось извлечь кодировку из XML declaration: {e}")
    
    return None


def detect_and_validate(file_path: Path) -> Tuple[str, str, bool]:
    """
    Полная проверка кодировки и валидности XML.
    
    Args:
        file_path: Путь к файлу.
    
    Returns:
        Кортеж (кодировка, сообщение, успешно).
    """
    xml_encoding = extract_xml_declaration_encoding(file_path)
    encoding, success = detect_encoding(file_path, xml_encoding)
    
    if not success:
        logger.warning(f"Кодировка определена с низкой уверенностью: {encoding}")
    
    try:
        from lxml import etree
        with open(file_path, 'r', encoding=encoding) as f:
            content = f.read()
        etree.fromstring(content.encode(encoding))
        return encoding, "Файл корректен", True
    except etree.XMLSyntaxError as e:
        return encoding, f"XML ошибка: {e}", False
    except UnicodeDecodeError as e:
        return encoding, f"Ошибка декодирования: {e}", False
    except Exception as e:
        return encoding, f"Неизвестная ошибка: {e}", False
