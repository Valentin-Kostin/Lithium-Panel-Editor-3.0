"""
Утилиты для работы с ZIP-архивами (PGMX формат).
Атомарное сохранение, сохранение всех файлов архива.
"""

import zipfile
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class ZipUtils:
    """Утилиты для работы с ZIP-архивами."""
    
    @staticmethod
    def extract_all(zip_path: Path, dest_dir: Path) -> Dict[str, Path]:
        """
        Извлекает все файлы из ZIP-архива.
        
        Args:
            zip_path: Путь к ZIP-файлу.
            dest_dir: Папка для извлечения.
        
        Returns:
            Словарь {имя_в_архиве: путь_к_файлу}.
        """
        extracted = {}
        
        with zipfile.ZipFile(zip_path, 'r') as zf:
            for name in zf.namelist():
                zf.extract(name, dest_dir)
                extracted[name] = dest_dir / name
        
        logger.info(f"Извлечено {len(extracted)} файлов из {zip_path}")
        return extracted
    
    @staticmethod
    def read_xml_from_zip(zip_path: Path, xml_name: str) -> Tuple[Optional[bytes], Optional[str]]:
        """
        Читает XML файл из ZIP-архива.
        
        Args:
            zip_path: Путь к ZIP-файлу.
            xml_name: Имя XML файла внутри архива.
        
        Returns:
            Кортеж (содержимое, ошибка).
        """
        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                if xml_name not in zf.namelist():
                    return None, f"Файл {xml_name} не найден в архиве"
                
                content = zf.read(xml_name)
                return content, None
                
        except Exception as e:
            logger.error(f"Ошибка чтения XML из ZIP: {e}")
            return None, str(e)
    
    @staticmethod
    def replace_xml_in_zip(
        zip_path: Path,
        xml_name: str,
        xml_content: bytes,
        output_path: Optional[Path] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Заменяет XML файл внутри ZIP-архива, сохраняя остальные файлы.
        Реализует атомарное сохранение через временный файл.
        
        Args:
            zip_path: Путь к исходному ZIP-файлу.
            xml_name: Имя XML файла внутри архива.
            xml_content: Новое содержимое XML.
            output_path: Путь для сохранения (если None, перезаписывает исходный).
        
        Returns:
            Кортеж (успешно, ошибка).
        """
        temp_path = None
        
        try:
            # Создаём временный файл для атомарного сохранения
            if output_path is None:
                output_path = zip_path
                temp_path = Path(tempfile.mktemp(suffix='.pgmx.tmp'))
            else:
                temp_path = output_path.with_suffix(output_path.suffix + '.tmp')
            
            # Копируем оригинальный архив во временный файл
            shutil.copy2(zip_path, temp_path)
            
            # Открываем временный архив для модификации
            with zipfile.ZipFile(temp_path, 'a', zipfile.ZIP_DEFLATED) as zf:
                # Проверяем существует ли файл в архиве
                existing_names = zf.namelist()
                
                if xml_name in existing_names:
                    # Удаляем старый XML (zipfile не поддерживает прямую замену)
                    # Читаем все файлы кроме XML
                    all_contents = {}
                    with zipfile.ZipFile(temp_path, 'r') as zf_read:
                        for name in zf_read.namelist():
                            if name != xml_name:
                                all_contents[name] = zf_read.read(name)
                    
                    # Пересоздаём архив без старого XML
                    with zipfile.ZipFile(temp_path, 'w', zipfile.ZIP_DEFLATED) as zf_new:
                        for name, content in all_contents.items():
                            zf_new.writestr(name, content)
                        # Добавляем новый XML
                        zf_new.writestr(xml_name, xml_content)
                else:
                    # XML не существовал - добавляем новый
                    zf.writestr(xml_name, xml_content)
            
            # Атомарная замена
            if output_path == zip_path:
                # Резервная копия оригинала
                backup_path = zip_path.with_suffix(zip_path.suffix + '.bak')
                shutil.copy2(zip_path, backup_path)
                shutil.move(temp_path, zip_path)
                logger.info(f"ZIP обновлён: {zip_path} (резервная копия: {backup_path})")
            else:
                shutil.move(temp_path, output_path)
                logger.info(f"ZIP сохранён: {output_path}")
            
            return True, None
            
        except Exception as e:
            logger.error(f"Ошибка замены XML в ZIP: {e}")
            # Очищаем временный файл при ошибке
            if temp_path and temp_path.exists():
                try:
                    temp_path.unlink()
                except:
                    pass
            return False, str(e)
    
    @staticmethod
    def list_contents(zip_path: Path) -> list:
        """
        Получает список содержимого ZIP-архива.
        
        Args:
            zip_path: Путь к ZIP-файлу.
        
        Returns:
            Список имён файлов.
        """
        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                return zf.namelist()
        except Exception as e:
            logger.error(f"Ошибка чтения содержимого ZIP: {e}")
            return []
    
    @staticmethod
    def find_main_xml(zip_path: Path) -> Optional[str]:
        """
        Находит главный XML файл в PGMX архиве.
        
        Args:
            zip_path: Путь к ZIP-файлу.
        
        Returns:
            Имя XML файла или None.
        """
        priority_names = [
            'main.xml',
            'program.xml',
            'data.xml',
            'content.xml',
            'project.xml'
        ]
        
        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                names = zf.namelist()
                
                # Сначала ищем по приоритетным именам
                for priority in priority_names:
                    if priority in names:
                        return priority
                
                # Затем ищем любой XML в корне
                for name in names:
                    if name.endswith('.xml') and '/' not in name:
                        return name
                
                # Если не найдено в корне, ищем любой XML
                for name in names:
                    if name.endswith('.xml'):
                        return name
                
        except Exception as e:
            logger.error(f"Ошибка поиска XML в ZIP: {e}")
        
        return None
