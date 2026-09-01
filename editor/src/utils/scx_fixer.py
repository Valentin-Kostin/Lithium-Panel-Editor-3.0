"""
Утилиты для исправления ошибок в SCX файлах (NANXING).

Реализует полную логику проверки и исправления:
- Замена точек на запятые в Type="4" только в атрибуте Width
- Исправление Face="0" (заглушка для будущей логики)
- Пересчёт Z = Thickness - Z для Type="4"
- Поиск панелей где Length > 1200 И Width > 1200
- Исправление отверстий Ø2.5мм с Depth > 5мм → Depth = 5
- Вывод списка файлов с замечаниями
"""

import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Tuple, Optional
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
            'type4_fixed': [],           # Файлы с исправленными Type="4"
            'face0_found': [],           # Файлы с найденными Face="0"
            'z_recalculated': [],        # Файлы с пересчитанным Z
            'wide_panels': [],           # Файлы с панелями > 1200x1200
            'holes_fixed': [],           # Файлы с исправленными отверстиями
            'errors': []
        }
    
    def _parse_float(self, value: str) -> Optional[float]:
        """Парсинг числа из строки (точка или запятая)."""
        if not value:
            return None
        try:
            return float(value.replace(',', '.'))
        except ValueError:
            return None
    
    def _has_decimal_point(self, value: str) -> bool:
        """Проверяет, есть ли в значении десятичная точка (не в целых числах)."""
        if not value:
            return False
        # Проверяем наличие точки и что это не целое число
        if '.' in value:
            try:
                num = float(value)
                return num != int(num)
            except ValueError:
                return False
        return False
    
    def fix_type4_decimals_and_z(self) -> Tuple[int, List[str]]:
        """
        Исправляет Type="4" (фрезеровка в торце):
        1. Ищет десятичные дроби с точкой в атрибуте Width → меняет на запятую
        2. Face="0" → добавляет в список замечаний (исправление позже)
        3. Пересчитывает Z = Thickness - Z, EndZ = Thickness - EndZ
        
        Returns:
            Кортеж (количество обработанных файлов, список замечаний)
        """
        count = 0
        all_issues = []
        logger.info(f"Начало обработки Type=\"4\" в {self.directory}")
        
        for filename in os.listdir(self.directory):
            filepath = self.directory / filename
            if filepath.is_file() and filename.endswith('.SCX'):
                file_issues = []
                try:
                    tree = ET.parse(filepath)
                    root = tree.getroot()
                    modified = False
                    
                    # Получаем толщину панели из первого Panel элемента
                    panel_elem = root.find('.//Panel')
                    thickness = 0.0
                    panel_length = 0.0
                    panel_width = 0.0
                    
                    if panel_elem is not None:
                        thickness_str = panel_elem.attrib.get('Thickness', '0')
                        thickness = self._parse_float(thickness_str) or 0.0
                        
                        length_str = panel_elem.attrib.get('Length', '0')
                        width_str = panel_elem.attrib.get('Width', '0')
                        panel_length = self._parse_float(length_str) or 0.0
                        panel_width = self._parse_float(width_str) or 0.0
                    
                    # Проверка панелей > 1200x1200
                    if panel_length > 1200 and panel_width > 1200:
                        issue = f"{filename}: панель {panel_length}x{panel_width}мм (>1200x1200)"
                        file_issues.append(issue)
                        self.results['wide_panels'].append(issue)
                    
                    # Обработка всех Machining элементов
                    for machining in root.findall('.//Machining'):
                        mach_type = machining.attrib.get('Type', '')
                        
                        if mach_type == '4':
                            type4_modified = False
                            
                            # Проверка и исправление десятичных дробей с точкой на запятую ТОЛЬКО в атрибуте Width
                            attr_name = 'Width'
                            attr_value = machining.attrib.get(attr_name, '')
                            if self._has_decimal_point(attr_value):
                                new_value = attr_value.replace('.', ',')
                                machining.set(attr_name, new_value)
                                type4_modified = True
                                modified = True
                            
                            # Проверка Face="0"
                            face_value = machining.attrib.get('Face', '')
                            if face_value == '0':
                                issue = f"{filename}: Type=\"4\" с Face=\"0\" (требуется исправление)"
                                file_issues.append(issue)
                                if filename not in self.results['face0_found']:
                                    self.results['face0_found'].append(filename)
                            
                            # Пересчёт Z и EndZ: новый Z = Thickness - старый Z
                            z_str = machining.attrib.get('Z', '')
                            endz_str = machining.attrib.get('EndZ', '')
                            
                            if thickness > 0:
                                z_old = self._parse_float(z_str.replace(',', '.') if z_str else '0')
                                endz_old = self._parse_float(endz_str.replace(',', '.') if endz_str else '0')
                                
                                if z_old is not None:
                                    z_new = thickness - z_old
                                    machining.set('Z', str(round(z_new, 3)))
                                    modified = True
                                    type4_modified = True
                                
                                if endz_old is not None:
                                    endz_new = thickness - endz_old
                                    machining.set('EndZ', str(round(endz_new, 3)))
                                    modified = True
                                    type4_modified = True
                            
                            if type4_modified:
                                if filename not in self.results['type4_fixed']:
                                    self.results['type4_fixed'].append(filename)
                                if filename not in self.results['z_recalculated']:
                                    self.results['z_recalculated'].append(filename)
                    
                    # Сохранение изменений
                    if modified:
                        tree.write(filepath, encoding='utf-8', xml_declaration=True)
                        count += 1
                        logger.info(f"Файл {filename}: обработан Type=\"4\"")
                    
                    if file_issues:
                        all_issues.extend(file_issues)
                        
                except ET.ParseError as e:
                    error_msg = f"Ошибка XML в файле {filename}: {str(e)}"
                    logger.error(error_msg)
                    self.results['errors'].append(error_msg)
                except Exception as e:
                    error_msg = f"Ошибка обработки файла {filename}: {str(e)}"
                    logger.error(error_msg)
                    self.results['errors'].append(error_msg)
        
        logger.info(f"Завершено: обработано {count} файлов Type=\"4\"")
        return count, all_issues
    
    def fix_holes_diameter_2_5(self) -> Tuple[int, List[str]]:
        """
        Исправляет отверстия диаметром 2.5мм:
        - Если Depth > 5мм → устанавливает Depth = 5мм
        
        Returns:
            Кортеж (количество обработанных файлов, список замечаний)
        """
        count = 0
        all_issues = []
        logger.info(f"Начало обработки отверстий Ø2.5мм в {self.directory}")
        
        for filename in os.listdir(self.directory):
            filepath = self.directory / filename
            if filepath.is_file() and filename.endswith('.SCX'):
                file_issues = []
                try:
                    tree = ET.parse(filepath)
                    root = tree.getroot()
                    modified = False
                    holes_fixed_count = 0
                    
                    # Обработка всех Machining элементов
                    for machining in root.findall('.//Machining'):
                        diameter_str = machining.attrib.get('Diameter', '')
                        diameter = self._parse_float(diameter_str)
                        
                        # Проверка: диаметр = 2.5мм
                        if diameter is not None and abs(diameter - 2.5) < 0.001:
                            depth_str = machining.attrib.get('Depth', '')
                            depth = self._parse_float(depth_str)
                            
                            # Если глубина > 5мм → исправляем на 5мм
                            if depth is not None and depth > 5:
                                machining.set('Depth', '5')
                                modified = True
                                holes_fixed_count += 1
                                issue = f"{filename}: отверстие Ø2.5мм Depth={depth}→5мм"
                                file_issues.append(issue)
                    
                    # Сохранение изменений
                    if modified:
                        tree.write(filepath, encoding='utf-8', xml_declaration=True)
                        count += 1
                        if filename not in self.results['holes_fixed']:
                            self.results['holes_fixed'].append(filename)
                        logger.info(f"Файл {filename}: исправлено {holes_fixed_count} отверстий Ø2.5мм")
                    
                    if file_issues:
                        all_issues.extend(file_issues)
                        
                except ET.ParseError as e:
                    error_msg = f"Ошибка XML в файле {filename}: {str(e)}"
                    logger.error(error_msg)
                    self.results['errors'].append(error_msg)
                except Exception as e:
                    error_msg = f"Ошибка обработки файла {filename}: {str(e)}"
                    logger.error(error_msg)
                    self.results['errors'].append(error_msg)
        
        logger.info(f"Завершено: обработано {count} файлов с отверстиями Ø2.5мм")
        return count, all_issues
    
    def run_full_check(self) -> Dict[str, any]:
        """
        Запускает полную проверку и исправление всех замечаний.
        
        Returns:
            Словарь с результатами проверки.
        """
        logger.info("=" * 60)
        logger.info("ЗАПУСК ПОЛНОЙ ПРОВЕРКИ SCX ФАЙЛОВ")
        logger.info("=" * 60)
        
        # Сброс результатов
        self.results = {
            'files_processed': 0,
            'type4_fixed': [],
            'face0_found': [],
            'z_recalculated': [],
            'wide_panels': [],
            'holes_fixed': [],
            'all_issues': [],
            'errors': []
        }
        
        # Этап 1: Type="4" - десятичные дроби, Face="0", пересчёт Z
        count1, issues1 = self.fix_type4_decimals_and_z()
        self.results['files_processed'] += count1
        self.results['all_issues'].extend(issues1)
        
        # Этап 2: Отверстия Ø2.5мм с Depth > 5мм
        count2, issues2 = self.fix_holes_diameter_2_5()
        self.results['files_processed'] += count2
        self.results['all_issues'].extend(issues2)
        
        # Логирование итогов
        logger.info("=" * 60)
        logger.info("ИТОГИ ПРОВЕРКИ:")
        logger.info(f"  Файлов с Type=\"4\" исправлено: {len(self.results['type4_fixed'])}")
        logger.info(f"  Файлов с Face=\"0\" найдено: {len(self.results['face0_found'])}")
        logger.info(f"  Файлов с пересчитанным Z: {len(self.results['z_recalculated'])}")
        logger.info(f"  Файлов с широкими панелями (>1200x1200): {len(self.results['wide_panels'])}")
        logger.info(f"  Файлов с исправленными отверстиями Ø2.5: {len(self.results['holes_fixed'])}")
        logger.info(f"  Ошибок: {len(self.results['errors'])}")
        logger.info("=" * 60)
        
        # Формирование итогового отчёта
        report_lines = []
        report_lines.append("\n" + "=" * 60)
        report_lines.append("ОТЧЁТ О НАЙДЕННЫХ ЗАМЕЧАНИЯХ")
        report_lines.append("=" * 60)
        
        if self.results['type4_fixed']:
            report_lines.append(f"\n📁 Файлы с исправленными Type=\"4\" (десятичные дроби):")
            for f in sorted(self.results['type4_fixed']):
                report_lines.append(f"   • {f}")
        
        if self.results['face0_found']:
            report_lines.append(f"\n⚠️  Файлы с Face=\"0\" в Type=\"4\" (требуют внимания):")
            for f in sorted(self.results['face0_found']):
                report_lines.append(f"   • {f}")
        
        if self.results['wide_panels']:
            report_lines.append(f"\n📏 Файлы с панелями > 1200x1200мм:")
            for issue in sorted(self.results['wide_panels']):
                report_lines.append(f"   • {issue}")
        
        if self.results['holes_fixed']:
            report_lines.append(f"\n🔩 Файлы с исправленными отверстиями Ø2.5мм (Depth>5→5):")
            for f in sorted(self.results['holes_fixed']):
                report_lines.append(f"   • {f}")
        
        if self.results['all_issues']:
            report_lines.append(f"\n📋 Полный список замечаний ({len(self.results['all_issues'])}):")
            for issue in sorted(self.results['all_issues']):
                report_lines.append(f"   • {issue}")
        
        if self.results['errors']:
            report_lines.append(f"\n❌ Ошибки ({len(self.results['errors'])}):")
            for err in self.results['errors']:
                report_lines.append(f"   • {err}")
        
        report_lines.append("\n" + "=" * 60)
        
        full_report = "\n".join(report_lines)
        logger.info(full_report)
        
        return self.results


def process_scx_directory(directory: str, operation: str = 'all') -> Dict[str, any]:
    """
    Универсальная функция для обработки SCX файлов.
    
    Args:
        directory: Путь к директории с SCX файлами.
        operation: Тип операции ('type4', 'holes', 'all').
    
    Returns:
        Словарь с результатами обработки.
    """
    fixer = ScxFixer(directory)
    
    if operation == 'type4':
        fixer.fix_type4_decimals_and_z()
    elif operation == 'holes':
        fixer.fix_holes_diameter_2_5()
    elif operation == 'all':
        fixer.run_full_check()
    else:
        raise ValueError(f"Неизвестная операция: {operation}")
    
    return fixer.get_results()


# Добавляем метод get_results если его нет
if not hasattr(ScxFixer, 'get_results'):
    ScxFixer.get_results = lambda self: self.results
