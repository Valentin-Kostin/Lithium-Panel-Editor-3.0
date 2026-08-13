"""Editor - Редактор файлов NANXING и SCM Group."""

from .core import SCXDocument, MappingConfig, PgmxFormatHandler, FolderScanner, ZipUtils
from .ui import MainWindow
from .utils import setup_logging

__version__ = '1.0.0'
__author__ = 'Editor Team'

__all__ = [
    'SCXDocument',
    'MappingConfig',
    'PgmxFormatHandler',
    'FolderScanner',
    'ZipUtils',
    'MainWindow',
    'setup_logging',
]
