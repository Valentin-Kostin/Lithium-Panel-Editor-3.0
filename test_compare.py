#!/usr/bin/env python3
"""Тест функции сравнения PGMX и CSV"""
import sys
sys.path.insert(0, '/workspace/editor/src')

from core.batch_processor import BatchProcessor

# Создаем процессор
processor = BatchProcessor()

# Сканируем папку 1971
print("=== Сканирование папки 1971 ===")
result = processor.scan_folder('/workspace/1971')
print(f"Найдено SCX: {result['scx_count']}")
print(f"Найдено PGMX: {result['pgmx_count']}")
print(f"Найдено CSV: {result['csv_count']}")
print()

# Запускаем сравнение PGMX и CSV
print("=== Запуск сравнения PGMX и CSV ===")
compare_result = processor.compare_pgmx_csv()

print("\n=== Результаты сравнения ===")
print(f"OBOROT файлы: {compare_result['oborot_keys']}")
print(f"Отсутствующие файлы: {compare_result['missing_in_csv']}")
print(f"Отсутствующие в PGMX: {compare_result['missing_in_pgmx']}")

print("\n=== Лог операций ===")
for msg in processor.log_messages:
    print(msg)
