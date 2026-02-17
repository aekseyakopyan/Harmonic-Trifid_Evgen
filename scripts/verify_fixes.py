#!/usr/bin/env python3
"""
Скрипт для проверки всех примененных исправлений.
"""
import ast
import re
from pathlib import Path
from typing import List, Tuple

PROJECT_ROOT = Path(__file__).parent.parent


def check_requirements_txt() -> bool:
    """Проверяет корректность requirements.txt."""
    req_file = PROJECT_ROOT / "requirements.txt"
    
    if not req_file.exists():
        print("❌ requirements.txt не найден")
        return False
    
    with open(req_file, 'r') as f:
        lines = f.readlines()
    
    # Проверка на дубликаты
    packages = [line.split('>=')[0].strip() for line in lines if '>=' in line]
    duplicates = [p for p in packages if packages.count(p) > 1]
    
    if duplicates:
        print(f"❌ Найдены дубликаты в requirements.txt: {set(duplicates)}")
        return False
    
    # Проверка на синтаксические ошибки
    for i, line in enumerate(lines, 1):
        line = line.strip()
        if line and not line.startswith('#'):
            if '>=' not in line and not line.isalpha():
                print(f"❌ Подозрительная строка {i}: {line}")
                return False
    
    print("✅ requirements.txt корректен")
    return True


def check_bare_excepts() -> Tuple[bool, int]:
    """Проверяет наличие bare except блоков."""
    python_files = list(PROJECT_ROOT.rglob('*.py'))
    exclude_dirs = {'venv', '.venv', 'env', '__pycache__', '.git'}
    python_files = [
        f for f in python_files 
        if not any(excluded in f.parts for excluded in exclude_dirs)
    ]
    
    total_bare = 0
    
    for file_path in python_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Ищем bare except
            bare_excepts = re.findall(r'^\s*except\s*:\s*(?:#.*)?$', content, re.MULTILINE)
            total_bare += len(bare_excepts)
            
        except Exception:
            continue
    
    if total_bare > 0:
        print(f"⚠️  Найдено {total_bare} bare except блоков")
        return False, total_bare
    
    print("✅ Bare except блоки не найдены")
    return True, 0


def check_todo_comments() -> Tuple[bool, List[str]]:
    """Проверяет наличие TODO комментариев."""
    critical_todos = [
        "systems/dashboard/routes/dashboard.py",
        "systems/parser/tasks.py",
        "systems/alexey/rate_limiter.py",
    ]
    
    found_todos = []
    
    for file_path in critical_todos:
        full_path = PROJECT_ROOT / file_path
        if not full_path.exists():
            continue
        
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if 'TODO' in content:
            found_todos.append(file_path)
    
    if found_todos:
        print(f"⚠️  TODO найдены в: {', '.join(found_todos)}")
        return False, found_todos
    
    print("✅ Критичные TODO реализованы")
    return True, []


def check_syntax_errors() -> Tuple[bool, List[str]]:
    """Проверяет синтаксические ошибки во всех Python файлах."""
    python_files = list(PROJECT_ROOT.rglob('*.py'))
    exclude_dirs = {'venv', '.venv', 'env', '__pycache__', '.git'}
    python_files = [
        f for f in python_files 
        if not any(excluded in f.parts for excluded in exclude_dirs)
    ]
    
    errors = []
    
    for file_path in python_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                ast.parse(f.read())
        except SyntaxError as e:
            errors.append(f"{file_path.name}: {e.msg} (строка {e.lineno})")
        except Exception:
            continue
    
    if errors:
        print(f"❌ Найдены синтаксические ошибки:\n" + "\n".join(errors))
        return False, errors
    
    print("✅ Синтаксических ошибок не найдено")
    return True, []


def main():
    """Основная функция проверки."""
    print("🔍 Начинаем финальную проверку исправлений...\n")
    
    results = {
        "requirements.txt": check_requirements_txt(),
        "bare_excepts": check_bare_excepts()[0],
        "todos": check_todo_comments()[0],
        "syntax": check_syntax_errors()[0],
    }
    
    print("\n" + "="*50)
    print("📊 ИТОГОВЫЙ ОТЧЕТ")
    print("="*50)
    
    for check, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{check:20s}: {status}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n🎉 Все проверки пройдены успешно!")
        return 0
    else:
        print("\n⚠️  Некоторые проверки не пройдены. См. детали выше.")
        return 1


if __name__ == "__main__":
    exit(main())
