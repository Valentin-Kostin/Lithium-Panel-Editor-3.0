"""
Lithium Panel Editor - Улучшенная версия ZPT-TCHK.py
С использованием логики из editor проекта
"""
import sys
import os
import re
import zipfile
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from xml.etree import ElementTree as ET
from dataclasses import dataclass

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTextEdit, QFileDialog, QLabel, QProgressBar,
    QGroupBox, QSplitter, QMessageBox, QScrollArea, QToolBar
)
from PySide6.QtCore import Qt, QThread, Signal, QObject, QSize
from PySide6.QtGui import QFont, QTextCursor, QAction, QIcon


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class ScxIssue:
    """Проблема найденная в SCX файле"""
    file_path: str
    issue_type: str  # 'hole_2_5', 'large_panel', 'type4_decimal', 'type4_face0'
    description: str
    part_name: str = ""
    operation_index: int = -1


@dataclass 
class PgmxIssue:
    """Проблема найденная в PGMX файле"""
    file_path: str
    tool_id: str
    old_diameter: float
    new_tool_code: str = "E007"
    description: str = ""


@dataclass
class CsvPgmxMismatch:
    """Несоответствие между CSV и PGMX файлами"""
    csv_file: str
    pgmx_file: str
    csv_count: int
    pgmx_count: int
    difference: int
    issue_type: str  # 'missing_pgmx', 'count_mismatch', 'oborot'


# ============================================================================
# ENCODING DETECTOR (из editor)
# ============================================================================

class EncodingDetector:
    """Определение кодировки файлов"""
    
    @staticmethod
    def detect_encoding(file_path: str) -> str:
        """Определение кодировки по BOM или анализу содержимого"""
        try:
            with open(file_path, 'rb') as f:
                raw = f.read(4)
                
            # Проверка BOM
            if raw.startswith(b'\xef\xbb\xbf'):
                return 'utf-8-sig'
            elif raw.startswith(b'\xff\xfe'):
                return 'utf-16-le'
            elif raw.startswith(b'\xfe\xff'):
                return 'utf-16-be'
            
            # Попытка декодирования приоритетными кодировками
            encodings = ['utf-8', 'gb18030', 'windows-1251', 'cp1251']
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        f.read(1024)
                    return encoding
                except (UnicodeDecodeError, LookupError):
                    continue
                    
            return 'utf-8'  # fallback
            
        except Exception:
            return 'utf-8'


# ============================================================================
# TOOL LIBRARY PARSER (def.tlgx)
# ============================================================================

class ToolLibraryParser:
    """Парсинг файла def.tlgx для получения информации об инструментах"""
    
    def __init__(self, tlgx_path: str):
        self.tlgx_path = tlgx_path
        self.tools: Dict[str, Dict] = {}
        self._parse()
    
    def _parse(self):
        """Парсинг TLGX файла"""
        if not os.path.exists(self.tlgx_path):
            return
            
        namespaces = {
            'ns': 'http://schemas.datacontract.org/2004/07/ScmGroup.XCam.ToolDataModel.Common',
            'd3p1': 'http://schemas.datacontract.org/2004/07/ScmGroup.XCam.ToolDataModel.Tool'
        }
        
        try:
            tree = ET.parse(self.tlgx_path)
            root = tree.getroot()
            
            # Поиск всех инструментов
            for tool in root.findall('.//d3p1:CuttingTool', namespaces):
                name_elem = tool.find('ns:Name', namespaces)
                desc_elem = tool.find('d3p1:Description', namespaces)
                
                if name_elem is not None:
                    tool_name = name_elem.text or ""
                    
                    # Поиск диаметра
                    diameter_elem = tool.find('d3p1:ToolBody/d3p1:ToolDimension/d3p1:Diameter', namespaces)
                    diameter = float(diameter_elem.text) if diameter_elem is not None and diameter_elem.text else 0.0
                    
                    self.tools[tool_name] = {
                        'name': tool_name,
                        'description': desc_elem.text if desc_elem is not None else "",
                        'diameter': diameter
                    }
                    
        except Exception as e:
            print(f"Ошибка парсинга def.tlgx: {e}")


# ============================================================================
# WORKER THREAD
# ============================================================================

