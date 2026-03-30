import sqlite3
import pandas as pd
import os

def export_split():
    db_path = "/opt/harmonic-trifid/Harmonic-Trifid_Evgen/data/db/vacancies.db"
    
    if not os.path.exists(db_path):
        print(f"Database file '{db_path}' not found.")
        return

    try:
        print(f"Connecting to {db_path}...")
        conn = sqlite3.connect(db_path)
        
        # We know there are ~207,679 records. Let's just use limit and offset to split them in half.
        query_all = "SELECT text, source, direction, contact_link, last_seen FROM vacancies WHERE last_seen >= '2026-02-01' AND last_seen <= '2026-03-05 23:59:59' ORDER BY last_seen DESC"
        
        print("Fetching data...")
        df = pd.read_sql_query(query_all, conn)
        conn.close()
        
        total_records = len(df)
        midpoint = total_records // 2
        
        print(f"Total records: {total_records}. Midpoint: {midpoint}")
        
        # Part 1
        df_part1 = df.iloc[:midpoint]
        file1 = "/opt/harmonic-trifid/Harmonic-Trifid_Evgen/full_parses_feb_mar5_part1.xlsx"
        print(f"Saving Part 1 ({len(df_part1)} records)...")
        df_part1.to_excel(file1, index=False, engine='openpyxl')
        
        # Part 2
        df_part2 = df.iloc[midpoint:]
        file2 = "/opt/harmonic-trifid/Harmonic-Trifid_Evgen/full_parses_feb_mar5_part2.xlsx"
        print(f"Saving Part 2 ({len(df_part2)} records)...")
        df_part2.to_excel(file2, index=False, engine='openpyxl')
        
        print("Successfully exported both parts.")
        print(f"Part 1 size: {os.path.getsize(file1) / (1024*1024):.2f} MB")
        print(f"Part 2 size: {os.path.getsize(file2) / (1024*1024):.2f} MB")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    export_split()
