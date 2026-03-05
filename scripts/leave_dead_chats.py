from telethon.sync import TelegramClient
from telethon import functions
import os
import logging
from core.config.settings import settings
import time

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Флаг для безопасности. Если True, только имитация.
DRY_RUN = False

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REPORT_PATH = os.path.join(PROJECT_ROOT, "reports", "dead_chats_2026-03-05.md")
SESSION_NAME = os.path.join(PROJECT_ROOT, "data", "sessions", "parser_session.session")

def leave_dead_chats():
    if not os.path.exists(REPORT_PATH):
        logger.error(f"❌ Отчет не найден: {REPORT_PATH}")
        return

    # 1. Загружаем список ID чатов из отчета
    dead_chat_ids = set()
    try:
        with open(REPORT_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()
            for line in lines:
                if line.startswith("|") and not any(x in line for x in ["Источник", "---"]):
                    parts = line.split("|")
                    if len(parts) >= 4:
                        try:
                            # ID чата всегда в предпоследней значимой колонке (с конца)
                            # Строка: | Title | ID | Date | -> split: ['', Title, ID, Date, '']
                            chat_id = int(parts[-3].strip())
                            dead_chat_ids.add(chat_id)
                        except (ValueError, IndexError):
                            continue
        
        logger.info(f"📑 Загружено {len(dead_chat_ids)} ID чатов из отчета")
    except Exception as e:
        logger.error(f"❌ Ошибка при чтении отчета: {e}")
        return

    if not dead_chat_ids:
        logger.warning("⚠️ Список чатов для выхода пуст.")
        return

    # 2. Инициализируем Telethon
    client = TelegramClient(SESSION_NAME.replace(".session", ""), settings.TELEGRAM_API_ID, settings.TELEGRAM_API_HASH)

    with client:
        logger.info(f"🚀 Сессия запущена. Начинаю выход из {len(dead_chat_ids)} чатов...")
        
        left_count = 0
        
        # Получаем все диалоги еще раз, чтобы иметь доступе к entity
        dialogs = client.get_dialogs()
        
        for dialog in dialogs:
            if dialog.id in dead_chat_ids:
                if DRY_RUN:
                    logger.info(f"[DRY-RUN] Был бы совершен выход из: {dialog.title} (ID: {dialog.id})")
                else:
                    try:
                        client(functions.channels.LeaveChannelRequest(
                            channel=dialog.entity
                        ))
                        logger.info(f"✅ Вышел из: {dialog.title} (ID: {dialog.id})")
                        left_count += 1
                        time.sleep(2) # Задержка для безопасности
                    except Exception as e:
                        logger.error(f"❌ Ошибка при выходе из {dialog.title}: {e}")

        logger.info("="*30)
        if DRY_RUN:
            logger.info(f"🏁 DRY-RUN завершен.")
        else:
            logger.info(f"🏁 Готово! Покинуто чатов: {left_count}")
        logger.info("="*30)

if __name__ == "__main__":
    leave_dead_chats()
