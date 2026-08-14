"""
Базовый абстрактный класс для обработчиков форматов файлов.
Определяет общий интерфейс для всех форматов (PGMX, SCX).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any, Optional
from lxml import etree


@dataclass
class FileInfo:
    """Информация о файле."""
    path: Path
    name: str
    size: int
    format_type: str  # 'PGMX' или 'SCX'
    encoding: Optional[str] = None
    is_valid: bool = True
    error_message: Optional[str] = None


@dataclass
class OperationRow:
    """Строка данных операции для таблицы."""
    id: int  # Уникальный ID в рамках сессии
    file_name: str  # Имя файла
    operation_name: str  # Имя операции
    operation_type: str  # Тип операции (Сверление, Фрезерование и т.д.)
    x: Optional[float] = None
    y: Optional[float] = None
    z: Optional[float] = None
    diameter: Optional[float] = None
    depth: Optional[float] = None
    feed: Optional[float] = None  # Подача
    speed: Optional[float] = None  # Обороты
    face: Optional[int] = None  # Плоскость
    tool_id: Optional[str] = None  # ID инструмента
    original_data: Dict[str, Any] = field(default_factory=dict)  # Исходные данные для сохранения
    xml_path: Optional[str] = None  # XPath к элементу в XML
    is_modified: bool = False


@dataclass
class ValidationError:
    """Ошибка валидации."""
    field: str
    message: str
    value: Any = None
    severity: str = 'error'  # 'error', 'warning', 'info'


@dataclass
class DocumentModel:
    """Модель документа (файла)."""
    file_info: FileInfo
    xml_tree: Optional[etree._ElementTree] = None
    root_element: Optional[etree._Element] = None
    operations: List[OperationRow] = field(default_factory=list)
    workpiece_params: Dict[str, Any] = field(default_factory=dict)
    namespaces: Dict[str, str] = field(default_factory=dict)
    original_xml_bytes: Optional[bytes] = None
    is_modified: bool = False
    changes_history: List[Dict[str, Any]] = field(default_factory=list)  # Для undo/redo


class BaseFormatHandler(ABC):
    """
    Абстрактный базовый класс для обработчиков форматов.
    Реализует общий пайплайн обработки файлов.
    """

    def __init__(self, mapping_config: Optional[Dict[str, Any]] = None):
        """
        Инициализация обработчика.

        Args:
            mapping_config: Конфигурация маппинга из JSON файла.
        """
        self.mapping_config = mapping_config or {}
        self._supported_extensions: List[str] = []

    @property
    @abstractmethod
    def format_name(self) -> str:
        """Возвращает название формата (например, 'SCM PGMX' или 'NANXING SCX')."""
        pass

    @property
    @abstractmethod
    def file_extension(self) -> str:
        """Возвращает расширение файла (например, '.pgmx' или '.scx')."""
        pass

    @abstractmethod
    def scan_folder(self, folder_path: Path) -> List[FileInfo]:
        """
        Сканирование папки на наличие файлов данного формата.

        Args:
            folder_path: Путь к папке для сканирования.

        Returns:
            Список информации о найденных файлах.
        """
        pass

    @abstractmethod
    def open_file(self, file_path: Path) -> DocumentModel:
        """
        Открытие и парсинг файла.

        Args:
            file_path: Путь к файлу.

        Returns:
            Модель документа с распарсенными данными.

        Raises:
            ValueError: Если файл некорректен.
            FileNotFoundError: Если файл не найден.
        """
        pass

    @abstractmethod
    def extract_operations(self, doc: DocumentModel) -> List[OperationRow]:
        """
        Извлечение параметров операций из документа.

        Args:
            doc: Модель документа.

        Returns:
            Список строк операций.
        """
        pass

    @abstractmethod
    def extract_workpiece_params(self, doc: DocumentModel) -> Dict[str, Any]:
        """
        Извлечение параметров заготовки.

        Args:
            doc: Модель документа.

        Returns:
            Словарь параметров заготовки.
        """
        pass

    @abstractmethod
    def apply_changes(self, doc: DocumentModel, changes: List[OperationRow]) -> DocumentModel:
        """
        Применение изменений к документу.

        Args:
            doc: Модель документа.
            changes: Список изменённых операций.

        Returns:
            Обновлённая модель документа.
        """
        pass

    @abstractmethod
    def validate_document(self, doc: DocumentModel) -> List[ValidationError]:
        """
        Валидация документа перед сохранением.

        Args:
            doc: Модель документа.

        Returns:
            Список ошибок валидации.
        """
        pass

    @abstractmethod
    def save_file(self, doc: DocumentModel, output_path: Optional[Path] = None) -> Path:
        """
        Сохранение документа в файл.

        Args:
            doc: Модель документа.
            output_path: Путь для сохранения (если None, сохраняется в исходный файл).

        Returns:
            Путь к сохранённому файлу.

        Raises:
            IOError: Если ошибка записи.
        """
        pass

    def get_diff(self, original_doc: DocumentModel, modified_doc: DocumentModel) -> Dict[str, Any]:
        """
        Получение различий между оригинальным и изменённым документом.

        Args:
            original_doc: Оригинальный документ.
            modified_doc: Изменённый документ.

        Returns:
            Словарь с различиями.
        """
        diff = {
            'operations_changed': [],
            'workpiece_changed': {},
            'has_changes': False
        }

        # Сравнение операций
        orig_ops = {op.id: op for op in original_doc.operations}
        mod_ops = {op.id: op for op in modified_doc.operations}

        for op_id, mod_op in mod_ops.items():
            if op_id in orig_ops:
                orig_op = orig_ops[op_id]
                if (orig_op.x != mod_op.x or orig_op.y != mod_op.y or
                    orig_op.z != mod_op.z or orig_op.diameter != mod_op.diameter or
                    orig_op.depth != mod_op.depth):
                    diff['operations_changed'].append({
                        'id': op_id,
                        'name': mod_op.operation_name,
                        'original': {
                            'x': orig_op.x, 'y': orig_op.y, 'z': orig_op.z,
                            'diameter': orig_op.diameter, 'depth': orig_op.depth
                        },
                        'modified': {
                            'x': mod_op.x, 'y': mod_op.y, 'z': mod_op.z,
                            'diameter': mod_op.diameter, 'depth': mod_op.depth
                        }
                    })
                    diff['has_changes'] = True

        # Сравнение параметров заготовки
        if original_doc.workpiece_params != modified_doc.workpiece_params:
            diff['workpiece_changed'] = {
                'original': original_doc.workpiece_params,
                'modified': modified_doc.workpiece_params
            }
            diff['has_changes'] = True

        return diff
