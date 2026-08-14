"""
Модуль сканирования папок на наличие файлов CNC форматов.
Поддерживает рекурсивное сканирование и фильтрацию по расширениям.
"""

import logging
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class FileInfo:
    """Информация о найденном файле."""
    path: Path
    format_type: str  # 'PGMX' или 'SCX'
    size: int
    modified: datetime
    is_valid: bool = True
    error_message: Optional[str] = None


class FolderScanner:
    """Сканер папок для поиска CNC файлов."""
    
    SUPPORTED_EXTENSIONS = {
        '.pgmx': 'PGMX',
        '.scx': 'SCX',
    }
    
    def __init__(self, recursive: bool = False):
        """
        Инициализирует сканер.
        
        Args:
            recursive: Рекурсивно сканировать подпапки.
        """
        self.recursive = recursive
    
    def scan(self, folder_path: Path) -> Dict[str, List[FileInfo]]:
        """
        Сканирует папку на наличие CNC файлов.
        
        Args:
            folder_path: Путь к папке для сканирования.
        
        Returns:
            Словарь {'PGMX': [...], 'SCX': [...]} со списками FileInfo.
        """
        results = {
            'PGMX': [],
            'SCX': []
        }
        
        if not folder_path.exists():
            logger.error(f"Папка не существует: {folder_path}")
            return results
        
        if not folder_path.is_dir():
            logger.error(f"Путь не является папкой: {folder_path}")
            return results
        
        # Определяем метод обхода
        if self.recursive:
            files = folder_path.rglob('*')
        else:
            files = folder_path.iterdir()
        
        for file_path in files:
            if not file_path.is_file():
                continue
            
            ext = file_path.suffix.lower()
            
            if ext in self.SUPPORTED_EXTENSIONS:
                format_type = self.SUPPORTED_EXTENSIONS[ext]
                
                try:
                    stat = file_path.stat()
                    file_info = FileInfo(
                        path=file_path,
                        format_type=format_type,
                        size=stat.st_size,
                        modified=datetime.fromtimestamp(stat.st_mtime),
                        is_valid=True
                    )
                    results[format_type].append(file_info)
                    
                except Exception as e:
                    logger.warning(f"Ошибка чтения файла {file_path}: {e}")
                    file_info = FileInfo(
                        path=file_path,
                        format_type=format_type,
                        size=0,
                        modified=datetime.now(),
                        is_valid=False,
                        error_message=str(e)
                    )
                    results[format_type].append(file_info)
        
        # Сортируем по имени
        for format_type in results:
            results[format_type].sort(key=lambda x: x.path.name)
        
        total = sum(len(files) for files in results.values())
        logger.info(f"Найдено {total} файлов: PGMX={len(results['PGMX'])}, SCX={len(results['SCX'])}")
        
        return results
    
    @staticmethod
    def validate_pgmx(file_path: Path) -> tuple[bool, Optional[str]]:
        """
        Проверяет валидность PGMX файла (ZIP архив).
        
        Args:
            file_path: Путь к файлу.
        
        Returns:
            Кортеж (валиден, сообщение об ошибке).
        """
        import zipfile
        
        try:
            with zipfile.ZipFile(file_path, 'r') as zf:
                # Проверяем что внутри есть XML
                names = zf.namelist()
                has_xml = any(name.endswith('.xml') for name in names)
                
                if not has_xml:
                    return False, "В архиве нет XML файлов"
                
                return True, None
                
        except zipfile.BadZipFile as e:
            return False, f"Некорректный ZIP архив: {e}"
        except Exception as e:
            return False, f"Ошибка проверки: {e}"
    
    @staticmethod
    def validate_scx(file_path: Path) -> tuple[bool, Optional[str]]:
        """
        Проверяет валидность SCX файла (XML).
        
        Args:
            file_path: Путь к файлу.
        
        Returns:
            Кортеж (валиден, сообщение об ошибке).
        """
        from lxml import etree
        
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            
            # Пробуем распарсить как XML
            etree.fromstring(content)
            return True, None
            
        except etree.XMLSyntaxError as e:
            return False, f"XML синтаксическая ошибка: {e}"
        except Exception as e:
            return False, f"Ошибка проверки: {e}"
