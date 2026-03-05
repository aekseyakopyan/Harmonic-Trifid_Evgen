from telethon.sync import TelegramClient
from telethon import functions, types
import os
import logging
from core.config.settings import settings

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Флаг для безопасности. Если True, скрипт только показывает, что бы он сделал.
DRY_RUN = False

# Пути
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REPORT_PATH = os.path.join(PROJECT_ROOT, "reports", "inactive_chats_2026-03-05.md")
SESSION_NAME = os.path.join(PROJECT_ROOT, "data", "sessions", "parser_session.session")

def leave_inactive_chats_telethon():
    if not os.path.exists(REPORT_PATH):
        logger.error(f"❌ Отчет не найден: {REPORT_PATH}")
        return

    # 1. Загружаем список названий чатов из отчета
    inactive_titles = set()
    try:
        with open(REPORT_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()
            for line in lines:
                if line.startswith("|") and not any(x in line for x in ["Источник", "---"]):
                    parts = line.split("|")
                    if len(parts) >= 2:
                        title = parts[1].strip().replace('\\|', '|')
                        inactive_titles.add(title)
        
        logger.info(f"📑 Загружено {len(inactive_titles)} названий чатов из отчета")
    except Exception as e:
        logger.error(f"❌ Ошибка при чтении отчета: {e}")
        return

    if not inactive_titles:
        logger.warning("⚠️ Список чатов для выхода пуст.")
        return

    # 2. Инициализируем Telethon
    try:
        # Telethon .session file handles everything
        client = TelegramClient(
            SESSION_NAME.replace(".session", ""), 
            settings.TELEGRAM_API_ID, 
            settings.TELEGRAM_API_HASH
        )
    except Exception as e:
        logger.error(f"❌ Ошибка при создании клиента Telethon: {e}")
        return

    with client:
        logger.info("🚀 Сессия запущена. Повышаю диалоги...")
        
        left_count = 0
        match_count = 0
        
        for dialog in client.get_dialogs():
            title = dialog.title
            if title in inactive_titles:
                match_count += 1
                if DRY_RUN:
                    logger.info(f"[DRY-RUN] Был бы совершен выход из: {title} (ID: {dialog.id})")
                else:
                    try:
                        client(functions.channels.LeaveChannelRequest(
                            channel=dialog.entity
                        ))
                        logger.info(f"✅ Вышел из: {title} (ID: {dialog.id})")
                        left_count += 1
                        import time
                        time.sleep(2) # Задержка для безопасности
                    except Exception as e:
                        logger.error(f"❌ Ошибка при выходе из {title}: {e}")

        logger.info("="*30)
        if DRY_RUN:
            logger.info(f"🏁 DRY-RUN завершен. Найдено совпадений: {match_count}")
        else:
            logger.info(f"🏁 Готово! Покинуто чатов: {left_count}")
        logger.info("="*30)

if __name__ == "__main__":
    leave_inactive_chats_telethon()
