
import sqlite3
import pandas as pd
import os

def export_db_to_excel():
    db_path = "vacancies.db"
    output_filename = "vacancies_export.xlsx"
    
    if not os.path.exists(db_path):
        print(f"Database file '{db_path}' not found.")
        return

    try:
        conn = sqlite3.connect(db_path)
        
        # Read the table into a DataFrame
        query = "SELECT * FROM vacancies ORDER BY last_seen DESC"
        df = pd.read_sql_query(query, conn)
        
        conn.close()
        
        if df.empty:
            print("Database is empty. No file created.")
            return

        # Export to Excel
        df.to_excel(output_filename, index=False, engine='openpyxl')
        print(f"Successfully exported {len(df)} records to '{output_filename}'")
        
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    export_db_to_excel()
