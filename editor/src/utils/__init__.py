"""
Модуль утилит приложения.
"""

from .logger import setup_logging
from .paths import get_resource_path, get_config_path

__all__ = [
    'setup_logging', 
    'get_resource_path', 
    'get_config_path'
]
