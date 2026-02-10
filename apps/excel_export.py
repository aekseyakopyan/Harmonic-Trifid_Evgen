import sqlite3
import pandas as pd
import os

def export_leads():
    db_path = "data/db/all_historical_leads.db"
    if not os.path.exists(db_path):
        print(f"❌ База данных {db_path} не найдена.")
        return

    print("⏳ Подключаюсь к новой базе лидов...")
    conn = sqlite3.connect(db_path)
    
    # Загружаем лиды из новой структуры
    query = "SELECT source, direction, text, contact_link, date FROM all_historical_leads"
    df = pd.read_sql_query(query, conn)
    conn.close()

    if df.empty:
        print("ℹ️ Принятых лидов пока нет в базе.")
        return

    # Переименовываем колонки для красоты
    df.columns = ['Источник', 'Направление', 'Текст', 'Контакт', 'Дата обнаружения']
    
    # Сортируем: сначала те, где есть SEO (ЫУЩ)
    # ЫУЩ - это SEO в русской раскладке
    df['is_seo'] = df['Текст'].str.contains('SEO|ЫУЩ|сео', case=False, na=False) | \
                   df['Направление'].str.contains('SEO|ЫУЩ|сео', case=False, na=False)
    
    df = df.sort_values(by=['is_seo', 'Дата обнаружения'], ascending=[False, False])
    
    # Удаляем служебную колонку перед сохранением
    df_export = df.drop(columns=['is_seo'])

    output_file = "assets/all_leads_seo_focus.xlsx"
    print(f"📊 Найдено лидов: {len(df)}")
    print(f"🔍 Из них по SEO: {df['is_seo'].sum()}")
    
    df_export.to_excel(output_file, index=False)
    print(f"✅ Готово! Файл сохранен: {output_file}")

if __name__ == "__main__":
    export_leads()
