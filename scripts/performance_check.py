#!/usr/bin/env python3
"""
Performance monitoring для Harmonic Trifid.
Показывает ключевые метрики производительности системы.
"""

import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from systems.parser.vacancy_db import VacancyDatabase
from datetime import datetime, timedelta
import aiosqlite

async def check_performance():
    """Проверка ключевых метрик производительности."""
    
    db = VacancyDatabase()
    await db.init_db()
    
    print("📊 Performance Report")
    print("=" * 60)
    
    # Прямое подключение к БД
    async with aiosqlite.connect(db.db_path) as conn:
        # Общая статистика
        cursor = await conn.execute("SELECT COUNT(*) FROM vacancies")
        total_leads = (await cursor.fetchone())[0]
        
        # Лиды за последние 24 часа
        yesterday = (datetime.now() - timedelta(days=1)).timestamp()
        cursor = await conn.execute(
            "SELECT COUNT(*) FROM vacancies WHERE timestamp > ?",
            (yesterday,)
        )
        leads_24h = (await cursor.fetchone())[0]
        
        # HOT лиды за 24 часа
        cursor = await conn.execute(
            "SELECT COUNT(*) FROM vacancies WHERE tier = 'HOT' AND timestamp > ?",
            (yesterday,)
        )
        hot_24h = (await cursor.fetchone())[0]
        
        # WARM лиды за 24 часа
        cursor = await conn.execute(
            "SELECT COUNT(*) FROM vacancies WHERE tier = 'WARM' AND timestamp > ?",
            (yesterday,)
        )
        warm_24h = (await cursor.fetchone())[0]
        
        # Средний informativeness score
        cursor = await conn.execute(
            "SELECT AVG(informativeness_score) FROM vacancies WHERE timestamp > ? AND informativeness_score > 0",
            (yesterday,)
        )
        avg_score = (await cursor.fetchone())[0] or 0
        
        # Acceptance rate
        accepted = hot_24h + warm_24h
        acceptance_rate = (accepted / max(leads_24h, 1)) * 100
    
    print(f"Всего лидов в БД: {total_leads:,}")
    print(f"Лидов за 24ч: {leads_24h}")
    print(f"HOT-лидов: {hot_24h} ({hot_24h/max(leads_24h, 1)*100:.1f}%)")
    print(f"WARM-лидов: {warm_24h} ({warm_24h/max(leads_24h, 1)*100:.1f}%)")
    print(f"Acceptance rate: {acceptance_rate:.1f}%")
    print(f"Средний Informativeness Score: {avg_score:.2f}")
    
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(check_performance())
