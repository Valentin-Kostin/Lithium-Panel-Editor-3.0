"""
Главный файл запуска приложения Editor.
"""

import sys
import logging
from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from src import setup_logging, MainWindow

logger = logging.getLogger(__name__)


def main():
    """Точка входа приложения."""
    setup_logging()
    
    logger.info("Запуск Editor")
    
    app = QApplication(sys.argv)
    app.setApplicationName("Editor")
    app.setOrganizationName("Editor")
    
    app.setStyle('Fusion')
    
    window = MainWindow()
    window.show()
    
    logger.info("Окно приложения показано")
    
    exit_code = app.exec()
    
    logger.info(f"Приложение завершено с кодом: {exit_code}")
    
    return exit_code


if __name__ == '__main__':
    sys.exit(main())
