import sqlite3
import textwrap

DB_FILE = "vacancies.db"

def main():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get pending leads (accepted, not yet fully responded/sent)
    cursor.execute("""
        SELECT direction, contact_link, text, draft_response, status
        FROM vacancies 
        WHERE status = 'accepted' AND response IS NULL
        ORDER BY last_seen DESC
    """)
    
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        print("📭 Нет активных лидов в очереди на отправку.")
        return

    print(f"🚀 Очередь на отправку: {len(rows)} лидов\n")
    print("="*60)
    
    for i, row in enumerate(rows, 1):
        direction = row['direction'] or "Общее"
        contact = row['contact_link'] or "Неизвестно"
        text_preview = textwrap.shorten(row['text'] or "", width=100, placeholder="...")
        
        draft = row['draft_response']
        status_icon = "⏳ Ожидает генерации" if not draft else "✅ Черновик готов"
        
        print(f"#{i} [{direction}] -> {contact}")
        print(f"📄 Вакансия: {text_preview}")
        print(f"Статус: {status_icon}")
        
        if draft:
            print("-" * 30)
            print("📝 ПЛАНИРУЕМ ОТПРАВИТЬ:")
            print(textwrap.indent(draft, "   "))
        
        print("="*60)

if __name__ == "__main__":
    main()
