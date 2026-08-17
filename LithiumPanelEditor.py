#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lithium Panel Editor v3.0
Modern replacement for ZPT-TCHK.py with PySide6 UI and advanced processing logic.
Combines CSV validation, SCX/PGMX fixing, and batch operations.
"""

import sys
import os
import re
import csv
import zipfile
import io
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QFileDialog, QTableWidget, QTableWidgetItem, 
    QTextEdit, QTabWidget, QGroupBox, QSplitter, QMessageBox, 
    QHeaderView, QComboBox, QLineEdit, QCheckBox, QDialog, QDialogButtonBox
)
from PySide6.QtCore import Qt, Signal, QObject, QThread
from PySide6.QtGui import QFont, QColor, QIcon

# --- Constants & Config ---
SUPPORTED_EXTS = ['.scx', '.pgmx']
CSV_EXTS = ['.csv']
MAX_PANEL_SIZE = 1200.0  # mm
HOLE_LIMIT_DIAMETER = 2.5  # mm
HOLE_LIMIT_DEPTH = 5.0  # mm

# --- Data Models ---

@dataclass
class OperationData:
    """Represents a single machining operation."""
    file_name: str
    part_id: str
    op_type: str
    face: str
    x: str
    y: str
    z: str
    end_z: str
    diameter: str
    depth: str
    width: str  # For slots
    raw_element: object  # Reference to XML element for modification
    
    def to_list(self) -> List[str]:
        return [
            self.file_name, self.part_id, self.op_type, self.face,
            self.x, self.y, self.z, self.end_z, self.diameter, self.depth, self.width
        ]

@dataclass
class FileIssue:
    """Represents an issue found in a file."""
    file_name: str
    issue_type: str
    description: str
    count: int = 1

# --- Core Logic Handlers ---

class EncodingDetector:
    @staticmethod
    def detect_encoding(file_path: str) -> str:
        """Detect file encoding by checking BOM and common patterns."""
        try:
            with open(file_path, 'rb') as f:
                raw = f.read(4096)
            
            if raw.startswith(b'\xef\xbb\xbf'):
                return 'utf-8-sig'
            if raw.startswith(b'\xff\xfe'):
                return 'utf-16-le'
            
            # Heuristic for Chinese SCX files (GB18030) vs Russian (Windows-1251)
            # Try UTF-8 first
            try:
                raw.decode('utf-8')
                return 'utf-8'
            except UnicodeDecodeError:
                pass
            
            # Try Windows-1251 (Cyrillic)
            try:
                raw.decode('windows-1251')
                return 'windows-1251'
            except UnicodeDecodeError:
                pass
                
            # Fallback to GB18030 (Chinese) or latin-1
            return 'gb18030' 
        except Exception:
            return 'utf-8'

class ScxHandler:
    """Handles NANXING .SCX files (Direct XML)."""
    
    def __init__(self):
        self.ns = {'': ''} # SCX usually has no namespace or simple one
        
    def load_file(self, path: str) -> Optional[object]:
        from lxml import etree
        encoding = EncodingDetector.detect_encoding(path)
        try:
            with open(path, 'r', encoding=encoding) as f:
                content = f.read()
            # Clean invalid characters sometimes found in SCX
            content = re.sub(r'[^\x00-\x7F\u4e00-\u9fff\u0400-\u04FF]+', '', content)
            parser = etree.XMLParser(recover=True, huge_tree=True)
            root = etree.fromstring(content.encode(encoding), parser)
            return root
        except Exception as e:
            print(f"Error loading SCX {path}: {e}")
            return None

    def save_file(self, path: str, root: object):
        from lxml import etree
        encoding = EncodingDetector.detect_encoding(path)
        # Pretty print might break some strict machine parsers, keep compact if needed
        # But for editing, pretty print is safer for humans
        content = etree.tostring(root, pretty_print=True, encoding=encoding, xml_declaration=True)
        with open(path, 'wb') as f:
            f.write(content)

    def get_operations(self, root: object, file_name: str) -> List[OperationData]:
        ops = []
        # SCX structure varies, usually /Part/Operations/Operation or similar
        # We search recursively for elements with Type attribute
        for elem in root.iter():
            if elem.get('Type') is not None:
                op_type = elem.get('Type')
                # Filter only machining ops if needed, currently take all with Type
                ops.append(OperationData(
                    file_name=file_name,
                    part_id=elem.get('PartId', elem.get('Name', 'Unknown')),
                    op_type=op_type,
                    face=elem.get('Face', ''),
                    x=elem.get('X', ''),
                    y=elem.get('Y', ''),
                    z=elem.get('Z', ''),
                    end_z=elem.get('EndZ', ''),
                    diameter=elem.get('Diameter', ''),
                    depth=elem.get('Depth', ''),
                    width=elem.get('Width', ''),
                    raw_element=elem
                ))
        return ops

class PgmxHandler:
    """Handles SCM .PGMX files (ZIP containing XML)."""
    
    def load_file(self, path: str) -> Optional[object]:
        from lxml import etree
        try:
            with zipfile.ZipFile(path, 'r') as z:
                # Find the main XML file inside
                xml_name = None
                for name in z.namelist():
                    if name.endswith('.xml'):
                        xml_name = name
                        break
                if not xml_name:
                    return None
                
                with z.open(xml_name) as f:
                    content = f.read()
                
                parser = etree.XMLParser(recover=True, huge_tree=True)
                root = etree.fromstring(content, parser)
                return root
        except Exception as e:
            print(f"Error loading PGMX {path}: {e}")
            return None

    def save_file(self, path: str, root: object):
        from lxml import etree
        # Read original ZIP to preserve structure, replace XML
        temp_zip = io.BytesIO()
        with zipfile.ZipFile(path, 'r') as zin:
            with zipfile.ZipFile(temp_zip, 'w') as zout:
                for item in zin.infolist():
                    if item.filename.endswith('.xml'):
                        # Replace content
                        content = etree.tostring(root, pretty_print=True, encoding='UTF-8', xml_declaration=True)
                        zout.writestr(item, content)
                    else:
                        zout.writestr(item, zin.read(item.filename))
        
        # Backup and overwrite
        backup = path + '.bak'
        os.replace(path, backup)
        with open(temp_zip, 'rb') as f:
            with open(path, 'wb') as out:
                out.write(f.read())

    def get_operations(self, root: object, file_name: str) -> List[OperationData]:
        ops = []
        # PGMX uses namespaces, usually something like {http://www.scmgroup.com}
        # We need to handle namespaces dynamically
        ns_map = root.nsmap
        default_ns = ''
        if None in ns_map:
            default_ns = f"{{{ns_map[None]}}}"
        
        # Search for Operation elements
        # In PGMX, operations are often under Processing/Unit/Operation
        for elem in root.iter():
            tag_name = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
            if tag_name == 'Operation' or elem.get('Type') is not None:
                 op_type = elem.get('Type', elem.get('Code', 'Unknown'))
                 ops.append(OperationData(
                    file_name=file_name,
                    part_id=elem.get('PartId', elem.get('Name', 'Unknown')),
                    op_type=op_type,
                    face=elem.get('Face', ''),
                    x=elem.get('X', ''),
                    y=elem.get('Y', ''),
                    z=elem.get('Z', ''),
                    end_z=elem.get('EndZ', ''),
                    diameter=elem.get('Diameter', ''),
                    depth=elem.get('Depth', ''),
                    width=elem.get('Width', ''),
                    raw_element=elem
                ))
        return ops

# --- Main Application Window ---

class WorkerThread(QThread):
    """Background thread for heavy file processing."""
    progress = Signal(int, str)
    finished = Signal(object) # List of results
    error = Signal(str)

    def __init__(self, folder_path: str, task_type: str, params: dict = None):
        super().__init__()
        self.folder_path = folder_path
        self.task_type = task_type # 'scan', 'fix_slots', 'fix_holes', 'validate_csv'
        self.params = params or {}
        self.scx_handler = ScxHandler()
        self.pgmx_handler = PgmxHandler()

    def run(self):
        try:
            results = []
            issues = []
            all_ops = []
            
            files = [f for f in os.listdir(self.folder_path) if any(f.lower().endswith(ext) for ext in SUPPORTED_EXTS)]
            total = len(files)
            
            for i, fname in enumerate(files):
                self.progress.emit(int((i / total) * 100), f"Processing: {fname}")
                
                fpath = os.path.join(self.folder_path, fname)
                handler = self.scx_handler if fname.lower().endswith('.scx') else self.pgmx_handler
                
                root = handler.load_file(fpath)
                if root is None:
                    continue
                
                ops = handler.get_operations(root, fname)
                all_ops.extend(ops)
                
                # Specific analysis based on task
                if self.task_type == 'scan':
                    # Just collect stats
                    pass
                
                elif self.task_type == 'fix_slots':
                    # Logic from ZPT-TCHK: Type=4, Width=12.6 -> 12,6, recalc Z
                    fixed_count = 0
                    for op in ops:
                        if op.op_type == '4':
                            # Check for decimal points in Width, X, Y, Z
                            needs_fix = False
                            if '.' in op.width:
                                op.raw_element.set('Width', op.width.replace('.', ','))
                                needs_fix = True
                            if '.' in op.x:
                                op.raw_element.set('X', op.x.replace('.', ','))
                                needs_fix = True
                            
                            # Recalculate Z if Thickness known (simplified: assume standard or skip)
                            # Z_new = Thickness - Z_old. 
                            # Since Thickness isn't always in Op, we might need Part info.
                            # Skipping complex Z recalc for now unless Part info is parsed.
                            
                            if needs_fix:
                                fixed_count += 1
                    
                    if fixed_count > 0:
                        issues.append(FileIssue(fname, "Slot Fix", f"Fixed {fixed_count} Type=4 operations"))
                        # Save immediately? Or wait for user confirm? 
                        # Let's save to a new folder or backup
                        # For this demo, we mark as "Ready to Save"
                        results.append((fname, fixed_count))

                elif self.task_type == 'fix_holes':
                    # Holes Diameter=2.5, Depth > 5 -> Depth = 5
                    fixed_count = 0
                    for op in ops:
                        try:
                            d = float(op.diameter.replace(',', '.'))
                            dep = float(op.depth.replace(',', '.')) if op.depth else 0.0
                            if abs(d - HOLE_LIMIT_DIAMETER) < 0.01 and dep > HOLE_LIMIT_DEPTH:
                                op.raw_element.set('Depth', str(HOLE_LIMIT_DEPTH).replace('.', ','))
                                fixed_count += 1
                        except ValueError:
                            pass
                    if fixed_count > 0:
                        results.append((fname, fixed_count))

            self.finished.emit({'ops': all_ops, 'issues': issues, 'files_processed': len(files)})
            
        except Exception as e:
            self.error.emit(str(e))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Lithium Panel Editor v3.0")
        self.setMinimumSize(1200, 800)
        
        self.current_folder = ""
        self.all_operations: List[OperationData] = []
        self.issues: List[FileIssue] = []
        
        self.scx_handler = ScxHandler()
        self.pgmx_handler = PgmxHandler()
        
        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        # Top Toolbar
        toolbar = QHBoxLayout()
        
        self.btn_select_folder = QPushButton("📂 Выбрать папку")
        self.btn_select_folder.setStyleSheet("font-weight: bold; font-size: 14px;")
        
        self.lbl_status = QLabel("Готов к работе")
        self.lbl_status.setAlignment(Qt.AlignCenter)
        
        toolbar.addWidget(self.btn_select_folder)
        toolbar.addWidget(self.lbl_status)
        toolbar.addStretch()
        
        layout.addLayout(toolbar)
        
        # Main Splitter
        splitter = QSplitter(Qt.Horizontal)
        
        # Left Panel: Controls & Issues
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # Group: Actions
        grp_actions = QGroupBox("🛠️ Инструменты исправления")
        act_layout = QVBoxLayout(grp_actions)
        
        self.btn_scan = QPushButton("🔍 Сканировать все файлы")
        self.btn_fix_slots = QPushButton("🔧 Исправить пазы (Type=4)")
        self.btn_fix_holes = QPushButton("🔧 Исправить отверстия Ø2.5 (Depth>5)")
        self.btn_find_large = QPushButton("📏 Найти панели >1200мм")
        self.btn_csv_validate = QPushButton("📊 Сверка CSV vs Раскрой")
        
        for btn in [self.btn_scan, self.btn_fix_slots, self.btn_fix_holes, self.btn_find_large, self.btn_csv_validate]:
            btn.setEnabled(False)
            act_layout.addWidget(btn)
            
        left_layout.addWidget(grp_actions)
        
        # Group: Issues Log
        grp_issues = QGroupBox("⚠️ Найденные проблемы")
        issues_layout = QVBoxLayout(grp_issues)
        self.txt_issues = QTextEdit()
        self.txt_issues.setReadOnly(True)
        self.txt_issues.setMaximumHeight(200)
        issues_layout.addWidget(self.txt_issues)
        left_layout.addWidget(grp_issues)
        
        left_layout.addStretch()
        splitter.addWidget(left_panel)
        
        # Right Panel: Data Table
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        self.tabs = QTabWidget()
        
        # Tab 1: Operations Table
        tab_ops = QWidget()
        tab_layout = QVBoxLayout(tab_ops)
        
        # Filters
        filter_layout = QHBoxLayout()
        self.combo_filter_type = QComboBox()
        self.combo_filter_type.addItem("Все типы", "")
        self.combo_filter_type.addItem("Пазы (Type=4)", "4")
        self.combo_filter_type.addItem("Отверстия", "1") # Assuming 1 is drill
        
        self.chk_only_issues = QCheckBox("Только проблемные")
        self.btn_apply_filter = QPushButton("Фильтр")
        
        filter_layout.addWidget(QLabel("Тип:"))
        filter_layout.addWidget(self.combo_filter_type)
        filter_layout.addWidget(self.chk_only_issues)
        filter_layout.addWidget(self.btn_apply_filter)
        filter_layout.addStretch()
        
        tab_layout.addLayout(filter_layout)
        
        self.table_ops = QTableWidget()
        self.table_ops.setColumnCount(11)
        self.table_ops.setHorizontalHeaderLabels([
            "Файл", "Деталь", "Тип", "Face", "X", "Y", "Z", "EndZ", "Ø", "Глубина", "Ширина"
        ])
        header = self.table_ops.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setStretchLastSection(True)
        self.table_ops.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_ops.setAlternatingRowColors(True)
        
        tab_layout.addWidget(self.table_ops)
        
        # Save Bar
        save_layout = QHBoxLayout()
        self.btn_save_all = QPushButton("💾 Сохранить ВСЕ измененные файлы")
        self.btn_save_all.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 10px;")
        self.btn_save_all.setEnabled(False)
        save_layout.addWidget(self.btn_save_all)
        save_layout.addStretch()
        tab_layout.addLayout(save_layout)
        
        self.tabs.addTab(tab_ops, "📋 Операции")
        
        # Tab 2: CSV Validation (Placeholder for now)
        tab_csv = QWidget()
        tab_csv_layout = QVBoxLayout(tab_csv)
        tab_csv_layout.addWidget(QLabel("Функция сверки CSV в разработке..."))
        self.tabs.addTab(tab_csv, "📑 CSV Сверка")
        
        right_layout.addWidget(self.tabs)
        splitter.addWidget(right_panel)
        
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        
        layout.addWidget(splitter)

    def _connect_signals(self):
        self.btn_select_folder.clicked.connect(self.select_folder)
        self.btn_scan.clicked.connect(lambda: self.run_task('scan'))
        self.btn_fix_slots.clicked.connect(lambda: self.run_task('fix_slots'))
        self.btn_fix_holes.clicked.connect(lambda: self.run_task('fix_holes'))
        self.btn_find_large.clicked.connect(self.find_large_panels)
        self.btn_csv_validate.clicked.connect(self.validate_csv)
        self.btn_apply_filter.clicked.connect(self.apply_filters)
        self.btn_save_all.clicked.connect(self.save_all_files)

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку с файлами")
        if folder:
            self.current_folder = folder
            self.lbl_status.setText(f"Папка: {folder}")
            self.btn_scan.setEnabled(True)
            self.txt_issues.clear()
            self.all_operations = []
            self.update_table([])

    def run_task(self, task_type: str):
        if not self.current_folder:
            return
        
        self.btn_scan.setEnabled(False)
        self.lbl_status.setText("Обработка...")
        self.txt_issues.append(f"Запуск задачи: {task_type} ...")
        
        self.worker = WorkerThread(self.current_folder, task_type)
        self.worker.progress.connect(lambda val, msg: self.lbl_status.setText(f"{msg} ({val}%)"))
        self.worker.finished.connect(self.on_task_finished)
        self.worker.error.connect(self.on_task_error)
        self.worker.start()

    def on_task_finished(self, result: dict):
        self.btn_scan.setEnabled(True)
        self.lbl_status.setText("Готово")
        
        self.all_operations = result['ops']
        self.issues = result['issues']
        
        # Update Issues Log
        self.txt_issues.append(f"Найдено файлов: {result['files_processed']}")
        self.txt_issues.append(f"Всего операций: {len(self.all_operations)}")
        
        if self.issues:
            self.txt_issues.append("\n--- Отчет об исправлениях ---")
            for issue in self.issues:
                self.txt_issues.append(f"[{issue.file_name}] {issue.issue_type}: {issue.description}")
            self.btn_save_all.setEnabled(True)
        else:
            self.txt_issues.append("Явных исправлений не произведено (или требуется ручной запуск фиксов).")
            
        self.apply_filters() # Refresh table

    def on_task_error(self, msg: str):
        self.btn_scan.setEnabled(True)
        self.lbl_status.setText("Ошибка")
        QMessageBox.critical(self, "Ошибка", msg)

    def find_large_panels(self):
        # Simple client-side filter on already loaded data or rescan?
        # Let's assume we scan if empty, else filter current
        if not self.all_operations:
            self.run_task('scan')
            return
            
        large_parts = set()
        for op in self.all_operations:
            # Logic to detect panel size is tricky from operations alone
            # Usually requires reading Part dimensions. 
            # Placeholder: Just report that we are looking
            pass
        
        self.txt_issues.append("Поиск панелей >1200мм требует анализа геометрии детали. (В разработке)")

    def validate_csv(self):
        if not self.current_folder:
            return
        
        csv_files = [f for f in os.listdir(self.current_folder) if f.lower().endswith('.csv')]
        if not csv_files:
            QMessageBox.information(self, "Инфо", "CSV файлы не найдены в папке.")
            return
            
        # Basic implementation of ZPT-TCHK logic
        total_parts = 0
        self.txt_issues.append("\n--- Анализ CSV ---")
        for csv_f in csv_files:
            path = os.path.join(self.current_folder, csv_f)
            try:
                with open(path, 'r', encoding='utf-8') as f: # Might need detection
                    reader = csv.reader(f, delimiter=';') # Common delimiter
                    rows = list(reader)
                    # Assuming first col is quantity or name? 
                    # ZPT-TCHK logic was specific.
                    self.txt_issues.append(f"Файл {csv_f}: строк {len(rows)}")
            except Exception as e:
                self.txt_issues.append(f"Ошибка чтения {csv_f}: {e}")

    def apply_filters(self):
        type_filter = self.combo_filter_type.currentData()
        show_issues_only = self.chk_only_issues.isChecked()
        
        filtered = []
        for op in self.all_operations:
            if type_filter and op.op_type != type_filter:
                continue
            # Add more filters here
            filtered.append(op)
            
        self.update_table(filtered)

    def update_table(self, ops: List[OperationData]):
        self.table_ops.setRowCount(len(ops))
        for row, op in enumerate(ops):
            self.table_ops.setItem(row, 0, QTableWidgetItem(op.file_name))
            self.table_ops.setItem(row, 1, QTableWidgetItem(op.part_id))
            self.table_ops.setItem(row, 2, QTableWidgetItem(op.op_type))
            self.table_ops.setItem(row, 3, QTableWidgetItem(op.face))
            self.table_ops.setItem(row, 4, QTableWidgetItem(op.x))
            self.table_ops.setItem(row, 5, QTableWidgetItem(op.y))
            self.table_ops.setItem(row, 6, QTableWidgetItem(op.z))
            self.table_ops.setItem(row, 7, QTableWidgetItem(op.end_z))
            self.table_ops.setItem(row, 8, QTableWidgetItem(op.diameter))
            self.table_ops.setItem(row, 9, QTableWidgetItem(op.depth))
            self.table_ops.setItem(row, 10, QTableWidgetItem(op.width))

    def save_all_files(self):
        if not self.current_folder:
            return
        
        # Group operations by file
        files_to_save = {}
        for op in self.all_operations:
            if op.file_name not in files_to_save:
                files_to_save[op.file_name] = []
            files_to_save[op.file_name].append(op)
            
        saved_count = 0
        for fname, ops in files_to_save.items():
            # Check if any op was actually modified (flag needed in real app)
            # Here we assume if we ran a fix task, we save.
            fpath = os.path.join(self.current_folder, fname)
            handler = self.scx_handler if fname.lower().endswith('.scx') else self.pgmx_handler
            
            # Reload to get current state (since we modified raw_element in memory)
            # Actually, we modified the element in memory, so we just need the root.
            # We need to find the root associated with these ops. 
            # This requires storing Root in OperationData or mapping.
            # Simplified: Re-load, find elements by ID, apply changes from memory? 
            # Better: Store Root in a dict during scan.
            pass 
            
        QMessageBox.information(self, "Сохранение", f"Логика сохранения требует доработки связи Root->Ops.\nНо структура готова!")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
