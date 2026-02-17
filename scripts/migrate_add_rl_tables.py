#!/usr/bin/env python3
"""
Миграция БД: добавление таблиц для Reinforcement Learning.
Создает таблицы для tracking откликов и параметров стратегий.
"""

import asyncio
import aiosqlite
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config.settings import settings

async def create_rl_tables():
    """Создание таблиц для Reinforcement Learning."""
    
    db_path = settings.VACANCY_DB_PATH
    
    print(f"🔧 Подключение к БД: {db_path}")
    
    async with aiosqlite.connect(db_path) as db:
        # Таблица для отслеживания откликов
        print("📝 Создание таблицы outreach_attempts...")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS outreach_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lead_id INTEGER NOT NULL,
                message_text TEXT NOT NULL,
                strategy_id TEXT NOT NULL,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                -- Feedback metrics
                client_replied BOOLEAN DEFAULT NULL,
                reply_time_seconds INTEGER DEFAULT NULL,
                conversation_length INTEGER DEFAULT 0,
                deal_closed BOOLEAN DEFAULT NULL,
                deal_amount REAL DEFAULT NULL,
                
                -- Context features (для контекстных бандитов)
                lead_priority INTEGER,
                lead_budget REAL,
                lead_category TEXT,
                time_of_day INTEGER,
                day_of_week INTEGER,
                
                -- Reward
                reward REAL DEFAULT 0.0,
                
                FOREIGN KEY (lead_id) REFERENCES vacancies(id)
            )
        """)
        
        # Таблица для хранения параметров стратегий
        print("📝 Создание таблицы rl_strategies...")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS rl_strategies (
                strategy_id TEXT PRIMARY KEY,
                strategy_name TEXT NOT NULL,
                description TEXT,
                
                -- Thompson Sampling parameters
                alpha REAL DEFAULT 1.0,
                beta REAL DEFAULT 1.0,
                
                -- Performance metrics
                total_attempts INTEGER DEFAULT 0,
                successful_attempts INTEGER DEFAULT 0,
                avg_reward REAL DEFAULT 0.0,
                
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Индексы для производительности
        print("🔍 Создание индексов...")
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_outreach_lead 
            ON outreach_attempts(lead_id)
        """)
        
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_outreach_strategy 
            ON outreach_attempts(strategy_id)
        """)
        
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_outreach_sent_at 
            ON outreach_attempts(sent_at)
        """)
        
        await db.commit()
        
        # Инициализация стандартных стратегий
        print("🎯 Инициализация стратегий...")
        strategies = [
            ("formal", "Формальный стиль", "Официальный деловой тон, акцент на экспертизу"),
            ("casual", "Дружеский стиль", "Неформальный тон, как между коллегами"),
            ("technical", "Технический стиль", "Много технических деталей, кейсы"),
            ("consultative", "Консультативный", "Вопросы, выявление потребностей"),
            ("direct", "Прямой стиль", "Кратко, сразу к делу, без воды")
        ]
        
        for strategy_id, name, desc in strategies:
            await db.execute("""
                INSERT OR IGNORE INTO rl_strategies 
                (strategy_id, strategy_name, description)
                VALUES (?, ?, ?)
            """, (strategy_id, name, desc))
        
        await db.commit()
        
        print("\n✅ RL таблицы созданы успешно!")
        print(f"   - outreach_attempts (для tracking откликов)")
        print(f"   - rl_strategies (5 стратегий инициализировано)")
        print(f"   - 3 индекса для производительности")

if __name__ == "__main__":
    asyncio.run(create_rl_tables())
