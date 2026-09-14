"""
Вкладка настроек приложения.
Содержит:
- Кнопку загрузки базы инструментов
- Таблицу для просмотра всех инструментов
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QFileDialog, QLabel, QTableWidget, QTableWidgetItem,
    QGroupBox, QHeaderView, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush
from ..core.tool_db import global_tool_db
from ..utils.settings import Settings


class SettingsTab(QWidget):
    """Вкладка настроек приложения."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = Settings()
        self._setup_ui()
        
    def _setup_ui(self):
        """Создание интерфейса вкладки настроек."""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        # === ГРУППА: База инструментов ===
        tools_group = QGroupBox("🔧 База инструментов")
        tools_layout = QVBoxLayout(tools_group)
        
        # Информация о текущей базе
        self.lbl_tool_path = QLabel("Путь к базе инструментов: не указан")
        self.lbl_tool_path.setWordWrap(True)
        self.lbl_tool_path.setStyleSheet("color: #888;")
        
        self.lbl_tool_status = QLabel("Статус: база не загружена")
        self.lbl_tool_status.setStyleSheet("color: #ff6b6b; font-weight: bold;")
        
        # Кнопки управления базой инструментов
        btn_layout = QHBoxLayout()
        
        self.btn_load_tools = QPushButton("📂 Загрузить базу инструментов")
        self.btn_load_tools.setToolTip("Выбрать файл def.tlgx с базой инструментов")
        self.btn_load_tools.setMinimumHeight(40)
        
        self.btn_refresh_tools = QPushButton("🔄 Обновить таблицу")
        self.btn_refresh_tools.setToolTip("Обновить таблицу инструментов")
        self.btn_refresh_tools.setMinimumHeight(40)
        
        btn_layout.addWidget(self.btn_load_tools)
        btn_layout.addWidget(self.btn_refresh_tools)
        
        tools_layout.addWidget(self.lbl_tool_path)
        tools_layout.addWidget(self.lbl_tool_status)
        tools_layout.addLayout(btn_layout)
        
        # === Таблица инструментов ===
        table_group = QGroupBox("📋 Список инструментов")
        table_layout = QVBoxLayout(table_group)
        
        self.table_tools = QTableWidget()
        self.table_tools.setColumnCount(4)
        self.table_tools.setHorizontalHeaderLabels(["ID", "Название", "Диаметр (мм)", "Описание"])
        self.table_tools.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_tools.setAlternatingRowColors(True)
        self.table_tools.setStyleSheet("""
            QTableWidget {
                background-color: #2d2d2d;
                color: #d4d4d4;
                border: 1px solid #3e3e3e;
                gridline-color: #3e3e3e;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QHeaderView::section {
                background-color: #3e3e3e;
                color: #ffffff;
                padding: 5px;
                border: none;
                font-weight: bold;
            }
        """)
        
        table_layout.addWidget(self.table_tools)
        
        # Сборка интерфейса
        main_layout.addWidget(tools_group)
        main_layout.addWidget(table_group, stretch=1)
        
    def connect_signals(self, main_window):
        """Подключение сигналов к методам главного окна."""
        self.btn_load_tools.clicked.connect(lambda: main_window._on_load_tools_in_settings())
        self.btn_refresh_tools.clicked.connect(self._refresh_tools_table)
        
    def update_tool_info(self, file_path: str, is_loaded: bool):
        """Обновление информации о базе инструментов."""
        if file_path:
            self.lbl_tool_path.setText(f"Путь к базе инструментов: {file_path}")
            self.lbl_tool_path.setStyleSheet("color: #4ecdc4;")
            
            if is_loaded:
                self.lbl_tool_status.setText("Статус: ✅ База загружена")
                self.lbl_tool_status.setStyleSheet("color: #51cf66; font-weight: bold;")
            else:
                self.lbl_tool_status.setText("Статус: ❌ Ошибка загрузки базы")
                self.lbl_tool_status.setStyleSheet("color: #ff6b6b; font-weight: bold;")
        else:
            self.lbl_tool_path.setText("Путь к базе инструментов: не указан")
            self.lbl_tool_path.setStyleSheet("color: #888;")
            self.lbl_tool_status.setText("Статус: база не загружена")
            self.lbl_tool_status.setStyleSheet("color: #ff6b6b; font-weight: bold;")
            
    def _refresh_tools_table(self):
        """Обновление таблицы инструментов."""
        self.table_tools.setRowCount(0)
        
        if not global_tool_db.is_loaded or not global_tool_db.tools:
            self.table_tools.setRowCount(1)
            item = QTableWidgetItem("База инструментов не загружена")
            item.setTextAlignment(Qt.AlignCenter)
            self.table_tools.setItem(0, 0, item)
            self.table_tools.setSpan(0, 0, 1, 4)
            return
        
        # Заполняем таблицу инструментами
        for tool_id, tool_data in sorted(global_tool_db.tools.items()):
            row = self.table_tools.rowCount()
            self.table_tools.insertRow(row)
            
            # ID
            item_id = QTableWidgetItem(tool_data.get('id', ''))
            item_id.setFlags(item_id.flags() & ~Qt.ItemIsEditable)
            self.table_tools.setItem(row, 0, item_id)
            
            # Название
            item_name = QTableWidgetItem(tool_data.get('name', ''))
            item_name.setFlags(item_name.flags() & ~Qt.ItemIsEditable)
            self.table_tools.setItem(row, 1, item_name)
            
            # Диаметр
            diameter = tool_data.get('diameter', 0.0)
            item_diameter = QTableWidgetItem(f"{diameter:.3f}" if diameter > 0 else "N/A")
            item_diameter.setFlags(item_diameter.flags() & ~Qt.ItemIsEditable)
            item_diameter.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table_tools.setItem(row, 2, item_diameter)
            
            # Описание
            item_desc = QTableWidgetItem(tool_data.get('description', ''))
            item_desc.setFlags(item_desc.flags() & ~Qt.ItemIsEditable)
            self.table_tools.setItem(row, 3, item_desc)
