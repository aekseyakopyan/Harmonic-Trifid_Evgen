"""
Парсер всех сообщений из всех чатов → history_raw_messages.db

Запуск: python apps/parse_all_messages.py
         python apps/parse_all_messages.py --from-date 2024-01-01
         python apps/parse_all_messages.py --limit 1000   (сообщений на чат)
"""

import asyncio
import hashlib
import sqlite3
import sys
import argparse
from datetime import datetime, timezone
from pathlib import Path

_ROOT = str(Path(__file__).resolve().parent.parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from pyrogram import Client
from pyrogram.errors import FloodWait, ChannelPrivate, ChatAdminRequired
from pyrogram.enums import ChatType
from dotenv import load_dotenv
load_dotenv()

from core.config.settings import settings

# ── Конфигурация ───────────────────────────────────────────────────────────────
DB_PATH = Path(_ROOT) / "data" / "db" / "history_raw_messages.db"
SESSION_PATH = str(Path(_ROOT) / "data" / "sessions" / "parser_session")

CHAT_TYPES = {ChatType.SUPERGROUP, ChatType.GROUP, ChatType.CHANNEL}
PARALLEL = 3          # чатов одновременно
BATCH_SIZE = 500      # INSERT за раз
PROGRESS_EVERY = 2000 # прогресс каждые N сообщений


def init_db(db_path: Path):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS raw_messages (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_name  TEXT,
                message_id INTEGER,
                date       TEXT,
                text       TEXT,
                hash       TEXT UNIQUE
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_hash ON raw_messages(hash)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_chat ON raw_messages(chat_name)")


def batch_insert(db_path: Path, rows: list):
    """Вставляет пачку строк, игнорируя дубликаты (hash UNIQUE)."""
    if not rows:
        return
    with sqlite3.connect(str(db_path), timeout=30) as conn:
        conn.executemany(
            "INSERT OR IGNORE INTO raw_messages (chat_name, message_id, date, text, hash) VALUES (?,?,?,?,?)",
            rows
        )


def make_hash(chat_id: int, message_id: int) -> str:
    return hashlib.md5(f"{chat_id}:{message_id}".encode()).hexdigest()


def get_existing_hashes(db_path: Path, chat_name: str) -> set:
    """Загружает уже обработанные хеши для чата (ускоряет дедупликацию)."""
    with sqlite3.connect(str(db_path)) as conn:
        rows = conn.execute(
            "SELECT hash FROM raw_messages WHERE chat_name = ?", (chat_name,)
        ).fetchall()
    return {r[0] for r in rows}


async def parse_chat(
    client: Client,
    dialog,
    db_path: Path,
    stop_date,
    limit,
    semaphore: asyncio.Semaphore,
    stats: dict,
    idx: int,
):
    async with semaphore:
        chat = dialog.chat
        chat_name = getattr(dialog.chat, 'title', None) or getattr(dialog.chat, 'username', None) or str(chat.id)
        chat_id = chat.id

        existing = get_existing_hashes(db_path, chat_name)
        batch = []
        count = 0
        skipped = 0

        try:
            async for msg in client.get_chat_history(chat_id, limit=limit):
                text = msg.text or msg.caption or ""
                if not text:
                    continue

                if stop_date and msg.date.replace(tzinfo=timezone.utc) < stop_date:
                    break

                h = make_hash(chat_id, msg.id)
                if h in existing:
                    skipped += 1
                    continue

                batch.append((
                    chat_name,
                    msg.id,
                    msg.date.isoformat(),
                    text,
                    h,
                ))
                existing.add(h)
                count += 1

                if len(batch) >= BATCH_SIZE:
                    batch_insert(db_path, batch)
                    batch = []

                if count % PROGRESS_EVERY == 0:
                    date_str = msg.date.strftime("%Y-%m-%d") if msg.date else "?"
                    print(f"  [{idx:3d}] {chat_name[:35]:<35} {count:>6} сообщ. (до {date_str})")

            batch_insert(db_path, batch)

            stats["total"] += count
            stats["chats"] += 1
            if count > 0:
                print(f"  [{idx:3d}] ✅ {chat_name[:45]:<45} {count:>6} (+{skipped} пропущено)")

        except (ChannelPrivate, ChatAdminRequired):
            print(f"  [{idx:3d}] 🔒 {chat_name} — нет доступа")
        except FloodWait as e:
            print(f"  [{idx:3d}] ⏳ FloodWait {e.value}s в {chat_name}")
            await asyncio.sleep(e.value + 5)
        except Exception as e:
            print(f"  [{idx:3d}] ❌ {chat_name}: {e}")


async def main(from_date, limit):
    stop_date = None
    if from_date:
        stop_date = datetime.strptime(from_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)

    # Инициализация БД
    init_db(DB_PATH)
    print(f"📦 База: {DB_PATH}")

    # Pyrogram клиент — session_string (in_memory, no updates)
    session_str = None
    for path in [
        Path(_ROOT) / "data/sessions/alexey_pyrogram.txt",
        Path(_ROOT) / "data/sessions/session_string_pyrogram.txt",
    ]:
        try:
            content = path.read_text().strip()
            if content:
                session_str = content
                break
        except FileNotFoundError:
            continue

    if session_str:
        client = Client(
            name="all_messages_parser",
            api_id=settings.TELEGRAM_API_ID,
            api_hash=settings.TELEGRAM_API_HASH,
            session_string=session_str,
            in_memory=True,
            no_updates=True,
            sleep_threshold=60,
        )
    else:
        client = Client(
            name=SESSION_PATH,
            api_id=settings.TELEGRAM_API_ID,
            api_hash=settings.TELEGRAM_API_HASH,
            no_updates=True,
            sleep_threshold=60,
        )

    await client.start()
    me = await client.get_me()
    print(f"👤 Аккаунт: {me.first_name} (@{me.username})")

    # Собираем все диалоги нужных типов
    print("📋 Загружаем список чатов...")
    dialogs = []
    async for d in client.get_dialogs():
        if d.chat.type in CHAT_TYPES:
            dialogs.append(d)

    print(f"🎯 Чатов для парсинга: {len(dialogs)}")
    if stop_date:
        print(f"📅 С даты: {stop_date.date()}")
    if limit:
        print(f"🔢 Лимит: {limit} сообщений на чат")
    print()

    stats = {"total": 0, "chats": 0}
    semaphore = asyncio.Semaphore(PARALLEL)

    tasks = [
        asyncio.create_task(
            parse_chat(client, d, DB_PATH, stop_date, limit, semaphore, stats, i + 1)
        )
        for i, d in enumerate(dialogs)
    ]
    await asyncio.gather(*tasks)

    await client.stop()

    print(f"\n{'='*55}")
    print(f"✅ Готово! Чатов: {stats['chats']}, новых сообщений: {stats['total']:,}")

    # Итоговая статистика
    with sqlite3.connect(str(DB_PATH)) as conn:
        total = conn.execute("SELECT COUNT(*) FROM raw_messages").fetchone()[0]
        chats_cnt = conn.execute("SELECT COUNT(DISTINCT chat_name) FROM raw_messages").fetchone()[0]
    print(f"📊 Всего в БД: {total:,} сообщений из {chats_cnt} чатов")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Парсинг всех сообщений из всех Telegram-чатов")
    parser.add_argument("--from-date", help="Дата с (YYYY-MM-DD), по умолчанию — всё")
    parser.add_argument("--limit", type=int, help="Максимум сообщений на чат")
    args = parser.parse_args()

    asyncio.run(main(args.from_date, args.limit))
