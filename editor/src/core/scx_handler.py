"""
Обработчик файлов формата SCX (NANXING).
Реализация парсера и сериализатора для китайского формата.
"""

from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
import json

from lxml import etree

from .base_handler import (
    BaseFormatHandler, FileInfo, DocumentModel, OperationRow, ValidationError
)
from .xml_utils import safe_parse_xml, serialize_xml, get_elements_by_xpath
from .encoding_detector import detect_encoding

logger = logging.getLogger(__name__)


class ScxFormatHandler(BaseFormatHandler):
    """
    Обработчик файлов формата SCX (NANXING).
    """

    def __init__(self, mapping_config: Optional[Dict[str, Any]] = None):
        """
        Инициализация обработчика SCX.

        Args:
            mapping_config: Конфигурация маппинга из JSON файла.
        """
        super().__init__(mapping_config)
        self._supported_extensions = ['.scx']
        
        # Загрузка маппинга по умолчанию если не передан
        if not mapping_config:
            self._load_default_mapping()

    def _load_default_mapping(self) -> None:
        """Загрузка маппинга по умолчанию из config/nanxing_mapping.json."""
        mapping_path = Path(__file__).parent.parent / 'config' / 'nanxing_mapping.json'
        if mapping_path.exists():
            try:
                with open(mapping_path, 'r', encoding='utf-8') as f:
                    self.mapping_config = json.load(f)
                logger.debug(f"Маппинг загружен: {mapping_path}")
            except Exception as e:
                logger.warning(f"Ошибка загрузки маппинга {mapping_path}: {e}")
                self._set_default_mapping()
        else:
            self._set_default_mapping()

    def _set_default_mapping(self) -> None:
        """Установка маппинга по умолчанию."""
        self.mapping_config = {
            'format': 'SCX',
            'vendor': 'NANXING',
            'namespaces': {},
            'workpiece': {
                'length': {'xpath': '//Panel/@Length', 'type': 'float'},
                'width': {'xpath': '//Panel/@Width', 'type': 'float'},
                'thickness': {'xpath': '//Panel/@Thickness', 'type': 'float'}
            },
            'operations': {
                'container_xpath': '//Machining',
                'fields': [
                    {'id': 'type', 'xpath': '@Type', 'type': 'string', 'label': 'Тип'},
                    {'id': 'face', 'xpath': '@Face', 'type': 'int', 'label': 'Плоскость'},
                    {'id': 'x', 'xpath': '@X', 'type': 'float', 'label': 'X'},
                    {'id': 'y', 'xpath': '@Y', 'type': 'float', 'label': 'Y'},
                    {'id': 'diameter', 'xpath': '@Diameter', 'type': 'float', 'label': 'Диаметр'},
                    {'id': 'depth', 'xpath': '@Depth', 'type': 'float', 'label': 'Глубина'}
                ]
            }
        }

    @property
    def format_name(self) -> str:
        return 'NANXING SCX'

    @property
    def file_extension(self) -> str:
        return '.scx'

    def scan_folder(self, folder_path: Path) -> List[FileInfo]:
        """Сканирование папки на наличие SCX файлов."""
        files_info = []
        
        if not folder_path.exists():
            logger.warning(f"Папка не найдена: {folder_path}")
            return files_info

        for ext in self._supported_extensions:
            for file_path in folder_path.rglob(f'*{ext}'):
                try:
                    size = file_path.stat().st_size
                    encoding, enc_method = detect_encoding(file_path)
                    
                    file_info = FileInfo(
                        path=file_path,
                        name=file_path.name,
                        size=size,
                        format_type='SCX',
                        encoding=encoding,
                        is_valid=True
                    )
                    files_info.append(file_info)
                    logger.debug(f"Найден SCX файл: {file_path.name} ({size} байт)")
                    
                except Exception as e:
                    file_info = FileInfo(
                        path=file_path,
                        name=file_path.name,
                        size=0,
                        format_type='SCX',
                        is_valid=False,
                        error_message=str(e)
                    )
                    files_info.append(file_info)
                    logger.error(f"Ошибка при сканировании файла {file_path}: {e}")

        return files_info

    def open_file(self, file_path: Path) -> DocumentModel:
        """Открытие и парсинг SCX файла."""
        logger.info(f"Открытие SCX файла: {file_path}")

        # Определение кодировки
        encoding, enc_method = detect_encoding(file_path)
        logger.debug(f"Кодировка определена методом '{enc_method}': {encoding}")

        # Парсинг XML
        tree, namespaces = safe_parse_xml(file_path, encoding=encoding)
        root = tree.getroot()

        # Создание FileInfo
        file_info = FileInfo(
            path=file_path,
            name=file_path.name,
            size=file_path.stat().st_size,
            format_type='SCX',
            encoding=encoding,
            is_valid=True
        )

        # Создание модели документа
        doc = DocumentModel(
            file_info=file_info,
            xml_tree=tree,
            root_element=root,
            namespaces=namespaces or {}
        )

        # Извлечение параметров заготовки
        doc.workpiece_params = self.extract_workpiece_params(doc)

        # Извлечение операций
        doc.operations = self.extract_operations(doc)

        logger.info(f"SCX файл открыт: {file_path.name}, операций: {len(doc.operations)}")
        return doc

    def extract_operations(self, doc: DocumentModel) -> List[OperationRow]:
        """Извлечение операций из SCX документа."""
        operations = []
        root = doc.root_element
        namespaces = doc.namespaces
        
        if root is None:
            logger.warning("Корневой элемент отсутствует")
            return operations

        # Получение XPath контейнера операций из маппинга
        container_xpath = self.mapping_config.get('operations', {}).get(
            'container_xpath', '//Machining'
        )
        
        # Поиск всех элементов операций
        machining_elements = get_elements_by_xpath(root, container_xpath, namespaces)
        
        logger.debug(f"Найдено элементов Machining: {len(machining_elements)}")

        # Поля для извлечения
        fields_config = self.mapping_config.get('operations', {}).get('fields', [])

        operation_id = 0
        for elem in machining_elements:
            operation_id += 1
            
            # Извлечение атрибутов
            op_type = elem.get('Type', '')
            face = elem.get('Face', '0')
            
            # Определение типа операции
            type_map = {'2': 'Сверление', '3': 'Фрезерование', '4': 'Раскрой'}
            operation_type = type_map.get(str(op_type), f'Тип {op_type}')
            
            # Имя операции (генерируем из параметров)
            x_val = elem.get('X', '0')
            y_val = elem.get('Y', '0')
            op_name = f"Операция #{operation_id} ({operation_type})"
            
            # Извлечение числовых параметров
            def get_float_attr(attr_name: str) -> Optional[float]:
                val = elem.get(attr_name)
                if val:
                    try:
                        return float(val)
                    except ValueError:
                        return None
                return None

            def get_int_attr(attr_name: str) -> Optional[int]:
                val = elem.get(attr_name)
                if val:
                    try:
                        return int(val)
                    except ValueError:
                        return None
                return None

            operation = OperationRow(
                id=operation_id,
                file_name=doc.file_info.name,
                operation_name=op_name,
                operation_type=operation_type,
                x=get_float_attr('X'),
                y=get_float_attr('Y'),
                z=get_float_attr('Z'),
                diameter=get_float_attr('Diameter'),
                depth=get_float_attr('Depth'),
                face=get_int_attr('Face'),
                tool_id=elem.get('ToolOffset', ''),
                original_data={
                    'element': elem,
                    'xpath': elem.sourceline
                },
                xml_path=f'//Machining[{operation_id}]'
            )
            operations.append(operation)

        logger.info(f"Извлечено операций: {len(operations)}")
        return operations

    def extract_workpiece_params(self, doc: DocumentModel) -> Dict[str, Any]:
        """Извлечение параметров заготовки."""
        params = {}
        root = doc.root_element
        namespaces = doc.namespaces
        
        if root is None:
            return params

        workpiece_config = self.mapping_config.get('workpiece', {})
        
        for param_name, config in workpiece_config.items():
            xpath = config.get('xpath', '')
            param_type = config.get('type', 'string')
            
            elements = get_elements_by_xpath(root, xpath, namespaces)
            if elements:
                elem = elements[0]
                # Для атрибутов Panel
                if xpath.startswith('//Panel/@'):
                    attr_name = xpath.split('@')[-1]
                    value = elem.get(attr_name) if hasattr(elem, 'get') else None
                else:
                    value = elem.text
                
                if value:
                    try:
                        if param_type == 'float':
                            params[param_name] = float(value)
                        elif param_type == 'int':
                            params[param_name] = int(value)
                        else:
                            params[param_name] = value
                    except (ValueError, TypeError):
                        params[param_name] = value

        return params

    def apply_changes(self, doc: DocumentModel, changes: List[OperationRow]) -> DocumentModel:
        """Применение изменений к документу."""
        root = doc.root_element
        
        if root is None:
            raise ValueError("Документ не имеет корневого элемента")

        for change in changes:
            if not change.is_modified:
                continue

            # Поиск элемента по ID (упрощённо по порядку)
            container_xpath = self.mapping_config.get('operations', {}).get(
                'container_xpath', '//Machining'
            )
            elements = get_elements_by_xpath(root, container_xpath, doc.namespaces)
            
            # Находим элемент соответствующий операции
            target_elem = None
            for i, elem in enumerate(elements):
                if i + 1 == change.id:  # ID начинается с 1
                    target_elem = elem
                    break
            
            if target_elem is None:
                logger.warning(f"Элемент для операции #{change.id} не найден")
                continue

            # Обновление атрибутов
            if change.x is not None:
                target_elem.set('X', str(change.x))
            if change.y is not None:
                target_elem.set('Y', str(change.y))
            if change.z is not None:
                target_elem.set('Z', str(change.z))
            if change.diameter is not None:
                target_elem.set('Diameter', str(change.diameter))
            if change.depth is not None:
                target_elem.set('Depth', str(change.depth))

        doc.is_modified = True
        logger.info(f"Применено изменений: {len(changes)}")
        return doc

    def validate_document(self, doc: DocumentModel) -> List[ValidationError]:
        """Валидация документа перед сохранением."""
        errors = []

        # Проверка числовых значений операций
        for op in doc.operations:
            if op.x is not None and (op.x < -10000 or op.x > 10000):
                errors.append(ValidationError(
                    field=f'Операция #{op.id}.X',
                    message=f'Значение X ({op.x}) вне допустимого диапазона',
                    value=op.x,
                    severity='error'
                ))
            
            if op.y is not None and (op.y < -10000 or op.y > 10000):
                errors.append(ValidationError(
                    field=f'Операция #{op.id}.Y',
                    message=f'Значение Y ({op.y}) вне допустимого диапазона',
                    value=op.y,
                    severity='error'
                ))

            if op.diameter is not None and op.diameter <= 0:
                errors.append(ValidationError(
                    field=f'Операция #{op.id}.Diameter',
                    message=f'Диаметр должен быть положительным',
                    value=op.diameter,
                    severity='error'
                ))

            if op.depth is not None and op.depth < 0:
                errors.append(ValidationError(
                    field=f'Операция #{op.id}.Depth',
                    message=f'Глубина не может быть отрицательной',
                    value=op.depth,
                    severity='warning'
                ))

        return errors

    def save_file(self, doc: DocumentModel, output_path: Optional[Path] = None) -> Path:
        """Сохранение SCX файла."""
        target_path = output_path or doc.file_info.path
        
        logger.info(f"Сохранение SCX файла: {target_path}")

        # Сериализация XML
        encoding = doc.file_info.encoding or 'utf-8'
        xml_bytes = serialize_xml(
            doc.xml_tree,
            encoding=encoding,
            xml_declaration=True,
            pretty_print=True,
            namespaces=doc.namespaces
        )

        # Атомарная запись
        import tempfile
        import shutil
        
        temp_fd, temp_path = tempfile.mkstemp(suffix='.scx.tmp')
        try:
            import os
            os.close(temp_fd)
            
            with open(temp_path, 'wb') as f:
                f.write(xml_bytes)
            
            # Перемещение временного файла
            shutil.move(temp_path, target_path)
            logger.info(f"SCX файл сохранён: {target_path}")
            
            doc.is_modified = False
            return target_path
            
        except Exception as e:
            logger.error(f"Ошибка сохранения SCX файла: {e}")
            # Очистка временного файла
            try:
                Path(temp_path).unlink()
            except Exception:
                pass
            raise IOError(f"Ошибка сохранения файла: {e}")
