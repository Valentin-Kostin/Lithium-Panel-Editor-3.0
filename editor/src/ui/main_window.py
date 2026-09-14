"""
Главное окно приложения Lithium Panel Editor.
Новый интерфейс:
- Верхняя панель с кнопками управления
- Большое текстовое окно логов внизу
- Вкладка настроек
"""
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QTextEdit, QFileDialog, QLabel, QProgressBar,
    QGroupBox, QApplication, QTabWidget
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
import os

from ..core.batch_processor import BatchProcessor
from ..core.tool_db import global_tool_db
from ..utils.settings import Settings
from .settings_tab import SettingsTab


class MainWindow(QMainWindow):
    """Главное окно приложения с новым интерфейсом."""
    
    def __init__(self):
        super().__init__()
        self.processor = BatchProcessor()
        self.settings = Settings()
        self.setWindowTitle("Lithium Panel Editor v3.0")
        self.setMinimumSize(900, 700)
        
        # Создаем вкладку настроек
        self.settings_tab = SettingsTab()
        
        self._setup_ui()
        self._connect_signals()
        
        # Подключаем сигналы вкладки настроек
        self.settings_tab.connect_signals(self)
        
        # Загружаем базу инструментов при старте если есть сохраненный путь
        self.load_tool_db_from_settings()
        
    def _setup_ui(self):
        """Создание интерфейса."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        # === ВКЛАДКИ ===
        self.tabs = QTabWidget()
        
        # Вкладка "Основная"
        main_tab = QWidget()
        main_tab_layout = QVBoxLayout(main_tab)
        main_tab_layout.setSpacing(10)
        main_tab_layout.setContentsMargins(0, 0, 0, 0)
        
        # === ВЕРХНЯЯ ПАНЕЛЬ С КНОПКАМИ (на основной вкладке) ===
        control_group = QGroupBox("🛠️ Панель управления")
        control_layout = QHBoxLayout(control_group)
        control_layout.setSpacing(10)
        
        # Кнопки
        self.btn_select_folder = QPushButton("📁 Выбрать папку")
        self.btn_select_folder.setToolTip("Выбрать папку с файлами .SCX, .PGMX, .CSV")
        self.btn_select_folder.setMinimumHeight(40)
        
        self.btn_fix_scx = QPushButton("✏️ Исправить .SCX (NANXING)")
        self.btn_fix_scx.setToolTip(
            "Исправить файлы .SCX:\n"
            "- Отверстия Ø2.5мм с глубиной >5мм → 5мм\n"
            "- Найти панели >1200×1200мм\n"
            "- Type=4: точки → запятые\n"
            "- Type=4 Face=0 → взять Face из метки Ø12.222"
        )
        self.btn_fix_scx.setMinimumHeight(40)
        
        self.btn_fix_pgmx = QPushButton("⚙️ Править .PGMX (SCM)")
        self.btn_fix_pgmx.setToolTip(
            "Исправить файлы .PGMX:\n"
            "- Найти сверления Ø~2.22мм\n"
            "- Заменить инструмент на E007"
        )
        self.btn_fix_pgmx.setMinimumHeight(40)
        self.btn_fix_pgmx.setEnabled(False)  # Пока база не загружена
        
        self.btn_revert_dots = QPushButton("↩️ Вернуть точки")
        self.btn_revert_dots.setToolTip(
            "Вернуть точки вместо запятых в Type=4\n"
            "(откат изменений для .SCX)"
        )
        self.btn_revert_dots.setMinimumHeight(40)
        
        self.btn_compare_csv = QPushButton("🔍 Сравнить PGMX с CSV")
        self.btn_compare_csv.setToolTip(
            "Сравнить файлы .PGMX с записями в .CSV по материалу и номеру заказа\n"
            "(ключ: всё что до первой точки, например DSP_25_U963-ST9_1971G1)"
        )
        self.btn_compare_csv.setMinimumHeight(40)
        
        # Убираем старую кнопку "База инструментов" - теперь она во вкладке Настройки
        # Добавление кнопок в layout
        control_layout.addWidget(self.btn_select_folder)
        control_layout.addWidget(self.btn_fix_scx)
        control_layout.addWidget(self.btn_fix_pgmx)
        control_layout.addWidget(self.btn_revert_dots)
        control_layout.addWidget(self.btn_compare_csv)
        
        # === ПРОГРЕСС БАР И СТАТУС ===
        status_layout = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumWidth(300)
        
        self.status_label = QLabel("Готов к работе")
        self.status_label.setAlignment(Qt.AlignCenter)
        
        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.progress_bar)
        
        # === ТЕКСТОВОЕ ОКНО ЛОГОВ ===
        log_group = QGroupBox("📋 Журнал операций")
        log_layout = QVBoxLayout(log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3e3e3e;
                border-radius: 5px;
                padding: 5px;
            }
        """)
        self.log_text.setPlaceholderText("Здесь будет выводиться информация о обработанных файлах...")
        
        log_layout.addWidget(self.log_text)
        
        # Кнопка очистки лога
        btn_clear_log = QPushButton("🗑️ Очистить лог")
        btn_clear_log.setMaximumWidth(120)
        btn_clear_log.clicked.connect(self.log_text.clear)
        log_layout.addWidget(btn_clear_log, alignment=Qt.AlignRight)
        
        # Сборка основной вкладки
        main_tab_layout.addWidget(control_group)
        main_tab_layout.addLayout(status_layout)
        main_tab_layout.addWidget(log_group, stretch=1)
        
        # Добавляем вкладки
        self.tabs.addTab(main_tab, "📊 Основная")
        self.tabs.addTab(self.settings_tab, "⚙️ Настройки")
        
        # === СБОРКА ИНТЕРФЕЙСА ===
        main_layout.addWidget(self.tabs)
        
    def _connect_signals(self):
        """Подключение сигналов к слотам."""
        self.btn_select_folder.clicked.connect(self._on_select_folder)
        # Кнопка загрузки инструментов теперь подключается через settings_tab.connect_signals()
        self.btn_fix_scx.clicked.connect(self._on_fix_scx)
        self.btn_fix_pgmx.clicked.connect(self._on_fix_pgmx)
        self.btn_revert_dots.clicked.connect(self._on_revert_dots)
        self.btn_compare_csv.clicked.connect(self._on_compare_csv)
        
    def _log(self, message: str):
        """Вывод сообщения в лог."""
        self.log_text.append(message)
        # Прокрутка вниз
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        QApplication.processEvents()
        
    def _on_select_folder(self):
        """Обработчик кнопки выбора папки."""
        folder = QFileDialog.getExistingDirectory(
            self, "Выберите папку с файлами", "",
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )
        
        if folder:
            # Очищаем лог процессора и интерфейс перед новым сканированием
            self.processor.log_messages.clear()
            self.log_text.clear()
            
            self._current_folder = folder  # Сохраняем путь к папке
            self._log(f"\n{'='*60}")
            self._log(f"📂 Выбрана папка: {folder}")
            self._log(f"{'='*60}")
            
            self.status_label.setText("Сканирование папки...")
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)  # Indeterminate mode
            
            try:
                stats = self.processor.scan_folder(folder)
                
                self._log(f"\n✅ Сканирование завершено!")
                self._log(f"\n📊 Статистика:")
                self._log(f"   Файлов .SCX найдено: {stats['scx_count']}")
                self._log(f"   Файлов .PGMX найдено: {stats['pgmx_count']}")
                self._log(f"   Файлов .CSV найдено: {stats['csv_count']}")
                
                # Подсчет общего количества записей в CSV
                total_csv_parts = stats['csv_parts_total']
                self._log(f"   Всего записей в CSV: {total_csv_parts}")
                
                # Вывод количества записей в каждом CSV файле
                if 'csv_file_counts' in stats and stats['csv_file_counts']:
                    for csv_name, count in stats['csv_file_counts'].items():
                        self._log(f"   {csv_name} = {count}шт.")
                        
                # Отсутствующие PGMX файлы уже выведены в логе batch_processor.py
                
                # OBOROT файлы уже выведены в логе batch_processor.py
                        
                self._log(f"\n💡 Теперь можно нажать 'Исправить .SCX' или 'Править .PGMX'")
                
            except Exception as e:
                self._log(f"❌ Ошибка сканирования: {e}")
            finally:
                self.progress_bar.setVisible(False)
                self.status_label.setText("Готов к работе")
                
    def _on_load_tools(self):
        """Обработчик кнопки загрузки базы инструментов (вызывается из вкладки настроек)."""
        # Проверяем есть ли сохраненный путь
        saved_path = self.settings.get_tool_db_path()
        
        if saved_path and os.path.exists(saved_path):
            self._log(f"\n✅ Найден сохраненный путь к базе инструментов: {saved_path}")
            if self._load_tool_database(saved_path):
                self._update_settings_tab()
                return
                
        # Если нет сохраненного пути или файл не найден, запрашиваем у пользователя
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите файл базы инструментов", "",
            "Tool Library Files (*.tlgx);;All Files (*)"
        )
        
        if file_path:
            if self._load_tool_database(file_path):
                # Сохраняем путь
                self.settings.set_tool_db_path(file_path)
                self._log(f"💾 Путь сохранен в настройках")
                self._update_settings_tab()
    
    def _on_load_tools_in_settings(self):
        """Вызывается при нажатии кнопки загрузки инструментов во вкладке настроек."""
        self._on_load_tools()
    
    def _update_settings_tab(self):
        """Обновляет информацию во вкладке настроек после загрузки базы."""
        saved_path = self.settings.get_tool_db_path()
        is_loaded = global_tool_db.is_loaded
        has_e007 = global_tool_db.get_replacement_tool("E007") is not None
        self.settings_tab.update_tool_info(saved_path, is_loaded, has_e007)
        self.settings_tab._refresh_tools_table()
    
    def _load_tool_database(self, file_path: str) -> bool:
        """Загружает базу инструментов и обновляет UI"""
        self._log(f"\n{'='*60}")
        self._log(f"🔧 Загрузка базы инструментов: {file_path}")
        
        # Загружаем базу через глобальный экземпляр
        if not global_tool_db.load(file_path):
            self._log(f"❌ Ошибка загрузки базы инструментов!")
            self.btn_fix_pgmx.setEnabled(False)
            return False
            
        e007 = global_tool_db.get_replacement_tool("E007")
        if e007:
            self._log(f"✅ База инструментов успешно загружена!")
            self._log(f"   🎯 Инструмент E007 найден (ID: {e007['id']})")
            self.btn_fix_pgmx.setEnabled(True)
            return True
        else:
            self._log(f"⚠️ Инструмент E007 НЕ найден в базе!")
            self._log(f"   Кнопка 'Править .PGMX' останется отключенной.")
            self.btn_fix_pgmx.setEnabled(False)
            return False
    
    def load_tool_db_from_settings(self):
        """Загружает базу инструментов при старте приложения если есть сохраненный путь."""
        saved_path = self.settings.get_tool_db_path()
        if saved_path and os.path.exists(saved_path):
            self._log(f"✅ Найден сохраненный путь к базе инструментов: {saved_path}")
            if self._load_tool_database(saved_path):
                self._update_settings_tab()
                self._log(f"💾 База инструментов загружена из сохраненного пути")
            
    def _on_fix_scx(self):
        """Обработчик кнопки исправления .SCX файлов."""
        folder = getattr(self, '_current_folder', None)
        if not folder:
            self._log("\n⚠️ Нет выбранной папки! Сначала выберите папку.")
            return
        
        # Очищаем лог процессора перед новым запуском
        self.processor.log_messages.clear()
        
        self._log(f"\n{'='*60}")
        self._log(f"✏️ ЗАПУСК ИСПРАВЛЕНИЯ .SCX")
        self._log(f"{'='*60}")
        
        self.status_label.setText("Исправление .SCX файлов...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        
        try:
            stats = self.processor.fix_scx_batch()
            
            self._log(f"\n✅ Исправление .SCX завершено!")
            if stats['processed'] > 0 or stats['panels_found'] > 0:
                self._log(f"🎉 Исправлено файлов: {stats['processed']}")
                self._log(f"   - Отверстий Ø2.5 исправлено: {stats['holes_fixed']}")
                self._log(f"   - Панелей >1200 найдено: {stats['panels_found']}")
                self._log(f"   - Type=4 с запятыми: {stats['dots_replaced']}")
                self._log(f"   - Face=0 исправлено: {stats['face_fixed']}")
                
                # Выводим детальные логи из процессора (включая названия файлов с панелями >1200)
                if self.processor.log_messages:
                    self._log(f"\n📋 Детальный отчет:")
                    for msg in self.processor.log_messages:
                        if "⚠️ Найдена панель >1200" in msg or "🔧" in msg or "🗑️" in msg or "🎯" in msg:
                            self._log(f"   {msg}")
            else:
                self._log("ℹ️ Нет файлов для исправления или изменений не требуется")
                
            if stats['errors'] > 0:
                self._log(f"⚠️ Ошибок: {stats['errors']}")
                
        except Exception as e:
            self._log(f"❌ Ошибка при исправлении .SCX: {e}")
        finally:
            self.progress_bar.setVisible(False)
            self.status_label.setText("Готов к работе")
            
    def _on_fix_pgmx(self):
        """Обработчик кнопки исправления .PGMX файлов."""
        folder = getattr(self, '_current_folder', None)
        if not folder:
            self._log("\n⚠️ Нет выбранной папки! Сначала выберите папку.")
            return
            
        # Проверяем загружена ли база инструментов
        tool_db = global_tool_db
        if tool_db is None or not tool_db.tools:
            self._log("\n⚠️ База инструментов не загружена! Укажите путь к def.tlgx в настройках.")
            return
            
        e007_id = global_tool_db.get_replacement_tool("E007")
        if not e007_id:
            self._log("\n⚠️ Инструмент E007 не найден в базе!")
            return
            
        self._log(f"\n{'='*60}")
        self._log(f"⚙️ ЗАПУСК ИСПРАВЛЕНИЯ .PGMX")
        self._log(f"{'='*60}")
        
        self.status_label.setText("Исправление .PGMX файлов...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        
        try:
            stats = self.processor.fix_pgmx_batch()
            
            self._log(f"\n✅ Исправление .PGMX завершено!")
            if stats['processed'] > 0:
                self._log(f"🎉 Исправлено файлов: {stats['processed']}")
                self._log(f"   - Инструментов заменено на E007: {stats['tools_replaced']}")
            else:
                self._log("ℹ️ Нет файлов для исправления или изменений не требуется")
                
            if stats['errors'] > 0:
                self._log(f"⚠️ Ошибок: {stats['errors']}")
                
        except Exception as e:
            self._log(f"❌ Ошибка при исправлении .PGMX: {e}")
        finally:
            self.progress_bar.setVisible(False)
            self.status_label.setText("Готов к работе")
            
    def _on_revert_dots(self):
        """Обработчик кнопки возврата точек."""
        folder = getattr(self, '_current_folder', None)
        if not folder:
            self._log("\n⚠️ Нет выбранной папки! Сначала выберите папку.")
            return
            
        self._log(f"\n{'='*60}")
        self._log(f"↩️ ВОЗВРАТ ТОЧЕК В .SCX")
        self._log(f"{'='*60}")
        
        self.status_label.setText("Возврат точек...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        
        try:
            stats = self.processor.revert_dots()
            
            self._log(f"\n✅ Возврат точек завершен!")
            self._log(f"\n📊 Результаты:")
            self._log(f"   Обработано файлов: {stats['processed']}")
            self._log(f"   Возвращено значений: {stats['reverted']}")
            if stats['errors'] > 0:
                self._log(f"   Ошибок: {stats['errors']}")
                
        except Exception as e:
            self._log(f"❌ Ошибка при возврате точек: {e}")
        finally:
            self.progress_bar.setVisible(False)
            self.status_label.setText("Готов к работе")
            
    def _on_compare_csv(self):
        """Обработчик кнопки сравнения PGMX с CSV (логика ZPT-TCHK.py)."""
        folder = getattr(self, '_current_folder', None)
        if not folder:
            self._log("\n⚠️ Нет выбранной папки! Сначала выберите папку.")
            return
        
        # Очищаем лог процессора перед новым запуском сравнения
        self.processor.log_messages.clear()
        
        self._log(f"\n{'='*60}")
        self._log(f"🔍 СРАВНЕНИЕ PGMX С CSV")
        self._log(f"{'='*60}")
        
        self.status_label.setText("Сравнение PGMX с CSV...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        
        try:
            stats = self.processor.compare_pgmx_csv()
            
            # Выводим все накопленные логи из процессора
            for msg in self.processor.log_messages:
                self._log(msg)
            
            self._log(f"\n✅ Сравнение завершено!")
                
        except Exception as e:
            self._log(f"❌ Ошибка при сравнении: {e}")
        finally:
            self.progress_bar.setVisible(False)
            self.status_label.setText("Готов к работе")
