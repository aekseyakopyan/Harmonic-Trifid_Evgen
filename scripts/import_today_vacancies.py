import json
import sqlite3
import hashlib
from datetime import datetime

JSON_FILE = "vacancies_2026-02-09_monitor.json"
DB_FILE = "vacancies.db"

def create_table(cursor):
    cursor.execute("""
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

def generate_hash(text):
    return hashlib.md5(text.encode('utf-8')).hexdigest()

def main():
    import sys
    json_file = sys.argv[1] if len(sys.argv) > 1 else JSON_FILE
    print(f"Loading vacancies from {json_file}...")
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"File {JSON_FILE} not found!")
        return

    relevant = data.get("relevant_vacancies", [])
    print(f"Found {len(relevant)} relevant vacancies.")

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    create_table(cursor)

    count = 0
    for v in relevant:
        text = v.get("text", "")
        # Use full_text if available, otherwise text
        full_text = v.get("full_text", text)
        
        # Generate hash based on text or use existing ID logic if we had one. 
        # Using text has for deduplication.
        v_hash = generate_hash(full_text)
        
        direction = v.get("analysis", {}).get("specialization", "Marketing")
        source = v.get("channel", "Unknown")
        
        contact = v.get("contact", {})
        contact_link = contact.get("contact_link")
        if not contact_link and contact.get("contact_value"):
             # If contact_value is @username, make it a link
             val = contact.get("contact_value")
             if val.startswith("@"):
                 contact_link = f"https://t.me/{val[1:]}"
             elif val.isdigit(): # ID
                 contact_link = f"tg://user?id={val}"
        
        last_seen = v.get("date", datetime.now().isoformat())
        
        # Check if exists
        cursor.execute("SELECT hash FROM vacancies WHERE hash = ?", (v_hash,))
        if cursor.fetchone():
            print(f"Vacancy {v_hash} already exists. Skipping.")
            continue

        cursor.execute("""
            INSERT INTO vacancies (hash, text, direction, source, contact_link, status, last_seen)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (v_hash, full_text, direction, source, contact_link, 'accepted', last_seen))
        count += 1

    conn.commit()
    conn.close()
    print(f"Imported {count} new vacancies into {DB_FILE}.")

if __name__ == "__main__":
    main()
