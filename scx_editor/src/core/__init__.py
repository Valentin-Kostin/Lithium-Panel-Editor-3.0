"""Core модуль для работы с SCX и PGMX файлами."""

from .xml_utils import XMLUtils
from .encoding_detector import detect_encoding, extract_xml_declaration_encoding, detect_and_validate
from .mapping import MappingConfig, MappingField
from .validation import ValidationUtils
from .diff import DiffUtils, Change, ChangeType
from .backup import BackupUtils
from .scx_document import SCXDocument
from .base_handler import BaseFormatHandler, OperationData, FileMetadata
from .pgmx_handler import PgmxFormatHandler

__all__ = [
    'XMLUtils',
    'detect_encoding',
    'extract_xml_declaration_encoding',
    'detect_and_validate',
    'MappingConfig',
    'MappingField',
    'ValidationUtils',
    'DiffUtils',
    'Change',
    'ChangeType',
    'BackupUtils',
    'SCXDocument',
    'BaseFormatHandler',
    'OperationData',
    'FileMetadata',
    'PgmxFormatHandler',
]
