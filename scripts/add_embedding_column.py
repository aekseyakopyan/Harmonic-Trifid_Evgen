#!/usr/bin/env python3
"""
Миграция БД: добавление колонки embedding для semantic deduplication.
"""

import asyncio
import aiosqlite
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config.settings import settings

async def migrate_add_embedding():
    """Добавить колонку embedding в vacancies если её нет."""
    db_path = settings.VACANCY_DB_PATH
    
    print(f"🔧 Checking database: {db_path}")
    
    async with aiosqlite.connect(db_path) as db:
        # Проверяем существование колонки
        cursor = await db.execute("PRAGMA table_info(vacancies)")
        columns = await cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        if 'embedding' not in column_names:
            print("📝 Adding 'embedding' column...")
            await db.execute("""
                ALTER TABLE vacancies 
                ADD COLUMN embedding BLOB
            """)
            await db.commit()
            print("✅ Column 'embedding' added successfully")
        else:
            print("✅ Column 'embedding' already exists")
        
        # Проверяем другие необходимые колонки
        required_columns = [
            'informativeness_score',
            'needs_review',
            'manual_label',
            'labeled_by',
            'labeled_at',
            'is_deleted',
            'deleted_at'
        ]
        
        missing_columns = [col for col in required_columns if col not in column_names]
        
        if missing_columns:
            print(f"\n⚠️  Missing columns detected: {', '.join(missing_columns)}")
            print("These columns should be added for full functionality.")
        else:
            print("✅ All required columns present")

if __name__ == "__main__":
    asyncio.run(migrate_add_embedding())
