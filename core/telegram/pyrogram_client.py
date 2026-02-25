"""
pyrogram_client.py — Фабрика клиентов Pyrogram.

Заменяет Telethon клиент. Pyrogram нативно поддерживает:
- Отправку по integer user_id без access_hash
- StringSession совместимый формат
"""

import os
from pyrogram import Client
from pyrogram.storage import MemoryStorage
from core.config.settings import settings
from core.utils.logger import logger


def get_userbot_client(session_name: str = "alexey_session") -> Client:
    """
    Создаёт Pyrogram userbot клиент.
    Пытается использовать StringSession из файла, иначе создаёт новую сессию.
    """
    # Пробуем прочитать сохранённую session string
    session_str = None
    session_paths = [
        f"data/sessions/{session_name}_pyrogram.txt",
        f"data/sessions/session_string_pyrogram.txt",
        "data/sessions/pyrogram_session.txt"
    ]
    for path in session_paths:
        try:
            with open(path, "r") as f:
                content = f.read().strip()
                if content:
                    session_str = content
                    logger.info(f"Loaded Pyrogram session from {path}")
                    break
        except FileNotFoundError:
            continue

    if session_str:
        client = Client(
            name=session_name,
            api_id=settings.TELEGRAM_API_ID,
            api_hash=settings.TELEGRAM_API_HASH,
            session_string=session_str,
            in_memory=True
        )
    else:
        # Сессия на диске (будет создана при первом запуске с авторизацией)
        os.makedirs("data/sessions", exist_ok=True)
        client = Client(
            name=f"data/sessions/{session_name}",
            api_id=settings.TELEGRAM_API_ID,
            api_hash=settings.TELEGRAM_API_HASH,
            phone_number=getattr(settings, 'TELEGRAM_PHONE', None),
        )
        logger.info(f"Will create new Pyrogram session at data/sessions/{session_name}")

    return client
