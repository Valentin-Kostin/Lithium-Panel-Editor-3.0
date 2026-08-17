"""
Главное окно приложения Lithium Panel Editor.
Новый интерфейс:
- Верхняя панель с кнопками управления
- Большое текстовое окно логов внизу
"""
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QTextEdit, QFileDialog, QLabel, QProgressBar,
    QGroupBox, QApplication
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
import os

from ..core.batch_processor import BatchProcessor
from ..core.tool_db import global_tool_db
from ..utils.settings import Settings


class MainWindow(QMainWindow):
    """Главное окно приложения с новым интерфейсом."""
    
    def __init__(self):
        super().__init__()
        self.processor = BatchProcessor()
        self.settings = Settings()
        self.setWindowTitle("Lithium Panel Editor v3.0")
        self.setMinimumSize(900, 700)
        
        self._setup_ui()
        self._connect_signals()
        
    def _setup_ui(self):
        """Создание интерфейса."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        # === ВЕРХНЯЯ ПАНЕЛЬ С КНОПКАМИ ===
        control_group = QGroupBox("🛠️ Панель управления")
        control_layout = QHBoxLayout(control_group)
        control_layout.setSpacing(10)
        
        # Кнопки
        self.btn_select_folder = QPushButton("📁 Выбрать папку")
        self.btn_select_folder.setToolTip("Выбрать папку с файлами .SCX, .PGMX, .CSV")
        self.btn_select_folder.setMinimumHeight(40)
        
        self.btn_load_tools = QPushButton("🔧 База инструментов")
        self.btn_load_tools.setToolTip("Загрузить файл def.tlgx с базой инструментов")
        self.btn_load_tools.setMinimumHeight(40)
        
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
        
        # Добавление кнопок в layout
        control_layout.addWidget(self.btn_select_folder)
        control_layout.addWidget(self.btn_load_tools)
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
        
        # === СБОРКА ИНТЕРФЕЙСА ===
        main_layout.addWidget(control_group)
        main_layout.addLayout(status_layout)
        main_layout.addWidget(log_group, stretch=1)  # Растягиваем лог
        
    def _connect_signals(self):
        """Подключение сигналов к слотам."""
        self.btn_select_folder.clicked.connect(self._on_select_folder)
        self.btn_load_tools.clicked.connect(self._on_load_tools)
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
                total_csv_parts = sum(stats['csv_parts'].values())
                self._log(f"   Всего записей в CSV: {total_csv_parts}")
                
                # Отсутствующие PGMX
                if stats['missing_pgmx']:
                    self._log(f"\n⚠️ Отсутствуют PGMX файлы для {len(stats['missing_pgmx'])} деталей:")
                    for name in stats['missing_pgmx'][:10]:
                        self._log(f"   - {name}")
                    if len(stats['missing_pgmx']) > 10:
                        self._log(f"   ... и еще {len(stats['missing_pgmx']) - 10}")
                        
                # OBOROT файлы
                if stats['oborot_files']:
                    self._log(f"\n⚠️ Найдено OBOROT файлов: {len(stats['oborot_files'])}:")
                    for name in stats['oborot_files'][:10]:
                        self._log(f"   - {name}")
                    if len(stats['oborot_files']) > 10:
                        self._log(f"   ... и еще {len(stats['oborot_files']) - 10}")
                        
                self._log(f"\n💡 Теперь можно нажать 'Исправить .SCX' или 'Править .PGMX'")
                
            except Exception as e:
                self._log(f"❌ Ошибка сканирования: {e}")
            finally:
                self.progress_bar.setVisible(False)
                self.status_label.setText("Готов к работе")
                
    def _on_load_tools(self):
        """Обработчик кнопки загрузки базы инструментов."""
        # Проверяем есть ли сохраненный путь
        saved_path = self.settings.get_tool_db_path()
        
        if saved_path and os.path.exists(saved_path):
            self._log(f"\n✅ Найден сохраненный путь к базе инструментов: {saved_path}")
            if self._load_tool_database(saved_path):
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
            
    def _on_fix_scx(self):
        """Обработчик кнопки исправления .SCX файлов."""
        folder = getattr(self, '_current_folder', None)
        if not folder:
            self._log("\n⚠️ Нет выбранной папки! Сначала выберите папку.")
            return
            
        self._log(f"\n{'='*60}")
        self._log(f"✏️ ЗАПУСК ИСПРАВЛЕНИЯ .SCX")
        self._log(f"{'='*60}")
        
        self.status_label.setText("Исправление .SCX файлов...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        
        try:
            stats = self.processor.fix_scx_batch()
            
            self._log(f"\n✅ Исправление .SCX завершено!")
            if stats['processed'] > 0:
                self._log(f"🎉 Исправлено файлов: {stats['processed']}")
                self._log(f"   - Отверстий Ø2.5 исправлено: {stats['holes_fixed']}")
                self._log(f"   - Панелей >1200 найдено: {stats['panels_found']}")
                self._log(f"   - Type=4 с запятыми: {stats['dots_replaced']}")
                self._log(f"   - Face=0 исправлено: {stats['face_fixed']}")
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
        """Обработчик кнопки сравнения PGMX с CSV."""
        folder = getattr(self, '_current_folder', None)
        if not folder:
            self._log("\n⚠️ Нет выбранной папки! Сначала выберите папку.")
            return
            
        self._log(f"\n{'='*60}")
        self._log(f"🔍 СРАВНЕНИЕ PGMX С CSV")
        self._log(f"{'='*60}")
        
        self.status_label.setText("Сравнение PGMX с CSV...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        
        try:
            stats = self.processor.compare_pgmx_csv()
            
            self._log(f"\n✅ Сравнение завершено!")
            self._log(f"\n📊 Результаты:")
            self._log(f"   Совпадений: {stats['matches']}")
            
            if stats['missing_in_csv']:
                self._log(f"\n⚠️ Есть в PGMX, но отсутствуют в CSV: {len(stats['missing_in_csv'])}")
            if stats['missing_in_pgmx']:
                self._log(f"\n⚠️ Есть в CSV, но отсутствуют в PGMX: {len(stats['missing_in_pgmx'])}")
                
        except Exception as e:
            self._log(f"❌ Ошибка при сравнении: {e}")
        finally:
            self.progress_bar.setVisible(False)
            self.status_label.setText("Готов к работе")