class WorkerThread(QThread):
    """Поток для выполнения тяжёлых операций"""
    progress = Signal(int, str)
    finished = Signal(object)
    error = Signal(str)
    
    def __init__(self, task_func, *args, **kwargs):
        super().__init__()
        self.task_func = task_func
        self.args = args
        self.kwargs = kwargs
    
    def run(self):
        try:
            result = self.task_func(*self.args, **self.kwargs, progress_callback=self._progress)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))
    
    def _progress(self, value: int, message: str):
        self.progress.emit(value, message)


# ============================================================================
# MAIN WINDOW
# ============================================================================

class LithiumPanelEditor(QMainWindow):
    """Главное окно приложения"""
    
    def __init__(self):
        super().__init__()
        
        self.folder_path: Optional[str] = None
        self.scx_files: List[str] = []
        self.pgmx_files: List[str] = []
        self.csv_files: List[str] = []
        
        self.scx_issues: List[ScxIssue] = []
        self.pgmx_issues: List[PgmxIssue] = []
        self.csv_pgmx_mismatches: List[CsvPgmxMismatch] = []
        
        self.tool_library: Optional[ToolLibraryParser] = None
        
        self._init_ui()
        self._load_tool_library()
    
    def _init_ui(self):
        """Инициализация интерфейса"""
        self.setWindowTitle("Lithium Panel Editor v3.0")
        self.setMinimumSize(1000, 700)
        
        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Главный layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Панель инструментов
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setSpacing(5)
        
        # Кнопка выбора папки
        self.btn_select_folder = QPushButton("📁 Выбрать папку")
        self.btn_select_folder.setMinimumHeight(40)
        self.btn_select_folder.clicked.connect(self._on_select_folder)
        toolbar_layout.addWidget(self.btn_select_folder)
        
        # Разделитель
        toolbar_layout.addSpacing(20)
        
        # Кнопка исправления SCX
        self.btn_fix_scx = QPushButton("🔧 Исправить .SCX (NANXING)")
        self.btn_fix_scx.setMinimumHeight(40)
        self.btn_fix_scx.clicked.connect(self._on_fix_scx)
        self.btn_fix_scx.setEnabled(False)
        toolbar_layout.addWidget(self.btn_fix_scx)
        
        # Кнопка правки PGMX
        self.btn_edit_pgmx = QPushButton("✏️ Править .PGMX (SCM)")
        self.btn_edit_pgmx.setMinimumHeight(40)
        self.btn_edit_pgmx.clicked.connect(self._on_edit_pgmx)
        self.btn_edit_pgmx.setEnabled(False)
        toolbar_layout.addWidget(self.btn_edit_pgmx)
        
        # Кнопка вернуть точки
        self.btn_restore_dots = QPushButton("🔄 Вернуть точки")
        self.btn_restore_dots.setMinimumHeight(40)
        self.btn_restore_dots.clicked.connect(self._on_restore_dots)
        self.btn_restore_dots.setEnabled(False)
        toolbar_layout.addWidget(self.btn_restore_dots)
        
        # Разделитель
        toolbar_layout.addStretch()
        
        # Индикатор прогресса
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumHeight(25)
        toolbar_layout.addWidget(self.progress_bar, 1)
        
        main_layout.addLayout(toolbar_layout)
        
        # Текстовое поле для вывода информации
        log_group = QGroupBox("📋 Информация о файлах и результатах обработки")
        log_layout = QVBoxLayout(log_group)
        
        self.text_log = QTextEdit()
        self.text_log.setReadOnly(True)
        self.text_log.setFont(QFont("Consolas", 10))
        self.text_log.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
                border-radius: 5px;
                padding: 5px;
            }
        """)
        log_layout.addWidget(self.text_log)
        
        main_layout.addWidget(log_group, 1)
        
        # Строка состояния
        self.status_label = QLabel("Готов к работе")
        self.status_label.setStyleSheet("color: #888; padding: 5px;")
        main_layout.addWidget(self.status_label)
    
    def _load_tool_library(self):
        """Загрузка библиотеки инструментов"""
        tlgx_path = Path(__file__).parent / "def.tlgx"
        if tlgx_path.exists():
            self.tool_library = ToolLibraryParser(str(tlgx_path))
            self._log(f"✅ Библиотека инструментов загружена: {len(self.tool_library.tools)} инструментов")
        else:
            self._log("⚠️ Файл def.tlgx не найден, функция правки PGMX будет ограничена")
    
    def _log(self, message: str):
        """Вывод сообщения в лог"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.text_log.append(f"[{timestamp}] {message}")
        scrollbar = self.text_log.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        QApplication.processEvents()
    
    def _on_select_folder(self):
        """Обработчик выбора папки"""
        folder = QFileDialog.getExistingDirectory(
            self, "Выберите папку с файлами", "",
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )
        
        if folder:
            self.folder_path = folder
            self._scan_folder(folder)
    
    def _scan_folder(self, folder_path: str):
        """Сканирование папки на наличие файлов"""
        self._log(f"\n🔍 Сканирование папки: {folder_path}")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        folder = Path(folder_path)
        
        # Поиск файлов
        self.scx_files = list(map(str, folder.rglob("*.scx")))
        self.pgmx_files = list(map(str, folder.rglob("*.pgmx")))
        self.csv_files = list(map(str, folder.rglob("*.csv")))
        
        self._log(f"Найдено файлов:")
        self._log(f"  • .SCX: {len(self.scx_files)}")
        self._log(f"  • .PGMX: {len(self.pgmx_files)}")
        self._log(f"  • .CSV: {len(self.csv_files)}")
        
        # Подсчёт записей в CSV
        total_csv_records = 0
        for csv_file in self.csv_files:
            try:
                with open(csv_file, 'r', encoding='utf-8') as f:
                    lines = sum(1 for _ in f) - 1  # минус заголовок
                    total_csv_records += lines
            except:
                pass
        
        self._log(f"  • Записей в CSV: {total_csv_records}")
        
        # Сравнение CSV и PGMX
        self._compare_csv_pgmx(total_csv_records)
        
        # Активация кнопок
        self.btn_fix_scx.setEnabled(len(self.scx_files) > 0)
        self.btn_edit_pgmx.setEnabled(len(self.pgmx_files) > 0)
        
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"Папка: {folder_path} | SCX: {len(self.scx_files)} | PGMX: {len(self.pgmx_files)} | CSV: {len(self.csv_files)}")
    
    def _compare_csv_pgmx(self, total_csv_records: int):
        """Сравнение количества записей CSV и PGMX"""
        self._log("\n📊 Сверка CSV и PGMX:")
        
        if not self.pgmx_files:
            if self.csv_files:
                self._log("  ⚠️ Найдены CSV файлы но отсутствуют PGMX!")
                for csv_file in self.csv_files:
                    mismatch = CsvPgmxMismatch(
                        csv_file=Path(csv_file).name,
                        pgmx_file="НЕ НАЙДЕН",
                        csv_count=0,
                        pgmx_count=0,
                        difference=0,
                        issue_type='missing_pgmx'
                    )
                    self.csv_pgmx_mismatches.append(mismatch)
                    self._log(f"    ❌ {Path(csv_file).name}: PGMX файл отсутствует")
            return
        
        total_pgmx_operations = 0
        for pgmx_file in self.pgmx_files:
            try:
                # Извлечение XML из ZIP
                with zipfile.ZipFile(pgmx_file, 'r') as zf:
                    xml_filename = [f for f in zf.namelist() if f.endswith('.xml')][0]
                    with zf.open(xml_filename) as xf:
                        xml_content = xf.read()
                        
                # Парсинг XML для подсчёта операций
                root = ET.fromstring(xml_content)
                ns = {'ns': 'http://schemas.datacontract.org/2004/07/ScmGroup.XCam.MachiningDataModel.ProjectModule'}
                operations = root.findall('.//ns:ManufacturingFeature', ns)
                total_pgmx_operations += len(operations)
                
            except Exception as e:
                self._log(f"  ⚠️ Ошибка чтения {Path(pgmx_file).name}: {e}")
        
        self._log(f"  Всего операций в PGMX: {total_pgmx_operations}")
        self._log(f"  Всего записей в CSV: {total_csv_records}")
        
        difference = abs(total_csv_records - total_pgmx_operations)
        if difference > 0:
            self._log(f"  ⚠️ РАЗНОСТЬ: {difference}")
            if total_csv_records > total_pgmx_operations:
                self._log(f"  → Возможно есть OBOROT (обороты) неучтённые в PGMX")
            else:
                self._log(f"  → Возможно в PGMX есть лишние операции")
        else:
            self._log("  ✅ Количество совпадает")
    
    def _on_fix_scx(self):
        """Исправление SCX файлов"""
        if not self.scx_files:
            QMessageBox.warning(self, "Предупреждение", "Нет файлов .SCX для обработки")
            return
        
        self._log("\n🔧 НАЧАЛО ИСПРАВЛЕНИЯ .SCX ФАЙЛОВ")
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(self.scx_files))
        
        fixed_files = []
        issues_found = []
        
        for i, scx_file in enumerate(self.scx_files):
            self.progress_bar.setValue(i + 1)
            self._log(f"\nОбработка: {Path(scx_file).name}")
            
            try:
                # Определение кодировки
                encoding = EncodingDetector.detect_encoding(scx_file)
                self._log(f"  Кодировка: {encoding}")
                
                # Чтение файла
                with open(scx_file, 'r', encoding=encoding) as f:
                    content = f.read()
                
                original_content = content
                file_issues = []
                
                # 1. Поиск отверстий Ø2.5мм с глубиной >5мм
                pattern_hole = r'<Machining[^>]*Type="2"[^>]*Diameter="2\.5"[^>]*Depth="([5-9]|[1-9]\d+)"'
                matches = re.finditer(pattern_hole, content)
                hole_count = 0
                for match in matches:
                    hole_count += 1
                    depth = match.group(1)
                    file_issues.append(f"    ⚠️ Отверстие Ø2.5мм с глубиной {depth}мм (>5мм)")
                
                if hole_count > 0:
                    self._log(f"  Найдено отверстий Ø2.5мм с глубиной >5мм: {hole_count}")
                    for issue in file_issues[-hole_count:]:
                        self._log(issue)
                
                # 2. Поиск панелей >1200×1200мм
                pattern_panel = r'<Panel[^>]*Length="([\d.]+)"[^>]*Width="([\d.]+)"'
                match = re.search(pattern_panel, content)
                if match:
                    length = float(match.group(1))
                    width = float(match.group(2))
                    if length > 1200 and width > 1200:
                        self._log(f"  ⚠️ Панель >1200×1200мм: {length}×{width}мм")
                        file_issues.append(f"    ⚠️ Панель >1200×1200мм: {length}×{width}мм")
                
                # 3. Type="4" с десятичными дробями (точки → запятые)
                type4_fixed = 0
                pattern_type4 = r'(Type="4"[^>]*)(X|Y|Z|EndZ|Width)="([\d]+\.[\d]+)"'
                
                def replace_dot_with_comma(match):
                    nonlocal type4_fixed
                    type4_fixed += 1
                    prefix = match.group(1)
                    attr = match.group(2)
                    value = match.group(3).replace('.', ',')
                    return f'{prefix}{attr}="{value}"'
                
                content = re.sub(pattern_type4, replace_dot_with_comma, content)
                
                if type4_fixed > 0:
                    self._log(f"  Исправлено Type=\"4\" с точками на запятые: {type4_fixed}")
                    file_issues.append(f"    ✅ Type=\"4\" исправлено: {type4_fixed}")
                
                # 4. Type="4" Face="0" - поиск меток 12.222
                face0_count = 0
                pattern_face0 = r'Type="4"[^>]*Face="0"'
                matches = re.finditer(pattern_face0, content)
                for match in matches:
                    face0_count += 1
                
                if face0_count > 0:
                    self._log(f"  Найдено Type=\"4\" Face=\"0\": {face0_count}")
                    file_issues.append(f"    ⚠️ Type=\"4\" Face=\"0\" найдено: {face0_count} (требуется ручная проверка)")
                
                # Сохранение если были изменения
                if content != original_content:
                    with open(scx_file, 'w', encoding=encoding) as f:
                        f.write(content)
                    fixed_files.append(scx_file)
                    self._log(f"  ✅ Файл сохранён с изменениями")
                else:
                    self._log(f"  ℹ️ Изменений не требуется")
                
                if file_issues:
                    issues_found.extend([(scx_file, file_issues)])
                    
            except Exception as e:
                self._log(f"  ❌ Ошибка: {e}")
        
        self.progress_bar.setVisible(False)
        
        # Итоговый отчёт
        self._log("\n" + "="*60)
        self._log("📊 ИТОГОВЫЙ ОТЧЁТ ПО ИСПРАВЛЕНИЮ .SCX")
        self._log("="*60)
        
        if fixed_files:
            self._log(f"\n✅ Исправлено файлов: {len(fixed_files)}")
            for f in fixed_files:
                self._log(f"  • {Path(f).name}")
        else:
            self._log("\nℹ️ Файлы не требовали исправлений")
        
        if issues_found:
            self._log(f"\n⚠️ Найденные проблемы:")
            for file_path, issues in issues_found:
                self._log(f"\n  {Path(file_path).name}:")
                for issue in issues:
                    self._log(f"  {issue}")
        
        self.btn_restore_dots.setEnabled(len(fixed_files) > 0)
        self.status_label.setText(f"Исправлено SCX файлов: {len(fixed_files)}")
    
    def _on_edit_pgmx(self):
        """Правка PGMX файлов - замена сверл диаметром ~2.22мм на фрезу E007"""
        if not self.pgmx_files:
            QMessageBox.warning(self, "Предупреждение", "Нет файлов .PGMX для обработки")
            return
        
        if not self.tool_library:
            QMessageBox.warning(self, "Предупреждение", "Библиотека инструментов не загружена")
            return
        
        self._log("\n✏️ НАЧАЛО ПРАВКИ .PGMX ФАЙЛОВ")
        self._log("Поиск сверл диаметром 2.22мм для замены на фрезу E007")
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(self.pgmx_files))
        
        fixed_files = []
        
        for i, pgmx_file in enumerate(self.pgmx_files):
            self.progress_bar.setValue(i + 1)
            self._log(f"\nОбработка: {Path(pgmx_file).name}")
            
            try:
                # Распаковка ZIP
                temp_dir = Path(pgmx_file).parent / f"temp_{Path(pgmx_file).stem}"
                temp_dir.mkdir(exist_ok=True)
                
                with zipfile.ZipFile(pgmx_file, 'r') as zf:
                    zf.extractall(temp_dir)
                    xml_files = [f for f in zf.namelist() if f.endswith('.xml')]
                
                if not xml_files:
                    self._log("  ⚠️ XML файл не найден в архиве")
                    shutil.rmtree(temp_dir)
                    continue
                
                xml_file = temp_dir / xml_files[0]
                
                # Чтение и парсинг XML
                tree = ET.parse(xml_file)
                root = tree.getroot()
                
                namespaces = {
                    'ns': 'http://schemas.datacontract.org/2004/07/ScmGroup.XCam.MachiningDataModel.ProjectModule',
                    'i': 'http://www.w3.org/2001/XMLSchema-instance',
                    'a': 'http://schemas.datacontract.org/2004/07/ScmGroup.XCam.MachiningDataModel.Utility',
                    'drilling': 'http://schemas.datacontract.org/2004/07/ScmGroup.XCam.MachiningDataModel.Drilling'
                }
                
                changes_count = 0
                
                # Поиск RoundHole с диаметром ~2.22мм
                for feature in root.findall('.//ns:ManufacturingFeature[@i:type="a:RoundHole"]', namespaces):
                    diameter_elem = feature.find('drilling:Diameter', namespaces)
                    
                    if diameter_elem is not None and diameter_elem.text:
                        try:
                            diameter = float(diameter_elem.text)
                            
                            # Проверка близости к 2.22мм (с погрешностью 0.01)
                            if abs(diameter - 2.22) < 0.01:
                                # Замена на фрезу E007
                                tool_key = feature.find('ns:ToolKey', namespaces)
                                if tool_key is None:
                                    tool_key = ET.SubElement(feature, '{http://schemas.datacontract.org/2004/07/ScmGroup.XCam.MachiningDataModel.Utility}ToolKey')
                                
                                tool_key.text = "E007"
                                
                                # Также можно изменить диаметр если нужно
                                # diameter_elem.text = "7.0"  # Диаметр фрезы E007
                                
                                changes_count += 1
                                self._log(f"  ✅ Заменено сверло Ø{diameter}мм на фрезу E007")
                                
                        except ValueError:
                            pass
                
                if changes_count > 0:
                    # Сохранение XML
                    tree.write(xml_file, encoding='utf-8', xml_declaration=True)
                    
                    # Упаковка обратно в ZIP
                    backup_path = Path(pgmx_file).with_suffix('.pgmx.bak')
                    shutil.copy2(pgmx_file, backup_path)
                    
                    with zipfile.ZipFile(pgmx_file, 'w', zipfile.ZIP_DEFLATED) as zf:
                        for file_path in temp_dir.rglob('*'):
                            if file_path.is_file():
                                arc_name = file_path.relative_to(temp_dir)
                                zf.write(file_path, arc_name)
                    
                    fixed_files.append(pgmx_file)
                    self._log(f"  ✅ Файл сохранён (заменено инструментов: {changes_count})")
                else:
                    self._log(f"  ℹ️ Изменений не требуется")
                
                # Очистка временных файлов
                shutil.rmtree(temp_dir)
                
            except Exception as e:
                self._log(f"  ❌ Ошибка: {e}")
                # Очистка в случае ошибки
                try:
                    shutil.rmtree(temp_dir)
                except:
                    pass
        
        self.progress_bar.setVisible(False)
        
        # Итоговый отчёт
        self._log("\n" + "="*60)
        self._log("📊 ИТОГОВЫЙ ОТЧЁТ ПО ПРАБКЕ .PGMX")
        self._log("="*60)
        
        if fixed_files:
            self._log(f"\n✅ Исправлено файлов: {len(fixed_files)}")
            for f in fixed_files:
                self._log(f"  • {Path(f).name}")
        else:
            self._log("\nℹ️ Файлы не требовали исправлений")
        
        self.status_label.setText(f"Исправлено PGMX файлов: {len(fixed_files)}")
    
    def _on_restore_dots(self):
        """Вернуть точки вместо запятых в исправленных файлах"""
        if not self.scx_files:
            QMessageBox.warning(self, "Предупреждение", "Нет файлов .SCX для обработки")
            return
        
        self._log("\n🔄 ВОЗВРАТ ТОЧЕК ВМЕСТО ЗАПЯТЫХ")
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(self.scx_files))
        
        restored_files = []
        
        for i, scx_file in enumerate(self.scx_files):
            self.progress_bar.setValue(i + 1)
            self._log(f"\nОбработка: {Path(scx_file).name}")
            
            try:
                encoding = EncodingDetector.detect_encoding(scx_file)
                
                with open(scx_file, 'r', encoding=encoding) as f:
                    content = f.read()
                
                original_content = content
                
                # Замена запятых на точки только в числовых значениях Type="4"
                # Pattern: Type="4" ... X="123,45" → X="123.45"
                pattern = r'(Type="4"[^>]*)(X|Y|Z|EndZ|Width)="([\d]+),([\d]+)"'
                
                def replace_comma_with_dot(match):
                    prefix = match.group(1)
                    attr = match.group(2)
                    int_part = match.group(3)
                    frac_part = match.group(4)
                    return f'{prefix}{attr}="{int_part}.{frac_part}"'
                
                content = re.sub(pattern, replace_comma_with_dot, content)
                
                if content != original_content:
                    with open(scx_file, 'w', encoding=encoding) as f:
                        f.write(content)
                    restored_files.append(scx_file)
                    self._log(f"  ✅ Точки возвращены")
                else:
                    self._log(f"  ℹ️ Изменений не требуется")
                
            except Exception as e:
                self._log(f"  ❌ Ошибка: {e}")
        
        self.progress_bar.setVisible(False)
        
        self._log("\n" + "="*60)
        self._log("📊 ИТОГОВЫЙ ОТЧЁТ ПО ВОЗВРАТУ ТОЧЕК")
        self._log("="*60)
        
        if restored_files:
            self._log(f"\n✅ Восстановлено файлов: {len(restored_files)}")
            for f in restored_files:
                self._log(f"  • {Path(f).name}")
        else:
            self._log("\nℹ️ Файлы не требовали восстановления")
        
        self.status_label.setText(f"Восстановлено точек в SCX файлах: {len(restored_files)}")


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    window = LithiumPanelEditor()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
