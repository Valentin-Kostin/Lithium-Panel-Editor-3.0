"""SCX Editor - Редактор файлов NANXING."""

from .core import SCXDocument, MappingConfig
from .ui import MainWindow
from .utils import setup_logging

__version__ = '1.0.0'
__author__ = 'SCX Editor Team'

__all__ = [
    'SCXDocument',
    'MappingConfig',
    'MainWindow',
    'setup_logging',
]
