from telethon.sync import TelegramClient
import os
from core.config.settings import settings

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REPORT_PATH = os.path.join(PROJECT_ROOT, "reports", "dead_chats_2026-03-05.md")
SESSION_NAME = os.path.join(PROJECT_ROOT, "data", "sessions", "parser_session.session")

def verify_dead_exits():
    if not os.path.exists(REPORT_PATH):
        print("❌ Отчет не найден.")
        return

    dead_chat_ids = set()
    with open(REPORT_PATH, "r", encoding="utf-8") as f:
        lines = f.readlines()
        for line in lines:
            if line.startswith("|") and not any(x in line for x in ["Источник", "---"]):
                parts = line.split("|")
                if len(parts) >= 4:
                    try:
                        dead_chat_ids.add(int(parts[-3].strip()))
                    except (ValueError, IndexError):
                        continue

    client = TelegramClient(SESSION_NAME.replace(".session", ""), settings.TELEGRAM_API_ID, settings.TELEGRAM_API_HASH)
    
    with client:
        print("🔍 Проверяю текущие диалоги...")
        current_dialogs = client.get_dialogs()
        current_ids = {d.id for d in current_dialogs}
        
        still_present = dead_chat_ids.intersection(current_ids)
        
        if not still_present:
            print(f"✅ Успех! Все {len(dead_chat_ids)} неактивных чатов покинуты.")
        else:
            print(f"⚠️ Внимание! Найдено {len(still_present)} чатов, которые все еще присутствуют.")
            # Выводим названия для отладки
            titles = {d.title for d in current_dialogs if d.id in still_present}
            for t in list(titles)[:10]:
                print(f"  - {t}")

if __name__ == "__main__":
    verify_dead_exits()
