"""
Модуль для валидации и сравнения CSV файлов с данными из PGMX проектов.
Реализует логику из ZPT-TCHK.py для подсчета деталей и сверки спецификаций.
"""

import logging
import os
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import csv
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class PartInfo:
    """Информация о детали из PGMX или CSV."""
    name: str
    length: float
    width: float
    thickness: float
    quantity: int
    material: str = ""
    source: str = "unknown"  # 'pgmx' или 'csv'


@dataclass
class ValidationResult:
    """Результат валидации CSV vs PGMX."""
    is_valid: bool
    pgmx_parts_count: int
    csv_parts_count: int
    matched_parts: int
    mismatched_parts: List[Dict]
    missing_in_csv: List[PartInfo]
    missing_in_pgmx: List[PartInfo]
    errors: List[str]


class CsvPgmxValidator:
    """
    Класс для валидации и сравнения CSV файлов с данными из PGMX проектов.
    
    Атрибуты:
        encoding: Кодировка для чтения CSV файлов (по умолчанию 'utf-8').
        delimiter: Разделитель в CSV файлах (по умолчанию ';').
    """
    
    def __init__(self, encoding: str = 'utf-8', delimiter: str = ';'):
        self.encoding = encoding
        self.delimiter = delimiter
        logger.info(f"CsvPgmxValidator инициализирован: encoding={encoding}, delimiter={delimiter}")
    
    def extract_pgmx_data(self, pgmx_path: str) -> List[PartInfo]:
        """
        Извлекает данные о деталях из PGMX файла.
        
        PGMX - это ZIP-архив, содержащий XML файл проекта.
        
        Args:
            pgmx_path: Путь к .pgmx файлу.
            
        Returns:
            Список объектов PartInfo с данными о деталях.
            
        Raises:
            FileNotFoundError: Если файл не найден.
            ValueError: Если файл не является корректным PGMX.
        """
        parts = []
        pgmx_path = Path(pgmx_path)
        
        if not pgmx_path.exists():
            raise FileNotFoundError(f"PGMX файл не найден: {pgmx_path}")
        
        if not pgmx_path.suffix.lower() == '.pgmx':
            raise ValueError(f"Файл должен иметь расширение .pgmx: {pgmx_path}")
        
        try:
            with zipfile.ZipFile(pgmx_path, 'r') as zip_ref:
                # Ищем основной XML файл проекта
                xml_files = [f for f in zip_ref.namelist() if f.endswith('.xml')]
                
                if not xml_files:
                    raise ValueError(f"В PGMX архиве не найдены XML файлы: {pgmx_path}")
                
                # Обычно основной файл имеет имя проекта или project.xml
                main_xml = None
                for xml_file in xml_files:
                    if 'project' in xml_file.lower() or xml_file == xml_files[0]:
                        main_xml = xml_file
                        break
                
                if main_xml:
                    with zip_ref.open(main_xml) as xml_file:
                        tree = ET.parse(xml_file)
                        root = tree.getroot()
                        
                        # Поиск элементов деталей в XML
                        # Формат может отличаться в зависимости от версии SCM
                        part_elements = root.findall('.//part') or \
                                       root.findall('.//Part') or \
                                       root.findall('.//{*}part') or \
                                       root.findall('.//{*}Part')
                        
                        if not part_elements:
                            # Пробуем найти по другим возможным тегам
                            part_elements = root.findall('.//item') or \
                                           root.findall('.//Item') or \
                                           root.findall('.//component') or \
                                           root.findall('.//Component')
                        
                        for part_elem in part_elements:
                            try:
                                part_info = self._parse_part_element(part_elem, 'pgmx')
                                if part_info:
                                    parts.append(part_info)
                            except Exception as e:
                                logger.warning(f"Ошибка парсинга элемента детали: {e}")
                                continue
                
                logger.info(f"Извлечено {len(parts)} деталей из PGMX: {pgmx_path.name}")
                
        except zipfile.BadZipFile as e:
            raise ValueError(f"Некорректный PGMX файл (не является ZIP архивом): {e}")
        except ET.ParseError as e:
            raise ValueError(f"Ошибка парсинга XML в PGMX: {e}")
        
        return parts
    
    def _parse_part_element(self, elem: ET.Element, source: str) -> Optional[PartInfo]:
        """
        Парсит XML элемент детали в объект PartInfo.
        
        Args:
            elem: XML элемент детали.
            source: Источник данных ('pgmx' или 'csv').
            
        Returns:
            Объект PartInfo или None если не удалось распарсить.
        """
        try:
            # Попытка извлечь атрибуты различными способами
            name = (elem.get('name') or elem.get('Name') or 
                   elem.get('id') or elem.get('ID') or 
                   elem.text or f"part_{hash(elem)}")
            
            # Размеры могут быть в атрибутах или дочерних элементах
            length = self._get_float_value(elem, ['length', 'Length', 'L', 'l'])
            width = self._get_float_value(elem, ['width', 'Width', 'W', 'w'])
            thickness = self._get_float_value(elem, ['thickness', 'Thickness', 'T', 't', 'thick'])
            quantity = self._get_int_value(elem, ['quantity', 'Quantity', 'qty', 'Qty', 'count'], default=1)
            material = (elem.get('material') or elem.get('Material') or 
                       elem.get('mat') or elem.get('Mat') or "")
            
            # Если размеры в дочерних элементах
            if length is None:
                length_elem = elem.find('.//length') or elem.find('.//Length')
                if length_elem is not None:
                    length = self._parse_float(length_elem.text)
            
            if width is None:
                width_elem = elem.find('.//width') or elem.find('.//Width')
                if width_elem is not None:
                    width = self._parse_float(width_elem.text)
            
            if thickness is None:
                thick_elem = elem.find('.//thickness') or elem.find('.//Thickness')
                if thick_elem is not None:
                    thickness = self._parse_float(thick_elem.text)
            
            # Пропускаем детали без обязательных размеров
            if length is None or width is None or thickness is None:
                return None
            
            return PartInfo(
                name=str(name).strip(),
                length=length,
                width=width,
                thickness=thickness,
                quantity=quantity,
                material=material,
                source=source
            )
            
        except Exception as e:
            logger.warning(f"Ошибка при парсинге элемента детали: {e}")
            return None
    
    def _get_float_value(self, elem: ET.Element, attr_names: List[str]) -> Optional[float]:
        """Извлекает float значение из атрибута элемента."""
        for attr in attr_names:
            value = elem.get(attr)
            if value:
                return self._parse_float(value)
        return None
    
    def _get_int_value(self, elem: ET.Element, attr_names: List[str], default: int = 0) -> int:
        """Извлекает int значение из атрибута элемента."""
        for attr in attr_names:
            value = elem.get(attr)
            if value:
                try:
                    return int(float(value.replace(',', '.')))
                except (ValueError, TypeError):
                    pass
        return default
    
    def _parse_float(self, value: str) -> Optional[float]:
        """Парсит строку в float, обрабатывая запятые как разделители."""
        if value is None:
            return None
        try:
            return float(str(value).replace(',', '.').strip())
        except (ValueError, TypeError):
            return None
    
    def parse_csv(self, csv_path: str) -> List[PartInfo]:
        """
        Парсит CSV файл со спецификацией деталей.
        
        Ожидает колонки: name, length, width, thickness, quantity, material
        (или их вариации на русском/английском)
        
        Args:
            csv_path: Путь к CSV файлу.
            
        Returns:
            Список объектов PartInfo.
            
        Raises:
            FileNotFoundError: Если файл не найден.
            ValueError: Если файл не является корректным CSV.
        """
        parts = []
        csv_path = Path(csv_path)
        
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV файл не найден: {csv_path}")
        
        # Попытка определить кодировку
        encodings_to_try = [self.encoding, 'utf-8-sig', 'cp1251', 'latin1']
        
        for encoding in encodings_to_try:
            try:
                with open(csv_path, 'r', encoding=encoding, newline='') as f:
                    # Пробуем разные разделители
                    for delimiter in [self.delimiter, ',', '\t']:
                        try:
                            f.seek(0)
                            reader = csv.DictReader(f, delimiter=delimiter)
                            
                            if reader.fieldnames:
                                # Нормализуем имена колонок
                                fieldnames_lower = [fn.lower().strip() if fn else '' for fn in reader.fieldnames]
                                
                                # Маппинг возможных названий колонок
                                name_col = self._find_column(fieldnames_lower, ['name', 'имя', 'название', 'detail', 'деталь'])
                                length_col = self._find_column(fieldnames_lower, ['length', 'длина', 'l', 'len'])
                                width_col = self._find_column(fieldnames_lower, ['width', 'ширина', 'w', 'wid'])
                                thickness_col = self._find_column(fieldnames_lower, ['thickness', 'толщина', 't', 'thick'])
                                quantity_col = self._find_column(fieldnames_lower, ['quantity', 'количество', 'qty', 'count', 'кол'])
                                material_col = self._find_column(fieldnames_lower, ['material', 'материал', 'mat'])
                                
                                if all([name_col, length_col, width_col, thickness_col]):
                                    f.seek(0)
                                    reader = csv.DictReader(f, delimiter=delimiter)
                                    
                                    for row_num, row in enumerate(reader, start=2):
                                        try:
                                            part_info = PartInfo(
                                                name=str(row.get(reader.fieldnames[name_col], '')).strip(),
                                                length=self._parse_float(row.get(reader.fieldnames[length_col])),
                                                width=self._parse_float(row.get(reader.fieldnames[width_col])),
                                                thickness=self._parse_float(row.get(reader.fieldnames[thickness_col])),
                                                quantity=self._parse_int(row.get(reader.fieldnames[quantity_col]), default=1) if quantity_col is not None else 1,
                                                material=str(row.get(reader.fieldnames[material_col], '')).strip() if material_col is not None else "",
                                                source='csv'
                                            )
                                            
                                            if part_info.length and part_info.width and part_info.thickness:
                                                parts.append(part_info)
                                            
                                        except Exception as e:
                                            logger.warning(f"Ошибка парсинга строки {row_num} в CSV: {e}")
                                            continue
                                    
                                    if parts:
                                        logger.info(f"Распарсено {len(parts)} деталей из CSV: {csv_path.name} (кодировка: {encoding}, разделитель: {delimiter})")
                                        return parts
                                        
                        except csv.Error:
                            continue
                            
            except UnicodeDecodeError:
                continue
        
        raise ValueError(f"Не удалось распарсить CSV файл: {csv_path}")
    
    def _find_column(self, fieldnames: List[str], possible_names: List[str]) -> Optional[int]:
        """Находит индекс колонки по списку возможных названий."""
        for i, field in enumerate(fieldnames):
            if field in possible_names:
                return i
        return None
    
    def _parse_int(self, value: str, default: int = 0) -> int:
        """Парсит строку в int."""
        if value is None:
            return default
        try:
            return int(float(str(value).replace(',', '.').strip()))
        except (ValueError, TypeError):
            return default
    
    def validate(self, pgmx_path: str, csv_path: str, tolerance: float = 0.1) -> ValidationResult:
        """
        Выполняет валидацию CSV файла против данных из PGMX.
        
        Сравнивает детали по имени и размерам с учетом допустимой погрешности.
        
        Args:
            pgmx_path: Путь к .pgmx файлу.
            csv_path: Путь к .csv файлу.
            tolerance: Допустимая погрешность размеров в мм.
            
        Returns:
            ValidationResult с результатами сравнения.
        """
        errors = []
        mismatched = []
        missing_in_csv = []
        missing_in_pgmx = []
        
        try:
            pgmx_parts = self.extract_pgmx_data(pgmx_path)
        except Exception as e:
            errors.append(f"Ошибка чтения PGMX: {str(e)}")
            pgmx_parts = []
        
        try:
            csv_parts = self.parse_csv(csv_path)
        except Exception as e:
            errors.append(f"Ошибка чтения CSV: {str(e)}")
            csv_parts = []
        
        # Создаем словари для быстрого поиска
        pgmx_dict = {}
        for part in pgmx_parts:
            key = self._create_part_key(part)
            if key not in pgmx_dict:
                pgmx_dict[key] = []
            pgmx_dict[key].append(part)
        
        csv_matched = set()
        matched_count = 0
        
        for csv_part in csv_parts:
            key = self._create_part_key(csv_part)
            found_match = False
            
            if key in pgmx_dict:
                for pgmx_part in pgmx_dict[key]:
                    if self._parts_match(csv_part, pgmx_part, tolerance):
                        matched_count += 1
                        csv_matched.add(id(csv_part))
                        found_match = True
                        break
            
            if not found_match:
                mismatched.append({
                    'csv_part': csv_part,
                    'reason': 'Не найдено соответствие в PGMX'
                })
        
        # Находим детали из PGMX, отсутствующие в CSV
        for pgmx_part in pgmx_parts:
            key = self._create_part_key(pgmx_part)
            found_in_csv = False
            
            for csv_part in csv_parts:
                if self._create_part_key(csv_part) == key and self._parts_match(csv_part, pgmx_part, tolerance):
                    found_in_csv = True
                    break
            
            if not found_in_csv:
                missing_in_pgmx.append(pgmx_part)
        
        # Находим детали из CSV, отсутствующие в PGMX
        for csv_part in csv_parts:
            if id(csv_part) not in csv_matched:
                missing_in_csv.append(csv_part)
        
        is_valid = len(errors) == 0 and len(mismatched) == 0 and len(missing_in_csv) == 0 and len(missing_in_pgmx) == 0
        
        result = ValidationResult(
            is_valid=is_valid,
            pgmx_parts_count=len(pgmx_parts),
            csv_parts_count=len(csv_parts),
            matched_parts=matched_count,
            mismatched_parts=mismatched,
            missing_in_csv=missing_in_csv,
            missing_in_pgmx=missing_in_pgmx,
            errors=errors
        )
        
        logger.info(f"Валидация завершена: PGMX={len(pgmx_parts)}, CSV={len(csv_parts)}, совпадений={matched_count}, ошибок={len(errors)}")
        
        return result
    
    def _create_part_key(self, part: PartInfo) -> str:
        """Создает уникальный ключ для детали на основе имени и размеров."""
        # Округляем размеры для сравнения
        return f"{part.name.lower()}_{round(part.length, 1)}_{round(part.width, 1)}_{round(part.thickness, 1)}"
    
    def _parts_match(self, part1: PartInfo, part2: PartInfo, tolerance: float) -> bool:
        """Проверяет соответствие двух деталей с учетом погрешности."""
        if part1.name.lower() != part2.name.lower():
            return False
        
        return (abs(part1.length - part2.length) <= tolerance and
                abs(part1.width - part2.width) <= tolerance and
                abs(part1.thickness - part2.thickness) <= tolerance)
    
    def generate_report(self, result: ValidationResult, output_path: str) -> None:
        """
        Генерирует текстовый отчет о результатах валидации.
        
        Args:
            result: Результат валидации.
            output_path: Путь для сохранения отчета.
        """
        report_lines = [
            "=" * 60,
            "ОТЧЕТ О ВАЛИДАЦИИ CSV vs PGMX",
            "=" * 60,
            "",
            f"Статус: {'УСПЕШНО' if result.is_valid else 'ОШИБКИ'}",
            "",
            "СТАТИСТИКА:",
            f"  Деталей в PGMX: {result.pgmx_parts_count}",
            f"  Деталей в CSV: {result.csv_parts_count}",
            f"  Совпадений: {result.matched_parts}",
            f"  Несовпадений: {len(result.mismatched_parts)}",
            f"  Отсутствует в CSV: {len(result.missing_in_csv)}",
            f"  Отсутствует в PGMX: {len(result.missing_in_pgmx)}",
            ""
        ]
        
        if result.errors:
            report_lines.append("ОШИБКИ:")
            for error in result.errors:
                report_lines.append(f"  ❌ {error}")
            report_lines.append("")
        
        if result.mismatched_parts:
            report_lines.append("НЕСОВПАДЕНИЯ:")
            for item in result.mismatched_parts[:10]:  # Показываем первые 10
                part = item['csv_part']
                report_lines.append(f"  ⚠️  {part.name}: {part.length}x{part.width}x{part.thickness}")
            if len(result.mismatched_parts) > 10:
                report_lines.append(f"  ... и еще {len(result.mismatched_parts) - 10}")
            report_lines.append("")
        
        if result.missing_in_csv:
            report_lines.append("ОТСУТСТВУЮТ В CSV:")
            for part in result.missing_in_csv[:10]:
                report_lines.append(f"  ❌ {part.name}: {part.length}x{part.width}x{part.thickness}")
            if len(result.missing_in_csv) > 10:
                report_lines.append(f"  ... и еще {len(result.missing_in_csv) - 10}")
            report_lines.append("")
        
        if result.missing_in_pgmx:
            report_lines.append("ОТСУТСТВУЮТ В PGMX:")
            for part in result.missing_in_pgmx[:10]:
                report_lines.append(f"  ❌ {part.name}: {part.length}x{part.width}x{part.thickness}")
            if len(result.missing_in_pgmx) > 10:
                report_lines.append(f"  ... и еще {len(result.missing_in_pgmx) - 10}")
            report_lines.append("")
        
        report_lines.append("=" * 60)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report_lines))
        
        logger.info(f"Отчет сохранен: {output_path}")
