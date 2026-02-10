import sqlite3
import os
import sys

# Добавляем корень проекта в пути импорта
sys.path.append(os.getcwd())

from core.config.settings import settings

def migrate():
    db_path = str(settings.VACANCY_DB_PATH)
    print(f"MIGRATION: Connecting to {db_path}...")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Пытаемся добавить новые колонки
    new_columns = [
        ("informativeness_score", "REAL DEFAULT 0.0"),
        ("needs_review", "BOOLEAN DEFAULT 0"),
        ("manual_label", "BOOLEAN"),
        ("labeled_by", "TEXT"),
        ("labeled_at", "TEXT"),
        ("tier", "TEXT"),
        ("message_id", "INTEGER"),
        ("chat_id", "INTEGER"),
        ("timestamp", "REAL")
    ]
    
    for col_name, col_type in new_columns:
        try:
            cursor.execute(f"ALTER TABLE vacancies ADD COLUMN {col_name} {col_type}")
            print(f"✅ Added column: {col_name}")
        except sqlite3.OperationalError:
            print(f"ℹ️  Column already exists: {col_name}")
            
    conn.commit()
    conn.close()
    print("MIGRATION: Completed.")

if __name__ == "__main__":
    migrate()
