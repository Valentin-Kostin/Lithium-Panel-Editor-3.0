"""
Вкладка настроек приложения.
Содержит:
- Кнопку загрузки базы инструментов
- Таблицу для просмотра всех инструментов
- Выбор темы оформления (5 вариантов)
- Настройка размера шрифта
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QFileDialog, QLabel, QTableWidget, QTableWidgetItem,
    QGroupBox, QHeaderView, QMessageBox, QComboBox, 
    QSpinBox, QFormLayout
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush, QFont
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
        
        # === ГРУППА: Оформление ===
        appearance_group = QGroupBox("🎨 Оформление")
        appearance_layout = QFormLayout(appearance_group)
        
        # Выбор темы
        theme_layout = QHBoxLayout()
        self.combo_theme = QComboBox()
        self.combo_theme.addItems(list(Settings.THEMES.keys()))
        current_theme = self.settings.get_theme()
        self.combo_theme.setCurrentText(current_theme)
        self.combo_theme.setMinimumWidth(200)
        
        btn_apply_theme = QPushButton("Применить тему")
        btn_apply_theme.clicked.connect(self._apply_theme)
        
        theme_layout.addWidget(self.combo_theme)
        theme_layout.addWidget(btn_apply_theme)
        theme_layout.addStretch()
        
        # Размер шрифта
        font_layout = QHBoxLayout()
        self.spin_font_size = QSpinBox()
        self.spin_font_size.setRange(8, 24)
        self.spin_font_size.setValue(self.settings.get_font_size())
        self.spin_font_size.setMinimumWidth(100)
        
        btn_apply_font = QPushButton("Применить шрифт")
        btn_apply_font.clicked.connect(self._apply_font_size)
        
        font_layout.addWidget(self.spin_font_size)
        font_layout.addWidget(QLabel("px"))
        font_layout.addWidget(btn_apply_font)
        font_layout.addStretch()
        
        appearance_layout.addRow("Тема оформления:", theme_layout)
        appearance_layout.addRow("Размер шрифта:", font_layout)
        
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
        self.table_tools.setHorizontalHeaderLabels(["ID", "Название фрезы", "Диаметр (мм)", "Обороты"])
        self.table_tools.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_tools.setAlternatingRowColors(False)  # Отключаем стандартное чередование, будем управлять через стили
        
        table_layout.addWidget(self.table_tools)
        
        # Сборка интерфейса
        main_layout.addWidget(appearance_group)
        main_layout.addWidget(tools_group)
        main_layout.addWidget(table_group, stretch=1)
        
        # Применяем текущую тему и шрифт при запуске
        self._apply_theme()
        self._apply_font_size()
        
    def connect_signals(self, main_window):
        """Подключение сигналов к методам главного окна."""
        self.btn_load_tools.clicked.connect(lambda: main_window._on_load_tools_in_settings())
        self.btn_refresh_tools.clicked.connect(self._refresh_tools_table)
        
    def _apply_theme(self):
        """Применение выбранной темы оформления."""
        theme_name = self.combo_theme.currentText()
        self.settings.set_theme(theme_name)
        colors = self.settings.get_theme_colors()
        
        # Получаем текущий размер шрифта для расчёта размеров кнопок
        font_size = self.spin_font_size.value()
        # Уменьшаем коэффициенты масштабирования, чтобы кнопки не были слишком большими
        padding = int(font_size * 0.4)  # вертикальный отступ
        hpadding = int(font_size * 0.8)  # горизонтальный отступ
        btn_min_height = int(font_size * 1.8)  # минимальная высота кнопки
        
        # Применяем стили ко всему приложению через главное окно
        main_window = self._get_main_window()
        if main_window:
            main_window.apply_theme_and_font(colors, font_size, padding, hpadding, btn_min_height)
            
        # Обновляем цвета статусных меток
        self._update_status_colors(colors)
    
    def _get_main_window(self):
        """Получение ссылки на главное окно MainWindow."""
        widget = self
        while widget:
            from .main_window import MainWindow
            if isinstance(widget, MainWindow):
                return widget
            widget = widget.parentWidget()
        return None
        
    def _update_status_colors(self, colors):
        """Обновление цветов статусных меток в соответствии с темой."""
        # Обновляем текущий статус
        current_text = self.lbl_tool_status.text()
        if "✅" in current_text:
            self.lbl_tool_status.setStyleSheet(f"color: {colors['accent']}; font-weight: bold;")
        elif "❌" in current_text or "Ошибка" in current_text:
            self.lbl_tool_status.setStyleSheet("color: #ff6b6b; font-weight: bold;")
        else:
            self.lbl_tool_status.setStyleSheet(f"color: {colors['text_primary']}; font-weight: bold;")
            
    def _apply_font_size(self):
        """Применение выбранного размера шрифта."""
        font_size = self.spin_font_size.value()
        self.settings.set_font_size(font_size)
        
        # Создаем новый шрифт с выбранным размером
        font = QFont("Segoe UI", font_size)
        
        # Применяем шрифт ко всем виджетам на вкладке
        self.setFont(font)
        
        # Применяем шрифт к таблице
        self.table_tools.setFont(font)
        header_font = self.table_tools.horizontalHeader().font()
        header_font.setPointSize(font_size)
        header_font.setBold(True)
        self.table_tools.horizontalHeader().setFont(header_font)
        
        # Увеличиваем высоту строк таблицы пропорционально шрифту
        row_height = int(font_size * 2.2)
        self.table_tools.verticalHeader().setDefaultSectionSize(row_height)
        
        # Пересчитываем и применяем тему с новыми размерами
        self._apply_theme()
                
    def update_tool_info(self, file_path: str, is_loaded: bool):
        """Обновление информации о базе инструментов."""
        colors = self.settings.get_theme_colors()
        
        if file_path:
            self.lbl_tool_path.setText(f"Путь к базе инструментов: {file_path}")
            self.lbl_tool_path.setStyleSheet(f"color: {colors['accent']};")
            
            if is_loaded:
                self.lbl_tool_status.setText("Статус: ✅ База загружена")
                self.lbl_tool_status.setStyleSheet(f"color: {colors['accent']}; font-weight: bold;")
            else:
                self.lbl_tool_status.setText("Статус: ❌ Ошибка загрузки базы")
                self.lbl_tool_status.setStyleSheet("color: #ff6b6b; font-weight: bold;")
        else:
            self.lbl_tool_path.setText("Путь к базе инструментов: не указан")
            self.lbl_tool_path.setStyleSheet(f"color: {colors['text_primary']}; opacity: 0.6;")
            self.lbl_tool_status.setText("Статус: база не загружена")
            self.lbl_tool_status.setStyleSheet(f"color: {colors['text_primary']}; font-weight: bold;")
            
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
        
        # Сначала отображаем фрезы (Exxx)
        for tool_id in global_tool_db.mill_order:
            if tool_id not in global_tool_db.tools:
                continue
            
            tool_data = global_tool_db.tools[tool_id]
            row = self.table_tools.rowCount()
            self.table_tools.insertRow(row)
            
            # ID (например, "E001")
            item_id = QTableWidgetItem(tool_data.get('id', ''))
            item_id.setFlags(item_id.flags() & ~Qt.ItemIsEditable)
            self.table_tools.setItem(row, 0, item_id)
            
            # Название фрезы (описание из файла - например "V90 зенковка")
            item_name = QTableWidgetItem(tool_data.get('description', ''))
            item_name.setFlags(item_name.flags() & ~Qt.ItemIsEditable)
            self.table_tools.setItem(row, 1, item_name)
            
            # Диаметр
            diameter = tool_data.get('diameter', 0.0)
            item_diameter = QTableWidgetItem(f"{diameter:.1f}" if diameter > 0 else "N/A")
            item_diameter.setFlags(item_diameter.flags() & ~Qt.ItemIsEditable)
            item_diameter.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table_tools.setItem(row, 2, item_diameter)
            
            # Обороты
            rpm = tool_data.get('rpm', 0.0)
            item_rpm = QTableWidgetItem(f"{int(rpm)}" if rpm > 0 else "N/A")
            item_rpm.setFlags(item_rpm.flags() & ~Qt.ItemIsEditable)
            item_rpm.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table_tools.setItem(row, 3, item_rpm)
        
        # Добавляем разделитель перед сверлами, если есть и фрезы и сверла
        has_mills = any(tool_id in global_tool_db.tools for tool_id in global_tool_db.mill_order)
        has_drills = any(tool_id in global_tool_db.tools for tool_id in global_tool_db.drill_order)
        
        if has_mills and has_drills:
            row = self.table_tools.rowCount()
            self.table_tools.insertRow(row)
            separator_item = QTableWidgetItem("═══ СВЁРЛА ═══")
            separator_item.setFlags(separator_item.flags() & ~Qt.ItemIsEditable)
            separator_item.setTextAlignment(Qt.AlignCenter)
            colors = self.settings.get_theme_colors()
            # Убираем явную установку фона и текста, пусть работает через стили темы
            font = separator_item.font()
            font.setBold(True)
            separator_item.setFont(font)
            self.table_tools.setItem(row, 0, separator_item)
            self.table_tools.setSpan(row, 0, 1, 4)
        
        # Затем отображаем сверла (0xx)
        for tool_id in global_tool_db.drill_order:
            if tool_id not in global_tool_db.tools:
                continue
            
            tool_data = global_tool_db.tools[tool_id]
            row = self.table_tools.rowCount()
            self.table_tools.insertRow(row)
            
            # ID (например, "001")
            item_id = QTableWidgetItem(tool_data.get('id', ''))
            item_id.setFlags(item_id.flags() & ~Qt.ItemIsEditable)
            self.table_tools.setItem(row, 0, item_id)
            
            # Описание (для сверел обычно пустое, но оставляем поле)
            item_name = QTableWidgetItem(tool_data.get('description', ''))
            item_name.setFlags(item_name.flags() & ~Qt.ItemIsEditable)
            self.table_tools.setItem(row, 1, item_name)
            
            # Диаметр
            diameter = tool_data.get('diameter', 0.0)
            item_diameter = QTableWidgetItem(f"{diameter:.1f}" if diameter > 0 else "N/A")
            item_diameter.setFlags(item_diameter.flags() & ~Qt.ItemIsEditable)
            item_diameter.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table_tools.setItem(row, 2, item_diameter)
            
            # Обороты
            rpm = tool_data.get('rpm', 0.0)
            item_rpm = QTableWidgetItem(f"{int(rpm)}" if rpm > 0 else "N/A")
            item_rpm.setFlags(item_rpm.flags() & ~Qt.ItemIsEditable)
            item_rpm.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table_tools.setItem(row, 3, item_rpm)
