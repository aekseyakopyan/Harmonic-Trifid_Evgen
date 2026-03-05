#!/usr/bin/env python3
import os
import asyncio
import logging
from pyrogram import Client
from pyrogram.errors import FloodWait
from core.config.settings import settings

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Флаг для безопасности. Если True, скрипт только показывает, что бы он сделал.
DRY_RUN = True

# Пути
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REPORT_PATH = os.path.join(PROJECT_ROOT, "reports", "inactive_chats_2026-03-05.md")

async def leave_inactive_chats():
    if not os.path.exists(REPORT_PATH):
        logger.error(f"❌ Отчет не найден: {REPORT_PATH}")
        return

    # 1. Загружаем список названий чатов из отчета
    inactive_titles = set()
    try:
        with open(REPORT_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()
            # Пропускаем заголовок таблицы
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

    # 2. Инициализируем Pyrogram
    # Сначала пробуем файлы .session (более надежно)
    session_file_name = None
    for name in ["userbot_session", "parser_session", "joiner_session"]:
        session_path = os.path.join(PROJECT_ROOT, "data", "sessions", f"{name}.session")
        if os.path.exists(session_path):
            session_file_name = os.path.join("data", "sessions", name)
            logger.info(f"✨ Найдена файл-сессия: {session_file_name}")
            break

    if session_file_name:
        app = Client(
            name=session_file_name,
            api_id=settings.TELEGRAM_API_ID,
            api_hash=settings.TELEGRAM_API_HASH,
            workdir=PROJECT_ROOT
        )
    else:
        # Пробуем строки сессий
        session_str = None
        for path in ["data/sessions/session_string_final.txt", "data/sessions/alexey_pyrogram.txt"]:
            session_path = os.path.join(PROJECT_ROOT, path)
            try:
                with open(session_path, "r") as f:
                    content = f.read().strip()
                    if content:
                        session_str = content
                        break
            except FileNotFoundError:
                continue

        if not session_str:
            logger.error("❌ Сессия Pyrogram (файл или строка) не найдена.")
            return

        app = Client(
            name="chat_leaver",
            api_id=settings.TELEGRAM_API_ID,
            api_hash=settings.TELEGRAM_API_HASH,
            session_string=session_str,
            in_memory=True
        )

    async with app:
        logger.info("🚀 Сессия запущена. Начинаю поиск диалогов...")
        
        left_count = 0
        match_count = 0
        
        async for dialog in app.get_dialogs():
            chat = dialog.chat
            title = chat.title or chat.first_name
            
            if title in inactive_titles:
                match_count += 1
                if DRY_RUN:
                    logger.info(f"[DRY-RUN] Был бы совершен выход из: {title} (ID: {chat.id})")
                else:
                    try:
                        await app.leave_chat(chat.id)
                        logger.info(f"✅ Вышел из: {title} (ID: {chat.id})")
                        left_count += 1
                        # Небольшая пауза, чтобы не злить Telegram
                        await asyncio.sleep(1)
                    except FloodWait as e:
                        logger.warning(f"⚠️ FloodWait: нужно подождать {e.value} сек.")
                        await asyncio.sleep(e.value + 5)
                        # Пробуем оставить этот же чат после ожидания
                        await app.leave_chat(chat.id)
                        left_count += 1
                    except Exception as e:
                        logger.error(f"❌ Ошибка при выходе из {title}: {e}")

        logger.info("="*30)
        if DRY_RUN:
            logger.info(f"🏁 DRY-RUN завершен. Найдено совпадений: {match_count}")
            logger.info("Установите DRY_RUN = False в скрипте для реального удаления.")
        else:
            logger.info(f"🏁 Готово! Покинуто чатов: {left_count}")
        logger.info("="*30)

if __name__ == "__main__":
    asyncio.run(leave_inactive_chats())
