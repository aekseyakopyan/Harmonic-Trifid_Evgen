#!/usr/bin/env python3
import sqlite3
import os
import pandas as pd
from datetime import datetime, timedelta

# Пути
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB_PATH = os.path.join(PROJECT_ROOT, "data", "db", "vacancies.db")
REPORTS_DIR = os.path.join(PROJECT_ROOT, "reports")
CHATS_DIR = os.path.join(PROJECT_ROOT, "assets", "chat_lists")

def find_inactive_chats():
    if not os.path.exists(DB_PATH):
        print(f"❌ БД не найдена: {DB_PATH}")
        return

    # 1. Рассчитываем порог в 3 месяца
    cutoff_date = (datetime.now() - timedelta(days=90)).isoformat()
    print(f"🔍 Ищем чаты без лидов (status='accepted') после {cutoff_date}")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 2. Получаем все уникальные источники (чаты)
    cur.execute("SELECT DISTINCT source FROM vacancies WHERE source IS NOT NULL")
    all_sources = [row[0] for row in cur.fetchall()]
    print(f"📊 Всего уникальных источников в БД: {len(all_sources)}")

    # 3. Находим последнюю дату лида для каждого чата
    inactive_results = []
    
    for source in all_sources:
        # Ищем последний 'accepted' лид
        cur.execute("""
            SELECT MAX(last_seen) 
            FROM vacancies 
            WHERE source = ? AND status = 'accepted'
        """, (source,))
        
        last_lead_date = cur.fetchone()[0]
        
        if not last_lead_date:
            # Лидов не было никогда
            inactive_results.append({
                "source": source,
                "last_lead": "Никогда",
                "days_since": "∞"
            })
        elif last_lead_date < cutoff_date:
            # Лид был, но давно
            try:
                last_dt = datetime.fromisoformat(last_lead_date)
                days_ago = (datetime.now() - last_dt).days
                inactive_results.append({
                    "source": source,
                    "last_lead": last_lead_date,
                    "days_since": days_ago
                })
            except:
                inactive_results.append({
                    "source": source,
                    "last_lead": last_lead_date,
                    "days_since": "Error"
                })

    conn.close()

    # 4. Сортируем по давности (сначала те, где не было никогда, потом старые)
    inactive_results.sort(key=lambda x: (0 if x['days_since'] == '∞' else 1, 
                                         -x['days_since'] if isinstance(x['days_since'], int) else 0))

    # 5. Сохраняем отчет
    os.makedirs(REPORTS_DIR, exist_ok=True)
    report_path = os.path.join(REPORTS_DIR, f"inactive_chats_{datetime.now().strftime('%Y-%m-%d')}.md")
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"# 📉 Отчет по неактивным чатам\n")
        f.write(f"**Дата отчета:** {datetime.now().strftime('%d.%m.%Y')}\n")
        f.write(f"**Критерий:** отсутствие лидов (status='accepted') за последние 3 месяца (>= 90 дней)\n\n")
        f.write(f"Всего неактивных чатов: **{len(inactive_results)}**\n\n")
        
        f.write("| Источник | Последний лид | Дней назад |\n")
        f.write("| :--- | :--- | :--- |\n")
        
        for res in inactive_results:
            source = res['source'].replace('|', '\\|')
            f.write(f"| {source} | {res['last_lead']} | {res['days_since']} |\n")

    print(f"✅ Отчет создан: {report_path}")
    print(f"📉 Найдено неактивных чатов: {len(inactive_results)}")

if __name__ == "__main__":
    find_inactive_chats()
