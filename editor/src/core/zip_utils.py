"""
Утилиты для работы с ZIP-архивами (для формата PGMX).
"""

import zipfile
import tempfile
import shutil
from pathlib import Path
from typing import Optional, Tuple, Dict
import logging

logger = logging.getLogger(__name__)


def extract_xml_from_zip(
    zip_path: Path,
    xml_filename: Optional[str] = None
) -> Tuple[bytes, str, Dict[str, bytes]]:
    """
    Извлечение XML файла из ZIP-архива.

    Args:
        zip_path: Путь к ZIP-файлу.
        xml_filename: Имя XML файла внутри архива (если None, ищется первый .xml).

    Returns:
        Кортеж (xml_content_bytes, xml_filename, other_files_dict).

    Raises:
        ValueError: Если XML файл не найден.
        zipfile.BadZipFile: Если файл не является корректным ZIP.
    """
    if not zip_path.exists():
        raise FileNotFoundError(f"ZIP-файл не найден: {zip_path}")

    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            # Поиск XML файла
            if xml_filename:
                if xml_filename not in zf.namelist():
                    raise ValueError(f"Файл {xml_filename} не найден в архиве")
            else:
                # Поиск первого XML файла с namespace SCM
                xml_files = [
                    name for name in zf.namelist()
                    if name.endswith('.xml') and 'project' in name.lower()
                ]
                if not xml_files:
                    xml_files = [name for name in zf.namelist() if name.endswith('.xml')]
                
                if not xml_files:
                    raise ValueError("XML файл не найден в архиве")
                xml_filename = xml_files[0]

            # Чтение XML файла
            xml_content = zf.read(xml_filename)

            # Чтение остальных файлов
            other_files = {}
            for name in zf.namelist():
                if name != xml_filename:
                    other_files[name] = zf.read(name)

            logger.debug(f"Извлечён XML из ZIP: {xml_filename}, других файлов: {len(other_files)}")
            return xml_content, xml_filename, other_files

    except zipfile.BadZipFile as e:
        logger.error(f"Некорректный ZIP-файл {zip_path}: {e}")
        raise zipfile.BadZipFile(f"Некорректный ZIP-файл: {zip_path}")


def update_xml_in_zip(
    zip_path: Path,
    xml_filename: str,
    xml_content: bytes,
    other_files: Dict[str, bytes],
    output_path: Optional[Path] = None
) -> Path:
    """
    Обновление XML файла внутри ZIP-архива.

    Args:
        zip_path: Путь к исходному ZIP-файлу.
        xml_filename: Имя XML файла внутри архива.
        xml_content: Новое содержимое XML файла.
        other_files: Словарь остальных файлов архива.
        output_path: Путь для сохранения (если None, перезаписывается исходный файл).

    Returns:
        Путь к сохранённому ZIP-файлу.

    Raises:
        IOError: Если ошибка записи.
    """
    target_path = output_path or zip_path
    temp_path = None

    try:
        # Создание временного файла для атомарной записи
        if target_path == zip_path:
            temp_fd, temp_path = tempfile.mkstemp(suffix='.pgmx.tmp')
            import os
            os.close(temp_fd)
            temp_path = Path(temp_path)
        else:
            temp_path = target_path.with_suffix('.tmp')

        # Запись нового ZIP
        with zipfile.ZipFile(temp_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Запись обновлённого XML
            zf.writestr(xml_filename, xml_content)

            # Запись остальных файлов
            for filename, content in other_files.items():
                zf.writestr(filename, content)

        # Атомарное перемещение
        if target_path == zip_path:
            temp_path.replace(zip_path)
            logger.info(f"ZIP обновлён: {zip_path}")
        else:
            temp_path.replace(target_path)
            logger.info(f"ZIP сохранён: {target_path}")

        return target_path

    except Exception as e:
        logger.error(f"Ошибка обновления ZIP {zip_path}: {e}")
        # Очистка временного файла при ошибке
        if temp_path and temp_path.exists():
            try:
                temp_path.unlink()
            except Exception:
                pass
        raise IOError(f"Ошибка обновления ZIP-файла: {e}")

    finally:
        # Очистка временного файла если он ещё существует
        if temp_path and temp_path.exists() and target_path != zip_path:
            try:
                temp_path.unlink()
            except Exception:
                pass


def is_zip_file(file_path: Path) -> bool:
    """
    Проверка, является ли файл ZIP-архивом.

    Args:
        file_path: Путь к файлу.

    Returns:
        True если файл является ZIP-архивом.
    """
    if not file_path.exists():
        return False

    try:
        with zipfile.ZipFile(file_path, 'r') as zf:
            # Проверка на корректность ZIP
            zf.testzip()
            return True
    except Exception:
        return False


def get_zip_contents(zip_path: Path) -> list:
    """
    Получение списка файлов внутри ZIP-архива.

    Args:
        zip_path: Путь к ZIP-файлу.

    Returns:
        Список имён файлов в архиве.
    """
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            return zf.namelist()
    except Exception as e:
        logger.error(f"Ошибка чтения содержимого ZIP {zip_path}: {e}")
        return []
