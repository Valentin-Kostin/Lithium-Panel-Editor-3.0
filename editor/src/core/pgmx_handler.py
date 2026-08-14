"""
Обработчик формата .PGMX от SCM Group.
PGMX файлы представляют собой ZIP-архивы, содержащие XML файлы с CNC данными.
"""
import zipfile
import tempfile
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional
from xml.etree import ElementTree as ET
from lxml import etree

from .base_handler import BaseFormatHandler, OperationData, FileMetadata
from .encoding_detector import detect_encoding


class PgmxFormatHandler(BaseFormatHandler):
    """
    Обработчик файлов .PGMX (формат SCM Group).
    
    Структура:
    - .pgmx это ZIP-архив
    - Содержит main.xml или подобный XML файл с операциями
    - Операции определены в специфичных XML узлах
    """
    
    # Распространённые пути внутри PGMX ZIP
    POSSIBLE_XML_PATHS = [
        'main.xml',
        'program.xml', 
        'data.xml',
        'content.xml',
        ''  # Попытаться на корневом уровне
    ]
    
    def __init__(self, file_path: Optional[Path] = None):
        super().__init__(file_path)
        self.zip_path: Optional[Path] = None
        self.temp_dir: Optional[Path] = None
        self.internal_xml_path: str = ""
        self.zip_contents: Dict[str, bytes] = {}  # Кэшировать содержимое ZIP
        
    def load(self, path: Path) -> bool:
        """
        Загрузить PGMX файл: распаковать ZIP, найти XML, распарсить операции.
        """
        try:
            self.file_path = path
            self.temp_dir = Path(tempfile.mkdtemp(prefix="pgmx_"))
            
            # Распаковать содержимое ZIP
            with zipfile.ZipFile(path, 'r') as zf:
                # Сохранить всё содержимое для последующей упаковки
                for name in zf.namelist():
                    self.zip_contents[name] = zf.read(name)
                
                # Найти главный XML файл
                xml_found = False
                for xml_name in self.POSSIBLE_XML_PATHS:
                    if xml_name in zf.namelist():
                        self.internal_xml_path = xml_name
                        xml_found = True
                        break
                
                if not xml_found:
                    # Попытаться найти любой XML файл
                    for name in zf.namelist():
                        if name.endswith('.xml'):
                            self.internal_xml_path = name
                            xml_found = True
                            break
                
                if not xml_found:
                    return False
                
                # Извлечь и распарсить XML
                xml_content = zf.read(self.internal_xml_path)
                
            # Определить кодировку из байтового содержимого
            # Создать временный файл для определения кодировки
            import tempfile as tmp_module
            with tmp_module.NamedTemporaryFile(mode='wb', delete=False) as tmp:
                tmp.write(xml_content)
                tmp_path = Path(tmp.name)
            
            try:
                encoding, _ = detect_encoding(tmp_path)
            finally:
                tmp_path.unlink()  # Очистить временный файл
            
            xml_str = xml_content.decode(encoding, errors='replace')
            
            # Парсинг XML - сохранить оригинальную кодировку для внутренней структуры PGMX
            # PGMX файлы обычно используют UTF-8 внутри
            try:
                self.raw_data = etree.fromstring(xml_str.encode('utf-8'))
            except Exception as parse_error:
                # Если парсинг UTF-8 не удался, попробовать с определённой кодировкой
                print(f"Warning: UTF-8 parsing failed, trying with detected encoding {encoding}: {parse_error}")
                self.raw_data = etree.fromstring(xml_content)
            
            # Извлечь метаданные и операции
            self._extract_metadata()
            self._extract_operations()
            
            return True
            
        except Exception as e:
            print(f"Error loading PGMX: {e}")
            return False
    
    def _extract_metadata(self):
        """Извлечь метаданные файла из PGMX XML."""
        if self.raw_data is None:
            return
            
        # Распространённые пути метаданных PGMX (настроить под реальную структуру)
        material = ""
        thickness = 0.0
        width = 0.0
        length = 0.0
        description = ""
        
        # Попробовать различные возможные расположения метаданных
        for elem in self.raw_data.iter():
            tag = elem.tag.lower()
            
            # Информация о материале
            if 'material' in tag or 'mat' in tag:
                material = elem.text or elem.get('name', '')
                if elem.get('thickness'):
                    thickness = float(elem.get('thickness', 0))
                    
            # Размеры
            if 'width' in tag or 'x_size' in tag:
                try:
                    width = float(elem.text or 0)
                except (ValueError, TypeError):
                    pass
                    
            if 'length' in tag or 'y_size' in tag:
                try:
                    length = float(elem.text or 0)
                except (ValueError, TypeError):
                    pass
                    
            # Описание
            if 'description' in tag or 'comment' in tag:
                description = elem.text or ''
        
        self.metadata = FileMetadata(
            filename=self.file_path.name if self.file_path else "",
            material=material,
            thickness=thickness,
            width=width,
            length=length,
            description=description
        )
    
    def _extract_operations(self):
        """Extract operations from PGMX XML."""
        if self.raw_data is None:
            return
            
        self.operations = []
        
        # Шаблоны операций PGMX (настроить под реальную структуру)
        operation_tags = [
            './/Operation',
            './/Process',
            './/WorkingUnit',
            './/ToolPath',
            './/MachiningOp',
            '*[@type="operation"]',
            '*[@class="process"]'
        ]
        
        for op_tag in operation_tags:
            try:
                ops = self.raw_data.xpath(op_tag)
                for idx, op_elem in enumerate(ops):
                    op_data = self._parse_operation_element(op_elem, idx)
                    if op_data:
                        self.operations.append(op_data)
            except Exception:
                continue
        
        # Если операции не найдены со стандартными тегами, попробовать общий подход
        if not self.operations:
            self._extract_operations_generic()
    
    def _parse_operation_element(self, elem: Any, index: int) -> Optional[OperationData]:
        """Parse a single operation XML element."""
        try:
            # Извлечь общие поля
            op_id = elem.get('id', f"op_{index}")
            name = elem.get('name', elem.get('description', f"Operation {index}"))
            
            # Информация об инструменте
            tool_elem = elem.find('.//Tool') or elem.find('.//tool')
            tool_id = tool_elem.get('id', '') if tool_elem is not None else elem.get('tool_id', '')
            tool_name = tool_elem.get('name', '') if tool_elem is not None else elem.get('tool_name', '')
            
            # Параметры
            feed_rate = 0.0
            speed = 0.0
            depth = 0.0
            
            # Попытаться найти скорость подачи
            feed_elem = elem.find('.//FeedRate') or elem.find('.//feed') or elem.find('.//Feed')
            if feed_elem is not None:
                try:
                    feed_rate = float(feed_elem.text or feed_elem.get('value', 0))
                except (ValueError, TypeError):
                    pass
            else:
                try:
                    feed_rate = float(elem.get('feed', elem.get('feedrate', 0)))
                except (ValueError, TypeError):
                    pass
            
            # Попытаться найти скорость (об/мин)
            speed_elem = elem.find('.//Speed') or elem.find('.//rpm') or elem.find('.//RPM')
            if speed_elem is not None:
                try:
                    speed = float(speed_elem.text or speed_elem.get('value', 0))
                except (ValueError, TypeError):
                    pass
            else:
                try:
                    speed = float(elem.get('speed', elem.get('rpm', 0)))
                except (ValueError, TypeError):
                    pass
            
            # Попытаться найти глубину
            depth_elem = elem.find('.//Depth') or elem.find('.//depth') or elem.find('.//Z')
            if depth_elem is not None:
                try:
                    depth = float(depth_elem.text or depth_elem.get('value', 0))
                except (ValueError, TypeError):
                    pass
            else:
                try:
                    depth = float(elem.get('depth', elem.get('z_depth', 0)))
                except (ValueError, TypeError):
                    pass
            
            # Собрать дополнительные параметры
            params = {}
            for attr_name, attr_val in elem.attrib.items():
                if attr_name not in ['id', 'name', 'tool_id', 'tool_name', 'feed', 'speed', 'depth']:
                    params[attr_name] = attr_val
            
            return OperationData(
                id=op_id,
                name=name,
                tool_id=tool_id,
                tool_name=tool_name,
                feed_rate=feed_rate,
                speed=speed,
                depth=depth,
                parameters=params,
                xml_node_ref=elem
            )
            
        except Exception as e:
            print(f"Error parsing operation element: {e}")
            return None
    
    def _extract_operations_generic(self):
        """Generic extraction when standard patterns fail."""
        if self.raw_data is None:
            return
            
        index = 0
        for elem in self.raw_data.iter():
            # Искать элементы, которые могут быть операциями
            if any(k in elem.tag.lower() for k in ['op', 'process', 'work', 'tool', 'path']):
                op_data = self._parse_operation_element(elem, index)
                if op_data and op_data.name != f"Operation {index}":
                    self.operations.append(op_data)
                    index += 1
    
    def save(self, path: Path) -> bool:
        """
        Save changes back to PGMX file.
        Rebuilds the ZIP archive with modified XML.
        """
        try:
            if self.raw_data is None:
                return False
            
            # Сериализовать изменённый XML
            xml_bytes = etree.tostring(
                self.raw_data,
                pretty_print=True,
                xml_declaration=True,
                encoding='UTF-8'
            )
            
            # Обновить содержимое ZIP
            self.zip_contents[self.internal_xml_path] = xml_bytes
            
            # Создать новый ZIP файл
            with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for name, content in self.zip_contents.items():
                    zf.writestr(name, content)
            
            return True
            
        except Exception as e:
            print(f"Error saving PGMX: {e}")
            return False
    
    def get_operations(self) -> List[OperationData]:
        """Вернуть список распарсенных операций."""
        return self.operations
    
    def update_operation(self, operation_id: str, changes: Dict[str, Any]) -> bool:
        """Обновить конкретную операцию новыми значениями."""
        for op in self.operations:
            if op.id == operation_id:
                try:
                    # Обновить локальные данные
                    for key, value in changes.items():
                        if hasattr(op, key):
                            setattr(op, key, value)
                    
                    # Обновить XML узел
                    if op.xml_node_ref is not None:
                        for key, value in changes.items():
                            if key == 'name':
                                op.xml_node_ref.set('name', str(value))
                            elif key == 'feed_rate':
                                # Попытаться найти и обновить элемент скорости подачи
                                feed_elem = op.xml_node_ref.find('.//FeedRate') or op.xml_node_ref.find('.//feed')
                                if feed_elem is not None:
                                    feed_elem.text = str(value)
                                else:
                                    op.xml_node_ref.set('feed', str(value))
                            elif key == 'speed':
                                speed_elem = op.xml_node_ref.find('.//Speed') or op.xml_node_ref.find('.//rpm')
                                if speed_elem is not None:
                                    speed_elem.text = str(value)
                                else:
                                    op.xml_node_ref.set('speed', str(value))
                            elif key == 'depth':
                                depth_elem = op.xml_node_ref.find('.//Depth') or op.xml_node_ref.find('.//depth')
                                if depth_elem is not None:
                                    depth_elem.text = str(value)
                                else:
                                    op.xml_node_ref.set('depth', str(value))
                            elif key == 'parameters':
                                for param_key, param_val in value.items():
                                    op.xml_node_ref.set(param_key, param_val)
                    
                    return True
                    
                except Exception as e:
                    print(f"Error updating operation: {e}")
                    return False
        
        return False
    
    def get_xml_tree(self) -> Any:
        """Return the XML tree structure."""
        if self.raw_data is None:
            return None
        # Обернуть корневой элемент в ElementTree если это просто Element
        if isinstance(self.raw_data, etree._Element):
            return etree.ElementTree(self.raw_data)
        return self.raw_data
    
    def cleanup(self):
        """Clean up temporary files."""
        if self.temp_dir and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        self.temp_dir = None
