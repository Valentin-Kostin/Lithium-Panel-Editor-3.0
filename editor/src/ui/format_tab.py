"""
Виджет вкладки формата (SCM или NANXING).
Содержит левую панель с логами изменений и правую с таблицей операций.
"""

from pathlib import Path
from typing import Optional, List, Dict, Any
import logging
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QTextEdit,
    QPushButton, QLabel, QToolBar, QFileDialog, QMessageBox, QGroupBox,
    QFormLayout, QLineEdit, QDoubleSpinBox, QComboBox
)
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QFont

from ..core.base_handler import BaseFormatHandler, FileInfo, DocumentModel
from ..models.operations_model import OperationsTableModel
from .operations_table import OperationsTableView
from .diff_dialog import DiffDialog

logger = logging.getLogger(__name__)


class FormatTab(QWidget):
    """
    Виджет вкладки для работы с файлами одного формата.
    """

    # Сигналы
    files_loaded = Signal(int)  # количество файлов
    modifications_changed = Signal(bool)  # есть ли изменения
    status_message = Signal(str)  # сообщение в статус-бар

    def __init__(self, format_handler: BaseFormatHandler, parent=None):
        super().__init__(parent)
        
        self.format_handler = format_handler
        self._documents: Dict[Path, DocumentModel] = {}
        self._current_file: Optional[Path] = None
        
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        """Настройка UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Сплиттер для разделения левой и правой панели
        splitter = QSplitter(Qt.Horizontal)

        # Левая панель - логи изменений и поиск
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(5, 5, 5, 5)

        # Группа поиска и фильтрации
        search_group = QGroupBox("🔍 Поиск и фильтрация")
        search_layout = QFormLayout(search_group)
        
        # Поиск по диаметру
        self.diameter_input = QDoubleSpinBox()
        self.diameter_input.setDecimals(3)
        self.diameter_input.setRange(0.0, 100.0)
        self.diameter_input.setValue(2.5)
        self.diameter_input.setSingleStep(0.1)
        search_layout.addRow("Диаметр (мм):", self.diameter_input)
        
        # Ограничение глубины
        self.max_depth_input = QDoubleSpinBox()
        self.max_depth_input.setDecimals(3)
        self.max_depth_input.setRange(0.0, 1000.0)
        self.max_depth_input.setValue(5.0)
        self.max_depth_input.setSingleStep(0.5)
        search_layout.addRow("Макс. глубина (мм):", self.max_depth_input)
        
        # Тип операции
        self.operation_type_combo = QComboBox()
        self.operation_type_combo.addItems(["Все", "Сверление", "Фрезерование", "Пиление"])
        search_layout.addRow("Тип операции:", self.operation_type_combo)
        
        # Кнопки поиска
        btn_search_layout = QHBoxLayout()
        self.find_btn = QPushButton("🔍 Найти")
        self.find_btn.setToolTip("Найти все операции по критериям")
        btn_search_layout.addWidget(self.find_btn)
        
        self.apply_all_btn = QPushButton("✅ Применить ко всем файлам")
        self.apply_all_btn.setToolTip("Применить изменения ко всем найденным операциям во всех файлах")
        self.apply_all_btn.setEnabled(False)
        btn_search_layout.addWidget(self.apply_all_btn)
        
        search_layout.addRow(btn_search_layout)
        left_layout.addWidget(search_group)

        # Заголовок логов
        log_header = QLabel("📋 Журнал изменений")
        log_header.setStyleSheet("font-weight: bold; font-size: 12px;")
        left_layout.addWidget(log_header)

        # Текстовое окно для логов
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        self.log_text.setStyleSheet("background-color: #f5f5f5; border: 1px solid #ccc;")
        left_layout.addWidget(self.log_text)

        # Кнопки управления
        btn_layout = QHBoxLayout()
        
        self.open_folder_btn = QPushButton("📁 Открыть папку")
        self.open_folder_btn.setToolTip("Выбрать папку для сканирования файлов")
        btn_layout.addWidget(self.open_folder_btn)

        self.clear_log_btn = QPushButton("🗑 Очистить лог")
        self.clear_log_btn.setToolTip("Очистить журнал изменений")
        btn_layout.addWidget(self.clear_log_btn)

        left_layout.addLayout(btn_layout)

        splitter.addWidget(left_widget)

        # Правая панель - таблица операций
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(5, 5, 5, 5)

        # Заголовок таблицы
        table_header = QLabel("📊 Найденные операции")
        table_header.setStyleSheet("font-weight: bold; font-size: 12px;")
        right_layout.addWidget(table_header)

        # Таблица операций
        self.operations_table = OperationsTableView()
        self.operations_model = OperationsTableModel(self)
        self.operations_table.set_model(self.operations_model)
        right_layout.addWidget(self.operations_table)

        # Информация о файле
        self.file_info_label = QLabel("")
        self.file_info_label.setStyleSheet("color: gray; font-style: italic;")
        right_layout.addWidget(self.file_info_label)

        splitter.addWidget(right_widget)

        # Настройка размеров сплиттера
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        splitter.setSizes([300, 700])

        layout.addWidget(splitter)

    def _connect_signals(self):
        """Подключение сигналов."""
        self.open_folder_btn.clicked.connect(self._on_open_folder)
        self.save_btn.clicked.connect(self._on_save)
        
        self.file_list_view.selectionModel().currentChanged.connect(
            self._on_file_selection_changed
        )
        
        self.operations_model.data_changed_signal.connect(
            self._on_operation_data_changed
        )

    @Slot()
    def _on_open_folder(self):
        """Обработка нажатия кнопки 'Открыть папку'."""
        folder_path = QFileDialog.getExistingDirectory(
            self,
            f"Выберите папку с файлами {self.format_handler.format_name}",
            "",
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )
        
        if folder_path:
            self.scan_folder(Path(folder_path))

    @Slot()
    def _on_save(self):
        """Обработка нажатия кнопки 'Сохранить'."""
        if not self._current_file:
            QMessageBox.warning(self, "Предупреждение", "Файл не выбран")
            return

        doc = self._documents.get(self._current_file)
        if not doc or not doc.is_modified:
            return

        # Получение diff
        diff_data = self.format_handler.get_diff(doc, doc)
        
        # Показ диалога diff
        if not DiffDialog.show_diff(diff_data, self):
            return

        # Валидация
        errors = self.format_handler.validate_document(doc)
        if errors:
            error_messages = [f"{e.field}: {e.message}" for e in errors if e.severity == 'error']
            if error_messages:
                QMessageBox.critical(
                    self,
                    "Ошибка валидации",
                    "Обнаружены ошибки:\n" + "\n".join(error_messages)
                )
                return

        # Сохранение
        try:
            saved_path = self.format_handler.save_file(doc)
            self.status_message.emit(f"Файл сохранён: {saved_path.name}")
            self.save_btn.setEnabled(False)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка сохранения", str(e))
            logger.error(f"Ошибка сохранения файла: {e}")

    @Slot(object)
    def _on_file_selection_changed(self, current, previous):
        """Обработка выбора файла в списке."""
        if not current.isValid():
            return

        file_info = self.file_list_model.get_file_at(current.row())
        if file_info and file_info.is_valid:
            self.load_file(file_info.path)

    @Slot(int, str, object)
    def _on_operation_data_changed(self, operation_id: int, field: str, value: any):
        """Обработка изменения данных операции."""
        has_modifications = self.operations_model.has_modifications()
        self.modifications_changed.emit(has_modifications)
        self.save_btn.setEnabled(has_modifications)
        self.status_message.emit(f"Изменено: операция #{operation_id}, {field} = {value}")

    def scan_folder(self, folder_path: Path) -> None:
        """Сканирование папки на наличие файлов."""
        logger.info(f"Сканирование папки: {folder_path} для формата {self.format_handler.format_name}")
        
        try:
            files = self.format_handler.scan_folder(folder_path)
            self.file_list_model.set_files(files)
            
            valid_count = sum(1 for f in files if f.is_valid)
            invalid_count = sum(1 for f in files if not f.is_valid)
            
            self.files_loaded.emit(valid_count)
            self.status_message.emit(
                f"Найдено файлов: {valid_count} (ошибок: {invalid_count})"
            )
            
            if valid_count > 0:
                self.file_list_view.setCurrentIndex(
                    self.file_list_model.index(0, 0)
                )
                
        except Exception as e:
            logger.error(f"Ошибка сканирования папки: {e}")
            self.status_message.emit(f"Ошибка сканирования: {e}")

    def load_file(self, file_path: Path) -> None:
        """Загрузка файла."""
        logger.info(f"Загрузка файла: {file_path}")
        
        try:
            # Проверка кэша
            if file_path in self._documents:
                doc = self._documents[file_path]
            else:
                doc = self.format_handler.open_file(file_path)
                self._documents[file_path] = doc

            self._current_file = file_path
            
            # Обновление таблицы операций
            self.operations_model.set_operations(doc.operations)
            
            # Обновление информации о файле
            self.file_info_label.setText(
                f"Файл: {doc.file_info.name} | "
                f"Операций: {len(doc.operations)} | "
                f"Кодировка: {doc.file_info.encoding or 'N/A'}"
            )
            
            self.save_btn.setEnabled(False)
            self.status_message.emit(f"Файл загружен: {doc.file_info.name}")
            
        except Exception as e:
            logger.error(f"Ошибка загрузки файла {file_path}: {e}")
            self.status_message.emit(f"Ошибка загрузки: {e}")
            QMessageBox.critical(self, "Ошибка загрузки", str(e))

    def get_current_document(self) -> Optional[DocumentModel]:
        """Получение текущего документа."""
        if self._current_file:
            return self._documents.get(self._current_file)
        return None

    def save_all(self) -> int:
        """Сохранение всех изменённых файлов."""
        saved_count = 0
        
        for path, doc in self._documents.items():
            if doc.is_modified:
                try:
                    self.format_handler.save_file(doc)
                    saved_count += 1
                except Exception as e:
                    logger.error(f"Ошибка сохранения файла {path}: {e}")
        
        return saved_count

    def has_unsaved_changes(self) -> bool:
        """Проверка наличия несохранённых изменений."""
        return any(doc.is_modified for doc in self._documents.values())
