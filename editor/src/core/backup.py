"""
Модуль резервного копирования файлов.
"""

import logging
import shutil
from typing import Optional
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class BackupUtils:
    """Утилиты резервного копирования."""
    
    @staticmethod
    def create_backup(file_path: Path, backup_format: str = 'timestamp') -> Optional[Path]:
        """
        Создаёт резервную копию файла.
        
        Args:
            file_path: Путь к файлу.
            backup_format: Формат имени ('timestamp' или 'bak').
        
        Returns:
            Путь к копии или None при ошибке.
        """
        if not file_path.exists():
            logger.error(f"Файл не существует: {file_path}")
            return None
        
        try:
            if backup_format == 'timestamp':
                timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
                backup_name = f"{file_path.stem}_{timestamp}{file_path.suffix}.bak"
            else:
                backup_name = f"{file_path.name}.bak"
            
            backup_path = file_path.parent / backup_name
            
            counter = 1
            while backup_path.exists():
                if backup_format == 'timestamp':
                    backup_name = f"{file_path.stem}_{timestamp}_{counter}{file_path.suffix}.bak"
                else:
                    backup_name = f"{file_path.name}.{counter}.bak"
                backup_path = file_path.parent / backup_name
                counter += 1
            
            shutil.copy2(file_path, backup_path)
            logger.info(f"Резервная копия создана: {backup_path}")
            return backup_path
            
        except Exception as e:
            logger.error(f"Ошибка создания резервной копии: {e}")
            return None
    
    @staticmethod
    def restore_from_backup(backup_path: Path, original_path: Path) -> bool:
        """
        Восстанавливает файл из резервной копии.
        
        Args:
            backup_path: Путь к копии.
            original_path: Путь к оригиналу.
        
        Returns:
            True если успешно.
        """
        if not backup_path.exists():
            logger.error(f"Резервная копия не существует: {backup_path}")
            return False
        
        try:
            shutil.copy2(backup_path, original_path)
            logger.info(f"Файл восстановлен из копии: {original_path}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка восстановления из копии: {e}")
            return False
    
    @staticmethod
    def cleanup_old_backups(directory: Path, pattern: str = "*.bak", 
                            keep_count: int = 5) -> int:
        """
        Удаляет старые резервные копии.
        
        Args:
            directory: Директория для очистки.
            pattern: Шаблон имён файлов.
            keep_count: Сколько последних копий сохранить.
        
        Returns:
            Количество удалённых файлов.
        """
        try:
            backups = sorted(directory.glob(pattern), key=lambda p: p.stat().st_mtime)
            
            if len(backups) <= keep_count:
                return 0
            
            to_delete = backups[:-keep_count]
            deleted_count = 0
            
            for backup in to_delete:
                backup.unlink()
                logger.info(f"Удалена старая копия: {backup}")
                deleted_count += 1
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Ошибка очистки старых копий: {e}")
            return 0
