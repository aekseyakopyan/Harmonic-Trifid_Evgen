import sqlite3
import pandas as pd
import os

def export_full():
    db_path = "/opt/harmonic-trifid/Harmonic-Trifid_Evgen/data/db/vacancies.db"
    output_filename = "/opt/harmonic-trifid/Harmonic-Trifid_Evgen/full_parses_feb_mar5_2026.xlsx"
    
    if not os.path.exists(db_path):
        print(f"Database file '{db_path}' not found.")
        return

    try:
        print(f"Connecting to {db_path}...")
        conn = sqlite3.connect(db_path)
        # Full range: Feb 1 to Mar 5
        query = "SELECT text, source, direction, contact_link, last_seen FROM vacancies WHERE last_seen >= '2026-02-01' AND last_seen <= '2026-03-05 23:59:59' ORDER BY last_seen DESC"
        
        print(f"Executing query: {query}")
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        if df.empty:
            print("No records found in this range.")
            return

        print(f"Found {len(df)} records. Exporting to Excel...")
        # Split into multiple sheets if it's too large, but 207k fits in one.
        df.to_excel(output_filename, index=False, engine='openpyxl')
        print(f"Successfully exported to '{output_filename}'")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    export_full()
