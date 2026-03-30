import sqlite3
import pandas as pd
import json
import os

def export_json():
    db_path = "/opt/harmonic-trifid/Harmonic-Trifid_Evgen/data/db/vacancies.db"
    output_filename = "/opt/harmonic-trifid/Harmonic-Trifid_Evgen/full_parses_feb_mar5_2026.json"
    
    if not os.path.exists(db_path):
        print(f"Database file '{db_path}' not found.")
        return

    try:
        print(f"Connecting to {db_path}...")
        conn = sqlite3.connect(db_path)
        # Full content: Feb 1 to Mar 5
        query = "SELECT text, source, direction, contact_link, last_seen FROM vacancies WHERE last_seen >= '2026-02-01' AND last_seen <= '2026-03-05 23:59:59' ORDER BY last_seen DESC"
        
        print(f"Executing query...")
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        if df.empty:
            print("No records found.")
            return

        print(f"Found {len(df)} records. Exporting to JSON...")
        # Use orient='records' and force_ascii=False for Cyrillic
        df.to_json(output_filename, orient='records', force_ascii=False, indent=2)
        
        print(f"Successfully exported to '{output_filename}'")
        file_size = os.path.getsize(output_filename) / (1024 * 1024)
        print(f"Final file size: {file_size:.2f} MB")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    export_json()
