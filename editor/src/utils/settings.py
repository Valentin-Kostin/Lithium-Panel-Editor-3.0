import os
import json
from pathlib import Path
from PySide6.QtCore import QStandardPaths

class Settings:
    """Управление настройками приложения"""
    
    CONFIG_DIR = Path(QStandardPaths.writableLocation(QStandardPaths.AppConfigLocation)) / "LithiumEditor"
    SETTINGS_FILE = CONFIG_DIR / "settings.json"
    
    DEFAULT_KEYS = {
        "tool_db_path": "",
        "theme": "Dark",
        "font_size": 10
    }
    
    THEMES = {
        "Dark": {
            "bg_primary": "#1e1e1e",
            "bg_secondary": "#2d2d2d",
            "bg_tertiary": "#3e3e3e",
            "text_primary": "#d4d4d4",
            "text_secondary": "#ffffff",
            "accent": "#4ecdc4",
            "border": "#3e3e3e",
            "gridline": "#3e3e3e"
        },
        "Light": {
            "bg_primary": "#ffffff",
            "bg_secondary": "#f5f5f5",
            "bg_tertiary": "#e0e0e0",
            "text_primary": "#1e1e1e",
            "text_secondary": "#000000",
            "accent": "#0078d4",
            "border": "#cccccc",
            "gridline": "#d0d0d0"
        },
        "Blue": {
            "bg_primary": "#0f172a",
            "bg_secondary": "#1e293b",
            "bg_tertiary": "#334155",
            "text_primary": "#e2e8f0",
            "text_secondary": "#f8fafc",
            "accent": "#38bdf8",
            "border": "#334155",
            "gridline": "#334155"
        },
        "Green": {
            "bg_primary": "#0c1a12",
            "bg_secondary": "#1a2f22",
            "bg_tertiary": "#2d4a3a",
            "text_primary": "#d1fae5",
            "text_secondary": "#f0fdf4",
            "accent": "#34d399",
            "border": "#2d4a3a",
            "gridline": "#2d4a3a"
        },
        "Purple": {
            "bg_primary": "#1a0f2e",
            "bg_secondary": "#2d1f4e",
            "bg_tertiary": "#4a3a6e",
            "text_primary": "#ede9fe",
            "text_secondary": "#f5f3ff",
            "accent": "#a78bfa",
            "border": "#4a3a6e",
            "gridline": "#4a3a6e"
        }
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
    
    def get_theme(self) -> str:
        return self._settings.get("theme", "Dark")
    
    def set_theme(self, theme: str):
        if theme in self.THEMES:
            self._settings["theme"] = theme
            self.save_settings()
    
    def get_font_size(self) -> int:
        return self._settings.get("font_size", 10)
    
    def set_font_size(self, size: int):
        self._settings["font_size"] = size
        self.save_settings()
    
    def get_theme_colors(self) -> dict:
        """Возвращает цвета текущей темы"""
        theme_name = self.get_theme()
        return self.THEMES.get(theme_name, self.THEMES["Dark"])
