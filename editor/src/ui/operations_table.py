"""
Таблица операций для отображения и редактирования данных.
"""

from PySide6.QtWidgets import (
    QTableView, QHeaderView, QMenu, QStyledItemDelegate, QLineEdit,
    QDoubleSpinBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QDoubleValidator

from ..models.operations_model import OperationsTableModel


class NumericDelegate(QStyledItemDelegate):
    """
    Делегат для редактирования числовых значений в таблице.
    """

    def createEditor(self, parent, option, index):
        editor = QDoubleSpinBox(parent)
        editor.setDecimals(3)
        editor.setRange(-10000.0, 10000.0)
        editor.setSingleStep(0.1)
        editor.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        return editor

    def setEditorData(self, editor, index):
        value = index.data(Qt.DisplayRole)
        if value and value != "":
            try:
                editor.setValue(float(value))
            except (ValueError, TypeError):
                editor.setValue(0.0)
        else:
            editor.setValue(0.0)

    def setModelData(self, editor, model, index):
        if editor.value() == 0.0:
            # Пустое значение
            model.setData(index, None, Qt.EditRole)
        else:
            model.setData(index, editor.value(), Qt.EditRole)


class OperationsTableView(QTableView):
    """
    Виджет таблицы операций с поддержкой редактирования.
    """

    # Сигнал при выборе операции
    operation_selected = Signal(int)  # row

    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        """Настройка UI."""
        # Настройка внешнего вида
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QTableView.SelectRows)
        self.setSelectionMode(QTableView.SingleSelection)
        self.setSortingEnabled(True)
        self.setEditTriggers(QTableView.DoubleClicked | QTableView.SelectedClicked)
        
        # Установка делегата для числовых ячеек (колонки 4, 5, 6 - Z, Диаметр, Глубина)
        numeric_delegate = NumericDelegate(self)
        self.setItemDelegateForColumn(4, numeric_delegate)  # Z
        self.setItemDelegateForColumn(5, numeric_delegate)  # Диаметр
        self.setItemDelegateForColumn(6, numeric_delegate)  # Глубина

        # Настройка заголовков
        header = self.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # ID
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # Файл
        header.setSectionResizeMode(2, QHeaderView.Stretch)  # Имя
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Тип
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Z
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Диаметр
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)  # Глубина

        vertical_header = self.verticalHeader()
        vertical_header.setVisible(True)
        vertical_header.setDefaultSectionSize(28)

        # Контекстное меню
        self.setContextMenuPolicy(Qt.CustomContextMenu)

    def _connect_signals(self):
        """Подключение сигналов."""
        self.customContextMenuRequested.connect(self._show_context_menu)
        # Сигнал selectionModel будет подключен после установки модели

    def set_model(self, model: OperationsTableModel) -> None:
        """Установка модели."""
        self.setModel(model)
        # Подключаем сигнал только после установки модели
        sel_model = self.selectionModel()
        if sel_model is not None:
            sel_model.currentChanged.connect(self._on_selection_changed)

    def _on_selection_changed(self, current, previous):
        """Обработка изменения выделения."""
        if current.isValid():
            self.operation_selected.emit(current.row())

    def _show_context_menu(self, position):
        """Показ контекстного меню."""
        menu = QMenu(self)
        
        index = self.indexAt(position)
        if not index.isValid():
            return

        # Действие копирования XPath (TODO)
        copy_xpath_action = QAction("Копировать XPath", self)
        copy_xpath_action.triggered.connect(lambda: self._copy_xpath(index.row()))
        menu.addAction(copy_xpath_action)

        # Действие сброса изменений строки
        reset_action = QAction("Сбросить изменения строки", self)
        reset_action.triggered.connect(lambda: self._reset_row(index.row()))
        menu.addAction(reset_action)

        menu.exec_(self.viewport().mapToGlobal(position))

    def _copy_xpath(self, row: int) -> None:
        """Копирование XPath элемента в буфер обмена."""
        # TODO: Реализовать получение XPath из модели
        pass

    def _reset_row(self, row: int) -> None:
        """Сброс изменений в строке."""
        model = self.model()
        if isinstance(model, OperationsTableModel):
            operation = model.get_operation_at(row)
            if operation:
                # TODO: Восстановление оригинальных значений
                operation.is_modified = False
                model.dataChanged.emit(
                    model.index(row, 0),
                    model.index(row, model.columnCount() - 1),
                    [Qt.BackgroundRole]
                )

    def get_selected_row(self) -> int:
        """Получение индекса выбранной строки."""
        selection_model = self.selectionModel()
        if selection_model.hasSelection():
            return selection_model.currentIndex().row()
        return -1

    def select_row(self, row: int) -> None:
        """Выделение строки по индексу."""
        if 0 <= row < self.model().rowCount():
            index = self.model().index(row, 0)
            self.selectionModel().setCurrentIndex(
                index,
                QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows
            )
