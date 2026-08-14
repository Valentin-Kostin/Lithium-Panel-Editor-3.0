"""
Базовый интерфейс для обработчиков форматов файлов.
Реализует паттерн Стратегия согласно техническому заданию.
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class OperationData:
    """Унифицированное представление CNC-операции."""
    id: str
    name: str
    tool_id: str
    tool_name: str
    feed_rate: float
    speed: float
    depth: float
    parameters: Dict[str, str]  # Дополнительные специфичные для формата параметры
    xml_node_ref: Any  # Ссылка на оригинальный XML узел


@dataclass
class FileMetadata:
    """Метаданные файла, извлечённые из документа."""
    filename: str
    material: str
    thickness: float
    width: float
    length: float
    description: str


class BaseFormatHandler(ABC):
    """
    Абстрактный базовый класс для обработчиков форматов (SCX, PGMX).
    Определяет общий интерфейс для парсинга, редактирования и сохранения.
    """

    def __init__(self, file_path: Optional[Path] = None):
        self.file_path = file_path
        self.operations: List[OperationData] = []
        self.metadata: Optional[FileMetadata] = None
        self.raw_data: Any = None  # Хранит сырое XML или ZIP содержимое

    @abstractmethod
    def load(self, path: Path) -> bool:
        """
        Загрузить и распарсить файл.
        Возвращает True если успешно, False иначе.
        Должен обрабатывать определение кодировки и специфичный для формата парсинг.
        """
        pass

    @abstractmethod
    def save(self, path: Path) -> bool:
        """
        Сохранить изменения обратно в файл.
        Должен сохранять оригинальное форматирование и кодировку где возможно.
        Возвращает True если успешно.
        """
        pass

    @abstractmethod
    def get_operations(self) -> List[OperationData]:
        """Вернуть список распарсенных операций."""
        pass

    @abstractmethod
    def update_operation(self, operation_id: str, changes: Dict[str, Any]) -> bool:
        """
        Обновить конкретную операцию новыми значениями.
        Возвращает True если обновлено успешно.
        """
        pass

    @abstractmethod
    def get_xml_tree(self) -> Any:
        """
        Вернуть XML-дерево структуры для представления в виде дерева.
        """
        pass

    def validate(self) -> List[str]:
        """
        Валидировать текущие данные.
        Возвращает список сообщений об ошибках.
        """
        errors = []
        # Общая логика валидации может быть реализована здесь
        return errors
