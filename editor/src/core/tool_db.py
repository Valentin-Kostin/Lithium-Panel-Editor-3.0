"""
Модуль для работы с базой инструментов (def.tlgx).
Парсит XML файл библиотеки инструментов и предоставляет доступ к данным.
"""
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Optional, List
import logging

logger = logging.getLogger(__name__)

class ToolDB:
    """Класс для управления базой инструментов."""
    
    def __init__(self):
        self.tools: Dict[str, dict] = {}  # Key: ToolID (e.g., "E007"), Value: tool data
        self.file_path: Optional[Path] = None
        self.is_loaded = False

    def load(self, file_path: str) -> bool:
        """
        Загружает базу инструментов из файла .tlgx.
        
        Args:
            file_path: Путь к файлу def.tlgx
            
        Returns:
            True если загрузка успешна, иначе False.
        """
        path = Path(file_path)
        if not path.exists():
            logger.error(f"Файл базы инструментов не найден: {file_path}")
            return False

        try:
            # def.tlgx имеет сложные namespaces SCM Group
            tree = ET.parse(path)
            root = tree.getroot()
            
            # Определяем namespaces из корня
            ns = {
                'main': 'http://schemas.datacontract.org/2004/07/ScmGroup.XCam.ToolDataModel.Common',
                'tool': 'http://schemas.datacontract.org/2004/07/ScmGroup.XCam.ToolDataModel.Tool',
                'util': 'http://schemas.datacontract.org/2004/07/ScmGroup.XCam.MachiningDataModel.Utility'
            }
            
            # Сброс старых данных
            self.tools.clear()
            
            # Ищем все CoreTool элементы
            count = 0
            for core_tool in root.findall('.//main:Tools/main:CoreTool', ns):
                # Получаем Name инструмента
                name_elem = core_tool.find('util:Name', ns)
                tool_name = name_elem.text if name_elem is not None else None
                
                if not tool_name:
                    continue
                
                # Получаем диаметр из ToolDimension
                dim_elem = core_tool.find('.//tool:ToolDimension/tool:Diameter', ns)
                diameter = float(dim_elem.text) if dim_elem is not None and dim_elem.text else 0.0
                
                # Получаем описание
                desc_elem = core_tool.find('util:Description', ns)
                description = desc_elem.text if desc_elem is not None else ""
                
                # Сохраняем инструмент
                self.tools[str(tool_name)] = {
                    'id': str(tool_name),
                    'name': str(tool_name),
                    'diameter': diameter,
                    'description': description,
                    'xml_element': core_tool
                }
                count += 1
            
            self.file_path = path
            self.is_loaded = True
            logger.info(f"База инструментов загружена: {path.name}. Найдено инструментов: {count}")
            return True
            
        except ET.ParseError as e:
            logger.error(f"Ошибка парсинга XML в файле {file_path}: {e}")
            return False
        except Exception as e:
            logger.error(f"Неожиданная ошибка при загрузке базы инструментов: {e}")
            return False

    def get_tool_by_id(self, tool_id: str) -> Optional[dict]:
        """Получить данные инструмента по ID."""
        return self.tools.get(str(tool_id))

    def find_tools_by_diameter(self, target_diameter: float, tolerance: float = 0.1) -> List[dict]:
        """
        Найти инструменты с диаметром, близким к целевому.
        
        Args:
            target_diameter: Целевой диаметр (например, 2.22)
            tolerance: Допуск (по умолчанию 0.1 мм)
            
        Returns:
            Список инструментов, попадающих в диапазон.
        """
        matches = []
        for tool in self.tools.values():
            if tool['diameter'] > 0:
                if abs(tool['diameter'] - target_diameter) <= tolerance:
                    matches.append(tool)
        return matches

    def get_replacement_tool(self, replacement_id: str = "E007") -> Optional[dict]:
        """
        Получить инструмент замены по умолчанию (например, E007).
        Если его нет в базе, возвращает None.
        """
        return self.get_tool_by_id(replacement_id)

# Глобальный экземпляр (Singleton pattern для удобства доступа из UI)
global_tool_db = ToolDB()
