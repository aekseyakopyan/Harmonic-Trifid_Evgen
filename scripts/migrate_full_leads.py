import sqlite3
import os

db_path = "data/db/bot_data.db"

def migrate():
    if not os.path.exists(db_path):
        print(f"База данных {db_path} не найдена.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("PRAGMA table_info(leads)")
        columns = [row[1] for row in cursor.fetchall()]
        
        target_columns = [
            ("last_outreach_at", "DATETIME"),
            ("tier", "VARCHAR(20)"),
            ("priority", "INTEGER DEFAULT 0"),
            ("meeting_scheduled", "BOOLEAN DEFAULT 0")
        ]
        
        for col_name, col_type in target_columns:
            if col_name not in columns:
                print(f"Добавляю колонку {col_name} ({col_type}) в таблицу leads...")
                cursor.execute(f"ALTER TABLE leads ADD COLUMN {col_name} {col_type}")
                conn.commit()
            else:
                print(f"Колонка {col_name} уже существует.")
            
        print("Миграция завершена успешно.")
            
    except Exception as e:
        print(f"Ошибка при миграции: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
