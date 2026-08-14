"""
Модуль пользовательского интерфейса.
"""

from .main_window import MainWindow
from .format_tab import FormatTab
from .operations_table import OperationsTableView
from .diff_dialog import DiffDialog

__all__ = ['MainWindow', 'FormatTab', 'OperationsTableView', 'DiffDialog']
