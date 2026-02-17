#!/usr/bin/env python3
"""
Скрипт верификации исправлений зависимостей Harmonic Trifid
"""
import sys
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

def check_syntax(file_path: Path) -> bool:
    """Проверка синтаксиса Python файла"""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", str(file_path)],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print(f"✅ {file_path.name}: синтаксис корректен")
            return True
        else:
            print(f"❌ {file_path.name}: ошибка синтаксиса")
            print(result.stderr)
            return False
    except Exception as e:
        print(f"❌ {file_path.name}: {e}")
        return False

def check_imports(file_path: Path, import_statement: str) -> bool:
    """Проверка возможности импорта"""
    try:
        result = subprocess.run(
            [sys.executable, "-c", import_statement],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT
        )
        if result.returncode == 0:
            print(f"✅ Импорт успешен: {import_statement}")
            return True
        else:
            print(f"❌ Ошибка импорта: {import_statement}")
            print(result.stderr)
            return False
    except Exception as e:
        print(f"❌ Ошибка при проверке импорта: {e}")
        return False

def main():
    print("🧪 Верификация исправлений Harmonic Trifid\n")
    
    all_passed = True
    
    # 1. Проверка синтаксиса критических файлов
    print("📝 Проверка синтаксиса Python файлов:")
    files_to_check = [
        PROJECT_ROOT / "main.py",
        PROJECT_ROOT / "export_db_to_excel.py",
    ]
    
    for file_path in files_to_check:
        if file_path.exists():
            if not check_syntax(file_path):
                all_passed = False
        else:
            print(f"⚠️  {file_path.name}: файл не найден")
    
    print()
    
    # 2. Проверка основных импортов
    print("📦 Проверка основных импортов:")
    imports_to_check = [
        "from core.config.settings import settings",
        "import pandas",
        "import sqlalchemy",
        "from pathlib import Path",
    ]
    
    for import_stmt in imports_to_check:
        if not check_imports(None, import_stmt):
            all_passed = False
    
    print()
    
    # 3. Проверка requirements.txt
    print("📋 Проверка requirements.txt:")
    req_file = PROJECT_ROOT / "requirements.txt"
    if req_file.exists():
        content = req_file.read_text()
        
        # Проверка на отсутствие проблемного пакета
        if "ub>=" in content:
            print("❌ Найден проблемный пакет 'ub' в requirements.txt")
            all_passed = False
        else:
            print("✅ Проблемный пакет 'ub' удален")
        
        # Проверка наличия необходимых пакетов
        required_packages = [
            "aiogram",
            "openpyxl",
            "joblib",
            "nltk",
            "fuzzywuzzy",
            "python-levenshtein"
        ]
        
        for pkg in required_packages:
            if pkg in content:
                print(f"✅ Пакет '{pkg}' присутствует")
            else:
                print(f"❌ Пакет '{pkg}' отсутствует")
                all_passed = False
        
        # Проверка закрепленных версий
        if "torch==2.1.2" in content:
            print("✅ Версия torch закреплена")
        else:
            print("⚠️  Версия torch не закреплена")
        
        if "transformers==4.35.2" in content:
            print("✅ Версия transformers закреплена")
        else:
            print("⚠️  Версия transformers не закреплена")
    else:
        print("❌ requirements.txt не найден")
        all_passed = False
    
    print()
    
    # 4. Проверка main.py на улучшенные импорты
    print("🔍 Проверка улучшений в main.py:")
    main_file = PROJECT_ROOT / "main.py"
    if main_file.exists():
        content = main_file.read_text()
        
        if "PROJECT_ROOT = Path(__file__).resolve().parent" in content:
            print("✅ Использован улучшенный метод определения корня проекта")
        else:
            print("❌ Не найден улучшенный метод определения корня проекта")
            all_passed = False
        
        if "if str(PROJECT_ROOT) not in sys.path:" in content:
            print("✅ Добавлена проверка на дублирование путей")
        else:
            print("❌ Отсутствует проверка на дублирование путей")
            all_passed = False
    else:
        print("❌ main.py не найден")
        all_passed = False
    
    print()
    print("=" * 60)
    
    if all_passed:
        print("✅ ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ УСПЕШНО!")
        print("\n📦 Для установки зависимостей выполните:")
        print("pip install -r requirements.txt --upgrade")
        return 0
    else:
        print("❌ ОБНАРУЖЕНЫ ПРОБЛЕМЫ")
        print("\nПожалуйста, проверьте вывод выше для деталей.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
