"""
Утилиты путей.
"""

from pathlib import Path


def get_app_dir() -> Path:
    """
    Получает директорию приложения.
    
    Returns:
        Путь к директории приложения.
    """
    return Path(__file__).parent.parent


def get_config_path(config_name: str) -> Path:
    """
    Получает путь к файлу конфигурации.
    
    Args:
        config_name: Имя файла конфигурации.
    
    Returns:
        Полный путь к файлу.
    """
    app_dir = get_app_dir()
    return app_dir / 'config' / config_name
