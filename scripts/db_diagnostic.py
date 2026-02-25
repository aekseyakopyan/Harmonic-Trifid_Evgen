import os
import sys
import asyncio
import sqlite3
from pathlib import Path

# Добавляем корень проекта
sys.path.append(os.getcwd())

from core.config.settings import settings
from core.database.connection import async_session, engine
from core.database.models import Lead
from sqlalchemy import select, text

async def diagnostic():
    print("=== DATABASE DIAGNOSTIC ===")
    print(f"Working Directory: {os.getcwd()}")
    print(f"DATABASE_URL from settings: {settings.DATABASE_URL}")
    print(f"Async URL: {settings.async_database_url}")
    
    # Пытаемся найти файл вручную
    db_rel_path = "data/db/bot_data.db"
    abs_path = os.path.abspath(db_rel_path)
    print(f"Checking absolute path: {abs_path}")
    
    if os.path.exists(abs_path):
        print(f"File exists: OK")
        conn = sqlite3.connect(abs_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(leads)")
        cols = [r[1] for r in cursor.fetchall()]
        print(f"Direct SQLite Columns: {cols}")
        conn.close()
    else:
        print(f"File NOT FOUND at {abs_path}")

    print("\n--- SQLAlchemy Test ---")
    try:
        async with async_session() as session:
            # Проверка через сырой запрос
            res = await session.execute(text("PRAGMA table_info(leads)"))
            sa_cols = [r[1] for r in res.fetchall()]
            print(f"SQLAlchemy PRAGMA columns: {sa_cols}")
            
            # Проверка через модель
            print("Querying Lead model...")
            stmt = select(Lead).limit(1)
            await session.execute(stmt)
            print("Query successful: Lead model matches database!")
            
    except Exception as e:
        print(f"SQLAlchemy Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(diagnostic())
