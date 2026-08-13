"""
Диалог настроек приложения.
"""

import logging
import json

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QCheckBox,
    QLineEdit, QPushButton, QDialogButtonBox, 
    QFileDialog, QLabel, QComboBox
)
from PySide6.QtCore import Qt

logger = logging.getLogger(__name__)


class SettingsDialog(QDialog):
    """Диалог настроек."""
    
    def __init__(self, settings: dict, parent=None):
        super().__init__(parent)
        self.settings = settings.copy()
        
        self.setWindowTitle("Настройки")
        self.setMinimumSize(400, 300)
        
        self._init_ui()
        self._load_settings()
    
    def _init_ui(self):
        """Инициализирует UI."""
        layout = QVBoxLayout(self)
        
        form_layout = QFormLayout()
        
        self._auto_backup_check = QCheckBox("Автоматически создавать резервную копию")
        form_layout.addRow(self._auto_backup_check)
        
        self._backup_format_combo = QComboBox()
        self._backup_format_combo.addItem("Временная метка", "timestamp")
        self._backup_format_combo.addItem(".bak расширение", "bak")
        form_layout.addRow("Формат резервной копии:", self._backup_format_combo)
        
        self._detailed_xml_check = QCheckBox("Подробный режим XML")
        form_layout.addRow(self._detailed_xml_check)
        
        self._mapping_path_edit = QLineEdit()
        mapping_browse_btn = QPushButton("Обзор...")
        mapping_browse_btn.clicked.connect(self._browse_mapping)
        
        mapping_layout = QVBoxLayout()
        mapping_layout.addWidget(self._mapping_path_edit)
        mapping_layout.addWidget(mapping_browse_btn)
        form_layout.addRow("Путь к маппингу:", mapping_layout)
        
        self._language_combo = QComboBox()
        self._language_combo.addItem("Русский", "ru")
        self._language_combo.addItem("English", "en")
        form_layout.addRow("Язык:", self._language_combo)
        
        self._warn_delete_check = QCheckBox("Предупреждать перед удалением узлов")
        form_layout.addRow(self._warn_delete_check)
        
        layout.addLayout(form_layout)
        
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def _load_settings(self):
        """Загружает настройки в UI."""
        self._auto_backup_check.setChecked(self.settings.get('auto_backup', True))
        
        backup_format = self.settings.get('backup_format', 'timestamp')
        index = self._backup_format_combo.findData(backup_format)
        if index >= 0:
            self._backup_format_combo.setCurrentIndex(index)
        
        self._detailed_xml_check.setChecked(self.settings.get('detailed_xml_mode', False))
        self._mapping_path_edit.setText(self.settings.get('mapping_path', ''))
        
        language = self.settings.get('language', 'ru')
        index = self._language_combo.findData(language)
        if index >= 0:
            self._language_combo.setCurrentIndex(index)
        
        self._warn_delete_check.setChecked(self.settings.get('warn_on_delete', True))
    
    def _browse_mapping(self):
        """Открывает диалог выбора файла маппинга."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите файл маппинга",
            "",
            "JSON Files (*.json)"
        )
        if path:
            self._mapping_path_edit.setText(path)
    
    def get_settings(self) -> dict:
        """Получает обновлённые настройки."""
        return {
            'auto_backup': self._auto_backup_check.isChecked(),
            'backup_format': self._backup_format_combo.currentData(),
            'detailed_xml_mode': self._detailed_xml_check.isChecked(),
            'mapping_path': self._mapping_path_edit.text(),
            'language': self._language_combo.currentData(),
            'warn_on_delete': self._warn_delete_check.isChecked(),
        }
