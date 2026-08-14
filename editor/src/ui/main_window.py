"""
Главное окно приложения.
Содержит вкладки для SCM (.PGMX) и NANXING (.SCX) форматов.
"""

import logging
from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QToolBar, QStatusBar, QLabel, QMessageBox, QFileDialog
)
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QAction, QIcon

from ..core.pgmx_handler import PgmxFormatHandler
from ..core.scx_handler import ScxFormatHandler
from .format_tab import FormatTab

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """
    Главное окно приложения Lithium Panel Editor.
    """

    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("Lithium Panel Editor 3.0")
        self.setMinimumSize(1024, 768)
        
        # Инициализация обработчиков форматов
        self.pgmx_handler = PgmxFormatHandler()
        self.scx_handler = ScxFormatHandler()
        
        # Вкладки
        self.tabs = QTabWidget()
        
        # Создание вкладок форматов
        self.scm_tab = FormatTab(self.pgmx_handler, self)
        self.nanxing_tab = FormatTab(self.scx_handler, self)
        
        self.tabs.addTab(self.scm_tab, "🇮🇹 SCM (.PGMX)")
        self.tabs.addTab(self.nanxing_tab, "🇨🇳 NANXING (.SCX)")
        
        self.setCentralWidget(self.tabs)
        
        self._setup_ui()
        self._create_actions()
        self._create_toolbar()
        self._create_statusbar()
        self._connect_signals()

    def _setup_ui(self):
        """Настройка UI."""
        # Центральная виджет уже установлен (tabs)
        pass

    def _create_actions(self):
        """Создание действий меню."""
        # Меню Файл
        self.open_folder_action = QAction("📁 Открыть папку", self)
        self.open_folder_action.setShortcut("Ctrl+O")
        self.open_folder_action.setToolTip("Открыть папку со сканированием файлов")
        
        self.save_all_action = QAction("💾 Сохранить всё", self)
        self.save_all_action.setShortcut("Ctrl+S")
        self.save_all_action.setToolTip("Сохранить все изменённые файлы")
        
        self.exit_action = QAction("Выход", self)
        self.exit_action.setShortcut("Ctrl+Q")
        self.exit_action.setToolTip("Закрыть приложение")
        
        # Меню Правка
        self.undo_action = QAction("↶ Отменить", self)
        self.undo_action.setShortcut("Ctrl+Z")
        self.undo_action.setEnabled(False)  # TODO
        
        self.redo_action = QAction("↷ Повторить", self)
        self.redo_action.setShortcut("Ctrl+Y")
        self.redo_action.setEnabled(False)  # TODO
        
        # Меню Помощь
        self.about_action = QAction("О программе", self)
        self.about_action.setToolTip("Информация о приложении")

    def _create_toolbar(self):
        """Создание панели инструментов."""
        toolbar = QToolBar("Основная панель")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        
        toolbar.addAction(self.open_folder_action)
        toolbar.addAction(self.save_all_action)
        toolbar.addSeparator()
        toolbar.addAction(self.undo_action)
        toolbar.addAction(self.redo_action)
        toolbar.addSeparator()
        toolbar.addAction(self.about_action)

    def _create_statusbar(self):
        """Создание статус-бара."""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        
        # Метки статуса
        self.status_label = QLabel("Готов")
        self.statusbar.addWidget(self.status_label, 1)
        
        self.files_count_label = QLabel("")
        self.statusbar.addPermanentWidget(self.files_count_label)
        
        self.modified_label = QLabel("")
        self.statusbar.addPermanentWidget(self.modified_label)

    def _connect_signals(self):
        """Подключение сигналов."""
        # Меню
        self.open_folder_action.triggered.connect(self._on_open_folder)
        self.save_all_action.triggered.connect(self._on_save_all)
        self.exit_action.triggered.connect(self.close)
        self.about_action.triggered.connect(self._show_about)
        
        # Сигналы от вкладок
        self.scm_tab.files_loaded.connect(self._on_files_loaded_scm)
        self.scm_tab.modifications_changed.connect(self._on_modifications_changed_scm)
        self.scm_tab.status_message.connect(self._on_status_message)
        
        self.nanxing_tab.files_loaded.connect(self._on_files_loaded_nanxing)
        self.nanxing_tab.modifications_changed.connect(self._on_modifications_changed_nanxing)
        self.nanxing_tab.status_message.connect(self._on_status_message)
        
        # Переключение вкладок
        self.tabs.currentChanged.connect(self._on_tab_changed)

    @Slot()
    def _on_open_folder(self):
        """Обработка открытия папки с текущей вкладки."""
        current_tab = self.tabs.currentWidget()
        if current_tab == self.scm_tab:
            self.scm_tab.open_folder_btn.click()
        elif current_tab == self.nanxing_tab:
            self.nanxing_tab.open_folder_btn.click()

    @Slot()
    def _on_save_all(self):
        """Сохранение всех изменённых файлов на текущей вкладке."""
        current_tab = self.tabs.currentWidget()
        saved_count = 0
        
        if current_tab == self.scm_tab:
            saved_count = self.scm_tab.save_all()
        elif current_tab == self.nanxing_tab:
            saved_count = self.nanxing_tab.save_all()
        
        if saved_count > 0:
            self._on_status_message(f"Сохранено файлов: {saved_count}")
        else:
            self._on_status_message("Нет изменений для сохранения")

    @Slot(int)
    def _on_files_loaded_scm(self, count: int):
        """Обработка загрузки файлов SCM."""
        self.files_count_label.setText(f"SCM: {count}")

    @Slot(int)
    def _on_files_loaded_nanxing(self, count: int):
        """Обработка загрузки файлов NANXING."""
        self.files_count_label.setText(f"NANXING: {count}")

    @Slot(bool)
    def _on_modifications_changed_scm(self, has_changes: bool):
        """Обработка изменений на вкладке SCM."""
        if has_changes:
            self.modified_label.setText("⚠ Есть несохранённые изменения (SCM)")
            self.modified_label.setStyleSheet("color: orange; font-weight: bold;")
        else:
            self.modified_label.setText("")

    @Slot(bool)
    def _on_modifications_changed_nanxing(self, has_changes: bool):
        """Обработка изменений на вкладке NANXING."""
        if has_changes:
            self.modified_label.setText("⚠ Есть несохранённые изменения (NANXING)")
            self.modified_label.setStyleSheet("color: orange; font-weight: bold;")
        else:
            self.modified_label.setText("")

    @Slot(str)
    def _on_status_message(self, message: str):
        """Показ сообщения в статус-баре."""
        self.status_label.setText(message)
        logger.info(f"Status: {message}")

    @Slot(int)
    def _on_tab_changed(self, index: int):
        """Обработка переключения вкладки."""
        tab_name = self.tabs.tabText(index)
        self._on_status_message(f"Вкладка: {tab_name}")
        
        # Обновление кнопок тулбара для текущей вкладки
        has_changes = False
        if index == 0:
            has_changes = self.scm_tab.has_unsaved_changes()
        elif index == 1:
            has_changes = self.nanxing_tab.has_unsaved_changes()
        
        self.save_all_action.setEnabled(has_changes)

    @Slot()
    def _show_about(self):
        """Показ диалога 'О программе'."""
        QMessageBox.about(
            self,
            "О программе",
            "<h2>Lithium Panel Editor 3.0</h2>"
            "<p>Приложение для редактирования параметров обработки "
            "в файлах форматов:</p>"
            "<ul>"
            "<li><b>.PGMX</b> — SCM Group (XCam / Maestro), Италия</li>"
            "<li><b>.SCX</b> — NANXING (Guangdong Nanxing Equipment), Китай</li>"
            "</ul>"
            "<p>Версия: 3.0</p>"
            "<p>Python + PySide6</p>"
        )

    def closeEvent(self, event):
        """Обработка закрытия окна."""
        # Проверка несохранённых изменений
        has_unsaved = (
            self.scm_tab.has_unsaved_changes() or
            self.nanxing_tab.has_unsaved_changes()
        )
        
        if has_unsaved:
            reply = QMessageBox.question(
                self,
                "Несохранённые изменения",
                "Есть несохранённые изменения. Закрыть приложение?",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
            )
            
            if reply == QMessageBox.Cancel:
                event.ignore()
                return
            elif reply == QMessageBox.No:
                event.ignore()
                return
        
        event.accept()
        logger.info("Приложение закрыто")
