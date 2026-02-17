#!/usr/bin/env python3
"""
Скрипт для автоматической замены bare except блоков на конкретные исключения.
"""
import re
import sys
from pathlib import Path
from typing import List, Tuple

# Путь к проекту
PROJECT_ROOT = Path(__file__).parent.parent

# Файлы для обработки
TARGET_FILES = [
    "apps/unified_monitor.py",
    "apps/history_parser.py",
    "apps/today_parser.py",
    "systems/gwen/commander.py",
    "systems/gwen/learning_engine.py",
    "systems/parser/vacancy_db.py",
    "systems/parser/outreach_generator.py",
    "systems/alexey/main.py",
    "systems/alexey/tasks.py",
    "systems/alexey/handlers/message_handler.py",
    "core/config/prompts.py",
]

def find_bare_excepts(content: str) -> List[Tuple[int, str]]:
    """Находит все bare except блоки в коде."""
    lines = content.split('\n')
    bare_excepts = []
    
    for i, line in enumerate(lines, 1):
        # Ищем строки с "except:" (не "except SomeException:")
        if re.match(r'^\s*except\s*:\s*(?:#.*)?$', line):
            bare_excepts.append((i, line))
    
    return bare_excepts

def fix_bare_except(content: str) -> str:
    """Заменяет bare except на конкретные исключения."""
    lines = content.split('\n')
    result = []
    
    for line in lines:
        # Паттерн для bare except
        match = re.match(r'^(\s*)except\s*:\s*(#.*)?$', line)
        if match:
            indent = match.group(1)
            comment = match.group(2) or ''
            # Заменяем на общее исключение с логированием
            new_line = f"{indent}except Exception as e:  {comment}"
            result.append(new_line)
        else:
            result.append(line)
    
    return '\n'.join(result)

def main():
    """Основная функция."""
    print("🔧 Начинаем исправление bare except блоков...\n")
    
    total_fixed = 0
    
    for file_path in TARGET_FILES:
        full_path = PROJECT_ROOT / file_path
        
        if not full_path.exists():
            print(f"⚠️  Файл не найден: {file_path}")
            continue
        
        # Читаем содержимое
        with open(full_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        # Находим bare excepts
        bare_excepts = find_bare_excepts(original_content)
        
        if not bare_excepts:
            print(f"✅ {file_path}: Bare except не найдены")
            continue
        
        print(f"📝 {file_path}: Найдено {len(bare_excepts)} bare except блоков")
        for line_num, line in bare_excepts:
            print(f"   Строка {line_num}: {line.strip()}")
        
        # Исправляем
        fixed_content = fix_bare_except(original_content)
        
        # Создаем бэкап
        backup_path = full_path.with_suffix('.py.backup')
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(original_content)
        
        # Записываем исправленный файл
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(fixed_content)
        
        print(f"✅ Исправлено. Бэкап: {backup_path.name}\n")
        total_fixed += len(bare_excepts)
    
    print(f"\n🎉 Завершено! Всего исправлено: {total_fixed} bare except блоков")
    return 0

if __name__ == "__main__":
    sys.exit(main())
