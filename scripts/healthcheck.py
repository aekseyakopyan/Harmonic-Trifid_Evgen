#!/usr/bin/env python3
"""
Healthcheck для системы Harmonic Trifid.
Проверяет работоспособность всех критических компонентов.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config.settings import settings
from systems.parser.vacancy_db import VacancyDatabase
from systems.parser.duplicate_detector import DuplicateDetector

async def check_database():
    """Проверка доступности БД"""
    try:
        db = VacancyDatabase()
        await db.init_db()
        
        # Проверяем запись
        stats = await db.get_stats()
        
        return True, f"DB OK: {stats['total']} total leads ({stats['accepted']} accepted, {stats['rejected']} rejected)"
    except Exception as e:
        return False, f"DB ERROR: {str(e)[:100]}"

async def check_duplicate_detector():
    """Проверка детектора дубликатов"""
    try:
        db = VacancyDatabase()
        await db.init_db()
        detector = DuplicateDetector(db_manager=db)
        
        stats = detector.get_statistics()
        return True, f"Detector OK: semantic={stats['semantic_enabled']}, cache={stats['cache_size']}/{stats['cache_max_size']}"
    except Exception as e:
        return False, f"Detector ERROR: {str(e)[:100]}"

async def check_settings():
    """Проверка конфигурации"""
    try:
        # Проверяем критические настройки
        checks = []
        checks.append(f"DB Path: {settings.VACANCY_DB_PATH}")
        checks.append(f"Admin: {settings.ADMIN_TELEGRAM_USERNAME}")
        checks.append(f"Monitored chats: {len(settings.monitored_chat_ids)}")
        
        return True, "Settings OK: " + ", ".join(checks)
    except Exception as e:
        return False, f"Settings ERROR: {str(e)[:100]}"

async def main():
    """Запуск всех проверок"""
    print("🔍 Harmonic Trifid System Healthcheck\n")
    print("=" * 60)
    
    checks = [
        ("Settings", check_settings()),
        ("Database", check_database()),
        ("Duplicate Detector", check_duplicate_detector()),
    ]
    
    all_passed = True
    
    for name, check_coro in checks:
        status, message = await check_coro
        icon = "✅" if status else "❌"
        print(f"{icon} {name}: {message}")
        
        if not status:
            all_passed = False
    
    print("=" * 60)
    
    if all_passed:
        print("\n✅ All systems operational")
        return 0
    else:
        print("\n❌ Some systems failed")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
