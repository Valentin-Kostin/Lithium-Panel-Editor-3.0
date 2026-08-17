import os
import json
from pathlib import Path
from PySide6.QtCore import QStandardPaths

class Settings:
    """Управление настройками приложения"""
    
    CONFIG_DIR = Path(QStandardPaths.writableLocation(QStandardPaths.AppConfigLocation)) / "LithiumEditor"
    SETTINGS_FILE = CONFIG_DIR / "settings.json"
    
    DEFAULT_KEYS = {
        "tool_db_path": ""
    }
    
    def __init__(self):
        self._ensure_config_dir()
        self._settings = self._load_settings()
    
    def _ensure_config_dir(self):
        """Создает директорию конфигурации если она не существует"""
        self.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    
    def _load_settings(self) -> dict:
        """Загружает настройки из JSON файла"""
        if self.SETTINGS_FILE.exists():
            try:
                with open(self.SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Merge with defaults to ensure all keys exist
                    return {**self.DEFAULT_KEYS, **data}
            except (json.JSONDecodeError, IOError):
                return self.DEFAULT_KEYS.copy()
        return self.DEFAULT_KEYS.copy()
    
    def save_settings(self):
        """Сохраняет текущие настройки в JSON файл"""
        try:
            with open(self.SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self._settings, f, indent=4, ensure_ascii=False)
        except IOError as e:
            print(f"Error saving settings: {e}")
    
    def get_tool_db_path(self) -> str:
        return self._settings.get("tool_db_path", "")
    
    def set_tool_db_path(self, path: str):
        self._settings["tool_db_path"] = path
        self.save_settings()
