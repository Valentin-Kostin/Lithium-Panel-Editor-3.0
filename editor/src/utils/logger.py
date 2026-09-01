"""
Настройка логирования приложения.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from logging.handlers import RotatingFileHandler


# Имя логгера приложения
APP_LOGGER_NAME = "cnc_editor"


def setup_logging(
    log_file: str = "logs/cnc_editor.log",
    level: int = logging.INFO,
    console_output: bool = True,
    max_bytes: int = 5 * 1024 * 1024,  # 5 MB
    backup_count: int = 3
) -> logging.Logger:
    """
    Настройка системы логирования.

    Args:
        log_file: Путь к файлу лога.
        level: Уровень логирования.
        console_output: Выводить ли логи в консоль.
        max_bytes: Максимальный размер файла лога перед ротацией.
        backup_count: Количество резервных файлов лога.

    Returns:
        Настроенный логгер приложения.
    """
    # Создание директории для логов
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Получение именованного логгера (не корневого)
    logger = logging.getLogger(APP_LOGGER_NAME)
    
    # Проверка: если уже настроен, не настраиваем повторно
    if logger.handlers:
        return logger
    
    logger.setLevel(level)

    # Формат сообщений
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Файловый обработчик с ротацией
    file_handler = RotatingFileHandler(
        log_file, 
        encoding='utf-8',
        maxBytes=max_bytes,
        backupCount=backup_count
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Консольный обработчик (опционально)
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)  # Тот же уровень, что и общий
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # Логирование запуска
    logger.info("=" * 60)
    logger.info(f"Запуск приложения: {datetime.now().isoformat()}")
    logger.info(f"Лог файл: {log_path.absolute()}")
    logger.info(f"Уровень логирования: {logging.getLevelName(level)}")
    logger.info(f"Ротация логов: {max_bytes} байт, {backup_count} резервных файлов")
    logger.info("=" * 60)
    
    return logger
