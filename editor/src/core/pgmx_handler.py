"""
Обработчик файлов формата PGMX (SCM Group XCam/Maestro).
Реализация парсера и сериализатора для итальянского формата.
"""

from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
import json
import zipfile

from lxml import etree

from .base_handler import (
    BaseFormatHandler, FileInfo, DocumentModel, OperationRow, ValidationError
)
from .xml_utils import safe_parse_xml, serialize_xml, get_elements_by_xpath
from .zip_utils import extract_xml_from_zip, update_xml_in_zip

logger = logging.getLogger(__name__)


class PgmxFormatHandler(BaseFormatHandler):
    """
    Обработчик файлов формата PGMX (SCM Group XCam/Maestro).
    Файлы PGMX представляют собой ZIP-архивы с XML внутри.
    """

    def __init__(self, mapping_config: Optional[Dict[str, Any]] = None):
        """
        Инициализация обработчика PGMX.

        Args:
            mapping_config: Конфигурация маппинга из JSON файла.
        """
        super().__init__(mapping_config)
        self._supported_extensions = ['.pgmx']
        
        # Загрузка маппинга по умолчанию если не передан
        if not mapping_config:
            self._load_default_mapping()

    def _load_default_mapping(self) -> None:
        """Загрузка маппинга по умолчанию из config/scm_mapping.json."""
        mapping_path = Path(__file__).parent.parent / 'config' / 'scm_mapping.json'
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
            'format': 'SCM',
            'vendor': 'SCM Group (XCam/Maestro)',
            'namespaces': {
                'project': 'http://schemas.datacontract.org/2004/07/ScmGroup.XCam.MachiningDataModel.ProjectModule',
                'utility': 'http://schemas.datacontract.org/2004/07/ScmGroup.XCam.MachiningDataModel.Utility',
                'parametrics': 'http://schemas.datacontract.org/2004/07/ScmGroup.XCam.MachiningDataModel.Parametrics',
                'i': 'http://www.w3.org/2001/XMLSchema-instance'
            },
            'operations': {
                'drilling': {
                    'container_xpath': ".//ManufacturingFeature[@i:type='RoundHole']",
                    'fields': [
                        {'id': 'name', 'xpath': '@Name', 'type': 'string', 'label': 'Имя операции'},
                        {'id': 'diameter', 'xpath': 'Diameter', 'type': 'float', 'label': 'Диаметр'},
                        {'id': 'depth', 'xpath': 'EndDepth', 'type': 'float', 'label': 'Глубина'}
                    ]
                }
            }
        }

    @property
    def format_name(self) -> str:
        return 'SCM PGMX'

    @property
    def file_extension(self) -> str:
        return '.pgmx'

    def scan_folder(self, folder_path: Path) -> List[FileInfo]:
        """Сканирование папки на наличие PGMX файлов."""
        files_info = []
        
        if not folder_path.exists():
            logger.warning(f"Папка не найдена: {folder_path}")
            return files_info

        for ext in self._supported_extensions:
            for file_path in folder_path.rglob(f'*{ext}'):
                try:
                    size = file_path.stat().st_size
                    
                    # Проверка что это корректный ZIP
                    is_valid_zip = True
                    error_msg = None
                    try:
                        with zipfile.ZipFile(file_path, 'r') as zf:
                            zf.testzip()
                    except Exception as e:
                        is_valid_zip = False
                        error_msg = f"Некорректный ZIP: {e}"
                    
                    file_info = FileInfo(
                        path=file_path,
                        name=file_path.name,
                        size=size,
                        format_type='PGMX',
                        encoding='utf-8',  # PGMX всегда UTF-8
                        is_valid=is_valid_zip,
                        error_message=error_msg
                    )
                    files_info.append(file_info)
                    logger.debug(f"Найден PGMX файл: {file_path.name} ({size} байт)")
                    
                except Exception as e:
                    file_info = FileInfo(
                        path=file_path,
                        name=file_path.name,
                        size=0,
                        format_type='PGMX',
                        is_valid=False,
                        error_message=str(e)
                    )
                    files_info.append(file_info)
                    logger.error(f"Ошибка при сканировании файла {file_path}: {e}")

        return files_info

    def open_file(self, file_path: Path) -> DocumentModel:
        """Открытие и парсинг PGMX файла (ZIP-архива с XML)."""
        logger.info(f"Открытие PGMX файла: {file_path}")

        # Извлечение XML из ZIP
        try:
            xml_bytes, xml_filename, other_files = extract_xml_from_zip(file_path)
        except Exception as e:
            logger.error(f"Ошибка извлечения XML из PGMX {file_path}: {e}")
            raise ValueError(f"Ошибка открытия PGMX файла: {e}")

        # Парсинг XML
        try:
            parser = etree.XMLParser(recover=False, resolve_entities=False)
            root = etree.fromstring(xml_bytes, parser)
            tree = etree.ElementTree(root)
            namespaces = root.nsmap or {}
        except etree.XMLSyntaxError as e:
            logger.error(f"Ошибка синтаксиса XML в PGMX {file_path}: {e}")
            raise ValueError(f"Некорректный XML в PGMX файле: {e}")

        # Создание FileInfo
        file_info = FileInfo(
            path=file_path,
            name=file_path.name,
            size=file_path.stat().st_size,
            format_type='PGMX',
            encoding='utf-8',
            is_valid=True
        )

        # Создание модели документа
        doc = DocumentModel(
            file_info=file_info,
            xml_tree=tree,
            root_element=root,
            namespaces=namespaces,
            original_xml_bytes=xml_bytes
        )
        
        # Сохранение информации о ZIP для последующего сохранения
        doc.workpiece_params['_zip_xml_filename'] = xml_filename
        doc.workpiece_params['_zip_other_files'] = other_files

        # Извлечение параметров заготовки
        doc.workpiece_params.update(self.extract_workpiece_params(doc))

        # Извлечение операций
        doc.operations = self.extract_operations(doc)

        logger.info(f"PGMX файл открыт: {file_path.name}, операций: {len(doc.operations)}")
        return doc

    def extract_operations(self, doc: DocumentModel) -> List[OperationRow]:
        """Извлечение операций из PGMX документа."""
        operations = []
        root = doc.root_element
        namespaces = doc.namespaces
        
        if root is None:
            logger.warning("Корневой элемент отсутствует")
            return operations

        # Добавление namespace i по умолчанию если отсутствует
        if 'i' not in namespaces:
            namespaces['i'] = 'http://www.w3.org/2001/XMLSchema-instance'

        # Поиск элементов ManufacturingFeature с типом RoundHole (сверление)
        drilling_xpath = ".//ManufacturingFeature[@i:type='RoundHole']"
        drilling_elements = get_elements_by_xpath(root, drilling_xpath, namespaces)
        
        logger.debug(f"Найдено элементов сверления: {len(drilling_elements)}")

        operation_id = 0
        
        # Обработка операций сверления
        for elem in drilling_elements:
            operation_id += 1
            
            # Извлечение имени операции
            op_name = elem.get('Name', f'Сверление #{operation_id}')
            
            # Извлечение Diameter и EndDepth
            diameter_elem = elem.find('Diameter', namespaces=namespaces)
            depth_elem = elem.find('EndDepth', namespaces=namespaces)
            
            diameter = float(diameter_elem.text) if diameter_elem is not None and diameter_elem.text else None
            depth = float(depth_elem.text) if depth_elem is not None and depth_elem.text else None
            
            # Извлечение GeometryID для координат
            geom_id_elem = elem.find('GeometryID', namespaces=namespaces)
            geometry_id = geom_id_elem.text if geom_id_elem is not None else None
            
            # Поиск координат по GeometryID
            x, y, z = None, None, None
            if geometry_id:
                coords = self._find_coordinates_by_id(root, geometry_id, namespaces)
                x, y, z = coords
            
            # Извлечение PlaneID для определения плоскости
            plane_id_elem = elem.find('PlaneID', namespaces=namespaces)
            plane_id = plane_id_elem.text if plane_id_elem is not None else None
            face = self._plane_id_to_face(plane_id)
            
            operation = OperationRow(
                id=operation_id,
                file_name=doc.file_info.name,
                operation_name=op_name,
                operation_type='Сверление',
                x=x,
                y=y,
                z=z,
                diameter=diameter,
                depth=depth,
                face=face,
                tool_id=None,
                original_data={
                    'element': elem,
                    'geometry_id': geometry_id,
                    'plane_id': plane_id
                },
                xml_path=f'//ManufacturingFeature[{operation_id}]'
            )
            operations.append(operation)

        # Поиск элементов ManufacturingFeature с типом PocketRectangular (фрезерование)
        milling_xpath = ".//ManufacturingFeature[@i:type='PocketRectangular']"
        milling_elements = get_elements_by_xpath(root, milling_xpath, namespaces)
        
        logger.debug(f"Найдено элементов фрезерования: {len(milling_elements)}")
        
        for elem in milling_elements:
            operation_id += 1
            
            op_name = elem.get('Name', f'Фрезерование #{operation_id}')
            
            depth_elem = elem.find('EndDepth', namespaces=namespaces)
            depth = float(depth_elem.text) if depth_elem is not None and depth_elem.text else None
            
            tool_key_elem = elem.find('ToolKey', namespaces=namespaces)
            tool_id = tool_key_elem.text if tool_key_elem is not None else None
            
            operation = OperationRow(
                id=operation_id,
                file_name=doc.file_info.name,
                operation_name=op_name,
                operation_type='Фрезерование',
                x=None,
                y=None,
                z=None,
                diameter=None,
                depth=depth,
                face=None,
                tool_id=tool_id,
                original_data={
                    'element': elem,
                    'tool_key': tool_id
                },
                xml_path=f'//ManufacturingFeature[{operation_id}]'
            )
            operations.append(operation)

        logger.info(f"Всего извлечено операций: {len(operations)}")
        return operations

    def _find_coordinates_by_id(
        self, 
        root: etree._Element, 
        geometry_id: str, 
        namespaces: Dict[str, str]
    ) -> tuple:
        """Поиск координат по ID геометрии."""
        # Поиск элемента Geometries с matching Key/ID
        xpath = f".//Geometries/*[Key/ID='{geometry_id}']"
        elements = get_elements_by_xpath(root, xpath, namespaces)
        
        if elements:
            elem = elements[0]
            x_elem = elem.find('_x', namespaces=namespaces)
            y_elem = elem.find('_y', namespaces=namespaces)
            z_elem = elem.find('_z', namespaces=namespaces)
            
            x = float(x_elem.text) if x_elem is not None and x_elem.text else None
            y = float(y_elem.text) if y_elem is not None and y_elem.text else None
            z = float(z_elem.text) if z_elem is not None and z_elem.text else None
            
            return x, y, z
        
        return None, None, None

    def _plane_id_to_face(self, plane_id: Optional[str]) -> Optional[int]:
        """Преобразование ID плоскости в номер грани."""
        if not plane_id:
            return None
        
        plane_map = {
            'Top': 1,
            'Bottom': 2,
            'Left': 3,
            'Right': 4,
            'Front': 5,
            'Back': 6
        }
        return plane_map.get(plane_id)

    def extract_workpiece_params(self, doc: DocumentModel) -> Dict[str, Any]:
        """Извлечение параметров заготовки."""
        params = {}
        root = doc.root_element
        namespaces = doc.namespaces
        
        if root is None:
            return params

        # Поиск WorkPiece элемента
        workpiece_xpath = ".//WorkPiece"
        workpiece_elems = get_elements_by_xpath(root, workpiece_xpath, namespaces)
        
        if workpiece_elems:
            wp = workpiece_elems[0]
            
            length_elem = wp.find('Length', namespaces=namespaces)
            width_elem = wp.find('Width', namespaces=namespaces)
            depth_elem = wp.find('Depth', namespaces=namespaces)
            
            if length_elem is not None and length_elem.text:
                params['length'] = float(length_elem.text)
            if width_elem is not None and width_elem.text:
                params['width'] = float(width_elem.text)
            if depth_elem is not None and depth_elem.text:
                params['thickness'] = float(depth_elem.text)

        return params

    def apply_changes(self, doc: DocumentModel, changes: List[OperationRow]) -> DocumentModel:
        """Применение изменений к документу."""
        root = doc.root_element
        namespaces = doc.namespaces
        
        if root is None:
            raise ValueError("Документ не имеет корневого элемента")

        if 'i' not in namespaces:
            namespaces['i'] = 'http://www.w3.org/2001/XMLSchema-instance'

        for change in changes:
            if not change.is_modified:
                continue

            # Поиск элемента по ID
            orig_data = change.original_data
            elem = orig_data.get('element')
            
            if elem is None:
                logger.warning(f"Элемент для операции #{change.id} не найден")
                continue

            # Обновление параметров сверления
            if change.operation_type == 'Сверление':
                if change.diameter is not None:
                    diam_elem = elem.find('Diameter', namespaces=namespaces)
                    if diam_elem is not None:
                        diam_elem.text = str(change.diameter)
                
                if change.depth is not None:
                    depth_elem = elem.find('EndDepth', namespaces=namespaces)
                    if depth_elem is not None:
                        depth_elem.text = str(change.depth)

            # Обновление параметров фрезерования
            elif change.operation_type == 'Фрезерование':
                if change.depth is not None:
                    depth_elem = elem.find('EndDepth', namespaces=namespaces)
                    if depth_elem is not None:
                        depth_elem.text = str(change.depth)

        doc.is_modified = True
        logger.info(f"Применено изменений: {len(changes)}")
        return doc

    def validate_document(self, doc: DocumentModel) -> List[ValidationError]:
        """Валидация документа перед сохранением."""
        errors = []

        for op in doc.operations:
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
        """Сохранение PGMX файла (ZIP-архива)."""
        target_path = output_path or doc.file_info.path
        
        logger.info(f"Сохранение PGMX файла: {target_path}")

        # Сериализация XML
        xml_bytes = serialize_xml(
            doc.xml_tree,
            encoding='utf-8',
            xml_declaration=True,
            pretty_print=True,
            namespaces=doc.namespaces
        )

        # Получение информации о ZIP из workpiece_params
        xml_filename = doc.workpiece_params.get('_zip_xml_filename', 'project.xml')
        other_files = doc.workpiece_params.get('_zip_other_files', {})

        # Обновление ZIP-архива
        try:
            saved_path = update_xml_in_zip(
                zip_path=doc.file_info.path,
                xml_filename=xml_filename,
                xml_content=xml_bytes,
                other_files=other_files,
                output_path=target_path
            )
            
            doc.is_modified = False
            logger.info(f"PGMX файл сохранён: {saved_path}")
            return saved_path
            
        except Exception as e:
            logger.error(f"Ошибка сохранения PGMX файла: {e}")
            raise IOError(f"Ошибка сохранения PGMX файла: {e}")
