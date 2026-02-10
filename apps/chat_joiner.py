import os
import asyncio
import pandas as pd
import random
import logging
from typing import List
from dotenv import load_dotenv
from telethon import TelegramClient, functions, types, errors

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()

API_ID = os.getenv('TELEGRAM_API_ID')
API_HASH = os.getenv('TELEGRAM_API_HASH')

# Настройки вступления
JOIN_DELAY_MIN = 60  # Минимум секунд между вступлениями
JOIN_DELAY_MAX = 90  # Максимум секунд между вступлениями
DEFAULT_EXCEL_PATH = "assets/chat_lists/chats_1600.xlsx"
DEFAULT_COLUMN_NAME = "link"

async def join_chat(client: TelegramClient, link: str):
    """
    Пытается вступить в чат по ссылке.
    Поддерживает @usernames, t.me/links и приватные приглашения (joinchat).
    """
    link = link.strip()
    if not link:
        return False

    logger.info(f"👉 Пытаюсь вступить в: {link}")
    
    try:
        if 'joinchat/' in link or '+' in link:
            # Обработка приватных ссылок-приглашений
            invite_hash = link.split('/')[-1].replace('+', '')
            await client(functions.messages.ImportChatInviteRequest(hash=invite_hash))
            logger.info(f"✅ Успешно вступил в приватный чат по ссылке.")
        else:
            # Обработка публичных ссылок и юзернеймов
            channel_username = link.split('/')[-1].replace('@', '')
            await client(functions.channels.JoinChannelRequest(channel=channel_username))
            logger.info(f"✅ Успешно вступил в {channel_username}.")
        return True

    except errors.FloodWaitError as e:
        logger.warning(f"⚠️ Flood Wait! Нужно подождать {e.seconds} секунд.")
        await asyncio.sleep(e.seconds)
        return await join_chat(client, link)
    except errors.UserAlreadyParticipantError:
        logger.info(f"ℹ️ Вы уже состоите в этом чате.")
        return True
    except errors.InviteHashExpiredError:
        logger.error(f"❌ Ссылка-приглашение истекла: {link}")
    except Exception as e:
        logger.error(f"❌ Ошибка при вступлении в {link}: {str(e)}")
    
    return False

async def main():
    import argparse
    parser = argparse.ArgumentParser(description="Автоматическое вступление в чаты Telegram из Excel.")
    parser.add_argument("--file", help="Путь к Excel файлу", default=None)
    parser.add_argument("--col", help="Название колонки со ссылками", default=None)
    parser.add_argument("--start", type=int, help="Начать с определенного индекса (1-indexed)", default=1)
    parser.add_argument("--no-delay-joined", action="store_true", help="Не делать длинную паузу, если уже состоите в чате")
    args = parser.parse_args()

    if not API_ID or not API_HASH:
        logger.error("❌ API_ID или API_HASH не найдены в .env файле.")
        return

    # Выбор файла
    if args.file:
        excel_path = args.file
    else:
        excel_path = input(f"Введите путь к Excel файлу (по умолчанию {DEFAULT_EXCEL_PATH}): ").strip() or DEFAULT_EXCEL_PATH
    
    if not os.path.exists(excel_path):
        logger.error(f"❌ Файл не найден: {excel_path}")
        return

    # Чтение Excel
    try:
        df = pd.read_excel(excel_path)
        if args.col:
            col_name = args.col
        else:
            col_name = input(f"Введите название колонки со ссылками (по умолчанию '{DEFAULT_COLUMN_NAME}'): ").strip() or DEFAULT_COLUMN_NAME
        
        if col_name not in df.columns:
            logger.error(f"❌ Колонка '{col_name}' не найдена в файле. Доступные колонки: {list(df.columns)}")
            return
            
        links = df[col_name].dropna().tolist()
        logger.info(f"📑 Найдено ссылок для вступления: {len(links)}")
        
        if args.start > 1:
            logger.info(f"⏭ Пропускаю первые {args.start-1} ссылок...")
            links = links[args.start-1:]
            start_idx = args.start
        else:
            start_idx = 1
            
    except Exception as e:
        logger.error(f"❌ Ошибка при чтении Excel: {str(e)}")
        return

    # Выбор сессии (StringSession)
    from telethon.sessions import StringSession
    with open("data/sessions/session_string_final.txt", "r") as f:
        session_str = f.read().strip()
    
    async with TelegramClient(StringSession(session_str), API_ID, API_HASH) as client:
        logger.info(f"🚀 Запущена сессия: StringSession")
        
        success_count = 0
        already_joined_count = 0
        total_links = len(links)
        overall_total = len(df[col_name].dropna().tolist())
        
        for i, link in enumerate(links, start_idx):
            logger.info(f"[{i}/{overall_total}]...")
            
            link = link.strip()
            if not link: continue
            
            try:
                if 'joinchat/' in link or '+' in link:
                    invite_hash = link.split('/')[-1].replace('+', '')
                    await client(functions.messages.ImportChatInviteRequest(hash=invite_hash))
                    logger.info(f"✅ Успешно вступил в приватный чат.")
                    success_count += 1
                else:
                    channel_username = link.split('/')[-1].replace('@', '')
                    await client(functions.channels.JoinChannelRequest(channel=channel_username))
                    logger.info(f"✅ Успешно вступил в {channel_username}.")
                    success_count += 1
            except errors.FloodWaitError as e:
                # Дополнительная отсрочка при блоке (например, +60 секунд к требуемому времени)
                extra_delay = 60 
                logger.warning(f"⚠️ Flood Wait! Нужно подождать {e.seconds} + {extra_delay} сек. (отсрочка)")
                await asyncio.sleep(e.seconds + extra_delay)
                # После ожидания можно попробовать снова тот же линк
                continue 
            except errors.ChannelsTooMuchError:
                logger.error(f"❌ Лимит достигнут! Вы вступили в слишком большое количество чатов (500).")
                logger.info("⏸ Пауза 10 минут перед следующей попыткой (на случай если это временный лимит)...")
                await asyncio.sleep(600)
                continue
            except errors.UserAlreadyParticipantError:
                logger.info(f"ℹ️ Вы уже состоите в этом чате.")
                already_joined_count += 1
                is_already_participant = True
            except Exception as e:
                logger.error(f"❌ Ошибка в {link}: {str(e)}")
            
            if i < overall_total:
                # Восстанавливаем стандартную задержку для всех случаев
                delay = random.randint(JOIN_DELAY_MIN, JOIN_DELAY_MAX)
                logger.info(f"⏸ Пауза {delay} сек...")
                await asyncio.sleep(delay)

    logger.info("="*30)
    logger.info("🏁 Работа завершена!")
    logger.info(f"📊 Ссылок обработано в этом сеансе: {i - start_idx + 1}")
    logger.info(f"✅ Новых вступлений: {success_count}")
    logger.info(f"ℹ️ Уже состояли в: {already_joined_count}")
    logger.info("="*30)


if __name__ == "__main__":
    asyncio.run(main())
