"""
Диалог показа различий (Diff) перед сохранением.
"""

from typing import Dict, Any, List
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTextEdit, QGroupBox, QScrollArea, QWidget
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


class DiffDialog(QDialog):
    """
    Диалог для отображения изменений перед сохранением.
    """

    def __init__(self, diff_data: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.diff_data = diff_data
        self._setup_ui()

    def _setup_ui(self):
        """Настройка UI."""
        self.setWindowTitle("Изменения перед сохранением")
        self.setMinimumSize(600, 400)
        self.setModal(True)

        layout = QVBoxLayout(self)

        # Заголовок
        title_label = QLabel("Следующие изменения будут сохранены:")
        title_label.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(title_label)

        # Scroll area для содержимого
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        # Изменения операций
        if 'operations_changed' in self.diff_data and self.diff_data['operations_changed']:
            ops_group = QGroupBox(f"Изменения операций ({len(self.diff_data['operations_changed'])})")
            ops_layout = QVBoxLayout()

            for change in self.diff_data['operations_changed'][:20]:  # Максимум 20 для производительности
                op_text = self._format_operation_change(change)
                text_edit = QTextEdit()
                text_edit.setPlainText(op_text)
                text_edit.setReadOnly(True)
                text_edit.setMaximumHeight(80)
                text_edit.setFont(QFont("Consolas", 9))
                ops_layout.addWidget(text_edit)

            if len(self.diff_data['operations_changed']) > 20:
                more_label = QLabel(f"... и ещё {len(self.diff_data['operations_changed']) - 20} операций")
                more_label.setStyleSheet("color: gray;")
                ops_layout.addWidget(more_label)

            ops_group.setLayout(ops_layout)
            scroll_layout.addWidget(ops_group)

        # Изменения параметров заготовки
        if 'workpiece_changed' in self.diff_data and self.diff_data['workpiece_changed']:
            wp_group = QGroupBox("Изменения параметров заготовки")
            wp_layout = QVBoxLayout()

            wp_changes = self.diff_data['workpiece_changed']
            wp_text = self._format_workpiece_change(wp_changes)
            text_edit = QTextEdit()
            text_edit.setPlainText(wp_text)
            text_edit.setReadOnly(True)
            text_edit.setMaximumHeight(150)
            text_edit.setFont(QFont("Consolas", 9))
            wp_layout.addWidget(text_edit)

            wp_group.setLayout(wp_layout)
            scroll_layout.addWidget(wp_group)

        # Если нет изменений
        if not self.diff_data.get('has_changes', False):
            no_changes_label = QLabel("Нет изменений для сохранения.")
            no_changes_label.setStyleSheet("color: green; font-weight: bold;")
            scroll_layout.addWidget(no_changes_label)

        scroll_area.setWidget(scroll_widget)
        layout.addWidget(scroll_area)

        # Кнопки
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.save_button = QPushButton("Сохранить")
        self.save_button.clicked.connect(self.accept)
        self.save_button.setEnabled(self.diff_data.get('has_changes', False))
        button_layout.addWidget(self.save_button)

        self.cancel_button = QPushButton("Отмена")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)

        layout.addLayout(button_layout)

    def _format_operation_change(self, change: Dict[str, Any]) -> str:
        """Форматирование текста изменения операции."""
        lines = [
            f"Операция #{change['id']}: {change['name']}",
            ""
        ]

        orig = change.get('original', {})
        mod = change.get('modified', {})

        for field in ['x', 'y', 'z', 'diameter', 'depth']:
            orig_val = orig.get(field)
            mod_val = mod.get(field)
            
            if orig_val != mod_val:
                orig_str = f"{orig_val:.3f}" if orig_val is not None else "N/A"
                mod_str = f"{mod_val:.3f}" if mod_val is not None else "N/A"
                lines.append(f"  {field.upper()}: {orig_str} → {mod_str}")

        return "\n".join(lines)

    def _format_workpiece_change(self, wp_changes: Dict[str, Any]) -> str:
        """Форматирование текста изменения параметров заготовки."""
        lines = ["Параметры заготовки:", ""]

        orig = wp_changes.get('original', {})
        mod = wp_changes.get('modified', {})

        all_keys = set(orig.keys()) | set(mod.keys())
        for key in sorted(all_keys):
            orig_val = orig.get(key)
            mod_val = mod.get(key)
            
            if orig_val != mod_val:
                orig_str = f"{orig_val:.3f}" if isinstance(orig_val, float) else str(orig_val)
                mod_str = f"{mod_val:.3f}" if isinstance(mod_val, float) else str(mod_val)
                lines.append(f"  {key}: {orig_str} → {mod_str}")

        return "\n".join(lines)

    @staticmethod
    def show_diff(diff_data: Dict[str, Any], parent=None) -> bool:
        """
        Статический метод для показа диалога и получения результата.

        Returns:
            True если пользователь нажал "Сохранить", False если "Отмена".
        """
        dialog = DiffDialog(diff_data, parent)
        result = dialog.exec_()
        return result == QDialog.Accepted
