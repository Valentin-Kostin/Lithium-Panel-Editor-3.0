"""
Модуль определения кодировки файлов.
Использует charset-normalizer для автоматического определения.
"""

from pathlib import Path
from typing import Optional, Tuple
import logging

try:
    from charset_normalizer import detect as detect_charset
except ImportError:
    detect_charset = None

logger = logging.getLogger(__name__)


# Приоритетные кодировки для проверки
PRIORITY_ENCODINGS = ['utf-8', 'utf-8-sig', 'gb18030', 'gbk', 'windows-1251', 'cp1251']


def detect_encoding(
    file_path: Path,
    priority_encodings: Optional[list] = None
) -> str:
    """
    Определение кодировки файла.

    Args:
        file_path: Путь к файлу.
        priority_encodings: Список кодировок для приоритетной проверки.

    Returns:
        Кодировка в виде строки.
    """
    encodings_to_try = priority_encodings or PRIORITY_ENCODINGS

    if not file_path.exists():
        logger.warning(f"Файл не найден: {file_path}")
        return 'utf-8'

    # Чтение первых байтов файла
    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read(4096)  # Первые 4KB
    except IOError as e:
        logger.error(f"Ошибка чтения файла {file_path}: {e}")
        return 'utf-8'

    # Проверка XML declaration
    xml_decl = raw_data[:200].decode('ascii', errors='ignore')
    if '<?xml' in xml_decl:
        import re
        match = re.search(r'encoding=["\']([^"\']+)["\']', xml_decl)
        if match:
            encoding_from_decl = match.group(1)
            logger.debug(f"Кодировка из XML declaration: {encoding_from_decl}")
            return encoding_from_decl

    # Проверка BOM
    if raw_data.startswith(b'\xef\xbb\xbf'):
        logger.debug("Обнаружен UTF-8 BOM")
        return 'utf-8-sig'
    elif raw_data.startswith(b'\xff\xfe'):
        logger.debug("Обнаружен UTF-16 LE BOM")
        return 'utf-16-le'
    elif raw_data.startswith(b'\xfe\xff'):
        logger.debug("Обнаружен UTF-16 BE BOM")
        return 'utf-16-be'

    # Попытка декодирования с приоритетными кодировками
    for encoding in encodings_to_try:
        try:
            raw_data.decode(encoding)
            logger.debug(f"Успешное декодирование с кодировкой: {encoding}")
            return encoding
        except UnicodeDecodeError:
            continue

    # Использование charset-normalizer если доступен
    if detect_charset:
        try:
            result = detect_charset(raw_data)
            if result and 'encoding' in result:
                detected_encoding = result['encoding']
                confidence = result.get('confidence', 0)
                logger.debug(f"charset-normalizer определил: {detected_encoding} (уверенность: {confidence})")
                return detected_encoding
        except Exception as e:
            logger.warning(f"charset-normalizer вернул ошибку: {e}")

    # Fallback на utf-8
    logger.warning(f"Не удалось определить кодировку, используется utf-8 по умолчанию: {file_path}")
    return 'utf-8'


def validate_encoding(
    file_path: Path,
    encoding: str
) -> bool:
    """
    Проверка корректности декодирования файла с указанной кодировкой.

    Args:
        file_path: Путь к файлу.
        encoding: Кодировка для проверки.

    Returns:
        True если файл корректно декодируется.
    """
    try:
        with open(file_path, 'r', encoding=encoding) as f:
            f.read()
        return True
    except (UnicodeDecodeError, IOError) as e:
        logger.warning(f"Ошибка валидации кодировки {encoding} для {file_path}: {e}")
        return False


def get_file_encoding_info(file_path: Path) -> dict:
    """
    Получение полной информации о кодировке файла.

    Args:
        file_path: Путь к файлу.

    Returns:
        Словарь с информацией о кодировке.
    """
    encoding, method = detect_encoding(file_path)

    return {
        'path': str(file_path),
        'encoding': encoding,
        'method': method,
        'is_valid': validate_encoding(file_path, encoding) if encoding else False
    }
