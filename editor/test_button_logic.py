#!/usr/bin/env python3
"""Тест логики кнопки загрузки базы инструментов - без импорта UI"""

import sys
import os
sys.path.insert(0, '.')

# Проверяем только core модуль
from src.core.tool_db import global_tool_db

print("=== Проверка загрузки базы инструментов ===")
test_file = 'tests/sample_def.tlgx'
if os.path.exists(test_file):
    result = global_tool_db.load(test_file)
    print(f"Загрузка {test_file}: {'OK' if result else 'FAIL'}")
    print(f"is_loaded: {global_tool_db.is_loaded}")
    print(f"tools count: {len(global_tool_db.tools)}")
    print(f"tools keys: {list(global_tool_db.tools.keys())}")
    
    # Проверяем E007
    e007 = global_tool_db.get_replacement_tool('E007')
    print(f"E007 found: {e007 is not None}")
    if e007:
        print(f"E007 data: {e007}")
else:
    print(f"Файл {test_file} не найден!")

print("\n=== Все проверки завершены ===")
