
import sqlite3
import hashlib
from datetime import datetime
import os

def get_hash(text):
    clean_text = "".join(text.lower().split())
    return hashlib.md5(clean_text.encode()).hexdigest()

def load_leads():
    root_db = "vacancies.db"
    db_hist1 = "data/db/all_historical_leads.db"
    db_hist2 = "data/db/history_buyer_leads.db"

    conn_root = sqlite3.connect(root_db)
    cursor_root = conn_root.cursor()

    # Создаем таблицу если нет (на всякий случай)
    cursor_root.execute("""
        CREATE TABLE IF NOT EXISTS vacancies (
            hash TEXT PRIMARY KEY,
            text TEXT,
            direction TEXT,
            source TEXT,
            contact_link TEXT,
            draft_response TEXT,
            status TEXT,
            rejection_reason TEXT,
            last_seen TEXT,
            response TEXT
        )
    """)

    count = 0
    dupes = 0

    # 1. Загрузка из all_historical_leads.db (table: all_historical_leads)
    if os.path.exists(db_hist1):
        print(f"Reading {db_hist1}...")
        conn_h1 = sqlite3.connect(db_hist1)
        conn_h1.row_factory = sqlite3.Row
        leads1 = conn_h1.execute("SELECT * FROM all_historical_leads").fetchall()
        
        for lead in leads1:
            h = lead['hash'] or get_hash(lead['text'])
            try:
                cursor_root.execute("""
                    INSERT INTO vacancies (hash, text, direction, source, contact_link, status, rejection_reason, last_seen)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    h, 
                    lead['text'], 
                    lead['direction'] or "Digital Marketing", 
                    lead['source'] or "Historical Archive", 
                    lead['contact_link'], 
                    'accepted', 
                    'HISTORICAL_LOAD_2024_2026', 
                    lead['date'] or lead['found_at']
                ))
                count += 1
            except sqlite3.IntegrityError:
                dupes += 1
        conn_h1.close()

    # 2. Загрузка из history_buyer_leads.db (table: history_leads)
    if os.path.exists(db_hist2):
        print(f"Reading {db_hist2}...")
        conn_h2 = sqlite3.connect(db_hist2)
        conn_h2.row_factory = sqlite3.Row
        leads2 = conn_h2.execute("SELECT * FROM history_leads").fetchall()
        
        for lead in leads2:
            h = lead['hash'] or get_hash(lead['text'])
            try:
                cursor_root.execute("""
                    INSERT INTO vacancies (hash, text, direction, source, contact_link, status, rejection_reason, last_seen)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    h, 
                    lead['text'], 
                    lead['direction'] or "Digital Marketing", 
                    lead['source'] or "Historical Archive", 
                    lead['contact_link'], 
                    'accepted', 
                    'HISTORICAL_LOAD_2024_2026', 
                    lead['date'] or lead['found_at']
                ))
                count += 1
            except sqlite3.IntegrityError:
                dupes += 1
        conn_h2.close()

    conn_root.commit()
    conn_root.close()
    print(f"Done! Imported: {count}, Duplicates skipped: {dupes}")

if __name__ == "__main__":
    load_leads()
