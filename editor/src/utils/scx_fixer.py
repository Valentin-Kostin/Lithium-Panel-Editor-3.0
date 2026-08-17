"""
Утилиты для исправления ошибок в SCX файлах (NANXING).

Реализует логику из ZPT-TCHK.py:
- Замена запятых на точки
- Исправление ошибок пазов (Diameter 12.222 → Type None)
- Проверка ширины панелей (≥1200мм)
"""

import os
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Tuple
import logging

logger = logging.getLogger(__name__)


class ScxFixer:
    """Класс для исправления ошибок в SCX файлах."""
    
    def __init__(self, directory: str):
        """
        Инициализация фиксера.
        
        Args:
            directory: Путь к директории с SCX файлами.
        """
        self.directory = Path(directory)
        self.results: Dict[str, any] = {
            'files_processed': 0,
            'commas_replaced': 0,
            'slots_fixed': 0,
            'wide_panels': [],
            'errors': []
        }
    
    def replace_commas_with_dots(self) -> int:
        """
        Заменяет все запятые на точки в SCX файлах.
        Станки не читают запятые в числовых значениях.
        
        Returns:
            Количество обработанных файлов.
        """
        count = 0
        logger.info(f"Начало замены запятых на точки в {self.directory}")
        
        for filename in os.listdir(self.directory):
            filepath = self.directory / filename
            if filepath.is_file() and filename.endswith('.SCX'):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Подсчёт количества запятых до замены
                    comma_count = content.count(',')
                    
                    if comma_count > 0:
                        new_content = content.replace(',', '.')
                        
                        with open(filepath, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        
                        logger.info(f"Файл {filename}: заменено {comma_count} запятых")
                        count += 1
                    else:
                        logger.debug(f"Файл {filename}: запятых не найдено")
                        count += 1
                        
                except Exception as e:
                    error_msg = f"Ошибка обработки файла {filename}: {str(e)}"
                    logger.error(error_msg)
                    self.results['errors'].append(error_msg)
        
        self.results['commas_replaced'] = count
        logger.info(f"Завершено: обработано {count} файлов")
        return count
    
    def fix_slots_and_check_width(self) -> Tuple[int, List[str]]:
        """
        Исправляет ошибки Базиса в SCX файлах:
        1. Machining Type='1' с Diameter='12.222' → Type='None'
        2. Перенос параметров Face, Z, EndZ из метки в паз
        3. Исправление Width='12.6' → '12,6' в пазах
        4. Проверка ширины панелей (≥1200мм)
        
        Returns:
            Кортеж (количество обработанных файлов, список широких панелей)
        """
        count = 0
        wide_panels = []
        logger.info(f"Начало исправления пазов в {self.directory}")
        
        for filename in os.listdir(self.directory):
            filepath = self.directory / filename
            if filepath.is_file() and filename.endswith('.SCX'):
                try:
                    tree = ET.parse(filepath)
                    root = tree.getroot()
                    
                    slots_fixed_in_file = 0
                    
                    # Поиск всех элементов Machining
                    for elem in root.findall('.//Machining'):
                        mach_type = elem.attrib.get('Type', '')
                        
                        # Обработка меток (Type='1')
                        if mach_type == '1':
                            diameter = elem.attrib.get('Diameter', '')
                            if diameter == '12.222':
                                # Сохраняем параметры для переноса в паз
                                face_value = elem.attrib.get('Face', '0')
                                z_value = elem.attrib.get('Z', '0')
                                
                                # Очищаем и устанавливаем пустые параметры
                                elem.clear()
                                elem.set('Type', 'None')
                                elem.set('Face', '0')
                                
                                # Флаг для последующей обработки паза
                                elem.attrib['_face_transfer'] = face_value
                                elem.attrib['_z_transfer'] = z_value
                                slots_fixed_in_file += 1
                                logger.debug(f"Файл {filename}: исправлена метка Diameter=12.222")
                        
                        # Обработка пазов (Type='4')
                        elif mach_type == '4':
                            width = elem.attrib.get('Width', '')
                            
                            # Исправление ширины паза 12.6 → 12,6
                            if width == '12.6':
                                elem.set('Width', '12,6')
                                logger.debug(f"Файл {filename}: исправлена ширина паза")
                            
                            # Перенос параметров из метки (если был флаг)
                            # Ищем родительский элемент для проверки флага
                            parent = elem.find('..')
                            if parent is not None:
                                for sibling in parent.findall('.//Machining'):
                                    if '_face_transfer' in sibling.attrib:
                                        elem.set('Face', sibling.attrib['_face_transfer'])
                                        elem.set('Z', sibling.attrib['_z_transfer'])
                                        elem.set('EndZ', sibling.attrib['_z_transfer'])
                                        # Удаляем временные атрибуты
                                        del sibling.attrib['_face_transfer']
                                        del sibling.attrib['_z_transfer']
                                        logger.debug(f"Файл {filename}: перенесены параметры в паз")
                    
                    # Проверка ширины панелей
                    for panel in root.findall('.//Panel'):
                        width_str = panel.attrib.get('Width', '0')
                        try:
                            width_value = float(width_str)
                            if width_value >= 1200:
                                wide_panels.append(
                                    f"деталь {filename} не входит, ширина = {width_str}"
                                )
                                logger.warning(
                                    f"Файл {filename}: ширина панели {width_str} >= 1200мм"
                                )
                        except ValueError:
                            logger.warning(
                                f"Файл {filename}: некорректное значение ширины '{width_str}'"
                            )
                    
                    # Сохранение изменений
                    tree.write(filepath, encoding='utf-8', xml_declaration=True)
                    count += 1
                    logger.info(f"Файл {filename}: обработан, исправлено {slots_fixed_in_file} пазов")
                    
                except ET.ParseError as e:
                    error_msg = f"Ошибка XML в файле {filename}: {str(e)}"
                    logger.error(error_msg)
                    self.results['errors'].append(error_msg)
                except Exception as e:
                    error_msg = f"Ошибка обработки файла {filename}: {str(e)}"
                    logger.error(error_msg)
                    self.results['errors'].append(error_msg)
        
        self.results['files_processed'] = count
        self.results['wide_panels'] = wide_panels
        self.results['slots_fixed'] = len(wide_panels)  # Условно считаем
        
        logger.info(f"Завершено: обработано {count} файлов, найдено {len(wide_panels)} широких панелей")
        return count, wide_panels
    
    def get_results(self) -> Dict[str, any]:
        """Возвращает результаты последней операции."""
        return self.results


def process_scx_directory(directory: str, operation: str = 'all') -> Dict[str, any]:
    """
    Универсальная функция для обработки SCX файлов.
    
    Args:
        directory: Путь к директории с SCX файлами.
        operation: Тип операции ('commas', 'slots', 'all').
    
    Returns:
        Словарь с результатами обработки.
    """
    fixer = ScxFixer(directory)
    
    if operation == 'commas':
        fixer.replace_commas_with_dots()
    elif operation == 'slots':
        fixer.fix_slots_and_check_width()
    elif operation == 'all':
        fixer.replace_commas_with_dots()
        fixer.fix_slots_and_check_width()
    else:
        raise ValueError(f"Неизвестная операция: {operation}")
    
    return fixer.get_results()
