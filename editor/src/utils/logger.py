"""
Настройка логирования приложения.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime


def setup_logging(
    log_file: str = "logs/cnc_editor.log",
    level: int = logging.INFO,
    console_output: bool = True
) -> None:
    """
    Настройка системы логирования.

    Args:
        log_file: Путь к файлу лога.
        level: Уровень логирования.
        console_output: Выводить ли логи в консоль.
    """
    # Создание директории для логов
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Конфигурация корневого логгера
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Очистка существующих обработчиков
    root_logger.handlers.clear()

    # Формат сообщений
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Файловый обработчик
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # Консольный обработчик (опционально)
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.WARNING)  # Только предупреждения и ошибки в консоль
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    # Логирование запуска
    logging.info("=" * 60)
    logging.info(f"Запуск приложения: {datetime.now().isoformat()}")
    logging.info(f"Лог файл: {log_path.absolute()}")
    logging.info(f"Уровень логирования: {logging.getLevelName(level)}")
    logging.info("=" * 60)
