import sqlite3
import pandas as pd
import os

def export_february_parses():
    db_path = "/opt/harmonic-trifid/Harmonic-Trifid_Evgen/data/db/vacancies.db"
    output_filename = "/opt/harmonic-trifid/Harmonic-Trifid_Evgen/parses_server_feb_2026.xlsx"
    
    if not os.path.exists(db_path):
        print(f"Database file '{db_path}' not found.")
        return

    try:
        print(f"Connecting to {db_path}...")
        conn = sqlite3.connect(db_path)
        query = "SELECT text, source, direction, contact_link, last_seen FROM vacancies WHERE last_seen >= '2026-02-01' ORDER BY last_seen DESC"
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        if df.empty:
            print("No records found.")
            return

        print(f"Found {len(df)} records. Exporting...")
        df.to_excel(output_filename, index=False, engine='openpyxl')
        print(f"Successfully exported to '{output_filename}'")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    export_february_parses()
