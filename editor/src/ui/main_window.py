"""
Главное окно приложения с поддержкой двух форматов: SCX (NANXING) и PGMX (SCM Group).
Реализует архитектуру с вкладками согласно технической спецификации.
"""

import logging
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QSplitter, QToolBar, QFileDialog, QMessageBox,
    QTabWidget, QLabel, QStackedWidget
)
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QAction, QIcon

from ..core.scx_document import SCXDocument
from ..core.base_handler import BaseFormatHandler, OperationData, FileMetadata
from ..core.pgmx_handler import PgmxFormatHandler
from ..core.mapping import MappingConfig
from ..models.tree_model import SCXTreeModel
from ..models.operations_model import OperationsModel
from ..models.undo_commands import UndoStack
from ..ui.xml_tree_view import SCXTreeView
from ..ui.property_editor import PropertyEditor
from ..ui.operations_table import OperationsTable
from ..ui.diff_dialog import DiffDialog
from ..ui.settings_dialog import SettingsDialog
from ..ui.status_bar import StatusBar

logger = logging.getLogger(__name__)


class FormatTab(QWidget):
    """Widget for a single format tab (SCX or PGMX)."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.handler: Optional[BaseFormatHandler] = None
        self.tree_model = SCXTreeModel()
        self.operations_model = OperationsModel()
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        splitter = QSplitter(Qt.Horizontal)
        
        # Left panel - XML Tree
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        self.tree_view = SCXTreeView()
        self.tree_view.set_model(self.tree_model)
        left_layout.addWidget(self.tree_view)
        
        splitter.addWidget(left_widget)
        
        # Right panel - Tabs with Properties and Operations
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        self.tab_widget = QTabWidget()
        
        self.property_editor = PropertyEditor()
        self.tab_widget.addTab(self.property_editor, "Свойства")
        
        self.operations_table = OperationsTable()
        self.operations_table.set_model(self.operations_model)
        self.tab_widget.addTab(self.operations_table, "Операции")
        
        right_layout.addWidget(self.tab_widget)
        
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        
        layout.addWidget(splitter)
    
    def load_data(self, handler: BaseFormatHandler):
        """Load data from handler into the UI components."""
        self.handler = handler
        
        # Load tree
        xml_tree = handler.get_xml_tree()
        if xml_tree is not None:
            self.tree_model.set_tree(xml_tree)
        
        # Load operations
        operations = handler.get_operations()
        if operations:
            self.operations_model.set_operations(operations)


class MainWindow(QMainWindow):
    """Главное окно приложения с поддержкой SCX и PGMX."""
    
    def __init__(self):
        super().__init__()
        
        self.scx_document: Optional[SCXDocument] = None
        self.pgmx_handler: Optional[PgmxFormatHandler] = None
        self.current_handler: Optional[BaseFormatHandler] = None
        self.mapping_config: Optional[MappingConfig] = None
        self.undo_stack = UndoStack(max_size=100)
        self.settings = self._load_default_settings()
        
        self.setWindowTitle("SCX/PGMX Editor - Редактор файлов ЧПУ")
        self.setMinimumSize(1200, 800)
        
        self._init_ui()
        self._init_toolbar()
        self._init_statusbar()
        self._connect_signals()
        
        self._load_mapping()
    
    def _load_default_settings(self) -> dict:
        """Загружает настройки по умолчанию."""
        return {
            'auto_backup': True,
            'backup_format': 'timestamp',
            'detailed_xml_mode': False,
            'mapping_path': 'config/default_mapping.json',
            'language': 'ru',
            'warn_on_delete': True,
        }
    
    def _init_ui(self):
        """Инициализирует UI с вкладками для SCX и PGMX."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        
        # Main tab widget for formats
        self.format_tabs = QTabWidget()
        
        # SCX Tab (NANXING)
        self.scx_tab = FormatTab(self)
        self.format_tabs.addTab(self.scx_tab, "🇨🇳 NANXING (.SCX)")
        
        # PGMX Tab (SCM Group)
        self.pgmx_tab = FormatTab(self)
        self.format_tabs.addTab(self.pgmx_tab, "🇮🇹 SCM (.PGMX)")
        
        # Connect tab change to update current handler
        self.format_tabs.currentChanged.connect(self._on_format_tab_changed)
        
        main_layout.addWidget(self.format_tabs)
        
        # Set initial current handler
        self.current_handler = None
    
    def _on_format_tab_changed(self, index: int):
        """Handle format tab switch."""
        if index == 0:  # SCX tab
            self.current_handler = self.scx_document
        elif index == 1:  # PGMX tab
            self.current_handler = self.pgmx_handler
        
        # Update status bar
        if self.current_handler and self.current_handler.file_path:
            self.statusbar.set_file_path(str(self.current_handler.file_path))
        else:
            self.statusbar.set_status("")
    
    def _init_toolbar(self):
        """Инициализирует панель инструментов."""
        toolbar = QToolBar("Основная")
        self.addToolBar(toolbar)
        
        self.open_action = QAction("Открыть", self)
        self.open_action.setShortcut("Ctrl+O")
        self.open_action.triggered.connect(self._open_file)
        toolbar.addAction(self.open_action)
        
        self.save_action = QAction("Сохранить", self)
        self.save_action.setShortcut("Ctrl+S")
        self.save_action.triggered.connect(self._save_file)
        toolbar.addAction(self.save_action)
        
        self.save_as_action = QAction("Сохранить как", self)
        self.save_as_action.setShortcut("Ctrl+Shift+S")
        self.save_as_action.triggered.connect(self._save_file_as)
        toolbar.addAction(self.save_as_action)
        
        toolbar.addSeparator()
        
        self.undo_action = QAction("Отмена", self)
        self.undo_action.setShortcut("Ctrl+Z")
        self.undo_action.triggered.connect(self._undo)
        toolbar.addAction(self.undo_action)
        
        self.redo_action = QAction("Повтор", self)
        self.redo_action.setShortcut("Ctrl+Y")
        self.redo_action.triggered.connect(self._redo)
        toolbar.addAction(self.redo_action)
        
        toolbar.addSeparator()
        
        self.show_diff_action = QAction("Показать изменения", self)
        self.show_diff_action.triggered.connect(self._show_diff)
        toolbar.addAction(self.show_diff_action)
        
        self.settings_action = QAction("Настройки", self)
        self.settings_action.triggered.connect(self._show_settings)
        toolbar.addAction(self.settings_action)
        
        self.about_action = QAction("О программе", self)
        self.about_action.triggered.connect(self._show_about)
        toolbar.addAction(self.about_action)
    
    def _init_statusbar(self):
        """Инициализирует статусную строку."""
        self.statusbar = StatusBar()
        self.setStatusBar(self.statusbar)
    
    def _connect_signals(self):
        """Подключает сигналы."""
    # Connect signals for both tabs
    self.scx_tab.tree_view.selectionModel().currentChanged.connect(
        self._on_tree_selection_changed
    )
    self.pgmx_tab.tree_view.selectionModel().currentChanged.connect(
        self._on_tree_selection_changed
    )
    
    self.scx_tab.property_editor.value_changed.connect(
        self._on_property_changed
    )
    self.pgmx_tab.property_editor.value_changed.connect(
        self._on_property_changed
    )
    
    self.scx_tab.operations_table.selectionModel().currentChanged.connect(
        self._on_operations_selection_changed
    )
    self.pgmx_tab.operations_table.selectionModel().currentChanged.connect(
        self._on_operations_selection_changed
    )
    
    def _load_mapping(self):
        """Загружает конфигурацию маппинга."""
        mapping_path = Path(self.settings.get('mapping_path', 'config/default_mapping.json'))
        
        if not mapping_path.is_absolute():
            app_dir = Path(__file__).parent.parent
            mapping_path = app_dir / mapping_path
        
        if mapping_path.exists():
            self.mapping_config = MappingConfig(mapping_path)
            logger.info(f"Маппинг загружен: {mapping_path}")
        else:
            logger.warning(f"Файл маппинга не найден: {mapping_path}")
            self.mapping_config = MappingConfig()
    
    @Slot()
    def _open_file(self):
        """Открывает файл с автоопределением формата."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Открыть файл ЧПУ",
            "",
            "CNC Files (*.scx *.pgmx);;SCX Files (*.scx);;PGMX Files (*.pgmx);;XML Files (*.xml);;All Files (*)"
        )
        
        if file_path:
            path = Path(file_path)
            # Auto-detect format by extension
            if path.suffix.lower() == '.pgmx':
                self._load_pgmx_file(path)
            else:
                self._load_scx_file(path)
    
    def _load_scx_file(self, file_path: Path):
        """Загружает SCX файл."""
        self.scx_document = SCXDocument()
        success, error = self.scx_document.load(file_path, self.mapping_config)
        
        if success:
            # Switch to SCX tab
            self.format_tabs.setCurrentIndex(0)
            
            # Load data into SCX tab
            self.scx_tab.load_data(self.scx_document)
            
            self.statusbar.set_file_path(str(file_path))
            self.statusbar.set_encoding(self.scx_document.encoding)
            
            root = self.scx_document.get_root_element()
            if root is not None:
                tag = root.tag
                if '}' in tag:
                    tag = tag.split('}')[1]
                self.statusbar.set_root_tag(tag)
            
            self.current_handler = self.scx_document
            self.statusbar.set_status("SCX файл успешно открыт")
            logger.info(f"SCX файл открыт: {file_path}")
        else:
            QMessageBox.critical(
                self,
                "Ошибка открытия файла",
                f"Не удалось открыть SCX файл:\n{error}"
            )
            logger.error(f"Ошибка открытия SCX файла: {error}")
    
    def _load_pgmx_file(self, file_path: Path):
        """Загружает PGMX файл."""
        self.pgmx_handler = PgmxFormatHandler()
        success = self.pgmx_handler.load(file_path)
        
        if success:
            # Switch to PGMX tab
            self.format_tabs.setCurrentIndex(1)
            
            # Load data into PGMX tab
            self.pgmx_tab.load_data(self.pgmx_handler)
            
            self.statusbar.set_file_path(str(file_path))
            self.statusbar.set_encoding("UTF-8 (ZIP)")
            
            if self.pgmx_handler.metadata:
                meta = self.pgmx_handler.metadata
                if meta.material:
                    self.statusbar.set_status(f"Материал: {meta.material}, Толщина: {meta.thickness}мм")
            
            self.current_handler = self.pgmx_handler
            self.statusbar.set_status("PGMX файл успешно открыт")
            logger.info(f"PGMX файл открыт: {file_path}")
        else:
            QMessageBox.critical(
                self,
                "Ошибка открытия файла",
                f"Не удалось открыть PGMX файл:\nФайл может быть повреждён или иметь неверный формат"
            )
            logger.error(f"Ошибка открытия PGMX файла: {file_path}")
    
    @Slot()
    def _save_file(self):
        """Сохраняет файл текущего формата."""
        current_index = self.format_tabs.currentIndex()
        
        if current_index == 0:  # SCX tab
            if self.scx_document and self.scx_document.file_path is None:
                self._save_file_as_scx()
                return
            self._do_save_scx()
        elif current_index == 1:  # PGMX tab
            if self.pgmx_handler and self.pgmx_handler.file_path is None:
                self._save_file_as_pgmx()
                return
            self._do_save_pgmx()
    
    def _save_file_as_scx(self):
        """Сохраняет SCX файл как."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить файл SCX",
            "",
            "SCX Files (*.scx);;XML Files (*.xml);;All Files (*)"
        )
        
        if file_path:
            self.scx_document.file_path = Path(file_path)
            self._do_save_scx()
    
    def _save_file_as_pgmx(self):
        """Сохраняет PGMX файл как."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить файл PGMX",
            "",
            "PGMX Files (*.pgmx);;All Files (*)"
        )
        
        if file_path:
            self._do_save_pgmx(Path(file_path))
    
    @Slot()
    def _save_file_as(self):
        """Сохраняет файл текущего формата как (универсальный метод)."""
        current_index = self.format_tabs.currentIndex()
        
        if current_index == 0:  # SCX tab
            self._save_file_as_scx()
        elif current_index == 1:  # PGMX tab
            self._save_file_as_pgmx()
    
    def _do_save_scx(self):
        """Выполняет сохранение SCX файла."""
        if not self.scx_document:
            return
            
        create_backup = self.settings.get('auto_backup', True)
        backup_format = self.settings.get('backup_format', 'timestamp')
        
        success, error = self.scx_document.save(
            create_backup=create_backup,
            backup_format=backup_format,
            pretty_print=self.settings.get('detailed_xml_mode', False)
        )
        
        if success:
            self.statusbar.set_status("SCX файл сохранён")
            logger.info("SCX файл сохранён")
        else:
            QMessageBox.critical(
                self,
                "Ошибка сохранения",
                f"Не удалось сохранить SCX файл:\n{error}"
            )
            logger.error(f"Ошибка сохранения SCX файла: {error}")
    
    def _do_save_pgmx(self, save_path: Optional[Path] = None):
        """Выполняет сохранение PGMX файла."""
        if not self.pgmx_handler:
            return
        
        path_to_save = save_path or self.pgmx_handler.file_path
        if not path_to_save:
            return
        
        success = self.pgmx_handler.save(path_to_save)
        
        if success:
            self.statusbar.set_status("PGMX файл сохранён")
            logger.info(f"PGMX файл сохранён: {path_to_save}")
        else:
            QMessageBox.critical(
                self,
                "Ошибка сохранения",
                f"Не удалось сохранить PGMX файл"
            )
            logger.error(f"Ошибка сохранения PGMX файла: {path_to_save}")
    
    @Slot()
    def _undo(self):
        """Отменяет действие."""
        current_index = self.format_tabs.currentIndex()
        if current_index == 0 and self.scx_tab:
            # SCX undo logic (if implemented)
            pass
        elif current_index == 1 and self.pgmx_tab:
            # PGMX undo logic (if implemented)
            pass
        
        self.statusbar.set_status("Отменено")
    
    @Slot()
    def _redo(self):
        """Повторяет действие."""
        current_index = self.format_tabs.currentIndex()
        if current_index == 0 and self.scx_tab:
            # SCX redo logic (if implemented)
            pass
        elif current_index == 1 and self.pgmx_tab:
            # PGMX redo logic (if implemented)
            pass
        
        self.statusbar.set_status("Повторено")
    
    @Slot()
    def _show_diff(self):
        """Показывает изменения."""
        current_index = self.format_tabs.currentIndex()
        changes = []
        
        if current_index == 0 and self.scx_document:
            # Get SCX changes
            pass
        elif current_index == 1 and self.pgmx_handler:
            # Get PGMX changes
            pass
        
        dialog = DiffDialog(changes, self)
        dialog.exec_()
    
    @Slot()
    def _show_settings(self):
        """Показывает настройки."""
        dialog = SettingsDialog(self.settings, self)
        if dialog.exec_() == SettingsDialog.Accepted:
            self.settings = dialog.get_settings()
            self._load_mapping()
    
    @Slot()
    def _show_about(self):
        """Показывает диалог о программе."""
        QMessageBox.about(
            self,
            "О программе",
            "SCX/PGMX Editor v1.0\n\n"
            "Редактор файлов ЧПУ для станков NANXING (.SCX) и SCM Group (.PGMX).\n\n"
            "Технологии: Python, PySide6, lxml, zipfile\n\n"
            "Поддерживаемые форматы:\n"
            "• .SCX - NANXING (Китай)\n"
            "• .PGMX - SCM Group (Италия)"
        )
    
    @Slot(object)
    def _on_tree_selection_changed(self, index):
        """Обрабатывает изменение выделения в дереве."""
        current_index = self.format_tabs.currentIndex()
        
        if current_index == 0 and self.scx_tab:
            element = self.scx_tab.tree_model.get_element(index)
            self.scx_tab.property_editor.set_element(element)
        elif current_index == 1 and self.pgmx_tab:
            element = self.pgmx_tab.tree_model.get_element(index)
            self.pgmx_tab.property_editor.set_element(element)
    
    @Slot(str, str, str)
    def _on_property_changed(self, attr_name: str, old_value: str, new_value: str):
        """Обрабатывает изменение свойства."""
        current_index = self.format_tabs.currentIndex()
        
        if current_index == 0 and self.scx_tab:
            element = self.scx_tab.property_editor.get_current_element()
            if element is None:
                return
            
            if attr_name == 'text':
                if self.scx_document:
                    self.scx_document.set_text(element, new_value)
            else:
                if self.scx_document:
                    self.scx_document.set_attribute(element, attr_name, new_value)
            
            self.scx_tab.tree_model.set_tree(self.scx_document.get_tree())
            self.statusbar.set_status(f"SCX: Изменено {attr_name}")
            
        elif current_index == 1 and self.pgmx_tab:
            element = self.pgmx_tab.property_editor.get_current_element()
            if element is None or not self.pgmx_handler:
                return
            
            # Update PGMX operation
            # Find operation by element reference and update
            self.statusbar.set_status(f"PGMX: Изменено {attr_name}")
    
    @Slot(int)
    def _on_operation_selected(self, row: int):
        """Обрабатывает выбор операции."""
        current_index = self.format_tabs.currentIndex()
        
        if current_index == 0 and self.scx_tab:
            element = self.scx_tab.operations_model.get_element(row)
            if element is not None:
                self.scx_tab.property_editor.set_element(element)
                self.scx_tab.tab_widget.setCurrentIndex(0)
        elif current_index == 1 and self.pgmx_tab:
            # PGMX operations are already in the handler
            if row < len(self.pgmx_tab.operations_model._operations):
                op = self.pgmx_tab.operations_model._operations[row]
                # Highlight in tree or show properties
                self.pgmx_tab.property_editor.set_element(op.xml_node_ref if hasattr(op, 'xml_node_ref') else None)
                self.pgmx_tab.tab_widget.setCurrentIndex(0)
