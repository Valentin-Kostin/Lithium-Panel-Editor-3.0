"""
Модуль настройки логирования.
"""

import logging
from pathlib import Path
from logging.handlers import RotatingFileHandler


def setup_logging(log_file: str = 'logs/scx_editor.log', 
                  level: int = logging.INFO) -> None:
    """
    Настраивает логирование приложения.
    
    Args:
        log_file: Путь к файлу лога.
        level: Уровень логирования.
    """
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    logger = logging.getLogger()
    logger.setLevel(level)
    
    if logger.handlers:
        return
    
    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=5*1024*1024,
        backupCount=3,
        encoding='utf-8'
    )
    file_handler.setLevel(level)
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    logging.getLogger('lxml').setLevel(logging.WARNING)
    logging.getLogger('PySide6').setLevel(logging.WARNING)
