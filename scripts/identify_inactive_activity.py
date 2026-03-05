from telethon.sync import TelegramClient
from datetime import datetime, timezone, timedelta
import os
import logging
from core.config.settings import settings

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REPORT_PATH = os.path.join(PROJECT_ROOT, "reports", "dead_chats_2026-03-05.md")
SESSION_NAME = os.path.join(PROJECT_ROOT, "data", "sessions", "parser_session.session")

def identify_dead_chats():
    os.makedirs(os.path.join(PROJECT_ROOT, "reports"), exist_ok=True)
    
    # 2 месяца = 60 дней
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=60)
    logger.info(f"🔍 Ищем чаты без публикаций после {cutoff_date.isoformat()}")

    client = TelegramClient(SESSION_NAME.replace(".session", ""), settings.TELEGRAM_API_ID, settings.TELEGRAM_API_HASH)
    
    dead_chats = []
    
    with client:
        logger.info("🚀 Получаю список диалогов...")
        dialogs = client.get_dialogs()
        logger.info(f"📊 Всего диалогов: {len(dialogs)}")
        
        for dialog in dialogs:
            # Интересуют только каналы и группы
            if not (dialog.is_channel or dialog.is_group):
                continue
                
            last_msg = dialog.message
            if not last_msg:
                # В чате вообще нет сообщений?
                last_date = None
                is_dead = True
            else:
                last_date = last_msg.date
                is_dead = last_date < cutoff_date
                
            if is_dead:
                dead_chats.append({
                    'title': dialog.title,
                    'id': dialog.id,
                    'last_date': last_date.isoformat() if last_date else "Никогда"
                })

    # Сортируем по дате (старые сверху)
    dead_chats.sort(key=lambda x: x['last_date'])

    # Сохраняем отчет
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("# Отчет: Чаты без публикаций более 2 месяцев\n\n")
        f.write(f"**Дата анализа**: {datetime.now().isoformat()}\n")
        f.write(f"**Критерий**: Последнее сообщение ранее {cutoff_date.isoformat()}\n")
        f.write(f"**Найдено неактивных чатов**: {len(dead_chats)}\n\n")
        f.write("| Источник | ID | Последняя публикация |\n")
        f.write("| :--- | :--- | :--- |\n")
        for chat in dead_chats:
            title = chat['title'].replace('|', '\\|')
            f.write(f"| {title} | {chat['id']} | {chat['last_date']} |\n")

    logger.info(f"✅ Отчет создан: {REPORT_PATH}")
    logger.info(f"💀 Найдено мертвых чатов: {len(dead_chats)}")

if __name__ == "__main__":
    identify_dead_chats()
