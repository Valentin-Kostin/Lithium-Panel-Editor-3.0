"""
Утилиты для работы с путями к файлам и ресурсам.
"""

import sys
from pathlib import Path


def get_app_root() -> Path:
    """
    Получение корневой директории приложения.
    
    Returns:
        Путь к корню приложения.
    """
    if getattr(sys, 'frozen', False):
        # Запуск через PyInstaller
        return Path(sys.executable).parent
    else:
        # Запуск из исходного кода
        return Path(__file__).parent.parent.parent


def get_resource_path(relative_path: str) -> Path:
    """
    Получение полного пути к ресурсу.

    Args:
        relative_path: Относительный путь к ресурсу от корня приложения.

    Returns:
        Полный путь к ресурсу.
    """
    return get_app_root() / relative_path


def get_config_path(relative_path: str = "") -> Path:
    """
    Получение пути к файлу конфигурации.

    Args:
        relative_path: Относительный путь от директории config.

    Returns:
        Полный путь к файлу конфигурации.
    """
    config_dir = get_app_root() / 'config'
    if relative_path:
        return config_dir / relative_path
    return config_dir


def get_logs_path(relative_path: str = "") -> Path:
    """
    Получение пути к файлу лога.

    Args:
        relative_path: Относительный путь от директории logs.

    Returns:
        Полный путь к файлу лога.
    """
    logs_dir = get_app_root() / 'logs'
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    if relative_path:
        return logs_dir / relative_path
    return logs_dir


def is_running_as_bundle() -> bool:
    """
    Проверка, запущено ли приложение как bundled (PyInstaller).

    Returns:
        True если приложение упаковано.
    """
    return getattr(sys, 'frozen', False)
