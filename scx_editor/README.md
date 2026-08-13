# SCX Editor - Редактор файлов NANXING

Приложение для редактирования XML-файлов `.SCX`, предназначенных для станков с ЧПУ производства **NANXING** (Guangdong Nanxing Equipment Co., Ltd).

## Возможности

- ✅ Открытие и просмотр XML-структуры файлов .SCX
- ✅ Редактирование параметров: размеры, координаты, инструменты, операции
- ✅ Отображение операций обработки в таблице
- ✅ Дерево XML-элементов с контекстным меню
- ✅ Резервное копирование перед сохранением
- ✅ Undo/Redo изменения
- ✅ Поддержка различных кодировок (UTF-8, GB18030, Windows-1251)
- ✅ Настраиваемый маппинг параметров через JSON
- ✅ Интерфейс на русском языке

## Требования

- Python 3.10 или новее
- Windows 10/11 (для GUI)
- Зависимости: PySide6, lxml, defusedxml, charset-normalizer

## Установка

### 1. Клонирование репозитория

```bash
git clone <repository-url>
cd scx_editor
```

### 2. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 3. Запуск приложения

```bash
python main.py
```

Или используйте `run.bat` на Windows.

## Структура проекта

```
scx_editor/
├── main.py                 # Точка входа
├── requirements.txt        # Зависимости
├── run.bat                 # Скрипт запуска
├── build_windows.bat       # Скрипт сборки
├── config/
│   ├── default_mapping.json  # Маппинг параметров по умолчанию
│   └── settings.json         # Настройки приложения
├── src/
│   ├── core/               # Основная логика
│   │   ├── scx_document.py
│   │   ├── xml_utils.py
│   │   ├── mapping.py
│   │   ├── validation.py
│   │   ├── diff.py
│   │   ├── backup.py
│   │   └── encoding_detector.py
│   ├── models/             # Модели данных
│   │   ├── tree_model.py
│   │   ├── operations_model.py
│   │   └── undo_commands.py
│   ├── ui/                 # GUI компоненты
│   │   ├── main_window.py
│   │   ├── xml_tree_view.py
│   │   ├── property_editor.py
│   │   ├── operations_table.py
│   │   ├── diff_dialog.py
│   │   ├── settings_dialog.py
│   │   └── status_bar.py
│   └── utils/              # Утилиты
│       ├── logger.py
│       └── paths.py
└── tests/                  # Тесты
```

## Сборка в Windows приложение

Для создания исполняемого файла:

```bash
build_windows.bat
```

Рекомендуется режим **onedir** (папка с приложением), так как он:
- Быстрее запускается
- Лучше работает с антивирусами
- Проще обновляется

Режим **onefile** (один exe) также доступен, но может быть медленнее.

## Как добавить поддержку конкретного формата .SCX

Если ваши файлы имеют специфическую структуру:

1. Откройте файл `config/default_mapping.json`
2. Добавьте новые поля в секцию `fields`:

```json
{
  "id": "custom.field",
  "label_ru": "Описание поля",
  "type": "float",
  "unit": "мм",
  "xpath": "//CustomElement/@Attribute"
}
```

3. При необходимости укажите namespace в секции `namespaces`

## Ограничения

- Приложение не отправляет данные на станок
- Не генерирует G-code
- Не выполняет постобработку файлов
- Только локальное редактирование XML

## Лицензия

Проект распространяется под лицензией LGPL (благодаря PySide6).

## Поддержка

Для вопросов и предложений создайте issue в репозитории.
