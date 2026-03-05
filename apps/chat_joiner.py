import os
import asyncio
import pandas as pd
import random
import logging
from typing import List
from dotenv import load_dotenv
from pyrogram import Client
from pyrogram.errors import FloodWait, UserAlreadyParticipant, ChannelsTooMuch, BadRequest

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()

API_ID = int(os.getenv('TELEGRAM_API_ID', 0))
API_HASH = os.getenv('TELEGRAM_API_HASH', '')

# Настройки вступления
JOIN_DELAY_MIN = 60
JOIN_DELAY_MAX = 90
DEFAULT_EXCEL_PATH = "assets/chat_lists/chats_1600.xlsx"
DEFAULT_COLUMN_NAME = "link"


async def join_chat(client: Client, link: str) -> bool:
    """
    Пытается вступить в чат по ссылке через Pyrogram.
    Поддерживает @usernames, t.me/links и приватные приглашения (joinchat/+).
    """
    link = link.strip()
    if not link:
        return False

    logger.info(f"👉 Пытаюсь вступить в: {link}")

    try:
        # Pyrogram: join_chat принимает ссылку, username или invite hash напрямую
        await client.join_chat(link)
        logger.info(f"✅ Успешно вступил в: {link}")
        return True

    except FloodWait as e:
        logger.warning(f"⚠️ Flood Wait! Нужно подождать {e.value} секунд.")
        await asyncio.sleep(e.value + 5)
        return await join_chat(client, link)  # Рекурсивный повтор

    except UserAlreadyParticipant:
        logger.info(f"ℹ️ Уже состоим в этом чате: {link}")
        return True

    except ChannelsTooMuch:
        logger.error(f"❌ Лимит чатов (500) достигнут! Пауза 1 час...")
        await asyncio.sleep(3600)
        return False

    except BadRequest as e:
        err = str(e)
        # Битая ссылка — пропускаем БЕЗ паузы
        if any(code in err for code in ["USERNAME_INVALID", "USERNAME_NOT_OCCUPIED", "INVITE_HASH_INVALID", "INVITE_HASH_EXPIRED", "CHANNEL_INVALID"]):
            logger.debug(f"♻️ Пропуск: {link} ({err})")
            return None  # None = битая ссылка, пауза не нужна
        logger.error(f"❌ Ошибка при вступлении в {link}: {err}")
        return False

    except Exception as e:
        logger.error(f"❌ Ошибка при вступлении в {link}: {str(e)}")
        return False


async def main():
    import argparse
    parser = argparse.ArgumentParser(description="Автоматическое вступление в чаты Telegram из Excel.")
    parser.add_argument("--file", help="Путь к Excel файлу", default=None)
    parser.add_argument("--col", help="Название колонки со ссылками", default=None)
    parser.add_argument("--header", type=int, help="Строка заголовка (0 или 1)", default=0)
    parser.add_argument("--start", type=int, help="Начать с определенного индекса (1-indexed)", default=1)
    args = parser.parse_args()

    if not API_ID or not API_HASH:
        logger.error("❌ API_ID или API_HASH не найдены в .env файле.")
        return

    # Выбор файла
    excel_path = args.file or DEFAULT_EXCEL_PATH
    if not os.path.exists(excel_path):
        logger.error(f"❌ Файл не найден: {excel_path}")
        return

    # Чтение Excel
    try:
        df = pd.read_excel(excel_path, header=args.header)
        col_name = args.col or DEFAULT_COLUMN_NAME

        if col_name not in df.columns:
            logger.error(f"❌ Колонка '{col_name}' не найдена. Доступные колонки: {list(df.columns)}")
            return

        links = df[col_name].dropna().tolist()
        links = [str(l).strip() for l in links
                 if str(l).strip() and str(l).strip().lower() not in ('название', 'link', 'url', 'ссылка', 'чат', 'nan')]
        logger.info(f"📑 Найдено ссылок: {len(links)}")

        if args.start > 1:
            logger.info(f"⏭ Пропускаю первые {args.start-1} ссылок...")
            links = links[args.start-1:]
    except Exception as e:
        logger.error(f"❌ Ошибка при чтении Excel: {str(e)}")
        return

    # Загружаем Pyrogram сессию
    session_str = None
    for path in ["data/sessions/alexey_pyrogram.txt", "data/sessions/session_string_pyrogram.txt"]:
        try:
            with open(path, "r") as f:
                content = f.read().strip()
                if content:
                    session_str = content
                    break
        except FileNotFoundError:
            continue

    overall_total = len(links)

    if session_str:
        app = Client(
            name="chat_joiner",
            api_id=API_ID,
            api_hash=API_HASH,
            session_string=session_str,
            in_memory=True,
            sleep_threshold=60,  # Авто-ожидание при FloodWait до 60 сек
        )
    else:
        os.makedirs("data/sessions", exist_ok=True)
        app = Client(
            name="data/sessions/chat_joiner",
            api_id=API_ID,
            api_hash=API_HASH,
            sleep_threshold=60,
        )

    async with app:
        logger.info("🚀 Pyrogram сессия запущена")

        success_count = 0

        for i, link in enumerate(links, 1):
            logger.info(f"[{i}/{overall_total}]...")
            link = str(link).strip()
            if not link:
                continue

            result = await join_chat(app, link)
            if result is True:
                success_count += 1

            # Пауза только если ссылка живая (result != None)
            if result is not None and i < overall_total:
                delay = random.randint(JOIN_DELAY_MIN, JOIN_DELAY_MAX)
                logger.info(f"⏸ Пауза {delay} сек...")
                await asyncio.sleep(delay)

        logger.info("="*30)
        logger.info(f"🏁 Готово! Новых вступлений: {success_count}")
        logger.info("="*30)


if __name__ == "__main__":
    asyncio.run(main())
