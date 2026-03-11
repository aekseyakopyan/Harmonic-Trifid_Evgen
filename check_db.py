import sqlite3
import os

db_path = "/opt/harmonic-trifid/Harmonic-Trifid_Evgen/data/db/vacancies.db"
if not os.path.exists(db_path):
    print(f"DB not found at {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("SELECT id, hash, source, contact_link, message_id, chat_id FROM vacancies WHERE status='accepted' ORDER BY id DESC LIMIT 5;")
rows = cursor.fetchall()

print("ID | Hash | Source | Contact | MsgID | ChatID")
for row in rows:
    print( " | ".join(map(str, row)) )

conn.close()
