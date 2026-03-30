import sqlite3
import pandas as pd
import os

def export_optimized():
    db_path = "/opt/harmonic-trifid/Harmonic-Trifid_Evgen/data/db/vacancies.db"
    output_filename = "/opt/harmonic-trifid/Harmonic-Trifid_Evgen/full_parses_optimized_30mb_v2.xlsx"
    
    if not os.path.exists(db_path):
        print(f"Database file '{db_path}' not found.")
        return

    try:
        print(f"Connecting to {db_path}...")
        conn = sqlite3.connect(db_path)
        # Further truncate text to 300 chars
        query = """
        SELECT 
            SUBSTR(text, 1, 300) as text_short, 
            source, 
            direction, 
            contact_link, 
            last_seen 
        FROM vacancies 
        WHERE last_seen >= '2026-02-01' AND last_seen <= '2026-03-05 23:59:59' 
        ORDER BY last_seen DESC
        """
        
        print(f"Executing query...")
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        if df.empty:
            print("No records found.")
            return

        df = df.rename(columns={'text_short': 'text'})

        print(f"Found {len(df)} records. Exporting to Excel (V2 optimized)...")
        df.to_excel(output_filename, index=False, engine='openpyxl')
        print(f"Successfully exported to '{output_filename}'")
        file_size = os.path.getsize(output_filename) / (1024 * 1024)
        print(f"Final file size: {file_size:.2f} MB")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    export_optimized()
