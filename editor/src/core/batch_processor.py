"""
Модуль пакетной обработки файлов (Batch Processor).
Реализует всю бизнес-логику для:
- Сканирования папки и сравнения CSV/PGMX
- Исправления .SCX файлов
- Исправления .PGMX файлов
- Отката изменений
"""
import os
import re
import shutil
import csv
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from datetime import datetime
import logging
import zipfile
import xml.etree.ElementTree as ET

from .encoding_detector import detect_encoding
from .tool_db import global_tool_db

logger = logging.getLogger(__name__)

class BatchProcessor:
    """Класс для пакетной обработки файлов проекта."""
    
    def __init__(self):
        self.folder_path: Optional[Path] = None
        self.scx_files: List[Path] = []
        self.pgmx_files: List[Path] = []
        self.csv_files: List[Path] = []
        self.log_messages: List[str] = []
        self.csv_key_to_names: Dict[str, List[str]] = {}  # Для хранения соответствий ключей CSV
        
    def log(self, message: str):
        """Добавляет сообщение в лог."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        full_msg = f"[{timestamp}] {message}"
        self.log_messages.append(full_msg)
        logger.info(message)

    def scan_folder(self, folder_path: str) -> Dict:
        """
        Сканирует папку на наличие файлов .SCX, .PGMX, .CSV.
        Сравнивает количество записей в CSV с количеством PGMX файлов.
        
        Returns:
            Dict со статистикой и списком проблем.
        """
        self.folder_path = Path(folder_path)
        self.scx_files = []
        self.pgmx_files = []
        self.csv_files = []
        self.log_messages.clear()
        
        self.log(f"Начало сканирования папки: {folder_path}")
        
        # Рекурсивный поиск файлов
        for ext in ['*.scx', '*.SCX']:
            self.scx_files.extend(self.folder_path.rglob(ext))
            
        for ext in ['*.pgmx', '*.PGMX']:
            self.pgmx_files.extend(self.folder_path.rglob(ext))
            
        for ext in ['*.csv', '*.CSV']:
            self.csv_files.extend(self.folder_path.rglob(ext))
            
        self.log(f"Найдено файлов: SCX={len(self.scx_files)}, PGMX={len(self.pgmx_files)}, CSV={len(self.csv_files)}")
        
        # Анализ CSV файлов
        csv_total_parts = 0
        csv_part_names = set()
        
        for csv_file in self.csv_files:
            try:
                # Пытаемся определить кодировку
                encoding = detect_encoding(csv_file)
                with open(csv_file, 'r', encoding=encoding) as f:
                    reader = csv.DictReader(f, delimiter=';') # Обычно разделитель ;
                    count = 0
                    for row in reader:
                        count += 1
                        # Ищем имя детали (обычно в колонке Name или PartName)
                        name = row.get('Name') or row.get('PartName') or row.get('Имя')
                        if name:
                            csv_part_names.add(name)
                    csv_total_parts += count
                    self.log(f"CSV {csv_file.name}: {count} записей")
            except Exception as e:
                self.log(f"Ошибка чтения CSV {csv_file.name}: {e}")
                
        # Сравнение с PGMX
        pgmx_names = {f.stem for f in self.pgmx_files}
        missing_pgmx = []
        oborot_issues = []
        
        for name in csv_part_names:
            # Проверка на отсутствие файла
            if name not in pgmx_names:
                # Проверяем, не является ли это оборотом (OBOROT)
                # Логика: если есть имя без OBOROT, но нет с OBOROT, или наоборот
                base_name = name.replace("OBOROT", "").replace("ОБОРОТ", "").strip("_ -")
                
                has_oborot_variant = any(
                    "OBOROT" in n or "ОБОРОТ" in n 
                    for n in pgmx_names 
                    if base_name in n
                )
                
                if has_oborot_variant:
                    oborot_issues.append(name)
                else:
                    missing_pgmx.append(name)
                    
        self.log(f"Всего деталей в CSV: {csv_total_parts}")
        self.log(f"Уникальных имен в CSV: {len(csv_part_names)}")
        self.log(f"Файлов PGMX найдено: {len(pgmx_names)}")
        
        if missing_pgmx:
            self.log(f"⚠️ Отсутствуют PGMX файлы для {len(missing_pgmx)} деталей из CSV")
            for name in missing_pgmx[:10]: # Показываем первые 10
                self.log(f"   - {name}")
            if len(missing_pgmx) > 10:
                self.log(f"   ... и еще {len(missing_pgmx) - 10}")
                
        if oborot_issues:
            self.log(f"⚠️ Несоответствие OBOROT для {len(oborot_issues)} деталей")
            for name in oborot_issues[:10]:
                self.log(f"   - {name}")
                
        return {
            'scx_count': len(self.scx_files),
            'pgmx_count': len(self.pgmx_files),
            'csv_count': len(self.csv_files),
            'csv_parts_total': csv_total_parts,
            'missing_pgmx': missing_pgmx,
            'oborot_issues': oborot_issues
        }

    def fix_scx_batch(self) -> Dict:
        """
        Исправляет все найденные .SCX файлы согласно правилам:
        1. Отверстия Ø2.5мм с глубиной >5мм -> глубина=5мм
        2. Панели >1200×1200мм (поиск и логирование)
        3. Type="4" с десятичными дробями -> замена точек на запятые
        4. Type="4" Face="0" -> попытка взять Face из метки отверстия 12.222
        """
        if not self.scx_files:
            self.log("Нет файлов .SCX для обработки")
            return {'processed': 0, 'errors': 0}
            
        self.log("=== Начало исправления файлов .SCX (NANXING) ===")
        stats = {'processed': 0, 'holes_fixed': 0, 'panels_found': 0, 'dots_replaced': 0, 'face_fixed': 0, 'z_recalculated': 0, 'errors': 0}
        
        for file_path in self.scx_files:
            try:
                self.log(f"Обработка файла: {file_path.name}")
                encoding = detect_encoding(file_path)
                
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()
                    
                original_content = content
                file_stats = {
                    'holes_fixed': 0,
                    'panels_found': 0,
                    'dots_replaced': 0,
                    'face_fixed': 0,
                    'z_recalculated': 0
                }
                
                # Парсим XML
                # Для SCX часто нужно вручную парсить, так как там могут быть проблемы с форматом
                # Используем regex для надежного поиска
                
                # 1. Поиск панелей > 1200x1200 (ищем в свойствах панели Length/Width или X/Y размеры)
                # Предполагаем, что размеры панели могут быть в атрибутах корня или в специфичных тегах
                # Это упрощенная эвристика, может потребоваться уточнение структуры SCX
                panel_pattern = r'(Length|Width|L|W)="([\d,.]+)"'
                matches = re.findall(panel_pattern, content)
                dims = {}
                for attr, val in matches:
                    try:
                        v = float(val.replace(',', '.'))
                        dims[attr] = v
                    except: pass
                
                length = dims.get('Length', dims.get('L', 0))
                width = dims.get('Width', dims.get('W', 0))
                
                if length > 1200 and width > 1200:
                    file_stats['panels_found'] += 1
                    self.log(f"   ⚠️ Найдена панель >1200x1200: {length}x{width}")
                    stats['panels_found'] += 1
                
                # 2. Исправление отверстий Ø2.5мм с глубиной >5мм
                # Ищем элементы с Diameter="2.5" или Diameter="2,5"
                # Pattern: <Operation ... Diameter="2.5" ... Depth="..." ... />
                hole_pattern = r'(<[^>]*Diameter=["\']?2[,\.]5["\']?[^>]*Depth=["\']?)([\d,.]+)(["\'][^>]*>)'
                
                def replace_hole_depth(match):
                    prefix = match.group(1)
                    depth_str = match.group(2)
                    suffix = match.group(3)
                    try:
                        depth = float(depth_str.replace(',', '.'))
                        if depth > 5.0:
                            file_stats['holes_fixed'] += 1
                            self.log(f"   🔧 Отверстие Ø2.5: глубина изменена {depth} -> 5.0")
                            return f"{prefix}5.0{suffix}"
                    except: pass
                    return match.group(0)
                    
                content = re.sub(hole_pattern, replace_hole_depth, content)
                stats['holes_fixed'] += file_stats['holes_fixed']
                
                # 3. Type="4" с десятичными дробями -> замена точек на запятые ТОЛЬКО в атрибуте Width
                # Ищем элементы Type="4" и меняем точки на запятые только в атрибуте Width
                type4_pattern = r'(<[^>]*Type=["\']?4["\']?[^>]*>)'
                
                def fix_type4_width(match):
                    tag_content = match.group(1)
                    # Меняем точки на запятые только в атрибуте Width
                    # Pattern: Width="123.45" -> Width="123,45"
                    fixed_tag = re.sub(r'(Width=["\'])([\d]+)\.([\d]+)(["\'])', r'\1\2,\3\4', tag_content)
                    if fixed_tag != tag_content:
                        file_stats['dots_replaced'] += 1
                        self.log(f"   🔢 Type=4: заменены точки на запятые в атрибуте Width")
                    return fixed_tag
                    
                content = re.sub(type4_pattern, fix_type4_width, content)
                stats['dots_replaced'] += file_stats['dots_replaced']
                
                # 3b. Type="4" -> пересчёт Z = Thickness - Z, EndZ = Thickness - EndZ
                # Извлекаем Thickness из корня документа или Panel элемента
                thickness_match = re.search(r'Thickness=["\']?([\d.,]+)["\']?', content)
                thickness = 0.0
                if thickness_match:
                    try:
                        thickness = float(thickness_match.group(1).replace(',', '.'))
                    except: pass
                
                # Если не нашли в корне, ищем в элементе Panel
                if thickness == 0.0:
                    panel_thickness_match = re.search(r'<Panel[^>]*Thickness=["\']?([\d.,]+)["\']?', content)
                    if panel_thickness_match:
                        try:
                            thickness = float(panel_thickness_match.group(1).replace(',', '.'))
                        except: pass
                
                if thickness > 0:
                    def recalc_type4_z(match):
                        tag_content = match.group(1)
                        modified = False
                        
                        # Извлекаем текущие Z и EndZ
                        z_match = re.search(r'Z=["\']?([\d.,]+)["\']?', tag_content)
                        endz_match = re.search(r'EndZ=["\']?([\d.,]+)["\']?', tag_content)
                        
                        if z_match:
                            try:
                                z_old = float(z_match.group(1).replace(',', '.'))
                                z_new = thickness - z_old
                                # Заменяем Z="..." на Z="новый"
                                tag_content = re.sub(
                                    r'Z=["\'][\d.,]+["\']',
                                    f'Z="{round(z_new, 3)}"',
                                    tag_content
                                )
                                modified = True
                            except: pass
                        
                        if endz_match:
                            try:
                                endz_old = float(endz_match.group(1).replace(',', '.'))
                                endz_new = thickness - endz_old
                                # Заменяем EndZ="..." на EndZ="новый"
                                tag_content = re.sub(
                                    r'EndZ=["\'][\d.,]+["\']',
                                    f'EndZ="{round(endz_new, 3)}"',
                                    tag_content
                                )
                                modified = True
                            except: pass
                        
                        if modified:
                            file_stats['z_recalculated'] += 1
                            self.log(f"   🔄 Type=4: пересчитан Z и EndZ (Thickness={thickness})")
                        
                        return tag_content
                    
                    content = re.sub(type4_pattern, recalc_type4_z, content)
                    stats['z_recalculated'] += file_stats['z_recalculated']
                
                # 4. Type="4" Face="0" -> попытка взять Face из метки отверстия 12.222
                # Сначала найдем все метки с Diameter="12.222" и их Face
                marker_faces = []
                marker_pattern = r'<[^>]*Diameter=["\']?12[,\.]222["\']?[^>]*Face=["\']([^"\']+)["\'][^>]*>'
                for m in re.finditer(marker_pattern, content):
                    face_val = m.group(1)
                    if face_val and face_val != "0":
                        marker_faces.append(face_val)
                
                if marker_faces:
                    # Берем первое найденное значение Face из меток (упрощенная логика)
                    target_face = marker_faces[0]
                    self.log(f"   🎯 Найдена метка Ø12.222 с Face={target_face}")
                    
                    # Теперь ищем Type="4" с Face="0" и меняем Face
                    face0_pattern = r'(<[^>]*Type=["\']?4["\']?[^>]*)Face=["\']0["\']([^>]*>)'
                    new_content = re.sub(face0_pattern, rf'\1Face="{target_face}"\2', content)
                    
                    if new_content != content:
                        count = content.count('Face="0"') - new_content.count('Face="0"')
                        file_stats['face_fixed'] += count
                        self.log(f"   🔧 Type=4 Face=0 исправлено: {count} раз (взят Face={target_face} из метки)")
                        content = new_content
                        
                stats['face_fixed'] += file_stats['face_fixed']
                
                # Сохранение если были изменения
                if content != original_content:
                    with open(file_path, 'w', encoding=encoding) as f:
                        f.write(content)
                    stats['processed'] += 1
                    self.log(f"   ✅ Файл {file_path.name} сохранен с изменениями")
                else:
                    self.log(f"   - Изменений не требуется")
                    
            except Exception as e:
                self.log(f"   ❌ Ошибка обработки {file_path.name}: {e}")
                stats['errors'] += 1
                
        self.log(f"=== Завершено. Обработано файлов: {stats['processed']} ===")
        return stats

    def fix_pgmx_batch(self) -> Dict:
        """
        Исправляет все .PGMX файлы:
        - Ищет сверления с диаметром ~2.22мм
        - Заменяет инструмент на E007 (из базы инструментов)
        """
        if not global_tool_db.is_loaded:
            self.log("❌ База инструментов не загружена! Нажмите 'База инструментов' сначала.")
            return {'processed': 0, 'errors': 0}
            
        if not self.pgmx_files:
            self.log("Нет файлов .PGMX для обработки")
            return {'processed': 0, 'errors': 0}
            
        self.log("=== Начало исправления файлов .PGMX (SCM) ===")
        stats = {'processed': 0, 'tools_replaced': 0, 'errors': 0}
        
        # Получаем данные о фрезе E007
        replacement_tool = global_tool_db.get_replacement_tool("E007")
        if not replacement_tool:
            self.log("❌ Инструмент E007 не найден в базе!")
            return stats
            
        self.log(f"Инструмент замены: ID={replacement_tool['id']}, Name={replacement_tool['name']}")
        
        for file_path in self.pgmx_files:
            try:
                self.log(f"Обработка файла: {file_path.name}")
                
                # PGMX это ZIP архив
                # Создаем временную копию для работы
                temp_zip = file_path.with_suffix('.tmp.zip')
                shutil.copy2(file_path, temp_zip)
                
                modified = False
                tool_count = 0
                
                with zipfile.ZipFile(temp_zip, 'r') as zin:
                    # Читаем содержимое
                    xml_data = {}
                    for name in zin.namelist():
                        if name.endswith('.xml'):
                            xml_data[name] = zin.read(name)
                            
                # Обрабатываем каждый XML внутри архива
                new_xml_data = {}
                for name, data in xml_data.items():
                    try:
                        encoding = detect_encoding(data) if isinstance(data, bytes) else 'utf-8'
                        content = data.decode(encoding) if isinstance(data, bytes) else data
                        
                        # Ищем операции сверления с диаметром ~2.22 и заменяем ToolId на E007
                        # Pattern для поиска тега с Diameter и ToolId
                        tag_pattern = r'<[^>]*Diameter=["\']?([2][.,]1[5-9]|[2][.,]2[0-9]|[2][.,]3[0-9])["\']?[^>]*ToolId=["\'][^"\']+["\'][^>]*>'
                        
                        def fix_tag(full_match):
                            nonlocal tool_count, modified
                            # Извлекаем диаметр из匹配的字符串
                            dia_match = re.search(r'Diameter=["\']?([2][.,]1[5-9]|[2][.,]2[0-9]|[2][.,]3[0-9])', full_match)
                            if not dia_match:
                                return full_match
                            
                            dia_str = dia_match.group(1)
                            try:
                                dia = float(dia_str.replace(',', '.'))
                            except:
                                return full_match
                                
                            if 2.15 <= dia <= 2.30:
                                # Заменяем ToolId в этом теге
                                new_tag = re.sub(r'ToolId=["\'][^"\']+["\']', f'ToolId="{replacement_tool["id"]}"', full_match)
                                if new_tag != full_match:
                                    tool_count += 1
                                    modified = True
                                    self.log(f"   🔧 Найдено сверло Ø{dia:.2f}, замена ToolId на {replacement_tool['id']}")
                                return new_tag
                            return full_match
                        
                        content = re.sub(tag_pattern, fix_tag, content)
                        new_xml_data[name] = content.encode(encoding)
                        
                    except Exception as e:
                        self.log(f"   Ошибка парсинга XML {name}: {e}")
                        
                # Если были изменения, сохраняем новый ZIP
                if modified:
                    with zipfile.ZipFile(file_path, 'w') as zout:
                        for name, data in new_xml_data.items():
                            zout.writestr(name, data)
                    stats['processed'] += 1
                    stats['tools_replaced'] += tool_count
                    self.log(f"   ✅ Файл сохранен. Заменено инструментов: {tool_count}")
                else:
                    self.log(f"   - Изменений не требуется")
                    
                # Удаляем временный файл если остался
                if temp_zip.exists():
                    temp_zip.unlink()
                    
            except Exception as e:
                self.log(f"   ❌ Ошибка обработки {file_path.name}: {e}")
                stats['errors'] += 1
                if temp_zip.exists():
                    temp_zip.unlink()
                    
        self.log(f"=== Завершено. Обработано файлов: {stats['processed']}, заменено инструментов: {stats['tools_replaced']} ===")
        return stats

    def revert_dots(self) -> Dict:
        """
        Возвращает точки вместо запятых в файлах .SCX, которые были изменены ранее.
        Ищет Type="4" с запятыми в числах и меняет на точки.
        """
        if not self.scx_files:
            self.log("Нет файлов .SCX для обработки")
            return {'processed': 0, 'errors': 0}
            
        self.log("=== Возврат точек в файлах .SCX ===")
        stats = {'processed': 0, 'reverted': 0, 'errors': 0}
        
        for file_path in self.scx_files:
            try:
                self.log(f"Обработка файла: {file_path.name}")
                encoding = detect_encoding(file_path)
                
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()
                    
                original_content = content
                count = 0
                
                # Ищем Type="4" и меняем запятые обратно на точки в числах
                type4_pattern = r'(<[^>]*Type=["\']?4["\']?[^>]*>)'
                
                def revert_numbers(match):
                    nonlocal count
                    tag_content = match.group(1)
                    # Меняем запятые между цифрами на точки
                    reverted_tag = re.sub(r'(["\'])([\d]+),([\d]+)(["\'])', r'\1\2.\3\4', tag_content)
                    if reverted_tag != tag_content:
                        count += 1
                        self.log(f"   ↩️ Возвращены точки в Type=4")
                    return reverted_tag
                    
                content = re.sub(type4_pattern, revert_numbers, content)
                
                if content != original_content:
                    with open(file_path, 'w', encoding=encoding) as f:
                        f.write(content)
                    stats['processed'] += 1
                    stats['reverted'] += count
                    self.log(f"   ✅ Файл сохранен. Возвращено значений: {count}")
                else:
                    self.log(f"   - Нет запятых для возврата")
                    
            except Exception as e:
                self.log(f"   ❌ Ошибка обработки {file_path.name}: {e}")
                stats['errors'] += 1
                
        self.log(f"=== Завершено. Обработано файлов: {stats['processed']} ===")
        return stats

    def compare_pgmx_csv(self) -> Dict:
        """
        Сравнивает файлы .PGMX с записями в .CSV по логике ZPT-TCHK.py:
        - CSV: ключ = первая колонка (имя детали) с удалением первых 18 символов
        - PGMX: ключ = полное имя файла без расширения
        - Использует симметричную разность для сравнения
        - Сначала выводит OBOROT, затем !ФАЙЛА НЕТ
        
        Returns:
            Dict со статистикой сравнения.
        """
        if not self.folder_path:
            self.log("❌ Папка не выбрана! Сначала выберите папку.")
            return {'matches': 0, 'missing_in_csv': [], 'missing_in_pgmx': [], 'oborot_keys': []}
            
        if not self.pgmx_files or not self.csv_files:
            self.log("⚠️ Нет файлов для сравнения (нужны и .PGMX, и .CSV)")
            return {'matches': 0, 'missing_in_csv': [], 'missing_in_pgmx': [], 'oborot_keys': []}
        
        self.log("=== Сравнение PGMX с CSV (логика ZPT-TCHK.py) ===")
        
        # Извлекаем ключи из CSV: первая колонка, удаляем первые 18 символов
        csv_keys = set()
        for csv_file in self.csv_files:
            try:
                encoding = detect_encoding(csv_file)
                with open(csv_file, 'r', encoding=encoding) as f:
                    content = f.read()
                    # Убираем последний символ (как в оригинале)
                    if content:
                        content = content[:-1]
                    lines = content.split("\n")
                    for line in lines:
                        parts = line.split(";")
                        if len(parts) >= 1:
                            key = str(parts[0])
                            # Удаляем первые 18 символов (как в оригинале ZPT-TCHK.py)
                            if len(key) > 18:
                                key = key[18:]
                            csv_keys.add(key)
                            self.log(f"   CSV: {key}")
            except Exception as e:
                self.log(f"   ❌ Ошибка чтения CSV {csv_file.name}: {e}")
        
        # Извлекаем ключи из PGMX: полное имя файла без расширения
        pgmx_keys = set()
        for pgmx_file in self.pgmx_files:
            key = pgmx_file.stem  # Полное имя без расширения, например DSP_25_U963-ST9_1971G1.01.07
            pgmx_keys.add(key)
            self.log(f"   PGMX: {key}")
        
        self.log(f"\n   Найдено CSV ключей: {len(csv_keys)}")
        self.log(f"   Найдено PGMX ключей: {len(pgmx_keys)}")
        
        # Сравниваем списки ключей
        if csv_keys == pgmx_keys:
            self.log("\n✅ Все файлы есть. Оборотов нет!")
            return {'matches': len(csv_keys), 'missing_in_csv': [], 'missing_in_pgmx': [], 'oborot_keys': []}
        
        # Симметричная разность (как в оригинале)
        diff_keys = csv_keys ^ pgmx_keys
        
        # Разделяем на OBOROT и остальные
        oborot_keys = []
        other_keys = []
        for key in diff_keys:
            if 'OBOROT' in key:
                oborot_keys.append(key)
            else:
                other_keys.append(key)
        
        # Сортируем (как в оригинале)
        oborot_keys = sorted(oborot_keys)
        other_keys = sorted(other_keys)
        
        # Вывод результатов (сначала OBOROT, затем !ФАЙЛА НЕТ)
        if oborot_keys:
            self.log(f"\n⚠️ OBOROT файлы ({len(oborot_keys)}):")
            for key in oborot_keys:
                self.log(f"   {key}")
        
        if other_keys:
            self.log(f"\n⚠️ Отсутствующие файлы ({len(other_keys)}):")
            for key in other_keys:
                self.log(f"   !ФАЙЛА НЕТ -- {key}")
        
        return {
            'matches': 0,
            'missing_in_csv': other_keys,
            'missing_in_pgmx': other_keys,
            'oborot_keys': oborot_keys
        }
