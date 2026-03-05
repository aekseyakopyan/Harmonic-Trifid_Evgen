
import sqlite3
import pandas as pd
import os

def export_february_parses():
    db_path = "data/db/vacancies.db"
    output_filename = "parses_feb_2026.xlsx"
    
    if not os.path.exists(db_path):
        print(f"❌ Database file '{db_path}' not found.")
        return

    try:
        print(f"⏳ Connecting to {db_path}...")
        conn = sqlite3.connect(db_path)
        
        # Select records from Feb 1st, 2026
        # last_seen format is likely ISO8601 based on previous inspection: 2026-02-17T07:03:37+00:00
        query = "SELECT text, source, direction, contact_link, last_seen FROM vacancies WHERE last_seen >= '2026-02-01' ORDER BY last_seen DESC"
        
        print(f"🔍 Executing query: {query}")
        df = pd.read_sql_query(query, conn)
        
        conn.close()
        
        if df.empty:
            print("ℹ️ No records found for February 2026.")
            return

        print(f"📊 Found {len(df)} records. Exporting to {output_filename}...")
        
        # Export to Excel
        df.to_excel(output_filename, index=False, engine='openpyxl')
        print(f"✅ Successfully exported to '{output_filename}'")
        
    except Exception as e:
        print(f"❌ An error occurred: {e}")

if __name__ == "__main__":
    export_february_parses()
