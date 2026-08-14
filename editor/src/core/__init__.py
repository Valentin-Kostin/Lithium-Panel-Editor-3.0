"""
Базовый модуль ядра приложения.
Определяет абстрактные классы и интерфейсы для обработчиков форматов.
"""

from .base_handler import BaseFormatHandler, FileInfo, DocumentModel, OperationRow, ValidationError
from .pgmx_handler import PgmxFormatHandler
from .scx_handler import ScxFormatHandler
from .xml_utils import safe_parse_xml, serialize_xml
from .zip_utils import extract_xml_from_zip, update_xml_in_zip
from .encoding_detector import detect_encoding

__all__ = [
    'BaseFormatHandler',
    'FileInfo',
    'DocumentModel',
    'OperationRow',
    'ValidationError',
    'PgmxFormatHandler',
    'ScxFormatHandler',
    'safe_parse_xml',
    'serialize_xml',
    'extract_xml_from_zip',
    'update_xml_in_zip',
    'detect_encoding'
]
