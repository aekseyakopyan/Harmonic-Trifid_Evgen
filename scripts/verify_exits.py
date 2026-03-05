from telethon.sync import TelegramClient
import os
import logging
from core.config.settings import settings

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REPORT_PATH = os.path.join(PROJECT_ROOT, "reports", "inactive_chats_2026-03-05.md")
SESSION_NAME = os.path.join(PROJECT_ROOT, "data", "sessions", "parser_session.session")

def verify_chats():
    if not os.path.exists(REPORT_PATH):
        print("❌ Отчет не найден.")
        return

    # Загружаем список того, что должны были покинуть
    target_titles = set()
    with open(REPORT_PATH, "r", encoding="utf-8") as f:
        lines = f.readlines()
        for line in lines:
            if line.startswith("|") and not any(x in line for x in ["Источник", "---"]):
                parts = line.split("|")
                if len(parts) >= 2:
                    target_titles.add(parts[1].strip().replace('\\|', '|'))

    client = TelegramClient(SESSION_NAME.replace(".session", ""), settings.TELEGRAM_API_ID, settings.TELEGRAM_API_HASH)
    
    with client:
        print("🔍 Проверяю текущие диалоги...")
        current_dialogs = client.get_dialogs()
        current_titles = {d.title for d in current_dialogs}
        
        still_present = target_titles.intersection(current_titles)
        
        if not still_present:
            print(f"✅ Успех! Ни один из {len(target_titles)} неактивных чатов не найден в списке диалогов.")
        else:
            print(f"⚠️ Внимание! Найдено {len(still_present)} чатов из списка, которые все еще присутствуют:")
            for title in list(still_present)[:10]:
                print(f"  - {title}")
            if len(still_present) > 10:
                print(f"  ... и еще {len(still_present) - 10}")

if __name__ == "__main__":
    verify_chats()
