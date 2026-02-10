import sqlite3
import pandas as pd
import os
import sys

def export_raw_leads():
    db_path = "data/db/history_buyer_leads.db"
    output_path = "assets/history_leads_raw.xlsx"
    
    if not os.path.exists(db_path):
        print(f"❌ База данных {db_path} не найдена.")
        return

    print(f"⏳ Чтение данных из {db_path}...")
    try:
        conn = sqlite3.connect(db_path)
        # Загружаем лиды: id, source, direction, text, contact_link, date, score, ai_reason
        query = "SELECT source, direction, text, contact_link, date, score, ai_reason FROM history_leads WHERE ai_status != 2"
        df = pd.read_sql_query(query, conn)
        conn.close()
    except Exception as e:
        print(f"❌ Ошибка при чтении базы данных: {e}")
        return

    if df.empty:
        print("ℹ️ Принятых лидов пока нет в базе.")
        return

    print(f"📊 Найдено лидов: {len(df)}")
    
    # Переименовываем колонки для удобства пользователя
    df.columns = ['Источник', 'Направление', 'Текст', 'Контакт', 'Дата', 'Score', 'Причина (AI)']
    
    # Сортировка по дате (если формат позволяет) или просто оставляем как есть
    # В данном случае лиды уже должны быть в порядке поступления
    
    print(f"💾 Создание нового Excel: {output_path}...")
    try:
        if not os.path.exists("assets"):
            os.makedirs("assets")
        
        # Удаляем старый файл, если он есть
        if os.path.exists(output_path):
            os.remove(output_path)
            print(f"  🗑️ Старый файл удален")
        
        df.to_excel(output_path, index=False)
        print(f"✅ Готово! Файл сохранен: {output_path}")
        print(f"📏 Размер файла: {os.path.getsize(output_path) / (1024*1024):.2f} МБ")
    except Exception as e:
        print(f"❌ Ошибка при сохранении Excel: {e}")

if __name__ == "__main__":
    export_raw_leads()
