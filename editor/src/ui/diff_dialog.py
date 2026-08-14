"""
Диалог отображения изменений (diff).
"""

import logging

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QTextEdit, QPushButton, 
    QLabel, QDialogButtonBox
)
from PySide6.QtCore import Qt

from ..core.diff import Change, DiffUtils

logger = logging.getLogger(__name__)


class DiffDialog(QDialog):
    """Диалог отображения изменений."""
    
    def __init__(self, changes: list[Change], parent=None):
        super().__init__(parent)
        self.changes = changes
        
        self.setWindowTitle("Изменения")
        self.setMinimumSize(500, 400)
        
        self._init_ui()
    
    def _init_ui(self):
        """Инициализирует UI."""
        layout = QVBoxLayout(self)
        
        label = QLabel("Список изменений:")
        layout.addWidget(label)
        
        self._text_edit = QTextEdit()
        self._text_edit.setReadOnly(True)
        self._text_edit.setFontFamily("Consolas")
        layout.addWidget(self._text_edit)
        
        if not self.changes:
            self._text_edit.setText("Изменений нет.")
        else:
            text = ""
            for i, change in enumerate(self.changes, 1):
                text += f"#{i}\n"
                text += DiffUtils.format_change_for_display(change, 'ru')
                text += "\n" + "-"*40 + "\n"
            
            self._text_edit.setText(text)
        
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok
        )
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)
