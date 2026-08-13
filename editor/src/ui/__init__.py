"""UI модуль приложения."""

from .main_window import MainWindow
from .xml_tree_view import SCXTreeView
from .property_editor import PropertyEditor
from .operations_table import OperationsTable
from .diff_dialog import DiffDialog
from .settings_dialog import SettingsDialog
from .status_bar import StatusBar

__all__ = [
    'MainWindow',
    'SCXTreeView',
    'PropertyEditor',
    'OperationsTable',
    'DiffDialog',
    'SettingsDialog',
    'StatusBar',
]
