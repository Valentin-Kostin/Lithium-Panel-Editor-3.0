# Editor - Редактор файлов ЧПУ NANXING и SCM Group

Desktop-приложение для редактирования файлов числового программного управления (ЧПУ) форматов:

- **.SCX** — NANXING (Guangdong Nanxing Equipment Co., Ltd, Китай)

- **.PGMX** — SCM Group (XCam / Maestro, Италия)

## Возможности

### Общие

- ✅ Открытие и просмотр файлов обоих форматов
- ✅ Раздельные вкладки для каждого формата (данные не смешиваются)
- ✅ Редактирование параметров операций
- ✅ Просмотр XML-структуры в дереве
- ✅ Undo/Redo изменения
- ✅ Diff изменений перед сохранением
- ✅ Валидация данных
- ✅ Логирование действий

### Формат .SCX (NANXING)

- ✅ Поддержка различных кодировок (UTF-8, GB18030, Windows-1251)
- ✅ Настраиваемый маппинг параметров через JSON
- ✅ Сохранение с резервной копией

### Формат .PGMX (SCM Group)

- ✅ Автоматическая распаковка ZIP-архива
- ✅ Извлечение главного XML файла
- ✅ Сохранение всех файлов архива без изменений
- ✅ Атомарное сохранение через временный файл

## Требования

- Python 3.10 или новее
- Windows 10/11 (для GUI)
- Зависимости: PySide6, lxml, defusedxml, charset-normalizer

## Установка

### 1. Клонирование репозитория

```bash
git clone <repository-url>
cd editor
```

### 2. Создание виртуального окружения (рекомендуется)

```bash
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac
```

### 3. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 4. Запуск приложения

```bash
python editor/main.py
```

Или используйте `run.bat` на Windows.

## Структура проекта

```
editor/
├── main.py                 # Точка входа
├── requirements.txt        # Зависимости
├── build_windows.bat       # Скрипт сборки
├── run.bat                 # Скрипт запуска
├── README.md              # Документация
├── config/
│   ├── settings.json      # Настройки приложения
│   ├── nanxing_mapping.json  # Маппинг для SCX
│   └── scm_mapping.json   # Маппинг для PGMX
├── resources/
│   ├── icons/             # Иконки приложения
│   └── themes/
│       ├── light.qss      # Светлая тема
│       └── dark.qss       # Тёмная тема
├── src/
│   ├── __init__.py
│   ├── app.py             # Приложение QApplication
│   ├── core/
│   │   ├── base_handler.py    # Базовый класс формата
│   │   ├── scx_document.py    # Обработка SCX
│   │   ├── pgmx_handler.py    # Обработка PGMX
│   │   ├── zip_utils.py       # Утилиты ZIP
│   │   ├── folder_scanner.py  # Сканирование папок
│   │   ├── xml_utils.py       # Работа с XML
│   │   ├── encoding_detector.py  # Определение кодировки
│   │   ├── mapping.py         # Маппинг параметров
│   │   ├── validation.py      # Валидация
│   │   ├── diff.py            # Сравнение изменений
│   │   └── backup.py          # Резервное копирование
│   ├── models/
│   │   ├── tree_model.py      # Модель дерева XML
│   │   ├── operations_model.py # Модель таблицы операций
│   │   └── undo_commands.py   # Команды Undo/Redo
│   ├── ui/
│   │   ├── main_window.py     # Главное окно
│   │   ├── format_tab.py      # Вкладка формата
│   │   ├── operations_table.py # Таблица операций
│   │   ├── xml_tree_view.py   # Дерево XML
│   │   ├── property_editor.py # Редактор свойств
│   │   ├── diff_dialog.py     # Диалог Diff
│   │   ├── settings_dialog.py # Настройки
│   │   └── status_bar.py      # Статусная строка
│   └── utils/
│       ├── logger.py          # Логирование
│       └── paths.py           # Пути
├── tests/
│   ├── test_pgmx_handler.py
│   ├── test_scx_handler.py
│   └── samples/
└── logs/
```

## Конфигурация

### Настройки (config/settings.json)

```json
{
  "auto_backup": false,
  "theme": "light",
  "language": "ru",
  "show_xml_tree": true,
  "nanxing_mapping_path": "config/nanxing_mapping.json",
  "scm_mapping_path": "config/scm_mapping.json"
}
```

### Маппинг параметров

Для адаптации к различным версиям форматов используются JSON-файлы маппинга:

- `nanxing_mapping.json` — правила извлечения параметров для SCX
- `scm_mapping.json` — правила извлечения параметров для PGMX

## Сборка в EXE

```bash
build_windows.bat
```

Приложение будет создано в папке `dist/Editor/`.

## Архитектура

Приложение построено по принципу **Strategy pattern**:

- `BaseFormatHandler` — абстрактный базовый класс
- `SCXDocument` — реализация для NANXING
- `PgmxFormatHandler` — реализация для SCM Group

Общий пайплайн обработки:

1. **SCAN** — поиск файлов в папке
2. **OPEN** — чтение/распаковка
3. **PARSE** — парсинг XML
4. **EXTRACT** — извлечение параметров
5. **DISPLAY** — отображение в GUI
6. **EDIT** — редактирование пользователем
7. **VALIDATE** — проверка данных
8. **DIFF** — показ изменений
9. **SAVE** — сохранение с атомарностью

## Лицензия

MIT License

## Контакты

Editor Team
