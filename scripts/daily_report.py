#!/usr/bin/env python3
"""
Ежедневный отчет по фильтрации парсера.
Запускается cron-ом на сервере ежедневно в 09:00 MSK.
Отправляет сводку за последние 24 часа в Telegram.
"""

import sqlite3
import os
import sys
import requests
from datetime import datetime, timedelta
from collections import Counter

# Пути
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

DB_PATH = os.path.join(PROJECT_ROOT, "data", "db", "vacancies.db")

# Загрузка .env
from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

BOT_TOKEN = os.getenv("SUPERVISOR_BOT_TOKEN")
CHAT_ID = os.getenv("SUPERVISOR_CHAT_ID")


def get_daily_stats():
    """Собирает статистику за последние 24 часа."""
    cutoff = (datetime.now() - timedelta(hours=24)).isoformat()

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Всего записей за 24ч
    cur.execute("SELECT COUNT(*) FROM vacancies WHERE first_seen >= ?", (cutoff,))
    total = cur.fetchone()[0]

    # Принятые
    cur.execute("SELECT COUNT(*) FROM vacancies WHERE status='accepted' AND first_seen >= ?", (cutoff,))
    accepted = cur.fetchone()[0]

    # Отклонённые
    cur.execute("SELECT COUNT(*) FROM vacancies WHERE status='rejected' AND first_seen >= ?", (cutoff,))
    rejected = cur.fetchone()[0]

    # Топ причин отклонения
    cur.execute("""
        SELECT rejection_reason, COUNT(*) as cnt
        FROM vacancies
        WHERE status='rejected' AND first_seen >= ? AND rejection_reason IS NOT NULL
        GROUP BY rejection_reason
        ORDER BY cnt DESC
        LIMIT 10
    """, (cutoff,))
    rejection_reasons = cur.fetchall()

    # Топ направлений (принятые)
    cur.execute("""
        SELECT direction, COUNT(*) as cnt
        FROM vacancies
        WHERE status='accepted' AND first_seen >= ? AND direction IS NOT NULL
        GROUP BY direction
        ORDER BY cnt DESC
        LIMIT 10
    """, (cutoff,))
    directions = cur.fetchall()

    # Топ источников (принятые)
    cur.execute("""
        SELECT source, COUNT(*) as cnt
        FROM vacancies
        WHERE status='accepted' AND first_seen >= ?
        GROUP BY source
        ORDER BY cnt DESC
        LIMIT 10
    """, (cutoff,))
    top_sources = cur.fetchall()

    # Общая статистика БД
    cur.execute("SELECT COUNT(*) FROM vacancies")
    total_all = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM vacancies WHERE status='accepted'")
    accepted_all = cur.fetchone()[0]

    conn.close()

    return {
        "total": total,
        "accepted": accepted,
        "rejected": rejected,
        "rejection_reasons": rejection_reasons,
        "directions": directions,
        "top_sources": top_sources,
        "total_all": total_all,
        "accepted_all": accepted_all,
    }


def format_report(stats):
    """Форматирует отчёт в Telegram-сообщение."""
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    acceptance_rate = (stats["accepted"] / stats["total"] * 100) if stats["total"] > 0 else 0

    lines = [
        f"📊 <b>Ежедневный отчёт по фильтрации</b>",
        f"📅 {now}",
        "",
        f"<b>За последние 24 часа:</b>",
        f"• Всего обработано: <b>{stats['total']}</b>",
        f"• ✅ Принято: <b>{stats['accepted']}</b>",
        f"• ❌ Отклонено: <b>{stats['rejected']}</b>",
        f"• 📈 Конверсия: <b>{acceptance_rate:.1f}%</b>",
    ]

    if stats["directions"]:
        lines.append("")
        lines.append("<b>🎯 Направления (принятые):</b>")
        for direction, cnt in stats["directions"]:
            lines.append(f"  • {direction}: {cnt}")

    if stats["rejection_reasons"]:
        lines.append("")
        lines.append("<b>🚫 Топ причин отклонения:</b>")
        for reason, cnt in stats["rejection_reasons"][:7]:
            short = reason[:50] + "…" if len(reason) > 50 else reason
            lines.append(f"  • {short}: {cnt}")

    if stats["top_sources"]:
        lines.append("")
        lines.append("<b>📡 Топ источников (принятые):</b>")
        for source, cnt in stats["top_sources"][:5]:
            short = source[:35] + "…" if len(source) > 35 else source
            lines.append(f"  • {short}: {cnt}")

    lines.append("")
    lines.append(f"<b>📦 Всего в БД:</b> {stats['total_all']} ({stats['accepted_all']} принятых)")

    return "\n".join(lines)


def send_telegram(text):
    """Отправляет сообщение через Telegram Bot API."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    resp = requests.post(url, json=payload, timeout=15)
    if resp.status_code != 200:
        print(f"❌ Telegram error: {resp.status_code} {resp.text}")
    else:
        print(f"✅ Отчёт отправлен в Telegram (chat_id={CHAT_ID})")


def main():
    if not BOT_TOKEN or not CHAT_ID:
        print("❌ SUPERVISOR_BOT_TOKEN или SUPERVISOR_CHAT_ID не заданы в .env")
        sys.exit(1)

    if not os.path.exists(DB_PATH):
        print(f"❌ БД не найдена: {DB_PATH}")
        sys.exit(1)

    stats = get_daily_stats()
    report = format_report(stats)

    print(report.replace("<b>", "").replace("</b>", ""))
    print("---")

    send_telegram(report)


if __name__ == "__main__":
    main()
