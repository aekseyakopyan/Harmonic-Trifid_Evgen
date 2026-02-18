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
        # Проверяем, есть ли уже такая колонка
        cursor.execute("PRAGMA table_info(leads)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if "last_outreach_at" not in columns:
            print("Добавляю колонку last_outreach_at в таблицу leads...")
            cursor.execute("ALTER TABLE leads ADD COLUMN last_outreach_at DATETIME")
            conn.commit()
            print("Готово.")
        else:
            print("Колонка last_outreach_at уже существует.")
            
    except Exception as e:
        print(f"Ошибка при миграции: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
